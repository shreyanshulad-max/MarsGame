"""
Open-world Mars research colony layout + top-down 2.5D rendering.
World: 3200 × 2200. Challenges stay in main.py; this only builds the hub.
"""

from __future__ import annotations

import math
import random

import pygame

from . import interactions

WORLD_W = 3200
WORLD_H = 2200

SKY_TOP = (255, 140, 70)
SKY_LOW = (160, 55, 40)
GROUND_LIGHT = (190, 95, 60)
GROUND_DARK = (140, 65, 40)
GROUND_SHADOW = (95, 45, 30)
ROCK_LIGHT = (175, 100, 70)
ROCK_DARK = (110, 55, 35)
MOUNTAIN_FAR = (120, 55, 40)
MOUNTAIN_MID = (145, 65, 45)


def _lerp(a, b, t):
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def make_colony(
    screen_ch1: str,
    screen_ch2: str,
    screen_ch3: str,
    screen_research: str = "research",
    screen_shop: str = "shop",
) -> dict:
    """Build zones, props, colliders, stations, collectibles."""
    rng = random.Random(42)

    zones = [
        {
            "id": "habitat",
            "name": "Central Habitat",
            "rect": pygame.Rect(1200, 850, 800, 550),
            "tint": (210, 120, 70),
        },
        {
            "id": "comm",
            "name": "Communication Zone",
            "rect": pygame.Rect(200, 550, 700, 550),
            "tint": (90, 160, 200),
        },
        {
            "id": "energy",
            "name": "Energy / Solar Zone",
            "rect": pygame.Rect(2300, 700, 700, 550),
            "tint": (230, 180, 70),
        },
        {
            "id": "rover",
            "name": "Rover Garage Zone",
            "rect": pygame.Rect(350, 1450, 750, 500),
            "tint": (220, 100, 60),
        },
        {
            "id": "research",
            "name": "Research Zone",
            "rect": pygame.Rect(2100, 250, 800, 450),
            "tint": (140, 200, 220),
        },
        {
            "id": "outer",
            "name": "Outer Mars Terrain",
            "rect": pygame.Rect(0, 0, WORLD_W, WORLD_H),
            "tint": (160, 80, 50),
        },
    ]

    habitat_pos = (1480, 980)
    antenna_pos = (420, 720)
    solar_pos = (2520, 880)
    solar2_pos = (2720, 940)
    rover_garage_pos = (520, 1620)
    research_lab_pos = (2350, 380)
    research_anchor = (2480, 480)

    # Visual props for Y-sort: {kind, x, y, w, h, ...}
    props = []

    def add_rock(x, y, w, h, solid=True):
        props.append({"kind": "rock", "x": x, "y": y, "w": w, "h": h, "solid": solid, "sort_y": y + h})

    def add_crater(x, y, r):
        props.append({"kind": "crater", "x": x, "y": y, "r": r, "solid": False, "sort_y": y})

    def add_debris(x, y):
        props.append({"kind": "debris", "x": x, "y": y, "solid": False, "sort_y": y + 8})

    # Spread rocks / craters / debris (avoid spawn pad)
    spawn = (1600.0, 1280.0)
    for _ in range(55):
        x = rng.randint(80, WORLD_W - 80)
        y = rng.randint(120, WORLD_H - 80)
        if abs(x - spawn[0]) < 120 and abs(y - spawn[1]) < 100:
            continue
        w, h = rng.randint(28, 70), rng.randint(18, 40)
        add_rock(x, y, w, h, solid=True)
    for _ in range(22):
        add_crater(rng.randint(100, WORLD_W - 100), rng.randint(150, WORLD_H - 100), rng.randint(18, 42))
    for _ in range(30):
        add_debris(rng.randint(100, WORLD_W - 100), rng.randint(150, WORLD_H - 100))

    # Seeded ground details (sand, cracks, rover tracks) — decorative only
    ground_details = []
    for _ in range(40):
        ground_details.append(
            {
                "kind": "sand",
                "x": rng.randint(50, WORLD_W - 50),
                "y": rng.randint(80, WORLD_H - 80),
                "w": rng.randint(40, 110),
                "h": rng.randint(18, 40),
            }
        )
    for _ in range(25):
        ground_details.append(
            {
                "kind": "crack",
                "x": rng.randint(50, WORLD_W - 50),
                "y": rng.randint(80, WORLD_H - 80),
                "w": rng.randint(20, 70),
                "h": rng.randint(-20, 20),
            }
        )
    for _ in range(8):
        ground_details.append(
            {
                "kind": "track",
                "x": rng.randint(200, WORLD_W - 200),
                "y": rng.randint(400, WORLD_H - 200),
                "w": rng.randint(80, 220),
                "h": 0,
            }
        )

    # Buildings as props (visual) — collision boxes separate
    props.append({"kind": "habitat", "x": habitat_pos[0], "y": habitat_pos[1], "sort_y": habitat_pos[1] + 120})
    props.append({"kind": "antenna", "x": antenna_pos[0], "y": antenna_pos[1], "sort_y": antenna_pos[1] + 110})
    props.append({"kind": "solar", "x": solar_pos[0], "y": solar_pos[1], "sort_y": solar_pos[1] + 100})
    props.append({"kind": "solar", "x": solar2_pos[0], "y": solar2_pos[1], "sort_y": solar2_pos[1] + 100})
    props.append({"kind": "garage", "x": rover_garage_pos[0], "y": rover_garage_pos[1], "sort_y": rover_garage_pos[1] + 100})
    props.append({"kind": "lab", "x": research_lab_pos[0], "y": research_lab_pos[1], "sort_y": research_lab_pos[1] + 90})
    props.append({"kind": "rover_park", "x": rover_garage_pos[0] + 160, "y": rover_garage_pos[1] + 40, "sort_y": rover_garage_pos[1] + 90})

    colliders = [
        pygame.Rect(habitat_pos[0] + 10, habitat_pos[1] + 50, 220, 100),
        pygame.Rect(antenna_pos[0] - 4, antenna_pos[1] + 50, 48, 70),
        pygame.Rect(solar_pos[0] + 8, solar_pos[1] + 45, 150, 65),
        pygame.Rect(solar2_pos[0] + 8, solar2_pos[1] + 45, 150, 65),
        pygame.Rect(rover_garage_pos[0], rover_garage_pos[1] + 20, 200, 110),
        pygame.Rect(research_lab_pos[0] + 10, research_lab_pos[1] + 30, 180, 90),
        pygame.Rect(rover_garage_pos[0] + 155, rover_garage_pos[1] + 45, 120, 50),
    ]
    for p in props:
        if p["kind"] == "rock" and p.get("solid"):
            colliders.append(pygame.Rect(p["x"], p["y"], p["w"], p["h"]))

    stations = [
        interactions.make_station(
            "comm",
            "Communication Station",
            (antenna_pos[0] + 20, antenna_pos[1] + 125),
            screen_ch1,
            "E - Access Communication Station",
            (90, 200, 255),
            radius=78,
        ),
        interactions.make_station(
            "power",
            "Habitat Power Control",
            (habitat_pos[0] + 240, habitat_pos[1] + 130),
            screen_ch2,
            "E - Access Habitat Power Control",
            (255, 200, 80),
            radius=78,
        ),
        interactions.make_station(
            "rover",
            "Rover Mission Terminal",
            (rover_garage_pos[0] + 100, rover_garage_pos[1] + 140),
            screen_ch3,
            "E - Access Rover Mission",
            (220, 100, 50),
            radius=78,
        ),
        interactions.make_station(
            "research",
            "Research Terminal",
            (research_lab_pos[0] + 100, research_lab_pos[1] + 120),
            screen_research,
            "E - Open Research Terminal",
            (120, 200, 230),
            radius=78,
        ),
        interactions.make_station(
            "shop",
            "Research Procurement",
            (habitat_pos[0] + 40, habitat_pos[1] + 140),
            screen_shop,
            "E - Open Procurement Station",
            (180, 220, 120),
            radius=72,
        ),
    ]

    # Flavor samples only — mission materials are spawned by caches.refresh_colony_supplies
    collectibles = [
        interactions.make_collectible(
            "mineral_01",
            "Geological Mineral Sample",
            (2280, 520),
            "mineral",
            "E - Collect Mineral Sample",
            (200, 160, 90),
        ),
        interactions.make_collectible(
            "data_01",
            "Research Data Storage Device",
            (2550, 420),
            "data",
            "E - Collect Data Device",
            (120, 200, 230),
        ),
    ]

    return {
        "world_w": WORLD_W,
        "world_h": WORLD_H,
        "zones": zones,
        "props": props,
        "colliders": colliders,
        "stations": stations,
        "collectibles": collectibles,
        "interactables": stations + collectibles,
        "habitat_pos": habitat_pos,
        "antenna_pos": antenna_pos,
        "solar_pos": solar_pos,
        "rover_garage_pos": rover_garage_pos,
        "research_lab_pos": research_lab_pos,
        "research_anchor": research_anchor,
        "spawn": spawn,
        "ground_details": ground_details,
    }


