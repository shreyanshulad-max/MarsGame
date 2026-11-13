"""Challenge 2 — circuit construction (polarity/fuse) + power allocation with consequences."""

from __future__ import annotations

import math

import pygame

from systems import challenge_ui as ui
from systems import journal as journal_mod
from systems import materials as mats

ENERGY_BUDGET = 80
FOOD_DECAY = 4.0
POINTS = 100
TIME_LIMIT = 90
MIN_LIFE = 30
MIN_FOOD = 30
MIN_COMMS = 10

# Board nodes with + / - ports
NODES = {
    "solar": {"label": "Solar Panel", "box": (100, 200, 160, 140), "out_p": (260, 240), "out_n": (260, 300)},
    "controller": {"label": "Charge Ctrl", "box": (320, 200, 160, 140), "in_p": (320, 240), "in_n": (320, 300), "out_p": (480, 240), "out_n": (480, 300)},
    "battery": {"label": "Battery", "box": (540, 200, 160, 140), "in_p": (540, 240), "in_n": (540, 300), "out_p": (700, 240), "out_n": (700, 300)},
    "fuse": {"label": "Fuse", "box": (760, 220, 120, 100), "in_p": (760, 250), "out_p": (880, 250)},
    "habitat": {"label": "Habitat", "box": (940, 200, 160, 140), "in_p": (940, 240), "in_n": (940, 300)},
}

# Required directed links (from_port, to_port)
REQUIRED_LINKS = [
    ("solar.out_p", "controller.in_p"),
    ("solar.out_n", "controller.in_n"),
    ("controller.out_p", "battery.in_p"),
    ("controller.out_n", "battery.in_n"),
    ("battery.out_p", "fuse.in_p"),
    ("fuse.out_p", "habitat.in_p"),
    ("battery.out_n", "habitat.in_n"),
]


def make_state():
    return {
        "time_left": float(TIME_LIMIT),
        "finish_time_left": 0.0,
        "hint": "Inspect the circuit. Connect + to + and − to −. Install a fuse.",
        "phase": "circuit",  # circuit -> power
        "links": [],  # list of (a, b) port ids
        "dragging": None,
        "drag_pos": (0, 0),
        "fuse_installed": False,
        "cables_used": 0,
        "tested": False,
        "test_msg": "",
        "circuit_ok": False,
        "wires_done": False,  # alias for main compatibility
        "life": 20,
        "food": 20,
        "comms": 40,
        "food_freshness": 100.0,
        "points_awarded": False,
        "completed": False,
        "complete_delay": 0.0,
        "flow_t": 0.0,
        "warn_flash": 0.0,
        "confirmed_alloc": False,
        "alloc_preview": "",
    }


def total_power(ch2) -> int:
    return ch2["life"] + ch2["food"] + ch2["comms"]


def power_ok(ch2) -> bool:
    return ch2["life"] >= MIN_LIFE and ch2["food"] >= MIN_FOOD and ch2["comms"] >= MIN_COMMS


def change_power(ch2, system: str, delta: int) -> None:
    new_value = ch2[system] + delta
    if new_value < 0:
        return
    old = ch2[system]
    ch2[system] = new_value
    if total_power(ch2) > ENERGY_BUDGET:
        ch2[system] = old
    ch2["confirmed_alloc"] = False
    _refresh_preview(ch2)


def _refresh_preview(ch2) -> None:
    parts = []
    if ch2["life"] < MIN_LIFE:
        parts.append("Life support below minimum — O₂ unsafe.")
    elif ch2["life"] > MIN_LIFE:
        parts.append(f"Extra life +{ch2['life'] - MIN_LIFE}: better oxygen reserve.")
    if ch2["food"] < MIN_FOOD:
        parts.append("Food fridge below minimum — spoilage risk.")
    elif ch2["food"] > MIN_FOOD:
        parts.append(f"Extra fridge +{ch2['food'] - MIN_FOOD}: better preservation.")
    if ch2["comms"] < MIN_COMMS:
        parts.append("Comms below minimum — link unstable.")
    elif ch2["comms"] > MIN_COMMS:
        parts.append(f"Extra comms +{ch2['comms'] - MIN_COMMS}: clearer Challenge 3 scans.")
    rem = ENERGY_BUDGET - total_power(ch2)
    if rem > 0:
        parts.append(f"Battery reserve {rem} units.")
    ch2["alloc_preview"] = " | ".join(parts) if parts else "Balanced."


