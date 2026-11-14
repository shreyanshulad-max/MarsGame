"""Challenge 1 — diagnose → assemble → radar identify SAT-02 → calibrate packets."""

from __future__ import annotations

import math
import random

import pygame

from systems import challenge_ui as ui
from systems import journal as journal_mod
from systems import materials as mats
from systems import workbench as wb

TIME_LIMIT = 120          # timed calibration only (briefing/practice do not use this)
POINTS = 100
# Timed mission starts near the target so new players are not lost
START_ANGLE = 5
PRACTICE_START_ANGLE = -10
TARGET_ANGLE = 20
STEP = 5
FINE_STEP = 2             # finer nudge when already near the stable zone
STABLE_ZONE_DEG = 10      # forgiving window (was exact 0.1°)
PACKETS_NEEDED = 3

# Correct assembly recipe (deterministic)
SLOTS = {
    "coil": {"label": "Copper Coil Slot", "needs": "copper_wire", "x": 220, "y": 260},
    "amp": {"label": "Amplifier Bay", "needs": "signal_amplifier", "x": 480, "y": 260},
    "fuse": {"label": "Fuse Socket", "needs": "spare_fuse", "x": 740, "y": 260},
}
# Cable ports on board: amp_out -> antenna_in
PORTS = {
    "amp_out": (560, 380),
    "antenna_in": (720, 380),
}


def make_state():
    return {
        "phase": "diagnose",  # diagnose -> assemble -> radar -> briefing/practice/ready -> align -> packets -> done
        "time_left": float(TIME_LIMIT),
        "finish_time_left": 0,
        "timer_running": False,  # countdown only during timed calibration
        "align_mode": "none",  # none | practice | timed
        "practice_step": "adjust",
        "practice_moved": False,
        "practice_saw_signal": False,
        "practice_stable_once": False,
        "hint": "Inspect the damaged antenna. Read symptoms, then collect parts if needed.",
        "symptoms_checked": [],
        "assembly": {"coil": None, "amp": None, "fuse": None},  # material ids placed
        "cable_ok": False,
        "dragging_cable": False,
        "drag_pos": (0, 0),
        "tested": False,
        "test_msg": "",
        "assembly_ok": False,
        "scan_angle": 0.0,
        "scan_progress": 0.0,
        "frequency": 50,
        "gain": 40,
        "tracks": {"SAT-01": 0, "SAT-02": 0, "SAT-03": 0},
        "identified": None,
        "telemetry": [],
        "antenna_angle": START_ANGLE,
        "packets": 0,
        "packet_timer": 0.0,
        "interference": 0.0,
        "interference_cd": 2.5,
        "points_awarded": False,
        "connection_restored": False,
        "restore_delay": 0.0,
        "pulse": 0.0,
        "align_feedback": "",
        "signal_band": "LOW SIGNAL",
        "flash_slot": None,
        "flash_timer": 0.0,
        "tracked": None,
    }


def signal_strength(angle: float) -> float:
    """0–100 strength. Soft falloff so the stable zone is readable."""
    distance = abs(angle - TARGET_ANGLE)
    # Inside stable zone: stay high (88–100)
    if distance <= STABLE_ZONE_DEG:
        return max(88.0, 100.0 - distance * 1.2)
    return max(0.0, 88.0 - (distance - STABLE_ZONE_DEG) * 2.5)


def angle_error(angle: float) -> float:
    return abs(float(angle) - TARGET_ANGLE)


def is_stable(angle: float) -> bool:
    return angle_error(angle) <= STABLE_ZONE_DEG


def signal_band(angle: float, interference: float = 0.0) -> str:
    if interference > 0:
        return "LOW SIGNAL"
    err = angle_error(angle)
    if err <= STABLE_ZONE_DEG * 0.35:
        return "STABLE SIGNAL"
    if err <= STABLE_ZONE_DEG:
        return "STABLE SIGNAL"
    if err <= STABLE_ZONE_DEG * 2.5:
        return "IMPROVING SIGNAL"
    return "LOW SIGNAL"


def current_step_size(ch1: dict) -> int:
    """5° normally; finer 2° steps once inside / near the stable zone."""
    if is_stable(ch1["antenna_angle"]) or angle_error(ch1["antenna_angle"]) <= STABLE_ZONE_DEG + 5:
        return FINE_STEP
    return STEP


def satellites():
    return [
        {"id": "SAT-01", "healthy": True, "base": 78, "ang": 40, "pattern": "steady", "color": (90, 200, 255)},
        {"id": "SAT-02", "healthy": False, "base": 42, "ang": 125, "pattern": "flicker", "color": (255, 190, 70)},
        {"id": "SAT-03", "healthy": True, "base": 70, "ang": 250, "pattern": "steady", "color": (140, 230, 160)},
    ]


