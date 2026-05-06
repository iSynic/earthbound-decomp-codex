from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CF_SOURCE = ROOT / "src" / "cf" / "bank_cf_helpers_asar.asm"
DEFAULT_DC_SOURCE = ROOT / "src" / "dc" / "bank_dc_helpers_asar.asm"
DEFAULT_JSON_OUT = ROOT / "notes" / "cf-event-music-context-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "cf-event-music-context-contracts.md"

SCHEMA = "earthbound-decomp.cf-event-music-context-contracts.v1"
CF_POINTER_START = 0x58EF
CF_TABLE_START = 0x5A39
CF_TABLE_END = 0x61DD
CF_POINTER_ROWS = 165
DC_SELECTOR_START = 0xD637
DC_SELECTOR_GRID_COLUMNS = 32
DC_SELECTOR_GRID_ROWS = 40
DC_SELECTOR_ROWS = DC_SELECTOR_GRID_COLUMNS * DC_SELECTOR_GRID_ROWS


def source_slice(text: str, source_name: str) -> str:
    marker = f"; Source: {source_name}"
    start = text.index(marker)
    next_source = text.find("; Source: ", start + len(marker))
    return text[start : next_source if next_source != -1 else len(text)]


def parse_db_bytes(text: str) -> list[int]:
    values: list[int] = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("db "):
            values.extend(int(match[1:], 16) for match in re.findall(r"\$[0-9A-Fa-f]{2}", line))
    return values


