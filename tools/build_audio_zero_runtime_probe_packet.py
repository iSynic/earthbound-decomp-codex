#!/usr/bin/env python3
"""Build an execution packet for 0x00 runtime audio probe jobs."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "manifests" / "audio-zero-runtime-probe-plan.json"
DEFAULT_COVERAGE = ROOT / "manifests" / "audio-zero-runtime-coverage-report.json"
DEFAULT_CAMPAIGN = ROOT / "manifests" / "audio-probe-campaign-plan.json"
DEFAULT_RESULTS = ROOT / "manifests" / "audio-zero-runtime-probe-results-summary.json"
DEFAULT_NEXT_ACTIONS = ROOT / "manifests" / "audio-duration-next-actions-plan.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-zero-runtime-probe-packet.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-zero-runtime-probe-packet.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build zero-runtime probe execution packet.")
    parser.add_argument("--plan", default=str(DEFAULT_PLAN), help="0x00 runtime probe plan JSON.")
    parser.add_argument("--coverage", default=str(DEFAULT_COVERAGE), help="0x00 runtime coverage report JSON.")
    parser.add_argument("--campaign", default=str(DEFAULT_CAMPAIGN), help="Unified probe campaign plan JSON.")
    parser.add_argument("--results", default=str(DEFAULT_RESULTS), help="0x00 runtime probe results summary JSON.")
    parser.add_argument("--next-actions", default=str(DEFAULT_NEXT_ACTIONS), help="Audio duration next-actions plan JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Probe packet JSON output.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Probe packet markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def by_job_id(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(record.get("job_id")): record for record in records}


def find_next_action_lane(next_actions: dict[str, Any]) -> dict[str, Any]:
    for lane in next_actions.get("priority_lanes", []):
        if lane.get("lane_id") == "zero_runtime_probe_import":
            return lane
    return {}


def compact_source(source: dict[str, Any]) -> dict[str, Any]:
    source_spc = source.get("source_spc", {})
    source_render = source.get("source_render", {})
    return {
        "oracle_job_id": source.get("oracle_job_id"),
        "source_spc": {
            "path": source_spc.get("path"),
            "sha1": source_spc.get("sha1"),
            "bytes": source_spc.get("bytes"),
        },
        "source_render": {
            "path": source_render.get("path"),
            "sha1": source_render.get("sha1"),
            "bytes": source_render.get("bytes"),
        },
    }


def packet_record(plan_job: dict[str, Any], coverage_job: dict[str, Any], campaign_job: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    outputs = plan_job.get("probe_outputs", {})
    return {
        "execution_order": int(campaign_job["execution_order"]),
        "campaign_job_id": campaign_job["campaign_job_id"],
        "job_id": plan_job["job_id"],
        "track_id": int(plan_job["track_id"]),
        "track_name": plan_job["track_name"],
        "phase": campaign_job["phase"],
        "priority_score": int(campaign_job["priority_score"]),
        "pack_id": int(plan_job["pack_id"]),
        "pack_track_ids": plan_job.get("pack_track_ids", []),
        "pack_context_class": plan_job["pack_context_class"],
        "trace_focus": plan_job["trace_focus"],
        "export_class": plan_job["export_class"],
        "recommended_mode": plan_job["recommended_mode"],
        "duration_seconds": plan_job.get("duration_seconds"),
        "pre_promotion_blockers": plan_job.get("pre_promotion_blockers", []),
        "post_zero_proof_action": plan_job["post_zero_proof_action"],
        "promotion_question": plan_job.get("promotion_question"),
        "remaining_uncertainty": campaign_job.get("remaining_uncertainty", []),
        "source": compact_source(plan_job.get("source", {})),
        "source_spc_sha1": coverage_job.get("source_spc_sha1"),
        "zero_static_context": plan_job.get("zero_static_context", {}),
        "reader_pc_target_count": int(coverage_job.get("reader_pc_target_count", 0)),
        "reader_pc_targets": plan_job.get("reader_pc_targets", []),
        "required_capture_fields": plan_job.get("required_capture_fields", []),
        "accepted_zero_effect_classifications": [
            "true_end",
            "ef_return",
            "loop_or_hold_continues",
            "unreachable_from_source_state",
            "unresolved",
        ],
        "success_criteria": plan_job.get("success_criteria", []),
        "probe_outputs": {
            "root": outputs.get("root"),
            "raw_trace": outputs.get("raw_trace"),
            "result_json": outputs.get("result_json"),
            "evidence_markdown": outputs.get("evidence_markdown"),
        },
        "commands": {
            "campaign_dry_run": f"python tools/run_audio_probe_campaign.py --lane zero --job-id {plan_job['job_id']} --mode dry-run-stub --force",
            "campaign_stub_shape": f"python tools/run_audio_probe_campaign.py --lane zero --job-id {plan_job['job_id']} --mode stub-shape --force",
            "external_run": campaign_job.get("run_command"),
            "stub_shape": campaign_job.get("stub_shape_command"),
            "validate_result": campaign_job.get("result_validator"),
            "collect_results": campaign_job.get("result_collector"),
            "refresh_intake": campaign_job.get("intake_refresh"),
        },
        "current_result_status": {
            "result_exists": bool(result.get("result_exists")),
            "status": result.get("status"),
            "valid": bool(result.get("valid")),
            "zero_effect_classification": result.get("zero_effect_classification"),
            "remaining_blockers": result.get("remaining_blockers", []),
        },
        "promotion_allowed_by_packet": False,
        "behavior_change_allowed": False,
    }


def grouped_jobs(records: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[str(record.get(key))].append(record)
    batches: list[dict[str, Any]] = []
    for value, items in groups.items():
        items.sort(key=lambda item: int(item["execution_order"]))
        batches.append(
            {
                key: value,
                "job_count": len(items),
                "execution_orders": [int(item["execution_order"]) for item in items],
                "track_ids": [int(item["track_id"]) for item in items],
                "job_ids": [str(item["job_id"]) for item in items],
            }
        )
    return sorted(batches, key=lambda item: min(item["execution_orders"]))


def build_packet(
    plan: dict[str, Any],
    coverage: dict[str, Any],
    campaign: dict[str, Any],
    results: dict[str, Any],
    next_actions: dict[str, Any],
) -> dict[str, Any]:
    plan_jobs = by_job_id(plan.get("jobs", []))
    coverage_jobs = by_job_id(coverage.get("jobs", []))
    result_records = by_job_id(results.get("results", []))
    campaign_jobs = {
        str(job.get("job_id")): job for job in campaign.get("campaign_jobs", []) if job.get("lane") == "zero"
    }
    records = [
        packet_record(plan_jobs[job_id], coverage_jobs[job_id], campaign_jobs[job_id], result_records.get(job_id, {}))
        for job_id in campaign_jobs
    ]
    records.sort(key=lambda record: int(record["execution_order"]))
    summary = coverage.get("summary", {})
    results_summary = results.get("summary", {})
    lane = find_next_action_lane(next_actions)
    return {
        "schema": "earthbound-decomp.audio-zero-runtime-probe-packet.v1",
        "status": "zero_runtime_probe_packet_ready_external_harness_required",
        "references": [
            "manifests/audio-zero-runtime-probe-plan.json",
            "manifests/audio-zero-runtime-coverage-report.json",
            "manifests/audio-probe-campaign-plan.json",
            "manifests/audio-zero-runtime-probe-results-summary.json",
            "manifests/audio-duration-next-actions-plan.json",
        ],
        "source_plan_status": plan.get("status"),
        "source_coverage_status": coverage.get("status"),
        "source_campaign_status": campaign.get("status"),
        "source_results_status": results.get("status"),
        "source_next_action_lane": lane.get("lane_id"),
        "summary": {
            "packet_job_count": len(records),
            "blocker_track_count": int(summary.get("blocker_track_count", 0)),
            "probe_job_count": int(summary.get("probe_job_count", 0)),
            "job_track_coverage_exact": bool(summary.get("job_track_coverage_exact")),
            "candidate_pack_count": int(summary.get("candidate_pack_count", 0)),
            "runtime_zero_read_count": int(summary.get("runtime_zero_read_count", 0)),
            "reader_pc_target_count": int(summary.get("reader_pc_target_count", 0)),
            "reader_pc_target_read_counts": summary.get("reader_pc_target_read_counts", {}),
            "export_class_counts": dict(sorted(Counter(str(record["export_class"]) for record in records).items())),
            "trace_focus_job_counts": dict(sorted(Counter(str(record["trace_focus"]) for record in records).items())),
            "pack_context_job_counts": dict(sorted(Counter(str(record["pack_context_class"]) for record in records).items())),
            "post_zero_proof_action_job_counts": dict(
                sorted(Counter(str(record["post_zero_proof_action"]) for record in records).items())
            ),
            "phase_job_counts": dict(sorted(Counter(str(record["phase"]) for record in records).items())),
            "pre_promotion_blocker_counts": summary.get("pre_promotion_blocker_counts", {}),
            "result_count": int(results_summary.get("result_count", 0)),
            "valid_result_count": int(results_summary.get("valid_result_count", 0)),
            "remaining_blocker_track_counts": results_summary.get("remaining_blocker_track_counts", {}),
            "accepted_zero_effect_classifications": plan.get("runner_contract", {}).get("accepted_zero_effect_classifications", []),
            "generated_outputs_root": plan.get("source_policy", {}).get("generated_outputs_root"),
            "sequence_promotion_allowed": False,
            "public_exact_promotion_allowed": False,
            "promotion_allowed_by_packet": False,
            "behavior_change_allowed": False,
        },
        "reader_pc_targets": coverage.get("reader_pc_targets", []),
        "operator_batches": {
            "by_phase": grouped_jobs(records, "phase"),
            "by_trace_focus": grouped_jobs(records, "trace_focus"),
            "by_post_zero_proof_action": grouped_jobs(records, "post_zero_proof_action"),
            "by_pack_context_class": grouped_jobs(records, "pack_context_class"),
        },
        "probe_packet_policy": [
            "This packet is an operator checklist for external 0x00 runtime harness evidence; it does not run a real harness.",
            "Generated traces, results, SPCs, WAVs, and evidence markdown must stay under ignored build/audio paths.",
            "Dry-run and stub-shape commands prove runner/result schema only; they do not resolve zero-runtime semantics.",
            "Every job must observe the same ten reader PCs so EF-return and true-end classifications are comparable.",
            "Validated zero-effect results route to active-preview, finite/transition, or loop-point follow-up before public exact export changes.",
            "This packet cannot directly promote sequence commands, public exact durations, or release-quality playback claims.",
        ],
        "records": records,
        "post_packet_validation_commands": [
            "python tools/validate_audio_zero_runtime_probe_packet.py",
            "python tools/run_audio_probe_campaign.py --lane zero --mode dry-run-stub --force",
            "python tools/validate_audio_probe_campaign_run_summary.py",
            "python tools/run_audio_probe_campaign.py --lane zero --mode stub-shape --force",
            "python tools/validate_audio_probe_campaign_run_summary.py",
            "python tools/collect_audio_zero_runtime_probe_results.py",
            "python tools/validate_audio_zero_runtime_probe_results_summary.py",
            "python tools/build_audio_sequence_semantics_intake_plan.py",
            "python tools/validate_audio_sequence_semantics_intake_plan.py",
            "python tools/validate_audio_duration_uncertainty_register.py",
            "python tools/validate_audio_zero_runtime_coverage_report.py",
            "python tools/build_audio_duration_readiness_rollup.py",
            "python tools/validate_audio_duration_readiness_rollup.py",
        ],
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    rows = [
        "| {order} | {track:03d} | `{name}` | `{phase}` | `{focus}` | `{action}` | `{result}` |".format(
            order=record["execution_order"],
            track=record["track_id"],
            name=record["track_name"],
            phase=record["phase"],
            focus=record["trace_focus"],
            action=record["post_zero_proof_action"],
            result=record["probe_outputs"]["result_json"],
        )
        for record in data["records"]
    ]
    phase_rows = [
        "| `{phase}` | {count} | `{tracks}` |".format(
            phase=batch["phase"],
            count=batch["job_count"],
            tracks=batch["track_ids"],
        )
        for batch in data["operator_batches"]["by_phase"]
    ]
    command_rows = [f"- `{command}`" for command in data["post_packet_validation_commands"]]
    return "\n".join(
        [
            "# Audio 0x00 Runtime Probe Packet",
            "",
            "Status: 0x00 runtime probe jobs are packaged for external harness evidence; current playback/export behavior is preserved.",
            "",
            "## Summary",
            "",
            f"- packet jobs: `{summary['packet_job_count']}`",
            f"- blocker tracks: `{summary['blocker_track_count']}`",
            f"- exact job/track coverage: `{summary['job_track_coverage_exact']}`",
            f"- candidate packs: `{summary['candidate_pack_count']}`",
            f"- runtime zero reads: `{summary['runtime_zero_read_count']}`",
            f"- reader PC targets: `{summary['reader_pc_target_count']}`",
            f"- export classes: `{summary['export_class_counts']}`",
            f"- trace focus jobs: `{summary['trace_focus_job_counts']}`",
            f"- post-proof actions: `{summary['post_zero_proof_action_job_counts']}`",
            f"- result files found: `{summary['result_count']}`",
            f"- valid results: `{summary['valid_result_count']}`",
            f"- remaining blockers: `{summary['remaining_blocker_track_counts']}`",
            f"- accepted classifications: `{summary['accepted_zero_effect_classifications']}`",
            "",
            "## Phase Batches",
            "",
            "| Phase | Jobs | Tracks |",
            "| --- | ---: | --- |",
            *phase_rows,
            "",
            "## Probe Jobs",
            "",
            "| Order | Track | Name | Phase | Trace focus | Post-proof action | Result output |",
            "| ---: | ---: | --- | --- | --- | --- | --- |",
            *rows,
            "",
            "## Validation After External Results",
            "",
            *command_rows,
            "",
            "## Probe Packet Policy",
            "",
            *[f"- {item}" for item in data["probe_packet_policy"]],
            "",
            "## Remaining Uncertainty",
            "",
            "- All 19 zero-runtime probe jobs still need external harness results before sequence semantics can change.",
            "- EF-return stack modeling remains pending for 15 tracks even after zero-effect proof is collected.",
            "- Post-proof actions still split into seven active-preview classifications, ten finite/transition reviews, and two loop-point metadata reviews.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    data = build_packet(
        load_json(Path(args.plan)),
        load_json(Path(args.coverage)),
        load_json(Path(args.campaign)),
        load_json(Path(args.results)),
        load_json(Path(args.next_actions)),
    )
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built zero-runtime probe packet: "
        f"{data['summary']['packet_job_count']} jobs, "
        f"{data['summary']['blocker_track_count']} blockers"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
