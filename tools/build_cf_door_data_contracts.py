from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CF_SOURCE = ROOT / "src" / "cf" / "bank_cf_helpers_asar.asm"
DEFAULT_SECTOR_CONTRACT = ROOT / "notes" / "cf-sector-list-contracts.json"
DEFAULT_JSON_OUT = ROOT / "notes" / "cf-door-data-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "cf-door-data-contracts.md"

SCHEMA = "earthbound-decomp.cf-door-data-contracts.v1"
DOOR_DATA_START = 0x0000
DOOR_DATA_END = 0x264F
TYPE0_RECORD_SIZE = 6
TYPE2_RECORD_SIZE = 0x0B
TYPE6_RECORD_SIZE = 4


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


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


def pointer_target(low_word: int, bank_word: int) -> str | None:
    if low_word == 0 and bank_word == 0:
        return None
    return cpu(bank_word & 0xFF, low_word)


def event_condition(word_value: int) -> dict[str, Any]:
    return {
        "event_flag_condition_word": word_value,
        "event_flag_id": None if word_value == 0 else word_value & 0x7FFF,
        "expected_flag_state": None if word_value == 0 else (1 if word_value & 0x8000 else 0),
        "is_unconditional": word_value == 0,
    }


def counter_dict(counter: Counter[int]) -> dict[str, int]:
    return {str(key): counter[key] for key in sorted(counter)}


def hex_counter_dict(counter: Counter[int]) -> dict[str, int]:
    return {f"0x{key:04X}": counter[key] for key in sorted(counter)}


