"""Minimap + full-screen exploration map with fog of war and discovery."""

from __future__ import annotations

import math

import pygame

from systems import challenge_ui as ui


def make_discovery(spawn: tuple) -> dict:
    """Session exploration / scan discovery data."""
    return {
        "revealed": set(),  # cell keys "cx,cy" at 128px grid
        "identified": set(),  # interactable ids fully known
        "scanned_ids": set(),  # detected by scanner (approx on map)
        "landmarks": set(),  # zone ids visited
        "show_resources": True,
        "show_missions": True,
        "show_research": True,
        # full map view state
        "zoom": 1.0,
        "pan_x": 0.0,
        "pan_y": 0.0,
        "dragging": False,
        "drag_last": (0, 0),
        "selected_marker": None,
        "info": "",
    }


def _cell_key(x: float, y: float, cell: int = 128) -> str:
    return f"{int(x) // cell},{int(y) // cell}"


def reveal_around(discovery: dict, x: float, y: float, radius: float = 220.0, cell: int = 128) -> None:
    r = int(radius)
    for dx in range(-r, r + 1, cell // 2):
        for dy in range(-r, r + 1, cell // 2):
            if dx * dx + dy * dy <= radius * radius:
                discovery["revealed"].add(_cell_key(x + dx, y + dy, cell))


def visit_zone(discovery: dict, zone_id: str) -> None:
    discovery["landmarks"].add(zone_id)


def is_revealed(discovery: dict, x: float, y: float, cell: int = 128) -> bool:
    return _cell_key(x, y, cell) in discovery["revealed"]


def draw_minimap(
    surface,
    fonts,
    astro,
    colony,
    cam,
    world_w: int,
    world_h: int,
    discovery: dict | None = None,
    objective: str = "",
    guide_obj: dict | None = None,
) -> pygame.Rect:
    map_w, map_h = 210, 140
    ox = surface.get_width() - map_w - 16
    oy = 16
    panel = pygame.Surface((map_w, map_h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (20, 12, 10, 210), (0, 0, map_w, map_h), border_radius=8)
    pygame.draw.rect(panel, (255, 180, 100, 160), (0, 0, map_w, map_h), 2, border_radius=8)

    def to_map(wx, wy):
        return (
            int((wx / world_w) * (map_w - 10)) + 5,
            int((wy / world_h) * (map_h - 10)) + 5,
        )

    for zone in colony["zones"]:
        if zone["id"] == "outer":
            continue
        x0, y0 = to_map(zone["rect"].x, zone["rect"].y)
        x1, y1 = to_map(zone["rect"].right, zone["rect"].bottom)
        known = discovery is None or zone["id"] in discovery.get("landmarks", set()) or True
        # Always show faint zone tint; fog handled on full map
        pygame.draw.rect(panel, (*zone["tint"], 40 if known else 18), (x0, y0, max(2, x1 - x0), max(2, y1 - y0)))

    if discovery is None or discovery.get("show_missions", True):
        for st in colony["stations"]:
            mx, my = to_map(st["pos"][0], st["pos"][1])
            pygame.draw.circle(panel, st["marker"], (mx, my), 4)

    if discovery and discovery.get("show_resources", True):
        for it in colony.get("collectibles", []):
            if it.get("collected"):
                continue
            uid = it["id"]
            if uid not in discovery.get("scanned_ids", set()) and uid not in discovery.get("identified", set()):
                continue
            mx, my = to_map(it["pos"][0], it["pos"][1])
            col = ui.C_GREEN if uid in discovery.get("identified", set()) else ui.C_AMBER
            pygame.draw.rect(panel, col, (mx - 2, my - 2, 4, 4))

    # Active guidance target (diamond — distinct from station dots)
    if guide_obj and "x" in guide_obj and "y" in guide_obj:
        gx, gy = to_map(guide_obj["x"], guide_obj["y"])
        gcol = (80, 230, 255) if guide_obj.get("exact", True) else (255, 190, 80)
        if not guide_obj.get("exact", True):
            # Search area ring
            pygame.draw.circle(panel, (*gcol, 90), (gx, gy), 14, 1)
        pygame.draw.polygon(panel, gcol, [(gx, gy - 7), (gx + 6, gy), (gx, gy + 7), (gx - 6, gy)])
        pygame.draw.line(panel, gcol, to_map(astro["x"], astro["y"]), (gx, gy), 1)

    # Player + facing
    px, py = to_map(astro["x"], astro["y"])
    facing = astro.get("facing", "down")
    ang = {"right": 0, "down": 90, "left": 180, "up": 270}.get(facing, 90)
    rad = math.radians(ang - 90)
    pygame.draw.circle(panel, (255, 255, 255), (px, py), 5)
    pygame.draw.circle(panel, (80, 220, 140), (px, py), 3)
    pygame.draw.line(
        panel, (80, 220, 140),
        (px, py),
        (px + int(math.cos(rad) * 10), py + int(math.sin(rad) * 10)),
        2,
    )

    surface.blit(panel, (ox, oy))
    surface.blit(fonts["small"].render("MAP (M)  ·  SCAN (Tab)", True, (255, 230, 200)), (ox + 6, oy + 4))
    return pygame.Rect(ox, oy, map_w, map_h)


def _map_to_world(discovery, inner, world_w, world_h, mx, my):
    zoom = discovery["zoom"]
    # centre of view in world space
    cx = world_w / 2 + discovery["pan_x"]
    cy = world_h / 2 + discovery["pan_y"]
    # local coords from inner center
    lx = (mx - inner.centerx) / zoom
    ly = (my - inner.centery) / zoom
    # scale: full world fits inner at zoom 1
    wx = cx + (lx / inner.w) * world_w
    wy = cy + (ly / inner.h) * world_h
    return wx, wy


def _world_to_map(discovery, inner, world_w, world_h, wx, wy):
    zoom = discovery["zoom"]
    cx = world_w / 2 + discovery["pan_x"]
    cy = world_h / 2 + discovery["pan_y"]
    lx = ((wx - cx) / world_w) * inner.w * zoom
    ly = ((wy - cy) / world_h) * inner.h * zoom
    return int(inner.centerx + lx), int(inner.centery + ly)


def draw_full_map(
    surface,
    fonts,
    astro,
    colony,
    world_w: int,
    world_h: int,
    open_flag: bool,
    discovery: dict | None = None,
    mouse_pos=(0, 0),
    objective: str = "",
    guide_obj: dict | None = None,
) -> dict:
    """Returns UI hit targets for map controls."""
    ui_state = {
        "close": pygame.Rect(0, 0, 0, 0),
        "zoom_in": pygame.Rect(0, 0, 0, 0),
        "zoom_out": pygame.Rect(0, 0, 0, 0),
        "center": pygame.Rect(0, 0, 0, 0),
        "reset": pygame.Rect(0, 0, 0, 0),
        "tog_res": pygame.Rect(0, 0, 0, 0),
        "tog_mis": pygame.Rect(0, 0, 0, 0),
        "tog_resr": pygame.Rect(0, 0, 0, 0),
        "inner": pygame.Rect(0, 0, 0, 0),
        "markers": {},
    }
    if not open_flag or discovery is None:
        return ui_state

    ui.dim_backdrop(surface, 185)
    panel = pygame.Rect(80, 30, 1120, 660)
    ui.panel(surface, panel)
    ui.header(surface, fonts, panel, "COLONY EXPLORATION MAP", "Scroll zoom · Drag pan · Click markers · M to close")

    inner = pygame.Rect(110, 120, 860, 500)
    ui_state["inner"] = inner
    pygame.draw.rect(surface, (35, 20, 14), inner, border_radius=8)
    pygame.draw.rect(surface, ui.C_EDGE, inner, 2, border_radius=8)

    # Zones (always faintly), then fog tiles for unexplored cells
    for zone in colony["zones"]:
        if zone["id"] == "outer":
            continue
        x0, y0 = _world_to_map(discovery, inner, world_w, world_h, zone["rect"].x, zone["rect"].y)
        x1, y1 = _world_to_map(discovery, inner, world_w, world_h, zone["rect"].right, zone["rect"].bottom)
        r = pygame.Rect(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))
        if not r.colliderect(inner):
            continue
        pygame.draw.rect(surface, zone["tint"], r, 2)
        if zone["id"] in discovery["landmarks"] or is_revealed(discovery, zone["rect"].centerx, zone["rect"].centery):
            ui.label(surface, fonts, zone["name"], (r.x + 4, r.y + 4), ui.C_TEXT, "small")

    # Fog of war: darken unrevealed cells
    cell = 160
    fog = pygame.Surface((inner.w, inner.h), pygame.SRCALPHA)
    for gx in range(0, world_w, cell):
        for gy in range(0, world_h, cell):
            if is_revealed(discovery, gx + cell // 2, gy + cell // 2, cell=128):
                continue
            mx, my = _world_to_map(discovery, inner, world_w, world_h, gx, gy)
            mx2, my2 = _world_to_map(discovery, inner, world_w, world_h, gx + cell, gy + cell)
            rx = pygame.Rect(min(mx, mx2) - inner.x, min(my, my2) - inner.y, abs(mx2 - mx) + 1, abs(my2 - my) + 1)
            pygame.draw.rect(fog, (6, 3, 2, 200), rx)
    surface.blit(fog, inner.topleft)

    # Stations
    if discovery.get("show_missions", True):
        for st in colony["stations"]:
            mx, my = _world_to_map(discovery, inner, world_w, world_h, st["pos"][0], st["pos"][1])
            if not inner.collidepoint(mx, my):
                continue
            pygame.draw.circle(surface, st["marker"], (mx, my), 8)
            pygame.draw.circle(surface, (20, 12, 8), (mx, my), 8, 2)
            ui_state["markers"][st["id"]] = (pygame.Rect(mx - 10, my - 10, 20, 20), st["name"], "Mission station")

    # Resources (discovered only)
    if discovery.get("show_resources", True):
        for it in colony.get("collectibles", []):
            if it.get("collected"):
                continue
            uid = it["id"]
            scanned = uid in discovery["scanned_ids"] or uid in discovery["identified"]
            if not scanned:
                continue
            if it.get("kind") in ("mineral", "data", "sample") and not discovery.get("show_research", True):
                continue
            mx, my = _world_to_map(discovery, inner, world_w, world_h, it["pos"][0], it["pos"][1])
            if not inner.collidepoint(mx, my):
                continue
            known = uid in discovery["identified"]
            col = ui.C_GREEN if known else ui.C_AMBER
            pygame.draw.rect(surface, col, (mx - 5, my - 5, 10, 10))
            label = it["name"] if known else "Unknown supply"
            ui_state["markers"][uid] = (pygame.Rect(mx - 8, my - 8, 16, 16), label, it.get("kind", "supply"))

    # Active guidance objective (shared with guiding arrow)
    if guide_obj and "x" in guide_obj:
        gx, gy = _world_to_map(discovery, inner, world_w, world_h, guide_obj["x"], guide_obj["y"])
        gcol = ui.C_CYAN if guide_obj.get("exact", True) else ui.C_AMBER
        if inner.collidepoint(gx, gy):
            if not guide_obj.get("exact", True):
                pygame.draw.circle(surface, gcol, (gx, gy), 28, 2)
                ui.label(surface, fonts, "SEARCH AREA", (gx + 18, gy - 18), gcol, "small")
            else:
                pygame.draw.circle(surface, gcol, (gx, gy), 16, 2)
            pygame.draw.polygon(
                surface, gcol,
                [(gx, gy - 12), (gx + 10, gy), (gx, gy + 12), (gx - 10, gy)],
            )
            ui.label(
                surface, fonts,
                f"ACTIVE: {guide_obj.get('dest_name', guide_obj.get('title', 'Objective'))[:28]}",
                (gx + 16, gy + 8), gcol, "small",
            )
            # Route line from player
            px0, py0 = _world_to_map(discovery, inner, world_w, world_h, astro["x"], astro["y"])
            if inner.collidepoint(px0, py0):
                pygame.draw.line(surface, gcol, (px0, py0), (gx, gy), 2)

    # Player
    px, py = _world_to_map(discovery, inner, world_w, world_h, astro["x"], astro["y"])
    if inner.collidepoint(px, py):
        pygame.draw.circle(surface, ui.C_GREEN, (px, py), 9)
        pygame.draw.circle(surface, (255, 255, 255), (px, py), 4)
        ui.label(surface, fonts, "YOU", (px + 12, py - 10), ui.C_GREEN, "small")

    # Side controls
    bx = 1000
    ui_state["zoom_in"] = pygame.Rect(bx, 140, 160, 40)
    ui_state["zoom_out"] = pygame.Rect(bx, 190, 160, 40)
    ui_state["center"] = pygame.Rect(bx, 240, 160, 40)
    ui_state["reset"] = pygame.Rect(bx, 290, 160, 40)
    ui_state["tog_res"] = pygame.Rect(bx, 360, 160, 40)
    ui_state["tog_mis"] = pygame.Rect(bx, 410, 160, 40)
    ui_state["tog_resr"] = pygame.Rect(bx, 460, 160, 40)
    ui.button(surface, ui_state["zoom_in"], "ZOOM +", fonts, mouse_pos, small=True)
    ui.button(surface, ui_state["zoom_out"], "ZOOM −", fonts, mouse_pos, small=True)
    ui.button(surface, ui_state["center"], "CENTRE ON YOU", fonts, mouse_pos, small=True)
    ui.button(surface, ui_state["reset"], "RESET VIEW", fonts, mouse_pos, small=True)
    ui.button(
        surface, ui_state["tog_res"],
        "SUPPLIES: ON" if discovery["show_resources"] else "SUPPLIES: OFF",
        fonts, mouse_pos, small=True,
    )
    ui.button(
        surface, ui_state["tog_mis"],
        "MISSIONS: ON" if discovery["show_missions"] else "MISSIONS: OFF",
        fonts, mouse_pos, small=True,
    )
    ui.button(
        surface, ui_state["tog_resr"],
        "RESEARCH: ON" if discovery["show_research"] else "RESEARCH: OFF",
        fonts, mouse_pos, small=True,
    )

    # Info panel
    info_box = pygame.Rect(110, 630, 860, 40)
    pygame.draw.rect(surface, (30, 18, 12), info_box, border_radius=8)
    if guide_obj:
        guide_msg = f"ACTIVE OBJECTIVE: {guide_obj.get('title', '')} — {guide_obj.get('task', '')}"
    else:
        guide_msg = ""
    msg = discovery.get("info") or guide_msg or objective or "Explore to clear fog. Scan (Tab) to mark nearby supplies."
    ui.label(surface, fonts, msg[:95], (120, 640), ui.C_TEXT, "small")

    if discovery.get("selected_marker"):
        ui.label(surface, fonts, f"Selected: {discovery['selected_marker']}", (bx, 520), ui.C_AMBER, "small")

    return ui_state


def handle_map_event(discovery: dict, event, ui_state: dict, astro: dict, world_w: int, world_h: int) -> bool:
    """Handle map interaction. Returns True if consumed."""
    if not ui_state.get("inner") or ui_state["inner"].width <= 0:
        return False
    if event.type == pygame.MOUSEWHEEL:
        discovery["zoom"] = max(0.7, min(2.8, discovery["zoom"] + event.y * 0.15))
        return True
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        pos = event.pos
        if ui_state["zoom_in"].collidepoint(pos):
            discovery["zoom"] = min(2.8, discovery["zoom"] + 0.2)
            return True
        if ui_state["zoom_out"].collidepoint(pos):
            discovery["zoom"] = max(0.7, discovery["zoom"] - 0.2)
            return True
        if ui_state["center"].collidepoint(pos):
            discovery["pan_x"] = astro["x"] - world_w / 2
            discovery["pan_y"] = astro["y"] - world_h / 2
            discovery["info"] = "Map centred on astronaut."
            return True
        if ui_state["reset"].collidepoint(pos):
            discovery["zoom"] = 1.0
            discovery["pan_x"] = 0.0
            discovery["pan_y"] = 0.0
            discovery["info"] = "Map view reset."
            return True
        if ui_state["tog_res"].collidepoint(pos):
            discovery["show_resources"] = not discovery["show_resources"]
            return True
        if ui_state["tog_mis"].collidepoint(pos):
            discovery["show_missions"] = not discovery["show_missions"]
            return True
        if ui_state["tog_resr"].collidepoint(pos):
            discovery["show_research"] = not discovery["show_research"]
            return True
        for mid, (rect, name, kind) in ui_state.get("markers", {}).items():
            if rect.collidepoint(pos):
                discovery["selected_marker"] = name
                discovery["info"] = f"{name} — {kind}. Travel there on foot; no teleport."
                return True
        if ui_state["inner"].collidepoint(pos):
            discovery["dragging"] = True
            discovery["drag_last"] = pos
            return True
    if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
        discovery["dragging"] = False
        return discovery.get("dragging") is False
    if event.type == pygame.MOUSEMOTION and discovery.get("dragging"):
        lx, ly = discovery["drag_last"]
        dx, dy = event.pos[0] - lx, event.pos[1] - ly
        discovery["drag_last"] = event.pos
        # pan opposite to drag
        discovery["pan_x"] -= (dx / ui_state["inner"].w) * world_w / max(0.5, discovery["zoom"])
        discovery["pan_y"] -= (dy / ui_state["inner"].h) * world_h / max(0.5, discovery["zoom"])
        return True
    return False
