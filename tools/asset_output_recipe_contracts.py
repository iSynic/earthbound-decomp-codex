from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any


@dataclass(frozen=True)
class OutputRecipeContract:
    kind: str
    output_type: str
    decoder: str | None
    renderer: str | None
    required_fields: tuple[str, ...] = ()
    optional_fields: tuple[str, ...] = ()
    report_required_fields: tuple[str, ...] = ()
    extension: str | None = None


OUTPUT_RECIPE_CONTRACTS: dict[str, OutputRecipeContract] = {
    "raw": OutputRecipeContract(
        kind="raw",
        output_type="byte-for-byte extract",
        decoder=None,
        renderer=None,
    ),
    "earthbound_lzhal": OutputRecipeContract(
        kind="earthbound_lzhal",
        output_type="decompressed binary",
        decoder="earthbound_lzhal",
        renderer=None,
        report_required_fields=("compressed_bytes_consumed", "decompressed_bytes"),
    ),
    "map_tile_chunk_index_json": OutputRecipeContract(
        kind="map_tile_chunk_index_json",
        output_type="decoded map tile chunk index JSON",
        decoder="map_tile_chunk_index",
        renderer=None,
        required_fields=("chunk_index",),
        report_required_fields=(
            "chunk_index",
            "entry_count",
            "min_tile_id",
            "max_tile_id",
            "distinct_tile_ids",
        ),
        extension=".json",
    ),
    "battle_swirl_frame_json": OutputRecipeContract(
        kind="battle_swirl_frame_json",
        output_type="battle swirl frame metadata JSON",
        decoder="battle_swirl_frame_metadata",
        renderer=None,
        required_fields=(
            "swirl_id",
            "sequence_id",
            "sequence_frame_index",
            "sequence_speed",
            "sequence_frame_count",
        ),
        report_required_fields=(
            "swirl_id",
            "sequence_id",
            "sequence_frame_index",
            "sequence_speed",
            "sequence_frame_count",
            "payload_bytes",
            "first_opcode",
        ),
        extension=".json",
    ),
    "font_metric_widths_json": OutputRecipeContract(
        kind="font_metric_widths_json",
        output_type="font metric width table JSON",
        decoder="font_metric_widths",
        renderer=None,
        required_fields=("font_id", "entry_count", "first_character_code"),
        report_required_fields=(
            "font_id",
            "entry_count",
            "first_character_code",
            "max_width",
            "distinct_widths",
            "sentinel_ff_count",
        ),
        extension=".json",
    ),
    "snes_2bpp_tiles_png": OutputRecipeContract(
        kind="snes_2bpp_tiles_png",
        output_type="tile preview PNG",
        decoder="snes_2bpp_tiles",
        renderer="grayscale_tile_sheet",
        required_fields=("columns",),
        optional_fields=("trim_trailing_bytes",),
        report_required_fields=("width", "height", "tiles"),
        extension=".png",
    ),
    "snes_4bpp_tiles_png": OutputRecipeContract(
        kind="snes_4bpp_tiles_png",
        output_type="tile preview PNG",
        decoder="snes_4bpp_tiles",
        renderer="grayscale_tile_sheet",
        required_fields=("columns",),
        report_required_fields=("width", "height", "tiles"),
        extension=".png",
    ),
    "earthbound_lzhal_snes_4bpp_tiles_png": OutputRecipeContract(
        kind="earthbound_lzhal_snes_4bpp_tiles_png",
        output_type="decompressed tile preview PNG",
        decoder="earthbound_lzhal+snes_4bpp_tiles",
        renderer="grayscale_tile_sheet",
        required_fields=("columns",),
        report_required_fields=("compressed_bytes_consumed", "decompressed_bytes", "width", "height", "tiles"),
        extension=".png",
    ),
    "snes_4bpp_tiles_palette_png": OutputRecipeContract(
        kind="snes_4bpp_tiles_palette_png",
        output_type="palette-applied tile preview PNG",
        decoder="snes_4bpp_tiles+snes_palette",
        renderer="palette_tile_sheet",
        required_fields=("columns", "colors", "palette_source"),
        optional_fields=("sprite_id", "palette_id", "graphics_id"),
        report_required_fields=("colors", "palette_source_range", "width", "height", "tiles"),
        extension=".png",
    ),
    "earthbound_lzhal_snes_4bpp_tiles_palette_png": OutputRecipeContract(
        kind="earthbound_lzhal_snes_4bpp_tiles_palette_png",
        output_type="decompressed palette-applied tile preview PNG",
        decoder="earthbound_lzhal+snes_4bpp_tiles+snes_palette",
        renderer="palette_tile_sheet",
        required_fields=("columns", "colors", "palette_source"),
        optional_fields=("sprite_id", "palette_id", "graphics_id"),
        report_required_fields=(
            "compressed_bytes_consumed",
            "decompressed_bytes",
            "colors",
            "palette_source_range",
            "width",
            "height",
            "tiles",
        ),
        extension=".png",
    ),
    "snes_palette_json": OutputRecipeContract(
        kind="snes_palette_json",
        output_type="decoded SNES palette JSON",
        decoder="snes_palette",
        renderer=None,
        report_required_fields=("colors",),
        extension=".json",
    ),
    "snes_palette_swatch_png": OutputRecipeContract(
        kind="snes_palette_swatch_png",
        output_type="palette swatch PNG",
        decoder="snes_palette",
        renderer="palette_swatch",
        required_fields=("per_row", "swatch"),
        report_required_fields=("colors", "width", "height"),
        extension=".png",
    ),
    "earthbound_lzhal_snes_palette_json": OutputRecipeContract(
        kind="earthbound_lzhal_snes_palette_json",
        output_type="decompressed SNES palette JSON",
        decoder="earthbound_lzhal+snes_palette",
        renderer=None,
        report_required_fields=("compressed_bytes_consumed", "decompressed_bytes", "colors"),
        extension=".json",
    ),
    "earthbound_lzhal_snes_palette_swatch_png": OutputRecipeContract(
        kind="earthbound_lzhal_snes_palette_swatch_png",
        output_type="decompressed palette swatch PNG",
        decoder="earthbound_lzhal+snes_palette",
        renderer="palette_swatch",
        required_fields=("per_row", "swatch"),
        report_required_fields=("compressed_bytes_consumed", "decompressed_bytes", "colors", "width", "height"),
        extension=".png",
    ),
    "earthbound_lzhal_battle_bg_arrangement_png": OutputRecipeContract(
        kind="earthbound_lzhal_battle_bg_arrangement_png",
        output_type="composed battle-background PNG",
        decoder="earthbound_lzhal+snes_tilemap+snes_tiles+snes_palette",
        renderer="battle_background_arrangement",
        required_fields=(
            "width_tiles",
            "height_tiles",
            "bpp",
            "colors",
            "arrangement_id",
            "graphics_id",
            "palette_id",
            "graphics_source",
            "palette_source",
        ),
        report_required_fields=(
            "compressed_bytes_consumed",
            "decompressed_bytes",
            "colors",
            "graphics_source_range",
            "palette_source_range",
            "bpp",
            "max_tile",
            "width",
            "height",
        ),
        extension=".png",
    ),
    "earthbound_lzhal_battle_sprite_png": OutputRecipeContract(
        kind="earthbound_lzhal_battle_sprite_png",
        output_type="composed battle-sprite PNG",
        decoder="earthbound_lzhal+snes_4bpp_tiles+snes_palette",
        renderer="battle_sprite",
        required_fields=("width", "height", "colors", "sprite_id", "palette_id", "palette_source"),
        report_required_fields=(
            "compressed_bytes_consumed",
            "decompressed_bytes",
            "colors",
            "palette_source_range",
            "sprite_id",
            "palette_id",
            "width",
            "height",
        ),
        extension=".png",
    ),
}


