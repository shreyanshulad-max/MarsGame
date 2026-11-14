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
    "mission_1": 70,
    "mission_2": 35,
    "mission_3": 90,
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


def draw_shop(surface, fonts, mouse_pos, campaign: dict, inventory: dict, ui_state: dict | None = None) -> dict:
    """Clean catalogue + purchase panel for selected item only."""
    if ui_state is None:
        ui_state = {"selected": None}

    ui.dim_backdrop(surface, 150)
    box = pygame.Rect(64, 32, 1152, 656)
    ui.panel(surface, box)
    ui.header(
        surface, fonts, box,
        "PROCUREMENT",
        f"Research Points  {campaign['research_points']} RP   ·   Tier {campaign.get('research_tier', 1)}",
    )

    # Required qty hint from next mission kit
    from systems import campaign as camp

    next_kit = []
    for mid in camp.MISSION_ORDER:
        if camp.mission_status(campaign, mid) in (camp.STATUS_AVAILABLE, camp.STATUS_IN_PROGRESS):
            next_kit = camp.MISSION_META[mid]["kit"]
            break

    list_box = pygame.Rect(88, 110, 640, 500)
    pygame.draw.rect(surface, ui.C_BG, list_box, border_radius=8)
    pygame.draw.rect(surface, ui.C_EDGE, list_box, 1, border_radius=8)

    buttons = {}
    row_rects = {}
    y = 124
    for it in items_for_tier(campaign.get("research_tier", 1)):
        mid = it["id"]
        info = mats.CATALOG[mid]
        owned = inventory["stock"].get(mid, {}).get("qty", 0)
        need = 1 if mid in next_kit else 0
        r = pygame.Rect(100, y, 616, 48)
        sel = ui_state.get("selected") == mid
        pygame.draw.rect(surface, ui.C_SURFACE_2 if sel else ui.C_SURFACE, r, border_radius=6)
        pygame.draw.rect(surface, ui.C_SIGNAL if sel else ui.C_EDGE, r, 1, border_radius=6)
        wb.draw_material_icon(surface, mid, (r.x + 22, r.centery), 14)
        ui.label(surface, fonts, info["name"], (r.x + 44, r.y + 6), ui.C_TEXT, "small")
        req_txt = f"Need {need}" if need else "—"
        ui.label(
            surface, fonts,
            f"{it['price']} RP   Own {owned}   {req_txt}",
            (r.x + 44, r.y + 26),
            ui.C_MUTED,
            "small",
        )
        row_rects[mid] = r
        y += 54
        if y > 580:
            break

    # Purchase panel for selection
    detail = pygame.Rect(752, 110, 440, 500)
    pygame.draw.rect(surface, ui.C_BG, detail, border_radius=8)
    pygame.draw.rect(surface, ui.C_EDGE, detail, 1, border_radius=8)
    buy = pygame.Rect(0, 0, 0, 0)
    sel = ui_state.get("selected")
    if sel:
        info = mats.CATALOG[sel]
        it = next(x for x in CATALOGUE if x["id"] == sel)
        owned = inventory["stock"].get(sel, {}).get("qty", 0)
        wb.draw_material_icon(surface, sel, (detail.centerx, 180), 28)
        ui.centered(surface, fonts, info["name"], (detail.centerx, 230), ui.C_TEXT, "body")
        ui.centered(surface, fonts, it["desc"], (detail.centerx, 262), ui.C_MUTED, "small")
        ui.centered(surface, fonts, f"{it['price']} RP each", (detail.centerx, 300), ui.C_SIGNAL, "body")
        ui.centered(surface, fonts, f"Owned: {owned}", (detail.centerx, 336), ui.C_MUTED, "small")
        ok, msg = can_buy(campaign, sel, 1)
        ui.centered(surface, fonts, ui.truncate(msg, 40), (detail.centerx, 380), ui.C_AMBER if not ok else ui.C_MUTED, "small")
        buy = pygame.Rect(0, 0, 200, 44)
        buy.center = (detail.centerx, 440)
        ui.button(surface, buy, "BUY", fonts, mouse_pos, accent=ok)
        buttons[sel] = buy
    else:
        ui.centered(surface, fonts, "Select a material", (detail.centerx, 320), ui.C_MUTED, "body")

    close = pygame.Rect(520, 640, 240, 36)
    ui.button(surface, close, "CLOSE", fonts, mouse_pos, small=True)
    return {"buy": buttons, "close": close, "rows": row_rects, "ui_state": ui_state}
