from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from build_overworld_sprite_preview_sheets import (
    RGBA,
    blank,
    paste,
    read_png_rgba,
    rel,
    slug,
    write_png_rgba,
)


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FRAME_CONTRACT = ROOT / "notes" / "overworld-sprite-frame-contracts.json"
DEFAULT_SECONDARY_CONTRACT = ROOT / "notes" / "secondary-visual-descriptor-contracts.json"
DEFAULT_ASSET_ROOT = ROOT / "build" / "assets"
DEFAULT_OUT = ROOT / "build" / "overworld-sprite-composed-previews"
TILE_SIZE = 8
CANVAS_PADDING = 32


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prototype composed overworld sprite previews from slot and secondary descriptor contracts."
    )
    parser.add_argument("--frame-contract", default=str(DEFAULT_FRAME_CONTRACT))
    parser.add_argument("--secondary-contract", default=str(DEFAULT_SECONDARY_CONTRACT))
    parser.add_argument("--asset-root", default=str(DEFAULT_ASSET_ROOT))
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
    return parser.parse_args()


def signed_byte(value: int) -> int:
    return value - 0x100 if value >= 0x80 else value


def flip_horizontal(tile: list[list[RGBA]]) -> list[list[RGBA]]:
    return [list(reversed(row)) for row in tile]


def flip_vertical(tile: list[list[RGBA]]) -> list[list[RGBA]]:
    return list(reversed(tile))


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
) -> tuple[list[list[RGBA]], dict[str, Any]]:
    preview = asset_root / slot["resolved_asset"]["palette_00_preview"]
    source_sheet = read_png_rgba(preview)
    pass_index = 1 if (int(slot["pointer_flags"]) & 0x01) else 0
    pieces = descriptor["body_passes"][pass_index]

    placed: list[tuple[list[list[RGBA]], int, int, dict[str, Any]]] = []
    min_x = min_y = 0
    max_x = max_y = 0
    for piece in pieces:
        tile_index = int(piece["source_tile_low_or_spatial_byte"]) // 2
        tile = crop_tile(source_sheet, tile_index)
        if piece["attribute_bits"]["horizontal_flip"]:
            tile = flip_horizontal(tile)
        if piece["attribute_bits"]["vertical_flip"]:
            tile = flip_vertical(tile)
        x = signed_byte(int(piece["relative_x"]))
        y = signed_byte(int(piece["relative_y"]))
        min_x = min(min_x, x)
        min_y = min(min_y, y)
        max_x = max(max_x, x + TILE_SIZE)
        max_y = max(max_y, y + TILE_SIZE)
        placed.append((tile, x, y, piece))

    width = max(1, max_x - min_x) + (CANVAS_PADDING * 2)
    height = max(1, max_y - min_y) + (CANVAS_PADDING * 2)
    canvas = blank(width, height, (20, 22, 26, 0))
    for tile, x, y, _piece in placed:
        paste(canvas, tile, x - min_x + CANVAS_PADDING, y - min_y + CANVAS_PADDING)

    return canvas, {
        "slot_index": slot["slot_index"],
        "direction_hint": slot.get("direction_hint"),
        "phase_hint": slot.get("phase_hint"),
        "pointer_flags": slot["pointer_flags"],
        "descriptor_pass_index": pass_index,
        "descriptor": descriptor["label"],
        "piece_count": len(pieces),
        "source_asset": slot["resolved_asset"]["asset_id"],
        "source_range": slot["resolved_asset"]["source_range"],
        "limitations": [
            "prototype_uses_8x8_piece_crops_only",
            "does_not_yet_apply_sprite_size_bits_from_trailing_attribute",
            "does_not_yet_apply_palette_variants_or_priority_bands_visually",
        ],
    }


def build_group_sheet(
    group: dict[str, Any],
    descriptor: dict[str, Any],
    asset_root: Path,
    out_dir: Path,
    slot_limit: int | None,
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
    for slot in slots:
        image, metadata = compose_slot(slot, descriptor, asset_root)
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
        "sheet": rel(out_path),
        "slots": slot_metadata,
    }


def main() -> int:
    args = parse_args()
    frame_contract = json.loads(Path(args.frame_contract).read_text(encoding="utf-8"))
    secondary_contract = json.loads(Path(args.secondary_contract).read_text(encoding="utf-8"))
    descriptors = descriptor_by_index(secondary_contract)
    asset_root = Path(args.asset_root)
    out_dir = Path(args.out)

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
            "uses_raw_palette_00_tile_previews",
            "does_not_yet_apply_16x16_or_large_sprite_size_bits",
            "does_not_yet_render_priority_bands_separately",
        ],
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
        index["groups"].append(
            build_group_sheet(group, descriptor, asset_root, out_dir, args.slot_limit)
        )

    index_path = out_dir / "index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Rendered {len(index['groups'])} composed overworld sprite preview sheets.")
    print(f"Wrote {rel(index_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
