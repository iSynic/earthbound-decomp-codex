from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / "src" / "d5" / "bank_d5_helpers_asar.asm"
DEFAULT_JSON_OUT = ROOT / "notes" / "d5-timed-delivery-row-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "d5-timed-delivery-row-contracts.md"
SCHEMA = "earthbound-decomp.d5-timed-delivery-row-contracts.v1"

ROW_COUNT = 10
ROW_SIZE = 0x14
EFFECTIVE_BASE = 0xF645
SOURCE_SPLIT_BASE = 0xF649

ROW_FAMILIES = {
    0: "pizza",
    1: "escargo",
    2: "escargo_alternate",
    3: "customer_a",
    4: "customer_b",
    5: "customer_c",
    6: "customer_d",
    7: "special_mach_pizza_zombie_paper",
    8: "special_escargo",
    9: "special_escargo",
}


def parse_db_bytes(text: str) -> list[int]:
    values: list[int] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("db "):
            continue
        values.extend(int(match[1:], 16) for match in re.findall(r"\$[0-9A-Fa-f]{2}", line))
    return values


def source_slice(text: str, source_name: str) -> str:
    marker = f"Source: src/d5/{source_name}"
    start = text.index(marker)
    next_source = text.find("; Source: src/d5/", start + len(marker))
    if next_source == -1:
        next_source = len(text)
    return text[start:next_source]


