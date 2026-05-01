from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PREJOIN = ROOT / "build" / "coilsnake" / "reports" / "coilsnake-experiment-prejoin-report.json"
DEFAULT_ANCHOR_HINTS = ROOT / "manifests" / "coilsnake-runtime-anchor-hints.json"
DEFAULT_JSON_OUT = ROOT / "manifests" / "coilsnake-promotion-stubs.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "coilsnake-promotion-stubs.md"


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def evidence_gate(prejoin_status: str) -> dict[str, Any]:
    if prejoin_status == "tooling-blocked-ready-to-rerun":
        return {
            "next_required_evidence": "successful-compile-diff",
            "blocking_status": "local-coilsnake-executable-timeout",
            "allowed_promotion_after": [
                "runner report has compile.returncode 0",
                "diff.status is different",
                "diff.first_changed_offset is present",
            ],
        }
    if prejoin_status == "ready-to-run":
        return {
            "next_required_evidence": "diff-confirmed",
            "blocking_status": "none",
            "allowed_promotion_after": [
                "runner report has compile.returncode 0",
                "diff.status is different",
                "diff.first_changed_offset is present",
            ],
        }
    return {
        "next_required_evidence": "plan-cleanup",
        "blocking_status": prejoin_status,
        "allowed_promotion_after": ["prejoin status is ready-to-run or tooling-blocked-ready-to-rerun"],
    }