def _port_pos(pid: str):
    node, port = pid.split(".", 1)
    return NODES[node][port]


def _has_link(ch2, a, b) -> bool:
    return (a, b) in ch2["links"] or (b, a) in ch2["links"]


def circuit_faults(ch2) -> list[str]:
    faults = []
    if not ch2["fuse_installed"]:
        faults.append("MISSING_FUSE: Install a spare fuse on the fuse block.")
    # Check reversed polarity examples
    if _has_link(ch2, "solar.out_p", "controller.in_n") or _has_link(ch2, "solar.out_n", "controller.in_p"):
        faults.append("REVERSED_POLARITY: Solar ± connected backwards to controller.")
    if _has_link(ch2, "battery.out_p", "habitat.in_n"):
        faults.append("REVERSED_POLARITY: Battery positive tied to habitat negative.")
    for a, b in REQUIRED_LINKS:
        if not _has_link(ch2, a, b):
            faults.append(f"OPEN_PATH: Need link {a} → {b}.")
            break
    return faults


def test_circuit(ch2, inventory) -> None:
    faults = circuit_faults(ch2)
    ch2["tested"] = True
    if faults:
        ch2["circuit_ok"] = False
        ch2["wires_done"] = False
        ch2["test_msg"] = faults[0]
        ch2["hint"] = "Circuit test failed. Fix the reported fault."
        return
    # Need insulated cable usage conceptually — require at least 4 links and fuse from inventory
    if inventory:
        if inventory["stock"].get("insulated_cable", {}).get("qty", 0) < 1 and ch2["cables_used"] < 1:
            # Allow if they placed links (cables conceptually used from inventory on first link)
            pass
        if ch2["fuse_installed"]:
            # commit fuse if reserved
            if inventory["stock"].get("spare_fuse", {}).get("reserved", 0) > 0:
                mats.commit(inventory["stock"], "spare_fuse", 1)
            elif mats.available(inventory["stock"], "spare_fuse") >= 1:
                mats.reserve(inventory["stock"], "spare_fuse", 1)
                mats.commit(inventory["stock"], "spare_fuse", 1)
            else:
                ch2["test_msg"] = "MISSING_FUSE: No spare fuse in inventory."
                ch2["circuit_ok"] = False
                return
        # Commit one insulated cable pack on success
        if inventory["stock"].get("insulated_cable", {}).get("reserved", 0) > 0:
            mats.commit(inventory["stock"], "insulated_cable", 1)
        elif mats.available(inventory["stock"], "insulated_cable") >= 1:
            mats.reserve(inventory["stock"], "insulated_cable", 1)
            mats.commit(inventory["stock"], "insulated_cable", 1)

    ch2["circuit_ok"] = True
    ch2["wires_done"] = True
    ch2["test_msg"] = "CIRCUIT PASS — energy path restored."
    ch2["hint"] = "Continue to power distribution."


def install_fuse(ch2, inventory) -> str:
    if ch2["fuse_installed"]:
        return "Fuse already installed."
    if not mats.reserve(inventory["stock"], "spare_fuse", 1):
        return "No Spare Fuse available — collect one first."
    ch2["fuse_installed"] = True
    ch2["tested"] = False
    ch2["circuit_ok"] = False
    return "Fuse installed (held until successful test)."


def remove_fuse(ch2, inventory) -> None:
    if ch2["fuse_installed"]:
        mats.release(inventory["stock"], "spare_fuse", 1)
        ch2["fuse_installed"] = False
        ch2["tested"] = False
        ch2["circuit_ok"] = False


