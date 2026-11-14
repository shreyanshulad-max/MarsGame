"""World-space terrain sampling for Challenge 3 rover driving."""

from __future__ import annotations

import math

from systems import runtime_paths as rpaths

ROOT = rpaths.resource_root()  # unused for data files; kept for consistency

# World size for the driving stage (larger than the 1280×720 screen)
WORLD_W = 2400
WORLD_H = 1500

# Physical properties per surface
TERRAIN_PROPS = {
    "firm": {
        "label": "Firm Ground",
        "grip": 1.0,
        "accel": 1.0,
        "resistance": 1.0,
        "dust": 0.15,
        "tracks": 0.25,
        "vibration": 0.05,
        "steer_noise": 0.0,
        "color": (186, 98, 58),
    },
    "sand": {
        "label": "Soft Sand",
        "grip": 0.72,
        "accel": 0.78,
        "resistance": 1.28,
        "dust": 1.0,
        "tracks": 1.0,
        "vibration": 0.12,
        "steer_noise": 0.0,
        "color": (210, 140, 78),
    },
    "rocky": {
        "label": "Rocky Ground",
        "grip": 0.88,
        "accel": 0.9,
        "resistance": 1.12,
        "dust": 0.4,
        "tracks": 0.35,
        "vibration": 0.85,
        "steer_noise": 18.0,
        "color": (150, 78, 48),
    },
    "crater": {
        "label": "Crater Zone",
        "grip": 0.65,
        "accel": 0.7,
        "resistance": 1.4,
        "dust": 0.55,
        "tracks": 0.5,
        "vibration": 1.0,
        "steer_noise": 28.0,
        "color": (120, 58, 36),
    },
}


def default_zones() -> list[dict]:
    """Authoritative terrain layout used by physics and route descriptions."""
    return [
        # Soft sand bands (southern flats)
        {"type": "sand", "kind": "rect", "x": 0, "y": 1050, "w": WORLD_W, "h": 450},
        {"type": "sand", "kind": "rect", "x": 900, "y": 700, "w": 500, "h": 280},
        # Rocky fields
        {"type": "rocky", "kind": "rect", "x": 480, "y": 420, "w": 420, "h": 260},
        {"type": "rocky", "kind": "rect", "x": 1300, "y": 280, "w": 380, "h": 300},
        {"type": "rocky", "kind": "rect", "x": 1600, "y": 800, "w": 320, "h": 220},
        # Crater bowls (slow + rough; solid rims handled separately as obstacles)
        {"type": "crater", "kind": "circle", "x": 720, "y": 620, "r": 95},
        {"type": "crater", "kind": "circle", "x": 1500, "y": 980, "r": 110},
        {"type": "crater", "kind": "circle", "x": 1850, "y": 560, "r": 80},
        # Firm northern corridor (safer / longer route)
        {"type": "firm", "kind": "rect", "x": 80, "y": 120, "w": 2200, "h": 260},
    ]


def solid_obstacles(route_key: str = "direct") -> list:
    """Solid collision rects (impassable). Decorative rocks are separate."""
    import pygame

    base = [
        pygame.Rect(560, 540, 70, 48),
        pygame.Rect(680, 500, 90, 55),
        pygame.Rect(980, 880, 80, 50),
        pygame.Rect(1200, 450, 75, 52),
        pygame.Rect(1450, 720, 95, 58),
        pygame.Rect(1700, 400, 70, 45),
        pygame.Rect(1900, 700, 85, 50),
        pygame.Rect(400, 900, 65, 42),
        pygame.Rect(1100, 1100, 100, 55),
        pygame.Rect(2000, 900, 70, 48),
        # Crater rim blocks (encourage routing around)
        pygame.Rect(680, 580, 80, 70),
        pygame.Rect(1460, 940, 90, 75),
        pygame.Rect(1820, 530, 70, 60),
    ]
    # Route modifiers — shorter/riskier keeps more rocks; safer removes some
    if route_key == "safe":
        keep = [0, 2, 4, 6, 8, 10]
        return [base[i] for i in keep if i < len(base)]
    if route_key == "shortcut":
        # Add extra debris cluster on shortcut
        extra = [
            pygame.Rect(900, 600, 60, 40),
            pygame.Rect(1050, 650, 55, 38),
            pygame.Rect(1250, 900, 70, 45),
            pygame.Rect(1550, 500, 65, 42),
        ]
        return base + extra
    # direct
    return base


