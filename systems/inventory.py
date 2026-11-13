"""Persistent material inventory with clear selection and mission highlighting."""

from __future__ import annotations

import pygame

from systems import challenge_ui as ui
from systems import materials as mats
from systems import workbench as wb


def make_inventory() -> dict:
    return {
        "stock": mats.empty_stock(),
        "items": [],
        "toast": "",
        "toast_timer": 0.0,
        "open": False,
        "selected": None,
        "highlight_mission": None,
        "detail_mid": None,
        "row_rects": {},
        "filter": "all",  # all | required | available
        "filter_rects": {},
    }


def add_item(inv: dict, item: dict) -> bool:
    mid = item.get("material")
    if mid:
        if any(i.get("uid") == item["id"] for i in inv["items"]):
            return False
        qty = int(item.get("qty", 1))
        mats.add_material(inv["stock"], mid, qty)
        entry = mats.catalog_entry(mid)
        inv["items"].append(
            {
                "id": item["id"],
                "uid": item["id"],
                "name": entry["name"],
                "kind": entry["category"],
                "material": mid,
                "qty": qty,
            }
        )
        inv["toast"] = f"Collected: {entry['name']} ×{qty}"
        inv["toast_timer"] = 2.6
        return True

    if any(i["id"] == item["id"] for i in inv["items"]):
        return False
    inv["items"].append({"id": item["id"], "name": item["name"], "kind": item.get("kind", "sample")})
    inv["toast"] = f"Collected: {item['name']}"
    inv["toast_timer"] = 2.4
    return True


def update_inventory(inv: dict, dt: float) -> None:
    if inv["toast_timer"] > 0:
        inv["toast_timer"] -= dt
        if inv["toast_timer"] <= 0:
            inv["toast"] = ""


def qty_line(inv: dict, mid: str) -> str:
    s = inv["stock"].get(mid, {"qty": 0, "reserved": 0})
    avail = mats.available(inv["stock"], mid)
    if s["reserved"]:
        return f"{avail} ready · {s['reserved']} installed"
    return str(avail)


def missing_for_mission(inv: dict, mission: str | None) -> list[tuple[str, str]]:
    """Return [(name, location_clue), ...] for missing required materials."""
    out = []
    if not mission:
        return out
    for mid in mats.MISSION_REQUIREMENTS.get(mission, []):
        if inv["stock"].get(mid, {}).get("qty", 0) < 1:
            info = mats.CATALOG[mid]
            out.append((info["name"], info.get("location", "Unknown area")))
    return out