def update(ch2, dt, active: bool) -> None:
    ch2["flow_t"] += dt
    if ch2["warn_flash"] > 0:
        ch2["warn_flash"] -= dt
    if not active or ch2["completed"]:
        return
    if ch2["food"] < MIN_FOOD:
        ch2["food_freshness"] = max(0.0, ch2["food_freshness"] - FOOD_DECAY * dt)
    if ch2["wires_done"] and power_ok(ch2) and ch2.get("confirmed_alloc") and not ch2["completed"]:
        ch2["completed"] = True
        ch2["finish_time_left"] = ch2["time_left"]
        ch2["complete_delay"] = 1.0


def allocation_bonuses(ch2) -> dict:
    """Extras above minimums for cross-challenge progression."""
    return {
        "extra_life": max(0, ch2["life"] - MIN_LIFE),
        "extra_food": max(0, ch2["food"] - MIN_FOOD),
        "extra_comms": max(0, ch2["comms"] - MIN_COMMS),
    }


def draw_intro(surface, fonts, mouse_pos):
    ui.dim_backdrop(surface)
    box = pygame.Rect(220, 120, 840, 460)
    ui.panel(surface, box)
    ui.header(surface, fonts, box, "POWER FAILURE DETECTED", "Build a real circuit — clicking cards will not restore power")
    lines = [
        "1. Place fuse and drag ± cables along Solar → Battery → Habitat",
        "2. Test the circuit (wrong polarity / missing fuse will fail)",
        "3. Allocate the 80-unit budget (Life≥30 Food≥30 Comms≥10)",
    ]
    for i, line in enumerate(lines):
        ui.centered(surface, fonts, line, (box.centerx, 250 + i * 40), ui.C_TEXT, "body")
    btn = pygame.Rect(0, 0, 280, 54)
    btn.center = (box.centerx, 480)
    ui.button(surface, btn, "OPEN CIRCUIT BOARD", fonts, mouse_pos)
    return btn


def draw_wire(surface, fonts, mouse_pos, ch2):
    """Circuit board stage (kept name for main.py)."""
    ui.dim_backdrop(surface, 140)
    box = pygame.Rect(40, 30, 1200, 660)
    ui.panel(surface, box)
    ui.header(surface, fonts, box, "CIRCUIT ASSEMBLY", "Drag from OUTPUT ports to matching INPUT · + red · − cyan")
    ui.objective_bar(surface, fonts, ch2["hint"][:95], y=105)

    port_hit = {}
    for key, node in NODES.items():
        bx, by, bw, bh = node["box"]
        r = pygame.Rect(bx, by, bw, bh)
        pygame.draw.rect(surface, (35, 22, 16), r, border_radius=10)
        accent = ui.C_GREEN if (key == "fuse" and ch2["fuse_installed"]) else ui.C_EDGE
        pygame.draw.rect(surface, accent, r, 2, border_radius=10)
        ui.centered(surface, fonts, node["label"], (r.centerx, r.y + 18), ui.C_TEXT, "small")
        for pk, pos_key in list(node.items()):
            if pk in ("label", "box"):
                continue
            pos = node[pk]
            is_pos = pk.endswith("_p") or pk == "in_p" or pk == "out_p"
            col = ui.C_RED if is_pos else ui.C_CYAN
            pygame.draw.circle(surface, col, pos, 10)
            pygame.draw.circle(surface, (20, 12, 8), pos, 10, 2)
            pid = f"{key}.{pk}"
            port_hit[pid] = pos

    for a, b in ch2["links"]:
        pa, pb = _port_pos(a), _port_pos(b)
        ok = (a, b) in REQUIRED_LINKS or (b, a) in [(x, y) for x, y in REQUIRED_LINKS]
        # directed check softer
        color = ui.C_GREEN if ok else ui.C_AMBER
        pygame.draw.line(surface, color, pa, pb, 4)
        if ch2["circuit_ok"]:
            u = (ch2["flow_t"] * 0.7) % 1.0
            pygame.draw.circle(
                surface, ui.C_CYAN,
                (int(pa[0] + (pb[0] - pa[0]) * u), int(pa[1] + (pb[1] - pa[1]) * u)),
                4,
            )

    if ch2["dragging"]:
        pygame.draw.line(surface, ui.C_AMBER, _port_pos(ch2["dragging"]), ch2["drag_pos"], 3)

    fuse_btn = pygame.Rect(120, 420, 200, 44)
    ui.button(surface, fuse_btn, "INSTALL FUSE" if not ch2["fuse_installed"] else "REMOVE FUSE", fonts, mouse_pos, small=True)
    test_btn = pygame.Rect(360, 420, 200, 44)
    ui.button(surface, test_btn, "TEST CIRCUIT", fonts, mouse_pos, small=True)
    reset_btn = pygame.Rect(600, 420, 160, 44)
    ui.button(surface, reset_btn, "RESET", fonts, mouse_pos, small=True)
    cont = pygame.Rect(0, 0, 0, 0)
    if ch2["test_msg"]:
        ui.centered(surface, fonts, ch2["test_msg"], (640, 490), ui.C_GREEN if ch2["circuit_ok"] else ui.C_RED, "body")
    if ch2["circuit_ok"]:
        cont = pygame.Rect(820, 420, 280, 44)
        ui.button(surface, cont, "POWER BOARD", fonts, mouse_pos, small=True)

    ui.label(surface, fonts, "Legend: RED = + positive   CYAN = − negative", (120, 540), ui.C_MUTED, "small")
    ui.label(surface, fonts, "Wrong links stay visible so you can diagnose them.", (120, 570), ui.C_MUTED, "small")

    return {
        "continue": cont,
        "reset": reset_btn,
        "test": test_btn,
        "fuse": fuse_btn,
        "ports": port_hit,
        "ports_legacy": {},  # compat
    }


