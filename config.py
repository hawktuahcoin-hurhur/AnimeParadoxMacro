"""Configuration settings for the Roblox Macro"""
import json
import os
import sys

def get_app_path():
    """Get the application path for writable data"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)

CONFIG_FILE = os.path.join(get_app_path(), "macro_config.json")

DEFAULT_CONFIG = {
    "start_keybind": "f1",
    "stop_keybind": "f3",
    "mode": "Story",
    "location": "Leaf Village",
    "act": "Act 1",
    "nightmare": False,
    "ocr_tolerance": 0.6,  # OCR confidence threshold (0.0 - 1.0)
    "t_press_delay": 0.08,  # Delay between repeated 'T' presses (seconds)
    "placement_area": None,  # Will store {"x": int, "y": int, "width": int, "height": int}
    "discord_webhook_url": "",  # Discord webhook URL for notifications
    "stats_wins": 0,  # Total wins tracked
    "stats_losses": 0,  # Total losses tracked
    "private_server_link": "",  # Roblox private server link for auto-reconnect
    "auto_challenges_enabled": False,  # Auto-challenges mode toggle
    "challenge_location": "Leaf Village",  # Challenge location selection
    "slots": [
        {
            "name": "Slot 1",
            "placement_priority": 1,
            "upgrade_priority": 1,
            "placement_limit": 3,
            "enabled": True
        },
        {
            "name": "Slot 2",
            "placement_priority": 2,
            "upgrade_priority": 2,
            "placement_limit": 3,
            "enabled": True
        },
        {
            "name": "Slot 3",
            "placement_priority": 3,
            "upgrade_priority": 3,
            "placement_limit": 3,
            "enabled": False
        },
        {
            "name": "Slot 4",
            "placement_priority": 4,
            "upgrade_priority": 4,
            "placement_limit": 3,
            "enabled": False
        },
        {
            "name": "Slot 5",
            "placement_priority": 5,
            "upgrade_priority": 5,
            "placement_limit": 3,
            "enabled": False
        },
        {
            "name": "Slot 6",
            "placement_priority": 6,
            "upgrade_priority": 6,
            "placement_limit": 3,
            "enabled": False
        }
    ]
}

def load_config():
    """Load configuration from file or return defaults"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Merge with defaults for any missing keys
                for key in DEFAULT_CONFIG:
                    if key not in config:
                        config[key] = DEFAULT_CONFIG[key]
                return config
        except (json.JSONDecodeError, IOError):
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()

def save_config(config):
    """Save configuration to file"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)
