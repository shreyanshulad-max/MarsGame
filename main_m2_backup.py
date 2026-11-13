"""
Mars Mission: Restore, Recharge & Rescue!
A beginner-friendly 2.5D Mars base game drawn only with shapes.
"""

import math
import random
import pygame

# ---- Window size and speed ----
WIDTH = 1280
HEIGHT = 720
FPS = 60

# ---- Game screens (what the player is looking at) ----
SCREEN_TITLE = "title"              # outdoor base + Start button
SCREEN_BRIEFING = "briefing"        # short mission story
SCREEN_BASE = "base"                # entered the Mars research base
SCREEN_CH1_RADAR = "ch1_radar"      # Challenge 1: scan satellites
SCREEN_CH1_ALIGN = "ch1_align"      # Challenge 1: aim the antenna
SCREEN_CH1_COMPLETE = "ch1_complete"
SCREEN_CH1_TIMEOUT = "ch1_timeout"

# ---- Challenge 1 settings ----
CH1_TIME_LIMIT = 90          # seconds on the mission timer
ANTENNA_START_ANGLE = -30    # degrees
ANTENNA_TARGET_ANGLE = 20    # degrees
ANTENNA_STEP = 5             # how far Left/Right moves the dish
CH1_POINTS = 100

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


def lerp_color(color_a, color_b, t):
    """Blend two colors. t=0 means color_a, t=1 means color_b."""
    return (
        int(color_a[0] + (color_b[0] - color_a[0]) * t),
        int(color_a[1] + (color_b[1] - color_a[1]) * t),
        int(color_a[2] + (color_b[2] - color_a[2]) * t),
    )


def draw_sky(surface):
    """Paint a dusty Mars sky with soft color bands."""
    for y in range(HEIGHT // 2 + 20):
        t = y / (HEIGHT // 2 + 20)
        if t < 0.45:
            color = lerp_color(SKY_TOP, SKY_MID, t / 0.45)
        else:
            color = lerp_color(SKY_MID, SKY_LOW, (t - 0.45) / 0.55)
        pygame.draw.line(surface, color, (0, y), (WIDTH, y))


def draw_hazy_sun(surface, cx, cy):
    """Draw a soft, hazy sun with glowing rings around it."""
    for radius, alpha in ((140, 28), (100, 40), (70, 55)):
        glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 185, 100, alpha), (radius, radius), radius)
        surface.blit(glow, (cx - radius, cy - radius))

    pygame.draw.circle(surface, SUN_GLOW, (cx, cy), 40)
    pygame.draw.circle(surface, SUN_CORE, (cx, cy), 26)