def handle_wire_event(ch2, event, ui_state, inventory=None) -> None:
    ports = ui_state.get("ports") or {}
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        pos = event.pos
        if ui_state["reset"].collidepoint(pos):
            ch2["links"] = []
            if ch2["fuse_installed"] and inventory:
                remove_fuse(ch2, inventory)
            ch2["fuse_installed"] = False
            ch2["circuit_ok"] = False
            ch2["wires_done"] = False
            ch2["tested"] = False
            ch2["test_msg"] = ""
            ch2["dragging"] = None
            ch2["hint"] = "Board reset."
            return
        if ui_state["fuse"].collidepoint(pos) and inventory is not None:
            if ch2["fuse_installed"]:
                remove_fuse(ch2, inventory)
                ch2["hint"] = "Fuse removed."
            else:
                ch2["hint"] = install_fuse(ch2, inventory)
            return
        if ui_state["test"].collidepoint(pos):
            test_circuit(ch2, inventory)
            return
        # start drag from a port
        for pid, ppos in ports.items():
            if math.hypot(pos[0] - ppos[0], pos[1] - ppos[1]) < 16:
                ch2["dragging"] = pid
                ch2["drag_pos"] = pos
                ch2["circuit_ok"] = False
                ch2["wires_done"] = False
                return
    elif event.type == pygame.MOUSEMOTION and ch2["dragging"]:
        ch2["drag_pos"] = event.pos
    elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and ch2["dragging"]:
        start = ch2["dragging"]
        ch2["dragging"] = None
        pos = event.pos
        for pid, ppos in ports.items():
            if pid == start:
                continue
            if math.hypot(pos[0] - ppos[0], pos[1] - ppos[1]) < 20:
                link = (start, pid)
                if link not in ch2["links"] and (pid, start) not in ch2["links"]:
                    ch2["links"].append(link)
                    ch2["cables_used"] += 1
                    ch2["hint"] = f"Linked {start} → {pid}"
                    ch2["tested"] = False
                break
        else:
            ch2["hint"] = "Cable not snapped to a port."


