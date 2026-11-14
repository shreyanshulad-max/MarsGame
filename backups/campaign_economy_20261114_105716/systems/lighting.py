"""Cached / lightweight lighting overlays for the colony view."""

from __future__ import annotations

import math

import pygame

_VIGNETTE = None


def get_vignette(w: int, h: int) -> pygame.Surface:
    global _VIGNETTE
    key = (w, h)
    if _VIGNETTE is not None and _VIGNETTE.get_size() == key:
        return _VIGNETTE
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w // 2, h // 2
    max_r = int(math.hypot(cx, cy))
    # Cheap radial vignette via nested rects (fast enough at 720p once)
    for i in range(8):
        t = i / 8
        alpha = int(18 * t * t)
        inset = int(max_r * (1 - t) * 0.08)
        pygame.draw.rect(
            surf,
            (40, 15, 5, alpha),
            (inset, inset, w - inset * 2, h - inset * 2),
            width=max(8, 20 - i),
        )
    # Darker corners
    corner = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(0, h, 4):
        for x in range(0, w, 4):
            dx = (x - cx) / cx
            dy = (y - cy) / cy
            d = dx * dx + dy * dy
            if d > 0.85:
                a = int(min(90, (d - 0.85) * 140))
                corner.fill((30, 10, 0, a), (x, y, 4, 4))
    surf.blit(corner, (0, 0))
    _VIGNETTE = surf
    return surf


def draw_ambient(surface, strength: float = 0.12) -> None:
    """Warm Mars ambient wash (single blit)."""
    wash = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    wash.fill((255, 140, 70, int(255 * strength)))
    surface.blit(wash, (0, 0))


def draw_local_glows(surface, cam: dict, colony: dict, status: dict) -> None:
    """Point glows around key equipment — small alpha circles only."""
    layer = pygame.Surface((cam["view_w"], cam["view_h"]), pygame.SRCALPHA)

    def glow(wx, wy, radius, color, alpha):
        sx = int(wx - cam["x"])
        sy = int(wy - cam["y"])
        if sx < -radius or sy < -radius or sx > cam["view_w"] + radius or sy > cam["view_h"] + radius:
            return
        pygame.draw.circle(layer, (*color, alpha), (sx, sy), radius)

    hx, hy = colony["habitat_pos"]
    if status.get("power") == "ONLINE":
        glow(hx + 115, hy + 70, 70, (255, 220, 140), 45)
        glow(hx + 115, hy + 70, 110, (255, 180, 80), 18)
    else:
        glow(hx + 115, hy + 70, 50, (80, 60, 40), 25)

    ax, ay = colony["antenna_pos"]
    if status.get("comm") == "ONLINE":
        glow(ax + 15, ay + 5, 40, (80, 220, 140), 55)
    else:
        # Flashing warning handled in prop draw; soft red pool
        pulse = 30 + int(25 * abs(math.sin(pygame.time.get_ticks() * 0.008)))
        glow(ax + 15, ay + 5, 36, (255, 60, 50), pulse)

    sx, sy = colony["solar_pos"]
    glow(sx + 80, sy + 40, 55, (255, 210, 100), 28)

    surface.blit(layer, (0, 0))


def draw_post(surface, cam, colony, status) -> None:
    draw_local_glows(surface, cam, colony, status)
    surface.blit(get_vignette(cam["view_w"], cam["view_h"]), (0, 0))
