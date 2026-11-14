"""Global MarsMission UI design system — minimalist sci-fi."""

from __future__ import annotations

import math

import pygame

# ---- Palette (hex → RGB) ----
C_BG = (23, 25, 28)           # #17191C
C_SURFACE = (39, 43, 48)      # #272B30
C_SURFACE_2 = (48, 53, 58)
C_EDGE = (70, 76, 84)
C_EDGE_DIM = (55, 60, 66)
C_MARS = (217, 130, 80)       # #D98250
C_SIGNAL = (116, 185, 176)    # #74B9B0
C_GREEN = (120, 184, 139)     # #78B88B
C_AMBER = (196, 158, 90)
C_RED = (186, 92, 86)
C_TEXT = (236, 232, 226)
C_MUTED = (148, 152, 158)
C_BTN = (54, 60, 68)
C_BTN_HOV = (70, 78, 88)
C_BTN_ACCENT = (217, 130, 80)
C_BTN_ACCENT_HOV = (232, 150, 100)

# Legacy aliases (existing call sites)
C_PANEL = C_SURFACE
C_CYAN = C_SIGNAL
C_EDGE_BRIGHT = C_MARS

RADIUS = 8
SPACE = 8
MARGIN = 16


def dim_backdrop(surface, alpha: int = 140) -> None:
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    overlay.fill((10, 12, 14, alpha))
    surface.blit(overlay, (0, 0))


def panel(surface, rect: pygame.Rect, accent=None, fill=None) -> None:
    """Flat surface with subtle border — no neon glow, no thick accent bars."""
    fill = fill or C_SURFACE
    accent = accent or C_EDGE
    pygame.draw.rect(surface, fill, rect, border_radius=RADIUS)
    pygame.draw.rect(surface, accent, rect, 1, border_radius=RADIUS)


def soft_panel(surface, rect: pygame.Rect, alpha: int = 200) -> None:
    """Semi-transparent HUD chip (explore mode)."""
    s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(s, (*C_BG, alpha), (0, 0, rect.w, rect.h), border_radius=RADIUS)
    pygame.draw.rect(s, (*C_EDGE, 160), (0, 0, rect.w, rect.h), 1, border_radius=RADIUS)
    surface.blit(s, rect.topleft)


def header(surface, fonts, rect: pygame.Rect, title: str, subtitle: str = "") -> int:
    t = fonts["title"].render(title, True, C_TEXT)
    surface.blit(t, (rect.x + 24, rect.y + 18))
    y = rect.y + 52
    if subtitle:
        s = fonts["small"].render(subtitle[:90], True, C_MUTED)
        surface.blit(s, (rect.x + 24, y))
        y += 22
    # Thin divider
    pygame.draw.line(surface, C_EDGE, (rect.x + 24, y + 4), (rect.right - 24, y + 4), 1)
    return y + 14


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


def button(
    surface,
    rect: pygame.Rect,
    text: str,
    fonts,
    mouse_pos,
    small: bool = False,
    accent: bool = False,
) -> bool:
    hovered = rect.collidepoint(mouse_pos)
    if accent:
        fill = C_BTN_ACCENT_HOV if hovered else C_BTN_ACCENT
        border = C_MARS
        tcol = (255, 248, 240)
    else:
        fill = C_BTN_HOV if hovered else C_BTN
        border = C_SIGNAL if hovered else C_EDGE
        tcol = C_TEXT
    pygame.draw.rect(surface, fill, rect, border_radius=RADIUS)
    pygame.draw.rect(surface, border, rect, 1, border_radius=RADIUS)
    key = "button_small" if small else "button"
    img = fonts[key].render(text, True, tcol)
    surface.blit(img, img.get_rect(center=rect.center))
    return hovered


def meter(surface, rect: pygame.Rect, value: float, maximum: float, color=C_SIGNAL, label_text: str = "") -> None:
    pygame.draw.rect(surface, C_BG, rect, border_radius=4)
    pygame.draw.rect(surface, C_EDGE, rect, 1, border_radius=4)
    t = 0 if maximum <= 0 else max(0.0, min(1.0, value / maximum))
    fill = pygame.Rect(rect.x + 2, rect.y + 2, int((rect.w - 4) * t), rect.h - 4)
    if fill.w > 0:
        pygame.draw.rect(surface, color, fill, border_radius=3)


def status_chip(surface, fonts, text: str, pos, ok: bool, width: int = 140) -> pygame.Rect:
    color = C_GREEN if ok else C_AMBER
    chip = pygame.Rect(pos[0], pos[1], width, 26)
    pygame.draw.rect(surface, C_SURFACE, chip, border_radius=6)
    pygame.draw.rect(surface, color, chip, 1, border_radius=6)
    # Status marker (not colour-only): filled vs hollow
    pygame.draw.circle(surface, color, (chip.x + 12, chip.centery), 4 if ok else 4, 0 if ok else 1)
    img = fonts["small"].render(text, True, color)
    surface.blit(img, img.get_rect(midleft=(chip.x + 24, chip.centery)))
    return chip