INT_FIELDS = {
    "arrangement_id",
    "bpp",
    "chunk_index",
    "colors",
    "columns",
    "entry_count",
    "first_character_code",
    "font_id",
    "graphics_id",
    "height",
    "height_tiles",
    "palette_id",
    "per_row",
    "sprite_id",
    "swatch",
    "sequence_frame_count",
    "sequence_frame_index",
    "sequence_id",
    "sequence_speed",
    "trim_trailing_bytes",
    "width",
    "width_tiles",
}

SOURCE_FIELDS = {"graphics_source", "palette_source"}
BASE_FIELDS = {"kind", "path"}
SHA1_RE = re.compile(r"[0-9a-f]{40}")
RANGE_RE = re.compile(r"[0-9A-Fa-f]{2}:[0-9A-Fa-f]{4}\.\.[0-9A-Fa-f]{2}:[0-9A-Fa-f]{4}")


def output_kind_contract(kind: str) -> OutputRecipeContract | None:
    return OUTPUT_RECIPE_CONTRACTS.get(kind)


def validate_output_path(path: Any) -> list[str]:
    if not isinstance(path, str) or not path:
        return ["output path must be a non-empty string"]
    if "\\" in path:
        return [f"output path must use manifest POSIX separators: {path!r}"]
    posix_path = PurePosixPath(path)
    if posix_path.is_absolute() or ".." in posix_path.parts:
        return [f"output path must stay relative to the output root: {path!r}"]
    return []


