"""Challenge 3 — scan → diagnose/repair → route plan → heading drive + rescue."""

from __future__ import annotations

import math
import random

import pygame

from systems import challenge_ui as ui
from systems import journal as journal_mod
from systems import materials as mats
from systems import workbench as wb

TIME_LIMIT = 120
POINTS = 100
WRONG_PENALTY = 5
CORRECT_CELL = "B2"
MAX_SPEED = 210.0
REVERSE_SPEED = 90.0
ACCEL = 160.0
BRAKE = 280.0
FRICTION = 70.0
TURN_RATE = 120.0

SIGNALS = {
    "A1": "Weak", "A2": "Weak", "A3": "Medium",
    "B1": "Weak", "B2": "Strong", "B3": "Weak",
    "C1": "Medium", "C2": "Weak", "C3": "Weak",
}

# Terrain intel per cell (shown more clearly with scan_clarity bonus)
TERRAIN_INTEL = {
    "A1": "Sand flats", "A2": "Rock field", "A3": "Rough wash",
    "B1": "Crater rim", "B2": "Clear corridor", "B3": "Dune wall",
    "C1": "Boulder cluster", "C2": "Soft sand", "C3": "Storm scar",
}

REPAIR_SLOTS = {
    "motor": {"label": "Drive Motor Bay", "needs": "servo_motor", "clue": "ch3_motor", "x": 180, "y": 220},
    "battery": {"label": "Power Cell Bay", "needs": "battery_cell", "clue": "ch3_batt", "x": 480, "y": 220},
    "wheel": {"label": "Wheel Assembly", "needs": "lubricant", "clue": "ch3_wheel", "x": 780, "y": 220},
    "bracket": {"label": "Support Mount", "needs": "metal_bracket", "clue": "ch3_wheel", "x": 480, "y": 380},
}

ROUTES = {
    "safe": {
        "name": "Safe Ridge Route",
        "risk": "Low",
        "time": "Longer",
        "desc": "Avoids crater cluster. Better traction, slower arrival.",
        "rock_scale": 0.7,
        "traction": 1.05,
    },
    "direct": {
        "name": "Direct Corridor",
        "risk": "Medium",
        "time": "Balanced",
        "desc": "Uses B2 corridor intel. Some rocks remain.",
        "rock_scale": 1.0,
        "traction": 1.0,
    },
    "shortcut": {
        "name": "Storm Scar Shortcut",
        "risk": "High",
        "time": "Shortest",
        "desc": "Cuts through rough ground. Harder steering.",
        "rock_scale": 1.35,
        "traction": 0.82,
    },
}


def make_state():
    rng = random.Random(11)
    rocks = [
        pygame.Rect(320, 420, 70, 45),
        pygame.Rect(510, 500, 90, 50),
        pygame.Rect(700, 390, 75, 48),
        pygame.Rect(880, 470, 85, 55),
        pygame.Rect(420, 300, 60, 40),
        pygame.Rect(980, 320, 70, 42),
        pygame.Rect(600, 350, 55, 40),
        pygame.Rect(250, 520, 65, 40),
    ]
    drive_dust = [
        {"x": rng.uniform(0, 1280), "y": rng.uniform(180, 700), "speed": rng.uniform(0.8, 2.5),
         "size": rng.randint(1, 4), "alpha": rng.randint(60, 160)}
        for _ in range(70)
    ]
    return {
        "time_left": float(TIME_LIMIT),
        "finish_time_left": 0.0,
        "phase": "ready",  # scan phases + diagnose/repair/route handled via screen
        "scan_angle": 0.0,
        "scan_progress": 0.0,
        "hint": "",
        "found": False,
        "symptoms_checked": [],
        "repair": {k: None for k in REPAIR_SLOTS},
        "repair_ok": False,
        "test_msg": "",
        "route": None,
        "rover_x": 100.0,
        "rover_y": 540.0,
        "heading": 0.0,
        "speed": 0.0,
        "wheel_spin": 0.0,
        "hit_timer": 0.0,
        "hit_message_timer": 0.0,
        "rescued": False,
        "points_awarded": False,
        "complete_delay": 0.0,
        "finish_storm": 0.0,
        "rocks": rocks,
        "base_rocks": [r.copy() for r in rocks],
        "drive_dust": drive_dust,
        "tracks": [],
        "target_x": 1100,
        "target_y": 480,
        "camera_x": 0.0,
        "camera_y": 0.0,
        "scan_clarity": 0.0,
        "traction_mod": 1.0,
        "selected_cell": None,
        "scanned_cells": {},  # cell -> telemetry dict after results or individual inspect
        "penalty_flash": 0.0,
        "flash_slot": None,
        "flash_timer": 0.0,
    }


