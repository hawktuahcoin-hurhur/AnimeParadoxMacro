"""Core macro engine for the Roblox automation"""
import time
import threading
import ctypes
import os
import sys
from ctypes import wintypes
from mouse_controller import (
    click, move_to, hold_key, press_key, hold_key_until_condition,
    get_screen_size, find_image_on_screen, wait_for_image, drag_down,
    hold_key_directinput
)

# Win32 keypress helper
from mouse_controller import win32_press_key
from config import save_config

# Helper function to get app path for resources
def get_app_path():
    """Get the application path for writable data"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)

def get_button_path(relative_path):
    """Get absolute path to button images"""
    return os.path.join(get_app_path(), relative_path)

# Windows API
user32 = ctypes.windll.user32

class MacroEngine:
    def __init__(self, config, status_callback=None):
        self.config = config
        self.running = False
        self.paused = False
        self.thread = None
        self.status_callback = status_callback
        self.ocr_tolerance = config.get("ocr_tolerance", 0.6)
        self.roblox_region = None  # Will store (x, y, width, height) of Roblox window
        self.is_replay = False
        # Stage timing
        self.stage_start_time = None
        # Placement timing configuration (can be set in config)
        self.placement_delay = float(config.get("placement_delay", 0.15))
        self.move_duration = float(config.get("placement_move_duration", 0.12))
        # Allow a longer default timeout for the upgrade confirmation image to appear
        self.upg_confirm_timeout = float(config.get("upg_confirm_timeout", 4.0))
        self.slot_press_delay = float(config.get("slot_press_delay", 0.15))
        # Delay between repeated 'T' presses when spamming upgrades (configurable in settings)
        self.t_press_delay = float(config.get("t_press_delay", 0.08))
        self.reselect_backoff = float(config.get("reselect_backoff", 0.15))
        self.max_retries = int(config.get("placement_max_retries", 8))
    
    def _get_location_key(self, location):
        """Get the folder/config key for a location"""
        location_lower = location.lower()
        if "planet" in location_lower or "namak" in location_lower or "namek" in location_lower:
            return "Planet"
        elif "leaf" in location_lower or "village" in location_lower:
            return "Leaf"
        elif "hollow" in location_lower or "dark" in location_lower:
            return "Dark"
        else:
            return "Leaf"  # Default
    
    def get_roblox_window_region(self):
        """Get the Roblox window region"""
        EnumWindows = user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        GetWindowText = user32.GetWindowTextW
        GetWindowTextLength = user32.GetWindowTextLengthW
        GetWindowRect = user32.GetWindowRect
        IsWindowVisible = user32.IsWindowVisible
        
        result = []
        
        def enum_callback(hwnd, lParam):
            if not IsWindowVisible(hwnd):
                return True
            length = GetWindowTextLength(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                GetWindowText(hwnd, buff, length + 1)
                title = buff.value
                if 'roblox' in title.lower():
                    rect = wintypes.RECT()
                    GetWindowRect(hwnd, ctypes.byref(rect))
                    width = rect.right - rect.left
                    height = rect.bottom - rect.top
                    if width > 200 and height > 200:
                        result.append((rect.left, rect.top, rect.right, rect.bottom))
            return True
        
        EnumWindows(EnumWindowsProc(enum_callback), 0)
        
        if result:
            # Return the largest window (main game window)
            result.sort(key=lambda r: (r[2]-r[0]) * (r[3]-r[1]), reverse=True)
            region = result[0]
            self.update_status(f"Found Roblox window at ({region[0]}, {region[1]}) size {region[2]-region[0]}x{region[3]-region[1]}")
            return region
        return None
        
    def update_status(self, message):
        """Update status message in UI"""
        if self.status_callback:
            self.status_callback(message)
        print(f"[MACRO] {message}")
    
    def _send_discord_webhook(self, is_victory, stage_time_seconds):
        """Send a Discord webhook notification with screenshot and stats"""
        import urllib.request
        import json
        import io
        import base64
        from PIL import ImageGrab
        
        webhook_url = self.config.get("discord_webhook_url", "")
        if not webhook_url:
            return
        
        try:
            # Take screenshot of Roblox window
            screenshot_data = None
            if self.roblox_region:
                x1, y1, x2, y2 = self.roblox_region
                screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
                # Convert to bytes
                img_buffer = io.BytesIO()
                screenshot.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                screenshot_data = img_buffer.getvalue()
            
            # Update stats in config
            if is_victory:
                self.config["stats_wins"] = self.config.get("stats_wins", 0) + 1
            else:
                self.config["stats_losses"] = self.config.get("stats_losses", 0) + 1
            save_config(self.config)
            
            wins = self.config.get("stats_wins", 0)
            losses = self.config.get("stats_losses", 0)
            total = wins + losses
            win_rate = round((wins / total) * 100) if total > 0 else 0
            
            # Format time
            minutes = int(stage_time_seconds // 60)
            seconds = int(stage_time_seconds % 60)
            time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
            
            # Get stage info
            mode = self.config.get("mode", "Story")
            location = self.config.get("location", "Unknown")
            act = self.config.get("act", "Act 1")
            
            # Build embed
            result_emoji = "🏆" if is_victory else "💀"
            result_text = "Victory" if is_victory else "Defeat"
            embed_color = 0x4ADE80 if is_victory else 0xEF4444  # Green or Red
            
            embed = {
                "content": None,
                "embeds": [{
                    "title": f"{result_emoji} {result_text}!",
                    "description": f"**{mode}** - {location} ({act})",
                    "color": embed_color,
                    "fields": [
                        {"name": "⏱️ Stage Time", "value": time_str, "inline": True},
                        {"name": "✅ Wins", "value": str(wins), "inline": True},
                        {"name": "❌ Losses", "value": str(losses), "inline": True},
                        {"name": "📊 Win Rate", "value": f"{win_rate}%", "inline": True}
                    ],
                    "footer": {"text": "AnimeParadoxMacro"},
                    "image": {"url": "attachment://screenshot.png"} if screenshot_data else None
                }]
            }
            
            # Remove None image field if no screenshot
            if not screenshot_data:
                del embed["embeds"][0]["image"]
            
            # Send with multipart form data if we have a screenshot
            if screenshot_data:
                import uuid
                boundary = str(uuid.uuid4())
                
                body = b''
                # Add JSON payload
                body += f'--{boundary}\r\n'.encode()
                body += b'Content-Disposition: form-data; name="payload_json"\r\n'
                body += b'Content-Type: application/json\r\n\r\n'
                body += json.dumps(embed).encode('utf-8')
                body += b'\r\n'
                
                # Add file
                body += f'--{boundary}\r\n'.encode()
                body += b'Content-Disposition: form-data; name="files[0]"; filename="screenshot.png"\r\n'
                body += b'Content-Type: image/png\r\n\r\n'
                body += screenshot_data
                body += b'\r\n'
                body += f'--{boundary}--\r\n'.encode()
                
                req = urllib.request.Request(
                    webhook_url,
                    data=body,
                    headers={
                        'Content-Type': f'multipart/form-data; boundary={boundary}',
                        'User-Agent': 'AnimeParadoxMacro/1.0'
                    }
                )
            else:
                embed["content"] = None
                data = json.dumps(embed).encode('utf-8')
                req = urllib.request.Request(
                    webhook_url, 
                    data=data, 
                    headers={
                        'Content-Type': 'application/json',
                        'User-Agent': 'AnimeParadoxMacro/1.0'
                    }
                )
            
            urllib.request.urlopen(req, timeout=15)
            self.update_status(f"Discord webhook sent: {result_text}")
            
        except Exception as e:
            self.update_status(f"Webhook error: {str(e)}")
            print(f"Discord webhook error: {e}")
    
    def _check_disconnect(self):
        """Check if disconnect.png is detected and handle reconnection"""
        import webbrowser
        
        disconnect_pos = find_image_on_screen(
            get_button_path("buttons/disconnect.png"),
            confidence=0.7,
            region=self.roblox_region
        )
        
        if disconnect_pos:
            self.update_status("⚠️ DISCONNECT DETECTED!")
            private_server_link = self.config.get("private_server_link", "")
            
            if not private_server_link:
                self.update_status("❌ No private server link configured!")
                self.update_status("Please set a private server link in Settings > Auto-Reconnect")
                return False
            
            self.update_status(f"🔄 Reconnecting to private server...")
            try:
                # Open private server link in default browser
                webbrowser.open(private_server_link)
                self.update_status("✓ Private server link opened in browser")
                self.update_status("Waiting 15 seconds for game to load...")
                time.sleep(15)
                
                # Click into game window to focus it
                if self.roblox_region:
                    click_x = self.roblox_region[0] + int((self.roblox_region[2] - self.roblox_region[0]) * 0.7)
                    click_y = (self.roblox_region[1] + self.roblox_region[3]) // 2
                    click(click_x, click_y)
                else:
                    screen_width, screen_height = get_screen_size()
                    click(int(screen_width * 0.7), screen_height // 2)
                time.sleep(2)
                
                self.update_status("✓ Reconnection complete, resuming macro...")
                return True
                
            except Exception as e:
                self.update_status(f"❌ Reconnection failed: {str(e)}")
                return False
        
        return None  # No disconnect detected
    
    def _running_and_not_disconnected(self):
        """Check if macro should continue running (checks both running state and disconnect)"""
        if not self.running:
            return False
        
        # Check for disconnect
        disconnect_result = self._check_disconnect()
        if disconnect_result == False:
            # Disconnect detected but no recovery link configured
            self.running = False
            return False
        elif disconnect_result == True:
            # Reconnected successfully, need to restart navigation
            # This will be handled by the main loop
            pass
        
        return self.running
    
    def _run_auto_challenges_loop(self):
        """Main loop for Auto-Challenges mode"""
        challenge_location = self.config.get("challenge_location", "Leaf Village")
        self.update_status(f"Auto-Challenges: Challenge map = {challenge_location}")
        
        CHALLENGE_INTERVAL = 30 * 60  # 30 minutes in seconds
        last_challenge_time = 0  # Force first challenge immediately
        
        while self.running:
            current_time = time.time()
            time_since_challenge = current_time - last_challenge_time
            
            # Check if it's time for a challenge
            if time_since_challenge >= CHALLENGE_INTERVAL or last_challenge_time == 0:
                self.update_status(f"\n=== CHALLENGE TIME ===")
                
                # Navigate to and complete challenge
                if not self._navigate_to_challenge():
                    self.update_status("Auto-Challenges: Failed to navigate to challenge")
                    time.sleep(5)
                    continue
                
                # Run the challenge game
                if not self._run_challenge_game():
                    self.update_status("Auto-Challenges: Challenge game failed")
                    time.sleep(5)
                    continue
                
                # Update challenge time
                last_challenge_time = time.time()
                self.update_status("Auto-Challenges: Challenge complete! Now running selected stage for 30 minutes...")
                
                # Navigate to selected stage
                if not self._navigate_to_selected_stage():
                    self.update_status("Auto-Challenges: Failed to navigate to selected stage")
                    time.sleep(5)
                    continue
            
            # Run selected stage games until challenge interval
            stage_start_time = time.time()
            while self.running:
                elapsed = time.time() - last_challenge_time
                remaining = CHALLENGE_INTERVAL - elapsed
                
                if remaining <= 0:
                    self.update_status("Auto-Challenges: 30 minutes elapsed, waiting for stage completion...")
                    # Complete current game then return to challenge
                    break
                
                mins_remaining = int(remaining // 60)
                self.update_status(f"Auto-Challenges: {mins_remaining}m until next challenge")
                
                # Run one stage game
                if not self._run_stage_game_for_challenges():
                    self.update_status("Auto-Challenges: Stage game failed, retrying...")
                    time.sleep(2)
                    continue
                
                # After win, check if we should do challenge
                if time.time() - last_challenge_time >= CHALLENGE_INTERVAL:
                    # Click return to go back to lobby
                    self.update_status("Auto-Challenges: Time for challenge, clicking Return...")
                    return_pos = wait_for_image(get_button_path("buttons/return.png"), timeout=30, confidence=0.65,
                                                region=self.roblox_region, running_check=lambda: self.running)
                    if return_pos:
                        move_to(*return_pos, duration=0.3)
                        time.sleep(0.2)
                        click(*return_pos)
                        time.sleep(2)
                    break
    
    def _navigate_to_challenge(self):
        """Navigate to challenge: Areas -> Challenges -> walk forward -> Regular -> trait -> offset click -> Start"""
        self.update_status("Challenge Nav: Starting challenge navigation...")
        
        # Step 1: Find and click "Areas"
        self.update_status("Challenge Nav: Looking for Areas button...")
        areas_pos = wait_for_image(get_button_path("buttons/Areas.png"), timeout=30, confidence=0.65,
                                   region=self.roblox_region, running_check=lambda: self.running)
        if not self._check_running():
            return False
        if not areas_pos:
            self.update_status("Challenge Nav: ✗ Could not find Areas button")
            return False
        
        move_to(*areas_pos, duration=0.3)
        time.sleep(0.2)
        click(*areas_pos)
        time.sleep(1.0)
        self.update_status("Challenge Nav: ✓ Clicked Areas")
        
        # Step 2: Find and click "challenges.png"
        self.update_status("Challenge Nav: Looking for Challenges button...")
        challenges_pos = wait_for_image(get_button_path("buttons/challenges.png"), timeout=30, confidence=0.65,
                                        region=self.roblox_region, running_check=lambda: self.running)
        if not self._check_running():
            return False
        if not challenges_pos:
            self.update_status("Challenge Nav: ✗ Could not find Challenges button")
            return False
        
        move_to(*challenges_pos, duration=0.3)
        time.sleep(0.2)
        click(*challenges_pos)
        time.sleep(1.0)
        self.update_status("Challenge Nav: ✓ Clicked Challenges")
        
        # Step 3: Walk forward until regular.png appears
        self.update_status("Challenge Nav: Walking forward to find Regular...")
        walk_start = time.time()
        regular_pos = None
        while self.running and (time.time() - walk_start) < 15:  # Max 15 seconds walk
            # Check for regular.png while walking
            regular_pos = find_image_on_screen(get_button_path("buttons/regular.png"), confidence=0.65, region=self.roblox_region)
            if regular_pos:
                break
            hold_key_directinput('w', 0.5)
            time.sleep(0.1)
        
        if not self._check_running():
            return False
        if not regular_pos:
            self.update_status("Challenge Nav: ✗ Could not find Regular button")
            return False
        
        self.update_status("Challenge Nav: ✓ Found Regular button")
        
        # Step 4: Click regular.png
        move_to(*regular_pos, duration=0.3)
        time.sleep(0.2)
        click(*regular_pos)
        time.sleep(1.0)
        self.update_status("Challenge Nav: ✓ Clicked Regular")
        
        # Step 5: Search for trait.png
        self.update_status("Challenge Nav: Looking for trait button...")
        trait_pos = wait_for_image(get_button_path("buttons/trait.png"), timeout=15, confidence=0.65,
                                   region=self.roblox_region, running_check=lambda: self.running)
        if not self._check_running():
            return False
        if not trait_pos:
            self.update_status("Challenge Nav: ✗ Could not find trait button")
            return False
        
        # Step 6: Hover over trait, then move X offset 200 and click
        self.update_status("Challenge Nav: Hovering over trait and clicking offset...")
        move_to(*trait_pos, duration=0.3)
        time.sleep(0.3)
        # Move 200 pixels to the right and click
        click_x = trait_pos[0] + 200
        click_y = trait_pos[1]
        move_to(click_x, click_y, duration=0.2)
        time.sleep(0.2)
        click(click_x, click_y)
        time.sleep(0.5)
        self.update_status("Challenge Nav: ✓ Clicked trait offset")
        
        # Step 7: Click Start button
        self.update_status("Challenge Nav: Looking for Start button...")
        start_pos = wait_for_image(get_button_path("buttons/start.png"), timeout=15, confidence=0.65,
                                   region=self.roblox_region, running_check=lambda: self.running)
        if not self._check_running():
            return False
        if not start_pos:
            self.update_status("Challenge Nav: ✗ Could not find Start button")
            return False
        
        move_to(*start_pos, duration=0.3)
        time.sleep(0.2)
        click(*start_pos)
        time.sleep(1.0)
        self.update_status("Challenge Nav: ✓ Clicked Start - Challenge navigation complete")
        
        return True
    
    def _run_challenge_game(self):
        """Run a single challenge game with auto-detected positioning"""
        self.update_status("Challenge Game: Waiting for Yes button...")
        
        # Wait for Yes button
        yes_pos = wait_for_image(get_button_path("buttons/Yes.png"), timeout=60, confidence=0.65,
                                 region=self.roblox_region, running_check=lambda: self.running)
        if not self._check_running():
            return False
        if not yes_pos:
            self.update_status("Challenge Game: ✗ Could not find Yes button")
            return False
        
        self.update_status("Challenge Game: Found Yes button, detecting map...")
        time.sleep(2.0)
        
        # Zoom out first
        self.update_status("Challenge Game: Zooming out...")
        if self.roblox_region:
            center_x = (self.roblox_region[0] + self.roblox_region[2]) // 2
            center_y = (self.roblox_region[1] + self.roblox_region[3]) // 2
            drag_distance = (self.roblox_region[3] - self.roblox_region[1]) - 100
            drag_down(center_x, center_y, distance=drag_distance, duration=0.3)
        time.sleep(0.3)
        hold_key('o', duration=0.5)
        time.sleep(1.0)
        
        # Detect which map we're on by checking challengeacts folder
        detected_map = self._detect_challenge_map()
        self.update_status(f"Challenge Game: Detected map = {detected_map}")
        
        # Do positioning based on detected map
        self._do_challenge_positioning(detected_map)
        
        # Click Yes to start
        self.update_status("Challenge Game: Clicking Yes...")
        yes_pos = find_image_on_screen(get_button_path("buttons/Yes.png"), confidence=0.65, region=self.roblox_region)
        if yes_pos:
            move_to(*yes_pos, duration=0.3)
            time.sleep(0.2)
            click(*yes_pos)
        time.sleep(1.0)
        
        # Start timing
        self.stage_start_time = time.time()
        
        # Phase 2: Place units (using challenge config based on DETECTED map, not config setting)
        self.update_status(f"Challenge Game: Placing units using {detected_map} challenge config...")
        self._place_units_from_config(early_placement=False, override_mode="Auto-Challenges", override_location=detected_map, override_act="Act 1")
        
        # Phase 3: Wait for victory/defeat
        self.update_status("Challenge Game: Waiting for victory/defeat...")
        game_result = None
        while self.running and game_result is None:
            victory_pos = find_image_on_screen(get_button_path("buttons/victory.png"), confidence=0.6, region=self.roblox_region)
            if victory_pos:
                game_result = 'victory'
                break
            
            defeat_pos = find_image_on_screen(get_button_path("buttons/defeat.png"), confidence=0.6, region=self.roblox_region)
            if defeat_pos:
                game_result = 'defeat'
                break
            
            time.sleep(0.5)
        
        if not self._check_running():
            return False
        
        # Calculate stage time and send webhook
        stage_time = time.time() - self.stage_start_time if self.stage_start_time else 0
        is_victory = (game_result == 'victory')
        self.update_status(f"Challenge Game: {game_result.upper()}! Time: {int(stage_time)}s")
        self._send_discord_webhook(is_victory, stage_time)
        
        # Click Return to go back to lobby
        self.update_status("Challenge Game: Clicking Return...")
        time.sleep(2)
        return_pos = wait_for_image(get_button_path("buttons/return.png"), timeout=30, confidence=0.65,
                                    region=self.roblox_region, running_check=lambda: self.running)
        if return_pos:
            move_to(*return_pos, duration=0.3)
            time.sleep(0.2)
            click(*return_pos)
            time.sleep(2)
        
        return True
    
    def _detect_challenge_map(self):
        """Detect which challenge map we're on by checking images in buttons/challengeacts"""
        # Check for each map image
        leaf_pos = find_image_on_screen(get_button_path("buttons/challengeacts/leaf.png"), confidence=0.6, region=self.roblox_region)
        if leaf_pos:
            return "Leaf Village"
        
        planet_pos = find_image_on_screen(get_button_path("buttons/challengeacts/planet.png"), confidence=0.6, region=self.roblox_region)
        if planet_pos:
            return "Planet Namek"
        
        dark_pos = find_image_on_screen(get_button_path("buttons/challengeacts/dark.png"), confidence=0.6, region=self.roblox_region)
        if dark_pos:
            return "Dark Hollow"
        
        # Default to challenge_location from config if not detected
        return self.config.get("challenge_location", "Leaf Village")
    
    def _do_challenge_positioning(self, map_name):
        """Do positioning based on detected challenge map"""
        map_lower = map_name.lower()
        
        if "leaf" in map_lower or "village" in map_lower:
            self.update_status("Challenge Positioning: Leaf Village sequence...")
            hold_key_directinput('a', 2.0)
            time.sleep(0.3)
            hold_key_directinput('w', 1.8)
            time.sleep(0.3)
        
        elif "planet" in map_lower or "namek" in map_lower or "namak" in map_lower:
            self.update_status("Challenge Positioning: Planet Namek sequence...")
            hold_key_directinput('s', 1.1)
            time.sleep(0.3)
            hold_key_directinput('a', 0.2)
            time.sleep(0.3)
        
        elif "dark" in map_lower or "hollow" in map_lower:
            self.update_status("Challenge Positioning: Dark Hollow sequence...")
            hold_key_directinput('a', 1.2)
            time.sleep(0.3)
        
        self.update_status("Challenge Positioning: ✓ Complete")
    
    def _navigate_to_selected_stage(self):
        """Navigate to the selected stage (the one configured in Stage tab) for between-challenge farming"""
        self.update_status("Stage Nav: Navigating to selected stage for farming...")
        
        # Wait for Areas button in lobby
        self.update_status("Stage Nav: Looking for Areas button...")
        areas_pos = wait_for_image(get_button_path("buttons/Areas.png"), timeout=30, confidence=0.65,
                                   region=self.roblox_region, running_check=lambda: self.running)
        if not self._check_running():
            return False
        if not areas_pos:
            self.update_status("Stage Nav: ✗ Could not find Areas button")
            return False
        
        move_to(*areas_pos, duration=0.3)
        time.sleep(0.2)
        click(*areas_pos)
        time.sleep(1.0)
        
        # Use Story mode navigation for the selected stage
        # The selected stage is based on challenge_location config
        challenge_location = self.config.get("challenge_location", "Leaf Village")
        self.update_status(f"Stage Nav: Going to Story mode for {challenge_location}...")
        
        # Navigate through Story mode
        return self._navigate_story_mode_for_challenges(challenge_location)
    
    def _navigate_story_mode_for_challenges(self, location):
        """Navigate Story mode for challenge farming"""
        # Click Story button
        self.update_status("Stage Nav: Looking for Story button...")
        story_pos = wait_for_image(get_button_path("buttons/Story.png"), timeout=30, confidence=0.65,
                                   region=self.roblox_region, running_check=lambda: self.running)
        if not self._check_running():
            return False
        if not story_pos:
            self.update_status("Stage Nav: ✗ Could not find Story button")
            return False
        
        move_to(*story_pos, duration=0.3)
        time.sleep(0.2)
        click(*story_pos)
        time.sleep(1.0)
        
        # Click X button
        x_pos = wait_for_image(get_button_path("buttons/X.png"), timeout=30, confidence=0.65,
                               region=self.roblox_region, running_check=lambda: self.running)
        if x_pos:
            move_to(*x_pos, duration=0.3)
            time.sleep(0.2)
            click(*x_pos)
            time.sleep(0.5)
        
        # Walk forward
        hold_key('w', duration=3.0)
        time.sleep(0.5)
        
        # Navigate to specific location
        location_lower = location.lower()
        if "leaf" in location_lower or "village" in location_lower:
            return self._navigate_to_leaf_village()
        elif "planet" in location_lower or "namek" in location_lower:
            return self._navigate_to_planet_namek()
        elif "dark" in location_lower or "hollow" in location_lower:
            return self._navigate_to_dark_hollow()
        
        return True
    
    def _navigate_to_leaf_village(self):
        """Navigate to Leaf Village and select Act 1"""
        self.update_status("Stage Nav: Looking for Leaf Village...")
        leaf_pos = wait_for_image(get_button_path("buttons/leaf.png"), timeout=30, confidence=0.65,
                                  region=self.roblox_region, running_check=lambda: self.running)
        if leaf_pos:
            move_to(*leaf_pos, duration=0.3)
            time.sleep(0.2)
            click(*leaf_pos)
            time.sleep(0.5)
        
        # Click Act 1
        act_pos = wait_for_image(get_button_path("buttons/Acts/act1.png"), timeout=15, confidence=0.65,
                                 region=self.roblox_region, running_check=lambda: self.running)
        if act_pos:
            move_to(*act_pos, duration=0.3)
            time.sleep(0.2)
            click(*act_pos)
            time.sleep(0.5)
        
        return True
    
    def _navigate_to_planet_namek(self):
        """Navigate to Planet Namek and select Act 1"""
        self.update_status("Stage Nav: Looking for Planet Namek...")
        planet_pos = wait_for_image(get_button_path("buttons/planet.png"), timeout=30, confidence=0.65,
                                    region=self.roblox_region, running_check=lambda: self.running)
        if planet_pos:
            move_to(*planet_pos, duration=0.3)
            time.sleep(0.2)
            click(*planet_pos)
            time.sleep(0.5)
        
        # Click Act 1
        act_pos = wait_for_image(get_button_path("buttons/Acts/act1.png"), timeout=15, confidence=0.65,
                                 region=self.roblox_region, running_check=lambda: self.running)
        if act_pos:
            move_to(*act_pos, duration=0.3)
            time.sleep(0.2)
            click(*act_pos)
            time.sleep(0.5)
        
        return True
    
    def _navigate_to_dark_hollow(self):
        """Navigate to Dark Hollow and select Act 1"""
        self.update_status("Stage Nav: Looking for Dark Hollow...")
        dark_pos = wait_for_image(get_button_path("buttons/dark.png"), timeout=30, confidence=0.65,
                                  region=self.roblox_region, running_check=lambda: self.running)
        if dark_pos:
            move_to(*dark_pos, duration=0.3)
            time.sleep(0.2)
            click(*dark_pos)
            time.sleep(0.5)
        
        # Click Act 1
        act_pos = wait_for_image(get_button_path("buttons/Acts/act1.png"), timeout=15, confidence=0.65,
                                 region=self.roblox_region, running_check=lambda: self.running)
        if act_pos:
            move_to(*act_pos, duration=0.3)
            time.sleep(0.2)
            click(*act_pos)
            time.sleep(0.5)
        
        return True
    
    def _run_stage_game_for_challenges(self):
        """Run a single stage game during challenge farming period"""
        # Wait for Yes button
        yes_pos = wait_for_image(get_button_path("buttons/Yes.png"), timeout=120, confidence=0.65,
                                 region=self.roblox_region, running_check=lambda: self.running)
        if not self._check_running():
            return False
        if not yes_pos:
            return False
        
        time.sleep(2.0)
        
        # Zoom out and position (if not replay)
        if not self.is_replay:
            if self.roblox_region:
                center_x = (self.roblox_region[0] + self.roblox_region[2]) // 2
                center_y = (self.roblox_region[1] + self.roblox_region[3]) // 2
                drag_distance = (self.roblox_region[3] - self.roblox_region[1]) - 100
                drag_down(center_x, center_y, distance=drag_distance, duration=0.3)
            time.sleep(0.3)
            hold_key('o', duration=0.5)
            time.sleep(1.0)
            
            # Do positioning based on challenge_location
            challenge_location = self.config.get("challenge_location", "Leaf Village")
            self._do_challenge_positioning(challenge_location)
        
        # Click Yes
        yes_pos = find_image_on_screen(get_button_path("buttons/Yes.png"), confidence=0.65, region=self.roblox_region)
        if yes_pos:
            move_to(*yes_pos, duration=0.3)
            time.sleep(0.2)
            click(*yes_pos)
        time.sleep(1.0)
        
        self.stage_start_time = time.time()
        
        # Place units using the Story config for challenge_location
        challenge_location = self.config.get("challenge_location", "Leaf Village")
        self._place_units_from_config(early_placement=False, override_mode="Story", override_location=challenge_location, override_act="Act 1")
        
        # Wait for victory/defeat
        game_result = None
        while self.running and game_result is None:
            victory_pos = find_image_on_screen(get_button_path("buttons/victory.png"), confidence=0.6, region=self.roblox_region)
            if victory_pos:
                game_result = 'victory'
                break
            
            defeat_pos = find_image_on_screen(get_button_path("buttons/defeat.png"), confidence=0.6, region=self.roblox_region)
            if defeat_pos:
                game_result = 'defeat'
                break
            
            time.sleep(0.5)
        
        if not self._check_running():
            return False
        
        # Send webhook
        stage_time = time.time() - self.stage_start_time if self.stage_start_time else 0
        is_victory = (game_result == 'victory')
        self._send_discord_webhook(is_victory, stage_time)
        
        # Click Replay to continue farming
        self.update_status("Stage Game: Clicking Replay...")
        time.sleep(2)
        replay_pos = wait_for_image(get_button_path("buttons/replay.png"), timeout=30, confidence=0.65,
                                    region=self.roblox_region, running_check=lambda: self.running)
        if replay_pos:
            move_to(*replay_pos, duration=0.3)
            time.sleep(0.2)
            click(*replay_pos)
            time.sleep(1)
            self.is_replay = True
        
        return True

    def start(self):
        """Start the macro"""
        if self.running:
            return
        
        self.running = True
        self.paused = False
        self.thread = threading.Thread(target=self._run_macro, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the macro"""
        self.running = False
        self.paused = False
        self.update_status("Macro stopped")
    
    def pause(self):
        """Pause the macro"""
        self.paused = True
        self.update_status("Macro paused")
    
    def resume(self):
        """Resume the macro"""
        self.paused = False
        self.update_status("Macro resumed")
    
    def _check_running(self):
        """Check if macro should continue running"""
        while self.paused and self.running:
            time.sleep(0.1)
        return self.running
    
    def _run_macro(self):
        """Main macro execution loop"""
        try:
            self.update_status("=== MACRO STARTED ===")
            self.update_status("Step 1: Initializing...")
            self.is_replay = False
            self.update_status("Step 1: Initialization complete")
            
            # Get Roblox window region
            self.update_status("Step 2: Detecting Roblox window...")
            # If region already provided externally (e.g. attached by UI), use it
            if self.roblox_region:
                self.update_status(f"Step 2: Using pre-set Roblox region: {self.roblox_region}")
            else:
                self.roblox_region = self.get_roblox_window_region()
                if not self.roblox_region:
                    self.update_status("Step 2: Roblox window not found, using full screen")
                    self.roblox_region = None
                else:
                    self.update_status("Step 2: Roblox window detected")
            
            # Click into game window to focus it (click further to the right side)
            self.update_status("Step 3: Focusing Roblox window...")
            if self.roblox_region:
                # Click 70% to the right of the window to avoid UI elements
                click_x = self.roblox_region[0] + int((self.roblox_region[2] - self.roblox_region[0]) * 0.7)
                click_y = (self.roblox_region[1] + self.roblox_region[3]) // 2
                click(click_x, click_y)
            else:
                screen_width, screen_height = get_screen_size()
                click(int(screen_width * 0.7), screen_height // 2)
            time.sleep(0.5)
            self.update_status("Step 3: Window focused")
            
            # Initial game navigation
            self.update_status("Step 4: Navigating to game...")
            
            # Check if Auto-Challenges mode
            mode = self.config.get("mode", "Story")
            if mode == "Auto-Challenges":
                self.update_status("=== AUTO-CHALLENGES MODE ===")
                self._run_auto_challenges_loop()
                return
            
            if not self._navigate_to_game():
                self.update_status("Step 4: Navigation failed")
                return
            self.update_status("Step 4: Navigation complete (with positioning)")
            
            # Main game loop
            game_count = 0
            while self.running:
                # Check for disconnect before starting each game
                disconnect_result = self._check_disconnect()
                if disconnect_result == False:
                    self.update_status("Stopping macro due to disconnect with no recovery link")
                    return
                elif disconnect_result == True:
                    # Reconnected successfully, continue with navigation
                    self.update_status("Step 4: Re-navigating after reconnect...")
                    if not self._navigate_to_game():
                        self.update_status("Step 4: Navigation failed after reconnect")
                        return
                    self.update_status("Step 4: Navigation complete after reconnect")
                
                game_count += 1
                self.update_status(f"\n=== GAME {game_count} START ===")
                
                # Track if this game was a win or loss
                game_result = None  # Will be 'victory' or 'defeat'
                
                # Phase 1: Wait for "Yes" button (detect only, don't click yet)
                self.update_status("Phase 1: Waiting for Yes button...")
                yes_pos = wait_for_image(get_button_path("buttons/Yes.png"), timeout=None, confidence=0.65, region=self.roblox_region, running_check=lambda: self.running)
                
                if not self._check_running():
                    return
                
                if yes_pos:
                    self.update_status("Phase 1: Found Yes button, waiting 2 seconds...")
                    time.sleep(2.0)
                    
                    # Phase 1.5: Zoom out by dragging down BEFORE early placement (skip on replay)
                    if not self.is_replay:
                        self.update_status("Phase 1.5: Zooming out...")
                        time.sleep(0.3)
                        if self.roblox_region:
                            center_x = (self.roblox_region[0] + self.roblox_region[2]) // 2
                            center_y = (self.roblox_region[1] + self.roblox_region[3]) // 2
                            drag_distance = (self.roblox_region[3] - self.roblox_region[1]) - 100
                            drag_down(center_x, center_y, distance=drag_distance, duration=0.3)
                        else:
                            screen_width, screen_height = get_screen_size()
                            drag_down(screen_width // 2, screen_height // 2, distance=screen_height - 100, duration=0.3)
                        time.sleep(0.3)
                        
                        # Phase 1.6: Hold O key before early placement (skip on replay)
                        self.update_status("Phase 1.6: Holding O key...")
                        time.sleep(0.5)
                        hold_key('o', duration=0.5)
                        time.sleep(1.0)
                    else:
                        self.update_status("Phase 1.5-1.6: Skipping zoom/O key (replay)")
                    
                    # Phase 1.65: Position character in stage based on location (works for both Story and Legend modes)
                    mode = self.config.get("mode", "Story")
                    location = self.config.get("location", "Leaf Village")
                    location_lower = location.lower()
                    self.update_status(f"Positioning: Mode={mode}, Location={location}")
                    
                    if mode == "Siege" and ("blue" in location_lower or "dungeon" in location_lower):
                        self.update_status("Positioning: Blue Dungeon (Siege) detected, starting positioning sequence...")
                        
                        # Walk forward with W for 5 seconds
                        self.update_status("Positioning: Holding 'W' to move forward for 5 seconds...")
                        hold_key_directinput('w', 5.0)
                        time.sleep(0.3)
                        
                        self.update_status("Positioning: ✓ Positioning sequence complete")
                    
                    elif "leaf" in location_lower or "village" in location_lower:
                        self.update_status("Positioning: Leaf Village detected, starting positioning sequence...")
                        
                        # Hold A to move right for 5 seconds
                        self.update_status("Positioning: Holding 'A' to move right for 5 seconds...")
                        hold_key_directinput('a', 2.0)
                        time.sleep(0.3)
                        
                        # Hold W to move forward for 2 seconds
                        self.update_status("Positioning: Holding 'W' to move forward for 2 seconds...")
                        hold_key_directinput('w', 1.8)
                        time.sleep(0.3)
                        
                        self.update_status("Positioning: ✓ Positioning sequence complete")
                    
                    elif "namak" in location_lower or "namek" in location_lower or "planet" in location_lower:
                        self.update_status("Positioning: Planet Namek detected, starting positioning sequence...")
                        
                        # Hold S to move down for 0.8 seconds
                        self.update_status("Positioning: Holding 'S' to move down for 0.8 seconds...")
                        hold_key_directinput('s', 1.1)
                        time.sleep(0.3)
                        
                        # Hold A to move left for 0.2 seconds
                        self.update_status("Positioning: Holding 'A' to move left for 0.2 seconds...")
                        hold_key_directinput('a', 0.2)
                        time.sleep(0.3)
                        
                        self.update_status("Positioning: ✓ Positioning sequence complete")
                    
                    elif "hollow" in location_lower or "dark" in location_lower:
                        self.update_status("Positioning: Dark Hollow detected, starting positioning sequence...")
                        
                        # Hold A to move left for 0.3 seconds
                        self.update_status("Positioning: Holding 'A' to move left for 0.3 seconds...")
                        hold_key_directinput('a', 1.2)
                        time.sleep(0.3)
                        
                        self.update_status("Positioning: ✓ Positioning sequence complete")
                    
                    # Phase 1.7: Early unit placement for units with PlaceBeforeYes toggle
                    self.update_status("Phase 1.7: Checking for early placement units...")
                    self._place_units_from_config(early_placement=True)
                    
                    # Phase 1.8: Re-find Yes button and click it
                    self.update_status("Phase 1.8: Re-locating Yes button...")
                    yes_pos = find_image_on_screen(get_button_path("buttons/Yes.png"), confidence=0.65, region=self.roblox_region)
                    if not yes_pos:
                        self.update_status("Phase 1.8: Could not re-locate Yes button, searching again...")
                        yes_pos = wait_for_image(get_button_path("buttons/Yes.png"), timeout=None, confidence=0.60, region=self.roblox_region, running_check=lambda: self.running)
                    
                    if yes_pos:
                        self.update_status("Phase 1.9: Clicking Yes button...")
                        move_to(*yes_pos, duration=0.3)
                        time.sleep(0.2)
                        click(*yes_pos)
                        # Start stage timer after clicking Yes
                        self.stage_start_time = time.time()
                        time.sleep(0.5)
                    else:
                        self.update_status("Phase 1.9: Warning - Yes button not found after early placement")
                else:
                    self.update_status("Phase 1: Could not find Yes button, skipping...")
                
                # Phase 2: Normal unit placement from config
                self.update_status("Phase 2: Starting unit placement...")
                self._place_units_from_config(early_placement=False)
                
                # Phase 3: Wait for game end (victory, defeat, or click)
                self.update_status("Phase 3: Waiting for game to end...")
                game_ended = False
                
                while self.running and not game_ended:
                    # Check for victory
                    victory_pos = find_image_on_screen(get_button_path("buttons/victory.png"), confidence=0.65, region=self.roblox_region)
                    if victory_pos:
                        self.update_status("Phase 3: Victory detected!")
                        game_result = 'victory'
                        time.sleep(1)
                        game_ended = True
                        break
                    
                    # Check for defeat
                    defeat_pos = find_image_on_screen(get_button_path("buttons/defeat.png"), confidence=0.65, region=self.roblox_region)
                    if defeat_pos:
                        self.update_status("Phase 3: Defeat detected!")
                        game_result = 'defeat'
                        time.sleep(1)
                        game_ended = True
                        break
                    
                    # Check for click button (spam click until victory)
                    click_pos = find_image_on_screen(get_button_path("buttons/click.png"), confidence=0.65, region=self.roblox_region)
                    if click_pos:
                        self.update_status("Phase 3: Click button detected, spam clicking...")
                        # Spam click until victory is detected
                        spam_count = 0
                        while self.running and spam_count < 100:
                            click(*click_pos)
                            time.sleep(0.1)
                            spam_count += 1
                            
                            # Check for victory during spam
                            victory_check = find_image_on_screen(get_button_path("buttons/victory.png"), confidence=0.65, region=self.roblox_region)
                            if victory_check:
                                self.update_status("Phase 3: Victory detected after clicking!")
                                game_result = 'victory'
                                game_ended = True
                                break
                        
                        if game_ended:
                            break
                    
                    time.sleep(0.5)
                
                if not self._check_running():
                    return
                
                # Calculate stage time and send webhook
                if game_result and self.stage_start_time:
                    stage_time = time.time() - self.stage_start_time
                    is_victory = game_result == 'victory'
                    # Send webhook notification with screenshot
                    self._send_discord_webhook(is_victory, stage_time)
                
                # Phase 4: Click replay button
                self.update_status("Phase 4: Looking for Replay button...")
                replay_pos = wait_for_image(get_button_path("buttons/replay.png"), timeout=30, confidence=0.65, region=self.roblox_region, running_check=lambda: self.running)
                
                if replay_pos:
                    self.update_status("Phase 4: Found Replay, clicking...")
                    move_to(*replay_pos, duration=0.3)
                    time.sleep(0.2)
                    click(*replay_pos)
                    time.sleep(1)
                    self.is_replay = True
                else:
                    self.update_status("Phase 4: Could not find Replay button")
                
                self.update_status(f"=== GAME {game_count} COMPLETE ===")
                time.sleep(2)
                    
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.running = False
            self.update_status("=== MACRO STOPPED ===")
    
    def _place_units_from_config(self, early_placement=False, override_mode=None, override_location=None, override_act=None):
        """Place units based on current location/act config
        
        Args:
            early_placement: If True, only place units with PlaceBeforeYes=True
                           If False, only place units without PlaceBeforeYes or PlaceBeforeYes=False
            override_mode: Override the mode from config
            override_location: Override the location from config
            override_act: Override the act from config
        """
        import json
        
        location = override_location or self.config.get("location", "Leaf")
        act = override_act or self.config.get("act", "Act 1")
        mode = override_mode or self.config.get("mode", "Story")
        
        # Map mode folder names
        if mode == "Auto-Challenges":
            mode_folder = "Challenges"
        elif mode == "Raids":
            mode_folder = "Raid"
        else:
            mode_folder = mode
        
        # Get config path - use get_app_path() for portable exe support
        config_path = os.path.join(get_app_path(), "Settings", mode_folder, location, f"{act}.json")
        
        if not os.path.exists(config_path):
            self.update_status(f"Unit Placement: No config found for {location}/{act}")
            return False
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                unit_config = json.load(f)
        except Exception as e:
            self.update_status(f"Unit Placement: Error loading config: {e}")
            return False
        
        units = unit_config.get("Units", [])
        # Filter units based on Enabled and PlaceBeforeYes toggle
        if early_placement:
            enabled_units = [u for u in units if u.get("Enabled", False) and u.get("PlaceBeforeYes", False)]
        else:
            enabled_units = [u for u in units if u.get("Enabled", False) and not u.get("PlaceBeforeYes", False)]
        
        if not enabled_units:
            if early_placement:
                self.update_status("Unit Placement: No early placement units in config")
            else:
                self.update_status("Unit Placement: No enabled units in config")
            return False
        
        placement_type = "early" if early_placement else "normal"
        self.update_status(f"Unit Placement: Placing {len(enabled_units)} {placement_type} units...")
        
        for unit in enabled_units:
            if not self._check_running():
                return False
            
            unit_index = unit.get("Index", 0)
            slot = unit.get("Slot", "1")
            x = unit.get("X", "")
            y = unit.get("Y", "")
            upgrade_raw = unit.get("Upgrade", "0")
            # Handle "Max" upgrade level (use a large number like 99 to keep upgrading)
            if str(upgrade_raw).lower() == "max":
                upgrade_level = 99  # Will upgrade until no more upgrades available
            else:
                try:
                    upgrade_level = int(upgrade_raw)
                except ValueError:
                    upgrade_level = 0
            
            # Skip if coordinates not set
            if not x or not y:
                self.update_status(f"Unit Placement: Unit {unit_index} - No coordinates set, skipping")
                continue
            
            try:
                # Coordinates are absolute screen coordinates (saved directly from picker)
                click_x = int(x)
                click_y = int(y)
            except ValueError:
                self.update_status(f"Unit Placement: Unit {unit_index} - Invalid coordinates, skipping")
                continue
            
            self.update_status(f"Unit Placement: Placing Unit {unit_index} (Slot {slot}) at ({click_x}, {click_y})")
            
            # ========== INFINITE PLACEMENT LOOP - NEVER GIVE UP ==========
            attempt_count = 0
            
            while self.running:
                if not self._check_running():
                    return False
                
                attempt_count += 1
                self.update_status(f"Unit Placement: === ATTEMPT {attempt_count} for Unit {unit_index} ===")
                
                # Step 1: Press slot key multiple times and click to initiate placement
                self.update_status(f"Unit Placement: Pressing slot {slot} and clicking...")
                if str(slot) != "0":
                    # Press slot key 3 times with delays to ensure it registers
                    for _ in range(3):
                        win32_press_key(slot)
                        time.sleep(0.1)
                    time.sleep(self.slot_press_delay)
                
                move_to(click_x, click_y, duration=0.1)
                time.sleep(0.15)
                click(click_x, click_y)
                time.sleep(0.25)
                
                # Step 2: INFINITE CONFIRMATION LOOP - keep pressing slot and clicking until upg.png found
                self.update_status(f"Unit Placement: Starting infinite confirmation loop...")
                confirm_clicks = 0
                upg_pos = None
                
                while self.running:
                    if not self._check_running():
                        return False
                    
                    confirm_clicks += 1
                    
                    # Press slot key once
                    if str(slot) != "0":
                        win32_press_key(slot)
                        time.sleep(0.1)
                    
                    # Move to position and click with proper delays
                    move_to(click_x, click_y, duration=0.1)
                    time.sleep(0.1)
                    click(click_x, click_y)
                    time.sleep(0.2)
                    
                    # Check for upg.png after each click
                    upg_pos = find_image_on_screen("unit stuff/upg.png", confidence=0.70, region=self.roblox_region)
                    if upg_pos:
                        self.update_status(f"Unit Placement: Found upg.png at {upg_pos} after {confirm_clicks} confirm clicks!")
                        break
                    
                    # Log progress every 10 clicks
                    if confirm_clicks % 10 == 0:
                        self.update_status(f"Unit Placement: Confirm clicks: {confirm_clicks}...")
                
                # Step 3: Check if placement succeeded
                if upg_pos:
                    self.update_status(f"Unit Placement: ✓ Unit {unit_index} PLACED after {confirm_clicks} confirm clicks!")
                    
                    # === PLACEMENT SUCCEEDED - NOW DO POST-PLACEMENT ACTIONS ===
                    
                    # POST-ACTION 1: AutoUpgrade toggle (ALWAYS press before manual upgrades)
                    if unit.get("AutoUpgrade", False) or upgrade_level > 0:
                        self.update_status(f"Unit Placement: Pressing AutoUpgrade for Unit {unit_index}...")
                        time.sleep(0.5)  # Wait longer to ensure panel is stable
                        autoup_pos = find_image_on_screen(get_button_path("buttons/autoupg.png"), confidence=0.55, region=self.roblox_region)
                        if autoup_pos:
                            move_to(*autoup_pos, duration=self.move_duration)
                            time.sleep(0.15)
                            click(*autoup_pos)
                            self.update_status(f"Unit Placement: Clicked autoupg.png")
                            time.sleep(0.5)  # Wait longer after clicking to prevent double-click
                        else:
                            self.update_status(f"Unit Placement: autoupg.png not found, pressing Z key...")
                            win32_press_key('z')
                            time.sleep(0.5)
                    
                    # POST-ACTION 2: Manual upgrades
                    if upgrade_level > 0:
                        is_max = (upgrade_level == 99)
                        
                        if is_max:
                            # MAX UPGRADE - infinite loop until upgmax.png or defeat
                            self.update_status(f"Unit Placement: Upgrading Unit {unit_index} to MAX (pressing T)...")
                            upgrade_presses = 0
                            
                            while self.running:
                                # Check for defeat
                                if find_image_on_screen(get_button_path("buttons/defeat.png"), confidence=0.65, region=self.roblox_region):
                                    self.update_status(f"Unit Placement: Defeat detected, stopping upgrades")
                                    break
                                
                                # Check for max upgrade reached (very high confidence to avoid false positives)
                                if find_image_on_screen("unit stuff/upgmax.png", confidence=0.75, region=self.roblox_region):
                                    self.update_status(f"Unit Placement: ✓ MAX upgrade reached after {upgrade_presses} T presses!")
                                    break
                                
                                # Press T key to upgrade (using win32 for proper Roblox detection)
                                win32_press_key('t')
                                upgrade_presses += 1
                                if upgrade_presses % 10 == 0:
                                    self.update_status(f"Unit Placement: T presses: {upgrade_presses}...")
                                
                                time.sleep(self.t_press_delay)
                        else:
                            # FIXED LEVEL UPGRADE
                            self.update_status(f"Unit Placement: Upgrading Unit {unit_index} to level {upgrade_level} (pressing T)...")
                            
                            for target_lvl in range(1, upgrade_level + 1):
                                if not self.running:
                                    break
                                
                                target_img = f"unit stuff/upg{target_lvl}.png"
                                self.update_status(f"Unit Placement: Upgrading to level {target_lvl}...")
                                upgrade_presses = 0
                                
                                while self.running:
                                    # Check for defeat
                                    if find_image_on_screen(get_button_path("buttons/defeat.png"), confidence=0.65, region=self.roblox_region):
                                        self.update_status(f"Unit Placement: Defeat detected, stopping upgrades")
                                        break
                                    
                                    # Check if level reached (very high confidence to avoid false positives)
                                    if find_image_on_screen(target_img, confidence=0.90, region=self.roblox_region):
                                        self.update_status(f"Unit Placement: ✓ Level {target_lvl} reached!")
                                        break
                                    
                                    # Press T key to upgrade (using win32 for proper Roblox detection)
                                    win32_press_key('t')
                                    upgrade_presses += 1
                                    if upgrade_presses % 10 == 0:
                                        self.update_status(f"Unit Placement: T presses: {upgrade_presses}...")
                                    
                                    time.sleep(self.t_press_delay)
                    
                    # POST-ACTION 3: Close unit panel
                    self.update_status(f"Unit Placement: Closing unit panel...")
                    time.sleep(0.2)
                    x_btn = find_image_on_screen(get_button_path("buttons/X.png"), confidence=0.60, region=self.roblox_region)
                    if x_btn:
                        move_to(*x_btn, duration=self.move_duration)
                        time.sleep(0.1)
                        click(*x_btn)
                    else:
                        # Click center to close
                        if self.roblox_region:
                            cx = (self.roblox_region[0] + self.roblox_region[2]) // 2
                            cy = (self.roblox_region[1] + self.roblox_region[3]) // 2
                        else:
                            cx, cy = get_screen_size()
                            cx, cy = cx // 2, cy // 2
                        move_to(cx, cy, duration=self.move_duration)
                        time.sleep(0.1)
                        click(cx, cy)
                    
                    time.sleep(0.2)
                    break  # EXIT the outer placement loop - unit is done!
            
            # Small delay between units
            time.sleep(0.3)
        
        self.update_status(f"Unit Placement: Completed placing {len(enabled_units)} units")
        return True
    
    def _navigate_to_game(self):
        """Navigate through menus to start the game"""
        if self.is_replay:
            self.update_status("Navigation: Skipping (replay)")
            return True
            
        mode = self.config.get("mode", "Story")
        self.update_status(f"Navigation: Mode = {mode}")
        
        # Step 1: Find and click "Areas"
        self.update_status("Navigation: Searching for 'Areas' button (image detection)...")
        areas_pos = wait_for_image(get_button_path("buttons/Areas.png"), timeout=30, confidence=0.65, 
                                   region=self.roblox_region, running_check=lambda: self.running)
        
        if not self._check_running():
            return False
        
        if not areas_pos:
            self.update_status("Navigation: ✗ Could not find 'Areas' button")
            return False
        
        self.update_status(f"Navigation: ✓ Found 'Areas' at {areas_pos}, hovering and clicking...")
        move_to(*areas_pos, duration=0.3)
        time.sleep(0.2)
        click(*areas_pos)
        time.sleep(1.0)
        
        # For Raids and Siege, go directly to mode-specific navigation
        if mode == "Raids":
            return self._navigate_raid_mode()
        elif mode == "Siege":
            return self._navigate_siege_mode()
        
        # For Story/Legend modes, click Story button first
        # Step 2: Look for and click "Story"
        self.update_status("Navigation: Searching for 'Story' button (image detection)...")
        story_pos = wait_for_image(get_button_path("buttons/Story.png"), timeout=None, confidence=0.65,
                                   region=self.roblox_region, running_check=lambda: self.running)
        
        if not self._check_running():
            return False
        
        if not story_pos:
            self.update_status("Navigation: ✗ Could not find 'Story' button")
            return False
        
        self.update_status(f"Navigation: ✓ Found 'Story' at {story_pos}, hovering and clicking...")
        move_to(*story_pos, duration=0.3)
        time.sleep(0.2)
        click(*story_pos)
        time.sleep(1.0)
        
        # Step 3: Look for "X" button
        self.update_status("Navigation: Searching for 'X' button...")
        x_pos = wait_for_image(get_button_path("buttons/X.png"), timeout=None, confidence=0.65, region=self.roblox_region, running_check=lambda: self.running)
        
        if not self._check_running():
            return False
        
        if not x_pos:
            self.update_status("Navigation: ✗ Could not find 'X' button")
            return False
        
        self.update_status(f"Navigation: ✓ Found 'X' at {x_pos}, hovering and clicking...")
        move_to(*x_pos, duration=0.3)
        time.sleep(0.2)
        click(*x_pos)
        time.sleep(0.5)
        
        # Step 4: Hold W to walk forward
        self.update_status("Navigation: Walking forward (holding W)...")
        hold_key('w', duration=3.0)
        time.sleep(0.5)
        
        if mode == "Story":
            return self._navigate_story_mode()
        elif mode == "Legend":
            return self._navigate_legend_mode()
        
        return True
    
    def _navigate_raid_mode(self):
        """Navigate Raid mode - Areas -> Raid -> walk forward -> walk left -> find Frozen Gate"""
        location = self.config.get("location", "Frozen Gate")
        act = self.config.get("act", "Act 1").replace(" ", "").replace("Act", "")
        self.update_status(f"Raid Mode: Location = {location}, Act = {act}")
        
        # Step 1: Find and click "raids" button
        self.update_status("Raid Mode: Step 1 - Searching for 'Raid' button...")
        raid_pos = wait_for_image(get_button_path("buttons/raids.png"), timeout=30, confidence=0.65, 
                                  region=self.roblox_region, running_check=lambda: self.running)
        
        if not self._check_running():
            return False
        
        if not raid_pos:
            self.update_status("Raid Mode: ✗ Could not find 'Raid' button")
            return False
        
        self.update_status(f"Raid Mode: ✓ Found 'Raid' at {raid_pos}, clicking...")
        move_to(*raid_pos, duration=0.3)
        time.sleep(0.2)
        click(*raid_pos)
        time.sleep(1.0)
        
        # Step 2: Walk forward with W for 3 seconds
        self.update_status("Raid Mode: Step 2 - Walking forward (W) for 3 seconds...")
        hold_key_directinput('w', 3.0)
        time.sleep(0.3)
        
        # Step 3: Walk left with A for 3 seconds
        self.update_status("Raid Mode: Step 3 - Walking left (A) for 3 seconds...")
        hold_key_directinput('a', 3.0)
        time.sleep(0.3)
        
        # Step 4: Find and click "Create Match" button
        self.update_status("Raid Mode: Step 4 - Searching for 'Create Match' button...")
        creatematch_pos = wait_for_image(get_button_path("buttons/creatematch.png"), timeout=30, confidence=0.65, 
                                         region=self.roblox_region, running_check=lambda: self.running)
        
        if not self._check_running():
            return False
        
        if not creatematch_pos:
            self.update_status("Raid Mode: ✗ Could not find 'Create Match' button")
            return False
        
        self.update_status(f"Raid Mode: ✓ Found 'Create Match' at {creatematch_pos}, clicking...")
        move_to(*creatematch_pos, duration=0.3)
        time.sleep(0.2)
        click(*creatematch_pos)
        time.sleep(1.0)
        
        # Step 5: Find Frozen Gate button
        self.update_status("Raid Mode: Step 5 - Searching for 'Frozen Gate'...")
        frozen_pos = wait_for_image(get_button_path("buttons/Frozen.png"), timeout=30, confidence=0.65, 
                                    region=self.roblox_region, running_check=lambda: self.running)
        
        if not self._check_running():
            return False
        
        if not frozen_pos:
            self.update_status("Raid Mode: ✗ Could not find 'Frozen Gate'")
            return False
        
        # Step 6: Click on Frozen Gate
        self.update_status(f"Raid Mode: ✓ Found 'Frozen Gate' at {frozen_pos}, clicking...")
        move_to(*frozen_pos, duration=0.3)
        time.sleep(0.2)
        click(*frozen_pos)
        time.sleep(0.5)
        
        # Step 7: Click on the act
        act_image = get_button_path(f"buttons/Acts/act{act}.png")
        self.update_status(f"Raid Mode: Step 7 - Searching for Act {act}...")
        act_pos = wait_for_image(act_image, timeout=30, confidence=0.65, 
                                 region=self.roblox_region, running_check=lambda: self.running)
        
        if not self._check_running():
            return False
        
        if act_pos:
            self.update_status(f"Raid Mode: ✓ Found Act {act}, clicking...")
            move_to(*act_pos, duration=0.3)
            time.sleep(0.2)
            click(*act_pos)
            time.sleep(0.5)
        else:
            self.update_status(f"Raid Mode: ✗ Could not find Act {act}")
            return False
        
        # Step 8: Click Start button
        self.update_status("Raid Mode: Step 8 - Searching for 'Start' button...")
        start_pos = wait_for_image(get_button_path("buttons/Start.png"), timeout=30, confidence=0.65, 
                                   region=self.roblox_region, running_check=lambda: self.running)
        
        if not self._check_running():
            return False
        
        if start_pos:
            self.update_status("Raid Mode: ✓ Found 'Start' button, clicking...")
            move_to(*start_pos, duration=0.3)
            time.sleep(0.2)
            click(*start_pos)
            time.sleep(0.5)
        else:
            self.update_status("Raid Mode: ✗ Could not find 'Start' button")
            return False
        
        # Step 9: Click other start button
        self.update_status("Raid Mode: Step 9 - Searching for other start button...")
        otherstart_pos = wait_for_image(get_button_path("buttons/otherstart.png"), timeout=30, confidence=0.65, 
                                        region=self.roblox_region, running_check=lambda: self.running)
        
        if not self._check_running():
            return False
        
        if otherstart_pos:
            self.update_status("Raid Mode: ✓ Found other start button, clicking...")
            move_to(*otherstart_pos, duration=0.4)
            time.sleep(0.3)
            click(*otherstart_pos)
            time.sleep(0.5)
        else:
            self.update_status("Raid Mode: ✗ Could not find other start button")
            return False
        
        # Step 10: Wait for game to load and detect Yes button
        if location == "Frozen Gate":
            self.update_status("Raid Mode: Step 10 - Waiting for game to load (detecting 'Yes' button)...")
            yes_pos = wait_for_image(get_button_path("buttons/Yes.png"), timeout=None, confidence=0.65, 
                                     region=self.roblox_region, running_check=lambda: self.running)
            
            if not self._check_running():
                return False
            
            if not yes_pos:
                self.update_status("Raid Mode: ✗ Could not find 'Yes' button")
                return False
            
            self.update_status("Raid Mode: ✓ Found 'Yes' button, starting positioning...")
            
            # Step 11: Zoom out (hold O)
            self.update_status("Raid Mode: Step 11 - Zooming out (holding O)...")
            hold_key_directinput('o', 0.1)
            time.sleep(0.3)
            
            # Step 12: Walk forward for 2 seconds
            self.update_status("Raid Mode: Step 12 - Walking forward (W) for 2 seconds...")
            hold_key_directinput('w', 2.0)
            time.sleep(0.3)
            
            # Step 13: Click Yes button
            self.update_status("Raid Mode: Step 13 - Clicking 'Yes' button...")
            move_to(*yes_pos, duration=0.3)
            time.sleep(0.2)
            click(*yes_pos)
            time.sleep(0.5)
        
        self.update_status("Raid Mode: Navigation complete!")
        return True
    
    def _navigate_siege_mode(self):
        """Navigate Siege mode - Areas -> Siege -> walk forward -> hold D until Blue detected"""
        location = self.config.get("location", "Blue Dungeon")
        act = self.config.get("act", "Act 1").replace(" ", "").replace("Act", "")
        self.update_status(f"Siege Mode: Location = {location}, Act = {act}")
        
        # Step 1: Find and click "siege" button
        self.update_status("Siege Mode: Step 1 - Searching for 'Siege' button...")
        siege_pos = wait_for_image(get_button_path("buttons/siege.png"), timeout=30, confidence=0.65, 
                                   region=self.roblox_region, running_check=lambda: self.running)
        
        if not self._check_running():
            return False
        
        if not siege_pos:
            self.update_status("Siege Mode: ✗ Could not find 'Siege' button")
            return False
        
        self.update_status(f"Siege Mode: ✓ Found 'Siege' at {siege_pos}, clicking...")
        move_to(*siege_pos, duration=0.3)
        time.sleep(0.2)
        click(*siege_pos)
        time.sleep(1.0)
        
        # Step 2: Walk forward with W for 1.5 seconds
        self.update_status("Siege Mode: Step 2 - Walking forward (W) for 1.5 seconds...")
        hold_key_directinput('w', 1.5)
        time.sleep(0.3)
        
        # Step 3: Hold D to walk right until "Create Match" is found
        self.update_status("Siege Mode: Step 3 - Walking right (D) until 'Create Match' appears...")
        
        def check_create_match():
            return find_image_on_screen(get_button_path("buttons/creatematch.png"), confidence=0.65, region=self.roblox_region)
        
        creatematch_pos = hold_key_until_condition('d', check_create_match, timeout=15, running_check=lambda: self.running)
        
        if not self._check_running():
            return False
        
        if not creatematch_pos:
            # Try waiting a bit more if not found
            self.update_status("Siege Mode: Create Match not found while walking, searching...")
            creatematch_pos = wait_for_image(get_button_path("buttons/creatematch.png"), timeout=10, confidence=0.65, 
                                             region=self.roblox_region, running_check=lambda: self.running)
        
        if not creatematch_pos:
            self.update_status("Siege Mode: ✗ Could not find 'Create Match' button")
            return False
        
        self.update_status(f"Siege Mode: ✓ Found 'Create Match' at {creatematch_pos}, clicking...")
        move_to(*creatematch_pos, duration=0.3)
        time.sleep(0.2)
        click(*creatematch_pos)
        time.sleep(1.0)
        
        # Step 4: Find Blue Dungeon button
        self.update_status("Siege Mode: Step 4 - Searching for 'Blue Dungeon'...")
        blue_pos = wait_for_image(get_button_path("buttons/Blue.png"), timeout=30, confidence=0.65, 
                                  region=self.roblox_region, running_check=lambda: self.running)
        
        if not self._check_running():
            return False
        
        if not blue_pos:
            self.update_status("Siege Mode: ✗ Could not find 'Blue Dungeon'")
            return False
        
        # Step 5: Click on Blue Dungeon
        self.update_status(f"Siege Mode: ✓ Found 'Blue Dungeon' at {blue_pos}, clicking...")
        move_to(*blue_pos, duration=0.3)
        time.sleep(0.2)
        click(*blue_pos)
        time.sleep(0.5)
        
        # Step 6: Click on the act
        act_image = get_button_path(f"buttons/Acts/act{act}.png")
        self.update_status(f"Siege Mode: Step 6 - Searching for Act {act}...")
        act_pos = wait_for_image(act_image, timeout=30, confidence=0.65, 
                                 region=self.roblox_region, running_check=lambda: self.running)
        
        if not self._check_running():
            return False
        
        if act_pos:
            self.update_status(f"Siege Mode: ✓ Found Act {act}, clicking...")
            move_to(*act_pos, duration=0.3)
            time.sleep(0.2)
            click(*act_pos)
            time.sleep(0.5)
        else:
            self.update_status(f"Siege Mode: ✗ Could not find Act {act}")
            return False
        
        # Step 7: Click Start button
        self.update_status("Siege Mode: Step 7 - Searching for 'Start' button...")
        start_pos = wait_for_image(get_button_path("buttons/Start.png"), timeout=30, confidence=0.65, 
                                   region=self.roblox_region, running_check=lambda: self.running)
        
        if not self._check_running():
            return False
        
        if start_pos:
            self.update_status("Siege Mode: ✓ Found 'Start' button, clicking...")
            move_to(*start_pos, duration=0.3)
            time.sleep(0.2)
            click(*start_pos)
            time.sleep(0.5)
        else:
            self.update_status("Siege Mode: ✗ Could not find 'Start' button")
            return False
        
        # Step 8: Click other start button
        self.update_status("Siege Mode: Step 8 - Searching for other start button...")
        otherstart_pos = wait_for_image(get_button_path("buttons/otherstart.png"), timeout=30, confidence=0.65, 
                                        region=self.roblox_region, running_check=lambda: self.running)
        
        if not self._check_running():
            return False
        
        if otherstart_pos:
            self.update_status("Siege Mode: ✓ Found other start button, clicking...")
            move_to(*otherstart_pos, duration=0.4)
            time.sleep(0.3)
            click(*otherstart_pos)
            time.sleep(0.5)
        else:
            self.update_status("Siege Mode: ✗ Could not find other start button")
            return False
        
        self.update_status("Siege Mode: Navigation complete!")
        return True

    def _navigate_legend_mode(self):
        """Navigate Legend mode menus - same as Story but clicks Legend.png after Create Match"""
        location = self.config.get("location", "Planet Namek")
        act = self.config.get("act", "Act 1").replace(" ", "").replace("Act", "")
        self.update_status(f"Legend Mode: Location = {location}, Act = {act}")
        
        # Hold A until "Create Match" appears
        self.update_status("Legend Mode: Holding 'A' to find 'Create Match'...")
        
        def check_create_match():
            return find_image_on_screen(get_button_path("buttons/creatematch.png"), confidence=0.65, region=self.roblox_region)
        
        create_match_pos = hold_key_until_condition('a', check_create_match, timeout=30, running_check=lambda: self.running)
        
        if not self._check_running():
            return False
        
        if not create_match_pos:
            self.update_status("Legend Mode: ✗ Could not find 'Create Match'")
            return False
        
        self.update_status("Legend Mode: ✓ Found 'Create Match', hovering and clicking...")
        move_to(*create_match_pos, duration=0.3)
        time.sleep(0.2)
        click(*create_match_pos)
        time.sleep(0.5)
        
        # Click Legend.png button
        self.update_status("Legend Mode: Searching for 'Legend' button...")
        legend_pos = wait_for_image(get_button_path("buttons/Legend.png"), timeout=10, confidence=0.65, region=self.roblox_region, running_check=lambda: self.running)
        
        if not self._check_running():
            return False
        
        if legend_pos:
            self.update_status(f"Legend Mode: ✓ Found 'Legend' at {legend_pos}, clicking...")
            move_to(*legend_pos, duration=0.3)
            time.sleep(0.2)
            click(*legend_pos)
            time.sleep(0.5)
        else:
            self.update_status("Legend Mode: ✗ Could not find 'Legend' button")
            return False
        
        # Find and click the stage/location button
        self.update_status(f"Legend Mode: Step 1 - Searching for stage '{location}'...")
        
        # Map location names to stage image files (same as Story)
        location_lower = location.lower()
        stage_image = None
        act_image = None
        
        if "hollow" in location_lower or "dark" in location_lower:
            stage_image = get_button_path("buttons/hollow.png")
            # Use unified act images named act1..act6.png
            act_image = get_button_path(f"buttons/Acts/act{act}.png")
        elif "namak" in location_lower or "namek" in location_lower or "planet" in location_lower:
            stage_image = get_button_path("buttons/planet.png")
            act_image = get_button_path(f"buttons/Acts/act{act}.png")
        
        if not stage_image:
            self.update_status(f"Legend Mode: ⚠ No image mapping for '{location}', skipping...")
            return False
        
        # Click stage button - use lower confidence for hollow.png
        stage_confidence = 0.50 if "hollow" in stage_image else 0.65
        self.update_status(f"Legend Mode: Looking for stage image: {stage_image}")
        stage_pos = wait_for_image(stage_image, timeout=None, confidence=stage_confidence, region=self.roblox_region, running_check=lambda: self.running)
        
        if not self._check_running():
            return False
        
        if stage_pos:
            self.update_status(f"Legend Mode: ✓ Found stage '{location}', hovering and clicking...")
            move_to(*stage_pos, duration=0.3)
            time.sleep(0.2)
            click(*stage_pos)
            time.sleep(0.5)
        else:
            self.update_status(f"Legend Mode: ✗ Could not find stage '{location}'")
            return False
        
        # Click act button
        self.update_status(f"Legend Mode: Step 2 - Searching for Act {act}...")
        self.update_status(f"Legend Mode: Looking for act image: {act_image}")
        act_pos = wait_for_image(act_image, timeout=None, confidence=0.65, region=self.roblox_region, running_check=lambda: self.running)
        
        if not self._check_running():
            return False
        
        if act_pos:
            self.update_status(f"Legend Mode: ✓ Found Act {act}, hovering and clicking...")
            move_to(*act_pos, duration=0.3)
            time.sleep(0.2)
            click(*act_pos)
            time.sleep(0.5)
        else:
            self.update_status(f"Legend Mode: ✗ Could not find Act {act}")
            return False
        
        # Check if nightmare mode is enabled
        nightmare_enabled = self.config.get("nightmare", False)
        if nightmare_enabled:
            self.update_status("Legend Mode: Step 2.5 - Nightmare mode enabled, searching for Nightmare button...")
            nightmare_pos = wait_for_image(get_button_path("buttons/nightmare.png"), timeout=10, confidence=0.65, region=self.roblox_region, running_check=lambda: self.running)
            
            if not self._check_running():
                return False
            
            if nightmare_pos:
                self.update_status(f"Legend Mode: ✓ Found Nightmare, clicking...")
                move_to(*nightmare_pos, duration=0.3)
                time.sleep(0.2)
                click(*nightmare_pos)
                time.sleep(0.5)
            else:
                self.update_status("Legend Mode: ⚠ Could not find Nightmare button, continuing without...")
        
        # Click Start
        self.update_status("Legend Mode: Step 3 - Searching for 'Start' button...")
        start_pos = wait_for_image(get_button_path("buttons/Start.png"), timeout=None, confidence=0.65, region=self.roblox_region, running_check=lambda: self.running)
        
        if not self._check_running():
            return False
        
        if start_pos:
            self.update_status(f"Legend Mode: ✓ Found 'Start', hovering and clicking...")
            move_to(*start_pos, duration=0.3)
            time.sleep(0.2)
            click(*start_pos)
            time.sleep(0.5)
        else:
            self.update_status("Legend Mode: ✗ Could not find 'Start' button")
            return False
        
        # Click other start button
        self.update_status("Legend Mode: Step 4 - Searching for other start button...")
        otherstart_pos = wait_for_image(get_button_path("buttons/otherstart.png"), timeout=None, confidence=0.65, region=self.roblox_region, running_check=lambda: self.running)
        
        if not self._check_running():
            return False
        
        if otherstart_pos:
            self.update_status("Legend Mode: ✓ Found other start button, hovering and clicking...")
            move_to(*otherstart_pos, duration=0.4)
            time.sleep(0.3)
            click(*otherstart_pos)
            time.sleep(0.5)
        else:
            self.update_status("Legend Mode: ✗ Could not find other start button")
            return False
        
        self.update_status("Legend Mode: Navigation complete!")
        return True
    
    def _navigate_story_mode(self):
        """Navigate Story mode menus"""
        location = self.config.get("location", "Leaf Village")
        act = self.config.get("act", "Act 1").replace(" ", "").replace("Act", "")
        self.update_status(f"Story Mode: Location = {location}, Act = {act}")
        
        # Hold A until "Create Match" appears
        self.update_status("Story Mode: Holding 'A' to find 'Create Match'...")
        
        def check_create_match():
            return find_image_on_screen(get_button_path("buttons/creatematch.png"), confidence=0.65, region=self.roblox_region)
        
        create_match_pos = hold_key_until_condition('a', check_create_match, timeout=30, running_check=lambda: self.running)
        
        if not self._check_running():
            return False
        
        if not create_match_pos:
            self.update_status("Story Mode: ✗ Could not find 'Create Match'")
            return False
        
        self.update_status("Story Mode: ✓ Found 'Create Match', hovering and clicking...")
        move_to(*create_match_pos, duration=0.3)
        time.sleep(0.2)
        click(*create_match_pos)
        time.sleep(0.5)
        
        # Find and click the stage/location button
        self.update_status(f"Story Mode: Step 1 - Searching for stage '{location}'...")
        
        # Map location names to stage image files
        location_lower = location.lower()
        stage_image = None
        act_image = None
        
        if "hollow" in location_lower or "dark" in location_lower:
            stage_image = get_button_path("buttons/hollow.png")
            act_image = get_button_path(f"buttons/Acts/act{act}.png")
        elif "leaf" in location_lower or "village" in location_lower:
            stage_image = get_button_path("buttons/leaf.png")
            act_image = get_button_path(f"buttons/Acts/act{act}.png")
        elif "namak" in location_lower or "namek" in location_lower or "planet" in location_lower:
            stage_image = get_button_path("buttons/planet.png")
            act_image = get_button_path(f"buttons/Acts/act{act}.png")
        
        if not stage_image:
            self.update_status(f"Story Mode: ⚠ No image mapping for '{location}', skipping...")
            return False
        
        # Click stage button - use lower confidence for hollow.png
        stage_confidence = 0.50 if "hollow" in stage_image else 0.65
        self.update_status(f"Story Mode: Looking for stage image: {stage_image}")
        stage_pos = wait_for_image(stage_image, timeout=None, confidence=stage_confidence, region=self.roblox_region, running_check=lambda: self.running)
        
        if not self._check_running():
            return False
        
        if stage_pos:
            self.update_status(f"Story Mode: ✓ Found stage '{location}', hovering and clicking...")
            move_to(*stage_pos, duration=0.3)
            time.sleep(0.2)
            click(*stage_pos)
            time.sleep(0.5)
        else:
            self.update_status(f"Story Mode: ✗ Could not find stage '{location}'")
            return False
        
        # Click act button
        self.update_status(f"Story Mode: Step 2 - Searching for Act {act}...")
        self.update_status(f"Story Mode: Looking for act image: {act_image}")
        act_pos = wait_for_image(act_image, timeout=None, confidence=0.65, region=self.roblox_region, running_check=lambda: self.running)
        
        if not self._check_running():
            return False
        
        if act_pos:
            self.update_status(f"Story Mode: ✓ Found Act {act}, hovering and clicking...")
            move_to(*act_pos, duration=0.3)
            time.sleep(0.2)
            click(*act_pos)
            time.sleep(0.5)
        else:
            self.update_status(f"Story Mode: ✗ Could not find Act {act}")
            return False
        
        # Check if nightmare mode is enabled
        nightmare_enabled = self.config.get("nightmare", False)
        if nightmare_enabled:
            self.update_status("Story Mode: Step 2.5 - Nightmare mode enabled, searching for Nightmare button...")
            nightmare_pos = wait_for_image(get_button_path("buttons/nightmare.png"), timeout=10, confidence=0.65, region=self.roblox_region, running_check=lambda: self.running)
            
            if not self._check_running():
                return False
            
            if nightmare_pos:
                self.update_status("Story Mode: ✓ Found Nightmare button, hovering and clicking...")
                move_to(*nightmare_pos, duration=0.3)
                time.sleep(0.2)
                click(*nightmare_pos)
                time.sleep(0.5)
            else:
                self.update_status("Story Mode: ✗ Could not find Nightmare button, continuing without it...")
        
        # Click Start button
        self.update_status("Story Mode: Step 3 - Searching for Start button...")
        self.update_status("Story Mode: Looking for start image: buttons/Start.png")
        start_pos = wait_for_image(get_button_path("buttons/Start.png"), timeout=None, confidence=0.65, region=self.roblox_region, running_check=lambda: self.running)
        
        if not self._check_running():
            return False
        
        if start_pos:
            self.update_status("Story Mode: ✓ Found Start button, hovering and clicking...")
            move_to(*start_pos, duration=0.3)
            time.sleep(0.2)
            click(*start_pos)
            time.sleep(0.5)
        else:
            self.update_status("Story Mode: ✗ Could not find Start button")
            return False
        
        # Click other start button
        self.update_status("Story Mode: Step 4 - Searching for other start button...")
        self.update_status("Story Mode: Looking for other start image: buttons/otherstart.png")
        otherstart_pos = wait_for_image(get_button_path("buttons/otherstart.png"), timeout=None, confidence=0.65, region=self.roblox_region, running_check=lambda: self.running)
        
        if not self._check_running():
            return False
        
        if otherstart_pos:
            self.update_status("Story Mode: ✓ Found other start button, hovering and clicking...")
            move_to(*otherstart_pos, duration=0.4)
            time.sleep(0.3)
            click(*otherstart_pos)
            time.sleep(0.5)
        else:
            self.update_status("Story Mode: ✗ Could not find other start button")
            return False
        
        return True

