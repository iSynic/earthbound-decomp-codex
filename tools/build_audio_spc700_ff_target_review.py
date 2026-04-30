#!/usr/bin/env python3
"""Build a focused static review of the provisional SPC700 FF target.

The dispatch frontier gives the FF lane a concrete address under the current
E0..FF table mapping. This script reviews that address without embedding ROM
payload bytes and, importantly, without promoting the runtime effect. The aim is
to capture why a trace/disassembly pass is still required.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import rom_tools
from build_audio_spc700_driver_dispatch_frontier import (
    extract_driver_payload,
    hex_byte,
    hex_word,
    pointer_run,
)


DEFAULT_CONTRACT = ROOT / "manifests" / "audio-pack-contracts.json"
DEFAULT_DISPATCH = ROOT / "manifests" / "audio-spc700-driver-dispatch-frontier.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-spc700-ff-target-review.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-spc700-ff-target-review.md"

CONTROL_TRANSFER_OPCODES = {
    0x1F: "jmp_abs_indexed_indirect",
    0x2F: "bra_relative",
    0x3F: "call_absolute",
    0x5F: "jmp_absolute",
    0x6F: "ret",
    0xD0: "bne_relative",
    0xF0: "beq_relative",
}
DIRECT_ABSOLUTE_CONTROL_OPCODES = {0x3F: "call_absolute", 0x5F: "jmp_absolute"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the SPC700 FF target review.")
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT), help="Audio pack contract JSON.")
    parser.add_argument("--dispatch", default=str(DEFAULT_DISPATCH), help="SPC700 driver dispatch frontier JSON.")
    parser.add_argument("--rom", help="Optional explicit EarthBound US ROM path.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Manifest output JSON.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Markdown note output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_hex_int(text: str) -> int:
    return int(text, 16)


def apu_offset(address: int, base: int, payload: bytes) -> int:
    offset = address - base
    if offset < 0 or offset >= len(payload):
        raise ValueError(f"address {hex_word(address)} is outside driver payload")
    return offset


def byte_profile(payload: bytes, base_address: int) -> dict[str, Any]:
    counts = Counter(payload)
    control_counts = Counter(CONTROL_TRANSFER_OPCODES[value] for value in payload if value in CONTROL_TRANSFER_OPCODES)
    high_command_like = sum(count for value, count in counts.items() if value >= 0xE0)
    note_or_rest_like = sum(count for value, count in counts.items() if 0x80 <= value <= 0xC9)
    duration_or_arg_like = sum(count for value, count in counts.items() if value < 0x80)
    return {
        "base_address": hex_word(base_address),
        "byte_count": len(payload),
        "zero_count": counts.get(0, 0),
        "high_command_like_count": high_command_like,
        "note_or_rest_like_count": note_or_rest_like,
        "duration_or_argument_like_count": duration_or_arg_like,
        "control_transfer_opcode_counts": dict(sorted(control_counts.items())),
        "top_bytes": [
            {"byte": hex_byte(value), "count": count}
            for value, count in counts.most_common(12)
        ],
    }


def word_references(payload: bytes, base: int, target: int) -> list[str]:
    refs = []
    lo = target & 0xFF
    hi = (target >> 8) & 0xFF
    for offset in range(len(payload) - 1):
        if payload[offset] == lo and payload[offset + 1] == hi:
            refs.append(hex_word(base + offset))
    return refs


def direct_control_refs(payload: bytes, base: int, target: int) -> list[dict[str, str]]:
    refs = []
    lo = target & 0xFF
    hi = (target >> 8) & 0xFF
    for offset in range(len(payload) - 2):
        opcode = payload[offset]
        if opcode not in DIRECT_ABSOLUTE_CONTROL_OPCODES:
            continue
        if payload[offset + 1] == lo and payload[offset + 2] == hi:
            refs.append({"address": hex_word(base + offset), "opcode": hex_byte(opcode), "kind": DIRECT_ABSOLUTE_CONTROL_OPCODES[opcode]})
    return refs


def command_entry(entries: list[dict[str, Any]], command: int) -> dict[str, Any]:
    wanted = hex_byte(command)
    for entry in entries:
        if entry.get("command") == wanted:
            return entry
    raise ValueError(f"dispatch frontier missing command {wanted}")


def build_review(contract: dict[str, Any], dispatch: dict[str, Any], rom: bytes) -> dict[str, Any]:
    driver, payload, base = extract_driver_payload(contract, rom)
    high = dispatch["high_command_dispatch_candidate"]
    entries = high["entries"]
    ff_entry = command_entry(entries, 0xFF)
    fe_entry = command_entry(entries, 0xFE)
    fd_entry = command_entry(entries, 0xFD)
    target = parse_hex_int(ff_entry["target"])
    target_offset = apu_offset(target, base, payload)

    full_run = pointer_run(payload, base, parse_hex_int(high["table_base"]), limit=64)
    ff_run_index = full_run.index(target)
    next_target = full_run[ff_run_index + 1] if ff_run_index + 1 < len(full_run) else base + len(payload)
    span = payload[target_offset:apu_offset(next_target, base, payload)]
    follow_window = payload[target_offset:min(len(payload), target_offset + 512)]
    refs = word_references(payload, base, target)
    control_refs = direct_control_refs(payload, base, target)

    profile = byte_profile(span, target)
    follow_profile = byte_profile(follow_window, target)
    classification = "ff_target_address_identified_effect_blocked_by_data_like_span"
    if profile["control_transfer_opcode_counts"]:
        classification = "ff_target_address_identified_has_local_control_transfer_static_effect_pending"

    return {
        "schema": "earthbound-decomp.audio-spc700-ff-target-review.v1",
        "status": classification,
        "references": [
            "manifests/audio-spc700-driver-dispatch-frontier.json",
            "manifests/audio-spc700-dispatch-trace-frontier.json",
            "manifests/audio-ff-terminator-review.json",
            "manifests/audio-sequence-walk-frontier.json",
        ],
        "driver": driver,
        "dispatch_context": {
            "table_base": high["table_base"],
            "source_indirect_jump_addresses": high["source_indirect_jump_addresses"],
            "mapping_assumption": "FF target uses the current E0..FF zero-based high-command table mapping from the dispatch frontier.",
            "neighbor_entries": [
                {"command": fd_entry["command"], "target": fd_entry["target"], "hypothesis": fd_entry["hypothesis"]},
                {"command": fe_entry["command"], "target": fe_entry["target"], "hypothesis": fe_entry["hypothesis"]},
                {"command": ff_entry["command"], "target": ff_entry["target"], "hypothesis": ff_entry["hypothesis"]},
            ],
        },
        "target_review": {
            "command": "0xFF",
            "target": hex_word(target),
            "next_pointer_run_target": hex_word(next_target),
            "span_byte_count": len(span),
            "word_references": refs,
            "direct_call_or_jump_references": control_refs,
            "span_profile": profile,
            "first_512_byte_profile": follow_profile,
        },
        "summary": {
            "ff_target": hex_word(target),
            "next_pointer_run_target": hex_word(next_target),
            "span_byte_count": len(span),
            "word_reference_count": len(refs),
            "direct_call_or_jump_reference_count": len(control_refs),
            "span_note_or_rest_like_count": profile["note_or_rest_like_count"],
            "span_high_command_like_count": profile["high_command_like_count"],
            "span_control_transfer_opcode_count": sum(profile["control_transfer_opcode_counts"].values()),
            "first_512_control_transfer_opcode_count": sum(follow_profile["control_transfer_opcode_counts"].values()),
            "semantic_status": classification,
        },
        "findings": [
            "The provisional FF target is only referenced as a little-endian word at the dispatch table entry; no direct CALL/JMP immediate reference to that target was found in the driver payload.",
            "The span from the FF target to the next pointer-run target is dominated by note/rest-like and high-command-like byte values, which makes static promotion to executable end/return semantics unsafe.",
            "No RET, JMP, CALL, BRA, or conditional branch marker appears in the target-to-next-pointer span or the first 512 bytes starting at the FF target under this byte-level scan.",
            "This strengthens the next task definition: capture live execution around the 0x12FD indirect dispatch and prove whether the current table mapping is executed as code, data, or a second-level sequence target.",
            "The current dispatch trace frontier records sampled sequence-region reads of FF bytes, but no 0x12FD, live 0x1F, or 0x1A81-window hits, so this remains a fetch-to-handler bridge tracing problem.",
        ],
        "next_work": [
            "instrument the SPC700 probe to record PC hits around 0x12FD, the X index used by the 0x1F dispatch, and the post-dispatch PC for a track that reaches FF",
            "if post-dispatch PC reaches 0x1A81, disassemble/trace enough live instructions to find the state mutation that ends, returns, stops, or advances the channel",
            "if runtime never jumps to 0x1A81 for FF, revise the high-command table mapping before promoting any FF terminator candidates",
        ],
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    review = data["target_review"]
    span = review["span_profile"]
    follow = review["first_512_byte_profile"]
    neighbors = data["dispatch_context"]["neighbor_entries"]
    neighbor_rows = [
        f"| `{entry['command']}` | `{entry['target']}` | `{entry['hypothesis']}` |"
        for entry in neighbors
    ]
    return "\n".join(
        [
            "# Audio SPC700 FF Target Review",
            "",
            "Status: FF target address reviewed; runtime effect still blocked pending live trace.",
            "",
            "## Summary",
            "",
            f"- FF target: `{summary['ff_target']}`",
            f"- next pointer-run target: `{summary['next_pointer_run_target']}`",
            f"- target span bytes: `{summary['span_byte_count']}`",
            f"- word references: `{summary['word_reference_count']}`",
            f"- direct CALL/JMP references: `{summary['direct_call_or_jump_reference_count']}`",
            f"- span note/rest-like bytes: `{summary['span_note_or_rest_like_count']}`",
            f"- span high-command-like bytes: `{summary['span_high_command_like_count']}`",
            f"- span control-transfer markers: `{summary['span_control_transfer_opcode_count']}`",
            f"- first-512 control-transfer markers: `{summary['first_512_control_transfer_opcode_count']}`",
            f"- semantic status: `{summary['semantic_status']}`",
            "",
            "## Dispatch Context",
            "",
            f"- table base: `{data['dispatch_context']['table_base']}`",
            f"- source indirect jump addresses: `{data['dispatch_context']['source_indirect_jump_addresses']}`",
            f"- mapping assumption: {data['dispatch_context']['mapping_assumption']}",
            "",
            "| Command | Target | Current hypothesis |",
            "| --- | ---: | --- |",
            *neighbor_rows,
            "",
            "## Target Profile",
            "",
            f"- span profile: `{span}`",
            f"- first-512 profile: `{follow}`",
            f"- word references: `{review['word_references']}`",
            f"- direct CALL/JMP references: `{review['direct_call_or_jump_references']}`",
            "",
            "## Findings",
            "",
            *[f"- {finding}" for finding in data["findings"]],
            "",
            "## Next Work",
            "",
            *[f"- {item}" for item in data["next_work"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    contract = load_json(Path(args.contract))
    dispatch = load_json(Path(args.dispatch))
    rom = rom_tools.load_rom(rom_tools.find_rom(args.rom))
    data = build_review(contract, dispatch, rom)
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built audio SPC700 FF target review: "
        f"{data['summary']['ff_target']} span {data['summary']['span_byte_count']} bytes, "
        f"status {data['summary']['semantic_status']}"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