def storm_intensity(ch3) -> float:
    elapsed = TIME_LIMIT - ch3["time_left"]
    return max(0.0, min(1.0, elapsed / TIME_LIMIT))


def rover_rect(ch3) -> pygame.Rect:
    return pygame.Rect(int(ch3["rover_x"]) - 40, int(ch3["rover_y"]) - 22, 80, 44)


def apply_route(ch3) -> None:
    route = ROUTES.get(ch3["route"] or "direct", ROUTES["direct"])
    ch3["traction_mod"] = route["traction"]
    scale = route["rock_scale"]
    ch3["rocks"] = []
    for r in ch3["base_rocks"]:
        if scale < 1.0 and random.Random(r.x).random() > scale:
            continue
        nr = r.copy()
        if scale > 1.0:
            nr.inflate_ip(int(8 * (scale - 1)), int(6 * (scale - 1)))
        ch3["rocks"].append(nr)
    # repair quality affects traction
    if ch3["repair_ok"]:
        ch3["traction_mod"] *= 1.08


def draw_intro(surface, fonts, mouse_pos):
    ui.dim_backdrop(surface)
    box = pygame.Rect(200, 120, 880, 460)
    ui.panel(surface, box)
    ui.header(surface, fonts, box, "ROVER SIGNAL LOST!", "Scan · Diagnose · Repair · Plan route · Drive")
    lines = [
        "Find the strong signal cell, repair the rover with collected parts,",
        "choose a rescue route, then drive and press E in the rescue zone.",
        "W/S throttle · A/D steer · wrong repairs can be corrected.",
    ]
    for i, line in enumerate(lines):
        ui.centered(surface, fonts, line, (box.centerx, 250 + i * 40), ui.C_TEXT, "body")
    btn = pygame.Rect(0, 0, 280, 54)
    btn.center = (box.centerx, 490)
    ui.button(surface, btn, "START RESCUE", fonts, mouse_pos)
    return btn


def grid_cells():
    labels = ["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3"]
    cells = {}
    start_x, start_y = 380, 180
    size, gap = 110, 16
    for i, name in enumerate(labels):
        row, col = i // 3, i % 3
        cells[name] = pygame.Rect(start_x + col * (size + gap), start_y + row * (size + gap), size, size)
    return cells


def signal_color(level: str):
    if level == "Strong":
        return ui.C_GREEN
    if level == "Medium":
        return ui.C_AMBER
    return (180, 120, 100)


def _sector_telemetry(name: str, clarity: float) -> dict:
    level = SIGNALS[name]
    conf = {"Strong": 92, "Medium": 55, "Weak": 22}[level]
    dens = {"Strong": "Low", "Medium": "Medium", "Weak": "High"}[level]
    return {
        "signal": level,
        "confidence": conf,
        "terrain": TERRAIN_INTEL[name],
        "obstacles": dens,
        "hazard": "Storm scar" if "Storm" in TERRAIN_INTEL[name] or "Crater" in TERRAIN_INTEL[name] else "Nominal",
    }


