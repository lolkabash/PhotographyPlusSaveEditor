"""UI-independent state and navigation for one photo-mapping session."""

from __future__ import annotations

from dataclasses import dataclass

from .catalog import EntityCatalog
from .models import PhotoArchive, PhotoRecord


@dataclass(frozen=True, slots=True)
class LabelChange:
    index: int
    before: str | None
    after: str | None


class EditorSession:
    """Own labels, navigation policy, and reversible edits for the GUI."""

    def __init__(self, catalog: EntityCatalog) -> None:
        self.catalog = catalog
        self.archive: PhotoArchive | None = None
        self.labels: dict[int, str] = {}
        self.current_index: int | None = None
        self.include_deleted = False
        self._undo: list[LabelChange] = []
        self._redo: list[LabelChange] = []

    @property
    def current_photo(self) -> PhotoRecord | None:
        if self.archive is None or self.current_index is None:
            return None
        if not 0 <= self.current_index < len(self.archive.photos):
            return None
        return self.archive.photos[self.current_index]

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def set_archive(self, archive: PhotoArchive) -> None:
        self.archive = archive
        self.labels = {}
        self._undo.clear()
        self._redo.clear()
        first_surviving = next((photo.index for photo in archive.photos if photo.has_image), None)
        self.current_index = first_surviving if first_surviving is not None else 0

    def set_labels(self, labels: dict[int, str]) -> tuple[str, ...]:
        if self.archive is None:
            raise RuntimeError("Load a photo archive before labels.")
        warnings: list[str] = []
        accepted: dict[int, str] = {}
        for index, entity_name in labels.items():
            if not 0 <= index < len(self.archive.photos):
                warnings.append(f"Ignored out-of-range photo index {index}.")
            elif self.catalog.get(entity_name) is None:
                warnings.append(f"Ignored unknown entity '{entity_name}' at index {index}.")
            else:
                accepted[index] = entity_name
        self.labels = accepted
        self._undo.clear()
        self._redo.clear()
        return tuple(warnings)

    def visible_photos(self) -> tuple[PhotoRecord, ...]:
        if self.archive is None:
            return ()
        return tuple(
            photo
            for photo in self.archive.photos
            if self.include_deleted or photo.has_image
        )

    def navigate(self, step: int) -> PhotoRecord | None:
        visible = self.visible_photos()
        if not visible:
            return None
        positions = {photo.index: position for position, photo in enumerate(visible)}
        position = positions.get(self.current_index, 0)
        position = min(max(position + step, 0), len(visible) - 1)
        self.current_index = visible[position].index
        return visible[position]

    def go_to(self, index: int) -> PhotoRecord | None:
        if self.archive is None or not 0 <= index < len(self.archive.photos):
            return None
        self.current_index = index
        return self.archive.photos[index]

    def next_unlabelled(self) -> PhotoRecord | None:
        visible = self.visible_photos()
        if not visible:
            return None
        start = next(
            (position for position, photo in enumerate(visible) if photo.index == self.current_index),
            -1,
        )
        ordered = visible[start + 1 :] + visible[: start + 1]
        for photo in ordered:
            if photo.index not in self.labels:
                self.current_index = photo.index
                return photo
        return None

    def assign(self, entity_name: str | None) -> bool:
        if self.current_index is None:
            return False
        if entity_name is not None and self.catalog.get(entity_name) is None:
            raise ValueError(f"Unknown entity: {entity_name}")
        before = self.labels.get(self.current_index)
        if before == entity_name:
            return False
        self._apply(LabelChange(self.current_index, before, entity_name))
        self._undo.append(LabelChange(self.current_index, before, entity_name))
        self._redo.clear()
        return True

    def undo(self) -> bool:
        if not self._undo:
            return False
        change = self._undo.pop()
        self._apply(LabelChange(change.index, change.after, change.before))
        self._redo.append(change)
        self.current_index = change.index
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        change = self._redo.pop()
        self._apply(change)
        self._undo.append(change)
        self.current_index = change.index
        return True

    def _apply(self, change: LabelChange) -> None:
        if change.after is None:
            self.labels.pop(change.index, None)
        else:
            self.labels[change.index] = change.after

    def surviving_progress(self) -> tuple[int, int]:
        if self.archive is None:
            return 0, 0
        surviving = self.archive.surviving_indices
        return sum(index in surviving for index in self.labels), len(surviving)
