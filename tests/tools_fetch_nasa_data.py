"""
Download a small curated NASA Image Library browse pack for offline research.

Uses https://images.nasa.gov/ search API (public).
Does NOT invent scientific measurements.
MOLA numeric samples are only written if downloaded from a documented source;
otherwise they are marked unavailable in the manifest.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent  # project root (script lives in MarsMission/)
DATA = ROOT / "assets" / "research_data"
MANIFEST = DATA / "research_manifest.json"

# Curated NASA Image Library search queries (educational browse imagery)
QUERIES = [
    {
        "id": "hirise_dunes_01",
        "dataset": "hirise",
        "q": "HiRISE Mars dunes",
        "title": "Mars dune field (HiRISE-related browse)",
        "research_use": "Identify sandy vs rocky terrain features.",
        "folder": "hirise",
    },
    {
        "id": "hirise_crater_01",
        "dataset": "hirise",
        "q": "HiRISE Mars crater",
        "title": "Impact crater terrain (HiRISE-related browse)",
        "research_use": "Compare crater rim and floor textures.",
        "folder": "hirise",
    },
    {
        "id": "perseverance_surface_01",
        "dataset": "perseverance",
        "q": "Perseverance rover Mars surface rock",
        "title": "Perseverance surface observation browse",
        "research_use": "Inspect rocks and possible obstacles in rover imagery.",
        "folder": "perseverance",
    },
    {
        "id": "perseverance_terrain_01",
        "dataset": "perseverance",
        "q": "Mars 2020 Perseverance Navcam",
        "title": "Perseverance navigation terrain browse",
        "research_use": "Compare visible terrain obstacles.",
        "folder": "perseverance",
    },
    {
        "id": "mola_context_01",
        "dataset": "mola",
        "q": "MOLA Mars topography elevation",
        "title": "MOLA topography context browse image",
        "research_use": "Context for elevation discussion (image only — not a numeric profile).",
        "folder": "mola",
    },
]


def nasa_search(query: str, page: int = 1) -> dict:
    url = "https://images-api.nasa.gov/search?" + urllib.parse.urlencode(
        {"q": query, "media_type": "image", "page": page}
    )
    req = urllib.request.Request(url, headers={"User-Agent": "MarsMission-Edu/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def pick_item(payload: dict) -> dict | None:
    items = payload.get("collection", {}).get("items", [])
    for it in items:
        data = (it.get("data") or [{}])[0]
        links = it.get("links") or []
        href = None
        for link in links:
            if link.get("render") == "image" or str(link.get("href", "")).endswith((".jpg", ".png", ".jpeg")):
                href = link.get("href")
                break
        if not href:
            continue
        return {
            "nasa_id": data.get("nasa_id"),
            "title": data.get("title"),
            "description": (data.get("description") or "")[:400],
            "date_created": data.get("date_created"),
            "center": data.get("center"),
            "keywords": data.get("keywords") or [],
            "href": href,
        }
    return None


def download(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "MarsMission-Edu/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = resp.read()
        # Cap ~2.5MB browse
        if len(data) > 2_500_000:
            print(f"  skip large file {len(data)} bytes")
            return False
        dest.write_bytes(data)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  download failed: {exc}")
        return False


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    for sub in ("hirise", "mola", "perseverance", "metadata", "thumbnails"):
        (DATA / sub).mkdir(exist_ok=True)

    items = []
    notes = []
    for q in QUERIES:
        print(f"Search: {q['q']}")
        try:
            payload = nasa_search(q["q"])
            picked = pick_item(payload)
        except Exception as exc:  # noqa: BLE001
            print(f"  search failed: {exc}")
            notes.append(f"Failed search for {q['id']}: {exc}")
            items.append(
                {
                    "id": q["id"],
                    "dataset": q["dataset"],
                    "title": q["title"],
                    "status": "unavailable",
                    "reason": f"Download failed during import: {exc}",
                    "source_url": "https://images.nasa.gov/",
                    "fabricated": False,
                }
            )
            continue
        if not picked:
            notes.append(f"No image result for {q['id']}")
            items.append(
                {
                    "id": q["id"],
                    "dataset": q["dataset"],
                    "title": q["title"],
                    "status": "unavailable",
                    "reason": "No suitable browse image found in NASA Image Library search.",
                    "source_url": "https://images.nasa.gov/",
                    "fabricated": False,
                }
            )
            continue
        ext = ".jpg"
        if ".png" in picked["href"].lower():
            ext = ".png"
        local_name = f"{q['folder']}/{q['id']}{ext}"
        dest = DATA / local_name
        print(f"  downloading {picked['nasa_id']} -> {local_name}")
        ok = download(picked["href"], dest)
        meta_path = DATA / "metadata" / f"{q['id']}.json"
        meta_path.write_text(json.dumps(picked, indent=2), encoding="utf-8")
        entry = {
            "id": q["id"],
            "dataset": q["dataset"],
            "title": picked.get("title") or q["title"],
            "description": picked.get("description") or q["research_use"],
            "mission_or_instrument": "NASA Image Library / related Mars imagery",
            "product_id": picked.get("nasa_id"),
            "source_url": picked.get("href"),
            "source_portal": "https://images.nasa.gov/",
            "original_filename": Path(urllib.parse.urlparse(picked["href"]).path).name,
            "local_filename": local_name if ok else None,
            "data_type": "browse_image",
            "observation_date": picked.get("date_created"),
            "units": None,
            "processing": "Original browse image downloaded; no scientific reprocessing.",
            "attribution": "NASA / image contributors as listed in NASA Image Library metadata.",
            "license_notes": "NASA media generally free for educational use; check item metadata.",
            "import_date": str(date.today()),
            "status": "available" if ok else "unavailable",
            "fabricated": False,
            "research_use": q["research_use"],
        }
        items.append(entry)
        time.sleep(0.4)

    # Honest MOLA numeric profile placeholder — unavailable until a real PDS extract is installed
    items.append(
        {
            "id": "mola_profile_sample_01",
            "dataset": "mola",
            "title": "MOLA elevation profile sample",
            "description": "Reserved slot for an authentic MOLA-derived elevation profile.",
            "mission_or_instrument": "MOLA / Mars Global Surveyor",
            "product_id": None,
            "source_url": "https://pds.nasa.gov/",
            "source_portal": "https://pds.nasa.gov/",
            "local_filename": None,
            "data_type": "numeric_profile",
            "units": "meters",
            "values": None,
            "processing": "Not installed. Do not invent elevations.",
            "attribution": "NASA / GSFC / MOLA Science Team",
            "import_date": str(date.today()),
            "status": "unavailable",
            "reason": "Authentic MOLA numeric extract not present in local pack. Install a documented profile to enable elevation analysis.",
            "fabricated": False,
            "research_use": "Compare relative elevation along a transect when data is installed.",
        }
    )
    notes.append(
        "MOLA numeric profile is marked unavailable until a real PDS-derived sample is added. "
        "Image context from NASA Image Library may still be used for educational framing."
    )

    manifest = {
        "version": 1,
        "attribution": (
            "Browse imagery retrieved via NASA Image Library API (images-api.nasa.gov). "
            "HiRISE: https://hirise.lpl.arizona.edu/  MOLA/PDS: https://pds.nasa.gov/  "
            "Mars 2020: https://pds-geosciences.wustl.edu/missions/mars2020/"
        ),
        "items": items,
        "notes": notes,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {MANIFEST}")
    avail = sum(1 for it in items if it.get("status") == "available")
    print(f"Available items: {avail}/{len(items)}")


if __name__ == "__main__":
    main()
