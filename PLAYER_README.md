# MARSMISSION

**Explore. Research. Repair. Survive.**

Version **1.0.0**

An educational Mars outpost campaign game. Restore communications, rebuild power, and rescue a stranded rover — with optional NASA-inspired research activities.

---

## Supported systems

- **Windows** 10 / 11 (64-bit) — `MARSMISSION.exe` in the Windows zip  
- **macOS** — `MARSMISSION.app` (build/tested on the Mac architecture listed in the release notes)

No Python or Pygame installation is required for the packaged builds.

---

## Install & launch

### Windows

1. Download `MARSMISSION_Windows.zip`  
2. Unzip to a folder (for example `Documents\MARSMISSION`)  
3. Open the folder and double-click **`MARSMISSION.exe`**  
4. Keep all files in that folder together — do not run only the `.exe` after deleting the other packaged files  

### macOS

1. Download `MARSMISSION_macOS.zip`  
2. Unzip to get **`MARSMISSION.app`**  
3. Double-click to launch  
4. If Gatekeeper blocks an **unsigned** build: Right-click the app → **Open**, or allow it in System Settings → Privacy & Security  

---

## What you do

Complete three missions in order:

1. **Communication Blackout** — repair and align the antenna  
2. **Shelter Power Emergency** — rebuild the power circuit and allocate energy  
3. **Rover Rescue** — scan, repair, route-plan, and drive to the stranded rover  

Optional **Research Terminal** activities teach science concepts and earn **Research Points** for the supply store. Research is **not** required to unlock the next mission.

---

## Controls

| Key | Action |
|-----|--------|
| WASD / Arrow keys | Move on base / drive rover |
| E | Interact, collect, rescue |
| I | Inventory |
| J | Journal |
| ESC | Pause / back |
| Mouse | Menus, research, workbenches |
| SPACE (Mission 3 drive) | Handbrake |

---

## Saving

Progress saves automatically to a user folder (not inside the game package):

| OS | Save location |
|----|----------------|
| Windows | `%LOCALAPPDATA%\MarsMission\` |
| macOS | `~/Library/Application Support/MarsMission/` |
| Linux (dev) | `~/.local/share/MarsMission/` |

**Continue Campaign** loads this save.  
**New Campaign** starts fresh after confirmation (previous progress can be archived).  
**Mission Replay** practices completed missions without changing campaign unlocks.

The game works **offline** after install.

---

## Known limitations

- Many world graphics use procedural fallbacks when optional PNG sprites are not present  
- macOS builds may be unsigned (Gatekeeper warning)  
- Custom top-down rover art is optional; a procedural rover is used if missing  

---

## Credits & data

- Game built with **Python** and **Pygame CE**  
- Included research browse products and metadata are curated for education; see `assets/research_data/research_manifest.json` for attribution (NASA / JPL / University of Arizona / USGS where applicable)  

---

## Troubleshooting

| Issue | What to try |
|-------|-------------|
| Game won’t start | Re-unzip the full folder; Windows Defender may need an allow for the folder |
| Crash on launch | Check `%LOCALAPPDATA%\MarsMission\crash.log` (Windows) |
| Missing research images | Expected for some non-image datasets; placeholders are intentional |
| Save not found | Confirm you are on the same Windows user account |

For developers: see `packaging/README.md` and `SETUP.md`.