def draw_scan(surface, fonts, mouse_pos, ch3):
    ui.dim_backdrop(surface, 145)
    box = pygame.Rect(60, 30, 1160, 660)
    ui.panel(surface, box)
    ui.header(surface, fonts, box, "TERRAIN / ROVER SCAN GRID", "Columns A–C · Rows 1–3 · Inspect sectors before committing")
    ui.objective_bar(surface, fonts, "Wrong guess: −5 seconds (shown clearly). Find the STRONG rover signal.", y=105)

    cells = grid_cells()
    clarity = ch3.get("scan_clarity", 0.0)

    # Column / row labels
    ui.label(surface, fonts, "A", (380 + 55, 155), ui.C_CYAN, "body")
    ui.label(surface, fonts, "B", (380 + 55 + 126, 155), ui.C_CYAN, "body")
    ui.label(surface, fonts, "C", (380 + 55 + 252, 155), ui.C_CYAN, "body")
    ui.label(surface, fonts, "1", (340, 180 + 40), ui.C_CYAN, "body")
    ui.label(surface, fonts, "2", (340, 180 + 40 + 126), ui.C_CYAN, "body")
    ui.label(surface, fonts, "3", (340, 180 + 40 + 252), ui.C_CYAN, "body")

    if ch3["phase"] == "scanning":
        cx, cy = 560, 360
        pygame.draw.circle(surface, (20, 40, 30), (cx, cy), 200, 2)
        ang = math.radians(ch3["scan_angle"] - 90)
        pygame.draw.line(surface, ui.C_GREEN, (cx, cy), (cx + math.cos(ang) * 200, cy + math.sin(ang) * 200), 3)
        ui.meter(surface, pygame.Rect(360, 580, 400, 14), ch3["scan_progress"], 1.0, ui.C_GREEN)
        ui.centered(surface, fonts, "SECTOR SWEEP IN PROGRESS…", (560, 555), ui.C_GREEN, "body")

    for name, rect in cells.items():
        selected = ch3.get("selected_cell") == name
        scanned = ch3["phase"] in ("results",) or ch3["found"] or name in ch3.get("scanned_cells", {})
        fill = (40, 25, 18)
        border = ui.C_EDGE
        if ch3["phase"] == "scanning":
            border = ui.C_CYAN
            fill = (30, 40, 28)
        elif scanned:
            level = SIGNALS[name]
            border = signal_color(level)
            fill = (35, 28, 18)
        if selected:
            border = ui.C_CYAN
        if ch3.get("penalty_flash", 0) > 0 and selected:
            border = ui.C_RED
        pygame.draw.rect(surface, fill, rect, border_radius=10)
        pygame.draw.rect(surface, border, rect, 4 if selected else 3, border_radius=10)
        lab = fonts["body"].render(name, True, ui.C_TEXT)
        surface.blit(lab, lab.get_rect(center=(rect.centerx, rect.centery - 22)))
        if scanned:
            level = SIGNALS[name]
            lvl = fonts["small"].render(level, True, signal_color(level))
            surface.blit(lvl, lvl.get_rect(center=(rect.centerx, rect.centery + 4)))
            if clarity >= 0.25 or name in ch3.get("scanned_cells", {}):
                terr = fonts["small"].render(TERRAIN_INTEL[name][:11], True, ui.C_MUTED)
                surface.blit(terr, terr.get_rect(center=(rect.centerx, rect.centery + 28)))
            if level == "Strong":
                pygame.draw.circle(
                    surface, border, rect.center,
                    int(16 + 5 * abs(math.sin(pygame.time.get_ticks() * 0.01))), 1,
                )
        else:
            st = fonts["small"].render("UNSCANNED", True, ui.C_MUTED)
            surface.blit(st, st.get_rect(center=(rect.centerx, rect.centery + 10)))

    # Telemetry side panel
    side = pygame.Rect(860, 160, 320, 360)
    pygame.draw.rect(surface, (32, 20, 14), side, border_radius=10)
    pygame.draw.rect(surface, ui.C_CYAN, side, 2, border_radius=10)
    ui.label(surface, fonts, "SECTOR TELEMETRY", (880, 175), ui.C_CYAN, "small")
    sel = ch3.get("selected_cell")
    if sel and (ch3["phase"] == "results" or ch3["found"] or sel in ch3.get("scanned_cells", {})):
        tel = ch3.get("scanned_cells", {}).get(sel) or _sector_telemetry(sel, clarity)
        lines = [
            f"Sector: {sel}",
            f"Signal: {tel['signal']}",
            f"Confidence: {tel['confidence']}%",
            f"Terrain: {tel['terrain']}",
            f"Obstacles: {tel['obstacles']}",
            f"Hazard: {tel['hazard']}",
        ]
        for i, line in enumerate(lines):
            ui.label(surface, fonts, line, (880, 210 + i * 28), ui.C_TEXT, "small")
    else:
        ui.label(surface, fonts, "Select a scanned sector", (880, 230), ui.C_MUTED, "small")
        ui.label(surface, fonts, "to read telemetry.", (880, 258), ui.C_MUTED, "small")

    if ch3.get("penalty_flash", 0) > 0:
        ui.centered(surface, fonts, "WRONG SECTOR — 5 SECONDS LOST", (560, 140), ui.C_RED, "title")

    scan_btn = pygame.Rect(0, 0, 0, 0)
    cont = pygame.Rect(0, 0, 0, 0)
    if ch3["phase"] == "ready":
        scan_btn = pygame.Rect(0, 0, 240, 50)
        scan_btn.center = (560, 600)
        ui.button(surface, scan_btn, "SCAN GRID", fonts, mouse_pos)
    if ch3["found"]:
        ui.centered(surface, fonts, "ROVER SIGNAL LOCKED — B2", (560, 545), ui.C_GREEN, "title")
        cont = pygame.Rect(0, 0, 300, 48)
        cont.center = (560, 600)
        ui.button(surface, cont, "DIAGNOSE ROVER", fonts, mouse_pos, small=True)
    elif ch3["hint"]:
        ui.centered(surface, fonts, ch3["hint"], (560, 620), ui.C_RED, "body")

    if clarity > 0:
        ui.label(surface, fonts, f"Scan clarity boost {int(clarity * 100)}%", (100, 620), ui.C_CYAN, "small")

    return {"cells": cells, "scan_button": scan_btn, "continue": cont}


