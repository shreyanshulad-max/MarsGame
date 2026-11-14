"""Detailed top-down rover drawing with cached rotations and procedural fallback."""

from __future__ import annotations

import math

import pygame

from systems import runtime_paths as rpaths

ROOT = rpaths.resource_root()
ASSET_ROVER = rpaths.assets_dir() / "vehicles" / "rover.png"
ASSET_ROVER_TOP = rpaths.assets_dir() / "vehicles" / "rover" / "rover_top.png"

_BASE_SURF: pygame.Surface | None = None
_ROT_CACHE: dict[int, pygame.Surface] = {}
_SHADOW: pygame.Surface | None = None
_MISSING_LOGGED = False
ANGLE_BUCKET = 3  # degrees


def _log_missing(path: Path) -> None:
    global _MISSING_LOGGED
    if not _MISSING_LOGGED:
        print(f"[rover_renderer] Using procedural rover (missing asset: {path})")
        _MISSING_LOGGED = True


def _build_procedural() -> pygame.Surface:
    """Detailed six-wheel exploration rover facing +X (right)."""
    s = pygame.Surface((120, 72), pygame.SRCALPHA)
    # Shadow baked lightly under body
    pygame.draw.ellipse(s, (0, 0, 0, 55), (12, 48, 96, 20))
    # Suspension rails
    pygame.draw.line(s, (70, 70, 78), (22, 28), (98, 28), 3)
    pygame.draw.line(s, (70, 70, 78), (22, 44), (98, 44), 3)
    # Six wheels
    for wx in (24, 60, 96):
        for wy in (18, 54):
            pygame.draw.circle(s, (32, 32, 38), (wx, wy), 11)
            pygame.draw.circle(s, (90, 90, 98), (wx, wy), 11, 2)
            pygame.draw.circle(s, (160, 160, 170), (wx, wy), 3)
    # Chassis
    body = pygame.Rect(28, 22, 70, 28)
    pygame.draw.rect(s, (210, 115, 55), body, border_radius=6)
    pygame.draw.rect(s, (255, 180, 100), body, 2, border_radius=6)
    # Deck instruments
    pygame.draw.rect(s, (90, 100, 110), (40, 28, 18, 10), border_radius=2)
    pygame.draw.rect(s, (70, 90, 100), (62, 30, 22, 8), border_radius=2)
    # Mast + camera
    pygame.draw.line(s, (200, 200, 210), (78, 24), (78, 8), 3)
    pygame.draw.circle(s, (230, 230, 240), (78, 6), 5)
    pygame.draw.circle(s, (40, 120, 200), (78, 6), 2)
    # High-gain antenna
    pygame.draw.line(s, (180, 180, 190), (48, 24), (40, 4), 2)
    pygame.draw.circle(s, (220, 220, 230), (40, 4), 6, 1)
    # Front lights (+X)
    pygame.draw.circle(s, (255, 240, 180), (100, 30), 3)
    pygame.draw.circle(s, (255, 240, 180), (100, 42), 3)
    # Rear lights
    pygame.draw.circle(s, (220, 60, 50), (30, 30), 2)
    pygame.draw.circle(s, (220, 60, 50), (30, 42), 2)
    return s


def get_base_surface() -> pygame.Surface:
    global _BASE_SURF
    if _BASE_SURF is not None:
        return _BASE_SURF
    for path in (ASSET_ROVER_TOP, ASSET_ROVER):
        if path.is_file():
            try:
                img = pygame.image.load(str(path)).convert_alpha()
                # Normalize to ~110px long facing right
                w, h = img.get_size()
                scale = 110 / max(w, 1)
                _BASE_SURF = pygame.transform.smoothscale(
                    img, (max(1, int(w * scale)), max(1, int(h * scale)))
                )
                return _BASE_SURF
            except pygame.error:
                _log_missing(path)
    _log_missing(ASSET_ROVER_TOP)
    _BASE_SURF = _build_procedural()
    return _BASE_SURF


def get_shadow() -> pygame.Surface:
    global _SHADOW
    if _SHADOW is None:
        _SHADOW = pygame.Surface((100, 36), pygame.SRCALPHA)
        pygame.draw.ellipse(_SHADOW, (0, 0, 0, 70), _SHADOW.get_rect())
    return _SHADOW


