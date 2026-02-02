# Anime Paradox Macro

A powerful Roblox automation tool for Anime Paradox with advanced features including OCR-based detection, unit placement, Discord notifications, auto-reconnect, and challenge automation.

## ✨ Features

### 🎮 Game Modes
- **Story Mode**: Full navigation through Areas → Create Match → Location → Act → Start
- **Raid Mode**: Optimized positioning for Frozen Gate (Acts 1-3)
- **Siege Mode**: Blue Dungeon automation with forward positioning
- **Auto-Challenges Mode**: Automated challenge rotation with 30-minute farming cycles

### 🤖 Automation
- **Smart Navigation**: Automatically navigates through all game menus
- **Unit Placement**: Configurable 30-unit system with spiral placement pattern
- **Auto-Upgrade**: Priority-based upgrade system during gameplay
- **Auto-Replay**: Detects Victory/Defeat and automatically replays
- **Map-Specific Positioning**: Automatic character positioning for each location

### 📊 Discord Integration
- **Victory/Defeat Notifications**: Real-time game results sent to Discord
- **Screenshot Capture**: Automatically captures and sends victory screen
- **Statistics Tracking**: Wins, losses, and win rate tracking
- **Stage Timing**: Reports completion time for each stage
- **Test Webhook**: Verify webhook configuration before use

### 🔄 Auto-Reconnect System
- **Disconnect Detection**: Monitors for disconnect.png during gameplay
- **Automatic Reconnection**: Opens private server link and resumes macro
- **Configurable Server Link**: Set your private server URL in settings
- **Seamless Recovery**: Continues macro after successful reconnection

### 🏆 Auto-Challenges System
- **Challenge Rotation**: Automatically runs challenges every 30 minutes
- **Dynamic Config Loading**: Uses correct unit config based on detected map
- **Challenge Detection**: Identifies Leaf Village, Planet Namek, or Dark Hollow challenges
- **Farming Cycles**: Runs selected stage between challenges for optimal efficiency
- **Map-Specific Positioning**: Auto-adjusts positioning based on challenge map

### ⚙️ Configuration
- **30 Unit Slots**: Full control over unit placement and upgrades
- **Placement Before Yes**: Option to place units before starting wave
- **Custom Coordinates**: Set exact X/Y coordinates for each unit
- **Upgrade Control**: Configure upgrade level for each unit (0-4)
- **Per-Location Configs**: Different unit setups for Story/Raid/Siege/Challenges
- **Customizable Hotkeys**: F1 to start, F3 to stop (fully customizable)

### 🖥️ User Interface
- **Modern Dark Theme**: Sleek purple/blue gradient design
- **Tab Navigation**: Organized interface with Stage, Units, Settings, Update tabs
- **Real-Time Status**: Live updates on macro progress and actions
- **Stats Display**: View wins, losses, and win rate in real-time
- **Auto-Update System**: Built-in updater checks for new versions

## 📦 Installation

### Prerequisites