def validate_source_ref(source: Any, field: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(source, dict):
        return [f"{field} must be an object"]
    if source.get("type") != "rom-range":
        errors.append(f"{field}.type must be 'rom-range'")
    range_text = source.get("range")
    if not isinstance(range_text, str) or RANGE_RE.fullmatch(range_text) is None:
        errors.append(f"{field}.range must be BB:AAAA..BB:AAAA")
    bytes_value = source.get("bytes")
    if not isinstance(bytes_value, int) or bytes_value <= 0:
        errors.append(f"{field}.bytes must be a positive integer")
    sha1 = source.get("sha1")
    if not isinstance(sha1, str) or SHA1_RE.fullmatch(sha1) is None:
        errors.append(f"{field}.sha1 must be a lowercase 40-character SHA-1")
    compression = source.get("compression")
    if compression is not None and compression != "earthbound_lzhal":
        errors.append(f"{field}.compression is unsupported: {compression!r}")
    allowed = {"type", "range", "bytes", "sha1", "compression"}
    for key in sorted(set(source) - allowed):
        errors.append(f"{field}.{key} is not part of the typed source contract")
    return errors


def validate_output_spec(output: dict[str, Any], asset_id: str) -> list[str]:
    errors: list[str] = []
    kind = output.get("kind")
    if not isinstance(kind, str):
        return [f"{asset_id}: output kind must be a string"]

    contract = output_kind_contract(kind)
    if contract is None:
        return [f"{asset_id}: unsupported output kind {kind!r}"]

    errors.extend(f"{asset_id}: {error}" for error in validate_output_path(output.get("path")))
    if contract.extension is not None:
        path = str(output.get("path", ""))
        if PurePosixPath(path).suffix.lower() != contract.extension:
            errors.append(f"{asset_id}: {kind} output path must end with {contract.extension}")

    allowed_fields = BASE_FIELDS | set(contract.required_fields) | set(contract.optional_fields)
    for key in sorted(set(output) - allowed_fields):
        errors.append(f"{asset_id}: {kind} has unsupported field {key!r}")

    for field in contract.required_fields:
        if field not in output:
            errors.append(f"{asset_id}: {kind} missing required field {field!r}")

    for field in sorted((set(contract.required_fields) | set(contract.optional_fields)) & INT_FIELDS):
        if field in output and (not isinstance(output[field], int) or output[field] < 0):
            errors.append(f"{asset_id}: {kind}.{field} must be a non-negative integer")
    for field in {
        "columns",
        "colors",
        "entry_count",
        "height",
        "height_tiles",
        "per_row",
        "swatch",
        "width",
        "width_tiles",
    }:
        if field in output and isinstance(output[field], int) and output[field] <= 0:
            errors.append(f"{asset_id}: {kind}.{field} must be positive")
    if "bpp" in output and output["bpp"] not in {2, 4}:
        errors.append(f"{asset_id}: {kind}.bpp must be 2 or 4")
    if "colors" in output and output["colors"] not in {4, 16}:
        errors.append(f"{asset_id}: {kind}.colors must be 4 or 16")
    if "width" in output and isinstance(output["width"], int) and output["width"] % 8 != 0:
        errors.append(f"{asset_id}: {kind}.width must be a tile multiple")
    if "height" in output and isinstance(output["height"], int) and output["height"] % 8 != 0:
        errors.append(f"{asset_id}: {kind}.height must be a tile multiple")

    for field in sorted((set(contract.required_fields) | set(contract.optional_fields)) & SOURCE_FIELDS):
        if field in output:
            errors.extend(f"{asset_id}: {error}" for error in validate_source_ref(output[field], field))

    return errors
