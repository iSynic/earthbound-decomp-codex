from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SECTOR_CONTRACT = ROOT / "notes" / "cf-sector-list-contracts.json"
DEFAULT_DOOR_DATA_CONTRACT = ROOT / "notes" / "cf-door-data-contracts.json"
DEFAULT_JSON_OUT = ROOT / "notes" / "cf-movement-trigger-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "cf-movement-trigger-contracts.md"

SCHEMA = "earthbound-decomp.cf-movement-trigger-contracts.v1"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def cpu_address(address: str) -> int:
    bank, low_word = address.split(":")
    return (int(bank, 16) << 16) | int(low_word, 16)


def hex_word(value: int) -> str:
    return f"0x{value:04X}"


def counter_dict(counter: Counter[int]) -> dict[str, int]:
    return {str(key): counter[key] for key in sorted(counter)}


def hex_counter_dict(counter: Counter[int]) -> dict[str, int]:
    return {hex_word(key): counter[key] for key in sorted(counter)}


def door_data_targets(door_data_contract: dict[str, Any]) -> dict[tuple[int, int], dict[str, Any]]:
    targets: dict[tuple[int, int], dict[str, Any]] = {}
    for record in door_data_contract["type0_event_gated_script_pointer_records"]:
        targets[(0, record["offset"])] = {
            "record_family": "type0_event_gated_script_pointer",
            "record_index": record["record_index"],
            "target": record["script_target"],
        }
    for record in door_data_contract["type2_door_transition_records"]:
        targets[(2, record["offset"])] = {
            "record_family": "type2_door_transition_record",
            "record_index": record["record_index"],
            "target": record["address"],
            "screen_transition_config_id": record["screen_transition_config_id"],
        }
    for record in door_data_contract["type6_cached_interaction_pointer_records"]:
        targets[(6, record["offset"])] = {
            "record_family": "type6_cached_interaction_pointer",
            "record_index": record["record_index"],
            "target": record["cached_interaction_target"],
        }
    return targets


def annotate_entry(entry: dict[str, Any], targets: dict[tuple[int, int], dict[str, Any]]) -> dict[str, Any]:
    trigger_type = int(entry["movement_trigger_type"])
    payload = int(entry["trigger_payload_word"])
    base = {
        "physical_entry_index": entry["physical_entry_index"],
        "entry_index": entry["entry_index"],
        "address": entry["address"],
        "sector_index": entry["sector_index"],
        "sector": entry["sector"],
        "sector_local_x": entry["sector_local_x"],
        "sector_local_y": entry["sector_local_y"],
        "movement_trigger_type": trigger_type,
        "trigger_payload_word": payload,
    }

    if trigger_type in {0, 2, 6}:
        target = targets.get((trigger_type, payload))
        if target is None:
            raise ValueError(f"missing door-data target for trigger type {trigger_type}, payload {payload:04X}")
        field_by_type = {
            0: "type0_door_data_event_gated_script_offset",
            2: "type2_door_transition_record_offset",
            6: "type6_cached_interaction_pointer_offset",
        }
        return base | {
            "parameter_family": target["record_family"],
            field_by_type[trigger_type]: payload,
            "door_data_record_index": target["record_index"],
            "resolved_target": target["target"],
        } | ({"screen_transition_config_id": target["screen_transition_config_id"]} if trigger_type == 2 else {})

    if trigger_type == 1:
        return base | {
            "parameter_family": "type1_state07_or08_selector",
            "state08_if_nonzero_selector_word": payload,
            "selected_movement_state": 0x0007 if payload == 0 else 0x0008,
            "selector_is_nonzero": payload != 0,
        }

    if trigger_type == 3:
        resume = bool(payload & 0x8000)
        return base | {
            "parameter_family": "type3_offset_step_mode_word",
            "offset_step_mode_word": payload,
            "resume_staged_offset_step": resume,
            "offset_step_selector": None if resume else ((payload >> 8) & 0x7F),
        }

    if trigger_type == 4:
        return base | {
            "parameter_family": "type4_staged_movement_mode_word",
            "staged_movement_mode_word": payload,
            "staged_movement_selector": (payload >> 8) & 0xFF,
        }

    if trigger_type in {5, 7}:
        return base | {
            "parameter_family": "type5_or7_dispatch_no_op_payload",
            "no_op_payload_word": payload,
        }

    return base | {
        "parameter_family": "unpromoted_or_raw_trigger_payload",
        "raw_payload_word": payload,
    }


