#!/usr/bin/env python3
"""Build an execution packet for non-0x00 audio control probe jobs."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "manifests" / "audio-nonzero-control-probe-plan.json"
DEFAULT_COVERAGE = ROOT / "manifests" / "audio-nonzero-control-coverage-report.json"
DEFAULT_CAMPAIGN = ROOT / "manifests" / "audio-probe-campaign-plan.json"
DEFAULT_RESULTS = ROOT / "manifests" / "audio-nonzero-control-probe-results-summary.json"
DEFAULT_NEXT_ACTIONS = ROOT / "manifests" / "audio-duration-next-actions-plan.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-nonzero-control-probe-packet.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-nonzero-control-probe-packet.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build nonzero control probe execution packet.")
    parser.add_argument("--plan", default=str(DEFAULT_PLAN), help="Nonzero control probe plan JSON.")
    parser.add_argument("--coverage", default=str(DEFAULT_COVERAGE), help="Nonzero control coverage report JSON.")
    parser.add_argument("--campaign", default=str(DEFAULT_CAMPAIGN), help="Unified probe campaign plan JSON.")
    parser.add_argument("--results", default=str(DEFAULT_RESULTS), help="Nonzero control probe results summary JSON.")
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
        if lane.get("lane_id") == "nonzero_control_probe_import":
            return lane
    return {}


def compact_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    source = candidate.get("source") or {}
    source_spc = source.get("source_spc", {})
    source_render = source.get("source_render", {})
    return {
        "track_id": int(candidate["track_id"]),
        "track_name": candidate["track_name"],
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
        "phase": campaign_job["phase"],
        "priority_score": int(campaign_job["priority_score"]),
        "priority_rank": int(plan_job["priority_rank"]),
        "priority_reason": plan_job.get("priority_reason"),
        "command": plan_job["command"],
        "reader_pc": plan_job["reader_pc"],
        "driver_offset": plan_job["driver_offset"],
        "read_count": int(plan_job["read_count"]),
        "affected_kind": plan_job["affected_kind"],
        "trace_focus": campaign_job.get("trace_focus"),
        "semantic_status": plan_job.get("semantic_status"),
        "promotion_question": plan_job.get("promotion_question"),
        "remaining_uncertainty": campaign_job.get("remaining_uncertainty", []),
        "source_candidate_count": int(coverage_job.get("source_candidate_count", 0)),
        "unique_source_candidate_track_ids": coverage_job.get("unique_source_candidate_track_ids", []),
        "blocker_source_candidate_track_ids": coverage_job.get("blocker_source_candidate_track_ids", []),
        "source_candidates": [compact_candidate(candidate) for candidate in plan_job.get("source_candidates", [])],
        "accepted_control_effect_classifications": plan_job.get("accepted_control_effect_classifications", []),
        "required_capture_fields": plan_job.get("required_capture_fields", []),
        "success_criteria": plan_job.get("success_criteria", []),
        "probe_outputs": {
            "root": outputs.get("root"),
            "raw_trace": outputs.get("raw_trace"),
            "result_json": outputs.get("result_json"),
            "evidence_markdown": outputs.get("evidence_markdown"),
        },
        "commands": {
            "campaign_dry_run": f"python tools/run_audio_probe_campaign.py --lane nonzero --job-id {plan_job['job_id']} --mode dry-run-stub --force",
            "campaign_stub_shape": f"python tools/run_audio_probe_campaign.py --lane nonzero --job-id {plan_job['job_id']} --mode stub-shape --force",
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
            "control_effect_classification": result.get("control_effect_classification"),
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
                "job_ids": [str(item["job_id"]) for item in items],
                "commands": [str(item["command"]) for item in items],
                "reader_pcs": [str(item["reader_pc"]) for item in items],
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
        str(job.get("job_id")): job for job in campaign.get("campaign_jobs", []) if job.get("lane") == "nonzero"
    }
    records = [
        packet_record(plan_jobs[job_id], coverage_jobs[job_id], campaign_jobs[job_id], result_records.get(job_id, {}))
        for job_id in campaign_jobs
    ]
    records.sort(key=lambda record: int(record["execution_order"]))
    command_counts = Counter(str(record["command"]) for record in records)
    reader_counts = Counter(str(record["reader_pc"]) for record in records)
    affected_counts = Counter(str(record["affected_kind"]) for record in records)
    phase_counts = Counter(str(record["phase"]) for record in records)
    unique_candidate_tracks = sorted(
        {int(candidate["track_id"]) for record in records for candidate in record.get("source_candidates", [])}
    )
    lane = find_next_action_lane(next_actions)
    coverage_summary = coverage.get("summary", {})
    results_summary = results.get("summary", {})
    return {
        "schema": "earthbound-decomp.audio-nonzero-control-probe-packet.v1",
        "status": "nonzero_control_probe_packet_ready_external_harness_required",
        "references": [
            "manifests/audio-nonzero-control-probe-plan.json",
            "manifests/audio-nonzero-control-coverage-report.json",
            "manifests/audio-probe-campaign-plan.json",
            "manifests/audio-nonzero-control-probe-results-summary.json",
            "manifests/audio-duration-next-actions-plan.json",
        ],
        "source_plan_status": plan.get("status"),
        "source_coverage_status": coverage.get("status"),
        "source_campaign_status": campaign.get("status"),
        "source_results_status": results.get("status"),
        "source_next_action_lane": lane.get("lane_id"),
        "summary": {
            "packet_job_count": len(records),
            "blocker_track_count": int(coverage_summary.get("blocker_track_count", 0)),
            "probe_job_count": int(coverage_summary.get("probe_job_count", 0)),
            "source_candidate_record_count": int(coverage_summary.get("source_candidate_record_count", 0)),
            "unique_source_candidate_track_count": len(unique_candidate_tracks),
            "blocker_tracks_without_source_candidate_count": int(
                coverage_summary.get("blocker_tracks_without_source_candidate_count", 0)
            ),
            "command_job_counts": dict(sorted(command_counts.items())),
            "reader_pc_job_counts": dict(sorted(reader_counts.items())),
            "affected_kind_job_counts": dict(sorted(affected_counts.items())),
            "phase_job_counts": dict(sorted(phase_counts.items())),
            "result_count": int(results_summary.get("result_count", 0)),
            "valid_result_count": int(results_summary.get("valid_result_count", 0)),
            "remaining_blocker_job_counts": results_summary.get("remaining_blocker_job_counts", {}),
            "accepted_control_effect_classifications": plan.get("runner_contract", {}).get(
                "accepted_control_effect_classifications", []
            ),
            "generated_outputs_root": plan.get("source_policy", {}).get("generated_outputs_root"),
            "sequence_promotion_allowed": False,
            "public_exact_promotion_allowed": False,
            "promotion_allowed_by_packet": False,
            "behavior_change_allowed": False,
        },
        "operator_batches": {
            "by_phase": grouped_jobs(records, "phase"),
            "by_command": grouped_jobs(records, "command"),
            "by_reader_pc": grouped_jobs(records, "reader_pc"),
        },
        "source_candidate_tracks": coverage.get("source_candidate_reuse", []),
        "probe_packet_policy": [
            "This packet is an operator checklist for external nonzero-control harness evidence; it does not run a real harness.",
            "Generated traces, results, SPCs, WAVs, and evidence markdown must stay under ignored build/audio paths.",
            "Dry-run and stub-shape commands prove runner/result schema only; they do not resolve sequence semantics.",
            "Only validated external results with accepted control-effect classifications may feed sequence semantics intake.",
            "This packet cannot directly promote sequence commands, public exact durations, or release-quality playback claims.",
        ],
        "records": records,
        "post_packet_validation_commands": [
            "python tools/validate_audio_nonzero_control_probe_packet.py",
            "python tools/run_audio_probe_campaign.py --lane nonzero --mode dry-run-stub --force",
            "python tools/validate_audio_probe_campaign_run_summary.py",
            "python tools/run_audio_probe_campaign.py --lane nonzero --mode stub-shape --force",
            "python tools/validate_audio_probe_campaign_run_summary.py",
            "python tools/collect_audio_nonzero_control_probe_results.py",
            "python tools/validate_audio_nonzero_control_probe_results_summary.py",
            "python tools/build_audio_sequence_semantics_intake_plan.py",
            "python tools/validate_audio_sequence_semantics_intake_plan.py",
            "python tools/validate_audio_duration_uncertainty_register.py",
            "python tools/validate_audio_nonzero_control_coverage_report.py",
            "python tools/build_audio_duration_readiness_rollup.py",
            "python tools/validate_audio_duration_readiness_rollup.py",
        ],
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    rows = [
        "| {order} | `{job_id}` | `{phase}` | `{command}` | `{reader}` | `{kind}` | {candidates} | `{result}` |".format(
            order=record["execution_order"],
            job_id=record["job_id"],
            phase=record["phase"],
            command=record["command"],
            reader=record["reader_pc"],
            kind=record["affected_kind"],
            candidates=record["source_candidate_count"],
            result=record["probe_outputs"]["result_json"],
        )
        for record in data["records"]
    ]
    batch_rows = [
        "| `{phase}` | {count} | `{jobs}` |".format(
            phase=batch["phase"],
            count=batch["job_count"],
            jobs=batch["job_ids"],
        )
        for batch in data["operator_batches"]["by_phase"]
    ]
    command_rows = [f"- `{command}`" for command in data["post_packet_validation_commands"]]
    return "\n".join(
        [
            "# Audio Nonzero Control Probe Packet",
            "",
            "Status: nonzero-control probe jobs are packaged for external harness evidence; current playback/export behavior is preserved.",
            "",
            "## Summary",
            "",
            f"- packet jobs: `{summary['packet_job_count']}`",
            f"- blocker tracks: `{summary['blocker_track_count']}`",
            f"- source candidate records: `{summary['source_candidate_record_count']}`",
            f"- unique source candidate tracks: `{summary['unique_source_candidate_track_count']}`",
            f"- blocker tracks without source candidate: `{summary['blocker_tracks_without_source_candidate_count']}`",
            f"- command jobs: `{summary['command_job_counts']}`",
            f"- reader PC jobs: `{summary['reader_pc_job_counts']}`",
            f"- result files found: `{summary['result_count']}`",
            f"- valid results: `{summary['valid_result_count']}`",
            f"- remaining blockers: `{summary['remaining_blocker_job_counts']}`",
            f"- accepted classifications: `{summary['accepted_control_effect_classifications']}`",
            "",
            "## Phase Batches",
            "",
            "| Phase | Jobs | Job IDs |",
            "| --- | ---: | --- |",
            *batch_rows,
            "",
            "## Probe Jobs",
            "",
            "| Order | Job | Phase | Command | Reader PC | Kind | Source candidates | Result output |",
            "| ---: | --- | --- | --- | --- | --- | ---: | --- |",
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
            "- All seven nonzero-control probe jobs still need external harness results before sequence semantics can change.",
            "- The representative source-candidate set covers ten tracks, while 146 primary nonzero blockers still lack a direct source candidate.",
            "- Sequence promotion and public exact-duration promotion remain blocked after packet generation.",
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
        "Built nonzero control probe packet: "
        f"{data['summary']['packet_job_count']} jobs, "
        f"{data['summary']['blocker_track_count']} blockers"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
