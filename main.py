"""
Mars Mission: Restore, Recharge & Rescue!
A beginner-friendly 2.5D Mars base game.
Shapes are the fallback; PNG assets in /assets are used when present.
"""

import math
import os
import random
import sys
import traceback

import pygame

# Ensure project root is importable when launched as a script
_BOOT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _BOOT_ROOT not in sys.path:
    sys.path.insert(0, _BOOT_ROOT)

from systems import runtime_paths as rpaths

_ROOT = str(rpaths.resource_root())
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
_exe_dir = str(rpaths.executable_dir())
if _exe_dir not in sys.path:
    sys.path.insert(0, _exe_dir)

from systems import audio_fx
from systems import camera as cam_sys
from systems import antenna_tutorial as atut
from systems import challenges_ch1 as ch1mod
from systems import challenges_ch2 as ch2mod
from systems import challenges_ch3 as ch3mod
from systems import challenge_ui as chal_ui
from systems import mission_debrief as debrief_sys
from systems import outpost as outpost_sys
from systems import outpost_ui
from systems import colony as colony_sys
from systems import hud_explore
from systems import interactions
from systems import inventory as inv_sys
from systems import journal as journal_sys
from systems import lighting as light_sys
from systems import caches as cache_sys
from systems import campaign as camp
from systems import campaign_ui as camp_ui
from systems import guidance as guide_sys
from systems import materials as mats
from systems import minimap as map_sys
from systems import notify as notify_sys
from systems import particles as particle_sys
from systems import player as player_sys
from systems import procurement as proc
from systems import research_terminal as research_term
from systems import savegame
from systems import scanner as scanner_sys
from systems import terrain as terrain_sys
from systems import tutorials as tut_sys
from systems import wind as wind_sys
from systems import workbench as wb
from systems import version as app_version
from systems.colony import WORLD_H, WORLD_W

# ---- Window size and speed ----
WIDTH = 1280
HEIGHT = 720
FPS = 60

# Folder that holds backgrounds, sprites, effects, ui, and audio
# Resolves correctly in development and inside PyInstaller bundles
ASSETS_DIR = str(rpaths.assets_dir())

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
SCREEN_CH1_DIAG = "ch1_diag"        # Challenge 1: diagnose symptoms
SCREEN_CH1_ASSEMBLE = "ch1_assemble"  # antenna component assembly
SCREEN_CH1_RADAR = "ch1_radar"      # radar signal investigation
SCREEN_CH1_BRIEF = "ch1_brief"      # antenna briefing (no timer)
SCREEN_CH1_PRACTICE = "ch1_practice"  # guided practice (no timer)
SCREEN_CH1_READY = "ch1_ready"      # confirm before timed calibration
SCREEN_CH1_ALIGN = "ch1_align"      # timed antenna calibration + packets
SCREEN_CH1_COMPLETE = "ch1_complete"
SCREEN_CH1_TIMEOUT = "ch1_timeout"
SCREEN_CH2_INTRO = "ch2_intro"      # Challenge 2: power failure story
SCREEN_CH2_WIRE = "ch2_wire"        # circuit construction board
SCREEN_CH2_POWER = "ch2_power"      # share the energy budget
SCREEN_CH2_COMPLETE = "ch2_complete"
SCREEN_CH2_TIMEOUT = "ch2_timeout"
SCREEN_CH3_INTRO = "ch3_intro"      # Challenge 3: rover rescue story
SCREEN_CH3_SCAN = "ch3_scan"        # find the stranded rover on a grid
SCREEN_CH3_DIAG = "ch3_diag"        # rover diagnostics
SCREEN_CH3_REPAIR = "ch3_repair"    # repair bay
SCREEN_CH3_ROUTE = "ch3_route"      # route planning
SCREEN_CH3_DRIVE = "ch3_drive"      # drive across Mars to rescue it
SCREEN_CH3_COMPLETE = "ch3_complete"
SCREEN_CH3_TIMEOUT = "ch3_timeout"
SCREEN_RESEARCH = "research"
SCREEN_SHOP = "shop"
SCREEN_DASHBOARD = "dashboard"
SCREEN_MISSION_REPORT = "mission_report"
SCREEN_FINAL_REPORT = "final_report"
SCREEN_LOCKED = "mission_locked"
SCREEN_NEW_CAMPAIGN = "new_campaign_confirm"
SCREEN_MISSION_PREP = "mission_prep"
SCREEN_RECORDS = "mission_records"
SCREEN_OUTPOST = "outpost"
SCREEN_DEBRIEF = "mission_debrief"

CH1_ACTIVE = (SCREEN_CH1_DIAG, SCREEN_CH1_ASSEMBLE, SCREEN_CH1_RADAR, SCREEN_CH1_ALIGN)
CH1_TIMED = (SCREEN_CH1_ALIGN,)  # countdown only during timed calibration
CH2_ACTIVE = (SCREEN_CH2_WIRE, SCREEN_CH2_POWER)
CH3_ACTIVE = (
    SCREEN_CH3_SCAN, SCREEN_CH3_DIAG, SCREEN_CH3_REPAIR, SCREEN_CH3_ROUTE, SCREEN_CH3_DRIVE
)

# ---- Challenge 1 settings (authoritative values live in challenges_ch1) ----
CH1_TIME_LIMIT = 120         # timed calibration only
ANTENNA_START_ANGLE = 5      # near target for forgiving start
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
CH3_ROVER_SPEED = 220.0      # max speed (pixels / second) — balancing unchanged
CH3_HIT_SLOW = 0.45          # brief traction loss after hitting a rock
CH3_ROVER_ACCEL = 380.0      # Milestone 2: heavier feel via accel (same max speed)
CH3_ROVER_FRICTION = 520.0

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
    """Compact challenge-side status chips (no large score / material panels)."""
    from systems import challenge_ui as _ui

    chips = [
        ("COMM", communication_status),
        ("PWR", power_status),
        ("RVR", rover_status),
    ]
    x = 16
    for lab, val in chips:
        ok = val in ("ONLINE", "SAFE", "RESCUED", "NOMINAL")
        _ui.status_chip(surface, fonts, f"{lab} {val[:8]}", (x, 16), ok, width=130)
        x += 138


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
    """Legacy wrapper — delegates to the shared design-system button."""
    return chal_ui.button(surface, rect, label, fonts, mouse_pos, small=(font_key == "button_small"), accent=True)


def draw_briefing_panel(surface, fonts, mouse_pos):
    """Show a short mission briefing and a Continue button."""
    chal_ui.dim_backdrop(surface, 150)
    panel = pygame.Rect(240, 140, 800, 420)
    chal_ui.panel(surface, panel)
    chal_ui.header(
        surface, fonts, panel,
        "MISSION BRIEFING",
        "Restore communications · Recharge power · Rescue the rover",
    )
    briefing_lines = [
        "Welcome, young astronaut!",
        "A dust storm damaged our Mars research base.",
        "Explore zones, collect repair materials (E), then use stations.",
        "Earn Research Points from NASA data, buy kits, then repair systems.",
        "C = Campaign · Research Lab & Procurement at the base · ESC leaves safely.",
    ]
    for i, line in enumerate(briefing_lines):
        chal_ui.centered(surface, fonts, line, (panel.centerx, 240 + i * 34), chal_ui.C_TEXT, "body")
    continue_rect = button_rect(panel.centerx, 500, 260, 56)
    chal_ui.button(surface, continue_rect, "CONTINUE", fonts, mouse_pos)
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
    """Fresh Challenge 1 state (radar tracking + antenna packets)."""
    return ch1mod.make_state()


def signal_strength(angle):
    """How strong the signal is (0-100). Closest to +20 is best."""
    return ch1mod.signal_strength(angle)


def draw_timer(surface, fonts, time_left):
    """Mission countdown badge (shared challenge chrome)."""
    chal_ui.timer_badge(surface, fonts, time_left, WIDTH)
    return


def _legacy_draw_timer(surface, fonts, time_left):
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
    return ch1mod.draw_radar(surface, fonts, mouse_pos, ch1)


