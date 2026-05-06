#!/usr/bin/env python3
"""Collect targeted 0x00 runtime probe result status."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import validate_audio_zero_runtime_probe_result


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "manifests" / "audio-zero-runtime-probe-plan.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-zero-runtime-probe-results-summary.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-zero-runtime-probe-results-summary.md"

RESOLVED_CLASSIFICATIONS = {"true_end", "ef_return", "loop_or_hold_continues"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect audio 0x00 runtime probe result status.")
    parser.add_argument("--plan", default=str(DEFAULT_PLAN), help="Probe plan manifest.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Summary JSON output.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Summary markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def result_path(job: dict[str, Any]) -> Path:
    return resolve_repo_path(str(job.get("probe_outputs", {}).get("result_json", "")))


def manifest_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def result_resolves_zero_proof(result: dict[str, Any] | None, valid: bool) -> bool:
    if not valid or result is None:
        return False
    return str(result.get("zero_effect_classification")) in RESOLVED_CLASSIFICATIONS


def result_resolves_ef_model(result: dict[str, Any] | None, valid: bool) -> bool:
    if not valid or result is None:
        return False
    return bool(result.get("ef_stack_observations")) and str(result.get("zero_effect_classification")) in RESOLVED_CLASSIFICATIONS


def remaining_blockers(job: dict[str, Any], result: dict[str, Any] | None, valid: bool) -> list[str]:
    blockers: list[str] = []
    original = set(job.get("pre_promotion_blockers", []))
    if "zero_runtime_effect_proof" in original and not result_resolves_zero_proof(result, valid):
        blockers.append("zero_runtime_effect_proof")
    if "ef_return_stack_model" in original and not result_resolves_ef_model(result, valid):
        blockers.append("ef_return_stack_model")
    action = str(job.get("post_zero_proof_action"))
    if action == "decode_loop_points_before_exact_export":
        blockers.append("loop_point_metadata")
    elif action == "review_observed_silence_as_finite_or_transition":
        blockers.append("finite_transition_review")
    elif action == "classify_active_preview_before_exact_export":
        blockers.append("active_preview_classification")
    return blockers


def collect(plan: dict[str, Any]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    validation_counts: Counter[str] = Counter()
    classification_counts: Counter[str] = Counter()
    blocker_counts: Counter[str] = Counter()
    proven_track_ids: list[int] = []

    for job in plan.get("jobs", []):
        path = result_path(job)
        record: dict[str, Any] = {
            "job_id": job["job_id"],
            "track_id": int(job["track_id"]),
            "track_name": job["track_name"],
            "pack_id": int(job["pack_id"]),
            "trace_focus": job["trace_focus"],
            "post_zero_proof_action": job["post_zero_proof_action"],
            "result_path": manifest_path(path),
            "result_exists": path.exists(),
            "status": "pending",
            "valid": False,
            "zero_effect_classification": "pending",
            "errors": [],
            "remaining_blockers": [],
            "promotion_allowed": False,
        }
        result: dict[str, Any] | None = None
        if path.exists():
            result = load_json(path)
            errors = validate_audio_zero_runtime_probe_result.validate(result, job)
            record["status"] = str(result.get("status", "unknown"))
            record["valid"] = not errors
            record["zero_effect_classification"] = str(result.get("zero_effect_classification", "unknown"))
            record["errors"] = errors
            record["promotion_allowed"] = bool(result.get("promotion_allowed_by_result"))
            if result_resolves_zero_proof(result, record["valid"]):
                proven_track_ids.append(int(job["track_id"]))
        record["remaining_blockers"] = remaining_blockers(job, result, bool(record["valid"]))
        for blocker in record["remaining_blockers"]:
            blocker_counts[str(blocker)] += 1
        status_counts[str(record["status"])] += 1
        validation_counts["valid" if record["valid"] else "invalid_or_pending"] += 1
        classification_counts[str(record["zero_effect_classification"])] += 1
        records.append(record)

    return {
        "schema": "earthbound-decomp.audio-zero-runtime-probe-results-summary.v1",
        "status": "zero_runtime_probe_results_collected",
        "probe_plan": "manifests/audio-zero-runtime-probe-plan.json",
        "source_policy": plan.get("source_policy", {}),
        "summary": {
            "job_count": len(records),
            "result_count": sum(1 for record in records if record["result_exists"]),
            "valid_result_count": sum(1 for record in records if record["valid"]),
            "status_counts": dict(sorted(status_counts.items())),
            "validation_counts": dict(sorted(validation_counts.items())),
            "zero_effect_classification_counts": dict(sorted(classification_counts.items())),
            "remaining_blocker_track_counts": dict(sorted(blocker_counts.items())),
            "proven_zero_effect_track_ids": proven_track_ids,
            "sequence_promotion_allowed": False,
            "semantic_status": "zero_runtime_probe_outputs_pending" if not proven_track_ids else "zero_runtime_probe_outputs_partially_collected",
        },
        "result_acceptance_policy": [
            "A result can resolve zero_runtime_effect_proof only when it validates and classifies 0x00 as true_end, ef_return, or loop_or_hold_continues.",
            "A result can resolve ef_return_stack_model only when it validates, includes EF stack observations, and has a resolved 0x00 classification.",
            "Loop-point metadata, finite/transition review, and active-preview classification remain separate post-proof blockers.",
            "This summary cannot directly promote public exact-duration exports.",
        ],
        "results": records,
        "next_work": [
            "run the zero probe jobs after the ares harness emits the widened trace contract",
            "review invalid or unresolved probe outputs before changing duration policy",
            "feed only validated true_end/ef_return/loop_or_hold_continues classifications back into triage",
        ],
    }


def render_markdown(summary: dict[str, Any]) -> str:
    stats = summary["summary"]
    rows = [
        "| `{track_id:03d}` | `{track_name}` | `{status}` | `{valid}` | `{classification}` | `{blockers}` | `{result_path}` |".format(
            track_id=record["track_id"],
            track_name=record["track_name"],
            status=record["status"],
            valid=record["valid"],
            classification=record["zero_effect_classification"],
            blockers=record["remaining_blockers"],
            result_path=record["result_path"],
        )
        for record in summary["results"]
    ]
    return "\n".join(
        [
            "# Audio 0x00 Runtime Probe Results Summary",
            "",
            "Status: no public export behavior changes; probe outputs are collected only when local ignored result files exist.",
            "",
            "## Summary",
            "",
            f"- probe jobs: `{stats['job_count']}`",
            f"- result files found: `{stats['result_count']}`",
            f"- valid results: `{stats['valid_result_count']}`",
            f"- statuses: `{stats['status_counts']}`",
            f"- validation: `{stats['validation_counts']}`",
            f"- classifications: `{stats['zero_effect_classification_counts']}`",
            f"- remaining blockers: `{stats['remaining_blocker_track_counts']}`",
            f"- proven zero-effect tracks: `{stats['proven_zero_effect_track_ids']}`",
            f"- sequence promotion allowed: `{stats['sequence_promotion_allowed']}`",
            "",
            "## Acceptance Policy",
            "",
            *[f"- {item}" for item in summary["result_acceptance_policy"]],
            "",
            "## Results",
            "",
            "| Track | Name | Status | Valid | 0x00 classification | Remaining blockers | Result path |",
            "| ---: | --- | --- | --- | --- | --- | --- |",
            *rows,
            "",
            "## Next Work",
            "",
            *[f"- {item}" for item in summary["next_work"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    summary = collect(load_json(Path(args.plan)))
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(summary), encoding="utf-8")
    print(
        "Collected audio 0x00 runtime probe results: "
        f"{summary['summary']['result_count']} / {summary['summary']['job_count']} result files, "
        f"remaining blockers {summary['summary']['remaining_blocker_track_counts']}"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
