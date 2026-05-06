from __future__ import annotations

import argparse
import binascii
import hashlib
import json
import math
import struct
import zlib
from pathlib import Path
from typing import Any

from rom_tools import (
    EXPECTED_SHA1,
    find_rom,
    hirom_to_file_offset,
    load_rom,
    read_rom_info,
    verify_earthbound_us,
)
from decompress_c41a9e import decompress_blob
from snes_palette import (
    decode_snes_bgr555_palette,
    write_palette_json,
    write_palette_swatch_png,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract manifest-described assets from a user-supplied ROM."
    )
    parser.add_argument(
        "--manifest",
        required=True,
        help="Path to an asset manifest JSON file.",
    )
    parser.add_argument(
        "--rom",
        default=None,
        help="Path to the EarthBound ROM. Defaults to the usual workspace locations.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output root. Defaults to manifest source_policy.default_output_root or build/assets.",
    )
    parser.add_argument(
        "--asset-id",
        action="append",
        default=[],
        help="Extract only a specific asset ID. Can be passed more than once.",
    )
    parser.add_argument(
        "--allow-rom-mismatch",
        action="store_true",
        help="Continue when the ROM header/SHA-1 does not match EarthBound US.",
    )
    parser.add_argument(
        "--allow-range-mismatch",
        action="store_true",
        help="Write outputs even when a manifest range SHA-1 does not match.",
    )
    return parser.parse_args()


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if manifest.get("schema") != "earthbound-decomp.asset-manifest.v1":
        raise ValueError(f"Unsupported manifest schema in {path}")
    if not isinstance(manifest.get("assets"), list):
        raise ValueError(f"Manifest has no assets list: {path}")
    return manifest


def parse_bank_range(text: str) -> tuple[int, int, int]:
    try:
        start_text, end_text = text.split("..", 1)
        start_bank_text, start_addr_text = start_text.split(":", 1)
        end_bank_text, end_addr_text = end_text.split(":", 1)
    except ValueError as exc:
        raise ValueError(f"Invalid range {text!r}; expected BB:AAAA..BB:AAAA") from exc

    start_bank = int(start_bank_text, 16)
    end_bank = int(end_bank_text, 16)
    if start_bank != end_bank:
        raise ValueError(f"Cross-bank ranges are not supported yet: {text}")

    start_addr = int(start_addr_text, 16)
    end_addr = int(end_addr_text, 16)
    if not 0 <= start_addr <= 0x10000 or not 0 <= end_addr <= 0x10000:
        raise ValueError(f"Range address outside bank bounds: {text}")
    if end_addr < start_addr:
        raise ValueError(f"Range end precedes start: {text}")
    return start_bank, start_addr, end_addr


def rom_range_slice(rom: bytes, range_text: str) -> tuple[bytes, int]:
    bank, start_addr, end_addr = parse_bank_range(range_text)
    start_offset = hirom_to_file_offset(bank, start_addr, len(rom))
    if start_offset is None:
        raise ValueError(f"Range start is not a ROM address: {range_text}")

    length = end_addr - start_addr
    end_offset = start_offset + length
    if end_offset > len(rom):
        raise ValueError(
            f"Range {range_text} extends past ROM EOF: 0x{end_offset:06X} > 0x{len(rom):06X}"
        )
    return rom[start_offset:end_offset], start_offset


def output_path(root: Path, relative_path: str) -> Path:
    path = root / relative_path
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    if resolved_root != resolved_path and resolved_root not in resolved_path.parents:
        raise ValueError(f"Output escapes root: {relative_path}")
    return path


def write_raw(data: bytes, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def decompress_earthbound_lzhal(data: bytes) -> tuple[bytes, int]:
    decompressed, consumed = decompress_blob(data, dest_base=0xC000)
    if consumed <= 0 or consumed > len(data):
        raise ValueError(
            f"LZHAL decompressor consumed an invalid byte count: {consumed}/{len(data)}"
        )
    return decompressed, consumed


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)
    )


def write_grayscale_png(path: Path, rows: list[list[int]]) -> None:
    if not rows or not rows[0]:
        raise ValueError("Cannot write an empty PNG")
    width = len(rows[0])
    height = len(rows)
    for row in rows:
        if len(row) != width:
            raise ValueError("PNG rows have inconsistent widths")

    raw = b"".join(bytes([0]) + bytes(row) for row in rows)
    payload = b"\x89PNG\r\n\x1a\n"
    payload += png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0))
    payload += png_chunk(b"IDAT", zlib.compress(raw))
    payload += png_chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def write_rgb_png(path: Path, rows: list[list[tuple[int, int, int]]]) -> None:
    if not rows or not rows[0]:
        raise ValueError("Cannot write an empty PNG")
    width = len(rows[0])
    height = len(rows)
    for row in rows:
        if len(row) != width:
            raise ValueError("PNG rows have inconsistent widths")

    raw_rows = []
    for row in rows:
        payload = bytearray([0])
        for red, green, blue in row:
            payload.extend((red, green, blue))
        raw_rows.append(bytes(payload))

    payload = b"\x89PNG\r\n\x1a\n"
    payload += png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    payload += png_chunk(b"IDAT", zlib.compress(b"".join(raw_rows)))
    payload += png_chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def palette_entry_count(data: bytes, spec: dict[str, Any]) -> int | None:
    count = spec.get("colors")
    if count is None:
        return None
    return int(count)


def write_snes_palette_json(data: bytes, path: Path, spec: dict[str, Any]) -> int:
    entries = decode_snes_bgr555_palette(data, count=palette_entry_count(data, spec))
    write_palette_json(path, entries)
    return len(entries)


