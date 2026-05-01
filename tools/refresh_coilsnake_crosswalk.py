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


def main() -> int:
    args = parse_args()
    project_dir = args.project_dir.resolve()
    baseline_rebuild = args.baseline_rebuild_rom.resolve()
    json_out = args.json_out.resolve()
    manifest_out = args.manifest_out.resolve()
    field_json_out = args.field_json_out.resolve()
    field_markdown_out = args.field_markdown_out.resolve()

    try:
        require_dir(project_dir, "CoilSnake baseline project")
        require_file(baseline_rebuild, "CoilSnake baseline rebuild ROM")

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
                "--json-out",
                str(field_json_out),
                "--markdown-out",
                str(field_markdown_out),
            ]
        )
        inject_field_join_workflow(manifest_out, field_json_out, field_markdown_out)
        print(f"Refreshed {rel(manifest_out)}")
        print(f"Refreshed {rel(field_markdown_out)}")
        return 0
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        print(exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