def load_anchor_hints(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    data = load_json(path)
    hints = data.get("anchor_hints", {})
    if not isinstance(hints, dict):
        return {}
    return {
        str(experiment_id): hint
        for experiment_id, hint in hints.items()
        if isinstance(hint, dict)
    }


def promotion_stub(prejoin: dict[str, Any], anchor_hints: dict[str, dict[str, Any]]) -> dict[str, Any]:
    experiment_id = str(prejoin.get("experiment_id", ""))
    experiment_report = f"build/coilsnake/edit-experiments/{experiment_id}/experiment-report.json"
    source_file = str(prejoin.get("source_file", ""))
    related_docs = [
        doc
        for doc in prejoin.get("related_local_docs", [])
        if isinstance(doc, str)
    ]

    return {
        "experiment_id": experiment_id,
        "source_file": source_file,
        "planned_edit": prejoin.get("edit"),
        "prejoin_status": prejoin.get("prejoin_status"),
        "resource_family": prejoin.get("resource_family"),
        "family_label": prejoin.get("family_label"),
        "promotion_target": prejoin.get("promotion_target"),
        "experiment_report": experiment_report,
        "ingest_command": f"python tools/refresh_coilsnake_crosswalk.py --experiment-report {experiment_report}",
        "evidence_gate": evidence_gate(str(prejoin.get("prejoin_status", ""))),
        "required_join_fields": [
            "changed file offset",
            "canonical HiROM address",
            "local asset/data or contract range",
            "field-level semantic claim",
            "runtime consumer status",
            "promotion status",
        ],
        "tracked_update_targets": related_docs[:8],
        "candidate_runtime_anchors": anchor_hints.get(experiment_id, {}),
        "field_semantics_action": (
            "add a manifests/coilsnake-field-semantics.json entry only after diff-confirmed offset/range evidence exists"
        ),
        "payload_policy": "Do not commit copied CoilSnake projects, rebuilt ROMs, project file contents, or ROM-derived bytes.",
    }


def build_report(prejoin_path: Path, anchor_hints_path: Path) -> dict[str, Any]:
    prejoin_report = load_json(prejoin_path)
    anchor_hints = load_anchor_hints(anchor_hints_path)
    prejoins = prejoin_report.get("prejoins", [])
    if not isinstance(prejoins, list):
        prejoins = []
    stubs = [
        promotion_stub(item, anchor_hints)
        for item in prejoins
        if isinstance(item, dict)
    ]
    return {
        "schema": "earthbound-decomp.coilsnake-promotion-stubs.v1",
        "generated_by": "tools/build_coilsnake_promotion_stubs.py",
        "source_prejoin_report": rel(prejoin_path),
        "source_anchor_hints": rel(anchor_hints_path) if anchor_hints_path.is_file() else None,
        "safety_note": "This manifest stores promotion workflow metadata only; it does not contain CoilSnake project contents, rebuilt ROMs, or ROM-derived payload bytes.",
        "summary": {
            "stub_count": len(stubs),
            "ready_to_run_count": sum(1 for stub in stubs if stub.get("prejoin_status") == "ready-to-run"),
            "tooling_blocked_count": sum(
                1 for stub in stubs if stub.get("prejoin_status") == "tooling-blocked-ready-to-rerun"
            ),
        },
        "promotion_stubs": stubs,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# CoilSnake Promotion Stubs",
        "",
        f"Generated by `tools/build_coilsnake_promotion_stubs.py` from `{report['source_prejoin_report']}`.",
        f"Runtime anchor hints: `{report.get('source_anchor_hints')}`.",
        "This note is compile-free and payload-free. It defines what evidence is required before planned CoilSnake probes can be promoted into local contracts.",
        "",
        "## Summary",
        "",
        f"- Promotion stubs: `{report['summary']['stub_count']}`",
        f"- Ready to run: `{report['summary']['ready_to_run_count']}`",
        f"- Tooling-blocked: `{report['summary']['tooling_blocked_count']}`",
        "",
        "## Stubs",
        "",
        "| Experiment | Gate | Family | First tracked targets |",
        "| --- | --- | --- | --- |",
    ]

    for stub in report.get("promotion_stubs", []):
        targets = ", ".join(f"`{target}`" for target in stub.get("tracked_update_targets", [])[:3])
        if not targets:
            targets = "`none`"
        lines.append(
            "| "
            f"`{stub.get('experiment_id')}` | "
            f"`{stub.get('evidence_gate', {}).get('next_required_evidence')}` | "
            f"`{stub.get('resource_family')}` | "
            f"{targets} |"
        )

    lines.extend(["", "## Promotion Checklist", ""])
    for stub in report.get("promotion_stubs", []):
        gate = stub.get("evidence_gate", {})
        lines.append(f"### `{stub.get('experiment_id')}`")
        lines.append("")
        lines.append(f"- Planned edit: {stub.get('planned_edit')}")
        lines.append(f"- Source file: `{stub.get('source_file')}`")
        lines.append(f"- Evidence gate: `{gate.get('next_required_evidence')}`")
        lines.append(f"- Blocking status: `{gate.get('blocking_status')}`")
        lines.append(f"- Ingest command: `{stub.get('ingest_command')}`")
        lines.append("- Required join fields:")
        for field in stub.get("required_join_fields", []):
            lines.append(f"  - `{field}`")
        anchors = stub.get("candidate_runtime_anchors", {})
        if isinstance(anchors, dict) and anchors:
            lines.append(f"- Runtime anchor status: `{anchors.get('status')}`")
            if anchors.get("candidate_local_ranges"):
                lines.append("- Candidate local ranges:")
                for range_hint in anchors.get("candidate_local_ranges", [])[:4]:
                    if not isinstance(range_hint, dict):
                        continue
                    lines.append(
                        "  - `{label}` `{range}`: {basis}".format(
                            label=range_hint.get("label", "unknown"),
                            range=range_hint.get("range", "unknown"),
                            basis=range_hint.get("basis", "no basis recorded"),
                        )
                    )
            if anchors.get("field_hints"):
                lines.append("- Field hints:")
                for field_hint in anchors.get("field_hints", [])[:4]:
                    if not isinstance(field_hint, dict):
                        continue
                    lines.append(
                        "  - `{field}` -> `{candidate}`: {basis}".format(
                            field=field_hint.get("coilsnake_field", "unknown"),
                            candidate=field_hint.get("candidate_local_field", "unknown"),
                            basis=field_hint.get("basis", "no basis recorded"),
                        )
                    )
            if anchors.get("source_anchor_paths"):
                lines.append("- Candidate source anchors:")
                for source in anchors["source_anchor_paths"][:6]:
                    lines.append(f"  - `{source}`")
            if anchors.get("note_anchor_paths"):
                lines.append("- Candidate note anchors:")
                for note in anchors["note_anchor_paths"][:6]:
                    lines.append(f"  - `{note}`")
            if anchors.get("runtime_consumer_hints"):
                lines.append("- Runtime consumer hints:")
                for consumer in anchors.get("runtime_consumer_hints", [])[:4]:
                    if not isinstance(consumer, dict):
                        continue
                    lines.append(
                        "  - `{consumer}` ({status}): {basis}".format(
                            consumer=consumer.get("consumer", "unknown"),
                            status=consumer.get("status", "unknown"),
                            basis=consumer.get("basis", "no basis recorded"),
                        )
                    )
        if stub.get("tracked_update_targets"):
            lines.append("- Candidate tracked update targets:")
            for target in stub["tracked_update_targets"][:8]:
                lines.append(f"  - `{target}`")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build promotion stubs for planned CoilSnake experiments.")
    parser.add_argument("--prejoin", type=Path, default=DEFAULT_PREJOIN)
    parser.add_argument("--anchor-hints", type=Path, default=DEFAULT_ANCHOR_HINTS)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN_OUT)
    args = parser.parse_args()

    prejoin = args.prejoin.resolve()
    if not prejoin.is_file():
        print(f"Prejoin report not found: {prejoin}", file=sys.stderr)
        return 2

    report = build_report(prejoin, args.anchor_hints.resolve())
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_out.write_text(render_markdown(report), encoding="utf-8")
    print(f"Wrote {rel(args.json_out)}")
    print(f"Wrote {rel(args.markdown_out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