def objective_bar(surface, fonts, text: str, y: int = 16) -> None:
    w = min(880, surface.get_width() - 80)
    rect = pygame.Rect(surface.get_width() // 2 - w // 2, y, w, 32)
    pygame.draw.rect(surface, C_BG, rect, border_radius=6)
    pygame.draw.rect(surface, C_EDGE, rect, 1, border_radius=6)
    img = fonts["small"].render(text[:88], True, C_TEXT)
    surface.blit(img, img.get_rect(center=rect.center))


def timer_badge(surface, fonts, time_left: float, width: int = 1280) -> None:
    seconds = max(0, int(math.ceil(time_left)))
    color = C_RED if seconds <= 15 else C_TEXT
    rect = pygame.Rect(width - 148, 16, 128, 36)
    pygame.draw.rect(surface, C_SURFACE, rect, border_radius=6)
    pygame.draw.rect(surface, C_RED if seconds <= 15 else C_EDGE, rect, 1, border_radius=6)
    img = fonts["small"].render(f"{seconds:02d}s", True, color)
    surface.blit(img, img.get_rect(center=rect.center))


def challenge_frame(
    surface,
    fonts,
    title: str,
    stage: str,
    progress: float = -1.0,
    time_left: float | None = None,
    hint: str = "",
) -> pygame.Rect:
    """
    Reusable challenge chrome: top header strip only.
    Returns content safe-rect for the puzzle area.
    """
    # Top bar
    bar = pygame.Rect(MARGIN, MARGIN, surface.get_width() - MARGIN * 2, 56)
    soft_panel(surface, bar, 210)
    label(surface, fonts, title[:40], (bar.x + 16, bar.y + 8), C_TEXT, "body")
    label(surface, fonts, stage[:50], (bar.x + 16, bar.y + 30), C_MUTED, "small")
    if progress >= 0:
        meter(surface, pygame.Rect(bar.right - 220, bar.y + 20, 120, 10), progress, 1.0, C_SIGNAL)
    if time_left is not None:
        timer_badge(surface, fonts, time_left, width=surface.get_width())
    if hint:
        objective_bar(surface, fonts, hint, y=bar.bottom + 8)
        content_top = bar.bottom + 48
    else:
        content_top = bar.bottom + 12
    return pygame.Rect(MARGIN, content_top, surface.get_width() - MARGIN * 2, surface.get_height() - content_top - 48)


def footer_hint(surface, fonts, text: str) -> None:
    img = fonts["small"].render(text[:100], True, C_MUTED)
    surface.blit(img, img.get_rect(midbottom=(surface.get_width() // 2, surface.get_height() - 14)))


def result_panel(surface, fonts, mouse_pos, title: str, lines: list[str], ok: bool, btn_label: str = "CONTINUE"):
    dim_backdrop(surface, 160)
    box = pygame.Rect(280, 150, 720, 400)
    panel(surface, box, accent=C_GREEN if ok else C_RED)
    centered(surface, fonts, title, (box.centerx, 200), C_GREEN if ok else C_RED, "title")
    for i, line in enumerate(lines[:5]):
        centered(surface, fonts, line[:70], (box.centerx, 260 + i * 32), C_TEXT, "body")
    btn = pygame.Rect(0, 0, 260, 48)
    btn.center = (box.centerx, 480)
    button(surface, btn, btn_label, fonts, mouse_pos, accent=ok)
    return btn


def dual_result_panel(surface, fonts, mouse_pos, title: str, lines: list[str], ok: bool):
    dim_backdrop(surface, 160)
    box = pygame.Rect(260, 150, 760, 400)
    panel(surface, box, accent=C_GREEN if ok else C_RED)
    centered(surface, fonts, title, (box.centerx, 200), C_GREEN if ok else C_RED, "title")
    for i, line in enumerate(lines[:5]):
        centered(surface, fonts, line[:70], (box.centerx, 258 + i * 30), C_TEXT, "body")
    retry = pygame.Rect(0, 0, 200, 46)
    base = pygame.Rect(0, 0, 220, 46)
    retry.center = (box.centerx - 130, 470)
    base.center = (box.centerx + 130, 470)
    button(surface, retry, "RETRY", fonts, mouse_pos, accent=True)
    button(surface, base, "RETURN TO BASE", fonts, mouse_pos, small=True)
    return {"retry": retry, "base": base}


def icon_bolt(surface, center, color=C_SIGNAL, scale: int = 1) -> None:
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


def truncate(text: str, n: int) -> str:
    text = text or ""
    return text if len(text) <= n else text[: n - 1] + "…"
