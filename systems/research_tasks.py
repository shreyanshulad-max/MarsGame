"""Research task definitions — RP rewards, tiers, validation (no fabricated NASA numbers)."""

from __future__ import annotations

# Tasks reference local manifest item IDs. Interactions are educational classifications
# based on visible browse imagery / documented availability — not fake chemistry.

TASKS = {
    # Tier 1 — before Mission 1 (target ~80 RP)
    "res_hirise_surface": {
        "id": "res_hirise_surface",
        "tier": 1,
        "title": "HiRISE Surface Investigation",
        "dataset_item": "hirise_dunes_01",
        "compare_item": "hirise_crater_01",
        "prompt": "Compare the two Mars surface scenes. Which scene shows a broader sandy dune field?",
        "options": [
            ("A", "Left image (dune / sand-dominated)"),
            ("B", "Right image (crater-dominated)"),
            ("C", "Neither shows surface features"),
        ],
        "correct": "A",
        "hint": "Look for repeating wave-like sand patterns versus a circular impact structure.",
        "base_rp": 35,
        "accuracy_bonus": 5,
        "first_bonus": 0,
        "explanation": "Dune fields show rippled sandy textures; craters show circular rims.",
    },
    "res_mola_elevation": {
        "id": "res_mola_elevation",
        "tier": 1,
        "title": "MOLA Elevation Investigation",
        "dataset_item": "mola_context_01",
        "numeric_item": "mola_profile_sample_01",
        "prompt": (
            "Using the MOLA context browse image and metadata, which statement is honest "
            "about this local data pack?"
        ),
        "options": [
            ("A", "We have a full numeric elevation profile with invented meter values."),
            ("B", "We have a topography context image; a numeric MOLA profile is not installed yet."),
            ("C", "This image proves exact mineral chemistry."),
        ],
        "correct": "B",
        "hint": "Check the Research Terminal attribution and dataset status badges.",
        "base_rp": 35,
        "accuracy_bonus": 5,
        "first_bonus": 0,
        "explanation": (
            "The pack includes NASA Image Library topography context. "
            "A real MOLA numeric extract must be installed before claiming meter values."
        ),
        # Still awards RP for understanding data provenance — scientifically honest.
    },
    # Tier 2 — after Mission 1 (~110 RP available)
    "res_perc_surface": {
        "id": "res_perc_surface",
        "tier": 2,
        "title": "Perseverance Surface Observation",
        "dataset_item": "perseverance_surface_01",
        "prompt": "In the Perseverance browse image, what should a rover driver watch for first?",
        "options": [
            ("A", "Only the sky colour"),
            ("B", "Nearby rocks and uneven ground that could block wheels"),
            ("C", "Ocean waves"),
        ],
        "correct": "B",
        "hint": "Nav/surface images help spot obstacles before driving.",
        "base_rp": 40,
        "accuracy_bonus": 5,
        "first_bonus": 0,
        "explanation": "Surface rocks and rough ground are primary mobility hazards.",
    },
    "res_perc_terrain": {
        "id": "res_perc_terrain",
        "tier": 2,
        "title": "Rover Terrain Comparison",
        "dataset_item": "perseverance_terrain_01",
        "compare_item": "perseverance_surface_01",
        "prompt": "Why do scientists compare multiple Perseverance camera observations?",
        "options": [
            ("A", "To invent new elevation numbers"),
            ("B", "To cross-check visible terrain and obstacles from different views"),
            ("C", "Because one image always contains every answer"),
        ],
        "correct": "B",
        "hint": "Different cameras and sols give complementary context.",
        "base_rp": 30,
        "accuracy_bonus": 5,
        "first_bonus": 0,
        "explanation": "Multiple views reduce uncertainty about hazards and surface texture.",
    },
    "res_hirise_comm": {
        "id": "res_hirise_comm",
        "tier": 2,
        "title": "Orbital Terrain for Communications Planning",
        "dataset_item": "hirise_crater_01",
        "prompt": "How can orbital HiRISE-related imagery help a communications repair team?",
        "options": [
            ("A", "By guaranteeing radio frequency numbers"),
            ("B", "By showing surface context near landing/ops areas for planning access"),
            ("C", "By replacing the need for antenna hardware"),
        ],
        "correct": "B",
        "hint": "Orbital images provide context, not a substitute for hardware.",
        "base_rp": 25,
        "accuracy_bonus": 5,
        "first_bonus": 0,
        "explanation": "Orbital browse products support situational awareness around field sites.",
    },
    # Tier 3 — after Mission 2
    "res_route_compare": {
        "id": "res_route_compare",
        "tier": 3,
        "title": "Route Safety Comparison",
        "dataset_item": "hirise_dunes_01",
        "compare_item": "hirise_crater_01",
        "prompt": "For a rover, which scene looks more risky for a direct crossing without more data?",
        "options": [
            ("A", "Open sand dunes can hide soft ground; crater rims can be steep — both need care"),
            ("B", "Any image means the route is perfectly safe"),
            ("C", "Only Earth roads matter on Mars"),
        ],
        "correct": "A",
        "hint": "Both sand and crater terrain can challenge mobility.",
        "base_rp": 45,
        "accuracy_bonus": 5,
        "first_bonus": 0,
        "explanation": "Sand and cratered terrain both present mobility risk without further analysis.",
    },
    "res_mola_honesty": {
        "id": "res_mola_honesty",
        "tier": 3,
        "title": "Topography Data Integrity Check",
        "dataset_item": "mola_context_01",
        "numeric_item": "mola_profile_sample_01",
        "prompt": "If a numeric MOLA profile is marked unavailable, what should the game do?",
        "options": [
            ("A", "Invent meter values so the puzzle still works"),
            ("B", "Show unavailable status and avoid presenting fake elevations as NASA data"),
            ("C", "Hide the Research Terminal"),
        ],
        "correct": "B",
        "hint": "Scientific integrity over convenience.",
        "base_rp": 30,
        "accuracy_bonus": 0,
        "first_bonus": 0,
        "explanation": "Unavailable authentic data must not be replaced with fabricated numbers.",
    },
    "res_perc_hazard": {
        "id": "res_perc_hazard",
        "tier": 3,
        "title": "Perseverance Hazard Brief",
        "dataset_item": "perseverance_terrain_01",
        "prompt": "Pick the best evidence-based action before sending a rover across rough ground.",
        "options": [
            ("A", "Ignore images and drive at full speed"),
            ("B", "Review camera observations, note obstacles, then choose a safer path"),
            ("C", "Assume all Mars ground is flat"),
        ],
        "correct": "B",
        "hint": "Observation first, then drive.",
        "base_rp": 30,
        "accuracy_bonus": 5,
        "first_bonus": 0,
        "explanation": "Imagery-informed routing reduces risk.",
    },
}


def tasks_for_tier(tier: int) -> list[dict]:
    return [t for t in TASKS.values() if t["tier"] <= tier]


def get_task(task_id: str) -> dict | None:
    return TASKS.get(task_id)


def grade(task: dict, answer: str) -> tuple[bool, int, int]:
    """Returns (correct, accuracy_bonus, first_bonus)."""
    correct = answer == task["correct"]
    acc = task.get("accuracy_bonus", 0) if correct else 0
    first = task.get("first_bonus", 0)
    return correct, acc, first
