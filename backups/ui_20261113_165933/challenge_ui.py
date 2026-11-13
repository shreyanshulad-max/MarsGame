"""Shared sci-fi challenge UI — Mars orange / cyan / green / red theme."""

from __future__ import annotations

import math

import pygame

# Theme
C_BG = (18, 10, 8)
C_PANEL = (28, 16, 12)
C_EDGE = (255, 160, 70)
C_EDGE_DIM = (160, 90, 45)
C_TEXT = (255, 235, 210)
C_MUTED = (200, 170, 140)
C_CYAN = (80, 210, 230)
C_GREEN = (90, 220, 140)
C_RED = (255, 85, 70)
C_AMBER = (255, 190, 80)
C_BTN = (200, 95, 40)
C_BTN_HOV = (235, 130, 55)


def dim_backdrop(surface, alpha: int = 150) -> None:
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    overlay.fill((6, 3, 0, alpha))
    surface.blit(overlay, (0, 0))


def panel(surface, rect: pygame.Rect, accent=C_EDGE, fill=C_PANEL) -> None:
    pygame.draw.rect(surface, fill, rect, border_radius=14)
    pygame.draw.rect(surface, accent, rect, 2, border_radius=14)
    # Top accent bar
    bar = pygame.Rect(rect.x + 12, rect.y + 10, rect.w - 24, 3)
    pygame.draw.rect(surface, accent, bar, border_radius=2)


def header(surface, fonts, rect: pygame.Rect, title: str, subtitle: str = "") -> int:
    """Draw title block; returns y below header."""
    t = fonts["title"].render(title, True, C_TEXT)
    surface.blit(t, t.get_rect(centerx=rect.centerx, y=rect.y + 22))
    y = rect.y + 58
    if subtitle:
        s = fonts["small"].render(subtitle, True, C_AMBER)
        surface.blit(s, s.get_rect(centerx=rect.centerx, y=y))
        y += 28
    return y


def label(surface, fonts, text: str, pos, color=C_TEXT, key: str = "body") -> pygame.Rect:
    img = fonts[key].render(text, True, color)
    r = img.get_rect(topleft=pos)
    surface.blit(img, r)
    return r


def centered(surface, fonts, text: str, center, color=C_TEXT, key: str = "body") -> pygame.Rect:
    img = fonts[key].render(text, True, color)
    r = img.get_rect(center=center)
    surface.blit(img, r)
    return r


def button(surface, rect: pygame.Rect, text: str, fonts, mouse_pos, small: bool = False) -> bool:
    hovered = rect.collidepoint(mouse_pos)
    fill = C_BTN_HOV if hovered else C_BTN
    pygame.draw.rect(surface, (40, 20, 10), rect.move(0, 3), border_radius=10)
    pygame.draw.rect(surface, fill, rect, border_radius=10)
    pygame.draw.rect(surface, C_EDGE, rect, 2, border_radius=10)
    key = "button_small" if small else "button"
    img = fonts[key].render(text, True, (255, 245, 230))
    surface.blit(img, img.get_rect(center=rect.center))
    return hovered


def meter(surface, rect: pygame.Rect, value: float, maximum: float, color=C_CYAN, label_text: str = "") -> None:
    pygame.draw.rect(surface, (40, 25, 18), rect, border_radius=6)
    pygame.draw.rect(surface, C_EDGE_DIM, rect, 1, border_radius=6)
    t = 0 if maximum <= 0 else max(0.0, min(1.0, value / maximum))
    fill = pygame.Rect(rect.x + 2, rect.y + 2, int((rect.w - 4) * t), rect.h - 4)
    if fill.w > 0:
        pygame.draw.rect(surface, color, fill, border_radius=4)


def status_chip(surface, fonts, text: str, pos, ok: bool) -> None:
    color = C_GREEN if ok else C_RED
    chip = pygame.Rect(pos[0], pos[1], 160, 28)
    pygame.draw.rect(surface, (30, 18, 12), chip, border_radius=8)
    pygame.draw.rect(surface, color, chip, 2, border_radius=8)
    img = fonts["small"].render(text, True, color)
    surface.blit(img, img.get_rect(center=chip.center))


def objective_bar(surface, fonts, text: str, y: int = 16) -> None:
    w = min(900, surface.get_width() - 80)
    rect = pygame.Rect(surface.get_width() // 2 - w // 2, y, w, 36)
    pygame.draw.rect(surface, (*C_BG, ), rect, border_radius=8)
    pygame.draw.rect(surface, C_CYAN, rect, 2, border_radius=8)
    img = fonts["small"].render(text, True, C_TEXT)
    surface.blit(img, img.get_rect(center=rect.center))


def timer_badge(surface, fonts, time_left: float, width: int = 1280) -> None:
    seconds = max(0, int(math.ceil(time_left)))
    color = C_RED if seconds <= 15 else C_TEXT
    rect = pygame.Rect(width - 190, 20, 170, 44)
    pygame.draw.rect(surface, C_PANEL, rect, border_radius=8)
    pygame.draw.rect(surface, C_EDGE if seconds > 15 else C_RED, rect, 2, border_radius=8)
    img = fonts["body"].render(f"TIME {seconds:02d}s", True, color)
    surface.blit(img, img.get_rect(center=rect.center))


def result_panel(surface, fonts, mouse_pos, title: str, lines: list[str], ok: bool, btn_label: str = "CONTINUE"):
    """Success / fail style panel. Returns primary button rect."""
    dim_backdrop(surface, 170)
    box = pygame.Rect(260, 140, 760, 420)
    panel(surface, box, accent=C_GREEN if ok else C_RED)
    centered(surface, fonts, title, (box.centerx, 190), C_GREEN if ok else C_RED, "title")
    for i, line in enumerate(lines):
        centered(surface, fonts, line, (box.centerx, 250 + i * 36), C_TEXT, "body")
    btn = pygame.Rect(0, 0, 280, 54)
    btn.center = (box.centerx, 480)
    button(surface, btn, btn_label, fonts, mouse_pos)
    return btn


def dual_result_panel(surface, fonts, mouse_pos, title: str, lines: list[str], ok: bool):
    """Returns dict retry/base button rects."""
    dim_backdrop(surface, 170)
    box = pygame.Rect(240, 140, 800, 420)
    panel(surface, box, accent=C_GREEN if ok else C_RED)
    centered(surface, fonts, title, (box.centerx, 185), C_GREEN if ok else C_RED, "title")
    for i, line in enumerate(lines):
        centered(surface, fonts, line, (box.centerx, 250 + i * 34), C_TEXT, "body")
    retry = pygame.Rect(0, 0, 220, 52)
    base = pygame.Rect(0, 0, 220, 52)
    retry.center = (box.centerx - 140, 470)
    base.center = (box.centerx + 140, 470)
    button(surface, retry, "RETRY", fonts, mouse_pos)
    button(surface, base, "RETURN TO BASE", fonts, mouse_pos, small=True)
    return {"retry": retry, "base": base}


def icon_bolt(surface, center, color=C_CYAN, scale: int = 1) -> None:
    x, y = center
    pts = [
        (x, y - 12 * scale),
        (x + 6 * scale, y - 2 * scale),
        (x + 1 * scale, y - 2 * scale),
        (x + 8 * scale, y + 12 * scale),
        (x - 2 * scale, y + 2 * scale),
        (x + 3 * scale, y + 2 * scale),
    ]
    pygame.draw.polygon(surface, color, pts)
