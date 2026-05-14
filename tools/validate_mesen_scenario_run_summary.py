#!/usr/bin/env python3
"""Validate ignored Mesen scenario runner summaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SUMMARY = ROOT / "build" / "mesen-scenarios" / "runs" / "srm-stonehenge-base-resource-scout" / "scenario-run-summary.json"
SCHEMA = "earthbound-decomp.mesen-scenario-run.v1"
STATUSES = {"dry_run", "pending", "completed", "failed"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", nargs="?", default=str(DEFAULT_SUMMARY))
    return parser.parse_args()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    require(data.get("schema") == SCHEMA, f"bad schema {data.get('schema')}", errors)
    require(str(data.get("status")) in STATUSES, f"bad status {data.get('status')}", errors)
    require(str(data.get("scenario_id", "")), "missing scenario_id", errors)
    require(str(data.get("evidence_tier", "")), "missing evidence_tier", errors)
    require(str(data.get("oracle_id", "")), "missing oracle_id", errors)
    require(data.get("source_promotion_allowed") is False, "source promotion must stay blocked", errors)
    require(isinstance(data.get("command"), list) and data.get("command"), "command missing", errors)
    metadata = data.get("scenario_run_metadata", {})
    require(isinstance(metadata, dict), "scenario_run_metadata must be object", errors)
    if isinstance(metadata, dict) and metadata.get("srm_anchor_id"):
        expected = str(metadata.get("srm_expected_sha256", ""))
        copied = str(metadata.get("srm_copied_sha256", ""))
        require(len(expected) == 64, "SRM expected SHA-256 missing/bad", errors)
        require(copied == expected, "copied SRM hash must match catalog hash", errors)
        require(metadata.get("post_resume_snapshot_required") is True, "SRM run must require post-resume snapshot proof", errors)
        bootstrap_status = str(metadata.get("bootstrap_status", ""))
        resume_status = str(metadata.get("resume_proof_status", ""))
        post_resume_seen = metadata.get("post_resume_snapshot_seen") is True
        if bootstrap_status == "launch_smoke_only_post_resume_pending":
            require(resume_status == "not_proven", "launch-smoke SRM run must not claim resume proof", errors)
            require(not post_resume_seen, "launch-smoke SRM run must not claim post-resume snapshot", errors)
        if bootstrap_status == "post_resume_snapshot_observed":
            require(resume_status == "proven", "post-resume SRM run must claim proven resume", errors)
            require(post_resume_seen, "post-resume SRM run must record snapshot proof", errors)
    return errors


def main() -> int:
    args = parse_args()
    summary = Path(args.summary)
    data = load_json(summary)
    errors = validate(data)
    if errors:
        print("Mesen scenario run summary validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Mesen scenario run summary validation OK: {data['scenario_id']} ({data['status']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
