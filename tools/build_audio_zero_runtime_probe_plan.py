#!/usr/bin/env python3
"""Build targeted runtime probe jobs for 0x00/EF exact-duration proof."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FRONTIER = ROOT / "manifests" / "audio-zero-ef-return-frontier.json"
DEFAULT_ORACLE_PLAN = ROOT / "manifests" / "audio-oracle-comparison-plan-all-tracks.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-zero-runtime-probe-plan.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-zero-runtime-probe-plan.md"
DEFAULT_OUTPUT_ROOT = "build/audio/zero-runtime-probe"

REQUIRED_CAPTURE_FIELDS = [
    "sequence_read_trace",
    "track_id",
    "track_name",
    "reader_pc",
    "sequence_address",
    "command",
    "instruction",
    "registers.ya",
    "registers.x",
    "registers.s",
    "registers.p",
    "command_pointer_registers.dp_10_11",
    "command_pointer_registers.dp_12_13",
    "ef_call_depth_before_zero",
    "ef_return_target_before_zero",
    "ef_call_depth_after_zero",
    "post_zero_branch_or_effect",
    "voice_slot_state",
    "zero_effect_classification",
    "classification_evidence",
]

PROMOTION_QUESTIONS = {
    "trace_zero_reader_with_ef_stack_state": (
        "Does 0x00 end the active phrase, or does EF context make it a return for this track?"
    ),
    "prove_zero_end_effect_then_review_finite_candidate": (
        "Does 0x00 produce a real finite end before the observed tail/silence review?"
    ),
    "prove_zero_effect_then_classify_active_preview": (
        "Does 0x00 explain a finite end, or is the current active preview hiding loop/hold behavior?"
    ),
    "prove_zero_effect_but_loop_points_remain_required": (
        "Does 0x00 have a proven effect while loop entry/exit metadata remains the release blocker?"
    ),
    "prove_zero_effect_for_policy_corroboration": (
        "Does 0x00 corroborate the current duration policy without changing public export behavior?"
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the audio 0x00 runtime probe plan.")
    parser.add_argument("--frontier", default=str(DEFAULT_FRONTIER), help="0x00/EF frontier JSON.")
    parser.add_argument("--oracle-plan", default=str(DEFAULT_ORACLE_PLAN), help="All-track oracle plan JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Probe plan manifest output JSON.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Probe plan markdown output.")
    parser.add_argument(
        "--output-root",
        default=DEFAULT_OUTPUT_ROOT,
        help="Ignored probe output root. Defaults to build/audio/zero-runtime-probe.",
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


def probe_outputs(job_id: str, output_root: str) -> dict[str, str]:
    root = f"{output_root.rstrip('/')}/{job_id}"
    return {
        "root": root,
        "raw_trace": f"{root}/zero-control-trace.jsonl",
        "result_json": f"{root}/zero-runtime-proof-result.json",
        "evidence_markdown": f"{root}/zero-runtime-proof.md",
    }


def reader_pc_targets(frontier: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "pc": record["pc"],
            "read_count": int(record["read_count"]),
            "driver_offset": record.get("driver_offset"),
            "role": record.get("role", "sequence_control_byte_reader_candidate"),
            "required_observation": record.get("required_observation"),
        }
        for record in frontier.get("runtime_probe_plan", {}).get("reader_pc_plan", [])
    ]


def build_jobs(frontier: dict[str, Any], oracle_plan: dict[str, Any], output_root: str) -> list[dict[str, Any]]:
    oracle_by_track = oracle_jobs_by_track(oracle_plan)
    reader_pcs = reader_pc_targets(frontier)
    jobs: list[dict[str, Any]] = []
    for pack in frontier.get("packs", []):
        trace_focus = str(pack.get("trace_focus"))
        for action in pack.get("track_review_actions", []):
            track_id = int(action["track_id"])
            track_name = str(action.get("track_name"))
            oracle_job = oracle_by_track.get(track_id)
            if oracle_job is None:
                raise ValueError(f"track {track_id}: missing all-track oracle source job")
            job_id = f"zero-probe-track-{track_id:03d}-{slug(track_name)}"
            blockers = list(action.get("pre_promotion_blockers", []))
            jobs.append(
                {
                    "job_id": job_id,
                    "track_id": track_id,
                    "track_name": track_name,
                    "pack_id": int(pack["pack_id"]),
                    "pack_track_ids": pack.get("track_ids", []),
                    "pack_context_class": pack.get("pack_context_class"),
                    "trace_focus": trace_focus,
                    "export_class": action.get("export_class"),
                    "recommended_mode": action.get("recommended_mode"),
                    "duration_seconds": action.get("duration_seconds"),
                    "pre_promotion_blockers": blockers,
                    "post_zero_proof_action": action.get("post_zero_proof_action"),
                    "promotion_question": PROMOTION_QUESTIONS.get(trace_focus, PROMOTION_QUESTIONS["prove_zero_effect_for_policy_corroboration"]),
                    "source": source_record(oracle_job),
                    "zero_static_context": {
                        "zero_terminator_candidates": int(pack.get("zero_terminator_candidates", 0)),
                        "ef_call_edges": int(pack.get("ef_call_edges", 0)),
                        "sampled_zero_walk_context_class_counts": pack.get("zero_walk_context_class_counts", {}),
                    },
                    "reader_pc_targets": [record["pc"] for record in reader_pcs],
                    "required_capture_fields": REQUIRED_CAPTURE_FIELDS,
                    "success_criteria": [
                        "capture at least one 0x00 sequence read for this track or explain why the source state cannot reach it",
                        "classify post-0x00 behavior as true_end, ef_return, loop_or_hold_continues, or unresolved",
                        "record EF call depth/return target before and after the observed 0x00 read",
                        "leave public exact-duration promotion blocked unless a later result validator consumes this evidence",
                    ],
                    "probe_outputs": probe_outputs(job_id, output_root),
                    "promotion_allowed_by_plan": False,
                }
            )
    jobs.sort(key=lambda item: (int(item["pack_id"]), int(item["track_id"])))
    return jobs


def count_jobs(jobs: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for job in jobs:
        counts[str(job.get(key))] += 1
    return dict(sorted(counts.items()))


def blocker_counts(jobs: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for job in jobs:
        for blocker in job.get("pre_promotion_blockers", []):
            counts[str(blocker)] += 1
    return dict(sorted(counts.items()))


def build_plan(frontier: dict[str, Any], oracle_plan: dict[str, Any], output_root: str) -> dict[str, Any]:
    jobs = build_jobs(frontier, oracle_plan, output_root)
    reader_pcs = reader_pc_targets(frontier)
    unique_tracks = {int(job["track_id"]) for job in jobs}
    source_oracle_job_count = sum(1 for job in jobs if job.get("source", {}).get("oracle_job_id"))
    return {
        "schema": "earthbound-decomp.audio-zero-runtime-probe-plan.v1",
        "status": "zero_runtime_probe_jobs_ready_runner_extension_pending",
        "references": [
            "manifests/audio-zero-ef-return-frontier.json",
            "manifests/audio-zero-terminator-review.json",
            "manifests/audio-oracle-comparison-plan-all-tracks.json",
            "notes/audio-zero-ef-return-frontier.md",
        ],
        "source_policy": {
            "requires_user_supplied_rom": True,
            "generated_probe_outputs_are_ignored": True,
            "generated_outputs_root": output_root,
            "do_not_distribute_reference_spc_wav_or_rom_derived_audio": True,
        },
        "summary": {
            "job_count": len(jobs),
            "unique_track_count": len(unique_tracks),
            "candidate_pack_count": int(frontier.get("summary", {}).get("candidate_pack_count", 0)),
            "source_oracle_job_count": source_oracle_job_count,
            "runtime_zero_read_count": int(frontier.get("summary", {}).get("zero_runtime_read_count", 0)),
            "reader_pc_target_count": len(reader_pcs),
            "trace_focus_job_counts": count_jobs(jobs, "trace_focus"),
            "pack_context_job_counts": count_jobs(jobs, "pack_context_class"),
            "post_zero_proof_action_job_counts": count_jobs(jobs, "post_zero_proof_action"),
            "pre_promotion_blocker_track_counts": blocker_counts(jobs),
            "sequence_promotion_allowed": False,
            "semantic_status": "job_plan_ready_zero_effect_and_ef_return_result_pending",
        },
        "runner_contract": {
            "harness_target": "tools/ares_audio_harness plus tools/run_audio_backend_batch.py external mode",
            "behavior_change_allowed": False,
            "public_exact_promotion_allowed": False,
            "required_capture_fields": REQUIRED_CAPTURE_FIELDS,
            "accepted_zero_effect_classifications": [
                "true_end",
                "ef_return",
                "loop_or_hold_continues",
                "unreachable_from_source_state",
                "unresolved",
            ],
            "result_schema_required_fields": [
                "job_id",
                "track_id",
                "source_spc_sha1",
                "zero_effect_classification",
                "reader_pc_observations",
                "ef_stack_observations",
                "promotion_allowed_by_result",
            ],
            "independent_oracle_scope": (
                "This probe proves sequence-control semantics only; release-quality playback still depends on the independent emulator oracle plan."
            ),
        },
        "reader_pc_targets": reader_pcs,
        "jobs": jobs,
        "promotion_policy": [
            "This plan creates diagnostic jobs only and cannot promote public exact-duration exports.",
            "0x00 true-end evidence must be joined with EF call/return state before finite-ending policy changes.",
            "Loop or held candidates still need loop-point metadata even when 0x00 behavior is understood.",
            "Independent emulator comparison remains a separate release gate.",
        ],
        "next_work": [
            "extend the ares audio harness trace contract to emit every required capture field",
            "run the 19 targeted zero-probe jobs into build/audio/zero-runtime-probe",
            "add a result collector/validator that feeds proven true_end or ef_return classifications back into duration triage",
        ],
    }


def render_markdown(plan: dict[str, Any]) -> str:
    summary = plan["summary"]
    pc_rows = [
        "| `{pc}` | {read_count} | `{driver_offset}` | `{role}` |".format(**record)
        for record in plan.get("reader_pc_targets", [])
    ]
    job_rows = [
        "| `{track_id:03d}` | `{track_name}` | `{pack_id}` | `{trace_focus}` | `{action}` | `{blockers}` | `{output}` |".format(
            track_id=job["track_id"],
            track_name=job["track_name"],
            pack_id=job["pack_id"],
            trace_focus=job["trace_focus"],
            action=job["post_zero_proof_action"],
            blockers=job["pre_promotion_blockers"],
            output=job["probe_outputs"]["root"],
        )
        for job in plan["jobs"]
    ]
    return "\n".join(
        [
            "# Audio 0x00 Runtime Probe Plan",
            "",
            "Status: targeted diagnostic jobs are planned; the runtime harness still needs the widened trace fields.",
            "",
            "## Summary",
            "",
            f"- probe jobs: `{summary['job_count']}`",
            f"- unique tracks: `{summary['unique_track_count']}`",
            f"- candidate packs: `{summary['candidate_pack_count']}`",
            f"- source oracle jobs joined: `{summary['source_oracle_job_count']}`",
            f"- runtime 0x00 reads already observed: `{summary['runtime_zero_read_count']}`",
            f"- reader PC targets: `{summary['reader_pc_target_count']}`",
            f"- trace focus jobs: `{summary['trace_focus_job_counts']}`",
            f"- post-zero-proof actions: `{summary['post_zero_proof_action_job_counts']}`",
            f"- blockers: `{summary['pre_promotion_blocker_track_counts']}`",
            f"- sequence promotion allowed: `{summary['sequence_promotion_allowed']}`",
            "",
            "## Probe Contract",
            "",
            f"- harness target: `{plan['runner_contract']['harness_target']}`",
            f"- behavior change allowed: `{plan['runner_contract']['behavior_change_allowed']}`",
            f"- public exact promotion allowed: `{plan['runner_contract']['public_exact_promotion_allowed']}`",
            f"- required capture fields: `{plan['runner_contract']['required_capture_fields']}`",
            f"- accepted classifications: `{plan['runner_contract']['accepted_zero_effect_classifications']}`",
            f"- independent oracle scope: {plan['runner_contract']['independent_oracle_scope']}",
            "",
            "## Reader PC Targets",
            "",
            "| Reader PC | 0x00 reads | Driver offset | Role |",
            "| --- | ---: | --- | --- |",
            *pc_rows,
            "",
            "## Jobs",
            "",
            "| Track | Name | Pack | Focus | Post-proof action | Blockers | Output root |",
            "| ---: | --- | ---: | --- | --- | --- | --- |",
            *job_rows,
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
        "Built audio 0x00 runtime probe plan: "
        f"{plan['summary']['job_count']} jobs, "
        f"{plan['summary']['reader_pc_target_count']} reader PCs"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
