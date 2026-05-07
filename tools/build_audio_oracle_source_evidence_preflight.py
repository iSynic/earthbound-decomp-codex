#!/usr/bin/env python3
"""Build a preflight report for oracle comparison source/reference evidence."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "manifests" / "audio-oracle-comparison-plan-all-tracks.json"
DEFAULT_VERIFICATION = ROOT / "manifests" / "audio-oracle-verification-report-all-tracks.json"
DEFAULT_HANDOFF = ROOT / "manifests" / "audio-independent-oracle-handoff-matrix.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-oracle-source-evidence-preflight.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-oracle-source-evidence-preflight.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build oracle source-evidence preflight report.")
    parser.add_argument("--plan", default=str(DEFAULT_PLAN), help="Oracle comparison plan JSON.")
    parser.add_argument("--verification", default=str(DEFAULT_VERIFICATION), help="All-track oracle verification report JSON.")
    parser.add_argument("--handoff", default=str(DEFAULT_HANDOFF), help="Independent oracle handoff matrix JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Preflight JSON output.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Preflight markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def exists(path_text: str) -> bool:
    return resolve_repo_path(path_text).exists()


def verification_gates(verification: dict[str, Any]) -> dict[str, Any]:
    gates = verification.get("gate_results", {})
    if isinstance(gates, dict):
        return gates
    return {}


def handoff_by_job(handoff: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(record.get("job_id")): record for record in handoff.get("records", [])}


def record_for_job(job: dict[str, Any], representative: dict[str, Any] | None) -> dict[str, Any]:
    source_spc = job.get("source_spc", {})
    source_render = job.get("source_render", {})
    outputs = job.get("reference_capture_outputs", {})
    path_status = {
        "source_spc_exists": exists(str(source_spc.get("path", ""))),
        "source_render_wav_exists": exists(str(source_render.get("path", ""))),
        "reference_spc_exists": exists(str(outputs.get("spc_snapshot", ""))),
        "reference_wav_exists": exists(str(outputs.get("pcm_wav", ""))),
        "capture_metadata_exists": exists(str(outputs.get("capture_metadata", ""))),
        "comparison_result_exists": exists(str(outputs.get("comparison_result", ""))),
    }
    blockers: list[str] = []
    if not path_status["source_spc_exists"]:
        blockers.append("missing_source_spc")
    if not path_status["source_render_wav_exists"]:
        blockers.append("missing_source_render_wav")
    if not path_status["reference_spc_exists"]:
        blockers.append("missing_reference_spc")
    if not path_status["reference_wav_exists"]:
        blockers.append("missing_reference_wav")
    if not path_status["capture_metadata_exists"]:
        blockers.append("missing_capture_metadata")
    if not path_status["comparison_result_exists"]:
        blockers.append("missing_comparison_result")
    if path_status["source_spc_exists"] and path_status["source_render_wav_exists"] and path_status["reference_spc_exists"] and path_status["reference_wav_exists"]:
        collect_status = "collector_ready_for_job"
    elif not path_status["source_spc_exists"] or not path_status["source_render_wav_exists"]:
        collect_status = "collector_blocked_missing_source_evidence"
    else:
        collect_status = "collector_pending_reference_capture"
    return {
        "job_id": job["job_id"],
        "track_id": int(job["track_id"]),
        "track_name": job["track_name"],
        "diagnostic_focus": job.get("diagnostic_focus"),
        "source_state": job.get("source_state"),
        "source_spc": {
            "path": source_spc.get("path"),
            "expected_sha1": source_spc.get("sha1"),
            "expected_bytes": source_spc.get("bytes"),
            "exists": path_status["source_spc_exists"],
        },
        "source_render": {
            "path": source_render.get("path"),
            "expected_sha1": source_render.get("sha1"),
            "expected_bytes": source_render.get("bytes"),
            "exists": path_status["source_render_wav_exists"],
        },
        "reference_outputs": {
            "spc_snapshot": outputs.get("spc_snapshot"),
            "spc_snapshot_exists": path_status["reference_spc_exists"],
            "pcm_wav": outputs.get("pcm_wav"),
            "pcm_wav_exists": path_status["reference_wav_exists"],
            "capture_metadata": outputs.get("capture_metadata"),
            "capture_metadata_exists": path_status["capture_metadata_exists"],
            "comparison_result": outputs.get("comparison_result"),
            "comparison_result_exists": path_status["comparison_result_exists"],
        },
        "independent_representative": representative is not None,
        "representative_phase": representative.get("phase") if representative else None,
        "representative_primary_uncertainty": representative.get("primary_uncertainty") if representative else None,
        "collector_preflight_status": collect_status,
        "blocking_reasons": blockers,
        "collect_summary_validation_ready": collect_status == "collector_ready_for_job",
        "behavior_change_allowed": False,
    }


def grouped(records: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[str(record.get(key))].append(record)
    batches: list[dict[str, Any]] = []
    for value, items in groups.items():
        items.sort(key=lambda item: int(item["track_id"]))
        batches.append(
            {
                key: value,
                "job_count": len(items),
                "track_ids": [int(item["track_id"]) for item in items],
                "job_ids": [str(item["job_id"]) for item in items],
            }
        )
    return sorted(batches, key=lambda item: (-int(item["job_count"]), str(item[key])))


def build_preflight(plan: dict[str, Any], verification: dict[str, Any], handoff: dict[str, Any]) -> dict[str, Any]:
    reps = handoff_by_job(handoff)
    records = [record_for_job(job, reps.get(str(job.get("job_id")))) for job in plan.get("jobs", [])]
    records.sort(key=lambda record: int(record["track_id"]))
    blocker_counts: Counter[str] = Counter()
    for record in records:
        blocker_counts.update(str(reason) for reason in record.get("blocking_reasons", []))
    status_counts = Counter(str(record.get("collector_preflight_status")) for record in records)
    focus_counts = Counter(str(record.get("diagnostic_focus")) for record in records)
    gates = verification_gates(verification)
    return {
        "schema": "earthbound-decomp.audio-oracle-source-evidence-preflight.v1",
        "status": "oracle_source_evidence_preflight_blocked_missing_ignored_artifacts",
        "references": [
            "manifests/audio-oracle-comparison-plan-all-tracks.json",
            "manifests/audio-oracle-verification-report-all-tracks.json",
            "manifests/audio-independent-oracle-handoff-matrix.json",
        ],
        "source_plan_status": plan.get("status"),
        "source_verification_status": verification.get("status"),
        "source_handoff_status": handoff.get("status"),
        "summary": {
            "job_count": len(records),
            "collector_ready_job_count": int(status_counts.get("collector_ready_for_job", 0)),
            "collector_blocked_missing_source_evidence_count": int(status_counts.get("collector_blocked_missing_source_evidence", 0)),
            "collector_pending_reference_capture_count": int(status_counts.get("collector_pending_reference_capture", 0)),
            "source_spc_present_count": sum(1 for record in records if record["source_spc"]["exists"]),
            "source_render_wav_present_count": sum(1 for record in records if record["source_render"]["exists"]),
            "reference_spc_present_count": sum(1 for record in records if record["reference_outputs"]["spc_snapshot_exists"]),
            "reference_wav_present_count": sum(1 for record in records if record["reference_outputs"]["pcm_wav_exists"]),
            "capture_metadata_present_count": sum(1 for record in records if record["reference_outputs"]["capture_metadata_exists"]),
            "comparison_result_present_count": sum(1 for record in records if record["reference_outputs"]["comparison_result_exists"]),
            "representative_job_count": sum(1 for record in records if record["independent_representative"]),
            "blocking_reason_counts": dict(sorted(blocker_counts.items())),
            "collector_preflight_status_counts": dict(sorted(status_counts.items())),
            "diagnostic_focus_counts": dict(sorted(focus_counts.items())),
            "representative_oracle_gate_passed": bool(gates.get("representative_oracle_gate_passed")),
            "all_track_oracle_gate_passed": bool(gates.get("all_track_oracle_gate_passed")),
            "independent_emulator_gate_passed": bool(gates.get("independent_emulator_gate_passed")),
            "release_quality_playback_claim_ready": bool(gates.get("release_quality_playback_claim_ready")),
            "behavior_change_allowed": False,
        },
        "operator_batches": {
            "by_collector_preflight_status": grouped(records, "collector_preflight_status"),
            "by_diagnostic_focus": grouped(records, "diagnostic_focus"),
            "by_representative_phase": grouped(
                [record for record in records if record["independent_representative"]],
                "representative_phase",
            ),
        },
        "preflight_policy": [
            "This report audits local ignored oracle evidence paths only; it does not collect or compare audio.",
            "Source SPC/WAV artifacts and external reference SPC/WAV artifacts are generated evidence under build/audio.",
            "The all-track verification report can remain green while this collector preflight is blocked in a clean workspace.",
            "Run source render/capture generation before collecting oracle comparison summaries from this plan.",
            "This preflight cannot promote playback, exact durations, loop metadata, or release-quality claims.",
        ],
        "records": records,
        "post_preflight_validation_commands": [
            "python tools/build_audio_oracle_source_evidence_preflight.py",
            "python tools/validate_audio_oracle_source_evidence_preflight.py",
            "python tools/validate_audio_oracle_comparison_plan.py manifests/audio-oracle-comparison-plan-all-tracks.json --allow-missing-source-outputs",
            "python tools/validate_audio_oracle_verification_report.py manifests/audio-oracle-verification-report-all-tracks.json --require-representative-pass",
            "python tools/validate_audio_independent_oracle_handoff_matrix.py",
            "python tools/validate_audio_independent_oracle_capture_packet.py",
        ],
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    status_rows = [
        "| `{status}` | {count} | `{tracks}` |".format(
            status=batch["collector_preflight_status"],
            count=batch["job_count"],
            tracks=batch["track_ids"][:24],
        )
        for batch in data["operator_batches"]["by_collector_preflight_status"]
    ]
    representative_rows = [
        "| {track:03d} | `{name}` | `{phase}` | `{uncertainty}` | `{status}` |".format(
            track=record["track_id"],
            name=record["track_name"],
            phase=record["representative_phase"],
            uncertainty=record["representative_primary_uncertainty"],
            status=record["collector_preflight_status"],
        )
        for record in data["records"]
        if record["independent_representative"]
    ]
    commands = [f"- `{command}`" for command in data["post_preflight_validation_commands"]]
    return "\n".join(
        [
            "# Audio Oracle Source Evidence Preflight",
            "",
            "Status: oracle comparison collection is blocked in this workspace by missing ignored source/reference artifacts; playback/export behavior is preserved.",
            "",
            "## Summary",
            "",
            f"- jobs: `{summary['job_count']}`",
            f"- collector-ready jobs: `{summary['collector_ready_job_count']}`",
            f"- missing-source blocked jobs: `{summary['collector_blocked_missing_source_evidence_count']}`",
            f"- source SPC present: `{summary['source_spc_present_count']}`",
            f"- source render WAV present: `{summary['source_render_wav_present_count']}`",
            f"- reference SPC present: `{summary['reference_spc_present_count']}`",
            f"- reference WAV present: `{summary['reference_wav_present_count']}`",
            f"- capture metadata present: `{summary['capture_metadata_present_count']}`",
            f"- comparison results present: `{summary['comparison_result_present_count']}`",
            f"- representative jobs: `{summary['representative_job_count']}`",
            f"- blocking reasons: `{summary['blocking_reason_counts']}`",
            f"- near-oracle gates: representative `{summary['representative_oracle_gate_passed']}`, all-track `{summary['all_track_oracle_gate_passed']}`",
            f"- independent gate passed: `{summary['independent_emulator_gate_passed']}`",
            "",
            "## Collector Status Batches",
            "",
            "| Status | Jobs | First tracks |",
            "| --- | ---: | --- |",
            *status_rows,
            "",
            "## Representative Handoff Tracks",
            "",
            "| Track | Name | Phase | Primary uncertainty | Collector status |",
            "| ---: | --- | --- | --- | --- |",
            *representative_rows,
            "",
            "## Validation",
            "",
            *commands,
            "",
            "## Preflight Policy",
            "",
            *[f"- {item}" for item in data["preflight_policy"]],
            "",
            "## Remaining Uncertainty",
            "",
            "- The committed all-track oracle report remains green from existing verification evidence.",
            "- The local collect-summary path needs regenerated source SPC/WAV evidence before it can validate in this workspace.",
            "- Independent emulator release-quality evidence still requires the 16 representative external captures.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    data = build_preflight(
        load_json(Path(args.plan)),
        load_json(Path(args.verification)),
        load_json(Path(args.handoff)),
    )
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built oracle source evidence preflight: "
        f"{data['summary']['collector_ready_job_count']} ready, "
        f"{data['summary']['collector_blocked_missing_source_evidence_count']} source-blocked"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
