from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / "src" / "d0" / "bank_d0_helpers_asar.asm"
DEFAULT_JSON_OUT = ROOT / "notes" / "d0-tile-event-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "d0-tile-event-contracts.md"
SCHEMA = "earthbound-decomp.d0-tile-event-contracts.v1"
EVENT_POINTER_ROWS = 20
EVENT_POINTER_TABLE_START = 0x1598
EVENT_CHAIN_START = 0x15C0
EVENT_CHAIN_END = 0x1880


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


def cpu(address: int) -> str:
    return f"D0:{address:04X}"


def counter_dict(counter: Counter[int]) -> dict[str, int]:
    return {str(key): counter[key] for key in sorted(counter)}


def hex_counter_dict(counter: Counter[int]) -> dict[str, int]:
    return {f"0x{key:04X}": counter[key] for key in sorted(counter)}


def build_contract(source_path: Path) -> dict[str, Any]:
    text = source_path.read_text(encoding="utf-8")
    pointer_data = parse_db_bytes(source_slice(text, "src/d0/table_event_control_ptr_table.asm"))
    chain_data = parse_db_bytes(source_slice(text, "src/d0/table_map_tile_event_control_table.asm"))

    if len(pointer_data) != EVENT_POINTER_ROWS * 2:
        raise ValueError(f"unexpected event pointer byte count: {len(pointer_data)}")
    if len(chain_data) != EVENT_CHAIN_END - EVENT_CHAIN_START:
        raise ValueError(f"unexpected tile-event chain byte count: {len(chain_data)}")

    pointers = [word(pointer_data, index * 2) for index in range(EVENT_POINTER_ROWS)]
    pointer_rows = []
    for index, pointer in enumerate(pointers):
        if not (EVENT_CHAIN_START <= pointer < EVENT_CHAIN_END):
            raise ValueError(f"tile-event pointer {index} outside D0:15C0..D0:187F: {pointer:04X}")
        pointer_rows.append(
            {
                "chain_id": index,
                "address": cpu(EVENT_POINTER_TABLE_START + index * 2),
                "chain_pointer_low_word": pointer,
                "target": cpu(pointer),
            }
        )

    chains = []
    event_entries = []
    replacement_pairs = []
    for chain_id, start in enumerate(pointers):
        cursor = start - EVENT_CHAIN_START
        chain_entries = []
        chain_pairs = []
        while True:
            event_word = word(chain_data, cursor)
            header_address = EVENT_CHAIN_START + cursor
            if event_word == 0:
                terminator = cpu(header_address)
                cursor += 2
                break

            replacement_count = word(chain_data, cursor + 2)
            entry = {
                "entry_index": len(event_entries),
                "entry_in_chain": len(chain_entries),
                "chain_id": chain_id,
                "address": cpu(header_address),
                "event_flag_condition_word": event_word,
                "event_flag_id": event_word & 0x7FFF,
                "expected_flag_state": 1 if event_word & 0x8000 else 0,
                "replacement_pair_count": replacement_count,
                "first_replacement_pair_index": len(replacement_pairs) if replacement_count else None,
            }
            cursor += 4

            entry_pairs = []
            for pair_in_entry in range(replacement_count):
                pair_address = EVENT_CHAIN_START + cursor
                pair = {
                    "pair_index": len(replacement_pairs),
                    "pair_in_entry": pair_in_entry,
                    "entry_index": entry["entry_index"],
                    "chain_id": chain_id,
                    "address": cpu(pair_address),
                    "replacement_target_block_index": word(chain_data, cursor),
                    "replacement_source_block_index": word(chain_data, cursor + 2),
                }
                replacement_pairs.append(pair)
                chain_pairs.append(pair)
                entry_pairs.append(pair)
                cursor += 4

            entry["pairs"] = entry_pairs
            event_entries.append(entry)
            chain_entries.append(entry)

        end = EVENT_CHAIN_START + cursor
        chains.append(
            {
                "chain_id": chain_id,
                "address": cpu(start),
                "end_exclusive": cpu(end),
                "bytes": end - start,
                "event_entries": len(chain_entries),
                "replacement_pairs": len(chain_pairs),
                "terminator": terminator,
                "pointer_rows": [index for index, pointer in enumerate(pointers) if pointer == start],
                "entries": chain_entries,
            }
        )

    terminal_end = max(int(chain["end_exclusive"].split(":")[1], 16) for chain in chains)
    if terminal_end != EVENT_CHAIN_END:
        raise ValueError(f"tile-event chain parse ended at {terminal_end:04X}, expected {EVENT_CHAIN_END:04X}")

    return {
        "schema": SCHEMA,
        "title": "D0 Tile Event Contracts",
        "generator": "tools/build_d0_tile_event_contracts.py",
        "source_policy": (
            "Derived from the byte-equivalent D0 source scaffold and the C0:062A "
            "consumer. This records chain boundaries, event-condition headers, "
            "replacement-pair rows, and consumer-backed field names only."
        ),
        "sources": {
            "d0_source_scaffold": str(source_path.relative_to(ROOT)),
            "d0_table_splits": "notes/d0-table-splits.md",
            "consumer": "src/c0/c0_062a_load_landing_hdma_dispatch_block.asm",
        },
        "spans": {
            "event_control_pointer_table": {
                "range": f"{cpu(EVENT_POINTER_TABLE_START)}..{cpu(EVENT_CHAIN_START)}",
                "rows": EVENT_POINTER_ROWS,
                "stride": 2,
            },
            "map_tile_event_control_table": {
                "range": f"{cpu(EVENT_CHAIN_START)}..{cpu(EVENT_CHAIN_END)}",
                "bytes": EVENT_CHAIN_END - EVENT_CHAIN_START,
            },
        },
        "record_shapes": {
            "event_control_pointer_row": [
                {
                    "offset": 0,
                    "field": "chain_pointer_low_word",
                    "size": 2,
                    "consumer": "C0:0703 indexes D0:1598 by tileset/event-control id and adds the low word to bank D0",
                }
            ],
            "tile_event_condition_header": [
                {
                    "offset": 0,
                    "field": "event_flag_condition_word",
                    "size": 2,
                    "consumer": "C0:0715 treats zero as chain terminator, masks 0x7FFF for C2:1628, and uses bit 15 as the expected flag state",
                },
                {
                    "offset": 2,
                    "field": "replacement_pair_count",
                    "size": 2,
                    "consumer": "C0:0722 uses this count to walk four-byte replacement pairs",
                },
            ],
            "tile_event_replacement_pair": [
                {
                    "offset": 0,
                    "field": "replacement_target_block_index",
                    "size": 2,
                    "consumer": "C0:074D passes this as A to REPLACE_BLOCK, selecting the destination active block/cache slot",
                },
                {
                    "offset": 2,
                    "field": "replacement_source_block_index",
                    "size": 2,
                    "consumer": "C0:074A passes this as X/Y to REPLACE_BLOCK, selecting the source active block/cache slot",
                },
            ],
        },
        "summary": {
            "pointer_rows": len(pointer_rows),
            "chains": len(chains),
            "non_empty_chains": sum(1 for chain in chains if chain["event_entries"]),
            "event_condition_entries": len(event_entries),
            "replacement_pairs": len(replacement_pairs),
            "terminal_boundary": cpu(terminal_end),
            "chain_event_entry_count_histogram": counter_dict(Counter(chain["event_entries"] for chain in chains)),
            "chain_replacement_pair_count_histogram": counter_dict(
                Counter(chain["replacement_pairs"] for chain in chains)
            ),
            "entry_replacement_pair_count_histogram": counter_dict(
                Counter(entry["replacement_pair_count"] for entry in event_entries)
            ),
            "event_flag_id_histogram": hex_counter_dict(Counter(entry["event_flag_id"] for entry in event_entries)),
            "expected_flag_state_histogram": counter_dict(
                Counter(entry["expected_flag_state"] for entry in event_entries)
            ),
            "replacement_target_block_index_range": [
                min(pair["replacement_target_block_index"] for pair in replacement_pairs),
                max(pair["replacement_target_block_index"] for pair in replacement_pairs),
            ],
            "replacement_source_block_index_range": [
                min(pair["replacement_source_block_index"] for pair in replacement_pairs),
                max(pair["replacement_source_block_index"] for pair in replacement_pairs),
            ],
        },
        "event_control_pointer_rows": pointer_rows,
        "tile_event_chains": chains,
        "tile_event_condition_entries": event_entries,
        "tile_event_replacement_pairs": replacement_pairs,
    }