def update_scan(ch3, dt: float) -> None:
    if ch3.get("penalty_flash", 0) > 0:
        ch3["penalty_flash"] -= dt
    if ch3.get("flash_timer", 0) > 0:
        ch3["flash_timer"] -= dt
        if ch3["flash_timer"] <= 0:
            ch3["flash_slot"] = None
    if ch3["phase"] != "scanning":
        return
    ch3["scan_angle"] = (ch3["scan_angle"] + 300 * dt) % 360
    ch3["scan_progress"] += dt / 2.0
    if ch3["scan_progress"] >= 1.0:
        ch3["phase"] = "results"
        ch3["scan_progress"] = 1.0
        # Populate telemetry for all sectors after sweep
        for name in SIGNALS:
            ch3["scanned_cells"][name] = _sector_telemetry(name, ch3.get("scan_clarity", 0))


def draw_diagnose(surface, fonts, mouse_pos, ch3):
    ui.dim_backdrop(surface, 145)
    box = pygame.Rect(100, 50, 1080, 620)
    ui.panel(surface, box)
    ui.header(surface, fonts, box, "ROVER DIAGNOSTICS", "Read symptoms — answers are not listed as a recipe")
    symptoms = [
        ("motor", "Drive sluggish", "Motor bay scorched.", "ch3_motor"),
        ("batt", "Low cabin voltage", "Won't hold charge.", "ch3_batt"),
        ("wheel", "Wheel squeal / jam", "Assembly sticks under load.", "ch3_wheel"),
    ]
    buttons = {}
    for i, (key, title, body, clue) in enumerate(symptoms):
        r = pygame.Rect(180, 160 + i * 120, 920, 100)
        checked = key in ch3["symptoms_checked"]
        pygame.draw.rect(surface, (35, 22, 16), r, border_radius=10)
        pygame.draw.rect(surface, ui.C_GREEN if checked else ui.C_EDGE, r, 2, border_radius=10)
        ui.label(surface, fonts, title, (r.x + 24, r.y + 20), ui.C_AMBER if not checked else ui.C_GREEN, "body")
        ui.label(surface, fonts, body, (r.x + 24, r.y + 55), ui.C_TEXT, "small")
        buttons[key] = (r, clue)
    cont = pygame.Rect(0, 0, 0, 0)
    if len(ch3["symptoms_checked"]) >= 2:
        cont = pygame.Rect(0, 0, 300, 50)
        cont.center = (640, 600)
        ui.button(surface, cont, "OPEN REPAIR BAY", fonts, mouse_pos)
    return {"symptoms": buttons, "continue": cont}


def handle_diagnose_event(ch3, event, ui_state, journal) -> str | None:
    if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
        return None
    for key, (rect, clue) in ui_state["symptoms"].items():
        if rect.collidepoint(event.pos):
            if key not in ch3["symptoms_checked"]:
                ch3["symptoms_checked"].append(key)
                journal_mod.add_clue(journal, clue)
            return None
    if ui_state["continue"].width > 0 and ui_state["continue"].collidepoint(event.pos):
        return "repair"
    return None


def _repair_faults(ch3) -> list[str]:
    faults = []
    for key, meta in REPAIR_SLOTS.items():
        if ch3["repair"][key] != meta["needs"]:
            faults.append(f"{meta['label']}: incorrect or empty.")
    return faults


