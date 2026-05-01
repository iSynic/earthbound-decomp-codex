from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "manifests" / "coilsnake-experiment-plan.json"
DEFAULT_CROSSWALK = ROOT / "manifests" / "coilsnake-crosswalk.json"
DEFAULT_PROJECT_DIR = ROOT / "build" / "coilsnake" / "baseline-project"

STATUSES = {
    "planned",
    "prepared-timeout-pending-rerun",
    "needs-match-review",
    "diff-confirmed",
    "retired",
}

REQUIRED_FIELDS = {
    "experiment_id",
    "batch",
    "priority",
    "resource_family",
    "source_file",
    "find",
    "replace",
    "expected_count",
    "edit_description",
    "promotion_target",
    "status",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def count_matches(project_dir: Path, source_file: str, needle: str) -> int | None:
    source_path = project_dir / source_file
    if not source_path.is_file():
        return None
    return source_path.read_text(encoding="utf-8").count(needle)


def validate_plan(plan_path: Path, crosswalk_path: Path, project_dir: Path) -> list[str]:
    problems: list[str] = []
    plan = load_json(plan_path)
    crosswalk = load_json(crosswalk_path)
    controlled_experiments = crosswalk.get("controlled_experiments", {})
    if not isinstance(controlled_experiments, dict):
        controlled_experiments = {}

    experiments = plan.get("planned_experiments", [])
    if not isinstance(experiments, list):
        return ["planned_experiments must be a list"]

    seen: set[str] = set()
    for index, experiment in enumerate(experiments):
        label = f"planned_experiments[{index}]"
        if not isinstance(experiment, dict):
            problems.append(f"{label}: entry must be an object")
            continue

        experiment_id = str(experiment.get("experiment_id", label))
        missing = sorted(REQUIRED_FIELDS - set(experiment))
        if missing:
            problems.append(f"{experiment_id}: missing required field(s): {', '.join(missing)}")

        if experiment_id in seen:
            problems.append(f"{experiment_id}: duplicate experiment_id")
        seen.add(experiment_id)

        if experiment_id in controlled_experiments and experiment.get("status") not in {"diff-confirmed", "retired"}:
            problems.append(f"{experiment_id}: already exists in crosswalk controlled_experiments")

        for key in ("batch", "resource_family", "source_file", "find", "replace", "edit_description", "promotion_target"):
            if key in experiment and (not isinstance(experiment[key], str) or not experiment[key]):
                problems.append(f"{experiment_id}: {key} must be a nonempty string")

        status = experiment.get("status")
        if status not in STATUSES:
            problems.append(f"{experiment_id}: invalid status: {status}")

        priority = experiment.get("priority")
        if not isinstance(priority, int) or priority < 0:
            problems.append(f"{experiment_id}: priority must be a nonnegative integer")

        expected_count = experiment.get("expected_count")
        if not isinstance(expected_count, int) or expected_count < 1:
            problems.append(f"{experiment_id}: expected_count must be a positive integer")
            continue

        source_file = experiment.get("source_file")
        find = experiment.get("find")
        if isinstance(source_file, str) and isinstance(find, str) and project_dir.is_dir():
            actual_count = count_matches(project_dir, source_file, find)
            if actual_count is None:
                problems.append(f"{experiment_id}: source file not found in project: {source_file}")
            elif actual_count != expected_count and status != "needs-match-review":
                problems.append(
                    f"{experiment_id}: expected {expected_count} text match(es) in {source_file}, found {actual_count}"
                )

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the planned CoilSnake edit experiment queue.")
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--project-dir", type=Path, default=DEFAULT_PROJECT_DIR)
    args = parser.parse_args()

    plan = args.plan.resolve()
    crosswalk = args.crosswalk.resolve()
    project_dir = args.project_dir.resolve()
    if not plan.is_file():
        print(f"Experiment plan not found: {plan}", file=sys.stderr)
        return 2
    if not crosswalk.is_file():
        print(f"Crosswalk manifest not found: {crosswalk}", file=sys.stderr)
        return 2

    problems = validate_plan(plan, crosswalk, project_dir)
    if problems:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        return 1

    experiment_count = len(load_json(plan).get("planned_experiments", []))
    project_note = rel(project_dir) if project_dir.is_dir() else "schema-only; baseline project not present"
    print(f"Validated {rel(plan)}: {experiment_count} planned experiments against {project_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
