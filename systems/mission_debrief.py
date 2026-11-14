"""Short educational debriefs after major missions (grades 5–8 language)."""

from __future__ import annotations

import pygame

from systems import challenge_ui as ui
from systems import outpost as op


DEBRIEFS = {
    "mission_1": {
        "title": "Why antenna alignment matters",
        "question": "What happens if a habitat antenna points the wrong way?",
        "points": [
            "You repaired the antenna hardware and identified SAT-02.",
            "You adjusted the dish until the signal entered a stable zone.",
            "Holding that alignment let the habitat capture data packets.",
            "Radio links need the antenna pointed toward the relay satellite.",
        ],
        "science": (
            "Real spacecraft use careful pointing so radio energy reaches the receiver. "
            "This game uses a simplified stable-zone meter — not a real RF calculation."
        ),
        "source": "Educational radio-link concept · Mars relay communications context (NASA)",
    },
    "mission_2": {
        "title": "Sharing limited habitat power",
        "question": "What happens when a Mars habitat cannot supply enough energy to every system?",
        "points": [
            "You rebuilt the solar → battery → distribution → habitat circuit.",
            "You shared a limited power budget across critical systems.",
            "Systems below their minimum can reduce simulated stability or food growth.",
            "Dust can reduce available solar generation in this simulation.",
        ],
        "science": (
            "Power budgets are simplified game mechanics (80 units). They are not actual "
            "habitat engineering specifications."
        ),
        "source": "NASA solar / dust context imagery · educational power trade-offs",
    },
    "mission_3": {
        "title": "Terrain, observation, and rescue",
        "question": "Why do rover teams study the ground before driving?",
        "points": [
            "You scanned for the stranded rover and confirmed its location.",
            "You repaired mobility systems and chose a route.",
            "You drove carefully and completed the rescue.",
            "Cameras and terrain data help drivers avoid rocks and steep slopes.",
        ],
        "science": (
            "Rover cameras and orbital maps support navigation. Global topography is not the same "
            "as high-resolution local obstacle maps."
        ),
        "source": "Perseverance / HiRISE / MOLA educational browse products",
    },
}


def draw_debrief(surface, fonts, mouse_pos, campaign: dict, mission_id: str) -> dict:
    info = DEBRIEFS.get(mission_id, DEBRIEFS["mission_1"])
    ui.dim_backdrop(surface, 170)
    box = pygame.Rect(160, 60, 960, 600)
    ui.panel(surface, box, accent=ui.C_SIGNAL)
    ui.header(surface, fonts, box, "MISSION DEBRIEF", info["title"])
    ui.centered(surface, fonts, info["question"], (box.centerx, 160), ui.C_AMBER, "body")
    y = 200
    for line in info["points"]:
        ui.label(surface, fonts, f"• {line}", (200, y), ui.C_TEXT, "small")
        y += 32
    ui.label(surface, fonts, "Science note", (200, y + 10), ui.C_MUTED, "small")
    ui.label(surface, fonts, ui.truncate(info["science"], 90), (200, y + 36), ui.C_TEXT, "small")
    ui.label(surface, fonts, ui.truncate(info["source"], 90), (200, y + 68), ui.C_MUTED, "small")

    # Optional outpost snapshot for mission 2
    if mission_id == "mission_2":
        state = op.ensure_outpost(campaign)
        y2 = y + 110
        ui.label(surface, fonts, "Outpost snapshot (simulation)", (200, y2), ui.C_SIGNAL, "small")
        for i, line in enumerate(op.summary_lines(state)[:3]):
            ui.label(surface, fonts, line, (200, y2 + 28 + i * 24), ui.C_MUTED, "small")

    close = pygame.Rect(0, 0, 240, 44)
    close.center = (box.centerx, 610)
    ui.button(surface, close, "CONTINUE", fonts, mouse_pos, accent=True)
    return {"close": close}
