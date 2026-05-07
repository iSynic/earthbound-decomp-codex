from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import extract_assets
from asset_output_recipe_contracts import OUTPUT_RECIPE_CONTRACTS


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "build" / "asset-output-codec-validation"
DEFAULT_JSON_OUT = ROOT / "build" / "asset-output-codec-validation.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "asset-output-codec-validation.md"
PALETTE_RANGE = "C0:1000..C0:1020"
GRAPHICS_RANGE = "C0:2000..C0:2040"
ROM_SIZE = 0x30000


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def literal_lzhal(data: bytes) -> bytes:
    payload = bytearray()
    cursor = 0
    while cursor < len(data):
        chunk = data[cursor : cursor + 32]
        payload.append(len(chunk) - 1)
        payload.extend(chunk)
        cursor += len(chunk)
    payload.append(0xFF)
    return bytes(payload)


def snes_color(red5: int, green5: int, blue5: int) -> int:
    return (red5 & 0x1F) | ((green5 & 0x1F) << 5) | ((blue5 & 0x1F) << 10)


def palette_bytes(colors: int = 16) -> bytes:
    data = bytearray()
    for index in range(colors):
        raw = snes_color(index * 2, 31 - index, (index * 3) & 0x1F)
        data.extend(raw.to_bytes(2, "little"))
    return bytes(data)


def encode_2bpp_tile(seed: int = 0) -> bytes:
    data = bytearray()
    for y in range(8):
        low = 0
        high = 0
        for x in range(8):
            color = (x + y + seed) & 0x03
            bit = 7 - x
            low |= (color & 0x01) << bit
            high |= ((color >> 1) & 0x01) << bit
        data.extend((low, high))
    return bytes(data)


def encode_4bpp_tile(seed: int = 0) -> bytes:
    plane01 = bytearray()
    plane23 = bytearray()
    for y in range(8):
        p0 = p1 = p2 = p3 = 0
        for x in range(8):
            color = (x + y + seed) & 0x0F
            bit = 7 - x
            p0 |= (color & 0x01) << bit
            p1 |= ((color >> 1) & 0x01) << bit
            p2 |= ((color >> 2) & 0x01) << bit
            p3 |= ((color >> 3) & 0x01) << bit
        plane01.extend((p0, p1))
        plane23.extend((p2, p3))
    return bytes(plane01 + plane23)


def make_4bpp_tiles(count: int) -> bytes:
    return b"".join(encode_4bpp_tile(index) for index in range(count))


def make_2bpp_tiles(count: int) -> bytes:
    return b"".join(encode_2bpp_tile(index) for index in range(count))


def make_arrangement(width_tiles: int, height_tiles: int, tile_count: int) -> bytes:
    data = bytearray()
    for index in range(width_tiles * height_tiles):
        data.extend((index % tile_count).to_bytes(2, "little"))
    return bytes(data)


def source_ref(range_text: str, data: bytes) -> dict[str, Any]:
    return {
        "type": "rom-range",
        "range": range_text,
        "bytes": len(data),
        "sha1": hashlib.sha1(data).hexdigest(),
    }


def make_text_window_properties_table() -> bytes:
    data = bytearray(495)
    selector_offsets = [0x0000, 0x0040, 0x0080, 0x00C0, 0x0100]
    for index, offset in enumerate(selector_offsets):
        cursor = index * 3
        data[cursor : cursor + 2] = offset.to_bytes(2, "little")
        data[cursor + 2] = 0x01 if index == 0 else 0x08

    palette_base = 0x000F
    for block in range(7):
        for row in range(8):
            for color in range(4):
                raw = snes_color((block + color) & 0x1F, (row + color) & 0x1F, (block + row + color) & 0x1F)
                cursor = palette_base + block * 0x40 + row * 8 + color * 2
                data[cursor : cursor + 2] = raw.to_bytes(2, "little")

    movement_palette = 0x01CF
    for color, raw in enumerate([0x0000, 0x4651, 0x4651, 0x6FFF]):
        cursor = movement_palette + color * 2
        data[cursor : cursor + 2] = raw.to_bytes(2, "little")

    pointer_offset = 0x01D7
    pointers = [0x21A8, 0x4920, 0x6721, 0x8379, 0xADB4, 0xC7F1]
    for index, pointer in enumerate(pointers):
        cursor = pointer_offset + index * 4
        data[cursor : cursor + 2] = pointer.to_bytes(2, "little")
        data[cursor + 2] = 0xE0
        data[cursor + 3] = 0
    return bytes(data)


