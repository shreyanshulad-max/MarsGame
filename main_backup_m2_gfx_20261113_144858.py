"""
Mars Mission: Restore, Recharge & Rescue!
A beginner-friendly 2.5D Mars base game.
Shapes are the fallback; PNG assets in /assets are used when present.
"""

import math
import os
import random
import sys

import pygame

# Ensure project root is importable when launched as a script
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from systems import camera as cam_sys
from systems import colony as colony_sys
from systems import hud_explore
from systems import interactions
from systems import inventory as inv_sys
from systems import journal as journal_sys
from systems import minimap as map_sys
from systems import particles as particle_sys
from systems import player as player_sys
from systems.colony import WORLD_H, WORLD_W

# ---- Window size and speed ----
WIDTH = 1280
HEIGHT = 720
FPS = 60

# Folder that holds backgrounds, sprites, effects, ui, and audio
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

# Image cache: key -> Surface or None (None means "tried, missing/failed")
_IMAGE_CACHE = {}

# Cached full layers built once (faster than redrawing every frame)
_SKY_CACHE = None
_HAZE_CACHE = None
_DUST_LAYER = None
_GROUND_BASE_CACHE = None

# ---- Game screens (what the player is looking at) ----
SCREEN_TITLE = "title"              # outdoor base + Start button
SCREEN_BRIEFING = "briefing"        # short mission story
SCREEN_BASE = "base"                # entered the Mars research base
SCREEN_CH1_RADAR = "ch1_radar"      # Challenge 1: scan satellites
SCREEN_CH1_ALIGN = "ch1_align"      # Challenge 1: aim the antenna
SCREEN_CH1_COMPLETE = "ch1_complete"
SCREEN_CH1_TIMEOUT = "ch1_timeout"
SCREEN_CH2_INTRO = "ch2_intro"      # Challenge 2: power failure story
SCREEN_CH2_WIRE = "ch2_wire"        # click-to-connect electrical wires
SCREEN_CH2_POWER = "ch2_power"      # share the energy budget
SCREEN_CH2_COMPLETE = "ch2_complete"
SCREEN_CH2_TIMEOUT = "ch2_timeout"
SCREEN_CH3_INTRO = "ch3_intro"      # Challenge 3: rover rescue story
SCREEN_CH3_SCAN = "ch3_scan"        # find the stranded rover on a grid
SCREEN_CH3_DRIVE = "ch3_drive"      # drive across Mars to rescue it
SCREEN_CH3_COMPLETE = "ch3_complete"
SCREEN_CH3_TIMEOUT = "ch3_timeout"

# ---- Challenge 1 settings ----
CH1_TIME_LIMIT = 90          # seconds on the mission timer
ANTENNA_START_ANGLE = -30    # degrees
ANTENNA_TARGET_ANGLE = 20    # degrees
ANTENNA_STEP = 5             # how far Left/Right moves the dish
CH1_POINTS = 100

# ---- Challenge 2 settings ----
CH2_TIME_LIMIT = 90          # seconds for the power mission
CH2_POINTS = 100
CH2_ENERGY_BUDGET = 80       # total power units the base can use
CH2_FOOD_DECAY_PER_SEC = 4.0 # how fast food freshness drops when cold

# ---- Challenge 3 settings ----
CH3_TIME_LIMIT = 120         # one shared timer for scanning + driving
CH3_POINTS = 100
CH3_WRONG_PENALTY = 5        # seconds lost for a wrong scan guess
CH3_CORRECT_CELL = "B2"      # strongest signal location
CH3_ROVER_SPEED = 220.0      # pixels per second
CH3_HIT_SLOW = 0.45          # brief slow-down after hitting a rock

# ---- Mars colors (dusty orange-red world) ----
SKY_TOP = (255, 140, 70)
SKY_MID = (210, 90, 55)
SKY_LOW = (160, 55, 40)
SUN_CORE = (255, 230, 180)
SUN_GLOW = (255, 180, 100)
MOUNTAIN_FAR = (120, 55, 40)
MOUNTAIN_MID = (145, 65, 45)
MOUNTAIN_NEAR = (170, 75, 50)
GROUND_LIGHT = (190, 95, 60)
GROUND_DARK = (140, 65, 40)
GROUND_SHADOW = (95, 45, 30)
ROCK_LIGHT = (175, 100, 70)
ROCK_DARK = (110, 55, 35)
HABITAT_BODY = (210, 215, 220)
HABITAT_EDGE = (150, 155, 165)
HABITAT_WINDOW = (90, 180, 220)
PANEL_BLUE = (35, 75, 150)
PANEL_CELL = (55, 100, 185)
PANEL_FRAME = (185, 190, 198)
ROVER_BODY = (220, 100, 50)
ROVER_DARK = (140, 55, 30)
HUD_BG = (20, 12, 10)
HUD_TEXT = (255, 230, 200)
HUD_WARN = (255, 180, 80)
HUD_ALERT = (255, 90, 70)
HUD_OK = (120, 220, 140)
BUTTON_NORMAL = (200, 95, 40)
BUTTON_HOVER = (235, 130, 55)
BUTTON_EDGE = (255, 210, 150)
BUTTON_TEXT = (255, 245, 230)
PANEL_DARK = (28, 16, 12)
RADAR_GREEN = (80, 220, 140)
RADAR_DIM = (30, 80, 55)

# Expected relative paths inside assets/ (optional — missing is OK)
ASSET_SKY = "backgrounds/sky.png"
ASSET_MOUNTAINS_FAR = "backgrounds/mountains_far.png"
ASSET_MOUNTAINS_NEAR = "backgrounds/mountains_near.png"
ASSET_GROUND = "backgrounds/ground.png"
ASSET_HABITAT = "sprites/habitat.png"
ASSET_SOLAR = "sprites/solar_panels.png"
ASSET_ANTENNA = "sprites/antenna.png"
ASSET_ROVER = "sprites/rover.png"
ASSET_ROCK = "sprites/rocks/rock1.png"


def lerp_color(color_a, color_b, t):
    """Blend two colors. t=0 means color_a, t=1 means color_b."""
    return (
        int(color_a[0] + (color_b[0] - color_a[0]) * t),
        int(color_a[1] + (color_b[1] - color_a[1]) * t),
        int(color_a[2] + (color_b[2] - color_a[2]) * t),
    )


# =====================================================================
# Image loading (cache + safe missing-file handling)
# =====================================================================


def asset_path(*parts):
    """Build a full path under the assets folder."""
    return os.path.join(ASSETS_DIR, *parts)


def load_image(relative_path, size=None):
    """
    Load a PNG from assets/ and remember it.
    relative_path examples: "sprites/rover.png", "backgrounds/sky.png"
    size: optional (width, height) to scale once.
    Returns a Surface, or None if the file is missing / broken.
    """
    cache_key = (relative_path.replace("\\", "/"), size)
    if cache_key in _IMAGE_CACHE:
        return _IMAGE_CACHE[cache_key]

    full_path = asset_path(*relative_path.replace("\\", "/").split("/"))
    if not os.path.isfile(full_path):
        _IMAGE_CACHE[cache_key] = None
        return None

    try:
        image = pygame.image.load(full_path)
        # Transparent PNGs keep their alpha channel
        if image.get_alpha() is not None or full_path.lower().endswith(".png"):
            image = image.convert_alpha()
        else:
            image = image.convert()
        if size is not None:
            image = pygame.transform.smoothscale(image, size)
        _IMAGE_CACHE[cache_key] = image
        return image
    except (pygame.error, OSError, ValueError):
        # Never crash the game because of a bad/missing image
        _IMAGE_CACHE[cache_key] = None
        return None


def blit_sprite(surface, relative_path, pos, size=None):
    """Draw a sprite if it exists. Returns True when drawn, else False."""
    image = load_image(relative_path, size=size)
    if image is None:
        return False
    surface.blit(image, pos)
    return True


def preload_environment_assets():
    """Load common environment images once at startup (not every frame)."""
    # Sizes match how we blit them in the world
    candidates = [
        (ASSET_SKY, (WIDTH, 400)),
        (ASSET_MOUNTAINS_FAR, (WIDTH + 100, 300)),
        (ASSET_MOUNTAINS_NEAR, (WIDTH + 100, 280)),
        (ASSET_GROUND, (WIDTH, 320)),
        (ASSET_HABITAT, (210, 145)),
        (ASSET_SOLAR, (170, 120)),
        (ASSET_ANTENNA, (70, 170)),
        (ASSET_ROVER, (140, 80)),
        (ASSET_ROCK, (48, 32)),
    ]
    for path, size in candidates:
        load_image(path, size=size)
    # Build gradient caches that do not depend on PNGs
    get_sky_surface()
    get_haze_surface()
    get_ground_base_surface()


def get_sky_surface():
    """Sky plate: PNG if present, else a cached gradient (drawn once)."""
    global _SKY_CACHE
    if _SKY_CACHE is not None:
        return _SKY_CACHE

    sky_h = 400
    png = load_image(ASSET_SKY, size=(WIDTH, sky_h))
    if png is not None:
        _SKY_CACHE = png
        return _SKY_CACHE

    sky = pygame.Surface((WIDTH, sky_h))
    for y in range(sky_h):
        t = y / sky_h
        if t < 0.45:
            color = lerp_color(SKY_TOP, SKY_MID, t / 0.45)
        else:
            color = lerp_color(SKY_MID, SKY_LOW, (t - 0.45) / 0.55)
        pygame.draw.line(sky, color, (0, y), (WIDTH, y))
    _SKY_CACHE = sky
    return _SKY_CACHE


def get_haze_surface():
    """Horizon haze plate built once."""
    global _HAZE_CACHE
    if _HAZE_CACHE is not None:
        return _HAZE_CACHE
    haze = pygame.Surface((WIDTH, 180), pygame.SRCALPHA)
    for y in range(180):
        alpha = int(80 * (y / 180))
        pygame.draw.line(haze, (255, 160, 100, alpha), (0, y), (WIDTH, y))
    _HAZE_CACHE = haze
    return _HAZE_CACHE


def get_ground_base_surface():
    """Ground plate: PNG if present, else a cached sandy fill."""
    global _GROUND_BASE_CACHE
    if _GROUND_BASE_CACHE is not None:
        return _GROUND_BASE_CACHE

    png = load_image(ASSET_GROUND, size=(WIDTH, 320))
    if png is not None:
        _GROUND_BASE_CACHE = png
        return _GROUND_BASE_CACHE

    ground = pygame.Surface((WIDTH, 320))
    ground.fill(GROUND_LIGHT)
    for i in range(10):
        shade = lerp_color(GROUND_LIGHT, GROUND_DARK, i / 12)
        pygame.draw.ellipse(ground, shade, (-50 + i * 35, 20 + i * 28, WIDTH + 100, 55))
    _GROUND_BASE_CACHE = ground
    return _GROUND_BASE_CACHE


def draw_sky(surface):
    """Paint a dusty Mars sky (cached plate — fast every frame)."""
    surface.blit(get_sky_surface(), (0, 0))


def draw_hazy_sun(surface, cx, cy):
    """Draw a soft, hazy sun with glowing rings around it."""
    # Soft rings use small surfaces; cheap compared to full-screen redraws
    for radius, alpha in ((140, 28), (100, 40), (70, 55)):
        glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 185, 100, alpha), (radius, radius), radius)
        surface.blit(glow, (cx - radius, cy - radius))

    pygame.draw.circle(surface, SUN_GLOW, (cx, cy), 40)
    pygame.draw.circle(surface, SUN_CORE, (cx, cy), 26)


