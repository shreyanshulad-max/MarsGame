"""Waypoints, compass, distance and driving HUD helpers for Challenge 3."""

from __future__ import annotations

import math

import pygame

from systems import challenge_ui as ui
from systems import rover_physics as phys
from systems import rover_terrain as terrain


def default_waypoints(route_key: str) -> list[dict]:
    """World-space waypoints from launch to stranded rover."""
    start = {"id": "launch", "x": 200.0, "y": 1100.0, "label": "Launch"}
    goal = {"id": "rescue", "x": 2100.0, "y": 450.0, "label": "Stranded Rover"}
    if route_key == "safe":
        return [
            start,
            {"id": "ridge", "x": 600.0, "y": 280.0, "label": "North Ridge"},
            {"id": "approach", "x": 1600.0, "y": 260.0, "label": "Firm Approach"},
            goal,
        ]
    if route_key == "shortcut":
        return [
            start,
            {"id": "scar", "x": 1000.0, "y": 900.0, "label": "Storm Scar"},
            {"id": "cut", "x": 1600.0, "y": 700.0, "label": "Crater Cut"},
            goal,
        ]
    return [
        start,
        {"id": "corridor", "x": 900.0, "y": 700.0, "label": "Corridor"},
        {"id": "mid", "x": 1500.0, "y": 550.0, "label": "Mid Basin"},
        goal,
    ]


def sync_waypoints(ch3: dict) -> None:
    route = ch3.get("route") or "direct"
    ch3["waypoints"] = default_waypoints(route)
    ch3["waypoint_index"] = 0
    # Align start/target with first/last
    ch3["rover_x"] = ch3["waypoints"][0]["x"]
    ch3["rover_y"] = ch3["waypoints"][0]["y"]
    ch3["target_x"] = ch3["waypoints"][-1]["x"]
    ch3["target_y"] = ch3["waypoints"][-1]["y"]
    ch3["heading"] = math.degrees(
        math.atan2(ch3["waypoints"][1]["y"] - ch3["rover_y"], ch3["waypoints"][1]["x"] - ch3["rover_x"])
    )


def update_waypoint_progress(ch3: dict) -> None:
    wps = ch3.get("waypoints") or []
    if not wps:
        return
    idx = int(ch3.get("waypoint_index", 0))
    # Advance when near intermediate waypoints (not the final rescue — E handles that)
    while idx < len(wps) - 1:
        wp = wps[idx]
        dx = ch3["rover_x"] - wp["x"]
        dy = ch3["rover_y"] - wp["y"]
        if idx == 0:
            idx = 1
            ch3["waypoint_index"] = idx
            continue
        if dx * dx + dy * dy < 90 * 90 and idx < len(wps) - 1:
            idx += 1
            ch3["waypoint_index"] = idx
        else:
            break
    # Always chase current or final
    if idx >= len(wps):
        idx = len(wps) - 1
        ch3["waypoint_index"] = idx


def current_waypoint(ch3: dict) -> dict:
    wps = ch3.get("waypoints") or [{"x": ch3["target_x"], "y": ch3["target_y"], "label": "Rescue"}]
    idx = min(int(ch3.get("waypoint_index", 0)), len(wps) - 1)
    # Prefer next unfinished waypoint; final is always rescue target
    if idx < len(wps) - 1:
        return wps[max(1, idx)]
    return wps[-1]


def distance_to(ch3: dict, x: float, y: float) -> float:
    dx = x - ch3["rover_x"]
    dy = y - ch3["rover_y"]
    return math.hypot(dx, dy)


def bearing_to(ch3: dict, x: float, y: float) -> float:
    return math.degrees(math.atan2(y - ch3["rover_y"], x - ch3["rover_x"])) % 360


def update_camera(ch3: dict, dt: float, screen_w: int = 1280, screen_h: int = 720) -> None:
    """Smooth follow with look-ahead along velocity heading."""
    look = 90.0 + min(140.0, abs(ch3.get("speed", 0)) * 0.45)
    rad = math.radians(ch3.get("heading", 0))
    desire_x = ch3["rover_x"] + math.cos(rad) * look - screen_w * 0.5
    desire_y = ch3["rover_y"] + math.sin(rad) * look - screen_h * 0.5
    # Shake
    shake = float(ch3.get("impact_shake", 0.0))
    if shake > 0:
        desire_x += math.sin(shake * 40) * shake * 6
        desire_y += math.cos(shake * 33) * shake * 4
    world_w = float(ch3.get("world_w", terrain.WORLD_W))
    world_h = float(ch3.get("world_h", terrain.WORLD_H))
    desire_x = max(0.0, min(world_w - screen_w, desire_x))
    desire_y = max(0.0, min(world_h - screen_h, desire_y))
    # Critically-damped-ish follow
    lerp = min(1.0, 6.0 * dt)
    ch3["camera_x"] = ch3.get("camera_x", desire_x) + (desire_x - ch3.get("camera_x", desire_x)) * lerp
    ch3["camera_y"] = ch3.get("camera_y", desire_y) + (desire_y - ch3.get("camera_y", desire_y)) * lerp


