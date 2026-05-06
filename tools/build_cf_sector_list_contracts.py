from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CF_HELPER = ROOT / "src" / "cf" / "bank_cf_helpers_asar.asm"
DEFAULT_D0_HELPER = ROOT / "src" / "d0" / "bank_d0_helpers_asar.asm"
DEFAULT_JSON_OUT = ROOT / "notes" / "cf-sector-list-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "cf-sector-list-contracts.md"

SCHEMA = "earthbound-decomp.cf-sector-list-contracts.v1"
SECTOR_COUNT = 40 * 32
SECTOR_ROWS = 32
DOOR_CONFIG_START = 0x264F
DOOR_CONFIG_END = 0x58EF
SPRITE_POINTER_START = 0x61E7
SPRITE_TABLE_START = 0x6BE7
SPRITE_TABLE_END = 0x8985
NPC_CONFIG_ROWS = 1584


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build CF/D0 counted sector-list contracts from preserved source-scaffold bytes."
    )
    parser.add_argument("--cf-helper", default=str(DEFAULT_CF_HELPER))
    parser.add_argument("--d0-helper", default=str(DEFAULT_D0_HELPER))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def parse_db_line(line: str) -> list[int]:
    match = re.match(r"\s*db\s+(.+)", line)
    if match is None:
        return []
    values: list[int] = []
    for item in match.group(1).split(","):
        item = item.strip()
        if not item:
            continue
        if not re.fullmatch(r"\$[0-9A-Fa-f]{2}", item):
            raise ValueError(f"Unsupported db token {item!r} in line {line!r}")
        values.append(int(item[1:], 16))
    return values


def source_bytes(path: Path, source_name: str) -> bytes:
    active = False
    values: list[int] = []
    source_marker = f"; Source: {source_name}"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("; Source: "):
            if active:
                break
            active = line.strip() == source_marker
            continue
        if active:
            values.extend(parse_db_line(line))
    if not values:
        raise ValueError(f"No db bytes found for {source_name} in {rel(path)}")
    return bytes(values)


