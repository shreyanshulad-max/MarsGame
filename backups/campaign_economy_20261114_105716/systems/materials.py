"""Persistent mission materials — catalog, quantities, reserve/commit for puzzles."""

from __future__ import annotations

from copy import deepcopy

# Categories
CAT_ELECTRICAL = "electrical"
CAT_MECHANICAL = "mechanical"
CAT_SUPPORT = "support"
CAT_CLUE = "clue"

# Material definitions (source of truth)
CATALOG = {
    "copper_wire": {
        "id": "copper_wire",
        "name": "Copper Wire",
        "description": "Conductive wire for antenna coils and signal paths.",
        "category": CAT_ELECTRICAL,
        "mandatory": True,
        "used_in": ["ch1"],
        "icon": "wire",
        "location": "Communication Area",
    },
    "signal_amplifier": {
        "id": "signal_amplifier",
        "name": "Signal Amplifier",
        "description": "Boosts weak satellite returns so telemetry can be read.",
        "category": CAT_ELECTRICAL,
        "mandatory": True,
        "used_in": ["ch1"],
        "icon": "amp",
        "location": "Communication Area",
    },
    "spare_fuse": {
        "id": "spare_fuse",
        "name": "Spare Fuse",
        "description": "Protects circuits from power faults.",
        "category": CAT_ELECTRICAL,
        "mandatory": True,
        "used_in": ["ch1", "ch2"],
        "icon": "fuse",
        "location": "Communication / Equipment Storage",
    },
    "insulated_cable": {
        "id": "insulated_cable",
        "name": "Insulated Cable",
        "description": "Safe cable for solar and habitat power links.",
        "category": CAT_ELECTRICAL,
        "mandatory": True,
        "used_in": ["ch2"],
        "icon": "cable",
        "location": "Damaged Equipment Storage",
    },
    "battery_cell": {
        "id": "battery_cell",
        "name": "Battery Cell",
        "description": "Portable cell for rover power or habitat buffer.",
        "category": CAT_ELECTRICAL,
        "mandatory": True,
        "used_in": ["ch2", "ch3"],
        "icon": "battery",
        "location": "Solar Farm",
    },
    "servo_motor": {
        "id": "servo_motor",
        "name": "Servo Motor",
        "description": "Drive motor for rover wheels.",
        "category": CAT_MECHANICAL,
        "mandatory": True,
        "used_in": ["ch3"],
        "icon": "motor",
        "location": "Rover Maintenance Area",
    },
    "lubricant": {
        "id": "lubricant",
        "name": "Lubricant Cartridge",
        "description": "Frees jammed wheel assemblies.",
        "category": CAT_MECHANICAL,
        "mandatory": True,
        "used_in": ["ch3"],
        "icon": "lube",
        "location": "Rover Maintenance Area",
    },
    "metal_bracket": {
        "id": "metal_bracket",
        "name": "Metal Bracket",
        "description": "Structural support for damaged mounts.",
        "category": CAT_MECHANICAL,
        "mandatory": True,
        "used_in": ["ch3"],
        "icon": "bracket",
        "location": "Rover Maintenance Area",
    },
    "research_log": {
        "id": "research_log",
        "name": "Research Log",
        "description": "Notes about storm damage and equipment clues.",
        "category": CAT_CLUE,
        "mandatory": False,
        "used_in": ["ch1", "ch2", "ch3"],
        "icon": "log",
        "location": "Research Area",
    },
}

