from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"

DEFAULT_PROJECT_DIR = ROOT / "build" / "coilsnake" / "baseline-project"
DEFAULT_BASELINE_REBUILD_ROM = ROOT / "build" / "coilsnake" / "baseline-rebuild.sfc"
DEFAULT_JSON_OUT = ROOT / "build" / "coilsnake" / "reports" / "coilsnake-project-inventory.json"
DEFAULT_MANIFEST_OUT = ROOT / "manifests" / "coilsnake-crosswalk.json"
DEFAULT_FIELD_SEMANTICS = ROOT / "manifests" / "coilsnake-field-semantics.json"
DEFAULT_EXPERIMENT_PLAN = ROOT / "manifests" / "coilsnake-experiment-plan.json"
DEFAULT_PREJOIN_JSON_OUT = ROOT / "build" / "coilsnake" / "reports" / "coilsnake-experiment-prejoin-report.json"
DEFAULT_PREJOIN_MARKDOWN_OUT = ROOT / "notes" / "coilsnake-experiment-prejoin-report.md"
DEFAULT_PROMOTION_STUBS_JSON_OUT = ROOT / "manifests" / "coilsnake-promotion-stubs.json"
DEFAULT_PROMOTION_STUBS_MARKDOWN_OUT = ROOT / "notes" / "coilsnake-promotion-stubs.md"
DEFAULT_FIELD_JSON_OUT = ROOT / "build" / "coilsnake" / "reports" / "coilsnake-field-join-report.json"
DEFAULT_FIELD_MARKDOWN_OUT = ROOT / "notes" / "coilsnake-field-join-report.md"

KNOWN_EXPERIMENT_ROMS = {
    "item-cost-probe": ROOT / "build" / "coilsnake" / "edit-experiments" / "item-cost-probe" / "rebuilt.sfc",
    "text-menu-probe": ROOT / "build" / "coilsnake" / "edit-experiments" / "text-menu-probe" / "rebuilt.sfc",
    "map-palette-probe": ROOT / "build" / "coilsnake" / "edit-experiments" / "map-palette-probe" / "rebuilt.sfc",
}


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh the tracked CoilSnake crosswalk manifest and field join note."
    )
    parser.add_argument("--project-dir", type=Path, default=DEFAULT_PROJECT_DIR)
    parser.add_argument("--baseline-rebuild-rom", type=Path, default=DEFAULT_BASELINE_REBUILD_ROM)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--manifest-out", type=Path, default=DEFAULT_MANIFEST_OUT)
    parser.add_argument("--field-semantics", type=Path, default=DEFAULT_FIELD_SEMANTICS)
    parser.add_argument("--experiment-plan", type=Path, default=DEFAULT_EXPERIMENT_PLAN)
    parser.add_argument("--prejoin-json-out", type=Path, default=DEFAULT_PREJOIN_JSON_OUT)
    parser.add_argument("--prejoin-markdown-out", type=Path, default=DEFAULT_PREJOIN_MARKDOWN_OUT)
    parser.add_argument("--promotion-stubs-json-out", type=Path, default=DEFAULT_PROMOTION_STUBS_JSON_OUT)
    parser.add_argument("--promotion-stubs-markdown-out", type=Path, default=DEFAULT_PROMOTION_STUBS_MARKDOWN_OUT)
    parser.add_argument("--field-json-out", type=Path, default=DEFAULT_FIELD_JSON_OUT)
    parser.add_argument("--field-markdown-out", type=Path, default=DEFAULT_FIELD_MARKDOWN_OUT)
    parser.add_argument(
        "--experiment-report",
        action="append",
        default=[],
        type=Path,
        help="Ignored report from tools/run_coilsnake_edit_experiment.py to ingest.",
    )
    parser.add_argument(
        "--skip-known-experiments",
        action="store_true",
        help="Do not include the three checked-in baseline diff experiment records.",
    )
    return parser.parse_args()


