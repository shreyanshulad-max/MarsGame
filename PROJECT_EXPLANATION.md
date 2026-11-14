# MarsMission — Project Explanation Document

**Engine:** Python + Pygame CE  
**Resolution:** 1280 × 720  
**Target FPS:** 60  
**Genre:** Open-world top-down 2.5D Mars exploration / educational STEM campaign  
**Audience:** Grades 5–8 (accessible systems with optional deeper science content)  
**Project root:** `C:\MarsMission`

---

## 1. What the game is

**MarsMission** is a single-player educational campaign game set on a Mars research outpost. The player explores a top-down colony, collects mission materials, optionally studies NASA-inspired research datasets, purchases supplies with Research Points, and completes three sequential challenges:

1. **Communication Blackout** — repair and align an antenna to restore SAT-02.
2. **Shelter Power Emergency** — rebuild a power circuit and allocate energy.
3. **Rover Rescue** — scan for a stranded rover, repair it, plan a route, and drive to rescue it.

The campaign is designed so that **research is optional for progression**. Completing the current mission’s challenge is the only mandatory unlock condition for the next mission. Research awards **Research Points (RP)** that can be spent in procurement, but every mandatory material can also be found in the world.

---

## 2. Design principles

| Principle | How it appears in the project |
|-----------|-------------------------------|
| Incremental upgrades | Features live in `systems/` modules; `main.py` orchestrates screens rather than owning all logic |
| One authoritative inventory | Material quantities live in central inventory stock; workbenches and shop read/write the same data |
| Mission sequence only | Mission 1 → 2 → 3 unlock by completion; research clearance does not gate starts |
| Current-mission materials | World caches and shop catalogue show only the active mission’s kit |
| Teach before testing | Research Terminal uses intro → visual → guide → practice → questions → result |
| Procedural fallbacks | Missing PNGs fall back to drawn shapes so the game always runs |
| Persist safely | Saves go to platform AppData (not only the project folder); tests use temp dirs |

---

## 3. How to run

```bash
cd C:\MarsMission
python main.py
```

**Requirements:** Python 3.10+ and Pygame CE (e.g. `pygame-ce`).

**Useful environment variables:**

| Variable | Purpose |
|----------|---------|
| `MARS_MISSION_SAVE_DIR` | Override save folder (used by automated tests) |
| `MARS_DEBUG_WORKBENCH` | Set to `1` for workbench inventory diagnostics on stdout |
| `SDL_VIDEODRIVER=dummy` | Headless runs for tests |

**Live campaign save (Windows):**  
`%LOCALAPPDATA%\MarsMission\campaign_save.json`

---

## 4. High-level architecture

```
main.py                     Entry point, screen loop, input, timers, campaign glue
systems/                    Feature modules (campaign, challenges, research, rover, …)
assets/                     Sprites, research data, audio (optional; procedural fallbacks)
save_data/                  Legacy / copy of saves (authoritative path is AppData)
tests/                      Unit tests and smoke tools
backups/                    In-repo historical backups (do not treat as live code)
```

### Main loop role (`main.py`)

`main.py` owns:

- Window creation (1280×720), clock at 60 FPS
- Screen state machine (`SCREEN_TITLE`, `SCREEN_BASE`, challenge screens, research, shop, …)
- Player exploration on the base map (astronaut + camera + colony)
- Starting / completing challenges and awarding campaign mission progress
- Persist / load via `systems.savegame` + `systems.campaign`

Challenge-specific logic is delegated to:

- `systems.challenges_ch1` — antenna mission  
- `systems.challenges_ch2` — power mission  
- `systems.challenges_ch3` — rover mission (+ rover_* modules for driving)

---

## 5. Player journey (end-to-end)

```
Title → Briefing → Mars Base (open world)
    │
    ├─ Explore, collect supply caches (E)
    ├─ Optional: Research Terminal (earn RP)
    ├─ Optional: Procurement (spend RP on current-mission kit)
    ├─ Optional: Outpost dashboard (power / life support / greenhouse context)
    │
    ├─ Mission Prep (materials required; research optional)
    │
    ├─ Mission 1: Diagnose → Assemble → Radar → Brief/Practice → Timed Align → Complete
    │       unlocks Mission 2 materials + research tier
    │
    ├─ Mission 2: Intro → Wire circuit → Power allocation → Complete
    │       unlocks Mission 3 materials
    │
    └─ Mission 3: Intro → Scan (B2) → Diagnose → Repair → Route → Drive → Rescue → Complete
            campaign finished
```

