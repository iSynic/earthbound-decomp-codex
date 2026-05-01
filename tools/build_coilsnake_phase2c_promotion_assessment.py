from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATUS = ROOT / "manifests" / "coilsnake-phase2c-status.json"
DEFAULT_MANIFEST_OUT = ROOT / "manifests" / "coilsnake-phase2c-promotion-assessment.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "coilsnake-phase2c-promotion-assessment.md"


ASSESSMENTS: dict[str, dict[str, Any]] = {
    "ccscript-body-command-byte-probe": {
        "assessment": "authoring-lowering-only",
        "local_result": "CCScript body argument lowering is isolated in the scriptdump rebuild, but text VM semantics remain owned by local C1 parser/handler evidence.",
        "recommended_action": "keep-as-oracle-evidence",
        "local_docs": [
            "notes/coilsnake-ccscript-experiments.md",
            "notes/text-script-assets-frontier.md",
        ],
    },
    "ccscript-rom-goto-label-probe": {
        "assessment": "authoring-lowering-only",
        "local_result": "CCScript label reference lowering is isolated in the scriptdump rebuild, but it is not a runtime command semantic.",
        "recommended_action": "keep-as-oracle-evidence",
        "local_docs": [
            "notes/coilsnake-ccscript-experiments.md",
            "notes/text-script-assets-frontier.md",
        ],
    },
    "font0-width5-probe": {
        "assessment": "defer-original-runtime-promotion",
        "local_result": "The CoilSnake rebuild byte lands at CF:60DC, which is inside the original ROM's CF event-music/table corridor rather than the checked E0/E1 font metric ranges.",
        "recommended_action": "record-as-rebuilt-layout-evidence",
        "local_docs": [
            "notes/font-bundle-contracts.md",
            "notes/ui-font-town-map-asset-contracts.md",
        ],
    },
    "bg-data-distortion1-probe": {
        "assessment": "promote-to-local-contract",
        "local_result": "The byte lands at CA:DCD0, inside the original CA battle-background config table. Relative to CA:DCA1, this is row 2 offset +0x2F overall / row offset +0x0D, matching the first distortion reference slot documented for BG_DATA_TABLE rows.",
        "recommended_action": "promote-runtime-correlated-field",
        "local_docs": [
            "notes/battle-background-scene-bundles.md",
            "notes/battle-visual-asset-contracts.md",
        ],
    },
    "town-map-first-icon-x-probe": {
        "assessment": "defer-original-runtime-promotion",
        "local_result": "The CoilSnake rebuild byte lands at E0:11A4, which is inside the original ROM's compressed SRAM template range, while original town-map icon placement records live in E1:F4A9..E1:F581.",
        "recommended_action": "record-as-rebuilt-layout-evidence",
        "local_docs": [
            "notes/town-map-selection-rendering-c4d274-c4d744.md",
            "notes/ui-font-town-map-asset-contracts.md",
        ],
    },
    "windowgraphics-windows1-copy-probe": {
        "assessment": "promote-to-local-contract",
        "local_result": "The bounded changed span E0:1FCB..E0:2000 sits inside the original text-window palette-block contract E0:1FC8..E0:2188.",
        "recommended_action": "promote-bounded-insertion-evidence",
        "local_docs": [
            "notes/text-window-skin-bundle-contracts.md",
            "notes/ui-font-town-map-asset-contracts.md",
        ],
    },
    "battlesprite-001-copy-probe": {
        "assessment": "defer-original-runtime-promotion",
        "local_result": "The broad changed span reflects compression/repacking behavior across many ROM regions, so it should constrain editor/tool expectations rather than name a stable runtime field.",
        "recommended_action": "keep-as-compiler-behavior-constraint",
        "local_docs": [
            "notes/battle-sprite-bundle-contracts.md",
        ],
    },
    "tileset00-fts-nibble-probe": {
        "assessment": "defer-original-runtime-promotion",
        "local_result": "The broad changed span reflects tileset compression/repacking behavior, so it should constrain editor/tool expectations rather than name a stable runtime field.",
        "recommended_action": "keep-as-compiler-behavior-constraint",
        "local_docs": [
            "notes/map-tileset-bundles.md",
        ],
    },
}


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_assessment(status_path: Path) -> dict[str, Any]:
    status = load_json(status_path)
    rows = []
    for experiment in status.get("experiments", []):
        if not isinstance(experiment, dict):
            continue
        experiment_id = experiment.get("experiment_id")
        assessment = ASSESSMENTS.get(str(experiment_id), {})
        rows.append(
            {
                "experiment_id": experiment_id,
                "resource_family": experiment.get("resource_family"),
                "behavior": experiment.get("behavior"),
                "phase2c_promotion_lane": experiment.get("promotion_lane"),
                "changed_bytes": experiment.get("changed_bytes"),
                "changed_span": experiment.get("changed_span"),
                **assessment,
            }
        )
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get("assessment", "unassessed"))
        counts[key] = counts.get(key, 0) + 1
    return {
        "schema": "earthbound-decomp.coilsnake-phase2c-promotion-assessment.v1",
        "generated_by": "tools/build_coilsnake_phase2c_promotion_assessment.py",
        "safety_note": "This assessment stores only experiment metadata, addresses, and local documentation decisions; it stores no ROM, image, or script payloads.",
        "input_status": rel(status_path),
        "assessment_counts": dict(sorted(counts.items())),
        "assessments": rows,
    }


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# CoilSnake Phase 2C Promotion Assessment",
        "",
        "This note decides which Phase 2C CoilSnake results are ready for local contract promotion.",
        "It is intentionally stricter than the raw diff classification: a small CoilSnake-rebuild diff is not promoted unless it also lines up with local original-ROM contracts.",
        "",
        "## Summary",
        "",
    ]
    for key, count in report["assessment_counts"].items():
        lines.append(f"- `{key}`: `{count}`")
    lines.extend(
        [
            "",
            "## Decisions",
            "",
            "| Experiment | Behavior | Assessment | Changed span | Action |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in report["assessments"]:
        lines.append(
            "| "
            f"`{row['experiment_id']}` | "
            f"`{row['behavior']}` | "
            f"`{row.get('assessment')}` | "
            f"`{row['changed_span']}` | "
            f"`{row.get('recommended_action')}` |"
        )
    lines.extend(["", "## Local Reads", ""])
    for row in report["assessments"]:
        docs = ", ".join(f"`{doc}`" for doc in row.get("local_docs", []))
        lines.extend(
            [
                f"### `{row['experiment_id']}`",
                "",
                f"- assessment: `{row.get('assessment')}`",
                f"- local result: {row.get('local_result')}",
                f"- local docs: {docs}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Phase 2C promotion assessment.")
    parser.add_argument("--status", type=Path, default=DEFAULT_STATUS)
    parser.add_argument("--manifest-out", type=Path, default=DEFAULT_MANIFEST_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN_OUT)
    args = parser.parse_args()

    if not args.status.is_file():
        raise SystemExit(f"Phase 2C status not found: {args.status}")
    report = build_assessment(args.status.resolve())
    write_json(args.manifest_out, report)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.write_text(markdown(report), encoding="utf-8")
    print(f"Wrote {rel(args.manifest_out)}")
    print(f"Wrote {rel(args.markdown_out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
