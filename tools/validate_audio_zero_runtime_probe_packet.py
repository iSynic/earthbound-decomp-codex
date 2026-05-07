#!/usr/bin/env python3
"""Validate the 0x00 runtime audio probe execution packet."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PACKET = ROOT / "manifests" / "audio-zero-runtime-probe-packet.json"
REQUIRED_REFERENCES = {
    "manifests/audio-zero-runtime-probe-plan.json",
    "manifests/audio-zero-runtime-coverage-report.json",
    "manifests/audio-probe-campaign-plan.json",
    "manifests/audio-zero-runtime-probe-results-summary.json",
    "manifests/audio-duration-next-actions-plan.json",
}
REQUIRED_PHASE_COUNTS = {
    "zero-active-preview-followup": 6,
    "zero-ef-return-stack": 11,
    "zero-finite-transition-followup": 1,
    "zero-loop-point-followup": 1,
}
REQUIRED_TRACE_COUNTS = {
    "prove_zero_effect_but_loop_points_remain_required": 2,
    "prove_zero_effect_then_classify_active_preview": 5,
    "prove_zero_end_effect_then_review_finite_candidate": 1,
    "trace_zero_reader_with_ef_stack_state": 11,
}
REQUIRED_POST_ACTION_COUNTS = {
    "classify_active_preview_before_exact_export": 7,
    "decode_loop_points_before_exact_export": 2,
    "review_observed_silence_as_finite_or_transition": 10,
}
REQUIRED_PACK_CONTEXT_COUNTS = {
    "needs_ef_return_stack_model": 11,
    "zero_phrase_end_candidate_runtime_pending": 8,
}
REQUIRED_REMAINING_BLOCKERS = {
    "active_preview_classification": 7,
    "ef_return_stack_model": 15,
    "finite_transition_review": 10,
    "loop_point_metadata": 2,
    "zero_runtime_effect_proof": 19,
}
REQUIRED_ZERO_CLASSIFICATIONS = {
    "true_end",
    "ef_return",
    "loop_or_hold_continues",
    "unreachable_from_source_state",
    "unresolved",
}
REQUIRED_READER_PCS = {"0x2DB0", "0x2DDA", "0x2DF8", "0x2E3D", "0x0957", "0x0B8A", "0x0847", "0x0782", "0x07A6", "0x0D12"}
REQUIRED_POST_COMMANDS = {
    "python tools/validate_audio_zero_runtime_probe_packet.py",
    "python tools/run_audio_probe_campaign.py --lane zero --mode dry-run-stub --force",
    "python tools/run_audio_probe_campaign.py --lane zero --mode stub-shape --force",
    "python tools/collect_audio_zero_runtime_probe_results.py",
    "python tools/validate_audio_zero_runtime_probe_results_summary.py",
    "python tools/build_audio_sequence_semantics_intake_plan.py",
    "python tools/validate_audio_sequence_semantics_intake_plan.py",
    "python tools/validate_audio_duration_uncertainty_register.py",
    "python tools/build_audio_duration_readiness_rollup.py",
    "python tools/validate_audio_duration_readiness_rollup.py",
}
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate audio zero-runtime probe packet.")
    parser.add_argument("packet", nargs="?", default=str(DEFAULT_PACKET))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def count_records(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        counts[str(record.get(key))] += 1
    return dict(sorted(counts.items()))


def output_path_is_under(root: str, path_text: str) -> bool:
    normalized_root = root.rstrip("/\\") + "/"
    normalized_path = path_text.replace("\\", "/")
    return normalized_path.startswith(normalized_root) and ".." not in Path(normalized_path).parts


def validate_source(job_id: str, source: dict[str, Any]) -> None:
    require(str(source.get("oracle_job_id", "")).startswith("oracle-track-"), f"{job_id}: missing oracle job id")
    source_spc = source.get("source_spc", {})
    source_render = source.get("source_render", {})
    require(str(source_spc.get("path", "")).endswith(".spc"), f"{job_id}: source SPC path missing")
    require(bool(SHA1_RE.match(str(source_spc.get("sha1", "")))), f"{job_id}: invalid source SPC sha1")
    require(int(source_spc.get("bytes", 0)) == 66048, f"{job_id}: source SPC byte count mismatch")
    require(str(source_render.get("path", "")).endswith(".wav"), f"{job_id}: source render path missing")
    require(bool(SHA1_RE.match(str(source_render.get("sha1", "")))), f"{job_id}: invalid source render sha1")
    require(int(source_render.get("bytes", 0)) > 0, f"{job_id}: source render byte count missing")


def validate_record(record: dict[str, Any], output_root: str) -> None:
    job_id = str(record.get("job_id"))
    require(job_id.startswith("zero-probe-track-"), f"{job_id}: unexpected job id")
    require(int(record.get("track_id", 0)) > 0, f"{job_id}: invalid track id")
    require(record.get("track_name"), f"{job_id}: missing track name")
    require(record.get("phase") in REQUIRED_PHASE_COUNTS, f"{job_id}: unexpected phase")
    require(int(record.get("pack_id", 0)) > 0, f"{job_id}: invalid pack id")
    require(record.get("pack_track_ids"), f"{job_id}: missing pack track ids")
    require(record.get("pack_context_class") in REQUIRED_PACK_CONTEXT_COUNTS, f"{job_id}: unexpected pack context")
    require(record.get("trace_focus") in REQUIRED_TRACE_COUNTS, f"{job_id}: unexpected trace focus")
    require(record.get("post_zero_proof_action") in REQUIRED_POST_ACTION_COUNTS, f"{job_id}: unexpected post-proof action")
    require("zero_runtime_effect_proof" in record.get("pre_promotion_blockers", []), f"{job_id}: missing zero proof blocker")
    require(record.get("promotion_question"), f"{job_id}: missing promotion question")
    require(record.get("remaining_uncertainty"), f"{job_id}: missing remaining uncertainty")
    validate_source(job_id, record.get("source", {}))
    require(record.get("source_spc_sha1") == record.get("source", {}).get("source_spc", {}).get("sha1"), f"{job_id}: source SHA mismatch")
    static_context = record.get("zero_static_context", {})
    require(int(static_context.get("zero_terminator_candidates", 0)) > 0, f"{job_id}: missing zero candidates")
    require(static_context.get("sampled_zero_walk_context_class_counts"), f"{job_id}: missing walk context")
    require(int(record.get("reader_pc_target_count", 0)) == 10, f"{job_id}: reader target count mismatch")
    require(set(record.get("reader_pc_targets", [])) == REQUIRED_READER_PCS, f"{job_id}: reader targets mismatch")
    require(len(record.get("required_capture_fields", [])) >= 20, f"{job_id}: capture fields missing")
    require(set(record.get("accepted_zero_effect_classifications", [])) == REQUIRED_ZERO_CLASSIFICATIONS, f"{job_id}: classification set mismatch")
    require(len(record.get("success_criteria", [])) >= 4, f"{job_id}: success criteria too thin")
    outputs = record.get("probe_outputs", {})
    for key in ("root", "raw_trace", "result_json", "evidence_markdown"):
        require(output_path_is_under(output_root, str(outputs.get(key, ""))), f"{job_id}: bad output path {key}")
    require(str(outputs.get("result_json", "")).endswith("zero-runtime-proof-result.json"), f"{job_id}: bad result output")
    commands = record.get("commands", {})
    required_fragments = {
        "campaign_dry_run": "run_audio_probe_campaign.py --lane zero",
        "campaign_stub_shape": "run_audio_probe_campaign.py --lane zero",
        "external_run": "run_audio_zero_runtime_probe_batch.py",
        "stub_shape": "audio_zero_runtime_probe_stub_harness.py",
        "validate_result": "validate_audio_zero_runtime_probe_result.py",
        "collect_results": "collect_audio_zero_runtime_probe_results.py",
        "refresh_intake": "build_audio_sequence_semantics_intake_plan.py",
    }
    for key, fragment in required_fragments.items():
        require(fragment in str(commands.get(key, "")), f"{job_id}: missing command {key}")
    current = record.get("current_result_status", {})
    require(current.get("result_exists") is False, f"{job_id}: committed packet should not see real results")
    require(current.get("status") == "pending", f"{job_id}: missing result should be pending")
    require(current.get("valid") is False, f"{job_id}: missing result cannot be valid")
    require(current.get("zero_effect_classification") == "pending", f"{job_id}: missing result classification should be pending")
    require("zero_runtime_effect_proof" in current.get("remaining_blockers", []), f"{job_id}: zero proof blocker missing")
    require(record.get("promotion_allowed_by_packet") is False, f"{job_id}: promotion should be blocked")
    require(record.get("behavior_change_allowed") is False, f"{job_id}: behavior changes should be blocked")


def validate_batches(data: dict[str, Any]) -> None:
    batches = data.get("operator_batches", {})
    expected = {
        "by_phase": ("phase", REQUIRED_PHASE_COUNTS),
        "by_trace_focus": ("trace_focus", REQUIRED_TRACE_COUNTS),
        "by_post_zero_proof_action": ("post_zero_proof_action", REQUIRED_POST_ACTION_COUNTS),
        "by_pack_context_class": ("pack_context_class", REQUIRED_PACK_CONTEXT_COUNTS),
    }
    for group, (key, counts) in expected.items():
        observed = {batch.get(key): int(batch.get("job_count", 0)) for batch in batches.get(group, [])}
        require(observed == counts, f"{group}: counts mismatch")
        for batch in batches.get(group, []):
            count = int(batch.get("job_count", 0))
            require(len(batch.get("track_ids", [])) == count, f"{group}: track count mismatch")
            require(len(batch.get("job_ids", [])) == count, f"{group}: job count mismatch")


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-zero-runtime-probe-packet.v1", "unexpected schema")
    require(data.get("status") == "zero_runtime_probe_packet_ready_external_harness_required", "unexpected status")
    require(data.get("source_plan_status") == "zero_runtime_probe_jobs_ready_runner_extension_pending", "unexpected plan status")
    require(data.get("source_coverage_status") == "zero_runtime_coverage_ready_probe_outputs_pending", "unexpected coverage status")
    require(data.get("source_campaign_status") == "probe_campaign_ready_for_external_harness_runs", "unexpected campaign status")
    require(data.get("source_results_status") == "zero_runtime_probe_results_collected", "unexpected results status")
    require(data.get("source_next_action_lane") == "zero_runtime_probe_import", "unexpected next-action lane")
    require(REQUIRED_REFERENCES <= set(data.get("references", [])), "missing references")
    summary = data.get("summary", {})
    records = data.get("records", [])
    require(int(summary.get("packet_job_count", 0)) == 19, "expected 19 packet jobs")
    require(len(records) == 19, "record count mismatch")
    require(int(summary.get("blocker_track_count", 0)) == 19, "blocker count mismatch")
    require(int(summary.get("probe_job_count", 0)) == 19, "probe job count mismatch")
    require(summary.get("job_track_coverage_exact") is True, "zero lane should exactly cover blocker tracks")
    require(int(summary.get("candidate_pack_count", 0)) == 10, "candidate pack count mismatch")
    require(int(summary.get("runtime_zero_read_count", 0)) == 5931, "runtime zero read count mismatch")
    require(int(summary.get("reader_pc_target_count", 0)) == 10, "reader PC count mismatch")
    require(set(summary.get("reader_pc_target_read_counts", {})) == REQUIRED_READER_PCS, "reader PC target set mismatch")
    require(summary.get("trace_focus_job_counts") == REQUIRED_TRACE_COUNTS, "trace focus counts mismatch")
    require(summary.get("pack_context_job_counts") == REQUIRED_PACK_CONTEXT_COUNTS, "pack context counts mismatch")
    require(summary.get("post_zero_proof_action_job_counts") == REQUIRED_POST_ACTION_COUNTS, "post-proof action counts mismatch")
    require(summary.get("phase_job_counts") == REQUIRED_PHASE_COUNTS, "phase counts mismatch")
    require(summary.get("pre_promotion_blocker_counts") == {"ef_return_stack_model": 15, "zero_runtime_effect_proof": 19}, "pre-promotion blocker counts mismatch")
    require(summary.get("remaining_blocker_track_counts") == REQUIRED_REMAINING_BLOCKERS, "remaining blocker counts mismatch")
    require(int(summary.get("result_count", -1)) == 0, "committed packet should have zero real results")
    require(int(summary.get("valid_result_count", -1)) == 0, "committed packet should have zero valid results")
    require(set(summary.get("accepted_zero_effect_classifications", [])) == REQUIRED_ZERO_CLASSIFICATIONS, "accepted classifications mismatch")
    output_root = str(summary.get("generated_outputs_root", ""))
    require(output_root == "build/audio/zero-runtime-probe", "unexpected output root")
    require(summary.get("sequence_promotion_allowed") is False, "sequence promotion should be blocked")
    require(summary.get("public_exact_promotion_allowed") is False, "public exact promotion should be blocked")
    require(summary.get("promotion_allowed_by_packet") is False, "packet promotion should be blocked")
    require(summary.get("behavior_change_allowed") is False, "behavior changes should be blocked")
    require(summary.get("trace_focus_job_counts") == count_records(records, "trace_focus"), "trace counts do not match records")
    require(summary.get("pack_context_job_counts") == count_records(records, "pack_context_class"), "pack context counts do not match records")
    require(summary.get("post_zero_proof_action_job_counts") == count_records(records, "post_zero_proof_action"), "post action counts do not match records")
    require(summary.get("phase_job_counts") == count_records(records, "phase"), "phase counts do not match records")
    reader_targets = data.get("reader_pc_targets", [])
    require(len(reader_targets) == 10, "reader PC target records mismatch")
    require({record.get("pc") for record in reader_targets} == REQUIRED_READER_PCS, "reader target records mismatch")
    seen_orders: set[int] = set()
    seen_jobs: set[str] = set()
    seen_tracks: set[int] = set()
    for record in records:
        order = int(record.get("execution_order", 0))
        job_id = str(record.get("job_id"))
        track_id = int(record.get("track_id", -1))
        require(order not in seen_orders, f"{job_id}: duplicate order")
        require(job_id not in seen_jobs, f"{job_id}: duplicate job")
        require(track_id not in seen_tracks, f"{job_id}: duplicate track")
        seen_orders.add(order)
        seen_jobs.add(job_id)
        seen_tracks.add(track_id)
        validate_record(record, output_root)
    require(seen_orders == set(range(8, 27)), "zero campaign execution orders should be 8..26")
    validate_batches(data)
    require(data.get("probe_packet_policy"), "missing packet policy")
    require(REQUIRED_POST_COMMANDS <= set(data.get("post_packet_validation_commands", [])), "missing post-packet validation commands")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.packet).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio zero-runtime probe packet validation OK: "
        f"{data['summary']['packet_job_count']} jobs, "
        f"{data['summary']['blocker_track_count']} blockers"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