---

## 6. Campaign system

**Module:** `systems/campaign.py`  
**UI:** `systems/campaign_ui.py`  
**Persistence:** `systems/savegame.py`

### Missions

| ID | Name | Challenge | Required materials |
|----|------|-----------|-------------------|
| `mission_1` | Communication Blackout | CH1 | copper_wire, signal_amplifier, spare_fuse |
| `mission_2` | Shelter Power Emergency | CH2 | insulated_cable, spare_fuse |
| `mission_3` | Rover Rescue | CH3 | servo_motor, battery_cell, lubricant, metal_bracket |

### Unlock rule (critical)

**Only completing the current mission unlocks the next.**  
Research completion, RP totals, and full kit purchases are **not** unlock conditions.

### Mission start readiness

`mission_readiness()` checks:

- Mission is unlocked and not already completed
- Required kit materials are owned in inventory

Research “clearance” is still tracked for optional RP/discovery messaging, but **does not block Start**.

### Two currencies

| Currency | Earned by | Spent on |
|----------|-----------|----------|
| **Mission Score** | Completing a mission once | Nothing (record / progress) |
| **Research Points (RP)** | Completing research tasks once | Procurement of current-mission supplies |

RP is never required to finish the campaign if the player collects world caches.

---

## 7. Open-world base

**Modules:** `colony.py`, `player.py`, `camera.py`, `collision.py`, `interactions.py`, `hud_explore.py`, `minimap.py`, `guidance.py`, `scanner.py`, `tutorials.py`

The base map is a large top-down world with zones (communication, habitat, energy, rover, research). The player:

- Moves with WASD / arrows
- Interacts with stations and pickups using **E**
- Opens inventory (**I**) and journal (**J**)
- Follows optional guidance arrows toward the next objective

**World supply caches** (`systems/caches.py`):

- Seeded per campaign (`campaign_seed`) so positions are stable across restarts
- Generated for the **active** mission only
- Deactivated when that mission completes; next mission’s caches appear after unlock
- Guarantees at least one world unit of each mandatory kit item (avoids softlock without research)

---

## 8. Materials, inventory, and procurement

### Materials (`systems/materials.py`)

Canonical catalog with stable IDs (not display-name matching), for example:

- Electrical: `copper_wire`, `signal_amplifier`, `spare_fuse`, `insulated_cable`, `battery_cell`
- Mechanical: `servo_motor`, `lubricant`, `metal_bracket`
- Optional clue: `research_log`

Quantities use `{ qty, reserved }`:

- **qty** — owned count  
- **reserved** — installed on a workbench but not yet committed  
- **available** = qty − reserved  

Successful challenge completion **commits** reserved parts (consumes them). Undo / reset **releases** reservation back to available.

### Inventory (`systems/inventory.py`)

Central inventory object used by exploration, shop, and all three challenge workbenches.

### Procurement (`systems/procurement.py`)

Store rules:

1. Item belongs to the **current** mission kit only  
2. Player has enough RP  
3. Purchase cannot exceed remaining deficit (“Required quantity secured.”)  
4. Insufficient RP shows: *Complete an optional research activity to earn more.*  

Future-mission items are hidden from the active catalogue.

---

## 9. Research Terminal (optional STEM layer)

**Modules:** `research_terminal.py`, `research_tasks.py`, `research_data.py`  
**Data:** `assets/research_data/` + `research_manifest.json`

### Flow per activity

```
Research Home
  → Introduction
  → Visual learning (NASA browse image / chart when available)
  → Guided explanation
  → Interactive practice (no RP yet)
  → MCQ / research task(s)
  → Feedback + RP reward (once)
```

### Navigation

- **RESEARCH HOME** — back to the activity list (preserves completion/RP)  
- **RETURN TO BASE** — closes the terminal and returns to the open world  

These are separate actions.

### Completion rules

- Stable task IDs (e.g. `res_1a_hirise`)  
- Completed tasks leave the **available** list; may appear under completed history  
- Incorrect answers remain retryable  
- RP awarded **once** per task ID  

### Image handling

Paths resolve from the **project root**, not the shell CWD. Only real image extensions load; JSON timelines (e.g. MEDA) are treated as non-image data with honest fallbacks. Diagnostic tool: `tests/tools_research_image_report.py`.

