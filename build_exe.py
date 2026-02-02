"""
Build script for creating executable
Run this with: python build_exe.py
"""
import subprocess
import sys

print("Building AnimeParadoxMacro.exe...")

# PyInstaller command
cmd = [
    sys.executable,
    '-m', 'PyInstaller',
    'main_webview.py',
    '--name=AnimeParadoxMacro',
    '--onefile',
    '--windowed',
    '--add-data=ui.html;.',
    '--add-data=overlay.html;.',
    '--add-data=buttons;buttons',
    '--add-data=Settings;Settings',
    '--add-data=starting image;starting image',
    '--add-data=unit stuff;unit stuff',
    '--hidden-import=paddleocr',
    '--hidden-import=paddlepaddle',
    '--hidden-import=easyocr',
    '--hidden-import=cv2',
    '--hidden-import=PIL',
    '--hidden-import=pydirectinput',
    '--hidden-import=keyboard',
    '--hidden-import=pynput',
    '--hidden-import=rapidfuzz',
    '--hidden-import=mss',
    '--collect-all=paddleocr',
    '--collect-all=paddlepaddle',
    '--collect-all=easyocr',
    '--noconfirm',
]

result = subprocess.run(cmd, cwd=r'c:\Users\Owner\OneDrive\Documents\anime paradox')

if result.returncode == 0:
    print(f"\n{'='*60}")
    print(f"Build completed successfully!")
    print(f"Executable: dist\\AnimeParadoxMacro.exe")
    print(f"{'='*60}")
else:
    print(f"\nBuild failed with error code: {result.returncode}")

