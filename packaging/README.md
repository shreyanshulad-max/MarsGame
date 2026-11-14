# MARSMISSION — Developer Packaging Guide

## Overview

| Target | Output | Build host |
|--------|--------|------------|
| Windows 10/11 | `dist/MARSMISSION/` + `releases/windows/MARSMISSION_Windows.zip` | Windows |
| macOS | `dist/MARSMISSION.app` + `releases/macos/MARSMISSION_macOS.zip` | **macOS only** |

Packaging mode: **PyInstaller ONEDIR** (not onefile).

Application version: see `systems/version.py` (`MARSMISSION v1.0.0`).

---

## Prerequisites

```bash
cd /path/to/MarsMission
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS:   source .venv/bin/activate
python -m pip install -r requirements-build.txt
```

Runtime dependency: **pygame-ce** (imported as `pygame`).  
Build dependency: **PyInstaller 6.x**.

---

## Windows build

```powershell
cd C:\MarsMission

# DEBUG (console window for logs)
.\packaging\build_windows.ps1 -Mode DEBUG

# RELEASE (no console)
.\packaging\build_windows.ps1 -Mode RELEASE
```

Or manually:

```powershell
$env:MARS_BUILD_CONSOLE="0"
python -m PyInstaller --clean --noconfirm packaging\MarsMission.spec
```

**Launch test:**

```powershell
.\dist\MARSMISSION\MARSMISSION.exe
```

Saves write to: `%LOCALAPPDATA%\MarsMission\`  
Crashes write: `%LOCALAPPDATA%\MarsMission\crash.log`

---

## macOS build

Run **on a Mac** (Apple Silicon or Intel — build for the machine you have; do not claim universal2 unless tested):

```bash
cd /path/to/MarsMission
chmod +x packaging/build_macos.sh
./packaging/build_macos.sh RELEASE
```

**Launch test:**

```bash
open dist/MARSMISSION.app
```

Saves: `~/Library/Application Support/MarsMission/`

### Code signing & notarization

Unsigned apps show Gatekeeper warnings. To distribute widely you need:

1. Apple Developer Program membership  
2. `codesign --deep --force --options runtime --sign "Developer ID Application: …" MARSMISSION.app`  
3. Notarization via `notarytool` / Xcode  

This repository does **not** include signing certificates or automate notarization.

---

## What is included

- `main.py` entry + all `systems/` modules (via Analysis imports)  
- Entire `assets/` tree (research datasets, manifests, optional sprites/audio)  
- Player README  

## What is excluded

- `.venv`, `.git`, `__pycache__`, `build/`, personal saves, `Mars_Survival_RPG`, `main_m2_backup.py`, tests, backups  

---

## Spec file

`packaging/MarsMission.spec`

- `MARS_BUILD_CONSOLE=1` → DEBUG console  
- `MARS_BUILD_CONSOLE=0` → RELEASE windowed  
- Optional icon: `assets/ui/marsmission_icon.ico` (if present)  

---

## itch.io

1. Build RELEASE packages on each OS.  
2. Upload zips from `releases/windows/` and `releases/macos/`.  
3. Use draft copy in `releases/release_notes/ITCH_IO_DRAFT.md`.  
4. Do not publish until smoke-tested outside the dev machine.

---

## Smoke checklist

- [ ] Launches without Python installed  
- [ ] Title screen appears  
- [ ] Assets / research images load (or honest placeholders)  
- [ ] Continue / New Campaign / Records  
- [ ] Mission 1–3 start paths  
- [ ] Save appears under AppData / Application Support  
- [ ] Offline play  
- [ ] No missing DLL / dylib errors  