def test_repair(ch3, inventory) -> None:
    faults = _repair_faults(ch3)
    if faults:
        ch3["repair_ok"] = False
        ch3["test_msg"] = faults[0] + " Remove and retry."
        return
    ch3["repair_ok"] = True
    ch3["test_msg"] = "REPAIR PASS — rover systems responsive."
    if inventory:
        for mid in ("servo_motor", "battery_cell", "lubricant", "metal_bracket"):
            mats.commit(inventory["stock"], mid, 1)


def place_repair(ch3, slot, inventory) -> str:
    ok, msg = wb.try_install(inventory, ch3["repair"], slot, REPAIR_SLOTS[slot])
    if ok:
        ch3["repair_ok"] = False
        ch3["flash_slot"] = None
    else:
        ch3["flash_slot"] = slot
        ch3["flash_timer"] = 1.2
    return msg


def clear_repair(ch3, slot, inventory) -> None:
    wb.remove_install(inventory, ch3["repair"], slot)
    ch3["repair_ok"] = False


def draw_repair(surface, fonts, mouse_pos, ch3, inventory):
    guided = wb.is_guided()
    filled = sum(1 for v in ch3["repair"].values() if v)
    chrome = wb.draw_workbench_chrome(
        surface, fonts, mouse_pos,
        "ROVER REPAIR WORKBENCH",
        "Motor · Battery · Wheel · Bracket",
        ch3.get("test_msg") or "Select a supply, then click a compatible bay.",
        filled / 4.0,
        f"Installed {filled}/4",
        guided,
    )
    slots = {}
    for key, meta in REPAIR_SLOTS.items():
        r = pygame.Rect(meta["x"], meta["y"], 220, 110)
        flash = ch3.get("flash_slot") == key and ch3.get("flash_timer", 0) > 0
        wb.draw_slot(
            surface, fonts, r, meta["label"], ch3["repair"][key], meta["needs"],
            inventory.get("selected"), guided, mouse_pos, flash_incompatible=flash,
        )
        slots[key] = r

    supply = wb.draw_supply_panel(
        surface, fonts, inventory, mouse_pos, "ch3",
        pygame.Rect(980, 150, 240, 360),
    )
    test_btn = pygame.Rect(120, 560, 200, 48)
    undo_btn = pygame.Rect(340, 560, 160, 48)
    reset = pygame.Rect(520, 560, 140, 48)
    cont = pygame.Rect(0, 0, 0, 0)
    ui.button(surface, test_btn, "TEST REPAIR", fonts, mouse_pos)
    ui.button(surface, undo_btn, "UNDO", fonts, mouse_pos, small=True)
    ui.button(surface, reset, "RESET", fonts, mouse_pos, small=True)
    if ch3["repair_ok"]:
        cont = pygame.Rect(700, 560, 240, 48)
        ui.button(surface, cont, "PLAN ROUTE", fonts, mouse_pos)
    return {
        "slots": slots, "test": test_btn, "continue": cont, "reset": reset,
        "undo": undo_btn, "supplies": supply, "mode": chrome["mode"],
    }


def handle_repair_event(ch3, event, ui_state, inventory) -> str | None:
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
        for key, rect in ui_state.get("slots", {}).items():
            if rect.collidepoint(event.pos):
                clear_repair(ch3, key, inventory)
                ch3["test_msg"] = "Part removed."
                return None
    if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
        return None
    pos = event.pos
    if ui_state.get("mode") and ui_state["mode"].collidepoint(pos):
        wb.toggle_guided()
        return None
    if ui_state.get("supplies") and wb.handle_supply_click(inventory, ui_state["supplies"], pos):
        return None
    if ui_state["reset"].collidepoint(pos):
        wb.clear_all(inventory, ch3["repair"])
        ch3["test_msg"] = "Workbench cleared."
        ch3["repair_ok"] = False
        return None
    if ui_state.get("undo") and ui_state["undo"].collidepoint(pos):
        for key in reversed(list(ch3["repair"].keys())):
            if ch3["repair"][key]:
                clear_repair(ch3, key, inventory)
                ch3["test_msg"] = "Last part removed."
                break
        return None
    if ui_state["test"].collidepoint(pos):
        test_repair(ch3, inventory)
        return None
    if ch3["repair_ok"] and ui_state["continue"].width and ui_state["continue"].collidepoint(pos):
        return "route"
    for key, rect in ui_state.get("slots", {}).items():
        if rect.collidepoint(pos):
            ch3["test_msg"] = place_repair(ch3, key, inventory)
            return None
    return None


