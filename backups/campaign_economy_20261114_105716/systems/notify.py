"""Small queued notifications — non-blocking, auto-dismiss."""

from __future__ import annotations

import pygame

from systems import challenge_ui as ui

MAX_QUEUE = 5
DEFAULT_LIFE = 2.8
STACK_Y = 72
STACK_H = 36


def make_notifier() -> dict:
    return {"items": []}  # [{text, kind, life, max_life}]


def push(notifier: dict, text: str, kind: str = "info") -> None:
    """kind: info | success | warn | error | rp | mission"""
    if not text:
        return
    notifier["items"].append(
        {"text": text[:64], "kind": kind, "life": DEFAULT_LIFE, "max_life": DEFAULT_LIFE}
    )
    if len(notifier["items"]) > MAX_QUEUE:
        notifier["items"] = notifier["items"][-MAX_QUEUE:]


def update(notifier: dict, dt: float) -> None:
    alive = []
    for it in notifier["items"]:
        it["life"] -= dt
        if it["life"] > 0:
            alive.append(it)
    notifier["items"] = alive


def _color(kind: str):
    return {
        "success": ui.C_GREEN,
        "warn": ui.C_AMBER,
        "error": ui.C_RED,
        "rp": ui.C_SIGNAL,
        "mission": ui.C_MARS,
    }.get(kind, ui.C_SIGNAL)


def _glyph(kind: str) -> str:
    return {
        "success": "+",
        "warn": "!",
        "error": "×",
        "rp": "R",
        "mission": "M",
        "info": "·",
    }.get(kind, "·")


def draw(surface, fonts, notifier: dict) -> None:
    if not notifier.get("items"):
        return
    cx = surface.get_width() // 2
    for i, it in enumerate(notifier["items"]):
        fade = min(1.0, it["life"] / 0.35, (it["max_life"] - it["life"]) / 0.2 + 0.8)
        fade = max(0.0, min(1.0, fade))
        w, h = 420, STACK_H
        x = cx - w // 2
        y = STACK_Y + i * (STACK_H + 6)
        alpha = int(210 * fade)
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        col = _color(it["kind"])
        pygame.draw.rect(s, (*ui.C_BG, alpha), (0, 0, w, h), border_radius=6)
        pygame.draw.rect(s, (*col, int(180 * fade)), (0, 0, w, h), 1, border_radius=6)
        surface.blit(s, (x, y))
        glyph = fonts["small"].render(_glyph(it["kind"]), True, col)
        surface.blit(glyph, (x + 12, y + 8))
        msg = fonts["small"].render(it["text"], True, ui.C_TEXT)
        surface.blit(msg, (x + 32, y + 8))
