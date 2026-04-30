#!/usr/bin/env python3
"""Summarize runtime traces around SPC700 indirect dispatch candidates."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BACKEND_JOBS = ROOT / "build" / "audio" / "backend-jobs"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-spc700-dispatch-trace-frontier.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-spc700-dispatch-trace-frontier.md"
TRACE_FIELD = "high_command_dispatch_trace"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the SPC700 dispatch trace frontier.")
    parser.add_argument("--backend-jobs", default=str(DEFAULT_BACKEND_JOBS), help="Backend job output directory.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Manifest output JSON.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Markdown note output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def trace_record(path: Path) -> dict[str, Any] | None:
    data = load_json(path)
    probe = data.get("spc700_entry_execution_probe", {})
    trace = probe.get(TRACE_FIELD)
    if not trace:
        return None
    sequence = probe.get("sequence_read_trace", {})
    hits = trace.get("hits", [])
    kinds = Counter(hit.get("kind", "unknown") for hit in hits)
    mapped = Counter(
        hit.get("mapped_high_command_if_e0_base")
        for hit in hits
        if hit.get("mapped_high_command_if_e0_base")
    )
    high_byte_counts = {str(key): int(value) for key, value in sequence.get("high_byte_counts", {}).items()}
    control_candidate_counts = {
        str(key): int(value)
        for key, value in sequence.get("control_candidate_counts", {}).items()
    }
    return {
        "job_id": data.get("job_id"),
        "track_id": data.get("track_id"),
        "track_name": data.get("track_name"),
        "capture_path": rel(path),
        "instruction_limit": int(probe.get("instruction_limit", 0)),
        "executed_instructions": int(probe.get("executed_instructions", 0)),
        "final_pc": probe.get("final_pc"),
        "key_on_events": int(probe.get("dsp_key_on_event_count", 0)),
        "dispatch_pc": trace.get("dispatch_pc"),
        "records_any_live_0x1f_opcode": bool(trace.get("records_any_live_0x1f_opcode")),
        "hit_count": int(trace.get("hit_count", 0)),
        "hit_kind_counts": dict(sorted(kinds.items())),
        "mapped_high_command_counts": dict(sorted(mapped.items())),
        "hit_samples": hits[:8],
        "sequence_read_count": int(sequence.get("read_count", 0)),
        "sequence_high_byte_read_count": int(sequence.get("high_byte_read_count", 0)),
        "sequence_control_candidate_read_count": int(sequence.get("control_candidate_read_count", 0)),
        "sequence_high_byte_counts": dict(sorted(high_byte_counts.items())),
        "sequence_control_candidate_counts": dict(sorted(control_candidate_counts.items())),
        "sequence_first_read_samples": sequence.get("first_reads", [])[:6],
        "sequence_tail_read_samples": sequence.get("tail_reads", [])[-6:],
    }


def build_frontier(backend_jobs: Path) -> dict[str, Any]:
    records = []
    for path in sorted(backend_jobs.glob("ares-track-*/ares-state-capture.json")):
        record = trace_record(path)
        if record is not None:
            records.append(record)

    hit_kind_counts: Counter[str] = Counter()
    command_counts: Counter[str] = Counter()
    sequence_high_counts: Counter[str] = Counter()
    sequence_control_counts: Counter[str] = Counter()
    for record in records:
        hit_kind_counts.update(record["hit_kind_counts"])
        command_counts.update(record["mapped_high_command_counts"])
        sequence_high_counts.update(record["sequence_high_byte_counts"])
        sequence_control_counts.update(record["sequence_control_candidate_counts"])

    long_runs = [record for record in records if record["instruction_limit"] > 200000]
    return {
        "schema": "earthbound-decomp.audio-spc700-dispatch-trace-frontier.v2",
        "status": "runtime_sequence_reads_observed_dispatch_hits_pending",
        "references": [
            "tools/ares_audio_harness/main.cpp",
            "manifests/audio-spc700-driver-dispatch-frontier.json",
            "manifests/audio-spc700-ff-target-review.json",
            "build/audio/backend-jobs/*/ares-state-capture.json",
        ],
        "summary": {
            "trace_record_count": len(records),
            "records_with_hits": sum(1 for record in records if record["hit_count"] > 0),
            "total_hits": sum(record["hit_count"] for record in records),
            "hit_kind_counts": dict(sorted(hit_kind_counts.items())),
            "mapped_high_command_counts": dict(sorted(command_counts.items())),
            "total_sequence_reads": sum(record["sequence_read_count"] for record in records),
            "total_sequence_high_byte_reads": sum(record["sequence_high_byte_read_count"] for record in records),
            "total_sequence_control_candidate_reads": sum(record["sequence_control_candidate_read_count"] for record in records),
            "sequence_high_byte_counts": dict(sorted(sequence_high_counts.items())),
            "sequence_control_candidate_counts": dict(sorted(sequence_control_counts.items())),
            "records_with_sequence_ff_reads": sum(
                1 for record in records if record["sequence_high_byte_counts"].get("0xFF", 0) > 0
            ),
            "long_trace_record_count": len(long_runs),
            "long_trace_instruction_limit_max": max((record["instruction_limit"] for record in long_runs), default=0),
            "semantic_status": "sequence_high_bytes_observed_but_dispatch_handler_pc_not_observed",
        },
        "trace_contract": {
            "field": "spc700_entry_execution_probe.high_command_dispatch_trace",
            "sequence_read_field": "spc700_entry_execution_probe.sequence_read_trace",
            "sequence_read_address_window": {"start": "0x2000", "end_exclusive": "0x6C00"},
            "dispatch_pc": "0x12FD",
            "table_base": "0x16C7",
            "ff_target_window": {"start": "0x1A81", "end_exclusive": "0x1ACB"},
            "hit_kinds": [
                "high_command_dispatch_source",
                "indirect_jump_opcode",
                "ff_target_window",
            ],
            "mapped_command_rule": "For high_command_dispatch_source hits, X is recorded as the table byte offset and even X values below 0x40 are mapped as 0xE0 + X/2.",
        },
        "records": records,
        "findings": [
            "The native ares audio harness now emits a bounded high-command dispatch trace block in each state capture.",
            "The native ares audio harness now also emits bounded sequence-region read traces for 0x2000..0x6BFF reads.",
            "Current sampled captures include live key-on events and thousands of sequence-region reads, including high-byte command-like values and control candidates.",
            "GAS_STATION and ONETT_INTRO both read 0xFF bytes from sequence/runtime RAM in the sampled windows, while GIVE_US_STRENGTH reads a 0xFE byte.",
            "Despite those sequence reads, current captures still record no hits at 0x12FD, no live 0x1F opcode hits, and no hits in the provisional FF target window, so the handler bridge is still missing.",
        ],
        "next_work": [
            "narrow sequence-read tracing to the actual bytecode fetch PC/state rather than broad 0x2000..0x6BFF reads",
            "run a longer or later-bound trace for one finite FF candidate such as ELEVATOR_DOWN once the all-track native job path accepts per-job instruction limits",
            "only promote FF semantics after a trace records the dispatch source, X-derived command, and post-dispatch PC/state mutation",
        ],
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    rows = [
        "| `{job}` | `{track}` | `{limit}` | `{execs}` | `{final}` | `{keyon}` | `{hits}` | `{seq}` | `{high}` | `{ctrl}` | `{controls}` |".format(
            job=record["job_id"],
            track=record["track_name"],
            limit=record["instruction_limit"],
            execs=record["executed_instructions"],
            final=record["final_pc"],
            keyon=record["key_on_events"],
            hits=record["hit_count"],
            seq=record["sequence_read_count"],
            high=record["sequence_high_byte_read_count"],
            ctrl=record["sequence_control_candidate_read_count"],
            controls=record["sequence_control_candidate_counts"],
        )
        for record in data["records"]
    ]
    return "\n".join(
        [
            "# Audio SPC700 Dispatch Trace Frontier",
            "",
            "Status: runtime trace hook present; current samples do not yet observe high-command dispatch.",
            "",
            "## Summary",
            "",
            f"- trace records: `{summary['trace_record_count']}`",
            f"- records with hits: `{summary['records_with_hits']}`",
            f"- total hits: `{summary['total_hits']}`",
            f"- total sequence reads: `{summary['total_sequence_reads']}`",
            f"- total high-byte sequence reads: `{summary['total_sequence_high_byte_reads']}`",
            f"- total control-candidate sequence reads: `{summary['total_sequence_control_candidate_reads']}`",
            f"- records with sequence FF reads: `{summary['records_with_sequence_ff_reads']}`",
            f"- long trace records: `{summary['long_trace_record_count']}`",
            f"- max long trace instruction limit: `{summary['long_trace_instruction_limit_max']}`",
            f"- semantic status: `{summary['semantic_status']}`",
            "",
            "## Trace Contract",
            "",
            f"- field: `{data['trace_contract']['field']}`",
            f"- sequence read field: `{data['trace_contract']['sequence_read_field']}`",
            f"- sequence read window: `{data['trace_contract']['sequence_read_address_window']}`",
            f"- dispatch PC: `{data['trace_contract']['dispatch_pc']}`",
            f"- table base: `{data['trace_contract']['table_base']}`",
            f"- FF target window: `{data['trace_contract']['ff_target_window']}`",
            f"- mapped command rule: {data['trace_contract']['mapped_command_rule']}",
            "",
            "## Records",
            "",
            "| Job | Track | Limit | Executed | Final PC | Key-ons | Dispatch hits | Seq reads | High reads | Control reads | Control counts |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
            *rows,
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
    data = build_frontier(Path(args.backend_jobs))
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built audio SPC700 dispatch trace frontier: "
        f"{data['summary']['trace_record_count']} records, "
        f"{data['summary']['total_hits']} hits"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
