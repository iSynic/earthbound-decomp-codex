from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from rom_tools import find_rom, hirom_to_file_offset, load_rom


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DE_MANIFEST = ROOT / "asset-manifests" / "bank-de-assets.json"
DEFAULT_DF_MANIFEST = ROOT / "asset-manifests" / "bank-df-assets.json"
DEFAULT_TILESET_BUNDLES = ROOT / "notes" / "map-tileset-bundles.json"
DEFAULT_FTS_CONTRACT = ROOT / "notes" / "map-fts-animation-settings-contract.json"
DEFAULT_JSON_OUT = ROOT / "notes" / "map-tile-animation-runtime-contract.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "map-tile-animation-runtime-contract.md"
SCHEMA = "earthbound-decomp.map-tile-animation-runtime-contract.v1"

ANIMATION_GFX_POINTER_TABLE_BANK = 0xEF
ANIMATION_GFX_POINTER_TABLE_OFFSET = 0x11CB
ANIMATION_SCRIPT_POINTER_TABLE_BANK = 0xEF
ANIMATION_SCRIPT_POINTER_TABLE_OFFSET = 0x121B
ANIMATION_TABLE_ENTRY_COUNT = 20
LONG_POINTER_BYTES = 4
ANIMATION_SCRIPT_DATA_END = 0x133F
RUNTIME_RECORD_WRAM_START = 0x43DC
RUNTIME_RECORD_BYTES = 0x10
RUNTIME_RECORD_CAPACITY = 8
RUNTIME_RECORD_COUNT_WRAM = 0x4472


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify EF map tile-animation graphics pointers and runtime upload scripts."
    )
    parser.add_argument("--rom", help="EarthBound US ROM path.")
    parser.add_argument("--de-manifest", default=str(DEFAULT_DE_MANIFEST))
    parser.add_argument("--df-manifest", default=str(DEFAULT_DF_MANIFEST))
    parser.add_argument("--tileset-bundles", default=str(DEFAULT_TILESET_BUNDLES))
    parser.add_argument("--fts-contract", default=str(DEFAULT_FTS_CONTRACT))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def cpu_to_offset(bank: int, address: int, rom_size: int) -> int:
    offset = hirom_to_file_offset(bank, address, rom_size)
    if offset is None:
        raise ValueError(f"{bank:02X}:{address:04X} does not map to ROM data")
    return offset


def read_long_pointer(rom_data: bytes, bank: int, address: int) -> int:
    offset = cpu_to_offset(bank, address, len(rom_data))
    return (
        rom_data[offset]
        | (rom_data[offset + 1] << 8)
        | (rom_data[offset + 2] << 16)
        | (rom_data[offset + 3] << 24)
    )


def pointer_to_cpu(pointer: int) -> str:
    return f"{(pointer >> 16) & 0xFF:02X}:{pointer & 0xFFFF:04X}"


def pointer_to_offset(pointer: int, rom_size: int) -> int:
    bank = (pointer >> 16) & 0xFF
    address = pointer & 0xFFFF
    return cpu_to_offset(bank, address, rom_size)


def parse_cpu_range_start(text: str) -> tuple[int, int]:
    start = text.split("..", 1)[0]
    bank_text, address_text = start.split(":", 1)
    return int(bank_text, 16), int(address_text, 16)


