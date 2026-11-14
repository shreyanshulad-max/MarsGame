"""Challenge 3 — scan → diagnose/repair → route plan → heading drive + rescue."""

from __future__ import annotations

import math
import random

import pygame

from systems import challenge_ui as ui
from systems import journal as journal_mod
from systems import materials as mats
from systems import rover_effects as rover_fx
from systems import rover_navigation as rover_nav
from systems import rover_physics as rover_phys
from systems import rover_renderer as rover_draw
from systems import rover_terrain as rover_terrain
from systems import workbench as wb

TIME_LIMIT = 120
POINTS = 100
WRONG_PENALTY = 5
CORRECT_CELL = "B2"
# Legacy aliases (HUD / tests) — authoritative values live in rover_physics.CONFIG
MAX_SPEED = rover_phys.CONFIG["max_forward"]
REVERSE_SPEED = rover_phys.CONFIG["max_reverse"]
ACCEL = rover_phys.CONFIG["accel"]
BRAKE = rover_phys.CONFIG["brake"]
FRICTION = rover_phys.CONFIG["coast_friction"]
TURN_RATE = rover_phys.CONFIG["steer_rate"]
RESCUE_RADIUS = 110.0

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

def _routes() -> dict:
    """Route cards derived from configured terrain/obstacle layout."""
    out = {}
    for key in ("safe", "direct", "shortcut"):
        out[key] = rover_terrain.route_summary(key)
    return out


ROUTES = _routes()


def make_state():
    rocks = rover_terrain.solid_obstacles("direct")
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
        "world_w": rover_terrain.WORLD_W,
        "world_h": rover_terrain.WORLD_H,
        "rover_x": 200.0,
        "rover_y": 1100.0,
        "heading": -25.0,
        "speed": 0.0,
        "lateral": 0.0,
        "angular_vel": 0.0,
        "wheel_spin": 0.0,
        "chassis_bob": 0.0,
        "impact_shake": 0.0,
        "hit_timer": 0.0,
        "hit_message_timer": 0.0,
        "rescued": False,
        "points_awarded": False,
        "complete_delay": 0.0,
        "finish_storm": 0.0,
        "rocks": [r.copy() for r in rocks],
        "base_rocks": [r.copy() for r in rocks],
        "decor_rocks": rover_terrain.decorative_rocks(),
        "terrain_zones": rover_terrain.default_zones(),
        "effects": rover_fx.make_effects(),
        "tracks": [],  # legacy alias; effects["tracks"] is authoritative
        "drive_dust": [],  # legacy; storm field lives in effects
        "target_x": 2100.0,
        "target_y": 450.0,
        "camera_x": 0.0,
        "camera_y": 780.0,
        "waypoints": [],
        "waypoint_index": 0,
        "terrain_label": "Firm Ground",
        "terrain_id": "firm",
        "assisted_steer": True,
        "rescue_hint": "",
        "scan_clarity": 0.0,
        "traction_mod": 1.0,
        "selected_cell": None,
        "scanned_cells": {},  # cell -> telemetry dict after results or individual inspect
        "penalty_flash": 0.0,
        "flash_slot": None,
        "flash_timer": 0.0,
        "_minimap_surf": None,
    }


def storm_intensity(ch3) -> float:
    elapsed = TIME_LIMIT - ch3["time_left"]
    return max(0.0, min(1.0, elapsed / TIME_LIMIT))


def rover_rect(ch3) -> pygame.Rect:
    return pygame.Rect(int(ch3["rover_x"]) - 36, int(ch3["rover_y"]) - 22, 72, 44)


def apply_route(ch3) -> None:
    key = ch3["route"] or "direct"
    # Refresh ROUTES from terrain so descriptions stay honest
    global ROUTES
    ROUTES = _routes()
    route = ROUTES.get(key, ROUTES["direct"])
    ch3["traction_mod"] = route["traction"]
    ch3["rocks"] = [r.copy() for r in rover_terrain.solid_obstacles(key)]
    ch3["base_rocks"] = [r.copy() for r in ch3["rocks"]]
    ch3["decor_rocks"] = rover_terrain.decorative_rocks()
    if ch3["repair_ok"]:
        ch3["traction_mod"] *= 1.08
    rover_nav.sync_waypoints(ch3)
    rover_phys.init_motion(ch3)
    ch3["effects"] = rover_fx.make_effects()
    ch3["rescue_hint"] = ""
    ch3["_minimap_surf"] = None


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
    pygame.draw.rect(surface, ui.C_BG, side, border_radius=10)
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
        pygame.draw.rect(surface, ui.C_SURFACE, r, border_radius=10)
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


def place_repair(ch3, slot, inventory) -> tuple[bool, str]:
    ok, msg = wb.try_install(inventory, ch3["repair"], slot, REPAIR_SLOTS[slot])
    if ok:
        ch3["repair_ok"] = False
        ch3["flash_slot"] = None
    else:
        ch3["flash_slot"] = slot
        ch3["flash_timer"] = 1.2
    return ok, msg


