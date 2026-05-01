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
DEFAULT_JSON_OUT = ROOT / "build" / "coilsnake" / "reports" / "coilsnake-experiment-prejoin-report.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "coilsnake-experiment-prejoin-report.md"


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def family_lookup(crosswalk: dict[str, Any]) -> dict[str, dict[str, Any]]:
    families: dict[str, dict[str, Any]] = {}
    for family in crosswalk.get("families", []):
        if isinstance(family, dict) and isinstance(family.get("id"), str):
            families[family["id"]] = family
    return families


def resources_for_file(crosswalk: dict[str, Any], source_file: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for resource in crosswalk.get("resources", []):
        if not isinstance(resource, dict):
            continue
        roots = resource.get("project_path_roots", [])
        if isinstance(roots, list) and source_file in roots:
            matches.append(
                {
                    "resource_family": resource.get("resource_family"),
                    "resource_type": resource.get("resource_type"),
                    "evidence_level": resource.get("evidence_level"),
                    "local_status": resource.get("local_status"),
                    "source_banks": resource.get("source_banks", []),
                    "related_local_docs": resource.get("related_local_docs", []),
                }
            )
    return matches


def match_count(project_dir: Path, source_file: str, needle: str) -> int | None:
    path = project_dir / source_file
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8").count(needle)


def prejoin_status(experiment: dict[str, Any], actual_count: int | None) -> str:
    status = experiment.get("status")
    if actual_count is None:
        return "source-file-missing"
    if actual_count != experiment.get("expected_count"):
        return "edit-match-mismatch"
    if status == "timeout-path-verified-pending-rerun":
        return "tooling-blocked-ready-to-rerun"
    if status == "planned":
        return "ready-to-run"
    return str(status or "unknown")


def build_report(plan_path: Path, crosswalk_path: Path, project_dir: Path) -> dict[str, Any]:
    plan = load_json(plan_path)
    crosswalk = load_json(crosswalk_path)
    families = family_lookup(crosswalk)
    planned = plan.get("planned_experiments", [])
    if not isinstance(planned, list):
        planned = []

    prejoins: list[dict[str, Any]] = []
    for experiment in sorted(
        (entry for entry in planned if isinstance(entry, dict)),
        key=lambda entry: entry.get("priority", 999999),
    ):
        source_file = str(experiment.get("source_file", ""))
        expected_count = experiment.get("expected_count")
        actual_count = match_count(project_dir, source_file, str(experiment.get("find", "")))
        family_id = str(experiment.get("resource_family", ""))
        family = families.get(family_id, {})
        resources = resources_for_file(crosswalk, source_file)
        related_docs = sorted(
            {
                doc
                for doc in family.get("related_local_docs", [])
                if isinstance(doc, str)
            }
            | {
                doc
                for resource in resources
                for doc in resource.get("related_local_docs", [])
                if isinstance(doc, str)
            }
        )

        prejoins.append(
            {
                "experiment_id": experiment.get("experiment_id"),
                "batch": experiment.get("batch"),
                "priority": experiment.get("priority"),
                "source_file": source_file,
                "edit": experiment.get("edit_description"),
                "plan_status": experiment.get("status"),
                "prejoin_status": prejoin_status(experiment, actual_count),
                "expected_match_count": expected_count,
                "actual_match_count": actual_count,
                "resource_family": family_id,
                "family_label": family.get("label"),
                "family_local_status": family.get("local_status"),
                "resource_matches": resources,
                "related_local_docs": related_docs,
                "promotion_target": experiment.get("promotion_target"),
            }
        )

    return {
        "schema": "earthbound-decomp.coilsnake-experiment-prejoin-report.v1",
        "generated_by": "tools/build_coilsnake_experiment_prejoin_report.py",
        "source_plan": rel(plan_path),
        "source_crosswalk": rel(crosswalk_path),
        "project_dir": rel(project_dir),
        "safety_note": "This report records planned edit metadata, exact match counts, and local crosswalk anchors only; it does not contain CoilSnake project file contents or ROM-derived payload bytes.",
        "summary": {
            "planned_count": len(prejoins),
            "ready_to_run_count": sum(1 for item in prejoins if item["prejoin_status"] == "ready-to-run"),
            "tooling_blocked_count": sum(
                1 for item in prejoins if item["prejoin_status"] == "tooling-blocked-ready-to-rerun"
            ),
            "match_mismatch_count": sum(1 for item in prejoins if item["prejoin_status"] == "edit-match-mismatch"),
        },
        "prejoins": prejoins,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# CoilSnake Planned Experiment Prejoin Report",
        "",
        f"Generated by `tools/build_coilsnake_experiment_prejoin_report.py` from `{report['source_plan']}`.",
        "This note is compile-free and payload-free; it only records planned edit metadata, match counts, and local anchors.",
        "",
        "## Summary",
        "",
        f"- Planned experiments: `{report['summary']['planned_count']}`",
        f"- Ready to run once CoilSnake is trusted: `{report['summary']['ready_to_run_count']}`",
        f"- Tooling-blocked but prepared: `{report['summary']['tooling_blocked_count']}`",
        f"- Edit match mismatches: `{report['summary']['match_mismatch_count']}`",
        "",
        "## Planned Probes",
        "",
        "| Experiment | Status | Source | Match | Local family | Promotion target |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]

    for item in report.get("prejoins", []):
        match_text = f"{item.get('actual_match_count')}/{item.get('expected_match_count')}"
        target = str(item.get("promotion_target") or "").replace("|", "\\|")
        lines.append(
            "| "
            f"`{item.get('experiment_id')}` | "
            f"`{item.get('prejoin_status')}` | "
            f"`{item.get('source_file')}` | "
            f"`{match_text}` | "
            f"`{item.get('resource_family')}` | "
            f"{target} |"
        )

    lines.extend(["", "## Local Anchors", ""])
    for item in report.get("prejoins", []):
        lines.append(f"### `{item.get('experiment_id')}`")
        lines.append("")
        lines.append(f"- Family: `{item.get('family_label')}` (`{item.get('family_local_status')}`)")
        lines.append(f"- Plan status: `{item.get('plan_status')}`")
        if item.get("resource_matches"):
            lines.append("- CoilSnake resource matches:")
            for resource in item["resource_matches"]:
                banks = ", ".join(resource.get("source_banks", [])) or "none"
                lines.append(
                    f"  - `{resource.get('resource_type')}` banks `{banks}` status `{resource.get('local_status')}`"
                )
        if item.get("related_local_docs"):
            lines.append("- Related local docs:")
            for doc in item["related_local_docs"][:8]:
                lines.append(f"  - `{doc}`")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build compile-free local prejoin report for planned CoilSnake experiments.")
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--project-dir", type=Path, default=DEFAULT_PROJECT_DIR)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN_OUT)
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
    if not project_dir.is_dir():
        print(f"CoilSnake baseline project not found: {project_dir}", file=sys.stderr)
        return 2

    report = build_report(plan, crosswalk, project_dir)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_out.write_text(render_markdown(report), encoding="utf-8")
    print(f"Wrote {rel(args.json_out)}")
    print(f"Wrote {rel(args.markdown_out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
