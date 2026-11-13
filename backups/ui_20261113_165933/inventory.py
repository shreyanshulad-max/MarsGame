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
    ui.dim_backdrop(surface, 175)
    panel = pygame.Rect(140, 40, 1000, 640)
    ui.panel(surface, panel)
    ui.header(
        surface, fonts, panel,
        "MATERIAL INVENTORY",
        "Click a material to select it · Press I to close",
    )

    mission = inv.get("highlight_mission")
    req = mats.MISSION_REQUIREMENTS.get(mission, []) if mission else []
    inv["row_rects"] = {}

    # Left list
    list_box = pygame.Rect(170, 130, 560, 420)
    pygame.draw.rect(surface, (32, 20, 14), list_box, border_radius=10)
    pygame.draw.rect(surface, ui.C_CYAN, list_box, 1, border_radius=10)

    y = 145
    for mid, info in mats.CATALOG.items():
        s = inv["stock"].get(mid, {"qty": 0, "reserved": 0})
        if s["qty"] <= 0 and mid not in req:
            continue
        r = pygame.Rect(185, y, 530, 56)
        selected = inv.get("selected") == mid
        needed = mid in req
        missing = needed and s["qty"] < 1
        fill = (48, 32, 20) if selected else (38, 24, 16)
        pygame.draw.rect(surface, fill, r, border_radius=8)
        border = ui.C_GREEN if selected else (ui.C_AMBER if needed else ui.C_EDGE_DIM)
        if missing:
            border = ui.C_RED
        if r.collidepoint(mouse_pos):
            border = ui.C_CYAN
        pygame.draw.rect(surface, border, r, 2, border_radius=8)
        wb.draw_material_icon(surface, mid, (r.x + 26, r.centery), 16)
        tag = "★ REQUIRED" if needed else info["category"].upper()
        ui.label(surface, fonts, info["name"], (r.x + 52, r.y + 8), ui.C_TEXT if not missing else ui.C_RED, "body")
        ui.label(surface, fonts, f"Qty {qty_line(inv, mid)}   {tag}", (r.x + 52, r.y + 32), ui.C_MUTED, "small")
        inv["row_rects"][mid] = r
        y += 64
        if y > 520:
            break

    # Detail panel
    detail = pygame.Rect(750, 130, 360, 420)
    pygame.draw.rect(surface, (32, 20, 14), detail, border_radius=10)
    pygame.draw.rect(surface, ui.C_EDGE, detail, 2, border_radius=10)
    mid = inv.get("selected") or inv.get("detail_mid")
    if mid and mid in mats.CATALOG:
        info = mats.CATALOG[mid]
        wb.draw_material_icon(surface, mid, (detail.centerx, 180), 28)
        ui.centered(surface, fonts, info["name"], (detail.centerx, 230), ui.C_TEXT, "title")
        ui.centered(surface, fonts, f"Available: {qty_line(inv, mid)}", (detail.centerx, 270), ui.C_CYAN, "body")
        ui.label(surface, fonts, "Purpose:", (770, 310), ui.C_AMBER, "small")
        # wrap description
        desc = info["description"]
        ui.label(surface, fonts, desc[:36], (770, 338), ui.C_TEXT, "small")
        ui.label(surface, fonts, desc[36:72], (770, 360), ui.C_TEXT, "small")
        ui.label(surface, fonts, f"Used in: {', '.join(info['used_in'])}", (770, 400), ui.C_MUTED, "small")
        ui.label(surface, fonts, f"Find near: {info['location']}", (770, 430), ui.C_MUTED, "small")
        if mid in req:
            ui.centered(surface, fonts, "Needed for current mission", (detail.centerx, 490), ui.C_AMBER, "small")
    else:
        ui.centered(surface, fonts, "Select a material", (detail.centerx, 300), ui.C_MUTED, "body")
        ui.centered(surface, fonts, "to see its purpose.", (detail.centerx, 340), ui.C_MUTED, "body")

    # Missing supplies banner
    missing = missing_for_mission(inv, mission)
    if mission and missing:
        ui.centered(
            surface, fonts,
            "Missing: " + "; ".join(f"{n} ({loc})" for n, loc in missing[:3]),
            (panel.centerx, 580),
            ui.C_RED,
            "small",
        )
    elif mission:
        ui.centered(surface, fonts, "All required mission supplies collected.", (panel.centerx, 580), ui.C_GREEN, "body")

    if inv.get("selected"):
        ui.centered(
            surface, fonts,
            f"Selected: {mats.CATALOG[inv['selected']]['name']} — open an assembly workbench to install",
            (panel.centerx, 620),
            ui.C_CYAN,
            "small",
        )


def handle_inventory_click(inv: dict, pos) -> bool:
    if not inv["open"]:
        return False
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
    if inv["toast_timer"] <= 0 or not inv["toast"]:
        return
    w, h = 560, 44
    x = surface.get_width() // 2 - w // 2
    y = 90
    banner = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(banner, (20, 12, 10, 210), (0, 0, w, h), border_radius=10)
    pygame.draw.rect(banner, (80, 220, 140, 200), (0, 0, w, h), 2, border_radius=10)
    surface.blit(banner, (x, y))
    label = fonts["body"].render(inv["toast"], True, (120, 220, 140))
    surface.blit(label, label.get_rect(center=(surface.get_width() // 2, y + h // 2)))
