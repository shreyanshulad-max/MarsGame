"""Reusable Assembly Workbench — click-to-select materials, compatible slot highlights."""

from __future__ import annotations

import os
import pygame

from systems import challenge_ui as ui
from systems import materials as mats

# Session UX prefs (shared)
_SESSION = {
    "guided": True,
    "mode_chosen": False,
    "show_other_supplies": False,
    "supply_scroll": 0,
}

# Temporary development diagnostics (stdout only — never player-facing UI)
# Set MARS_DEBUG_WORKBENCH=1 to print inventory/filter diagnostics to stdout
DEBUG_WORKBENCH = os.environ.get("MARS_DEBUG_WORKBENCH", "0") == "1"


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


def required_ids_for_mission(mission: str | None) -> list[str]:
    """Stable required material IDs for a workbench mission key (ch1/ch2/ch3)."""
    return list(mats.MISSION_REQUIREMENTS.get(mission or "", []))


def required_qty_map(mission: str | None) -> dict[str, int]:
    """Required quantity per material ID for the active workbench recipe."""
    req = required_ids_for_mission(mission)
    out: dict[str, int] = {}
    for mid in req:
        out[mid] = out.get(mid, 0) + 1
    # Prefer campaign kit counts when mission maps to mission_N
    challenge_to_mission = {v: k for k, v in mats.MISSION_CHALLENGE.items()}
    kit_key = challenge_to_mission.get(mission or "")
    if kit_key:
        for mid, need in mats.required_quantities_for_mission(kit_key).items():
            out[mid] = int(need)
    return out


def installed_material_ids(slots_state: dict | None) -> set[str]:
    if not slots_state:
        return set()
    return {mid for mid in slots_state.values() if mid}


def build_supply_rows(
    inventory: dict,
    mission: str | None,
    slots_state: dict | None = None,
) -> dict:
    """
    Build authoritative supply rows from central inventory + recipe.
    Required materials always appear (even at qty 0). Other owned items are secondary.
    """
    stock = inventory.get("stock") or {}
    req_ids = required_ids_for_mission(mission)
    req_qty = required_qty_map(mission)
    installed = installed_material_ids(slots_state)
    # Also treat reserved units of a required material as installed when slot map absent
    required_rows = []
    for mid in req_ids:
        info = mats.CATALOG.get(mid, {"name": mid, "category": "?"})
        s = stock.get(mid, {"qty": 0, "reserved": 0})
        qty = int(s.get("qty", 0))
        reserved = int(s.get("reserved", 0))
        avail = mats.available(stock, mid)
        need = int(req_qty.get(mid, 1))
        if slots_state is not None:
            is_installed = mid in installed
        else:
            # Fallback when slot map not passed: reserved units count as installed
            is_installed = reserved > 0
        if is_installed:
            status = "installed"
            status_text = "INSTALLED"
        elif avail > 0:
            status = "available"
            status_text = f"{avail} available / {need} required"
        else:
            status = "missing"
            status_text = f"0 available / {need} required"
        required_rows.append(
            {
                "id": mid,
                "name": info.get("name", mid),
                "category": info.get("category", ""),
                "required": True,
                "qty": qty,
                "reserved": reserved,
                "available": avail,
                "need": need,
                "status": status,
                "status_text": status_text,
                "selectable": avail > 0 and not is_installed,
            }
        )

    other_rows = []
    req_set = set(req_ids)
    for mid, info in mats.CATALOG.items():
        if mid in req_set:
            continue
        s = stock.get(mid, {"qty": 0, "reserved": 0})
        qty = int(s.get("qty", 0))
        if qty <= 0:
            continue
        avail = mats.available(stock, mid)
        other_rows.append(
            {
                "id": mid,
                "name": info.get("name", mid),
                "category": info.get("category", ""),
                "required": False,
                "qty": qty,
                "reserved": int(s.get("reserved", 0)),
                "available": avail,
                "need": 0,
                "status": "other",
                "status_text": f"{avail} available",
                "selectable": avail > 0,
            }
        )

    excluded = [
        mid
        for mid, info in mats.CATALOG.items()
        if mid not in req_set and int(stock.get(mid, {}).get("qty", 0)) <= 0
    ]
    return {
        "required": required_rows,
        "other": other_rows,
        "excluded_empty": excluded,
        "required_ids": req_ids,
    }


def log_workbench_diagnostics(
    mission: str | None,
    inventory: dict,
    slots_state: dict | None = None,
    reason: str = "open",
) -> None:
    if not DEBUG_WORKBENCH:
        return
    rows = build_supply_rows(inventory, mission, slots_state)
    stock = inventory.get("stock") or {}
    print(f"[workbench:{reason}] mission={mission} recipe={mission}")
    print(f"  required_ids={rows['required_ids']}")
    print(
        "  inventory="
        + ", ".join(
            f"{mid}:qty={stock.get(mid, {}).get('qty', 0)}/res={stock.get(mid, {}).get('reserved', 0)}"
            for mid in mats.CATALOG
            if int(stock.get(mid, {}).get("qty", 0)) > 0
            or int(stock.get(mid, {}).get("reserved", 0)) > 0
        )
    )
    print(
        "  display_required="
        + ", ".join(f"{r['id']}:{r['status_text']}" for r in rows["required"])
    )
    print(
        "  display_other="
        + ", ".join(r["id"] for r in rows["other"])
        + (f" (collapsed)" if not _SESSION.get("show_other_supplies") else "")
    )
    print(f"  installed_slots={dict(slots_state or {})}")