def draw_nav_arrow(surface, fonts, ch3: dict, camera: tuple[float, float]) -> None:
    """Single navigation arrow toward current waypoint (world-projected near rover)."""
    wp = current_waypoint(ch3)
    cam_x, cam_y = camera
    rx = ch3["rover_x"] - cam_x
    ry = ch3["rover_y"] - cam_y
    bearing = bearing_to(ch3, wp["x"], wp["y"])
    rad = math.radians(bearing)
    ax = rx + math.cos(rad) * 70
    ay = ry + math.sin(rad) * 70
    tip = (ax + math.cos(rad) * 18, ay + math.sin(rad) * 18)
    left = (ax + math.cos(rad + 2.5) * 10, ay + math.sin(rad + 2.5) * 10)
    right = (ax + math.cos(rad - 2.5) * 10, ay + math.sin(rad - 2.5) * 10)
    pygame.draw.polygon(surface, ui.C_SIGNAL, [tip, left, right])
    dist = distance_to(ch3, wp["x"], wp["y"])
    ui.label(surface, fonts, f"{int(dist)} m", (ax - 18, ay + 14), ui.C_SIGNAL, "small")


def draw_hud(surface, fonts, ch3: dict, storm: float) -> None:
    """Minimal premium driving HUD (screen-fixed)."""
    wp = current_waypoint(ch3)
    terrain_label = ch3.get("terrain_label", "Firm Ground")
    # Top left — objective
    ui.label(surface, fonts, "OBJECTIVE: Rescue stranded rover", (24, 18), ui.C_TEXT, "small")
    ui.label(surface, fonts, f"Waypoint: {wp.get('label', 'Rescue')}", (24, 40), ui.C_MUTED, "small")

    # Top right — time / storm (timer badge also drawn by main)
    ui.label(surface, fonts, f"Storm {int(storm * 100)}%", (1080, 48), ui.C_AMBER, "small")
    ui.meter(surface, pygame.Rect(1080, 70, 160, 8), storm, 1.0, ui.C_AMBER)

    # Bottom left — speed / heading / terrain
    spd = abs(float(ch3.get("speed", 0.0)))
    max_spd = phys.CONFIG["max_forward"]
    ui.label(surface, fonts, f"SPD {int(spd)}", (24, 620), ui.C_CYAN, "body")
    ui.meter(surface, pygame.Rect(24, 648, 160, 10), spd, max_spd, ui.C_CYAN)
    ui.label(surface, fonts, f"HDG {int(ch3.get('heading', 0)) % 360}°", (24, 662), ui.C_MUTED, "small")
    ui.label(surface, fonts, terrain_label, (24, 682), ui.C_AMBER, "small")

    # Bottom right — minimap
    mm = pygame.Rect(1080, 560, 170, 130)
    pygame.draw.rect(surface, (18, 12, 10), mm, border_radius=6)
    pygame.draw.rect(surface, ui.C_EDGE, mm, 1, border_radius=6)
    world_w = float(ch3.get("world_w", terrain.WORLD_W))
    world_h = float(ch3.get("world_h", terrain.WORLD_H))
    # Terrain preview
    preview = ch3.get("_minimap_surf")
    if preview is None:
        ch3["_minimap_surf"] = terrain.build_minimap_surface(mm.w - 8, mm.h - 8)
        preview = ch3["_minimap_surf"]
    surface.blit(preview, (mm.x + 4, mm.y + 4))
    def _mm(x, y):
        return (
            mm.x + 4 + int((x / world_w) * (mm.w - 8)),
            mm.y + 4 + int((y / world_h) * (mm.h - 8)),
        )
    for w in ch3.get("waypoints") or []:
        pygame.draw.circle(surface, (80, 160, 200), _mm(w["x"], w["y"]), 3)
    pygame.draw.circle(surface, ui.C_GREEN, _mm(ch3["target_x"], ch3["target_y"]), 5)
    pygame.draw.circle(surface, (255, 255, 255), _mm(ch3["rover_x"], ch3["rover_y"]), 4)

    # Controls hint (compact)
    ui.centered(
        surface, fonts,
        "W/S throttle · A/D steer · SPACE brake · E rescue",
        (640, 704),
        ui.C_MUTED,
        "small",
    )

    # Rescue proximity
    dist = distance_to(ch3, ch3["target_x"], ch3["target_y"])
    if dist < 220:
        msg = "E — Initiate rescue" if dist < 110 else "Move closer to the stranded rover."
        col = ui.C_GREEN if dist < 110 else ui.C_AMBER
        ui.centered(surface, fonts, msg, (640, 120), col, "body")

    if ch3.get("rescue_hint"):
        ui.centered(surface, fonts, ch3["rescue_hint"], (640, 150), ui.C_AMBER, "small")

    if ch3.get("hit_message_timer", 0) > 0:
        ui.centered(surface, fonts, "ROCK IMPACT!", (640, 90), ui.C_RED, "body")

    if ch3.get("rescued"):
        ui.centered(surface, fonts, "ROVER RESCUED!", (640, 340), ui.C_GREEN, "title")