def draw_inventory(surface, fonts, inv: dict, mouse_pos) -> None:
    if not inv["open"]:
        return
    ui.dim_backdrop(surface, 160)
    panel = pygame.Rect(120, 48, 1040, 624)
    ui.panel(surface, panel)
    ui.header(
        surface, fonts, panel,
        "INVENTORY",
        "Select a material for details · I to close",
    )

    mission = inv.get("highlight_mission")
    req = mats.MISSION_REQUIREMENTS.get(mission, []) if mission else []
    inv["row_rects"] = {}
    inv["filter_rects"] = {}

    # Filters
    fx = 150
    for key, lab in (("all", "All"), ("required", "Required"), ("available", "Available")):
        r = pygame.Rect(fx, 108, 100, 28)
        active = inv.get("filter", "all") == key
        pygame.draw.rect(surface, ui.C_SURFACE_2 if active else ui.C_BG, r, border_radius=6)
        pygame.draw.rect(surface, ui.C_SIGNAL if active else ui.C_EDGE, r, 1, border_radius=6)
        ui.centered(surface, fonts, lab, r.center, ui.C_TEXT if active else ui.C_MUTED, "small")
        inv["filter_rects"][key] = r
        fx += 110

    # Left list
    list_box = pygame.Rect(150, 150, 520, 440)
    pygame.draw.rect(surface, ui.C_BG, list_box, border_radius=8)
    pygame.draw.rect(surface, ui.C_EDGE, list_box, 1, border_radius=8)

    filt = inv.get("filter", "all")
    y = 162
    for mid, info in mats.CATALOG.items():
        s = inv["stock"].get(mid, {"qty": 0, "reserved": 0})
        needed = mid in req
        if s["qty"] <= 0 and mid not in req:
            continue
        if filt == "required" and not needed:
            continue
        if filt == "available" and s["qty"] <= 0:
            continue
        r = pygame.Rect(162, y, 496, 48)
        selected = inv.get("selected") == mid or inv.get("detail_mid") == mid
        missing = needed and s["qty"] < 1
        fill = ui.C_SURFACE_2 if selected else ui.C_SURFACE
        pygame.draw.rect(surface, fill, r, border_radius=6)
        border = ui.C_SIGNAL if selected else (ui.C_RED if missing else (ui.C_AMBER if needed else ui.C_EDGE_DIM))
        if r.collidepoint(mouse_pos):
            border = ui.C_SIGNAL
        pygame.draw.rect(surface, border, r, 1, border_radius=6)
        wb.draw_material_icon(surface, mid, (r.x + 22, r.centery), 14)
        tag = "REQ" if needed else info["category"][:8].upper()
        ui.label(surface, fonts, info["name"], (r.x + 44, r.y + 6), ui.C_TEXT if not missing else ui.C_RED, "small")
        ui.label(surface, fonts, f"×{qty_line(inv, mid)}  {tag}", (r.x + 44, r.y + 26), ui.C_MUTED, "small")
        inv["row_rects"][mid] = r
        y += 54
        if y > 560:
            break

    # Detail — only when selected
    detail = pygame.Rect(690, 150, 440, 440)
    pygame.draw.rect(surface, ui.C_BG, detail, border_radius=8)
    pygame.draw.rect(surface, ui.C_EDGE, detail, 1, border_radius=8)
    mid = inv.get("selected") or inv.get("detail_mid")
    if mid and mid in mats.CATALOG:
        info = mats.CATALOG[mid]
        wb.draw_material_icon(surface, mid, (detail.centerx, 200), 26)
        ui.centered(surface, fonts, info["name"], (detail.centerx, 250), ui.C_TEXT, "body")
        ui.centered(surface, fonts, f"Qty  {qty_line(inv, mid)}", (detail.centerx, 282), ui.C_SIGNAL, "small")
        ui.label(surface, fonts, "Purpose", (710, 320), ui.C_MUTED, "small")
        desc = info["description"]
        ui.label(surface, fonts, ui.truncate(desc, 42), (710, 344), ui.C_TEXT, "small")
        ui.label(surface, fonts, ui.truncate(desc[42:], 42) if len(desc) > 42 else "", (710, 364), ui.C_TEXT, "small")
        ui.label(surface, fonts, f"Used in: {', '.join(info['used_in'])}", (710, 400), ui.C_MUTED, "small")
        ui.label(surface, fonts, f"Find near: {info['location']}", (710, 424), ui.C_MUTED, "small")
        if mid in req:
            ui.centered(surface, fonts, "Needed for current mission", (detail.centerx, 520), ui.C_AMBER, "small")
    else:
        ui.centered(surface, fonts, "Select a material", (detail.centerx, 340), ui.C_MUTED, "body")

    missing = missing_for_mission(inv, mission)
    if mission and missing:
        ui.centered(
            surface, fonts,
            "Missing: " + "; ".join(f"{n}" for n, _ in missing[:3]),
            (panel.centerx, 620),
            ui.C_AMBER,
            "small",
        )


def handle_inventory_click(inv: dict, pos) -> bool:
    if not inv["open"]:
        return False
    for key, rect in inv.get("filter_rects", {}).items():
        if rect.collidepoint(pos):
            inv["filter"] = key
            return True
    for mid, rect in inv.get("row_rects", {}).items():
        if rect.collidepoint(pos):
            s = inv["stock"].get(mid, {"qty": 0})
            if s["qty"] > 0:
                inv["selected"] = None if inv.get("selected") == mid else mid
                inv["detail_mid"] = mid
            else:
                inv["detail_mid"] = mid
            return True
    return False


def draw_toast(surface, fonts, inv: dict) -> None:
    """Legacy toast — prefer notify system; kept for compatibility."""
    if inv["toast_timer"] <= 0 or not inv["toast"]:
        return
    w, h = 400, 34
    x = surface.get_width() // 2 - w // 2
    y = 72
    banner = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(banner, (*ui.C_BG, 210), (0, 0, w, h), border_radius=6)
    pygame.draw.rect(banner, (*ui.C_GREEN, 180), (0, 0, w, h), 1, border_radius=6)
    surface.blit(banner, (x, y))
    label = fonts["small"].render(inv["toast"][:48], True, ui.C_TEXT)
    surface.blit(label, label.get_rect(center=(surface.get_width() // 2, y + h // 2)))