def draw_alignment_screen(surface, fonts, mouse_pos, ch1):
    """Antenna calibration with packet acquisition."""
    return ch1mod.draw_align(surface, fonts, mouse_pos, ch1)


def draw_complete_panel(surface, fonts, mouse_pos, score, time_left):
    return ch1mod.draw_complete(surface, fonts, mouse_pos, score, time_left)


def draw_timeout_panel(surface, fonts, mouse_pos):
    return ch1mod.draw_timeout(surface, fonts, mouse_pos)


def rotate_antenna(ch1, direction):
    """Turn the antenna left (-1) or right (+1) by 5 degrees."""
    ch1mod.rotate_antenna(ch1, direction)


# =====================================================================
# Challenge 2 — Restore Shelter Power
# =====================================================================


def make_challenge2_state():
    """Fresh Challenge 2 state (drag cables + power board)."""
    return ch2mod.make_state()


def ch2_total_power(ch2):
    return ch2mod.total_power(ch2)


def ch2_power_ok(ch2):
    return ch2mod.power_ok(ch2)


def ch2_change_power(ch2, system, delta):
    ch2mod.change_power(ch2, system, delta)


def draw_dim_panel(surface, rect):
    """Shared dark console panel used by Challenge 2 screens."""
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dim.fill((8, 4, 0, 140))
    surface.blit(dim, (0, 0))
    pygame.draw.rect(surface, PANEL_DARK, rect, border_radius=18)
    pygame.draw.rect(surface, (255, 170, 90), rect, 3, border_radius=18)


def draw_ch2_intro(surface, fonts, mouse_pos):
    return ch2mod.draw_intro(surface, fonts, mouse_pos)


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
    return ch2mod.draw_wire(surface, fonts, mouse_pos, ch2)


def try_ch2_wire_click(ch2, part):
    """Legacy no-op — wiring uses drag-and-snap."""
    return


def draw_ch2_power_screen(surface, fonts, mouse_pos, ch2):
    return ch2mod.draw_power(surface, fonts, mouse_pos, ch2)


def draw_ch2_complete_panel(surface, fonts, mouse_pos, score, time_left, freshness):
    return ch2mod.draw_complete(surface, fonts, mouse_pos, score, time_left, freshness)


def draw_ch2_timeout_panel(surface, fonts, mouse_pos):
    return ch2mod.draw_timeout(surface, fonts, mouse_pos)


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
    """Fresh Challenge 3 state (scan + heading-based rover)."""
    return ch3mod.make_state()


def ch3_storm_intensity(ch3):
    return ch3mod.storm_intensity(ch3)


def ch3_rover_rect(ch3):
    """Hit box used for collisions and rescue range."""
    return pygame.Rect(int(ch3["rover_x"]), int(ch3["rover_y"]), 110, 55)


def draw_ch3_intro(surface, fonts, mouse_pos):
    return ch3mod.draw_intro(surface, fonts, mouse_pos)


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
    return ch3mod.draw_scan(surface, fonts, mouse_pos, ch3)


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
    ch3mod.draw_drive(surface, ch3, fonts)


def update_ch3_drive(ch3, dt, keys):
    ch3mod.update_drive(ch3, dt, keys)


def try_ch3_rescue(ch3):
    return ch3mod.try_rescue(ch3)


def draw_ch3_complete_panel(surface, fonts, mouse_pos, score, time_left, storm):
    return ch3mod.draw_complete(surface, fonts, mouse_pos, score, time_left, storm)


def draw_ch3_timeout_panel(surface, fonts, mouse_pos):
    return ch3mod.draw_timeout(surface, fonts, mouse_pos)


# =====================================================================
# Milestone 1 open-world systems live under systems/
# (player, camera, colony, interactions, inventory, journal, …)
# Challenge screens CH1–CH3 below / above remain in this file.
# =====================================================================