def references_by_type(entries: list[dict[str, Any]]) -> dict[int, dict[int, list[dict[str, Any]]]]:
    by_type: dict[int, dict[int, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for entry in entries:
        trigger_type = int(entry["movement_trigger_type"])
        payload = int(entry["trigger_payload_word"])
        by_type[trigger_type][payload].append(
            {
                "physical_entry_index": entry.get("physical_entry_index"),
                "entry_index": entry["entry_index"],
                "sector_index": entry["sector_index"],
                "sector": entry["sector"],
                "sector_local_x": entry["sector_local_x"],
                "sector_local_y": entry["sector_local_y"],
                "address": entry["address"],
            }
        )
    return by_type


def parse_type0_records(data: list[int], refs: dict[int, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    records = []
    for record_index, offset in enumerate(sorted(refs)):
        if offset + TYPE0_RECORD_SIZE > DOOR_DATA_END:
            raise ValueError(f"type 0 door-data record at {offset:04X} exceeds CF door-data block")
        flag_word = word(data, offset)
        low_word = word(data, offset + 2)
        bank_word = word(data, offset + 4)
        records.append(
            {
                "record_index": record_index,
                "address": cpu(0xCF, offset),
                "offset": offset,
                **event_condition(flag_word),
                "script_pointer_low_word": low_word,
                "script_pointer_bank_word": bank_word,
                "script_target": pointer_target(low_word, bank_word),
                "source_order_reference_count": len(refs[offset]),
                "referencing_physical_entry_indices": [ref["physical_entry_index"] for ref in refs[offset]],
                "sample_references": refs[offset][:8],
            }
        )
    return records


def parse_type2_records(data: list[int], refs: dict[int, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    records = []
    for record_index, offset in enumerate(sorted(refs)):
        if offset + TYPE2_RECORD_SIZE > DOOR_DATA_END:
            raise ValueError(f"type 2 door-transition record at {offset:04X} exceeds CF door-data block")
        script_low = word(data, offset)
        script_bank = word(data, offset + 2)
        flag_word = word(data, offset + 4)
        y_word = word(data, offset + 6)
        x_word = word(data, offset + 8)
        transition_config_id = data[offset + 0x0A]
        records.append(
            {
                "record_index": record_index,
                "address": cpu(0xCF, offset),
                "offset": offset,
                "pre_transition_script_pointer_low_word": script_low,
                "pre_transition_script_pointer_bank_word": script_bank,
                "pre_transition_script_target": pointer_target(script_low, script_bank),
                **event_condition(flag_word),
                "destination_y_position_word": y_word,
                "destination_y_position_units": (y_word & 0x3FFF) * 8,
                "destination_y_high_bits": y_word >> 14,
                "destination_x_position_word": x_word,
                "destination_x_position_units": x_word * 8,
                "screen_transition_config_id": transition_config_id,
                "source_order_reference_count": len(refs[offset]),
                "referencing_physical_entry_indices": [ref["physical_entry_index"] for ref in refs[offset]],
                "sample_references": refs[offset][:8],
            }
        )
    return records


def parse_type6_records(data: list[int], refs: dict[int, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    records = []
    for record_index, offset in enumerate(sorted(refs)):
        if offset + TYPE6_RECORD_SIZE > DOOR_DATA_END:
            raise ValueError(f"type 6 cached-pointer record at {offset:04X} exceeds CF door-data block")
        low_word = word(data, offset)
        bank_word = word(data, offset + 2)
        records.append(
            {
                "record_index": record_index,
                "address": cpu(0xCF, offset),
                "offset": offset,
                "cached_interaction_pointer_low_word": low_word,
                "cached_interaction_pointer_bank_word": bank_word,
                "cached_interaction_target": pointer_target(low_word, bank_word),
                "source_order_reference_count": len(refs[offset]),
                "referencing_physical_entry_indices": [ref["physical_entry_index"] for ref in refs[offset]],
                "sample_references": refs[offset][:8],
            }
        )
    return records


def build_contract(cf_source: Path, sector_contract_path: Path) -> dict[str, Any]:
    data = parse_db_bytes(source_slice(cf_source.read_text(encoding="utf-8"), "src/cf/table_door_data.asm"))
    if len(data) != DOOR_DATA_END - DOOR_DATA_START:
        raise ValueError(f"unexpected CF door-data byte count: {len(data)}")

    sector_contract = json.loads(sector_contract_path.read_text(encoding="utf-8"))
    physical_entries = sector_contract["door_config"]["source_order_physical_entries"]
    logical_entries = sector_contract["door_config"]["logical_pointer_entries"]
    physical_refs = references_by_type(physical_entries)
    logical_refs = references_by_type(logical_entries)

    type0_records = parse_type0_records(data, physical_refs[0])
    type2_records = parse_type2_records(data, physical_refs[2])
    type6_records = parse_type6_records(data, physical_refs[6])

    def raw_only_offsets(trigger_type: int) -> list[int]:
        physical = set(physical_refs.get(trigger_type, {}))
        logical = set(logical_refs.get(trigger_type, {}))
        return sorted(logical - physical)

    type2_script_banks = Counter(record["pre_transition_script_pointer_bank_word"] for record in type2_records)
    return {
        "schema": SCHEMA,
        "title": "CF Door Data Contracts",
        "generator": "tools/build_cf_door_data_contracts.py",
        "source_policy": (
            "Derived from the byte-equivalent CF source scaffold, the decoded CF sector-list "
            "contract, and C0 movement/interaction consumers. This promotes only the type 0, "
            "type 2, and type 6 payload shapes directly read by those consumers."
        ),
        "sources": {
            "cf_source_scaffold": rel(cf_source),
            "sector_list_contract": rel(sector_contract_path),
            "type0_consumer": "src/c0/c0_6a1b_movement_trigger_type0_queue_door_destination.asm",
            "type2_consumer": "src/c0/c0_6aca_movement_trigger_type2_queue_door_transition.asm",
            "transition_consumer": "src/c0/c0_6bff_run_deferred_script_pointer_and_refresh_transition_state.asm",
            "type6_consumer": "src/c0/c0_65c2_probe_type6_door_candidate.asm",
            "queue_note": "notes/staged-movement-queue.md",
            "type6_note": "notes/type6-door-candidate-probe-65c2.md",
        },
        "spans": {
            "door_data": {
                "range": f"{cpu(0xCF, DOOR_DATA_START)}..{cpu(0xCF, DOOR_DATA_END)}",
                "bytes": DOOR_DATA_END - DOOR_DATA_START,
            }
        },
        "record_shapes": {
            "type0_event_gated_script_pointer": [
                {
                    "offset": 0,
                    "field": "event_flag_condition_word",
                    "size": 2,
                    "consumer": "C0:6A3F masks 0x7FFF for C2:1628 and bit 15 supplies the expected flag state before queueing",
                },
                {
                    "offset": 2,
                    "field": "script_pointer_low_word",
                    "size": 2,
                    "consumer": "C0:6A69 reads this low word and enqueues it as queue type 0",
                },
                {
                    "offset": 4,
                    "field": "script_pointer_bank_word",
                    "size": 2,
                    "consumer": "C0:6A6D reads this bank word for the queue payload consumed by C0:75DD/C10004",
                },
            ],
            "type2_door_transition_record": [
                {
                    "offset": 0,
                    "field": "pre_transition_script_pointer_low_word",
                    "size": 2,
                    "consumer": "C0:6C22 reads the script low word from the queued CF pointer before optional C10004 dispatch",
                },
                {
                    "offset": 2,
                    "field": "pre_transition_script_pointer_bank_word",
                    "size": 2,
                    "consumer": "C0:6C1F reads the script bank word from the queued CF pointer before optional C10004 dispatch",
                },
                {
                    "offset": 4,
                    "field": "event_flag_condition_word",
                    "size": 2,
                    "consumer": "C0:6C6B treats zero as no gate; otherwise it tests 0x7FFF through C2:1628 and bit 15 as expected state",
                },
                {
                    "offset": 6,
                    "field": "destination_y_position_word",
                    "size": 2,
                    "consumer": "C0:6D0A masks this word with 0x3FFF, scales by 8, passes it as the Y-side position, and also uses the raw word for placement direction lookup",
                },
                {
                    "offset": 8,
                    "field": "destination_x_position_word",
                    "size": 2,
                    "consumer": "C0:6CFE scales this word by 8 and passes it as the X-side position to transition/context refresh helpers",
                },
                {
                    "offset": 10,
                    "field": "screen_transition_config_id",
                    "size": 1,
                    "consumer": "C0:6CCB/C0:6DBF read this byte to select the D0:1400 screen-transition config and associated SFX/effect handling",
                },
            ],
            "type6_cached_interaction_pointer": [
                {
                    "offset": 0,
                    "field": "cached_interaction_pointer_low_word",
                    "size": 2,
                    "consumer": "C0:663F reads this low word from the type-6 CF payload and stores it in $5DDE",
                },
                {
                    "offset": 2,
                    "field": "cached_interaction_pointer_bank_word",
                    "size": 2,
                    "consumer": "C0:663C reads this bank word from the type-6 CF payload and stores it in $5DE0",
                },
            ],
        },
        "summary": {
            "door_data_bytes": len(data),
            "type0_physical_references": sum(len(refs) for refs in physical_refs[0].values()),
            "type0_unique_records": len(type0_records),
            "type2_physical_references": sum(len(refs) for refs in physical_refs[2].values()),
            "type2_unique_records": len(type2_records),
            "type6_physical_references": sum(len(refs) for refs in physical_refs[6].values()),
            "type6_unique_records": len(type6_records),
            "type2_pre_transition_script_pointer_bank_histogram": hex_counter_dict(type2_script_banks),
            "type2_unconditional_records": sum(1 for record in type2_records if record["is_unconditional"]),
            "type2_transition_config_id_histogram": counter_dict(
                Counter(record["screen_transition_config_id"] for record in type2_records)
            ),
            "type2_destination_y_high_bit_histogram": counter_dict(
                Counter(record["destination_y_high_bits"] for record in type2_records)
            ),
            "raw_pointer_only_payload_offsets": {
                str(trigger_type): [f"0x{offset:04X}" for offset in raw_only_offsets(trigger_type)]
                for trigger_type in sorted(set(logical_refs) | set(physical_refs))
                if raw_only_offsets(trigger_type)
            },
        },
        "type0_event_gated_script_pointer_records": type0_records,
        "type2_door_transition_records": type2_records,
        "type6_cached_interaction_pointer_records": type6_records,
    }


def render_markdown(contract: dict[str, Any]) -> str:
    summary = contract["summary"]
    lines = [
        "# CF Door Data Contracts",
        "",
        "Generated by `tools/build_cf_door_data_contracts.py` from the CF door-data scaffold, the decoded CF sector-list contract, and C0 movement/interaction consumers.",
        "",
        "## Summary",
        "",
        f"- door-data bytes: `{summary['door_data_bytes']}`",
        f"- type 0 physical references: `{summary['type0_physical_references']}`",
        f"- type 0 unique event-gated script records: `{summary['type0_unique_records']}`",
        f"- type 2 physical references: `{summary['type2_physical_references']}`",
        f"- type 2 unique door-transition records: `{summary['type2_unique_records']}`",
        f"- type 6 physical references: `{summary['type6_physical_references']}`",
        f"- type 6 unique cached-interaction pointer records: `{summary['type6_unique_records']}`",
        f"- type 2 unconditional records: `{summary['type2_unconditional_records']}`",
        f"- type 2 screen-transition config histogram: `{summary['type2_transition_config_id_histogram']}`",
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
            "## Samples",
            "",
            "| Family | Address | Target / position | Gate | References |",
            "| --- | --- | --- | --- | ---: |",
        ]
    )
    for record in contract["type0_event_gated_script_pointer_records"]:
        lines.append(
            f"| type 0 | `{record['address']}` | `{record['script_target']}` | "
            f"`0x{record['event_flag_condition_word']:04X}` | {record['source_order_reference_count']} |"
        )
    for record in contract["type6_cached_interaction_pointer_records"]:
        lines.append(
            f"| type 6 | `{record['address']}` | `{record['cached_interaction_target']}` | - | "
            f"{record['source_order_reference_count']} |"
        )
    for record in contract["type2_door_transition_records"][:8]:
        lines.append(
            f"| type 2 | `{record['address']}` | "
            f"`x={record['destination_x_position_units']}, y={record['destination_y_position_units']}, transition={record['screen_transition_config_id']}` | "
            f"`0x{record['event_flag_condition_word']:04X}` | {record['source_order_reference_count']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- Type `0` records are named only as event-gated script pointers because `C0:6A1B` checks the event word and queues the pointer as queue type 0.",
            "- Type `2` records are named as door-transition records because `C0:6ACA` queues the CF pointer as queue type 2 and `C0:6BFF` consumes the script pointer, event gate, destination position words, and transition config id.",
            "- Type `6` records are named only as cached interaction pointers because `C0:65C2` stores the resolved target in `$5DDE/$5DE0` and marks `$5D62 = #$FFFE`.",
            "- Type `5` offsets are not promoted here even though many are pointer-like; the local `C0:7526` dispatcher body for type `5` is a no-op, so there is not enough consumer evidence for a typed contract.",
            "- Raw pointer-consumer overlap rows from `notes/cf-sector-list-contracts.json` can expose extra type/payload combinations; this artifact records those as boundary data rather than promoting them as source-order records.",
            "",
            "## Evidence",
            "",
            "- `notes/cf-sector-list-contracts.json` supplies the source-order physical movement-trigger rows that reference these CF offsets.",
            "- `src/c0/c0_6a1b_movement_trigger_type0_queue_door_destination.asm` reads the type 0 event gate and script pointer.",
            "- `src/c0/c0_6aca_movement_trigger_type2_queue_door_transition.asm` queues type 2 CF offsets as queue type 2.",
            "- `src/c0/c0_6bff_run_deferred_script_pointer_and_refresh_transition_state.asm` reads the type 2 transition record fields.",
            "- `src/c0/c0_65c2_probe_type6_door_candidate.asm` reads type 6 cached interaction pointers.",
            "- `notes/cf-door-data-contracts.json` carries the complete decoded type 0, type 2, and type 6 record rows.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build CF door-data payload contracts.")
    parser.add_argument("--cf-source", type=Path, default=DEFAULT_CF_SOURCE)
    parser.add_argument("--sector-contract", type=Path, default=DEFAULT_SECTOR_CONTRACT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN_OUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    contract = build_contract(args.cf_source, args.sector_contract)
    args.json_out.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    args.markdown_out.write_text(render_markdown(contract), encoding="utf-8")
    print(f"Wrote {args.json_out} and {args.markdown_out}")


if __name__ == "__main__":
    main()
