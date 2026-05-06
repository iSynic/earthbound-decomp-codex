#!/usr/bin/env python3
"""Build a ranked next-actions plan for audio exact-duration evidence work."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROLLUP = ROOT / "manifests" / "audio-duration-readiness-rollup.json"
DEFAULT_INDEPENDENT_ORACLE = ROOT / "manifests" / "audio-independent-oracle-coverage-report.json"
DEFAULT_NONZERO = ROOT / "manifests" / "audio-nonzero-control-coverage-report.json"
DEFAULT_ZERO = ROOT / "manifests" / "audio-zero-runtime-coverage-report.json"
DEFAULT_FINITE_TAIL = ROOT / "manifests" / "audio-finite-ending-tail-metrics.json"
DEFAULT_LOOP_TAIL = ROOT / "manifests" / "audio-loop-point-tail-metrics.json"
DEFAULT_RESIDUAL = ROOT / "manifests" / "audio-residual-uncertainty-coverage-report.json"
DEFAULT_PROBE_CAMPAIGN = ROOT / "manifests" / "audio-probe-campaign-plan.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-duration-next-actions-plan.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-duration-next-actions-plan.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build audio duration next-actions plan.")
    parser.add_argument("--rollup", default=str(DEFAULT_ROLLUP), help="Audio duration readiness rollup JSON.")
    parser.add_argument("--independent-oracle", default=str(DEFAULT_INDEPENDENT_ORACLE), help="Independent oracle coverage report JSON.")
    parser.add_argument("--nonzero", default=str(DEFAULT_NONZERO), help="Nonzero control coverage report JSON.")
    parser.add_argument("--zero", default=str(DEFAULT_ZERO), help="0x00 runtime coverage report JSON.")
    parser.add_argument("--finite-tail", default=str(DEFAULT_FINITE_TAIL), help="Finite-ending tail metrics JSON.")
    parser.add_argument("--loop-tail", default=str(DEFAULT_LOOP_TAIL), help="Loop-point tail metrics JSON.")
    parser.add_argument("--residual", default=str(DEFAULT_RESIDUAL), help="Residual uncertainty coverage report JSON.")
    parser.add_argument("--probe-campaign", default=str(DEFAULT_PROBE_CAMPAIGN), help="Unified probe campaign plan JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Next-actions plan JSON output.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Next-actions markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def track_refs(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs = [
        {"track_id": int(record["track_id"]), "track_name": str(record["track_name"])}
        for record in records
        if record.get("track_id") is not None
    ]
    return sorted(refs, key=lambda item: int(item["track_id"]))


def job_ids(records: list[dict[str, Any]]) -> list[str]:
    return [str(record["job_id"]) for record in records]


def campaign_job_ids(campaign: dict[str, Any], lane: str) -> list[str]:
    jobs = [job for job in campaign.get("campaign_jobs", []) if job.get("lane") == lane]
    jobs.sort(key=lambda item: int(item.get("execution_order", 0)))
    return job_ids(jobs)


def residual_records_by_state(residual: dict[str, Any], state: str) -> list[dict[str, Any]]:
    records = [record for record in residual.get("records", []) if record.get("current_policy_state") == state]
    return sorted(records, key=lambda item: int(item["track_id"]))


def residual_records_by_uncertainty(residual: dict[str, Any], uncertainty: str) -> list[dict[str, Any]]:
    records = [record for record in residual.get("records", []) if record.get("primary_uncertainty") == uncertainty]
    return sorted(records, key=lambda item: int(item["track_id"]))


def build_plan(
    rollup: dict[str, Any],
    independent: dict[str, Any],
    nonzero: dict[str, Any],
    zero: dict[str, Any],
    finite_tail: dict[str, Any],
    loop_tail: dict[str, Any],
    residual: dict[str, Any],
    probe_campaign: dict[str, Any],
) -> dict[str, Any]:
    rollup_summary = rollup.get("summary", {})
    independent_summary = independent.get("summary", {})
    nonzero_summary = nonzero.get("summary", {})
    zero_summary = zero.get("summary", {})
    finite_summary = finite_tail.get("summary", {})
    loop_summary = loop_tail.get("summary", {})
    residual_summary = residual.get("summary", {})
    residual_public_blockers = residual_records_by_state(residual, "public_exact_blocked")
    pcm_trim_records = residual_records_by_uncertainty(residual, "pcm_trim_usable_sequence_intent_open")
    independent_records = independent.get("campaign_records", [])
    nonzero_jobs = nonzero.get("jobs", [])
    zero_jobs = zero.get("jobs", [])
    finite_records = finite_tail.get("records", [])
    loop_records = loop_tail.get("records", [])
    nonzero_campaign_jobs = campaign_job_ids(probe_campaign, "nonzero")
    zero_campaign_jobs = campaign_job_ids(probe_campaign, "zero")

    lanes = [
        {
            "priority_rank": 1,
            "lane_id": "independent_oracle_representative_capture",
            "status": "external_captures_missing",
            "priority_reason": (
                "Release-quality playback claims are blocked even though the all-track near-oracle gate is green; "
                "the representative external-emulator campaign is the smallest independent comparison set."
            ),
            "primary_inputs": [
                "manifests/audio-independent-oracle-coverage-report.json",
                "manifests/audio-oracle-comparison-plan-all-tracks.json",
            ],
            "counts": {
                "representative_job_count": int(independent_summary.get("representative_campaign_job_count", 0)),
                "representative_missing_independent_capture_count": int(
                    independent_summary.get("representative_missing_independent_capture_count", 0)
                ),
                "all_track_missing_independent_capture_count": int(independent_summary.get("missing_independent_capture_count", 0)),
            },
            "track_refs": track_refs(independent_records),
            "job_ids": job_ids(independent_records),
            "commands": [
                "python tools/build_audio_independent_oracle_capture_packet.py",
                "python tools/validate_audio_independent_oracle_capture_packet.py",
                "python tools/validate_audio_independent_oracle_coverage_report.py",
                "python tools/run_audio_independent_oracle_campaign.py --mode audit-existing-captures",
                "python tools/import_audio_oracle_reference_capture.py --plan manifests/audio-oracle-comparison-plan-all-tracks.json --track-id <track-id> --spc <external-capture.spc> --wav <external-render.wav> --oracle-id <mesen2|bsnes_higan|mednafen> --emulator-version <version> --capture-command <command> --audio-settings <settings> --overwrite",
                "python tools/validate_audio_oracle_reference_capture.py --plan manifests/audio-oracle-comparison-plan-all-tracks.json --track-id <track-id>",
                "python tools/validate_audio_oracle_verification_report.py manifests/audio-oracle-verification-report-all-tracks.json --require-representative-pass",
            ],
            "completion_gate": (
                "Import and validate all 16 representative independent captures, then refresh the all-track oracle "
                "verification report until the independent emulator gate passes for the representative set."
            ),
            "promotion_allowed_by_lane": False,
            "behavior_change_allowed": False,
        },
        {
            "priority_rank": 2,
            "lane_id": "nonzero_control_probe_import",
            "status": "probe_outputs_missing",
            "priority_reason": (
                "Nonzero control semantics are the largest track-count blocker; the seven probe jobs are the "
                "highest-leverage way to reduce the 155-track uncertainty lane."
            ),
            "primary_inputs": [
                "manifests/audio-nonzero-control-coverage-report.json",
                "manifests/audio-probe-campaign-plan.json",
            ],
            "counts": {
                "blocker_track_count": int(nonzero_summary.get("blocker_track_count", 0)),
                "probe_job_count": int(nonzero_summary.get("probe_job_count", 0)),
                "source_candidate_record_count": int(nonzero_summary.get("source_candidate_record_count", 0)),
                "blocker_tracks_without_source_candidate_count": int(
                    nonzero_summary.get("blocker_tracks_without_source_candidate_count", 0)
                ),
            },
            "source_candidate_track_refs": track_refs(nonzero.get("source_candidate_reuse", [])),
            "job_ids": job_ids(nonzero_jobs),
            "campaign_job_ids": nonzero_campaign_jobs,
            "commands": [
                "python tools/validate_audio_nonzero_control_coverage_report.py",
                "python tools/validate_audio_nonzero_control_probe_plan.py",
                "python tools/run_audio_probe_campaign.py --lane nonzero --mode dry-run-stub --force",
                "python tools/run_audio_probe_campaign.py --lane nonzero --mode stub-shape --force",
                "python tools/run_audio_nonzero_control_probe_batch.py --job-id <job-id> --force --mode external --external <nonzero-control-probe-harness> --job \"{job}\" --result \"{result}\"",
                "python tools/collect_audio_nonzero_control_probe_results.py",
                "python tools/build_audio_sequence_semantics_intake_plan.py",
                "python tools/validate_audio_sequence_semantics_intake_plan.py",
                "python tools/validate_audio_duration_uncertainty_register.py",
            ],
            "completion_gate": (
                "Every nonzero probe job has imported result JSON and the intake refresh classifies EF/FD/FE/FF effects "
                "without opening sequence promotion."
            ),
            "promotion_allowed_by_lane": False,
            "behavior_change_allowed": False,
        },
        {
            "priority_rank": 3,
            "lane_id": "zero_runtime_probe_import",
            "status": "probe_outputs_missing",
            "priority_reason": (
                "The 0x00 lane has exact one-job-per-track coverage, so it can produce clean finite/loop/preview "
                "follow-up buckets once runtime effect proofs are imported."
            ),
            "primary_inputs": [
                "manifests/audio-zero-runtime-coverage-report.json",
                "manifests/audio-probe-campaign-plan.json",
            ],
            "counts": {
                "blocker_track_count": int(zero_summary.get("blocker_track_count", 0)),
                "probe_job_count": int(zero_summary.get("probe_job_count", 0)),
                "reader_pc_target_count": int(zero_summary.get("reader_pc_target_count", 0)),
                "runtime_zero_read_count": int(zero_summary.get("runtime_zero_read_count", 0)),
            },
            "track_refs": track_refs(zero_jobs),
            "job_ids": job_ids(zero_jobs),
            "campaign_job_ids": zero_campaign_jobs,
            "commands": [
                "python tools/validate_audio_zero_runtime_coverage_report.py",
                "python tools/validate_audio_zero_runtime_probe_plan.py",
                "python tools/run_audio_probe_campaign.py --lane zero --mode dry-run-stub --force",
                "python tools/run_audio_probe_campaign.py --lane zero --mode stub-shape --force",
                "python tools/run_audio_zero_runtime_probe_batch.py --job-id <job-id> --force --mode external --external <zero-runtime-probe-harness> --job \"{job}\" --result \"{result}\"",
                "python tools/collect_audio_zero_runtime_probe_results.py",
                "python tools/build_audio_sequence_semantics_intake_plan.py",
                "python tools/validate_audio_sequence_semantics_intake_plan.py",
                "python tools/validate_audio_duration_uncertainty_register.py",
            ],
            "completion_gate": (
                "Every zero-runtime blocker has imported runtime effect proof, then each track is routed to active-preview, "
                "finite/transition, or loop-point follow-up according to the refreshed uncertainty register."
            ),
            "promotion_allowed_by_lane": False,
            "behavior_change_allowed": False,
        },
        {
            "priority_rank": 4,
            "lane_id": "finite_transition_tail_classification",
            "status": "runtime_tail_classification_pending",
            "priority_reason": (
                "Five candidate finite ends all have nonzero PCM after the candidate end; three remain active through the "
                "diagnostic render boundary and need transition/stinger evidence before exact finite export."
            ),
            "primary_inputs": [
                "manifests/audio-finite-ending-tail-metrics.json",
                "manifests/audio-finite-ending-evidence-plan.json",
            ],
            "counts": {
                "track_count": int(finite_summary.get("record_count", 0)),
                "nonzero_after_candidate_end_count": int(finite_summary.get("nonzero_after_candidate_end_count", 0)),
                "active_through_render_boundary_count": int(finite_summary.get("active_through_render_boundary_count", 0)),
            },
            "track_refs": track_refs(finite_records),
            "job_ids": job_ids(finite_records),
            "commands": [
                "python tools/run_audio_finite_ending_evidence_plan.py --mode audit-current-export",
                "python tools/validate_audio_finite_ending_evidence_run_summary.py",
                "python tools/build_audio_finite_ending_tail_metrics.py",
                "python tools/validate_audio_finite_ending_tail_metrics.py",
                "python tools/validate_audio_duration_uncertainty_register.py",
            ],
            "completion_gate": (
                "Each finite-transition candidate has runtime/oracle state evidence that distinguishes true finite release "
                "from transition/stinger or active preview behavior."
            ),
            "promotion_allowed_by_lane": False,
            "behavior_change_allowed": False,
        },
        {
            "priority_rank": 5,
            "lane_id": "loop_point_or_hold_classification",
            "status": "exact_loop_metadata_missing",
            "priority_reason": (
                "All five loop/held candidates are active through the diagnostic render boundary, but exact intro/start/end "
                "loop fields are still placeholders."
            ),
            "primary_inputs": [
                "manifests/audio-loop-point-tail-metrics.json",
                "manifests/audio-loop-point-evidence-plan.json",
            ],
            "counts": {
                "track_count": int(loop_summary.get("record_count", 0)),
                "active_through_render_boundary_count": int(loop_summary.get("active_through_render_boundary_count", 0)),
                "missing_exact_loop_field_count": int(loop_summary.get("missing_exact_loop_field_count", 0)),
            },
            "track_refs": track_refs(loop_records),
            "job_ids": job_ids(loop_records),
            "commands": [
                "python tools/run_audio_loop_point_evidence_plan.py --mode audit-current-export",
                "python tools/validate_audio_loop_point_evidence_run_summary.py",
                "python tools/build_audio_loop_point_tail_metrics.py",
                "python tools/validate_audio_loop_point_tail_metrics.py",
                "python tools/validate_audio_duration_uncertainty_register.py",
            ],
            "completion_gate": (
                "Each candidate has validated exact loop intro/start/end metadata or a documented held/no-exact-loop policy "
                "that keeps public preview behavior explicit."
            ),
            "promotion_allowed_by_lane": False,
            "behavior_change_allowed": False,
        },
        {
            "priority_rank": 6,
            "lane_id": "residual_public_exact_blockers",
            "status": "two_public_exact_blockers_remaining",
            "priority_reason": (
                "The residual lane isolates the only public-exact blockers not already covered by control, finite-tail, "
                "loop-tail, or oracle campaign work."
            ),
            "primary_inputs": [
                "manifests/audio-residual-uncertainty-coverage-report.json",
                "manifests/audio-export-plan.json",
            ],
            "counts": {
                "record_count": int(residual_summary.get("record_count", 0)),
                "public_exact_blocked_count": int(residual_summary.get("public_exact_blocked_count", 0)),
            },
            "track_refs": track_refs(residual_public_blockers),
            "recommended_actions": {
                str(record["track_id"]): record.get("recommended_action") for record in residual_public_blockers
            },
            "commands": [
                "python tools/validate_audio_residual_uncertainty_coverage_report.py",
                "python tools/build_audio_export_plan.py",
                "python tools/validate_audio_export_plan.py",
                "python tools/build_audio_duration_uncertainty_register.py",
                "python tools/validate_audio_duration_uncertainty_register.py",
            ],
            "completion_gate": (
                "NONE has a measured duration or explicit skip policy, and WHAT_THE_HECK has active-preview classification "
                "or exact-end evidence before public exact export."
            ),
            "promotion_allowed_by_lane": False,
            "behavior_change_allowed": False,
        },
        {
            "priority_rank": 7,
            "lane_id": "pcm_trim_sequence_intent_review",
            "status": "semantic_promotion_open_public_exact_ready",
            "priority_reason": (
                "Five PCM-trim tracks are already public-exact ready from PCM evidence; reviewing sequence intent prevents "
                "those usable exports from being confused with sequence-derived semantic promotion."
            ),
            "primary_inputs": [
                "manifests/audio-residual-uncertainty-coverage-report.json",
                "manifests/audio-sequence-semantics-intake-plan.json",
            ],
            "counts": {
                "pcm_trim_sequence_intent_open_count": int(residual_summary.get("pcm_trim_sequence_intent_open_count", 0)),
                "public_exact_allowed_count": int(residual_summary.get("public_exact_allowed_count", 0)),
            },
            "track_refs": track_refs(pcm_trim_records),
            "commands": [
                "python tools/validate_audio_residual_uncertainty_coverage_report.py",
                "python tools/validate_audio_sequence_semantics_intake_plan.py",
                "python tools/validate_audio_duration_uncertainty_register.py",
                "python tools/validate_audio_export_plan.py",
            ],
            "completion_gate": (
                "PCM trim remains usable for public export while sequence-intent evidence either validates or explicitly "
                "blocks semantic sequence promotion."
            ),
            "promotion_allowed_by_lane": False,
            "behavior_change_allowed": False,
        },
    ]
    return {
        "schema": "earthbound-decomp.audio-duration-next-actions-plan.v1",
        "status": "audio_duration_next_actions_ready_policy_preserved",
        "references": [
            "manifests/audio-duration-readiness-rollup.json",
            "manifests/audio-independent-oracle-coverage-report.json",
            "manifests/audio-nonzero-control-coverage-report.json",
            "manifests/audio-zero-runtime-coverage-report.json",
            "manifests/audio-finite-ending-tail-metrics.json",
            "manifests/audio-loop-point-tail-metrics.json",
            "manifests/audio-residual-uncertainty-coverage-report.json",
            "manifests/audio-probe-campaign-plan.json",
        ],
        "summary": {
            "priority_lane_count": len(lanes),
            "release_ready": bool(rollup_summary.get("release_ready")),
            "behavior_change_allowed": False,
            "promotion_allowed_by_plan": False,
            "blocking_track_count": int(rollup_summary.get("blocking_track_count", 0)),
            "independent_oracle_representative_jobs": int(independent_summary.get("representative_campaign_job_count", 0)),
            "independent_oracle_representative_missing": int(
                independent_summary.get("representative_missing_independent_capture_count", 0)
            ),
            "nonzero_control_probe_jobs": int(nonzero_summary.get("probe_job_count", 0)),
            "nonzero_control_blocker_tracks": int(nonzero_summary.get("blocker_track_count", 0)),
            "zero_runtime_probe_jobs": int(zero_summary.get("probe_job_count", 0)),
            "zero_runtime_blocker_tracks": int(zero_summary.get("blocker_track_count", 0)),
            "finite_transition_tracks": int(finite_summary.get("record_count", 0)),
            "loop_point_tracks": int(loop_summary.get("record_count", 0)),
            "residual_public_exact_blockers": int(residual_summary.get("public_exact_blocked_count", 0)),
            "pcm_trim_sequence_intent_tracks": int(residual_summary.get("pcm_trim_sequence_intent_open_count", 0)),
        },
        "priority_lanes": lanes,
        "post_completion_validation_commands": [
            "python tools/build_audio_duration_readiness_rollup.py",
            "python tools/validate_audio_duration_readiness_rollup.py",
            "python tools/build_audio_duration_next_actions_plan.py",
            "python tools/validate_audio_duration_next_actions_plan.py",
            "python tools/validate_audio_export_plan.py",
            "python tools/validate_audio_duration_uncertainty_register.py",
            "python tools/validate_audio_oracle_verification_report.py manifests/audio-oracle-verification-report-all-tracks.json --require-representative-pass",
            "git diff --check",
        ],
        "decision_policy": [
            "This plan ranks evidence collection and validation only; it does not change playback or export behavior.",
            "Promotion remains blocked in every lane until source reports are refreshed by imported evidence.",
            "Independent external-emulator captures are the first release-quality comparison gate even though near-oracle equivalence passes.",
            "Nonzero and zero probe outputs must be collected under ignored build/audio paths before they can affect duration uncertainty.",
            "Finite and loop candidates need runtime/oracle classification before exact-duration or exact-loop public export claims.",
            "Residual public-exact blockers are tracked separately from PCM-trim tracks that are already usable by PCM evidence.",
        ],
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    lane_rows = [
        "| {rank} | `{lane}` | `{status}` | {reason} | `{counts}` |".format(
            rank=lane["priority_rank"],
            lane=lane["lane_id"],
            status=lane["status"],
            reason=lane["priority_reason"],
            counts=lane["counts"],
        )
        for lane in data["priority_lanes"]
    ]
    command_rows = [
        f"- `{command}`" for command in data["post_completion_validation_commands"]
    ]
    remaining = [
        "- Independent external-emulator representative captures remain missing for all 16 queued jobs.",
        "- Nonzero control semantics remain the largest track-count blocker: 155 tracks, with seven representative probe jobs.",
        "- Zero runtime semantics have exact blocker coverage: 19 tracks and 19 probe jobs.",
        "- Five finite-transition candidates and five loop/held candidates still need runtime/oracle classification.",
        "- `NONE` and `WHAT_THE_HECK` remain the residual public-exact blockers.",
        "- Five PCM-trim tracks are public-exact ready from PCM evidence, but sequence-intent promotion remains open.",
    ]
    return "\n".join(
        [
            "# Audio Duration Next Actions Plan",
            "",
            "Status: next evidence actions are ranked; current playback/export behavior is preserved.",
            "",
            "## Summary",
            "",
            f"- priority lanes: `{summary['priority_lane_count']}`",
            f"- release ready: `{summary['release_ready']}`",
            f"- blocking tracks: `{summary['blocking_track_count']}`",
            f"- independent representative jobs: `{summary['independent_oracle_representative_jobs']}`",
            f"- nonzero control probe jobs: `{summary['nonzero_control_probe_jobs']}`",
            f"- zero runtime probe jobs: `{summary['zero_runtime_probe_jobs']}`",
            f"- finite-transition tracks: `{summary['finite_transition_tracks']}`",
            f"- loop-point tracks: `{summary['loop_point_tracks']}`",
            f"- residual public-exact blockers: `{summary['residual_public_exact_blockers']}`",
            f"- PCM-trim sequence-intent tracks: `{summary['pcm_trim_sequence_intent_tracks']}`",
            "",
            "## Priority Lanes",
            "",
            "| Rank | Lane | Status | Why first | Counts |",
            "| ---: | --- | --- | --- | --- |",
            *lane_rows,
            "",
            "## Post-Completion Validation",
            "",
            *command_rows,
            "",
            "## Decision Policy",
            "",
            *[f"- {item}" for item in data["decision_policy"]],
            "",
            "## Remaining Uncertainty",
            "",
            *remaining,
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    data = build_plan(
        load_json(Path(args.rollup)),
        load_json(Path(args.independent_oracle)),
        load_json(Path(args.nonzero)),
        load_json(Path(args.zero)),
        load_json(Path(args.finite_tail)),
        load_json(Path(args.loop_tail)),
        load_json(Path(args.residual)),
        load_json(Path(args.probe_campaign)),
    )
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built audio duration next-actions plan: "
        f"{data['summary']['priority_lane_count']} lanes, "
        f"{data['summary']['blocking_track_count']} blocking tracks"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
