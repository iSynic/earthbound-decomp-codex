#!/usr/bin/env python3
"""Validate the non-0x00 audio control probe execution packet."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PACKET = ROOT / "manifests" / "audio-nonzero-control-probe-packet.json"
REQUIRED_REFERENCES = {
    "manifests/audio-nonzero-control-probe-plan.json",
    "manifests/audio-nonzero-control-coverage-report.json",
    "manifests/audio-probe-campaign-plan.json",
    "manifests/audio-nonzero-control-probe-results-summary.json",
    "manifests/audio-duration-next-actions-plan.json",
}
REQUIRED_COMMAND_COUNTS = {"0xEF": 3, "0xFD": 1, "0xFE": 2, "0xFF": 1}
REQUIRED_READER_COUNTS = {"0x0847": 2, "0x0957": 3, "0x0B8A": 1, "0x0D12": 1}
REQUIRED_PHASE_COUNTS = {"nonzero-0957-command-mix": 3, "nonzero-reader-coverage": 4}
REQUIRED_AFFECTED_COUNTS = {"return_stack_context": 3, "static_walk_blocker": 1, "timing_toggle_context": 3}
REQUIRED_CLASSIFICATIONS = {"ef_call_return", "timing_toggle", "earthbound_variant_ff", "unreachable", "unresolved"}
REQUIRED_POST_COMMANDS = {
    "python tools/validate_audio_nonzero_control_probe_packet.py",
    "python tools/run_audio_probe_campaign.py --lane nonzero --mode dry-run-stub --force",
    "python tools/run_audio_probe_campaign.py --lane nonzero --mode stub-shape --force",
    "python tools/collect_audio_nonzero_control_probe_results.py",
    "python tools/validate_audio_nonzero_control_probe_results_summary.py",
    "python tools/build_audio_sequence_semantics_intake_plan.py",
    "python tools/validate_audio_sequence_semantics_intake_plan.py",
    "python tools/validate_audio_duration_uncertainty_register.py",
    "python tools/build_audio_duration_readiness_rollup.py",
    "python tools/validate_audio_duration_readiness_rollup.py",
}
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate audio nonzero control probe packet.")
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


def validate_candidate(job_id: str, candidate: dict[str, Any]) -> None:
    require(int(candidate.get("track_id", 0)) > 0, f"{job_id}: invalid source candidate track id")
    require(candidate.get("track_name"), f"{job_id}: missing source candidate name")
    require(str(candidate.get("oracle_job_id", "")).startswith("oracle-track-"), f"{job_id}: missing oracle job id")
    source_spc = candidate.get("source_spc", {})
    source_render = candidate.get("source_render", {})
    require(str(source_spc.get("path", "")).endswith(".spc"), f"{job_id}: source SPC path missing")
    require(bool(SHA1_RE.match(str(source_spc.get("sha1", "")))), f"{job_id}: invalid source SPC sha1")
    require(int(source_spc.get("bytes", 0)) == 66048, f"{job_id}: source SPC byte count mismatch")
    require(str(source_render.get("path", "")).endswith(".wav"), f"{job_id}: source render path missing")
    require(bool(SHA1_RE.match(str(source_render.get("sha1", "")))), f"{job_id}: invalid source render sha1")
    require(int(source_render.get("bytes", 0)) > 0, f"{job_id}: source render byte count missing")


def validate_record(record: dict[str, Any], output_root: str) -> None:
    job_id = str(record.get("job_id"))
    command = str(record.get("command"))
    reader_pc = str(record.get("reader_pc"))
    require(job_id.startswith("nonzero-probe-"), f"{job_id}: unexpected job id")
    require(record.get("phase") in REQUIRED_PHASE_COUNTS, f"{job_id}: unexpected phase")
    require(command in REQUIRED_COMMAND_COUNTS, f"{job_id}: unexpected command")
    require(reader_pc in REQUIRED_READER_COUNTS, f"{job_id}: unexpected reader PC")
    require(str(record.get("driver_offset", "")).startswith("0x"), f"{job_id}: missing driver offset")
    require(int(record.get("read_count", 0)) > 0, f"{job_id}: missing read count")
    require(record.get("affected_kind") in REQUIRED_AFFECTED_COUNTS, f"{job_id}: unexpected affected kind")
    require(record.get("trace_focus"), f"{job_id}: missing trace focus")
    require(record.get("semantic_status"), f"{job_id}: missing semantic status")
    require(record.get("priority_reason"), f"{job_id}: missing priority reason")
    require(record.get("promotion_question"), f"{job_id}: missing promotion question")
    if command == "0xFF":
        require(reader_pc == "0x0957", f"{job_id}: FF should be at reader PC 0x0957")
        require(record.get("affected_kind") == "static_walk_blocker", f"{job_id}: FF affected kind mismatch")
    if command in {"0xFD", "0xFE"}:
        require(record.get("affected_kind") == "timing_toggle_context", f"{job_id}: timing affected kind mismatch")
    if command == "0xEF":
        require(record.get("affected_kind") == "return_stack_context", f"{job_id}: EF affected kind mismatch")
    require(set(record.get("accepted_control_effect_classifications", [])) == REQUIRED_CLASSIFICATIONS, f"{job_id}: classification set mismatch")
    require(len(record.get("required_capture_fields", [])) >= 20, f"{job_id}: capture fields missing")
    require(len(record.get("success_criteria", [])) >= 4, f"{job_id}: success criteria too thin")
    candidates = record.get("source_candidates", [])
    require(len(candidates) == int(record.get("source_candidate_count", -1)), f"{job_id}: source candidate count mismatch")
    for candidate in candidates:
        validate_candidate(job_id, candidate)
    outputs = record.get("probe_outputs", {})
    for key in ("root", "raw_trace", "result_json", "evidence_markdown"):
        require(output_path_is_under(output_root, str(outputs.get(key, ""))), f"{job_id}: bad output path {key}")
    require(str(outputs.get("result_json", "")).endswith("nonzero-control-proof-result.json"), f"{job_id}: bad result output")
    commands = record.get("commands", {})
    required_fragments = {
        "campaign_dry_run": "run_audio_probe_campaign.py --lane nonzero",
        "campaign_stub_shape": "run_audio_probe_campaign.py --lane nonzero",
        "external_run": "run_audio_nonzero_control_probe_batch.py",
        "stub_shape": "audio_nonzero_control_probe_stub_harness.py",
        "validate_result": "validate_audio_nonzero_control_probe_result.py",
        "collect_results": "collect_audio_nonzero_control_probe_results.py",
        "refresh_intake": "build_audio_sequence_semantics_intake_plan.py",
    }
    for key, fragment in required_fragments.items():
        require(fragment in str(commands.get(key, "")), f"{job_id}: missing command {key}")
    current = record.get("current_result_status", {})
    require(current.get("result_exists") is False, f"{job_id}: committed packet should not see real results")
    require(current.get("status") == "pending", f"{job_id}: missing result should be pending")
    require(current.get("valid") is False, f"{job_id}: missing result cannot be valid")
    require(current.get("control_effect_classification") == "pending", f"{job_id}: missing result classification should be pending")
    require("non_zero_control_semantics_pending" in current.get("remaining_blockers", []), f"{job_id}: nonzero blocker missing")
    require(record.get("promotion_allowed_by_packet") is False, f"{job_id}: promotion should be blocked")
    require(record.get("behavior_change_allowed") is False, f"{job_id}: behavior changes should be blocked")


def validate_batches(data: dict[str, Any]) -> None:
    batches = data.get("operator_batches", {})
    by_phase = {batch.get("phase"): int(batch.get("job_count", 0)) for batch in batches.get("by_phase", [])}
    by_command = {batch.get("command"): int(batch.get("job_count", 0)) for batch in batches.get("by_command", [])}
    by_reader = {batch.get("reader_pc"): int(batch.get("job_count", 0)) for batch in batches.get("by_reader_pc", [])}
    require(by_phase == REQUIRED_PHASE_COUNTS, "phase batch counts mismatch")
    require(by_command == REQUIRED_COMMAND_COUNTS, "command batch counts mismatch")
    require(by_reader == REQUIRED_READER_COUNTS, "reader batch counts mismatch")
    for group in ("by_phase", "by_command", "by_reader_pc"):
        for batch in batches.get(group, []):
            count = int(batch.get("job_count", 0))
            require(len(batch.get("job_ids", [])) == count, f"{group}: job count mismatch")
            require(len(batch.get("commands", [])) == count, f"{group}: command count mismatch")
            require(len(batch.get("reader_pcs", [])) == count, f"{group}: reader count mismatch")


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-nonzero-control-probe-packet.v1", "unexpected schema")
    require(data.get("status") == "nonzero_control_probe_packet_ready_external_harness_required", "unexpected status")
    require(data.get("source_plan_status") == "nonzero_control_probe_jobs_ready_runner_extension_pending", "unexpected plan status")
    require(data.get("source_coverage_status") == "nonzero_control_coverage_ready_probe_outputs_pending", "unexpected coverage status")
    require(data.get("source_campaign_status") == "probe_campaign_ready_for_external_harness_runs", "unexpected campaign status")
    require(data.get("source_results_status") == "nonzero_control_probe_results_collected", "unexpected results status")
    require(data.get("source_next_action_lane") == "nonzero_control_probe_import", "unexpected next-action lane")
    require(REQUIRED_REFERENCES <= set(data.get("references", [])), "missing references")
    summary = data.get("summary", {})
    records = data.get("records", [])
    require(int(summary.get("packet_job_count", 0)) == 7, "expected seven packet jobs")
    require(len(records) == 7, "record count mismatch")
    require(int(summary.get("blocker_track_count", 0)) == 155, "blocker count mismatch")
    require(int(summary.get("probe_job_count", 0)) == 7, "probe job count mismatch")
    require(int(summary.get("source_candidate_record_count", 0)) == 56, "source candidate count mismatch")
    require(int(summary.get("unique_source_candidate_track_count", 0)) == 10, "unique source candidate track count mismatch")
    require(int(summary.get("blocker_tracks_without_source_candidate_count", 0)) == 146, "missing source candidate count mismatch")
    require(summary.get("command_job_counts") == REQUIRED_COMMAND_COUNTS, "command counts mismatch")
    require(summary.get("reader_pc_job_counts") == REQUIRED_READER_COUNTS, "reader PC counts mismatch")
    require(summary.get("affected_kind_job_counts") == REQUIRED_AFFECTED_COUNTS, "affected kind counts mismatch")
    require(summary.get("phase_job_counts") == REQUIRED_PHASE_COUNTS, "phase counts mismatch")
    require(summary.get("command_job_counts") == count_records(records, "command"), "command counts do not match records")
    require(summary.get("reader_pc_job_counts") == count_records(records, "reader_pc"), "reader counts do not match records")
    require(summary.get("affected_kind_job_counts") == count_records(records, "affected_kind"), "affected counts do not match records")
    require(summary.get("phase_job_counts") == count_records(records, "phase"), "phase counts do not match records")
    require(int(summary.get("result_count", -1)) == 0, "committed packet should have zero real results")
    require(int(summary.get("valid_result_count", -1)) == 0, "committed packet should have zero valid results")
    require(summary.get("remaining_blocker_job_counts") == {
        "earthbound_variant_ff_effect": 1,
        "ef_call_return_effect": 3,
        "non_zero_control_semantics_pending": 7,
        "timing_toggle_effect": 3,
    }, "remaining blocker counts mismatch")
    require(set(summary.get("accepted_control_effect_classifications", [])) == REQUIRED_CLASSIFICATIONS, "accepted classifications mismatch")
    output_root = str(summary.get("generated_outputs_root", ""))
    require(output_root == "build/audio/nonzero-control-probe", "unexpected output root")
    require(summary.get("sequence_promotion_allowed") is False, "sequence promotion should be blocked")
    require(summary.get("public_exact_promotion_allowed") is False, "public exact promotion should be blocked")
    require(summary.get("promotion_allowed_by_packet") is False, "packet promotion should be blocked")
    require(summary.get("behavior_change_allowed") is False, "behavior changes should be blocked")
    seen_orders: set[int] = set()
    seen_jobs: set[str] = set()
    candidate_total = 0
    for record in records:
        order = int(record.get("execution_order", 0))
        job_id = str(record.get("job_id"))
        require(order not in seen_orders, f"{job_id}: duplicate order")
        require(job_id not in seen_jobs, f"{job_id}: duplicate job")
        seen_orders.add(order)
        seen_jobs.add(job_id)
        validate_record(record, output_root)
        candidate_total += len(record.get("source_candidates", []))
    require(seen_orders == set(range(1, 8)), "execution orders should be contiguous")
    require(candidate_total == 56, "source candidate record total mismatch")
    require({int(item["track_id"]) for item in data.get("source_candidate_tracks", [])} == {1, 17, 83, 84, 109, 110, 133, 137, 138, 139}, "source candidate track set mismatch")
    validate_batches(data)
    require(data.get("probe_packet_policy"), "missing packet policy")
    require(REQUIRED_POST_COMMANDS <= set(data.get("post_packet_validation_commands", [])), "missing post-packet validation commands")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.packet).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio nonzero control probe packet validation OK: "
        f"{data['summary']['packet_job_count']} jobs, "
        f"{data['summary']['blocker_track_count']} blockers"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
