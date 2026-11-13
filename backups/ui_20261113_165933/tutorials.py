"""Short dismissible contextual tutorials."""

from __future__ import annotations

import pygame

from systems import challenge_ui as ui

TIPS = {
    "inventory": {
        "id": "inventory",
        "title": "Inventory",
        "text": "Select a material to view its purpose and available quantity. Press I to open or close.",
    },
    "assembly": {
        "id": "assembly",
        "title": "Assembly",
        "text": "Select a material from supplies, then select a compatible component slot. Wrong parts are rejected safely.",
    },
    "scanner": {
        "id": "scanner",
        "title": "Field Scanner",
        "text": "Press Tab to scan nearby supplies and equipment. Approach unknowns to identify them.",
    },
    "map": {
        "id": "map",
        "title": "Colony Map",
        "text": "Press M for the map. It reveals places as you explore and scan. Scroll to zoom, drag to pan.",
    },
}


def make_tutorials() -> dict:
    return {
        "seen": set(),
        "active": None,  # tip id
        "dismiss_rect": pygame.Rect(0, 0, 0, 0),
        "replay": False,
    }


def trigger(tutorials: dict, tip_id: str, force: bool = False) -> None:
    if tip_id not in TIPS:
        return
    if tip_id in tutorials["seen"] and not force:
        return
    tutorials["active"] = tip_id


def dismiss(tutorials: dict) -> None:
    if tutorials["active"]:
        tutorials["seen"].add(tutorials["active"])
    tutorials["active"] = None


def draw(surface, fonts, tutorials: dict, mouse_pos) -> pygame.Rect:
    """Draw active tip card. Returns dismiss button rect."""
    tip_id = tutorials.get("active")
    if not tip_id:
        return pygame.Rect(0, 0, 0, 0)
    tip = TIPS[tip_id]
    card = pygame.Rect(280, 560, 720, 100)
    pygame.draw.rect(surface, (22, 14, 10), card, border_radius=12)
    pygame.draw.rect(surface, ui.C_CYAN, card, 2, border_radius=12)
    ui.label(surface, fonts, f"TIP — {tip['title']}", (card.x + 20, card.y + 14), ui.C_CYAN, "small")
    ui.label(surface, fonts, tip["text"][:90], (card.x + 20, card.y + 42), ui.C_TEXT, "small")
    btn = pygame.Rect(card.right - 130, card.y + 28, 110, 44)
    ui.button(surface, btn, "GOT IT", fonts, mouse_pos, small=True)
    tutorials["dismiss_rect"] = btn
    return btn


def handle_click(tutorials: dict, pos) -> bool:
    if tutorials.get("active") and tutorials.get("dismiss_rect") and tutorials["dismiss_rect"].collidepoint(pos):
        dismiss(tutorials)
        return True
    return False
