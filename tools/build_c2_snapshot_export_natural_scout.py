#!/usr/bin/env python3
"""Summarize natural-save C1/C2 snapshot-export scout runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
MANUAL_PROBES_ROOT = ROOT / "build" / "c2" / "battle-trace-oracles" / "manual-probes"
DEFAULT_INPUT_ROOTS = (
    MANUAL_PROBES_ROOT / "snapshot-export-natural-scout",
    MANUAL_PROBES_ROOT / "target-staging-scout",
)
DEFAULT_MANIFEST = ROOT / "manifests" / "c2-snapshot-export-natural-scout.json"
DEFAULT_NOTE = ROOT / "notes" / "c2-snapshot-export-natural-scout.md"
SNAPSHOT_EXPORT_CALLSITES = {"C1:B3DB", "C1:B462", "C1:B505", "C1:B859", "C1:B9A9", "C1:BA60"}


def repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def hit_count(summary: dict[str, Any], address: str) -> int:
    return int(summary.get("breakpoint_hit_counts", {}).get(address, 0) or 0)


def build_run(path: Path) -> dict[str, Any]:
    summary = load_json(path)
    observed = as_list(summary.get("observed_addresses"))
    probe_observed = as_list(summary.get("probe_observed_addresses"))
    hit_counts = summary.get("breakpoint_hit_counts", {})
    export_hits = sorted(SNAPSHOT_EXPORT_CALLSITES & set(hit_counts))
    return {
        "run_id": repo_path(path.parent),
        "summary_path": repo_path(path),
        "trace_path": summary.get("trace_path"),
        "status": summary.get("status"),
        "line_count": summary.get("line_count"),
        "first_frame": summary.get("first_frame"),
        "last_frame": summary.get("last_frame"),
        "observed_addresses": observed,
        "probe_observed_addresses": probe_observed,
        "minimum_hits_satisfied": summary.get("minimum_hits_satisfied"),
        "missing_minimum_hits": as_list(summary.get("missing_minimum_hits")),
        "hit_counts": {key: hit_counts[key] for key in sorted(hit_counts)},
        "snapshot_export_callsite_hits": export_hits,
        "natural_b930_hit": hit_count(summary, "C2:B930") > 0,
        "c1_adb4_hit": hit_count(summary, "C1:ADB4") > 0,
        "c1_ce85_hit": hit_count(summary, "C1:CE85") > 0,
        "c2_bac5_hit": hit_count(summary, "C2:BAC5") > 0,
        "post_call_snapshot_counts": summary.get("post_call_snapshot_counts", {}),
        "input_pattern": summary.get("runner_start", {}).get("inputPattern"),
        "frame_limit": summary.get("runner_summary", {}).get("frames"),
    }


def build_manifest(input_roots: tuple[Path, ...] = DEFAULT_INPUT_ROOTS) -> dict[str, Any]:
    summary_paths: list[Path] = []
    for input_root in input_roots:
        summary_paths.extend(sorted(input_root.glob("*/raw-trace-summary.json")))
    runs = [build_run(path) for path in summary_paths]
    export_ready = [run for run in runs if run["snapshot_export_callsite_hits"] or run["natural_b930_hit"]]
    c1_neighbors = [run for run in runs if run["c1_adb4_hit"]]
    item_neighbors = [run for run in runs if run["c1_ce85_hit"] and run["c1_adb4_hit"]]
    bac5_neighbors = [run for run in runs if run["c2_bac5_hit"]]
    best_neighbor = (
        item_neighbors[0]["run_id"]
        if item_neighbors
        else (c1_neighbors[0]["run_id"] if c1_neighbors else "none")
    )
    return {
        "schema": "earthbound-decomp.c2-snapshot-export-natural-scout.v1",
        "generated_by": "tools/build_c2_snapshot_export_natural_scout.py",
        "input_roots": [repo_path(path) for path in input_roots],
        "summary": {
            "run_count": len(runs),
            "snapshot_export_callsite_run_count": len(export_ready),
            "natural_b930_run_count": len([run for run in runs if run["natural_b930_hit"]]),
            "c1_adb4_neighbor_run_count": len(c1_neighbors),
            "c1_ce85_item_resolver_neighbor_run_count": len(item_neighbors),
            "c2_bac5_neighbor_run_count": len(bac5_neighbors),
            "natural_route_proven": False,
            "source_promotion_allowed": False,
            "behavior_change_allowed": False,
        },
        "runs": runs,
        "interpretation": {
            "current_existing_saves_position": "mostly_after_c1_snapshot_export_or_on_target_count_neighbors",
            "best_existing_neighbor": best_neighbor,
            "latest_live_result": (
                "The slot9 Large Pizza and slot2 Fresh Egg battle Goods saves both reach "
                "C1:CE85 -> C1:ADB4 -> C2:BAC5, but neither battle-selection path touches "
                "the C1:AF73 use-item bridge where the C2:B930 export callsites live."
            ),
            "next_required_fixture": (
                "An overworld/menu Goods Use save that enters the C1:AF73 USE_ITEM bridge, "
                "preferably with a usable item whose D5 action row has a non-null +0x08 payload. "
                "Battle Goods C1:CE85/ADB4 saves are now proven neighbor evidence, not B930 routes."
            ),
        },
    }


def render_note(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    lines = [
        "# C2 Snapshot Export Natural Scout",
        "",
        "Generated by `tools/build_c2_snapshot_export_natural_scout.py` from ignored local Mesen scout summaries.",
        "This note records negative/neighbor evidence for existing saves; it is not source-promotion evidence.",
        "",
        "## Summary",
        "",
        f"- scout runs: `{summary['run_count']}`",
        f"- natural snapshot-export callsite runs: `{summary['snapshot_export_callsite_run_count']}`",
        f"- natural `C2:B930` runs: `{summary['natural_b930_run_count']}`",
        f"- `C1:ADB4` neighbor runs: `{summary['c1_adb4_neighbor_run_count']}`",
        f"- `C1:CE85` + `C1:ADB4` item-resolver neighbor runs: `{summary['c1_ce85_item_resolver_neighbor_run_count']}`",
        f"- `C2:BAC5` neighbor runs: `{summary['c2_bac5_neighbor_run_count']}`",
        f"- natural route proven: `{summary['natural_route_proven']}`",
        "",
        "## Runs",
        "",
        "| Run | Observed | Snapshot Export Hits | Missing Minimums | Frames |",
        "| --- | --- | --- | --- | --- |",
    ]
    for run in manifest["runs"]:
        observed = ", ".join(run["observed_addresses"]) or "-"
        export_hits = ", ".join(run["snapshot_export_callsite_hits"]) or "-"
        missing = ", ".join(run["missing_minimum_hits"]) or "-"
        if run.get("first_frame") is None or run.get("last_frame") is None:
            frames = "-"
        else:
            frames = f"{run.get('first_frame')}..{run.get('last_frame')}"
        lines.append(f"| `{run['run_id']}` | {observed} | {export_hits} | {missing} | {frames} |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Existing saves mostly observe `C2:BAC5` target-count neighbors or later effect-resolution paths.",
            f"- `{manifest['interpretation']['best_existing_neighbor']}` is the best current neighbor because it reaches the deepest natural pre-export route seen so far, but it still misses the natural snapshot-export callsites and `C2:B930`.",
            f"- {manifest['interpretation']['latest_live_result']}",
            "- The enhanced runner remains useful: it is now waiting for an earlier pre-export fixture rather than missing capture support.",
            "",
            "## Next Fixture",
            "",
            f"- {manifest['interpretation']['next_required_fixture']}",
            "- Until that exists, keep `notes/c2-b930-controlled-snapshot-export.md` as controlled mechanics evidence only.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    manifest = build_manifest()
    DEFAULT_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    DEFAULT_NOTE.write_text(render_note(manifest), encoding="utf-8")
    print(f"Wrote {DEFAULT_MANIFEST}")
    print(f"Wrote {DEFAULT_NOTE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