def rotate_antenna(ch1, direction: int) -> None:
    if ch1["connection_restored"] or ch1["phase"] not in ("align", "packets"):
        return
    step = current_step_size(ch1)
    ch1["antenna_angle"] += direction * step
    ch1["antenna_angle"] = max(-60, min(60, ch1["antenna_angle"]))
    dist = ch1["antenna_angle"] - TARGET_ANGLE
    band = signal_band(ch1["antenna_angle"], ch1.get("interference", 0))
    ch1["signal_band"] = band
    if band == "STABLE SIGNAL":
        ch1["align_feedback"] = f"STABLE — hold steady (angle {ch1['antenna_angle']:+d}°, target {TARGET_ANGLE:+d}°)."
    elif dist < 0:
        ch1["align_feedback"] = f"Too low — turn RIGHT to strengthen the signal ({band})."
    else:
        ch1["align_feedback"] = f"Too high — turn LEFT to strengthen the signal ({band})."
    if ch1.get("align_mode") == "practice":
        from systems import antenna_tutorial as atut

        atut.advance_practice_on_rotate(ch1)


def _assembly_faults(ch1) -> list[str]:
    faults = []
    a = ch1["assembly"]
    if a["coil"] != "copper_wire":
        faults.append("COIL_OPEN: copper path incomplete.")
    if a["amp"] != "signal_amplifier":
        faults.append("WEAK_GAIN: amplifier missing — returns will stay faint.")
    if a["fuse"] != "spare_fuse":
        faults.append("POWER_FAULT: fuse missing — bus trips on load.")
    if not ch1["cable_ok"]:
        faults.append("LINK_ERROR: amplifier output not linked to antenna input.")
    return faults


def test_assembly(ch1, inventory) -> None:
    faults = _assembly_faults(ch1)
    ch1["tested"] = True
    if faults:
        ch1["assembly_ok"] = False
        ch1["test_msg"] = faults[0]
        ch1["hint"] = "Test failed. Remove wrong parts or fix the cable, then test again."
    else:
        ch1["assembly_ok"] = True
        ch1["test_msg"] = "ASSEMBLY PASS — antenna hardware ready."
        ch1["hint"] = "Hardware ready. Continue to radar investigation."
        if inventory:
            for mid in ("copper_wire", "signal_amplifier", "spare_fuse"):
                mats.commit(inventory["stock"], mid, 1)


def place_in_slot(ch1, slot: str, inventory) -> str:
    """Click-to-install: rejects incompatible parts without consuming them."""
    if ch1["assembly_ok"]:
        return "Assembly already passed — clear the board to change parts."
    ok, msg = wb.try_install(inventory, ch1["assembly"], slot, SLOTS[slot])
    if ok:
        ch1["tested"] = False
        ch1["assembly_ok"] = False
        ch1["flash_slot"] = None
    else:
        ch1["flash_slot"] = slot
        ch1["flash_timer"] = 1.2
    return msg


def clear_slot(ch1, slot: str, inventory) -> None:
    wb.remove_install(inventory, ch1["assembly"], slot)
    ch1["tested"] = False
    ch1["assembly_ok"] = False


