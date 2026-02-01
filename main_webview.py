"""
Roblox Macro with OCR - Main Application (PyWebview Version)
A macro for automating gameplay in Roblox games with OCR-based detection.
"""
import webview
import keyboard
import threading
import queue
import os
import base64
import ctypes
import time
import sys
from ctypes import wintypes
from config import load_config, save_config
from macro_engine import MacroEngine
from version import VERSION
from updater import check_update, perform_update

# Windows API for window management
user32 = ctypes.windll.user32
EnumWindows = user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
GetWindowText = user32.GetWindowTextW
GetWindowTextLength = user32.GetWindowTextLengthW
SetParent = user32.SetParent
SetWindowPos = user32.SetWindowPos
GetWindowRect = user32.GetWindowRect
ShowWindow = user32.ShowWindow
IsWindow = user32.IsWindow

SWP_SHOWWINDOW = 0x0040
SW_SHOW = 5

class MacroAPI:
    def __init__(self):
        self.config = load_config()
        self.engine = None
        self._status_queue = queue.Queue()
        self._hotkeys_registered = False
        self._capturing_key = False
        self._captured_key = None
        self._roblox_hwnd = None
        self._original_parent = None
        self._window = None
        self._overlay_window = None
        
    def capture_keybind(self, key_type):
        """Capture a keybind from user input"""
        self._capturing_key = True
        self._captured_key = None
        
        def on_key(event):
            if self._capturing_key:
                self._captured_key = event.name
                self._capturing_key = False
                keyboard.unhook_all()
                return False
        
        keyboard.on_press(on_key)
        
        # Wait for key capture (with timeout)
        import time
        timeout = 10
        start = time.time()
        while self._capturing_key and time.time() - start < timeout:
            time.sleep(0.1)
        
        keyboard.unhook_all()
        return self._captured_key if self._captured_key else ('F1' if key_type == 'start' else 'F3')
    
    def apply_keybinds(self, start_key, stop_key):
        """Apply the keybinds"""
        if self._hotkeys_registered:
            keyboard.unhook_all_hotkeys()
            self._hotkeys_registered = False
        
        try:
            # Ensure keys are lowercase
            start_key = start_key.lower()
            stop_key = stop_key.lower()
            
            # Register hotkeys in a separate thread to avoid blocking
            def register_keys():
                try:
                    keyboard.add_hotkey(start_key, self._start_macro_callback, suppress=False)
                    keyboard.add_hotkey(stop_key, self._stop_macro_callback, suppress=False)
                    keyboard.add_hotkey('f4', self._take_screenshot_callback, suppress=False)
                    self._hotkeys_registered = True
                    print(f"Hotkeys registered: Start={start_key}, Stop={stop_key}, Screenshot=F4")
                except Exception as e:
                    print(f"Error in register_keys thread: {e}")
            
            # Run registration in thread
            threading.Thread(target=register_keys, daemon=True).start()
            time.sleep(0.5)  # Give time for registration
            
            self.config["start_keybind"] = start_key
            self.config["stop_keybind"] = stop_key
            save_config(self.config)
            return True
        except Exception as e:
            print(f"Error registering hotkeys: {e}")
            return False
    
    def _get_image_folder_path(self):
        """Get the image folder path based on current mode and location"""
        # Reload config to get latest values
        self.config = load_config()
        
        base_folder = os.path.join(os.path.dirname(__file__), "starting image")
        mode = self.config.get("mode", "Story")
        location = self.config.get("location", "Leaf Village")
        
        print(f"DEBUG: mode={mode}, location={location}")
        
        # Build path based on mode and location
        # Legend mode uses the same images as Story mode
        if mode == "Story" or mode == "Legend":
            folder_name = self._get_location_key(location)
            print(f"DEBUG: folder_name={folder_name}")
            image_folder = os.path.join(base_folder, "Story", folder_name)
        else:
            # For other modes, use base folder
            image_folder = base_folder
        
        # Create folder if it doesn't exist
        os.makedirs(image_folder, exist_ok=True)
        print(f"DEBUG: image_folder={image_folder}")
        return image_folder
    
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
    

    
    def _take_screenshot_callback(self):
        """Callback for F4 screenshot hotkey"""
        print("F4 screenshot hotkey pressed!")
        try:
            # Try to get Roblox region from attached window first, then from engine
            region = None
            
            # Check if Roblox is attached/embedded
            if self._roblox_hwnd and IsWindow(self._roblox_hwnd):
                rect = wintypes.RECT()
                GetWindowRect(self._roblox_hwnd, ctypes.byref(rect))
                region = (rect.left, rect.top, rect.right, rect.bottom)
                print(f"Using attached Roblox window region: {region}")
            # Fall back to engine detection
            elif self.engine and self.engine.roblox_region:
                region = self.engine.roblox_region
                print(f"Using engine Roblox region: {region}")
            
            if not region:
                msg = "Screenshot failed: No Roblox window detected. Please attach Roblox first."
                print(msg)
                self._status_callback(msg)
                return
            
            # Take screenshot of Roblox window
            import mss
            from PIL import Image
            import io
            
            with mss.mss() as sct:
                monitor = {
                    "left": region[0],
                    "top": region[1],
                    "width": region[2] - region[0],
                    "height": region[3] - region[1]
                }
                screenshot = sct.grab(monitor)
                img = Image.frombytes('RGB', (screenshot.width, screenshot.height), screenshot.rgb)
                
                # Get the correct folder path
                image_folder = self._get_image_folder_path()
                
                # Delete existing images in the folder
                for filename in os.listdir(image_folder):
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                        os.remove(os.path.join(image_folder, filename))
                
                # Save new screenshot
                image_path = os.path.join(image_folder, "screenshot.png")
                img.save(image_path)
                
                mode = self.config.get("mode", "Story")
                location = self.config.get("location", "Leaf Village")
                self._status_callback(f"Screenshot saved to {image_folder} for {mode} - {location}")
                print(f"Screenshot saved: {image_path}")
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            self._status_callback(f"Screenshot error: {str(e)}")
    
    def update_tolerance(self, tolerance):
        """Update OCR tolerance setting"""
        self.config["ocr_tolerance"] = tolerance
        save_config(self.config)
        print(f"OCR tolerance updated to: {tolerance}")
        return True

    def update_t_press_delay(self, delay):
        """Update delay between repeated T presses (from UI)"""
        try:
            val = float(delay)
        except Exception:
            print(f"Invalid t_press_delay value: {delay}")
            return False
        self.config["t_press_delay"] = val
        save_config(self.config)
        print(f"T-press delay updated to: {val}")
        return True
    
    def _start_macro_callback(self):
        """Callback for start hotkey"""
        print("Start hotkey pressed!")
        if not self.engine or not self.engine.running:
            self._status_callback("Macro started via hotkey!")
            self._start_macro_internal()
        else:
            self._status_callback("Macro already running")
            print("Macro already running")
    
    def _stop_macro_callback(self):
        """Callback for stop hotkey"""
        print("Stop hotkey pressed!")
        if self.engine and self.engine.running:
            self.engine.stop()
            self._status_callback("Macro stopped via hotkey")
        else:
            self._status_callback("Macro not running")
            print("Macro not running")
    

    

    

    
    def attach_roblox(self):
        """Find and attach Roblox window"""
        def find_roblox_window():
            result = []
            
            def enum_callback(hwnd, lParam):
                length = GetWindowTextLength(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    GetWindowText(hwnd, buff, length + 1)
                    title = buff.value
                    if 'roblox' in title.lower():
                        result.append(hwnd)
                return True
            
            EnumWindows(EnumWindowsProc(enum_callback), 0)
            return result[0] if result else None
        
        hwnd = find_roblox_window()
        if not hwnd:
            return {"success": False, "message": "Roblox window not found. Make sure Roblox is running!"}
        
        # Get the pywebview window handle
        try:
            import time
            time.sleep(0.1)  # Give window time to render
            
            # Find our webview window
            webview_hwnd = None
            def find_webview():
                result = []
                def enum_cb(h, lp):
                    length = GetWindowTextLength(h)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        GetWindowText(h, buff, length + 1)
                        if 'Anime Paradox Macro' in buff.value:
                            result.append(h)
                    return True
                EnumWindows(EnumWindowsProc(enum_cb), 0)
                return result[0] if result else None
            
            webview_hwnd = find_webview()
            if not webview_hwnd:
                return {"success": False, "message": "Could not find app window handle"}
            
            # Compute container offsets dynamically from ui.html to stay in sync with CSS
            ui_path = os.path.join(os.path.dirname(__file__), 'ui.html')
            main_panel_width = 550
            body_padding = 15
            gap = 15
            border_adj = 5
            try:
                if os.path.exists(ui_path):
                    with open(ui_path, 'r', encoding='utf-8') as fh:
                        content = fh.read()
                    import re
                    m = re.search(r"\.main-panel\s*\{[^}]*width:\s*(\d+)px", content)
                    if m:
                        main_panel_width = int(m.group(1))
            except Exception:
                pass

            settings_width = main_panel_width + body_padding + gap + border_adj
            fixed_game_width = 960  # Fixed width for Roblox window (16:10 aspect)
            fixed_game_height = 600  # Fixed height for Roblox window
            header_height = 60  # Header for game container

            # Try to account for DPI scaling of the webview window so child positioning matches CSS pixels
            try:
                # Get DPI for webview window if available (Windows 10+)
                GetDpiForWindow = user32.GetDpiForWindow
                dpi = GetDpiForWindow(webview_hwnd)
            except Exception:
                try:
                    # Fallback: use desktop DPI
                    hdc = user32.GetDC(0)
                    gdi32 = ctypes.windll.gdi32
                    LOGPIXELSX = 88
                    dpi = gdi32.GetDeviceCaps(hdc, LOGPIXELSX)
                    user32.ReleaseDC(0, hdc)
                except Exception:
                    dpi = 96

            scale = float(dpi) / 96.0 if dpi else 1.0
            # Scale CSS pixel measurements to device pixels for positioning only
            scaled_settings_width = int(settings_width * scale)
            scaled_header_height = int(header_height * scale)

            # Keep the actual Roblox game window at the original resolution so templates match
            unscaled_game_width = fixed_game_width
            unscaled_game_height = fixed_game_height

            total_width = scaled_settings_width + unscaled_game_width + 30  # Extra padding
            total_height = max(750, unscaled_game_height + scaled_header_height + 50)
            
            # Resize main window first
            if self._window:
                self._window.resize(total_width, total_height)
                time.sleep(0.3)  # Let window resize
            
            # Store original parent
            GetParent = user32.GetParent
            self._original_parent = GetParent(hwnd)
            
            # Remove Roblox window border/titlebar to make it fit exactly
            GWL_STYLE = -16
            WS_POPUP = 0x80000000
            WS_VISIBLE = 0x10000000
            WS_CLIPSIBLINGS = 0x04000000
            WS_CLIPCHILDREN = 0x02000000
            
            # Get current style and modify it
            GetWindowLong = user32.GetWindowLongW
            SetWindowLong = user32.SetWindowLongW
            original_style = GetWindowLong(hwnd, GWL_STYLE)
            
            # Set borderless style for exact fit
            new_style = WS_POPUP | WS_VISIBLE | WS_CLIPSIBLINGS | WS_CLIPCHILDREN
            SetWindowLong(hwnd, GWL_STYLE, new_style)
            
            # Set Roblox as child of our window
            SetParent(hwnd, webview_hwnd)

            # Position and FORCE RESIZE Roblox window to fit exactly in the container
            SWP_NOZORDER = 0x0004
            SWP_NOACTIVATE = 0x0010
            SWP_FRAMECHANGED = 0x0020  # Apply style changes
            # If the webview client area has an offset or DPI scaling, place the Roblox window
            # at the scaled settings offset but keep its size unscaled so templates remain valid.
            SetWindowPos(hwnd, 0, scaled_settings_width, scaled_header_height, unscaled_game_width, unscaled_game_height, 
                        SWP_NOZORDER | SWP_NOACTIVATE | SWP_SHOWWINDOW | SWP_FRAMECHANGED)
            ShowWindow(hwnd, SW_SHOW)
            
            self._roblox_hwnd = hwnd
            self._original_style = original_style  # Store for restoration
            # Update engine with exact Roblox region so image detection uses correct coords
            try:
                # After positioning, read back the actual window rect and update engine region
                rect = wintypes.RECT()
                GetWindowRect(hwnd, ctypes.byref(rect))
                region = (rect.left, rect.top, rect.right, rect.bottom)
                print(f"DEBUG: Attached Roblox region set to: {region}")
                if self.engine:
                    self.engine.roblox_region = region
            except Exception as e:
                print(f"DEBUG: Could not set engine.roblox_region: {e}")
            return {"success": True, "message": "Roblox window attached!"}
            
        except Exception as e:
            return {"success": False, "message": f"Error embedding window: {str(e)}"}
    
    def detach_roblox(self):
        """Detach Roblox window"""
        if self._roblox_hwnd and IsWindow(self._roblox_hwnd):
            try:
                # Restore original parent
                if self._original_parent:
                    SetParent(self._roblox_hwnd, self._original_parent)
                else:
                    # Set to desktop if no original parent
                    SetParent(self._roblox_hwnd, 0)
                
                # Reset window position
                SWP_NOMOVE = 0x0002
                SWP_NOSIZE = 0x0001
                SWP_NOZORDER = 0x0004
                SWP_SHOWWINDOW = 0x0040
                SWP_FRAMECHANGED = 0x0020
                
                # Restore original window style if we saved it
                if hasattr(self, '_original_style') and self._original_style:
                    GWL_STYLE = -16
                    SetWindowLong = user32.SetWindowLongW
                    SetWindowLong(self._roblox_hwnd, GWL_STYLE, self._original_style)
                
                SetWindowPos(self._roblox_hwnd, 0, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_SHOWWINDOW | SWP_FRAMECHANGED)
                
            except Exception as e:
                pass
        
        self._roblox_hwnd = None
        self._original_parent = None
        self._original_style = None
        return {"success": True}
    
    def start_macro(self, config_update):
        """Start the macro with updated configuration"""
        # Reload config from file first
        self.config = load_config()
        
        # Update config with new values
        self.config["mode"] = config_update.get("mode", "Story")
        self.config["location"] = config_update.get("location", "Leaf Village")
        self.config["act"] = config_update.get("act", "Act 1")
        save_config(self.config)
        
        # Start macro
        self._start_macro_internal()
        return {"success": True}
    
    def _start_macro_internal(self):
        """Internal method to start macro"""
        if self.engine and self.engine.running:
            return

        self.engine = MacroEngine(self.config, self._status_callback)
        # If we have an attached Roblox window, set engine.roblox_region before starting
        try:
            if self._roblox_hwnd and IsWindow(self._roblox_hwnd):
                rect = wintypes.RECT()
                GetWindowRect(self._roblox_hwnd, ctypes.byref(rect))
                region = (rect.left, rect.top, rect.right, rect.bottom)
                print(f"DEBUG: Setting engine.roblox_region from attached hwnd: {region}")
                self.engine.roblox_region = region
        except Exception as e:
            print(f"DEBUG: Could not set engine.roblox_region before start: {e}")

        self.engine.start()
    
    def stop_macro(self):
        """Stop the macro"""
        if self.engine:
            self.engine.stop()
    
    def _status_callback(self, message):
        """Callback for status updates from macro engine"""
        self._status_queue.put(message)
    
    def get_status_updates(self):
        """Get pending status updates"""
        updates = []
        while not self._status_queue.empty():
            try:
                updates.append(self._status_queue.get_nowait())
            except queue.Empty:
                break
        return updates
    

    

    
    def get_config(self):
        """Get full config for UI"""
        return self.config
    
    def update_story_config(self, mode, location, act, nightmare=False):
        """Update story mode configuration"""
        self.config["mode"] = mode
        self.config["location"] = location
        self.config["act"] = act
        self.config["nightmare"] = nightmare
        save_config(self.config)
        print(f"Config updated: mode={mode}, location={location}, act={act}, nightmare={nightmare}")
        return True
    
    def get_unit_config_template(self):
        """Get blank unit config template"""
        return {
            "Units": [
                {
                    "Index": i,
                    "Enabled": False,
                    "PlaceBeforeYes": False,
                    "AutoUpgrade": False,
                    "Slot": "1",
                    "X": "",
                    "Y": "",
                    "Upgrade": "0",
                    "Note": f"Unit {i}"
                }
                for i in range(1, 16)  # 15 unit slots
            ]
        }
    
    def get_unit_config_path(self, location, act):
        """Get the path for unit config based on location and act"""
        settings_folder = os.path.join(os.path.dirname(__file__), "Settings", "Story", location)
        os.makedirs(settings_folder, exist_ok=True)
        return os.path.join(settings_folder, f"{act}.json")
    
    def load_unit_config(self, location, act):
        """Load unit configuration for a location and act"""
        import json
        config_path = self.get_unit_config_path(location, act)
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return self.get_unit_config_template()
        else:
            # Create blank config
            template = self.get_unit_config_template()
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=4)
            return template
    
    def save_unit_config(self, location, act, config_data):
        """Save unit configuration"""
        import json
        config_path = self.get_unit_config_path(location, act)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)
        
        print(f"Unit config saved to: {config_path}")
        return True
    
    def get_map_preview_path(self, location, act):
        """Get the map preview image as base64 data URL"""
        import base64
        
        # Check Settings folder first (where coordinate picker saves screenshots)
        settings_folder = os.path.join(os.path.dirname(__file__), "Settings", "Story", location)
        
        if os.path.exists(settings_folder):
            for filename in os.listdir(settings_folder):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    image_path = os.path.join(settings_folder, filename)
                    try:
                        with open(image_path, 'rb') as f:
                            img_data = base64.b64encode(f.read()).decode('utf-8')
                        ext = filename.lower().split('.')[-1]
                        mime = 'image/jpeg' if ext in ['jpg', 'jpeg'] else 'image/png'
                        return {"success": True, "path": f"data:{mime};base64,{img_data}"}
                    except Exception as e:
                        print(f"Error reading image: {e}")
        
        # Fallback to starting image folder
        folder_name = self._get_location_key(location)
        image_folder = os.path.join(os.path.dirname(__file__), "starting image", "Story", folder_name)
        
        if os.path.exists(image_folder):
            for filename in os.listdir(image_folder):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    image_path = os.path.join(image_folder, filename)
                    try:
                        with open(image_path, 'rb') as f:
                            img_data = base64.b64encode(f.read()).decode('utf-8')
                        ext = filename.lower().split('.')[-1]
                        mime = 'image/jpeg' if ext in ['jpg', 'jpeg'] else 'image/png'
                        return {"success": True, "path": f"data:{mime};base64,{img_data}"}
                    except Exception as e:
                        print(f"Error reading image: {e}")
        
        return {"success": False, "path": None}
    
    def get_roblox_window_info(self):
        """Get the current Roblox window position and size"""
        if self._roblox_hwnd and IsWindow(self._roblox_hwnd):
            rect = wintypes.RECT()
            GetWindowRect(self._roblox_hwnd, ctypes.byref(rect))
            return {
                "x": rect.left,
                "y": rect.top,
                "width": rect.right - rect.left,
                "height": rect.bottom - rect.top
            }
        return {"x": 0, "y": 0, "width": 960, "height": 600}
    
    def open_coordinate_picker(self, location, act, unit_index):
        """Open coordinate picker for a specific unit"""
        import subprocess
        import sys
        import json
        
        # Get image folder for the location
        image_folder = self._get_image_folder_path()
        image_path = None
        
        if os.path.exists(image_folder):
            for filename in os.listdir(image_folder):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    image_path = os.path.join(image_folder, filename)
                    break
        
        if not image_path:
            return {"success": False, "message": "No screenshot found. Take a screenshot first (F4)."}
        
        # Load existing unit coordinates to display in picker
        location_key = self._get_location_key(location)
        config_path = os.path.join(os.path.dirname(__file__), "Settings", "Story", location_key, f"{act}.json")
        other_units = []
        
        print(f"DEBUG: Looking for unit config at: {config_path}")
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                for unit in config.get("Units", []):
                    # Show all units that have coordinates set (not just enabled ones)
                    if unit.get("X") and unit.get("Y"):
                        try:
                            other_units.append({
                                "index": unit["Index"],
                                "x": int(unit["X"]),
                                "y": int(unit["Y"]),
                                "note": unit.get("Note", f"Unit {unit['Index']}")
                            })
                        except (ValueError, KeyError):
                            pass
                print(f"DEBUG: Found {len(other_units)} units with coordinates")
            except Exception as e:
                print(f"Error loading unit config: {e}")
        else:
            print(f"DEBUG: Config file does not exist: {config_path}")
        
        # Launch coordinate picker
        script_path = os.path.join(os.path.dirname(__file__), "coordinate_picker.py")
        
        # Get the actual position of the Roblox window on screen
        if self._roblox_hwnd and IsWindow(self._roblox_hwnd):
            rect = wintypes.RECT()
            GetWindowRect(self._roblox_hwnd, ctypes.byref(rect))
            roblox_x = rect.left
            roblox_y = rect.top
            roblox_width = rect.right - rect.left
            roblox_height = rect.bottom - rect.top
        else:
            # Fallback to default embedded position - compute offsets from ui.html
            ui_path = os.path.join(os.path.dirname(__file__), 'ui.html')
            main_panel_width = 550
            body_padding = 15
            gap = 15
            border_adj = 5
            try:
                if os.path.exists(ui_path):
                    with open(ui_path, 'r', encoding='utf-8') as fh:
                        content = fh.read()
                    import re
                    m = re.search(r"\.main-panel\s*\{[^}]*width:\s*(\d+)px", content)
                    if m:
                        main_panel_width = int(m.group(1))
            except Exception:
                pass

            settings_width = main_panel_width + body_padding + gap + border_adj
            roblox_x = settings_width
            roblox_y = 60
            roblox_width = 960
            roblox_height = 600
        
        try:
            # Pass other units as JSON argument
            other_units_json = json.dumps(other_units)
            
            # Run coordinate picker and wait for result (synchronously)
            result = subprocess.run(
                [sys.executable, script_path, image_path, location, act, str(unit_index),
                 str(roblox_x), str(roblox_y), str(roblox_width), str(roblox_height), other_units_json],
                cwd=os.path.dirname(__file__),
                capture_output=True,
                text=True,
                timeout=120
            )
            
            # Parse coordinates from output
            for line in result.stdout.split('\n'):
                line = line.strip()
                if ',' in line and not line.startswith('✓'):
                    try:
                        x, y = line.split(',')
                        x = int(x.strip())
                        y = int(y.strip())
                        print(f"Coordinates selected: ({x}, {y})")
                        return {"success": True, "x": x, "y": y}
                    except:
                        continue
            
            return {"success": False, "message": "No coordinates selected"}
            
        except subprocess.TimeoutExpired:
            return {"success": False, "message": "Coordinate picker timed out"}
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}
    
    def get_version(self):
        """Get the current application version"""
        return {"version": VERSION}
    
    def check_for_updates(self):
        """Check for available updates"""
        return check_update()
    
    def install_update(self, download_url):
        """Download and install an update"""
        def status_callback(message):
            # Queue status updates for UI
            self._status_queue.put(message)
        
        result = perform_update(download_url, status_callback)
        return result
    
    def restart_application(self):
        """Restart the application after update"""
        try:
            if getattr(sys, 'frozen', False):
                # Running as exe
                os.execv(sys.executable, [sys.executable])
            else:
                # Running as script
                os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            return {"success": False, "message": str(e)}


def main():
    api = MacroAPI()
    
    # Load HTML content
    html_path = os.path.join(os.path.dirname(__file__), 'ui.html')
    
    # Register hotkeys before window creation
    def setup_hotkeys():
        start_key = api.config.get("start_keybind", "f1")
        stop_key = api.config.get("stop_keybind", "f3")
        api.apply_keybinds(start_key, stop_key)
    
    # Create single window with transparent background
    window = webview.create_window(
        'Anime Paradox Macro',
        html_path,
        js_api=api,
        width=1100,
        height=850,
        resizable=False,
        transparent=False,
        frameless=False
    )
    
    api._window = window
    
    # Start webview
    webview.start(setup_hotkeys, debug=False)
    
    # Cleanup on exit
    if api._hotkeys_registered:
        keyboard.unhook_all_hotkeys()
    if api.engine and api.engine.running:
        api.engine.stop()


if __name__ == "__main__":
    main()
