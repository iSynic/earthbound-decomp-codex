from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import build_asset_bank_manifest
from build_asset_extraction_manifest import load_overworld_sprite_palette_registry
from build_overworld_sprite_preview_sheets import (
    RGBA,
    blank,
    paste,
    rel,
    slug,
    write_png_rgba,
)
from extract_assets import decode_snes_4bpp_tile_indices, palette_source_data
import rom_tools
from snes_palette import PaletteEntry, decode_snes_bgr555_palette


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FRAME_CONTRACT = ROOT / "notes" / "overworld-sprite-frame-contracts.json"
DEFAULT_SECONDARY_CONTRACT = ROOT / "notes" / "secondary-visual-descriptor-contracts.json"
DEFAULT_ASSET_ROOT = ROOT / "build" / "assets"
DEFAULT_YML = build_asset_bank_manifest.DEFAULT_YML
DEFAULT_OUT = ROOT / "build" / "overworld-sprite-composed-previews"
TILE_SIZE = 8
PIECE_SIZE = 16
CANVAS_PADDING = 32
BAND_COLORS = {
    "first_priority_band": (44, 134, 255, 255),
    "second_priority_band": (255, 181, 46, 255),
}
TERMINAL_MARKER_COLOR = (255, 72, 184, 255)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prototype composed overworld sprite previews from slot and secondary descriptor contracts."
    )
    parser.add_argument("--frame-contract", default=str(DEFAULT_FRAME_CONTRACT))
    parser.add_argument("--secondary-contract", default=str(DEFAULT_SECONDARY_CONTRACT))
    parser.add_argument("--asset-root", default=str(DEFAULT_ASSET_ROOT))
    parser.add_argument("--rom", default=None, help="EarthBound US ROM path.")
    parser.add_argument(
        "--yml",
        default=str(DEFAULT_YML),
        help="Path to refs/ebsrc-main/ebsrc-main/earthbound.yml for sprite palette ranges.",
    )
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument(
        "--group-id",
        action="append",
        type=int,
        default=[],
        help="Only render one overworld sprite id. Can be passed more than once.",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--slot-limit", type=int, default=None)
    parser.add_argument(
        "--show-priority-bands",
        action="store_true",
        help="Tint and outline pieces by the secondary descriptor header's two priority bands.",
    )
    parser.add_argument(
        "--show-trailing-markers",
        action="store_true",
        help="Mark pieces whose trailing byte has the pass-terminal bit set.",
    )
    parser.add_argument(
        "--palette-mode",
        choices=["sprite", "zero"],
        default="sprite",
        help="Use each sprite group's decoded OAM palette id, or force palette 0.",
    )
    parser.add_argument(
        "--palette-id",
        type=int,
        default=None,
        help="Force a specific overworld sprite palette id 0-7 for all groups.",
    )
    return parser.parse_args()


def signed_byte(value: int) -> int:
    return value - 0x100 if value >= 0x80 else value


def flip_horizontal(tile: list[list[RGBA]]) -> list[list[RGBA]]:
    return [list(reversed(row)) for row in tile]


def flip_vertical(tile: list[list[RGBA]]) -> list[list[RGBA]]:
    return list(reversed(tile))


def tint_image(rows: list[list[RGBA]], color: RGBA, alpha: int = 72) -> list[list[RGBA]]:
    tinted: list[list[RGBA]] = []
    for row in rows:
        out_row: list[RGBA] = []
        for red, green, blue, pixel_alpha in row:
            if pixel_alpha == 0:
                out_row.append((red, green, blue, pixel_alpha))
                continue
            out_row.append(
                (
                    ((red * (255 - alpha)) + (color[0] * alpha)) // 255,
                    ((green * (255 - alpha)) + (color[1] * alpha)) // 255,
                    ((blue * (255 - alpha)) + (color[2] * alpha)) // 255,
                    pixel_alpha,
                )
            )
        tinted.append(out_row)
    return tinted


def draw_rect(
    rows: list[list[RGBA]], left: int, top: int, width: int, height: int, color: RGBA
) -> None:
    right = left + width - 1
    bottom = top + height - 1
    for x in range(max(0, left), min(len(rows[0]), left + width)):
        if 0 <= top < len(rows):
            rows[top][x] = color
        if 0 <= bottom < len(rows):
            rows[bottom][x] = color
    for y in range(max(0, top), min(len(rows), top + height)):
        if 0 <= left < len(rows[0]):
            rows[y][left] = color
        if 0 <= right < len(rows[0]):
            rows[y][right] = color


def crop_tile(sheet: list[list[RGBA]], tile_index: int) -> list[list[RGBA]]:
    width = len(sheet[0])
    columns = width // TILE_SIZE
    if columns <= 0:
        raise ValueError("Tile sheet is too narrow")
    left = (tile_index % columns) * TILE_SIZE
    top = (tile_index // columns) * TILE_SIZE
    if top + TILE_SIZE > len(sheet):
        return blank(TILE_SIZE, TILE_SIZE, (0, 0, 0, 0))
    return [row[left : left + TILE_SIZE] for row in sheet[top : top + TILE_SIZE]]


def compose_metatile_16x16(sheet: list[list[RGBA]], chunk_index: int) -> list[list[RGBA]]:
    """Build one 16x16 piece from the extracted tile-preview stream."""
    base_tile_index = chunk_index * 4
    top_left = crop_tile(sheet, base_tile_index)
    top_right = crop_tile(sheet, base_tile_index + 1)
    bottom_left = crop_tile(sheet, base_tile_index + 2)
    bottom_right = crop_tile(sheet, base_tile_index + 3)
    rows = blank(PIECE_SIZE, PIECE_SIZE, (0, 0, 0, 0))
    paste(rows, top_left, 0, 0)
    paste(rows, top_right, TILE_SIZE, 0)
    paste(rows, bottom_left, 0, TILE_SIZE)
    paste(rows, bottom_right, TILE_SIZE, TILE_SIZE)
    return rows


def snes_4bpp_rgba_rows(raw_path: Path, palette_entries: list[PaletteEntry]) -> list[list[RGBA]]:
    indices = decode_snes_4bpp_tile_indices(raw_path.read_bytes(), columns=8)
    rows: list[list[RGBA]] = []
    for row in indices:
        out_row: list[RGBA] = []
        for color_index in row:
            if color_index >= len(palette_entries):
                raise ValueError(
                    f"{raw_path} uses color {color_index}, but palette only has "
                    f"{len(palette_entries)} colors"
                )
            entry = palette_entries[color_index]
            alpha = 0 if color_index == 0 else 255
            out_row.append((entry.red8, entry.green8, entry.blue8, alpha))
        rows.append(out_row)
    return rows


def oam_palette_id_from_group(group: dict[str, Any]) -> int:
    header = group["sprite_grouping_record"]["header"]
    if "oam_palette_id" in header:
        return int(header["oam_palette_id"])
    return (int(header["palette"]) >> 1) & 0x07


def group_base_oam_attribute_byte(group: dict[str, Any]) -> int:
    header = group["sprite_grouping_record"]["header"]
    return int(header.get("base_oam_attribute_byte", header["palette"]))


def palette_id_for_group(
    group: dict[str, Any], palette_mode: str, forced_palette_id: int | None
) -> int:
    if forced_palette_id is not None:
        return forced_palette_id
    if palette_mode == "zero":
        return 0
    return oam_palette_id_from_group(group)


def palette_entries_for_id(
    rom: bytes, palette_registry: dict[int, dict[str, Any]], palette_id: int
) -> tuple[list[PaletteEntry], dict[str, Any]]:
    palette_source = palette_registry.get(palette_id)
    if palette_source is None:
        raise ValueError(f"No overworld sprite palette source found for palette id {palette_id}")
    palette_data = palette_source_data(
        rom,
        {
            "palette_source": palette_source,
            "colors": 16,
        },
    )
    return decode_snes_bgr555_palette(palette_data, count=16), palette_source


def descriptor_by_index(secondary_contract: dict[str, Any]) -> dict[int, dict[str, Any]]:
    by_index: dict[int, dict[str, Any]] = {}
    by_address = {descriptor["address"]: descriptor for descriptor in secondary_contract["descriptors"]}
    for entry in secondary_contract["pointer_entries"]:
        by_index[int(entry["index"])] = by_address[entry["target"]]
    return by_index


def compose_slot(
    slot: dict[str, Any],
    descriptor: dict[str, Any],
    asset_root: Path,
    palette_entries: list[PaletteEntry],
    palette_id: int,
    palette_mode: str,
    palette_source: dict[str, Any],
    base_oam_attribute_byte: int,
    show_priority_bands: bool,
    show_trailing_markers: bool,
) -> tuple[list[list[RGBA]], dict[str, Any]]:
    raw_path = asset_root / slot["resolved_asset"]["raw_output"]
    source_sheet = snes_4bpp_rgba_rows(raw_path, palette_entries)
    pass_index = 1 if (int(slot["pointer_flags"]) & 0x01) else 0
    pieces = descriptor["body_passes"][pass_index]
    first_band_count = int(descriptor["header"]["first_priority_band_count"])
    second_band_count = int(descriptor["header"]["second_priority_band_count"])

    placed: list[tuple[list[list[RGBA]], int, int, dict[str, Any], str]] = []
    piece_metadata = []
    min_x = min_y = 0
    max_x = max_y = 0
    for piece in pieces:
        trailing_bits = piece.get("trailing_attribute_bits", {})
        is_terminal_piece = bool(trailing_bits.get("pass_terminal_piece_marker"))
        priority_band = (
            "first_priority_band"
            if int(piece["ordinal"]) < first_band_count
            else "second_priority_band"
        )
        tile_index = int(piece["source_tile_low_or_spatial_byte"]) // 2
        tile = compose_metatile_16x16(source_sheet, tile_index)
        if piece["attribute_bits"]["horizontal_flip"]:
            tile = flip_horizontal(tile)
        if piece["attribute_bits"]["vertical_flip"]:
            tile = flip_vertical(tile)
        if show_priority_bands:
            tile = tint_image(tile, BAND_COLORS[priority_band])
        x = signed_byte(int(piece["relative_x"]))
        y = signed_byte(int(piece["relative_y"]))
        min_x = min(min_x, x)
        min_y = min(min_y, y)
        max_x = max(max_x, x + PIECE_SIZE)
        max_y = max(max_y, y + PIECE_SIZE)
        placed.append((tile, x, y, piece, priority_band))
        piece_metadata.append(
            {
                "ordinal": piece["ordinal"],
                "contract_priority_band": priority_band,
                "relative_x": x,
                "relative_y": y,
                "source_tile_chunk_index": tile_index,
                "trailing_attribute": piece["trailing_attribute"],
                "is_pass_terminal_piece": is_terminal_piece,
            }
        )

    width = max(1, max_x - min_x) + (CANVAS_PADDING * 2)
    height = max(1, max_y - min_y) + (CANVAS_PADDING * 2)
    canvas = blank(width, height, (20, 22, 26, 0))
    for tile, x, y, _piece, priority_band in placed:
        left = x - min_x + CANVAS_PADDING
        top = y - min_y + CANVAS_PADDING
        paste(canvas, tile, left, top)
        if show_priority_bands:
            draw_rect(canvas, left, top, PIECE_SIZE, PIECE_SIZE, BAND_COLORS[priority_band])
        if show_trailing_markers and _piece.get("trailing_attribute_bits", {}).get(
            "pass_terminal_piece_marker"
        ):
            draw_rect(canvas, left, top, PIECE_SIZE, PIECE_SIZE, TERMINAL_MARKER_COLOR)

    return canvas, {
        "slot_index": slot["slot_index"],
        "direction_hint": slot.get("direction_hint"),
        "phase_hint": slot.get("phase_hint"),
        "pointer_flags": slot["pointer_flags"],
        "descriptor_pass_index": pass_index,
        "descriptor": descriptor["label"],
        "piece_count": len(pieces),
        "priority_band_counts": {
            "first_priority_band": first_band_count,
            "second_priority_band": second_band_count,
        },
        "pieces": piece_metadata,
        "source_asset": slot["resolved_asset"]["asset_id"],
        "source_range": slot["resolved_asset"]["source_range"],
        "source_raw_graphics": slot["resolved_asset"]["raw_output"],
        "piece_render_model": "16x16_metatile_from_extracted_tile_stream",
        "palette_render_model": "raw_4bpp_graphics_plus_overworld_sprite_palette",
        "palette_mode": palette_mode,
        "palette_id": palette_id,
        "palette_source_range": palette_source["range"],
        "base_oam_attribute_byte": f"${base_oam_attribute_byte:02X}",
        "priority_band_overlay": show_priority_bands,
        "trailing_marker_overlay": show_trailing_markers,
        "limitations": [],
    }


def build_group_sheet(
    group: dict[str, Any],
    descriptor: dict[str, Any],
    asset_root: Path,
    out_dir: Path,
    palette_entries: list[PaletteEntry],
    palette_id: int,
    palette_mode: str,
    palette_source: dict[str, Any],
    slot_limit: int | None,
    show_priority_bands: bool,
    show_trailing_markers: bool,
) -> dict[str, Any]:
    slots = group["runtime_slots"][:slot_limit]
    if not slots:
        return {
            "group": group["label"],
            "enum_name": group["enum_name"],
            "overworld_sprite_id": group["overworld_sprite_id"],
            "rendered": False,
            "secondary_descriptor_index": group["sprite_grouping_record"]["header"]["size_code"],
            "secondary_descriptor": descriptor["label"],
            "reason": "no_runtime_slots",
            "slots": [],
        }

    composed = []
    max_w = max_h = 1
    base_oam_attribute_byte = group_base_oam_attribute_byte(group)
    for slot in slots:
        image, metadata = compose_slot(
            slot,
            descriptor,
            asset_root,
            palette_entries,
            palette_id,
            palette_mode,
            palette_source,
            base_oam_attribute_byte,
            show_priority_bands,
            show_trailing_markers,
        )
        composed.append((image, metadata))
        max_w = max(max_w, len(image[0]))
        max_h = max(max_h, len(image))

    columns = min(8, max(1, len(composed)))
    rows = (len(composed) + columns - 1) // columns
    sheet = blank(columns * max_w, rows * max_h, (18, 20, 24, 255))
    slot_metadata = []
    for index, (image, metadata) in enumerate(composed):
        left = (index % columns) * max_w
        top = (index // columns) * max_h
        paste(sheet, image, left + ((max_w - len(image[0])) // 2), top + ((max_h - len(image)) // 2))
        metadata["cell"] = {"x": left, "y": top, "width": max_w, "height": max_h}
        slot_metadata.append(metadata)

    filename = f"{int(group['overworld_sprite_id']):04d}-{slug(group['label'])}.png"
    out_path = out_dir / filename
    write_png_rgba(out_path, sheet)
    return {
        "group": group["label"],
        "enum_name": group["enum_name"],
        "overworld_sprite_id": group["overworld_sprite_id"],
        "rendered": True,
        "secondary_descriptor_index": group["sprite_grouping_record"]["header"]["size_code"],
        "secondary_descriptor": descriptor["label"],
        "base_oam_attribute_byte": f"${base_oam_attribute_byte:02X}",
        "oam_palette_id": oam_palette_id_from_group(group),
        "rendered_palette_id": palette_id,
        "palette_mode": palette_mode,
        "palette_source_range": palette_source["range"],
        "priority_band_overlay": show_priority_bands,
        "trailing_marker_overlay": show_trailing_markers,
        "sheet": rel(out_path),
        "slots": slot_metadata,
    }


def main() -> int:
    args = parse_args()
    if args.palette_id is not None and not 0 <= args.palette_id <= 7:
        raise SystemExit("--palette-id must be in range 0..7")

    frame_contract = json.loads(Path(args.frame_contract).read_text(encoding="utf-8"))
    secondary_contract = json.loads(Path(args.secondary_contract).read_text(encoding="utf-8"))
    descriptors = descriptor_by_index(secondary_contract)
    asset_root = Path(args.asset_root)
    out_dir = Path(args.out)
    rom_path = rom_tools.find_rom(args.rom)
    rom = rom_tools.load_rom(rom_path)
    palette_registry = load_overworld_sprite_palette_registry(Path(args.yml), rom)

    groups = frame_contract["groups"]
    if args.group_id:
        wanted = set(args.group_id)
        groups = [group for group in groups if int(group["overworld_sprite_id"]) in wanted]
    if args.limit is not None:
        groups = groups[: args.limit]

    index = {
        "schema": "earthbound-decomp.overworld-sprite-composed-previews.v1",
        "source_policy": {
            "contains_rom_derived_outputs": True,
            "do_not_commit_generated_outputs": True,
        },
        "source_contracts": {
            "frame_contract": rel(Path(args.frame_contract)),
            "secondary_visual_descriptor_contract": rel(Path(args.secondary_contract)),
        },
        "output_root": rel(out_dir),
        "prototype_limitations": [
            "uses_secondary_visual_descriptor_piece_positions",
            "uses_pointer_bit0_to_select_descriptor_pass0_or_pass1",
            "renders_raw_4bpp_graphics_with_decoded_oam_palette_id",
            "uses_16x16_piece_chunks_from_extracted_tile_stream",
            "can_tint_contract_priority_bands_with_show_priority_bands",
            "can_mark_pass_terminal_pieces_with_show_trailing_markers",
        ],
        "render_options": {
            "show_priority_bands": args.show_priority_bands,
            "show_trailing_markers": args.show_trailing_markers,
            "palette_mode": args.palette_mode,
            "forced_palette_id": args.palette_id,
            "palette_source": rel(Path(args.yml)),
            "priority_band_colors": {
                key: f"#{red:02X}{green:02X}{blue:02X}"
                for key, (red, green, blue, _alpha) in BAND_COLORS.items()
            },
            "terminal_marker_color": f"#{TERMINAL_MARKER_COLOR[0]:02X}{TERMINAL_MARKER_COLOR[1]:02X}{TERMINAL_MARKER_COLOR[2]:02X}",
        },
        "groups": [],
    }
    for group in groups:
        descriptor_index = int(group["sprite_grouping_record"]["header"]["size_code"])
        descriptor = descriptors.get(descriptor_index)
        if descriptor is None:
            index["groups"].append(
                {
                    "group": group["label"],
                    "enum_name": group["enum_name"],
                    "overworld_sprite_id": group["overworld_sprite_id"],
                    "rendered": False,
                    "secondary_descriptor_index": descriptor_index,
                    "reason": "secondary_descriptor_index_not_in_contract",
                }
            )
            continue
        palette_id = palette_id_for_group(group, args.palette_mode, args.palette_id)
        palette_entries, palette_source = palette_entries_for_id(
            rom, palette_registry, palette_id
        )
        index["groups"].append(
            build_group_sheet(
                group,
                descriptor,
                asset_root,
                out_dir,
                palette_entries,
                palette_id,
                args.palette_mode,
                palette_source,
                args.slot_limit,
                args.show_priority_bands,
                args.show_trailing_markers,
            )
        )

    index_path = out_dir / "index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Rendered {len(index['groups'])} composed overworld sprite preview sheets.")
    print(f"Wrote {rel(index_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