def word(data: list[int], offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def cpu(bank: int, address: int) -> str:
    return f"{bank:02X}:{address:04X}"


def counter_dict(counter: Counter[int]) -> dict[str, int]:
    return {str(key): counter[key] for key in sorted(counter)}


def hex_counter_dict(counter: Counter[int]) -> dict[str, int]:
    return {f"0x{key:02X}": counter[key] for key in sorted(counter)}


def parse_context_chain(
    selector_id: int, start: int, table_data: list[int], pointer_targets: dict[int, list[int]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cursor = start - CF_TABLE_START
    rows: list[dict[str, Any]] = []
    while True:
        address = CF_TABLE_START + cursor
        if cursor < 0 or cursor + 4 > len(table_data):
            raise ValueError(f"context selector {selector_id} ran outside CF event-music table at {address:04X}")
        event_word = word(table_data, cursor)
        is_default = event_word == 0
        row = {
            "row_index": None,
            "row_in_chain": len(rows),
            "selector_id": selector_id,
            "address": cpu(0xCF, address),
            "event_flag_condition_word": event_word,
            "event_flag_id": None if is_default else event_word & 0x7FFF,
            "expected_flag_state": None if is_default else (1 if event_word & 0x8000 else 0),
            "is_default_row": is_default,
            "music_track": table_data[cursor + 2],
            "screen_transition_sfx": table_data[cursor + 3],
        }
        rows.append(row)
        cursor += 4
        if is_default:
            break

    end = CF_TABLE_START + cursor
    chain = {
        "selector_id": selector_id,
        "address": cpu(0xCF, start),
        "end_exclusive": cpu(0xCF, end),
        "bytes": end - start,
        "row_count": len(rows),
        "conditional_rows": len(rows) - 1,
        "default_row": rows[-1],
        "pointer_rows": pointer_targets[start],
        "rows": rows,
    }
    return chain, rows


def build_contract(cf_source: Path, dc_source: Path) -> dict[str, Any]:
    cf_text = cf_source.read_text(encoding="utf-8")
    dc_text = dc_source.read_text(encoding="utf-8")
    pointer_data = parse_db_bytes(source_slice(cf_text, "src/cf/table_overworld_event_music_pointer_table.asm"))
    table_data = parse_db_bytes(source_slice(cf_text, "src/cf/table_overworld_event_music_table.asm"))
    sector_data = parse_db_bytes(source_slice(dc_text, "src/dc/table_data_map_per_sector_music_asm.asm"))

    if len(pointer_data) != CF_POINTER_ROWS * 2:
        raise ValueError(f"unexpected CF event-music pointer bytes: {len(pointer_data)}")
    if len(table_data) != CF_TABLE_END - CF_TABLE_START:
        raise ValueError(f"unexpected CF event-music table bytes: {len(table_data)}")
    if len(sector_data) != DC_SELECTOR_ROWS * 2:
        raise ValueError(f"unexpected DC per-sector music bytes: {len(sector_data)}")

    pointers = [word(pointer_data, index * 2) for index in range(CF_POINTER_ROWS)]
    pointer_targets: dict[int, list[int]] = {}
    pointer_rows: list[dict[str, Any]] = []
    for selector_id, pointer in enumerate(pointers):
        in_context_table = CF_TABLE_START <= pointer < CF_TABLE_END
        if pointer != 0 and not in_context_table:
            raise ValueError(f"selector {selector_id} points outside CF event-music context table: {pointer:04X}")
        if in_context_table:
            pointer_targets.setdefault(pointer, []).append(selector_id)
        pointer_rows.append(
            {
                "selector_id": selector_id,
                "address": cpu(0xCF, CF_POINTER_START + selector_id * 2),
                "context_pointer_low_word": pointer,
                "target": cpu(0xCF, pointer) if in_context_table else None,
                "in_context_table": in_context_table,
            }
        )

    chains: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for selector_id, pointer in enumerate(pointers):
        if not (CF_TABLE_START <= pointer < CF_TABLE_END):
            continue
        chain, chain_rows = parse_context_chain(selector_id, pointer, table_data, pointer_targets)
        for row in chain_rows:
            row["row_index"] = len(rows)
            rows.append(row)
        chains.append(chain)

    terminal_end = max(int(chain["end_exclusive"].split(":")[1], 16) for chain in chains)
    if terminal_end != CF_TABLE_END:
        raise ValueError(f"event-music context parse ended at {terminal_end:04X}, expected {CF_TABLE_END:04X}")

    first_plane = sector_data[:DC_SELECTOR_ROWS]
    second_plane = sector_data[DC_SELECTOR_ROWS:]
    invalid_selectors = sorted({value for value in first_plane if value >= CF_POINTER_ROWS})
    if invalid_selectors:
        raise ValueError(f"DC selector plane references invalid CF selectors: {invalid_selectors}")

    selector_rows = []
    for sector_index, selector_id in enumerate(first_plane):
        sector_x = sector_index % DC_SELECTOR_GRID_COLUMNS
        sector_y = sector_index // DC_SELECTOR_GRID_COLUMNS
        pointer_row = pointer_rows[selector_id]
        selector_rows.append(
            {
                "sector_index": sector_index,
                "sector": {"x": sector_x, "y": sector_y},
                "address": cpu(0xDC, DC_SELECTOR_START + sector_index),
                "event_music_context_selector": selector_id,
                "pointer_target": pointer_row["target"],
            }
        )

    return {
        "schema": SCHEMA,
        "title": "CF Event Music Context Contracts",
        "generator": "tools/build_cf_event_music_context_contracts.py",
        "source_policy": (
            "Derived from byte-equivalent CF/DC source scaffolds plus the C0:68F4/C0:69AF "
            "and EF debug-overlay consumers. This records only the selector, pointer, "
            "event-condition, music-track, and transition-SFX fields those consumers read."
        ),
        "sources": {
            "cf_source_scaffold": str(cf_source.relative_to(ROOT)),
            "dc_source_scaffold": str(dc_source.relative_to(ROOT)),
            "cf_table_splits": "notes/cf-table-splits.md",
            "c0_consumer": "src/c0/c0_65c2_probe_type6_door_candidate.asm",
            "ef_debug_consumer": "src/ef/ef_dcbc_de1a_debug_check_position_overlay.asm",
            "position_context_note": "notes/c0-current-position-music-refresh-c068f4-c069af.md",
        },
        "spans": {
            "event_music_context_pointer_table": {
                "range": f"{cpu(0xCF, CF_POINTER_START)}..{cpu(0xCF, CF_TABLE_START)}",
                "rows": CF_POINTER_ROWS,
                "stride": 2,
            },
            "event_music_context_table": {
                "range": f"{cpu(0xCF, CF_TABLE_START)}..{cpu(0xCF, CF_TABLE_END)}",
                "bytes": CF_TABLE_END - CF_TABLE_START,
            },
            "current_position_selector_plane": {
                "range": f"{cpu(0xDC, DC_SELECTOR_START)}..{cpu(0xDC, DC_SELECTOR_START + DC_SELECTOR_ROWS)}",
                "rows": DC_SELECTOR_ROWS,
                "stride": 1,
                "grid": {"columns": DC_SELECTOR_GRID_COLUMNS, "rows": DC_SELECTOR_GRID_ROWS},
            },
            "uninterpreted_second_plane": {
                "range": f"{cpu(0xDC, DC_SELECTOR_START + DC_SELECTOR_ROWS)}..{cpu(0xDC, DC_SELECTOR_START + DC_SELECTOR_ROWS * 2)}",
                "bytes": DC_SELECTOR_ROWS,
            },
        },
        "record_shapes": {
            "event_music_context_pointer_row": [
                {
                    "offset": 0,
                    "field": "context_pointer_low_word",
                    "size": 2,
                    "consumer": "C0:6932 reads CF:58EF + selector*2, masks 0x7FFF, and uses bank CF for the selected context chain",
                }
            ],
            "event_music_context_row": [
                {
                    "offset": 0,
                    "field": "event_flag_condition_word",
                    "size": 2,
                    "consumer": "C0:6948 treats zero as the selected default row; otherwise C0:6950 masks 0x7FFF for C2:1628 and bit 15 supplies the expected state",
                },
                {
                    "offset": 2,
                    "field": "music_track",
                    "size": 1,
                    "consumer": "C0:6987 reads this byte into $5DD6 before optional ChangeMusic dispatch",
                },
                {
                    "offset": 3,
                    "field": "screen_transition_sfx",
                    "size": 1,
                    "consumer": "C0:69DC reads this byte from the selected row and sends it through C0:AC0C as an APUIO1 transition cue",
                },
            ],
            "current_position_selector_byte": [
                {
                    "offset": 0,
                    "field": "event_music_context_selector",
                    "size": 1,
                    "consumer": "C0:691E indexes DC:D637 by sector_y*32 + sector_x and masks the byte before indexing CF:58EF",
                }
            ],
        },
        "summary": {
            "pointer_rows": len(pointer_rows),
            "null_pointer_rows": sum(1 for row in pointer_rows if not row["in_context_table"]),
            "context_chains": len(chains),
            "context_rows": len(rows),
            "conditional_rows": sum(1 for row in rows if not row["is_default_row"]),
            "default_rows": sum(1 for row in rows if row["is_default_row"]),
            "terminal_boundary": cpu(0xCF, terminal_end),
            "current_position_selector_rows": len(selector_rows),
            "current_position_selector_unique_count": len(set(first_plane)),
            "current_position_selector_range": [min(first_plane), max(first_plane)],
            "current_position_selector_histogram": counter_dict(Counter(first_plane)),
            "chain_row_count_histogram": counter_dict(Counter(chain["row_count"] for chain in chains)),
            "chain_conditional_row_count_histogram": counter_dict(Counter(chain["conditional_rows"] for chain in chains)),
            "music_track_histogram": hex_counter_dict(Counter(row["music_track"] for row in rows)),
            "screen_transition_sfx_histogram": hex_counter_dict(Counter(row["screen_transition_sfx"] for row in rows)),
            "second_plane_value_range": [min(second_plane), max(second_plane)],
            "second_plane_unique_count": len(set(second_plane)),
        },
        "event_music_context_pointer_rows": pointer_rows,
        "event_music_context_chains": chains,
        "event_music_context_rows": rows,
        "current_position_selector_rows": selector_rows,
    }


def render_markdown(contract: dict[str, Any]) -> str:
    summary = contract["summary"]
    lines = [
        "# CF Event Music Context Contracts",
        "",
        "Generated by `tools/build_cf_event_music_context_contracts.py` from the byte-equivalent CF/DC source scaffolds and the C0/EF consumers.",
        "",
        "## Summary",
        "",
        f"- CF pointer rows: `{summary['pointer_rows']}`",
        f"- null pointer rows: `{summary['null_pointer_rows']}`",
        f"- CF context chains: `{summary['context_chains']}`",
        f"- CF context rows: `{summary['context_rows']}`",
        f"- conditional rows: `{summary['conditional_rows']}`",
        f"- default rows: `{summary['default_rows']}`",
        f"- terminal boundary: `{summary['terminal_boundary']}`",
        f"- DC current-position selector rows: `{summary['current_position_selector_rows']}`",
        f"- DC selector unique count: `{summary['current_position_selector_unique_count']}`",
        f"- DC selector range: `{summary['current_position_selector_range']}`",
        f"- chain row-count histogram: `{summary['chain_row_count_histogram']}`",
        "",
        "## Record Shapes",
        "",
        "| Record | Offset | Field | Size | Consumer evidence |",
        "| --- | ---: | --- | ---: | --- |",
    ]
    for record_name, fields in contract["record_shapes"].items():
        for field in fields:
            lines.append(
                f"| `{record_name}` | `+0x{field['offset']:X}` | `{field['field']}` | {field['size']} | {field['consumer']} |"
            )

    lines.extend(
        [
            "",
            "## Chain Samples",
            "",
            "| Selector | Address | End | Rows | Conditional rows | Default music | Default SFX |",
            "| ---: | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    sample_selector_ids = {1, 2, 3, 11, 47, 164}
    for chain in contract["event_music_context_chains"]:
        if chain["selector_id"] in sample_selector_ids:
            default = chain["default_row"]
            lines.append(
                f"| {chain['selector_id']} | `{chain['address']}` | `{chain['end_exclusive']}` | "
                f"{chain['row_count']} | {chain['conditional_rows']} | "
                f"`0x{default['music_track']:02X}` | `0x{default['screen_transition_sfx']:02X}` |"
            )

    top_selectors = Counter(
        row["event_music_context_selector"] for row in contract["current_position_selector_rows"]
    ).most_common(12)
    lines.extend(
        [
            "",
            "## DC Selector Plane",
            "",
            "`C0:68F4` computes `sector_index = sector_y * 32 + sector_x`, reads the byte at `DC:D637 + sector_index`, and uses that selector to choose a CF pointer row.",
            "",
            "| Selector | Sectors | Target |",
            "| ---: | ---: | --- |",
        ]
    )
    pointer_rows = {
        row["selector_id"]: row for row in contract["event_music_context_pointer_rows"]
    }
    for selector_id, count in top_selectors:
        lines.append(f"| {selector_id} | {count} | `{pointer_rows[selector_id]['target']}` |")

    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- Selector `0` is a null CF pointer row and is not referenced by the observed `DC:D637` current-position selector plane.",
            "- A zero `event_flag_condition_word` is the selected default row; C0 still reads `music_track` and `screen_transition_sfx` from that row.",
            "- The second 1280-byte half of `DC:D637..DC:E036` is byte-accounted here but remains unnamed because the C0/EF consumers cited in this pass read only the first plane.",
            "- Track ids, SFX ids, and individual event flags are left as numeric ids; this contract does not assign human names to them.",
            "",
            "## Evidence",
            "",
            "- `src/c0/c0_65c2_probe_type6_door_candidate.asm` derives the 32x40 sector index, reads `DC:D637`, indexes `CF:58EF`, walks four-byte rows, and selects music/SFX bytes.",
            "- `src/ef/ef_dcbc_de1a_debug_check_position_overlay.asm` reads the same `DC:D637` selector byte for the debug position overlay.",
            "- `notes/c0-current-position-music-refresh-c068f4-c069af.md` documents the C0 music-context refresh and apply path.",
            "- `notes/cf-event-music-context-contracts.json` carries complete decoded pointer rows, context chains, context rows, and first-plane DC selector rows.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build CF/DC event-music context contracts.")
    parser.add_argument("--cf-source", type=Path, default=DEFAULT_CF_SOURCE)
    parser.add_argument("--dc-source", type=Path, default=DEFAULT_DC_SOURCE)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN_OUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    contract = build_contract(args.cf_source, args.dc_source)
    args.json_out.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    args.markdown_out.write_text(render_markdown(contract), encoding="utf-8")
    print(f"Wrote {args.json_out} and {args.markdown_out}")


if __name__ == "__main__":
    main()