def word(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def sector_coords(linear_index: int) -> dict[str, int]:
    return {"x": linear_index // SECTOR_ROWS, "y": linear_index % SECTOR_ROWS}


def cpu(bank: int, low_word: int) -> str:
    return f"{bank:02X}:{low_word:04X}"


def parse_door_lists(
    data: bytes, pointer_rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    lists: list[dict[str, Any]] = []
    logical_entries: list[dict[str, Any]] = []
    physical_entries: list[dict[str, Any]] = []
    sorted_starts = sorted(row["pointer_low_word"] for row in pointer_rows)
    next_start_by_start = {
        start: sorted_starts[index + 1] if index + 1 < len(sorted_starts) else DOOR_CONFIG_END
        for index, start in enumerate(sorted_starts)
    }
    overlaps: list[dict[str, Any]] = []

    for row in pointer_rows:
        sector_index = row["sector_index"]
        list_low_word = row["pointer_low_word"]
        cursor = list_low_word - DOOR_CONFIG_START
        count = word(data, cursor)
        raw_end = list_low_word + 2 + count * 5
        next_start = next_start_by_start[list_low_word]
        effective_end = min(raw_end, next_start)
        effective_count = max(0, (effective_end - list_low_word - 2) // 5)
        if raw_end > next_start:
            overlaps.append(
                {
                    "sector_index": sector_index,
                    "sector": row["sector"],
                    "address": cpu(0xCF, list_low_word),
                    "raw_count": count,
                    "source_order_physical_count": effective_count,
                    "raw_end": cpu(0xCF, raw_end),
                    "next_pointer_start": cpu(0xCF, next_start),
                    "overlap_bytes": raw_end - next_start,
                }
            )
        list_logical_entries: list[dict[str, Any]] = []
        list_physical_entries: list[dict[str, Any]] = []
        for entry_in_list in range(count):
            entry_offset = cursor + 2 + entry_in_list * 5
            entry = {
                "entry_index": len(logical_entries),
                "entry_in_sector": entry_in_list,
                "address": cpu(0xCF, DOOR_CONFIG_START + entry_offset),
                "sector_index": sector_index,
                "sector": sector_coords(sector_index),
                "sector_local_x": data[entry_offset],
                "sector_local_y": data[entry_offset + 1],
                "movement_trigger_type": data[entry_offset + 2],
                "trigger_payload_word": word(data, entry_offset + 3),
            }
            logical_entries.append(entry)
            list_logical_entries.append(entry)
            if entry_in_list < effective_count:
                physical_entries.append(entry | {"physical_entry_index": len(physical_entries)})
                list_physical_entries.append(entry)
        lists.append(
            {
                "sector_index": sector_index,
                "sector": sector_coords(sector_index),
                "address": cpu(0xCF, list_low_word),
                "raw_count": count,
                "source_order_physical_count": effective_count,
                "raw_byte_length": 2 + count * 5,
                "source_order_physical_byte_length": 2 + effective_count * 5,
                "first_entry_index": list_logical_entries[0]["entry_index"] if list_logical_entries else None,
                "first_physical_entry_index": (
                    list_physical_entries[0]["entry_index"] if list_physical_entries else None
                ),
            }
        )
    max_raw_end = max(
        row["pointer_low_word"] + 2 + word(data, row["pointer_low_word"] - DOOR_CONFIG_START) * 5
        for row in pointer_rows
    )
    if max_raw_end != DOOR_CONFIG_END:
        raise ValueError(f"Door sector-list scan ended at {max_raw_end:#x}, expected {DOOR_CONFIG_END:#x}")
    return lists, logical_entries, physical_entries, overlaps


def parse_d0_door_pointers(data: bytes) -> list[dict[str, Any]]:
    if len(data) != SECTOR_COUNT * 4:
        raise ValueError(f"Unexpected D0 door pointer byte count: {len(data)}")
    rows: list[dict[str, Any]] = []
    for sector_index in range(SECTOR_COUNT):
        offset = sector_index * 4
        low_word = word(data, offset)
        rows.append(
            {
                "sector_index": sector_index,
                "sector": sector_coords(sector_index),
                "pointer_low_word": low_word,
                "pointer_bank": data[offset + 2],
                "reserved": data[offset + 3],
                "target": cpu(data[offset + 2], low_word),
            }
        )
    return rows


def parse_sprite_pointers(data: bytes) -> list[dict[str, Any]]:
    if len(data) != SECTOR_COUNT * 2:
        raise ValueError(f"Unexpected sprite pointer byte count: {len(data)}")
    rows: list[dict[str, Any]] = []
    for sector_index in range(SECTOR_COUNT):
        offset = sector_index * 2
        low_word = word(data, offset)
        rows.append(
            {
                "sector_index": sector_index,
                "sector": sector_coords(sector_index),
                "sprite_placement_list_offset": low_word,
                "target": None if low_word == 0 else cpu(0xCF, low_word),
            }
        )
    return rows


def parse_sprite_lists(data: bytes) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    lists: list[dict[str, Any]] = []
    entries: list[dict[str, Any]] = []
    cursor = 0
    while cursor < len(data):
        list_low_word = SPRITE_TABLE_START + cursor
        count = word(data, cursor)
        cursor += 2
        list_entries: list[dict[str, Any]] = []
        for entry_in_list in range(count):
            entry_offset = cursor + entry_in_list * 4
            entry = {
                "entry_index": len(entries),
                "entry_in_sector": entry_in_list,
                "address": cpu(0xCF, SPRITE_TABLE_START + entry_offset),
                "npc_config_id": word(data, entry_offset),
                "sector_local_y": data[entry_offset + 2],
                "sector_local_x": data[entry_offset + 3],
            }
            entries.append(entry)
            list_entries.append(entry)
        cursor += count * 4
        lists.append(
            {
                "list_index": len(lists),
                "address": cpu(0xCF, list_low_word),
                "count": count,
                "byte_length": 2 + count * 4,
                "first_entry_index": list_entries[0]["entry_index"] if list_entries else None,
            }
        )
    if cursor != len(data):
        raise ValueError(f"Sprite placement parse ended at {cursor:#x}, expected {len(data):#x}")
    return lists, entries


def counter_dict(counter: Counter[int]) -> dict[str, int]:
    return {f"0x{key:02X}": counter[key] for key in sorted(counter)}


def decimal_counter_dict(counter: Counter[int]) -> dict[str, int]:
    return {str(key): counter[key] for key in sorted(counter)}


def sample_rows(rows: list[dict[str, Any]], count: int = 5) -> list[dict[str, Any]]:
    return rows[:count]


def build_contract(cf_helper: Path, d0_helper: Path) -> dict[str, Any]:
    door_config = source_bytes(cf_helper, "src/cf/table_door_config_table.asm")
    sprite_pointers_raw = source_bytes(cf_helper, "src/cf/table_sprite_placement_pointer_table.asm")
    sprite_table = source_bytes(cf_helper, "src/cf/table_sprite_placement_table.asm")
    d0_door_pointers_raw = source_bytes(d0_helper, "src/d0/table_door_pointer_table.asm")

    expected_door_bytes = DOOR_CONFIG_END - DOOR_CONFIG_START
    expected_sprite_bytes = SPRITE_TABLE_END - SPRITE_TABLE_START
    if len(door_config) != expected_door_bytes:
        raise ValueError(f"Door config byte count {len(door_config)} != {expected_door_bytes}")
    if len(sprite_table) != expected_sprite_bytes:
        raise ValueError(f"Sprite placement byte count {len(sprite_table)} != {expected_sprite_bytes}")

    d0_door_pointers = parse_d0_door_pointers(d0_door_pointers_raw)
    door_lists, door_logical_entries, door_physical_entries, door_overlaps = parse_door_lists(
        door_config, d0_door_pointers
    )
    sprite_pointers = parse_sprite_pointers(sprite_pointers_raw)
    sprite_lists, sprite_entries = parse_sprite_lists(sprite_table)

    door_pointer_mismatches = [
        row["sector_index"]
        for row in d0_door_pointers
        if not (DOOR_CONFIG_START <= row["pointer_low_word"] < DOOR_CONFIG_END)
        or row["pointer_bank"] != 0xCF
        or row["reserved"] != 0
    ]

    nonzero_sprite_pointers = [row for row in sprite_pointers if row["sprite_placement_list_offset"] != 0]
    sprite_pointer_targets = [row["sprite_placement_list_offset"] for row in nonzero_sprite_pointers]
    sprite_list_starts = [int(row["address"].split(":")[1], 16) for row in sprite_lists]
    sprite_pointer_mismatches = [
        index
        for index, (pointer, parsed_start) in enumerate(zip(sprite_pointer_targets, sprite_list_starts, strict=True))
        if pointer != parsed_start
    ]

    door_logical_type_counter = Counter(entry["movement_trigger_type"] for entry in door_logical_entries)
    door_physical_type_counter = Counter(entry["movement_trigger_type"] for entry in door_physical_entries)
    door_raw_count_counter = Counter(row["raw_count"] for row in door_lists)
    door_physical_count_counter = Counter(row["source_order_physical_count"] for row in door_lists)
    door_payload_by_type: dict[str, dict[str, int]] = {}
    for trigger_type in sorted(door_physical_type_counter):
        payloads = [
            entry["trigger_payload_word"]
            for entry in door_physical_entries
            if entry["movement_trigger_type"] == trigger_type
        ]
        door_payload_by_type[f"0x{trigger_type:02X}"] = {
            "count": len(payloads),
            "min": min(payloads),
            "max": max(payloads),
            "in_cf_door_data_span": sum(1 for value in payloads if 0 <= value < DOOR_CONFIG_START),
            "sentinel_8000": sum(1 for value in payloads if value == 0x8000),
        }

    sprite_npc_ids = [entry["npc_config_id"] for entry in sprite_entries]
    sprite_xs = [entry["sector_local_x"] for entry in sprite_entries]
    sprite_ys = [entry["sector_local_y"] for entry in sprite_entries]
    sprite_list_count_counter = Counter(row["count"] for row in sprite_lists)

    validation = {
        "door_config_byte_count_ok": len(door_config) == expected_door_bytes,
        "door_sector_list_count_ok": len(door_lists) == SECTOR_COUNT,
        "door_entry_width": 5,
        "door_logical_pointer_entry_count": len(door_logical_entries),
        "door_source_order_physical_entry_count": len(door_physical_entries),
        "door_pointer_overlap_count": len(door_overlaps),
        "door_pointer_overlap_bytes": sum(row["overlap_bytes"] for row in door_overlaps),
        "d0_door_pointer_rows_ok": len(d0_door_pointers) == SECTOR_COUNT,
        "d0_door_pointer_match_count": SECTOR_COUNT - len(door_pointer_mismatches),
        "d0_door_pointer_mismatch_count": len(door_pointer_mismatches),
        "sprite_pointer_rows_ok": len(sprite_pointers) == SECTOR_COUNT,
        "sprite_nonzero_pointer_count": len(nonzero_sprite_pointers),
        "sprite_list_count": len(sprite_lists),
        "sprite_pointer_match_count": len(sprite_list_starts) - len(sprite_pointer_mismatches),
        "sprite_pointer_mismatch_count": len(sprite_pointer_mismatches),
        "sprite_entry_width": 4,
        "sprite_entry_count": len(sprite_entries),
        "sprite_npc_ids_within_npc_config_table": all(0 <= value < NPC_CONFIG_ROWS for value in sprite_npc_ids),
    }

    if door_pointer_mismatches:
        raise ValueError(f"D0 door pointer mismatches: {door_pointer_mismatches[:10]}")
    if sprite_pointer_mismatches:
        raise ValueError(f"Sprite pointer mismatches: {sprite_pointer_mismatches[:10]}")
    if len(nonzero_sprite_pointers) != len(sprite_lists):
        raise ValueError("Sprite pointer/list count mismatch")
    if not validation["sprite_npc_ids_within_npc_config_table"]:
        raise ValueError("Sprite placement NPC ids exceed NPC_CONFIG_TABLE")

    return {
        "schema": SCHEMA,
        "title": "CF Sector List Contracts",
        "generator": "tools/build_cf_sector_list_contracts.py",
        "source_policy": (
            "Derived from byte-equivalent CF and D0 source scaffolds. This records "
            "list boundaries, pointer ownership, consumer-backed field names, overlap "
            "metadata, and decoded row values only; it does not commit raw table bytes."
        ),
        "sources": {
            "cf_helper": rel(cf_helper),
            "d0_helper": rel(d0_helper),
            "cf_table_splits": "notes/cf-table-splits.md",
            "d0_table_splits": "notes/d0-table-splits.md",
        },
        "sector_grid": {"columns": 40, "rows": 32, "order": "x-major: sector_index = x * 32 + y"},
        "door_config": {
            "span": f"CF:{DOOR_CONFIG_START:04X}..CF:{DOOR_CONFIG_END - 1:04X}",
            "list_count": len(door_lists),
            "non_empty_list_count": sum(1 for row in door_lists if row["source_order_physical_count"]),
            "logical_pointer_entry_count": len(door_logical_entries),
            "source_order_physical_entry_count": len(door_physical_entries),
            "max_raw_entries_per_sector": max(row["raw_count"] for row in door_lists),
            "max_source_order_physical_entries_per_sector": max(
                row["source_order_physical_count"] for row in door_lists
            ),
            "raw_count_histogram": decimal_counter_dict(door_raw_count_counter),
            "source_order_physical_count_histogram": decimal_counter_dict(door_physical_count_counter),
            "trigger_type_counts": counter_dict(door_physical_type_counter),
            "logical_pointer_trigger_type_counts": counter_dict(door_logical_type_counter),
            "payload_stats_by_trigger_type": door_payload_by_type,
            "overlap_count": len(door_overlaps),
            "overlap_bytes": sum(row["overlap_bytes"] for row in door_overlaps),
            "sector_lists": door_lists,
            "logical_pointer_entries": door_logical_entries,
            "source_order_physical_entries": door_physical_entries,
            "pointer_overlaps": door_overlaps,
            "sample_overlaps": sample_rows(door_overlaps),
            "sample_lists": sample_rows([row for row in door_lists if row["source_order_physical_count"]]),
            "sample_entries": sample_rows(door_physical_entries),
        },
        "d0_door_pointer_table": {
            "span": "D0:0000..D0:13FF",
            "row_count": len(d0_door_pointers),
            "target_bank_counts": counter_dict(Counter(row["pointer_bank"] for row in d0_door_pointers)),
            "reserved_byte_counts": counter_dict(Counter(row["reserved"] for row in d0_door_pointers)),
            "rows": d0_door_pointers,
        },
        "sprite_placement": {
            "pointer_span": f"CF:{SPRITE_POINTER_START:04X}..CF:{SPRITE_TABLE_START - 1:04X}",
            "table_span": f"CF:{SPRITE_TABLE_START:04X}..CF:{SPRITE_TABLE_END - 1:04X}",
            "pointer_row_count": len(sprite_pointers),
            "nonzero_pointer_count": len(nonzero_sprite_pointers),
            "zero_pointer_count": len(sprite_pointers) - len(nonzero_sprite_pointers),
            "list_count": len(sprite_lists),
            "entry_count": len(sprite_entries),
            "max_entries_per_sector": max(row["count"] for row in sprite_lists),
            "entry_count_histogram": decimal_counter_dict(sprite_list_count_counter),
            "npc_config_id_range": [min(sprite_npc_ids), max(sprite_npc_ids)],
            "sector_local_x_range": [min(sprite_xs), max(sprite_xs)],
            "sector_local_y_range": [min(sprite_ys), max(sprite_ys)],
            "pointer_rows": sprite_pointers,
            "sector_lists": sprite_lists,
            "entries": sprite_entries,
            "sample_pointer_rows": sample_rows(nonzero_sprite_pointers),
            "sample_lists": sample_rows(sprite_lists),
            "sample_entries": sample_rows(sprite_entries),
        },
        "validation": validation,
    }


def markdown(contract: dict[str, Any]) -> str:
    door = contract["door_config"]
    sprite = contract["sprite_placement"]
    validation = contract["validation"]
    lines = [
        "# CF Sector List Contracts",
        "",
        f"Generated by `tools/build_cf_sector_list_contracts.py` from `{contract['sources']['cf_helper']}` and `{contract['sources']['d0_helper']}`.",
        "",
        "## Main result",
        "",
        "The CF counted sector-list families now have reproducible subrecord boundaries:",
        "",
        f"- `DOOR_CONFIG_TABLE` covers `{door['span']}` as `{door['list_count']}` D0-pointer-addressed counted sector lists.",
        f"- In source-order physical row view, those lists contain `{door['source_order_physical_entry_count']}` five-byte movement-trigger rows across `{door['non_empty_list_count']}` non-empty sectors, matching the existing `map_doors.yml` bundle count.",
        f"- In raw pointer-consumer view, the same starts expose `{door['logical_pointer_entry_count']}` candidate rows because `{door['overlap_count']}` pointer starts overlap the previous counted-list tail by `{door['overlap_bytes']}` total bytes.",
        f"- `D0_DOOR_POINTER_TABLE` covers `D0:0000..D0:13FF`; all `{validation['d0_door_pointer_match_count']}` long pointers target `CF:264F..CF:58EE` with bank byte `CF` and zero reserved byte.",
        f"- `SPRITE_PLACEMENT_POINTER_TABLE` covers `{sprite['pointer_span']}` with `{sprite['nonzero_pointer_count']}` nonzero pointers and `{sprite['zero_pointer_count']}` empty-sector sentinels.",
        f"- `SPRITE_PLACEMENT_TABLE` covers `{sprite['table_span']}` as `{sprite['list_count']}` counted lists with `{sprite['entry_count']}` four-byte placement rows.",
        f"- Full decoded pointer rows, sector-list rows, overlap rows, and entry rows are checked in at `notes/cf-sector-list-contracts.json`.",
        "",
        "## Record shapes",
        "",
        "| Contract | Offset | Field | Size | Evidence boundary |",
        "| --- | ---: | --- | ---: | --- |",
        "| `door_sector_list` | `+0x00` | `count` | 2 | counted-list parser reaches `CF:58EF` exactly |",
        "| `door_trigger_entry` | `+0x00` | `sector_local_x` | 1 | movement-trigger lookup compares low 5-bit sector-local coordinates |",
        "| `door_trigger_entry` | `+0x01` | `sector_local_y` | 1 | movement-trigger lookup compares low 5-bit sector-local coordinates |",
        "| `door_trigger_entry` | `+0x02` | `movement_trigger_type` | 1 | C0 dispatch branches trigger types into the helper family |",
        "| `door_trigger_entry` | `+0x03` | `trigger_payload_word` | 2 | helper-specific side data; type `0`/`2` resolve door-destination family rows, while other types use different payload meanings |",
        "| `sprite_placement_sector_list` | `+0x00` | `count` | 2 | nonzero sector pointers enumerate exactly 627 counted lists |",
        "| `sprite_placement_entry` | `+0x00` | `npc_config_id` | 2 | CoilSnake `map_sprites.yml` NPC-id probe maps to the first original placement row |",
        "| `sprite_placement_entry` | `+0x02` | `sector_local_y` | 1 | CoilSnake clustered Y probe maps to the first original placement row |",
        "| `sprite_placement_entry` | `+0x03` | `sector_local_x` | 1 | CoilSnake clustered X probe maps to the first original placement row |",
        "",
        "## Door trigger distribution",
        "",
        "This table uses the source-order physical row view. The raw pointer-consumer view is retained in the JSON because overlapping starts can expose suffix rows differently.",
        "",
        "| Trigger type | Rows | Payload min | Payload max | Payloads in `CF:0000..CF:264E` | `0x8000` sentinels |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for trigger_type, stats in door["payload_stats_by_trigger_type"].items():
        lines.append(
            f"| `{trigger_type}` | {stats['count']} | `0x{stats['min']:04X}` | `0x{stats['max']:04X}` | {stats['in_cf_door_data_span']} | {stats['sentinel_8000']} |"
        )

    lines.extend(
        [
            "",
            "## Sprite placement validation",
            "",
            "| Check | Result |",
            "| --- | ---: |",
            f"| pointer rows | {sprite['pointer_row_count']} |",
            f"| nonzero pointers | {sprite['nonzero_pointer_count']} |",
            f"| parsed lists | {sprite['list_count']} |",
            f"| parsed placement rows | {sprite['entry_count']} |",
            f"| NPC config id range | `0x{sprite['npc_config_id_range'][0]:04X}..0x{sprite['npc_config_id_range'][1]:04X}` |",
            f"| sector-local X range | `0x{sprite['sector_local_x_range'][0]:02X}..0x{sprite['sector_local_x_range'][1]:02X}` |",
            f"| sector-local Y range | `0x{sprite['sector_local_y_range'][0]:02X}..0x{sprite['sector_local_y_range'][1]:02X}` |",
            f"| NPC ids fit `NPC_CONFIG_TABLE[0..1583]` | `{validation['sprite_npc_ids_within_npc_config_table']}` |",
            "",
            "## Source-Emission Readiness",
            "",
            "- `notes/cf-sector-list-contracts.json` now carries complete decoded rows for `D0_DOOR_POINTER_TABLE`, `CF_DOOR_CONFIG_TABLE`, `SPRITE_PLACEMENT_POINTER_TABLE`, and `SPRITE_PLACEMENT_TABLE`.",
            "- Door rows retain both source-order physical entries and raw pointer-consumer entries because the 19 overlapping starts are real consumer-visible pointer targets.",
            "- Sprite placement rows retain sector-list ownership plus `NPC_CONFIG_TABLE` ids so generated source can emit stable sector-local rows without re-parsing the scaffold.",
            "",
            "## Evidence",
            "",
            "- `notes/cf-table-splits.md` fixes the CF source-order spans and counted-list byte boundaries.",
            "- `notes/d0-table-splits.md` fixes `D0:0000..D0:13FF` as the 40x32 long-pointer grid into CF door sector lists.",
            "- `notes/movement-trigger-lookup-7477.md` and `notes/movement-trigger-helper-bodies.md` back the door-trigger coordinate/type/payload naming boundary.",
            "- `notes/coilsnake-field-join-report.md` backs the sprite placement `npc_config_id`, `sector_local_y`, and `sector_local_x` names through the clustered `map_sprites.yml` probes.",
            "",
            "## Remaining frontier",
            "",
            "- `DOOR_DATA` is still a packed payload family. The sector-list row contract should treat `trigger_payload_word` as type-specific until each trigger helper is joined to a payload variant.",
            "- `OVERWORLD_EVENT_MUSIC_TABLE` remains a separate variable-length row family.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    cf_helper = Path(args.cf_helper)
    d0_helper = Path(args.d0_helper)
    contract = build_contract(cf_helper, d0_helper)
    json_out = Path(args.json_out)
    markdown_out = Path(args.markdown_out)
    json_out.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    markdown_out.write_text(markdown(contract), encoding="utf-8")
    print(f"Wrote {rel(json_out)}")
    print(f"Wrote {rel(markdown_out)}")


if __name__ == "__main__":
    main()