def build_contract(sector_contract_path: Path, door_data_contract_path: Path) -> dict[str, Any]:
    sector_contract = json.loads(sector_contract_path.read_text(encoding="utf-8"))
    door_data_contract = json.loads(door_data_contract_path.read_text(encoding="utf-8"))
    entries = sector_contract["door_config"]["source_order_physical_entries"]
    targets = door_data_targets(door_data_contract)
    annotated = [annotate_entry(entry, targets) for entry in entries]

    trigger_counts = Counter(row["movement_trigger_type"] for row in annotated)
    payload_unique_counts = {
        str(trigger_type): len({row["trigger_payload_word"] for row in annotated if row["movement_trigger_type"] == trigger_type})
        for trigger_type in sorted(trigger_counts)
    }
    type1_state_counts = Counter(row["selected_movement_state"] for row in annotated if row["movement_trigger_type"] == 1)
    type3_selector_counts = Counter(
        row["offset_step_selector"]
        for row in annotated
        if row["movement_trigger_type"] == 3 and row["offset_step_selector"] is not None
    )
    type4_selector_counts = Counter(row["staged_movement_selector"] for row in annotated if row["movement_trigger_type"] == 4)
    type5_payloads = sorted({row["trigger_payload_word"] for row in annotated if row["movement_trigger_type"] == 5})

    return {
        "schema": SCHEMA,
        "title": "CF Movement Trigger Contracts",
        "generator": "tools/build_cf_movement_trigger_contracts.py",
        "source_policy": (
            "Derived from the decoded CF sector-list rows, the CF door-data payload contract, "
            "and the local C0 dispatcher/helper bodies. This names the trigger payload word "
            "per movement trigger type only where C0 consumer behavior supports it."
        ),
        "sources": {
            "sector_list_contract": rel(sector_contract_path),
            "door_data_contract": rel(door_data_contract_path),
            "dispatcher": "src/c0/c0_7477_lookup_movement_trigger_type.asm",
            "type0_consumer": "src/c0/c0_6a1b_movement_trigger_type0_queue_door_destination.asm",
            "type1_consumer": "src/c0/c0_6a91_movement_trigger_type1_set_state07_or08.asm",
            "type2_consumer": "src/c0/c0_6aca_movement_trigger_type2_queue_door_transition.asm",
            "type3_consumer": "src/c0/c0_6e6e_movement_trigger_type3_queue_offset_step.asm",
            "type4_consumer": "src/c0/c0_70cb_queue_staged_movement_from_grid_coords.asm",
            "type5_consumer": "src/c0/c0_6a8b_movement_trigger_type5_or7_no_op.asm",
            "type6_probe": "src/c0/c0_65c2_probe_type6_door_candidate.asm",
        },
        "record_shapes": {
            "movement_trigger_entry": [
                {
                    "offset": 0,
                    "field": "sector_local_x",
                    "size": 1,
                    "consumer": "C0:7477 compares this byte against the low 5 bits of the input X-side coordinate",
                },
                {
                    "offset": 1,
                    "field": "sector_local_y",
                    "size": 1,
                    "consumer": "C0:7477 compares this byte against the low 5 bits of the input Y-side coordinate",
                },
                {
                    "offset": 2,
                    "field": "movement_trigger_type",
                    "size": 1,
                    "consumer": "C0:7526 dispatches this byte to type-specific movement/transition helpers",
                },
                {
                    "offset": 3,
                    "field": "trigger_payload_word",
                    "size": 2,
                    "consumer": "C0:7477 stores this word in $5DBC; the dispatcher passes it to the selected helper",
                },
            ],
            "trigger_payload_word_by_type": [
                {
                    "trigger_type": 0,
                    "field": "type0_door_data_event_gated_script_offset",
                    "consumer": "C0:6A1B masks the word to a CF DOOR_DATA offset and reads a type 0 event-gated script pointer record",
                },
                {
                    "trigger_type": 1,
                    "field": "state08_if_nonzero_selector_word",
                    "consumer": "C0:6A91 writes movement state 0x0007 when zero and 0x0008 when nonzero",
                },
                {
                    "trigger_type": 2,
                    "field": "type2_door_transition_record_offset",
                    "consumer": "C0:6ACA masks the word to a CF DOOR_DATA offset and queues it as a type 2 door-transition pointer",
                },
                {
                    "trigger_type": 3,
                    "field": "offset_step_mode_word",
                    "consumer": "C0:6E6E uses bit 15 for the resume branch and otherwise uses the high byte as a staged offset-step selector",
                },
                {
                    "trigger_type": 4,
                    "field": "staged_movement_mode_word",
                    "consumer": "C0:70CB uses the high byte as a 0..3 staged movement selector for C3:E200/E208/E210/E218/E220/E228 tables",
                },
                {
                    "trigger_type": 5,
                    "field": "no_op_payload_word",
                    "consumer": "C0:7526 passes the word to C0:6A8B, whose local body is REP #$31; RTS",
                },
                {
                    "trigger_type": 6,
                    "field": "type6_cached_interaction_pointer_offset",
                    "consumer": "C0:65C2 uses type 6 lookups to resolve a CF DOOR_DATA cached interaction pointer into $5DDE/$5DE0",
                },
            ],
        },
        "summary": {
            "source_order_physical_entries": len(annotated),
            "trigger_type_counts": counter_dict(trigger_counts),
            "payload_unique_counts_by_type": payload_unique_counts,
            "type1_selected_state_counts": hex_counter_dict(type1_state_counts),
            "type3_offset_step_selector_counts": counter_dict(type3_selector_counts),
            "type3_resume_rows": sum(1 for row in annotated if row["movement_trigger_type"] == 3 and row["resume_staged_offset_step"]),
            "type4_staged_movement_selector_counts": counter_dict(type4_selector_counts),
            "type5_unique_no_op_payloads": len(type5_payloads),
            "type5_payload_min": min(type5_payloads),
            "type5_payload_max": max(type5_payloads),
        },
        "movement_trigger_entries": annotated,
    }


