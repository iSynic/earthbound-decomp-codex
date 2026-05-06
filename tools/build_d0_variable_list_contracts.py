from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / "src" / "d0" / "bank_d0_helpers_asar.asm"
SCHEMA = "earthbound-decomp.d0-variable-list-contracts.v1"


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


def build_contract(source_path: Path) -> dict[str, Any]:
    text = source_path.read_text(encoding="utf-8")
    placement_ptr = parse_db_bytes(source_slice(text, "table_enemy_placement_groups_ptr_table.asm"))
    placement_data = parse_db_bytes(source_slice(text, "table_enemy_placement_groups_table.asm"))
    battle_entry_ptr = parse_db_bytes(source_slice(text, "table_btl_entry_ptr_table.asm"))
    battle_data = parse_db_bytes(source_slice(text, "table_enemy_battle_groups_table.asm"))

    placement_pointers = [long_low_word(placement_ptr, index * 4) for index in range(203)]
    placement_unique = sorted(set(placement_pointers))
    placement_lists = []
    for list_index, start in enumerate(placement_unique):
        end = placement_unique[list_index + 1] if list_index + 1 < len(placement_unique) else 0xC60D
        length = end - start
        if length < 4 or (length - 4) % 3:
            raise ValueError(f"bad enemy placement list length at {start:04X}: {length}")
        offset = start - 0xBBAC
        entry_count = (length - 4) // 3
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
                "pointer_rows": [index for index, pointer in enumerate(placement_pointers) if pointer == start],
            }
        )

    battle_pointers: list[int] = []
    battle_pointer_rows: list[int | None] = []
    battle_entry_rows = []
    for index in range(484):
        offset = index * 8
        target = long_low_word(battle_entry_ptr, offset)
        bank = battle_entry_ptr[offset + 2]
        extra = battle_entry_ptr[offset + 3]
        if target or bank or extra:
            battle_pointers.append(target)
            battle_pointer_rows.append(target)
        else:
            battle_pointer_rows.append(None)
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
    for list_index, start in enumerate(sorted(set(battle_pointers))):
        entry_count = 0
        offset = start - 0xD52D
        if offset < 0 or offset >= len(battle_data):
            raise ValueError(f"enemy battle group pointer outside D0:D52D data span: {start:04X}")
        while offset + entry_count * 3 < len(battle_data) and battle_data[offset + entry_count * 3] != 0xFF:
            entry_count += 1
        terminator_offset = offset + entry_count * 3
        if terminator_offset >= len(battle_data):
            raise ValueError(f"enemy battle group at {start:04X} lacks FF terminator")
        length = entry_count * 3 + 1
        end = start + length
        enemy_ids = [word(battle_data, offset + 1 + entry * 3) for entry in range(entry_count)]
        counts = [battle_data[offset + entry * 3] for entry in range(entry_count)]
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
            }
        )

    placement_entry_counts = Counter(item["weighted_entries"] for item in placement_lists)
    battle_entry_counts = Counter(item["enemy_entries"] for item in battle_lists)
    return {
        "schema": SCHEMA,
        "source": str(source_path.relative_to(ROOT)),
        "record_shapes": {
            "enemy_placement_group_list": [
                {"offset": 0, "field": "event_flag_gate", "size": 2, "consumer": "C0:2668 tests this through C2:1628"},
                {"offset": 2, "field": "primary_spawn_chance", "size": 1, "consumer": "C0:2668 seeds $4A70 from this byte"},
                {"offset": 3, "field": "flagged_spawn_chance", "size": 1, "consumer": "C0:2668 can replace $4A70 with this byte when the gate flag is set"},
                {"offset": 4, "field": "weighted_entries", "size": 3, "consumer": "C0:2668 walks cumulative weight byte + battle group id word entries"},
            ],
            "enemy_battle_group_entry": [
                {"offset": 0, "field": "repeat_count_or_ff_terminator", "size": 1, "consumer": "C2:2F38 repeats the enemy id this many times; C2:EEE7 treats FF as terminator"},
                {"offset": 1, "field": "enemy_id", "size": 2, "consumer": "C2:2F38 stages this id into $9F8C; C2:EEE7 maps it through D5 enemy config"},
            ],
        },
        "summary": {
            "enemy_placement_pointer_rows": len(placement_pointers),
            "enemy_placement_unique_lists": len(placement_lists),
            "enemy_placement_weighted_entries": sum(item["weighted_entries"] for item in placement_lists),
            "enemy_placement_entry_count_histogram": dict(sorted(placement_entry_counts.items())),
            "battle_entry_pointer_rows": len(battle_entry_rows),
            "battle_group_unique_pointer_slices": len(battle_lists),
            "battle_group_enemy_entries": sum(item["enemy_entries"] for item in battle_lists),
            "battle_group_entry_count_histogram": dict(sorted(battle_entry_counts.items())),
        },
        "enemy_placement_group_lists": placement_lists,
        "battle_entry_rows": battle_entry_rows,
        "enemy_battle_group_lists": battle_lists,
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
        f"- battle entry pointer rows: `{summary['battle_entry_pointer_rows']}`",
        f"- unique enemy battle-group pointer slices: `{summary['battle_group_unique_pointer_slices']}`",
        f"- battle-group enemy entries: `{summary['battle_group_enemy_entries']}`",
        "",
        "## Record Shapes",
        "",
        "Enemy placement group lists at `D0:BBAC..D0:C60D` have a four-byte header followed by three-byte weighted entries.",
        "",
        "| Offset | Field | Size | Consumer evidence |",
        "| ---: | --- | ---: | --- |",
    ]
    for field in contract["record_shapes"]["enemy_placement_group_list"]:
        lines.append(f"| `+0x{field['offset']:X}` | `{field['field']}` | {field['size']} | {field['consumer']} |")
    lines.extend(
        [
            "",
            "Enemy battle-group pointer slices at `D0:D52D..D0:DFB4` have three-byte entries and a final `FF` terminator byte.",
            "Some `BTL_ENTRY_PTR_TABLE` rows intentionally target later entry boundaries inside a shared terminated byte run, so each pointer target is parsed as a consumer-visible suffix slice.",
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
            "## Evidence",
            "",
            "- `notes/d0-table-splits.md` pins the D0 variable-list spans and pointer-table counts.",
            "- `notes/entity-placement-probe-c0263d-c02668.md` documents the C0 spawn-candidate consumer for `D0:B880` / `D0:BBAC`.",
            "- `src/c0/c0_2668_resolve_spawn_probe_candidate_list.asm` reads the placement-list header and weighted entries.",
            "- `src/c2/c2_2f38_init_battle_scripted.asm` expands battle-group repeat counts into `$9F8C` enemy ids.",
            "- `src/c2/c2_eee7_load_battle_group_enemy_sprites.asm` and `src/c2/c2_bd5e_call_for_help_enemy_selection_and_message_body.asm` walk battle-group entries until `FF` and consume the enemy id word.",
            "",
            "Full per-list boundaries are available in `build/d0-variable-list-contracts.json`.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build D0 variable-list subrecord contracts.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--json-out", type=Path, default=ROOT / "build" / "d0-variable-list-contracts.json")
    parser.add_argument("--markdown-out", type=Path, default=ROOT / "notes" / "d0-variable-list-contracts.md")
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
