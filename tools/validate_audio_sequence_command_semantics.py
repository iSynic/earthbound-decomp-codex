#!/usr/bin/env python3
"""Validate promoted audio sequence command semantics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "audio-sequence-command-semantics.json"
REQUIRED_COMMANDS = {"0x00", "0xEF", "0xFD", "0xFE", "0xFF"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate audio sequence command semantics.")
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-sequence-command-semantics.v1", "unexpected schema")
    commands = data.get("commands", {})
    summary = data.get("summary", {})
    control_reader = data.get("control_reader_frontier", {})
    require(set(commands) == REQUIRED_COMMANDS, "control command set mismatch")
    require(
        control_reader.get("schema") == "earthbound-decomp.audio-spc700-control-reader-frontier.v1",
        "missing control reader frontier reference",
    )
    require(summary.get("control_reader_pc_count", 0) > 0, "expected control reader PC evidence")
    require(data.get("external_semantic_hypothesis", {}).get("source") == "SnesLab N-SPC Engine", "missing N-SPC semantic hypothesis")
    require(summary.get("external_semantic_family") == "n_spc", "missing N-SPC summary tag")
    require(
        not bool(summary.get("external_semantic_family_promotes_exact_duration")),
        "external N-SPC hypothesis must not directly promote exact duration",
    )
    require(int(summary.get("command_count", -1)) == len(commands), "command count mismatch")
    confirmed = 0
    pending = 0
    blocked = 0
    for command, record in commands.items():
        require(record.get("command") == command, f"{command}: command field mismatch")
        require(record.get("semantic_status"), f"{command}: missing semantic status")
        require(record.get("source_role"), f"{command}: missing source role")
        require(record.get("effect_proof_status"), f"{command}: missing effect proof status")
        require(record.get("duration_promotion_status"), f"{command}: missing duration promotion status")
        require(record.get("eligible_next_export_action"), f"{command}: missing next export action")
        require("n_spc_reference_semantics" in record, f"{command}: missing N-SPC reference semantics field")
        trace = record.get("trace_evidence", {})
        require("sequence_control_read_count" in trace, f"{command}: missing sequence read evidence")
        require("execution_fetch_control_read_count" in trace, f"{command}: missing execution fetch evidence")
        require("control_reader_pc_counts" in trace, f"{command}: missing reader PC evidence")
        require("mapped_dispatch_hit_count" in trace, f"{command}: missing dispatch hit evidence")
        policy = record.get("static_walk_policy", {})
        require("blocks_static_walk" in policy, f"{command}: missing static walk blocking policy")
        allowed = bool(record.get("exact_duration_promotion_allowed"))
        if allowed:
            confirmed += 1
            require(
                int(trace.get("mapped_dispatch_hit_count", 0)) > 0,
                f"{command}: promotion requires mapped runtime dispatch hits",
            )
            require(
                trace.get("post_dispatch_pc_counts"),
                f"{command}: promotion requires post-dispatch PC evidence",
            )
        elif str(record.get("semantic_status", "")).startswith("pending"):
            pending += 1
        else:
            blocked += 1
        if command == "0xFF":
            require(record.get("source_role") == "outside_vcmd_table", "0xFF must be outside the source-backed VCMD table")
            require(record.get("effect_proof_status") == "outside_vcmd_table", "0xFF must carry outside-VCMD effect status")
            require(record.get("source_label") is None, "0xFF must not have a source-backed VCMD label")
            require(
                not policy.get("candidate_terminator"),
                "0xFF must not be treated as a promoted/static terminator under the N-SPC hypothesis",
            )
            require("stock N-SPC" in record.get("status_reason", ""), "0xFF must cite stock N-SPC contradiction")
        if command == "0x00":
            require(record.get("source_role") == "zero_control_pending", "0x00 must use zero-control source role")
            require(record.get("effect_proof_status") == "zero_control_pending", "0x00 must remain zero-control pending")
            require(policy.get("candidate_terminator"), "0x00 should be the primary N-SPC terminator candidate")
        if command in {"0xEF", "0xFD", "0xFE"}:
            require(record.get("source_role") == "source_backed_vcmd", f"{command}: expected source-backed VCMD role")
            require(record.get("effect_proof_status") == "runtime_effect_pending", f"{command}: expected runtime effect pending")
            require(record.get("source_label", "").startswith("VCMD_"), f"{command}: missing source VCMD label")
            require(record.get("source_target") == record.get("static_dispatch_target"), f"{command}: target mismatch")
            require(isinstance(record.get("arg_length"), int), f"{command}: missing arg length")
    require(summary.get("confirmed_for_exact_duration_count") == confirmed, "confirmed count mismatch")
    require(summary.get("pending_count") == pending, "pending count mismatch")
    require(summary.get("blocked_or_contradicted_count") == blocked, "blocked count mismatch")
    require(
        bool(summary.get("release_sequence_promotion_allowed")) == any(
            bool(record.get("exact_duration_promotion_allowed")) for record in commands.values()
        ),
        "release promotion flag mismatch",
    )
    require(summary.get("source_backed_vcmd_count") == 3, "expected three source-backed control VCMDs")
    require(summary.get("zero_control_pending_count") == 1, "expected one zero-control pending command")
    require(summary.get("outside_vcmd_table_count") == 1, "expected one outside-VCMD command")
    require(data.get("promotion_policy"), "missing promotion policy")
    require(data.get("findings"), "missing findings")
    require(data.get("next_work"), "missing next work")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio sequence command semantics validation OK: "
        f"{data['summary']['command_count']} commands, "
        f"{data['summary']['confirmed_for_exact_duration_count']} confirmed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
