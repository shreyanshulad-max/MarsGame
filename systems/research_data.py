"""Local NASA research data pack loader — never fabricates scientific values."""

from __future__ import annotations

import json
from pathlib import Path

from systems import runtime_paths as rpaths

ROOT = rpaths.resource_root()
DATA_ROOT = rpaths.research_data_dir()
MANIFEST_PATH = DATA_ROOT / "research_manifest.json"


def ensure_dirs() -> None:
    # Never write into read-only PyInstaller bundles
    if not rpaths.can_write_resources():
        return
    for sub in ("hirise", "mola", "meda", "themis", "perseverance", "solar", "metadata", "thumbnails"):
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
        # Only persist during development; packaged builds stay read-only
        if rpaths.can_write_resources():
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
    if not rpaths.can_write_resources():
        return
    ensure_dirs()
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def get_item(manifest: dict, item_id: str) -> dict | None:
    for it in manifest.get("items", []):
        if it.get("id") == item_id:
            return it
    return None


_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
_IMAGE_CACHE: dict[str, object] = {}


def resolve_path(item: dict) -> Path | None:
    """Resolve a local file under assets/research_data (project-root based)."""
    rel = item.get("local_filename")
    if not rel:
        return None
    path = (DATA_ROOT / rel).resolve()
    try:
        path.relative_to(DATA_ROOT.resolve())
    except ValueError:
        return None
    return path if path.is_file() else None


def resolve_image_path(item: dict | None) -> Path | None:
    path = resolve_path(item) if item else None
    if path is None:
        return None
    if path.suffix.lower() not in _IMAGE_EXTS:
        return None
    return path


def item_available(item: dict | None) -> bool:
    if not item:
        return False
    if item.get("status") == "unavailable":
        return False
    if item.get("data_type") in ("numeric_profile", "timeline"):
        return bool(item.get("values")) and item.get("fabricated") is not True
    if item.get("data_type") == "context_note" and item.get("status") == "available":
        return item.get("fabricated") is not True
    # Browse / thermal image: available when a real image file exists
    if resolve_image_path(item) is not None:
        return item.get("fabricated") is not True
    return False


def load_image_surface(item: dict):
    """Return cached pygame Surface or None. Never treats JSON/timeline as an image."""
    import pygame

    path = resolve_image_path(item)
    if path is None:
        return None
    key = str(path)
    if key in _IMAGE_CACHE:
        return _IMAGE_CACHE[key]
    try:
        surf = pygame.image.load(str(path))
        if pygame.display.get_surface() is not None:
            surf = surf.convert_alpha() if path.suffix.lower() == ".png" else surf.convert()
        _IMAGE_CACHE[key] = surf
        return surf
    except pygame.error as exc:
        print(f"[research_data] Failed to load image: {path} ({exc})")
        _IMAGE_CACHE[key] = None
        return None


def scale_to_fit(surface, max_w: int, max_h: int):
    """Preserve aspect ratio while fitting inside max box."""
    import pygame

    if surface is None:
        return None
    sw, sh = surface.get_width(), surface.get_height()
    if sw <= 0 or sh <= 0:
        return surface
    scale = min(max_w / sw, max_h / sh, 1.0) if max(sw, sh) < min(max_w, max_h) else min(max_w / sw, max_h / sh)
    nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
    return pygame.transform.smoothscale(surface, (nw, nh))


def diagnose_assets() -> list[dict]:
    """Return verification rows for research image references."""
    from systems import research_tasks as rtasks

    man = load_manifest()
    rows = []
    for task in rtasks.TASKS.values():
        for key in ("dataset_item", "compare_item"):
            iid = task.get(key)
            if not iid:
                continue
            item = get_item(man, iid)
            img_path = resolve_image_path(item)
            rows.append(
                {
                    "task_id": task["id"],
                    "ref": key,
                    "item_id": iid,
                    "exists": img_path is not None,
                    "path": str(img_path) if img_path else (item or {}).get("local_filename"),
                    "available": item_available(item),
                    "data_type": (item or {}).get("data_type"),
                }
            )
    return rows


def list_by_dataset(manifest: dict, dataset: str) -> list[dict]:
    return [it for it in manifest.get("items", []) if it.get("dataset") == dataset]
