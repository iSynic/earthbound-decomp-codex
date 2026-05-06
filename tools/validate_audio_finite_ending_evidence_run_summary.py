#!/usr/bin/env python3
"""Validate an ignored audio finite-ending evidence run summary."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SUMMARY = ROOT / "build" / "audio" / "finite-ending-evidence-runs" / "finite-ending-evidence-run-summary.json"
VALID_STATUSES = {"finite_ending_evidence_ready", "pending_finite_ending_evidence"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate audio finite-ending evidence run summary.")
    parser.add_argument("summary", nargs="?", default=str(DEFAULT_SUMMARY))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def count_runs(runs: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for run in runs:
        counts[str(run.get(key))] += 1
    return dict(sorted(counts.items()))


def list_count_runs(runs: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for run in runs:
        for item in run.get(key, []):
            counts[str(item)] += 1
    return dict(sorted(counts.items()))


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-finite-ending-evidence-run.v1", "unexpected schema")
    require(data.get("plan") == "manifests/audio-finite-ending-evidence-plan.json", "unexpected plan")
    require(data.get("plan_status") == "finite_ending_evidence_plan_ready_preview_policy_preserved", "unexpected plan status")
    require(data.get("mode") in {"dry-run-plan", "audit-current-export"}, f"unexpected mode {data.get('mode')}")
    require(data.get("promotion_allowed_by_run") is False, "run must not allow promotion")
    runs = data.get("runs", [])
    require(len(runs) > 0, "run summary should include at least one selected job")
    require(int(data.get("selected_count", -1)) == len(runs), "selected count mismatch")
    ready_count = sum(1 for run in runs if run.get("status") == "finite_ending_evidence_ready")
    pending_count = sum(1 for run in runs if run.get("status") == "pending_finite_ending_evidence")
    require(int(data.get("finite_ending_evidence_ready_count", -1)) == ready_count, "ready count mismatch")
    require(int(data.get("pending_finite_ending_evidence_count", -1)) == pending_count, "pending count mismatch")
    require(ready_count + pending_count == len(runs), "status counts do not cover selected runs")
    require(data.get("status_counts") == count_runs(runs, "status"), "status counts mismatch")
    require(data.get("evidence_status_counts") == count_runs(runs, "evidence_status"), "evidence status counts mismatch")
    require(data.get("blocking_reason_counts") == list_count_runs(runs, "blocking_reasons"), "blocking reason counts mismatch")
    require(data.get("diagnostic_focus_counts") == count_runs(runs, "diagnostic_focus"), "focus counts mismatch")
    require(
        int(data.get("nonzero_after_candidate_end_count", -1))
        == sum(1 for run in runs if run.get("nonzero_after_candidate_end") is True),
        "post-candidate nonzero count mismatch",
    )
    require(
        data.get("public_exact_finite_export_ready_by_run") is (pending_count == 0 and len(runs) > 0),
        "public exact readiness flag mismatch",
    )

    seen_orders: set[int] = set()
    previous_order = 0
    for run in runs:
        job_id = str(run.get("job_id", ""))
        order = int(run.get("execution_order", 0))
        status = str(run.get("status"))
        require(order > 0, f"{job_id}: invalid execution order")
        require(order not in seen_orders, f"{job_id}: duplicate execution order")
        require(order >= previous_order, f"{job_id}: run order is not sorted")
        previous_order = order
        seen_orders.add(order)
        require(job_id.startswith("finite-ending-track-"), f"{job_id}: unexpected job id")
        require(status in VALID_STATUSES, f"{job_id}: unexpected status {status}")
        require(int(run.get("track_id", -1)) > 0, f"{job_id}: invalid track id")
        require(run.get("diagnostic_focus"), f"{job_id}: missing diagnostic focus")
        require(run.get("promotion_allowed_by_run") is False, f"{job_id}: run promoted unexpectedly")
        reasons = run.get("blocking_reasons", [])
        require(isinstance(reasons, list), f"{job_id}: blocking reasons must be a list")
        if status == "finite_ending_evidence_ready":
            require(not reasons, f"{job_id}: ready run has blocking reasons")
        else:
            require(bool(reasons), f"{job_id}: pending run lacks blocking reasons")
        if data.get("mode") == "dry-run-plan":
            require(run.get("evidence_status") == "not_audited", f"{job_id}: dry run should be not_audited")
            require(reasons == ["finite_ending_evidence_not_audited"], f"{job_id}: dry run reason mismatch")
        else:
            require(run.get("evidence_status") == "finite_tail_review_pending", f"{job_id}: expected current pending status")
            require("finite_tail_review_pending" in reasons, f"{job_id}: missing finite tail blocker")
            require("missing_explicit_tail_classification" in reasons, f"{job_id}: missing classification blocker")
            require("nonzero_pcm_after_candidate_end" in reasons, f"{job_id}: missing post-candidate PCM blocker")
            require("public_exact_export_blocked" in reasons, f"{job_id}: missing public exact blocker")
            require("sequence_semantics_required" in reasons, f"{job_id}: missing sequence semantics blocker")
            require(run.get("nonzero_after_candidate_end") is True, f"{job_id}: expected nonzero PCM after candidate")
            require(int(run.get("last_nonzero_sample_index", -1)) >= int(run.get("finite_end_sample", 0)), f"{job_id}: bad tail ordering")
            require(run.get("public_exact_export_allowed") is False, f"{job_id}: public exact export should remain blocked")
            require(run.get("needs_sequence_semantics") is True, f"{job_id}: expected sequence semantics gate")

    require(data.get("selection") is not None, "missing selection")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio finite-ending evidence run summary validation OK: "
        f"{data['finite_ending_evidence_ready_count']} ready, "
        f"{data['pending_finite_ending_evidence_count']} pending"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