def draw_route(surface, fonts, mouse_pos, ch3):
    ui.dim_backdrop(surface, 145)
    box = pygame.Rect(100, 50, 1080, 620)
    ui.panel(surface, box)
    ui.header(surface, fonts, box, "RESCUE ROUTE PLANNING", "Shortest is not always safest — repair quality helps handling")
    ui.objective_bar(surface, fonts, "Choose a route, then begin driving", y=110)

    buttons = {}
    x = 140
    for key, info in ROUTES.items():
        r = pygame.Rect(x, 180, 300, 320)
        selected = ch3["route"] == key
        pygame.draw.rect(surface, (35, 22, 16), r, border_radius=12)
        pygame.draw.rect(surface, ui.C_GREEN if selected else ui.C_EDGE, r, 3, border_radius=12)
        ui.centered(surface, fonts, info["name"], (r.centerx, r.y + 40), ui.C_TEXT, "body")
        ui.centered(surface, fonts, f"Risk: {info['risk']}", (r.centerx, r.y + 100), ui.C_RED if info["risk"] == "High" else ui.C_AMBER, "body")
        ui.centered(surface, fonts, f"Time: {info['time']}", (r.centerx, r.y + 140), ui.C_CYAN, "small")
        # wrap desc
        ui.centered(surface, fonts, info["desc"][:28], (r.centerx, r.y + 200), ui.C_MUTED, "small")
        ui.centered(surface, fonts, info["desc"][28:56], (r.centerx, r.y + 226), ui.C_MUTED, "small")
        buttons[key] = r
        x += 340

    cont = pygame.Rect(0, 0, 0, 0)
    if ch3["route"]:
        cont = pygame.Rect(0, 0, 300, 50)
        cont.center = (640, 560)
        ui.button(surface, cont, "BEGIN DRIVE", fonts, mouse_pos)
    return {"routes": buttons, "continue": cont}


def handle_route_event(ch3, event, ui_state) -> str | None:
    if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
        return None
    for key, rect in ui_state["routes"].items():
        if rect.collidepoint(event.pos):
            ch3["route"] = key
            apply_route(ch3)
            return None
    if ch3["route"] and ui_state["continue"].width and ui_state["continue"].collidepoint(event.pos):
        return "drive"
    return None


def _terrain_factor(x, y) -> float:
    band = math.sin(x * 0.01) * math.cos(y * 0.012)
    if band > 0.55:
        return 0.75
    if band < -0.4:
        return 0.85
    return 1.0


def update_drive(ch3, dt: float, keys) -> None:
    if ch3["rescued"]:
        return
    if ch3["hit_timer"] > 0:
        ch3["hit_timer"] -= dt
    if ch3["hit_message_timer"] > 0:
        ch3["hit_message_timer"] -= dt

    throttle = 0.0
    if keys[pygame.K_w] or keys[pygame.K_UP]:
        throttle = 1.0
    elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
        throttle = -1.0
    steer = 0.0
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        steer = -1.0
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        steer = 1.0

    spd = abs(ch3["speed"])
    if spd > 8:
        ch3["heading"] = (ch3["heading"] + steer * TURN_RATE * (spd / MAX_SPEED) * dt) % 360

    terrain = _terrain_factor(ch3["rover_x"], ch3["rover_y"]) * ch3.get("traction_mod", 1.0)
    if ch3["hit_timer"] > 0:
        terrain *= 0.4
    if not ch3.get("repair_ok"):
        terrain *= 0.55  # unrepaired handling penalty if somehow driving

    if throttle > 0:
        ch3["speed"] += ACCEL * terrain * dt
    elif throttle < 0:
        if ch3["speed"] > 0:
            ch3["speed"] -= BRAKE * dt
        else:
            ch3["speed"] -= ACCEL * 0.6 * terrain * dt
    else:
        if ch3["speed"] > 0:
            ch3["speed"] = max(0.0, ch3["speed"] - FRICTION * dt)
        elif ch3["speed"] < 0:
            ch3["speed"] = min(0.0, ch3["speed"] + FRICTION * dt)

    max_fwd = MAX_SPEED * terrain
    max_rev = -REVERSE_SPEED * terrain
    ch3["speed"] = max(max_rev, min(max_fwd, ch3["speed"]))

    rad = math.radians(ch3["heading"])
    new_x = max(40, min(1240, ch3["rover_x"] + math.cos(rad) * ch3["speed"] * dt))
    new_y = max(300, min(680, ch3["rover_y"] + math.sin(rad) * ch3["speed"] * dt))
    test = pygame.Rect(int(new_x) - 40, int(new_y) - 22, 80, 44)
    blocked = False
    for rock in ch3["rocks"]:
        if test.colliderect(rock):
            blocked = True
            ch3["hit_timer"] = 0.45
            ch3["hit_message_timer"] = 0.8
            ch3["speed"] *= -0.25
            break
    if not blocked:
        if abs(ch3["speed"]) > 20:
            ch3["tracks"].append({"x": ch3["rover_x"], "y": ch3["rover_y"], "h": ch3["heading"], "life": 2.5})
            if len(ch3["tracks"]) > 80:
                ch3["tracks"] = ch3["tracks"][-80:]
        moved = abs(new_x - ch3["rover_x"]) + abs(new_y - ch3["rover_y"])
        ch3["rover_x"] = new_x
        ch3["rover_y"] = new_y
        ch3["wheel_spin"] += moved * 0.12

    intensity = storm_intensity(ch3)
    for p in ch3["drive_dust"]:
        p["x"] += p["speed"] * (1.0 + intensity * 2.5) + abs(ch3["speed"]) * 0.01
        p["y"] += math.sin(p["x"] * 0.02) * 0.4
        if p["x"] > 1285:
            p["x"] = -5
            p["y"] = random.uniform(180, 700)
    for tr in ch3["tracks"]:
        tr["life"] -= dt
    ch3["tracks"] = [t for t in ch3["tracks"] if t["life"] > 0]


