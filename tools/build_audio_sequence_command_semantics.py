#!/usr/bin/env python3
"""Build promoted audio sequence command semantics.

This manifest is intentionally stricter than the static frontiers. It may use
static dispatch-table evidence as context, but it only marks exact-duration
promotion as allowed when runtime dispatch/effect evidence is present.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DISPATCH_TRACE = ROOT / "manifests" / "audio-spc700-dispatch-trace-frontier.json"
DEFAULT_DRIVER_DISPATCH = ROOT / "manifests" / "audio-spc700-driver-dispatch-frontier.json"
DEFAULT_FF_TARGET_REVIEW = ROOT / "manifests" / "audio-spc700-ff-target-review.json"
DEFAULT_CONTROL_READER_FRONTIER = ROOT / "manifests" / "audio-spc700-control-reader-frontier.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-sequence-command-semantics.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-sequence-command-semantics.md"
CONTROL_COMMANDS = ("0x00", "0xEF", "0xFD", "0xFE", "0xFF")
NSPC_REFERENCE = {
    "source": "SnesLab N-SPC Engine",
    "url": "https://sneslab.net/wiki/N-SPC_Engine",
    "applicability": "PK Hack community reports EarthBound uses this N-SPC-family engine; local EarthBound runtime/disassembly proof is still required for promotion.",
    "voice_commands": {
        "0x00": "phrase_termination_or_end_of_subroutine",
        "0xEF": "subroutine",
        "0xFD": "fast_forward_on",
        "0xFE": "fast_forward_off",
        "0xFF": "invalid_stock_n_spc_vcmd",
    },
    "phrase_commands": {
        "0x00_0x00": "end_of_song",
        "0x00_0x01_to_0x7F": "jump_x_times",
        "0x00_0x80": "fast_forward_on",
        "0x00_0x81": "fast_forward_off",
        "0x00_0x82_to_0xFF": "always_jump",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build audio sequence command semantics.")
    parser.add_argument("--dispatch-trace", default=str(DEFAULT_DISPATCH_TRACE), help="Runtime dispatch trace frontier JSON.")
    parser.add_argument("--driver-dispatch", default=str(DEFAULT_DRIVER_DISPATCH), help="Static driver dispatch frontier JSON.")
    parser.add_argument("--ff-target-review", default=str(DEFAULT_FF_TARGET_REVIEW), help="FF target review JSON.")
    parser.add_argument("--control-reader-frontier", default=str(DEFAULT_CONTROL_READER_FRONTIER), help="Control reader frontier JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Manifest output JSON.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Markdown note output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def driver_entries(driver_dispatch: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries = driver_dispatch.get("high_command_dispatch_candidate", {}).get("entries", [])
    return {str(entry.get("command")): entry for entry in entries}


def post_pc_counts(records: list[dict[str, Any]], command: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for record in records:
        for hit in record.get("hit_samples", []):
            if hit.get("mapped_high_command_if_e0_base") != command:
                continue
            post_pc = hit.get("post_instruction_pc")
            if post_pc:
                counts[str(post_pc)] += 1
    return counts


def sequence_read_count(trace: dict[str, Any], command: str) -> int:
    return int(trace.get("summary", {}).get("sequence_control_candidate_counts", {}).get(command, 0))


def mapped_dispatch_count(trace: dict[str, Any], command: str) -> int:
    return int(trace.get("summary", {}).get("mapped_high_command_counts", {}).get(command, 0))


def execution_fetch_count(trace: dict[str, Any], command: str) -> int:
    return int(trace.get("summary", {}).get("sequence_execution_fetch_control_candidate_counts", {}).get(command, 0))


def control_reader_pc_counts(trace: dict[str, Any], command: str) -> Counter[str]:
    return Counter(trace.get("summary", {}).get("control_reader_pc_counts_by_command", {}).get(command, {}))


def command_status(
    command: str,
    mapped_hits: int,
    post_pcs: Counter[str],
    reader_pcs: Counter[str],
    fetch_reads: int,
    ff_target_review: dict[str, Any],
) -> tuple[str, bool, str]:
    if command == "0x00":
        return (
            "pending_earthbound_zero_control_effect_proof",
            False,
            "Stock N-SPC treats VCMD 0x00 as phrase termination/end-of-subroutine and phrase $00 $00 as end-of-song, but EarthBound exact-duration promotion still needs local effect proof.",
        )
    if command == "0xFF" and mapped_hits <= 0:
        if reader_pcs:
            return (
                "contradicted_by_stock_n_spc_pending_earthbound_variant_proof",
                False,
                "Runtime reader PCs consumed 0xFF, but stock N-SPC marks VCMD 0xFF invalid; keep as variant/unreachable evidence until EarthBound's reader effect is decoded.",
            )
        return (
            "contradicted_by_stock_n_spc_no_runtime_effect_proof",
            False,
            "Stock N-SPC marks VCMD 0xFF invalid, so static FF table shape cannot promote an exact terminator.",
        )
    if mapped_hits <= 0:
        if reader_pcs:
            return (
                "runtime_interpreter_read_observed_dispatch_decode_pending",
                False,
                "Runtime reader PCs consumed this command byte, but the reader path effect is not decoded.",
            )
        if fetch_reads > 0:
            return (
                "runtime_fetch_observed_dispatch_bridge_pending",
                False,
                "Runtime fetch-like reads observed this command byte, but no mapped dispatch/effect was captured.",
            )
        return "pending_runtime_dispatch_bridge", False, "No runtime trace has bridged a sequence command fetch to the high-command dispatch handler."
    if not post_pcs:
        return "pending_post_dispatch_pc", False, "Runtime dispatch was observed, but post-dispatch PC was not captured."
    if command == "0xFF":
        semantic_status = str(ff_target_review.get("summary", {}).get("semantic_status", "unknown"))
        if semantic_status.endswith("effect_confirmed"):
            return "confirmed_end_or_return", True, "Runtime dispatch and FF effect review confirm exact end/return behavior."
        return "pending_runtime_effect_classification", False, "Runtime dispatch reached FF, but the end/return/channel-stop effect is not confirmed."
    return "pending_runtime_effect_classification", False, "Runtime dispatch was observed, but exact control-flow effect still needs classification."


def static_walk_policy(command: str, status: str, promotion_allowed: bool) -> dict[str, Any]:
    if command == "0x00":
        return {
            "candidate_terminator": True,
            "blocks_static_walk": False,
            "terminator_promoted": promotion_allowed,
            "reason": "N-SPC-family 0x00 is the primary phrase termination/end-of-subroutine candidate; promotion waits for EarthBound-local effect proof.",
        }
    if command == "0xFF":
        return {
            "candidate_terminator": False,
            "blocks_static_walk": not promotion_allowed,
            "terminator_promoted": promotion_allowed,
            "reason": "Stock N-SPC marks VCMD 0xFF invalid, so FF is a variant/unreachable blocker until EarthBound runtime effect is proven.",
        }
    if command in {"0xFD", "0xFE"}:
        return {
            "candidate_terminator": False,
            "blocks_static_walk": False,
            "terminator_promoted": False,
            "reason": "Stock N-SPC treats FD/FE as fast-forward toggles; timing/export promotion still waits for EarthBound-local effect proof.",
        }
    return {
        "candidate_terminator": False,
        "blocks_static_walk": False,
        "terminator_promoted": False,
        "reason": "EF call edges may be recorded statically, but return/stack behavior is not exact-duration promoted.",
    }


def build_semantics(
    dispatch_trace: dict[str, Any],
    driver_dispatch: dict[str, Any],
    ff_target_review: dict[str, Any],
    control_reader_frontier: dict[str, Any],
) -> dict[str, Any]:
    entries = driver_entries(driver_dispatch)
    trace_records = dispatch_trace.get("records", [])
    commands: dict[str, dict[str, Any]] = {}
    confirmed_count = 0
    pending_count = 0
    blocked_count = 0
    for command in CONTROL_COMMANDS:
        entry = entries.get(command, {})
        post_pcs = post_pc_counts(trace_records, command)
        mapped_hits = mapped_dispatch_count(dispatch_trace, command)
        seq_reads = sequence_read_count(dispatch_trace, command)
        fetch_reads = execution_fetch_count(dispatch_trace, command)
        reader_pcs = control_reader_pc_counts(dispatch_trace, command)
        status, promotion_allowed, reason = command_status(
            command,
            mapped_hits,
            post_pcs,
            reader_pcs,
            fetch_reads,
            ff_target_review,
        )
        if promotion_allowed:
            confirmed_count += 1
        elif status.startswith("pending"):
            pending_count += 1
        else:
            blocked_count += 1
        commands[command] = {
            "command": command,
            "hypothesis": NSPC_REFERENCE["voice_commands"].get(command, entry.get("hypothesis")),
            "n_spc_reference_semantics": NSPC_REFERENCE["voice_commands"].get(command),
            "static_dispatch_target": entry.get("target"),
            "static_dispatch_target_source": "audio-spc700-driver-dispatch-frontier" if entry.get("target") else None,
            "semantic_status": status,
            "exact_duration_promotion_allowed": promotion_allowed,
            "eligible_next_export_action": (
                "allow_sequence_exact_duration_promotion"
                if promotion_allowed
                else "keep_public_exact_promotion_blocked"
            ),
            "status_reason": reason,
            "trace_evidence": {
                "sequence_control_read_count": seq_reads,
                "execution_fetch_control_read_count": fetch_reads,
                "control_reader_pc_counts": dict(sorted(reader_pcs.items())),
                "mapped_dispatch_hit_count": mapped_hits,
                "post_dispatch_pc_counts": dict(sorted(post_pcs.items())),
            },
            "static_walk_policy": static_walk_policy(command, status, promotion_allowed),
        }

    release_allowed = any(record["exact_duration_promotion_allowed"] for record in commands.values())
    return {
        "schema": "earthbound-decomp.audio-sequence-command-semantics.v1",
        "status": "runtime_command_semantics_promotion_ready" if release_allowed else "runtime_command_semantics_promotion_blocked",
        "references": [
            "https://sneslab.net/wiki/N-SPC_Engine",
            "manifests/audio-spc700-dispatch-trace-frontier.json",
            "manifests/audio-spc700-control-reader-frontier.json",
            "manifests/audio-spc700-driver-dispatch-frontier.json",
            "manifests/audio-spc700-ff-target-review.json",
            "tools/ares_audio_harness/main.cpp",
        ],
        "summary": {
            "command_count": len(commands),
            "confirmed_for_exact_duration_count": confirmed_count,
            "pending_count": pending_count,
            "blocked_or_contradicted_count": blocked_count,
            "release_sequence_promotion_allowed": release_allowed,
            "semantic_status": "promotions_require_runtime_dispatch_and_effect_evidence",
            "control_reader_pc_count": int(control_reader_frontier.get("summary", {}).get("reader_pc_count", 0)),
            "external_semantic_family": "n_spc",
            "external_semantic_family_promotes_exact_duration": False,
        },
        "external_semantic_hypothesis": NSPC_REFERENCE,
        "control_reader_frontier": {
            "schema": control_reader_frontier.get("schema"),
            "status": control_reader_frontier.get("status"),
            "summary": control_reader_frontier.get("summary", {}),
        },
        "promotion_policy": [
            "Static dispatch-table targets are evidence, not promotion authority.",
            "N-SPC family semantics are hypotheses for EarthBound, not promotion authority.",
            "0x00 is the primary terminator/end-of-subroutine candidate under N-SPC semantics, but needs local EarthBound effect proof before sequence exact-duration promotion.",
            "FF cannot promote finite exact-duration semantics from the source-backed VCMD table because that table ends at FE; stock N-SPC also marks VCMD 0xFF invalid.",
            "FD and FE are treated as fast-forward timing toggles under the N-SPC hypothesis, but public exact exports still require local timing/effect proof.",
            "Loop/held tracks require loop metadata even if a local terminator is later confirmed.",
        ],
        "commands": commands,
        "findings": [
            "The current checked-in evidence does not yet permit sequence-command exact-duration promotion.",
            "Existing PCM silence evidence may still support finite trim candidates independently of sequence-command promotion.",
            "The source-backed VCMD table and N-SPC hypothesis both shift exact finite-end work from FF toward 0x00 phrase/VCMD termination evidence.",
            "Runtime traces now identify control-byte reader PCs, but those reader paths still need effect decoding before this manifest can unblock exact sequence semantics.",
        ],
        "next_work": [
            "trace or disassemble EarthBound handling of 0x00 phrase/VCMD termination and EF return behavior",
            "decode the control reader frontier PCs, starting with 0x0957 for FF/FE/EF behavior",
            "treat FF observations as variant/unreachable evidence unless the reader path proves an EarthBound-specific effect",
            "decode FD/FE timing behavior before using fast-forward regions for exact loop or finite export decisions",
        ],
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    rows = [
        "| `{command}` | `{hypothesis}` | `{target}` | `{status}` | `{reads}` | `{hits}` | `{allowed}` | `{action}` |".format(
            command=command,
            hypothesis=record.get("hypothesis"),
            target=record.get("static_dispatch_target"),
            status=record["semantic_status"],
            reads=record["trace_evidence"]["sequence_control_read_count"],
            hits=record["trace_evidence"]["mapped_dispatch_hit_count"],
            allowed=record["exact_duration_promotion_allowed"],
            action=record["eligible_next_export_action"],
        )
        for command, record in data["commands"].items()
    ]
    return "\n".join(
        [
            "# Audio Sequence Command Semantics",
            "",
            "Status: promoted command semantics are evidence-gated; current checked-in traces do not permit sequence exact-duration promotion.",
            "",
            "## Summary",
            "",
            f"- commands: `{summary['command_count']}`",
            f"- confirmed for exact duration: `{summary['confirmed_for_exact_duration_count']}`",
            f"- pending: `{summary['pending_count']}`",
            f"- blocked or contradicted: `{summary['blocked_or_contradicted_count']}`",
            f"- sequence promotion allowed: `{summary['release_sequence_promotion_allowed']}`",
            f"- semantic status: `{summary['semantic_status']}`",
            "",
            "## Promotion Policy",
            "",
            *[f"- {item}" for item in data["promotion_policy"]],
            "",
            "## Commands",
            "",
            "| Command | Hypothesis | Static target | Semantic status | Seq reads | Dispatch hits | Promotion allowed | Next export action |",
            "| --- | --- | ---: | --- | ---: | ---: | --- | --- |",
            *rows,
            "",
            "## Findings",
            "",
            *[f"- {item}" for item in data["findings"]],
            "",
            "## Next Work",
            "",
            *[f"- {item}" for item in data["next_work"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    data = build_semantics(
        load_json(Path(args.dispatch_trace)),
        load_json(Path(args.driver_dispatch)),
        load_json(Path(args.ff_target_review)),
        load_json(Path(args.control_reader_frontier)) if Path(args.control_reader_frontier).exists() else {},
    )
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built audio sequence command semantics: "
        f"{data['summary']['command_count']} commands, "
        f"{data['summary']['confirmed_for_exact_duration_count']} confirmed"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
