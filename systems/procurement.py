"""Research-gated Procurement — spend RP on current-mission materials only."""

from __future__ import annotations

import pygame

from systems import campaign as camp
from systems import challenge_ui as ui
from systems import economy_config as econ
from systems import materials as mats
from systems import workbench as wb

CATALOGUE = [
    {"id": "copper_wire", "mission": "mission_1", "essential": True, "desc": "Antenna coil conductor"},
    {"id": "signal_amplifier", "mission": "mission_1", "essential": True, "desc": "Boosts weak uplink"},
    {"id": "spare_fuse", "mission": "mission_1", "essential": True, "desc": "Protects power bus"},
    {"id": "insulated_cable", "mission": "mission_2", "essential": True, "desc": "Solar/habitat power cable"},
    {"id": "spare_fuse_m2", "mission": "mission_2", "material": "spare_fuse", "essential": True, "desc": "Protects power bus"},
    {"id": "battery_cell", "mission": "mission_3", "essential": True, "desc": "Portable energy cell"},
    {"id": "servo_motor", "mission": "mission_3", "essential": True, "desc": "Rover drive motor"},
    {"id": "lubricant", "mission": "mission_3", "essential": True, "desc": "Frees jammed wheels"},
    {"id": "metal_bracket", "mission": "mission_3", "essential": True, "desc": "Structural support"},
]

# spare_fuse appears in mission_1 and mission_2 kits — catalogue uses real material ids
def _normalize_catalogue() -> list[dict]:
    out = []
    seen = set()
    for it in CATALOGUE:
        mid = it.get("material") or it["id"]
        key = (it["mission"], mid)
        if key in seen:
            continue
        seen.add(key)
        row = dict(it)
        row["id"] = mid
        row["price"] = int(econ.PROCUREMENT_PRICES.get(mid, 9999))
        out.append(row)
    # Ensure mission_2 spare_fuse listed
    if ("mission_2", "spare_fuse") not in seen:
        out.append(
            {
                "id": "spare_fuse",
                "mission": "mission_2",
                "price": int(econ.PROCUREMENT_PRICES["spare_fuse"]),
                "essential": True,
                "desc": "Protects power bus",
            }
        )
    return out


CATALOGUE_NORM = None


def catalogue() -> list[dict]:
    global CATALOGUE_NORM
    if CATALOGUE_NORM is None:
        CATALOGUE_NORM = _normalize_catalogue()
    return CATALOGUE_NORM


def price_of(mid: str) -> int:
    return int(econ.PROCUREMENT_PRICES.get(mid, 9999))


def current_store_mission(campaign: dict) -> str | None:
    return camp.active_mission_id(campaign)


def items_for_campaign(campaign: dict) -> list[dict]:
    """Only current mission materials — never future kits."""
    mid = current_store_mission(campaign)
    if mid is None:
        return []
    # Deduplicate by material id for the active mission
    out = []
    seen = set()
    for it in catalogue():
        if it["mission"] != mid:
            continue
        if it["id"] in seen:
            continue
        seen.add(it["id"])
        out.append(it)
    return out


def items_for_tier(tier: int) -> list[dict]:
    """Legacy helper used by older tests — maps tier to mission pool."""
    mission = {1: "mission_1", 2: "mission_2", 3: "mission_3"}.get(int(tier), "mission_1")
    out = []
    seen = set()
    for it in catalogue():
        if it["mission"] != mission:
            continue
        if it["id"] in seen:
            continue
        seen.add(it["id"])
        out.append(it)
    return out


def remaining_need(campaign: dict, inventory: dict, mid: str) -> int:
    mission = current_store_mission(campaign)
    if not mission:
        return 0
    reqs = mats.required_quantities_for_mission(mission)
    need = int(reqs.get(mid, 0))
    owned = int(inventory["stock"].get(mid, {}).get("qty", 0))
    return max(0, need - owned)


def can_buy(campaign: dict, inventory: dict, mid: str, qty: int = 1) -> tuple[bool, str]:
    mission = current_store_mission(campaign)
    if mission is None:
        return False, "No active mission supplies."
    item = next((x for x in items_for_campaign(campaign) if x["id"] == mid), None)
    if not item:
        return False, "Not in the current mission catalogue."
    if mid not in mats.required_quantities_for_mission(mission):
        return False, "Material is not part of this mission kit."

    rem = remaining_need(campaign, inventory, mid)
    if rem <= 0:
        return False, "Required quantity secured."
    if qty > rem:
        return False, f"Only {rem} more needed."

    cost = price_of(mid) * qty
    if campaign["research_points"] < cost:
        return False, "Insufficient Research Points. Complete an optional research activity to earn more."
    return True, f"Buy {mats.CATALOG[mid]['name']} ×{qty} for {cost} RP?"