def draw_supply_panel(
    surface,
    fonts,
    inventory: dict,
    mouse_pos,
    mission: str | None,
    panel_rect: pygame.Rect,
    title: str = "YOUR SUPPLIES",
    slots_state: dict | None = None,
) -> dict:
    """
    Draw clickable supply list from the central inventory.
    Required recipe materials are always listed first and never clipped by unrelated stock.
    Returns hit targets: {mid: rect, ...} plus meta keys (_other_toggle, _scroll_up, _scroll_down).
    """
    pygame.draw.rect(surface, ui.C_BG, panel_rect, border_radius=8)
    pygame.draw.rect(surface, ui.C_EDGE, panel_rect, 1, border_radius=8)
    ui.label(surface, fonts, title, (panel_rect.x + 12, panel_rect.y + 10), ui.C_MUTED, "small")

    rows_data = build_supply_rows(inventory, mission, slots_state)
    required_rows = rows_data["required"]
    other_rows = rows_data["other"]
    show_other = bool(_SESSION.get("show_other_supplies"))

    rects: dict = {}
    y = panel_rect.y + 36
    row_h = 54
    bottom_reserve = 36 if other_rows else 8
    content_bottom = panel_rect.bottom - bottom_reserve

    def _draw_row(row: dict, y_pos: int) -> int:
        mid = row["id"]
        r = pygame.Rect(panel_rect.x + 8, y_pos, panel_rect.w - 16, row_h - 4)
        if r.bottom > content_bottom:
            return -1
        selected = inventory.get("selected") == mid
        status = row["status"]
        fill = ui.C_SURFACE_2 if selected else ui.C_SURFACE
        pygame.draw.rect(surface, fill, r, border_radius=6)
        if status == "installed":
            border = ui.C_GREEN
            name_col = ui.C_GREEN
            status_col = ui.C_GREEN
        elif status == "missing":
            border = ui.C_RED
            name_col = ui.C_RED
            status_col = ui.C_MUTED
        elif selected:
            border = ui.C_SIGNAL
            name_col = ui.C_GREEN
            status_col = ui.C_MUTED
        elif row["required"]:
            border = ui.C_AMBER
            name_col = ui.C_TEXT
            status_col = ui.C_MUTED
        else:
            border = ui.C_EDGE_DIM
            name_col = ui.C_TEXT
            status_col = ui.C_MUTED
        if r.collidepoint(mouse_pos):
            border = ui.C_SIGNAL
        pygame.draw.rect(surface, border, r, 1, border_radius=6)
        draw_material_icon(surface, mid, (r.x + 22, r.centery), 14)
        ui.label(surface, fonts, row["name"], (r.x + 44, r.y + 6), name_col, "small")
        ui.label(surface, fonts, row["status_text"], (r.x + 44, r.y + 26), status_col, "small")
        rects[mid] = r
        return y_pos + row_h

    # Required materials — always drawn first, never replaced by unrelated stock
    for row in required_rows:
        nxt = _draw_row(row, y)
        if nxt < 0:
            break
        y = nxt

    if inventory.get("selected"):
        ui.label(
            surface,
            fonts,
            "Select a compatible slot to install.",
            (panel_rect.x + 10, min(y + 2, panel_rect.bottom - 48)),
            ui.C_SIGNAL,
            "small",
        )
        y += 22

    # Other Supplies (expandable) — Mission 1/2 leftovers live here for Mission 3
    if other_rows:
        toggle = pygame.Rect(panel_rect.x + 8, panel_rect.bottom - 30, panel_rect.w - 16, 24)
        label = f"Other Supplies ({len(other_rows)}) {'▼' if show_other else '▶'}"
        pygame.draw.rect(surface, ui.C_SURFACE, toggle, border_radius=4)
        pygame.draw.rect(surface, ui.C_EDGE_DIM, toggle, 1, border_radius=4)
        ui.centered(surface, fonts, label, toggle.center, ui.C_MUTED, "small")
        rects["_other_toggle"] = toggle
        if show_other:
            # Draw other rows above the toggle if space remains
            oy = y
            for row in other_rows:
                if oy + row_h > toggle.top - 4:
                    break
                nxt = _draw_row(row, oy)
                if nxt < 0:
                    break
                oy = nxt

    if not required_rows and not other_rows:
        ui.centered(
            surface, fonts, "No supplies yet — explore and collect (E).",
            panel_rect.center, ui.C_MUTED, "small",
        )
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
        fill = (32, 48, 38)
    elif flash_incompatible:
        border = ui.C_RED
        fill = (48, 30, 28)
    elif compatible and guided:
        border = ui.C_SIGNAL
        fill = (30, 44, 46)
    elif incompatible and selected_mid:
        border = ui.C_EDGE_DIM
        fill = ui.C_SURFACE
    else:
        border = ui.C_EDGE
        fill = ui.C_SURFACE
    if rect.collidepoint(mouse_pos) and selected_mid:
        border = ui.C_SIGNAL if compatible else ui.C_RED
    pygame.draw.rect(surface, fill, rect, border_radius=8)
    pygame.draw.rect(surface, border, rect, 2 if (compatible and guided) else 1, border_radius=8)
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
            ui.centered(surface, fonts, "CLICK TO INSTALL", (rect.centerx, rect.bottom - 16), ui.C_SIGNAL, "small")


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
    """Outer frame + mode toggle + one hint + progress. Returns button rects."""
    ui.dim_backdrop(surface, 140)
    box = pygame.Rect(40, 24, 1200, 672)
    ui.panel(surface, box)
    ui.header(surface, fonts, box, title, subtitle)
    mode_btn = pygame.Rect(980, 52, 200, 32)
    mode_label = "GUIDED" if guided else "CHALLENGE"
    ui.button(surface, mode_btn, mode_label, fonts, mouse_pos, small=True)
    tip = hint[:90] if hint else (
        "Select a supply, then click a compatible slot." if guided else "Assemble from clues and supplies."
    )
    ui.objective_bar(surface, fonts, tip, y=96)
    ui.label(surface, fonts, progress_label, (60, 640), ui.C_MUTED, "small")
    ui.meter(
        surface, pygame.Rect(220, 646, 400, 10), progress, 1.0,
        ui.C_GREEN if progress >= 1.0 else ui.C_SIGNAL,
    )
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
        if DEBUG_WORKBENCH:
            print(
                f"[workbench:install_reject] mid={mid} slot={slot_key} needs={needs} "
                f"qty_before={inventory['stock'].get(mid, {}).get('qty')}"
            )
        return False, incompatibility_message(mid, needs, slot_meta.get("label", "this slot"))
    if not mats.can_reserve(inventory["stock"], mid, 1):
        return False, f"No available {mats.CATALOG[mid]['name']} (already installed or none left)."
    qty_before = int(inventory["stock"].get(mid, {}).get("qty", 0))
    # Remove previous if any
    old = slots_state.get(slot_key)
    if old:
        mats.release(inventory["stock"], old, 1)
    mats.reserve(inventory["stock"], mid, 1)
    slots_state[slot_key] = mid
    inventory["selected"] = None
    if DEBUG_WORKBENCH:
        print(
            f"[workbench:install] mid={mid} slot={slot_key} "
            f"qty_before={qty_before} qty_after={inventory['stock'][mid]['qty']} "
            f"reserved={inventory['stock'][mid]['reserved']} installed={slots_state[slot_key]}"
        )
    return True, f"Installed {mats.CATALOG[mid]['name']} into {slot_meta.get('label', slot_key)}."