def try_rescue(ch3) -> bool:
    if ch3["rescued"]:
        return False
    player = rover_rect(ch3)
    target = pygame.Rect(ch3["target_x"] - 30, ch3["target_y"] - 30, 140, 100)
    if player.colliderect(target):
        ch3["rescued"] = True
        ch3["finish_time_left"] = ch3["time_left"]
        ch3["finish_storm"] = storm_intensity(ch3)
        ch3["complete_delay"] = 1.3
        ch3["speed"] = 0.0
        return True
    return False


_DRIVE_BG = None


def _drive_background():
    global _DRIVE_BG
    if _DRIVE_BG is None:
        _DRIVE_BG = pygame.Surface((1280, 720))
        for y in range(0, 360):
            t = y / 360
            c = (int(255 + (160 - 255) * t), int(140 + (55 - 140) * t), int(70 + (40 - 70) * t))
            pygame.draw.line(_DRIVE_BG, c, (0, y), (1280, y))
        pygame.draw.rect(_DRIVE_BG, (190, 95, 60), (0, 360, 1280, 360))
        for cx, cy, r in ((180, 480, 40), (640, 560, 55), (980, 430, 35), (420, 640, 48)):
            pygame.draw.circle(_DRIVE_BG, (160, 80, 50), (cx, cy), r, 2)
    return _DRIVE_BG


