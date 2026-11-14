# MARSMISSION — Packaging final report (v1.0.0)

## 1. Backup
`C:\MarsMission_Backups\MarsMission_Deploy_20261114_151610`

## 2. Git
- Branch: `master`
- Commit at start of packaging work: `81f81d1 clean folder`
- Uncommitted packaging changes were preserved (not discarded)

## 3. Dependency audit
- Entry point: `main.py`
- Python tested: **3.10.11** (Windows 64-bit)
- Runtime import: **pygame** (installed build used pygame 2.6.1; `requirements.txt` prefers **pygame-ce**)
- Stdlib only otherwise (json, pathlib, etc.)
- No API keys packaged

## 4. Requirements files
- `requirements.txt` — runtime (`pygame-ce`)
- `requirements-build.txt` — includes PyInstaller

## 5. Asset path changes
- New `systems/runtime_paths.py` (`resource_root`, `_MEIPASS`, frozen detection)
- `main.py`, `research_data.py`, `rover_renderer.py` (and related) use it
- Packaged assets live under PyInstaller 6 `_internal/assets` (resolved via `_MEIPASS`)

## 6. Save directory
Unchanged AppData strategy in `systems/savegame.py`:
- Windows `%LOCALAPPDATA%\MarsMission\`
- macOS `~/Library/Application Support/MarsMission/`
- Linux XDG / `~/.local/share/MarsMission/`
Bundled assets are never written when frozen.

## 7. PyInstaller
- Spec: `packaging/MarsMission.spec` (ONEDIR)
- Scripts: `packaging/build_windows.ps1`, `packaging/build_macos.sh`
- Docs: `packaging/README.md`, `PLAYER_README.md`

## 8. Windows build result
| Artifact | Result |
|----------|--------|
| DEBUG zip | `releases/windows/MARSMISSION_Windows_DEBUG.zip` (~28.8 MB) |
| RELEASE zip | `releases/windows/MARSMISSION_Windows.zip` (~28.8 MB) |
| Folder | `dist/MARSMISSION/MARSMISSION.exe` |
| Smoke launch DEBUG | Process stayed running 6s — OK |
| Smoke launch RELEASE | Process stayed running 5s — OK (`runw` / no console) |

## 9. macOS readiness
Scripts and `.app` BUNDLE block are ready. **Not built on this Windows machine.** Must run `./packaging/build_macos.sh` on a Mac and smoke-test there. Unsigned Gatekeeper caveats documented.

## 10. Data packaged
See `packaging/asset_inclusion_report.md` (research JPGs/JSON + manifests). Optional sprites/audio use procedural fallbacks when absent.

## 11. Excluded
`.venv`, `.git`, `__pycache__`, tests, personal saves, `Mars_Survival_RPG`, `main_m2_backup.py`

## 12. Build sizes
~28.8 MB compressed Windows zip (DEBUG and RELEASE).

## 13–14. Tests / OS
- OS tested for packaging: **Windows 10/11 (build host 10.0.26200)**
- Launch smoke: packaged EXE started successfully
- Full mission playthrough on a **Python-free** clean PC: **not yet performed** — required before calling the build public-ready
- macOS: **not tested**

## 15. Known limitations
- Placeholder icon PNG only (no `.ico` yet)
- pygame vs pygame-ce: either works as `import pygame`; clean venvs should use `requirements.txt`
- Do not claim itch.io publication until upload + clean-machine verification

## 16. Commands

```powershell
cd C:\MarsMission
.\packaging\build_windows.ps1 -Mode DEBUG
.\packaging\build_windows.ps1 -Mode RELEASE
.\dist\MARSMISSION\MARSMISSION.exe
```

```bash
# on macOS only
./packaging/build_macos.sh RELEASE
open dist/MARSMISSION.app
```