def draw_atmosphere(surface):
    """Add a soft dusty haze near the horizon for depth."""
    surface.blit(get_haze_surface(), (0, HEIGHT // 2 - 120))


def _shift_peaks(peaks, offset_x):
    """Move mountain peaks sideways for a gentle parallax slide."""
    return [(x + offset_x, y) for x, y in peaks]


def mountain_ridge(base_y, peaks, color, surface):
    """Draw one mountain layer from a list of peak points."""
    points = [(0, HEIGHT), (0, base_y)]
    points.extend(peaks)
    points.extend([(WIDTH, base_y), (WIDTH, HEIGHT)])
    pygame.draw.polygon(surface, color, points)

    shadow = lerp_color(color, (40, 20, 15), 0.35)
    for i in range(0, len(peaks) - 1, 2):
        x, y = peaks[i]
        nx, ny = peaks[i + 1]
        pygame.draw.polygon(
            surface,
            shadow,
            [(x, y), (nx, ny), (nx, base_y + 40), (x - 20, base_y + 40)],
        )


def draw_mountains(surface, parallax=0.0):
    """Draw layered mountains (PNG layers if present, else shapes)."""
    # Far PNG layer
    far_img = load_image(ASSET_MOUNTAINS_FAR, size=(WIDTH + 100, 300))
    if far_img is not None:
        surface.blit(far_img, (int(parallax * 0.25) - 40, 140))
    else:
        mountain_ridge(
            340,
            _shift_peaks(
                [
                    (80, 300), (160, 250), (250, 310), (340, 230), (430, 290),
                    (520, 240), (610, 300), (720, 220), (830, 285), (940, 245),
                    (1050, 300), (1150, 255), (1240, 310),
                ],
                int(parallax * 0.25),
            ),
            MOUNTAIN_FAR,
            surface,
        )

    # Mid shapes always add depth between far and near
    mountain_ridge(
        380,
        _shift_peaks(
            [
                (40, 340), (140, 290), (240, 350), (350, 270), (470, 340),
                (580, 285), (690, 355), (800, 275), (920, 340), (1040, 295),
                (1160, 350), (1260, 310),
            ],
            int(parallax * 0.55),
        ),
        MOUNTAIN_MID,
        surface,
    )

    near_img = load_image(ASSET_MOUNTAINS_NEAR, size=(WIDTH + 100, 280))
    if near_img is not None:
        surface.blit(near_img, (int(parallax * 1.0) - 50, 200))
    else:
        mountain_ridge(
            420,
            _shift_peaks(
                [
                    (0, 390), (110, 330), (220, 400), (330, 310), (450, 385),
                    (560, 325), (680, 405), (790, 320), (910, 390), (1030, 335),
                    (1140, 400), (1280, 360),
                ],
                int(parallax * 1.0),
            ),
            MOUNTAIN_NEAR,
            surface,
        )


def make_ground_details(seed=42):
    """Create rocks and craters once so they stay in the same place."""
    rng = random.Random(seed)
    rocks = []
    craters = []

    for _ in range(55):
        rocks.append(
            {
                "x": rng.randint(20, WIDTH - 20),
                "y": rng.randint(470, HEIGHT - 30),
                "w": rng.randint(8, 28),
                "h": rng.randint(5, 16),
            }
        )

    for _ in range(14):
        craters.append(
            {
                "x": rng.randint(80, WIDTH - 80),
                "y": rng.randint(490, HEIGHT - 60),
                "r": rng.randint(18, 42),
            }
        )

    return rocks, craters


def make_dust_particles(count=55, seed=7):
    """Make tiny dust specks that drift across the Mars air."""
    rng = random.Random(seed)
    particles = []
    for _ in range(count):
        particles.append(
            {
                "x": rng.uniform(0, WIDTH),
                "y": rng.uniform(80, HEIGHT - 40),
                "speed": rng.uniform(0.25, 1.1),
                "drift": rng.uniform(-0.15, 0.25),
                "size": rng.randint(1, 3),
                "alpha": rng.randint(50, 140),
            }
        )
    return particles


def update_dust_particles(particles):
    """Move each dust speck a little every frame."""
    for p in particles:
        p["x"] += p["speed"]
        p["y"] += p["drift"] + math.sin(p["x"] * 0.01) * 0.08
        if p["x"] > WIDTH + 4:
            p["x"] = -4
            p["y"] = random.uniform(100, HEIGHT - 50)
        if p["y"] < 60:
            p["y"] = 60
        if p["y"] > HEIGHT - 20:
            p["y"] = HEIGHT - 20


def draw_dust_particles(surface, particles):
    """Draw floating dust. Reuses one alpha layer instead of making a new one."""
    global _DUST_LAYER
    if _DUST_LAYER is None:
        _DUST_LAYER = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    _DUST_LAYER.fill((0, 0, 0, 0))
    for p in particles:
        color = (255, 200, 140, p["alpha"])
        pygame.draw.circle(_DUST_LAYER, color, (int(p["x"]), int(p["y"])), p["size"])
    surface.blit(_DUST_LAYER, (0, 0))


def draw_ground(surface, rocks, craters):
    """Draw the rocky Mars floor with shadows and craters."""
    # Cached sandy plate (PNG or generated)
    surface.blit(get_ground_base_surface(), (0, 400))

    # Soft long shadows for depth (cheap ellipses)
    for i in range(5):
        shade = lerp_color(GROUND_DARK, GROUND_SHADOW, i / 6)
        pygame.draw.ellipse(
            surface,
            shade,
            (-60 + i * 50, 455 + i * 38, WIDTH + 120, 40),
        )

    rock_sprite = load_image(ASSET_ROCK, size=(48, 32))

    for crater in craters:
        x, y, r = crater["x"], crater["y"], crater["r"]
        # Soft outer shadow ring
        pygame.draw.ellipse(
            surface,
            (70, 35, 25),
            (x - r - 4, y - r // 2 + 2, r * 2 + 8, r + 6),
        )
        pygame.draw.ellipse(surface, GROUND_SHADOW, (x - r, y - r // 2, r * 2, r))
        pygame.draw.ellipse(
            surface,
            lerp_color(GROUND_SHADOW, GROUND_DARK, 0.4),
            (x - r + 6, y - r // 2 + 4, r * 2 - 12, r - 8),
        )
        pygame.draw.arc(
            surface,
            ROCK_LIGHT,
            (x - r, y - r // 2, r * 2, r),
            3.4,
            5.6,
            2,
        )

    for rock in rocks:
        x, y, w, h = rock["x"], rock["y"], rock["w"], rock["h"]
        # Drop shadow under every rock
        pygame.draw.ellipse(surface, GROUND_SHADOW, (x + 4, y + h // 2 + 2, w, max(6, h // 2)))
        if rock_sprite is not None and w >= 18:
            # Use the cached rock sprite (already scaled at load time)
            surface.blit(rock_sprite, (x - 4, y - 6))
        else:
            pygame.draw.ellipse(surface, ROCK_DARK, (x, y, w, h))
            pygame.draw.ellipse(surface, ROCK_LIGHT, (x + 2, y + 1, w // 2, h // 2))


def draw_habitat(surface, x, y):
    """Draw a futuristic habitat (sprite if available, else shapes)."""
    # Always keep a ground shadow for depth
    pygame.draw.ellipse(surface, GROUND_SHADOW, (x - 20, y + 95, 220, 36))

    if blit_sprite(surface, ASSET_HABITAT, (x - 5, y - 8), size=(210, 145)):
        return

    pygame.draw.ellipse(surface, (160, 160, 170), (x - 10, y + 100, 200, 24))

    body = [(x + 20, y + 40), (x + 160, y + 40), (x + 170, y + 110), (x + 10, y + 110)]
    pygame.draw.polygon(surface, HABITAT_BODY, body)
    pygame.draw.polygon(surface, HABITAT_EDGE, body, 2)

    side = [(x + 160, y + 40), (x + 185, y + 55), (x + 185, y + 120), (x + 170, y + 110)]
    pygame.draw.polygon(surface, (170, 175, 185), side)
    pygame.draw.polygon(surface, HABITAT_EDGE, side, 1)

    pygame.draw.ellipse(surface, (230, 235, 240), (x + 15, y, 150, 70))
    pygame.draw.ellipse(surface, HABITAT_EDGE, (x + 15, y, 150, 70), 2)
    pygame.draw.ellipse(surface, (250, 252, 255), (x + 45, y + 10, 55, 22))

    for wx in (x + 35, x + 80, x + 125):
        pygame.draw.rect(surface, HABITAT_WINDOW, (wx, y + 52, 24, 30), border_radius=4)
        pygame.draw.rect(surface, (40, 80, 110), (wx, y + 52, 24, 30), 2, border_radius=4)
        pygame.draw.line(surface, (200, 240, 255), (wx + 3, y + 55), (wx + 9, y + 68), 2)

    pygame.draw.rect(surface, (70, 75, 85), (x + 74, y + 78, 36, 32), border_radius=4)
    pygame.draw.rect(surface, (110, 115, 125), (x + 78, y + 82, 28, 24), border_radius=3)
    pygame.draw.circle(surface, (255, 200, 80), (x + 100, y + 94), 3)
    pygame.draw.polygon(
        surface,
        (150, 150, 158),
        [(x + 70, y + 110), (x + 114, y + 110), (x + 124, y + 122), (x + 60, y + 122)],
    )


def draw_communication_antenna(surface, x, y, online=False):
    """Draw a tall communication antenna (sprite if available, else shapes)."""
    pygame.draw.ellipse(surface, GROUND_SHADOW, (x - 8, y + 95, 50, 16))

    if blit_sprite(surface, ASSET_ANTENNA, (x - 15, y - 60), size=(70, 170)):
        # Status light still drawn so ONLINE/OFFLINE stays visible
        tip = (80, 220, 120) if online else (255, 70, 60)
        pygame.draw.circle(surface, tip, (x + 17, y - 54), 5)
        return

    pygame.draw.rect(surface, (120, 125, 135), (x, y + 70, 34, 30))
    pygame.draw.rect(surface, (90, 95, 105), (x, y + 70, 34, 30), 2)
    pygame.draw.line(surface, (85, 90, 100), (x + 17, y + 70), (x + 17, y - 50), 4)
    pygame.draw.ellipse(surface, (200, 205, 215), (x - 5, y - 35, 45, 28))
    pygame.draw.ellipse(surface, (120, 130, 150), (x + 2, y - 30, 30, 18))
    pygame.draw.line(surface, (180, 185, 195), (x + 17, y - 20), (x + 40, y - 45), 3)
    tip = (80, 220, 120) if online else (255, 70, 60)
    pygame.draw.circle(surface, tip, (x + 17, y - 54), 5)
    pygame.draw.circle(surface, (255, 180, 160), (x + 15, y - 56), 2)


def draw_solar_panels(surface, x, y):
    """Draw solar panels (sprite if available, else shapes)."""
    pygame.draw.ellipse(surface, GROUND_SHADOW, (x + 5, y + 92, 150, 18))

    if blit_sprite(surface, ASSET_SOLAR, (x - 5, y - 15), size=(170, 120)):
        return

    pygame.draw.rect(surface, (90, 95, 100), (x + 20, y + 42, 8, 55))
    pygame.draw.rect(surface, (90, 95, 100), (x + 118, y + 42, 8, 55))

    panels = (
        [(x, y + 12), (x + 72, y), (x + 72, y + 48), (x, y + 60)],
        [(x + 84, y + 8), (x + 156, y - 4), (x + 156, y + 44), (x + 84, y + 56)],
    )

    for panel in panels:
        pygame.draw.polygon(surface, PANEL_FRAME, panel)
        inset = [
            (panel[0][0] + 5, panel[0][1] + 4),
            (panel[1][0] - 4, panel[1][1] + 4),
            (panel[2][0] - 4, panel[2][1] - 4),
            (panel[3][0] + 5, panel[3][1] - 4),
        ]
        pygame.draw.polygon(surface, PANEL_BLUE, inset)

        for row in range(1, 3):
            t = row / 3
            left = (
                inset[0][0] + (inset[3][0] - inset[0][0]) * t,
                inset[0][1] + (inset[3][1] - inset[0][1]) * t,
            )
            right = (
                inset[1][0] + (inset[2][0] - inset[1][0]) * t,
                inset[1][1] + (inset[2][1] - inset[1][1]) * t,
            )
            pygame.draw.line(surface, PANEL_CELL, left, right, 1)

        for col in range(1, 4):
            t = col / 4
            top = (
                inset[0][0] + (inset[1][0] - inset[0][0]) * t,
                inset[0][1] + (inset[1][1] - inset[0][1]) * t,
            )
            bottom = (
                inset[3][0] + (inset[2][0] - inset[3][0]) * t,
                inset[3][1] + (inset[2][1] - inset[3][1]) * t,
            )
            pygame.draw.line(surface, PANEL_CELL, top, bottom, 1)

        pygame.draw.polygon(surface, PANEL_FRAME, inset, 1)


def draw_rover_wheel(surface, cx, cy, radius):
    """Draw one rover wheel with a hub."""
    pygame.draw.circle(surface, (35, 35, 40), (cx, cy), radius)
    pygame.draw.circle(surface, (85, 85, 92), (cx, cy), radius - 4)
    pygame.draw.circle(surface, (200, 200, 205), (cx, cy), 3)


def draw_rover(surface, x, y):
    """Draw a Mars rover (sprite if available, else six-wheel shapes)."""
    pygame.draw.ellipse(surface, GROUND_SHADOW, (x - 8, y + 34, 120, 20))

    if blit_sprite(surface, ASSET_ROVER, (x - 10, y - 30), size=(140, 80)):
        return

    for wx in (x + 12, x + 48, x + 84):
        draw_rover_wheel(surface, wx + 6, y + 24, 10)

    pygame.draw.line(surface, (70, 70, 75), (x + 10, y + 18), (x + 100, y + 18), 4)

    for wx in (x + 10, x + 48, x + 86):
        draw_rover_wheel(surface, wx, y + 32, 13)

    body = [(x + 8, y + 2), (x + 100, y + 2), (x + 108, y + 24), (x, y + 24)]
    pygame.draw.polygon(surface, ROVER_BODY, body)
    pygame.draw.polygon(surface, ROVER_DARK, body, 2)
    pygame.draw.rect(surface, (240, 150, 90), (x + 18, y + 6, 70, 8), border_radius=2)

    pygame.draw.rect(surface, (230, 230, 235), (x + 36, y - 12, 30, 16), border_radius=3)
    pygame.draw.rect(surface, (60, 140, 180), (x + 41, y - 9, 20, 10), border_radius=2)
    pygame.draw.line(surface, (80, 80, 85), (x + 51, y - 12), (x + 51, y - 34), 3)
    pygame.draw.circle(surface, (50, 50, 55), (x + 51, y - 36), 7)
    pygame.draw.circle(surface, (120, 200, 255), (x + 51, y - 36), 3)

    pygame.draw.line(surface, (180, 185, 190), (x + 95, y + 6), (x + 122, y - 8), 4)
    pygame.draw.line(surface, (180, 185, 190), (x + 122, y - 8), (x + 132, y + 6), 3)
    pygame.draw.circle(surface, (255, 200, 80), (x + 132, y + 6), 4)


def draw_hud(
    surface,
    fonts,
    communication_status="OFFLINE",
    score=0,
    power_status="LOW",
    food_status="AT RISK",
    rover_status="MISSING",
):
    """Show mission title and base status (fits inside the panel)."""
    panel_h = 172
    panel = pygame.Surface((430, panel_h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*HUD_BG, 175), (0, 0, 430, panel_h), border_radius=10)
    pygame.draw.rect(panel, (255, 180, 100, 130), (0, 0, 430, panel_h), 2, border_radius=10)
    surface.blit(panel, (20, 18))

    title = fonts["title"].render("MARS MISSION", True, HUD_TEXT)
    surface.blit(title, (36, 26))

    # Colors change when systems are fixed
    comm_color = HUD_OK if communication_status == "ONLINE" else HUD_ALERT
    power_color = HUD_OK if power_status == "ONLINE" else HUD_WARN
    food_color = HUD_OK if food_status == "SAFE" else HUD_ALERT
    rover_color = HUD_OK if rover_status == "RESCUED" else HUD_ALERT

    lines = [
        (f"COMMUNICATION: {communication_status}", comm_color),
        (f"POWER: {power_status}", power_color),
        (f"FOOD: {food_status}", food_color),
        (f"ROVER STATUS: {rover_status}", rover_color),
    ]
    for i, (text, color) in enumerate(lines):
        label = fonts["body"].render(text, True, color)
        surface.blit(label, (36, 62 + i * 26))

    # Small score readout in the top-right of the HUD area
    if score > 0:
        score_label = fonts["small"].render(f"SCORE: {score}", True, HUD_TEXT)
        surface.blit(score_label, (320, 30))


def draw_bottom_notice(surface, fonts, message, center_y=HEIGHT - 58):
    """Show a short message in the bottom notification area."""
    banner = pygame.Surface((640, 56), pygame.SRCALPHA)
    pygame.draw.rect(banner, (*HUD_BG, 175), (0, 0, 640, 56), border_radius=10)
    pygame.draw.rect(banner, (255, 180, 100, 130), (0, 0, 640, 56), 2, border_radius=10)
    surface.blit(banner, (WIDTH // 2 - 320, center_y - 28))

    msg = fonts["body"].render(message, True, HUD_TEXT)
    surface.blit(msg, msg.get_rect(center=(WIDTH // 2, center_y)))


def button_rect(center_x, center_y, width=280, height=58):
    """Make a pygame Rect centered on a point."""
    return pygame.Rect(0, 0, width, height).move(center_x - width // 2, center_y - height // 2)


def draw_button(surface, rect, label, fonts, mouse_pos, font_key="button"):
    """Draw a button that lights up when the mouse is over it."""
    hovered = rect.collidepoint(mouse_pos)
    fill = BUTTON_HOVER if hovered else BUTTON_NORMAL
    shadow = rect.move(0, 4)
    pygame.draw.rect(surface, (40, 20, 10), shadow, border_radius=12)
    pygame.draw.rect(surface, fill, rect, border_radius=12)
    pygame.draw.rect(surface, BUTTON_EDGE, rect, 2, border_radius=12)

    text = fonts[font_key].render(label, True, BUTTON_TEXT)
    text_rect = text.get_rect(center=rect.center)
    surface.blit(text, text_rect)
    return hovered


def draw_briefing_panel(surface, fonts, mouse_pos):
    """Show a short mission briefing and a Continue button."""
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dim.fill((10, 5, 0, 150))
    surface.blit(dim, (0, 0))

    panel = pygame.Rect(240, 140, 800, 420)
    pygame.draw.rect(surface, PANEL_DARK, panel, border_radius=16)
    pygame.draw.rect(surface, (255, 170, 90), panel, 3, border_radius=16)

    heading = fonts["title"].render("MISSION BRIEFING", True, HUD_TEXT)
    surface.blit(heading, heading.get_rect(centerx=panel.centerx, y=165))

    briefing_lines = [
        "Welcome, young astronaut!",
        "A dust storm damaged our Mars research base.",
        "Communication is offline. Power is low. Food is at risk.",
        "Your mission: Restore, Recharge & Rescue!",
        "Enter the base to begin. Challenges come next.",
    ]
    for i, line in enumerate(briefing_lines):
        label = fonts["body"].render(line, True, HUD_TEXT)
        surface.blit(label, label.get_rect(centerx=panel.centerx, y=230 + i * 34))

    continue_rect = button_rect(panel.centerx, 500, 260, 56)
    draw_button(surface, continue_rect, "CONTINUE", fonts, mouse_pos)
    return continue_rect


def draw_world(
    surface,
    rocks,
    craters,
    dust_particles,
    communication_online=False,
    parallax=0.0,
):
    """
    Draw the outdoor Mars environment from back to front.
    parallax: small horizontal shift for layered mountain depth (subtle motion).
    """
    # 1) Sky layer
    draw_sky(surface)
    draw_hazy_sun(surface, 980 + int(parallax * 0.1), 120)

    # 2) Distant + near mountains (parallax differs per layer)
    draw_mountains(surface, parallax=parallax)

    # 3) Atmospheric depth haze
    draw_atmosphere(surface)

    # 4) Mars ground + rocks/craters
    draw_ground(surface, rocks, craters)

    # 5) Mid-ground structures
    draw_habitat(surface, 500, 355)
    draw_communication_antenna(surface, 430, 360, online=communication_online)
    draw_solar_panels(surface, 740, 395)

    # 6) Foreground rover + dust
    draw_rover(surface, 160, 555)
    draw_dust_particles(surface, dust_particles)


def make_challenge1_state():
    """Fresh values every time Challenge 1 starts or restarts."""
    return {
        "phase": "ready",          # ready -> scanning -> results
        "scan_angle": 0.0,         # sweeping radar beam (degrees)
        "scan_progress": 0.0,      # 0 to 1 while scanning
        "hint": "",
        "antenna_angle": ANTENNA_START_ANGLE,
        "points_awarded": False,
        "time_left": float(CH1_TIME_LIMIT),
        "finish_time_left": 0,
        "connection_restored": False,
        "restore_delay": 0.0,  # short pause so kids can read the success message
    }


def signal_strength(angle):
    """How strong the signal is (0-100). Closest to +20 is best."""
    distance = abs(angle - ANTENNA_TARGET_ANGLE)
    # Every degree away from the target lowers the bar
    strength = max(0, 100 - distance * 2)
    return strength


def draw_timer(surface, fonts, time_left):
    """Show the remaining mission time in the top-right."""
    seconds = max(0, int(math.ceil(time_left)))
    color = HUD_ALERT if seconds <= 15 else HUD_TEXT
    panel = pygame.Surface((170, 48), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*HUD_BG, 180), (0, 0, 170, 48), border_radius=8)
    pygame.draw.rect(panel, (255, 180, 100, 130), (0, 0, 170, 48), 2, border_radius=8)
    surface.blit(panel, (WIDTH - 190, 20))
    label = fonts["body"].render(f"TIME: {seconds:02d}s", True, color)
    surface.blit(label, label.get_rect(center=(WIDTH - 105, 44)))


def satellite_positions():
    """Where the three satellites sit on the radar (and their click boxes)."""
    # Different markers: circle, diamond, triangle
    return [
        {
            "id": "SAT-01",
            "status": "CONNECTED",
            "healthy": True,
            "pos": (540, 250),
            "marker": "circle",
            "color": (90, 200, 255),
        },
        {
            "id": "SAT-02",
            "status": "WEAK SIGNAL",
            "healthy": False,
            "pos": (760, 300),
            "marker": "diamond",
            "color": (255, 190, 70),
        },
        {
            "id": "SAT-03",
            "status": "CONNECTED",
            "healthy": True,
            "pos": (650, 420),
            "marker": "triangle",
            "color": (140, 230, 160),
        },
    ]


def draw_satellite_marker(surface, sat):
    """Draw one satellite with its special shape."""
    x, y = sat["pos"]
    color = sat["color"]
    if sat["marker"] == "circle":
        pygame.draw.circle(surface, color, (x, y), 16)
        pygame.draw.circle(surface, (20, 30, 40), (x, y), 16, 2)
        pygame.draw.circle(surface, (255, 255, 255), (x, y), 4)
    elif sat["marker"] == "diamond":
        points = [(x, y - 18), (x + 16, y), (x, y + 18), (x - 16, y)]
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, (20, 30, 40), points, 2)
    else:  # triangle
        points = [(x, y - 18), (x + 16, y + 14), (x - 16, y + 14)]
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, (20, 30, 40), points, 2)

    # Invisible-ish click area used by the caller
    return pygame.Rect(x - 28, y - 28, 56, 56)


def draw_radar_screen(surface, fonts, mouse_pos, ch1):
    """Interactive radar console for Challenge 1."""
    # Soft dim so the Mars world still shows behind the console
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dim.fill((8, 4, 0, 140))
    surface.blit(dim, (0, 0))

    panel = pygame.Rect(160, 70, 960, 560)
    pygame.draw.rect(surface, PANEL_DARK, panel, border_radius=18)
    pygame.draw.rect(surface, (255, 170, 90), panel, 3, border_radius=18)

    title = fonts["title"].render("CHALLENGE 1 — RESTORE COMMUNICATION", True, HUD_TEXT)
    surface.blit(title, title.get_rect(centerx=panel.centerx, y=88))

    subtitle = fonts["small"].render(
        "Scan the sky, then click the satellite with the weak signal.",
        True,
        HUD_WARN,
    )
    surface.blit(subtitle, subtitle.get_rect(centerx=panel.centerx, y=128))

    # Radar dish circle
    radar_center = (640, 330)
    radar_radius = 170
    pygame.draw.circle(surface, (15, 35, 28), radar_center, radar_radius)
    pygame.draw.circle(surface, RADAR_DIM, radar_center, radar_radius, 3)
    for ring in (40, 80, 120, 160):
        pygame.draw.circle(surface, RADAR_DIM, radar_center, ring, 1)
    pygame.draw.line(
        surface, RADAR_DIM,
        (radar_center[0] - radar_radius, radar_center[1]),
        (radar_center[0] + radar_radius, radar_center[1]),
        1,
    )
    pygame.draw.line(
        surface, RADAR_DIM,
        (radar_center[0], radar_center[1] - radar_radius),
        (radar_center[0], radar_center[1] + radar_radius),
        1,
    )

    satellites = satellite_positions()
    sat_rects = {}

    # Always show satellite markers (different shapes)
    for sat in satellites:
        sat_rects[sat["id"]] = draw_satellite_marker(surface, sat)
        name = fonts["small"].render(sat["id"], True, HUD_TEXT)
        surface.blit(name, name.get_rect(center=(sat["pos"][0], sat["pos"][1] + 32)))

    # Sweeping beam while scanning (no sleep — moves each frame)
    if ch1["phase"] == "scanning":
        angle_rad = math.radians(ch1["scan_angle"] - 90)
        end_x = radar_center[0] + math.cos(angle_rad) * radar_radius
        end_y = radar_center[1] + math.sin(angle_rad) * radar_radius
        # Fading wedge behind the beam
        wedge = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for fade in range(8):
            a = math.radians(ch1["scan_angle"] - 90 - fade * 4)
            wx = radar_center[0] + math.cos(a) * radar_radius
            wy = radar_center[1] + math.sin(a) * radar_radius
            pygame.draw.line(
                wedge,
                (80, 220, 140, 18 + fade * 8),
                radar_center,
                (wx, wy),
                6,
            )
        surface.blit(wedge, (0, 0))
        pygame.draw.line(surface, RADAR_GREEN, radar_center, (end_x, end_y), 3)
        scan_label = fonts["body"].render("SCANNING...", True, RADAR_GREEN)
        surface.blit(scan_label, scan_label.get_rect(center=(640, 530)))

    scan_button = button_rect(640, 560, 240, 52)
    status_rects = {}  # not used for clicks; sat markers are

    if ch1["phase"] == "ready":
        draw_button(surface, scan_button, "SCAN RADAR", fonts, mouse_pos)
    else:
        scan_button = pygame.Rect(0, 0, 0, 0)  # disable after start

    # After the scan, list each satellite's status
    if ch1["phase"] == "results":
        status_lines = [
            ("SAT-01: CONNECTED", HUD_OK),
            ("SAT-02: WEAK SIGNAL", HUD_WARN),
            ("SAT-03: CONNECTED", HUD_OK),
        ]
        box = pygame.Rect(190, 180, 230, 160)
        pygame.draw.rect(surface, (18, 28, 24), box, border_radius=10)
        pygame.draw.rect(surface, RADAR_GREEN, box, 2, border_radius=10)
        for i, (text, color) in enumerate(status_lines):
            label = fonts["body"].render(text, True, color)
            surface.blit(label, (205, 200 + i * 36))

        tip = fonts["small"].render("Click SAT-02 (the diamond) to realign.", True, HUD_TEXT)
        surface.blit(tip, tip.get_rect(center=(640, 545)))

    if ch1["hint"]:
        hint = fonts["body"].render(ch1["hint"], True, HUD_ALERT)
        surface.blit(hint, hint.get_rect(center=(640, 500)))

    return {"scan_button": scan_button, "sat_rects": sat_rects}


def draw_alignment_screen(surface, fonts, mouse_pos, ch1):
    """Antenna alignment console: rotate until the signal is strong."""
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dim.fill((8, 4, 0, 140))
    surface.blit(dim, (0, 0))

    panel = pygame.Rect(160, 70, 960, 560)
    pygame.draw.rect(surface, PANEL_DARK, panel, border_radius=18)
    pygame.draw.rect(surface, (255, 170, 90), panel, 3, border_radius=18)

    title = fonts["title"].render("ANTENNA ALIGNMENT — SAT-02", True, HUD_TEXT)
    surface.blit(title, title.get_rect(centerx=panel.centerx, y=90))

    help_text = fonts["small"].render(
        "Use LEFT / RIGHT buttons or arrow keys. Target angle: +20 degrees.",
        True,
        HUD_WARN,
    )
    surface.blit(help_text, help_text.get_rect(centerx=panel.centerx, y=130))

    # Dish graphic that rotates with the current angle
    dish_center = (640, 320)
    pygame.draw.rect(surface, (90, 95, 105), (dish_center[0] - 18, dish_center[1], 36, 90))
    pygame.draw.ellipse(surface, (70, 75, 85), (dish_center[0] - 40, dish_center[1] + 80, 80, 24))

    angle_rad = math.radians(ch1["antenna_angle"] - 90)
    dish_len = 110
    tip_x = dish_center[0] + math.cos(angle_rad) * dish_len
    tip_y = dish_center[1] + math.sin(angle_rad) * dish_len
    # Dish bowl as a thick line + arc feel
    pygame.draw.line(surface, (200, 205, 215), dish_center, (tip_x, tip_y), 10)
    pygame.draw.circle(surface, (120, 180, 255), (int(tip_x), int(tip_y)), 14, 3)
    pygame.draw.circle(surface, (180, 220, 255), (int(tip_x), int(tip_y)), 5)

    # Target marker (ghost line at +20)
    target_rad = math.radians(ANTENNA_TARGET_ANGLE - 90)
    tx = dish_center[0] + math.cos(target_rad) * dish_len
    ty = dish_center[1] + math.sin(target_rad) * dish_len
    pygame.draw.line(surface, (80, 180, 100), dish_center, (tx, ty), 2)

    angle_label = fonts["body"].render(
        f"Current angle: {ch1['antenna_angle']:+d} degrees",
        True,
        HUD_TEXT,
    )
    surface.blit(angle_label, angle_label.get_rect(center=(640, 455)))

    # Signal strength bar
    strength = signal_strength(ch1["antenna_angle"])
    bar_x, bar_y, bar_w, bar_h = 390, 480, 500, 28
    pygame.draw.rect(surface, (40, 30, 25), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
    fill_w = int(bar_w * (strength / 100))
    bar_color = lerp_color(HUD_ALERT, HUD_OK, strength / 100)
    if fill_w > 0:
        pygame.draw.rect(surface, bar_color, (bar_x, bar_y, fill_w, bar_h), border_radius=6)
    pygame.draw.rect(surface, BUTTON_EDGE, (bar_x, bar_y, bar_w, bar_h), 2, border_radius=6)
    strength_label = fonts["small"].render(f"Signal strength: {int(strength)}%", True, HUD_TEXT)
    surface.blit(strength_label, strength_label.get_rect(center=(640, 530)))

    left_btn = button_rect(420, 575, 160, 50)
    right_btn = button_rect(860, 575, 160, 50)
    draw_button(surface, left_btn, "LEFT  <<", fonts, mouse_pos)
    draw_button(surface, right_btn, ">>  RIGHT", fonts, mouse_pos)

    if ch1["connection_restored"]:
        restored = fonts["title"].render("CONNECTION RESTORED", True, HUD_OK)
        surface.blit(restored, restored.get_rect(center=(640, 200)))
        online = fonts["body"].render("Signal status: ONLINE", True, HUD_OK)
        surface.blit(online, online.get_rect(center=(640, 235)))

    return {"left": left_btn, "right": right_btn}


def draw_complete_panel(surface, fonts, mouse_pos, score, time_left):
    """Mission completed panel after Challenge 1 success."""
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dim.fill((8, 4, 0, 160))
    surface.blit(dim, (0, 0))

    panel = pygame.Rect(290, 160, 700, 380)
    pygame.draw.rect(surface, PANEL_DARK, panel, border_radius=18)
    pygame.draw.rect(surface, HUD_OK, panel, 3, border_radius=18)

    heading = fonts["title"].render("MISSION COMPLETED!", True, HUD_OK)
    surface.blit(heading, heading.get_rect(centerx=panel.centerx, y=195))

    lines = [
        "Communication link restored with Earth.",
        f"Score: {score} points",
        f"Time remaining: {int(math.ceil(time_left))} seconds",
        "COMMUNICATION: ONLINE",
    ]
    for i, line in enumerate(lines):
        label = fonts["body"].render(line, True, HUD_TEXT)
        surface.blit(label, label.get_rect(centerx=panel.centerx, y=260 + i * 36))

    return_btn = button_rect(panel.centerx, 470, 300, 56)
    draw_button(surface, return_btn, "RETURN TO BASE", fonts, mouse_pos)
    return return_btn


def draw_timeout_panel(surface, fonts, mouse_pos):
    """Shown when the 90-second timer runs out."""
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dim.fill((8, 4, 0, 160))
    surface.blit(dim, (0, 0))

    panel = pygame.Rect(290, 180, 700, 320)
    pygame.draw.rect(surface, PANEL_DARK, panel, border_radius=18)
    pygame.draw.rect(surface, HUD_ALERT, panel, 3, border_radius=18)

    heading = fonts["title"].render("TIME IS UP!", True, HUD_ALERT)
    surface.blit(heading, heading.get_rect(centerx=panel.centerx, y=220))

    msg = fonts["body"].render("The dust storm scrambled the signal again.", True, HUD_TEXT)
    surface.blit(msg, msg.get_rect(centerx=panel.centerx, y=280))
    tip = fonts["small"].render("Try again to restore communication.", True, HUD_WARN)
    surface.blit(tip, tip.get_rect(centerx=panel.centerx, y=320))

    retry_btn = button_rect(panel.centerx, 400, 260, 56)
    draw_button(surface, retry_btn, "RETRY CHALLENGE", fonts, mouse_pos)
    return retry_btn


def rotate_antenna(ch1, direction):
    """Turn the antenna left (-1) or right (+1) by 5 degrees."""
    if ch1["connection_restored"]:
        return
    ch1["antenna_angle"] += direction * ANTENNA_STEP
    # Keep the dish in a sensible range so kids do not spin forever
    ch1["antenna_angle"] = max(-60, min(60, ch1["antenna_angle"]))


# =====================================================================
# Challenge 2 — Restore Shelter Power
# =====================================================================


def make_challenge2_state():
    """Fresh values every time Challenge 2 starts or restarts."""
    return {
        "time_left": float(CH2_TIME_LIMIT),
        "finish_time_left": 0.0,
        "selected": None,              # first component the player clicked
        "hint": "",
        "wire_solar_battery": False,   # Solar Panel → Battery
        "wire_battery_habitat": False, # Battery → Mars Habitat
        "wires_done": False,
        "wire_success_delay": 0.0,
        # Power allocations (must add up to at most 80)
        "life": 20,
        "food": 20,
        "comms": 40,
        "food_freshness": 100.0,
        "points_awarded": False,
        "completed": False,
        "complete_delay": 0.0,
    }


def ch2_total_power(ch2):
    """Add up all power currently given to the three systems."""
    return ch2["life"] + ch2["food"] + ch2["comms"]


def ch2_power_ok(ch2):
    """True when every system has at least its minimum power."""
    return ch2["life"] >= 30 and ch2["food"] >= 30 and ch2["comms"] >= 10


def ch2_change_power(ch2, system, delta):
    """Move power up or down by 10. Never go below 0 or above the budget."""
    new_value = ch2[system] + delta
    if new_value < 0:
        return
    # Pretend we made the change, then check the total still fits
    old = ch2[system]
    ch2[system] = new_value
    if ch2_total_power(ch2) > CH2_ENERGY_BUDGET:
        ch2[system] = old  # undo — not enough energy left


def draw_dim_panel(surface, rect):
    """Shared dark console panel used by Challenge 2 screens."""
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dim.fill((8, 4, 0, 140))
    surface.blit(dim, (0, 0))
    pygame.draw.rect(surface, PANEL_DARK, rect, border_radius=18)
    pygame.draw.rect(surface, (255, 170, 90), rect, 3, border_radius=18)


def draw_ch2_intro(surface, fonts, mouse_pos):
    """Challenge 2 introduction: power failure story + START."""
    panel = pygame.Rect(220, 130, 840, 440)
    draw_dim_panel(surface, panel)

    heading = fonts["title"].render("POWER FAILURE DETECTED!", True, HUD_ALERT)
    surface.blit(heading, heading.get_rect(centerx=panel.centerx, y=170))

    lines = [
        "The solar power system has failed.",
        "The habitat is losing electricity and food supplies are at risk.",
        "Reconnect the circuit, then share power wisely.",
    ]
    for i, line in enumerate(lines):
        label = fonts["body"].render(line, True, HUD_TEXT)
        surface.blit(label, label.get_rect(centerx=panel.centerx, y=250 + i * 40))

    start_btn = button_rect(panel.centerx, 480, 240, 56)
    draw_button(surface, start_btn, "START", fonts, mouse_pos)
    return start_btn


def ch2_component_boxes():
    """Clickable boxes for Solar Panel, Battery, and Mars Habitat."""
    return {
        "solar": pygame.Rect(220, 260, 200, 180),
        "battery": pygame.Rect(540, 260, 200, 180),
        "habitat": pygame.Rect(860, 260, 200, 180),
    }


def draw_ch2_solar_icon(surface, rect):
    """Simple solar panel icon inside a box."""
    pygame.draw.rect(surface, (40, 55, 90), rect.inflate(-30, -50), border_radius=6)
    inner = rect.inflate(-50, -70)
    pygame.draw.rect(surface, PANEL_BLUE, inner, border_radius=4)
    for i in range(1, 3):
        y = inner.y + i * inner.height // 3
        pygame.draw.line(surface, PANEL_CELL, (inner.x, y), (inner.right, y), 2)
    for i in range(1, 4):
        x = inner.x + i * inner.width // 4
        pygame.draw.line(surface, PANEL_CELL, (x, inner.y), (x, inner.bottom), 2)


def draw_ch2_battery_icon(surface, rect):
    """Simple battery icon inside a box."""
    body = pygame.Rect(0, 0, 90, 120)
    body.center = (rect.centerx, rect.centery + 5)
    pygame.draw.rect(surface, (70, 160, 90), body, border_radius=8)
    pygame.draw.rect(surface, (200, 220, 200), body, 3, border_radius=8)
    tip = pygame.Rect(0, 0, 36, 14)
    tip.midbottom = (body.centerx, body.top + 2)
    pygame.draw.rect(surface, (220, 220, 230), tip, border_radius=3)
    # Charge bars
    for i in range(3):
        bar = pygame.Rect(body.x + 14, body.bottom - 28 - i * 28, body.width - 28, 18)
        pygame.draw.rect(surface, (180, 255, 160), bar, border_radius=3)


def draw_ch2_habitat_icon(surface, rect):
    """Simple habitat dome icon inside a box."""
    base = pygame.Rect(0, 0, 110, 50)
    base.midbottom = (rect.centerx, rect.centery + 55)
    pygame.draw.rect(surface, HABITAT_BODY, base, border_radius=4)
    pygame.draw.ellipse(surface, (230, 235, 240), (base.x, base.y - 55, base.width, 70))
    pygame.draw.rect(surface, HABITAT_WINDOW, (base.centerx - 12, base.y + 10, 24, 28), border_radius=3)


def draw_ch2_wire_screen(surface, fonts, mouse_pos, ch2):
    """Click two parts to connect them with a green power wire."""
    panel = pygame.Rect(140, 60, 1000, 600)
    draw_dim_panel(surface, panel)

    title = fonts["title"].render("CHALLENGE 2 — RECONNECT POWER", True, HUD_TEXT)
    surface.blit(title, title.get_rect(centerx=panel.centerx, y=78))

    tip = fonts["small"].render(
        "Click Solar Panel then Battery. Next click Battery then Mars Habitat.",
        True,
        HUD_WARN,
    )
    surface.blit(tip, tip.get_rect(centerx=panel.centerx, y=120))

    boxes = ch2_component_boxes()
    labels = {
        "solar": "Solar Panel",
        "battery": "Battery",
        "habitat": "Mars Habitat",
    }

    # Draw each component card
    for key, rect in boxes.items():
        selected = ch2["selected"] == key
        border = HUD_OK if selected else (255, 170, 90)
        pygame.draw.rect(surface, (35, 22, 16), rect, border_radius=12)
        pygame.draw.rect(surface, border, rect, 3 if selected else 2, border_radius=12)
        if key == "solar":
            draw_ch2_solar_icon(surface, rect)
        elif key == "battery":
            draw_ch2_battery_icon(surface, rect)
        else:
            draw_ch2_habitat_icon(surface, rect)
        name = fonts["body"].render(labels[key], True, HUD_TEXT)
        surface.blit(name, name.get_rect(center=(rect.centerx, rect.bottom - 22)))

    # Green wires for correct links
    if ch2["wire_solar_battery"]:
        pygame.draw.line(
            surface, HUD_OK,
            boxes["solar"].midright, boxes["battery"].midleft, 6,
        )
    if ch2["wire_battery_habitat"]:
        pygame.draw.line(
            surface, HUD_OK,
            boxes["battery"].midright, boxes["habitat"].midleft, 6,
        )

    if ch2["hint"]:
        hint = fonts["body"].render(ch2["hint"], True, HUD_ALERT)
        surface.blit(hint, hint.get_rect(center=(640, 500)))

    continue_btn = pygame.Rect(0, 0, 0, 0)
    if ch2["wires_done"]:
        ok = fonts["title"].render("POWER CONNECTION RESTORED", True, HUD_OK)
        surface.blit(ok, ok.get_rect(center=(640, 480)))
        continue_btn = button_rect(640, 560, 360, 52)
        draw_button(surface, continue_btn, "CONTINUE TO POWER SYSTEMS", fonts, mouse_pos, "button_small")

    return {"boxes": boxes, "continue": continue_btn}


def try_ch2_wire_click(ch2, part):
    """Handle one click on a power component during the wire puzzle."""
    if ch2["wires_done"]:
        return

    if ch2["selected"] is None:
        ch2["selected"] = part
        ch2["hint"] = f"Selected {part.upper()}. Now click what it should connect to."
        return

    first = ch2["selected"]
    second = part
    ch2["selected"] = None

    if first == second:
        ch2["hint"] = "Choose two different parts to connect."
        return

    pair = (first, second)
    if pair == ("solar", "battery") and not ch2["wire_solar_battery"]:
        ch2["wire_solar_battery"] = True
        ch2["hint"] = "Great! Solar Panel is charging the Battery."
    elif pair == ("battery", "habitat") and not ch2["wire_battery_habitat"]:
        ch2["wire_battery_habitat"] = True
        ch2["hint"] = "Great! Battery is powering the Mars Habitat."
    else:
        # Friendly tip for Grade 5 players
        ch2["hint"] = "Wrong link. Try Solar Panel → Battery, then Battery → Habitat."

    if ch2["wire_solar_battery"] and ch2["wire_battery_habitat"]:
        ch2["wires_done"] = True
        ch2["hint"] = ""
        ch2["wire_success_delay"] = 0.0


def draw_ch2_power_screen(surface, fonts, mouse_pos, ch2):
    """Share the 80 energy units between Life Support, Food, and Comms."""
    panel = pygame.Rect(120, 50, 1040, 620)
    draw_dim_panel(surface, panel)

    title = fonts["title"].render("POWER DISTRIBUTION — ENERGY BUDGET 80", True, HUD_TEXT)
    surface.blit(title, title.get_rect(centerx=panel.centerx, y=68))

    used = ch2_total_power(ch2)
    remaining = CH2_ENERGY_BUDGET - used
    totals = fonts["body"].render(
        f"Power used: {used} / 80     Remaining: {remaining}",
        True,
        HUD_TEXT,
    )
    surface.blit(totals, totals.get_rect(centerx=panel.centerx, y=110))

    # System rows: name, value, min, +/- buttons
    systems = [
        ("life", "Life Support", 30, 170),
        ("food", "Food Storage", 30, 290),
        ("comms", "Communications", 10, 410),
    ]
    buttons = {}

    for key, name, minimum, y in systems:
        value = ch2[key]
        ok = value >= minimum
        status_color = HUD_OK if ok else HUD_ALERT
        status_text = "OK" if ok else "LOW POWER"

        row = pygame.Rect(180, y, 920, 95)
        pygame.draw.rect(surface, (35, 22, 16), row, border_radius=12)
        pygame.draw.rect(surface, status_color, row, 2, border_radius=12)

        label = fonts["body"].render(f"{name}: {value} units  (need {minimum})", True, HUD_TEXT)
        surface.blit(label, (210, y + 18))
        status = fonts["small"].render(status_text, True, status_color)
        surface.blit(status, (210, y + 52))

        minus = pygame.Rect(880, y + 22, 70, 50)
        plus = pygame.Rect(980, y + 22, 70, 50)
        draw_button(surface, minus, "−", fonts, mouse_pos)
        draw_button(surface, plus, "+", fonts, mouse_pos)
        buttons[key] = {"minus": minus, "plus": plus}

    # Food freshness meter
    freshness = max(0, min(100, ch2["food_freshness"]))
    food_ok = ch2["food"] >= 30
    meter_label = fonts["body"].render(
        f"Food freshness: {int(freshness)}%",
        True,
        HUD_TEXT,
    )
    surface.blit(meter_label, (210, 520))
    bar = pygame.Rect(210, 555, 500, 24)
    pygame.draw.rect(surface, (40, 30, 25), bar, border_radius=6)
    fill = int(bar.width * (freshness / 100))
    pygame.draw.rect(
        surface,
        lerp_color(HUD_ALERT, HUD_OK, freshness / 100),
        (bar.x, bar.y, fill, bar.height),
        border_radius=6,
    )
    pygame.draw.rect(surface, BUTTON_EDGE, bar, 2, border_radius=6)

    if food_ok:
        food_msg = fonts["small"].render("FOOD PRESERVED", True, HUD_OK)
    else:
        food_msg = fonts["small"].render("FOOD SPOILING", True, HUD_ALERT)
    surface.blit(food_msg, (730, 555))

    # Life support status
    if ch2["life"] >= 30:
        life_msg = fonts["small"].render("Life support: STABLE", True, HUD_OK)
    else:
        life_msg = fonts["small"].render("Life support: CRITICAL", True, HUD_ALERT)
    surface.blit(life_msg, (210, 590))

    if ch2["completed"]:
        win = fonts["title"].render("POWER RESTORED", True, HUD_OK)
        surface.blit(win, win.get_rect(center=(640, 145)))

    return buttons


def draw_ch2_complete_panel(surface, fonts, mouse_pos, score, time_left, freshness):
    """Shown after Challenge 2 is solved."""
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dim.fill((8, 4, 0, 160))
    surface.blit(dim, (0, 0))

    panel = pygame.Rect(260, 120, 760, 460)
    pygame.draw.rect(surface, PANEL_DARK, panel, border_radius=18)
    pygame.draw.rect(surface, HUD_OK, panel, 3, border_radius=18)

    heading = fonts["title"].render("POWER RESTORED", True, HUD_OK)
    surface.blit(heading, heading.get_rect(centerx=panel.centerx, y=145))

    lines = [
        "FOOD SUPPLY PROTECTED",
        "LIFE SUPPORT STABLE",
        f"Score: {score} points",
        f"Time remaining: {int(math.ceil(time_left))} seconds",
        f"Food freshness: {int(freshness)}%",
        "POWER: ONLINE    FOOD: SAFE",
    ]
    for i, line in enumerate(lines):
        color = HUD_OK if i < 2 else HUD_TEXT
        label = fonts["body"].render(line, True, color)
        surface.blit(label, label.get_rect(centerx=panel.centerx, y=210 + i * 34))

    return_btn = button_rect(panel.centerx, 500, 300, 56)
    draw_button(surface, return_btn, "RETURN TO BASE", fonts, mouse_pos)
    return return_btn


def draw_ch2_timeout_panel(surface, fonts, mouse_pos):
    """Mission failed when the Challenge 2 timer hits zero."""
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dim.fill((8, 4, 0, 160))
    surface.blit(dim, (0, 0))

    panel = pygame.Rect(260, 150, 760, 400)
    pygame.draw.rect(surface, PANEL_DARK, panel, border_radius=18)
    pygame.draw.rect(surface, HUD_ALERT, panel, 3, border_radius=18)

    heading = fonts["title"].render("MISSION FAILED", True, HUD_ALERT)
    surface.blit(heading, heading.get_rect(centerx=panel.centerx, y=190))

    msg = fonts["body"].render("Time ran out before power was restored.", True, HUD_TEXT)
    surface.blit(msg, msg.get_rect(centerx=panel.centerx, y=260))
    tip = fonts["small"].render("Retry the challenge or return to base.", True, HUD_WARN)
    surface.blit(tip, tip.get_rect(centerx=panel.centerx, y=310))

    retry_btn = button_rect(panel.centerx - 160, 420, 240, 56)
    base_btn = button_rect(panel.centerx + 160, 420, 240, 56)
    draw_button(surface, retry_btn, "RETRY", fonts, mouse_pos)
    draw_button(surface, base_btn, "RETURN TO BASE", fonts, mouse_pos)
    return {"retry": retry_btn, "base": base_btn}


# =====================================================================
# Challenge 3 — Rescue the Rover
# =====================================================================

# Fixed signal map for the 3x3 satellite scan (Strong is at B2)
CH3_SIGNALS = {
    "A1": "Weak", "A2": "Weak", "A3": "Medium",
    "B1": "Weak", "B2": "Strong", "B3": "Weak",
    "C1": "Medium", "C2": "Weak", "C3": "Weak",
}


def make_challenge3_state():
    """Fresh values every time Challenge 3 starts or restarts."""
    # Rocks the rescue rover can bump into (x, y, w, h)
    rocks = [
        pygame.Rect(320, 420, 70, 45),
        pygame.Rect(510, 500, 90, 50),
        pygame.Rect(700, 390, 75, 48),
        pygame.Rect(880, 470, 85, 55),
        pygame.Rect(420, 300, 60, 40),
        pygame.Rect(980, 320, 70, 42),
    ]
    # Extra driving dust (separate from the base-scene dust)
    rng = random.Random(11)
    drive_dust = []
    for _ in range(70):
        drive_dust.append(
            {
                "x": rng.uniform(0, WIDTH),
                "y": rng.uniform(180, HEIGHT - 20),
                "speed": rng.uniform(0.8, 2.5),
                "size": rng.randint(1, 4),
                "alpha": rng.randint(60, 160),
            }
        )

    return {
        "time_left": float(CH3_TIME_LIMIT),
        "finish_time_left": 0.0,
        "phase": "ready",          # ready -> scanning -> results -> found
        "scan_angle": 0.0,
        "scan_progress": 0.0,
        "hint": "",
        "found": False,
        # Rescue rover position (top-left of body)
        "rover_x": 80.0,
        "rover_y": 520.0,
        "wheel_spin": 0.0,
        "hit_timer": 0.0,          # >0 means briefly slowed after a rock
        "hit_message_timer": 0.0,
        "rescued": False,
        "points_awarded": False,
        "complete_delay": 0.0,
        "finish_storm": 0.0,
        "rocks": rocks,
        "drive_dust": drive_dust,
        # Stranded rover destination
        "target_x": 1100,
        "target_y": 480,
    }


def ch3_storm_intensity(ch3):
    """0.0 (calm) to 1.0 (worst). Grows as time runs out."""
    elapsed = CH3_TIME_LIMIT - ch3["time_left"]
    return max(0.0, min(1.0, elapsed / CH3_TIME_LIMIT))


def ch3_rover_rect(ch3):
    """Hit box used for collisions and rescue range."""
    return pygame.Rect(int(ch3["rover_x"]), int(ch3["rover_y"]), 110, 55)


def draw_ch3_intro(surface, fonts, mouse_pos):
    """Challenge 3 introduction: lost rover story + START RESCUE."""
    panel = pygame.Rect(200, 120, 880, 460)
    draw_dim_panel(surface, panel)

    heading = fonts["title"].render("ROVER SIGNAL LOST!", True, HUD_ALERT)
    surface.blit(heading, heading.get_rect(centerx=panel.centerx, y=155))

    lines = [
        "A training rover is stranded somewhere on Mars.",
        "A powerful dust storm is approaching.",
        "Use satellite scanning to find its location",
        "and drive the rescue rover to save it!",
    ]
    for i, line in enumerate(lines):
        label = fonts["body"].render(line, True, HUD_TEXT)
        surface.blit(label, label.get_rect(centerx=panel.centerx, y=230 + i * 36))

    start_btn = button_rect(panel.centerx, 490, 280, 56)
    draw_button(surface, start_btn, "START RESCUE", fonts, mouse_pos)
    return start_btn


def ch3_grid_cells():
    """Build the 3x3 scan grid rectangles and labels."""
    labels = ["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3"]
    cells = {}
    start_x, start_y = 380, 180
    size, gap = 110, 16
    for i, name in enumerate(labels):
        row = i // 3
        col = i % 3
        rect = pygame.Rect(
            start_x + col * (size + gap),
            start_y + row * (size + gap),
            size,
            size,
        )
        cells[name] = rect
    return cells


def signal_color(level):
    """Pick a colour for Weak / Medium / Strong signals."""
    if level == "Strong":
        return HUD_OK
    if level == "Medium":
        return HUD_WARN
    return (180, 120, 100)


def draw_ch3_scan_screen(surface, fonts, mouse_pos, ch3):
    """3x3 satellite scan grid to find the stranded rover."""
    panel = pygame.Rect(140, 50, 1000, 620)
    draw_dim_panel(surface, panel)

    title = fonts["title"].render("SATELLITE SCAN — FIND THE ROVER", True, HUD_TEXT)
    surface.blit(title, title.get_rect(centerx=panel.centerx, y=68))

    tip = fonts["small"].render(
        "Scan the area, then click the cell with the STRONG signal.",
        True,
        HUD_WARN,
    )
    surface.blit(tip, tip.get_rect(centerx=panel.centerx, y=110))

    cells = ch3_grid_cells()

    # Soft radar ring behind the grid while scanning
    if ch3["phase"] == "scanning":
        cx, cy = 640, 360
        rad = 200
        pygame.draw.circle(surface, (20, 40, 30), (cx, cy), rad, 2)
        ang = math.radians(ch3["scan_angle"] - 90)
        pygame.draw.line(
            surface,
            RADAR_GREEN,
            (cx, cy),
            (cx + math.cos(ang) * rad, cy + math.sin(ang) * rad),
            3,
        )

    for name, rect in cells.items():
        pygame.draw.rect(surface, (40, 25, 18), rect, border_radius=10)
        border = (255, 170, 90)
        if ch3["phase"] == "results" or ch3["found"]:
            level = CH3_SIGNALS[name]
            border = signal_color(level)
            level_label = fonts["small"].render(level, True, border)
            surface.blit(level_label, level_label.get_rect(center=(rect.centerx, rect.centery + 18)))
        pygame.draw.rect(surface, border, rect, 3, border_radius=10)
        name_label = fonts["body"].render(name, True, HUD_TEXT)
        surface.blit(name_label, name_label.get_rect(center=(rect.centerx, rect.centery - 10)))

    scan_btn = button_rect(640, 560, 240, 52)
    continue_btn = pygame.Rect(0, 0, 0, 0)

    if ch3["phase"] == "ready":
        draw_button(surface, scan_btn, "SCAN AREA", fonts, mouse_pos)
    else:
        scan_btn = pygame.Rect(0, 0, 0, 0)

    if ch3["phase"] == "scanning":
        scanning = fonts["body"].render("SCANNING...", True, RADAR_GREEN)
        surface.blit(scanning, scanning.get_rect(center=(640, 560)))

    if ch3["found"]:
        found = fonts["title"].render("ROVER LOCATION FOUND!", True, HUD_OK)
        surface.blit(found, found.get_rect(center=(640, 520)))
        coords = fonts["body"].render("Coordinates: B2", True, HUD_TEXT)
        surface.blit(coords, coords.get_rect(center=(640, 555)))
        continue_btn = button_rect(640, 610, 300, 50)
        draw_button(surface, continue_btn, "CONTINUE TO RESCUE", fonts, mouse_pos, "button_small")

    if ch3["hint"] and not ch3["found"]:
        hint = fonts["body"].render(ch3["hint"], True, HUD_ALERT)
        surface.blit(hint, hint.get_rect(center=(640, 610)))

    return {"cells": cells, "scan_button": scan_btn, "continue": continue_btn}


def draw_mini_rover(surface, x, y, color=ROVER_BODY, wheel_spin=0.0, stranded=False):
    """Draw a small rover (player or stranded) with simple spinning wheels."""
    body = pygame.Rect(int(x), int(y), 100, 40)
    pygame.draw.ellipse(surface, GROUND_SHADOW, (body.x - 4, body.bottom - 4, 110, 18))
    pygame.draw.rect(surface, color, body, border_radius=6)
    pygame.draw.rect(surface, ROVER_DARK, body, 2, border_radius=6)
    # Cabin
    pygame.draw.rect(surface, (220, 230, 240), (body.x + 30, body.y - 16, 36, 18), border_radius=3)
    if stranded:
        # Distress beacon
        pygame.draw.circle(surface, HUD_ALERT, (body.centerx, body.y - 28), 6)

    for i, wx in enumerate((body.x + 18, body.x + 50, body.x + 82)):
        cy = body.bottom + 2
        pygame.draw.circle(surface, (40, 40, 45), (wx, cy), 11)
        # Tiny spoke so the wheel looks like it turns
        ang = wheel_spin + i * 0.8
        sx = wx + int(math.cos(ang) * 6)
        sy = cy + int(math.sin(ang) * 6)
        pygame.draw.line(surface, (200, 200, 205), (wx, cy), (sx, sy), 2)


def draw_ch3_drive_world(surface, ch3, fonts):
    """2.5D Mars driving scene for the rescue mission."""
    # Sky + desert ground (same Mars colours as the base)
    for y in range(0, 360):
        t = y / 360
        color = lerp_color(SKY_TOP, SKY_LOW, t)
        pygame.draw.line(surface, color, (0, y), (WIDTH, y))
    pygame.draw.rect(surface, GROUND_LIGHT, (0, 360, WIDTH, HEIGHT - 360))

    # Layered mountains
    mountain_ridge(
        300,
        [(0, 280), (160, 230), (320, 270), (500, 210), (700, 260), (900, 220), (1100, 270), (1280, 240)],
        MOUNTAIN_FAR,
        surface,
    )
    mountain_ridge(
        340,
        [(0, 320), (200, 270), (400, 330), (620, 260), (850, 310), (1050, 270), (1280, 320)],
        MOUNTAIN_MID,
        surface,
    )

    # Rocky ground shading
    for i in range(6):
        shade = lerp_color(GROUND_LIGHT, GROUND_DARK, i / 8)
        pygame.draw.ellipse(surface, shade, (-30 + i * 40, 400 + i * 40, WIDTH + 60, 55))

    # Craters
    for cx, cy, r in ((250, 450, 28), (600, 560, 34), (950, 430, 26)):
        pygame.draw.ellipse(surface, GROUND_SHADOW, (cx - r, cy - r // 2, r * 2, r))

    # Destination marker near the stranded rover
    marker_x = ch3["target_x"] + 50
    marker_y = ch3["target_y"] - 30
    pygame.draw.polygon(
        surface,
        HUD_OK,
        [(marker_x, marker_y - 40), (marker_x + 14, marker_y), (marker_x - 14, marker_y)],
    )
    pygame.draw.circle(surface, HUD_OK, (marker_x, marker_y + 8), 6)
    flag = fonts["small"].render("RESCUE ZONE", True, HUD_OK)
    surface.blit(flag, (marker_x - 40, marker_y - 60))

    # Obstacle rocks
    for rock in ch3["rocks"]:
        pygame.draw.ellipse(surface, GROUND_SHADOW, (rock.x + 4, rock.bottom - 8, rock.w, 16))
        pygame.draw.ellipse(surface, ROCK_DARK, rock)
        pygame.draw.ellipse(
            surface,
            ROCK_LIGHT,
            (rock.x + 8, rock.y + 6, rock.w // 2, rock.h // 2),
        )

    # Stranded rover
    draw_mini_rover(surface, ch3["target_x"], ch3["target_y"], (180, 80, 60), 0.0, stranded=True)
    # Player rescue rover
    draw_mini_rover(surface, ch3["rover_x"], ch3["rover_y"], ROVER_BODY, ch3["wheel_spin"])

    # Storm dust particles (faster when the storm is stronger)
    intensity = ch3_storm_intensity(ch3)
    dust_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for p in ch3["drive_dust"]:
        alpha = min(220, int(p["alpha"] * (0.5 + intensity)))
        pygame.draw.circle(
            dust_layer,
            (255, 190, 130, alpha),
            (int(p["x"]), int(p["y"])),
            p["size"] + int(intensity * 2),
        )
    surface.blit(dust_layer, (0, 0))

    # Atmospheric overlay grows with the storm
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((180, 90, 40, int(30 + intensity * 110)))
    surface.blit(overlay, (0, 0))

    # Storm HUD bits
    storm_pct = int(intensity * 100)
    storm_label = fonts["small"].render(f"Storm intensity: {storm_pct}%", True, HUD_TEXT)
    surface.blit(storm_label, (WIDTH - 230, 70))
    bar = pygame.Rect(WIDTH - 230, 95, 180, 14)
    pygame.draw.rect(surface, (40, 25, 15), bar, border_radius=4)
    pygame.draw.rect(
        surface,
        lerp_color(HUD_WARN, HUD_ALERT, intensity),
        (bar.x, bar.y, int(bar.w * intensity), bar.h),
        border_radius=4,
    )

    if ch3["time_left"] <= 30:
        warn = fonts["title"].render("STORM CRITICAL — HURRY!", True, HUD_ALERT)
    else:
        warn = fonts["body"].render("STORM APPROACHING", True, HUD_WARN)
    surface.blit(warn, warn.get_rect(center=(WIDTH // 2, 40)))

    help_line = fonts["small"].render(
        "WASD / Arrows move   |   Reach the stranded rover and press E",
        True,
        HUD_TEXT,
    )
    surface.blit(help_line, help_line.get_rect(center=(WIDTH // 2, HEIGHT - 24)))

    if ch3["hit_message_timer"] > 0:
        hit = fonts["body"].render("ROCK AHEAD!", True, HUD_ALERT)
        surface.blit(hit, hit.get_rect(center=(WIDTH // 2, 100)))

    if ch3["rescued"]:
        rescued = fonts["title"].render("ROVER RESCUED!", True, HUD_OK)
        surface.blit(rescued, rescued.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 40)))


def update_ch3_drive(ch3, dt, keys):
    """Move the rescue rover, handle rocks, and blow the dust storm."""
    if ch3["rescued"]:
        return

    if ch3["hit_timer"] > 0:
        ch3["hit_timer"] -= dt
    if ch3["hit_message_timer"] > 0:
        ch3["hit_message_timer"] -= dt

    speed = CH3_ROVER_SPEED
    if ch3["hit_timer"] > 0:
        speed *= 0.35  # brief slow-down after a bump

    dx = dy = 0.0
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        dx -= 1
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        dx += 1
    if keys[pygame.K_w] or keys[pygame.K_UP]:
        dy -= 1
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
        dy += 1

    # Diagonal movement should not be faster
    if dx != 0 and dy != 0:
        dx *= 0.707
        dy *= 0.707

    new_x = ch3["rover_x"] + dx * speed * dt
    new_y = ch3["rover_y"] + dy * speed * dt

    # Keep the rover on the desert play area
    new_x = max(20, min(WIDTH - 130, new_x))
    new_y = max(280, min(HEIGHT - 80, new_y))

    test = pygame.Rect(int(new_x), int(new_y), 110, 55)
    blocked = False
    for rock in ch3["rocks"]:
        if test.colliderect(rock):
            blocked = True
            ch3["hit_timer"] = CH3_HIT_SLOW
            ch3["hit_message_timer"] = 0.8
            break

    if not blocked:
        moved = abs(new_x - ch3["rover_x"]) + abs(new_y - ch3["rover_y"])
        ch3["rover_x"] = new_x
        ch3["rover_y"] = new_y
        ch3["wheel_spin"] += moved * 0.08

    # Blow driving dust faster as the storm grows
    intensity = ch3_storm_intensity(ch3)
    for p in ch3["drive_dust"]:
        p["x"] += p["speed"] * (1.0 + intensity * 2.5)
        p["y"] += math.sin(p["x"] * 0.02) * 0.4
        if p["x"] > WIDTH + 5:
            p["x"] = -5
            p["y"] = random.uniform(180, HEIGHT - 20)


def try_ch3_rescue(ch3):
    """Press E near the stranded rover to save it."""
    if ch3["rescued"]:
        return False
    player = ch3_rover_rect(ch3)
    target = pygame.Rect(ch3["target_x"] - 20, ch3["target_y"] - 20, 140, 90)
    if player.colliderect(target):
        ch3["rescued"] = True
        ch3["finish_time_left"] = ch3["time_left"]
        ch3["finish_storm"] = ch3_storm_intensity(ch3)
        ch3["complete_delay"] = 1.3
        return True
    return False


def draw_ch3_complete_panel(surface, fonts, mouse_pos, score, time_left, storm):
    """Shown after the rover is rescued."""
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dim.fill((8, 4, 0, 160))
    surface.blit(dim, (0, 0))

    panel = pygame.Rect(260, 130, 760, 440)
    pygame.draw.rect(surface, PANEL_DARK, panel, border_radius=18)
    pygame.draw.rect(surface, HUD_OK, panel, 3, border_radius=18)

    heading = fonts["title"].render("ROVER RESCUED!", True, HUD_OK)
    surface.blit(heading, heading.get_rect(centerx=panel.centerx, y=160))

    # Simple celebration pulses (drawn each frame — looks like animation)
    pulse = 8 + int(6 * abs(math.sin(pygame.time.get_ticks() * 0.006)))
    pygame.draw.circle(surface, HUD_OK, (panel.centerx, 230), pulse, 2)

    lines = [
        f"Score: {score} points",
        f"Time remaining: {int(math.ceil(time_left))} seconds",
        f"Final storm intensity: {int(storm * 100)}%",
        "ROVER STATUS: RESCUED",
    ]
    for i, line in enumerate(lines):
        label = fonts["body"].render(line, True, HUD_TEXT)
        surface.blit(label, label.get_rect(centerx=panel.centerx, y=270 + i * 36))

    return_btn = button_rect(panel.centerx, 490, 300, 56)
    draw_button(surface, return_btn, "RETURN TO BASE", fonts, mouse_pos)
    return return_btn


def draw_ch3_timeout_panel(surface, fonts, mouse_pos):
    """Mission failed when the dust storm reaches the rescue site."""
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dim.fill((8, 4, 0, 160))
    surface.blit(dim, (0, 0))

    panel = pygame.Rect(240, 150, 800, 400)
    pygame.draw.rect(surface, PANEL_DARK, panel, border_radius=18)
    pygame.draw.rect(surface, HUD_ALERT, panel, 3, border_radius=18)

    heading = fonts["title"].render("MISSION FAILED", True, HUD_ALERT)
    surface.blit(heading, heading.get_rect(centerx=panel.centerx, y=190))

    msg = fonts["body"].render(
        "The dust storm reached the rescue location!",
        True,
        HUD_TEXT,
    )
    surface.blit(msg, msg.get_rect(centerx=panel.centerx, y=270))

    retry_btn = button_rect(panel.centerx - 160, 400, 240, 56)
    base_btn = button_rect(panel.centerx + 160, 400, 240, 56)
    draw_button(surface, retry_btn, "RETRY", fonts, mouse_pos)
    draw_button(surface, base_btn, "RETURN TO BASE", fonts, mouse_pos)
    return {"retry": retry_btn, "base": base_btn}


# =====================================================================
# Milestone 1 open-world systems live under systems/
# (player, camera, colony, interactions, inventory, journal, …)
# Challenge screens CH1–CH3 below / above remain in this file.
# =====================================================================


def main():
    """Start the game window and keep drawing until we quit."""
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Mars Mission: Restore, Recharge & Rescue!")
    clock = pygame.time.Clock()

    fonts = {
        "title": pygame.font.SysFont("segoeui", 28, bold=True),
        "body": pygame.font.SysFont("segoeui", 22),
        "small": pygame.font.SysFont("segoeui", 18),
        "button": pygame.font.SysFont("segoeui", 22, bold=True),
        "button_small": pygame.font.SysFont("segoeui", 18, bold=True),
    }

    # Load optional PNGs + build cached sky/ground plates once
    preload_environment_assets()

    rocks, craters = make_ground_details()
    dust_particles = make_dust_particles()
    env_time = 0.0  # drives subtle parallax motion

    # Open-world colony (3200×2200) — challenges still opened via stations
    colony = colony_sys.make_colony(SCREEN_CH1_RADAR, SCREEN_CH2_INTRO, SCREEN_CH3_INTRO)
    astronaut = player_sys.make_astronaut(colony["spawn"])
    camera = cam_sys.make_camera(astronaut, WIDTH, HEIGHT)
    cam_sys.clamp_camera(camera, WORLD_W, WORLD_H)
    world_dust = particle_sys.make_dust(70, WORLD_W, WORLD_H)
    inventory = inv_sys.make_inventory()
    journal = journal_sys.make_journal()
    map_open = False
    paused = False
    active_target = None
    saved_base_pos = None  # restored after challenges

    current_screen = SCREEN_TITLE
    start_button = button_rect(WIDTH // 2, 640, 300, 60)
    continue_button = pygame.Rect(0, 0, 260, 56)

    # Mission progress that lasts across screens
    communication_status = "OFFLINE"
    power_status = "LOW"
    food_status = "AT RISK"
    rover_status = "MISSING"
    score = 0
    ch1 = make_challenge1_state()
    ch2 = make_challenge2_state()
    ch3 = make_challenge3_state()

    # Buttons that change each frame on challenge screens
    radar_ui = {"scan_button": pygame.Rect(0, 0, 0, 0), "sat_rects": {}}
    align_ui = {"left": pygame.Rect(0, 0, 0, 0), "right": pygame.Rect(0, 0, 0, 0)}
    return_button = pygame.Rect(0, 0, 0, 0)
    retry_button = pygame.Rect(0, 0, 0, 0)
    ch2_intro_start = pygame.Rect(0, 0, 0, 0)
    ch2_wire_ui = {"boxes": {}, "continue": pygame.Rect(0, 0, 0, 0)}
    ch2_power_ui = {}
    ch2_timeout_ui = {"retry": pygame.Rect(0, 0, 0, 0), "base": pygame.Rect(0, 0, 0, 0)}
    ch3_intro_start = pygame.Rect(0, 0, 0, 0)
    ch3_scan_ui = {
        "cells": {},
        "scan_button": pygame.Rect(0, 0, 0, 0),
        "continue": pygame.Rect(0, 0, 0, 0),
    }
    ch3_timeout_ui = {"retry": pygame.Rect(0, 0, 0, 0), "base": pygame.Rect(0, 0, 0, 0)}

    def return_to_colony():
        """Leave a challenge and restore exploration at the saved world position."""
        nonlocal current_screen
        if saved_base_pos is not None:
            astronaut["x"], astronaut["y"] = saved_base_pos
        cam_sys.update_camera(camera, astronaut, 1.0, WORLD_W, WORLD_H)
        current_screen = SCREEN_BASE

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        dt = clock.get_time() / 1000.0  # seconds since last frame
        keys = pygame.key.get_pressed()

        # ---- events ----
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if current_screen == SCREEN_BASE:
                    if inventory["open"]:
                        inventory["open"] = False
                    elif journal["open"]:
                        journal["open"] = False
                    elif map_open:
                        map_open = False
                    else:
                        paused = not paused
                else:
                    running = False

            elif event.type == pygame.KEYDOWN and current_screen == SCREEN_BASE and paused:
                if event.key == pygame.K_q:
                    running = False

            elif (
                event.type == pygame.KEYDOWN
                and current_screen == SCREEN_BASE
                and not paused
            ):
                if event.key == pygame.K_i:
                    inventory["open"] = not inventory["open"]
                    journal["open"] = False
                    map_open = False
                elif event.key == pygame.K_j:
                    journal["open"] = not journal["open"]
                    inventory["open"] = False
                    map_open = False
                elif event.key == pygame.K_m:
                    map_open = not map_open
                    inventory["open"] = False
                    journal["open"] = False
                elif event.key == pygame.K_e and not (
                    inventory["open"] or journal["open"] or map_open
                ):
                    # Edge-triggered interact (once per key press)
                    if active_target is not None:
                        if active_target.get("type") == "station":
                            saved_base_pos = (astronaut["x"], astronaut["y"])
                            sid = active_target["id"]
                            if sid == "comm":
                                ch1 = make_challenge1_state()
                            elif sid == "power":
                                ch2 = make_challenge2_state()
                            elif sid == "rover":
                                ch3 = make_challenge3_state()
                            current_screen = active_target["screen"]
                            inventory["open"] = False
                            journal["open"] = False
                            map_open = False
                        elif active_target.get("type") == "collectible":
                            if inv_sys.add_item(inventory, active_target):
                                active_target["collected"] = True
                                active_target["status"] = "collected"

            elif event.type == pygame.KEYDOWN and current_screen == SCREEN_CH1_ALIGN:
                if event.key == pygame.K_LEFT:
                    rotate_antenna(ch1, -1)
                elif event.key == pygame.K_RIGHT:
                    rotate_antenna(ch1, 1)

            elif event.type == pygame.KEYDOWN and current_screen == SCREEN_CH3_DRIVE:
                # Press E near the stranded rover to rescue it
                if event.key == pygame.K_e:
                    if try_ch3_rescue(ch3):
                        if not ch3["points_awarded"]:
                            score += CH3_POINTS
                            ch3["points_awarded"] = True
                        rover_status = "RESCUED"

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if current_screen == SCREEN_TITLE and start_button.collidepoint(pos):
                    current_screen = SCREEN_BRIEFING

                elif current_screen == SCREEN_BRIEFING and continue_button.collidepoint(pos):
                    # Enter open-world colony at the spawn pad
                    astronaut = player_sys.make_astronaut(colony["spawn"])
                    camera = cam_sys.make_camera(astronaut, WIDTH, HEIGHT)
                    cam_sys.clamp_camera(camera, WORLD_W, WORLD_H)
                    saved_base_pos = None
                    paused = False
                    current_screen = SCREEN_BASE

                elif current_screen == SCREEN_CH1_RADAR:
                    if ch1["phase"] == "ready" and radar_ui["scan_button"].collidepoint(pos):
                        ch1["phase"] = "scanning"
                        ch1["scan_angle"] = 0.0
                        ch1["scan_progress"] = 0.0
                        ch1["hint"] = ""
                    elif ch1["phase"] == "results":
                        for sat_id, rect in radar_ui["sat_rects"].items():
                            if rect.collidepoint(pos):
                                if sat_id == "SAT-02":
                                    ch1["hint"] = ""
                                    current_screen = SCREEN_CH1_ALIGN
                                else:
                                    ch1["hint"] = (
                                        f"{sat_id} is healthy. Choose the weak signal (SAT-02)."
                                    )

                elif current_screen == SCREEN_CH1_ALIGN:
                    if align_ui["left"].collidepoint(pos):
                        rotate_antenna(ch1, -1)
                    elif align_ui["right"].collidepoint(pos):
                        rotate_antenna(ch1, 1)

                elif current_screen == SCREEN_CH1_COMPLETE and return_button.collidepoint(pos):
                    communication_status = "ONLINE"
                    return_to_colony()

                elif current_screen == SCREEN_CH1_TIMEOUT and retry_button.collidepoint(pos):
                    ch1 = make_challenge1_state()
                    current_screen = SCREEN_CH1_RADAR

                elif current_screen == SCREEN_CH2_INTRO and ch2_intro_start.collidepoint(pos):
                    current_screen = SCREEN_CH2_WIRE

                elif current_screen == SCREEN_CH2_WIRE:
                    if ch2["wires_done"] and ch2_wire_ui["continue"].collidepoint(pos):
                        current_screen = SCREEN_CH2_POWER
                    else:
                        for part, rect in ch2_wire_ui["boxes"].items():
                            if rect.collidepoint(pos):
                                try_ch2_wire_click(ch2, part)
                                break

                elif current_screen == SCREEN_CH2_POWER and not ch2["completed"]:
                    for key, pair in ch2_power_ui.items():
                        if pair["minus"].collidepoint(pos):
                            ch2_change_power(ch2, key, -10)
                        elif pair["plus"].collidepoint(pos):
                            ch2_change_power(ch2, key, 10)

                elif current_screen == SCREEN_CH2_COMPLETE and return_button.collidepoint(pos):
                    power_status = "ONLINE"
                    food_status = "SAFE"
                    return_to_colony()

                elif current_screen == SCREEN_CH2_TIMEOUT:
                    if ch2_timeout_ui["retry"].collidepoint(pos):
                        ch2 = make_challenge2_state()
                        current_screen = SCREEN_CH2_INTRO
                    elif ch2_timeout_ui["base"].collidepoint(pos):
                        return_to_colony()

                elif current_screen == SCREEN_CH3_INTRO and ch3_intro_start.collidepoint(pos):
                    # Timer begins here and keeps running through scan + drive
                    ch3["time_left"] = float(CH3_TIME_LIMIT)
                    current_screen = SCREEN_CH3_SCAN

                elif current_screen == SCREEN_CH3_SCAN:
                    if ch3["phase"] == "ready" and ch3_scan_ui["scan_button"].collidepoint(pos):
                        ch3["phase"] = "scanning"
                        ch3["scan_angle"] = 0.0
                        ch3["scan_progress"] = 0.0
                        ch3["hint"] = ""
                    elif ch3["found"] and ch3_scan_ui["continue"].collidepoint(pos):
                        current_screen = SCREEN_CH3_DRIVE
                    elif ch3["phase"] == "results" and not ch3["found"]:
                        for cell_name, rect in ch3_scan_ui["cells"].items():
                            if rect.collidepoint(pos):
                                if cell_name == CH3_CORRECT_CELL:
                                    ch3["found"] = True
                                    ch3["hint"] = ""
                                else:
                                    ch3["hint"] = (
                                        f"{cell_name} is not strongest. Look for Strong (B2)."
                                    )
                                    ch3["time_left"] = max(0.0, ch3["time_left"] - CH3_WRONG_PENALTY)
                                break

                elif current_screen == SCREEN_CH3_COMPLETE and return_button.collidepoint(pos):
                    rover_status = "RESCUED"
                    return_to_colony()

                elif current_screen == SCREEN_CH3_TIMEOUT:
                    if ch3_timeout_ui["retry"].collidepoint(pos):
                        ch3 = make_challenge3_state()
                        current_screen = SCREEN_CH3_INTRO
                    elif ch3_timeout_ui["base"].collidepoint(pos):
                        return_to_colony()

        # ---- update ----
        update_dust_particles(dust_particles)
        env_time += dt
        # Gentle sideways drift for mountain layers (not gameplay)
        parallax_offset = math.sin(env_time * 0.12) * 16.0

        # Base exploration: move astronaut + camera (never during CH3 drive)
        inv_sys.update_inventory(inventory, dt)
        if current_screen == SCREEN_BASE and not paused and not (
            inventory["open"] or journal["open"] or map_open
        ):
            player_sys.move_astronaut(
                astronaut, keys, colony["colliders"], dt, WORLD_W, WORLD_H
            )
            cam_sys.update_camera(camera, astronaut, dt, WORLD_W, WORLD_H)
            particle_sys.update_dust(world_dust, dt, WORLD_W, WORLD_H)
            active_target = interactions.nearest_interactable(
                astronaut, colony["interactables"]
            )
        elif current_screen == SCREEN_BASE:
            active_target = interactions.nearest_interactable(
                astronaut, colony["interactables"]
            )
        else:
            active_target = None

        # Challenge 1 timer (pause after success)
        if current_screen in (SCREEN_CH1_RADAR, SCREEN_CH1_ALIGN) and not ch1["connection_restored"]:
            ch1["time_left"] -= dt
            if ch1["time_left"] <= 0:
                ch1["time_left"] = 0
                current_screen = SCREEN_CH1_TIMEOUT

        # Challenge 2 timer during wire + power stages
        if current_screen in (SCREEN_CH2_WIRE, SCREEN_CH2_POWER) and not ch2["completed"]:
            ch2["time_left"] -= dt
            if ch2["time_left"] <= 0:
                ch2["time_left"] = 0
                current_screen = SCREEN_CH2_TIMEOUT

        # Challenge 3 shared timer (scan + drive, no reset between them)
        if current_screen in (SCREEN_CH3_SCAN, SCREEN_CH3_DRIVE) and not ch3["rescued"]:
            ch3["time_left"] -= dt
            if ch3["time_left"] <= 0:
                ch3["time_left"] = 0
                current_screen = SCREEN_CH3_TIMEOUT

        # Food freshness slowly drops when Food Storage has too little power
        if current_screen == SCREEN_CH2_POWER and not ch2["completed"]:
            if ch2["food"] < 30:
                ch2["food_freshness"] -= CH2_FOOD_DECAY_PER_SEC * dt
                if ch2["food_freshness"] < 0:
                    ch2["food_freshness"] = 0

            # Win when wires are done AND all power minimums are met
            if ch2["wires_done"] and ch2_power_ok(ch2) and not ch2["completed"]:
                ch2["completed"] = True
                ch2["finish_time_left"] = ch2["time_left"]
                if not ch2["points_awarded"]:
                    score += CH2_POINTS
                    ch2["points_awarded"] = True
                power_status = "ONLINE"
                food_status = "SAFE"
                ch2["complete_delay"] = 1.0

        if current_screen == SCREEN_CH2_POWER and ch2["completed"]:
            ch2["complete_delay"] -= dt
            if ch2["complete_delay"] <= 0:
                current_screen = SCREEN_CH2_COMPLETE

        # Non-blocking radar sweep animation (Challenge 1)
        if current_screen == SCREEN_CH1_RADAR and ch1["phase"] == "scanning":
            ch1["scan_angle"] = (ch1["scan_angle"] + 280 * dt) % 360
            ch1["scan_progress"] += dt / 2.2  # about 2.2 seconds to finish
            if ch1["scan_progress"] >= 1.0:
                ch1["phase"] = "results"
                ch1["scan_progress"] = 1.0

        # Non-blocking satellite grid sweep (Challenge 3)
        if current_screen == SCREEN_CH3_SCAN and ch3["phase"] == "scanning":
            ch3["scan_angle"] = (ch3["scan_angle"] + 300 * dt) % 360
            ch3["scan_progress"] += dt / 2.0
            if ch3["scan_progress"] >= 1.0:
                ch3["phase"] = "results"
                ch3["scan_progress"] = 1.0

        # Drive the rescue rover
        if current_screen == SCREEN_CH3_DRIVE:
            update_ch3_drive(ch3, dt, keys)
            if ch3["rescued"]:
                ch3["complete_delay"] -= dt
                if ch3["complete_delay"] <= 0:
                    current_screen = SCREEN_CH3_COMPLETE

        # Check if the antenna is lined up with the target
        if (
            current_screen == SCREEN_CH1_ALIGN
            and ch1["antenna_angle"] == ANTENNA_TARGET_ANGLE
            and not ch1["connection_restored"]
        ):
            ch1["connection_restored"] = True
            if not ch1["points_awarded"]:
                score += CH1_POINTS
                ch1["points_awarded"] = True
            ch1["finish_time_left"] = ch1["time_left"]
            communication_status = "ONLINE"
            ch1["restore_delay"] = 1.2  # show "CONNECTION RESTORED" briefly

        # After the success message, open the completion panel (no sleep/blocking)
        if current_screen == SCREEN_CH1_ALIGN and ch1["connection_restored"]:
            ch1["restore_delay"] -= dt
            if ch1["restore_delay"] <= 0:
                current_screen = SCREEN_CH1_COMPLETE

        # ---- draw ----
        online = communication_status == "ONLINE"
        status_pack = {
            "comm": communication_status,
            "power": power_status,
            "food": food_status,
            "rover": rover_status,
        }

        if current_screen == SCREEN_BASE:
            def _draw_astro():
                player_sys.draw_astronaut(
                    screen, astronaut, camera, power_online=(power_status == "ONLINE")
                )

            colony_sys.draw_colony_world(
                screen,
                colony,
                camera,
                world_dust,
                parallax_offset,
                status_pack,
                near_id=(active_target["id"] if active_target else None),
                draw_fn_dust=particle_sys.draw_dust,
                astronaut=astronaut,
                draw_astronaut_fn=_draw_astro,
            )
        elif current_screen not in (SCREEN_CH3_DRIVE, SCREEN_CH3_COMPLETE, SCREEN_CH3_TIMEOUT):
            # Title / briefing / challenge overlays still use the classic base plate
            draw_world(
                screen,
                rocks,
                craters,
                dust_particles,
                communication_online=online,
                parallax=parallax_offset,
            )

        def hud():
            draw_hud(
                screen,
                fonts,
                communication_status,
                score,
                power_status,
                food_status,
                rover_status,
            )

        if current_screen == SCREEN_TITLE:
            hud()
            draw_button(screen, start_button, "START MISSION", fonts, mouse_pos)

        elif current_screen == SCREEN_BRIEFING:
            hud()
            continue_button = draw_briefing_panel(screen, fonts, mouse_pos)

        elif current_screen == SCREEN_BASE:
            prompt = active_target["prompt"] if active_target else ""
            zone_name = colony_sys.zone_at(colony, astronaut["x"], astronaut["y"])
            objective = colony_sys.current_objective(
                communication_status, power_status, food_status, rover_status
            )
            hud_explore.draw_explore_hud(
                screen,
                fonts,
                astronaut,
                colony,
                camera,
                communication_status,
                power_status,
                food_status,
                rover_status,
                score,
                zone_name,
                objective,
                len(inventory["items"]),
                prompt=prompt,
                paused=paused,
            )
            inv_sys.draw_toast(screen, fonts, inventory)
            inv_sys.draw_inventory(screen, fonts, inventory, mouse_pos)
            journal_sys.draw_journal(
                screen,
                fonts,
                journal,
                communication_status,
                power_status,
                food_status,
                rover_status,
                score,
                inventory["items"],
            )
            map_sys.draw_full_map(
                screen, fonts, astronaut, colony, WORLD_W, WORLD_H, map_open
            )

        elif current_screen == SCREEN_CH1_RADAR:
            hud()
            draw_timer(screen, fonts, ch1["time_left"])
            radar_ui = draw_radar_screen(screen, fonts, mouse_pos, ch1)

        elif current_screen == SCREEN_CH1_ALIGN:
            hud()
            draw_timer(screen, fonts, ch1["time_left"])
            align_ui = draw_alignment_screen(screen, fonts, mouse_pos, ch1)

        elif current_screen == SCREEN_CH1_COMPLETE:
            hud()
            return_button = draw_complete_panel(
                screen, fonts, mouse_pos, score, ch1["finish_time_left"]
            )

        elif current_screen == SCREEN_CH1_TIMEOUT:
            hud()
            retry_button = draw_timeout_panel(screen, fonts, mouse_pos)

        elif current_screen == SCREEN_CH2_INTRO:
            hud()
            ch2_intro_start = draw_ch2_intro(screen, fonts, mouse_pos)

        elif current_screen == SCREEN_CH2_WIRE:
            hud()
            draw_timer(screen, fonts, ch2["time_left"])
            ch2_wire_ui = draw_ch2_wire_screen(screen, fonts, mouse_pos, ch2)

        elif current_screen == SCREEN_CH2_POWER:
            hud()
            draw_timer(screen, fonts, ch2["time_left"])
            ch2_power_ui = draw_ch2_power_screen(screen, fonts, mouse_pos, ch2)

        elif current_screen == SCREEN_CH2_COMPLETE:
            hud()
            return_button = draw_ch2_complete_panel(
                screen,
                fonts,
                mouse_pos,
                score,
                ch2["finish_time_left"],
                ch2["food_freshness"],
            )

        elif current_screen == SCREEN_CH2_TIMEOUT:
            hud()
            ch2_timeout_ui = draw_ch2_timeout_panel(screen, fonts, mouse_pos)

        elif current_screen == SCREEN_CH3_INTRO:
            hud()
            ch3_intro_start = draw_ch3_intro(screen, fonts, mouse_pos)

        elif current_screen == SCREEN_CH3_SCAN:
            hud()
            draw_timer(screen, fonts, ch3["time_left"])
            ch3_scan_ui = draw_ch3_scan_screen(screen, fonts, mouse_pos, ch3)

        elif current_screen == SCREEN_CH3_DRIVE:
            draw_ch3_drive_world(screen, ch3, fonts)
            hud()
            draw_timer(screen, fonts, ch3["time_left"])

        elif current_screen == SCREEN_CH3_COMPLETE:
            draw_ch3_drive_world(screen, ch3, fonts)
            hud()
            return_button = draw_ch3_complete_panel(
                screen,
                fonts,
                mouse_pos,
                score,
                ch3["finish_time_left"],
                ch3["finish_storm"],
            )

        elif current_screen == SCREEN_CH3_TIMEOUT:
            # Show a stormy desert behind the fail panel
            draw_ch3_drive_world(screen, ch3, fonts)
            hud()
            ch3_timeout_ui = draw_ch3_timeout_panel(screen, fonts, mouse_pos)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
