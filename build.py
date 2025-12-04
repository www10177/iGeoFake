import PyInstaller.__main__
import os
import shutil
import sys
from pathlib import Path

# Clean previous build
if os.path.exists("dist"):
    shutil.rmtree("dist")
if os.path.exists("build"):
    shutil.rmtree("build")

# 1. Build pymobiledevice3 as a console tool (separate exe)
# Skipped, using OneFile strategy below directly

# 2. Build iGeoFake Main App
print("Building iGeoFake Main App...")
PyInstaller.__main__.run([
    'main.py',
    '--name=iGeoFake',
    '--onedir',
    '--windowed', # GUI app
    '--clean',
    f'--add-data=static{os.pathsep}static', # Use correct separator for platform
    '--hidden-import=nicegui',
    '--hidden-import=pymobiledevice3',
    '--distpath=dist',
])

# 3. Merge files
# Copy content of dist/temp_cli/pymobiledevice3/ to dist/iGeoFake/
# We only need the executable and maybe some unique dependencies?
# Actually, since both are python apps, they share a lot.
# If we dump everything into one folder, we might have conflicts if versions differ,
# but here they are built from the same env.
# However, PyInstaller onedir builds are self-contained.
# Merging them is tricky because of internal manifest/structure.

# Simpler approach: Just put the 'pymobiledevice3.exe' (and its dependencies)
# into a subfolder 'cli' or just separate?
# The Requirement is that process_manager.py can find it.
# If process_manager.py looks in `.` (current dir), then they should be in the same dir.

# Let's see. If we build two onedirs, we have:
# dist/iGeoFake/ (contains iGeoFake.exe and internal _internal/)
# dist/temp_cli/pymobiledevice3/ (contains pymobiledevice3.exe and _internal/)

# We cannot easily merge two onedir builds because they might expect different internal structures
# or overwrite each other's python dlls.
# Although, since they use same python version, the DLLs are same.
# But `_internal` folders might contain different set of pyc files.

# Strategy:
# Build pymobiledevice3 as --onefile ?
# Startup is slower, but easier to bundle inside iGeoFake's folder.
# User said "whatever make it could be build it as windows exe".
# Onefile for the CLI tool is acceptable as it is a background process helper.

print("Re-building pymobiledevice3 as OneFile for easier bundling...")
PyInstaller.__main__.run([
    'cli_entry.py',
    '--name=pymobiledevice3',
    '--onefile',
    '--clean',
    '--console',
    '--hidden-import=pymobiledevice3',
    '--collect-all=pymobiledevice3',
    '--copy-metadata=readchar',
    '--copy-metadata=pymobiledevice3',
    '--copy-metadata=inquirer3',
    '--copy-metadata=pyimg4',
    '--copy-metadata=click',
    '--distpath=dist', # Will create dist/pymobiledevice3.exe
])

# Now move pymobiledevice3.exe into dist/iGeoFake/
source = Path('dist/pymobiledevice3.exe')
if sys.platform != 'win32':
     source = Path('dist/pymobiledevice3')

if not source.exists():
    print(f"Warning: {source} not found. Build might have failed or platform specific naming issue.")

dest_dir = Path('dist/iGeoFake')
if dest_dir.exists():
    print(f"Moving {source.name} to {dest_dir}...")
    shutil.move(str(source), str(dest_dir / source.name))
else:
    print("Error: iGeoFake dist folder not found.")

# Clean up temp
if os.path.exists("dist/temp_cli"):
    shutil.rmtree("dist/temp_cli")

print("Build Complete. executable is in dist/iGeoFake/iGeoFake.exe")