1. **Python 3.8+** - Download from [python.org](https://www.python.org/downloads/)
   - Not required for standalone .exe version

### Quick Start (Standalone)

1. Download `AnimeParadoxMacro_Release.zip` from releases
2. Extract to a folder
3. Run `AnimeParadoxMacro.exe`
4. Configure your settings and start automating!

### Development Setup

1. Clone this repository
   ```bash
   git clone https://github.com/yourusername/anime-paradox-macro.git
   cd anime-paradox-macro
   ```

2. Create virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   python main_webview.py
   ```

## 🚀 Usage

### Initial Setup

1. **Launch the Application**
   - Run `AnimeParadoxMacro.exe` or `python main_webview.py`

2. **Configure Your Stage** (Stage Tab)
   - Select Mode: Story, Raid, Siege, or Auto-Challenges
   - Choose Location and Act
   - For Auto-Challenges: Enable toggle and select challenge location

3. **Configure Units** (Units Tab)
   - Enable units you want to place (checkboxes)
   - Set unit slot numbers (1-6)
   - Configure X/Y coordinates for each unit
   - Set upgrade levels (0-4)
   - Option to place before Yes button
   - Click Save to store configuration

4. **Configure Settings** (Settings Tab)
   - Set custom keybinds (default F1 start, F3 stop)
   - Add Discord webhook URL for notifications
   - Add private server link for auto-reconnect

### Discord Webhook Setup

1. Create a Discord webhook:
   - Go to Discord Server Settings → Integrations → Webhooks
   - Click "New Webhook"
   - Copy the webhook URL

2. In the macro:
   - Go to Settings tab
   - Paste webhook URL in the field
   - Click "Save Webhook"
   - Click "Test Webhook" to verify it works

3. Features:
   - Receives victory/defeat notifications with screenshots
   - Shows stage completion time
   - Displays win/loss/win rate stats
   - Reset stats button available in Settings

### Auto-Reconnect Setup

1. Get your private server link from Roblox
2. Go to Settings → Auto-Reconnect
3. Paste the link and click "Save Private Server"
4. Add `disconnect.png` to the `buttons` folder:
   - Take a screenshot when disconnect screen appears
   - Crop to show disconnect button/text
   - Save as `disconnect.png` in `buttons` folder

### Auto-Challenges Setup

1. **Prepare Challenge Configs**:
   - Configure units for each challenge map:
     - `Settings/Challenges/Leaf Village/Act 1.json`
     - `Settings/Challenges/Planet Namek/Act 1.json`
     - `Settings/Challenges/Dark Hollow/Act 1.json`

2. **Add Challenge Detection Images** to `buttons/challengeacts/`:
   - `leaf.png` - Screenshot of Leaf Village challenge map
   - `planet.png` - Screenshot of Planet Namek challenge map
   - `dark.png` - Screenshot of Dark Hollow challenge map

3. **Add Challenge Button Images** to `buttons/`:
   - `challenges.png` - The Challenges button in Areas menu
   - `regular.png` - The Regular difficulty button
   - `trait.png` - The trait selection button
   - `return.png` - The Return button after victory/defeat

4. **Configure in UI**:
   - Stage Tab: Select "Auto-Challenges" mode
   - Choose a stage for farming (Story/Raid/Siege)
   - Enable "Auto-Challenges" toggle
   - Select challenge location preference

5. **How It Works**:
   - Runs a challenge immediately
   - Farms selected stage for 30 minutes
   - Returns to challenge after 30 minutes
   - Repeats cycle automatically
   - Uses map-specific configs based on detected challenge

### Running the Macro

1. **Start Roblox** and join Anime Paradox
2. **Start the Macro** (Press F1 or click Start button)
3. **Monitor Progress** in the status panel
4. **Stop if Needed** (Press F3 or click Stop button)

The macro will:
- Navigate through menus automatically
- Position character based on location
- Place and upgrade units
- Detect victory/defeat
- Send Discord notifications
- Auto-reconnect if disconnected
- Run challenge cycles (if Auto-Challenges enabled)

## 🔧 How It Works

### Navigation Flow

**Story/Raid/Siege Mode:**
1. Finds "Areas" button → Clicks
2. Holds movement key until mode button appears
3. Finds Location button → Clicks
4. Finds Act button (scrolls if needed) → Clicks
5. Finds "Start" button → Clicks
6. Waits for "Yes" button
7. Performs map-specific positioning
8. Clicks "Yes" to start wave
9. Begins unit placement

**Auto-Challenges Mode:**
1. Finds "Areas" button → Clicks
2. Finds "Challenges" button → Clicks
3. Walks forward to navigation
4. Clicks "Regular" difficulty
5. Hovers over trait → Offsets X+200 → Clicks
6. Clicks "Start"
7. Detects challenge map (leaf/planet/dark)
8. Uses appropriate config and positioning
9. After victory: Returns to lobby
10. Runs selected stage for 30 minutes
11. Repeats challenge cycle

### Placement System

1. **Early Placement** (Before Yes):
   - Places units marked with "PlaceBeforeYes"
   - Uses configured X/Y coordinates
   - Verifies placement success

2. **Main Placement** (After Yes):
   - Places remaining enabled units
   - Presses slot number key (1-6)
   - Clicks at configured coordinates
   - Checks for placement confirmation
   - Tracks placement count per unit

3. **Upgrade System**:
   - Clicks on placed units
   - Checks for "Upgrade" button
   - Clicks to upgrade
   - Repeats until target level reached
   - Continues until all units upgraded

### Position Detection

**Map-Specific Positioning:**
- **Leaf Village**: Right (A key 2s) → Forward (W key 1.8s)
- **Planet Namek**: Back (S key 1.1s) → Left (A key 0.2s)
- **Dark Hollow**: Left (A key 1.2s)
- **Blue Dungeon (Siege)**: Forward (W key 5s)
- **Frozen Gate (Raid)**: Zoom → Position → Click Yes

### Game End Detection

1. Continuously scans for victory.png or defeat.png
2. Calculates stage completion time
3. Sends Discord webhook notification with:
   - Victory/Defeat status
   - Screenshot of results
   - Stage completion time
   - Updated win/loss statistics
4. Finds and clicks "Replay" or "Return" button
5. Continues to next game

### Disconnect Handling

1. Continuously monitors for disconnect.png
2. When detected:
   - Opens configured private server link in browser
   - Waits 15 seconds for game to load
   - Refocuses Roblox window
   - Re-navigates to stage
   - Continues macro execution

## ⚠️ Troubleshooting

### Macro Not Starting

- Check that Roblox window is visible and in focus
- Verify keybinds are set correctly (F1 start, F3 stop)
- Run application as Administrator if needed
- Make sure no other program is capturing the hotkeys

### Image Detection Failing

- Ensure screenshot images are clear and match in-game appearance
- Check confidence threshold (default 0.65)
- Verify Roblox window region is detected correctly
- Screenshots should be taken at same resolution as gameplay

### Unit Placement Issues

- Verify X/Y coordinates are correct for each unit
- Check that slot numbers (1-6) match in-game
- Ensure "Enabled" checkbox is checked for units
- Test with low unit counts first
- Make sure camera positioning completes before placement

### Discord Webhook Not Working

- Verify webhook URL is correct (should start with https://discord.com/api/webhooks/)
- Click "Test Webhook" to verify connection
- Check Discord server permissions
- Ensure webhook hasn't been deleted in Discord settings
- Webhook may fail if Discord API is down

### Auto-Reconnect Not Working

- Verify `disconnect.png` exists in `buttons` folder
- Check that private server link is correctly configured
- Ensure link is a valid Roblox private server URL
- Test private server link manually in browser first
- Make sure Roblox opens in default browser

### Auto-Challenges Issues

- Verify all challenge images exist in `buttons/challengeacts/`
- Check that `challenges.png`, `regular.png`, `trait.png`, `return.png` exist
- Ensure challenge configs exist for all three maps
- Test each challenge config individually first
- Verify selected stage for farming is configured correctly

### Performance Issues

- Close unnecessary applications
- Lower Roblox graphics settings
- Increase check intervals in config if CPU usage is high
- Ensure sufficient RAM is available
- Check that antivirus isn't blocking the application

## 📁 File Structure

```
anime paradox/
├── dist/
│   └── AnimeParadoxMacro.exe   # Standalone executable
├── buttons/                     # Button/UI detection images
│   ├── Acts/                    # Act number images
│   ├── challengeacts/           # Challenge map detection
│   │   ├── leaf.png
│   │   ├── planet.png
│   │   └── dark.png
│   ├── challengemaps/           # Challenge map images
│   ├── Areas.png
│   ├── challenges.png
│   ├── regular.png
│   ├── trait.png
│   ├── Start.png
│   ├── Yes.png
│   ├── victory.png
│   ├── defeat.png
│   ├── return.png
│   └── disconnect.png           # Disconnect detection
├── Settings/                    # Unit configurations
│   ├── Story/
│   │   ├── Leaf Village/
│   │   ├── Planet Namek/
│   │   └── Dark Hollow/
│   ├── Raid/
│   │   └── Frozen Gate/
│   ├── Siege/
│   │   └── Blue Dungeon/
│   └── Challenges/              # Challenge configs
│       ├── Leaf Village/
│       ├── Planet Namek/
│       └── Dark Hollow/
├── starting image/              # Reference screenshots
├── main_webview.py              # Main application entry point
├── macro_engine.py              # Core automation logic
├── mouse_controller.py          # Input control functions
├── config.py                    # Configuration management
├── version.py                   # Version information
├── updater.py                   # Auto-update system
├── ui.html                      # Web-based UI
├── requirements.txt             # Python dependencies
├── macro_config.json            # Runtime configuration (auto-generated)
└── README.md                    # This file
```

## 🔐 Configuration Files

### macro_config.json
Auto-generated file storing:
- Selected mode, location, and act
- Discord webhook URL
- Private server link
- Win/loss statistics
- Custom keybinds
- Challenge settings

### Unit Config Files (Settings folder)
JSON files for each mode/location/act:
```json
{
  "Units": [
    {
      "Index": 1,
      "Enabled": true,
      "PlaceBeforeYes": false,
      "AutoUpgrade": true,
      "Slot": "1",
      "X": "500",
      "Y": "400",
      "Upgrade": "4",
      "Note": "Main DPS"
    }
  ]
}
```

## 🛡️ Safety & Best Practices

### Safety Features
- **Failsafe**: Move mouse to screen corner to emergency stop
- **Disconnect Detection**: Auto-recovers from connection issues
- **Status Monitoring**: Real-time updates on all macro actions
- **Error Handling**: Gracefully handles failures and retries

### Best Practices
1. **Test First**: Always test new configs with a few units before full automation
2. **Monitor Initially**: Watch the first few runs to ensure proper operation
3. **Use Private Servers**: Reduces risk of disconnection
4. **Configure Webhooks**: Stay informed of macro status remotely
5. **Regular Backups**: Save your unit configs regularly
6. **Update Software**: Keep the macro updated for bug fixes and features

### Performance Tips
- Close unnecessary programs to reduce lag
- Lower Roblox graphics for better detection reliability
- Use wired internet connection for stability
- Keep Roblox window visible and unobstructed
- Run on primary monitor for best results

## 🔄 Updates

The macro includes an auto-update system:
1. Go to Update tab
2. Click "Check for Updates"
3. If update available, click "Download & Install"
4. Application will download, extract, and restart automatically

Updates are fetched from the GitHub releases page.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## 📝 Version History

### V0.0 - Initial Release
- ✅ Story, Raid, Siege mode support
- ✅ 30-unit configuration system
- ✅ Discord webhook notifications with screenshots
- ✅ Auto-reconnect system for disconnects
- ✅ Auto-Challenges with 30-minute cycles
- ✅ Map-specific positioning for all locations
- ✅ Win/loss statistics tracking
- ✅ Modern web-based UI
- ✅ Auto-update system

## ⚖️ License & Disclaimer

This tool is for **educational purposes only**. 

**Important Notes:**
- Automation may violate Roblox Terms of Service
- Use at your own risk
- No warranty or guarantee provided
- Not responsible for account actions
- Recommended for private server use only

The developers are not responsible for any consequences resulting from the use of this software.

## 📧 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing issues for solutions
- Include error messages and logs when reporting bugs

---

**Made with ❤️ for the Anime Paradox community**
