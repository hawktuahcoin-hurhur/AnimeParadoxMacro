"""
Auto-updater module for AnimeParadoxMacro
Checks GitHub for new versions and updates the application.
"""
import os
import sys
import json
import shutil
import tempfile
import subprocess
import urllib.request
import urllib.error
from version import VERSION, GITHUB_REPO, GITHUB_RELEASES_API

# WinRAR download URL (official)
WINRAR_DOWNLOAD_URL = "https://www.win-rar.com/fileadmin/winrar-versions/winrar/winrar-x64-701.exe"
SEVENZ_DOWNLOAD_URL = "https://www.7-zip.org/a/7z2301-x64.exe"

class AutoUpdater:
    def __init__(self, status_callback=None):
        self.status_callback = status_callback or print
        self.current_version = VERSION
        self.app_dir = self._get_app_directory()
        
    def _get_app_directory(self):
        """Get the application directory (handles both .py and .exe)"""
        if getattr(sys, 'frozen', False):
            # Running as compiled exe
            return os.path.dirname(sys.executable)
        else:
            # Running as script
            return os.path.dirname(os.path.abspath(__file__))
    
    def _update_status(self, message):
        """Update status via callback"""
        if self.status_callback:
            self.status_callback(message)
    
    def check_for_updates(self):
        """Check GitHub for the latest version"""
        try:
            self._update_status("Checking for updates...")
            
            # Get latest release info from GitHub API
            req = urllib.request.Request(
                GITHUB_RELEASES_API,
                headers={'User-Agent': 'AnimeParadoxMacro-Updater'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
            
            latest_version = data.get('tag_name', '').lstrip('v')
            release_notes = data.get('body', 'No release notes available.')
            download_url = None
            
            # Find the zip asset
            for asset in data.get('assets', []):
                if asset['name'].endswith('.zip'):
                    download_url = asset['browser_download_url']
                    break
            
            # If no assets, check for the release zip directly
            if not download_url:
                # Try to get from releases/download
                download_url = f"https://github.com/{GITHUB_REPO}/releases/download/{data.get('tag_name')}/AnimeParadoxMacro_Release.zip"
            
            if not latest_version:
                return {
                    "success": False,
                    "message": "Could not determine latest version"
                }
            
            # Compare versions
            is_newer = self._compare_versions(latest_version, self.current_version)
            
            return {
                "success": True,
                "current_version": self.current_version,
                "latest_version": latest_version,
                "update_available": is_newer,
                "download_url": download_url,
                "release_notes": release_notes
            }
            
        except urllib.error.URLError as e:
            return {
                "success": False,
                "message": f"Network error: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error checking for updates: {str(e)}"
            }
    
    def _compare_versions(self, latest, current):
        """Compare version strings. Returns True if latest > current"""
        try:
            latest_parts = [int(x) for x in latest.split('.')]
            current_parts = [int(x) for x in current.split('.')]
            
            # Pad shorter version with zeros
            while len(latest_parts) < len(current_parts):
                latest_parts.append(0)
            while len(current_parts) < len(latest_parts):
                current_parts.append(0)
            
            for l, c in zip(latest_parts, current_parts):
                if l > c:
                    return True
                elif l < c:
                    return False
            return False
        except:
            return False
    
    def download_and_install(self, download_url):
        """Download the update and install it"""
        try:
            self._update_status("Downloading update...")
            
            # Create temp directory
            temp_dir = tempfile.mkdtemp(prefix="anime_paradox_update_")
            zip_path = os.path.join(temp_dir, "update.zip")
            extract_dir = os.path.join(temp_dir, "extracted")
            
            # Download the zip file
            self._download_file(download_url, zip_path)
            
            self._update_status("Extracting update...")
            
            # Extract using available method
            extract_result = self._extract_zip(zip_path, extract_dir)
            if not extract_result.get("success"):
                # Cleanup temp directory
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
                
                if extract_result.get("need_extractor"):
                    return {
                        "success": False,
                        "need_extractor": True,
                        "message": extract_result.get("message", "No extractor available")
                    }
                return {
                    "success": False,
                    "message": extract_result.get("message", "Failed to extract update package")
                }
            
            self._update_status("Installing update...")
            
            # Find the extracted content
            extracted_contents = os.listdir(extract_dir)
            source_dir = extract_dir
            
            # If there's a single folder, use that as source
            if len(extracted_contents) == 1:
                potential_dir = os.path.join(extract_dir, extracted_contents[0])
                if os.path.isdir(potential_dir):
                    source_dir = potential_dir
            
            # Copy files to app directory
            files_updated = self._copy_update_files(source_dir, self.app_dir)
            
            # Cleanup temp directory
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
            
            self._update_status(f"Update complete! {files_updated} files updated.")
            
            return {
                "success": True,
                "message": f"Update installed successfully! {files_updated} files updated.",
                "restart_required": True
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Update failed: {str(e)}"
            }
    
    def _download_file(self, url, dest_path):
        """Download a file with progress updates"""
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'AnimeParadoxMacro-Updater'}
        )
        
        with urllib.request.urlopen(req, timeout=300) as response:
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            block_size = 8192
            
            with open(dest_path, 'wb') as f:
                while True:
                    chunk = response.read(block_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if total_size > 0:
                        percent = int((downloaded / total_size) * 100)
                        self._update_status(f"Downloading... {percent}%")
    
    def _extract_zip(self, zip_path, extract_dir):
        """Extract zip file using available methods"""
        os.makedirs(extract_dir, exist_ok=True)
        
        # Try WinRAR first
        winrar_paths = [
            r"C:\Program Files\WinRAR\WinRAR.exe",
            r"C:\Program Files (x86)\WinRAR\WinRAR.exe"
        ]
        
        winrar_found = False
        for winrar_path in winrar_paths:
            if os.path.exists(winrar_path):
                winrar_found = True
                try:
                    subprocess.run(
                        [winrar_path, 'x', '-y', zip_path, extract_dir + '\\'],
                        check=True,
                        capture_output=True,
                        timeout=300
                    )
                    self._update_status("Extracted with WinRAR")
                    return {"success": True}
                except:
                    pass
        
        # Try 7-Zip
        sevenz_paths = [
            r"C:\Program Files\7-Zip\7z.exe",
            r"C:\Program Files (x86)\7-Zip\7z.exe"
        ]
        
        sevenz_found = False
        for sevenz_path in sevenz_paths:
            if os.path.exists(sevenz_path):
                sevenz_found = True
                try:
                    subprocess.run(
                        [sevenz_path, 'x', '-y', f'-o{extract_dir}', zip_path],
                        check=True,
                        capture_output=True,
                        timeout=300
                    )
                    self._update_status("Extracted with 7-Zip")
                    return {"success": True}
                except:
                    pass
        
        # Fallback to Python's zipfile
        try:
            import zipfile
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            self._update_status("Extracted with Python zipfile")
            return {"success": True}
        except Exception as e:
            # If no extractor found, prompt to install
            if not winrar_found and not sevenz_found:
                self._update_status("No archive extractor found!")
                return {
                    "success": False,
                    "need_extractor": True,
                    "message": "No archive extractor found. Please install WinRAR or 7-Zip."
                }
            self._update_status(f"Extraction failed: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def check_extractors(self):
        """Check if WinRAR or 7-Zip is installed"""
        winrar_paths = [
            r"C:\Program Files\WinRAR\WinRAR.exe",
            r"C:\Program Files (x86)\WinRAR\WinRAR.exe"
        ]
        sevenz_paths = [
            r"C:\Program Files\7-Zip\7z.exe",
            r"C:\Program Files (x86)\7-Zip\7z.exe"
        ]
        
        winrar_installed = any(os.path.exists(p) for p in winrar_paths)
        sevenz_installed = any(os.path.exists(p) for p in sevenz_paths)
        
        return {
            "winrar": winrar_installed,
            "sevenz": sevenz_installed,
            "any_installed": winrar_installed or sevenz_installed
        }
    
    def download_winrar(self):
        """Download WinRAR installer"""
        try:
            self._update_status("Downloading WinRAR installer...")
            
            # Download to temp directory
            temp_dir = tempfile.gettempdir()
            installer_path = os.path.join(temp_dir, "winrar_installer.exe")
            
            self._download_file(WINRAR_DOWNLOAD_URL, installer_path)
            
            self._update_status("Running WinRAR installer...")
            
            # Run the installer
            subprocess.Popen([installer_path], shell=True)
            
            return {
                "success": True,
                "message": "WinRAR installer started. Please complete the installation and try the update again.",
                "installer_path": installer_path
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to download WinRAR: {str(e)}"
            }
    
    def download_7zip(self):
        """Download 7-Zip installer"""
        try:
            self._update_status("Downloading 7-Zip installer...")
            
            # Download to temp directory
            temp_dir = tempfile.gettempdir()
            installer_path = os.path.join(temp_dir, "7zip_installer.exe")
            
            self._download_file(SEVENZ_DOWNLOAD_URL, installer_path)
            
            self._update_status("Running 7-Zip installer...")
            
            # Run the installer
            subprocess.Popen([installer_path], shell=True)
            
            return {
                "success": True,
                "message": "7-Zip installer started. Please complete the installation and try the update again.",
                "installer_path": installer_path
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to download 7-Zip: {str(e)}"
            }
    
    def _copy_update_files(self, source_dir, dest_dir):
        """Copy update files to destination, skipping config files"""
        files_to_skip = ['config.json', 'macro_config.json']
        folders_to_update = ['buttons', 'Settings', 'starting image', 'unit stuff']
        files_updated = 0
        
        # Copy folders
        for folder in folders_to_update:
            src_folder = os.path.join(source_dir, folder)
            dst_folder = os.path.join(dest_dir, folder)
            
            if os.path.exists(src_folder):
                # Remove existing folder and copy new one
                if os.path.exists(dst_folder):
                    try:
                        shutil.rmtree(dst_folder)
                    except:
                        pass
                
                try:
                    shutil.copytree(src_folder, dst_folder)
                    files_updated += 1
                    self._update_status(f"Updated: {folder}/")
                except Exception as e:
                    self._update_status(f"Warning: Could not update {folder}: {e}")
        
        # Copy exe if it exists in update
        for filename in os.listdir(source_dir):
            src_path = os.path.join(source_dir, filename)
            dst_path = os.path.join(dest_dir, filename)
            
            if os.path.isfile(src_path):
                if filename in files_to_skip:
                    continue
                
                if filename.endswith('.exe'):
                    # For exe, we need to rename current and copy new
                    try:
                        if os.path.exists(dst_path):
                            backup_path = dst_path + '.old'
                            if os.path.exists(backup_path):
                                os.remove(backup_path)
                            os.rename(dst_path, backup_path)
                        shutil.copy2(src_path, dst_path)
                        files_updated += 1
                        self._update_status(f"Updated: {filename}")
                    except Exception as e:
                        self._update_status(f"Warning: Could not update {filename}: {e}")
        
        return files_updated


def check_update():
    """Quick check for updates - returns dict with update info"""
    updater = AutoUpdater()
    return updater.check_for_updates()


def perform_update(download_url, status_callback=None):
    """Perform the update - downloads and installs"""
    updater = AutoUpdater(status_callback)
    return updater.download_and_install(download_url)