def remove_install(inventory, slots_state: dict, slot_key: str) -> str:
    old = slots_state.get(slot_key)
    if not old:
        return "Slot is already empty."
    mats.release(inventory["stock"], old, 1)
    slots_state[slot_key] = None
    if DEBUG_WORKBENCH:
        print(
            f"[workbench:undo] slot={slot_key} mid={old} "
            f"qty={inventory['stock'].get(old, {}).get('qty')} "
            f"reserved={inventory['stock'].get(old, {}).get('reserved')}"
        )
    return f"Removed {mats.CATALOG[old]['name']} — returned to supplies."


def clear_all(inventory, slots_state: dict) -> None:
    for key in list(slots_state.keys()):
        old = slots_state.get(key)
        if old:
            mats.release(inventory["stock"], old, 1)
            slots_state[key] = None
    if DEBUG_WORKBENCH:
        print(f"[workbench:reset] slots cleared; reserved released")


def handle_supply_click(inventory, supply_rects: dict, pos) -> bool:
    toggle = supply_rects.get("_other_toggle")
    if toggle and toggle.width and toggle.collidepoint(pos):
        _SESSION["show_other_supplies"] = not _SESSION.get("show_other_supplies", False)
        return True
    for mid, rect in supply_rects.items():
        if str(mid).startswith("_"):
            continue
        if rect.collidepoint(pos):
            avail = mats.available(inventory["stock"], mid)
            if avail <= 0:
                # Installed or missing — do not select; keep feedback path open
                if DEBUG_WORKBENCH:
                    print(f"[workbench:select_blocked] mid={mid} avail={avail}")
                return True
            inventory["selected"] = None if inventory.get("selected") == mid else mid
            if DEBUG_WORKBENCH:
                print(
                    f"[workbench:select] mid={mid} avail={avail} "
                    f"selected={inventory.get('selected')}"
                )
            return True
    return False
