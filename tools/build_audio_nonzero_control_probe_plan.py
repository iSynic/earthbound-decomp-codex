#!/usr/bin/env python3
"""Build targeted runtime probe jobs for non-0x00 control commands."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FRONTIER = ROOT / "manifests" / "audio-nonzero-control-semantics-frontier.json"
DEFAULT_ORACLE_PLAN = ROOT / "manifests" / "audio-oracle-comparison-plan-all-tracks.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-nonzero-control-probe-plan.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-nonzero-control-probe-plan.md"
DEFAULT_OUTPUT_ROOT = "build/audio/nonzero-control-probe"

REQUIRED_CAPTURE_FIELDS = [
    "sequence_read_trace",
    "track_id",
    "track_name",
    "command",
    "reader_pc",
    "sequence_address",
    "instruction",
    "registers.ya",
    "registers.x",
    "registers.s",
    "registers.p",
    "command_pointer_registers.dp_10_11",
    "command_pointer_registers.dp_12_13",
    "post_read_pc",
    "post_read_branch_or_effect",
    "voice_slot_state",
    "phrase_or_subroutine_stack_state",
    "timing_counter_state",
    "tempo_or_fast_forward_state",
    "control_effect_classification",
    "classification_evidence",
]

CLASSIFICATIONS = [
    "ef_call_return",
    "timing_toggle",
    "earthbound_variant_ff",
    "unreachable",
    "unresolved",
]

COMMAND_QUESTIONS = {
    "0xEF": "Does EF establish call/return state that changes end-vs-return duration decisions?",
    "0xFD": "Does FD change fast-forward/timing state in a way exact duration math must model?",
    "0xFE": "Does FE restore fast-forward/timing state in a way exact duration math must model?",
    "0xFF": "Is FF an EarthBound-specific control effect, unreachable data, or a static-walk blocker only?",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the audio non-0x00 control probe plan.")
    parser.add_argument("--frontier", default=str(DEFAULT_FRONTIER), help="Nonzero control frontier JSON.")
    parser.add_argument("--oracle-plan", default=str(DEFAULT_ORACLE_PLAN), help="All-track oracle plan JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Probe plan output JSON.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Probe plan markdown output.")
    parser.add_argument(
        "--output-root",
        default=DEFAULT_OUTPUT_ROOT,
        help="Ignored probe output root. Defaults to build/audio/nonzero-control-probe.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def slug(text: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")


def oracle_jobs_by_track(oracle_plan: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {int(job["track_id"]): job for job in oracle_plan.get("jobs", [])}


def source_record(oracle_job: dict[str, Any]) -> dict[str, Any]:
    return {
        "oracle_job_id": oracle_job.get("job_id"),
        "source_state": oracle_job.get("source_state"),
        "source_spc": oracle_job.get("source_spc", {}),
        "source_render": oracle_job.get("source_render", {}),
    }


def fallback_track_ids(frontier: dict[str, Any], command: str) -> list[int]:
    ids: list[int] = []
    for pack in frontier.get("priority_packs", []):
        if command == "0xFF" and int(pack.get("blocker_counts", {}).get("0xFF", 0)) <= 0:
            continue
        for track_id in pack.get("track_ids", []):
            if int(track_id) not in ids:
                ids.append(int(track_id))
        if len(ids) >= 8:
            break
    return ids[:8]


def source_candidates(
    frontier: dict[str, Any],
    reader_record: dict[str, Any],
    command: str,
    oracle_by_track: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    ordered_track_ids: list[int] = []
    sample_records: dict[int, dict[str, Any]] = {}
    for sample in reader_record.get("sample_reads", []):
        track_id = int(sample["track_id"])
        if track_id not in ordered_track_ids:
            ordered_track_ids.append(track_id)
        sample_records[track_id] = sample
    for track_id in fallback_track_ids(frontier, command):
        if track_id not in ordered_track_ids:
            ordered_track_ids.append(track_id)
    candidates = []
    for track_id in ordered_track_ids[:8]:
        oracle_job = oracle_by_track.get(track_id)
        sample = sample_records.get(track_id, {})
        candidates.append(
            {
                "track_id": track_id,
                "track_name": sample.get("track_name", oracle_job.get("track_name") if oracle_job else None),
                "sample_sequence_address": sample.get("sequence_address"),
                "sample_instruction": sample.get("instruction"),
                "sample_registers": sample.get("registers"),
                "sample_command_pointer_registers": sample.get("command_pointer_registers"),
                "source": source_record(oracle_job) if oracle_job else None,
            }
        )
    return candidates


def probe_outputs(job_id: str, output_root: str) -> dict[str, str]:
    root = f"{output_root.rstrip('/')}/{job_id}"
    return {
        "root": root,
        "raw_trace": f"{root}/nonzero-control-trace.jsonl",
        "result_json": f"{root}/nonzero-control-proof-result.json",
        "evidence_markdown": f"{root}/nonzero-control-proof.md",
    }


def priority_rank(command: str, pc: str) -> int:
    if pc == "0x0957" and command == "0xFF":
        return 100
    if pc == "0x0957":
        return 90
    if command == "0xEF":
        return 70
    if command in {"0xFD", "0xFE"}:
        return 60
    return 50


def build_jobs(frontier: dict[str, Any], oracle_plan: dict[str, Any], output_root: str) -> list[dict[str, Any]]:
    oracle_by_track = oracle_jobs_by_track(oracle_plan)
    jobs: list[dict[str, Any]] = []
    for command_record in frontier.get("command_frontier", []):
        command = str(command_record["command"])
        for reader in command_record.get("reader_pc_records", []):
            pc = str(reader["pc"])
            job_id = f"nonzero-probe-{command.lower().replace('0x', '')}-pc-{pc.lower().replace('0x', '')}"
            jobs.append(
                {
                    "job_id": job_id,
                    "command": command,
                    "reader_pc": pc,
                    "driver_offset": reader.get("driver_offset"),
                    "read_count": int(reader.get("read_count", 0)),
                    "affected_kind": command_record.get("affected_kind"),
                    "semantic_status": command_record.get("semantic_status"),
                    "static_dispatch_target": command_record.get("static_dispatch_target"),
                    "priority_rank": priority_rank(command, pc),
                    "priority_reason": command_record.get("priority_reason"),
                    "promotion_question": COMMAND_QUESTIONS[command],
                    "source_candidates": source_candidates(frontier, reader, command, oracle_by_track),
                    "required_capture_fields": REQUIRED_CAPTURE_FIELDS,
                    "accepted_control_effect_classifications": CLASSIFICATIONS,
                    "success_criteria": [
                        "capture at least one matching command read at the targeted reader PC or explain why the source state cannot reach it",
                        "record command pointer, post-read PC/branch, channel/voice state, and stack/timing state as applicable",
                        "classify the command effect as ef_call_return, timing_toggle, earthbound_variant_ff, unreachable, or unresolved",
                        "leave sequence-derived public exact-duration promotion blocked unless a later command-semantics validator consumes this evidence",
                    ],
                    "probe_outputs": probe_outputs(job_id, output_root),
                    "promotion_allowed_by_plan": False,
                }
            )
    jobs.sort(key=lambda item: (int(item["priority_rank"]), int(item["read_count"])), reverse=True)
    return jobs


def count_jobs(jobs: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for job in jobs:
        counts[str(job.get(key))] += 1
    return dict(sorted(counts.items()))


def build_plan(frontier: dict[str, Any], oracle_plan: dict[str, Any], output_root: str) -> dict[str, Any]:
    jobs = build_jobs(frontier, oracle_plan, output_root)
    source_candidate_count = sum(len(job.get("source_candidates", [])) for job in jobs)
    source_join_count = sum(
        1
        for job in jobs
        for candidate in job.get("source_candidates", [])
        if candidate.get("source")
    )
    return {
        "schema": "earthbound-decomp.audio-nonzero-control-probe-plan.v1",
        "status": "nonzero_control_probe_jobs_ready_runner_extension_pending",
        "references": [
            "manifests/audio-nonzero-control-semantics-frontier.json",
            "manifests/audio-duration-uncertainty-register.json",
            "manifests/audio-sequence-command-semantics.json",
            "manifests/audio-oracle-comparison-plan-all-tracks.json",
        ],
        "source_policy": {
            "requires_user_supplied_rom": True,
            "generated_probe_outputs_are_ignored": True,
            "generated_outputs_root": output_root,
            "do_not_distribute_reference_spc_wav_or_rom_derived_audio": True,
        },
        "summary": {
            "job_count": len(jobs),
            "command_job_counts": count_jobs(jobs, "command"),
            "reader_pc_job_counts": count_jobs(jobs, "reader_pc"),
            "affected_kind_job_counts": count_jobs(jobs, "affected_kind"),
            "source_candidate_count": source_candidate_count,
            "source_candidate_with_oracle_job_count": source_join_count,
            "frontier_track_count": int(frontier.get("summary", {}).get("track_count", 0)),
            "frontier_pack_count": int(frontier.get("summary", {}).get("pack_count", 0)),
            "sequence_promotion_allowed": False,
            "semantic_status": "nonzero_command_effect_probe_outputs_pending",
        },
        "runner_contract": {
            "harness_target": "future zero/nonzero-capable ares audio harness external mode",
            "behavior_change_allowed": False,
            "public_exact_promotion_allowed": False,
            "required_capture_fields": REQUIRED_CAPTURE_FIELDS,
            "accepted_control_effect_classifications": CLASSIFICATIONS,
            "result_schema_required_fields": [
                "job_id",
                "command",
                "reader_pc",
                "control_effect_classification",
                "reader_pc_observations",
                "state_effect_observations",
                "promotion_allowed_by_result",
            ],
            "independent_oracle_scope": (
                "This probe proves sequence-control semantics only; release-quality playback still depends on the independent emulator oracle plan."
            ),
        },
        "jobs": jobs,
        "promotion_policy": [
            "This plan creates diagnostic jobs only and cannot promote sequence-derived public exact-duration exports.",
            "0xFF remains a static-walk blocker until EarthBound reader-path effect is locally classified.",
            "EF evidence must describe call/return state, not just command reads.",
            "FD/FE evidence must describe timing or tempo state before exact duration math can depend on it.",
        ],
        "next_work": [
            "run the 0x0957 FF/FE/EF jobs first because that reader PC spans the highest-value command mix",
            "add a nonzero control result validator/collector after the harness writes real effect classifications",
            "feed only validated command effects back into audio-sequence-command-semantics",
        ],
    }


def render_markdown(plan: dict[str, Any]) -> str:
    summary = plan["summary"]
    rows = [
        "| `{job_id}` | `{command}` | `{reader_pc}` | {reads} | `{kind}` | {sources} | `{output}` |".format(
            job_id=job["job_id"],
            command=job["command"],
            reader_pc=job["reader_pc"],
            reads=job["read_count"],
            kind=job["affected_kind"],
            sources=len(job["source_candidates"]),
            output=job["probe_outputs"]["root"],
        )
        for job in plan["jobs"]
    ]
    return "\n".join(
        [
            "# Audio Nonzero Control Probe Plan",
            "",
            "Status: targeted EF/FD/FE/FF reader-PC probe jobs are planned; runtime effect proof is still pending.",
            "",
            "## Summary",
            "",
            f"- jobs: `{summary['job_count']}`",
            f"- command jobs: `{summary['command_job_counts']}`",
            f"- reader PC jobs: `{summary['reader_pc_job_counts']}`",
            f"- affected kinds: `{summary['affected_kind_job_counts']}`",
            f"- source candidates: `{summary['source_candidate_count']}`",
            f"- source candidates joined to oracle jobs: `{summary['source_candidate_with_oracle_job_count']}`",
            f"- frontier tracks: `{summary['frontier_track_count']}`",
            f"- sequence promotion allowed: `{summary['sequence_promotion_allowed']}`",
            "",
            "## Probe Contract",
            "",
            f"- harness target: `{plan['runner_contract']['harness_target']}`",
            f"- behavior change allowed: `{plan['runner_contract']['behavior_change_allowed']}`",
            f"- public exact promotion allowed: `{plan['runner_contract']['public_exact_promotion_allowed']}`",
            f"- required capture fields: `{plan['runner_contract']['required_capture_fields']}`",
            f"- accepted classifications: `{plan['runner_contract']['accepted_control_effect_classifications']}`",
            "",
            "## Jobs",
            "",
            "| Job | Command | Reader PC | Reads | Affected kind | Source candidates | Output root |",
            "| --- | --- | --- | ---: | --- | ---: | --- |",
            *rows,
            "",
            "## Promotion Policy",
            "",
            *[f"- {item}" for item in plan["promotion_policy"]],
            "",
            "## Next Work",
            "",
            *[f"- {item}" for item in plan["next_work"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    plan = build_plan(load_json(Path(args.frontier)), load_json(Path(args.oracle_plan)), args.output_root)
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(plan), encoding="utf-8")
    print(
        "Built audio nonzero control probe plan: "
        f"{plan['summary']['job_count']} jobs, "
        f"{plan['summary']['reader_pc_job_counts']}"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
