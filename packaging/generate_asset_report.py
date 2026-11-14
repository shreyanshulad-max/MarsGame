"""Generate packaging/asset_inclusion_report.md from the live assets tree."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
OUT = Path(__file__).resolve().parent / "asset_inclusion_report.md"


def main() -> None:
    lines = [
        "# MARSMISSION — Asset & NASA data inclusion report",
        "",
        f"Generated from `{ASSETS}`.",
        "",
        "## Summary",
        "",
    ]
    files = sorted(p for p in ASSETS.rglob("*") if p.is_file())
    by_ext: dict[str, list[Path]] = {}
    for p in files:
        by_ext.setdefault(p.suffix.lower() or "[none]", []).append(p)
    lines.append(f"- Total files: **{len(files)}**")
    for ext, items in sorted(by_ext.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        lines.append(f"- `{ext}`: {len(items)}")
    lines += ["", "## All packaged asset paths", ""]
    for p in files:
        rel = p.relative_to(ROOT).as_posix()
        lines.append(f"- `{rel}` ({p.stat().st_size} bytes)")

    man = ASSETS / "research_data" / "research_manifest.json"
    lines += ["", "## Research manifest items", ""]
    if man.is_file():
        data = json.loads(man.read_text(encoding="utf-8"))
        lines.append(f"Attribution: {data.get('attribution', '(none)')}")
        lines.append("")
        for it in data.get("items", []):
            iid = it.get("id")
            rel = it.get("local_filename")
            status = it.get("status")
            dtype = it.get("data_type")
            exists = "MISSING"
            if rel:
                path = ASSETS / "research_data" / rel
                exists = "OK" if path.is_file() else "MISSING"
            elif dtype in ("context_note", "timeline", "numeric_profile"):
                exists = "NON-FILE / STRUCTURED"
            lines.append(
                f"- `{iid}` type={dtype} status={status} file={rel} → **{exists}**"
            )
    else:
        lines.append("Manifest missing.")

    lines += [
        "",
        "## Excluded from package (by design)",
        "",
        "- `.venv`, `.git`, `__pycache__`, `build/`, `dist/` (regenerated)",
        "- Personal `save_data/` / AppData campaign saves",
        "- `Mars_Survival_RPG/`, `main_m2_backup.py`",
        "- `tests/` (not required at runtime)",
        "",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({len(files)} asset files)")


if __name__ == "__main__":
    main()