def clear_repair(ch3, slot, inventory) -> None:
    wb.remove_install(inventory, ch3["repair"], slot)
    ch3["repair_ok"] = False


def draw_repair(surface, fonts, mouse_pos, ch3, inventory):
    guided = wb.is_guided()
    # Progress from validated installed slots only
    filled = sum(1 for key, meta in REPAIR_SLOTS.items() if ch3["repair"].get(key) == meta["needs"])
    if not ch3.get("_wb_diag_logged"):
        wb.log_workbench_diagnostics("ch3", inventory, ch3.get("repair"), reason="ch3_repair_open")
        ch3["_wb_diag_logged"] = True
    hint = ch3.get("test_msg") or (
        "Select a compatible component slot to install this material."
        if inventory.get("selected")
        else "Select a supply, then click a compatible bay."
    )
    chrome = wb.draw_workbench_chrome(
        surface, fonts, mouse_pos,
        "ROVER REPAIR WORKBENCH",
        "Motor · Battery · Wheel · Bracket",
        hint,
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

    # Taller panel so all 4 required Mission 3 materials fit without scrolling
    supply = wb.draw_supply_panel(
        surface, fonts, inventory, mouse_pos, "ch3",
        pygame.Rect(980, 130, 250, 420),
        slots_state=ch3.get("repair"),
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
            _ok, ch3["test_msg"] = place_repair(ch3, key, inventory)
            return None
    return None


def draw_route(surface, fonts, mouse_pos, ch3):
    ui.dim_backdrop(surface, 145)
    box = pygame.Rect(60, 40, 1160, 640)
    ui.panel(surface, box)
    ui.header(surface, fonts, box, "RESCUE ROUTE PLANNING", "Inspect the map — both routes are completable")
    ui.objective_bar(surface, fonts, "Choose a route, then begin driving", y=100)

    # Terrain preview map
    preview = rover_terrain.build_minimap_surface(420, 260)
    map_rect = pygame.Rect(100, 150, 420, 260)
    pygame.draw.rect(surface, ui.C_BG, map_rect, border_radius=8)
    surface.blit(pygame.transform.smoothscale(preview, (map_rect.w - 8, map_rect.h - 8)), (map_rect.x + 4, map_rect.y + 4))
    # Launch + destination markers
    sx = map_rect.x + 4 + int(200 / rover_terrain.WORLD_W * (map_rect.w - 8))
    sy = map_rect.y + 4 + int(1100 / rover_terrain.WORLD_H * (map_rect.h - 8))
    tx = map_rect.x + 4 + int(2100 / rover_terrain.WORLD_W * (map_rect.w - 8))
    ty = map_rect.y + 4 + int(450 / rover_terrain.WORLD_H * (map_rect.h - 8))
    pygame.draw.circle(surface, (255, 255, 255), (sx, sy), 5)
    pygame.draw.circle(surface, ui.C_GREEN, (tx, ty), 6)
    ui.label(surface, fonts, "Launch", (sx + 8, sy - 8), ui.C_TEXT, "small")
    ui.label(surface, fonts, "Rescue", (tx - 40, ty - 18), ui.C_GREEN, "small")
    ui.label(surface, fonts, "Firm · Sand · Rocky · Crater", (100, 420), ui.C_MUTED, "small")

    buttons = {}
    y = 150
    for key in ("safe", "direct", "shortcut"):
        info = ROUTES[key]
        r = pygame.Rect(560, y, 580, 100)
        selected = ch3["route"] == key
        pygame.draw.rect(surface, ui.C_SURFACE, r, border_radius=10)
        pygame.draw.rect(surface, ui.C_GREEN if selected else ui.C_EDGE, r, 2, border_radius=10)
        ui.label(surface, fonts, info["name"], (r.x + 16, r.y + 12), ui.C_TEXT, "body")
        risk_col = ui.C_RED if info["risk"] == "High" else (ui.C_AMBER if info["risk"] == "Medium" else ui.C_GREEN)
        ui.label(surface, fonts, f"Risk {info['risk']} · {info['time']} · Obstacles {info.get('obstacle_count', '?')}", (r.x + 16, r.y + 42), risk_col, "small")
        ui.label(surface, fonts, info["desc"][:70], (r.x + 16, r.y + 66), ui.C_MUTED, "small")
        buttons[key] = r
        y += 112

    cont = pygame.Rect(0, 0, 0, 0)
    if ch3["route"]:
        cont = pygame.Rect(0, 0, 300, 50)
        cont.center = (640, 620)
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


def update_drive(ch3, dt: float, keys) -> None:
    if ch3["rescued"]:
        rover_fx.update(ch3, dt, storm_intensity(ch3))
        return

    throttle = 0.0
    if keys[pygame.K_w] or keys[pygame.K_UP]:
        throttle = 1.0
    elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
        throttle = -1.0
    steer = 0.0
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        steer -= 1.0
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        steer += 1.0
    handbrake = bool(keys[pygame.K_SPACE])

    props = rover_terrain.sample(
        ch3["rover_x"], ch3["rover_y"], ch3.get("terrain_zones")
    )
    # Smooth label transitions
    if props["id"] != ch3.get("terrain_id"):
        ch3["terrain_id"] = props["id"]
        ch3["terrain_label"] = props["label"]
    else:
        ch3["terrain_label"] = props["label"]

    target = (ch3["target_x"], ch3["target_y"])
    ev = rover_phys.step(
        ch3,
        dt,
        throttle,
        steer,
        handbrake,
        props,
        float(ch3.get("world_w", rover_terrain.WORLD_W)),
        float(ch3.get("world_h", rover_terrain.WORLD_H)),
        ch3.get("rocks") or [],
        target=target,
    )
    intensity = storm_intensity(ch3)
    if ev.get("hit"):
        rover_fx.emit_impact(ch3)
    rover_fx.emit_motion(ch3, props, float(ev.get("moved_px", 0.0)), intensity, dt)
    rover_fx.update(ch3, dt, intensity)
    rover_nav.update_waypoint_progress(ch3)
    rover_nav.update_camera(ch3, dt)

    # Clear stale rescue hint after a moment
    if ch3.get("rescue_hint") and ch3.get("hit_message_timer", 0) <= 0:
        # keep hint until next E / success — fade via distance UI instead
        pass


def try_rescue(ch3) -> bool:
    if ch3["rescued"]:
        return False
    dist = rover_nav.distance_to(ch3, ch3["target_x"], ch3["target_y"])
    if dist > RESCUE_RADIUS:
        ch3["rescue_hint"] = "Move closer to the stranded rover."
        return False
    ch3["rescued"] = True
    ch3["rescue_hint"] = ""
    ch3["finish_time_left"] = ch3["time_left"]
    ch3["finish_storm"] = storm_intensity(ch3)
    ch3["complete_delay"] = 1.6
    ch3["speed"] = 0.0
    ch3["lateral"] = 0.0
    return True


def draw_drive(surface, ch3, fonts):
    intensity = storm_intensity(ch3)
    cam = (float(ch3.get("camera_x", 0.0)), float(ch3.get("camera_y", 0.0)))
    world_w = int(ch3.get("world_w", rover_terrain.WORLD_W))
    world_h = int(ch3.get("world_h", rover_terrain.WORLD_H))

    rover_draw.draw_world_ground(surface, cam, world_w, world_h)

    # Solid obstacles
    for rock in ch3.get("rocks") or []:
        r = pygame.Rect(int(rock.x - cam[0]), int(rock.y - cam[1]), rock.w, rock.h)
        if r.right < 0 or r.left > 1280 or r.bottom < 0 or r.top > 720:
            continue
        pygame.draw.ellipse(surface, (95, 48, 30), r)
        pygame.draw.ellipse(surface, (60, 30, 20), r, 2)

    # Decorative rocks (no collision)
    for d in ch3.get("decor_rocks") or []:
        sx, sy = int(d["x"] - cam[0]), int(d["y"] - cam[1])
        if -30 <= sx <= 1310 and -30 <= sy <= 750:
            pygame.draw.circle(surface, (120, 65, 40), (sx, sy), d["r"])

    # Rescue zone
    tx = ch3["target_x"] - cam[0]
    ty = ch3["target_y"] - cam[1]
    pygame.draw.circle(surface, ui.C_GREEN, (int(tx), int(ty)), int(RESCUE_RADIUS), 2)
    ui.label(surface, fonts, "RESCUE ZONE", (int(tx) - 48, int(ty) - int(RESCUE_RADIUS) - 22), ui.C_GREEN, "small")

    rover_fx.draw_world(surface, ch3, cam)

    # Stranded rover
    rover_draw.draw_rover(
        surface, ch3["target_x"], ch3["target_y"], 200.0,
        stranded=True, camera=cam,
    )
    # Player rover
    headlights = intensity > 0.35
    rover_draw.draw_rover(
        surface,
        ch3["rover_x"],
        ch3["rover_y"],
        ch3["heading"],
        wheel_spin=ch3.get("wheel_spin", 0.0),
        chassis_bob=ch3.get("chassis_bob", 0.0),
        headlights=headlights,
        camera=cam,
    )

    rover_nav.draw_nav_arrow(surface, fonts, ch3, cam)
    rover_fx.draw_storm_screen(surface, ch3, intensity)
    rover_nav.draw_hud(surface, fonts, ch3, intensity)


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
