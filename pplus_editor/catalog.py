"""Load and validate the data-driven Photography Plus entity catalog."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from .models import EntityCategory, EntityRecord


class CatalogError(ValueError):
    """Raised when the entity catalog is incomplete or internally inconsistent."""


class EntityCatalog:
    """Searchable collection of entities loaded from a maintainable JSON file."""

    def __init__(self, entities: Iterable[EntityRecord]) -> None:
        records = tuple(entities)
        by_name = {entity.name: entity for entity in records}
        if len(by_name) != len(records):
            raise CatalogError("Entity names must be unique.")
        self._entities = tuple(sorted(records, key=lambda entity: entity.name.casefold()))
        self._by_name = by_name

    @classmethod
    def load(cls, path: Path) -> "EntityCatalog":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise CatalogError(f"Could not load entity catalog: {error}") from error

        if not isinstance(payload, list):
            raise CatalogError("Entity catalog must be a JSON list.")

        records: list[EntityRecord] = []
        for position, row in enumerate(payload, start=1):
            if not isinstance(row, dict):
                raise CatalogError(f"Entity #{position} must be an object.")
            name = str(row.get("name", "")).strip()
            category = str(row.get("category", "")).strip().lower()
            icon = str(row.get("icon", "")).strip()
            if not name:
                raise CatalogError(f"Entity #{position} is missing a name.")
            if category not in ("spooky", "mundane"):
                raise CatalogError(f"Entity '{name}' has invalid category '{category}'.")
            if not icon:
                raise CatalogError(f"Entity '{name}' is missing an icon filename.")
            records.append(
                EntityRecord(
                    name=name,
                    category=category,  # type: ignore[arg-type]
                    icon=icon,
                    hint_short=str(row.get("hint_short", "")),
                )
            )
        return cls(records)

    def __len__(self) -> int:
        return len(self._entities)

    def __iter__(self):
        return iter(self._entities)

    def get(self, name: str) -> EntityRecord | None:
        return self._by_name.get(name)

    def search(
        self,
        query: str = "",
        category: EntityCategory | None = None,
    ) -> tuple[EntityRecord, ...]:
        needle = query.strip().casefold()
        return tuple(
            entity
            for entity in self._entities
            if (category is None or entity.category == category)
            and (not needle or needle in entity.name.casefold())
        )
