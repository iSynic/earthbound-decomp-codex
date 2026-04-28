#!/usr/bin/env python3
"""Build a source-macro expansion frontier for recovered localization commands.

The authoring-command frontier answers "what bucket does this command belong
to?" This report answers "what kind of expansion model is needed next?" It
keeps recovered dialogue/source text out of tracked artifacts while making the
remaining Text VM / Localization Script Semantics work queryable.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUTHORING_FRONTIER = ROOT / "build" / "localization-authoring-command-frontier.json"
DEFAULT_JSON = ROOT / "build" / "localization-macro-expansion-frontier.json"
DEFAULT_MARKDOWN = ROOT / "notes" / "localization-macro-expansion-frontier.md"


EXPANSION_BY_BUCKET = {
    "runtime_mapped": "direct_runtime_hint",
    "authoring_format_candidate": "authoring_format_markup",
    "branch_macro_candidate": "text_vm_control_macro",
    "display_macro_candidate": "text_vm_display_macro",
    "movement_macro_candidate": "event_actionscript_join",
    "inventory_macro_candidate": "text_vm_inventory_macro",
    "query_macro_candidate": "text_vm_query_macro",
    "status_macro_candidate": "text_vm_status_macro",
    "battle_macro_candidate": "battle_text_macro",
    "authoring_macro_candidate": "source_tooling_macro",
}

NEXT_SEAM_BY_EXPANSION = {
    "direct_runtime_hint": "Confirm operand shape only when confidence is medium/low.",
    "authoring_format_markup": "Decide whether the marker emits bytes or is source-only layout metadata.",
    "text_vm_control_macro": "Model expansion into branch/call/register text VM commands.",
    "text_vm_display_macro": "Tie aliases to 0x1C display leaves or document source-only display macros.",
    "event_actionscript_join": "Join to map-object/C3 event-actionscript semantics before forcing text VM names.",
    "text_vm_inventory_macro": "Tie to 0x1D/0x19 inventory, shop, Tracy, and Escargo leaves.",
    "text_vm_query_macro": "Tie predicates to checks, staged-memory tests, or branch macros.",
    "text_vm_status_macro": "Tie condition toggles to 0x1E or event-helper leaves.",
    "battle_text_macro": "Join battle authoring macros to EF/battle text payloads and C2 battle consumers.",
    "source_tooling_macro": "Document source-tool behavior before assigning a ROM bytecode form.",
}

LANE_ORDER = [
    "text_vm_control_macro",
    "text_vm_display_macro",
    "text_vm_inventory_macro",
    "text_vm_query_macro",
    "text_vm_status_macro",
    "battle_text_macro",
    "event_actionscript_join",
    "authoring_format_markup",
    "source_tooling_macro",
    "direct_runtime_hint",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def load_frontier(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def confidence(row: dict[str, Any]) -> str:
    hint = row.get("runtime_hint")
    if not hint:
        return "-"
    return str(hint.get("confidence", "-"))


def hint_label(row: dict[str, Any]) -> str:
    hint = row.get("runtime_hint")
    if not hint:
        return "-"
    opcode = hint["opcode"]
    if "subopcode" in hint:
        opcode = f"{opcode} {hint['subopcode']}"
    return f"{opcode} {hint['name']} ({hint['confidence']})"


def shape_label(row: dict[str, Any]) -> str:
    shapes = row.get("argument_shapes", {})
    return ", ".join(f"{shape}:{count}" for shape, count in shapes.items()) or "-"


def build_frontier(authoring: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for row in authoring["commands"]:
        bucket = row["bucket"]
        expansion = EXPANSION_BY_BUCKET.get(bucket, "unclassified_expansion")
        rows.append(
            {
                "command": row["command"],
                "count": row["count"],
                "files": row["files"],
                "metadata_records": row["metadata_records"],
                "argument_shapes": row["argument_shapes"],
                "bucket": bucket,
                "expansion_lane": expansion,
                "runtime_hint": row.get("runtime_hint"),
                "next_seam": NEXT_SEAM_BY_EXPANSION.get(expansion, "Classify expansion lane."),
            }
        )

    lane_counts: dict[str, dict[str, int]] = {}
    by_lane: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_lane[row["expansion_lane"]].append(row)
    for lane, lane_rows in by_lane.items():
        lane_counts[lane] = {
            "commands": len(lane_rows),
            "occurrences": sum(int(row["count"]) for row in lane_rows),
        }

    runtime_confidence_counts = Counter(confidence(row) for row in rows if row["bucket"] == "runtime_mapped")
    unresolved_macro_rows = [row for row in rows if row["bucket"] != "runtime_mapped"]

    return {
        "generated_by": "tools/build_localization_macro_expansion_frontier.py",
        "source_frontier": rel(DEFAULT_AUTHORING_FRONTIER),
        "summary": {
            "commands": len(rows),
            "runtime_mapped": sum(1 for row in rows if row["bucket"] == "runtime_mapped"),
            "macro_or_markup_commands": len(unresolved_macro_rows),
            "macro_or_markup_occurrences": sum(int(row["count"]) for row in unresolved_macro_rows),
            "runtime_high_confidence": runtime_confidence_counts.get("high", 0),
            "runtime_medium_confidence": runtime_confidence_counts.get("medium", 0),
            "runtime_low_confidence": runtime_confidence_counts.get("low", 0),
            "expansion_lanes": len(lane_counts),
        },
        "lane_counts": dict(sorted(lane_counts.items())),
        "rows": rows,
    }


def ordered_lanes(lane_counts: dict[str, Any]) -> list[str]:
    known = [lane for lane in LANE_ORDER if lane in lane_counts]
    unknown = sorted(lane for lane in lane_counts if lane not in set(known))
    return known + unknown


def write_markdown(frontier: dict[str, Any], output_path: Path) -> None:
    s = frontier["summary"]
    lane_counts = frontier["lane_counts"]
    rows = frontier["rows"]
    by_lane: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_lane[row["expansion_lane"]].append(row)

    lines = [
        "# Localization Macro Expansion Frontier",
        "",
        "Generated by `tools/build_localization_macro_expansion_frontier.py` from",
        "`build/localization-authoring-command-frontier.json`.",
        "",
        "This is the work queue for turning recovered `.MSG` source syntax into",
        "portable text/script asset semantics without checking in dialogue bodies.",
        "",
        "## Summary",
        "",
        f"- Authoring commands tracked: `{s['commands']}`",
        f"- Direct runtime hints: `{s['runtime_mapped']}`",
        f"- Macro or markup commands needing expansion models: `{s['macro_or_markup_commands']}`",
        f"- Macro or markup occurrences: `{s['macro_or_markup_occurrences']}`",
        f"- Runtime hints by confidence: high `{s['runtime_high_confidence']}`, medium `{s['runtime_medium_confidence']}`, low `{s['runtime_low_confidence']}`",
        f"- Expansion lanes: `{s['expansion_lanes']}`",
        "",
        "## Expansion Lanes",
        "",
        "| Lane | Commands | Occurrences | Next seam |",
        "| --- | ---: | ---: | --- |",
    ]
    for lane in ordered_lanes(lane_counts):
        counts = lane_counts[lane]
        lines.append(
            f"| `{lane}` | {counts['commands']} | {counts['occurrences']} | "
            f"{NEXT_SEAM_BY_EXPANSION.get(lane, 'Classify expansion lane.')} |"
        )

    lines.extend(
        [
            "",
            "## Non-Runtime Expansion Work",
            "",
            "These commands do not yet have direct runtime hints. They are grouped by",
            "the kind of expansion model they need next.",
            "",
        ]
    )
    for lane in ordered_lanes(lane_counts):
        if lane == "direct_runtime_hint":
            continue
        lane_rows = sorted(by_lane[lane], key=lambda row: (-int(row["count"]), row["command"]))
        lines.append(f"### `{lane}`")
        lines.append("")
        lines.append("| Command | Count | Files | Records | Bucket | Argument shapes |")
        lines.append("| --- | ---: | ---: | ---: | --- | --- |")
        for row in lane_rows:
            lines.append(
                f"| `{row['command']}` | {row['count']} | {row['files']} | "
                f"{row['metadata_records']} | `{row['bucket']}` | {shape_label(row)} |"
            )
        lines.append("")

    runtime_rows = sorted(
        by_lane.get("direct_runtime_hint", []),
        key=lambda row: ({"low": 0, "medium": 1, "high": 2}.get(confidence(row), 3), -int(row["count"]), row["command"]),
    )
    lines.extend(
        [
            "## Runtime Hints To Revisit",
            "",
            "High-confidence rows are mostly stable. Medium and low confidence rows are",
            "the best follow-up candidates for operand-shape checks.",
            "",
            "| Command | Count | Runtime hint | Argument shapes |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for row in runtime_rows:
        if confidence(row) == "high":
            continue
        lines.append(
            f"| `{row['command']}` | {row['count']} | {hint_label(row)} | {shape_label(row)} |"
        )

    lines.extend(
        [
            "",
            "## Next Manual Seams",
            "",
            "1. Build source-macro expansion notes for `text_vm_control_macro`, because",
            "   branch/register macros are the most important for reassembly-friendly",
            "   scripts. Start with `notes/localization-control-macro-context.md`",
            "   and `notes/localization-control-macro-expansion-model.md`.",
            "2. Model display and inventory macro aliases next; these are likely to",
            "   become the romhacker-facing text editing vocabulary.",
            "3. Keep movement/camera/visibility macros joined to C3/map-object work",
            "   rather than treating them as ordinary text VM commands.",
            "",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authoring-frontier", type=Path, default=DEFAULT_AUTHORING_FRONTIER)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    authoring = load_frontier(args.authoring_frontier)
    frontier = build_frontier(authoring)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(frontier, indent=2, sort_keys=True), encoding="utf-8")
    write_markdown(frontier, args.markdown_out)
    s = frontier["summary"]
    print(f"wrote {args.json_out}")
    print(f"wrote {args.markdown_out}")
    print(
        "commands={commands} runtime={runtime_mapped} macro_or_markup={macro_or_markup_commands}".format(
            **s
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
