from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_asset_bank_manifest
import decompress_c41a9e
import rom_tools


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_ROOT = "build/assets"
SCHEMA = "earthbound-decomp.asset-manifest.v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert an asset-bank layout manifest into extraction-manifest v1."
    )
    parser.add_argument("bank", nargs="+", help="Canonical bank(s), e.g. CA D5.")
    parser.add_argument("--rom", help="Optional explicit ROM path.")
    parser.add_argument(
        "--yml",
        default=str(build_asset_bank_manifest.DEFAULT_YML),
        help="Path to earthbound.yml for rebuilding missing bank manifests.",
    )
    parser.add_argument(
        "--bank-manifest-dir",
        default=str(ROOT / "build"),
        help="Directory containing asset-bank-xx.json files.",
    )
    parser.add_argument(
        "--out-dir",
        default=str(ROOT / "asset-manifests"),
        help="Directory for generated extraction manifests.",
    )
    parser.add_argument(
        "--include-tables",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include table corridors as raw extractable assets.",
    )
    parser.add_argument(
        "--include-gaps",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include coverage gaps as raw extractable assets.",
    )
    return parser.parse_args()


def slug(text: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return cleaned or fallback


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_or_build_bank_manifest(
    bank: str,
    bank_manifest_dir: Path,
    yml_path: Path,
    rom_path: Path,
) -> dict[str, Any]:
    path = bank_manifest_dir / f"asset-bank-{bank.lower()}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return build_asset_bank_manifest.build_manifest(bank, yml_path, rom_path)


def parse_cpu(cpu: str) -> tuple[str, int]:
    bank, address = cpu.split(":", 1)
    return bank.upper(), int(address, 16)


def inclusive_span_to_exclusive_range(cpu_start: str, cpu_end: str) -> str:
    start_bank, start_addr = parse_cpu(cpu_start)
    end_bank, end_addr = parse_cpu(cpu_end)
    if start_bank != end_bank:
        raise ValueError(f"Cross-bank span is not supported yet: {cpu_start}..{cpu_end}")
    return f"{start_bank}:{start_addr:04X}..{end_bank}:{end_addr + 1:04X}"


def rom_slice_sha1(rom: bytes, file_offset_text: str, size: int) -> str:
    offset = int(file_offset_text, 16)
    data = rom[offset : offset + size]
    if len(data) != size:
        raise ValueError(f"ROM slice extends past EOF at {file_offset_text} size {size}")
    return hashlib.sha1(data).hexdigest()


def binary_category(entry: dict[str, Any]) -> str:
    extension = str(entry.get("extension", "")).lower()
    if extension in {"gfx", "arr", "pal", "map", "tilemap"}:
        return "graphics"
    if extension in {"brr", "ebm"}:
        return "audio"
    if extension in {"txt", "ebtxt"}:
        return "text"
    return "binary-asset"


def output_payload_path(bank: str, payload: str) -> str:
    cleaned = payload.replace(":", "_").replace("\\", "/").strip("/")
    return f"{bank.lower()}/{cleaned}"


def preview_path(raw_path: str, suffix: str) -> str:
    path = Path(raw_path)
    return path.with_name(f"{path.stem}_{suffix}.png").as_posix()


def sidecar_path(raw_path: str, suffix: str, extension: str) -> str:
    path = Path(raw_path)
    return path.with_name(f"{path.stem}_{suffix}{extension}").as_posix()


def without_lzhal_suffix(raw_path: str) -> str:
    if raw_path.lower().endswith(".lzhal"):
        return raw_path[:-6]
    return f"{raw_path}.decompressed"


def map_tile_chunk_index(payload: str) -> int | None:
    normalized = payload.replace("\\", "/").lower()
    match = re.match(r"^maps/tiles/chunk_(\d+)\.bin$", normalized)
    if match is None:
        return None
    return int(match.group(1))


def read_entry_bytes(rom: bytes, entry: dict[str, Any]) -> bytes:
    offset = int(str(entry["file_offset"]), 16)
    size = int(entry["size"])
    data = rom[offset : offset + size]
    if len(data) != size:
        raise ValueError(f"ROM slice extends past EOF at {entry['file_offset']} size {size}")
    return data


def source_bytes_from_manifest_source(rom: bytes, source: dict[str, Any]) -> bytes:
    range_text = str(source["range"])
    start_text, end_text = range_text.split("..", 1)
    start_bank_text, start_addr_text = start_text.split(":", 1)
    end_bank_text, end_addr_text = end_text.split(":", 1)
    start_bank = int(start_bank_text, 16)
    end_bank = int(end_bank_text, 16)
    if start_bank != end_bank:
        raise ValueError(f"Cross-bank source range is not supported: {range_text}")
    start_addr = int(start_addr_text, 16)
    end_addr = int(end_addr_text, 16)
    start_offset = rom_tools.hirom_to_file_offset(start_bank, start_addr, len(rom))
    if start_offset is None:
        raise ValueError(f"Source range does not map to ROM: {range_text}")
    data = rom[start_offset : start_offset + (end_addr - start_addr)]
    if len(data) != int(source["bytes"]):
        raise ValueError(f"Source range byte count mismatch: {range_text}")
    return data


def lzhal_decompressed_size(rom: bytes, entry: dict[str, Any]) -> int | None:
    try:
        decompressed, consumed = decompress_c41a9e.decompress_blob(
            read_entry_bytes(rom, entry),
            dest_base=0xC000,
        )
    except (IndexError, ValueError):
        return None
    if consumed <= 0 or consumed > int(entry["size"]):
        return None
    return len(decompressed)


def battle_bg_asset_number(entry: dict[str, Any], subdir: str, extension: str) -> int | None:
    payload = str(entry.get("payload_path") or "").replace("\\", "/").lower()
    pattern = rf"^battle_bgs/{subdir}/(\d+)\.{extension}(?:\.lzhal)?$"
    match = re.match(pattern, payload)
    if match is None:
        return None
    return int(match.group(1))


def battle_sprite_asset_number(entry: dict[str, Any], extension: str) -> int | None:
    payload = str(entry.get("payload_path") or "").replace("\\", "/").lower()
    if extension == "pal":
        pattern = r"^battle_sprites/palettes/(\d+)\.pal(?:\.lzhal)?$"
    else:
        pattern = rf"^battle_sprites/(\d+)\.{extension}(?:\.lzhal)?$"
    match = re.match(pattern, payload)
    if match is None:
        return None
    return int(match.group(1))


def overworld_sprite_asset_number(entry: dict[str, Any]) -> int | None:
    payload = str(entry.get("payload_path") or "").replace("\\", "/").lower()
    match = re.match(r"^overworld_sprites/gfx/(\d+)\.gfx$", payload)
    if match is None:
        return None
    return int(match.group(1))


def battle_swirl_asset_number(entry: dict[str, Any]) -> int | None:
    payload = str(entry.get("payload_path") or "").replace("\\", "/").lower()
    match = re.match(r"^swirls/(\d+)\.swirl$", payload)
    if match is None:
        return None
    return int(match.group(1))


def battle_swirl_sequence_context(swirl_id: int) -> dict[str, int] | None:
    sequence_rows = [
        {"sequence_id": 1, "sequence_speed": 2, "first": 0, "sequence_frame_count": 23},
        {"sequence_id": 2, "sequence_speed": 4, "first": 23, "sequence_frame_count": 15},
        {"sequence_id": 3, "sequence_speed": 3, "first": 38, "sequence_frame_count": 22},
        {"sequence_id": 4, "sequence_speed": 4, "first": 60, "sequence_frame_count": 21},
        {"sequence_id": 5, "sequence_speed": 2, "first": 81, "sequence_frame_count": 28},
        {"sequence_id": 6, "sequence_speed": 3, "first": 109, "sequence_frame_count": 17},
    ]
    for row in sequence_rows:
        first = row["first"]
        count = row["sequence_frame_count"]
        if first <= swirl_id < first + count:
            return {
                "sequence_id": row["sequence_id"],
                "sequence_frame_index": swirl_id - first,
                "sequence_speed": row["sequence_speed"],
                "sequence_frame_count": count,
            }
    return None


def battle_swirl_frame_metadata_output(raw_path: str, entry: dict[str, Any]) -> dict[str, Any] | None:
    swirl_id = battle_swirl_asset_number(entry)
    if swirl_id is None:
        return None
    context = battle_swirl_sequence_context(swirl_id)
    if context is None:
        return None
    return {
        "kind": "battle_swirl_frame_json",
        "path": sidecar_path(raw_path, "frame", ".json"),
        "swirl_id": swirl_id,
        **context,
    }


FONT_METRIC_IDS = {
    "fonts/main.bin": 0,
    "fonts/mrsaturn.bin": 1,
    "fonts/large.bin": 2,
    "fonts/battle.bin": 3,
    "fonts/tiny.bin": 4,
}


def font_metric_widths_output(raw_path: str, entry: dict[str, Any]) -> dict[str, Any] | None:
    payload = str(entry.get("payload_path") or "").replace("\\", "/").lower()
    font_id = FONT_METRIC_IDS.get(payload)
    if font_id is None or int(entry["size"]) != 96:
        return None
    return {
        "kind": "font_metric_widths_json",
        "path": sidecar_path(raw_path, "widths", ".json"),
        "font_id": font_id,
        "entry_count": 96,
        "first_character_code": 0x50,
    }


def romaji_font_2bpp_preview_output(raw_path: str, entry: dict[str, Any]) -> dict[str, Any] | None:
    payload = str(entry.get("payload_path") or "").replace("\\", "/").lower()
    size = int(entry["size"])
    if payload != "fonts/romaji.gfx":
        return None
    trim = size % 16
    if trim == 0:
        trim = 0
    elif (size - trim) <= 0:
        return None
    return {
        "kind": "snes_2bpp_tiles_png",
        "path": preview_path(raw_path, "2bpp_preview"),
        "columns": 11,
        **({"trim_trailing_bytes": trim} if trim else {}),
    }


def load_battle_bg_palette_registry(
    bank_manifest_dir: Path,
    rom: bytes,
) -> dict[int, dict[str, Any]]:
    registry: dict[int, dict[str, Any]] = {}
    for path in sorted(bank_manifest_dir.glob("asset-bank-*.json")):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for entry in manifest.get("binary_assets", []):
            if str(entry.get("extension", "")).lower() != "pal":
                continue
            number = battle_bg_asset_number(entry, "palettes", "pal")
            if number is None:
                continue
            source = make_source(entry, rom)
            if entry.get("compressed") or str(entry.get("payload_path", "")).lower().endswith(".lzhal"):
                source["compression"] = "earthbound_lzhal"
            registry[number] = source
    return registry


def source_from_file_offset(rom: bytes, offset: int, size: int) -> dict[str, Any]:
    if size <= 0:
        raise ValueError(f"Source size must be positive, got {size}")
    bank = rom_tools.canonical_bank_for_file_offset(offset)
    start = offset % 0x10000
    end = start + size
    if end > 0x10000:
        raise ValueError(f"Source crosses a bank boundary: offset 0x{offset:06X} size {size}")
    data = rom[offset : offset + size]
    if len(data) != size:
        raise ValueError(f"ROM slice extends past EOF at 0x{offset:06X} size {size}")
    return {
        "type": "rom-range",
        "range": f"{bank:02X}:{start:04X}..{bank:02X}:{end:04X}",
        "bytes": size,
        "sha1": hashlib.sha1(data).hexdigest(),
    }


def load_overworld_sprite_palette_registry(
    yml_path: Path,
    rom: bytes,
) -> dict[int, dict[str, Any]]:
    registry: dict[int, dict[str, Any]] = {}
    if not yml_path.exists():
        return registry

    current: dict[str, str] = {}
    for line in yml_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("- subdir:"):
            current = {"subdir": line.split(":", 1)[1].strip().strip("'\"")}
            continue
        if not current:
            continue
        match = re.match(r"\s+(name|offset|size|extension|compressed):\s*(.+)$", line)
        if match is None:
            continue
        current[match.group(1)] = match.group(2).strip().strip("'\"")
        if {"subdir", "name", "offset", "size", "extension", "compressed"} <= set(current):
            if (
                current["subdir"] == "overworld_sprites/palettes"
                and current["extension"].lower() == "pal"
            ):
                palette_id = int(current["name"])
                offset = int(current["offset"], 0)
                size = int(current["size"], 0)
                source = source_from_file_offset(rom, offset, size)
                if current["compressed"].lower() == "true":
                    source["compression"] = "earthbound_lzhal"
                registry[palette_id] = source
            current = {}

    return registry


def load_battle_sprite_palette_registry(
    bank_manifest_dir: Path,
    rom: bytes,
) -> dict[int, dict[str, Any]]:
    registry: dict[int, dict[str, Any]] = {}
    for path in sorted(bank_manifest_dir.glob("asset-bank-*.json")):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for entry in manifest.get("binary_assets", []):
            if str(entry.get("extension", "")).lower() != "pal":
                continue
            number = battle_sprite_asset_number(entry, "pal")
            if number is None:
                continue
            source = make_source(entry, rom)
            if entry.get("compressed") or str(entry.get("payload_path", "")).lower().endswith(".lzhal"):
                source["compression"] = "earthbound_lzhal"
            registry[number] = source
    return registry


def load_battle_sprite_palette_usage() -> dict[int, list[int]]:
    path = ROOT / "refs" / "ebsrc-main" / "ebsrc-main" / "src" / "data" / "battle" / "enemies.asm"
    if not path.exists():
        return {}

    usage: dict[int, set[int]] = {}
    text = path.read_text(encoding="utf-8")
    for block in re.split(r"\n\s*\n", text):
        sprite_match = re.search(r"\.WORD\s+\$([0-9A-Fa-f]{4})\s*;Battle sprite", block)
        palette_match = re.search(r"\.BYTE\s+\$([0-9A-Fa-f]{2})\s*;Palette", block)
        if sprite_match is None or palette_match is None:
            continue
        sprite = int(sprite_match.group(1), 16)
        palette = int(palette_match.group(1), 16)
        usage.setdefault(sprite, set()).add(palette)

    return {sprite: sorted(palettes) for sprite, palettes in usage.items()}


def load_battle_sprite_sizes() -> dict[int, tuple[int, int]]:
    path = ROOT / "refs" / "ebsrc-main" / "ebsrc-main" / "src" / "data" / "battle" / "battle_sprites_pointers.asm"
    if not path.exists():
        return {}

    sizes: dict[int, tuple[int, int]] = {}
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"\.DWORD\s+BATTLE_SPRITE_(\d+)\s*\n\s*"
        r"\.BYTE\s+BATTLE_SPRITE_SIZE::_(\d+)X(\d+)"
    )
    for match in pattern.finditer(text):
        sizes[int(match.group(1))] = (int(match.group(2)), int(match.group(3)))
    return sizes


