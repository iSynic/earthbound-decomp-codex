from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
STATUS = ROOT / "manifests" / "coilsnake-phase2c-status.json"
VALID_BEHAVIORS = {
    "script-lowering",
    "fixed-byte",
    "bounded-insertion",
    "broad-repack",
}
VALID_LANES = {
    "authoring-lowering-only",
    "candidate-local-contract-update",
    "defer-runtime-promotion",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    if not STATUS.is_file():
        print(f"Phase 2C status not found: {STATUS}")
        return 2
    status = load_json(STATUS)
    problems: list[str] = []

    if status.get("schema") != "earthbound-decomp.coilsnake-phase2c-status.v1":
        problems.append("unexpected schema")

    experiments = status.get("experiments")
    if not isinstance(experiments, list):
        problems.append("experiments must be a list")
        experiments = []

    if status.get("experiment_count") != len(experiments):
        problems.append("experiment_count does not match experiments length")

    behavior_counts: dict[str, int] = {}
    lane_counts: dict[str, int] = {}
    seen_ids: set[str] = set()
    for index, experiment in enumerate(experiments):
        if not isinstance(experiment, dict):
            problems.append(f"experiment {index} is not an object")
            continue
        experiment_id = experiment.get("experiment_id")
        if not isinstance(experiment_id, str) or not experiment_id:
            problems.append(f"experiment {index} missing experiment_id")
        elif experiment_id in seen_ids:
            problems.append(f"duplicate experiment_id: {experiment_id}")
        else:
            seen_ids.add(experiment_id)

        behavior = experiment.get("behavior")
        if behavior not in VALID_BEHAVIORS:
            problems.append(f"{experiment_id}: invalid behavior {behavior!r}")
        else:
            behavior_counts[behavior] = behavior_counts.get(behavior, 0) + 1

        lane = experiment.get("promotion_lane")
        if lane not in VALID_LANES:
            problems.append(f"{experiment_id}: invalid promotion_lane {lane!r}")
        else:
            lane_counts[lane] = lane_counts.get(lane, 0) + 1

        changed_bytes = experiment.get("changed_bytes")
        runs = experiment.get("contiguous_changed_runs")
        if not isinstance(changed_bytes, int) or changed_bytes < 0:
            problems.append(f"{experiment_id}: changed_bytes must be a nonnegative integer")
        if not isinstance(runs, int) or runs < 0:
            problems.append(f"{experiment_id}: contiguous_changed_runs must be a nonnegative integer")

        if behavior == "fixed-byte" and not (changed_bytes <= 2 and runs == 1):
            problems.append(f"{experiment_id}: fixed-byte behavior does not match diff size")
        if behavior == "bounded-insertion" and not (changed_bytes <= 128 and runs <= 16):
            problems.append(f"{experiment_id}: bounded-insertion behavior does not match diff size")
        if behavior == "broad-repack" and not (changed_bytes > 128 or runs > 16):
            problems.append(f"{experiment_id}: broad-repack behavior does not match diff size")
        if behavior == "script-lowering" and experiment.get("kind") != "ccscript":
            problems.append(f"{experiment_id}: script-lowering must be a ccscript experiment")

    if status.get("behavior_counts") != dict(sorted(behavior_counts.items())):
        problems.append("behavior_counts are stale")
    if status.get("promotion_lane_counts") != dict(sorted(lane_counts.items())):
        problems.append("promotion_lane_counts are stale")

    scriptdump = status.get("scriptdump_roundtrip", {})
    if scriptdump.get("classification") != "compiler-normalized-roundtrip":
        problems.append("scriptdump roundtrip classification must remain compiler-normalized-roundtrip")
    if scriptdump.get("promotion_lane") != "authoring-oracle-only":
        problems.append("scriptdump roundtrip promotion lane must remain authoring-oracle-only")

    if problems:
        for problem in problems:
            print(f"ERROR: {problem}")
        return 1

    print(f"Validated {STATUS.relative_to(ROOT)}: {len(experiments)} experiments")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
