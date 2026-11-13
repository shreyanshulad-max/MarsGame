"""Field scanner — detects nearby objects without revealing the whole map."""

from __future__ import annotations

import math

import pygame

from systems import challenge_ui as ui

SCAN_RADIUS = 420.0
SCAN_DURATION = 1.4


def make_scanner() -> dict:
    return {
        "active": False,
        "timer": 0.0,
        "angle": 0.0,
        "hits": [],  # {id, category, bearing, dist, known, name, pos}
        "status": "Ready — press Tab to scan nearby signals.",
        "cooldown": 0.0,
    }


def update(scanner: dict, dt: float) -> None:
    if scanner["cooldown"] > 0:
        scanner["cooldown"] -= dt
    if not scanner["active"]:
        return
    scanner["timer"] += dt
    scanner["angle"] = (scanner["angle"] + 280 * dt) % 360
    if scanner["timer"] >= SCAN_DURATION:
        scanner["active"] = False
        scanner["timer"] = 0.0
        n = len(scanner["hits"])
        if n == 0:
            scanner["status"] = "Scan complete — no signals in range."
        else:
            scanner["status"] = f"Scan complete — {n} signal(s) nearby. Approach unknowns to identify."


def start_scan(scanner: dict, astro: dict, colony: dict, discovery: dict) -> None:
    if scanner["active"] or scanner["cooldown"] > 0:
        return
    scanner["active"] = True
    scanner["timer"] = 0.0
    scanner["hits"] = []
    scanner["status"] = "Scanning…"
    scanner["cooldown"] = 0.5
    ax, ay = astro["x"], astro["y"]
    # Collectibles / materials
    for it in colony.get("interactables", []):
        if it.get("collected") or it.get("disabled"):
            continue
        d = math.hypot(ax - it["pos"][0], ay - it["pos"][1])
        if d > SCAN_RADIUS:
            continue
        known = it["id"] in discovery.get("identified", set()) or it.get("type") == "station"
        if it.get("type") == "station":
            cat = "station"
            name = it["name"]
            known = True
        elif it.get("material"):
            cat = "supply"
            name = it["name"] if known else "Unidentified supply signal"
        else:
            cat = "research"
            name = it["name"] if known else "Unidentified research signal"
        bearing = (math.degrees(math.atan2(it["pos"][1] - ay, it["pos"][0] - ax)) + 360) % 360
        scanner["hits"].append(
            {
                "id": it["id"],
                "category": cat,
                "bearing": bearing,
                "dist": d,
                "known": known,
                "name": name,
                "pos": it["pos"],
            }
        )
        # Soft discovery: mark approximate on map without full ID if unknown
        discovery.setdefault("scanned_ids", set()).add(it["id"])
        if known:
            discovery.setdefault("identified", set()).add(it["id"])
    scanner["hits"].sort(key=lambda h: h["dist"])


def try_identify_nearby(astro: dict, colony: dict, discovery: dict, radius: float = 70.0) -> str | None:
    """When player is close, reveal identity of scanned unknowns."""
    ax, ay = astro["x"], astro["y"]
    for it in colony.get("interactables", []):
        if it.get("collected"):
            continue
        d = math.hypot(ax - it["pos"][0], ay - it["pos"][1])
        if d <= radius:
            discovery.setdefault("identified", set()).add(it["id"])
            discovery.setdefault("scanned_ids", set()).add(it["id"])
            return it.get("name")
    return None


def draw_overlay(surface, fonts, scanner: dict, astro: dict, camera: dict) -> None:
    if not scanner["active"] and not scanner["hits"]:
        return
    # Screen-space player
    sx = int(astro["x"] - camera["x"])
    sy = int(astro["y"] - camera["y"])
    if scanner["active"]:
        r = int(SCAN_RADIUS * (scanner["timer"] / SCAN_DURATION))
        r = max(40, min(int(SCAN_RADIUS), r))
        ring = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.circle(ring, (80, 210, 230, 40), (sx, sy), r)
        pygame.draw.circle(ring, (80, 210, 230, 160), (sx, sy), r, 2)
        ang = math.radians(scanner["angle"] - 90)
        pygame.draw.line(
            ring, (90, 220, 140, 200), (sx, sy),
            (sx + math.cos(ang) * r, sy + math.sin(ang) * r), 3,
        )
        surface.blit(ring, (0, 0))

    # Hit list panel
    panel = pygame.Rect(16, 280, 340, 200)
    pygame.draw.rect(surface, (20, 12, 10, ), panel, border_radius=10)
    pygame.draw.rect(surface, ui.C_CYAN, panel, 2, border_radius=10)
    ui.label(surface, fonts, "FIELD SCANNER", (panel.x + 12, panel.y + 10), ui.C_CYAN, "small")
    ui.label(surface, fonts, scanner["status"][:42], (panel.x + 12, panel.y + 34), ui.C_MUTED, "small")
    y = panel.y + 60
    for hit in scanner["hits"][:5]:
        mark = "●" if hit["known"] else "?"
        col = ui.C_GREEN if hit["known"] else ui.C_AMBER
        line = f"{mark} {hit['name'][:22]}  {int(hit['dist'])}m  {int(hit['bearing'])}°"
        ui.label(surface, fonts, line, (panel.x + 12, y), col, "small")
        y += 24
