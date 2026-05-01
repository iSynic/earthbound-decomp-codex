from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "manifests" / "coilsnake-experiment-plan.json"
DEFAULT_RUNNER = ROOT / "tools" / "run_coilsnake_edit_experiment.py"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def find_experiment(plan: dict[str, Any], experiment_id: str) -> dict[str, Any] | None:
    experiments = plan.get("planned_experiments", [])
    if not isinstance(experiments, list):
        return None
    for experiment in experiments:
        if isinstance(experiment, dict) and experiment.get("experiment_id") == experiment_id:
            return experiment
    return None


def build_command(
    *,
    runner: Path,
    experiment: dict[str, Any],
    dry_run: bool,
    compile_timeout_seconds: int | None,
) -> list[str]:
    command = [
        sys.executable,
        str(runner),
        "--experiment-id",
        str(experiment["experiment_id"]),
        "--source-file",
        str(experiment["source_file"]),
        "--find",
        str(experiment["find"]),
        "--replace",
        str(experiment["replace"]),
        "--expected-count",
        str(experiment["expected_count"]),
        "--resource-family",
        str(experiment["resource_family"]),
        "--edit-description",
        str(experiment["edit_description"]),
    ]
    if compile_timeout_seconds is not None:
        command.extend(["--compile-timeout-seconds", str(compile_timeout_seconds)])
    if dry_run:
        command.append("--dry-run")
    return command


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one planned CoilSnake edit experiment by id.")
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--runner", type=Path, default=DEFAULT_RUNNER)
    parser.add_argument("--compile-timeout-seconds", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--print-command", action="store_true")
    args = parser.parse_args()

    plan_path = args.plan.resolve()
    runner = args.runner.resolve()
    if not plan_path.is_file():
        print(f"Experiment plan not found: {plan_path}", file=sys.stderr)
        return 2
    if not runner.is_file():
        print(f"Experiment runner not found: {runner}", file=sys.stderr)
        return 2

    plan = load_json(plan_path)
    experiment = find_experiment(plan, args.experiment_id)
    if experiment is None:
        print(f"Planned experiment not found: {args.experiment_id}", file=sys.stderr)
        return 2

    compile_timeout_seconds = args.compile_timeout_seconds
    if compile_timeout_seconds is None:
        experiment_timeout = experiment.get("compile_timeout_seconds")
        plan_timeout = plan.get("default_compile_timeout_seconds")
        if isinstance(experiment_timeout, int):
            compile_timeout_seconds = experiment_timeout
        elif isinstance(plan_timeout, int):
            compile_timeout_seconds = plan_timeout

    command = build_command(
        runner=runner,
        experiment=experiment,
        dry_run=args.dry_run,
        compile_timeout_seconds=compile_timeout_seconds,
    )
    print(" ".join(command))
    if args.print_command:
        return 0
    return subprocess.run(command, cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