def load_battle_bg_graphics_registry(
    bank_manifest_dir: Path,
    rom: bytes,
) -> dict[int, dict[str, Any]]:
    registry: dict[int, dict[str, Any]] = {}
    for path in sorted(bank_manifest_dir.glob("asset-bank-*.json")):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for entry in manifest.get("binary_assets", []):
            if str(entry.get("extension", "")).lower() != "gfx":
                continue
            number = battle_bg_asset_number(entry, "graphics", "gfx")
            if number is None:
                continue
            source = make_source(entry, rom)
            if entry.get("compressed") or str(entry.get("payload_path", "")).lower().endswith(".lzhal"):
                source["compression"] = "earthbound_lzhal"
            registry[number] = source
    return registry


def palette_outputs(raw_path: str, compressed: bool) -> list[dict[str, Any]]:
    prefix = "earthbound_lzhal_" if compressed else ""
    return [
        {
            "kind": f"{prefix}snes_palette_json",
            "path": sidecar_path(raw_path, "palette", ".json"),
        },
        {
            "kind": f"{prefix}snes_palette_swatch_png",
            "path": sidecar_path(raw_path, "palette", ".png"),
            "per_row": 16,
            "swatch": 16,
        },
    ]


def battle_bg_palette_preview_output(
    raw_path: str,
    entry: dict[str, Any],
    palette_registry: dict[int, dict[str, Any]],
    compressed: bool,
) -> dict[str, Any] | None:
    number = battle_bg_asset_number(entry, "graphics", "gfx")
    if number is None or number not in palette_registry:
        return None
    palette_source = palette_registry[number]
    if palette_source.get("compression") is None and int(palette_source.get("bytes", 0)) < 32:
        return None
    return {
        "kind": (
            "earthbound_lzhal_snes_4bpp_tiles_palette_png"
            if compressed
            else "snes_4bpp_tiles_palette_png"
        ),
        "path": preview_path(raw_path, "palette_preview"),
        "columns": 8,
        "colors": 16,
        "palette_source": palette_source,
    }