def make_town_map_icon_table() -> bytes:
    data = bytearray(894)

    descriptor_starts = [index * 5 for index in range(22)]
    for list_index, start in enumerate(descriptor_starts):
        data[start] = (list_index * 2) & 0x7F
        data[start + 1 : start + 3] = (0x2000 + list_index).to_bytes(2, "little")
        data[start + 3] = (list_index * 3) & 0x7F
        data[start + 4] = 0x81 if list_index % 2 else 0x80

    icon_pointer_offset = 0x0249
    for icon_id in range(23):
        descriptor_start = descriptor_starts[icon_id if icon_id < 22 else 0]
        pointer = 0xF203 + descriptor_start
        cursor = icon_pointer_offset + icon_id * 2
        data[cursor : cursor + 2] = pointer.to_bytes(2, "little")

    blink_offset = 0x0277
    for icon_id in range(23):
        data[blink_offset + icon_id] = 1 if icon_id < 16 else 0

    placement_pointer_offset = 0x028E
    placement_targets = [0xF4A9, 0xF4CD, 0xF4F6, 0xF524, 0xF548, 0xF562]
    placement_counts = [7, 8, 9, 7, 5, 6]
    for town_map_index, target in enumerate(placement_targets):
        cursor = placement_pointer_offset + town_map_index * 4
        data[cursor : cursor + 2] = target.to_bytes(2, "little")
        data[cursor + 2] = 0xE1
        data[cursor + 3] = 0

        list_cursor = target - 0xF203
        for record_index in range(placement_counts[town_map_index]):
            data[list_cursor] = 8 + record_index
            data[list_cursor + 1] = 16 + town_map_index
            data[list_cursor + 2] = record_index % 23
            event_flag = (0x8000 if record_index % 2 else 0) | (0x100 + town_map_index * 16 + record_index)
            data[list_cursor + 3 : list_cursor + 5] = event_flag.to_bytes(2, "little")
            list_cursor += 5
        data[list_cursor] = 0xFF

    return bytes(data)


def make_photographer_config_table() -> bytes:
    data = bytearray(32 * 0x3E)
    for record_index in range(32):
        base = record_index * 0x3E
        data[base : base + 2] = (0x0200 + record_index).to_bytes(2, "little")
        data[base + 2 : base + 4] = (0x0010 + record_index).to_bytes(2, "little")
        data[base + 4 : base + 6] = (0x0020 + record_index).to_bytes(2, "little")
        background_offset = 0x4000 + record_index * 0x10 if record_index % 2 else 0
        data[base + 6 : base + 8] = background_offset.to_bytes(2, "little")
        data[base + 8] = record_index & 0xFF
        data[base + 9] = (record_index + 1) & 0xFF
        data[base + 0x0A : base + 0x0C] = (0x0030 + record_index).to_bytes(2, "little")
        data[base + 0x0C : base + 0x0E] = (0x0040 + record_index).to_bytes(2, "little")

        data[base + 0x0E : base + 0x10] = (0x0050 + record_index).to_bytes(2, "little")
        data[base + 0x10 : base + 0x12] = (0x0060 + record_index).to_bytes(2, "little")
        if record_index % 3 == 0:
            data[base + 0x12 : base + 0x14] = (0x0070 + record_index).to_bytes(2, "little")
            data[base + 0x14 : base + 0x16] = (0x0080 + record_index).to_bytes(2, "little")

        if record_index % 4 == 0:
            data[base + 0x26 : base + 0x28] = (0x0090 + record_index).to_bytes(2, "little")
            data[base + 0x28 : base + 0x2A] = (0x00A0 + record_index).to_bytes(2, "little")
            data[base + 0x2A : base + 0x2C] = (0x0100 + record_index).to_bytes(2, "little")

    return bytes(data)


def make_map_sector_music_table() -> bytes:
    data = bytearray()
    for sector_x in range(80):
        for sector_y in range(32):
            data.append((sector_x * 3 + sector_y) % 17)
    return bytes(data)


def make_map_palette_pointer_table() -> bytes:
    data = bytearray()
    for palette_id in range(32):
        pointer = (0xDA << 16) | (0x8000 + palette_id * 0x40)
        data.extend(pointer.to_bytes(3, "little"))
    return bytes(data)