Example datasets: HiRISE dunes/craters, MOLA context, THEMIS thermal, Perseverance surface, solar dust context.

---

## 10. Challenge 1 — Communication Blackout

**Module:** `systems/challenges_ch1.py` (+ `antenna_tutorial.py` for briefing/practice)

| Stage | What happens |
|-------|----------------|
| Diagnose | Inspect antenna symptom panels |
| Assemble | Workbench: copper coil, amplifier, fuse + cable link |
| Radar | Identify SAT-02 among tracks |
| Brief / Practice | Untimed antenna pointing tutorial (forgiving ±10° zone) |
| Ready | Confirm before starting the timer |
| Align | **120 s** timed calibration; hold stable signal; collect packets |
| Complete / Timeout | Score once; return to base |

**Workbench:** shared `systems/workbench.py` (select supply → compatible slot → install).

---

## 11. Challenge 2 — Shelter Power Emergency

**Module:** `systems/challenges_ch2.py`

| Stage | What happens |
|-------|----------------|
| Intro | Power failure story |
| Wire | Build circuit links; install fuse / insulated cable usage |
| Power | Allocate an **80-unit** budget across life / food / comms |
| Complete | Bonuses can feed outpost systems; timer **90 s** while active |

Food freshness decays if cold storage is under-powered — teaching energy trade-offs.

---

## 12. Challenge 3 — Rover Rescue

**Modules:** `challenges_ch3.py` plus dedicated rover stack:

| Module | Role |
|--------|------|
| `rover_physics.py` | Velocity-based driving (accel, brake, reverse, steering, lateral grip) |
| `rover_terrain.py` | Firm / sand / rocky / crater world (2400×1500) |
| `rover_renderer.py` | Procedural or sprite top-down rover; rotation cache |
| `rover_effects.py` | Wheel dust, tyre tracks, storm particles |
| `rover_navigation.py` | Waypoints, camera follow, driving HUD, minimap |

### Stage flow

1. **Scan** — find strongest signal cell **B2** (wrong guess: −5 s)  
2. **Diagnose** — rover fault panels  
3. **Repair workbench** — install servo motor, battery cell, lubricant, metal bracket  
4. **Route planning** — Safe / Direct / Shortcut (descriptions match real terrain density)  
5. **Drive** — physics driving with storm intensity rising over the shared **120 s** timer  
6. **Rescue** — press **E** inside the rescue radius  

### Driving controls

| Key | Action |
|-----|--------|
| W / ↑ | Accelerate |
| S / ↓ | Brake / reverse |
| A / ← | Steer left |
| D / → | Steer right |
| SPACE | Handbrake |
| E | Rescue (only in zone) |

Terrain changes grip, dust, and vibration. Solid rocks collide; decorative rocks do not. Camera follows with look-ahead. Storm haze increases but keeps nearby obstacles readable.

### Workbench supplies panel

Required Mission 3 parts are listed first with statuses:

- `N available / 1 required`  
- `INSTALLED`  
- `0 available / 1 required`  

Mission 1/2 leftovers appear under expandable **Other Supplies** so they cannot clip required rows off-screen.

---

## 13. Outpost systems

**Modules:** `outpost.py`, `outpost_ui.py`, `mission_debrief.py`

After missions (especially Mission 2), the outpost dashboard can reflect:

- Power budget / life support  
- Radiation / shielding context  
- Greenhouse / food production hooks  

Debrief screens summarize consequences without rewriting challenge success conditions.

---

## 14. UI language

**Modules:** `challenge_ui.py`, `hud_explore.py`, `notify.py`, `campaign_ui.py`

Shared visual language: dimmed backdrops, panels, meters, objective bars, muted/signal/amber/green accents. Explore HUD stays screen-fixed; world content scrolls with the camera.

Assets under `assets/` are optional. `assets/MANIFEST.txt` lists expected paths; missing files use procedural drawings.

---

## 15. Save / load model

**Module:** `systems/savegame.py`

- Schema/version migration for older campaigns  
- Atomic write + `.bak` backup  
- Archive support when starting a **New Campaign**  
- Stores: mission status, RP, score, inventory stock, research completions, cache positions, outpost state, purchases  

Tests must set `MARS_MISSION_SAVE_DIR` so they never overwrite the player’s only live save.

