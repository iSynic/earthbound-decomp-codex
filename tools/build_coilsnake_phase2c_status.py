from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCRIPTDUMP = ROOT / "manifests" / "coilsnake-scriptdump-summary.json"
DEFAULT_CCSCRIPT = ROOT / "manifests" / "coilsnake-ccscript-experiments.json"
DEFAULT_FORMAT = ROOT / "manifests" / "coilsnake-format-experiments.json"
DEFAULT_MANIFEST_OUT = ROOT / "manifests" / "coilsnake-phase2c-status.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "coilsnake-phase2c-status.md"


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def diff_span(diff: dict[str, Any]) -> str:
    start = diff.get("first_changed_offset")
    start_hirom = diff.get("first_changed_hirom")
    end = diff.get("last_changed_offset_exclusive")
    end_hirom = diff.get("last_changed_hirom_exclusive")
    if not start or not end:
        return "-"
    return f"{start} ({start_hirom})..{end} ({end_hirom})"


def classify_diff(diff: dict[str, Any]) -> str:
    changed_bytes = diff.get("changed_bytes")
    runs = diff.get("contiguous_changed_runs")
    if not isinstance(changed_bytes, int) or not isinstance(runs, int):
        return "unknown"
    if changed_bytes <= 2 and runs == 1:
        return "fixed-byte"
    if changed_bytes <= 128 and runs <= 16:
        return "bounded-insertion"
    return "broad-repack"


def promotion_lane(behavior: str, family: str) -> str:
    if family == "text-script":
        return "authoring-lowering-only"
    if behavior in {"fixed-byte", "bounded-insertion"}:
        return "candidate-local-contract-update"
    if behavior == "broad-repack":
        return "defer-runtime-promotion"
    return "needs-triage"


