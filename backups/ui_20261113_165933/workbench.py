"""Reusable Assembly Workbench — click-to-select materials, compatible slot highlights."""

from __future__ import annotations

import pygame

from systems import challenge_ui as ui
from systems import materials as mats

# Session UX prefs (shared)
_SESSION = {"guided": True, "mode_chosen": False}


def is_guided() -> bool:
    return bool(_SESSION.get("guided", True))


def set_guided(value: bool) -> None:
    _SESSION["guided"] = bool(value)
    _SESSION["mode_chosen"] = True


def toggle_guided() -> bool:
    _SESSION["guided"] = not _SESSION.get("guided", True)
    _SESSION["mode_chosen"] = True
    return _SESSION["guided"]


def draw_material_icon(surface, mid: str, center, size: int = 18) -> None:
    """Procedural icon by material type (no asset dependency)."""
    x, y = center
    info = mats.CATALOG.get(mid, {})
    icon = info.get("icon", "box")
    if icon == "wire":
        pygame.draw.arc(surface, ui.C_AMBER, (x - size, y - size // 2, size * 2, size), 0.2, 2.8, 3)
    elif icon == "amp":
        pygame.draw.polygon(surface, ui.C_CYAN, [(x - size, y + size // 2), (x, y - size), (x + size, y + size // 2)])
    elif icon == "fuse":
        pygame.draw.rect(surface, ui.C_AMBER, (x - 6, y - size, 12, size * 2), border_radius=3)
        pygame.draw.line(surface, ui.C_RED, (x, y - size + 4), (x, y + size - 4), 2)
    elif icon == "cable":
        pygame.draw.line(surface, (60, 60, 70), (x - size, y), (x + size, y), 6)
        pygame.draw.line(surface, ui.C_CYAN, (x - size, y), (x + size, y), 2)
    elif icon == "battery":
        pygame.draw.rect(surface, ui.C_GREEN, (x - 10, y - size // 2, 20, size), border_radius=3)
        pygame.draw.rect(surface, (220, 220, 220), (x - 4, y - size // 2 - 4, 8, 5))
    elif icon == "motor":
        pygame.draw.circle(surface, (180, 180, 190), (x, y), size // 2 + 2)
        pygame.draw.circle(surface, (40, 40, 45), (x, y), 4)
    elif icon == "lube":
        pygame.draw.ellipse(surface, (100, 180, 220), (x - 8, y - size, 16, size * 2))
    elif icon == "bracket":
        pygame.draw.lines(surface, ui.C_MUTED, False, [(x - size, y + size // 2), (x - size, y - size // 2), (x + size, y - size // 2)], 3)
    else:
        pygame.draw.rect(surface, ui.C_MUTED, (x - size // 2, y - size // 2, size, size), 2)


def incompatibility_message(mid: str, slot_needs: str, slot_label: str) -> str:
    want = mats.CATALOG.get(slot_needs, {}).get("name", slot_needs)
    got = mats.CATALOG.get(mid, {}).get("name", mid)
    if slot_needs == "spare_fuse":
        return f"{got} cannot be installed in the fuse holder. This slot needs a {want}."
    if slot_needs == "signal_amplifier":
        return f"{got} does not belong in the amplifier bay. Install a {want}."
    if slot_needs == "copper_wire":
        return f"{got} cannot fill the copper coil path. This slot requires {want}."
    if slot_needs == "servo_motor":
        return f"{got} is not a drive motor. The motor bay needs a {want}."
    if slot_needs == "battery_cell":
        return f"{got} cannot power this bay. Install a {want}."
    if slot_needs == "lubricant":
        return f"{got} will not free the wheel jam. Use a {want}."
    if slot_needs == "metal_bracket":
        return f"{got} is not structural support. This mount needs a {want}."
    return f"{got} does not fit {slot_label}. Required: {want}. Check the diagram."


def draw_supply_panel(
    surface,
    fonts,
    inventory: dict,
    mouse_pos,
    mission: str | None,
    panel_rect: pygame.Rect,
    title: str = "YOUR SUPPLIES",
) -> dict:
    """Draw clickable supply list. Returns {mid: rect}."""
    pygame.draw.rect(surface, (32, 20, 14), panel_rect, border_radius=10)
    pygame.draw.rect(surface, ui.C_CYAN, panel_rect, 2, border_radius=10)
    ui.label(surface, fonts, title, (panel_rect.x + 12, panel_rect.y + 10), ui.C_CYAN, "small")
    req = mats.MISSION_REQUIREMENTS.get(mission or "", [])
    rects = {}
    y = panel_rect.y + 40
    row = 0
    for mid, info in mats.CATALOG.items():
        s = inventory["stock"].get(mid, {"qty": 0, "reserved": 0})
        if s["qty"] <= 0 and mid not in req:
            continue
        avail = mats.available(inventory["stock"], mid)
        r = pygame.Rect(panel_rect.x + 8, y, panel_rect.w - 16, 52)
        selected = inventory.get("selected") == mid
        needed = mid in req
        missing = needed and s["qty"] < 1
        fill = (50, 35, 22) if selected else (40, 25, 16)
        pygame.draw.rect(surface, fill, r, border_radius=8)
        border = ui.C_GREEN if selected else (ui.C_AMBER if needed else ui.C_EDGE_DIM)
        if missing:
            border = ui.C_RED
        if r.collidepoint(mouse_pos):
            border = ui.C_CYAN
        pygame.draw.rect(surface, border, r, 2, border_radius=8)
        draw_material_icon(surface, mid, (r.x + 22, r.centery), 14)
        name_col = ui.C_GREEN if selected else (ui.C_RED if missing else ui.C_TEXT)
        ui.label(surface, fonts, info["name"], (r.x + 44, r.y + 6), name_col, "small")
        tag = "REQUIRED" if needed else info["category"]
        ui.label(surface, fonts, f"×{avail}  [{tag}]", (r.x + 44, r.y + 26), ui.C_MUTED, "small")
        rects[mid] = r
        y += 58
        row += 1
        if y + 56 > panel_rect.bottom:
            break
    if row == 0:
        ui.centered(surface, fonts, "No supplies yet — explore and collect (E).", panel_rect.center, ui.C_MUTED, "small")
    return rects


def draw_slot(
    surface,
    fonts,
    rect: pygame.Rect,
    label: str,
    installed: str | None,
    needs: str,
    selected_mid: str | None,
    guided: bool,
    mouse_pos,
    flash_incompatible: bool = False,
) -> None:
    compatible = selected_mid is not None and selected_mid == needs
    incompatible = selected_mid is not None and selected_mid != needs
    if installed:
        border = ui.C_GREEN
        fill = (28, 45, 30)
    elif flash_incompatible:
        border = ui.C_RED
        fill = (55, 22, 18)
    elif compatible and guided:
        border = ui.C_CYAN
        fill = (25, 45, 50)
    elif incompatible and selected_mid:
        border = ui.C_EDGE_DIM
        fill = (40, 25, 16)
    else:
        border = ui.C_EDGE
        fill = (35, 22, 16)
    if rect.collidepoint(mouse_pos) and selected_mid:
        border = ui.C_CYAN if compatible else ui.C_RED
    pygame.draw.rect(surface, fill, rect, border_radius=10)
    pygame.draw.rect(surface, border, rect, 3 if (compatible and guided) else 2, border_radius=10)
    ui.centered(surface, fonts, label, (rect.centerx, rect.y + 18), ui.C_MUTED, "small")
    if installed:
        draw_material_icon(surface, installed, (rect.centerx, rect.centery + 4), 16)
        ui.centered(surface, fonts, mats.CATALOG[installed]["name"][:18], (rect.centerx, rect.bottom - 18), ui.C_TEXT, "small")
    else:
        need_name = mats.CATALOG.get(needs, {}).get("name", needs)
        if guided:
            ui.centered(surface, fonts, f"Needs: {need_name}", (rect.centerx, rect.centery + 4), ui.C_AMBER, "small")
        else:
            ui.centered(surface, fonts, "EMPTY SLOT", (rect.centerx, rect.centery + 4), ui.C_RED, "small")
        if compatible and guided:
            ui.centered(surface, fonts, "CLICK TO INSTALL", (rect.centerx, rect.bottom - 16), ui.C_CYAN, "small")


def draw_workbench_chrome(
    surface,
    fonts,
    mouse_pos,
    title: str,
    subtitle: str,
    hint: str,
    progress: float,
    progress_label: str,
    guided: bool,
) -> dict:
    """Outer frame + mode toggle + hint + progress. Returns button rects."""
    ui.dim_backdrop(surface, 145)
    box = pygame.Rect(40, 24, 1200, 672)
    ui.panel(surface, box)
    ui.header(surface, fonts, box, title, subtitle)
    mode_btn = pygame.Rect(980, 55, 220, 36)
    mode_label = "GUIDED MODE" if guided else "CHALLENGE MODE"
    ui.button(surface, mode_btn, mode_label, fonts, mouse_pos, small=True)
    if guided:
        ui.objective_bar(surface, fonts, hint[:100] if hint else "Select a supply, then click a highlighted compatible slot.", y=100)
    else:
        ui.objective_bar(surface, fonts, hint[:100] if hint else "Assemble using your clues and supplies.", y=100)
    # Progress
    ui.label(surface, fonts, progress_label, (60, 640), ui.C_CYAN, "small")
    ui.meter(surface, pygame.Rect(220, 645, 400, 14), progress, 1.0, ui.C_GREEN if progress >= 1.0 else ui.C_CYAN)
    return {"mode": mode_btn, "box": box}


def try_install(inventory, slots_state: dict, slot_key: str, slot_meta: dict) -> tuple[bool, str]:
    """
    Click-to-install into a slot.
    slots_state[slot_key] holds installed mid or None.
    Returns (ok, message). Rejects incompatible without consuming.
    """
    mid = inventory.get("selected")
    if not mid:
        return False, "Select a material from YOUR SUPPLIES first, then click a slot."
    needs = slot_meta["needs"]
    if mid != needs:
        return False, incompatibility_message(mid, needs, slot_meta.get("label", "this slot"))
    if not mats.can_reserve(inventory["stock"], mid, 1):
        return False, f"No available {mats.CATALOG[mid]['name']} (already installed or none left)."
    # Remove previous if any
    old = slots_state.get(slot_key)
    if old:
        mats.release(inventory["stock"], old, 1)
    mats.reserve(inventory["stock"], mid, 1)
    slots_state[slot_key] = mid
    inventory["selected"] = None
    return True, f"Installed {mats.CATALOG[mid]['name']} into {slot_meta.get('label', slot_key)}."


def remove_install(inventory, slots_state: dict, slot_key: str) -> str:
    old = slots_state.get(slot_key)
    if not old:
        return "Slot is already empty."
    mats.release(inventory["stock"], old, 1)
    slots_state[slot_key] = None
    return f"Removed {mats.CATALOG[old]['name']} — returned to supplies."


def clear_all(inventory, slots_state: dict) -> None:
    for key in list(slots_state.keys()):
        old = slots_state.get(key)
        if old:
            mats.release(inventory["stock"], old, 1)
            slots_state[key] = None


def handle_supply_click(inventory, supply_rects: dict, pos) -> bool:
    for mid, rect in supply_rects.items():
        if rect.collidepoint(pos):
            avail = mats.available(inventory["stock"], mid)
            if avail <= 0 and inventory["stock"].get(mid, {}).get("qty", 0) <= 0:
                return True
            inventory["selected"] = None if inventory.get("selected") == mid else mid
            return True
    return False
