"""Research task definitions — RP rewards, tiers, interactive validation."""

from __future__ import annotations

from systems.economy_config import RESEARCH_BASE_RP

# Interaction kinds:
#   choice — multiple choice (validated)
#   image_pick — click a labeled hotspot on an image
#   route_compare — pick safer of two routes
#   marker — place markers near annotated obstacles
#   timeline — pick a suitable observation window index

TASKS = {
    # -------- Tier 1: Communication Research (90 RP base) --------
    "res_1a_hirise": {
        "id": "res_1a_hirise",
        "tier": 1,
        "mission": "mission_1",
        "title": "HiRISE Landform Investigation",
        "interaction": "image_pick",
        "dataset_item": "hirise_dunes_01",
        "compare_item": "hirise_crater_01",
        "intro": (
            "HiRISE (High Resolution Imaging Science Experiment) on Mars Reconnaissance Orbiter "
            "images Mars surface landforms at high resolution for geology and landing-site studies."
        ),
        "prompt": "Which scene shows a broader sandy dune field?",
        "hotspots": [
            {"id": "A", "label": "Left — dune / sand-dominated", "rect": [0.05, 0.15, 0.42, 0.75]},
            {"id": "B", "label": "Right — crater-dominated", "rect": [0.55, 0.15, 0.42, 0.75]},
        ],
        "correct": "A",
        "hint": "Look for repeating wave-like sand patterns versus a circular impact structure.",
        "base_rp": RESEARCH_BASE_RP,
        "accuracy_bonus": 0,
        "first_bonus": 0,
        "explanation": (
            "Dune fields show rippled sandy textures. Crater scenes show circular rims and ejecta. "
            "Annotation is based on the curated NASA Image Library product titles for these browse images."
        ),
    },
    "res_1b_mola": {
        "id": "res_1b_mola",
        "tier": 1,
        "mission": "mission_1",
        "title": "MOLA Elevation Profile",
        "interaction": "route_compare",
        "dataset_item": "mola_context_01",
        "numeric_item": "mola_profile_sample_01",
        "intro": (
            "MOLA (Mars Orbiter Laser Altimeter) MEGDR products provide regional topography. "
            "This activity uses the installed local data pack — numeric MEGDR extracts are only "
            "used when present and verified."
        ),
        "prompt": "Which route candidate shows the more gradual regional relief based on the available data?",
        "routes": [
            {
                "id": "A",
                "label": "Route A — follow yardang-aligned ridges",
                "note": "Ridge-aligned path can cross sharper relief transitions.",
            },
            {
                "id": "B",
                "label": "Route B — follow the broader valley / meander corridor",
                "note": "Corridor follows lower relative relief in the context scene.",
            },
        ],
        "correct": "B",
        "hint": "Prefer the broader corridor over sharp ridge crossings when only regional context is available.",
        "base_rp": RESEARCH_BASE_RP,
        "accuracy_bonus": 0,
        "first_bonus": 0,
        "explanation": (
            "MOLA MEGDR is suited to broad regional topography, not local obstacle detection. "
            "When a numeric profile is unavailable, choose the visibly broader corridor and treat "
            "meter claims as unavailable until a verified extract is installed."
        ),
        "requires_numeric": False,  # educational route choice on context image; no invented meters
    },
    "res_1c_site": {
        "id": "res_1c_site",
        "tier": 1,
        "mission": "mission_1",
        "title": "Communication Site Assessment",
        "interaction": "route_compare",
        "dataset_item": "hirise_crater_01",
        "compare_item": "hirise_dunes_01",
        "intro": (
            "Educational site-selection simulation using HiRISE browse imagery and terrain context. "
            "This does not perform real RF propagation or Mars relay coverage calculations."
        ),
        "prompt": "Which candidate area is more suitable for a simulated antenna install (access + stable surface)?",
        "routes": [
            {
                "id": "A",
                "label": "Candidate A — crater-cluster terrain",
                "note": "Irregular rims and ejecta complicate access.",
            },
            {
                "id": "B",
                "label": "Candidate B — open dune-adjacent plain context",
                "note": "Broader access; still verify soft ground before real ops.",
            },
        ],
        "correct": "B",
        "hint": "Prefer accessible open ground over dense cratered clutter for a simulated install.",
        "base_rp": RESEARCH_BASE_RP,
        "accuracy_bonus": 0,
        "first_bonus": 0,
        "explanation": (
            "For this educational simulation, the open-access candidate is preferred. "
            "Real antenna siting would require engineering RF and geotech analysis beyond this pack."
        ),
    },
    # -------- Tier 2: Power Systems Research --------
    "res_2a_meda": {
        "id": "res_2a_meda",
        "tier": 2,
        "mission": "mission_2",
        "title": "MEDA Dust and Weather Analysis",
        "interaction": "timeline",
        "dataset_item": "meda_timeline_01",
        "intro": (
            "MEDA (Mars Environmental Dynamics Analyzer) on Mars 2020 measures environmental conditions. "
            "Use only verified local measurements from the data pack."
        ),
        "prompt": "Select the observation window that best matches calmer dust/wind conditions in the installed timeline.",
        "timeline_windows": [
            {"id": "A", "label": "Window A — high dust indicator"},
            {"id": "B", "label": "Window B — calmer interval"},
            {"id": "C", "label": "Window C — peak wind gust"},
        ],
        "correct": "B",
        "hint": "Prefer the calmer labeled interval when planning outdoor power work.",
        "base_rp": RESEARCH_BASE_RP,
        "accuracy_bonus": 0,
        "first_bonus": 0,
        "explanation": "Calmer environmental windows reduce dust interference for outdoor maintenance planning.",
        "requires_dataset": True,
    },
    "res_2b_themis": {
        "id": "res_2b_themis",
        "tier": 2,
        "mission": "mission_2",
        "title": "THEMIS Thermal Investigation",
        "interaction": "image_pick",
        "dataset_item": "themis_thermal_01",
        "intro": (
            "THEMIS on Mars Odyssey provides infrared / brightness-temperature products. "
            "Brightness temperature is not the same as air temperature."
        ),
        "prompt": "Which region appears relatively warmer in the thermal browse product?",
        "hotspots": [
            {"id": "A", "label": "Region A", "rect": [0.08, 0.20, 0.38, 0.60]},
            {"id": "B", "label": "Region B", "rect": [0.52, 0.20, 0.38, 0.60]},
        ],
        "correct": "A",
        "hint": "Use the product legend / brighter IR presentation in the installed browse image.",
        "base_rp": RESEARCH_BASE_RP,
        "accuracy_bonus": 0,
        "first_bonus": 0,
        "explanation": (
            "Thermal products help environmental planning. Values shown are brightness temperature "
            "context from the product — not air temperature."
        ),
        "requires_dataset": True,
    },
    "res_2c_rad": {
        "id": "res_2c_rad",
        "tier": 2,
        "mission": "mission_2",
        "title": "Curiosity RAD Shielding Study",
        "interaction": "choice",
        "dataset_item": "rad_context_01",
        "intro": (
            "Curiosity's Radiation Assessment Detector (RAD) measured the radiation environment "
            "on the Martian surface. This activity uses documented NASA RAD context — the game "
            "protection index is a simulation score, not a real crew dose calculation."
        ),
        "prompt": "Why do habitat designers study radiation measurements like RAD?",
        "options": [
            ("A", "To invent exact safe crew doses inside this game"),
            ("B", "To understand the radiation environment and why shielding concepts matter"),
            ("C", "Because Mars has no radiation"),
        ],
        "correct": "B",
        "hint": "RAD informs environmental understanding; this game does not compute real safety doses.",
        "base_rp": RESEARCH_BASE_RP,
        "accuracy_bonus": 0,
        "first_bonus": 0,
        "explanation": (
            "RAD data help scientists understand Mars surface radiation. Game shielding choices use "
            "a simulation index only — not validated dose/safety math."
        ),
        "requires_dataset": False,
    },
    "res_2c_solar": {
        "id": "res_2c_solar",
        "tier": 2,
        "mission": "mission_2",
        "title": "Solar Power Management Study",
        "interaction": "choice",
        "dataset_item": "solar_dust_spirit_01",
        "compare_item": "solar_insight_power_01",
        "intro": (
            "NASA missions have documented dust accumulation on solar arrays (e.g. Spirit, InSight). "
            "The habitat's 80-unit power budget is a fictional game mechanic — not a measured NASA value."
        ),
        "prompt": "How does dust accumulation affect solar power generation?",
        "options": [
            ("A", "Dust has no effect on solar arrays"),
            ("B", "Dust reduces available power until arrays are cleaned or cleared"),
            ("C", "Dust increases power output"),
        ],
        "correct": "B",
        "hint": "Compare clean vs dust-covered array imagery and NASA notes.",
        "base_rp": RESEARCH_BASE_RP,
        "accuracy_bonus": 0,
        "first_bonus": 0,
        "explanation": (
            "Dust blocks sunlight reaching solar cells, reducing generation until removal "
            "(wind cleaning or operational mitigations). Game power units remain fictional."
        ),
    },
    # -------- Tier 3: Rover Navigation Research --------
    "res_3a_perc": {
        "id": "res_3a_perc",
        "tier": 3,
        "mission": "mission_3",
        "title": "Perseverance Camera Investigation",
        "interaction": "marker",
        "dataset_item": "perseverance_surface_01",
        "intro": "Rover cameras (Navcam/Hazcam and science imagers) help identify terrain obstacles before driving.",
        "prompt": "Mark the rock / surface target area that a driver should treat as an obstacle to inspect.",
        "markers_truth": [
            {"id": "rock", "cx": 0.50, "cy": 0.55, "radius": 0.18},
        ],
        "correct": "rock",
        "hint": "Look for the abraded/rock target region emphasized in the browse image.",
        "base_rp": RESEARCH_BASE_RP,
        "accuracy_bonus": 0,
        "first_bonus": 0,
        "explanation": "Surface rocks and uneven ground are primary mobility hazards in rover ops.",
    },
    "res_3b_hirise_dtm": {
        "id": "res_3b_hirise_dtm",
        "tier": 3,
        "mission": "mission_3",
        "title": "HiRISE Terrain and Slope Analysis",
        "interaction": "route_compare",
        "dataset_item": "hirise_dunes_01",
        "compare_item": "hirise_crater_01",
        "intro": (
            "HiRISE DTM products (MRO-M-HIRISE-5-DTM-V1.0) support slope/terrain study. "
            "This pack uses verified browse terrain context when a full DTM extract is not installed."
        ),
        "prompt": "Which route looks lower-risk from the displayed terrain evidence?",
        "routes": [
            {"id": "A", "label": "Cross dense crater-cluster terrain", "note": "Steep rims / irregular blocks."},
            {"id": "B", "label": "Skirt open sand with gradual approach", "note": "Still soft-ground risk, but less rim hazard."},
        ],
        "correct": "B",
        "hint": "Avoid steep crater rims when choosing a lower-risk educational route.",
        "base_rp": RESEARCH_BASE_RP,
        "accuracy_bonus": 0,
        "first_bonus": 0,
        "explanation": "Crater rims imply steeper local slopes; open approaches are preferred when DTM detail is limited.",
        "requires_dataset": False,
    },
    "res_3c_mola_route": {
        "id": "res_3c_mola_route",
        "tier": 3,
        "mission": "mission_3",
        "title": "MOLA Regional Route Assessment",
        "interaction": "route_compare",
        "dataset_item": "mola_context_01",
        "intro": (
            "Regional MOLA topography and local HiRISE/rover views must be considered together. "
            "MOLA alone cannot resolve local obstacles."
        ),
        "prompt": "Which broad route is more suitable at regional scale?",
        "routes": [
            {"id": "A", "label": "Ridge-hopping traverse", "note": "Larger regional relief changes."},
            {"id": "B", "label": "Corridor following lower relative relief", "note": "More gradual regional change."},
        ],
        "correct": "B",
        "hint": "Prefer gradual regional corridors, then refine with local imagery.",
        "base_rp": RESEARCH_BASE_RP,
        "accuracy_bonus": 0,
        "first_bonus": 0,
        "explanation": "Regional relief guides corridor choice; local cameras/DTM refine hazard avoidance.",
    },
    # Optional educational — NASA Veggie analogue (not Mars surface crop data)
    "res_veggie_growth": {
        "id": "res_veggie_growth",
        "tier": 2,
        "mission": "mission_2",
        "title": "NASA Veggie Growth Conditions",
        "interaction": "choice",
        "dataset_item": "veggie_context_01",
        "intro": (
            "NASA Veggie experiments grow plants in controlled spaceflight environments (ISS). "
            "They are analogues for controlled-environment agriculture — not direct Mars surface crop measurements."
        ),
        "prompt": "What do plants in a controlled greenhouse need in this educational model?",
        "options": [
            ("A", "Only darkness and no water"),
            ("B", "Adequate light, water, nutrients, and power for systems"),
            ("C", "Nothing — plants grow without resources on Mars"),
        ],
        "correct": "B",
        "hint": "Think about lighting, water, nutrients, and power for growth systems.",
        "base_rp": RESEARCH_BASE_RP,
        "accuracy_bonus": 0,
        "first_bonus": 0,
        "explanation": (
            "Controlled-environment crops need light, water, and nutrients. ISS Veggie is a spaceflight "
            "analogue; this habitat greenhouse uses simplified game rules."
        ),
        "requires_dataset": False,
    },
}