def synthetic_rom(palette: bytes, graphics: bytes) -> bytes:
    rom = bytearray(ROM_SIZE)
    palette_offset = 0x1000
    graphics_offset = 0x2000
    rom[palette_offset : palette_offset + len(palette)] = palette
    rom[graphics_offset : graphics_offset + len(graphics)] = graphics
    return bytes(rom)


def output_cases() -> list[dict[str, Any]]:
    palette = palette_bytes()
    graphics_4bpp = make_4bpp_tiles(2)
    graphics_2bpp = make_2bpp_tiles(2)
    battle_sprite = make_4bpp_tiles(4)
    arrangement = make_arrangement(2, 2, tile_count=2)
    return [
        {
            "id": "raw-bytes",
            "data": b"raw fixture bytes",
            "spec": {"kind": "raw", "path": "raw.bin"},
        },
        {
            "id": "earthbound-lzhal",
            "data": literal_lzhal(b"decompressed fixture bytes"),
            "spec": {"kind": "earthbound_lzhal", "path": "decoded.bin"},
        },
        {
            "id": "map-tile-chunk-index",
            "data": bytes([0x00, 0x00, 0x25, 0x00, 0xAA, 0x00, 0x25, 0x00]),
            "spec": {"kind": "map_tile_chunk_index_json", "path": "map_tile_chunk.json", "chunk_index": 1},
            "expected_metadata": {
                "chunk_index": 1,
                "entry_count": 4,
                "min_tile_id": 0,
                "max_tile_id": 170,
                "distinct_tile_ids": 3,
            },
        },
        {
            "id": "map-sector-music-table",
            "data": make_map_sector_music_table(),
            "spec": {
                "kind": "map_sector_music_table_json",
                "path": "map_sector_music.json",
                "column_count": 80,
                "row_count": 32,
            },
            "expected_metadata": {
                "sector_count": 2560,
                "distinct_entry_count": 17,
                "min_entry_id": 0,
                "max_entry_id": 16,
            },
        },
        {
            "id": "map-palette-pointer-table",
            "data": make_map_palette_pointer_table(),
            "spec": {
                "kind": "map_palette_pointer_table_json",
                "path": "map_palette_pointers.json",
                "entry_count": 32,
                "pointer_bank": 0xDA,
            },
            "expected_metadata": {
                "entry_count": 32,
                "pointer_bank": 0xDA,
                "distinct_pointers": 32,
                "distinct_target_banks": 1,
                "sequential_palette_id_count": 32,
            },
        },
        {
            "id": "battle-swirl-frame-metadata",
            "data": bytes([0x04, 0x5E, 0xFF, 0x00, 0xFF, 0x00, 0x91, 0x82]),
            "spec": {
                "kind": "battle_swirl_frame_json",
                "path": "battle_swirl_frame.json",
                "swirl_id": 4,
                "sequence_id": 1,
                "sequence_frame_index": 4,
                "sequence_speed": 2,
                "sequence_frame_count": 23,
            },
            "expected_metadata": {
                "swirl_id": 4,
                "sequence_id": 1,
                "sequence_frame_index": 4,
                "sequence_speed": 2,
                "sequence_frame_count": 23,
                "payload_bytes": 8,
                "first_opcode": 4,
            },
        },
        {
            "id": "battle-swirl-pointer-table",
            "data": bytes([0x14, 0x69, 0x1C, 0x69, 0x33, 0x69]),
            "spec": {
                "kind": "battle_swirl_pointer_table_json",
                "path": "battle_swirl_pointers.json",
                "entry_count": 3,
                "pointer_bank": 0xCE,
            },
            "expected_metadata": {
                "entry_count": 3,
                "pointer_bank": 0xCE,
                "min_pointer": 0x6914,
                "max_pointer": 0x6933,
                "distinct_pointers": 3,
            },
        },
        {
            "id": "battle-swirl-sequence-table",
            "data": bytes([0, 0, 0, 0, 2, 0, 3, 0, 4, 3, 2, 0]),
            "spec": {
                "kind": "battle_swirl_sequence_table_json",
                "path": "battle_swirl_sequences.json",
                "row_count": 3,
            },
            "expected_metadata": {
                "row_count": 3,
                "visible_sequence_count": 2,
                "total_frame_count": 5,
                "max_sequence_speed": 4,
            },
        },
        {
            "id": "battle-bg-pointer-table",
            "data": bytes(
                [
                    0x97,
                    0xD8,
                    0xCB,
                    0x00,
                    0xD4,
                    0xA5,
                    0xCB,
                    0x00,
                    0x00,
                    0x80,
                    0xCA,
                    0x00,
                ]
            ),
            "spec": {
                "kind": "battle_bg_pointer_table_json",
                "path": "battle_bg_pointers.json",
                "entry_count": 3,
                "table_id": 0,
                "table_role": "graphics",
            },
            "expected_metadata": {
                "entry_count": 3,
                "min_pointer": 0xCA8000,
                "max_pointer": 0xCBD897,
                "distinct_pointers": 3,
                "distinct_banks": 2,
            },
        },
        {
            "id": "battle-bg-config-table",
            "data": bytes(
                [
                    0x01,
                    0x02,
                    0x04,
                    0x03,
                    0x01,
                    0x03,
                    0x00,
                    0x00,
                    0x08,
                    0x4C,
                    0x00,
                    0x00,
                    0x00,
                    0x3C,
                    0x00,
                    0x00,
                    0x00,
                ]
            ),
            "spec": {
                "kind": "battle_bg_config_table_json",
                "path": "battle_bg_config.json",
                "row_count": 1,
            },
            "expected_metadata": {
                "row_count": 1,
                "max_graphics_index": 1,
                "max_palette_index": 2,
                "max_scrolling_movement": 0x4C,
                "max_distortion_style": 0x3C,
            },
        },
        {
            "id": "battle-bg-scrolling-table",
            "data": bytes([0xB4, 0x00, 0x00, 0xFF, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00]),
            "spec": {
                "kind": "battle_bg_scrolling_table_json",
                "path": "battle_bg_scrolling.json",
                "row_count": 1,
            },
            "expected_metadata": {
                "row_count": 1,
                "max_duration": 180,
                "nonzero_duration_count": 1,
                "distinct_motion_vectors": 1,
            },
        },
        {
            "id": "battle-bg-distortion-table",
            "data": bytes(
                [
                    0x78,
                    0x00,
                    0x04,
                    0x00,
                    0x02,
                    0x00,
                    0x20,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x01,
                    0x0A,
                    0x00,
                ]
            ),
            "spec": {
                "kind": "battle_bg_distortion_table_json",
                "path": "battle_bg_distortion.json",
                "row_count": 1,
            },
            "expected_metadata": {
                "row_count": 1,
                "max_duration": 120,
                "nonzero_duration_count": 1,
                "distinct_distortion_types": 1,
            },
        },
        {
            "id": "battle-bg-layer-table",
            "data": bytes([0x06, 0x01, 0x00, 0x00, 0xCB, 0x00, 0xCA, 0x00, 0x00, 0x00, 0x00, 0x00]),
            "spec": {
                "kind": "battle_bg_layer_table_json",
                "path": "battle_bg_layers.json",
                "row_count": 3,
                "config_row_count": 327,
            },
            "expected_metadata": {
                "row_count": 3,
                "max_layer_config_index": 262,
                "distinct_layer_refs": 3,
                "two_layer_entry_count": 1,
            },
        },
        {
            "id": "battle-sprite-pointer-table",
            "data": bytes(
                [
                    0x6D,
                    0x60,
                    0xCE,
                    0x00,
                    0x01,
                    0x02,
                    0xB8,
                    0xCD,
                    0x00,
                    0x04,
                    0x00,
                    0x00,
                    0xCD,
                    0x00,
                    0x06,
                ]
            ),
            "spec": {
                "kind": "battle_sprite_pointer_table_json",
                "path": "battle_sprite_pointers.json",
                "entry_count": 3,
            },
            "expected_metadata": {
                "entry_count": 3,
                "max_width": 128,
                "max_height": 128,
                "distinct_size_codes": 3,
                "distinct_banks": 2,
            },
        },
        {
            "id": "psi-animation-config-table",
            "data": bytes(
                [
                    0x27,
                    0xDB,
                    0x05,
                    0x03,
                    0x01,
                    0x02,
                    0x2F,
                    0x02,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x25,
                    0xAC,
                    0x04,
                    0x02,
                    0x01,
                    0x03,
                    0x13,
                    0x00,
                    0x05,
                    0x06,
                    0x00,
                    0x7C,
                ]
            ),
            "spec": {
                "kind": "psi_anim_config_table_json",
                "path": "psi_anim_config.json",
                "row_count": 2,
            },
            "expected_metadata": {
                "row_count": 2,
                "max_frame_hold_frames": 5,
                "max_total_frames": 47,
                "distinct_target_modes": 2,
                "nonzero_enemy_colour_count": 1,
            },
        },
        {
            "id": "psi-animation-pointer-table",
            "data": bytes([0x27, 0xDB, 0xCC, 0x00, 0x25, 0xAC, 0xCC, 0x00]),
            "spec": {
                "kind": "psi_anim_pointer_table_json",
                "path": "psi_anim_pointers.json",
                "entry_count": 2,
            },
            "expected_metadata": {
                "entry_count": 2,
                "min_pointer": 0xCCAC25,
                "max_pointer": 0xCCDB27,
                "distinct_pointers": 2,
                "distinct_banks": 1,
            },
        },
        {
            "id": "animation-sequence-pointer-table",
            "data": bytes(
                [
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0xE9,
                    0x2B,
                    0xCC,
                    0x00,
                    0x10,
                    0x1C,
                    0x06,
                    0x03,
                    0xF0,
                    0x2C,
                    0xCC,
                    0x00,
                    0xA0,
                    0x05,
                    0x07,
                    0x10,
                ]
            ),
            "spec": {
                "kind": "animation_sequence_pointer_table_json",
                "path": "animation_sequence_pointers.json",
                "row_count": 3,
            },
            "expected_metadata": {
                "row_count": 3,
                "nonnull_pointer_count": 2,
                "max_parameter_byte": 0xA0,
                "distinct_pointer_banks": 1,
            },
        },
        {
            "id": "font-metric-widths",
            "data": bytes([2, 3, 4, 0xFF, 6, 7]),
            "spec": {
                "kind": "font_metric_widths_json",
                "path": "font_widths.json",
                "font_id": 0,
                "entry_count": 6,
                "first_character_code": 0x50,
            },
            "expected_metadata": {
                "font_id": 0,
                "entry_count": 6,
                "first_character_code": 0x50,
                "max_width": 0xFF,
                "distinct_widths": 6,
                "sentinel_ff_count": 1,
            },
        },
        {
            "id": "text-window-properties-table",
            "data": make_text_window_properties_table(),
            "spec": {
                "kind": "text_window_properties_table_json",
                "path": "text_window_properties.json",
                "selector_count": 5,
                "palette_block_count": 7,
                "town_map_pointer_count": 6,
            },
            "expected_metadata": {
                "selector_count": 5,
                "palette_block_count": 7,
                "palette_row_count": 57,
                "town_map_pointer_count": 6,
            },
        },
        {
            "id": "town-map-icon-table",
            "data": make_town_map_icon_table(),
            "spec": {
                "kind": "town_map_icon_table_json",
                "path": "town_map_icons.json",
                "icon_count": 23,
                "town_map_count": 6,
            },
            "expected_metadata": {
                "icon_count": 23,
                "unique_descriptor_list_count": 22,
                "descriptor_record_count": 117,
                "blink_suppress_count": 16,
                "placement_record_count": 42,
            },
        },
        {
            "id": "photographer-config-table",
            "data": make_photographer_config_table(),
            "spec": {
                "kind": "photographer_config_table_json",
                "path": "photographer_config.json",
                "row_count": 32,
                "record_size_bytes": 62,
            },
            "expected_metadata": {
                "row_count": 32,
                "enabled_event_flag_count": 32,
                "background_offset_count": 16,
                "slide_vector_count": 32,
                "visual_position_count": 43,
                "spawned_entity_count": 8,
            },
        },
        {
            "id": "snes-2bpp-tiles",
            "data": graphics_2bpp,
            "spec": {"kind": "snes_2bpp_tiles_png", "path": "tiles_2bpp.png", "columns": 2},
        },
        {
            "id": "snes-2bpp-tiles-trimmed",
            "data": graphics_2bpp + b"\x00",
            "spec": {
                "kind": "snes_2bpp_tiles_png",
                "path": "tiles_2bpp_trimmed.png",
                "columns": 2,
                "trim_trailing_bytes": 1,
            },
            "expected_metadata": {
                "tiles": 2,
                "trimmed_source_bytes": len(graphics_2bpp),
            },
        },
        {
            "id": "snes-4bpp-tiles",
            "data": graphics_4bpp,
            "spec": {"kind": "snes_4bpp_tiles_png", "path": "tiles_4bpp.png", "columns": 2},
        },
        {
            "id": "earthbound-lzhal-snes-4bpp-tiles",
            "data": literal_lzhal(graphics_4bpp),
            "spec": {"kind": "earthbound_lzhal_snes_4bpp_tiles_png", "path": "tiles_4bpp_lz.png", "columns": 2},
        },
        {
            "id": "snes-4bpp-palette-tiles",
            "data": graphics_4bpp,
            "spec": {
                "kind": "snes_4bpp_tiles_palette_png",
                "path": "tiles_4bpp_palette.png",
                "columns": 2,
                "colors": 16,
                "palette_source": source_ref(PALETTE_RANGE, palette),
            },
        },
        {
            "id": "earthbound-lzhal-snes-4bpp-palette-tiles",
            "data": literal_lzhal(graphics_4bpp),
            "spec": {
                "kind": "earthbound_lzhal_snes_4bpp_tiles_palette_png",
                "path": "tiles_4bpp_palette_lz.png",
                "columns": 2,
                "colors": 16,
                "palette_source": source_ref(PALETTE_RANGE, palette),
            },
        },
        {
            "id": "snes-palette-json",
            "data": palette,
            "spec": {"kind": "snes_palette_json", "path": "palette.json", "colors": 16},
        },
        {
            "id": "snes-palette-swatch",
            "data": palette,
            "spec": {"kind": "snes_palette_swatch_png", "path": "palette.png", "per_row": 8, "swatch": 4},
        },
        {
            "id": "earthbound-lzhal-snes-palette-json",
            "data": literal_lzhal(palette),
            "spec": {"kind": "earthbound_lzhal_snes_palette_json", "path": "palette_lz.json", "colors": 16},
        },
        {
            "id": "earthbound-lzhal-snes-palette-swatch",
            "data": literal_lzhal(palette),
            "spec": {"kind": "earthbound_lzhal_snes_palette_swatch_png", "path": "palette_lz.png", "per_row": 8, "swatch": 4},
        },
        {
            "id": "earthbound-lzhal-battle-bg-arrangement",
            "data": literal_lzhal(arrangement),
            "spec": {
                "kind": "earthbound_lzhal_battle_bg_arrangement_png",
                "path": "battle_bg.png",
                "width_tiles": 2,
                "height_tiles": 2,
                "bpp": 4,
                "colors": 16,
                "arrangement_id": 0,
                "graphics_id": 0,
                "palette_id": 0,
                "graphics_source": source_ref(GRAPHICS_RANGE, graphics_4bpp),
                "palette_source": source_ref(PALETTE_RANGE, palette),
            },
        },
        {
            "id": "earthbound-lzhal-battle-sprite",
            "data": literal_lzhal(battle_sprite),
            "spec": {
                "kind": "earthbound_lzhal_battle_sprite_png",
                "path": "battle_sprite.png",
                "width": 16,
                "height": 16,
                "colors": 16,
                "sprite_id": 0,
                "palette_id": 0,
                "palette_source": source_ref(PALETTE_RANGE, palette),
            },
        },
    ]


