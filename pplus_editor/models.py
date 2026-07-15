"""Shared data models used by the catalog, save services, and UI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


EntityCategory = Literal["spooky", "mundane"]


@dataclass(frozen=True, slots=True)
class EntityRecord:
    """One entity that Photography Plus can associate with a photo."""

    name: str
    category: EntityCategory
    icon: str
    hint_short: str = ""


@dataclass(frozen=True, slots=True)
class PhotoRecord:
    """Metadata for one stable position in the vanilla photo array."""

    index: int
    has_image: bool
    filename: str | None

    def image_path(self, photos_directory: Path) -> Path | None:
        if not self.filename:
            return None
        return photos_directory / self.filename


@dataclass(frozen=True, slots=True)
class PhotoArchive:
    """Extracted photo-array metadata tied to one vanilla save file."""

    source_path: Path
    source_size: int
    source_sha256: str
    photos: tuple[PhotoRecord, ...]

    @property
    def surviving_count(self) -> int:
        return sum(photo.has_image for photo in self.photos)

    @property
    def deleted_count(self) -> int:
        return len(self.photos) - self.surviving_count

    @property
    def surviving_indices(self) -> frozenset[int]:
        return frozenset(photo.index for photo in self.photos if photo.has_image)


@dataclass(slots=True)
class ProgressState:
    """Recoverable labels plus the source identity they were created against."""

    labels: dict[int, str]
    source_sha256: str | None = None

    def matches(self, archive: PhotoArchive) -> bool | None:
        if not self.source_sha256:
            return None
        return self.source_sha256 == archive.source_sha256


@dataclass(frozen=True, slots=True)
class ExportStats:
    mundane: int
    spooky: int
    bestiary_mundane: int
    bestiary_spooky: int