def write_map_tile_chunk_index_json(data: bytes, path: Path, spec: dict[str, Any]) -> dict[str, int]:
    if len(data) % 2 != 0:
        raise ValueError(f"Map tile chunk data must have an even byte count, got {len(data)}")
    chunk_index = int(spec["chunk_index"])
    values = [data[offset] | (data[offset + 1] << 8) for offset in range(0, len(data), 2)]
    distinct_values = len(set(values))
    payload = {
        "schema": "earthbound-decomp.map-tile-chunk-index.v1",
        "decoder": "map_tile_chunk_index",
        "chunk_index": chunk_index,
        "byte_order": "little",
        "entry_size_bytes": 2,
        "source_bytes": len(data),
        "entry_count": len(values),
        "min_tile_id": min(values) if values else 0,
        "max_tile_id": max(values) if values else 0,
        "distinct_tile_ids": distinct_values,
        "tile_ids": values,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {
        "chunk_index": chunk_index,
        "entry_count": len(values),
        "min_tile_id": payload["min_tile_id"],
        "max_tile_id": payload["max_tile_id"],
        "distinct_tile_ids": distinct_values,
    }


def write_battle_swirl_frame_json(data: bytes, path: Path, spec: dict[str, Any]) -> dict[str, int]:
    if not data:
        raise ValueError("Battle swirl frame metadata requires a non-empty payload")
    swirl_id = int(spec["swirl_id"])
    sequence_id = int(spec["sequence_id"])
    sequence_frame_index = int(spec["sequence_frame_index"])
    sequence_speed = int(spec["sequence_speed"])
    sequence_frame_count = int(spec["sequence_frame_count"])
    if sequence_frame_index < 0 or sequence_frame_index >= sequence_frame_count:
        raise ValueError(
            "Battle swirl sequence frame index must be within the sequence frame count: "
            f"{sequence_frame_index}/{sequence_frame_count}"
        )

    payload = {
        "schema": "earthbound-decomp.battle-swirl-frame-metadata.v1",
        "decoder": "battle_swirl_frame_metadata",
        "bytecode_status": "raw-preserved",
        "swirl_id": swirl_id,
        "sequence_id": sequence_id,
        "sequence_frame_index": sequence_frame_index,
        "sequence_speed": sequence_speed,
        "sequence_frame_count": sequence_frame_count,
        "source_bytes": len(data),
        "first_opcode": data[0],
        "last_byte": data[-1],
        "source_sha1": hashlib.sha1(data).hexdigest(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {
        "swirl_id": swirl_id,
        "sequence_id": sequence_id,
        "sequence_frame_index": sequence_frame_index,
        "sequence_speed": sequence_speed,
        "sequence_frame_count": sequence_frame_count,
        "payload_bytes": len(data),
        "first_opcode": data[0],
    }


def write_battle_swirl_pointer_table_json(data: bytes, path: Path, spec: dict[str, Any]) -> dict[str, int]:
    entry_count = int(spec["entry_count"])
    pointer_bank = int(spec["pointer_bank"])
    expected_bytes = entry_count * 2
    if entry_count <= 0:
        raise ValueError(f"Battle swirl pointer table entry_count must be positive, got {entry_count}")
    if len(data) != expected_bytes:
        raise ValueError(f"Battle swirl pointer table expected {expected_bytes} bytes, got {len(data)}")

    values = [data[offset] | (data[offset + 1] << 8) for offset in range(0, len(data), 2)]
    payload = {
        "schema": "earthbound-decomp.battle-swirl-pointer-table.v1",
        "decoder": "battle_swirl_pointer_table",
        "byte_order": "little",
        "pointer_bank": pointer_bank,
        "entry_size_bytes": 2,
        "entry_count": entry_count,
        "min_pointer": min(values),
        "max_pointer": max(values),
        "distinct_pointers": len(set(values)),
        "pointers": [
            {
                "swirl_id": index,
                "address": f"{pointer_bank:02X}:{value:04X}",
                "offset_in_bank": value,
            }
            for index, value in enumerate(values)
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {
        "entry_count": entry_count,
        "pointer_bank": pointer_bank,
        "min_pointer": payload["min_pointer"],
        "max_pointer": payload["max_pointer"],
        "distinct_pointers": payload["distinct_pointers"],
    }


def write_battle_swirl_sequence_table_json(data: bytes, path: Path, spec: dict[str, Any]) -> dict[str, int]:
    row_count = int(spec["row_count"])
    expected_bytes = row_count * 4
    if row_count <= 0:
        raise ValueError(f"Battle swirl sequence table row_count must be positive, got {row_count}")
    if len(data) != expected_bytes:
        raise ValueError(f"Battle swirl sequence table expected {expected_bytes} bytes, got {len(data)}")

    rows = []
    visible_sequence_count = 0
    total_frame_count = 0
    max_sequence_speed = 0
    for offset in range(0, len(data), 4):
        sequence_id = offset // 4
        speed, first_payload_index, frame_count, reserved_zero = data[offset : offset + 4]
        if frame_count:
            visible_sequence_count += 1
            total_frame_count += frame_count
            max_sequence_speed = max(max_sequence_speed, speed)
        rows.append(
            {
                "sequence_id": sequence_id,
                "speed": speed,
                "first_payload_index": first_payload_index,
                "frame_count": frame_count,
                "reserved_zero": reserved_zero,
                "last_payload_index": first_payload_index + frame_count - 1 if frame_count else None,
                "status": "visible" if frame_count else "disabled",
            }
        )

    payload = {
        "schema": "earthbound-decomp.battle-swirl-sequence-table.v1",
        "decoder": "battle_swirl_sequence_table",
        "row_size_bytes": 4,
        "row_count": row_count,
        "visible_sequence_count": visible_sequence_count,
        "total_frame_count": total_frame_count,
        "max_sequence_speed": max_sequence_speed,
        "rows": rows,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {
        "row_count": row_count,
        "visible_sequence_count": visible_sequence_count,
        "total_frame_count": total_frame_count,
        "max_sequence_speed": max_sequence_speed,
    }


def write_battle_bg_pointer_table_json(data: bytes, path: Path, spec: dict[str, Any]) -> dict[str, int]:
    entry_count = int(spec["entry_count"])
    table_id = int(spec["table_id"])
    table_role = str(spec["table_role"])
    expected_bytes = entry_count * 4
    if entry_count <= 0:
        raise ValueError(f"Battle background pointer table entry_count must be positive, got {entry_count}")
    if len(data) != expected_bytes:
        raise ValueError(f"Battle background pointer table expected {expected_bytes} bytes, got {len(data)}")

    entries = []
    packed_pointers = []
    target_banks = set()
    for offset in range(0, len(data), 4):
        low_word = data[offset] | (data[offset + 1] << 8)
        bank = data[offset + 2]
        padding = data[offset + 3]
        if padding != 0:
            raise ValueError(
                "Battle background pointer table expected zero in fourth byte "
                f"for row {offset // 4}, got 0x{padding:02X}"
            )
        packed_pointer = (bank << 16) | low_word
        packed_pointers.append(packed_pointer)
        target_banks.add(bank)
        entries.append(
            {
                "index": offset // 4,
                "address": f"{bank:02X}:{low_word:04X}",
                "bank": bank,
                "offset_in_bank": low_word,
                "packed_pointer": packed_pointer,
                "raw_bytes": list(data[offset : offset + 4]),
            }
        )

    payload = {
        "schema": "earthbound-decomp.battle-bg-pointer-table.v1",
        "decoder": "battle_background_pointer_table",
        "byte_order": "little",
        "table_id": table_id,
        "table_role": table_role,
        "entry_size_bytes": 4,
        "entry_count": entry_count,
        "source_bytes": len(data),
        "source_sha1": hashlib.sha1(data).hexdigest(),
        "zero_padding_byte": True,
        "min_pointer": min(packed_pointers),
        "max_pointer": max(packed_pointers),
        "distinct_pointers": len(set(packed_pointers)),
        "distinct_banks": len(target_banks),
        "target_banks": [f"{bank:02X}" for bank in sorted(target_banks)],
        "entries": entries,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {
        "entry_count": entry_count,
        "min_pointer": payload["min_pointer"],
        "max_pointer": payload["max_pointer"],
        "distinct_pointers": payload["distinct_pointers"],
        "distinct_banks": payload["distinct_banks"],
    }


def read_u16_le(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def read_s16_le(data: bytes, offset: int) -> int:
    value = read_u16_le(data, offset)
    return value - 0x10000 if value & 0x8000 else value


def write_battle_bg_config_table_json(data: bytes, path: Path, spec: dict[str, Any]) -> dict[str, int]:
    row_count = int(spec["row_count"])
    row_size = 17
    expected_bytes = row_count * row_size
    if row_count <= 0:
        raise ValueError(f"Battle background config table row_count must be positive, got {row_count}")
    if len(data) != expected_bytes:
        raise ValueError(f"Battle background config table expected {expected_bytes} bytes, got {len(data)}")

    rows = []
    for offset in range(0, len(data), row_size):
        row = data[offset : offset + row_size]
        decoded = {
            "index": offset // row_size,
            "graphics_index": row[0],
            "arrangement_index": row[0],
            "palette_index": row[1],
            "bits_per_pixel": row[2],
            "unknown_palette_shift_style": row[3],
            "palette_cycle_1_first": row[4],
            "palette_cycle_1_last": row[5],
            "palette_cycle_2_first": row[6],
            "palette_cycle_2_last": row[7],
            "palette_change_speed": row[8],
            "scrolling_movements": list(row[9:13]),
            "distortion_styles": list(row[13:17]),
            "raw_bytes": list(row),
        }
        rows.append(decoded)

    max_scrolling_movement = max(max(row["scrolling_movements"]) for row in rows)
    max_distortion_style = max(max(row["distortion_styles"]) for row in rows)
    payload = {
        "schema": "earthbound-decomp.battle-bg-config-table.v1",
        "decoder": "battle_background_config_table",
        "row_size_bytes": row_size,
        "row_count": row_count,
        "source_bytes": len(data),
        "source_sha1": hashlib.sha1(data).hexdigest(),
        "max_graphics_index": max(row["graphics_index"] for row in rows),
        "max_palette_index": max(row["palette_index"] for row in rows),
        "max_scrolling_movement": max_scrolling_movement,
        "max_distortion_style": max_distortion_style,
        "rows": rows,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {
        "row_count": row_count,
        "max_graphics_index": payload["max_graphics_index"],
        "max_palette_index": payload["max_palette_index"],
        "max_scrolling_movement": max_scrolling_movement,
        "max_distortion_style": max_distortion_style,
    }


def write_battle_bg_scrolling_table_json(data: bytes, path: Path, spec: dict[str, Any]) -> dict[str, int]:
    row_count = int(spec["row_count"])
    row_size = 10
    expected_bytes = row_count * row_size
    if row_count <= 0:
        raise ValueError(f"Battle background scrolling table row_count must be positive, got {row_count}")
    if len(data) != expected_bytes:
        raise ValueError(f"Battle background scrolling table expected {expected_bytes} bytes, got {len(data)}")

    rows = []
    motion_vectors = set()
    for offset in range(0, len(data), row_size):
        row = data[offset : offset + row_size]
        motion = (
            read_s16_le(row, 2),
            read_s16_le(row, 4),
            read_s16_le(row, 6),
            read_s16_le(row, 8),
        )
        motion_vectors.add(motion)
        rows.append(
            {
                "index": offset // row_size,
                "duration": read_u16_le(row, 0),
                "horizontal_movement": motion[0],
                "vertical_movement": motion[1],
                "horizontal_acceleration": motion[2],
                "vertical_acceleration": motion[3],
                "raw_words": [read_u16_le(row, word_offset) for word_offset in range(0, row_size, 2)],
            }
        )

    payload = {
        "schema": "earthbound-decomp.battle-bg-scrolling-table.v1",
        "decoder": "battle_background_scrolling_table",
        "byte_order": "little",
        "row_size_bytes": row_size,
        "row_count": row_count,
        "source_bytes": len(data),
        "source_sha1": hashlib.sha1(data).hexdigest(),
        "max_duration": max(row["duration"] for row in rows),
        "nonzero_duration_count": sum(1 for row in rows if row["duration"] != 0),
        "distinct_motion_vectors": len(motion_vectors),
        "rows": rows,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {
        "row_count": row_count,
        "max_duration": payload["max_duration"],
        "nonzero_duration_count": payload["nonzero_duration_count"],
        "distinct_motion_vectors": payload["distinct_motion_vectors"],
    }


def write_battle_bg_distortion_table_json(data: bytes, path: Path, spec: dict[str, Any]) -> dict[str, int]:
    row_count = int(spec["row_count"])
    row_size = 17
    expected_bytes = row_count * row_size
    if row_count <= 0:
        raise ValueError(f"Battle background distortion table row_count must be positive, got {row_count}")
    if len(data) != expected_bytes:
        raise ValueError(f"Battle background distortion table expected {expected_bytes} bytes, got {len(data)}")

    rows = []
    distortion_types = set()
    for offset in range(0, len(data), row_size):
        row = data[offset : offset + row_size]
        distortion_type = row[2]
        distortion_types.add(distortion_type)
        rows.append(
            {
                "index": offset // row_size,
                "duration": read_u16_le(row, 0),
                "distortion_type": distortion_type,
                "ripple_frequency": read_s16_le(row, 3),
                "ripple_amplitude": read_s16_le(row, 5),
                "speed": row[7],
                "compression_rate": read_s16_le(row, 8),
                "ripple_frequency_acceleration": read_s16_le(row, 10),
                "ripple_amplitude_acceleration": read_s16_le(row, 12),
                "speed_acceleration": row[14],
                "compression_rate_acceleration": read_s16_le(row, 15),
                "raw_bytes": list(row),
            }
        )

    payload = {
        "schema": "earthbound-decomp.battle-bg-distortion-table.v1",
        "decoder": "battle_background_distortion_table",
        "byte_order": "little",
        "row_size_bytes": row_size,
        "row_count": row_count,
        "source_bytes": len(data),
        "source_sha1": hashlib.sha1(data).hexdigest(),
        "max_duration": max(row["duration"] for row in rows),
        "nonzero_duration_count": sum(1 for row in rows if row["duration"] != 0),
        "distinct_distortion_types": len(distortion_types),
        "rows": rows,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {
        "row_count": row_count,
        "max_duration": payload["max_duration"],
        "nonzero_duration_count": payload["nonzero_duration_count"],
        "distinct_distortion_types": payload["distinct_distortion_types"],
    }


BATTLE_SPRITE_SIZE_CODES = {
    1: ("_32X32", 32, 32),
    2: ("_64X32", 64, 32),
    3: ("_32X64", 32, 64),
    4: ("_64X64", 64, 64),
    5: ("_128X64", 128, 64),
    6: ("_128X128", 128, 128),
}


def write_battle_sprite_pointer_table_json(data: bytes, path: Path, spec: dict[str, Any]) -> dict[str, int]:
    entry_count = int(spec["entry_count"])
    row_size = 5
    expected_bytes = entry_count * row_size
    if entry_count <= 0:
        raise ValueError(f"Battle sprite pointer table entry_count must be positive, got {entry_count}")
    if len(data) != expected_bytes:
        raise ValueError(f"Battle sprite pointer table expected {expected_bytes} bytes, got {len(data)}")

    entries = []
    target_banks = set()
    size_codes = set()
    max_width = 0
    max_height = 0
    for offset in range(0, len(data), row_size):
        low_word = data[offset] | (data[offset + 1] << 8)
        bank = data[offset + 2]
        padding = data[offset + 3]
        if padding != 0:
            raise ValueError(
                "Battle sprite pointer table expected zero in fourth byte "
                f"for row {offset // row_size}, got 0x{padding:02X}"
            )
        size_code = data[offset + 4]
        size = BATTLE_SPRITE_SIZE_CODES.get(size_code)
        if size is None:
            raise ValueError(f"Unknown battle sprite size code 0x{size_code:02X} in row {offset // row_size}")
        size_label, width, height = size
        target_banks.add(bank)
        size_codes.add(size_code)
        max_width = max(max_width, width)
        max_height = max(max_height, height)
        entries.append(
            {
                "sprite_id": offset // row_size,
                "address": f"{bank:02X}:{low_word:04X}",
                "bank": bank,
                "offset_in_bank": low_word,
                "packed_pointer": (bank << 16) | low_word,
                "size_code": size_code,
                "size_label": size_label,
                "width": width,
                "height": height,
                "raw_bytes": list(data[offset : offset + row_size]),
            }
        )

    size_counts = {
        str(code): sum(1 for entry in entries if int(entry["size_code"]) == code)
        for code in sorted(size_codes)
    }
    payload = {
        "schema": "earthbound-decomp.battle-sprite-pointer-table.v1",
        "decoder": "battle_sprite_pointer_table",
        "byte_order": "little",
        "row_size_bytes": row_size,
        "entry_count": entry_count,
        "source_bytes": len(data),
        "source_sha1": hashlib.sha1(data).hexdigest(),
        "zero_padding_byte": True,
        "distinct_size_codes": len(size_codes),
        "size_code_counts": size_counts,
        "distinct_banks": len(target_banks),
        "target_banks": [f"{bank:02X}" for bank in sorted(target_banks)],
        "max_width": max_width,
        "max_height": max_height,
        "entries": entries,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {
        "entry_count": entry_count,
        "max_width": max_width,
        "max_height": max_height,
        "distinct_size_codes": len(size_codes),
        "distinct_banks": len(target_banks),
    }


def write_font_metric_widths_json(data: bytes, path: Path, spec: dict[str, Any]) -> dict[str, int]:
    font_id = int(spec["font_id"])
    entry_count = int(spec["entry_count"])
    first_character_code = int(spec["first_character_code"])
    if entry_count <= 0:
        raise ValueError(f"Font metric entry_count must be positive, got {entry_count}")
    if len(data) != entry_count:
        raise ValueError(f"Font metric table expected {entry_count} bytes, got {len(data)}")

    widths = list(data)
    payload = {
        "schema": "earthbound-decomp.font-metric-widths.v1",
        "decoder": "font_metric_widths",
        "font_id": font_id,
        "first_character_code": first_character_code,
        "entry_count": entry_count,
        "entry_size_bytes": 1,
        "width_units": "pixels",
        "min_width": min(widths),
        "max_width": max(widths),
        "distinct_widths": len(set(widths)),
        "sentinel_ff_count": widths.count(0xFF),
        "widths": [
            {"character_code": first_character_code + index, "width": width}
            for index, width in enumerate(widths)
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {
        "font_id": font_id,
        "entry_count": entry_count,
        "first_character_code": first_character_code,
        "max_width": payload["max_width"],
        "distinct_widths": payload["distinct_widths"],
        "sentinel_ff_count": payload["sentinel_ff_count"],
    }


def write_snes_palette_swatch_png(data: bytes, path: Path, spec: dict[str, Any]) -> int:
    entries = decode_snes_bgr555_palette(data, count=palette_entry_count(data, spec))
    per_row = int(spec.get("per_row", 16))
    swatch = int(spec.get("swatch", 16))
    write_palette_swatch_png(path, entries, per_row=per_row, swatch=swatch)
    return len(entries)


def swatch_dimensions(colors: int, spec: dict[str, Any]) -> dict[str, int]:
    per_row = int(spec.get("per_row", 16))
    swatch = int(spec.get("swatch", 16))
    rows = math.ceil(colors / per_row) if colors else 0
    return {"width": min(colors, per_row) * swatch if colors else 0, "height": rows * swatch}


def tile_sheet_metadata(rows: list[list[Any]], data: bytes, tile_size: int) -> dict[str, int]:
    return {
        "width": len(rows[0]) if rows else 0,
        "height": len(rows),
        "tiles": len(data) // tile_size,
    }


def decode_snes_2bpp_tiles(data: bytes, columns: int) -> list[list[int]]:
    if len(data) % 16 != 0:
        raise ValueError(f"SNES 2bpp tile data must be a multiple of 16 bytes, got {len(data)}")
    if columns <= 0:
        raise ValueError("Tile preview columns must be positive")

    tile_count = len(data) // 16
    rows_of_tiles = math.ceil(tile_count / columns)
    pixels = [[255 for _ in range(columns * 8)] for _ in range(rows_of_tiles * 8)]
    palette = [255, 170, 85, 0]

    for tile_index in range(tile_count):
        tile_x = (tile_index % columns) * 8
        tile_y = (tile_index // columns) * 8
        tile = data[tile_index * 16 : (tile_index + 1) * 16]
        for y in range(8):
            low = tile[y * 2]
            high = tile[y * 2 + 1]
            for x in range(8):
                bit = 7 - x
                color = ((high >> bit) & 1) << 1 | ((low >> bit) & 1)
                pixels[tile_y + y][tile_x + x] = palette[color]

    return pixels


def trim_trailing_bytes(data: bytes, spec: dict[str, Any]) -> bytes:
    trim = int(spec.get("trim_trailing_bytes", 0) or 0)
    if trim <= 0:
        return data
    if trim >= len(data):
        raise ValueError(f"Cannot trim {trim} trailing bytes from {len(data)}-byte source")
    return data[:-trim]


def decode_snes_4bpp_tile_indices(data: bytes, columns: int) -> list[list[int]]:
    if len(data) % 32 != 0:
        raise ValueError(f"SNES 4bpp tile data must be a multiple of 32 bytes, got {len(data)}")
    if columns <= 0:
        raise ValueError("Tile preview columns must be positive")

    tile_count = len(data) // 32
    rows_of_tiles = math.ceil(tile_count / columns)
    pixels = [[0 for _ in range(columns * 8)] for _ in range(rows_of_tiles * 8)]

    for tile_index in range(tile_count):
        tile_x = (tile_index % columns) * 8
        tile_y = (tile_index // columns) * 8
        tile = data[tile_index * 32 : (tile_index + 1) * 32]
        for y in range(8):
            plane0 = tile[y * 2]
            plane1 = tile[y * 2 + 1]
            plane2 = tile[16 + y * 2]
            plane3 = tile[16 + y * 2 + 1]
            for x in range(8):
                bit = 7 - x
                color = (
                    ((plane0 >> bit) & 1)
                    | (((plane1 >> bit) & 1) << 1)
                    | (((plane2 >> bit) & 1) << 2)
                    | (((plane3 >> bit) & 1) << 3)
                )
                pixels[tile_y + y][tile_x + x] = color

    return pixels


def decode_snes_4bpp_tiles(data: bytes, columns: int) -> list[list[int]]:
    palette = [255, 238, 221, 204, 187, 170, 153, 136, 119, 102, 85, 68, 51, 34, 17, 0]
    return [[palette[color] for color in row] for row in decode_snes_4bpp_tile_indices(data, columns)]


def palette_source_data(rom: bytes, spec: dict[str, Any]) -> bytes:
    source = spec.get("palette_source")
    if not isinstance(source, dict):
        raise ValueError(f"Palette-aware output requires palette_source: {spec!r}")
    if source.get("type") != "rom-range":
        raise ValueError(f"Only rom-range palette sources are supported: {source!r}")
    range_text = source.get("range")
    if not isinstance(range_text, str):
        raise ValueError(f"Palette source is missing a range: {source!r}")
    data, _ = rom_range_slice(rom, range_text)
    expected_bytes = source.get("bytes")
    if expected_bytes is not None and len(data) != int(expected_bytes):
        raise ValueError(
            f"Palette source {range_text}: expected {expected_bytes} bytes, got {len(data)}"
        )
    expected_sha1 = source.get("sha1")
    if expected_sha1 is not None:
        actual_sha1 = hashlib.sha1(data).hexdigest()
        if actual_sha1 != expected_sha1:
            raise ValueError(
                f"Palette source SHA-1 mismatch for {range_text}: "
                f"expected {expected_sha1}, got {actual_sha1}"
            )
    compression = source.get("compression")
    if compression is None:
        return data
    if compression == "earthbound_lzhal":
        decompressed, _ = decompress_earthbound_lzhal(data)
        return decompressed
    raise ValueError(f"Unsupported palette source compression: {compression}")


def write_snes_4bpp_palette_png(
    data: bytes,
    palette_data: bytes,
    path: Path,
    spec: dict[str, Any],
) -> dict[str, Any]:
    columns = int(spec.get("columns", 16))
    entries = decode_snes_bgr555_palette(palette_data, count=palette_entry_count(palette_data, spec))
    indices = decode_snes_4bpp_tile_indices(data, columns)
    max_color = max((max(row) for row in indices), default=0)
    if max_color >= len(entries):
        raise ValueError(
            f"4bpp tile data uses palette index {max_color}, "
            f"but palette only has {len(entries)} colors"
        )
    rows = [
        [(entries[color].red8, entries[color].green8, entries[color].blue8) for color in row]
        for row in indices
    ]
    write_rgb_png(path, rows)
    result = {"colors": len(entries), "palette_source_range": spec["palette_source"]["range"]}
    result.update(tile_sheet_metadata(rows, data, 32))
    for key in ("sprite_id", "graphics_id", "palette_id"):
        if key in spec:
            result[key] = spec[key]
    return result


def source_data(rom: bytes, spec: dict[str, Any], key: str) -> bytes:
    source = spec.get(key)
    if not isinstance(source, dict):
        raise ValueError(f"Output requires {key}: {spec!r}")
    if source.get("type") != "rom-range":
        raise ValueError(f"Only rom-range sources are supported for {key}: {source!r}")
    range_text = source.get("range")
    if not isinstance(range_text, str):
        raise ValueError(f"{key} is missing a range: {source!r}")
    data, _ = rom_range_slice(rom, range_text)
    expected_bytes = source.get("bytes")
    if expected_bytes is not None and len(data) != int(expected_bytes):
        raise ValueError(f"{key} {range_text}: expected {expected_bytes} bytes, got {len(data)}")
    expected_sha1 = source.get("sha1")
    if expected_sha1 is not None:
        actual_sha1 = hashlib.sha1(data).hexdigest()
        if actual_sha1 != expected_sha1:
            raise ValueError(
                f"{key} SHA-1 mismatch for {range_text}: expected {expected_sha1}, got {actual_sha1}"
            )
    compression = source.get("compression")
    if compression is None:
        return data
    if compression == "earthbound_lzhal":
        decompressed, _ = decompress_earthbound_lzhal(data)
        return decompressed
    raise ValueError(f"Unsupported {key} compression: {compression}")


def decode_snes_4bpp_tile_list(data: bytes) -> list[list[list[int]]]:
    if len(data) % 32 != 0:
        raise ValueError(f"SNES 4bpp tile data must be a multiple of 32 bytes, got {len(data)}")
    tiles: list[list[list[int]]] = []
    for tile_offset in range(0, len(data), 32):
        tile = data[tile_offset : tile_offset + 32]
        rows: list[list[int]] = []
        for y in range(8):
            plane0 = tile[y * 2]
            plane1 = tile[y * 2 + 1]
            plane2 = tile[16 + y * 2]
            plane3 = tile[16 + y * 2 + 1]
            row = []
            for x in range(8):
                bit = 7 - x
                row.append(
                    ((plane0 >> bit) & 1)
                    | (((plane1 >> bit) & 1) << 1)
                    | (((plane2 >> bit) & 1) << 2)
                    | (((plane3 >> bit) & 1) << 3)
                )
            rows.append(row)
        tiles.append(rows)
    return tiles


def decode_snes_2bpp_tile_list(data: bytes) -> list[list[list[int]]]:
    if len(data) % 16 != 0:
        raise ValueError(f"SNES 2bpp tile data must be a multiple of 16 bytes, got {len(data)}")
    tiles: list[list[list[int]]] = []
    for tile_offset in range(0, len(data), 16):
        tile = data[tile_offset : tile_offset + 16]
        rows: list[list[int]] = []
        for y in range(8):
            plane0 = tile[y * 2]
            plane1 = tile[y * 2 + 1]
            row = []
            for x in range(8):
                bit = 7 - x
                row.append(((plane0 >> bit) & 1) | (((plane1 >> bit) & 1) << 1))
            rows.append(row)
        tiles.append(rows)
    return tiles


def write_battle_bg_arrangement_png(
    arrangement_data: bytes,
    graphics_data: bytes,
    palette_data: bytes,
    path: Path,
    spec: dict[str, Any],
) -> dict[str, Any]:
    width_tiles = int(spec.get("width_tiles", 32))
    height_tiles = int(spec.get("height_tiles", 32))
    expected_bytes = width_tiles * height_tiles * 2
    if len(arrangement_data) != expected_bytes:
        raise ValueError(
            f"Battle background arrangement expected {expected_bytes} bytes, "
            f"got {len(arrangement_data)}"
        )

    bpp = int(spec.get("bpp", 4))
    if bpp == 2:
        tiles = decode_snes_2bpp_tile_list(graphics_data)
    elif bpp == 4:
        tiles = decode_snes_4bpp_tile_list(graphics_data)
    else:
        raise ValueError(f"Unsupported battle background arrangement bpp: {bpp}")
    entries = decode_snes_bgr555_palette(palette_data, count=palette_entry_count(palette_data, spec))
    rows = [[(0, 0, 0) for _ in range(width_tiles * 8)] for _ in range(height_tiles * 8)]
    max_tile = 0

    for tilemap_index in range(width_tiles * height_tiles):
        word_offset = tilemap_index * 2
        word = arrangement_data[word_offset] | (arrangement_data[word_offset + 1] << 8)
        tile_index = word & 0x03FF
        max_tile = max(max_tile, tile_index)
        if tile_index >= len(tiles):
            raise ValueError(
                f"Arrangement references tile {tile_index}, but graphics only has {len(tiles)} tiles"
            )
        hflip = bool(word & 0x4000)
        vflip = bool(word & 0x8000)
        tile_x = (tilemap_index % width_tiles) * 8
        tile_y = (tilemap_index // width_tiles) * 8
        tile = tiles[tile_index]
        for y in range(8):
            src_y = 7 - y if vflip else y
            for x in range(8):
                src_x = 7 - x if hflip else x
                color = tile[src_y][src_x]
                if color >= len(entries):
                    raise ValueError(
                        f"Tile color {color} is outside palette with {len(entries)} colors"
                    )
                entry = entries[color]
                rows[tile_y + y][tile_x + x] = (entry.red8, entry.green8, entry.blue8)

    write_rgb_png(path, rows)
    return {
        "colors": len(entries),
        "graphics_source_range": spec["graphics_source"]["range"],
        "palette_source_range": spec["palette_source"]["range"],
        "bpp": bpp,
        "max_tile": max_tile,
        "width": width_tiles * 8,
        "height": height_tiles * 8,
        "tiles": width_tiles * height_tiles,
    }


def write_battle_sprite_png(
    graphics_data: bytes,
    palette_data: bytes,
    path: Path,
    spec: dict[str, Any],
) -> dict[str, Any]:
    width = int(spec.get("width", 0))
    height = int(spec.get("height", 0))
    if width <= 0 or height <= 0 or width % 8 != 0 or height % 8 != 0:
        raise ValueError(f"Battle sprite dimensions must be positive tile multiples: {width}x{height}")

    expected_bytes = width * height // 2
    if len(graphics_data) != expected_bytes:
        raise ValueError(
            f"Battle sprite expected {expected_bytes} graphics bytes for {width}x{height}, "
            f"got {len(graphics_data)}"
        )

    tiles = decode_snes_4bpp_tile_list(graphics_data)
    entries = decode_snes_bgr555_palette(palette_data, count=palette_entry_count(palette_data, spec))
    tiles_per_row = width // 8
    rows = [[(0, 0, 0) for _ in range(width)] for _ in range(height)]

    for tile_index, tile in enumerate(tiles):
        tile_x = (tile_index % tiles_per_row) * 8
        tile_y = (tile_index // tiles_per_row) * 8
        for y in range(8):
            for x in range(8):
                color = tile[y][x]
                if color >= len(entries):
                    raise ValueError(
                        f"Tile color {color} is outside palette with {len(entries)} colors"
                    )
                entry = entries[color]
                rows[tile_y + y][tile_x + x] = (entry.red8, entry.green8, entry.blue8)

    write_rgb_png(path, rows)
    return {
        "colors": len(entries),
        "palette_source_range": spec["palette_source"]["range"],
        "sprite_id": spec["sprite_id"],
        "palette_id": spec["palette_id"],
        "width": width,
        "height": height,
    }


def write_output(data: bytes, root: Path, spec: dict[str, Any], rom: bytes) -> dict[str, Any]:
    kind = spec.get("kind")
    relative_path = spec.get("path")
    if not isinstance(kind, str) or not isinstance(relative_path, str):
        raise ValueError(f"Output spec must include string kind/path: {spec!r}")

    path = output_path(root, relative_path)
    metadata: dict[str, Any] = {}
    if kind == "raw":
        write_raw(data, path)
    elif kind == "earthbound_lzhal":
        decompressed, consumed = decompress_earthbound_lzhal(data)
        write_raw(decompressed, path)
        metadata["compressed_bytes_consumed"] = consumed
        metadata["decompressed_bytes"] = len(decompressed)
    elif kind == "map_tile_chunk_index_json":
        metadata.update(write_map_tile_chunk_index_json(data, path, spec))
    elif kind == "battle_swirl_frame_json":
        metadata.update(write_battle_swirl_frame_json(data, path, spec))
    elif kind == "battle_swirl_pointer_table_json":
        metadata.update(write_battle_swirl_pointer_table_json(data, path, spec))
    elif kind == "battle_swirl_sequence_table_json":
        metadata.update(write_battle_swirl_sequence_table_json(data, path, spec))
    elif kind == "battle_bg_pointer_table_json":
        metadata.update(write_battle_bg_pointer_table_json(data, path, spec))
    elif kind == "battle_bg_config_table_json":
        metadata.update(write_battle_bg_config_table_json(data, path, spec))
    elif kind == "battle_bg_scrolling_table_json":
        metadata.update(write_battle_bg_scrolling_table_json(data, path, spec))
    elif kind == "battle_bg_distortion_table_json":
        metadata.update(write_battle_bg_distortion_table_json(data, path, spec))
    elif kind == "battle_sprite_pointer_table_json":
        metadata.update(write_battle_sprite_pointer_table_json(data, path, spec))
    elif kind == "font_metric_widths_json":
        metadata.update(write_font_metric_widths_json(data, path, spec))
    elif kind == "snes_2bpp_tiles_png":
        columns = int(spec.get("columns", 16))
        tile_data = trim_trailing_bytes(data, spec)
        rows = decode_snes_2bpp_tiles(tile_data, columns)
        write_grayscale_png(path, rows)
        metadata.update(tile_sheet_metadata(rows, tile_data, 16))
        if tile_data is not data:
            metadata["trimmed_source_bytes"] = len(tile_data)
    elif kind == "snes_4bpp_tiles_png":
        columns = int(spec.get("columns", 16))
        rows = decode_snes_4bpp_tiles(data, columns)
        write_grayscale_png(path, rows)
        metadata.update(tile_sheet_metadata(rows, data, 32))
    elif kind == "earthbound_lzhal_snes_4bpp_tiles_png":
        columns = int(spec.get("columns", 16))
        decompressed, consumed = decompress_earthbound_lzhal(data)
        rows = decode_snes_4bpp_tiles(decompressed, columns)
        write_grayscale_png(path, rows)
        metadata["compressed_bytes_consumed"] = consumed
        metadata["decompressed_bytes"] = len(decompressed)
        metadata.update(tile_sheet_metadata(rows, decompressed, 32))
    elif kind == "snes_4bpp_tiles_palette_png":
        metadata.update(write_snes_4bpp_palette_png(data, palette_source_data(rom, spec), path, spec))
    elif kind == "earthbound_lzhal_snes_4bpp_tiles_palette_png":
        decompressed, consumed = decompress_earthbound_lzhal(data)
        metadata.update(
            write_snes_4bpp_palette_png(decompressed, palette_source_data(rom, spec), path, spec)
        )
        metadata["compressed_bytes_consumed"] = consumed
        metadata["decompressed_bytes"] = len(decompressed)
    elif kind == "earthbound_lzhal_battle_bg_arrangement_png":
        decompressed, consumed = decompress_earthbound_lzhal(data)
        metadata.update(
            write_battle_bg_arrangement_png(
                decompressed,
                source_data(rom, spec, "graphics_source"),
                source_data(rom, spec, "palette_source"),
                path,
                spec,
            )
        )
        metadata["compressed_bytes_consumed"] = consumed
        metadata["decompressed_bytes"] = len(decompressed)
    elif kind == "earthbound_lzhal_battle_sprite_png":
        decompressed, consumed = decompress_earthbound_lzhal(data)
        metadata.update(
            write_battle_sprite_png(
                decompressed,
                source_data(rom, spec, "palette_source"),
                path,
                spec,
            )
        )
        metadata["compressed_bytes_consumed"] = consumed
        metadata["decompressed_bytes"] = len(decompressed)
    elif kind == "snes_palette_json":
        metadata["colors"] = write_snes_palette_json(data, path, spec)
    elif kind == "snes_palette_swatch_png":
        metadata["colors"] = write_snes_palette_swatch_png(data, path, spec)
        metadata.update(swatch_dimensions(metadata["colors"], spec))
    elif kind == "earthbound_lzhal_snes_palette_json":
        decompressed, consumed = decompress_earthbound_lzhal(data)
        metadata["colors"] = write_snes_palette_json(decompressed, path, spec)
        metadata["compressed_bytes_consumed"] = consumed
        metadata["decompressed_bytes"] = len(decompressed)
    elif kind == "earthbound_lzhal_snes_palette_swatch_png":
        decompressed, consumed = decompress_earthbound_lzhal(data)
        metadata["colors"] = write_snes_palette_swatch_png(decompressed, path, spec)
        metadata["compressed_bytes_consumed"] = consumed
        metadata["decompressed_bytes"] = len(decompressed)
        metadata.update(swatch_dimensions(metadata["colors"], spec))
    else:
        raise ValueError(f"Unsupported output kind: {kind}")

    output_data = path.read_bytes()
    result = {
        "kind": kind,
        "path": str(path),
        "bytes": len(output_data),
        "sha1": hashlib.sha1(output_data).hexdigest(),
    }
    result.update(metadata)
    return result


def asset_source(asset: dict[str, Any]) -> dict[str, Any]:
    source = asset.get("source")
    if not isinstance(source, dict):
        raise ValueError(f"Asset {asset.get('id', '<missing>')} has no source object")
    if source.get("type") != "rom-range":
        raise ValueError(f"Only rom-range sources are supported: {asset.get('id')}")
    return source


def extract_assets(
    manifest: dict[str, Any],
    manifest_path: Path,
    rom_path: Path,
    rom: bytes,
    out_root: Path,
    selected_ids: set[str],
    allow_range_mismatch: bool,
) -> dict[str, Any]:
    extracted: list[dict[str, Any]] = []

    for asset in manifest["assets"]:
        asset_id = asset.get("id")
        if not isinstance(asset_id, str):
            raise ValueError(f"Asset is missing string id: {asset!r}")
        if selected_ids and asset_id not in selected_ids:
            continue

        source = asset_source(asset)
        range_text = source.get("range")
        if not isinstance(range_text, str):
            raise ValueError(f"Asset {asset_id} has no source range")

        data, file_offset = rom_range_slice(rom, range_text)
        expected_bytes = source.get("bytes")
        if expected_bytes is not None and len(data) != int(expected_bytes):
            raise ValueError(
                f"{asset_id}: expected {expected_bytes} bytes from {range_text}, got {len(data)}"
            )

        actual_sha1 = hashlib.sha1(data).hexdigest()
        expected_sha1 = source.get("sha1")
        sha1_ok = expected_sha1 is None or actual_sha1 == expected_sha1
        if not sha1_ok and not allow_range_mismatch:
            raise ValueError(
                f"{asset_id}: range SHA-1 mismatch for {range_text}: "
                f"expected {expected_sha1}, got {actual_sha1}"
            )

        outputs = asset.get("outputs", [])
        if not isinstance(outputs, list):
            raise ValueError(f"Asset {asset_id} outputs must be a list")

        written = [write_output(data, out_root, spec, rom) for spec in outputs]
        extracted.append(
            {
                "id": asset_id,
                "title": asset.get("title"),
                "range": range_text,
                "file_offset": f"0x{file_offset:06X}",
                "bytes": len(data),
                "sha1": actual_sha1,
                "sha1_ok": sha1_ok,
                "outputs": written,
            }
        )

    unknown_ids = selected_ids - {asset["id"] for asset in manifest["assets"]}
    if unknown_ids:
        raise ValueError(f"Requested asset IDs not found in manifest: {sorted(unknown_ids)}")

    return {
        "schema": "earthbound-decomp.asset-extraction-report.v1",
        "manifest": str(manifest_path),
        "rom": str(rom_path),
        "rom_sha1": hashlib.sha1(rom).hexdigest(),
        "output_root": str(out_root),
        "asset_count": len(extracted),
        "assets": extracted,
    }


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest).resolve()
    manifest = load_manifest(manifest_path)

    rom_path = find_rom(args.rom)
    rom = load_rom(rom_path)
    rom_info = read_rom_info(rom_path)
    problems = verify_earthbound_us(rom_info)
    if problems and not args.allow_rom_mismatch:
        formatted = "\n".join(f"- {problem}" for problem in problems)
        raise SystemExit(
            "ROM did not match expected EarthBound US metadata:\n"
            f"{formatted}\n"
            f"Expected SHA-1: {EXPECTED_SHA1}"
        )

    out_root = Path(
        args.out
        or manifest.get("source_policy", {}).get("default_output_root")
        or "build/assets"
    ).resolve()

    report = extract_assets(
        manifest=manifest,
        manifest_path=manifest_path,
        rom_path=rom_path,
        rom=rom,
        out_root=out_root,
        selected_ids=set(args.asset_id),
        allow_range_mismatch=args.allow_range_mismatch,
    )
    report["rom_verified"] = not problems
    report["rom_info"] = rom_info.to_dict()

    report_path = out_root / f"asset-extraction-report-{manifest_path.stem}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(
        f"Extracted {report['asset_count']} assets from {manifest_path.name} "
        f"to {out_root}"
    )
    print(f"Wrote report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