def decorative_rocks() -> list[dict]:
    """Non-colliding visual rocks."""
    return [
        {"x": 300, "y": 400, "r": 18},
        {"x": 850, "y": 350, "r": 14},
        {"x": 1600, "y": 1100, "r": 20},
        {"x": 2100, "y": 300, "r": 16},
        {"x": 500, "y": 1200, "r": 22},
        {"x": 1750, "y": 950, "r": 12},
    ]


def _in_zone(x: float, y: float, z: dict) -> bool:
    if z["kind"] == "rect":
        return z["x"] <= x <= z["x"] + z["w"] and z["y"] <= y <= z["y"] + z["h"]
    if z["kind"] == "circle":
        dx = x - z["x"]
        dy = y - z["y"]
        return dx * dx + dy * dy <= z["r"] * z["r"]
    return False


def sample(x: float, y: float, zones: list[dict] | None = None) -> dict:
    """Return terrain props at world position. Later zones in list override earlier."""
    zones = zones if zones is not None else default_zones()
    t = "firm"
    # First match from reverse so specific overlays win
    for z in reversed(zones):
        if _in_zone(x, y, z):
            t = z["type"]
            break
    # Mild procedural noise for variety without new objects
    if t == "firm":
        n = math.sin(x * 0.008) * math.cos(y * 0.01)
        if n > 0.65:
            t = "rocky"
        elif n < -0.7:
            t = "sand"
    props = dict(TERRAIN_PROPS[t])
    props["id"] = t
    return props


def route_summary(route_key: str) -> dict:
    """Honest descriptions derived from configured terrain / obstacle density."""
    solids = solid_obstacles(route_key)
    if route_key == "safe":
        return {
            "name": "Safe Ridge Route",
            "risk": "Low",
            "time": "Longer",
            "desc": "Northern firm ground. Fewer rocks. Longer path to the stranded rover.",
            "terrain_focus": "firm",
            "obstacle_count": len(solids),
            "rock_scale": 0.7,
            "traction": 1.05,
        }
    if route_key == "shortcut":
        return {
            "name": "Storm Scar Shortcut",
            "risk": "High",
            "time": "Shortest",
            "desc": "Cuts sand and crater edges. More debris. Fastest if you handle rough ground.",
            "terrain_focus": "sand/crater",
            "obstacle_count": len(solids),
            "rock_scale": 1.35,
            "traction": 0.82,
        }
    return {
        "name": "Direct Corridor",
        "risk": "Medium",
        "time": "Balanced",
        "desc": "Mixed firm and rocky ground. Moderate obstacles along the B2 approach.",
        "terrain_focus": "mixed",
        "obstacle_count": len(solids),
        "rock_scale": 1.0,
        "traction": 1.0,
    }


def build_minimap_surface(scale_w: int = 160, scale_h: int = 120) -> object:
    """Cached miniature terrain preview for route UI / HUD."""
    import pygame

    surf = pygame.Surface((scale_w, scale_h))
    sx = scale_w / WORLD_W
    sy = scale_h / WORLD_H
    surf.fill(TERRAIN_PROPS["firm"]["color"])
    for z in default_zones():
        col = TERRAIN_PROPS[z["type"]]["color"]
        if z["kind"] == "rect":
            pygame.draw.rect(
                surf, col,
                (int(z["x"] * sx), int(z["y"] * sy), max(1, int(z["w"] * sx)), max(1, int(z["h"] * sy))),
            )
        else:
            pygame.draw.circle(
                surf, col,
                (int(z["x"] * sx), int(z["y"] * sy)),
                max(2, int(z["r"] * sx)),
            )
    return surf