def animation_assets_by_index(manifests: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    assets: dict[int, dict[str, Any]] = {}
    for manifest in manifests:
        for asset in manifest["assets"]:
            title = str(asset["title"])
            if not title.startswith("MAP_DATA_TILE_ANIMATION_GFX_"):
                continue
            animation_id = int(title.rsplit("_", 1)[1])
            bank, address = parse_cpu_range_start(str(asset["source"]["range"]))
            outputs = {output["kind"]: output["path"] for output in asset["outputs"]}
            assets[animation_id] = {
                "asset_id": asset["id"],
                "title": title,
                "bank": bank,
                "start": address,
                "start_cpu": f"{bank:02X}:{address:04X}",
                "range": asset["source"]["range"],
                "bytes": int(asset["source"]["bytes"]),
                "sha1": asset["source"]["sha1"],
                "raw_output": outputs.get("raw"),
                "decompressed_output": outputs.get("earthbound_lzhal"),
                "preview_output": outputs.get("earthbound_lzhal_snes_4bpp_tiles_png"),
                "is_tiny_placeholder_payload": int(asset["source"]["bytes"]) == 25,
            }
    return assets


def tilesets_by_id(contract: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {int(row["tileset_id"]): row for row in contract["tilesets"]}


def fts_animation_context_by_tileset(contract: dict[str, Any]) -> dict[int, dict[str, Any]]:
    by_tileset = {int(row["tileset_id"]): row for row in contract["tilesets"]}
    ownership_by_tileset: dict[int, list[dict[str, Any]]] = {}
    for owner in contract.get("row_group_ownership", []):
        for tileset_id in owner["tileset_ids"]:
            ownership_by_tileset.setdefault(int(tileset_id), []).append(owner)

    result = {}
    for tileset_id, tileset in by_tileset.items():
        owners = sorted(ownership_by_tileset.get(tileset_id, []), key=lambda item: item["group"])
        result[tileset_id] = {
            "row_count": int(tileset["row_count"]),
            "row_ids": tileset["row_ids"],
            "owned_row_groups": [
                {
                    "group": owner["group"],
                    "group_base32_value": owner["group_base32_value"],
                    "slot_count": owner["slot_count"],
                    "slot_ids": owner["slot_ids"],
                    "row_ids": owner["row_ids"],
                }
                for owner in owners
            ],
            "owned_row_group_count": len(owners),
        }
    return result


def read_pointer_table(
    rom_data: bytes,
    bank: int,
    address: int,
    count: int,
) -> list[int]:
    return [
        read_long_pointer(rom_data, bank, address + (index * LONG_POINTER_BYTES))
        for index in range(count)
    ]


def decode_script_record(raw: bytes, record_index: int) -> dict[str, Any]:
    frame_count = raw[0]
    reload_delay = raw[1]
    transfer_size = raw[2] | (raw[3] << 8)
    source_base = raw[4] | (raw[5] << 8)
    vram_destination = raw[6] | (raw[7] << 8)
    total_source_bytes = frame_count * transfer_size
    return {
        "record_index": record_index,
        "frame_count_limit": frame_count,
        "reload_delay": reload_delay,
        "transfer_size_bytes": transfer_size,
        "transfer_size_tiles_4bpp": transfer_size // 32 if transfer_size % 32 == 0 else None,
        "source_base_offset": f"0x{source_base:04X}",
        "source_base_offset_value": source_base,
        "source_end_offset_exclusive": f"0x{source_base + total_source_bytes:04X}",
        "source_end_offset_exclusive_value": source_base + total_source_bytes,
        "total_source_bytes_if_linear_frames": total_source_bytes,
        "vram_destination": f"0x{vram_destination:04X}",
        "vram_destination_value": vram_destination,
    }


def decode_script(rom_data: bytes, pointer: int, next_pointer: int | None) -> dict[str, Any]:
    offset = pointer_to_offset(pointer, len(rom_data))
    count = rom_data[offset]
    byte_count = 1 + (count * 8)
    expected_end = offset + byte_count
    records = [
        decode_script_record(
            rom_data[offset + 1 + (index * 8) : offset + 1 + ((index + 1) * 8)],
            index,
        )
        for index in range(count)
    ]
    next_offset = pointer_to_offset(next_pointer, len(rom_data)) if next_pointer is not None else cpu_to_offset(
        ANIMATION_SCRIPT_POINTER_TABLE_BANK, ANIMATION_SCRIPT_DATA_END, len(rom_data)
    )
    return {
        "pointer": f"{pointer:08X}",
        "pointer_cpu": pointer_to_cpu(pointer),
        "record_count": count,
        "byte_count": byte_count,
        "end_cpu_exclusive": f"{(pointer >> 16) & 0xFF:02X}:{(pointer & 0xFFFF) + byte_count:04X}",
        "ends_at_next_pointer": expected_end == next_offset,
        "records": records,
        "max_source_end_offset_exclusive": max(
            (record["source_end_offset_exclusive_value"] for record in records),
            default=0,
        ),
        "total_upload_bytes_per_cycle": sum(record["transfer_size_bytes"] for record in records),
        "total_linear_frame_source_bytes": sum(
            record["total_source_bytes_if_linear_frames"] for record in records
        ),
        "runtime_record_bytes": count * RUNTIME_RECORD_BYTES,
        "fits_runtime_record_capacity": count <= RUNTIME_RECORD_CAPACITY,
    }


def build_entries(
    rom_data: bytes,
    assets: dict[int, dict[str, Any]],
    tilesets: dict[int, dict[str, Any]],
    fts_context: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    gfx_pointers = read_pointer_table(
        rom_data,
        ANIMATION_GFX_POINTER_TABLE_BANK,
        ANIMATION_GFX_POINTER_TABLE_OFFSET,
        ANIMATION_TABLE_ENTRY_COUNT,
    )
    script_pointers = read_pointer_table(
        rom_data,
        ANIMATION_SCRIPT_POINTER_TABLE_BANK,
        ANIMATION_SCRIPT_POINTER_TABLE_OFFSET,
        ANIMATION_TABLE_ENTRY_COUNT,
    )
    entries = []
    for index in range(ANIMATION_TABLE_ENTRY_COUNT):
        asset = assets.get(index)
        gfx_pointer = gfx_pointers[index]
        expected_pointer = None if asset is None else (asset["bank"] << 16) | asset["start"]
        script = decode_script(
            rom_data,
            script_pointers[index],
            script_pointers[index + 1] if index + 1 < len(script_pointers) else None,
        )
        tileset = tilesets.get(index, {})
        fts = fts_context.get(index, {})
        placeholder = bool(asset and asset["is_tiny_placeholder_payload"])
        empty_script = script["record_count"] == 0
        entries.append(
            {
                "animation_id": index,
                "graphics_pointer": f"{gfx_pointer:08X}",
                "graphics_pointer_cpu": pointer_to_cpu(gfx_pointer),
                "graphics_asset": asset,
                "graphics_pointer_match_status": (
                    "matches_map_data_tile_animation_gfx_asset"
                    if gfx_pointer == expected_pointer
                    else "mismatch"
                ),
                "script_pointer": script["pointer"],
                "script_pointer_cpu": script["pointer_cpu"],
                "script": script,
                "placeholder_empty_script_match": placeholder and empty_script,
                "nonplaceholder_nonempty_script_match": (not placeholder) and (not empty_script),
                "tileset_dependency": {
                    "tileset_id": index,
                    "sector_count": int(tileset.get("sector_count", 0)),
                    "dependency_status": tileset.get("dependency_status"),
                    "has_direct_fts_export": bool(tileset.get("has_direct_fts_export", False)),
                    "palette_setting_count": int(tileset.get("palette_setting_count", 0)),
                },
                "fts_animation_settings_context": fts,
            }
        )
    return entries


def build_contract(args: argparse.Namespace) -> dict[str, Any]:
    de_manifest_path = Path(args.de_manifest)
    df_manifest_path = Path(args.df_manifest)
    tileset_bundles_path = Path(args.tileset_bundles)
    fts_contract_path = Path(args.fts_contract)
    rom_data = load_rom(find_rom(args.rom))
    assets = animation_assets_by_index([load_json(df_manifest_path), load_json(de_manifest_path)])
    tilesets = tilesets_by_id(load_json(tileset_bundles_path))
    fts_context = fts_animation_context_by_tileset(load_json(fts_contract_path))
    entries = build_entries(rom_data, assets, tilesets, fts_context)

    graphics_matches = sum(
        1
        for entry in entries
        if entry["graphics_pointer_match_status"] == "matches_map_data_tile_animation_gfx_asset"
    )
    empty_scripts = [entry["animation_id"] for entry in entries if entry["script"]["record_count"] == 0]
    nonempty_scripts = [
        entry["animation_id"] for entry in entries if entry["script"]["record_count"] != 0
    ]
    tiny_payloads = [
        entry["animation_id"]
        for entry in entries
        if entry["graphics_asset"] and entry["graphics_asset"]["is_tiny_placeholder_payload"]
    ]
    return {
        "schema": SCHEMA,
        "title": "Map Tile Animation Runtime Contract",
        "generator": "tools/build_map_tile_animation_runtime_contract.py",
        "source_policy": (
            "ROM-verified runtime-table contract. This records pointer targets, "
            "asset IDs, upload-script fields, hashes, and counts only; it does "
            "not commit compressed or decompressed graphics payload bytes."
        ),
        "sources": {
            "de_manifest": rel(de_manifest_path),
            "df_manifest": rel(df_manifest_path),
            "tileset_bundles": rel(tileset_bundles_path),
            "fts_animation_settings_contract": rel(fts_contract_path),
            "graphics_pointer_table": "EF:11CB..EF:121B",
            "script_pointer_table": "EF:121B..EF:126B",
            "script_data": "EF:126B..EF:133F",
            "next_known_table": "EF:133F sprite grouping pointer table",
        },
        "runtime_model": {
            "loader": "C0:0085",
            "tick_consumer": "C0:0172",
            "selector_wram": "$4372",
            "decompressed_graphics_buffer": "7E:C000",
            "runtime_record_wram_start": f"${RUNTIME_RECORD_WRAM_START:04X}",
            "runtime_record_bytes": RUNTIME_RECORD_BYTES,
            "runtime_record_capacity": RUNTIME_RECORD_CAPACITY,
            "runtime_record_count_wram": f"${RUNTIME_RECORD_COUNT_WRAM:04X}",
            "transfer_routine": "C0:8616 mode A=0",
            "expanded_record_fields": [
                {"offset": "+0x00", "name": "frame_count_limit", "source": "script byte +0"},
                {"offset": "+0x02", "name": "reload_delay", "source": "script byte +1"},
                {"offset": "+0x04", "name": "transfer_size_bytes", "source": "script word +2"},
                {"offset": "+0x06", "name": "source_base_offset", "source": "script word +4"},
                {"offset": "+0x08", "name": "vram_destination", "source": "script word +6"},
                {"offset": "+0x0A", "name": "live_countdown", "source": "initialized from +0x02"},
                {"offset": "+0x0C", "name": "live_frame_counter", "source": "initialized to 0"},
                {"offset": "+0x0E", "name": "live_source_offset", "source": "initialized from +0x06"},
            ],
        },
        "summary": {
            "entry_count": len(entries),
            "graphics_pointer_asset_matches": graphics_matches,
            "script_pointer_entries": len(entries),
            "script_record_count": sum(entry["script"]["record_count"] for entry in entries),
            "nonempty_script_count": len(nonempty_scripts),
            "empty_script_count": len(empty_scripts),
            "nonempty_script_ids": nonempty_scripts,
            "empty_script_ids": empty_scripts,
            "tiny_placeholder_payload_ids": tiny_payloads,
            "placeholder_empty_script_matches": sum(
                1 for entry in entries if entry["placeholder_empty_script_match"]
            ),
            "nonplaceholder_nonempty_script_matches": sum(
                1 for entry in entries if entry["nonplaceholder_nonempty_script_match"]
            ),
            "script_records_fit_runtime_capacity": all(
                entry["script"]["fits_runtime_record_capacity"] for entry in entries
            ),
            "script_records_end_at_next_pointer": all(
                entry["script"]["ends_at_next_pointer"] for entry in entries
            ),
            "script_data_end_matches_sprite_grouping_table_start": entries[-1]["script"][
                "end_cpu_exclusive"
            ]
            == f"EF:{ANIMATION_SCRIPT_DATA_END:04X}",
            "max_script_records_per_entry": max(
                entry["script"]["record_count"] for entry in entries
            ),
            "direct_fts_entry_count": sum(
                1 for entry in entries if entry["tileset_dependency"]["has_direct_fts_export"]
            ),
            "used_by_sector_count": sum(
                1 for entry in entries if entry["tileset_dependency"]["sector_count"] > 0
            ),
        },
        "interpretation_notes": [
            "The graphics pointer table at EF:11CB maps animation IDs 0..19 to MAP_DATA_TILE_ANIMATION_GFX_N compressed payloads in banks DF and DE.",
            "The script pointer table at EF:121B maps the same animation IDs to variable upload-script records ending exactly at EF:133F, the known sprite grouping pointer table start.",
            "C0:0085 selects both tables by $4372, decompresses the selected graphics payload into 7E:C000, and expands each 8-byte script record into a 16-byte runtime record at $43DC.",
            "C0:0172 ticks the $43DC records and queues VRAM transfers through C0:8616 with A=0.",
            "The eight 25-byte tiny/placeholder compressed animation payloads exactly match the eight empty upload scripts.",
            "The 290-character .fts animation/settings rows remain a separate EBDecomp export layer; their row counts do not equal these runtime upload-script record counts.",
        ],
        "entries": entries,
    }


def write_markdown(contract: dict[str, Any], path: Path) -> None:
    summary = contract["summary"]
    runtime = contract["runtime_model"]
    lines = [
        "# Map Tile Animation Runtime Contract",
        "",
        "This ROM-verified contract closes the active EF/C0 map tile-animation",
        "runtime tables used by `C0:0085` and consumed by `C0:0172`.",
        "",
        "## Summary",
        "",
        f"- entries: `{summary['entry_count']}`",
        f"- graphics pointer/asset matches: `{summary['graphics_pointer_asset_matches']}`",
        f"- upload-script records: `{summary['script_record_count']}`",
        f"- nonempty scripts: `{summary['nonempty_script_count']}`",
        f"- empty scripts: `{summary['empty_script_count']}`",
        f"- tiny placeholder payload IDs: `{', '.join(str(item) for item in summary['tiny_placeholder_payload_ids'])}`",
        f"- placeholder/empty-script matches: `{summary['placeholder_empty_script_matches']}`",
        f"- nonplaceholder/nonempty-script matches: `{summary['nonplaceholder_nonempty_script_matches']}`",
        f"- max script records per entry: `{summary['max_script_records_per_entry']}`",
        f"- all scripts fit `$43DC` runtime capacity: `{summary['script_records_fit_runtime_capacity']}`",
        f"- all scripts end at the next pointer: `{summary['script_records_end_at_next_pointer']}`",
        f"- script data ends at sprite grouping table start: `{summary['script_data_end_matches_sprite_grouping_table_start']}`",
        "",
        "## Runtime Model",
        "",
        f"- selector: `{runtime['selector_wram']}`",
        f"- graphics pointer table: `{contract['sources']['graphics_pointer_table']}`",
        f"- upload-script pointer table: `{contract['sources']['script_pointer_table']}`",
        f"- upload-script data: `{contract['sources']['script_data']}`",
        f"- decompressed graphics buffer: `{runtime['decompressed_graphics_buffer']}`",
        f"- runtime records: `{runtime['runtime_record_wram_start']}` records of `{runtime['runtime_record_bytes']}` bytes",
        f"- active record count: `{runtime['runtime_record_count_wram']}`",
        f"- VRAM transfer routine: `{runtime['transfer_routine']}`",
        "",
        "Each 8-byte upload-script record expands to one 16-byte runtime record:",
        "",
        "| Runtime offset | Field | Source |",
        "| --- | --- | --- |",
    ]
    for field in runtime["expanded_record_fields"]:
        lines.append(f"| `{field['offset']}` | `{field['name']}` | {field['source']} |")
    lines.extend(
        [
            "",
            "## Entries",
            "",
            "| ID | Graphics Pointer | Asset | Compressed Bytes | Script Records | Sector Count | Direct `.fts` Rows | Max Source End | Status |",
            "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for entry in contract["entries"]:
        asset = entry["graphics_asset"]
        script = entry["script"]
        dependency = entry["tileset_dependency"]
        fts = entry["fts_animation_settings_context"]
        status = "placeholder-empty" if entry["placeholder_empty_script_match"] else "active"
        if entry["graphics_pointer_match_status"] != "matches_map_data_tile_animation_gfx_asset":
            status = "pointer-mismatch"
        lines.append(
            f"| {entry['animation_id']} | `{entry['graphics_pointer_cpu']}` | `{asset['title']}` | "
            f"{asset['bytes']} | {script['record_count']} | {dependency['sector_count']} | "
            f"{fts.get('row_count', 0)} | `0x{script['max_source_end_offset_exclusive']:04X}` | `{status}` |"
        )
    lines.extend(
        [
            "",
            "## Upload Script Records",
            "",
            "| ID | Record | Frames | Delay | Transfer Bytes | Source Offset | Source End | VRAM Destination |",
            "| ---: | ---: | ---: | ---: | ---: | --- | --- | --- |",
        ]
    )
    for entry in contract["entries"]:
        for record in entry["script"]["records"]:
            lines.append(
                f"| {entry['animation_id']} | {record['record_index']} | "
                f"{record['frame_count_limit']} | {record['reload_delay']} | "
                f"{record['transfer_size_bytes']} | `{record['source_base_offset']}` | "
                f"`{record['source_end_offset_exclusive']}` | `{record['vram_destination']}` |"
            )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "This contract resolves the active runtime graphics/script table pair. The",
            "290-character `.fts` animation/settings rows are still a separate export",
            "layer: they are structurally related to map tileset animation/settings work,",
            "but their row counts do not equal these C0 upload-script record counts.",
            "",
            "The older community ROM map labels around `0x2F13CB..0x2F153E` are not used",
            "as the current runtime anchor here; local C0 code and the sprite-frame",
            "contract place those bytes inside the sprite grouping pointer/data region.",
            "",
            "## Machine-Readable Data",
            "",
            "`notes/map-tile-animation-runtime-contract.json` records one row per",
            "animation ID with matched graphics asset metadata, decoded upload-script",
            "fields, tileset/sector context, and direct `.fts` row context.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    contract = build_contract(args)
    json_out = Path(args.json_out)
    markdown_out = Path(args.markdown_out)
    json_out.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(contract, markdown_out)
    print(f"Wrote {rel(json_out)} and {rel(markdown_out)}")


if __name__ == "__main__":
    main()
