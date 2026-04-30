#!/usr/bin/env python3
"""Validate the SPC700 dispatch trace frontier manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "audio-spc700-dispatch-trace-frontier.json"
REQUIRED_CONTROL_COMMANDS = {"0x00", "0xEF", "0xFD", "0xFE", "0xFF"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the audio SPC700 dispatch trace frontier.")
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-spc700-dispatch-trace-frontier.v2", "unexpected schema")
    summary = data.get("summary", {})
    contract = data.get("trace_contract", {})
    records = data.get("records", [])
    require(contract.get("field") == "spc700_entry_execution_probe.high_command_dispatch_trace", "unexpected trace field")
    require(contract.get("sequence_read_field") == "spc700_entry_execution_probe.sequence_read_trace", "unexpected sequence trace field")
    require(contract.get("sequence_read_address_window", {}).get("start") == "0x2000", "unexpected sequence read window start")
    require(contract.get("dispatch_pc") == "0x12FD", "unexpected dispatch pc")
    require(contract.get("table_base") == "0x16C7", "unexpected table base")
    require(contract.get("ff_target_window", {}).get("start") == "0x1A81", "unexpected FF window start")
    require(summary.get("trace_record_count") == len(records), "record count mismatch")
    require(len(records) >= 5, "expected at least the sampled FF-lane representative records")
    require(summary.get("long_trace_record_count", 0) >= 1, "expected at least one long trace record")
    require(summary.get("long_trace_instruction_limit_max", 0) >= 1000000, "long trace limit was not recorded")
    total_hits = sum(int(record.get("hit_count", 0)) for record in records)
    total_sequence_reads = sum(int(record.get("sequence_read_count", 0)) for record in records)
    total_high_reads = sum(int(record.get("sequence_high_byte_read_count", 0)) for record in records)
    total_control_reads = sum(int(record.get("sequence_control_candidate_read_count", 0)) for record in records)
    total_fetch_reads = sum(int(record.get("sequence_execution_fetch_read_count", 0)) for record in records)
    total_fetch_high_reads = sum(int(record.get("sequence_execution_fetch_high_byte_read_count", 0)) for record in records)
    total_fetch_control_reads = sum(
        int(record.get("sequence_execution_fetch_control_candidate_read_count", 0)) for record in records
    )
    require(summary.get("total_hits") == total_hits, "total hit count mismatch")
    require(summary.get("total_sequence_reads") == total_sequence_reads, "total sequence read count mismatch")
    require(summary.get("total_sequence_high_byte_reads") == total_high_reads, "total high-byte read count mismatch")
    require(summary.get("total_sequence_control_candidate_reads") == total_control_reads, "total control read count mismatch")
    require(summary.get("total_sequence_execution_fetch_reads", 0) == total_fetch_reads, "fetch-like read count mismatch")
    require(
        summary.get("total_sequence_execution_fetch_high_byte_reads", 0) == total_fetch_high_reads,
        "fetch-like high-byte read count mismatch",
    )
    require(
        summary.get("total_sequence_execution_fetch_control_candidate_reads", 0) == total_fetch_control_reads,
        "fetch-like control read count mismatch",
    )
    require(total_sequence_reads > 0, "expected sequence-region reads")
    require(total_high_reads > 0, "expected high-byte sequence reads")
    require(total_control_reads > 0, "expected control-candidate sequence reads")
    require(summary.get("records_with_sequence_ff_reads", 0) >= 1, "expected at least one sampled FF sequence read")
    require("0x00" in summary.get("sequence_control_candidate_counts", {}), "expected sampled 0x00 sequence reads")
    require("0xEF" in summary.get("sequence_control_candidate_counts", {}), "expected sampled EF sequence reads")
    command_semantics = data.get("control_command_semantics", {})
    require(set(command_semantics) == REQUIRED_CONTROL_COMMANDS, "control command semantic set mismatch")
    require(summary.get("control_command_semantic_status_counts"), "missing command semantic status counts")
    for command, record in command_semantics.items():
        require(record.get("command") == command, f"{command}: command field mismatch")
        require(record.get("semantic_status"), f"{command}: missing semantic status")
        require("sequence_control_read_count" in record, f"{command}: missing sequence read count")
        require("mapped_dispatch_hit_count" in record, f"{command}: missing dispatch hit count")
        require(record.get("exact_duration_promotion_allowed") is False, f"{command}: trace frontier cannot directly promote exact duration")
    for record in records:
        require(record.get("capture_path"), "record missing capture path")
        require(record.get("instruction_limit", 0) >= 200000, "record instruction limit too low")
        require(record.get("executed_instructions", 0) > 0, "record missing executed instruction count")
        require(record.get("records_any_live_0x1f_opcode") is True, "record missing widened 0x1F trace flag")
        require(record.get("hit_count", 0) == len(record.get("hit_samples", [])) or record.get("hit_count", 0) > len(record.get("hit_samples", [])), "hit sample count invalid")
        require(record.get("sequence_read_count", 0) > 0, "record missing sequence reads")
        require(record.get("sequence_high_byte_read_count", 0) > 0, "record missing high-byte sequence reads")
        require("sequence_execution_fetch_read_count" in record, "record missing fetch-like read count")
        require("sequence_execution_fetch_control_candidate_read_count" in record, "record missing fetch-like control read count")
        require(record.get("control_candidate_read_samples") is not None, "record missing control candidate read samples")
        require(record.get("control_reader_pc_counts") is not None, "record missing control reader PC counts")
        require(record.get("sequence_first_read_samples") is not None, "record missing first sequence read samples")
        require(record.get("sequence_tail_read_samples") is not None, "record missing tail sequence read samples")
        require(record.get("command_fetch_context_samples") is not None, "record missing command fetch context samples")
    require(data.get("findings"), "missing findings")
    require(data.get("next_work"), "missing next work")


def main() -> int:
    args = parse_args()
    path = Path(args.manifest)
    data = json.loads(path.read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio SPC700 dispatch trace frontier validation OK: "
        f"{data['summary']['trace_record_count']} records, "
        f"{data['summary']['total_hits']} hits"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
