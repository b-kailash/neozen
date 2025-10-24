# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller spec file for NeoZen
This file defines how to build the standalone executable
"""

import sys
from pathlib import Path

# Get the base directory
spec_root = Path(SPECPATH)

# Determine the platform
is_windows = sys.platform.startswith('win')
is_macos = sys.platform == 'darwin'
is_linux = sys.platform.startswith('linux')

# Set executable name - simple naming for all platforms
exe_name = 'neozen.exe' if is_windows else 'neozen'

# Analysis - gather all Python files and dependencies
a = Analysis(
    ['main.py'],
    pathex=[str(spec_root)],
    binaries=[],
    datas=[
        # Include the icon file
        ('neozen/resources/neozen.png', 'neozen/resources'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'nmap',
        'psutil',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'tkinter',
    ],
    noarchive=False,
)

# Build the executable
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=exe_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Windowed mode (no console window)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='neozen/resources/neozen.png' if not is_windows else None,
)

# For macOS, create an app bundle
if is_macos:
    app = BUNDLE(
        exe,
        name='NeoZen.app',
        icon='neozen/resources/neozen.png',
        bundle_identifier='com.neozen.app',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSHighResolutionCapable': 'True',
            'CFBundleName': 'NeoZen',
            'CFBundleDisplayName': 'NeoZen',
            'CFBundleGetInfoString': 'Modern Nmap GUI',
            'CFBundleVersion': '0.1.0',
            'CFBundleShortVersionString': '0.1.0',
        },
    )
