"""Load and atomically save recoverable photo-label progress."""

from __future__ import annotations

import json
from pathlib import Path

from ..models import PhotoArchive, ProgressState


class ProgressError(ValueError):
    """Raised when a progress file is malformed."""


def load_progress(path: Path) -> ProgressState:
    if not path.exists():
        return ProgressState(labels={})
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProgressError(f"Could not load progress: {error}") from error
    if not isinstance(payload, dict):
        raise ProgressError("Progress must be a JSON object.")

    if "labels" not in payload:
        labels_payload = payload
        source = {}
    else:
        labels_payload = payload.get("labels")
        source = payload.get("source") or {}
    if not isinstance(labels_payload, dict) or not isinstance(source, dict):
        raise ProgressError("Progress labels or source metadata are invalid.")

    try:
        labels = {int(index): str(entity) for index, entity in labels_payload.items()}
    except (TypeError, ValueError) as error:
        raise ProgressError("Progress contains a non-numeric photo index.") from error
    return ProgressState(
        labels=labels,
        source_sha256=source.get("sha256"),
    )


def save_progress(path: Path, labels: dict[int, str], archive: PhotoArchive) -> None:
    payload = {
        "schema_version": 2,
        "source": {
            "path": str(archive.source_path),
            "size": archive.source_size,
            "sha256": archive.source_sha256,
        },
        "labels": {str(index): labels[index] for index in sorted(labels)},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary_path.replace(path)