def update(ch1, dt: float, active_radar: bool, active_align: bool) -> None:
    ch1["pulse"] += dt
    if ch1.get("flash_timer", 0) > 0:
        ch1["flash_timer"] -= dt
        if ch1["flash_timer"] <= 0:
            ch1["flash_slot"] = None
    sats = satellites()

    if active_radar and ch1["phase"] == "scanning":
        ch1["scan_angle"] = (ch1["scan_angle"] + 220 * dt) % 360
        ch1["scan_progress"] = min(1.0, ch1["scan_progress"] + dt / 2.4)
        freq_bonus = max(0.25, 1.0 - abs(ch1["frequency"] - 62) / 80.0)
        beam = ch1["scan_angle"]
        for sat in sats:
            diff = abs((beam - sat["ang"] + 180) % 360 - 180)
            if diff < 12:
                strength = sat["base"] * freq_bonus * (0.6 + ch1["gain"] / 200)
                if sat["pattern"] == "flicker":
                    strength *= 0.55 + 0.45 * abs(math.sin(ch1["pulse"] * 6))
                # Without amp assembly, weaken tracks
                if not ch1.get("assembly_ok"):
                    strength *= 0.35
                ch1["tracks"][sat["id"]] = min(100, ch1["tracks"][sat["id"]] + strength * dt * 1.8)
                if len(ch1["telemetry"]) < 10 and random.random() < 0.1:
                    note = f"{sat['id']} return {int(ch1['tracks'][sat['id']])}%"
                    if sat["pattern"] == "flicker":
                        note += " FLICKER"
                    else:
                        note += " STEADY"
                    ch1["telemetry"].append(note)
        if ch1["scan_progress"] >= 1.0:
            ch1["phase"] = "track"
            ch1["hint"] = "Compare telemetry. Find the flickering weak relay."

    if active_align and ch1["phase"] in ("align", "packets"):
        practice = ch1.get("align_mode") == "practice"
        # Interference only during timed mission
        if not practice:
            ch1["interference_cd"] -= dt
            if ch1["interference_cd"] <= 0 and ch1["interference"] <= 0:
                ch1["interference"] = random.uniform(0.8, 1.4)
                ch1["interference_cd"] = random.uniform(5.0, 8.0)
            if ch1["interference"] > 0:
                ch1["interference"] -= dt
                ch1["align_feedback"] = "Interference — wait briefly, then re-enter the stable zone."

        strength = signal_strength(ch1["antenna_angle"])
        if ch1["interference"] > 0:
            strength *= 0.45
        band = signal_band(ch1["antenna_angle"], ch1.get("interference", 0))
        ch1["signal_band"] = band
        stable = is_stable(ch1["antenna_angle"]) and ch1["interference"] <= 0

        if practice:
            # Practice never awards mission completion / packets permanently
            if stable and ch1.get("practice_step") != "success":
                ch1["practice_stable_once"] = True
                ch1["practice_step"] = "success"
                ch1["hint"] = "Good work! You established a stable test connection."
                ch1["align_feedback"] = "PRACTICE COMPLETE — stable test link."
        else:
            if ch1["phase"] == "align" and stable and strength >= 85:
                ch1["phase"] = "packets"
                ch1["hint"] = "STABLE lock — hold to capture transmission packets."
            if ch1["phase"] == "packets":
                good = stable and strength >= 80
                if good:
                    ch1["packet_timer"] += dt
                    if ch1["packet_timer"] >= 0.7:
                        ch1["packet_timer"] = 0.0
                        ch1["packets"] = min(PACKETS_NEEDED, ch1["packets"] + 1)
                        ch1["hint"] = f"Packet {ch1['packets']}/{PACKETS_NEEDED} acquired."
                        ch1["signal_band"] = "STABLE SIGNAL"
                else:
                    ch1["packet_timer"] = max(0.0, ch1["packet_timer"] - dt * 0.4)
                if ch1["packets"] >= PACKETS_NEEDED and not ch1["connection_restored"]:
                    ch1["connection_restored"] = True
                    ch1["restore_delay"] = 1.1
                    ch1["finish_time_left"] = ch1["time_left"]
                    ch1["timer_running"] = False
                    ch1["signal_band"] = "COMMUNICATION ESTABLISHED"
                    ch1["hint"] = "CONNECTION RESTORED"

    if ch1["connection_restored"] and ch1["restore_delay"] > 0:
        ch1["restore_delay"] -= dt


# ---- Drawing / events ----

