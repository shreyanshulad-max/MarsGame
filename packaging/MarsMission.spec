# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller ONEDIR spec for MARSMISSION.

Build (from project root):
  set MARS_BUILD_CONSOLE=1          # DEBUG (console)
  set MARS_BUILD_CONSOLE=0          # RELEASE (no console)  [default]
  python -m PyInstaller --clean --noconfirm packaging/MarsMission.spec
"""

from __future__ import annotations

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

SPECDIR = Path(SPECPATH).resolve()
ROOT = SPECDIR.parent

# Console: DEBUG builds enable a console for troubleshooting
CONSOLE = os.environ.get("MARS_BUILD_CONSOLE", "0").strip() in ("1", "true", "True", "yes")

# Collect all systems.* modules (hidden / dynamic imports)
hidden = collect_submodules("systems")
hidden += [
    "pygame",
    "pygame._sdl2",
    "pygame._sdl2.sdl2",
    "pygame.locals",
    "pygame.mixer",
    "pygame.font",
    "pygame.image",
    "pygame.transform",
]

# Bundled read-only data
datas = [
    (str(ROOT / "assets"), "assets"),
    (str(ROOT / "PLAYER_README.md"), "."),
    (str(ROOT / "SETUP.md"), "."),
]

# Optional icon
icon_path = ROOT / "assets" / "ui" / "marsmission_icon.ico"
if not icon_path.is_file():
    icon_path = None

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter.test",
        "unittest",
        "pytest",
        "numpy.tests",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MARSMISSION",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=CONSOLE,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path) if icon_path else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="MARSMISSION",
)

# macOS .app bundle — only define when building on Darwin
import sys as _sys

if _sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="MARSMISSION.app",
        icon=str(icon_path) if icon_path else None,
        bundle_identifier="com.marsmission.game",
        info_plist={
            "CFBundleName": "MARSMISSION",
            "CFBundleDisplayName": "MARSMISSION",
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
            "NSHighResolutionCapable": True,
            "CFBundleGetInfoString": "MARSMISSION – Explore. Research. Repair. Survive.",
        },
    )
