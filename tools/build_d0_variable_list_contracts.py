from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / "src" / "d0" / "bank_d0_helpers_asar.asm"
DEFAULT_JSON_OUT = ROOT / "notes" / "d0-variable-list-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "d0-variable-list-contracts.md"
SCHEMA = "earthbound-decomp.d0-variable-list-contracts.v1"
PLACEMENT_POINTER_ROWS = 203
PLACEMENT_TABLE_START = 0xBBAC
PLACEMENT_TABLE_END = 0xC60D
BATTLE_ENTRY_ROWS = 484
BATTLE_POINTER_TABLE_START = 0xC60D
BATTLE_GROUP_TABLE_START = 0xD52D
BATTLE_GROUP_TABLE_END = 0xDFB4


def parse_db_bytes(text: str) -> list[int]:
    values: list[int] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("db "):
            continue
        values.extend(int(match[1:], 16) for match in re.findall(r"\$[0-9A-Fa-f]{2}", line))
    return values


def source_slice(text: str, source_name: str) -> str:
    marker = f"Source: src/d0/{source_name}"
    start = text.index(marker)
    next_source = text.find("; Source: src/d0/", start + len(marker))
    if next_source == -1:
        next_source = len(text)
    return text[start:next_source]


def word(data: list[int], offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def long_low_word(data: list[int], offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def cpu(bank: str, address: int) -> str:
    return f"{bank}:{address:04X}"


def counter_dict(counter: Counter[int]) -> dict[str, int]:
    return {str(key): counter[key] for key in sorted(counter)}


def hex_byte_counter_dict(counter: Counter[int]) -> dict[str, int]:
    return {f"0x{key:02X}": counter[key] for key in sorted(counter)}


def hex_word_counter_dict(counter: Counter[int]) -> dict[str, int]:
    return {f"0x{key:04X}": counter[key] for key in sorted(counter)}


def cpu_low_word(address: str) -> int:
    return int(address.split(":")[1], 16)


def find_unpointed_ranges(rows: list[dict[str, Any]], start: int, end: int) -> list[dict[str, Any]]:
    ranges = []
    cursor = start
    for row in sorted(rows, key=lambda item: cpu_low_word(item["address"])):
        row_start = cpu_low_word(row["address"])
        row_end = cpu_low_word(row["end_exclusive"])
        if row_start > cursor:
            ranges.append(
                {
                    "range": f"{cpu('D0', cursor)}..{cpu('D0', row_start)}",
                    "bytes": row_start - cursor,
                    "reason": "no BTL_ENTRY_PTR_TABLE row targets this byte range",
                }
            )
        cursor = max(cursor, row_end)
    if cursor < end:
        ranges.append(
            {
                "range": f"{cpu('D0', cursor)}..{cpu('D0', end)}",
                "bytes": end - cursor,
                "reason": "no BTL_ENTRY_PTR_TABLE row targets this byte range",
            }
        )
    return ranges


def format_histogram(histogram: dict[str, int]) -> str:
    return ", ".join(f"`{key}`: {value}" for key, value in histogram.items()) or "-"


def build_contract(source_path: Path) -> dict[str, Any]:
    text = source_path.read_text(encoding="utf-8")
    placement_ptr = parse_db_bytes(source_slice(text, "table_enemy_placement_groups_ptr_table.asm"))
    placement_data = parse_db_bytes(source_slice(text, "table_enemy_placement_groups_table.asm"))
    battle_entry_ptr = parse_db_bytes(source_slice(text, "table_btl_entry_ptr_table.asm"))
    battle_data = parse_db_bytes(source_slice(text, "table_enemy_battle_groups_table.asm"))

    placement_pointers = [long_low_word(placement_ptr, index * 4) for index in range(PLACEMENT_POINTER_ROWS)]
    placement_unique = sorted(set(placement_pointers))
    placement_lists = []
    placement_entries = []
    for list_index, start in enumerate(placement_unique):
        end = placement_unique[list_index + 1] if list_index + 1 < len(placement_unique) else PLACEMENT_TABLE_END
        length = end - start
        if length < 4 or (length - 4) % 3:
            raise ValueError(f"bad enemy placement list length at {start:04X}: {length}")
        offset = start - PLACEMENT_TABLE_START
        entry_count = (length - 4) // 3
        entries = []
        total_selection_weight = 0
        for entry_in_list in range(entry_count):
            entry_offset = offset + 4 + entry_in_list * 3
            selection_weight = placement_data[entry_offset]
            total_selection_weight += selection_weight
            entry = {
                "entry_index": len(placement_entries),
                "entry_in_list": entry_in_list,
                "address": cpu("D0", PLACEMENT_TABLE_START + entry_offset),
                "selection_weight": selection_weight,
                "battle_group_id": word(placement_data, entry_offset + 1),
                "battle_entry_pointer_row": word(placement_data, entry_offset + 1),
            }
            placement_entries.append(entry | {"list_id": list_index, "list_address": cpu("D0", start)})
            entries.append(entry)
        placement_lists.append(
            {
                "id": list_index,
                "address": cpu("D0", start),
                "end_exclusive": cpu("D0", end),
                "bytes": length,
                "event_flag_gate": word(placement_data, offset),
                "primary_spawn_chance": placement_data[offset + 2],
                "flagged_spawn_chance": placement_data[offset + 3],
                "weighted_entries": entry_count,
                "total_selection_weight": total_selection_weight,
                "pointer_rows": [index for index, pointer in enumerate(placement_pointers) if pointer == start],
                "entries": entries,
            }
        )

    battle_pointers: list[int] = []
    battle_pointer_rows: list[int | None] = []
    battle_entry_rows = []
    battle_pointer_banks = []
    battle_pointer_padding_bytes = []
    for index in range(BATTLE_ENTRY_ROWS):
        offset = index * 8
        target = long_low_word(battle_entry_ptr, offset)
        bank = battle_entry_ptr[offset + 2]
        extra = battle_entry_ptr[offset + 3]
        if target or bank or extra:
            battle_pointers.append(target)
            battle_pointer_rows.append(target)
        else:
            battle_pointer_rows.append(None)
        battle_pointer_banks.append(bank)
        battle_pointer_padding_bytes.append(extra)
        battle_entry_rows.append(
            {
                "id": index,
                "enemy_list_pointer": cpu(f"{bank:02X}", target) if target or bank else None,
                "run_away_flag": word(battle_entry_ptr, offset + 4),
                "run_away_flag_state": battle_entry_ptr[offset + 6],
                "presentation_sprite_style": battle_entry_ptr[offset + 7],
            }
        )

    battle_lists = []
    battle_group_entries = []
    for list_index, start in enumerate(sorted(set(battle_pointers))):
        entry_count = 0
        offset = start - BATTLE_GROUP_TABLE_START
        if offset < 0 or offset >= len(battle_data):
            raise ValueError(f"enemy battle group pointer outside D0:D52D data span: {start:04X}")
        while offset + entry_count * 3 < len(battle_data) and battle_data[offset + entry_count * 3] != 0xFF:
            entry_count += 1
        terminator_offset = offset + entry_count * 3
        if terminator_offset >= len(battle_data):
            raise ValueError(f"enemy battle group at {start:04X} lacks FF terminator")
        length = entry_count * 3 + 1
        end = start + length
        entries = []
        for entry_in_list in range(entry_count):
            entry_offset = offset + entry_in_list * 3
            entry = {
                "entry_index": len(battle_group_entries),
                "entry_in_list": entry_in_list,
                "address": cpu("D0", BATTLE_GROUP_TABLE_START + entry_offset),
                "repeat_count": battle_data[entry_offset],
                "enemy_id": word(battle_data, entry_offset + 1),
            }
            battle_group_entries.append(entry | {"list_id": list_index, "list_address": cpu("D0", start)})
            entries.append(entry)
        enemy_ids = [entry["enemy_id"] for entry in entries]
        counts = [entry["repeat_count"] for entry in entries]
        battle_lists.append(
            {
                "id": list_index,
                "address": cpu("D0", start),
                "end_exclusive": cpu("D0", end),
                "bytes": length,
                "enemy_entries": entry_count,
                "terminator": cpu("D0", end - 1),
                "total_enemy_count": sum(counts),
                "unique_enemy_ids": sorted(set(enemy_ids)),
                "pointer_rows": [index for index, pointer in enumerate(battle_pointer_rows) if pointer == start],
                "entries": entries,
            }
        )

    placement_entry_counts = Counter(item["weighted_entries"] for item in placement_lists)
    placement_pointer_fan_in_counts = Counter(len(item["pointer_rows"]) for item in placement_lists)
    placement_weight_counts = Counter(entry["selection_weight"] for entry in placement_entries)
    placement_total_weight_counts = Counter(item["total_selection_weight"] for item in placement_lists)
    battle_entry_counts = Counter(item["enemy_entries"] for item in battle_lists)
    battle_pointer_fan_in_counts = Counter(len(item["pointer_rows"]) for item in battle_lists)
    battle_repeat_counts = Counter(entry["repeat_count"] for entry in battle_group_entries)
    battle_total_enemy_counts = Counter(item["total_enemy_count"] for item in battle_lists)
    battle_byte_length_counts = Counter(item["bytes"] for item in battle_lists)
    battle_group_unpointed_ranges = find_unpointed_ranges(
        battle_lists,
        BATTLE_GROUP_TABLE_START,
        BATTLE_GROUP_TABLE_END,
    )
    pointed_battle_group_bytes = sum(item["bytes"] for item in battle_lists)
    return {
        "schema": SCHEMA,
        "title": "D0 Variable-List Contracts",
        "generator": "tools/build_d0_variable_list_contracts.py",
        "source_policy": (
            "Derived from the byte-equivalent D0 source scaffold. This records "
            "list boundaries, consumer-backed field names, pointer ownership, "
            "and decoded entry values only; it does not commit raw table bytes."
        ),
        "source": str(source_path.relative_to(ROOT)),
        "spans": {
            "enemy_placement_groups": {
                "range": f"{cpu('D0', PLACEMENT_TABLE_START)}..{cpu('D0', PLACEMENT_TABLE_END)}",
                "bytes": PLACEMENT_TABLE_END - PLACEMENT_TABLE_START,
            },
            "enemy_battle_groups": {
                "range": f"{cpu('D0', BATTLE_GROUP_TABLE_START)}..{cpu('D0', BATTLE_GROUP_TABLE_END)}",
                "bytes": BATTLE_GROUP_TABLE_END - BATTLE_GROUP_TABLE_START,
            },
        },
        "record_shapes": {
            "enemy_placement_group_list": [
                {"offset": 0, "field": "event_flag_gate", "size": 2, "consumer": "C0:2668 tests this through C2:1628"},
                {"offset": 2, "field": "primary_spawn_chance", "size": 1, "consumer": "C0:2668 seeds $4A70 from this byte"},
                {"offset": 3, "field": "flagged_spawn_chance", "size": 1, "consumer": "C0:2668 can replace $4A70 with this byte when the gate flag is set"},
            ],
            "enemy_placement_weighted_entry": [
                {"offset": 0, "field": "selection_weight", "size": 1, "consumer": "C0:2668 adds this byte to the running selection threshold"},
                {"offset": 1, "field": "battle_group_id", "size": 2, "consumer": "C0:2668 stores this as the selected BTL_ENTRY_PTR_TABLE row id in $4A72"},
            ],
            "enemy_battle_group_entry": [
                {"offset": 0, "field": "repeat_count_or_ff_terminator", "size": 1, "consumer": "C2:2F38 repeats the enemy id this many times; C2:EEE7 treats FF as terminator"},
                {"offset": 1, "field": "enemy_id", "size": 2, "consumer": "C2:2F38 stages this id into $9F8C; C2:EEE7 maps it through D5 enemy config"},
            ],
            "battle_entry_pointer_row": [
                {"offset": 0, "field": "enemy_list_pointer", "size": 4, "consumer": "ebsrc `battle_entry_ptr_entry` field; every non-null row targets a D0 enemy battle-group slice"},
                {"offset": 4, "field": "run_away_flag", "size": 2, "consumer": "ebsrc `battle_entry_ptr_entry` field; this pass keeps numeric values"},
                {"offset": 6, "field": "run_away_flag_state", "size": 1, "consumer": "ebsrc `battle_entry_ptr_entry` field; this pass keeps numeric values"},
                {"offset": 7, "field": "presentation_sprite_style", "size": 1, "consumer": "C2 battle presentation paths pass this byte as Y to C2:D121 LoadPresentationSpriteResource"},
            ],
        },
        "summary": {
            "enemy_placement_pointer_rows": len(placement_pointers),
            "enemy_placement_unique_lists": len(placement_lists),
            "enemy_placement_weighted_entries": sum(item["weighted_entries"] for item in placement_lists),
            "enemy_placement_entry_count_histogram": counter_dict(placement_entry_counts),
            "enemy_placement_pointer_fan_in_histogram": counter_dict(placement_pointer_fan_in_counts),
            "enemy_placement_selection_weight_histogram": counter_dict(placement_weight_counts),
            "enemy_placement_total_selection_weight_histogram": counter_dict(placement_total_weight_counts),
            "enemy_placement_event_flag_rows": sum(1 for item in placement_lists if item["event_flag_gate"]),
            "enemy_placement_flagged_chance_rows": sum(1 for item in placement_lists if item["flagged_spawn_chance"]),
            "battle_entry_pointer_rows": len(battle_entry_rows),
            "battle_entry_pointer_null_rows": sum(1 for pointer in battle_pointer_rows if pointer is None),
            "battle_entry_pointer_bank_histogram": hex_byte_counter_dict(Counter(battle_pointer_banks)),
            "battle_entry_pointer_padding_byte_histogram": hex_byte_counter_dict(Counter(battle_pointer_padding_bytes)),
            "battle_entry_run_away_flag_histogram": hex_word_counter_dict(
                Counter(row["run_away_flag"] for row in battle_entry_rows)
            ),
            "battle_entry_run_away_flag_state_histogram": counter_dict(
                Counter(row["run_away_flag_state"] for row in battle_entry_rows)
            ),
            "battle_entry_presentation_sprite_style_histogram": counter_dict(
                Counter(row["presentation_sprite_style"] for row in battle_entry_rows)
            ),
            "battle_group_unique_pointer_slices": len(battle_lists),
            "battle_group_pointer_fan_in_histogram": counter_dict(battle_pointer_fan_in_counts),
            "battle_group_enemy_entries": sum(item["enemy_entries"] for item in battle_lists),
            "battle_group_entry_count_histogram": counter_dict(battle_entry_counts),
            "battle_group_total_enemy_count_histogram": counter_dict(battle_total_enemy_counts),
            "battle_group_repeat_count_histogram": counter_dict(battle_repeat_counts),
            "battle_group_byte_length_histogram": counter_dict(battle_byte_length_counts),
            "battle_group_pointed_list_bytes": pointed_battle_group_bytes,
            "battle_group_unpointed_gap_bytes": sum(item["bytes"] for item in battle_group_unpointed_ranges),
            "battle_group_unpointed_gap_ranges": battle_group_unpointed_ranges,
        },
        "enemy_placement_group_lists": placement_lists,
        "enemy_placement_weighted_entries": placement_entries,
        "battle_entry_rows": battle_entry_rows,
        "enemy_battle_group_lists": battle_lists,
        "enemy_battle_group_entries": battle_group_entries,
    }


def render_markdown(contract: dict[str, Any]) -> str:
    summary = contract["summary"]
    lines = [
        "# D0 Variable-List Contracts",
        "",
        "Generated by `tools/build_d0_variable_list_contracts.py` from the byte-equivalent D0 source scaffold.",
        "",
        "## Summary",
        "",
        f"- enemy placement pointer rows: `{summary['enemy_placement_pointer_rows']}`",
        f"- unique enemy placement lists: `{summary['enemy_placement_unique_lists']}`",
        f"- weighted spawn entries: `{summary['enemy_placement_weighted_entries']}`",
        f"- enemy placement entry-count histogram: `{summary['enemy_placement_entry_count_histogram']}`",
        f"- enemy placement pointer fan-in histogram: `{summary['enemy_placement_pointer_fan_in_histogram']}`",
        f"- enemy placement nonzero event-flag rows: `{summary['enemy_placement_event_flag_rows']}`",
        f"- enemy placement nonzero flagged-chance rows: `{summary['enemy_placement_flagged_chance_rows']}`",
        f"- battle entry pointer rows: `{summary['battle_entry_pointer_rows']}`",
        f"- battle entry null pointer rows: `{summary['battle_entry_pointer_null_rows']}`",
        f"- unique enemy battle-group pointer slices: `{summary['battle_group_unique_pointer_slices']}`",
        f"- battle-group enemy entries: `{summary['battle_group_enemy_entries']}`",
        f"- battle-group entry-count histogram: `{summary['battle_group_entry_count_histogram']}`",
        f"- battle-group pointed bytes: `{summary['battle_group_pointed_list_bytes']}`",
        f"- battle-group unpointed gap bytes: `{summary['battle_group_unpointed_gap_bytes']}`",
        "",
        "## Record Shapes",
        "",
        "Enemy placement group lists at `D0:BBAC..D0:C60D` have a four-byte header followed by three-byte weighted entries.",
        "`ENEMY_PLACEMENT_GROUPS_PTR_TABLE` rows select these lists, and `C0:2668` uses the header chance bytes before walking the weighted entries.",
        "",
        "| Offset | Field | Size | Consumer evidence |",
        "| ---: | --- | ---: | --- |",
    ]
    for field in contract["record_shapes"]["enemy_placement_group_list"]:
        lines.append(f"| `+0x{field['offset']:X}` | `{field['field']}` | {field['size']} | {field['consumer']} |")
    lines.extend(
        [
            "",
            "Each weighted entry is three bytes.",
            "",
            "| Offset | Field | Size | Consumer evidence |",
            "| ---: | --- | ---: | --- |",
        ]
    )
    for field in contract["record_shapes"]["enemy_placement_weighted_entry"]:
        lines.append(f"| `+0x{field['offset']:X}` | `{field['field']}` | {field['size']} | {field['consumer']} |")
    lines.extend(
        [
            "",
            "`BTL_ENTRY_PTR_TABLE` rows are eight bytes and point at enemy battle-group slices.",
            "",
            "| Offset | Field | Size | Consumer evidence |",
            "| ---: | --- | ---: | --- |",
        ]
    )
    for field in contract["record_shapes"]["battle_entry_pointer_row"]:
        lines.append(f"| `+0x{field['offset']:X}` | `{field['field']}` | {field['size']} | {field['consumer']} |")

    lines.extend(
        [
            "",
            "Enemy battle-group pointer slices at `D0:D52D..D0:DFB4` have three-byte entries and a final `FF` terminator byte.",
            "Every non-null `BTL_ENTRY_PTR_TABLE` row targets a unique parsed slice; the table span also carries the unpointed gap recorded below.",
            "",
            "| Offset | Field | Size | Consumer evidence |",
            "| ---: | --- | ---: | --- |",
        ]
    )
    for field in contract["record_shapes"]["enemy_battle_group_entry"]:
        lines.append(f"| `+0x{field['offset']:X}` | `{field['field']}` | {field['size']} | {field['consumer']} |")

    lines.extend(
        [
            "",
            "## Distribution Snapshot",
            "",
            "| Family | Metric | Values |",
            "| --- | --- | --- |",
            f"| enemy placement lists | entry count | {format_histogram(summary['enemy_placement_entry_count_histogram'])} |",
            f"| enemy placement entries | selection weight | {format_histogram(summary['enemy_placement_selection_weight_histogram'])} |",
            f"| enemy placement lists | total selection weight | {format_histogram(summary['enemy_placement_total_selection_weight_histogram'])} |",
            f"| BTL entry rows | pointer bank | {format_histogram(summary['battle_entry_pointer_bank_histogram'])} |",
            f"| BTL entry rows | pointer padding byte | {format_histogram(summary['battle_entry_pointer_padding_byte_histogram'])} |",
            f"| BTL entry rows | run-away flag | {format_histogram(summary['battle_entry_run_away_flag_histogram'])} |",
            f"| BTL entry rows | run-away flag state | {format_histogram(summary['battle_entry_run_away_flag_state_histogram'])} |",
            f"| BTL entry rows | presentation sprite style | {format_histogram(summary['battle_entry_presentation_sprite_style_histogram'])} |",
            f"| enemy battle groups | entry count | {format_histogram(summary['battle_group_entry_count_histogram'])} |",
            f"| enemy battle groups | total enemy count | {format_histogram(summary['battle_group_total_enemy_count_histogram'])} |",
            f"| enemy battle groups | repeat count | {format_histogram(summary['battle_group_repeat_count_histogram'])} |",
            f"| enemy battle groups | byte length | {format_histogram(summary['battle_group_byte_length_histogram'])} |",
        ]
    )

    if summary["battle_group_unpointed_gap_ranges"]:
        lines.extend(
            [
                "",
                "## Unpointed Battle-Group Gap",
                "",
                "The gap is inside the byte-accounted `ENEMY_BATTLE_GROUPS_TABLE` span but has no `BTL_ENTRY_PTR_TABLE` owner.",
                "",
                "| Range | Bytes | Reason |",
                "| --- | ---: | --- |",
            ]
        )
        for row in summary["battle_group_unpointed_gap_ranges"]:
            lines.append(f"| `{row['range']}` | {row['bytes']} | {row['reason']} |")

    lines.extend(
        [
            "",
            "## Boundary Samples",
            "",
            "| Family | First | Last | Count | Terminal boundary |",
            "| --- | --- | --- | ---: | --- |",
        ]
    )
    placement = contract["enemy_placement_group_lists"]
    battle = contract["enemy_battle_group_lists"]
    lines.append(
        f"| enemy placement groups | `{placement[0]['address']}` | `{placement[-1]['address']}` | {len(placement)} | `{placement[-1]['end_exclusive']}` |"
    )
    lines.append(
        f"| enemy battle-group pointer slices | `{battle[0]['address']}` | `{battle[-1]['address']}` | {len(battle)} | `{battle[-1]['end_exclusive']}` |"
    )

    lines.extend(
        [
            "",
            "## Entry Samples",
            "",
            "| Family | Address | Fields |",
            "| --- | --- | --- |",
        ]
    )
    for row in contract["enemy_placement_group_lists"][:4]:
        lines.append(
            "| enemy placement list | "
            f"`{row['address']}` | event_flag_gate `{row['event_flag_gate']}`, "
            f"primary_spawn_chance `{row['primary_spawn_chance']}`, "
            f"flagged_spawn_chance `{row['flagged_spawn_chance']}`, "
            f"weighted_entries `{row['weighted_entries']}` |"
        )
    for row in contract["enemy_battle_group_lists"][:4]:
        lines.append(
            "| enemy battle group | "
            f"`{row['address']}` | enemy_entries `{row['enemy_entries']}`, "
            f"total_enemy_count `{row['total_enemy_count']}`, terminator `{row['terminator']}` |"
        )

    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- Placement `selection_weight` bytes are named only as the C0 selection weights; this pass does not assign encounter-design meanings to individual weights.",
            "- Battle group pointer targets are consumer-visible slices; preserve unpointed bytes in the table span separately instead of assigning them to a pointer row.",
            "- `run_away_flag` and `run_away_flag_state` names come from the ebsrc battle-entry pointer structure and remain numeric here.",
            "- Enemy ids are linked to the D5 enemy config table by C2 consumers; this pass does not rename individual enemy ids.",
            "",
            "## Evidence",
            "",
            "- `notes/d0-table-splits.md` pins the D0 variable-list spans and pointer-table counts.",
            "- `notes/data-contracts-c0-c4.md` carries the central `BTL_ENTRY_PTR_TABLE` row shape, including the presentation-sprite-style consumer note.",
            "- `notes/entity-placement-probe-c0263d-c02668.md` documents the C0 spawn-candidate consumer for `D0:B880` / `D0:BBAC`.",
            "- `src/c0/c0_2668_resolve_spawn_probe_candidate_list.asm` reads the placement-list header and weighted entries.",
            "- `src/c2/c2_2f38_init_battle_scripted.asm` expands battle-group repeat counts into `$9F8C` enemy ids.",
            "- `src/c2/c2_eee7_load_battle_group_enemy_sprites.asm` and `src/c2/c2_bd5e_call_for_help_enemy_selection_and_message_body.asm` walk battle-group entries until `FF` and consume the enemy id word.",
            "",
            "Full per-list boundaries and decoded entry rows are available in `notes/d0-variable-list-contracts.json`.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build D0 variable-list subrecord contracts.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN_OUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    contract = build_contract(args.source)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.write_text(render_markdown(contract), encoding="utf-8")
    print(f"Wrote {args.json_out} and {args.markdown_out}")


if __name__ == "__main__":
    main()
