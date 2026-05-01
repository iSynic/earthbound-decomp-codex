from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_coilsnake_project_inventory import diff_roms


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROJECT_DIR = ROOT / "build" / "coilsnake" / "baseline-project"
DEFAULT_BASE_EXPANDED_ROM = ROOT / "build" / "coilsnake" / "base-expanded.sfc"
DEFAULT_BASELINE_REBUILD_ROM = ROOT / "build" / "coilsnake" / "baseline-rebuild.sfc"
DEFAULT_EXPERIMENTS_DIR = ROOT / "build" / "coilsnake" / "edit-experiments"
DEFAULT_COILSNAKE_EXE = ROOT / "build" / "coilsnake" / "tools" / "CoilSnake-4.2.exe"
DEFAULT_COMPILE_TIMEOUT_SECONDS = 600


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def require_inside(path: Path, parent: Path) -> None:
    resolved = path.resolve()
    resolved_parent = parent.resolve()
    if resolved != resolved_parent and resolved_parent not in resolved.parents:
        raise ValueError(f"Refusing to write outside {resolved_parent}: {resolved}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one controlled CoilSnake edit/rebuild/diff experiment."
    )
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--source-file", required=True, help="Path inside the CoilSnake project.")
    parser.add_argument("--find", required=True, help="Exact text to replace.")
    parser.add_argument("--replace", required=True, help="Replacement text.")
    parser.add_argument("--edit-description", required=True)
    parser.add_argument("--resource-family", default="uncategorized")
    parser.add_argument("--expected-count", type=int, default=1)
    parser.add_argument("--project-dir", type=Path, default=DEFAULT_PROJECT_DIR)
    parser.add_argument("--base-expanded-rom", type=Path, default=DEFAULT_BASE_EXPANDED_ROM)
    parser.add_argument("--baseline-rebuild-rom", type=Path, default=DEFAULT_BASELINE_REBUILD_ROM)
    parser.add_argument("--experiments-dir", type=Path, default=DEFAULT_EXPERIMENTS_DIR)
    parser.add_argument("--coilsnake", type=Path, default=DEFAULT_COILSNAKE_EXE)
    parser.add_argument(
        "--compile-timeout-seconds",
        type=int,
        default=DEFAULT_COMPILE_TIMEOUT_SECONDS,
        help="Abort CoilSnake compile after this many seconds and still write a report.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Apply checks but do not copy or compile.")
    return parser.parse_args()


def copy_project(source: Path, destination: Path, experiments_dir: Path) -> None:
    require_inside(destination, experiments_dir)
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def apply_text_edit(path: Path, find: str, replace: str, expected_count: int) -> int:
    text = path.read_text(encoding="utf-8")
    count = text.count(find)
    if count != expected_count:
        raise ValueError(
            f"Expected {expected_count} match(es) in {path}, found {count}"
        )
    path.write_text(text.replace(find, replace), encoding="utf-8")
    return count


def run_compile(
    coilsnake: Path,
    project: Path,
    base_rom: Path,
    output_rom: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    output_rom.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(coilsnake),
        "--verbose",
        "compile",
        str(project),
        str(base_rom),
        str(output_rom),
    ]
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout_seconds,
        )
        return {
            "command": command,
            "returncode": result.returncode,
            "timed_out": False,
            "output_tail": result.stdout.splitlines()[-40:],
        }
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
        return {
            "command": command,
            "returncode": None,
            "timed_out": True,
            "timeout_seconds": timeout_seconds,
            "output_tail": str(output).splitlines()[-40:],
        }


def build_report(
    *,
    experiment_id: str,
    resource_family: str,
    source_file: str,
    edit_description: str,
    project_copy: Path,
    rebuilt_rom: Path,
    baseline_rebuild_rom: Path,
    compile_result: dict[str, Any] | None,
    diff: dict[str, Any] | None,
    dry_run: bool,
    status: str,
    prepared_at: str | None = None,
) -> dict[str, Any]:
    return {
        "experiment_id": experiment_id,
        "status": status,
        "resource_family": resource_family,
        "source_file": source_file,
        "edit": edit_description,
        "evidence_level": "diff-confirmed" if diff and diff.get("status") == "different" else "coilsnake-observed",
        "comparison_base": rel(baseline_rebuild_rom),
        "project_copy": rel(project_copy),
        "rebuilt_rom": rel(rebuilt_rom),
        "dry_run": dry_run,
        "compile": compile_result,
        "diff": diff,
        "prepared_at": prepared_at,
    }