def rotated(heading: float) -> pygame.Surface:
    """Cached rotation; heading 0 = facing +X."""
    bucket = int(round(heading / ANGLE_BUCKET) * ANGLE_BUCKET) % 360
    cached = _ROT_CACHE.get(bucket)
    if cached is not None:
        return cached
    base = get_base_surface()
    # pygame rotates counter-clockwise; our heading increases clockwise from +X
    surf = pygame.transform.rotate(base, -bucket)
    _ROT_CACHE[bucket] = surf
    if len(_ROT_CACHE) > 140:
        # Drop arbitrary old entries
        for k in list(_ROT_CACHE.keys())[:40]:
            _ROT_CACHE.pop(k, None)
    return surf


def draw_rover(
    surface: pygame.Surface,
    x: float,
    y: float,
    heading: float,
    wheel_spin: float = 0.0,
    chassis_bob: float = 0.0,
    headlights: bool = False,
    stranded: bool = False,
    camera: tuple[float, float] = (0.0, 0.0),
) -> None:
    cam_x, cam_y = camera
    sx = x - cam_x
    sy = y - cam_y + chassis_bob
    if stranded:
        heading = 200.0  # tilted look

    # Shadow
    sh = get_shadow()
    surface.blit(sh, sh.get_rect(center=(int(sx + 4), int(sy + 18))))

    body = rotated(heading)
    rect = body.get_rect(center=(int(sx), int(sy)))
    surface.blit(body, rect)

    # Animated wheel ticks (overlay) for motion feel
    if not stranded and abs(wheel_spin) > 0:
        rad = math.radians(heading)
        spin = math.radians(wheel_spin * 40)
        for ox, oy in ((-28, 18), (0, 18), (28, 18), (-28, -18), (0, -18), (28, -18)):
            rx = ox * math.cos(rad) - oy * math.sin(rad)
            ry = ox * math.sin(rad) + oy * math.cos(rad)
            wx, wy = int(sx + rx), int(sy + ry)
            pygame.draw.line(
                surface,
                (200, 200, 210),
                (wx, wy),
                (wx + int(math.cos(spin + rad) * 5), wy + int(math.sin(spin + rad) * 5)),
                2,
            )

    if headlights:
        rad = math.radians(heading)
        fx = sx + math.cos(rad) * 48
        fy = sy + math.sin(rad) * 48
        light = pygame.Surface((160, 100), pygame.SRCALPHA)
        pygame.draw.polygon(
            light,
            (255, 230, 160, 45),
            [(80, 50), (150, 20), (150, 80)],
        )
        # Orient light cone roughly
        rot = pygame.transform.rotate(light, -heading)
        surface.blit(rot, rot.get_rect(center=(int(fx), int(fy))))


_WORLD_SURF: pygame.Surface | None = None
_WORLD_KEY: tuple[int, int] | None = None


def _build_world_surface(world_w: int, world_h: int) -> pygame.Surface:
    from systems import rover_terrain as terrain

    # Half-res cache for speed; scaled when blitting
    scale = 0.35
    sw, sh = max(1, int(world_w * scale)), max(1, int(world_h * scale))
    surf = pygame.Surface((sw, sh))
    step = 4
    for sy in range(0, sh, step):
        for sx in range(0, sw, step):
            wx = (sx + step * 0.5) / scale
            wy = (sy + step * 0.5) / scale
            col = terrain.sample(wx, wy)["color"]
            pygame.draw.rect(surf, col, (sx, sy, step + 1, step + 1))
    return surf


def draw_world_ground(surface: pygame.Surface, camera: tuple[float, float], world_w: int, world_h: int) -> None:
    """Blit cached Mars ground for the camera window."""
    global _WORLD_SURF, _WORLD_KEY
    key = (world_w, world_h)
    if _WORLD_SURF is None or _WORLD_KEY != key:
        _WORLD_SURF = _build_world_surface(world_w, world_h)
        _WORLD_KEY = key
    cam_x, cam_y = camera
    # Map camera window onto cache
    scale_x = _WORLD_SURF.get_width() / max(1, world_w)
    scale_y = _WORLD_SURF.get_height() / max(1, world_h)
    src = pygame.Rect(
        int(cam_x * scale_x),
        int(cam_y * scale_y),
        int(1280 * scale_x),
        int(720 * scale_y),
    )
    src.clamp_ip(_WORLD_SURF.get_rect())
    view = _WORLD_SURF.subsurface(src)
    scaled = pygame.transform.scale(view, (1280, 720))
    surface.blit(scaled, (0, 0))
    if cam_y < 80:
        pygame.draw.rect(surface, (255, 170, 90), (0, 0, 1280, int(max(0, 80 - cam_y))))