def render_markdown(contract: dict[str, Any]) -> str:
    summary = contract["summary"]
    lines = [
        "# D0 Tile Event Contracts",
        "",
        "Generated by `tools/build_d0_tile_event_contracts.py` from the byte-equivalent D0 source scaffold and the C0 tile-event consumer.",
        "",
        "## Summary",
        "",
        f"- event-control pointer rows: `{summary['pointer_rows']}`",
        f"- tile-event chains: `{summary['chains']}`",
        f"- non-empty chains: `{summary['non_empty_chains']}`",
        f"- event-condition entries: `{summary['event_condition_entries']}`",
        f"- replacement pairs: `{summary['replacement_pairs']}`",
        f"- terminal boundary: `{summary['terminal_boundary']}`",
        f"- chain event-entry histogram: `{summary['chain_event_entry_count_histogram']}`",
        f"- chain replacement-pair histogram: `{summary['chain_replacement_pair_count_histogram']}`",
        f"- expected flag-state histogram: `{summary['expected_flag_state_histogram']}`",
        "",
        "## Record Shapes",
        "",
        "`EVENT_CONTROL_PTR_TABLE` rows are low-word pointers into the D0 tile-event chain block.",
        "",
        "| Record | Offset | Field | Size | Consumer evidence |",
        "| --- | ---: | --- | ---: | --- |",
    ]
    for field in contract["record_shapes"]["event_control_pointer_row"]:
        lines.append(
            f"| `event_control_pointer_row` | `+0x{field['offset']:X}` | `{field['field']}` | {field['size']} | {field['consumer']} |"
        )
    for field in contract["record_shapes"]["tile_event_condition_header"]:
        lines.append(
            f"| `tile_event_condition_header` | `+0x{field['offset']:X}` | `{field['field']}` | {field['size']} | {field['consumer']} |"
        )
    for field in contract["record_shapes"]["tile_event_replacement_pair"]:
        lines.append(
            f"| `tile_event_replacement_pair` | `+0x{field['offset']:X}` | `{field['field']}` | {field['size']} | {field['consumer']} |"
        )

    lines.extend(
        [
            "",
            "## Chain Samples",
            "",
            "| Chain | Address | End | Event entries | Replacement pairs | Terminator |",
            "| ---: | --- | --- | ---: | ---: | --- |",
        ]
    )
    for chain in contract["tile_event_chains"]:
        if chain["event_entries"] or chain["chain_id"] in {0, len(contract["tile_event_chains"]) - 1}:
            lines.append(
                f"| {chain['chain_id']} | `{chain['address']}` | `{chain['end_exclusive']}` | "
                f"{chain['event_entries']} | {chain['replacement_pairs']} | `{chain['terminator']}` |"
            )

    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- `event_flag_condition_word & 0x7FFF` is the event flag id tested through `C2:1628`; bit 15 selects the expected flag state.",
            "- Replacement pairs are named from the `REPLACE_BLOCK` call convention only: target block index first, source block index second.",
            "- This pass does not assign human map-event names to individual chains, flags, or replacement pairs.",
            "",
            "## Evidence",
            "",
            "- `notes/d0-table-splits.md` pins the `EVENT_CONTROL_PTR_TABLE` and `MAP_TILE_EVENT_CONTROL_TABLE` spans.",
            "- `src/c0/c0_062a_load_landing_hdma_dispatch_block.asm` indexes `D0:1598`, walks the chain records, calls `C2:1628`, and applies replacement pairs through `REPLACE_BLOCK`.",
            "- `notes/d0-tile-event-contracts.json` carries the complete decoded pointer rows, chains, condition headers, and replacement pairs.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build D0 tile-event chain contracts.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN_OUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    contract = build_contract(args.source)
    args.json_out.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    args.markdown_out.write_text(render_markdown(contract), encoding="utf-8")
    print(f"Wrote {args.json_out} and {args.markdown_out}")


if __name__ == "__main__":
    main()