---

## 16. Module map (systems/)

| Area | Files |
|------|-------|
| Campaign / economy | `campaign`, `campaign_ui`, `procurement`, `economy_config`, `caches`, `materials`, `inventory`, `savegame` |
| Research | `research_terminal`, `research_tasks`, `research_data` |
| Challenges | `challenges_ch1`, `challenges_ch2`, `challenges_ch3`, `workbench`, `antenna_tutorial`, `challenge_ui` |
| Rover drive | `rover_physics`, `rover_terrain`, `rover_renderer`, `rover_effects`, `rover_navigation` |
| World | `colony`, `player`, `camera`, `collision`, `interactions`, `terrain`, `particles`, `wind`, `lighting` |
| Meta UX | `guidance`, `hud_explore`, `minimap`, `tutorials`, `journal`, `scanner`, `notify`, `audio_fx` |
| Outpost | `outpost`, `outpost_ui`, `mission_debrief` |

---

## 17. Testing

Located under `tests/`.

| Suite | Focus |
|-------|--------|
| `tests_campaign_economy.py` | Save/load, RP once, procurement, readiness, caches |
| `tests_research_ux.py` | Optional research, hide completed, images, multi-question |
| `tests_workbench_m3.py` | Mission 3 supplies filter, install/undo/reset |
| `tests_rover_drive.py` | Physics, terrain, routes, rescue radius |
| `tests_antenna_tutorial.py` | Practice vs timed antenna behaviour |
| `tests_outpost.py` | Outpost migration / power hooks |
| `tools_*_smoke.py` | Broader integration smoke checks |

Example:

```bash
cd C:\MarsMission
python -m unittest tests.tests_rover_drive tests.tests_workbench_m3 -v
python tests/tools_puzzle_smoke.py
python tests/tools_campaign_smoke.py
```

*(If your environment imports tests from the project root, use the paths that match your layout — test files live in `tests/`.)*

---

## 18. Controls quick reference

### Base exploration

| Key | Action |
|-----|--------|
| WASD / Arrows | Move |
| E | Interact / collect |
| I | Inventory |
| J | Journal |
| ESC | Pause / back (context-dependent) |

### Challenges

- Workbenches: click supply → click compatible slot; right-click / Undo / Reset as shown  
- CH1 timed align: A/D or arrows rotate dish  
- CH3 drive: see section 12  

---

## 19. Educational goals

| Mission | STEM ideas |
|---------|------------|
| Communication | Antenna pointing, signal strength, satellite identification |
| Power | Circuits, energy budgets, life-support trade-offs |
| Rover | Remote sensing scan, mechanical repair, route risk, driving physics |
| Research | Real NASA instrument context (HiRISE, MOLA, MEDA, THEMIS, Perseverance) with honest attribution and no fabricated numeric science |

Language in research lessons targets Grades 5–8: short paragraphs, teach-then-test, clear feedback.

---

## 20. Important non-goals / constraints

- Do **not** treat `main_m2_backup.py` or `Mars_Survival_RPG` as part of the live game path  
- Do **not** invent NASA measurements; use curated local data or mark unavailable  
- Do **not** require research to unlock missions  
- Do **not** spawn future-mission materials early  
- Prefer extending `systems/` over rewriting `main.py` from scratch  

---

## 21. Suggested reading order for developers

1. This document  
2. `main.py` — screen constants and loop  
3. `systems/campaign.py` + `materials.py` — progression and kits  
4. `systems/challenges_ch1.py` / `_ch2.py` / `_ch3.py` — mission flows  
5. `systems/research_terminal.py` — optional STEM UX  
6. `systems/rover_*.py` — driving overhaul  
7. `assets/MANIFEST.txt` + `assets/research_data/IMPORT.md` — content packaging  

---

## 22. Version snapshot notes

As of the rover-driving and research-UX upgrades:

- Campaign schema version **3** (see `campaign.SCHEMA_VERSION`)  
- Research is lesson-first and optional  
- Mission 3 workbench shows required supplies without clipping  
- Challenge 3 drive uses a larger terrain world with velocity physics and dynamic camera  
- Backups of working trees are stored under `C:\MarsMission_Backups\` when created by milestone workflows  

---

*Document generated for the MarsMission educational game project. For launch: `python main.py` from `C:\MarsMission`.*