def battle_bg_arrangement_preview_output(
    raw_path: str,
    entry: dict[str, Any],
    graphics_registry: dict[int, dict[str, Any]],
    palette_registry: dict[int, dict[str, Any]],
    compressed: bool,
    rom: bytes,
) -> dict[str, Any] | None:
    number = battle_bg_asset_number(entry, "arrangements", "arr")
    if number is None:
        return None
    graphics_source = graphics_registry.get(number)
    palette_source = palette_registry.get(number)
    if graphics_source is None or palette_source is None:
        return None
    arrangement_data = source_bytes_from_manifest_source(rom, make_source(entry, rom))
    if compressed:
        arrangement_data, _ = decompress_c41a9e.decompress_blob(arrangement_data, dest_base=0xC000)
    if len(arrangement_data) != 2048:
        return None
    max_tile = max(
        arrangement_data[offset] | ((arrangement_data[offset + 1] & 0x03) << 8)
        for offset in range(0, len(arrangement_data), 2)
    )

    graphics_data = source_bytes_from_manifest_source(rom, graphics_source)
    if graphics_source.get("compression") == "earthbound_lzhal":
        graphics_data, _ = decompress_c41a9e.decompress_blob(graphics_data, dest_base=0xC000)
    palette_data = source_bytes_from_manifest_source(rom, palette_source)
    if palette_source.get("compression") == "earthbound_lzhal":
        palette_data, _ = decompress_c41a9e.decompress_blob(palette_data, dest_base=0xC000)

    if len(graphics_data) % 32 == 0 and len(graphics_data) // 32 > max_tile and len(palette_data) >= 32:
        bpp = 4
        colors = 16
    elif len(graphics_data) % 16 == 0 and len(graphics_data) // 16 > max_tile and len(palette_data) >= 8:
        bpp = 2
        colors = 4
    else:
        return None

    return {
        "kind": "earthbound_lzhal_battle_bg_arrangement_png",
        "path": preview_path(raw_path, "composed_preview"),
        "width_tiles": 32,
        "height_tiles": 32,
        "bpp": bpp,
        "colors": colors,
        "arrangement_id": number,
        "graphics_id": number,
        "palette_id": number,
        "graphics_source": graphics_source,
        "palette_source": palette_source,
    }


