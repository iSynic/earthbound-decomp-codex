#!/usr/bin/env python3
"""Build a unified execution campaign for audio zero/nonzero probe jobs."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ZERO_PLAN = ROOT / "manifests" / "audio-zero-runtime-probe-plan.json"
DEFAULT_NONZERO_PLAN = ROOT / "manifests" / "audio-nonzero-control-probe-plan.json"
DEFAULT_INTAKE_PLAN = ROOT / "manifests" / "audio-sequence-semantics-intake-plan.json"
DEFAULT_UNCERTAINTY = ROOT / "manifests" / "audio-duration-uncertainty-register.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-probe-campaign-plan.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-probe-campaign-plan.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build audio probe campaign plan.")
    parser.add_argument("--zero-plan", default=str(DEFAULT_ZERO_PLAN), help="0x00 probe plan JSON.")
    parser.add_argument("--nonzero-plan", default=str(DEFAULT_NONZERO_PLAN), help="Non-0x00 probe plan JSON.")
    parser.add_argument("--intake-plan", default=str(DEFAULT_INTAKE_PLAN), help="Sequence semantics intake plan JSON.")
    parser.add_argument("--uncertainty", default=str(DEFAULT_UNCERTAINTY), help="Duration uncertainty register JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Campaign plan output JSON.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Campaign plan markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def zero_priority(job: dict[str, Any]) -> int:
    score = 5000
    blockers = set(job.get("pre_promotion_blockers", []))
    if "ef_return_stack_model" in blockers:
        score += 500
    action = str(job.get("post_zero_proof_action"))
    if action == "review_observed_silence_as_finite_or_transition":
        score += 220
    elif action == "decode_loop_points_before_exact_export":
        score += 180
    elif action == "classify_active_preview_before_exact_export":
        score += 140
    if job.get("trace_focus") == "trace_zero_reader_with_ef_stack_state":
        score += 80
    duration = job.get("duration_seconds")
    if isinstance(duration, int | float):
        score += max(0, 60 - min(int(duration), 60))
    return score


def zero_phase(job: dict[str, Any]) -> str:
    if job.get("pack_context_class") == "needs_ef_return_stack_model":
        return "zero-ef-return-stack"
    action = str(job.get("post_zero_proof_action"))
    if action == "decode_loop_points_before_exact_export":
        return "zero-loop-point-followup"
    if action == "classify_active_preview_before_exact_export":
        return "zero-active-preview-followup"
    return "zero-finite-transition-followup"


def nonzero_phase(job: dict[str, Any]) -> str:
    if job.get("reader_pc") == "0x0957":
        return "nonzero-0957-command-mix"
    return "nonzero-reader-coverage"


def nonzero_priority(job: dict[str, Any]) -> int:
    return 10000 + int(job.get("priority_rank", 0)) * 10 + int(job.get("read_count", 0))


def campaign_command(lane: str, job_id: str) -> str:
    if lane == "zero":
        return (
            "python tools/run_audio_zero_runtime_probe_batch.py "
            f"--job-id {job_id} --force --mode external --external "
            '<zero-probe-harness> --job "{job}" --result "{result}"'
        )
    return (
        "python tools/run_audio_nonzero_control_probe_batch.py "
        f"--job-id {job_id} --force --mode external --external "
        '<nonzero-control-probe-harness> --job "{job}" --result "{result}"'
    )


def stub_command(lane: str, job_id: str) -> str:
    if lane == "zero":
        return (
            "python tools/run_audio_zero_runtime_probe_batch.py "
            f"--job-id {job_id} --force --mode external --external "
            'python tools/audio_zero_runtime_probe_stub_harness.py --job "{job}" --result "{result}"'
        )
    return (
        "python tools/run_audio_nonzero_control_probe_batch.py "
            f"--job-id {job_id} --force --mode external --external "
            'python tools/audio_nonzero_control_probe_stub_harness.py --job "{job}" --result "{result}"'
    )


def result_validator(lane: str, result_path: str) -> str:
    if lane == "zero":
        return f"python tools/validate_audio_zero_runtime_probe_result.py {result_path}"
    return f"python tools/validate_audio_nonzero_control_probe_result.py {result_path}"


def build_zero_campaign_jobs(zero_plan: dict[str, Any]) -> list[dict[str, Any]]:
    jobs = []
    for job in zero_plan.get("jobs", []):
        lane = "zero"
        result_path = str(job.get("probe_outputs", {}).get("result_json", ""))
        jobs.append(
            {
                "campaign_job_id": f"campaign-zero-{job['job_id']}",
                "lane": lane,
                "job_id": job["job_id"],
                "phase": zero_phase(job),
                "priority_score": zero_priority(job),
                "track_id": int(job["track_id"]),
                "track_name": job["track_name"],
                "command": "0x00",
                "reader_pc": "multi",
                "trace_focus": job.get("trace_focus"),
                "post_probe_action": job.get("post_zero_proof_action"),
                "remaining_uncertainty": job.get("pre_promotion_blockers", []),
                "result_path": result_path,
                "run_command": campaign_command(lane, job["job_id"]),
                "stub_shape_command": stub_command(lane, job["job_id"]),
                "result_validator": result_validator(lane, result_path),
                "result_collector": "python tools/collect_audio_zero_runtime_probe_results.py",
                "intake_refresh": "python tools/build_audio_sequence_semantics_intake_plan.py",
                "promotion_allowed_by_campaign": False,
            }
        )
    jobs.sort(key=lambda item: (-int(item["priority_score"]), int(item["track_id"])))
    return jobs


def build_nonzero_campaign_jobs(nonzero_plan: dict[str, Any]) -> list[dict[str, Any]]:
    jobs = []
    for job in nonzero_plan.get("jobs", []):
        lane = "nonzero"
        result_path = str(job.get("probe_outputs", {}).get("result_json", ""))
        jobs.append(
            {
                "campaign_job_id": f"campaign-nonzero-{job['job_id']}",
                "lane": lane,
                "job_id": job["job_id"],
                "phase": nonzero_phase(job),
                "priority_score": nonzero_priority(job),
                "track_id": None,
                "track_name": None,
                "command": job["command"],
                "reader_pc": job["reader_pc"],
                "trace_focus": job.get("affected_kind"),
                "post_probe_action": "collect_control_effect_for_sequence_semantics",
                "remaining_uncertainty": [job.get("semantic_status")],
                "result_path": result_path,
                "run_command": campaign_command(lane, job["job_id"]),
                "stub_shape_command": stub_command(lane, job["job_id"]),
                "result_validator": result_validator(lane, result_path),
                "result_collector": "python tools/collect_audio_nonzero_control_probe_results.py",
                "intake_refresh": "python tools/build_audio_sequence_semantics_intake_plan.py",
                "promotion_allowed_by_campaign": False,
            }
        )
    jobs.sort(key=lambda item: (-int(item["priority_score"]), str(item["job_id"])))
    return jobs


def phase_order(phase: str) -> int:
    order = {
        "nonzero-0957-command-mix": 0,
        "nonzero-reader-coverage": 1,
        "zero-ef-return-stack": 2,
        "zero-finite-transition-followup": 3,
        "zero-loop-point-followup": 4,
        "zero-active-preview-followup": 5,
    }
    return order.get(phase, 99)


def build_plan(
    zero_plan: dict[str, Any],
    nonzero_plan: dict[str, Any],
    intake_plan: dict[str, Any],
    uncertainty: dict[str, Any],
) -> dict[str, Any]:
    campaign_jobs = build_nonzero_campaign_jobs(nonzero_plan) + build_zero_campaign_jobs(zero_plan)
    campaign_jobs.sort(key=lambda item: (phase_order(str(item["phase"])), -int(item["priority_score"]), str(item["job_id"])))
    for index, job in enumerate(campaign_jobs, start=1):
        job["execution_order"] = index
    phase_counts: Counter[str] = Counter(str(job["phase"]) for job in campaign_jobs)
    lane_counts: Counter[str] = Counter(str(job["lane"]) for job in campaign_jobs)
    command_counts: Counter[str] = Counter(str(job["command"]) for job in campaign_jobs)
    return {
        "schema": "earthbound-decomp.audio-probe-campaign-plan.v1",
        "status": "probe_campaign_ready_for_external_harness_runs",
        "references": [
            "manifests/audio-zero-runtime-probe-plan.json",
            "manifests/audio-nonzero-control-probe-plan.json",
            "manifests/audio-sequence-semantics-intake-plan.json",
            "manifests/audio-duration-uncertainty-register.json",
        ],
        "summary": {
            "campaign_job_count": len(campaign_jobs),
            "lane_job_counts": dict(sorted(lane_counts.items())),
            "phase_job_counts": dict(sorted(phase_counts.items())),
            "command_job_counts": dict(sorted(command_counts.items())),
            "first_phase": campaign_jobs[0]["phase"] if campaign_jobs else None,
            "first_three_job_ids": [job["job_id"] for job in campaign_jobs[:3]],
            "accepted_intake_candidate_count": int(intake_plan.get("summary", {}).get("accepted_candidate_count", 0)),
            "sequence_promotion_allowed_by_campaign": False,
            "duration_uncertainty_track_counts": uncertainty.get("summary", {}).get(
                "primary_uncertainty_track_counts",
                {},
            ),
        },
        "execution_policy": [
            "Run external harness jobs only against local user-supplied ROM-derived source artifacts.",
            "Generated result, trace, SPC, and WAV evidence must stay under ignored build/audio paths.",
            "Stub shape commands prove runner/result schemas only and never resolve semantic blockers.",
            "After any real harness run, validate the individual result, collect lane results, rebuild the intake plan, then rerun duration uncertainty validation.",
            "This campaign plan cannot directly promote sequence semantics or public exact-duration exports.",
        ],
        "post_run_validation_commands": [
            "python tools/validate_audio_zero_runtime_probe_results_summary.py",
            "python tools/validate_audio_nonzero_control_probe_results_summary.py",
            "python tools/build_audio_sequence_semantics_intake_plan.py",
            "python tools/validate_audio_sequence_semantics_intake_plan.py",
            "python tools/validate_audio_duration_uncertainty_register.py",
            "python tools/validate_audio_sequence_command_semantics.py",
        ],
        "campaign_jobs": campaign_jobs,
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    rows = [
        "| {order} | `{phase}` | `{lane}` | `{job_id}` | `{command}` | `{reader_pc}` | {score} | `{result_path}` |".format(
            order=job["execution_order"],
            phase=job["phase"],
            lane=job["lane"],
            job_id=job["job_id"],
            command=job["command"],
            reader_pc=job["reader_pc"],
            score=job["priority_score"],
            result_path=job["result_path"],
        )
        for job in data["campaign_jobs"][:30]
    ]
    return "\n".join(
        [
            "# Audio Probe Campaign Plan",
            "",
            "Status: unified zero/nonzero probe execution order is ready for external harness runs; no playback or export behavior changes.",
            "",
            "## Summary",
            "",
            f"- campaign jobs: `{summary['campaign_job_count']}`",
            f"- lane jobs: `{summary['lane_job_counts']}`",
            f"- phase jobs: `{summary['phase_job_counts']}`",
            f"- command jobs: `{summary['command_job_counts']}`",
            f"- first phase: `{summary['first_phase']}`",
            f"- first three jobs: `{summary['first_three_job_ids']}`",
            f"- accepted intake candidates: `{summary['accepted_intake_candidate_count']}`",
            f"- sequence promotion allowed by campaign: `{summary['sequence_promotion_allowed_by_campaign']}`",
            "",
            "## Execution Policy",
            "",
            *[f"- {item}" for item in data["execution_policy"]],
            "",
            "## Campaign Jobs",
            "",
            "| Order | Phase | Lane | Job | Command | Reader PC | Score | Result path |",
            "| ---: | --- | --- | --- | --- | --- | ---: | --- |",
            *rows,
            "",
            "## Post Run Validation",
            "",
            *[f"- `{command}`" for command in data["post_run_validation_commands"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    data = build_plan(
        load_json(Path(args.zero_plan)),
        load_json(Path(args.nonzero_plan)),
        load_json(Path(args.intake_plan)),
        load_json(Path(args.uncertainty)),
    )
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built audio probe campaign plan: "
        f"{data['summary']['campaign_job_count']} jobs, "
        f"first phase {data['summary']['first_phase']}"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
