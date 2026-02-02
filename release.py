"""
Release script for AnimeParadoxMacro
Automates version bumping, building, and publishing to GitHub.

Usage:
    python release.py patch   # 1.0.0 -> 1.0.1
    python release.py minor   # 1.0.0 -> 1.1.0
    python release.py major   # 1.0.0 -> 2.0.0
"""
import sys
import os
import re
import subprocess

# Fix stdout encoding for emoji characters on Windows
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

def get_current_version():
    """Read current version from version.py"""
    with open('version.py', 'r') as f:
        content = f.read()
    match = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', content)
    if match:
        return match.group(1)
    return "1.0.0"

def bump_version(version, bump_type):
    """Bump version number"""
    parts = [int(x) for x in version.split('.')]
    while len(parts) < 3:
        parts.append(0)
    
    if bump_type == 'major':
        parts[0] += 1
        parts[1] = 0
        parts[2] = 0
    elif bump_type == 'minor':
        parts[1] += 1
        parts[2] = 0
    else:  # patch
        parts[2] += 1
    
    return '.'.join(str(p) for p in parts)

def update_version_file(new_version):
    """Update version.py with new version"""
    with open('version.py', 'r') as f:
        content = f.read()
    
    content = re.sub(
        r'VERSION\s*=\s*["\'][^"\']+["\']',
        f'VERSION = "{new_version}"',
        content
    )
    
    with open('version.py', 'w') as f:
        f.write(content)

def build_exe():
    """Build the executable"""
    print("\n📦 Building executable...")
    result = subprocess.run([sys.executable, 'build_exe.py'])
    return result.returncode == 0

def create_release_zip():
    """Create the release zip file"""
    print("\n📁 Creating release zip...")
    import shutil
    
    zip_name = 'AnimeParadoxMacro_Release'
    
    # Remove old zip if exists
    if os.path.exists(f'{zip_name}.zip'):
        os.remove(f'{zip_name}.zip')
    
    # Create zip with required files
    shutil.make_archive(
        zip_name,
        'zip',
        root_dir='.',
        base_dir=None
    )
    
    # Actually we need to use a different approach for selective files
    import zipfile
    
    # Remove the archive we just made
    os.remove(f'{zip_name}.zip')
    
    with zipfile.ZipFile(f'{zip_name}.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add exe
        exe_path = os.path.join('dist', 'AnimeParadoxMacro.exe')
        if os.path.exists(exe_path):
            zipf.write(exe_path, 'AnimeParadoxMacro.exe')
        
        # Add folders
        folders = ['buttons', 'Settings', 'starting image', 'unit stuff']
        for folder in folders:
            if os.path.exists(folder):
                for root, dirs, files in os.walk(folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, file_path)
    
    print(f"✅ Created {zip_name}.zip")
    return True

def git_commit_and_tag(version):
    """Commit changes and create tag"""
    print(f"\n📝 Committing version {version}...")
    
    # Add files
    subprocess.run(['git', 'add', 'version.py', 'AnimeParadoxMacro_Release.zip'])
    
    # Commit
    subprocess.run(['git', 'commit', '-m', f'Release v{version}'])
    
    # Create tag
    subprocess.run(['git', 'tag', '-a', f'v{version}', '-m', f'Release v{version}'])
    
    print(f"✅ Created tag v{version}")

def push_to_github():
    """Push commits and tags to GitHub"""
    print("\n🚀 Pushing to GitHub...")
    subprocess.run(['git', 'push'])
    subprocess.run(['git', 'push', '--tags'])

def create_github_release(version):
    """Create GitHub release using gh CLI"""
    print(f"\n🎉 Creating GitHub release v{version}...")
    
    # Refresh PATH to ensure gh is available
    env = os.environ.copy()
    env['PATH'] = subprocess.run(
        ['powershell', '-c', '[System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")'],
        capture_output=True, text=True
    ).stdout.strip() + ';' + env.get('PATH', '')
    
    result = subprocess.run([
        'gh', 'release', 'create', f'v{version}',
        'AnimeParadoxMacro_Release.zip',
        '--title', f'AnimeParadoxMacro v{version}',
        '--notes', f'Release v{version}\n\nDownload AnimeParadoxMacro_Release.zip and extract to install.'
    ], env=env)
    
    if result.returncode == 0:
        print(f"✅ Created release v{version}")
    else:
        print("⚠️ Failed to create release. You may need to create it manually on GitHub.")

def main():
    if len(sys.argv) < 2:
        print("Usage: python release.py [patch|minor|major]")
        print("  patch: 1.0.0 -> 1.0.1")
        print("  minor: 1.0.0 -> 1.1.0")
        print("  major: 1.0.0 -> 2.0.0")
        return
    
    bump_type = sys.argv[1].lower()
    if bump_type not in ['patch', 'minor', 'major']:
        print(f"Invalid bump type: {bump_type}")
        print("Use: patch, minor, or major")
        return
    
    current_version = get_current_version()
    new_version = bump_version(current_version, bump_type)
    
    print(f"🔄 Bumping version: {current_version} -> {new_version}")
    
    # Update version file
    update_version_file(new_version)
    print(f"✅ Updated version.py")
    
    # Build executable
    if not build_exe():
        print("❌ Build failed!")
        return
    
    # Create release zip
    create_release_zip()
    
    # Git operations
    git_commit_and_tag(new_version)
    push_to_github()
    
    # Create GitHub release
    create_github_release(new_version)
    
    print(f"\n{'='*50}")
    print(f"🎉 Release v{new_version} complete!")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
