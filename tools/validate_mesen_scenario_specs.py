#!/usr/bin/env python3
"""Validate sanitized Mesen scenario specs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "mesen-scenario-specs.json"
SCHEMA = "earthbound-decomp.mesen-scenario-spec-index.v1"
STATUS = "scenario_specs_generated_local_paths_ignored"
START_TYPES = {"load_state", "load_srm_anchor"}
TIERS = {"vanilla_save_state", "vanilla_srm_plus_input", "runtime_steered", "fixture_rom_or_game_genie"}
BOOTSTRAP_STATUSES = {
    "ready",
    "launch_smoke_only_post_resume_pending",
    "post_resume_snapshot_observed",
}
RESUME_PROOF_STATUSES = {"not_applicable", "not_proven", "proven"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    return parser.parse_args()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    require(data.get("schema") == SCHEMA, f"bad schema {data.get('schema')}", errors)
    require(data.get("status") == STATUS, f"bad status {data.get('status')}", errors)
    scenarios = data.get("scenarios")
    require(isinstance(scenarios, list) and scenarios, "scenarios must be a non-empty list", errors)
    if isinstance(scenarios, list):
        ids: set[str] = set()
        for index, spec in enumerate(scenarios):
            prefix = f"scenario {index}"
            scenario_id = str(spec.get("scenario_id", ""))
            require(scenario_id and scenario_id not in ids, f"{prefix}: duplicate/missing scenario_id", errors)
            ids.add(scenario_id)
            require(str(spec.get("evidence_tier")) in TIERS, f"{prefix}: bad evidence tier", errors)
            require(spec.get("source_promotion_allowed") is False, f"{prefix}: source promotion must be blocked", errors)
            require(str(spec.get("oracle_id", "")), f"{prefix}: oracle_id missing", errors)
            require(str(spec.get("input_pattern", "")), f"{prefix}: input_pattern missing", errors)
            require(isinstance(spec.get("watched_routines"), list), f"{prefix}: watched_routines not list", errors)
            start = spec.get("start", {})
            require(isinstance(start, dict), f"{prefix}: start not object", errors)
            if isinstance(start, dict):
                start_type = str(start.get("type", ""))
                require(start_type in START_TYPES, f"{prefix}: bad start type {start_type}", errors)
                require("state_path_local_only" not in start, f"{prefix}: leaked local state path", errors)
                require("working_srm_path_local_only" not in start, f"{prefix}: leaked local SRM path", errors)
                if start_type == "load_state":
                    require(str(start.get("state_basename", "")).endswith(".mss"), f"{prefix}: missing state basename", errors)
                    require(len(str(start.get("state_sha256", ""))) == 64, f"{prefix}: bad state hash", errors)
                if start_type == "load_srm_anchor":
                    require(str(start.get("anchor_id", "")), f"{prefix}: missing anchor id", errors)
                    require(len(str(start.get("srm_sha256", ""))) == 64, f"{prefix}: bad SRM hash", errors)
                    bootstrap_status = str(spec.get("bootstrap_status", ""))
                    require(bootstrap_status in BOOTSTRAP_STATUSES, f"{prefix}: bad bootstrap status", errors)
                    require(str(spec.get("bootstrap_input_pattern", "")), f"{prefix}: missing bootstrap input pattern", errors)
                    require(isinstance(spec.get("bootstrap_frame_count"), int), f"{prefix}: bootstrap frame count not integer", errors)
                    require(spec.get("post_resume_snapshot_required") is True, f"{prefix}: SRM specs must require post-resume snapshot proof", errors)
                    resume_status = str(spec.get("resume_proof_status", ""))
                    require(resume_status in RESUME_PROOF_STATUSES, f"{prefix}: bad resume proof status", errors)
                    if bootstrap_status in {"ready", "post_resume_snapshot_observed"}:
                        require(
                            str(spec.get("bootstrap_input_pattern")) != "not_implemented",
                            f"{prefix}: ready SRM bootstrap must use a real input pattern",
                            errors,
                        )
                        require(int(spec.get("bootstrap_frame_count", 0)) > 0, f"{prefix}: ready SRM bootstrap needs frames", errors)
                    if bootstrap_status == "launch_smoke_only_post_resume_pending":
                        require(resume_status == "not_proven", f"{prefix}: launch-smoke SRM status must not claim resume proof", errors)
                    if bootstrap_status == "post_resume_snapshot_observed":
                        require(resume_status == "proven", f"{prefix}: post-resume bootstrap status must claim proven resume", errors)
    summary = data.get("summary", {})
    if isinstance(scenarios, list):
        require(summary.get("scenario_count") == len(scenarios), "summary scenario_count mismatch", errors)
    require(summary.get("source_promotion_allowed") is False, "summary source promotion must be blocked", errors)
    return errors


def main() -> int:
    args = parse_args()
    data = load_json(Path(args.manifest))
    errors = validate(data)
    if errors:
        print("Mesen scenario spec validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Mesen scenario spec validation OK: {data['summary']['scenario_count']} scenarios")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
