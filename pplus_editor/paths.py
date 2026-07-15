"""Central filesystem locations for the portable editor project."""

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPOILERS_DIRECTORY = PROJECT_ROOT / "spoilers"
ENTITY_CATALOG_PATH = SPOILERS_DIRECTORY / "entities.json"
ENTITY_ICONS_DIRECTORY = SPOILERS_DIRECTORY / "entity_icons"

USER_DATA_DIRECTORY = PROJECT_ROOT / "user_data"
PHOTOS_DIRECTORY = USER_DATA_DIRECTORY / "photos"
PROGRESS_PATH = USER_DATA_DIRECTORY / "progress.json"
SETTINGS_PATH = USER_DATA_DIRECTORY / "settings.json"

LOCAL_APP_DATA_DIRECTORY = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
VOTV_SAVE_DIRECTORY = LOCAL_APP_DATA_DIRECTORY / "VotV" / "Saved" / "SaveGames"