def verify_case(case: dict[str, Any], result: dict[str, Any], out_root: Path) -> list[str]:
    errors: list[str] = []
    kind = str(case["spec"]["kind"])
    contract = OUTPUT_RECIPE_CONTRACTS[kind]
    output_path = Path(str(result["path"]))
    if not output_path.is_file():
        return [f"{case['id']}: missing output file {output_path}"]
    output_data = output_path.read_bytes()
    if len(output_data) != int(result.get("bytes", -1)):
        errors.append(f"{case['id']}: reported byte count does not match file size")
    if hashlib.sha1(output_data).hexdigest() != result.get("sha1"):
        errors.append(f"{case['id']}: reported SHA-1 does not match file content")
    for field in contract.report_required_fields:
        if field not in result:
            errors.append(f"{case['id']}: missing report metadata field {field}")
    for field, expected in case.get("expected_metadata", {}).items():
        if result.get(field) != expected:
            errors.append(f"{case['id']}: expected {field}={expected!r}, got {result.get(field)!r}")
    try:
        output_path.resolve().relative_to(out_root.resolve())
    except ValueError:
        errors.append(f"{case['id']}: output escaped validation root")
    return errors


def reset_output_root(out_root: Path) -> None:
    build_root = (ROOT / "build").resolve()
    resolved = out_root.resolve()
    try:
        resolved.relative_to(build_root)
    except ValueError as exc:
        raise ValueError(f"validation output root must stay under {rel(build_root)}: {out_root}") from exc
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)


