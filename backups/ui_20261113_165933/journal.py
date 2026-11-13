"""Mission journal — objectives, clues, materials, repairs (no spoiler answers)."""

from __future__ import annotations

import pygame

from systems import challenge_ui as ui
from systems import materials as mats

# Clue catalog — hints only, never full slot recipes
CLUES = {
    "ch1_symptom_weak": {
        "id": "ch1_symptom_weak",
        "title": "Weak uplink",
        "text": "The antenna receives a weak signal even when the dish looks aimed. Inspect the signal amplifier.",
        "mission": "ch1",
    },
    "ch1_symptom_power": {
        "id": "ch1_symptom_power",
        "title": "Power trips",
        "text": "The console reports unstable power on the antenna bus. A protective fuse may be missing.",
        "mission": "ch1",
    },
    "ch1_symptom_coil": {
        "id": "ch1_symptom_coil",
        "title": "Coil gap",
        "text": "The copper coil path is open. Conductive wire is needed before any test will pass.",
        "mission": "ch1",
    },
    "ch1_sat_note": {
        "id": "ch1_sat_note",
        "title": "Relay note",
        "text": "Storm logs mention one relay that flickers instead of holding a steady return.",
        "mission": "ch1",
    },
    "ch2_path": {
        "id": "ch2_path",
        "title": "Power path",
        "text": "Energy should flow Solar → Charge Controller → Battery → Fuse → Habitat. Polarity matters.",
        "mission": "ch2",
    },
    "ch2_fuse": {
        "id": "ch2_fuse",
        "title": "Safety fuse",
        "text": "Without a fuse between battery output and habitat, the test board will report a short risk.",
        "mission": "ch2",
    },
    "ch3_motor": {
        "id": "ch3_motor",
        "title": "Drive fault",
        "text": "The rover rolls poorly. The drive motor bay shows scorched mounts.",
        "mission": "ch3",
    },
    "ch3_wheel": {
        "id": "ch3_wheel",
        "title": "Wheel jam",
        "text": "One wheel assembly squeals and sticks. Lubricant and a support bracket may be needed.",
        "mission": "ch3",
    },
    "ch3_batt": {
        "id": "ch3_batt",
        "title": "Low voltage",
        "text": "Cabin voltage is below safe start. A fresh battery cell is required before driving.",
        "mission": "ch3",
    },
    "research_storm": {
        "id": "research_storm",
        "title": "Storm briefing",
        "text": "Research notes: dust storm damaged antenna, habitat bus, and rover garage systems.",
        "mission": "all",
    },
}


def make_journal() -> dict:
    return {
        "open": False,
        "clues": [],  # clue ids discovered
        "page": 0,
    }


def add_clue(journal: dict, clue_id: str) -> bool:
    if clue_id not in CLUES:
        return False
    if clue_id in journal["clues"]:
        return False
    journal["clues"].append(clue_id)
    return True


def draw_journal(
    surface,
    fonts,
    journal: dict,
    communication_status: str,
    power_status: str,
    food_status: str,
    rover_status: str,
    score: int,
    discoveries: list,
    inventory=None,
    progression=None,
) -> None:
    if not journal["open"]:
        return
    ui.dim_backdrop(surface, 175)
    panel = pygame.Rect(180, 40, 920, 640)
    ui.panel(surface, panel, accent=ui.C_CYAN)
    ui.header(surface, fonts, panel, "MISSION JOURNAL", "Press J to close · Clues help you reason — they do not give the full recipe")

    objectives = [
        ("Restore Communication", communication_status == "ONLINE"),
        ("Restore Shelter Power", power_status == "ONLINE" and food_status == "SAFE"),
        ("Rescue the Rover", rover_status == "RESCUED"),
    ]
    y = 120
    ui.label(surface, fonts, "OBJECTIVES", (210, y), ui.C_AMBER, "small")
    y += 28
    for text, done in objectives:
        mark = "[DONE]" if done else "[OPEN]"
        color = ui.C_GREEN if done else ui.C_AMBER
        ui.label(surface, fonts, f"{mark}  {text}", (230, y), color, "small")
        y += 26

    ui.label(
        surface, fonts,
        f"Score {score}  |  COMM {communication_status}  POWER {power_status}  FOOD {food_status}  ROVER {rover_status}",
        (210, y + 6), ui.C_TEXT, "small",
    )
    y += 40

    # Materials summary
    ui.label(surface, fonts, "MATERIALS ON HAND", (210, y), ui.C_AMBER, "small")
    y += 26
    if inventory is None:
        ui.label(surface, fonts, "—", (230, y), ui.C_MUTED, "small")
        y += 24
    else:
        shown = 0
        for mid, info in mats.CATALOG.items():
            q = inventory["stock"].get(mid, {"qty": 0})["qty"]
            if q <= 0:
                continue
            ui.label(surface, fonts, f"• {info['name']} ×{q}", (230, y), ui.C_TEXT, "small")
            y += 22
            shown += 1
            if shown >= 6:
                break
        if shown == 0:
            ui.label(surface, fonts, "No repair materials yet — explore the zones.", (230, y), ui.C_MUTED, "small")
            y += 22

    y += 10
    ui.label(surface, fonts, "DISCOVERED CLUES", (210, y), ui.C_AMBER, "small")
    y += 26
    if not journal["clues"]:
        ui.label(surface, fonts, "Inspect stations and research to discover clues.", (230, y), ui.C_MUTED, "small")
    else:
        for cid in journal["clues"][-7:]:
            clue = CLUES[cid]
            ui.label(surface, fonts, f"• {clue['title']}: {clue['text'][:70]}", (220, y), ui.C_TEXT, "small")
            y += 24
            if y > 640:
                break

    if progression:
        y = 620
        extras = []
        if progression.get("scan_clarity", 0) > 0:
            extras.append(f"Scan clarity {int(progression['scan_clarity']*100)}%")
        if progression.get("extra_comms", 0) > 0:
            extras.append(f"Comms boost +{progression['extra_comms']}")
        if extras:
            ui.centered(surface, fonts, "Cross-mission: " + " · ".join(extras), (panel.centerx, y), ui.C_CYAN, "small")