def write_report(report_path: Path, report: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    project_dir = args.project_dir.resolve()
    base_expanded_rom = args.base_expanded_rom.resolve()
    baseline_rebuild_rom = args.baseline_rebuild_rom.resolve()
    experiments_dir = args.experiments_dir.resolve()
    experiment_dir = experiments_dir / args.experiment_id
    project_copy = experiment_dir / "project"
    rebuilt_rom = experiment_dir / "rebuilt.sfc"
    report_path = experiment_dir / "experiment-report.json"

    try:
        if not project_dir.is_dir():
            raise FileNotFoundError(f"CoilSnake baseline project not found: {project_dir}")
        if not base_expanded_rom.is_file():
            raise FileNotFoundError(f"Expanded base ROM not found: {base_expanded_rom}")
        if not baseline_rebuild_rom.is_file():
            raise FileNotFoundError(f"Baseline rebuild ROM not found: {baseline_rebuild_rom}")
        if not args.coilsnake.is_file():
            raise FileNotFoundError(f"CoilSnake executable not found: {args.coilsnake}")

        experiments_dir.mkdir(parents=True, exist_ok=True)
        require_inside(experiment_dir, experiments_dir)

        source_in_baseline = project_dir / args.source_file
        if not source_in_baseline.is_file():
            raise FileNotFoundError(f"Source file not found in project: {source_in_baseline}")
        baseline_text = source_in_baseline.read_text(encoding="utf-8")
        count = baseline_text.count(args.find)
        if count != args.expected_count:
            raise ValueError(
                f"Expected {args.expected_count} match(es) in {source_in_baseline}, found {count}"
            )

        if args.dry_run:
            report = build_report(
                experiment_id=args.experiment_id,
                resource_family=args.resource_family,
                source_file=args.source_file,
                edit_description=args.edit_description,
                project_copy=project_copy,
                rebuilt_rom=rebuilt_rom,
                baseline_rebuild_rom=baseline_rebuild_rom,
                compile_result=None,
                diff=None,
                dry_run=True,
                status="dry-run",
            )
            print(json.dumps(report, indent=2))
            return 0

        copy_project(project_dir, project_copy, experiments_dir)
        edited_file = project_copy / args.source_file
        apply_text_edit(edited_file, args.find, args.replace, args.expected_count)
        prepared_at = datetime.now(timezone.utc).isoformat()
        write_report(
            report_path,
            build_report(
                experiment_id=args.experiment_id,
                resource_family=args.resource_family,
                source_file=args.source_file,
                edit_description=args.edit_description,
                project_copy=project_copy,
                rebuilt_rom=rebuilt_rom,
                baseline_rebuild_rom=baseline_rebuild_rom,
                compile_result=None,
                diff=None,
                dry_run=False,
                status="prepared",
                prepared_at=prepared_at,
            ),
        )

        compile_result = run_compile(
            args.coilsnake.resolve(),
            project_copy,
            base_expanded_rom,
            rebuilt_rom,
            args.compile_timeout_seconds,
        )
        diff = None
        if compile_result["returncode"] == 0:
            diff = diff_roms(baseline_rebuild_rom.read_bytes(), rebuilt_rom)

        report = build_report(
            experiment_id=args.experiment_id,
            resource_family=args.resource_family,
            source_file=args.source_file,
            edit_description=args.edit_description,
            project_copy=project_copy,
            rebuilt_rom=rebuilt_rom,
            baseline_rebuild_rom=baseline_rebuild_rom,
            compile_result=compile_result,
            diff=diff,
            dry_run=False,
            status=(
                "diffed"
                if diff and diff.get("status") == "different"
                else "compiled"
                if compile_result["returncode"] == 0
                else "compile-timeout"
                if compile_result["timed_out"]
                else "compile-failed"
            ),
            prepared_at=prepared_at,
        )
        write_report(report_path, report)
        print(json.dumps(report, indent=2))
        if compile_result["returncode"] == 0:
            return 0
        if compile_result["timed_out"]:
            return 124
        return int(compile_result["returncode"])
    except (FileNotFoundError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