def battle_sprite_palette_preview_outputs(
    raw_path: str,
    entry: dict[str, Any],
    palette_registry: dict[int, dict[str, Any]],
    palette_usage: dict[int, list[int]],
    sprite_sizes: dict[int, tuple[int, int]],
    compressed: bool,
) -> list[dict[str, Any]]:
    number = battle_sprite_asset_number(entry, "gfx")
    if number is None or number not in palette_usage:
        return []

    outputs: list[dict[str, Any]] = []
    sprite_size = sprite_sizes.get(number)
    for palette in palette_usage[number]:
        palette_source = palette_registry.get(palette)
        if palette_source is None:
            continue
        outputs.append(
            {
                "kind": (
                    "earthbound_lzhal_snes_4bpp_tiles_palette_png"
                    if compressed
                    else "snes_4bpp_tiles_palette_png"
                ),
                "path": preview_path(raw_path, f"palette_{palette:02d}_preview"),
                "columns": 8,
                "colors": 16,
                "sprite_id": number,
                "palette_id": palette,
                "palette_source": palette_source,
            }
        )
        if compressed and sprite_size is not None:
            width, height = sprite_size
            outputs.append(
                {
                    "kind": "earthbound_lzhal_battle_sprite_png",
                    "path": preview_path(raw_path, f"palette_{palette:02d}_sprite"),
                    "width": width,
                    "height": height,
                    "colors": 16,
                    "sprite_id": number,
                    "palette_id": palette,
                    "palette_source": palette_source,
                }
            )
    return outputs