def draw_atmosphere(surface):
    """Add a soft dusty haze near the horizon for depth."""
    haze = pygame.Surface((WIDTH, 180), pygame.SRCALPHA)
    for y in range(180):
        alpha = int(70 * (y / 180))
        pygame.draw.line(haze, (255, 160, 100, alpha), (0, y), (WIDTH, y))
    surface.blit(haze, (0, HEIGHT // 2 - 120))


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


def draw_mountains(surface):
    """Draw three mountain layers so far hills look farther away."""
    mountain_ridge(
        340,
        [
            (80, 300), (160, 250), (250, 310), (340, 230), (430, 290),
            (520, 240), (610, 300), (720, 220), (830, 285), (940, 245),
            (1050, 300), (1150, 255), (1240, 310),
        ],
        MOUNTAIN_FAR,
        surface,
    )
    mountain_ridge(
        380,
        [
            (40, 340), (140, 290), (240, 350), (350, 270), (470, 340),
            (580, 285), (690, 355), (800, 275), (920, 340), (1040, 295),
            (1160, 350), (1260, 310),
        ],
        MOUNTAIN_MID,
        surface,
    )
    mountain_ridge(
        420,
        [
            (0, 390), (110, 330), (220, 400), (330, 310), (450, 385),
            (560, 325), (680, 405), (790, 320), (910, 390), (1030, 335),
            (1140, 400), (1280, 360),
        ],
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
    """Draw the floating dust on top of the scene."""
    dust_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for p in particles:
        color = (255, 200, 140, p["alpha"])
        pygame.draw.circle(dust_layer, color, (int(p["x"]), int(p["y"])), p["size"])
    surface.blit(dust_layer, (0, 0))


def draw_ground(surface, rocks, craters):
    """Draw the rocky Mars floor with shadows and craters."""
    pygame.draw.rect(surface, GROUND_LIGHT, (0, 420, WIDTH, HEIGHT - 420))

    for i in range(8):
        y = 440 + i * 35
        shade = lerp_color(GROUND_LIGHT, GROUND_DARK, i / 10)
        pygame.draw.ellipse(surface, shade, (-40 + i * 30, y, WIDTH + 80, 50))

    for crater in craters:
        x, y, r = crater["x"], crater["y"], crater["r"]
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
        pygame.draw.ellipse(surface, GROUND_SHADOW, (x + 3, y + 3, w, h // 2 + 2))
        pygame.draw.ellipse(surface, ROCK_DARK, (x, y, w, h))
        pygame.draw.ellipse(surface, ROCK_LIGHT, (x + 2, y + 1, w // 2, h // 2))


def draw_habitat(surface, x, y):
    """Draw a futuristic habitat dome with windows and an entrance."""
    pygame.draw.ellipse(surface, GROUND_SHADOW, (x - 20, y + 95, 220, 36))
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
    """Draw a tall communication antenna standing beside the habitat."""
    pygame.draw.ellipse(surface, GROUND_SHADOW, (x - 8, y + 95, 50, 16))
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
    """Draw solar panels with clear cell divisions."""
    pygame.draw.rect(surface, (90, 95, 100), (x + 20, y + 42, 8, 55))
    pygame.draw.rect(surface, (90, 95, 100), (x + 118, y + 42, 8, 55))
    pygame.draw.ellipse(surface, GROUND_SHADOW, (x + 5, y + 92, 150, 18))

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
    """Draw a Mars rover in the foreground with six visible wheels."""
    pygame.draw.ellipse(surface, GROUND_SHADOW, (x - 8, y + 34, 120, 20))

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


def draw_hud(surface, fonts, communication_status="OFFLINE", score=0):
    """Show mission title and base status (fits inside the panel)."""
    panel = pygame.Surface((430, 150), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*HUD_BG, 175), (0, 0, 430, 150), border_radius=10)
    pygame.draw.rect(panel, (255, 180, 100, 130), (0, 0, 430, 150), 2, border_radius=10)
    surface.blit(panel, (20, 18))

    title = fonts["title"].render("MARS MISSION", True, HUD_TEXT)
    surface.blit(title, (36, 28))

    # Communication color changes when the player restores the link
    if communication_status == "ONLINE":
        comm_color = HUD_OK
    else:
        comm_color = HUD_ALERT

    lines = [
        ("BASE STATUS: SYSTEMS CRITICAL", HUD_WARN),
        (f"COMMUNICATION: {communication_status}", comm_color),
        ("POWER: LOW", HUD_WARN),
        ("FOOD: AT RISK", HUD_ALERT),
    ]
    for i, (text, color) in enumerate(lines):
        label = fonts["body"].render(text, True, color)
        surface.blit(label, (36, 68 + i * 24))

    # Small score readout in the top-right of the HUD area
    if score > 0:
        score_label = fonts["small"].render(f"SCORE: {score}", True, HUD_TEXT)
        surface.blit(score_label, (320, 32))


def draw_bottom_notice(surface, fonts, message):
    """Show a short message in the bottom notification area."""
    banner = pygame.Surface((640, 56), pygame.SRCALPHA)
    pygame.draw.rect(banner, (*HUD_BG, 175), (0, 0, 640, 56), border_radius=10)
    pygame.draw.rect(banner, (255, 180, 100, 130), (0, 0, 640, 56), 2, border_radius=10)
    surface.blit(banner, (WIDTH // 2 - 320, HEIGHT - 86))

    msg = fonts["body"].render(message, True, HUD_TEXT)
    surface.blit(msg, msg.get_rect(center=(WIDTH // 2, HEIGHT - 58)))


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


def draw_world(surface, rocks, craters, dust_particles, communication_online=False):
    """Draw the outdoor Mars environment from back to front."""
    draw_sky(surface)
    draw_hazy_sun(surface, 980, 120)
    draw_mountains(surface)
    draw_atmosphere(surface)
    draw_ground(surface, rocks, craters)
    draw_habitat(surface, 500, 355)
    draw_communication_antenna(surface, 430, 360, online=communication_online)
    draw_solar_panels(surface, 740, 395)
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

    rocks, craters = make_ground_details()
    dust_particles = make_dust_particles()

    current_screen = SCREEN_TITLE
    start_button = button_rect(WIDTH // 2, 640, 300, 60)
    continue_button = pygame.Rect(0, 0, 260, 56)
    challenge1_button = button_rect(WIDTH // 2, 620, 520, 56)

    # Mission progress that lasts across screens
    communication_status = "OFFLINE"
    score = 0
    ch1 = make_challenge1_state()

    # Buttons that change each frame on challenge screens
    radar_ui = {"scan_button": pygame.Rect(0, 0, 0, 0), "sat_rects": {}}
    align_ui = {"left": pygame.Rect(0, 0, 0, 0), "right": pygame.Rect(0, 0, 0, 0)}
    return_button = pygame.Rect(0, 0, 0, 0)
    retry_button = pygame.Rect(0, 0, 0, 0)

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        dt = clock.get_time() / 1000.0  # seconds since last frame

        # ---- events ----
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

            elif event.type == pygame.KEYDOWN and current_screen == SCREEN_CH1_ALIGN:
                if event.key == pygame.K_LEFT:
                    rotate_antenna(ch1, -1)
                elif event.key == pygame.K_RIGHT:
                    rotate_antenna(ch1, 1)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if current_screen == SCREEN_TITLE and start_button.collidepoint(pos):
                    current_screen = SCREEN_BRIEFING

                elif current_screen == SCREEN_BRIEFING and continue_button.collidepoint(pos):
                    current_screen = SCREEN_BASE

                elif current_screen == SCREEN_BASE and challenge1_button.collidepoint(pos):
                    ch1 = make_challenge1_state()
                    current_screen = SCREEN_CH1_RADAR

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
                    current_screen = SCREEN_BASE

                elif current_screen == SCREEN_CH1_TIMEOUT and retry_button.collidepoint(pos):
                    ch1 = make_challenge1_state()
                    current_screen = SCREEN_CH1_RADAR

        # ---- update ----
        update_dust_particles(dust_particles)

        # Mission timer only while Challenge 1 is active (pause after success)
        if current_screen in (SCREEN_CH1_RADAR, SCREEN_CH1_ALIGN) and not ch1["connection_restored"]:
            ch1["time_left"] -= dt
            if ch1["time_left"] <= 0:
                ch1["time_left"] = 0
                current_screen = SCREEN_CH1_TIMEOUT

        # Non-blocking radar sweep animation
        if current_screen == SCREEN_CH1_RADAR and ch1["phase"] == "scanning":
            ch1["scan_angle"] = (ch1["scan_angle"] + 280 * dt) % 360
            ch1["scan_progress"] += dt / 2.2  # about 2.2 seconds to finish
            if ch1["scan_progress"] >= 1.0:
                ch1["phase"] = "results"
                ch1["scan_progress"] = 1.0

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
        draw_world(screen, rocks, craters, dust_particles, communication_online=online)

        if current_screen == SCREEN_TITLE:
            draw_hud(screen, fonts, communication_status, score)
            draw_button(screen, start_button, "START MISSION", fonts, mouse_pos)

        elif current_screen == SCREEN_BRIEFING:
            draw_hud(screen, fonts, communication_status, score)
            continue_button = draw_briefing_panel(screen, fonts, mouse_pos)

        elif current_screen == SCREEN_BASE:
            draw_hud(screen, fonts, communication_status, score)
            notice = "You are at the Mars Research Base."
            if communication_status == "ONLINE":
                notice = "Communication online! Challenge 1 complete."
            draw_bottom_notice(screen, fonts, notice)
            draw_button(
                screen,
                challenge1_button,
                "START CHALLENGE 1 — RESTORE COMMUNICATION",
                fonts,
                mouse_pos,
                font_key="button_small",
            )

        elif current_screen == SCREEN_CH1_RADAR:
            draw_hud(screen, fonts, communication_status, score)
            draw_timer(screen, fonts, ch1["time_left"])
            radar_ui = draw_radar_screen(screen, fonts, mouse_pos, ch1)

        elif current_screen == SCREEN_CH1_ALIGN:
            draw_hud(screen, fonts, communication_status, score)
            draw_timer(screen, fonts, ch1["time_left"])
            align_ui = draw_alignment_screen(screen, fonts, mouse_pos, ch1)

        elif current_screen == SCREEN_CH1_COMPLETE:
            draw_hud(screen, fonts, communication_status, score)
            return_button = draw_complete_panel(
                screen, fonts, mouse_pos, score, ch1["finish_time_left"]
            )

        elif current_screen == SCREEN_CH1_TIMEOUT:
            draw_hud(screen, fonts, communication_status, score)
            retry_button = draw_timeout_panel(screen, fonts, mouse_pos)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