def word(data: list[int], offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def pointer24(data: list[int], offset: int) -> str:
    low_word = word(data, offset)
    bank = data[offset + 2]
    return f"{bank:02X}:{low_word:04X}"


def cpu(address: int) -> str:
    return f"D5:{address:04X}"


def build_contract(source_path: Path) -> dict[str, Any]:
    text = source_path.read_text(encoding="utf-8")
    initial_stats = parse_db_bytes(source_slice(text, "table_initial_stats.asm"))
    source_split = parse_db_bytes(source_slice(text, "table_timed_delivery_table.asm"))

    effective_payload = initial_stats[-4:] + source_split[: ROW_COUNT * ROW_SIZE - 4]
    source_trailing_padding = source_split[ROW_COUNT * ROW_SIZE - 4 :]
    if len(effective_payload) != ROW_COUNT * ROW_SIZE:
        raise ValueError(f"effective timed-delivery payload size mismatch: {len(effective_payload)}")
    if len(source_split) != ROW_COUNT * ROW_SIZE:
        raise ValueError(f"source timed-delivery split size mismatch: {len(source_split)}")
    if any(source_trailing_padding):
        raise ValueError("source split trailing bytes after effective controller rows are not zero")

    rows = []
    for index in range(ROW_COUNT):
        offset = index * ROW_SIZE
        row_data = effective_payload[offset : offset + ROW_SIZE]
        rows.append(
            {
                "row": index,
                "selector_byte": index + 1,
                "address": cpu(EFFECTIVE_BASE + offset),
                "family": ROW_FAMILIES[index],
                "sprite_object_descriptor": word(row_data, 0x00),
                "event_flag_gate": f"0x{word(row_data, 0x02):04X}",
                "retry_threshold": word(row_data, 0x04),
                "retry_wait_seconds": word(row_data, 0x06),
                "delivery_time": word(row_data, 0x08),
                "success_pointer": pointer24(row_data, 0x0A),
                "failure_pointer": pointer24(row_data, 0x0D),
                "enter_speed": word(row_data, 0x10),
                "exit_speed": word(row_data, 0x12),
            }
        )

    return {
        "schema": SCHEMA,
        "title": "D5 Timed Delivery Row Contracts",
        "generator": "tools/build_d5_timed_delivery_contracts.py",
        "source": str(source_path.relative_to(ROOT)),
        "summary": {
            "effective_controller_base": cpu(EFFECTIVE_BASE),
            "source_split_base": cpu(SOURCE_SPLIT_BASE),
            "source_split_starts_at_controller_offset": SOURCE_SPLIT_BASE - EFFECTIVE_BASE,
            "row_count": ROW_COUNT,
            "row_size": ROW_SIZE,
            "effective_controller_end_exclusive": cpu(EFFECTIVE_BASE + ROW_COUNT * ROW_SIZE),
            "source_split_end_exclusive": cpu(SOURCE_SPLIT_BASE + ROW_COUNT * ROW_SIZE),
            "source_split_trailing_padding_range": (
                f"{cpu(EFFECTIVE_BASE + ROW_COUNT * ROW_SIZE)}..{cpu(SOURCE_SPLIT_BASE + ROW_COUNT * ROW_SIZE)}"
            ),
            "source_split_trailing_padding_bytes": len(source_trailing_padding),
            "source_split_trailing_padding_all_zero": all(value == 0 for value in source_trailing_padding),
            "row_7_retry_pair": {
                "retry_threshold": rows[7]["retry_threshold"],
                "retry_wait_seconds": rows[7]["retry_wait_seconds"],
            },
        },
        "record_shape": [
            {"offset": 0x00, "field": "sprite_object_descriptor", "size": 2, "consumer": "EF:0EAD/EF:0EE8 pass this descriptor to C0:1E49, with placeholder fallback when zero"},
            {"offset": 0x02, "field": "event_flag_gate", "size": 2, "consumer": "EF:0EE8 tests this through C2:1628 while scanning rows"},
            {"offset": 0x04, "field": "retry_threshold", "size": 2, "consumer": "EF:0CA7 compares the row-local retry counter against this threshold"},
            {"offset": 0x06, "field": "retry_wait_seconds", "size": 2, "consumer": "EF:0D23 returns this to the 499+500_common one-second retry loop"},
            {"offset": 0x08, "field": "delivery_time", "size": 2, "consumer": "EF:0D46 seeds the row-local countdown from this field"},
            {"offset": 0x0A, "field": "success_pointer", "size": 3, "consumer": "EF:0D8D queues this far pointer as staged queue type 0x0008"},
            {"offset": 0x0D, "field": "failure_pointer", "size": 3, "consumer": "EF:0DFA queues this far pointer as staged queue type 0x000A"},
            {"offset": 0x10, "field": "enter_speed", "size": 2, "consumer": "EF:0E67 returns this for the arrival-side movement branch"},
            {"offset": 0x12, "field": "exit_speed", "size": 2, "consumer": "EF:0E8A returns this for the departure-side movement branch"},
        ],
        "rows": rows,
    }


def hex_word(value: int) -> str:
    return f"0x{value:04X}"


def render_markdown(contract: dict[str, Any]) -> str:
    summary = contract["summary"]
    lines = [
        "# D5 Timed Delivery Row Contracts",
        "",
        "Generated by `tools/build_d5_timed_delivery_contracts.py` from the byte-equivalent D5 source scaffold.",
        "",
        "## Summary",
        "",
        f"- effective controller base: `{summary['effective_controller_base']}`",
        f"- source split base: `{summary['source_split_base']}`",
        f"- source split starts at controller offset: `+0x{summary['source_split_starts_at_controller_offset']:X}`",
        f"- rows: `{summary['row_count']}` of `{summary['row_size']}` bytes",
        f"- effective controller end: `{summary['effective_controller_end_exclusive']}`",
        f"- source split end: `{summary['source_split_end_exclusive']}`",
        f"- source split trailing padding: `{summary['source_split_trailing_padding_range']}` ({summary['source_split_trailing_padding_bytes']} zero bytes)",
        "- row 7 retry pair: "
        f"`{hex_word(summary['row_7_retry_pair']['retry_threshold'])}`, "
        f"`{hex_word(summary['row_7_retry_pair']['retry_wait_seconds'])}`",
        "",
        "## Boundary Model",
        "",
        "The source-order split `TIMED_DELIVERY_TABLE` begins at `D5:F649`, four bytes into runtime row 0.",
        "The EF helper family uses `D5:F645` as the effective row base, so the first row's descriptor and flag gate live in the last four bytes of `INITIAL_STATS` by source-order boundary.",
        "The source split then carries controller rows through `D5:F70C` plus four zero bytes at `D5:F70D..D5:F710`.",
        "",
        "## Record Shape",
        "",
        "| Offset | Field | Size | Consumer evidence |",
        "| ---: | --- | ---: | --- |",
    ]
    for field in contract["record_shape"]:
        lines.append(f"| `+0x{field['offset']:X}` | `{field['field']}` | {field['size']} | {field['consumer']} |")

    lines.extend(
        [
            "",
            "## Rows",
            "",
            "| Row | Selector | Family | Sprite | Flag | Retry | Wait | Timer | Success | Failure | Enter | Exit |",
            "| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: |",
        ]
    )
    for row in contract["rows"]:
        lines.append(
            f"| {row['row']} | {row['selector_byte']} | `{row['family']}` | "
            f"`{hex_word(row['sprite_object_descriptor'])}` | `{row['event_flag_gate']}` | "
            f"`{hex_word(row['retry_threshold'])}` | `{hex_word(row['retry_wait_seconds'])}` | "
            f"`{hex_word(row['delivery_time'])}` | `{row['success_pointer']}` | "
            f"`{row['failure_pointer']}` | `{hex_word(row['enter_speed'])}` | `{hex_word(row['exit_speed'])}` |"
        )

    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- `TIMED_DELIVERY_CONTROLLER_TABLE` is the consumer-effective row contract.",
            "- `TIMED_DELIVERY_TABLE` is still useful as the exact source-order split window, but it is not row-aligned by itself.",
            "- `EF:0CA7` supports `0xFFFF` as a retry-threshold sentinel, but the observed row-7 retry pair in this scaffold is `0x00FF/0x00FF`.",
            "- Row-family labels come from the local `1F D3` row-selector note and warning-text flag crosswalk; they should not be expanded into more specific story labels without script evidence.",
            "",
            "## Evidence",
            "",
            "- `notes/d5-table-splits.md` pins the source-order split at `D5:F649..D5:F710`.",
            "- `notes/delivery-row-helpers-ef0e67-ef0ead.md` pins the EF helper field consumers at effective base `D5:F645`.",
            "- `notes/timed-delivery-controller-499-500-common.md` ties those helpers to the shared retry, success, failure, and movement phases.",
            "- `notes/timed-delivery-row-index-command-1f-d3.md` maps `1F D3` selector bytes `1..10` onto rows `0..9`.",
            "- `notes/timed-delivery-warning-text-gates.md` cross-checks row event flags against player-facing pending-service warning categories.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build D5 timed-delivery row contracts.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN_OUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    contract = build_contract(args.source)
    args.json_out.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_out.write_text(render_markdown(contract), encoding="utf-8")
    print(f"Wrote {args.json_out} and {args.markdown_out}")


if __name__ == "__main__":
    main()
