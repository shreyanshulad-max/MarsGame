"""Application version metadata (separate from campaign save schema versions)."""

APP_NAME = "MARSMISSION"
APP_TITLE = "MARSMISSION – Explore. Research. Repair. Survive."
APP_VERSION = "1.0.0"
APP_VERSION_LABEL = f"{APP_NAME} v{APP_VERSION}"
APP_TAGLINE = "Explore. Research. Repair. Survive."
APP_ENGINE = "Python + Pygame CE"
APP_CREDITS = (
    "MarsMission educational game.\n"
    "Built with Python and Pygame CE.\n"
    "Imagery and sample datasets courtesy of NASA / JPL / University of Arizona / USGS "
    "where included in assets/research_data (see research_manifest.json)."
)


def version_string() -> str:
    return APP_VERSION_LABEL