def summarize_experiments(source: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    rows = []
    for experiment in source.get("experiments", []):
        if not isinstance(experiment, dict):
            continue
        diff = experiment.get("diff") if isinstance(experiment.get("diff"), dict) else {}
        family = str(experiment.get("resource_family") or "")
        behavior = "script-lowering" if kind == "ccscript" else classify_diff(diff)
        rows.append(
            {
                "kind": kind,
                "experiment_id": experiment.get("experiment_id"),
                "resource_family": family,
                "source_file": experiment.get("source_file"),
                "replacement_file": experiment.get("replacement_file"),
                "comparison_base": experiment.get("comparison_base"),
                "evidence_level": experiment.get("evidence_level"),
                "behavior": behavior,
                "promotion_lane": promotion_lane(behavior, family),
                "changed_bytes": diff.get("changed_bytes"),
                "contiguous_changed_runs": diff.get("contiguous_changed_runs"),
                "changed_span": diff_span(diff),
            }
        )
    return rows


def build_status(
    *,
    scriptdump_path: Path,
    ccscript_path: Path,
    format_path: Path,
) -> dict[str, Any]:
    scriptdump = load_json(scriptdump_path)
    ccscript = load_json(ccscript_path)
    format_summary = load_json(format_path)

    scriptdump_diff = (
        scriptdump.get("compile_roundtrip", {})
        .get("diff_against_baseline_rebuild", {})
    )
    ccscript_rows = summarize_experiments(ccscript, "ccscript")
    format_rows = summarize_experiments(format_summary, "format")
    all_rows = ccscript_rows + format_rows

    behavior_counts: dict[str, int] = {}
    lane_counts: dict[str, int] = {}
    for row in all_rows:
        behavior_counts[row["behavior"]] = behavior_counts.get(row["behavior"], 0) + 1
        lane_counts[row["promotion_lane"]] = lane_counts.get(row["promotion_lane"], 0) + 1

    return {
        "schema": "earthbound-decomp.coilsnake-phase2c-status.v1",
        "generated_by": "tools/build_coilsnake_phase2c_status.py",
        "safety_note": "This status stores only CoilSnake run metadata, counts, classifications, and diff spans; generated projects, images, scripts, and ROMs remain ignored.",
        "inputs": {
            "scriptdump": rel(scriptdump_path),
            "ccscript_experiments": rel(ccscript_path),
            "format_experiments": rel(format_path),
        },
        "scriptdump_roundtrip": {
            "status": scriptdump_diff.get("status"),
            "changed_bytes": scriptdump_diff.get("changed_bytes"),
            "contiguous_changed_runs": scriptdump_diff.get("contiguous_changed_runs"),
            "changed_span": diff_span(scriptdump_diff),
            "classification": "compiler-normalized-roundtrip",
            "promotion_lane": "authoring-oracle-only",
        },
        "experiment_count": len(all_rows),
        "behavior_counts": dict(sorted(behavior_counts.items())),
        "promotion_lane_counts": dict(sorted(lane_counts.items())),
        "experiments": all_rows,
        "remaining_phase2c_actions": [
            {
                "action": "promote fixed-byte and bounded-insertion probes only where existing local callers/contracts already support the address",
                "status": "ready",
            },
            {
                "action": "keep broad-repack probes as editor/compiler behavior constraints until a narrower diff or pointer walk exists",
                "status": "ready",
            },
            {
                "action": "avoid treating full scriptdump roundtrip output as byte-stable runtime proof",
                "status": "satisfied-by-policy",
            },
        ],
    }


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def markdown(status: dict[str, Any]) -> str:
    scriptdump = status["scriptdump_roundtrip"]
    lines = [
        "# CoilSnake Phase 2C Status",
        "",
        "This note closes the current CoilSnake format-behavior pass with payload-free classifications.",
        "Generated projects, image assets, CCScript dumps, and rebuilt ROMs remain under ignored `build/coilsnake/`.",
        "",
        "## Summary",
        "",
        f"- Scriptdump roundtrip: `{scriptdump['classification']}`",
        f"- Scriptdump changed bytes: `{scriptdump['changed_bytes']}` across `{scriptdump['contiguous_changed_runs']}` runs",
        f"- Scriptdump changed span: `{scriptdump['changed_span']}`",
        f"- Classified experiments: `{status['experiment_count']}`",
        "",
        "Behavior counts:",
        "",
    ]
    for behavior, count in status["behavior_counts"].items():
        lines.append(f"- `{behavior}`: `{count}`")
    lines.extend(
        [
            "",
            "Promotion lanes:",
            "",
        ]
    )
    for lane, count in status["promotion_lane_counts"].items():
        lines.append(f"- `{lane}`: `{count}`")
    lines.extend(
        [
            "",
            "## Experiment Classification",
            "",
            "| Experiment | Kind | Family | Behavior | Promotion lane | Changed bytes | Runs | Changed span |",
            "| --- | --- | --- | --- | --- | ---: | ---: | --- |",
        ]
    )
    for experiment in status["experiments"]:
        lines.append(
            "| "
            f"`{experiment['experiment_id']}` | "
            f"`{experiment['kind']}` | "
            f"`{experiment['resource_family']}` | "
            f"`{experiment['behavior']}` | "
            f"`{experiment['promotion_lane']}` | "
            f"`{experiment['changed_bytes']}` | "
            f"`{experiment['contiguous_changed_runs']}` | "
            f"`{experiment['changed_span']}` |"
        )
    lines.extend(
        [
            "",
            "## Remaining Actions",
            "",
        ]
    )
    for action in status["remaining_phase2c_actions"]:
        lines.append(f"- `{action['status']}`: {action['action']}.")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `fixed-byte` and `bounded-insertion` probes can support local contract updates when existing source or asset notes already explain the address.",
            "- `broad-repack` probes prove CoilSnake accepts and compiles the edit, but the changed spans are compiler/recompression behavior rather than stable runtime fields.",
            "- `script-lowering` probes prove authoring/compiler behavior and must be joined back to local text VM evidence before naming runtime commands.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the CoilSnake Phase 2C status report.")
    parser.add_argument("--scriptdump", type=Path, default=DEFAULT_SCRIPTDUMP)
    parser.add_argument("--ccscript", type=Path, default=DEFAULT_CCSCRIPT)
    parser.add_argument("--format", type=Path, default=DEFAULT_FORMAT)
    parser.add_argument("--manifest-out", type=Path, default=DEFAULT_MANIFEST_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN_OUT)
    args = parser.parse_args()

    for path, description in (
        (args.scriptdump, "scriptdump summary"),
        (args.ccscript, "CCScript experiment summary"),
        (args.format, "format experiment summary"),
    ):
        if not path.is_file():
            raise SystemExit(f"{description} not found: {path}")

    status = build_status(
        scriptdump_path=args.scriptdump.resolve(),
        ccscript_path=args.ccscript.resolve(),
        format_path=args.format.resolve(),
    )
    write_json(args.manifest_out, status)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.write_text(markdown(status), encoding="utf-8")
    print(f"Wrote {rel(args.manifest_out)}")
    print(f"Wrote {rel(args.markdown_out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
