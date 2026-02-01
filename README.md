# Anime Paradox Macro

A Roblox macro with OCR-based automation for Anime Paradox gameplay.

## Features

- **Stage Selection**: Support for Story, Raids, and Siege modes
- **Story Mode Navigation**: Automatically navigates through menus (Areas → Create Match → Location → Act → Start)
- **OCR Detection**: Uses Tesseract OCR to find and click on-screen text
- **Customizable Hotkeys**: F1 to start, F3 to stop (customizable)
- **Placement System**: 
  - 6 configurable unit slots
  - Placement and upgrade priority system
  - Placement limits per slot
  - Spiral placement pattern
- **Auto-Replay**: Automatically detects Victory/Defeat and clicks Replay

## Installation

### Prerequisites

1. **Python 3.8+** - Download from [python.org](https://www.python.org/downloads/)

2. **Tesseract OCR** - Required for text recognition
   - Download from: https://github.com/UB-Mannheim/tesseract/wiki
   - Install to default location: `C:\Program Files\Tesseract-OCR\`
   - Add to PATH or update the path in `ocr_utils.py`

### Setup

1. Open a terminal in this folder

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. If Tesseract is installed in a non-default location, edit `ocr_utils.py`:
   ```python
   pytesseract.pytesseract.tesseract_cmd = r'C:\Your\Path\To\tesseract.exe'
   ```

## Usage

### Running the Macro

```bash
python main.py
```

### Configuration

1. **Select Stage**:
   - Choose Mode (Story, Raids, Siege)
   - For Story: Select Location and Act

2. **Configure Keybinds**:
   - Default: F1 (Start), F3 (Stop)
   - Click "Set" to capture a new key

3. **Configure Placement Area**:
   - Click "Configure Placement Area & Slots"
   - Add a screenshot to the `starting image` folder
   - Draw a rectangle on the image to define the placement area
   - Configure each slot's priorities and limits

4. **Start the Macro**:
   - Press F1 or click "Start Macro"
   - The macro will navigate through menus and start placing units

### Slot Configuration

Each slot has:
- **Name**: Custom name for the slot
- **Placement Priority**: Order in which units are placed (1-6)
- **Upgrade Priority**: Order in which units are upgraded (1-6)
- **Placement Limit**: Maximum units to place from this slot
- **Enabled**: Toggle to include/exclude the slot

## How It Works

### Story Mode Flow

1. Finds "Areas" on screen → Clicks
2. Holds 'A' key until "Create Match" appears → Clicks
3. Finds selected Location → Clicks
4. Finds selected Act (scrolls for Act 6) → Clicks
5. Finds "Start" → Clicks
6. Waits for "Yes" → Clicks
7. Adjusts camera (right-click drag + hold O)
8. Starts placement phase

### Placement Phase

1. Presses slot number key (1-6)
2. Clicks at spiral pattern coordinates
3. Checks for "Upgrade" text to verify placement
4. Saves coordinates and tracks placement count
5. Repeats until all slots hit their limits

### Upgrade Phase

1. Clicks on each placed unit
2. Clicks "Upgrade" button
3. Follows upgrade priority order

### Game End

1. Detects "Victory" or "Defeat"
2. Finds and clicks "Replay"
3. Repeats placement phase (skips menu navigation)

## Troubleshooting

### OCR Not Working

- Ensure Tesseract is installed and path is correct
- Try adjusting screen brightness/contrast
- The game UI should be clearly visible

### Hotkeys Not Working

- Run the program as Administrator
- Check if another program is capturing the hotkeys
- Try different keybinds

### Placement Failing

- Ensure placement area is correctly configured
- Check that the game camera is properly positioned
- Verify slot numbers match your in-game unit slots

## File Structure

```
anime paradox/
├── main.py              # Main application with GUI
├── macro_engine.py      # Core macro logic
├── ocr_utils.py         # OCR functions
├── mouse_controller.py  # Mouse/keyboard control
├── placement_editor.py  # Placement area configuration
├── config.py            # Configuration management
├── requirements.txt     # Python dependencies
├── macro_config.json    # Saved configuration (auto-generated)
├── starting image/      # Folder for game screenshot
└── README.md            # This file
```

## Safety Notes

- The macro uses PyAutoGUI's failsafe - move mouse to top-left corner to abort
- Always test with low placement limits first
- Don't leave the macro running unattended for extended periods

## Disclaimer

This tool is for educational purposes. Use at your own risk. Automation may violate game terms of service.