def render_markdown(contract: dict[str, Any]) -> str:
    summary = contract["summary"]
    lines = [
        "# CF Movement Trigger Contracts",
        "",
        "Generated by `tools/build_cf_movement_trigger_contracts.py` from the CF sector-list and door-data contracts plus C0 helper evidence.",
        "",
        "## Summary",
        "",
        f"- source-order physical trigger rows: `{summary['source_order_physical_entries']}`",
        f"- trigger type counts: `{summary['trigger_type_counts']}`",
        f"- payload unique counts by type: `{summary['payload_unique_counts_by_type']}`",
        f"- type 1 selected movement states: `{summary['type1_selected_state_counts']}`",
        f"- type 3 offset-step selectors: `{summary['type3_offset_step_selector_counts']}`",
        f"- type 3 resume rows: `{summary['type3_resume_rows']}`",
        f"- type 4 staged-movement selectors: `{summary['type4_staged_movement_selector_counts']}`",
        f"- type 5 unique no-op payloads: `{summary['type5_unique_no_op_payloads']}`",
        "",
        "## Trigger Payload Fields",
        "",
        "| Trigger type | Field | Consumer evidence |",
        "| ---: | --- | --- |",
    ]
    for row in contract["record_shapes"]["trigger_payload_word_by_type"]:
        lines.append(f"| {row['trigger_type']} | `{row['field']}` | {row['consumer']} |")

    sample_by_type: dict[int, list[dict[str, Any]]] = {}
    for row in contract["movement_trigger_entries"]:
        sample_by_type.setdefault(row["movement_trigger_type"], [])
        if len(sample_by_type[row["movement_trigger_type"]]) < 5:
            sample_by_type[row["movement_trigger_type"]].append(row)
    lines.extend(
        [
            "",
            "## Samples",
            "",
            "| Type | Address | Sector | Payload | Interpretation |",
            "| ---: | --- | --- | ---: | --- |",
        ]
    )
    for trigger_type in sorted(sample_by_type):
        for row in sample_by_type[trigger_type]:
            detail = row["parameter_family"]
            if "resolved_target" in row:
                detail += f" -> `{row['resolved_target']}`"
            elif trigger_type == 1:
                detail += f" -> state `0x{row['selected_movement_state']:04X}`"
            elif trigger_type == 3:
                detail += " -> resume" if row["resume_staged_offset_step"] else f" -> selector `{row['offset_step_selector']}`"
            elif trigger_type == 4:
                detail += f" -> selector `{row['staged_movement_selector']}`"
            lines.append(
                f"| {trigger_type} | `{row['address']}` | `{row['sector']['x']},{row['sector']['y']}` | "
                f"`0x{row['trigger_payload_word']:04X}` | {detail} |"
            )

    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- This contract names the `trigger_payload_word` according to the helper selected by `movement_trigger_type`; it does not rename the base five-byte sector-list row.",
            "- Type `0`, `2`, and `6` payload words are CF `DOOR_DATA` offsets and join to `notes/cf-door-data-contracts.json`.",
            "- Type `1` is a state selector only: C0 proves zero selects state `0x0007` and nonzero selects state `0x0008`, but this pass does not assign gameplay labels to those states.",
            "- Type `3` and type `4` use high-byte selectors for staged movement helper tables; selector labels remain numeric.",
            "- Type `5` is intentionally left as `no_op_payload_word` because the local dispatcher passes it to a no-op body. The source bytes may be pointer-like, but this pass does not promote pointer semantics without a non-no-op consumer.",
            "",
            "## Evidence",
            "",
            "- `notes/cf-sector-list-contracts.json` supplies complete source-order physical movement-trigger rows.",
            "- `notes/cf-door-data-contracts.json` supplies the decoded type `0`, type `2`, and type `6` CF payload records.",
            "- `src/c0/c0_7477_lookup_movement_trigger_type.asm` copies `trigger_payload_word` to `$5DBC` and dispatches by type.",
            "- The type-specific C0 helper files listed in the JSON sources provide the per-type field names above.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build CF movement-trigger parameter contracts.")
    parser.add_argument("--sector-contract", type=Path, default=DEFAULT_SECTOR_CONTRACT)
    parser.add_argument("--door-data-contract", type=Path, default=DEFAULT_DOOR_DATA_CONTRACT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN_OUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    contract = build_contract(args.sector_contract, args.door_data_contract)
    args.json_out.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    args.markdown_out.write_text(render_markdown(contract), encoding="utf-8")
    print(f"Wrote {args.json_out} and {args.markdown_out}")


if __name__ == "__main__":
    main()
