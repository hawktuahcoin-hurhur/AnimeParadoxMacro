"""Version information for AnimeParadoxMacro"""
import os
import sys

def _get_app_path():
    """Get the application path for version.txt"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)

def _load_version():
    """Load version from version.txt if it exists, otherwise use default"""
    version_file = os.path.join(_get_app_path(), "version.txt")
    try:
        if os.path.exists(version_file):
            with open(version_file, 'r', encoding='utf-8') as f:
                return f.read().strip()
    except:
        pass
    return "0.0"

VERSION = _load_version()
GITHUB_REPO = "hawktuahcoin-hurhur/AnimeParadoxMacro"
GITHUB_RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main"
GITHUB_RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
