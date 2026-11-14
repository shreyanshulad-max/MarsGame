# Research data import

Local offline pack under `assets/research_data/`.

## Layout

- `hirise/` — HiRISE browse imagery
- `mola/` — topography context browse imagery
- `meda/` — MEDA timeline JSON (`meda_timeline_01.json`)
- `themis/` — THEMIS / IR browse imagery
- `perseverance/` — rover camera browse imagery
- `solar/` — solar array dust / power context imagery
- `metadata/` — per-item metadata JSON
- `research_manifest.json` — authoritative catalog

## Rules

1. Do not invent Product IDs or scientific measurements.
2. Mark missing products `"status": "unavailable"` and leave `values` / `local_filename` empty.
3. Set `"fabricated": false` only for verified local files or curated cited summaries.
4. After adding files, update `research_manifest.json` and re-run `python tools_fetch_nasa_data.py` if using NASA Image Library browse products.

## MEDA timeline import

Place a JSON file at `meda/meda_timeline_01.json` with `windows` and documented source DOI/URL, then set the manifest item `values` and `status` to `available`.