def zone_at(colony: dict, x: float, y: float) -> str:
    # Prefer specific zones over outer
    for zone in colony["zones"]:
        if zone["id"] == "outer":
            continue
        if zone["rect"].collidepoint(int(x), int(y)):
            return zone["name"]
    return "Outer Mars Terrain"


def current_objective(communication_status, power_status, food_status, rover_status) -> str:
    if communication_status != "ONLINE":
        return "Reach the Communication Zone and restore the link."
    if power_status != "ONLINE" or food_status != "SAFE":
        return "Access Habitat Power Control and restore shelter power."
    if rover_status != "RESCUED":
        return "Go to the Rover Garage and begin the rescue mission."
    return "Colony systems nominal. Continue exploring Mars."


def _draw_ground_viewport(surface, cam, colony):
    """Detailed Mars ground for the visible region (no full-world surface)."""
    # Layered bands with variation
    for i in range(0, cam["view_h"] + 48, 16):
        wy = cam["y"] + i
        wx0 = cam["x"]
        t = (wy * 0.01 + wx0 * 0.004) % 1.0
        base = _lerp(GROUND_LIGHT, GROUND_DARK, 0.3 + 0.35 * math.sin(t * 6.28))
        # Subtle stripe noise
        n = (math.sin(wy * 0.07) + math.cos(wx0 * 0.03 + wy * 0.02)) * 0.08
        color = _lerp(base, (210, 110, 65), max(0, min(1, 0.5 + n)))
        pygame.draw.rect(surface, color, (0, i, cam["view_w"], 18))

    # Zone floor tint overlays
    for zone in colony["zones"]:
        if zone["id"] == "outer":
            continue
        r = zone["rect"]
        sx = int(r.x - cam["x"])
        sy = int(r.y - cam["y"])
        if sx > cam["view_w"] or sy > cam["view_h"] or sx + r.w < 0 or sy + r.h < 0:
            continue
        overlay = pygame.Surface((min(r.w, cam["view_w"] + 40), min(r.h, cam["view_h"] + 40)), pygame.SRCALPHA)
        # clip blit region
        blit_w = min(r.w, cam["view_w"] - max(0, sx) + 20)
        blit_h = min(r.h, cam["view_h"] - max(0, sy) + 20)
        if blit_w <= 0 or blit_h <= 0:
            continue
        patch = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        alpha = 36 if zone["id"] in ("habitat", "rover") else 24
        patch.fill((*zone["tint"], alpha))
        # Metal / pad sheen for habitat & rover
        if zone["id"] in ("habitat", "rover", "research"):
            for k in range(0, r.w, 48):
                pygame.draw.line(patch, (255, 220, 180, 18), (k, 0), (k + 20, r.h), 2)
        surface.blit(patch, (sx, sy))

    # Seeded sand patches / cracks visible in viewport
    view = pygame.Rect(int(cam["x"]) - 40, int(cam["y"]) - 40, cam["view_w"] + 80, cam["view_h"] + 80)
    for patch in colony.get("ground_details", []):
        if not view.collidepoint(patch["x"], patch["y"]):
            continue
        sx = int(patch["x"] - cam["x"])
        sy = int(patch["y"] - cam["y"])
        if patch["kind"] == "sand":
            pygame.draw.ellipse(
                surface,
                (200, 120, 70),
                (sx, sy, patch["w"], patch["h"]),
            )
            pygame.draw.ellipse(
                surface,
                (180, 100, 55),
                (sx + 4, sy + 3, patch["w"] // 2, patch["h"] // 2),
            )
        elif patch["kind"] == "crack":
            pygame.draw.line(
                surface,
                (90, 45, 30),
                (sx, sy),
                (sx + patch["w"], sy + patch["h"]),
                2,
            )
        elif patch["kind"] == "track":
            pygame.draw.line(surface, (110, 55, 35), (sx, sy), (sx + patch["w"], sy), 3)
            pygame.draw.line(surface, (110, 55, 35), (sx, sy + 8), (sx + patch["w"], sy + 8), 3)


def _draw_sky(surface, cam, parallax):
    for y in range(0, 220):
        t = y / 220
        color = _lerp(SKY_TOP, SKY_LOW, t)
        pygame.draw.line(surface, color, (0, y), (cam["view_w"], y))
    # Sun
    sun_x = int(980 - cam["x"] * 0.05 + parallax * 0.2)
    sun_y = 90
    for r, col in ((55, (255, 180, 100)), (28, (255, 230, 180))):
        pygame.draw.circle(surface, col, (sun_x, sun_y), r)
    # Distant mountains (screen-space parallax)
    pts_far = [(0, 200), (200, 150), (450, 190), (700, 130), (1000, 180), (1300, 140)]
    shift = -cam["x"] * 0.12
    poly = [(p[0] + shift, p[1]) for p in pts_far] + [(cam["view_w"] + 40, 220), (-40, 220)]
    pygame.draw.polygon(surface, MOUNTAIN_FAR, poly)
    pts_mid = [(0, 210), (260, 170), (520, 205), (820, 160), (1100, 200), (1400, 175)]
    shift2 = -cam["x"] * 0.22
    poly2 = [(p[0] + shift2, p[1] + 10) for p in pts_mid] + [(cam["view_w"] + 40, 240), (-40, 240)]
    pygame.draw.polygon(surface, MOUNTAIN_MID, poly2)


def _draw_prop(surface, prop, cam, status):
    sx = int(prop["x"] - cam["x"])
    sy = int(prop["y"] - cam["y"])
    kind = prop["kind"]

    if kind == "crater":
        r = prop["r"]
        if sx < -r or sy < -r or sx > cam["view_w"] + r or sy > cam["view_h"] + r:
            return
        pygame.draw.ellipse(surface, GROUND_SHADOW, (sx - r, sy - r // 2, r * 2, r))
        return

    if kind == "rock":
        w, h = prop["w"], prop["h"]
        if sx < -40 or sy < -40 or sx > cam["view_w"] + 40 or sy > cam["view_h"] + 40:
            return
        pygame.draw.ellipse(surface, GROUND_SHADOW, (sx + 3, sy + h // 2, w, max(6, h // 2)))
        pygame.draw.ellipse(surface, ROCK_DARK, (sx, sy, w, h))
        pygame.draw.ellipse(surface, ROCK_LIGHT, (sx + 5, sy + 3, w // 2, h // 2))
        return

    if kind == "debris":
        if sx < -20 or sy < -20 or sx > cam["view_w"] + 20 or sy > cam["view_h"] + 20:
            return
        pygame.draw.rect(surface, (120, 90, 70), (sx, sy, 14, 8), border_radius=2)
        return

    if kind == "habitat":
        pygame.draw.ellipse(surface, GROUND_SHADOW, (sx - 14, sy + 108, 260, 40))
        # Side module
        pygame.draw.rect(surface, (160, 165, 175), (sx - 25, sy + 55, 50, 70), border_radius=6)
        pygame.draw.rect(surface, (120, 125, 135), (sx - 25, sy + 55, 50, 70), 2, border_radius=6)
        body = pygame.Rect(sx, sy + 38, 230, 95)
        pygame.draw.rect(surface, (205, 210, 220), body, border_radius=12)
        pygame.draw.rect(surface, (150, 155, 165), body, 2, border_radius=12)
        # Panel lines
        for lx in (sx + 40, sx + 115, sx + 190):
            pygame.draw.line(surface, (170, 175, 185), (lx, sy + 45), (lx, sy + 125), 1)
        pygame.draw.ellipse(surface, (240, 243, 248), (sx + 18, sy - 5, 195, 78))
        pygame.draw.ellipse(surface, (170, 175, 185), (sx + 18, sy - 5, 195, 78), 2)
        pygame.draw.ellipse(surface, (255, 255, 255), (sx + 55, sy + 8, 70, 22))
        win = (110, 220, 245) if status["power"] == "ONLINE" else (45, 55, 70)
        for wx in (sx + 40, sx + 100, sx + 160):
            pygame.draw.rect(surface, win, (wx, sy + 55, 30, 34), border_radius=4)
            pygame.draw.rect(surface, (40, 80, 100), (wx, sy + 55, 30, 34), 1, border_radius=4)
            if status["power"] == "ONLINE":
                pygame.draw.circle(surface, (255, 235, 140), (wx + 15, sy + 48), 4)
                pygame.draw.line(surface, (200, 240, 255), (wx + 4, sy + 60), (wx + 12, sy + 72), 2)
        door = pygame.Rect(sx + 95, sy + 78, 42, 52)
        pygame.draw.rect(surface, (55, 60, 70), door, border_radius=5)
        pygame.draw.rect(surface, (100, 105, 115), (sx + 100, sy + 84, 32, 40), border_radius=3)
        pygame.draw.circle(surface, (255, 200, 80), (sx + 128, sy + 104), 3)
        food_col = (120, 220, 140) if status["food"] == "SAFE" else (255, 90, 70)
        pygame.draw.circle(surface, food_col, (sx + 215, sy + 48), 7)
        pygame.draw.circle(surface, (20, 20, 20), (sx + 215, sy + 48), 7, 1)
        # Ramp
        pygame.draw.polygon(
            surface,
            (130, 135, 145),
            [(sx + 90, sy + 130), (sx + 142, sy + 130), (sx + 155, sy + 148), (sx + 78, sy + 148)],
        )
        return

    if kind == "antenna":
        pygame.draw.ellipse(surface, GROUND_SHADOW, (sx - 10, sy + 105, 70, 18))
        pygame.draw.rect(surface, (95, 100, 110), (sx + 2, sy + 85, 40, 28), border_radius=3)
        pygame.draw.rect(surface, (130, 135, 145), (sx + 14, sy + 15, 12, 75))
        pygame.draw.line(surface, (90, 95, 105), (sx + 8, sy + 40), (sx + 32, sy + 70), 3)
        pygame.draw.ellipse(surface, (210, 215, 225), (sx - 8, sy + 5, 58, 32))
        pygame.draw.ellipse(surface, (120, 130, 150), (sx + 2, sy + 12, 38, 20))
        pygame.draw.line(surface, (190, 195, 205), (sx + 20, sy + 20), (sx + 48, sy - 10), 3)
        tip = (80, 220, 120) if status["comm"] == "ONLINE" else (255, 70, 60)
        blink = True
        if status["comm"] != "ONLINE":
            blink = (pygame.time.get_ticks() // 280) % 2 == 0
        if blink:
            pygame.draw.circle(surface, tip, (sx + 20, sy), 7)
            pygame.draw.circle(surface, (255, 255, 255), (sx + 18, sy - 2), 2)
        if status["comm"] == "ONLINE":
            pulse = int((pygame.time.get_ticks() // 180) % 4)
            pygame.draw.circle(surface, (90, 220, 160), (sx + 20, sy), 12 + pulse * 7, 1)
        return

    if kind == "solar":
        pygame.draw.ellipse(surface, GROUND_SHADOW, (sx + 8, sy + 98, 160, 20))
        pygame.draw.rect(surface, (85, 90, 98), (sx + 32, sy + 48, 10, 55))
        pygame.draw.rect(surface, (85, 90, 98), (sx + 122, sy + 48, 10, 55))
        for ox, oy in ((0, 18), (78, 10)):
            panel = [
                (sx + ox, sy + oy + 8),
                (sx + ox + 72, sy + oy - 6),
                (sx + ox + 72, sy + oy + 48),
                (sx + ox, sy + oy + 62),
            ]
            pygame.draw.polygon(surface, (40, 90, 170), panel)
            pygame.draw.polygon(surface, (180, 200, 230), panel, 1)
            # Cell grid + highlight
            pygame.draw.line(surface, (70, 130, 200), panel[0], panel[1], 1)
            mid = ((panel[0][0] + panel[1][0]) // 2, (panel[0][1] + panel[1][1]) // 2 + 20)
            pygame.draw.circle(surface, (120, 180, 255), mid, 3)
        return

    if kind == "garage":
        pygame.draw.ellipse(surface, GROUND_SHADOW, (sx - 8, sy + 105, 230, 30))
        pygame.draw.rect(surface, (75, 80, 90), (sx, sy + 18, 210, 110), border_radius=8)
        pygame.draw.rect(surface, (120, 125, 135), (sx, sy + 18, 210, 110), 2, border_radius=8)
        pygame.draw.rect(surface, (35, 38, 48), (sx + 18, sy + 42, 110, 75), border_radius=4)
        # Corrugation
        for i in range(5):
            pygame.draw.line(
                surface, (95, 100, 110),
                (sx + 10 + i * 40, sy + 22), (sx + 10 + i * 40, sy + 120), 1,
            )
        label_col = (120, 220, 140) if status["rover"] == "RESCUED" else (255, 180, 80)
        pygame.draw.rect(surface, label_col, (sx + 145, sy + 28, 52, 20), border_radius=3)
        pygame.draw.circle(surface, label_col, (sx + 195, sy + 55), 5)
        return

    if kind == "lab":
        pygame.draw.ellipse(surface, GROUND_SHADOW, (sx - 4, sy + 98, 200, 26))
        pygame.draw.rect(surface, (175, 185, 200), (sx, sy + 22, 185, 90), border_radius=10)
        pygame.draw.rect(surface, (120, 140, 165), (sx, sy + 22, 185, 90), 2, border_radius=10)
        pygame.draw.polygon(
            surface, (150, 170, 195),
            [(sx + 20, sy + 22), (sx + 90, sy - 8), (sx + 160, sy + 22)],
        )
        for wx in (sx + 25, sx + 95):
            pygame.draw.rect(surface, (60, 150, 200), (wx, sy + 42, 48, 36), border_radius=3)
            pygame.draw.line(surface, (180, 230, 255), (wx + 6, sy + 48), (wx + 18, sy + 62), 2)
        pygame.draw.circle(surface, (255, 200, 80), (sx + 170, sy + 40), 5)
        return

    if kind == "rover_park":
        pygame.draw.ellipse(surface, GROUND_SHADOW, (sx - 6, sy + 42, 130, 20))
        body = pygame.Rect(sx, sy + 8, 108, 38)
        color = (220, 100, 50) if status["rover"] != "RESCUED" else (100, 190, 90)
        pygame.draw.rect(surface, color, body, border_radius=6)
        pygame.draw.rect(surface, (40, 40, 45), body, 2, border_radius=6)
        pygame.draw.rect(surface, (230, 235, 240), (sx + 35, sy - 6, 32, 16), border_radius=3)
        pygame.draw.line(surface, (70, 70, 75), (sx + 50, sy - 6), (sx + 50, sy - 28), 2)
        pygame.draw.circle(surface, (80, 180, 220), (sx + 50, sy - 30), 5)
        for wx in (sx + 16, sx + 52, sx + 90):
            pygame.draw.circle(surface, (35, 35, 40), (wx, sy + 48), 9)
            pygame.draw.circle(surface, (120, 120, 125), (wx, sy + 48), 3)
        return


def draw_colony_world(
    surface,
    colony,
    cam,
    dust,
    parallax,
    status,
    near_id=None,
    draw_fn_dust=None,
    astronaut=None,
    draw_astronaut_fn=None,
    lighting_fn=None,
):
    """Render the open world relative to the camera (Y-sorted props + astronaut)."""
    # Apply camera shake offset without mutating follow position permanently
    draw_cam = {
        **cam,
        "x": cam["x"] + cam.get("ox", 0.0),
        "y": cam["y"] + cam.get("oy", 0.0),
    }
    cam = draw_cam

    _draw_sky(surface, cam, parallax)
    _draw_ground_viewport(surface, cam, colony)

    # Y-sorted props (only near viewport)
    view = pygame.Rect(int(cam["x"]) - 80, int(cam["y"]) - 80, cam["view_w"] + 160, cam["view_h"] + 160)
    visible = []
    for p in colony["props"]:
        if p["kind"] == "crater":
            if view.collidepoint(p["x"], p["y"]):
                visible.append(p)
        elif p["kind"] in ("rock", "debris"):
            if view.colliderect(pygame.Rect(p["x"], p["y"], p.get("w", 16), p.get("h", 10))):
                visible.append(p)
        else:
            if view.collidepoint(p["x"] + 40, p["y"] + 40):
                visible.append(p)
    visible.sort(key=lambda p: p.get("sort_y", p["y"]))

    astro_drawn = False
    astro_y = astronaut["y"] if astronaut else None
    for p in visible:
        if (
            astronaut is not None
            and draw_astronaut_fn is not None
            and not astro_drawn
            and astro_y is not None
            and p.get("sort_y", p["y"]) > astro_y
        ):
            draw_astronaut_fn()
            astro_drawn = True
        _draw_prop(surface, p, cam, status)
    if astronaut is not None and draw_astronaut_fn is not None and not astro_drawn:
        draw_astronaut_fn()

    # Station rings
    for st in colony["stations"]:
        sx = int(st["pos"][0] - cam["x"])
        sy = int(st["pos"][1] - cam["y"])
        if sx < -90 or sy < -90 or sx > cam["view_w"] + 90 or sy > cam["view_h"] + 90:
            continue
        width = 3 if st["id"] == near_id else 1
        pygame.draw.circle(surface, st["marker"], (sx, sy), int(st["radius"] * 0.5), width)
        pygame.draw.circle(surface, st["marker"], (sx, sy - 10), 4)

    # Collectible markers
    for c in colony["collectibles"]:
        if c.get("collected"):
            continue
        sx = int(c["pos"][0] - cam["x"])
        sy = int(c["pos"][1] - cam["y"])
        if sx < -40 or sy < -40 or sx > cam["view_w"] + 40 or sy > cam["view_h"] + 40:
            continue
        pygame.draw.circle(surface, c["marker"], (sx, sy), 10, 2)
        pygame.draw.rect(surface, c["marker"], (sx - 6, sy - 6, 12, 12), border_radius=2)

    if draw_fn_dust:
        draw_fn_dust(surface, dust, cam)

    if lighting_fn:
        lighting_fn(surface, cam, colony, status)
