"""Optional lightweight audio — silent if mixer/files unavailable."""

from __future__ import annotations

import os

import pygame

_ENABLED = False
_SOUNDS: dict[str, pygame.mixer.Sound | None] = {}
_LAST = {}


def init_audio(assets_dir: str) -> bool:
    global _ENABLED
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        _ENABLED = True
    except pygame.error:
        _ENABLED = False
        return False

    audio_dir = os.path.join(assets_dir, "audio")
    mapping = {
        "step": "sfx_footstep.ogg",
        "interact": "sfx_interact.ogg",
        "pickup": "sfx_pickup.ogg",
        "repair": "sfx_repair.ogg",
        "antenna": "sfx_antenna.ogg",
        "rover": "sfx_rover.ogg",
        "bump": "sfx_bump.ogg",
        "success": "sfx_success.ogg",
        "wind": "ambient_wind.ogg",
    }
    for key, name in mapping.items():
        path = os.path.join(audio_dir, name)
        if os.path.isfile(path):
            try:
                _SOUNDS[key] = pygame.mixer.Sound(path)
            except pygame.error:
                _SOUNDS[key] = None
        else:
            _SOUNDS[key] = None
    return _ENABLED


def play(name: str, volume: float = 0.45, cooldown: float = 0.08) -> None:
    if not _ENABLED:
        return
    snd = _SOUNDS.get(name)
    if snd is None:
        return
    now = pygame.time.get_ticks() / 1000.0
    last = _LAST.get(name, -999.0)
    if now - last < cooldown:
        return
    _LAST[name] = now
    try:
        snd.set_volume(max(0.0, min(1.0, volume)))
        snd.play()
    except pygame.error:
        pass