def draw_drive(surface, ch3, fonts):
    surface.blit(_drive_background(), (0, 0))
    for tr in ch3["tracks"]:
        pygame.draw.circle(surface, (110, 55, 35), (int(tr["x"]), int(tr["y"])), 4)
    for rock in ch3["rocks"]:
        pygame.draw.ellipse(surface, (110, 55, 35), rock)
    mx, my = ch3["target_x"] + 40, ch3["target_y"] - 20
    pygame.draw.polygon(surface, ui.C_GREEN, [(mx, my - 36), (mx + 12, my), (mx - 12, my)])
    pygame.draw.circle(surface, ui.C_GREEN, (ch3["target_x"] + 40, ch3["target_y"] + 20), 70, 1)
    ui.label(surface, fonts, "RESCUE ZONE", (mx - 50, my - 58), ui.C_GREEN, "small")
    _draw_rover_body(surface, ch3["target_x"], ch3["target_y"], (180, 80, 60), True, 0.0)
    _draw_rover_body(surface, ch3["rover_x"], ch3["rover_y"], ch3["heading"], False, ch3["wheel_spin"])

    intensity = storm_intensity(ch3)
    dust = pygame.Surface((1280, 720), pygame.SRCALPHA)
    for p in ch3["drive_dust"]:
        alpha = min(220, int(p["alpha"] * (0.5 + intensity)))
        pygame.draw.circle(dust, (255, 190, 130, alpha), (int(p["x"]), int(p["y"])), p["size"] + int(intensity * 2))
    surface.blit(dust, (0, 0))
    overlay = pygame.Surface((1280, 720), pygame.SRCALPHA)
    overlay.fill((180, 90, 40, int(30 + intensity * 110)))
    surface.blit(overlay, (0, 0))

    ui.meter(surface, pygame.Rect(40, 70, 180, 12), abs(ch3["speed"]), MAX_SPEED, ui.C_CYAN)
    ui.label(surface, fonts, f"SPD {int(abs(ch3['speed']))}", (40, 48), ui.C_CYAN, "small")
    route = ROUTES.get(ch3.get("route") or "direct", ROUTES["direct"])
    ui.label(surface, fonts, f"Route: {route['name']} ({route['risk']})", (40, 95), ui.C_AMBER, "small")
    ui.centered(surface, fonts, "W/S throttle  A/D steer  |  E in rescue zone", (640, 696), ui.C_TEXT, "small")
    if ch3["hit_message_timer"] > 0:
        ui.centered(surface, fonts, "ROCK IMPACT!", (640, 100), ui.C_RED, "body")
    if ch3["rescued"]:
        ui.centered(surface, fonts, "ROVER RESCUED!", (640, 340), ui.C_GREEN, "title")

    mm = pygame.Rect(1080, 560, 160, 120)
    pygame.draw.rect(surface, (20, 12, 10), mm, border_radius=6)
    pygame.draw.rect(surface, ui.C_EDGE, mm, 1, border_radius=6)
    px = mm.x + int((ch3["rover_x"] / 1280) * mm.w)
    py = mm.y + int((ch3["rover_y"] / 720) * mm.h)
    tx = mm.x + int((ch3["target_x"] / 1280) * mm.w)
    ty = mm.y + int((ch3["target_y"] / 720) * mm.h)
    pygame.draw.circle(surface, ui.C_GREEN, (tx, ty), 4)
    pygame.draw.circle(surface, (255, 255, 255), (px, py), 4)


def _draw_rover_body(surface, x, y, heading_or_color, stranded, wheel_spin):
    if stranded is True:
        color = heading_or_color if isinstance(heading_or_color, tuple) else (180, 80, 60)
        body = pygame.Rect(int(x), int(y), 100, 40)
        pygame.draw.rect(surface, color, body, border_radius=6)
        for wx in (body.x + 18, body.x + 50, body.x + 82):
            pygame.draw.circle(surface, (40, 40, 45), (wx, body.bottom + 2), 10)
        return
    heading = float(heading_or_color)
    rad = math.radians(heading)
    cx, cy = float(x), float(y)
    pts = []
    for ox, oy in ((-40, -18), (40, -18), (40, 18), (-40, 18)):
        pts.append((cx + ox * math.cos(rad) - oy * math.sin(rad), cy + ox * math.sin(rad) + oy * math.cos(rad)))
    pygame.draw.polygon(surface, (220, 100, 50), pts)
    spin = float(wheel_spin)
    for ox, oy in ((-28, 20), (0, 20), (28, 20), (-28, -20), (0, -20), (28, -20)):
        rx = ox * math.cos(rad) - oy * math.sin(rad)
        ry = ox * math.sin(rad) + oy * math.cos(rad)
        wx, wy = int(cx + rx), int(cy + ry)
        pygame.draw.circle(surface, (35, 35, 40), (wx, wy), 7)
        tick = math.radians(spin * 40)
        pygame.draw.line(surface, (180, 180, 190), (wx, wy), (wx + int(math.cos(tick + rad) * 6), wy + int(math.sin(tick + rad) * 6)), 2)


def draw_complete(surface, fonts, mouse_pos, score, time_left, storm):
    return ui.result_panel(
        surface, fonts, mouse_pos,
        "ROVER RESCUED!",
        [
            f"Score: {score} points",
            f"Time remaining: {int(math.ceil(time_left))} seconds",
            f"Final storm intensity: {int(storm * 100)}%",
            "ROVER STATUS: RESCUED",
        ],
        ok=True,
        btn_label="RETURN TO BASE",
    )


def draw_timeout(surface, fonts, mouse_pos):
    return ui.dual_result_panel(
        surface, fonts, mouse_pos,
        "MISSION FAILED",
        ["The dust storm reached the rescue location!", "Retry — inventory and repairs can be redone."],
        ok=False,
    )
