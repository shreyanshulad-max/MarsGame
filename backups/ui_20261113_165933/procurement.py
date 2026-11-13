"""Research Procurement Station — spend RP on essential mission materials."""

from __future__ import annotations

import pygame

from systems import challenge_ui as ui
from systems import materials as mats
from systems import workbench as wb

# Prices tuned so Tier1 (80 RP) can buy Mission 1 kit (20+35+15=70)
CATALOGUE = [
    {"id": "copper_wire", "price": 20, "tier": 1, "essential": True, "desc": "Antenna coil conductor"},
    {"id": "signal_amplifier", "price": 35, "tier": 1, "essential": True, "desc": "Boosts weak uplink"},
    {"id": "spare_fuse", "price": 15, "tier": 1, "essential": True, "desc": "Protects power bus"},
    {"id": "insulated_cable", "price": 20, "tier": 2, "essential": True, "desc": "Solar/habitat power cable"},
    {"id": "battery_cell", "price": 25, "tier": 2, "essential": True, "desc": "Portable energy cell"},
    {"id": "servo_motor", "price": 35, "tier": 3, "essential": True, "desc": "Rover drive motor"},
    {"id": "lubricant", "price": 15, "tier": 3, "essential": True, "desc": "Frees jammed wheels"},
    {"id": "metal_bracket", "price": 15, "tier": 3, "essential": True, "desc": "Structural support"},
]

KIT_COST = {
    "mission_1": 70,   # 20+35+15
    "mission_2": 35,   # 20+15 (cable+fuse) — battery optional
    "mission_3": 90,   # 35+25+15+15
}


def items_for_tier(tier: int) -> list[dict]:
    return [it for it in CATALOGUE if it["tier"] <= tier]


def price_of(mid: str) -> int:
    for it in CATALOGUE:
        if it["id"] == mid:
            return int(it["price"])
    return 9999


def can_buy(campaign: dict, mid: str, qty: int = 1) -> tuple[bool, str]:
    item = next((x for x in CATALOGUE if x["id"] == mid), None)
    if not item:
        return False, "Unknown item."
    if item["tier"] > campaign.get("research_tier", 1):
        return False, f"Requires Research Tier {item['tier']}."
    cost = item["price"] * qty
    if campaign["research_points"] < cost:
        need = cost - campaign["research_points"]
        return False, f"Need {need} more RP (costs {cost} RP)."
    return True, f"Buy {mats.CATALOG[mid]['name']} ×{qty} for {cost} RP?"


def purchase(campaign: dict, inventory: dict, mid: str, qty: int = 1) -> tuple[bool, str]:
    from systems import campaign as camp

    ok, msg = can_buy(campaign, mid, qty)
    if not ok:
        return False, msg
    cost = price_of(mid) * qty
    if not camp.spend_rp(campaign, cost):
        return False, "Purchase failed — insufficient RP."
    mats.add_material(inventory["stock"], mid, qty)
    campaign["purchased_materials"][mid] = campaign["purchased_materials"].get(mid, 0) + qty
    campaign["reward_log"].append(f"Purchased {mats.CATALOG[mid]['name']} ×{qty} (−{cost} RP)")
    return True, f"Purchased {mats.CATALOG[mid]['name']} ×{qty}."


def draw_shop(surface, fonts, mouse_pos, campaign: dict, inventory: dict) -> dict:
    ui.dim_backdrop(surface, 160)
    box = pygame.Rect(80, 30, 1120, 660)
    ui.panel(surface, box)
    ui.header(
        surface, fonts, box,
        "RESEARCH PROCUREMENT STATION",
        f"Research Points: {campaign['research_points']} RP  ·  Tier {campaign.get('research_tier', 1)}",
    )
    ui.objective_bar(
        surface, fonts,
        "Essential kits are always listed for your unlocked tier — caches are optional extras.",
        y=105,
    )

    buttons = {}
    y = 150
    for it in items_for_tier(campaign.get("research_tier", 1)):
        mid = it["id"]
        info = mats.CATALOG[mid]
        owned = inventory["stock"].get(mid, {}).get("qty", 0)
        r = pygame.Rect(120, y, 900, 58)
        pygame.draw.rect(surface, (35, 22, 16), r, border_radius=8)
        pygame.draw.rect(surface, ui.C_EDGE, r, 2, border_radius=8)
        wb.draw_material_icon(surface, mid, (r.x + 28, r.centery), 16)
        ui.label(surface, fonts, info["name"], (r.x + 56, r.y + 8), ui.C_TEXT, "body")
        ui.label(
            surface, fonts,
            f"{it['desc']}  ·  Own {owned}  ·  {it['price']} RP",
            (r.x + 56, r.y + 32),
            ui.C_MUTED,
            "small",
        )
        buy = pygame.Rect(1040, y + 8, 120, 42)
        ui.button(surface, buy, "BUY", fonts, mouse_pos, small=True)
        buttons[mid] = buy
        y += 66
        if y > 620:
            break

    close = pygame.Rect(520, 640, 240, 40)
    ui.button(surface, close, "CLOSE", fonts, mouse_pos, small=True)
    return {"buy": buttons, "close": close}