def overworld_sprite_palette_preview_outputs(
    raw_path: str,
    entry: dict[str, Any],
    palette_registry: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    number = overworld_sprite_asset_number(entry)
    if number is None or 0 not in palette_registry:
        return []

    return [
        {
            "kind": "snes_4bpp_tiles_palette_png",
            "path": preview_path(raw_path, "palette_00_preview"),
            "columns": 8,
            "colors": 16,
            "sprite_id": number,
            "palette_id": 0,
            "palette_source": palette_registry[0],
        }
    ]


def binary_outputs(
    bank: str,
    entry: dict[str, Any],
    rom: bytes,
    palette_registry: dict[int, dict[str, Any]],
    graphics_registry: dict[int, dict[str, Any]],
    battle_sprite_palette_registry: dict[int, dict[str, Any]],
    battle_sprite_palette_usage: dict[int, list[int]],
    battle_sprite_sizes: dict[int, tuple[int, int]],
    overworld_sprite_palette_registry: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    payload = str(entry.get("payload_path") or f"asset_{entry['order']:03d}.bin")
    raw_path = output_payload_path(bank, payload)
    outputs: list[dict[str, Any]] = [{"kind": "raw", "path": raw_path}]

    extension = str(entry.get("extension", "")).lower()
    size = int(entry["size"])
    compressed = bool(entry.get("compressed")) or payload.lower().endswith(".lzhal")
    chunk_index = map_tile_chunk_index(payload)
    if chunk_index is not None and not compressed and size % 2 == 0:
        outputs.append(
            {
                "kind": "map_tile_chunk_index_json",
                "path": sidecar_path(raw_path, "tile_index", ".json"),
                "chunk_index": chunk_index,
            }
        )
    if compressed:
        decompressed_path = without_lzhal_suffix(raw_path)
        outputs.append(
            {
                "kind": "earthbound_lzhal",
                "path": decompressed_path,
            }
        )
        decompressed_size = lzhal_decompressed_size(rom, entry)
        if extension == "pal" and decompressed_size is not None and decompressed_size % 2 == 0:
            outputs.extend(palette_outputs(decompressed_path, compressed=True))
        if extension == "gfx" and decompressed_size is not None and decompressed_size % 32 == 0:
            outputs.append(
                {
                    "kind": "earthbound_lzhal_snes_4bpp_tiles_png",
                    "path": preview_path(decompressed_path, "4bpp_preview"),
                    "columns": 8,
                }
            )
            palette_preview = battle_bg_palette_preview_output(
                decompressed_path,
                entry,
                palette_registry,
                compressed=True,
            )
            if palette_preview is not None:
                outputs.append(palette_preview)
            outputs.extend(
                battle_sprite_palette_preview_outputs(
                    decompressed_path,
                    entry,
                    battle_sprite_palette_registry,
                    battle_sprite_palette_usage,
                    battle_sprite_sizes,
                    compressed=True,
                )
            )
        if extension == "arr" and decompressed_size == 2048:
            arrangement_preview = battle_bg_arrangement_preview_output(
                decompressed_path,
                entry,
                graphics_registry,
                palette_registry,
                compressed=True,
                rom=rom,
            )
            if arrangement_preview is not None:
                outputs.append(arrangement_preview)
        return outputs

    if extension == "gfx" and not compressed and size % 32 == 0:
        outputs.append(
            {
                "kind": "snes_4bpp_tiles_png",
                "path": preview_path(raw_path, "4bpp_preview"),
                "columns": 8,
            }
        )
        palette_preview = battle_bg_palette_preview_output(
            raw_path,
            entry,
            palette_registry,
            compressed=False,
        )
        if palette_preview is not None:
            outputs.append(palette_preview)
        outputs.extend(
            overworld_sprite_palette_preview_outputs(
                raw_path,
                entry,
                overworld_sprite_palette_registry,
            )
        )
    if extension == "gfx" and not compressed:
        romaji_preview = romaji_font_2bpp_preview_output(raw_path, entry)
        if romaji_preview is not None:
            outputs.append(romaji_preview)
    if extension == "pal" and not compressed and size % 2 == 0:
        outputs.extend(palette_outputs(raw_path, compressed=False))
    swirl_metadata = battle_swirl_frame_metadata_output(raw_path, entry)
    if swirl_metadata is not None:
        outputs.append(swirl_metadata)
    font_metrics = font_metric_widths_output(raw_path, entry)
    if font_metrics is not None:
        outputs.append(font_metrics)
    return outputs


def make_source(entry: dict[str, Any], rom: bytes) -> dict[str, Any]:
    size = int(entry["size"])
    return {
        "type": "rom-range",
        "range": inclusive_span_to_exclusive_range(str(entry["cpu_start"]), str(entry["cpu_end"])),
        "bytes": size,
        "sha1": rom_slice_sha1(rom, str(entry["file_offset"]), size),
    }


BATTLE_BG_POINTER_TABLES = {
    "data/battle/backgrounds/graphics_pointers.asm": {
        "table_id": 0,
        "table_role": "graphics",
        "description": "graphics payload",
    },
    "data/battle/backgrounds/arrangement_pointers.asm": {
        "table_id": 1,
        "table_role": "arrangement",
        "description": "tile arrangement payload",
    },
    "data/battle/backgrounds/palette_pointers.asm": {
        "table_id": 2,
        "table_role": "palette",
        "description": "palette payload",
    },
}


BATTLE_BG_RUNTIME_TABLES = {
    "data/battle/backgrounds/config_table.asm": {
        "kind": "battle_bg_config_table_json",
        "row_size": 17,
        "description": "327-row battle background layer config table",
    },
    "data/battle/backgrounds/scrolling_table.asm": {
        "kind": "battle_bg_scrolling_table_json",
        "row_size": 10,
        "description": "120-row battle background scrolling movement table",
    },
    "data/battle/backgrounds/distortion_table.asm": {
        "kind": "battle_bg_distortion_table_json",
        "row_size": 17,
        "description": "135-row battle background distortion effect table",
    },
}


def battle_bg_pointer_table_output(raw_path: str, include: str, size: int) -> dict[str, Any] | None:
    table = BATTLE_BG_POINTER_TABLES.get(include)
    if table is None or size % 4:
        return None
    return {
        "kind": "battle_bg_pointer_table_json",
        "path": sidecar_path(raw_path, "decoded", ".json"),
        "entry_count": size // 4,
        "table_id": table["table_id"],
        "table_role": table["table_role"],
    }


def battle_bg_runtime_table_output(raw_path: str, include: str, size: int) -> dict[str, Any] | None:
    table = BATTLE_BG_RUNTIME_TABLES.get(include)
    if table is None:
        return None
    row_size = int(table["row_size"])
    if size % row_size:
        return None
    return {
        "kind": table["kind"],
        "path": sidecar_path(raw_path, "decoded", ".json"),
        "row_count": size // row_size,
    }


def convert_binary_asset(
    bank: str,
    entry: dict[str, Any],
    rom: bytes,
    palette_registry: dict[int, dict[str, Any]],
    graphics_registry: dict[int, dict[str, Any]],
    battle_sprite_palette_registry: dict[int, dict[str, Any]],
    battle_sprite_palette_usage: dict[int, list[int]],
    battle_sprite_sizes: dict[int, tuple[int, int]],
    overworld_sprite_palette_registry: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    label = str(entry.get("label") or "")
    payload = str(entry.get("payload_path") or "")
    stable_name = slug(label or payload, f"asset_{entry['order']}")
    notes = [
        f"Source payload path from ebsrc: {payload}",
        f"Original file offset: {entry['file_offset']}",
    ]
    if entry.get("compressed"):
        notes.append("Payload is marked compressed in earthbound.yml or inferred from its extension.")
    if entry.get("inferred_from_next_asset"):
        notes.append("Span was inferred from the next known asset because yml metadata was missing.")
    if entry.get("inference_note"):
        notes.append(str(entry["inference_note"]))

    return {
        "id": f"asset.{bank.lower()}.{stable_name}",
        "title": label or payload,
        "category": binary_category(entry),
        "source": make_source(entry, rom),
        "outputs": binary_outputs(
            bank,
            entry,
            rom,
            palette_registry,
            graphics_registry,
            battle_sprite_palette_registry,
            battle_sprite_palette_usage,
            battle_sprite_sizes,
            overworld_sprite_palette_registry,
        ),
        "notes": notes,
    }


def convert_table_asset(bank: str, entry: dict[str, Any], rom: bytes) -> dict[str, Any] | None:
    if "error" in entry or "file_offset" not in entry or "size" not in entry:
        return None
    size = int(entry["size"])
    if size <= 0:
        return None
    include = str(entry.get("include") or f"table_{entry['order']}")
    stable_name = slug(include, f"table_{entry['order']}")
    notes = [
        f"Source include from ebsrc: {include}",
        f"Original file offset: {entry['file_offset']}",
    ]
    if entry.get("inferred_from_next_asset"):
        notes.append("Size was inferred from the next known binary asset boundary.")

    raw_path = f"{bank.lower()}/tables/{int(entry['order']):03d}_{stable_name}.bin"
    outputs = [
        {
            "kind": "raw",
            "path": raw_path,
        }
    ]
    if bank.upper() == "CE" and include == "data/battle/swirl_pointers.asm" and size == 252:
        outputs.append(
            {
                "kind": "battle_swirl_pointer_table_json",
                "path": sidecar_path(raw_path, "decoded", ".json"),
                "entry_count": 126,
                "pointer_bank": 0xCE,
            }
        )
        notes.append(
            "Decoded as the 126-entry little-endian pointer table for CE SWIRL_DATA payload frames."
        )
    if bank.upper() == "CE" and include == "inline:SWIRL_PRIMARY_TABLE" and size == 28:
        outputs.append(
            {
                "kind": "battle_swirl_sequence_table_json",
                "path": sidecar_path(raw_path, "decoded", ".json"),
                "row_count": 7,
            }
        )
        notes.append(
            "Decoded as the seven-row primary battle swirl sequence table; rows preserve speed, first payload, and frame count."
        )
    if bank.upper() == "CE" and include == "data/battle/battle_sprites_pointers.asm" and size % 5 == 0:
        outputs.append(
            {
                "kind": "battle_sprite_pointer_table_json",
                "path": sidecar_path(raw_path, "decoded", ".json"),
                "entry_count": size // 5,
            }
        )
        notes.append(
            "Decoded as the battle sprite pointer/size table; rows preserve long pointer target and sprite dimensions."
        )
    if bank.upper() == "CB" and include == "data/battle/background_layer_table.asm" and size % 4 == 0:
        outputs.append(
            {
                "kind": "battle_bg_layer_table_json",
                "path": sidecar_path(raw_path, "decoded", ".json"),
                "row_count": size // 4,
                "config_row_count": 327,
            }
        )
        notes.append(
            "Decoded as the battle-entry background layer table; rows preserve two CA layer config references."
        )
    if bank.upper() == "CC" and include == "data/animation_sequence_pointers.asm" and size % 8 == 0:
        outputs.append(
            {
                "kind": "animation_sequence_pointer_table_json",
                "path": sidecar_path(raw_path, "decoded", ".json"),
                "row_count": size // 8,
            }
        )
        notes.append(
            "Decoded as the named animation sequence pointer table; rows preserve the long pointer and four caller parameter bytes."
        )
    if bank.upper() == "CC" and include == "data/psi_anim_cfg.asm" and size % 12 == 0:
        outputs.append(
            {
                "kind": "psi_anim_config_table_json",
                "path": sidecar_path(raw_path, "decoded", ".json"),
                "row_count": size // 12,
            }
        )
        notes.append(
            "Decoded as 12-byte PSI animation config rows used by SHOW_PSI_ANIMATION for graphics, timing, target mode, and enemy-color state."
        )
    if bank.upper() == "CC" and include == "data/psi_anim_pointers.asm" and size % 4 == 0:
        outputs.append(
            {
                "kind": "psi_anim_pointer_table_json",
                "path": sidecar_path(raw_path, "decoded", ".json"),
                "entry_count": size // 4,
            }
        )
        notes.append(
            "Decoded as the PSI animation arrangement pointer table; one long pointer per PSI animation id."
        )
    if bank.upper() == "E0" and include == "data/text_window_properties.asm" and size == 495:
        outputs.append(
            {
                "kind": "text_window_properties_table_json",
                "path": sidecar_path(raw_path, "decoded", ".json"),
                "selector_count": 5,
                "palette_block_count": 7,
                "town_map_pointer_count": 6,
            }
        )
        notes.append(
            "Decoded as the combined text-window flavor selector, palette-block, movement-text palette, and town-map graphics pointer table."
        )
    if bank.upper() == "E1" and include == "data/unknown/E1F203.asm" and size == 894:
        outputs.append(
            {
                "kind": "town_map_icon_table_json",
                "path": sidecar_path(raw_path, "decoded", ".json"),
                "icon_count": 23,
                "town_map_count": 6,
            }
        )
        notes.append(
            "Decoded as the town-map icon descriptor, icon pointer, blink suppress, placement pointer, and placement record table."
        )
    if bank.upper() == "E1" and include == "data/photographer_cfg.asm" and size == 1984:
        outputs.append(
            {
                "kind": "photographer_config_table_json",
                "path": sidecar_path(raw_path, "decoded", ".json"),
                "row_count": 32,
                "record_size_bytes": 62,
            }
        )
        notes.append(
            "Decoded as 32 photographer/photo-scene records; rows preserve event flag, map-load position, background offset, slide vector, photo anchor, visual positions, and spawned entity rows."
        )
    if bank.upper() == "DC" and include == "data/map/per-sector_music.asm" and size == 2560:
        outputs.append(
            {
                "kind": "map_sector_music_table_json",
                "path": sidecar_path(raw_path, "decoded", ".json"),
                "column_count": 80,
                "row_count": 32,
            }
        )
        notes.append(
            "Decoded as the 80-by-32 map-sector destination/music row lookup consumed by C0:68F4 before resolving the current map music track."
        )
    if bank.upper() == "D7" and include == "data/map/global_tileset_palette_data.asm" and size == 7680:
        outputs.append(
            {
                "kind": "map_global_tileset_palette_data_json",
                "path": sidecar_path(raw_path, "decoded", ".json"),
                "column_count": 80,
                "row_count": 32,
                "attribute_word_table_offset": 2560,
            }
        )
        notes.append(
            "Decoded as the 80-by-32 D7:A800 context-byte table plus the 80-by-32 D7:B200 per-sector attribute word table consumed by C0/C4 map loaders."
        )
    if bank.upper() == "DA" and include == "data/map/unknown_map_palette_pointer_table.asm" and size == 96:
        outputs.append(
            {
                "kind": "map_palette_pointer_table_json",
                "path": sidecar_path(raw_path, "decoded", ".json"),
                "entry_count": 32,
                "pointer_bank": 0xDA,
            }
        )
        notes.append(
            "Decoded as the 32-entry DA map palette long-pointer table; entries target MAP_DATA_PALETTE_0..31 payload starts."
        )
    if bank.upper() == "CA":
        battle_bg_pointer_output = battle_bg_pointer_table_output(raw_path, include, size)
        if battle_bg_pointer_output is not None:
            outputs.append(battle_bg_pointer_output)
            table = BATTLE_BG_POINTER_TABLES[include]
            notes.append(
                "Decoded as a 4-byte little-endian battle background pointer table "
                f"for {table['description']} targets."
            )
        battle_bg_runtime_output = battle_bg_runtime_table_output(raw_path, include, size)
        if battle_bg_runtime_output is not None:
            outputs.append(battle_bg_runtime_output)
            table = BATTLE_BG_RUNTIME_TABLES[include]
            notes.append(f"Decoded as the {table['description']}.")

    return {
        "id": f"table.{bank.lower()}.{int(entry['order']):03d}_{stable_name}",
        "title": include,
        "category": "raw-table",
        "source": make_source(entry, rom),
        "outputs": outputs,
        "notes": notes,
    }


def convert_gap_asset(bank: str, index: int, gap: dict[str, Any], rom: bytes) -> dict[str, Any] | None:
    size = int(gap["size"])
    if size <= 0:
        return None
    entry = {
        "cpu_start": gap["cpu_start"],
        "cpu_end": gap["cpu_end"],
        "file_offset": gap["file_start"],
        "size": size,
    }
    start_slug = slug(str(gap["cpu_start"]), f"gap_{index}")
    return {
        "id": f"gap.{bank.lower()}.{start_slug}",
        "title": f"Bank {bank} coverage gap {index}",
        "category": "raw-gap",
        "source": make_source(entry, rom),
        "outputs": [
            {
                "kind": "raw",
                "path": f"{bank.lower()}/gaps/{index:02d}_{start_slug}.bin",
            }
        ],
        "notes": [
            "Raw coverage gap preserved for byte accounting; promote to a named asset/table when its role is understood.",
            f"Original file span: {gap['file_start']}..{gap['file_end']}",
        ],
    }


def convert_manifest(
    bank_manifest: dict[str, Any],
    rom: bytes,
    include_tables: bool,
    include_gaps: bool,
    palette_registry: dict[int, dict[str, Any]],
    graphics_registry: dict[int, dict[str, Any]],
    battle_sprite_palette_registry: dict[int, dict[str, Any]],
    battle_sprite_palette_usage: dict[int, list[int]],
    battle_sprite_sizes: dict[int, tuple[int, int]],
    overworld_sprite_palette_registry: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    bank = str(bank_manifest["bank"]).upper()
    assets: list[dict[str, Any]] = []

    for entry in bank_manifest.get("binary_assets", []):
        assets.append(
            convert_binary_asset(
                bank,
                entry,
                rom,
                palette_registry,
                graphics_registry,
                battle_sprite_palette_registry,
                battle_sprite_palette_usage,
                battle_sprite_sizes,
                overworld_sprite_palette_registry,
            )
        )

    if include_tables:
        for entry in bank_manifest.get("table_includes", []):
            asset = convert_table_asset(bank, entry, rom)
            if asset is not None:
                assets.append(asset)

    if include_gaps:
        for index, gap in enumerate(bank_manifest.get("coverage_gaps", []), start=1):
            asset = convert_gap_asset(bank, index, gap, rom)
            if asset is not None:
                assets.append(asset)

    summary = bank_manifest.get("summary", {})
    return {
        "schema": SCHEMA,
        "game": "earthbound-us",
        "title": f"Bank {bank} asset extraction manifest",
        "source_policy": {
            "requires_user_supplied_rom": True,
            "do_not_commit_generated_outputs": True,
            "default_output_root": DEFAULT_OUTPUT_ROOT,
        },
        "generator": {
            "tool": "tools/build_asset_extraction_manifest.py",
            "source_schema": bank_manifest.get("schema"),
        },
        "references": [
            f"notes/bank-{bank.lower()}-asset-data-map.md",
            "refs/ebsrc-main/ebsrc-main/earthbound.yml",
            str(bank_manifest.get("config", "")),
        ],
        "bank_summary": summary,
        "assets": assets,
    }


def write_manifest(out_dir: Path, bank: str, manifest: dict[str, Any]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"bank-{bank.lower()}-assets.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    args = parse_args()
    rom_path = rom_tools.find_rom(args.rom)
    rom = rom_tools.load_rom(rom_path)
    yml_path = Path(args.yml)
    bank_manifest_dir = Path(args.bank_manifest_dir)
    out_dir = Path(args.out_dir)
    palette_registry = load_battle_bg_palette_registry(bank_manifest_dir, rom)
    graphics_registry = load_battle_bg_graphics_registry(bank_manifest_dir, rom)
    battle_sprite_palette_registry = load_battle_sprite_palette_registry(bank_manifest_dir, rom)
    battle_sprite_palette_usage = load_battle_sprite_palette_usage()
    battle_sprite_sizes = load_battle_sprite_sizes()
    overworld_sprite_palette_registry = load_overworld_sprite_palette_registry(yml_path, rom)

    for raw_bank in args.bank:
        bank = raw_bank.upper()
        bank_manifest = load_or_build_bank_manifest(bank, bank_manifest_dir, yml_path, rom_path)
        extraction_manifest = convert_manifest(
            bank_manifest,
            rom,
            include_tables=args.include_tables,
            include_gaps=args.include_gaps,
            palette_registry=palette_registry,
            graphics_registry=graphics_registry,
            battle_sprite_palette_registry=battle_sprite_palette_registry,
            battle_sprite_palette_usage=battle_sprite_palette_usage,
            battle_sprite_sizes=battle_sprite_sizes,
            overworld_sprite_palette_registry=overworld_sprite_palette_registry,
        )
        path = write_manifest(out_dir, bank, extraction_manifest)
        print(f"{bank}: wrote {len(extraction_manifest['assets'])} assets to {rel(path)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