def draw_diagnose(surface, fonts, mouse_pos, ch1, journal):
    ui.dim_backdrop(surface, 145)
    box = pygame.Rect(80, 40, 1120, 640)
    ui.panel(surface, box)
    ui.header(surface, fonts, box, "COMMUNICATION BLACKOUT — DIAGNOSTICS", "Observe symptoms. Clues are recorded in your journal (J).")
    ui.objective_bar(surface, fonts, "Inspect each symptom panel, then begin repair assembly", y=110)

    symptoms = [
        ("weak", "Weak signal", "Uplink amplitude is low.", "ch1_symptom_weak"),
        ("power", "Unstable power", "Bus voltage dips under load.", "ch1_symptom_power"),
        ("inter", "Interference", "Noise spikes on the feed.", "ch1_sat_note"),
        ("coil", "Open coil path", "Continuity check failed.", "ch1_symptom_coil"),
    ]
    buttons = {}
    for i, (key, title, body, clue) in enumerate(symptoms):
        r = pygame.Rect(140 + (i % 2) * 500, 180 + (i // 2) * 160, 440, 130)
        checked = key in ch1["symptoms_checked"]
        pygame.draw.rect(surface, ui.C_SURFACE, r, border_radius=12)
        pygame.draw.rect(surface, ui.C_GREEN if checked else ui.C_EDGE, r, 2, border_radius=12)
        ui.label(surface, fonts, title, (r.x + 20, r.y + 20), ui.C_AMBER if not checked else ui.C_GREEN, "body")
        ui.label(surface, fonts, body, (r.x + 20, r.y + 55), ui.C_TEXT, "small")
        ui.label(surface, fonts, "CLICK TO INSPECT" if not checked else "LOGGED", (r.x + 20, r.y + 90), ui.C_CYAN, "small")
        buttons[key] = (r, clue)

    cont = pygame.Rect(0, 0, 0, 0)
    if len(ch1["symptoms_checked"]) >= 3:
        cont = pygame.Rect(0, 0, 320, 50)
        cont.center = (640, 620)
        ui.button(surface, cont, "BEGIN ASSEMBLY", fonts, mouse_pos)
        ui.centered(surface, fonts, "Enough symptoms logged. Build the repair.", (640, 575), ui.C_GREEN, "body")
    else:
        ui.centered(surface, fonts, f"Inspected {len(ch1['symptoms_checked'])}/3+ panels", (640, 600), ui.C_MUTED, "body")
    return {"symptoms": buttons, "continue": cont}


def handle_diagnose_event(ch1, event, ui_state, journal) -> str | None:
    if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
        return None
    for key, (rect, clue) in ui_state["symptoms"].items():
        if rect.collidepoint(event.pos):
            if key not in ch1["symptoms_checked"]:
                ch1["symptoms_checked"].append(key)
                journal_mod.add_clue(journal, clue)
                ch1["hint"] = journal_mod.CLUES[clue]["text"]
            return None
    if ui_state["continue"].width > 0 and ui_state["continue"].collidepoint(event.pos):
        ch1["phase"] = "assemble"
        ch1["hint"] = "Place required parts in slots, connect the cable, then TEST."
        return "assemble"
    return None


def draw_assemble(surface, fonts, mouse_pos, ch1, inventory):
    guided = wb.is_guided()
    filled_n = sum(1 for v in ch1["assembly"].values() if v) + (1 if ch1["cable_ok"] else 0)
    chrome = wb.draw_workbench_chrome(
        surface, fonts, mouse_pos,
        "ANTENNA ASSEMBLY WORKBENCH",
        "Diagram · Supplies · Slots · Cable · Test",
        ch1["hint"] or "Select a supply on the right, then click a compatible slot.",
        filled_n / 4.0,
        f"Progress {filled_n}/4",
        guided,
    )

    # Diagram labels
    ui.label(surface, fonts, "EQUIPMENT DIAGRAM", (80, 145), ui.C_AMBER, "small")
    slot_rects = {}
    for key, meta in SLOTS.items():
        r = pygame.Rect(meta["x"] - 40, meta["y"] - 40, 200, 110)
        flash = ch1.get("flash_slot") == key and ch1.get("flash_timer", 0) > 0
        wb.draw_slot(
            surface, fonts, r, meta["label"], ch1["assembly"][key], meta["needs"],
            inventory.get("selected"), guided, mouse_pos, flash_incompatible=flash,
        )
        slot_rects[key] = r

    # Cable connection diagram
    for name, pos in PORTS.items():
        pygame.draw.circle(surface, ui.C_CYAN, pos, 12)
        pygame.draw.circle(surface, (20, 12, 8), pos, 12, 2)
        ui.label(surface, fonts, name.replace("_", " "), (pos[0] - 36, pos[1] + 14), ui.C_MUTED, "small")
    if ch1["cable_ok"]:
        pygame.draw.line(surface, ui.C_GREEN, PORTS["amp_out"], PORTS["antenna_in"], 5)
        ui.label(surface, fonts, "LINK OK", (600, 400), ui.C_GREEN, "small")
    elif ch1["dragging_cable"]:
        pygame.draw.line(surface, ui.C_AMBER, PORTS["amp_out"], ch1["drag_pos"], 4)
    elif guided:
        ui.label(surface, fonts, "Drag amp out → antenna in", (560, 400), ui.C_AMBER, "small")

    supply = wb.draw_supply_panel(
        surface, fonts, inventory, mouse_pos, "ch1",
        pygame.Rect(980, 130, 250, 420),
        slots_state=ch1.get("assembly"),
    )

    test_btn = pygame.Rect(80, 560, 200, 48)
    undo_btn = pygame.Rect(300, 560, 160, 48)
    reset = pygame.Rect(480, 560, 160, 48)
    cont = pygame.Rect(0, 0, 0, 0)
    ui.button(surface, test_btn, "TEST ASSEMBLY", fonts, mouse_pos)
    ui.button(surface, undo_btn, "UNDO SLOT", fonts, mouse_pos, small=True)
    ui.button(surface, reset, "RESET", fonts, mouse_pos, small=True)
    if ch1["test_msg"]:
        color = ui.C_GREEN if ch1["assembly_ok"] else ui.C_RED
        ui.centered(surface, fonts, ch1["test_msg"][:80], (640, 530), color, "body")
    if ch1["assembly_ok"]:
        cont = pygame.Rect(680, 560, 260, 48)
        ui.button(surface, cont, "OPEN RADAR", fonts, mouse_pos)
    ui.label(surface, fonts, "R-click a slot to remove · Click supply then slot to install", (80, 620), ui.C_MUTED, "small")

    return {
        "slots": slot_rects,
        "test": test_btn,
        "continue": cont,
        "reset": reset,
        "undo": undo_btn,
        "ports": PORTS,
        "supplies": supply,
        "mode": chrome["mode"],
    }


def handle_assemble_event(ch1, event, ui_state, inventory) -> str | None:
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
        for key, rect in ui_state.get("slots", {}).items():
            if rect.collidepoint(event.pos):
                clear_slot(ch1, key, inventory)
                ch1["hint"] = "Part removed — materials returned to supplies."
                return None
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        pos = event.pos
        if ui_state.get("mode") and ui_state["mode"].collidepoint(pos):
            wb.toggle_guided()
            return None
        if ui_state.get("supplies") and wb.handle_supply_click(inventory, ui_state["supplies"], pos):
            mid = inventory.get("selected")
            if mid:
                ch1["hint"] = f"Selected {mats.CATALOG[mid]['name']}. Click a compatible highlighted slot."
            return None
        if ui_state["reset"].collidepoint(pos):
            wb.clear_all(inventory, ch1["assembly"])
            ch1["cable_ok"] = False
            ch1["tested"] = False
            ch1["assembly_ok"] = False
            ch1["test_msg"] = ""
            ch1["hint"] = "Workbench cleared."
            return None
        if ui_state.get("undo") and ui_state["undo"].collidepoint(pos):
            # remove last filled slot
            for key in reversed(list(ch1["assembly"].keys())):
                if ch1["assembly"][key]:
                    clear_slot(ch1, key, inventory)
                    ch1["hint"] = "Last component removed."
                    break
            return None
        if ui_state["test"].collidepoint(pos):
            test_assembly(ch1, inventory)
            return None
        if ch1["assembly_ok"] and ui_state["continue"].width > 0 and ui_state["continue"].collidepoint(pos):
            ch1["phase"] = "ready"
            ch1["hint"] = "Scan, tune frequency, identify the flickering satellite."
            return "radar"
        for key, rect in ui_state.get("slots", {}).items():
            if rect.collidepoint(pos):
                ch1["hint"] = place_in_slot(ch1, key, inventory)
                return None
        ax, ay = PORTS["amp_out"]
        if math.hypot(pos[0] - ax, pos[1] - ay) < 20:
            ch1["dragging_cable"] = True
            ch1["drag_pos"] = pos
            ch1["cable_ok"] = False
            ch1["tested"] = False
            ch1["assembly_ok"] = False
    elif event.type == pygame.MOUSEMOTION and ch1["dragging_cable"]:
        ch1["drag_pos"] = event.pos
    elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and ch1["dragging_cable"]:
        ch1["dragging_cable"] = False
        bx, by = PORTS["antenna_in"]
        if math.hypot(event.pos[0] - bx, event.pos[1] - by) < 28:
            ch1["cable_ok"] = True
            ch1["hint"] = "Cable linked. Run TEST ASSEMBLY."
        else:
            ch1["cable_ok"] = False
            ch1["hint"] = "Cable missed antenna input — drag from amp out to antenna in."
    return None


def draw_radar(surface, fonts, mouse_pos, ch1):
    ui.dim_backdrop(surface, 145)
    box = pygame.Rect(60, 40, 1160, 640)
    ui.panel(surface, box)
    ui.header(surface, fonts, box, "COMMUNICATION RADAR", "Acquire contacts · Compare stability · Identify the faulty relay")
    ui.objective_bar(surface, fonts, "Scan → tune freq/gain → track contacts → select the weak flickering satellite", y=110)

    cx, cy, rad = 400, 390, 210
    pygame.draw.circle(surface, (12, 28, 22), (cx, cy), rad)
    pygame.draw.circle(surface, ui.C_GREEN, (cx, cy), rad, 2)
    for r in (52, 105, 158, 210):
        pygame.draw.circle(surface, (30, 80, 55), (cx, cy), r, 1)
    pygame.draw.line(surface, (30, 80, 55), (cx - rad, cy), (cx + rad, cy), 1)
    pygame.draw.line(surface, (30, 80, 55), (cx, cy - rad), (cx, cy + rad), 1)
    ui.label(surface, fonts, "RANGE", (cx - 24, cy + rad + 8), ui.C_MUTED, "small")
    ang = math.radians(ch1["scan_angle"] - 90)
    pygame.draw.line(surface, ui.C_GREEN, (cx, cy), (cx + math.cos(ang) * rad, cy + math.sin(ang) * rad), 3)
    for i in range(10):
        a = math.radians(ch1["scan_angle"] - i * 3 - 90)
        pygame.draw.line(surface, (40, 110, 70), (cx, cy), (cx + math.cos(a) * rad, cy + math.sin(a) * rad), 1)

    sat_rects = {}
    for sat in satellites():
        track = ch1["tracks"][sat["id"]]
        visible = ch1["phase"] != "ready" and (track > 8 or ch1["phase"] in ("track", "identify"))
        if not visible:
            continue
        a = math.radians(sat["ang"] - 90)
        dist = rad * 0.55 if sat["healthy"] else rad * 0.72
        bx = int(cx + math.cos(a) * dist)
        by = int(cy + math.sin(a) * dist)
        size = 8 + int(track / 20)
        col = sat["color"]
        stable = "STABLE" if sat["pattern"] == "steady" else "UNSTABLE"
        if sat["pattern"] == "flicker" and abs(math.sin(ch1["pulse"] * 7)) < 0.35:
            col = (80, 60, 40)
        tracked = ch1.get("tracked") == sat["id"]
        if tracked:
            pygame.draw.circle(surface, ui.C_CYAN, (bx, by), size + 8, 2)
        pygame.draw.circle(surface, col, (bx, by), size)
        tag = fonts["small"].render(f"{sat['id']} {int(track)}% {stable}", True, col)
        surface.blit(tag, (bx + 12, by - 10))
        sat_rects[sat["id"]] = pygame.Rect(bx - 22, by - 22, 44, 44)

    console = pygame.Rect(680, 150, 500, 480)
    ui.panel(surface, console, accent=ui.C_CYAN)
    ui.label(surface, fonts, "CONTACT / TELEMETRY", (700, 165), ui.C_CYAN, "small")
    tracked = ch1.get("tracked")
    if tracked:
        tval = int(ch1["tracks"].get(tracked, 0))
        ui.label(surface, fonts, f"Tracking: {tracked}  strength {tval}%", (700, 195), ui.C_GREEN, "body")
        if tracked == "SAT-02":
            ui.label(surface, fonts, "Diagnostic: weak + intermittent (flicker)", (700, 225), ui.C_AMBER, "small")
        else:
            ui.label(surface, fonts, "Diagnostic: healthy steady return", (700, 225), ui.C_MUTED, "small")
    else:
        ui.label(surface, fonts, "No contact selected — click a blip after scan", (700, 195), ui.C_MUTED, "small")

    ui.label(surface, fonts, "History", (700, 260), ui.C_AMBER, "small")
    for i, line in enumerate(ch1["telemetry"][-6:]):
        ui.label(surface, fonts, line[:40], (700, 288 + i * 22), ui.C_MUTED, "small")

    ui.label(surface, fonts, f"FREQUENCY  {ch1['frequency']}", (700, 430), ui.C_TEXT, "body")
    ui.meter(surface, pygame.Rect(700, 460, 280, 16), ch1["frequency"], 100, ui.C_CYAN)
    freq_minus = pygame.Rect(1000, 450, 44, 34)
    freq_plus = pygame.Rect(1055, 450, 44, 34)
    ui.button(surface, freq_minus, "−", fonts, mouse_pos, small=True)
    ui.button(surface, freq_plus, "+", fonts, mouse_pos, small=True)
    ui.label(surface, fonts, f"GAIN  {ch1['gain']}", (700, 500), ui.C_TEXT, "body")
    ui.meter(surface, pygame.Rect(700, 528, 280, 16), ch1["gain"], 100, ui.C_AMBER)
    gain_minus = pygame.Rect(1000, 518, 44, 34)
    gain_plus = pygame.Rect(1055, 518, 44, 34)
    ui.button(surface, gain_minus, "−", fonts, mouse_pos, small=True)
    ui.button(surface, gain_plus, "+", fonts, mouse_pos, small=True)

    scan_btn = pygame.Rect(0, 0, 0, 0)
    if ch1["phase"] == "ready":
        scan_btn = pygame.Rect(780, 575, 220, 48)
        ui.button(surface, scan_btn, "SCAN AREA", fonts, mouse_pos)
    elif ch1["phase"] == "scanning":
        ui.centered(surface, fonts, "ACQUIRING CONTACTS…", (920, 575), ui.C_GREEN, "body")
        ui.meter(surface, pygame.Rect(760, 605, 340, 14), ch1["scan_progress"], 1.0, ui.C_GREEN)

    cont = pygame.Rect(0, 0, 0, 0)
    if ch1["identified"] == "SAT-02":
        ui.centered(surface, fonts, "SAT-02 CONFIRMED FAULTY", (920, 560), ui.C_GREEN, "title")
        cont = pygame.Rect(780, 590, 280, 46)
        ui.button(surface, cont, "CALIBRATE ANTENNA", fonts, mouse_pos, small=True)
    elif ch1["phase"] in ("track", "identify"):
        ui.centered(surface, fonts, "Select contact · confirm the weak unstable one", (920, 555), ui.C_AMBER, "small")

    if ch1["hint"]:
        ui.centered(surface, fonts, ch1["hint"][:85], (400, 640), ui.C_AMBER, "small")

    return {
        "scan": scan_btn,
        "freq_minus": freq_minus,
        "freq_plus": freq_plus,
        "gain_minus": gain_minus,
        "gain_plus": gain_plus,
        "sat_rects": sat_rects,
        "continue": cont,
    }


def handle_radar_event(ch1, event, ui_state) -> str | None:
    if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
        return None
    pos = event.pos
    if ch1["phase"] == "ready" and ui_state["scan"].collidepoint(pos):
        ch1["phase"] = "scanning"
        ch1["scan_progress"] = 0.0
        ch1["hint"] = "Sweeping… tune mid-high frequency for weak returns."
        return None
    if ui_state["freq_minus"].collidepoint(pos):
        ch1["frequency"] = max(0, ch1["frequency"] - 5)
    elif ui_state["freq_plus"].collidepoint(pos):
        ch1["frequency"] = min(100, ch1["frequency"] + 5)
    elif ui_state["gain_minus"].collidepoint(pos):
        ch1["gain"] = max(10, ch1["gain"] - 5)
    elif ui_state["gain_plus"].collidepoint(pos):
        ch1["gain"] = min(100, ch1["gain"] + 5)

    if ch1["phase"] in ("track", "identify") and ch1["identified"] is None:
        for sat_id, rect in ui_state["sat_rects"].items():
            if rect.collidepoint(pos):
                ch1["tracked"] = sat_id
                if sat_id == "SAT-02":
                    ch1["identified"] = "SAT-02"
                    ch1["phase"] = "identify"
                    ch1["hint"] = "Contact SAT-02 confirmed weak/unstable. Proceed to calibration."
                else:
                    ch1["hint"] = f"{sat_id} tracked: steady healthy return. Keep investigating."
                break

    if ch1["identified"] == "SAT-02" and ui_state["continue"].collidepoint(pos):
        ch1["phase"] = "briefing"
        ch1["timer_running"] = False
        ch1["hint"] = "Read the antenna briefing, then try guided practice."
        return "briefing"
    return None


def draw_align(surface, fonts, mouse_pos, ch1, practice: bool = False):
    ui.dim_backdrop(surface, 145)
    box = pygame.Rect(80, 40, 1120, 600 if practice else 620)
    ui.panel(surface, box)
    mode = "PRACTICE — no timer, no score" if practice or ch1.get("align_mode") == "practice" else "TIMED CALIBRATION"
    ui.header(surface, fonts, box, "ANTENNA CALIBRATION", mode)

    band = ch1.get("signal_band") or signal_band(ch1["antenna_angle"], ch1.get("interference", 0))
    step = current_step_size(ch1)
    ui.objective_bar(
        surface, fonts,
        f"{band}  |  Angle {ch1['antenna_angle']:+d}°  |  Target ~{TARGET_ANGLE:+d}°  |  Packets {ch1['packets']}/{PACKETS_NEEDED}",
        y=110,
    )

    dx, dy = 360, 360
    pygame.draw.ellipse(surface, (40, 25, 18), (dx - 90, dy + 70, 180, 36))
    pygame.draw.rect(surface, (110, 115, 125), (dx - 8, dy - 10, 16, 100))
    # Target bearing indicator (dashed arc cue)
    t_ang = math.radians(TARGET_ANGLE - 90)
    t_tip = (dx + int(math.cos(t_ang) * 58), dy - 40 + int(math.sin(t_ang) * 24))
    pygame.draw.line(surface, (80, 120, 90), (dx, dy - 40), t_tip, 2)
    ui.label(surface, fonts, "target", (t_tip[0] - 18, t_tip[1] - 18), ui.C_MUTED, "small")

    ang = math.radians(ch1["antenna_angle"] - 90)
    pygame.draw.ellipse(surface, (200, 205, 215), (dx - 70, dy - 80, 140, 70))
    tip = (dx + int(math.cos(ang) * 50), dy - 40 + int(math.sin(ang) * 20))
    pygame.draw.line(surface, (180, 185, 195), (dx, dy - 40), tip, 4)
    pygame.draw.circle(surface, ui.C_CYAN, tip, 6)

    strength = signal_strength(ch1["antenna_angle"])
    if ch1.get("interference", 0) > 0:
        strength *= 0.45
        ui.centered(surface, fonts, "INTERFERENCE!", (dx, 190), ui.C_RED, "title")

    ui.label(surface, fonts, "SIGNAL STRENGTH", (620, 160), ui.C_TEXT, "body")
    col = ui.C_GREEN if "STABLE" in band or band.startswith("COMM") else (ui.C_AMBER if "IMPROVING" in band else ui.C_RED)
    ui.meter(surface, pygame.Rect(620, 196, 420, 28), strength, 100, col)
    ui.label(surface, fonts, f"{int(strength)}%", (1060, 198), col, "body")
    # Text status (not colour-only)
    ui.label(surface, fonts, band, (620, 232), col, "body")
    ui.label(
        surface, fonts,
        f"Stable zone: ±{STABLE_ZONE_DEG}° of {TARGET_ANGLE:+d}°  ·  Step ±{step}°",
        (620, 258),
        ui.C_MUTED,
        "small",
    )
    if ch1.get("align_feedback"):
        ui.label(surface, fonts, ui.truncate(ch1["align_feedback"], 62), (620, 282), ui.C_AMBER, "small")

    if not practice:
        ui.label(surface, fonts, "TRANSMISSION PACKETS", (620, 318), ui.C_CYAN, "body")
        for i in range(PACKETS_NEEDED):
            slot = pygame.Rect(620 + i * 90, 350, 70, 50)
            filled = i < ch1["packets"]
            pygame.draw.rect(surface, ui.C_SURFACE, slot, border_radius=8)
            pygame.draw.rect(surface, ui.C_GREEN if filled else ui.C_EDGE, slot, 2, border_radius=8)
            if filled:
                ui.icon_bolt(surface, slot.center, ui.C_CYAN)
            if ch1["phase"] == "packets" and i == ch1["packets"] and ch1["packet_timer"] > 0:
                ui.meter(surface, pygame.Rect(slot.x, slot.bottom + 6, slot.w, 8), ch1["packet_timer"], 0.7, ui.C_AMBER)

    left = pygame.Rect(620, 440 if not practice else 360, 140, 50)
    right = pygame.Rect(900, 440 if not practice else 360, 140, 50)
    ui.button(surface, left, f"◀ −{step}°", fonts, mouse_pos)
    ui.button(surface, right, f"+{step}° ▶", fonts, mouse_pos)
    ui.label(surface, fonts, "Keyboard: ← Left   → Right", (620, left.bottom + 12), ui.C_MUTED, "small")

    if ch1["connection_restored"]:
        ui.centered(surface, fonts, "COMMUNICATION ESTABLISHED", (840, 540), ui.C_GREEN, "title")
    elif ch1["hint"] and not practice:
        ui.centered(surface, fonts, ui.truncate(ch1["hint"], 70), (840, 540), ui.C_AMBER, "body")
    return {"left": left, "right": right}


def draw_complete(surface, fonts, mouse_pos, score, time_left):
    return ui.result_panel(
        surface, fonts, mouse_pos,
        "COMMUNICATION RESTORED!",
        [
            f"Score: {score} points",
            f"Time remaining: {int(math.ceil(time_left))} seconds",
            "SAT-02 link stable · Hardware repaired",
        ],
        ok=True,
        btn_label="RETURN TO BASE",
    )


def draw_timeout(surface, fonts, mouse_pos):
    return ui.result_panel(
        surface, fonts, mouse_pos,
        "TIME IS UP!",
        [
            "The dust storm scrambled the signal again.",
            "Tip: watch the signal band — move into STABLE, then hold for packets.",
            "Use the green target cue and LEFT/RIGHT adjustments.",
            "Retry returns to the antenna briefing (practice has no time penalty).",
        ],
        ok=False,
        btn_label="RETRY CHALLENGE",
    )


# Back-compat aliases used by older main wiring
def draw_intro(surface, fonts, mouse_pos):
    return draw_diagnose(surface, fonts, mouse_pos, make_state(), journal_mod.make_journal())["continue"]
