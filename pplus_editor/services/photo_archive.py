"""Extract the stable indexed photo array from a vanilla VotV sub-save."""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path

from ..models import PhotoArchive, PhotoRecord


class PhotoArchiveError(ValueError):
    """Raised when a file does not contain a valid supported photo array."""


PHOTO_PROPERTY_MARKER = b"\x07\x00\x00\x00photos\x00"
PHOTO_BYTES_FIELD = "bytes_3_E9E39AC546977B90F68795B3AFCC4D49"
PHOTO_BYTES_MARKER = struct.pack("<i", len(PHOTO_BYTES_FIELD) + 1) + PHOTO_BYTES_FIELD.encode() + b"\x00"


def _read_string(data: bytes, offset: int) -> tuple[str, int]:
    if offset + 4 > len(data):
        raise PhotoArchiveError("Unexpected end of file while reading a string length.")
    length = struct.unpack_from("<i", data, offset)[0]
    if length <= 0:
        raise PhotoArchiveError("Photo array contains an unsupported string encoding.")
    start = offset + 4
    end = start + length
    if end > len(data) or data[end - 1] != 0:
        raise PhotoArchiveError("Photo array contains a truncated string.")
    return data[start : end - 1].decode("utf-8"), end


def _photo_array_bounds(data: bytes) -> tuple[int, int, int]:
    property_start = data.find(PHOTO_PROPERTY_MARKER)
    if property_start < 0:
        raise PhotoArchiveError("Could not find the 'photos' array in this save.")

    property_name, offset = _read_string(data, property_start)
    property_type, offset = _read_string(data, offset)
    if property_name != "photos" or property_type != "ArrayProperty":
        raise PhotoArchiveError("The 'photos' property is not a supported array.")
    if offset + 8 > len(data):
        raise PhotoArchiveError("The photo array header is truncated.")
    value_size = struct.unpack_from("<Q", data, offset)[0]
    offset += 8
    element_type, offset = _read_string(data, offset)
    if element_type != "StructProperty":
        raise PhotoArchiveError(f"Unsupported photo element type: {element_type}")
    if offset >= len(data):
        raise PhotoArchiveError("The photo array header has no terminator.")
    value_start = offset + 1
    value_end = value_start + value_size
    if value_end > len(data) or value_size < 4:
        raise PhotoArchiveError("The photo array size extends beyond the save file.")
    expected_count = struct.unpack_from("<I", data, value_start)[0]
    return value_start, value_end, expected_count


def _photo_payloads(data: bytes, start: int, end: int) -> list[tuple[int, int]]:
    payloads: list[tuple[int, int]] = []
    offset = start
    while True:
        field_start = data.find(PHOTO_BYTES_MARKER, offset, end)
        if field_start < 0:
            break
        field_name, cursor = _read_string(data, field_start)
        property_type, cursor = _read_string(data, cursor)
        if field_name != PHOTO_BYTES_FIELD or property_type != "ArrayProperty":
            offset = field_start + 1
            continue
        if cursor + 8 > end:
            raise PhotoArchiveError("A photo byte-array header is truncated.")
        cursor += 8
        inner_type, cursor = _read_string(data, cursor)
        if inner_type != "ByteProperty" or cursor + 5 > end:
            raise PhotoArchiveError("A photo contains an unsupported byte-array value.")
        cursor += 1
        byte_count = struct.unpack_from("<I", data, cursor)[0]
        data_start = cursor + 4
        data_end = data_start + byte_count
        if data_end > end:
            raise PhotoArchiveError("A photo payload extends beyond the photo array.")
        payloads.append((data_start, byte_count))
        offset = data_end
    return payloads


def extract_photo_archive(save_path: Path, output_directory: Path) -> PhotoArchive:
    """Extract JPEG payloads and return metadata whose position is the PP index."""

    data = save_path.read_bytes()
    array_start, array_end, expected_count = _photo_array_bounds(data)
    payloads = _photo_payloads(data, array_start, array_end)
    if len(payloads) != expected_count:
        raise PhotoArchiveError(
            f"Photo array declares {expected_count} slots but {len(payloads)} were found."
        )

    output_directory.mkdir(parents=True, exist_ok=True)
    for old_photo in output_directory.glob("idx_*.jpg"):
        old_photo.unlink()

    photos: list[PhotoRecord] = []
    for index, (data_start, byte_count) in enumerate(payloads):
        filename = f"idx_{index:04d}.jpg" if byte_count else None
        if filename:
            (output_directory / filename).write_bytes(data[data_start : data_start + byte_count])
        photos.append(
            PhotoRecord(
                index=index,
                has_image=byte_count > 0,
                filename=filename,
            )
        )

    archive = PhotoArchive(
        source_path=save_path.resolve(),
        source_size=len(data),
        source_sha256=hashlib.sha256(data).hexdigest(),
        photos=tuple(photos),
    )
    return archive