def draw_power(surface, fonts, mouse_pos, ch2):
    ui.dim_backdrop(surface, 140)
    box = pygame.Rect(80, 40, 1120, 640)
    ui.panel(surface, box)
    ui.header(surface, fonts, box, "POWER DISTRIBUTION BOARD", f"Budget {ENERGY_BUDGET} · Meet mins, then decide extras")
    _refresh_preview(ch2)
    ui.objective_bar(surface, fonts, "Life≥30  Food≥30  Comms≥10  |  Confirm after reviewing consequences", y=115)

    used = total_power(ch2)
    remaining = ENERGY_BUDGET - used
    ui.centered(
        surface, fonts,
        f"Used {used} / {ENERGY_BUDGET}     Remaining {remaining}",
        (640, 155),
        ui.C_GREEN if remaining >= 0 and power_ok(ch2) else ui.C_AMBER,
        "body",
    )

    systems = [
        ("life", "Life Support", MIN_LIFE, 200, ui.C_CYAN),
        ("food", "Food Refrigeration", MIN_FOOD, 300, ui.C_AMBER),
        ("comms", "Communications", MIN_COMMS, 400, ui.C_GREEN),
    ]
    controls = {}
    for key, name, minimum, y, color in systems:
        value = ch2[key]
        ok = value >= minimum
        ui.label(surface, fonts, f"{name}: {value}  (need {minimum})", (160, y), ui.C_TEXT if ok else ui.C_RED)
        ui.meter(surface, pygame.Rect(160, y + 32, 520, 22), value, ENERGY_BUDGET, color if ok else ui.C_RED)
        minus = pygame.Rect(720, y + 20, 56, 40)
        plus = pygame.Rect(800, y + 20, 56, 40)
        ui.button(surface, minus, "−", fonts, mouse_pos, small=True)
        ui.button(surface, plus, "+", fonts, mouse_pos, small=True)
        controls[key] = {"minus": minus, "plus": plus}
        if key == "life":
            ui.label(surface, fonts, "O₂ FLOW" if ok else "LOW O₂", (900, y + 24), ui.C_CYAN if ok else ui.C_RED, "small")
        elif key == "food":
            ui.label(surface, fonts, f"FRESH {int(ch2['food_freshness'])}%", (900, y + 24), ui.C_GREEN if ok else ui.C_RED, "small")
        else:
            ui.label(surface, fonts, "SIGNAL OK" if ok else "SIGNAL WEAK", (900, y + 24), ui.C_GREEN if ok else ui.C_RED, "small")

    # Consequences preview
    prev = pygame.Rect(140, 500, 1000, 50)
    pygame.draw.rect(surface, (35, 22, 16), prev, border_radius=8)
    pygame.draw.rect(surface, ui.C_CYAN, prev, 1, border_radius=8)
    ui.centered(surface, fonts, ch2["alloc_preview"][:110], prev.center, ui.C_TEXT, "small")

    confirm = pygame.Rect(0, 0, 320, 48)
    confirm.center = (640, 600)
    label = "CONFIRM ALLOCATION" if power_ok(ch2) else "FIX MINIMUMS FIRST"
    ui.button(surface, confirm, label, fonts, mouse_pos)
    controls["confirm"] = confirm
    return controls


def draw_complete(surface, fonts, mouse_pos, score, time_left, freshness):
    return ui.result_panel(
        surface, fonts, mouse_pos,
        "SHELTER POWER RESTORED!",
        [
            f"Score: {score} points",
            f"Time remaining: {int(math.ceil(time_left))} seconds",
            f"Food freshness: {int(freshness)}%",
            "POWER ONLINE · FOOD SAFE",
        ],
        ok=True,
        btn_label="RETURN TO BASE",
    )


def draw_timeout(surface, fonts, mouse_pos):
    return ui.dual_result_panel(
        surface, fonts, mouse_pos,
        "POWER FAILURE",
        ["Time ran out before systems stabilized.", "Retry — materials remain available."],
        ok=False,
    )