def run_validation(out_root: Path) -> dict[str, Any]:
    reset_output_root(out_root)

    palette = palette_bytes()
    graphics = make_4bpp_tiles(2)
    rom = synthetic_rom(palette, graphics)
    cases = output_cases()
    results = []
    errors: list[str] = []
    for case in cases:
        result = extract_assets.write_output(case["data"], out_root, case["spec"], rom)
        case_errors = verify_case(case, result, out_root)
        errors.extend(case_errors)
        results.append(
            {
                "id": case["id"],
                "kind": case["spec"]["kind"],
                "path": rel(Path(result["path"])),
                "bytes": result["bytes"],
                "sha1": result["sha1"],
                "metadata": {
                    key: value
                    for key, value in result.items()
                    if key not in {"kind", "path", "bytes", "sha1"}
                },
                "spec_options": {
                    key: value
                    for key, value in case["spec"].items()
                    if key not in {"kind", "path"}
                },
                "errors": case_errors,
            }
        )

    covered_kinds = sorted({str(item["kind"]) for item in results})
    missing_kinds = sorted(set(OUTPUT_RECIPE_CONTRACTS) - set(covered_kinds))
    if missing_kinds:
        errors.append(f"missing synthetic coverage for output kinds: {missing_kinds}")

    return {
        "schema": "earthbound-decomp.asset-output-codec-validation.v1",
        "source_policy": {
            "contains_rom_derived_outputs": False,
            "uses_synthetic_payloads_only": True,
        },
        "output_root": rel(out_root),
        "case_count": len(results),
        "trim_trailing_bytes_case_count": sum(
            1 for item in results if "trim_trailing_bytes" in item["spec_options"]
        ),
        "covered_output_kinds": covered_kinds,
        "missing_output_kinds": missing_kinds,
        "status": "ok" if not errors else "invalid",
        "errors": errors,
        "cases": results,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Asset Output Codec Validation",
        "",
        "Generated by `tools/validate_asset_output_codecs.py` from synthetic tile, palette, tilemap, and literal LZHAL payloads.",
        "",
        "This validates the offline renderer/decoder code paths behind typed output recipes without requiring a user-supplied ROM. Generated PNG/JSON/bin outputs stay under ignored `build/` paths.",
        "",
        "Generated asset-output reports are freshness-checked together with `tools/validate_asset_output_reports.py`.",
        "",
        "## Snapshot",
        "",
        f"- status: `{report['status']}`",
        f"- synthetic cases: `{report['case_count']}`",
        f"- trim-trailing-bytes cases: `{report['trim_trailing_bytes_case_count']}`",
        f"- output kinds covered: `{len(report['covered_output_kinds'])}`",
        f"- missing output kinds: `{len(report['missing_output_kinds'])}`",
        f"- output root: `{report['output_root']}`",
        "",
        "## Cases",
        "",
        "| Case | Recipe kind | Bytes | Spec options | Metadata keys |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for case in report["cases"]:
        metadata_keys = ", ".join(f"`{key}`" for key in sorted(case["metadata"])) or "-"
        spec_options = ", ".join(f"`{key}`" for key in sorted(case["spec_options"])) or "-"
        lines.append(
            f"| `{case['id']}` | `{case['kind']}` | {case['bytes']} | {spec_options} | {metadata_keys} |"
        )
    if report["errors"]:
        lines.extend(["", "## Errors", ""])
        for error in report["errors"]:
            lines.append(f"- {error}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate asset output codecs with synthetic fixtures.")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    args = parser.parse_args()

    report = run_validation(Path(args.out))
    json_out = Path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    markdown_out = Path(args.markdown_out)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(render_markdown(report), encoding="utf-8")

    print(
        "asset output codec validation: "
        f"{report['status']}, "
        f"{report['case_count']} cases, "
        f"{len(report['covered_output_kinds'])} kinds"
    )
    if report["errors"]:
        for error in report["errors"]:
            print(f"ERROR {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
