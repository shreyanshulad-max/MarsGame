# MARSMISSION

**Explore. Research. Repair. Survive.**

An educational top-down Mars outpost game built with **Python** and **Pygame CE**.

You are a mission specialist at a Mars research base. Explore the colony, gather supplies, study optional NASA-inspired research, and complete three sequential challenges to restore the outpost and rescue a stranded rover.

---

## What the game is

MARSMISSION is a single-player campaign that mixes:

- **Open-world exploration** around the Mars base  
- **Puzzle / systems challenges** (antenna, power, rover)  
- **Optional research lessons** using curated educational NASA datasets  
- **Supply collection and procurement** so you can prepare for each mission  

### Story / campaign

A dust storm has damaged the outpost. You must restore critical systems in order:

| Mission | Name | Goal |
|---------|------|------|
| 1 | **Communication Blackout** | Repair the antenna assembly and align it to restore the SAT-02 link |
| 2 | **Shelter Power Emergency** | Rebuild the habitat power circuit and allocate limited energy |
| 3 | **Rover Rescue** | Scan for the stranded rover, repair it, plan a route, and drive to the rescue |

Completing the **current mission** unlocks the next one.  
**Research is optional** — it teaches science concepts and earns Research Points (RP) for the supply store, but it is not required to progress.

---

## How to run

### From source

```bash
cd MarsMission
python -m pip install -r requirements.txt
python main.py
```

### Packaged build (Windows)

Unzip `MARSMISSION_Windows.zip` and run `MARSMISSION.exe` (keep the whole folder together).

More setup detail: `SETUP.md` · Packaging: `packaging/README.md`

---

## Controls

### Base exploration (open world)

| Key | Action |
|-----|--------|
| **W A S D** or **Arrow keys** | Move |
| **E** | Interact / collect supplies / use stations |
| **I** | Open / close inventory |
| **J** | Open / close journal |
| **ESC** | Pause / back (context-dependent) |
| **Mouse** | Click menus, buttons, and UI |

### Research Terminal

| Control | Action |
|---------|--------|
| **Mouse** | Select activities, answers, and buttons |
| **RESEARCH HOME** | Return to the research activity list |
| **RETURN TO BASE** | Close research and return to the open world |

### Workbenches (Mission 1 & 3 assembly / repair)

| Control | Action |
|---------|--------|
| **Left click** a supply | Select a material |
| **Left click** a compatible slot | Install the selected material |
| **Right click** a slot | Remove installed part (where supported) |
| **UNDO / RESET** | Remove last part / clear the board |
| **TEST** | Check whether the assembly / repair is correct |

### Mission 1 — Antenna calibration

| Key | Action |
|-----|--------|
| **A** / **←** | Rotate antenna left |
| **D** / **→** | Rotate antenna right |

Hold the dish in the stable signal zone to collect packets during the timed challenge.

### Mission 2 — Power circuit

| Control | Action |
|---------|--------|
| **Mouse** | Place / confirm circuit links, install fuse, set power allocation |

### Mission 3 — Rover drive

| Key | Action |
|-----|--------|
| **W** / **↑** | Accelerate |
| **S** / **↓** | Brake / reverse |
| **A** / **←** | Steer left |
| **D** / **→** | Steer right |
| **SPACE** | Handbrake |
| **E** | Rescue (only inside the green rescue zone) |

---

## Tips

1. Explore the base and press **E** near supply caches to collect mission materials.  
2. Visit the **Research Terminal** to learn and earn RP, then use **Procurement** if you need remaining parts.  
3. Open a mission from the campaign dashboard when your kit is ready.  
4. Progress is saved automatically (Continue Campaign on the title screen).  

### Save locations

| OS | Folder |
|----|--------|
| Windows | `%LOCALAPPDATA%\MarsMission\` |
| macOS | `~/Library/Application Support/MarsMission/` |
| Linux | `~/.local/share/MarsMission/` |

---

## Credits

Built with Python and Pygame CE.  
Included research browse products carry attribution in `assets/research_data/research_manifest.json` (NASA / JPL / University of Arizona / USGS where applicable).

Version: **MARSMISSION v1.0.0**
