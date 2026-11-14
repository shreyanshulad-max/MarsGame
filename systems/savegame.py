"""Atomic JSON campaign save/load — user AppData path, backup, migration, archive."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from pathlib import Path

from systems import campaign as camp

SCHEMA_VERSION = 2
ENV_SAVE_DIR = "MARS_MISSION_SAVE_DIR"


def default_user_save_dir() -> Path:
    """Platform-aware persistent directory (never CWD-dependent)."""
    override = os.environ.get(ENV_SAVE_DIR)
    if override:
        return Path(override).expanduser().resolve()

    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "MarsMission"
    if sys_platform_is_darwin():
        return Path.home() / "Library" / "Application Support" / "MarsMission"
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "MarsMission"
    return Path.home() / ".local" / "share" / "MarsMission"


def sys_platform_is_darwin() -> bool:
    import sys

    return sys.platform == "darwin"


def legacy_project_save_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "save_data"


SAVE_DIR = default_user_save_dir()
SAVE_PATH = SAVE_DIR / "campaign_save.json"
BACKUP_PATH = SAVE_DIR / "campaign_save.bak.json"
ARCHIVE_PATH = SAVE_DIR / "campaign_archive.json"
RECOVERY_FLAG = SAVE_DIR / "recovery_needed.json"


def configure_paths(base: Path | None = None) -> None:
    """Rebind paths (tests / explicit override)."""
    global SAVE_DIR, SAVE_PATH, BACKUP_PATH, ARCHIVE_PATH, RECOVERY_FLAG
    SAVE_DIR = (base or default_user_save_dir()).resolve()
    SAVE_PATH = SAVE_DIR / "campaign_save.json"
    BACKUP_PATH = SAVE_DIR / "campaign_save.bak.json"
    ARCHIVE_PATH = SAVE_DIR / "campaign_archive.json"
    RECOVERY_FLAG = SAVE_DIR / "recovery_needed.json"


def ensure_dir() -> None:
    SAVE_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        raise ValueError("Save root must be a JSON object")
    return raw


def _atomic_write(path: Path, data: dict) -> bool:
    ensure_dir()
    try:
        payload = json.dumps(data, indent=2, sort_keys=True)
    except (TypeError, ValueError):
        return False
    fd, tmp_name = tempfile.mkstemp(dir=str(SAVE_DIR), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
        return True
    except OSError:
        try:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
        except OSError:
            pass
        return False


def save_campaign(data: dict) -> bool:
    """Write campaign atomically; keep previous file as .bak."""
    ensure_dir()
    data = dict(data)
    data["schema_version"] = max(int(data.get("schema_version", 0) or 0), SCHEMA_VERSION)
    data["version"] = data["schema_version"]
    data["last_saved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    if SAVE_PATH.is_file():
        try:
            shutil.copy2(SAVE_PATH, BACKUP_PATH)
        except OSError:
            pass
    ok = _atomic_write(SAVE_PATH, data)
    if ok and RECOVERY_FLAG.is_file():
        try:
            RECOVERY_FLAG.unlink()
        except OSError:
            pass
    return ok


def _try_load_path(path: Path) -> dict:
    raw = _read_json(path)
    return camp.migrate(raw)


def migrate_legacy_save_if_needed() -> None:
    """Copy old project save_data into user AppData once if destination empty."""
    ensure_dir()
    if SAVE_PATH.is_file():
        return
    legacy = legacy_project_save_dir() / "campaign_save.json"
    legacy_bak = legacy_project_save_dir() / "campaign_save.bak.json"
    src = legacy if legacy.is_file() else (legacy_bak if legacy_bak.is_file() else None)
    if src is None:
        return
    try:
        shutil.copy2(src, SAVE_PATH)
        if legacy_bak.is_file():
            shutil.copy2(legacy_bak, BACKUP_PATH)
    except OSError:
        pass


def load_campaign() -> dict | None:
    """
    Load and migrate.
    Returns None if no save exists.
    Raises ValueError if a save exists but cannot be recovered (does NOT wipe it).
    """
    ensure_dir()
    migrate_legacy_save_if_needed()
    path = SAVE_PATH if SAVE_PATH.is_file() else None
    if path is None and BACKUP_PATH.is_file():
        path = BACKUP_PATH
    if path is None:
        return None

    errors: list[str] = []
    for candidate in (path, BACKUP_PATH if path != BACKUP_PATH else None):
        if candidate is None or not candidate.is_file():
            continue
        try:
            return _try_load_path(candidate)
        except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
            errors.append(f"{candidate.name}: {exc}")

    # Mark recovery needed — never silently overwrite live progress
    flag = {
        "message": "Campaign save could not be loaded. Start a new campaign only after confirming.",
        "errors": errors,
        "save_path": str(SAVE_PATH),
        "backup_path": str(BACKUP_PATH),
        "flagged_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    try:
        _atomic_write(RECOVERY_FLAG, flag)
    except OSError:
        pass
    raise ValueError("; ".join(errors) or "Campaign save unreadable")


def save_exists() -> bool:
    ensure_dir()
    migrate_legacy_save_if_needed()
    return SAVE_PATH.is_file() or BACKUP_PATH.is_file()


def recovery_needed() -> dict | None:
    if not RECOVERY_FLAG.is_file():
        return None
    try:
        return _read_json(RECOVERY_FLAG)
    except (OSError, json.JSONDecodeError, ValueError):
        return {"message": "Save recovery required."}


def new_campaign_save(seed: int | None = None) -> dict:
    data = camp.make_campaign(seed)
    save_campaign(camp.export_for_save(data, {}))
    return data


def load_archive() -> list:
    ensure_dir()
    if not ARCHIVE_PATH.is_file():
        return []
    try:
        raw = _read_json(ARCHIVE_PATH)
    except (OSError, json.JSONDecodeError, ValueError):
        return []
    records = raw.get("records", [])
    return records if isinstance(records, list) else []


def append_archive(record: dict) -> bool:
    ensure_dir()
    records = load_archive()
    records.append(record)
    return _atomic_write(ARCHIVE_PATH, {"schema_version": 1, "records": records})


def archive_and_start_new(current: dict | None, seed: int | None = None) -> dict:
    """Archive previous campaign summary, then create a fresh campaign."""
    if current:
        append_archive(camp.archive_record(current))
        # Keep a full snapshot of the replaced campaign
        if SAVE_PATH.is_file():
            try:
                snap = SAVE_DIR / f"campaign_snapshot_{int(time.time())}.json"
                shutil.copy2(SAVE_PATH, snap)
            except OSError:
                pass
            try:
                shutil.copy2(SAVE_PATH, SAVE_DIR / "campaign_save_archived.json")
            except OSError:
                pass
    data = camp.make_campaign(seed)
    save_campaign(camp.export_for_save(data, {}))
    return data


def delete_campaign_for_new() -> None:
    """Legacy helper — prefer archive_and_start_new. Archives then removes active save."""
    ensure_dir()
    if SAVE_PATH.is_file():
        try:
            loaded = _try_load_path(SAVE_PATH)
            append_archive(camp.archive_record(loaded))
        except Exception:
            pass
        try:
            shutil.copy2(SAVE_PATH, SAVE_DIR / "campaign_save_archived.json")
        except OSError:
            pass
        try:
            SAVE_PATH.unlink()
        except OSError:
            pass
