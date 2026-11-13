"""Atomic JSON campaign save/load with backup + migration."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

from systems import campaign as camp

SAVE_DIR = Path(__file__).resolve().parent.parent / "save_data"
SAVE_PATH = SAVE_DIR / "campaign_save.json"
BACKUP_PATH = SAVE_DIR / "campaign_save.bak.json"


def ensure_dir() -> None:
    SAVE_DIR.mkdir(parents=True, exist_ok=True)


def save_campaign(data: dict) -> bool:
    """Write campaign atomically; keep previous file as .bak."""
    ensure_dir()
    try:
        payload = json.dumps(data, indent=2, sort_keys=True)
    except (TypeError, ValueError):
        return False
    # Backup existing
    if SAVE_PATH.is_file():
        try:
            shutil.copy2(SAVE_PATH, BACKUP_PATH)
        except OSError:
            pass
    fd, tmp_name = tempfile.mkstemp(dir=str(SAVE_DIR), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, SAVE_PATH)
        return True
    except OSError:
        try:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
        except OSError:
            pass
        return False


def load_campaign() -> dict | None:
    """Load and migrate. Returns None if no save. Raises ValueError on unreadable critical failure."""
    ensure_dir()
    path = SAVE_PATH if SAVE_PATH.is_file() else None
    if path is None and BACKUP_PATH.is_file():
        path = BACKUP_PATH
    if path is None:
        return None
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        # Try backup
        if path != BACKUP_PATH and BACKUP_PATH.is_file():
            try:
                with open(BACKUP_PATH, encoding="utf-8") as f:
                    raw = json.load(f)
            except (OSError, json.JSONDecodeError):
                raise ValueError(f"Campaign save unreadable: {exc}") from exc
        else:
            raise ValueError(f"Campaign save unreadable: {exc}") from exc
    return camp.migrate(raw)


def new_campaign_save(seed: int | None = None) -> dict:
    data = camp.make_campaign(seed)
    save_campaign(camp.export_for_save(data, {}))
    return data


def delete_campaign_for_new() -> None:
    """Explicit new-campaign action — backup then remove active save."""
    ensure_dir()
    if SAVE_PATH.is_file():
        try:
            shutil.copy2(SAVE_PATH, SAVE_DIR / "campaign_save_archived.json")
        except OSError:
            pass
        try:
            SAVE_PATH.unlink()
        except OSError:
            pass