# Guaranteed world pickups (id -> qty granted on collect). Unique pickup spots.
WORLD_PICKUPS = [
    # Communication area
    {"uid": "mat_copper_1", "material": "copper_wire", "qty": 2, "pos": (380, 820), "zone": "comm"},
    {"uid": "mat_copper_2", "material": "copper_wire", "qty": 1, "pos": (520, 780), "zone": "comm"},
    {"uid": "mat_amp_1", "material": "signal_amplifier", "qty": 1, "pos": (460, 880), "zone": "comm"},
    {"uid": "mat_fuse_1", "material": "spare_fuse", "qty": 1, "pos": (340, 900), "zone": "comm"},
    # Damaged equipment storage (near habitat / energy edge)
    {"uid": "mat_cable_1", "material": "insulated_cable", "qty": 2, "pos": (1680, 1120), "zone": "habitat"},
    {"uid": "mat_fuse_2", "material": "spare_fuse", "qty": 1, "pos": (1750, 1180), "zone": "habitat"},
    # Solar farm
    {"uid": "mat_batt_1", "material": "battery_cell", "qty": 1, "pos": (2580, 1000), "zone": "energy"},
    # Rover maintenance
    {"uid": "mat_servo_1", "material": "servo_motor", "qty": 1, "pos": (620, 1720), "zone": "rover"},
    {"uid": "mat_lube_1", "material": "lubricant", "qty": 1, "pos": (700, 1780), "zone": "rover"},
    {"uid": "mat_bracket_1", "material": "metal_bracket", "qty": 1, "pos": (560, 1760), "zone": "rover"},
    # Research optional
    {"uid": "mat_log_1", "material": "research_log", "qty": 1, "pos": (2480, 500), "zone": "research"},
]

MISSION_REQUIREMENTS = {
    "ch1": ["copper_wire", "signal_amplifier", "spare_fuse"],
    "ch2": ["insulated_cable", "spare_fuse"],
    "ch3": ["servo_motor", "battery_cell", "lubricant", "metal_bracket"],
}


def empty_stock() -> dict:
    """qty + reserved for each material id."""
    return {mid: {"qty": 0, "reserved": 0} for mid in CATALOG}


def available(stock: dict, mid: str) -> int:
    s = stock.get(mid, {"qty": 0, "reserved": 0})
    return max(0, s["qty"] - s["reserved"])


def add_material(stock: dict, mid: str, qty: int = 1) -> None:
    if mid not in stock:
        stock[mid] = {"qty": 0, "reserved": 0}
    stock[mid]["qty"] += qty


def can_reserve(stock: dict, mid: str, qty: int = 1) -> bool:
    return available(stock, mid) >= qty


def reserve(stock: dict, mid: str, qty: int = 1) -> bool:
    if not can_reserve(stock, mid, qty):
        return False
    stock[mid]["reserved"] += qty
    return True


def release(stock: dict, mid: str, qty: int = 1) -> None:
    if mid not in stock:
        return
    stock[mid]["reserved"] = max(0, stock[mid]["reserved"] - qty)


def commit(stock: dict, mid: str, qty: int = 1) -> None:
    """Spend reserved materials permanently (after successful repair)."""
    if mid not in stock:
        return
    use = min(qty, stock[mid]["reserved"], stock[mid]["qty"])
    stock[mid]["reserved"] -= use
    stock[mid]["qty"] -= use


def release_all_reserved(stock: dict) -> None:
    for mid in stock:
        stock[mid]["reserved"] = 0


def has_requirements(stock: dict, mission: str) -> tuple[bool, list[str]]:
    missing = []
    for mid in MISSION_REQUIREMENTS.get(mission, []):
        total = stock.get(mid, {"qty": 0}).get("qty", 0)
        if total < 1:
            missing.append(CATALOG[mid]["name"])
    return (len(missing) == 0, missing)


def make_progression() -> dict:
    """Cross-challenge bonuses that never soft-lock later missions."""
    return {
        "comm_restored": False,
        "power_restored": False,
        "rover_rescued": False,
        "extra_life": 0,       # CH2 allocation above min
        "extra_food": 0,
        "extra_comms": 0,
        "scan_clarity": 0.0,   # 0-1 from CH1 success + CH2 comms
        "oxygen_reserve": 0,   # from extra life
        "food_bonus": 0,       # from extra food
        "clues": [],           # discovered journal clue ids
        "repairs_done": [],
    }


def catalog_entry(mid: str) -> dict:
    return CATALOG[mid]


def clone_catalog() -> dict:
    return deepcopy(CATALOG)