# Legacy ID aliases so older saves / tests still resolve
LEGACY_ALIASES = {
    "res_hirise_surface": "res_1a_hirise",
    "res_mola_elevation": "res_1b_mola",
    "res_perc_surface": "res_3a_perc",
    "res_perc_terrain": "res_3b_hirise_dtm",
    "res_hirise_comm": "res_1c_site",
    "res_route_compare": "res_3b_hirise_dtm",
    "res_mola_honesty": "res_1b_mola",
    "res_perc_hazard": "res_3a_perc",
}


def tasks_for_tier(tier: int) -> list[dict]:
    """Tasks with task.tier <= tier (unlocked tiers)."""
    return [t for t in TASKS.values() if t["tier"] <= int(tier)]


def tasks_for_mission_tier(tier: int) -> list[dict]:
    """Only the core tasks belonging to this exact tier."""
    return [t for t in TASKS.values() if t["tier"] == int(tier)]


def get_task(task_id: str) -> dict | None:
    if task_id in TASKS:
        return TASKS[task_id]
    alias = LEGACY_ALIASES.get(task_id)
    return TASKS.get(alias) if alias else None


def grade(task: dict, answer: str) -> tuple[bool, int, int]:
    """Returns (correct, accuracy_bonus, first_bonus)."""
    correct = str(answer) == str(task["correct"])
    acc = task.get("accuracy_bonus", 0) if correct else 0
    first = task.get("first_bonus", 0) if correct else 0
    return correct, acc, first


def grade_marker(task: dict, nx: float, ny: float) -> tuple[bool, int, int]:
    """Validate a normalized image click against marker truth circles."""
    for m in task.get("markers_truth") or []:
        dx = nx - float(m["cx"])
        dy = ny - float(m["cy"])
        if dx * dx + dy * dy <= float(m.get("radius", 0.15)) ** 2:
            return True, int(task.get("accuracy_bonus", 0)), int(task.get("first_bonus", 0))
    return False, 0, 0


def clearance_task_ids(mission_id: str) -> list[str]:
    from systems.campaign import CLEARANCE_TASKS

    return list(CLEARANCE_TASKS.get(mission_id, []))
