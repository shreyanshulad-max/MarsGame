"""AABB collision helpers — nearby culling + multi-axis resolve."""

from __future__ import annotations

import pygame


def feet_rect(x: float, y: float, radius: float = 13) -> pygame.Rect:
    """Player collision smaller than the visible sprite."""
    r = radius
    return pygame.Rect(int(x - r * 0.85), int(y - r * 0.25), int(r * 1.7), int(r * 1.05))


def collides_any(rect: pygame.Rect, boxes: list[pygame.Rect]) -> bool:
    for box in boxes:
        if rect.colliderect(box):
            return True
    return False


def nearby_colliders(
    x: float, y: float, boxes: list[pygame.Rect], margin: float = 200
) -> list[pygame.Rect]:
    area = pygame.Rect(int(x - margin), int(y - margin), int(margin * 2), int(margin * 2))
    return [b for b in boxes if area.colliderect(b)]


def shrink_rect(rect: pygame.Rect, pad: int = 4) -> pygame.Rect:
    """Tighten visual-sized boxes into fairer collision footprints."""
    return rect.inflate(-pad * 2, -pad * 2)
