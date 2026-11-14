"""Local NASA research data pack loader — never fabricates scientific values."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = ROOT / "assets" / "research_data"
MANIFEST_PATH = DATA_ROOT / "research_manifest.json"


def ensure_dirs() -> None:
    for sub in ("hirise", "mola", "perseverance", "metadata", "thumbnails"):
        (DATA_ROOT / sub).mkdir(parents=True, exist_ok=True)


def default_manifest() -> dict:
    return {
        "version": 1,
        "attribution": (
            "Imagery and topographic samples courtesy of NASA / JPL / University of Arizona / USGS. "
            "Educational use within Mars Mission. See each product entry for source URLs."
        ),
        "items": [],
        "notes": [],
    }


def load_manifest() -> dict:
    ensure_dirs()
    if not MANIFEST_PATH.is_file():
        man = default_manifest()
        save_manifest(man)
        return man
    try:
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return default_manifest()
    if "items" not in data:
        data["items"] = []
    return data


def save_manifest(manifest: dict) -> None:
    ensure_dirs()
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def get_item(manifest: dict, item_id: str) -> dict | None:
    for it in manifest.get("items", []):
        if it.get("id") == item_id:
            return it
    return None


def resolve_path(item: dict) -> Path | None:
    rel = item.get("local_filename")
    if not rel:
        return None
    path = DATA_ROOT / rel
    return path if path.is_file() else None


def item_available(item: dict | None) -> bool:
    if not item:
        return False
    if item.get("status") == "unavailable":
        return False
    if item.get("data_type") == "numeric_profile":
        return bool(item.get("values")) and item.get("fabricated") is not True
    return resolve_path(item) is not None


def load_image_surface(item: dict):
    """Return pygame Surface or None."""
    import pygame

    path = resolve_path(item)
    if path is None:
        return None
    try:
        return pygame.image.load(str(path)).convert()
    except pygame.error:
        return None


def list_by_dataset(manifest: dict, dataset: str) -> list[dict]:
    return [it for it in manifest.get("items", []) if it.get("dataset") == dataset]
