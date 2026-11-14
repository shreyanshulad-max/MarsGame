"""Challenge 1 antenna briefing, guided practice, and calibration-ready screens.

Uses the same angle / signal logic as challenges_ch1 — not a separate demo.
"""

from __future__ import annotations

import math

import pygame

from systems import challenge_ui as ui
from systems import challenges_ch1 as ch1mod


PRACTICE_STEPS = (
    "adjust",
    "watch_signal",
    "stable_zone",
    "success",
)


def reset_practice(ch1: dict) -> None:
    """Prepare a non-scoring practice calibration using the real interaction logic."""
    ch1["align_mode"] = "practice"
    ch1["timer_running"] = False
    ch1["practice_step"] = "adjust"
    ch1["practice_moved"] = False
    ch1["practice_saw_signal"] = False
    ch1["practice_stable_once"] = False
    ch1["phase"] = "align"
    ch1["antenna_angle"] = ch1mod.PRACTICE_START_ANGLE
    ch1["packets"] = 0
    ch1["packet_timer"] = 0.0
    ch1["interference"] = 0.0
    ch1["interference_cd"] = 9999.0  # no interference in practice
    ch1["connection_restored"] = False
    ch1["restore_delay"] = 0.0
    ch1["align_feedback"] = "Practice mode — take your time."
    ch1["hint"] = "Use LEFT / RIGHT (or the buttons) to adjust the antenna."
    ch1["signal_band"] = ch1mod.signal_band(ch1["antenna_angle"])


def begin_timed_mission(ch1: dict) -> None:
    """Start the scored timed calibration after the player confirms readiness."""
    ch1["align_mode"] = "timed"
    ch1["timer_running"] = True
    ch1["time_left"] = float(ch1mod.TIME_LIMIT)
    ch1["phase"] = "align"
    ch1["antenna_angle"] = ch1mod.START_ANGLE
    ch1["packets"] = 0
    ch1["packet_timer"] = 0.0
    ch1["interference"] = 0.0
    ch1["interference_cd"] = 4.0
    ch1["connection_restored"] = False
    ch1["restore_delay"] = 0.0
    ch1["align_feedback"] = "Mission started — move toward the stable signal zone."
    ch1["hint"] = "Adjust until STABLE SIGNAL, then hold for packet capture."
    ch1["signal_band"] = ch1mod.signal_band(ch1["antenna_angle"])


def advance_practice_on_rotate(ch1: dict) -> None:
    ch1["practice_moved"] = True
    band = ch1mod.signal_band(ch1["antenna_angle"])
    ch1["signal_band"] = band
    if ch1.get("practice_step") == "adjust":
        ch1["practice_step"] = "watch_signal"
        ch1["hint"] = "Watch the signal strength meter. Move toward the strongest signal."
    if band in ("IMPROVING SIGNAL", "STABLE SIGNAL"):
        ch1["practice_saw_signal"] = True
        if ch1.get("practice_step") == "watch_signal":
            ch1["practice_step"] = "stable_zone"
            ch1["hint"] = "When the signal enters the STABLE zone, you are aligned."
    if band == "STABLE SIGNAL":
        ch1["practice_stable_once"] = True
        ch1["practice_step"] = "success"
        ch1["hint"] = "Good work! You established a stable test connection."
        ch1["align_feedback"] = "PRACTICE COMPLETE — stable test link."


def draw_briefing(surface, fonts, mouse_pos) -> dict:
    ui.dim_backdrop(surface, 160)
    box = pygame.Rect(100, 40, 1080, 640)
    ui.panel(surface, box)
    ui.header(surface, fonts, box, "RESTORE THE EARTH COMMUNICATION LINK", "Antenna calibration briefing")

    lines = [
        "Mission Control has lost communication with the Mars habitat.",
        "The satellite relay (SAT-02) has been identified, but the antenna is not aligned.",
        "Your task: adjust the antenna until a stable signal is established.",
        "",
        "OBJECTIVES",
        "1. Locate the target satellite (already done).",
        "2. Adjust the antenna direction.",
        "3. Monitor signal strength.",
        "4. Find the optimal / stable alignment.",
        "5. Hold the link to capture transmission packets.",
        "",
        "CONTROLS (this challenge)",
        "LEFT  /  ◀ button  — turn antenna left (−5°)",
        "RIGHT /  ▶ button  — turn antenna right (+5°)",
        "No Enter key is required — hold the stable zone to capture packets.",
        "ESC — leave challenge and return toward base.",
    ]
    y = 130
    for line in lines:
        col = ui.C_SIGNAL if line in ("OBJECTIVES", "CONTROLS (this challenge)") else ui.C_TEXT
        if not line:
            y += 10
            continue
        ui.label(surface, fonts, line, (140, y), col, "small" if line[0].isdigit() or line.startswith("LEFT") or line.startswith("RIGHT") or line.startswith("No ") or line.startswith("ESC") else "body")
        y += 26 if line.startswith(("1.", "2.", "3.", "4.", "5.", "LEFT", "RIGHT", "No ", "ESC")) else 28

    practice = pygame.Rect(0, 0, 280, 48)
    practice.center = (box.centerx, 620)
    ui.button(surface, practice, "START GUIDED PRACTICE", fonts, mouse_pos, accent=True)
    return {"practice": practice}