def require_file(path: Path, description: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{description} not found: {path}")


def require_dir(path: Path, description: str) -> None:
    if not path.is_dir():
        raise FileNotFoundError(f"{description} not found: {path}")


def run(command: list[str]) -> None:
    print(" ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def build_field_join_workflow(
    field_report: dict[str, Any],
    field_report_path: Path,
    field_markdown_path: Path,
) -> dict[str, Any]:
    promoted_joins = []
    for join in field_report.get("joins", []):
        if not isinstance(join, dict):
            continue
        diff_summary = join.get("diff_summary", {})
        address = join.get("address", {})
        contract = join.get("local_contract_matches", [{}])[0] if join.get("local_contract_matches") else {}
        source = join.get("source_scaffold_matches", [{}])[0] if join.get("source_scaffold_matches") else {}
        promoted_joins.append(
            {
                "experiment_id": join.get("experiment_id"),
                "coilsnake_file": join.get("coilsnake_file"),
                "changed_file_offset": diff_summary.get("first_changed_offset"),
                "hirom": address.get("hirom"),
                "local_contract": contract.get("label"),
                "source_scaffold": source.get("path"),
                "evidence_level": join.get("evidence_level"),
                "field_evidence_level": join.get("field_semantics", {}).get("field_evidence_level"),
                "promotion_status": join.get("field_semantics", {}).get("promotion_status"),
                "join_status": join.get("join_status"),
                "runtime_consumer_status": (
                    "relocation-or-compiler-normalization-candidate"
                    if join.get("warning")
                    else join.get("lookup_status")
                ),
            }
        )

    return {
        "tool": "tools/build_coilsnake_field_join_report.py",
        "tracked_summary": rel(field_markdown_path),
        "ignored_json_report": rel(field_report_path),
        "promoted_joins": promoted_joins,
    }


def inject_field_join_workflow(
    manifest_path: Path,
    field_report_path: Path,
    field_markdown_path: Path,
) -> None:
    manifest = load_json(manifest_path)
    field_report = load_json(field_report_path)
    workflow = build_field_join_workflow(field_report, field_report_path, field_markdown_path)

    updated: dict[str, Any] = {}
    inserted = False
    for key, value in manifest.items():
        if key == "field_join_workflow":
            continue
        if key == "promotion_policy":
            updated["field_join_workflow"] = workflow
            inserted = True
        updated[key] = value
    if not inserted:
        updated["field_join_workflow"] = workflow
    write_json(manifest_path, updated)


def inject_experiment_plan_workflow(
    manifest_path: Path,
    experiment_plan_path: Path,
    prejoin_json_path: Path,
    prejoin_markdown_path: Path,
) -> None:
    manifest = load_json(manifest_path)
    plan = load_json(experiment_plan_path)
    experiments = plan.get("planned_experiments", [])
    if not isinstance(experiments, list):
        experiments = []
    next_experiments = [
        {
            "experiment_id": experiment.get("experiment_id"),
            "batch": experiment.get("batch"),
            "source_file": experiment.get("source_file"),
            "status": experiment.get("status"),
            "promotion_target": experiment.get("promotion_target"),
        }
        for experiment in sorted(
            (item for item in experiments if isinstance(item, dict)),
            key=lambda item: item.get("priority", 999999),
        )
        if experiment.get("status") not in {"diff-confirmed", "retired"}
    ]

    workflow = {
        "tracked_plan": rel(experiment_plan_path),
        "validator": "tools/validate_coilsnake_experiment_plan.py",
        "runner": "tools/run_coilsnake_edit_experiment.py",
        "planned_runner": "tools/run_coilsnake_planned_experiment.py",
        "prejoin_tool": "tools/build_coilsnake_experiment_prejoin_report.py",
        "tracked_prejoin_summary": rel(prejoin_markdown_path),
        "ignored_prejoin_json_report": rel(prejoin_json_path),
        "default_compile_timeout_seconds": plan.get("default_compile_timeout_seconds"),
        "planned_count": len(experiments),
        "next_experiments": next_experiments,
    }

    updated: dict[str, Any] = {}
    inserted = False
    for key, value in manifest.items():
        if key == "experiment_plan_workflow":
            continue
        if key == "promotion_policy":
            updated["experiment_plan_workflow"] = workflow
            inserted = True
        updated[key] = value
    if not inserted:
        updated["experiment_plan_workflow"] = workflow
    write_json(manifest_path, updated)


def inject_promotion_stubs_workflow(
    manifest_path: Path,
    promotion_stubs_json_path: Path,
    promotion_stubs_markdown_path: Path,
) -> None:
    manifest = load_json(manifest_path)
    stubs_doc = load_json(promotion_stubs_json_path)

    workflow = {
        "tool": "tools/build_coilsnake_promotion_stubs.py",
        "validator": "tools/validate_coilsnake_promotion_stubs.py",
        "tracked_manifest": rel(promotion_stubs_json_path),
        "tracked_summary": rel(promotion_stubs_markdown_path),
        "stub_count": stubs_doc.get("summary", {}).get("stub_count"),
        "ready_to_run_count": stubs_doc.get("summary", {}).get("ready_to_run_count"),
        "tooling_blocked_count": stubs_doc.get("summary", {}).get("tooling_blocked_count"),
    }

    updated: dict[str, Any] = {}
    inserted = False
    for key, value in manifest.items():
        if key == "promotion_stubs_workflow":
            continue
        if key == "promotion_policy":
            updated["promotion_stubs_workflow"] = workflow
            inserted = True
        updated[key] = value
    if not inserted:
        updated["promotion_stubs_workflow"] = workflow
    write_json(manifest_path, updated)


def main() -> int:
    args = parse_args()
    project_dir = args.project_dir.resolve()
    baseline_rebuild = args.baseline_rebuild_rom.resolve()
    json_out = args.json_out.resolve()
    manifest_out = args.manifest_out.resolve()
    field_semantics = args.field_semantics.resolve()
    experiment_plan = args.experiment_plan.resolve()
    prejoin_json_out = args.prejoin_json_out.resolve()
    prejoin_markdown_out = args.prejoin_markdown_out.resolve()
    promotion_stubs_json_out = args.promotion_stubs_json_out.resolve()
    promotion_stubs_markdown_out = args.promotion_stubs_markdown_out.resolve()
    field_json_out = args.field_json_out.resolve()
    field_markdown_out = args.field_markdown_out.resolve()

    try:
        require_dir(project_dir, "CoilSnake baseline project")
        require_file(baseline_rebuild, "CoilSnake baseline rebuild ROM")
        require_file(field_semantics, "CoilSnake field semantics manifest")
        require_file(experiment_plan, "CoilSnake experiment plan manifest")

        inventory_command = [
            sys.executable,
            str(TOOLS / "build_coilsnake_project_inventory.py"),
            "--project-dir",
            str(project_dir),
            "--compare-rom",
            f"baseline-rebuild={baseline_rebuild}",
            "--experiment-base-rom",
            str(baseline_rebuild),
            "--json-out",
            str(json_out),
            "--manifest-out",
            str(manifest_out),
        ]

        if not args.skip_known_experiments:
            for label, rom_path in KNOWN_EXPERIMENT_ROMS.items():
                require_file(rom_path, f"Known CoilSnake experiment ROM {label}")
                inventory_command.extend(["--experiment-rom", f"{label}={rom_path.resolve()}"])

        for report_path in args.experiment_report:
            resolved = report_path.resolve()
            require_file(resolved, "CoilSnake experiment report")
            inventory_command.extend(["--experiment-report", str(resolved)])

        run(inventory_command)
        run(
            [
                sys.executable,
                str(TOOLS / "build_coilsnake_field_join_report.py"),
                "--crosswalk",
                str(manifest_out),
                "--field-semantics",
                str(field_semantics),
                "--json-out",
                str(field_json_out),
                "--markdown-out",
                str(field_markdown_out),
            ]
        )
        run(
            [
                sys.executable,
                str(TOOLS / "validate_coilsnake_experiment_plan.py"),
                "--plan",
                str(experiment_plan),
                "--crosswalk",
                str(manifest_out),
                "--project-dir",
                str(project_dir),
            ]
        )
        run(
            [
                sys.executable,
                str(TOOLS / "build_coilsnake_experiment_prejoin_report.py"),
                "--plan",
                str(experiment_plan),
                "--crosswalk",
                str(manifest_out),
                "--project-dir",
                str(project_dir),
                "--json-out",
                str(prejoin_json_out),
                "--markdown-out",
                str(prejoin_markdown_out),
            ]
        )
        run(
            [
                sys.executable,
                str(TOOLS / "build_coilsnake_promotion_stubs.py"),
                "--prejoin",
                str(prejoin_json_out),
                "--json-out",
                str(promotion_stubs_json_out),
                "--markdown-out",
                str(promotion_stubs_markdown_out),
            ]
        )
        run(
            [
                sys.executable,
                str(TOOLS / "validate_coilsnake_promotion_stubs.py"),
                "--stubs",
                str(promotion_stubs_json_out),
                "--prejoin",
                str(prejoin_json_out),
            ]
        )
        inject_field_join_workflow(manifest_out, field_json_out, field_markdown_out)
        inject_experiment_plan_workflow(manifest_out, experiment_plan, prejoin_json_out, prejoin_markdown_out)
        inject_promotion_stubs_workflow(manifest_out, promotion_stubs_json_out, promotion_stubs_markdown_out)
        print(f"Refreshed {rel(manifest_out)}")
        print(f"Refreshed {rel(field_markdown_out)}")
        print(f"Refreshed {rel(promotion_stubs_markdown_out)}")
        return 0
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        print(exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
