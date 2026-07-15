"""Central filesystem locations for the portable editor project."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPOILERS_DIRECTORY = PROJECT_ROOT / "spoilers"
ENTITY_CATALOG_PATH = SPOILERS_DIRECTORY / "entities.json"
ENTITY_ICONS_DIRECTORY = SPOILERS_DIRECTORY / "entity_icons"

USER_DATA_DIRECTORY = PROJECT_ROOT / "user_data"
PHOTOS_DIRECTORY = USER_DATA_DIRECTORY / "photos"
PROGRESS_PATH = USER_DATA_DIRECTORY / "progress.json"
SETTINGS_PATH = USER_DATA_DIRECTORY / "settings.json"