def main():
    """Start the game window and keep drawing until we quit."""
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(app_version.APP_TITLE)
    clock = pygame.time.Clock()

    fonts = {
        "title": pygame.font.SysFont("segoeui", 26, bold=True),
        "body": pygame.font.SysFont("segoeui", 15),
        "small": pygame.font.SysFont("segoeui", 12),
        "button": pygame.font.SysFont("segoeui", 15, bold=True),
        "button_small": pygame.font.SysFont("segoeui", 12, bold=True),
    }

    # Load optional PNGs + build cached sky/ground plates once
    preload_environment_assets()

    rocks, craters = make_ground_details()
    dust_particles = make_dust_particles()
    env_time = 0.0  # drives subtle parallax motion

    # Open-world colony (3200×2200) — challenges still opened via stations
    colony = colony_sys.make_colony(
        SCREEN_CH1_DIAG, SCREEN_CH2_INTRO, SCREEN_CH3_INTRO,
        SCREEN_RESEARCH, SCREEN_SHOP,
    )
    terrain_map = terrain_sys.build_terrain_map(colony)
    wind = wind_sys.make_wind()
    astronaut = player_sys.make_astronaut(colony["spawn"])
    camera = cam_sys.make_camera(astronaut, WIDTH, HEIGHT)
    cam_sys.clamp_camera(camera, WORLD_W, WORLD_H)
    fx = particle_sys.make_system(WORLD_W, WORLD_H, ambient=60)
    world_dust = fx  # alias for draw path
    inventory = inv_sys.make_inventory()
    journal = journal_sys.make_journal()
    discovery = map_sys.make_discovery(colony["spawn"])
    map_sys.reveal_around(discovery, colony["spawn"][0], colony["spawn"][1], radius=320)
    field_scanner = scanner_sys.make_scanner()
    tutorials = tut_sys.make_tutorials()
    guidance = guide_sys.make_guidance()
    notifier = notify_sys.make_notifier()
    shop_ui = {"selected": None}
    map_ui = {}
    map_open = False
    paused = False
    active_target = None
    saved_base_pos = None  # restored after challenges
    audio_fx.init_audio(ASSETS_DIR)
    _signal_t = 0.0
    tut_sys.trigger(tutorials, "inventory")

    # ---- Campaign save / load (never auto-create / overwrite on failure) ----
    save_load_error = None
    recovery_info = savegame.recovery_needed()
    loaded = None
    try:
        loaded = savegame.load_campaign()
    except ValueError as exc:
        print("SAVE WARNING:", exc)
        save_load_error = str(exc)
        recovery_info = savegame.recovery_needed() or {"message": str(exc)}

    campaign = None
    has_campaign_save = loaded is not None
    if loaded is not None:
        campaign = loaded
        for mid, slot in (campaign.get("inventory_stock") or {}).items():
            if mid in inventory["stock"] and isinstance(slot, dict):
                inventory["stock"][mid]["qty"] = int(slot.get("qty", 0))
                inventory["stock"][mid]["reserved"] = 0
        for z in campaign.get("discovered_locations") or []:
            discovery["landmarks"].add(z)
        for key in campaign.get("discovery_revealed") or []:
            discovery["revealed"].add(key)
        for uid in campaign.get("discovery_identified") or []:
            discovery["identified"].add(uid)
        for uid in campaign.get("discovery_scanned") or []:
            discovery["scanned_ids"].add(uid)
        if campaign.get("current_player_position"):
            try:
                px, py = campaign["current_player_position"]
                astronaut["x"], astronaut["y"] = float(px), float(py)
                cam_sys.update_camera(camera, astronaut, 1.0, WORLD_W, WORLD_H)
            except (TypeError, ValueError):
                pass

    # Placeholder until Continue / New Campaign — do not persist empty campaign on boot
    if campaign is None:
        campaign = camp.make_campaign()
        has_campaign_save = False

    cache_sys.ensure_campaign_caches(campaign)
    cache_sys.refresh_colony_supplies(colony, campaign)
    outpost_sys.ensure_outpost(campaign)

    replay_ctx = None  # practice isolation snapshot
    campaign_inventory = inventory  # permanent inventory reference
    title_hit = {}
    newcamp_hit = {}
    prep_hit = {}
    records_hit = {}
    outpost_hit = {}
    debrief_hit = {}
    debrief_mission_id = "mission_1"
    prep_mission_id = "mission_1"
    pending_station_screen = SCREEN_CH1_DIAG

    def persist():
        if replay_ctx is not None:
            return False  # never write practice mutations over campaign save
        if not has_campaign_save:
            return False
        campaign["current_player_position"] = [astronaut["x"], astronaut["y"]]
        campaign["total_play_time"] = float(campaign.get("total_play_time", 0.0)) + 0.0
        data = camp.export_for_save(campaign, inventory["stock"], discovery)
        return savegame.save_campaign(data)

    def apply_loaded_campaign(data: dict, reset_world: bool = False):
        nonlocal campaign, inventory, campaign_inventory, has_campaign_save, discovery, astronaut, camera
        nonlocal communication_status, power_status, food_status, rover_status, score, progression
        campaign = data
        has_campaign_save = True
        inventory = inv_sys.make_inventory()
        for mid, slot in (campaign.get("inventory_stock") or {}).items():
            if mid in inventory["stock"] and isinstance(slot, dict):
                inventory["stock"][mid]["qty"] = int(slot.get("qty", 0))
        campaign_inventory = inventory
        if reset_world:
            discovery = map_sys.make_discovery(colony["spawn"])
            map_sys.reveal_around(discovery, colony["spawn"][0], colony["spawn"][1], radius=320)
            astronaut = player_sys.make_astronaut(colony["spawn"])
            camera = cam_sys.make_camera(astronaut, WIDTH, HEIGHT)
            cam_sys.clamp_camera(camera, WORLD_W, WORLD_H)
            # Clear prior material pickups then respawn for new seed
            colony["collectibles"] = [c for c in colony["collectibles"] if not c.get("material")]
            stations = [x for x in colony.get("interactables", []) if x.get("type") == "station"]
            colony["interactables"] = stations + colony["collectibles"]
        cache_sys.ensure_campaign_caches(campaign)
        cache_sys.refresh_colony_supplies(colony, campaign)
        progression = campaign["cross"]
        refresh_status()

    research_ui = research_term.make_ui_state()
    research_hit = {}
    shop_hit = {}
    dash_hit = {}
    report_hit = {}
    report_mission_id = "mission_1"
    locked_reason = ""
    locked_hit = {}

    current_screen = SCREEN_TITLE
    start_button = button_rect(WIDTH // 2, 640, 300, 60)
    continue_button = pygame.Rect(0, 0, 260, 56)

    # Mission progress mirrored from campaign
    communication_status, power_status, food_status, rover_status = camp.sync_status_flags(campaign)
    score = campaign["mission_score"]
    progression = campaign["cross"]  # reuse cross-bonus dict
    ch1 = make_challenge1_state()
    ch2 = make_challenge2_state()
    ch3 = make_challenge3_state()

    def refresh_status():
        nonlocal communication_status, power_status, food_status, rover_status, score
        communication_status, power_status, food_status, rover_status = camp.sync_status_flags(campaign)
        score = campaign["mission_score"]

    def begin_mission_challenge(mid: str, default_screen: str):
        nonlocal current_screen, ch1, ch2, ch3, inventory
        if replay_ctx is None:
            camp.mark_in_progress(campaign, mid)
        if mid == "mission_1":
            ch1 = make_challenge1_state()
            if replay_ctx is None:
                journal_sys.add_clue(journal, "ch1_symptom_weak")
            tut_sys.trigger(tutorials, "assembly")
        elif mid == "mission_2":
            ch2 = make_challenge2_state()
            if replay_ctx is None:
                journal_sys.add_clue(journal, "ch2_path")
        elif mid == "mission_3":
            ch3 = make_challenge3_state()
            apply_ch3_scan_bonus()
            tut_sys.trigger(tutorials, "assembly")
        current_screen = default_screen
        if replay_ctx is None:
            persist()

    def start_replay(mid: str):
        nonlocal replay_ctx, inventory, report_mission_id
        replay_ctx = camp.begin_replay(campaign, mid)
        inventory = camp.practice_inventory_for(mid)
        meta = camp.MISSION_META[mid]
        begin_mission_challenge(mid, meta["screen"])
        notify_sys.push(notifier, "PRACTICE / REPLAY — no campaign rewards", "info")

    def end_replay_session():
        nonlocal replay_ctx, inventory
        if replay_ctx is None:
            return
        camp.end_replay(campaign, replay_ctx)
        replay_ctx = None
        inventory = campaign_inventory
        # Restore stock from campaign after replay restore
        for mid, slot in (campaign.get("inventory_stock") or {}).items():
            if mid in inventory["stock"] and isinstance(slot, dict):
                inventory["stock"][mid]["qty"] = int(slot.get("qty", 0))
                inventory["stock"][mid]["reserved"] = 0
        refresh_status()

    def award_mission_if_campaign(mid: str, report: dict):
        """Complete mission only outside replay practice."""
        nonlocal debrief_mission_id
        if replay_ctx is not None:
            return {"awarded": False, "message": "Practice complete — no campaign rewards."}
        award = camp.complete_mission(campaign, mid, report)
        refresh_status()
        cache_sys.refresh_colony_supplies(colony, campaign)
        if award.get("awarded"):
            debrief_mission_id = mid
        persist()
        return award

    def open_station(station_id: str, default_screen: str):
        """Central unlock / completion / readiness gate for challenge stations."""
        nonlocal current_screen, report_mission_id, locked_reason, prep_mission_id, pending_station_screen
        mid = camp.station_to_mission(station_id)
        if mid is None:
            current_screen = default_screen
            return
        if not has_campaign_save:
            locked_reason = "Start or continue a campaign from the title screen first."
            current_screen = SCREEN_LOCKED
            return
        st = camp.mission_status(campaign, mid)
        if st == camp.STATUS_COMPLETED:
            report_mission_id = mid
            current_screen = SCREEN_MISSION_REPORT
            return
        if st == camp.STATUS_LOCKED:
            locked_reason = camp.lock_reason(campaign, mid)
            current_screen = SCREEN_LOCKED
            return
        # Available / in progress — require research + materials before start
        prep_mission_id = mid
        pending_station_screen = default_screen
        ready = camp.mission_readiness(campaign, inventory["stock"], mid)
        if ready["can_start"]:
            begin_mission_challenge(mid, default_screen)
        else:
            current_screen = SCREEN_MISSION_PREP

    # Buttons that change each frame on challenge screens
    ch1_diag_ui = {"symptoms": {}, "continue": pygame.Rect(0, 0, 0, 0)}
    ch1_assemble_ui = {}
    radar_ui = {
        "scan": pygame.Rect(0, 0, 0, 0),
        "freq_minus": pygame.Rect(0, 0, 0, 0),
        "freq_plus": pygame.Rect(0, 0, 0, 0),
        "gain_minus": pygame.Rect(0, 0, 0, 0),
        "gain_plus": pygame.Rect(0, 0, 0, 0),
        "sat_rects": {},
        "continue": pygame.Rect(0, 0, 0, 0),
    }
    align_ui = {"left": pygame.Rect(0, 0, 0, 0), "right": pygame.Rect(0, 0, 0, 0)}
    brief_hit = {}
    ready_hit = {}
    return_button = pygame.Rect(0, 0, 0, 0)
    retry_button = pygame.Rect(0, 0, 0, 0)
    ch2_intro_start = pygame.Rect(0, 0, 0, 0)
    ch2_wire_ui = {
        "continue": pygame.Rect(0, 0, 0, 0),
        "reset": pygame.Rect(0, 0, 0, 0),
        "ports": {},
        "test": pygame.Rect(0, 0, 0, 0),
        "fuse": pygame.Rect(0, 0, 0, 0),
    }
    ch2_power_ui = {}
    ch2_timeout_ui = {"retry": pygame.Rect(0, 0, 0, 0), "base": pygame.Rect(0, 0, 0, 0)}
    ch3_intro_start = pygame.Rect(0, 0, 0, 0)
    ch3_scan_ui = {
        "cells": {},
        "scan_button": pygame.Rect(0, 0, 0, 0),
        "continue": pygame.Rect(0, 0, 0, 0),
    }
    ch3_diag_ui = {"symptoms": {}, "continue": pygame.Rect(0, 0, 0, 0)}
    ch3_repair_ui = {}
    ch3_route_ui = {"routes": {}, "continue": pygame.Rect(0, 0, 0, 0)}
    ch3_timeout_ui = {"retry": pygame.Rect(0, 0, 0, 0), "base": pygame.Rect(0, 0, 0, 0)}

    def sync_inventory_highlight():
        if current_screen in (
            *CH1_ACTIVE,
            SCREEN_CH1_BRIEF,
            SCREEN_CH1_PRACTICE,
            SCREEN_CH1_READY,
            SCREEN_CH1_TIMEOUT,
        ):
            inventory["highlight_mission"] = "ch1"
        elif current_screen in CH2_ACTIVE or current_screen in (SCREEN_CH2_INTRO, SCREEN_CH2_TIMEOUT):
            inventory["highlight_mission"] = "ch2"
        elif current_screen in CH3_ACTIVE or current_screen in (SCREEN_CH3_INTRO, SCREEN_CH3_TIMEOUT):
            inventory["highlight_mission"] = "ch3"
        else:
            inventory["highlight_mission"] = None

    def apply_ch3_scan_bonus():
        clarity = 0.0
        if campaign["cross"].get("comm_restored"):
            clarity += 0.45
        clarity += min(0.4, campaign["cross"].get("extra_comms", 0) / 20.0)
        clarity = max(clarity, campaign["cross"].get("scan_clarity", 0))
        ch3["scan_clarity"] = clarity

    def return_to_colony():
        """Leave a challenge and restore exploration at the saved world position."""
        nonlocal current_screen
        if replay_ctx is not None:
            end_replay_session()
            notify_sys.push(notifier, "Exited practice replay", "info")
        if saved_base_pos is not None:
            astronaut["x"], astronaut["y"] = saved_base_pos
        cam_sys.update_camera(camera, astronaut, 1.0, WORLD_W, WORLD_H)
        current_screen = SCREEN_BASE
        persist()

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        dt = clock.get_time() / 1000.0  # seconds since last frame
        keys = pygame.key.get_pressed()

        # ---- events ----
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if replay_ctx is not None:
                    end_replay_session()
                persist()
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
                elif inventory["open"]:
                    inventory["open"] = False
                elif journal["open"]:
                    journal["open"] = False
                elif current_screen in (
                    SCREEN_TITLE, SCREEN_BRIEFING,
                    SCREEN_CH1_COMPLETE, SCREEN_CH2_COMPLETE, SCREEN_CH3_COMPLETE,
                ):
                    running = False
                else:
                    # Leave challenge without soft-lock — materials reserved are released
                    mats.release_all_reserved(inventory["stock"])
                    return_to_colony()

            elif event.type == pygame.KEYDOWN and current_screen == SCREEN_BASE and paused:
                if event.key == pygame.K_q:
                    if replay_ctx is not None:
                        end_replay_session()
                    persist()
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
                    sync_inventory_highlight()
                    if inventory["open"]:
                        tut_sys.trigger(tutorials, "inventory")
                elif event.key == pygame.K_j:
                    journal["open"] = not journal["open"]
                    inventory["open"] = False
                    map_open = False
                elif event.key == pygame.K_m:
                    map_open = not map_open
                    inventory["open"] = False
                    journal["open"] = False
                    if map_open:
                        tut_sys.trigger(tutorials, "map")
                elif event.key == pygame.K_c:
                    inventory["open"] = False
                    journal["open"] = False
                    map_open = False
                    current_screen = SCREEN_DASHBOARD
                elif event.key == pygame.K_o:
                    inventory["open"] = False
                    journal["open"] = False
                    map_open = False
                    outpost_sys.ensure_outpost(campaign)
                    current_screen = SCREEN_OUTPOST
                elif event.key == pygame.K_g:
                    guidance["enabled"] = not guidance["enabled"]
                    notify_sys.push(
                        notifier,
                        "Guidance ON" if guidance["enabled"] else "Guidance OFF",
                        "info",
                    )
                elif event.key == pygame.K_TAB:
                    scanner_sys.start_scan(field_scanner, astronaut, colony, discovery)
                    tut_sys.trigger(tutorials, "scanner")
                elif event.key == pygame.K_e and not (
                    inventory["open"] or journal["open"] or map_open
                ):
                    # Edge-triggered interact (once per key press)
                    if active_target is not None:
                        if active_target.get("type") == "station":
                            saved_base_pos = (astronaut["x"], astronaut["y"])
                            sid = active_target["id"]
                            player_sys.set_anim(astronaut, "interact", 0.3)
                            particle_sys.emit_sparks(
                                fx, active_target["pos"][0], active_target["pos"][1] - 10
                            )
                            audio_fx.play("interact", 0.45)
                            open_station(sid, active_target["screen"])
                            inventory["open"] = False
                            journal["open"] = False
                            map_open = False
                            sync_inventory_highlight()
                        elif active_target.get("type") == "collectible":
                            if inv_sys.add_item(inventory, active_target):
                                active_target["collected"] = True
                                active_target["status"] = "collected"
                                discovery["identified"].add(active_target["id"])
                                discovery["scanned_ids"].add(active_target["id"])
                                cache_sys.mark_collected(campaign, active_target["id"])
                                player_sys.set_anim(astronaut, "collect", 0.45)
                                particle_sys.emit_pickup(
                                    fx, active_target["pos"][0], active_target["pos"][1]
                                )
                                audio_fx.play("pickup", 0.5)
                                if active_target.get("material") == "research_log":
                                    journal_sys.add_clue(journal, "research_storm")
                                scanner_sys.try_identify_nearby(astronaut, colony, discovery)
                                persist()

            elif event.type == pygame.KEYDOWN and current_screen in (
                SCREEN_CH1_ALIGN, SCREEN_CH1_PRACTICE
            ):
                if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                    rotate_antenna(ch1, -1)
                elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                    rotate_antenna(ch1, 1)

            elif event.type == pygame.KEYDOWN and current_screen == SCREEN_CH3_DRIVE:
                # Press E near the stranded rover to rescue it
                if event.key == pygame.K_e:
                    if try_ch3_rescue(ch3):
                        if not ch3["points_awarded"]:
                            ch3["points_awarded"] = True
                            award = award_mission_if_campaign(
                                "mission_3",
                                {
                                    "time_left": int(ch3.get("finish_time_left", 0)),
                                    "summary": f"Route {ch3.get('route')}; rover rescued.",
                                },
                            )
                            if award.get("awarded"):
                                audio_fx.play("success", 0.5)
                            elif replay_ctx is not None:
                                notify_sys.push(notifier, "Practice rescue complete", "success")

            # Allow I/J during challenges for materials / clues
            elif event.type == pygame.KEYDOWN and current_screen != SCREEN_BASE:
                if event.key == pygame.K_i:
                    inventory["open"] = not inventory["open"]
                    sync_inventory_highlight()
                elif event.key == pygame.K_j:
                    journal["open"] = not journal["open"]

            # Challenge cable / assembly drag
            elif current_screen == SCREEN_CH2_WIRE and event.type in (
                pygame.MOUSEMOTION,
                pygame.MOUSEBUTTONUP,
            ):
                if ch2_wire_ui.get("ports"):
                    ch2mod.handle_wire_event(ch2, event, ch2_wire_ui, inventory)

            elif current_screen == SCREEN_CH1_ASSEMBLE and event.type in (
                pygame.MOUSEMOTION,
                pygame.MOUSEBUTTONUP,
                pygame.MOUSEBUTTONDOWN,
            ):
                if event.type == pygame.MOUSEBUTTONDOWN and inventory["open"]:
                    inv_sys.handle_inventory_click(inventory, event.pos)
                elif ch1_assemble_ui.get("slots"):
                    nxt = ch1mod.handle_assemble_event(ch1, event, ch1_assemble_ui, inventory)
                    if nxt == "radar":
                        current_screen = SCREEN_CH1_RADAR

            elif map_open and current_screen == SCREEN_BASE and event.type in (
                pygame.MOUSEBUTTONDOWN,
                pygame.MOUSEBUTTONUP,
                pygame.MOUSEMOTION,
                pygame.MOUSEWHEEL,
            ):
                if tut_sys.handle_click(tutorials, getattr(event, "pos", (0, 0))):
                    pass
                elif map_sys.handle_map_event(discovery, event, map_ui, astronaut, WORLD_W, WORLD_H):
                    pass

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if tut_sys.handle_click(tutorials, pos):
                    continue
                if inventory["open"]:
                    if inv_sys.handle_inventory_click(inventory, pos):
                        continue
                if journal["open"]:
                    continue
                if map_open and current_screen == SCREEN_BASE:
                    continue

                if current_screen == SCREEN_TITLE:
                    if title_hit.get("continue") and title_hit["continue"].collidepoint(pos):
                        if has_campaign_save and not recovery_info:
                            current_screen = SCREEN_BRIEFING
                    elif title_hit.get("completed") and title_hit["completed"].collidepoint(pos):
                        current_screen = SCREEN_FINAL_REPORT
                    elif title_hit.get("final") and title_hit["final"].collidepoint(pos):
                        current_screen = SCREEN_FINAL_REPORT
                    elif title_hit.get("records") and title_hit["records"].collidepoint(pos):
                        current_screen = SCREEN_RECORDS
                    elif title_hit.get("new") and title_hit["new"].collidepoint(pos):
                        current_screen = SCREEN_NEW_CAMPAIGN
                    elif title_hit.get("quit") and title_hit["quit"].collidepoint(pos):
                        persist()
                        running = False

                elif current_screen == SCREEN_NEW_CAMPAIGN:
                    if newcamp_hit.get("cancel") and newcamp_hit["cancel"].collidepoint(pos):
                        current_screen = SCREEN_TITLE
                    elif newcamp_hit.get("confirm") and newcamp_hit["confirm"].collidepoint(pos):
                        prev = campaign if has_campaign_save else None
                        data = savegame.archive_and_start_new(prev)
                        apply_loaded_campaign(data, reset_world=True)
                        campaign_inventory = inventory
                        recovery_info = None
                        current_screen = SCREEN_BRIEFING

                elif current_screen == SCREEN_RECORDS:
                    if records_hit.get("close") and records_hit["close"].collidepoint(pos):
                        current_screen = SCREEN_TITLE

                elif current_screen == SCREEN_MISSION_PREP:
                    if prep_hit.get("close") and prep_hit["close"].collidepoint(pos):
                        return_to_colony()
                    elif prep_hit.get("can_start") and prep_hit.get("start") and prep_hit["start"].collidepoint(pos):
                        begin_mission_challenge(prep_mission_id, pending_station_screen)

                elif current_screen == SCREEN_BRIEFING and continue_button.collidepoint(pos):
                    if not has_campaign_save:
                        has_campaign_save = True
                        campaign["campaign_started"] = True
                        cache_sys.ensure_campaign_caches(campaign)
                        cache_sys.refresh_colony_supplies(colony, campaign)
                        persist()
                    spawn = colony["spawn"]
                    if campaign.get("current_player_position"):
                        try:
                            spawn = (
                                float(campaign["current_player_position"][0]),
                                float(campaign["current_player_position"][1]),
                            )
                        except (TypeError, ValueError, IndexError):
                            spawn = colony["spawn"]
                    astronaut = player_sys.make_astronaut(spawn)
                    camera = cam_sys.make_camera(astronaut, WIDTH, HEIGHT)
                    cam_sys.clamp_camera(camera, WORLD_W, WORLD_H)
                    saved_base_pos = None
                    paused = False
                    current_screen = SCREEN_BASE

                elif current_screen == SCREEN_CH1_DIAG:
                    nxt = ch1mod.handle_diagnose_event(ch1, event, ch1_diag_ui, journal)
                    if nxt == "assemble":
                        current_screen = SCREEN_CH1_ASSEMBLE

                elif current_screen == SCREEN_CH1_RADAR:
                    next_phase = ch1mod.handle_radar_event(ch1, event, radar_ui)
                    if next_phase == "briefing":
                        current_screen = SCREEN_CH1_BRIEF
                    elif next_phase == "align":
                        # Legacy path — still go through briefing
                        current_screen = SCREEN_CH1_BRIEF

                elif current_screen == SCREEN_CH1_BRIEF:
                    if brief_hit.get("practice") and brief_hit["practice"].collidepoint(pos):
                        atut.reset_practice(ch1)
                        current_screen = SCREEN_CH1_PRACTICE

                elif current_screen == SCREEN_CH1_PRACTICE:
                    if align_ui.get("left") and align_ui["left"].collidepoint(pos):
                        rotate_antenna(ch1, -1)
                    elif align_ui.get("right") and align_ui["right"].collidepoint(pos):
                        rotate_antenna(ch1, 1)
                    elif align_ui.get("repeat") and align_ui["repeat"].width > 0 and align_ui["repeat"].collidepoint(pos):
                        atut.reset_practice(ch1)
                    elif align_ui.get("start_mission") and align_ui["start_mission"].width > 0 and align_ui["start_mission"].collidepoint(pos):
                        current_screen = SCREEN_CH1_READY

                elif current_screen == SCREEN_CH1_READY:
                    if ready_hit.get("start") and ready_hit["start"].collidepoint(pos):
                        atut.begin_timed_mission(ch1)
                        current_screen = SCREEN_CH1_ALIGN
                    elif ready_hit.get("practice") and ready_hit["practice"].collidepoint(pos):
                        atut.reset_practice(ch1)
                        current_screen = SCREEN_CH1_PRACTICE

                elif current_screen == SCREEN_CH1_ALIGN:
                    if align_ui["left"].collidepoint(pos):
                        rotate_antenna(ch1, -1)
                    elif align_ui["right"].collidepoint(pos):
                        rotate_antenna(ch1, 1)

                elif current_screen == SCREEN_CH1_COMPLETE and return_button.collidepoint(pos):
                    if campaign.get("last_debrief_mission") == "mission_1" and replay_ctx is None:
                        debrief_mission_id = "mission_1"
                        current_screen = SCREEN_DEBRIEF
                    else:
                        return_to_colony()

                elif current_screen == SCREEN_CH1_TIMEOUT and retry_button.collidepoint(pos):
                    if camp.is_completed(campaign, "mission_1"):
                        report_mission_id = "mission_1"
                        current_screen = SCREEN_MISSION_REPORT
                    else:
                        mats.release_all_reserved(inventory["stock"])
                        # Retry returns to briefing — materials already committed only if assembly passed
                        ch1["timer_running"] = False
                        ch1["connection_restored"] = False
                        ch1["points_awarded"] = False
                        ch1["packets"] = 0
                        current_screen = SCREEN_CH1_BRIEF

                elif current_screen == SCREEN_CH2_INTRO and ch2_intro_start.collidepoint(pos):
                    current_screen = SCREEN_CH2_WIRE

                elif current_screen == SCREEN_CH2_WIRE:
                    if ch2.get("circuit_ok") and ch2_wire_ui["continue"].collidepoint(pos):
                        current_screen = SCREEN_CH2_POWER
                    elif ch2_wire_ui.get("ports"):
                        ch2mod.handle_wire_event(ch2, event, ch2_wire_ui, inventory)

                elif current_screen == SCREEN_CH2_POWER and not ch2["completed"]:
                    if "confirm" in ch2_power_ui and ch2_power_ui["confirm"].collidepoint(pos):
                        if ch2_power_ok(ch2):
                            ch2["confirmed_alloc"] = True
                    else:
                        for key, pair in ch2_power_ui.items():
                            if key == "confirm":
                                continue
                            if pair["minus"].collidepoint(pos):
                                ch2_change_power(ch2, key, -10)
                            elif pair["plus"].collidepoint(pos):
                                ch2_change_power(ch2, key, 10)

                elif current_screen == SCREEN_CH2_COMPLETE and return_button.collidepoint(pos):
                    if campaign.get("last_debrief_mission") == "mission_2" and replay_ctx is None:
                        debrief_mission_id = "mission_2"
                        current_screen = SCREEN_DEBRIEF
                    else:
                        return_to_colony()

                elif current_screen == SCREEN_CH2_TIMEOUT:
                    if ch2_timeout_ui["retry"].collidepoint(pos):
                        if camp.is_completed(campaign, "mission_2"):
                            report_mission_id = "mission_2"
                            current_screen = SCREEN_MISSION_REPORT
                        else:
                            mats.release_all_reserved(inventory["stock"])
                            ch2 = make_challenge2_state()
                            current_screen = SCREEN_CH2_INTRO
                    elif ch2_timeout_ui["base"].collidepoint(pos):
                        return_to_colony()

                elif current_screen == SCREEN_CH3_INTRO and ch3_intro_start.collidepoint(pos):
                    ch3["time_left"] = float(CH3_TIME_LIMIT)
                    apply_ch3_scan_bonus()
                    current_screen = SCREEN_CH3_SCAN

                elif current_screen == SCREEN_CH3_SCAN:
                    if ch3["phase"] == "ready" and ch3_scan_ui["scan_button"].collidepoint(pos):
                        ch3["phase"] = "scanning"
                        ch3["scan_angle"] = 0.0
                        ch3["scan_progress"] = 0.0
                        ch3["hint"] = ""
                    elif ch3["found"] and ch3_scan_ui["continue"].collidepoint(pos):
                        current_screen = SCREEN_CH3_DIAG
                    elif ch3["phase"] == "results" and not ch3["found"]:
                        for cell_name, rect in ch3_scan_ui["cells"].items():
                            if rect.collidepoint(pos):
                                ch3["selected_cell"] = cell_name
                                if cell_name == CH3_CORRECT_CELL:
                                    ch3["found"] = True
                                    ch3["hint"] = "Strong rover signal confirmed in B2."
                                    ch3["penalty_flash"] = 0.0
                                else:
                                    ch3["hint"] = (
                                        f"{cell_name} is not strongest. Look for Strong (B2)."
                                    )
                                    ch3["time_left"] = max(0.0, ch3["time_left"] - CH3_WRONG_PENALTY)
                                    ch3["penalty_flash"] = 1.6
                                break
                    elif ch3["phase"] == "results" or ch3["found"]:
                        for cell_name, rect in ch3_scan_ui["cells"].items():
                            if rect.collidepoint(pos):
                                ch3["selected_cell"] = cell_name
                                break

                elif current_screen == SCREEN_CH3_DIAG:
                    nxt = ch3mod.handle_diagnose_event(ch3, event, ch3_diag_ui, journal)
                    if nxt == "repair":
                        current_screen = SCREEN_CH3_REPAIR

                elif current_screen == SCREEN_CH3_REPAIR:
                    nxt = ch3mod.handle_repair_event(ch3, event, ch3_repair_ui, inventory)
                    if nxt == "route":
                        current_screen = SCREEN_CH3_ROUTE

                elif current_screen == SCREEN_CH3_ROUTE:
                    nxt = ch3mod.handle_route_event(ch3, event, ch3_route_ui)
                    if nxt == "drive":
                        current_screen = SCREEN_CH3_DRIVE

                elif current_screen == SCREEN_CH3_COMPLETE and return_button.collidepoint(pos):
                    if campaign.get("last_debrief_mission") == "mission_3" and replay_ctx is None:
                        debrief_mission_id = "mission_3"
                        current_screen = SCREEN_DEBRIEF
                    else:
                        return_to_colony()

                elif current_screen == SCREEN_DEBRIEF:
                    if debrief_hit.get("close") and debrief_hit["close"].collidepoint(pos):
                        campaign["last_debrief_mission"] = None
                        persist()
                        return_to_colony()

                elif current_screen == SCREEN_OUTPOST:
                    close, msg = outpost_ui.handle_click(campaign, outpost_hit, pos)
                    if msg:
                        notify_sys.push(notifier, msg, "info")
                        persist()
                    if close:
                        return_to_colony()

                elif current_screen == SCREEN_CH3_TIMEOUT:
                    if ch3_timeout_ui["retry"].collidepoint(pos):
                        if camp.is_completed(campaign, "mission_3"):
                            report_mission_id = "mission_3"
                            current_screen = SCREEN_MISSION_REPORT
                        else:
                            mats.release_all_reserved(inventory["stock"])
                            ch3 = make_challenge3_state()
                            apply_ch3_scan_bonus()
                            current_screen = SCREEN_CH3_INTRO
                    elif ch3_timeout_ui["base"].collidepoint(pos):
                        return_to_colony()

                elif current_screen == SCREEN_RESEARCH:
                    if research_term.handle_event(campaign, inventory, event, research_ui, research_hit):
                        return_to_colony()
                    else:
                        persist()

                elif current_screen == SCREEN_SHOP:
                    if shop_hit.get("close") and shop_hit["close"].collidepoint(pos):
                        shop_ui["selected"] = None
                        return_to_colony()
                    else:
                        selected_row = False
                        for mid, rect in (shop_hit.get("rows") or {}).items():
                            if rect.collidepoint(pos):
                                shop_ui["selected"] = mid
                                selected_row = True
                                break
                        if not selected_row:
                            for mid, rect in (shop_hit.get("buy") or {}).items():
                                if rect.collidepoint(pos):
                                    ok, msg = proc.purchase(campaign, inventory, mid, 1)
                                    notify_sys.push(
                                        notifier, msg, "success" if ok else "warn"
                                    )
                                    persist()
                                    break

                elif current_screen == SCREEN_DASHBOARD:
                    if dash_hit.get("close") and dash_hit["close"].collidepoint(pos):
                        return_to_colony()
                    elif dash_hit.get("research") and dash_hit["research"].collidepoint(pos):
                        current_screen = SCREEN_RESEARCH
                    elif dash_hit.get("shop") and dash_hit["shop"].collidepoint(pos):
                        shop_ui["selected"] = None
                        current_screen = SCREEN_SHOP
                    elif dash_hit.get("outpost") and dash_hit["outpost"].collidepoint(pos):
                        outpost_sys.ensure_outpost(campaign)
                        current_screen = SCREEN_OUTPOST
                    elif dash_hit.get("records") and dash_hit["records"].collidepoint(pos):
                        current_screen = SCREEN_RECORDS
                    elif dash_hit.get("final") and dash_hit["final"].collidepoint(pos):
                        current_screen = SCREEN_FINAL_REPORT
                    elif dash_hit.get("new") and dash_hit["new"].collidepoint(pos):
                        current_screen = SCREEN_NEW_CAMPAIGN

                elif current_screen == SCREEN_MISSION_REPORT:
                    if report_hit.get("replay") and report_hit["replay"].collidepoint(pos):
                        start_replay(report_mission_id)
                    elif report_hit.get("close") and report_hit["close"].collidepoint(pos):
                        return_to_colony()

                elif current_screen == SCREEN_FINAL_REPORT:
                    if report_hit.get("new") and report_hit["new"].collidepoint(pos):
                        current_screen = SCREEN_NEW_CAMPAIGN
                    elif report_hit.get("close") and report_hit["close"].collidepoint(pos):
                        if has_campaign_save:
                            return_to_colony()
                        else:
                            current_screen = SCREEN_TITLE

                elif current_screen == SCREEN_LOCKED:
                    if locked_hit.get("close") and locked_hit["close"].collidepoint(pos):
                        return_to_colony()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                if current_screen == SCREEN_CH3_REPAIR and ch3_repair_ui:
                    ch3mod.handle_repair_event(ch3, event, ch3_repair_ui, inventory)

        # ---- update ----
        if has_campaign_save and replay_ctx is None:
            campaign["total_play_time"] = float(campaign.get("total_play_time", 0.0)) + max(0.0, dt)
            # Greenhouse grows slowly while exploring / in outpost view
            if current_screen in (SCREEN_BASE, SCREEN_OUTPOST):
                outpost_sys.tick_greenhouse(outpost_sys.ensure_outpost(campaign), dt)
        update_dust_particles(dust_particles)
        env_time += dt
        # Gentle sideways drift for mountain layers (not gameplay)
        parallax_offset = math.sin(env_time * 0.12) * 16.0

        # Base exploration: move astronaut + camera (never during CH3 drive)
        inv_sys.update_inventory(inventory, dt)
        # Bridge legacy inventory toasts into the notification queue once
        if inventory.get("toast"):
            notify_sys.push(notifier, inventory["toast"], "success")
            inventory["toast"] = ""
            inventory["toast_timer"] = 0.0
        notify_sys.update(notifier, dt)
        wind_sys.update_wind(wind, dt)
        scanner_sys.update(field_scanner, dt)
        if current_screen == SCREEN_BASE and not paused and not (
            inventory["open"] or journal["open"] or map_open
        ):
            tprops = terrain_sys.terrain_props(terrain_map, astronaut["x"], astronaut["y"])
            zone_name = colony_sys.zone_at(colony, astronaut["x"], astronaut["y"])
            # Fog of war + landmark discovery
            map_sys.reveal_around(discovery, astronaut["x"], astronaut["y"], radius=200)
            for zone in colony["zones"]:
                if zone["id"] != "outer" and zone["rect"].collidepoint(int(astronaut["x"]), int(astronaut["y"])):
                    map_sys.visit_zone(discovery, zone["id"])
            scanner_sys.try_identify_nearby(astronaut, colony, discovery, radius=64)
            exposed = zone_name == "Outer Mars Terrain"
            wfx, wfy = wind_sys.wind_force(wind, exposed=exposed)

            def _on_bump():
                cam_sys.add_shake(camera, 0.12, 2.8)
                audio_fx.play("bump", 0.3, cooldown=0.2)

            def _on_step(x, y, running):
                if tprops.get("name") == "Soft sand" or running:
                    particle_sys.emit_footstep(fx, x, y, running)
                audio_fx.play("step", 0.18 if not running else 0.28, cooldown=0.15)

            player_sys.move_astronaut(
                astronaut,
                keys,
                colony["colliders"],
                dt,
                WORLD_W,
                WORLD_H,
                terrain_props=tprops,
                wind_accel=(wfx, wfy),
                on_bump=_on_bump,
                on_step=_on_step,
            )
            cam_sys.update_camera(camera, astronaut, dt, WORLD_W, WORLD_H)
            particle_sys.update(fx, dt, wind=wind)
            active_target = interactions.nearest_interactable(
                astronaut, colony["interactables"]
            )
            # Online antenna signal motes
            if communication_status == "ONLINE":
                _signal_t += dt
                if _signal_t > 0.7:
                    _signal_t = 0.0
                    ax, ay = colony["antenna_pos"]
                    particle_sys.emit_signal(fx, ax + 20, ay)
        elif current_screen == SCREEN_BASE:
            particle_sys.update(fx, dt, wind=wind)
            cam_sys.update_camera(camera, astronaut, dt, WORLD_W, WORLD_H)
            active_target = interactions.nearest_interactable(
                astronaut, colony["interactables"]
            )
        else:
            active_target = None

        # Dynamic guiding arrow — same objective as map / minimap
        if current_screen == SCREEN_BASE:
            guide_obj = guide_sys.resolve_objective(
                campaign, inventory, colony, discovery, current_screen=current_screen
            )
            guide_sys.update(
                guidance, dt, astronaut, guide_obj, colliders=colony.get("colliders", [])
            )
        else:
            guide_obj = guidance.get("objective")

        # Challenge timers — CH1 countdown only during confirmed timed calibration
        if (
            current_screen in CH1_TIMED
            and ch1.get("timer_running")
            and not ch1["connection_restored"]
        ):
            ch1["time_left"] -= dt
            if ch1["time_left"] <= 0:
                ch1["time_left"] = 0
                ch1["timer_running"] = False
                current_screen = SCREEN_CH1_TIMEOUT

        if current_screen in CH2_ACTIVE and not ch2["completed"]:
            ch2["time_left"] -= dt
            if ch2["time_left"] <= 0:
                ch2["time_left"] = 0
                current_screen = SCREEN_CH2_TIMEOUT

        if current_screen in CH3_ACTIVE and not ch3["rescued"]:
            ch3["time_left"] -= dt
            if ch3["time_left"] <= 0:
                ch3["time_left"] = 0
                current_screen = SCREEN_CH3_TIMEOUT

        # Challenge 2 circuit + power board
        if current_screen == SCREEN_CH2_WIRE:
            ch2mod.update(ch2, dt, active=False)
        if current_screen == SCREEN_CH2_POWER:
            was_done = ch2["completed"]
            ch2mod.update(ch2, dt, active=True)
            if ch2["completed"] and not was_done:
                if not ch2["points_awarded"]:
                    ch2["points_awarded"] = True
                    bonuses = ch2mod.allocation_bonuses(ch2)
                    award_mission_if_campaign(
                        "mission_2",
                        {
                            "time_left": int(ch2.get("finish_time_left", 0)),
                            "summary": "Power circuit restored; allocation confirmed.",
                            "allocation_bonuses": bonuses,
                            "freshness": int(ch2.get("food_freshness", 0)),
                            "power_allocation": {
                                "life": int(ch2.get("life", 20)),
                                "food": int(ch2.get("food", 20)),
                                "comms": int(ch2.get("comms", 20)),
                            },
                        },
                    )
            if ch2["completed"]:
                ch2["complete_delay"] -= dt
                if ch2["complete_delay"] <= 0:
                    current_screen = SCREEN_CH2_COMPLETE

        # Challenge 1
        if current_screen == SCREEN_CH1_RADAR:
            ch1mod.update(ch1, dt, active_radar=True, active_align=False)
        if current_screen == SCREEN_CH1_PRACTICE:
            ch1mod.update(ch1, dt, active_radar=False, active_align=True)
        if current_screen == SCREEN_CH1_ALIGN:
            was_restored = ch1["connection_restored"]
            ch1mod.update(ch1, dt, active_radar=False, active_align=True)
            if ch1["connection_restored"] and not was_restored:
                if not ch1["points_awarded"] and ch1.get("align_mode") == "timed":
                    ch1["points_awarded"] = True
                    award_mission_if_campaign(
                        "mission_1",
                        {
                            "time_left": int(ch1.get("finish_time_left", 0)),
                            "summary": "SAT-02 link restored after repair + packets.",
                            "debrief": (
                                "Antenna pointing must match the satellite bearing. "
                                "A stable radio link needs the dish inside a usable alignment window."
                            ),
                        },
                    )
            if ch1["connection_restored"] and ch1["restore_delay"] <= 0:
                current_screen = SCREEN_CH1_COMPLETE

        if current_screen == SCREEN_CH3_SCAN:
            ch3mod.update_scan(ch3, dt)

        if current_screen == SCREEN_CH3_DRIVE:
            update_ch3_drive(ch3, dt, keys)
            if ch3["rescued"]:
                ch3["complete_delay"] -= dt
                if ch3["complete_delay"] <= 0:
                    current_screen = SCREEN_CH3_COMPLETE

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
                fx,
                parallax_offset,
                status_pack,
                near_id=(active_target["id"] if active_target else None),
                draw_fn_dust=particle_sys.draw,
                astronaut=astronaut,
                draw_astronaut_fn=_draw_astro,
                lighting_fn=light_sys.draw_post,
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
            brand = fonts["title"].render("MARS MISSION", True, chal_ui.C_MARS)
            screen.blit(brand, brand.get_rect(center=(WIDTH // 2, 180)))
            sub = fonts["body"].render("Restore · Recharge · Rescue", True, chal_ui.C_TEXT)
            screen.blit(sub, sub.get_rect(center=(WIDTH // 2, 220)))
            tip = fonts["small"].render("A dust-stormed research colony awaits.", True, chal_ui.C_MUTED)
            screen.blit(tip, tip.get_rect(center=(WIDTH // 2, 250)))
            if has_campaign_save and not recovery_info:
                seed_tip = fonts["small"].render(
                    f"Save found · seed {campaign.get('campaign_seed')} · score {campaign.get('mission_score', 0)}",
                    True,
                    chal_ui.C_SIGNAL,
                )
                screen.blit(seed_tip, seed_tip.get_rect(center=(WIDTH // 2, 280)))
            title_hit = camp_ui.draw_title_menu(
                screen, fonts, mouse_pos, has_campaign_save, campaign if has_campaign_save else None, recovery_info
            )

        elif current_screen == SCREEN_NEW_CAMPAIGN:
            newcamp_hit = camp_ui.draw_new_campaign_confirm(screen, fonts, mouse_pos)

        elif current_screen == SCREEN_RECORDS:
            records_hit = camp_ui.draw_mission_records(
                screen, fonts, mouse_pos, campaign if has_campaign_save else None
            )

        elif current_screen == SCREEN_MISSION_PREP:
            hud()
            prep_hit = camp_ui.draw_mission_prep(
                screen, fonts, mouse_pos, campaign, inventory, prep_mission_id
            )

        elif current_screen == SCREEN_BRIEFING:
            hud()
            continue_button = draw_briefing_panel(screen, fonts, mouse_pos)

        elif current_screen == SCREEN_BASE:
            prompt = active_target["prompt"] if active_target else ""
            zone_name = colony_sys.zone_at(colony, astronaut["x"], astronaut["y"])
            guide_obj = guidance.get("objective")
            objective = guide_sys.objective_label(
                guide_obj,
                colony_sys.current_objective(
                    communication_status, power_status, food_status, rover_status
                ),
            )
            mission_hint = None
            if communication_status != "ONLINE":
                mission_hint = "ch1"
            elif power_status != "ONLINE" or food_status != "SAFE":
                mission_hint = "ch2"
            elif rover_status != "RESCUED":
                mission_hint = "ch3"
            # World-space arrow under HUD overlays
            guide_sys.draw_world_arrow(screen, fonts, guidance, astronaut, camera)
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
                discovery=discovery,
                inventory=inventory,
                mission_hint=mission_hint,
                guide_obj=guide_obj,
            )
            notify_sys.draw(screen, fonts, notifier)
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
                inventory=inventory,
                progression=progression,
            )
            map_ui = map_sys.draw_full_map(
                screen, fonts, astronaut, colony, WORLD_W, WORLD_H, map_open,
                discovery=discovery, mouse_pos=mouse_pos, objective=objective,
                guide_obj=guide_obj,
            )
            scanner_sys.draw_overlay(screen, fonts, field_scanner, astronaut, camera)
            tut_sys.draw(screen, fonts, tutorials, mouse_pos)

        elif current_screen == SCREEN_CH1_DIAG:
            hud()
            # Timer starts only after Calibration Ready confirmation
            ch1_diag_ui = ch1mod.draw_diagnose(screen, fonts, mouse_pos, ch1, journal)

        elif current_screen == SCREEN_CH1_ASSEMBLE:
            hud()
            ch1_assemble_ui = ch1mod.draw_assemble(screen, fonts, mouse_pos, ch1, inventory)
            tut_sys.trigger(tutorials, "assembly")

        elif current_screen == SCREEN_CH1_RADAR:
            hud()
            # No mission countdown during radar investigation
            radar_ui = draw_radar_screen(screen, fonts, mouse_pos, ch1)

        elif current_screen == SCREEN_CH1_BRIEF:
            hud()
            brief_hit = atut.draw_briefing(screen, fonts, mouse_pos)

        elif current_screen == SCREEN_CH1_PRACTICE:
            hud()
            align_ui = atut.draw_practice(screen, fonts, mouse_pos, ch1)

        elif current_screen == SCREEN_CH1_READY:
            hud()
            ready_hit = atut.draw_ready(screen, fonts, mouse_pos)

        elif current_screen == SCREEN_CH1_ALIGN:
            hud()
            if ch1.get("timer_running"):
                draw_timer(screen, fonts, ch1["time_left"])
            align_ui = draw_alignment_screen(screen, fonts, mouse_pos, ch1)
            atut.draw_control_reference(screen, fonts, mouse_pos)

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

        elif current_screen == SCREEN_CH3_DIAG:
            hud()
            draw_timer(screen, fonts, ch3["time_left"])
            ch3_diag_ui = ch3mod.draw_diagnose(screen, fonts, mouse_pos, ch3)

        elif current_screen == SCREEN_CH3_REPAIR:
            hud()
            draw_timer(screen, fonts, ch3["time_left"])
            ch3_repair_ui = ch3mod.draw_repair(screen, fonts, mouse_pos, ch3, inventory)

        elif current_screen == SCREEN_CH3_ROUTE:
            hud()
            draw_timer(screen, fonts, ch3["time_left"])
            ch3_route_ui = ch3mod.draw_route(screen, fonts, mouse_pos, ch3)

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

        elif current_screen == SCREEN_RESEARCH:
            hud()
            research_hit = research_term.draw(screen, fonts, mouse_pos, campaign, research_ui)

        elif current_screen == SCREEN_SHOP:
            hud()
            shop_hit = proc.draw_shop(
                screen, fonts, mouse_pos, campaign, inventory, ui_state=shop_ui
            )

        elif current_screen == SCREEN_DASHBOARD:
            hud()
            dash_hit = camp_ui.draw_dashboard(screen, fonts, mouse_pos, campaign, inventory)

        elif current_screen == SCREEN_OUTPOST:
            hud()
            outpost_hit = outpost_ui.draw_dashboard(screen, fonts, mouse_pos, campaign)

        elif current_screen == SCREEN_DEBRIEF:
            hud()
            debrief_hit = debrief_sys.draw_debrief(
                screen, fonts, mouse_pos, campaign, debrief_mission_id
            )

        elif current_screen == SCREEN_MISSION_REPORT:
            hud()
            report_hit = camp_ui.draw_mission_report(
                screen, fonts, mouse_pos, campaign, report_mission_id
            )

        elif current_screen == SCREEN_FINAL_REPORT:
            hud()
            report_hit = camp_ui.draw_final_report(screen, fonts, mouse_pos, campaign)

        elif current_screen == SCREEN_LOCKED:
            hud()
            locked_hit = camp_ui.draw_locked_notice(screen, fonts, mouse_pos, locked_reason)

        if replay_ctx is not None and current_screen not in (SCREEN_TITLE, SCREEN_BRIEFING, SCREEN_NEW_CAMPAIGN):
            camp_ui.draw_replay_banner(screen, fonts)

        # Challenge overlays for inventory / journal / tips
        if current_screen != SCREEN_BASE:
            if inventory["open"]:
                inv_sys.draw_inventory(screen, fonts, inventory, mouse_pos)
            if journal["open"]:
                journal_sys.draw_journal(
                    screen, fonts, journal,
                    communication_status, power_status, food_status, rover_status,
                    score, inventory["items"], inventory=inventory, progression=progression,
                )
            tut_sys.draw(screen, fonts, tutorials, mouse_pos)
            notify_sys.draw(screen, fonts, notifier)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


def _write_crash_log(exc: BaseException):
    """Write fatal errors next to the exe or into the user save dir (never into bundled assets)."""
    from pathlib import Path

    text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    candidates = []
    try:
        candidates.append(Path(savegame.default_user_save_dir()) / "crash.log")
    except Exception:
        pass
    candidates.append(Path(rpaths.executable_dir()) / "crash.log")
    for path in candidates:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            return path
        except OSError:
            continue
    return None


if __name__ == "__main__":
    try:
        main()
    except Exception as _fatal:
        log_path = _write_crash_log(_fatal)
        # Keep a console message for DEBUG builds; RELEASE still writes crash.log
        msg = f"MARSMISSION crashed. Details: {log_path or '(could not write crash.log)'}\n{_fatal}"
        print(msg)
        try:
            import tkinter
            from tkinter import messagebox

            root = tkinter.Tk()
            root.withdraw()
            messagebox.showerror("MARSMISSION", msg)
            root.destroy()
        except Exception:
            pass
        raise SystemExit(1) from _fatal