def draw_practice(surface, fonts, mouse_pos, ch1: dict) -> dict:
    """Guided practice reusing the real dish / meter drawing helpers."""
    hit = ch1mod.draw_align(surface, fonts, mouse_pos, ch1, practice=True)
    step = ch1.get("practice_step", "adjust")
    tips = {
        "adjust": "Step 1 — Use LEFT or RIGHT to adjust the antenna.",
        "watch_signal": "Step 2 — Watch the signal meter. Move toward the strongest signal.",
        "stable_zone": "Step 3 — Enter the STABLE SIGNAL zone (green).",
        "success": "Step 4 — Good work! Stable test connection established.",
    }
    tip = tips.get(step, "")
    bar = pygame.Rect(120, 640, 1040, 36)
    pygame.draw.rect(surface, ui.C_BG, bar, border_radius=8)
    pygame.draw.rect(surface, ui.C_SIGNAL, bar, 1, border_radius=8)
    ui.centered(surface, fonts, tip, bar.center, ui.C_TEXT, "small")

    start = pygame.Rect(0, 0, 0, 0)
    again = pygame.Rect(0, 0, 0, 0)
    if step == "success":
        start = pygame.Rect(0, 0, 240, 44)
        again = pygame.Rect(0, 0, 240, 44)
        start.center = (520, 580)
        again.center = (780, 580)
        ui.button(surface, start, "START MISSION", fonts, mouse_pos, accent=True)
        ui.button(surface, again, "REPEAT PRACTICE", fonts, mouse_pos)
    hit["start_mission"] = start
    hit["repeat"] = again
    hit["practice_step"] = step
    return hit


def draw_ready(surface, fonts, mouse_pos) -> dict:
    ui.dim_backdrop(surface, 160)
    box = pygame.Rect(220, 120, 840, 480)
    ui.panel(surface, box, accent=ui.C_SIGNAL)
    ui.header(surface, fonts, box, "CALIBRATION READY", "Timed mission — start when you are ready")

    lines = [
        "OBJECTIVE: Establish a stable satellite communication link.",
        "",
        "CONTROLS: LEFT / RIGHT or on-screen buttons adjust the antenna.",
        "Hold the STABLE SIGNAL zone to capture transmission packets.",
        "",
        f"MISSION TIMER: {ch1mod.TIME_LIMIT} seconds (starts only after you confirm).",
        f"Stable zone: within ±{ch1mod.STABLE_ZONE_DEG}° of optimal bearing.",
        "Briefing and practice time are NOT counted.",
    ]
    y = 200
    for line in lines:
        if not line:
            y += 12
            continue
        ui.centered(surface, fonts, line, (box.centerx, y), ui.C_TEXT, "body")
        y += 34

    start = pygame.Rect(0, 0, 280, 48)
    back = pygame.Rect(0, 0, 240, 44)
    start.center = (box.centerx, 500)
    back.center = (box.centerx, 560)
    ui.button(surface, start, "START TIMED MISSION", fonts, mouse_pos, accent=True)
    ui.button(surface, back, "BACK TO PRACTICE", fonts, mouse_pos, small=True)
    return {"start": start, "practice": back}


def draw_control_reference(surface, fonts, mouse_pos) -> dict:
    """Compact overlay helper used from timed align (optional)."""
    box = pygame.Rect(40, 640, 400, 48)
    pygame.draw.rect(surface, ui.C_BG, box, border_radius=8)
    ui.label(surface, fonts, "◀ / ▶ or ← → : adjust   |   Hold STABLE to capture", (52, 654), ui.C_MUTED, "small")
    return {}