def purchase(campaign: dict, inventory: dict, mid: str, qty: int = 1) -> tuple[bool, str]:
    ok, msg = can_buy(campaign, inventory, mid, qty)
    if not ok:
        return False, msg
    cost = price_of(mid) * qty
    if not camp.spend_rp(campaign, cost):
        return False, "Purchase failed — insufficient RP."
    mats.add_material(inventory["stock"], mid, qty)
    purchases = campaign.setdefault("material_purchases", {})
    purchases[mid] = purchases.get(mid, 0) + qty
    campaign["purchased_materials"] = dict(purchases)
    campaign["reward_log"].append(f"Purchased {mats.CATALOG[mid]['name']} ×{qty} (−{cost} RP)")

    # Reconcile world caches when requirement is fully secured
    mission = current_store_mission(campaign)
    if mission:
        req = mats.required_quantities_for_mission(mission).get(mid, 0)
        owned = inventory["stock"].get(mid, {}).get("qty", 0)
        from systems import caches as cache_sys

        cache_sys.reconcile_after_purchase(campaign, mid, owned, req)
    return True, f"Purchased {mats.CATALOG[mid]['name']} ×{qty}."


def draw_shop(surface, fonts, mouse_pos, campaign: dict, inventory: dict, ui_state: dict | None = None) -> dict:
    """Clean catalogue + purchase panel for selected item only."""
    if ui_state is None:
        ui_state = {"selected": None}

    mission = current_store_mission(campaign)
    ui.dim_backdrop(surface, 150)
    box = pygame.Rect(64, 32, 1152, 656)
    ui.panel(surface, box)
    mname = camp.MISSION_META[mission]["name"] if mission else "—"
    ui.header(
        surface, fonts, box,
        "PROCUREMENT",
        f"{campaign['research_points']} RP   ·   {mname} supplies only   ·   Research optional",
    )

    list_box = pygame.Rect(88, 110, 640, 500)
    pygame.draw.rect(surface, ui.C_BG, list_box, border_radius=8)
    pygame.draw.rect(surface, ui.C_EDGE, list_box, 1, border_radius=8)

    buttons = {}
    row_rects = {}
    y = 124
    items = items_for_campaign(campaign)
    if not items:
        ui.centered(surface, fonts, "No active mission supplies.", (list_box.centerx, 320), ui.C_MUTED, "body")
    for it in items:
        mid = it["id"]
        info = mats.CATALOG[mid]
        owned = inventory["stock"].get(mid, {}).get("qty", 0)
        need = mats.required_quantities_for_mission(mission or "").get(mid, 0)
        rem = max(0, need - owned)
        r = pygame.Rect(100, y, 616, 48)
        sel = ui_state.get("selected") == mid
        pygame.draw.rect(surface, ui.C_SURFACE_2 if sel else ui.C_SURFACE, r, border_radius=6)
        pygame.draw.rect(surface, ui.C_SIGNAL if sel else ui.C_EDGE, r, 1, border_radius=6)
        wb.draw_material_icon(surface, mid, (r.x + 22, r.centery), 14)
        ui.label(surface, fonts, info["name"], (r.x + 44, r.y + 6), ui.C_TEXT, "small")
        ui.label(
            surface, fonts,
            f"{it['price']} RP   Own {owned}/{need}   Need {rem}",
            (r.x + 44, r.y + 26),
            ui.C_MUTED,
            "small",
        )
        row_rects[mid] = r
        y += 54
        if y > 580:
            break

    detail = pygame.Rect(752, 110, 440, 500)
    pygame.draw.rect(surface, ui.C_BG, detail, border_radius=8)
    pygame.draw.rect(surface, ui.C_EDGE, detail, 1, border_radius=8)
    buy = pygame.Rect(0, 0, 0, 0)
    sel = ui_state.get("selected")
    if sel and any(x["id"] == sel for x in items):
        info = mats.CATALOG[sel]
        it = next(x for x in items if x["id"] == sel)
        owned = inventory["stock"].get(sel, {}).get("qty", 0)
        wb.draw_material_icon(surface, sel, (detail.centerx, 180), 28)
        ui.centered(surface, fonts, info["name"], (detail.centerx, 230), ui.C_TEXT, "body")
        ui.centered(surface, fonts, it["desc"], (detail.centerx, 262), ui.C_MUTED, "small")
        ui.centered(surface, fonts, f"{it['price']} RP each", (detail.centerx, 300), ui.C_SIGNAL, "body")
        ui.centered(surface, fonts, f"Owned: {owned}", (detail.centerx, 336), ui.C_MUTED, "small")
        ok, msg = can_buy(campaign, inventory, sel, 1)
        ui.centered(
            surface, fonts, ui.truncate(msg, 42), (detail.centerx, 380),
            ui.C_AMBER if not ok else ui.C_MUTED, "small",
        )
        buy = pygame.Rect(0, 0, 200, 44)
        buy.center = (detail.centerx, 440)
        ui.button(surface, buy, "BUY", fonts, mouse_pos, accent=ok)
        buttons[sel] = buy
    else:
        ui.centered(surface, fonts, "Select a material", (detail.centerx, 320), ui.C_MUTED, "body")

    close = pygame.Rect(520, 640, 240, 36)
    ui.button(surface, close, "CLOSE", fonts, mouse_pos, small=True)
    return {"buy": buttons, "close": close, "rows": row_rects, "ui_state": ui_state}
