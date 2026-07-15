"""Small JSON store for non-sensitive UI preferences and recent paths."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_SETTINGS: dict[str, Any] = {
    "main_save": "",
    "pp_source": "",
    "include_deleted": False,
    "entity_category": "all",
}


def load_settings(path: Path) -> dict[str, Any]:
    if not path.exists():
        return dict(DEFAULT_SETTINGS)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_SETTINGS)
    if not isinstance(payload, dict):
        return dict(DEFAULT_SETTINGS)
    return {**DEFAULT_SETTINGS, **payload}


def save_settings(path: Path, settings: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    temporary_path.replace(path)
