"""Import and export Photography Plus photo-to-entity mapping variables."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..catalog import EntityCatalog
from ..gvas_reader import GvasReader
from ..gvas_writer import GvasWriter
from ..models import ExportStats, PhotoArchive


class SaveFormatError(ValueError):
    """Raised when a PP save or online-editor export has an unexpected shape."""


PHOTO_MUNDANE = "photoIndexesEntityMundane"
PHOTO_SPOOKY = "photoIndexesEntitySpooky"
BESTIARY_MUNDANE = "bestiaryPhotoIndexesEntityMundane"
BESTIARY_SPOOKY = "bestiaryPhotoIndexesEntitySpooky"
PHOTO_VARIABLES = (PHOTO_MUNDANE, PHOTO_SPOOKY)
ALL_MAPPING_VARIABLES = (PHOTO_MUNDANE, PHOTO_SPOOKY, BESTIARY_MUNDANE, BESTIARY_SPOOKY)


def parse_mapping_string(value: str) -> dict[int, str]:
    labels: dict[int, str] = {}
    for part in value.strip("|").split("|"):
        if not part:
            continue
        index_text, separator, entity_name = part.partition("_")
        if not separator or not entity_name:
            raise SaveFormatError(f"Invalid photo mapping entry: {part!r}")
        try:
            labels[int(index_text)] = entity_name
        except ValueError as error:
            raise SaveFormatError(f"Invalid photo index in mapping: {part!r}") from error
    return labels


def _field(properties: dict[str, Any], base_name: str) -> Any:
    for field_name, field_value in properties.items():
        if field_name == base_name or field_name.startswith(base_name + "_"):
            return field_value
    return None


def _parse_binary(path: Path) -> dict[str, Any]:
    parsed = GvasReader(path.read_bytes()).parse()
    parse_error = parsed.get("properties", {}).get("__parse_error__")
    if parse_error:
        raise SaveFormatError(
            f"Could not parse PP save at byte {parse_error.get('offset')}: {parse_error.get('error')}"
        )
    return parsed


def _custom_variables(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    property_value = parsed.get("properties", {}).get("CustomVariableList", {}).get("value")
    if not isinstance(property_value, list):
        raise SaveFormatError("PP save has no CustomVariableList array.")
    return property_value


def _binary_mapping_values(parsed: dict[str, Any]) -> dict[str, str]:
    values: dict[str, str] = {}
    for entry in _custom_variables(parsed):
        properties = entry.get("properties", {})
        variable_field = _field(properties, "VariableID") or {}
        string_field = _field(properties, "StringVal") or {}
        variable_id = variable_field.get("value", "")
        if variable_id in ALL_MAPPING_VARIABLES:
            values[variable_id] = str(string_field.get("value", ""))
    return values


def load_pp_labels(path: Path) -> dict[int, str]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries = payload.get("CustomVariableList") if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            raise SaveFormatError("Online-editor JSON has no CustomVariableList array.")
        values = {
            str(entry.get("VariableID", "")): str(entry.get("StringVal") or "")
            for entry in entries
            if isinstance(entry, dict)
        }
    else:
        values = _binary_mapping_values(_parse_binary(path))

    labels: dict[int, str] = {}
    for variable_id in PHOTO_VARIABLES:
        labels.update(parse_mapping_string(values.get(variable_id, "")))
    return labels


def _format_mapping(entries: list[str]) -> str:
    return "|".join(entries) + ("|" if entries else "")


def compose_mapping_values(
    labels: dict[int, str],
    archive: PhotoArchive,
    catalog: EntityCatalog,
) -> tuple[dict[str, str], ExportStats]:
    grouped: dict[str, list[str]] = {variable_id: [] for variable_id in ALL_MAPPING_VARIABLES}
    surviving = archive.surviving_indices
    for index in sorted(labels):
        entity_name = labels[index]
        entity = catalog.get(entity_name)
        if entity is None:
            raise SaveFormatError(f"Unknown entity in labels: {entity_name}")
        mapping = f"{index}_{entity_name}"
        if entity.category == "mundane":
            grouped[PHOTO_MUNDANE].append(mapping)
            if index in surviving:
                grouped[BESTIARY_MUNDANE].append(mapping)
        else:
            grouped[PHOTO_SPOOKY].append(mapping)
            if index in surviving:
                grouped[BESTIARY_SPOOKY].append(mapping)

    values = {variable_id: _format_mapping(entries) for variable_id, entries in grouped.items()}
    stats = ExportStats(
        mundane=len(grouped[PHOTO_MUNDANE]),
        spooky=len(grouped[PHOTO_SPOOKY]),
        bestiary_mundane=len(grouped[BESTIARY_MUNDANE]),
        bestiary_spooky=len(grouped[BESTIARY_SPOOKY]),
    )
    return values, stats


def build_pp_save(
    template_path: Path,
    output_path: Path,
    labels: dict[int, str],
    archive: PhotoArchive,
    catalog: EntityCatalog,
) -> ExportStats:
    if template_path.suffix.lower() != ".sav":
        raise SaveFormatError("Export requires a binary PP .sav template, not JSON.")
    parsed = _parse_binary(template_path)
    new_values, stats = compose_mapping_values(labels, archive, catalog)

    updated: set[str] = set()
    for entry in _custom_variables(parsed):
        properties = entry.get("properties", {})
        variable_field = _field(properties, "VariableID") or {}
        variable_id = variable_field.get("value", "")
        if variable_id not in new_values:
            continue
        string_field = _field(properties, "StringVal")
        if not isinstance(string_field, dict):
            raise SaveFormatError(f"{variable_id} has no StringVal field.")
        string_field["value"] = new_values[variable_id]
        string_field["size"] = len(new_values[variable_id].encode("utf-8")) + 5
        updated.add(variable_id)
    missing = set(ALL_MAPPING_VARIABLES) - updated
    if missing:
        raise SaveFormatError(f"Template is missing mapping variables: {', '.join(sorted(missing))}")

    writer = GvasWriter()
    writer.write_header(parsed["header"])
    writer.write_string(parsed["header"]["save_game_class"])
    for property_name, property_value in parsed["properties"].items():
        writer.write_property(property_name, property_value)
    writer.write_string("None")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(bytes(writer.data))

    written_values = _binary_mapping_values(_parse_binary(output_path))
    if any(written_values.get(key) != value for key, value in new_values.items()):
        output_path.unlink(missing_ok=True)
        raise SaveFormatError("Export verification failed; the incomplete output was removed.")
    return stats