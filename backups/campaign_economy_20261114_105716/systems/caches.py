"""Seeded randomized supply caches — reproducible, never blocks essential kits."""

from __future__ import annotations

import random

from systems import interactions
from systems import materials as mats

# Optional bonus pools (essentials remain purchasable)
OPTIONAL_POOL = [
    ("copper_wire", 1, 2),
    ("spare_fuse", 1, 1),
    ("insulated_cable", 1, 1),
    ("lubricant", 1, 1),
    ("metal_bracket", 1, 1),
    ("research_log", 1, 1),
]

# Candidate locations away from spawn (deterministic pick via seed)
CANDIDATE_SITES = [
    (900, 600), (1100, 400), (1800, 700), (2000, 1400), (1400, 1600),
    (600, 1100), (2400, 1200), (2800, 600), (300, 1400), (2100, 1800),
    (1000, 1800), (1600, 500), (2600, 1600), (700, 400), (1900, 1000),
]


def generate_caches(seed: int, count: int = 6) -> list[dict]:
    rng = random.Random(int(seed) ^ 0xCACE)
    sites = CANDIDATE_SITES[:]
    rng.shuffle(sites)
    caches = []
    for i in range(min(count, len(sites))):
        mid, lo, hi = rng.choice(OPTIONAL_POOL)
        qty = rng.randint(lo, hi)
        pos = sites[i]
        uid = f"cache_{seed}_{i}_{mid}"
        caches.append(
            {
                "uid": uid,
                "material": mid,
                "qty": qty,
                "pos": pos,
                "name": f"Supply Cache ({mats.CATALOG[mid]['name']})",
            }
        )
    return caches


def apply_caches_to_colony(colony: dict, cache_records: list[dict]) -> None:
    """Add cache collectibles into colony interactables (idempotent by uid)."""
    existing = {c["id"] for c in colony.get("collectibles", [])}
    for rec in cache_records:
        if rec["uid"] in existing:
            continue
        col = interactions.make_collectible(
            rec["uid"],
            rec["name"],
            rec["pos"],
            mats.CATALOG[rec["material"]]["category"],
            f"E - Collect {mats.CATALOG[rec['material']]['name']}",
            (255, 200, 90),
            radius=58,
        )
        col["material"] = rec["material"]
        col["qty"] = rec["qty"]
        col["cache"] = True
        colony["collectibles"].append(col)
        colony["interactables"].append(col)


def ensure_campaign_caches(campaign: dict) -> list[dict]:
    if campaign.get("randomized_cache_records"):
        return campaign["randomized_cache_records"]
    records = generate_caches(campaign["campaign_seed"])
    campaign["randomized_cache_records"] = records
    return records
