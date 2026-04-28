#!/usr/bin/env python3
"""Profile recovered localization authoring commands without copying dialogue.

The recovered `.MSG` source is ignored. This tool scans it locally and writes
tracked structural summaries: command counts, argument shapes, file/record
coverage, and whether the text-command semantic manifest already has a runtime
hint for the command.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from build_text_command_semantics_manifest import AUTHORING_HINTS


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = ROOT / "refs" / "earthbound-script-source-1995-03-25"
DEFAULT_TEXT_MANIFEST = ROOT / "build" / "text-command-semantics-manifest.json"
DEFAULT_JSON = ROOT / "build" / "localization-authoring-command-frontier.json"
DEFAULT_MARKDOWN = ROOT / "notes" / "localization-authoring-command-frontier.md"

COMMAND_RE = re.compile(r"@!?[A-Z0-9_]+(?:\s*\(([^)]*)\))?")
RECORD_START_RE = re.compile(r"(?m)^;@Habitat:")


def read_msg(path: Path) -> str:
    return path.read_text(encoding="cp932", errors="replace")


def command_bucket(command: str, has_runtime_hint: bool) -> str:
    if has_runtime_hint:
        return "runtime_mapped"
    if command in {"@A", "@C", "@F", "@G", "@H", "@M", "@P", "@WI"}:
        return "authoring_format_candidate"
    if "GOTO" in command or "GOSUB" in command or command in {"@CMP", "@LOAD_REG", "@SET_LOOPREG"}:
        return "branch_macro_candidate"
    if command.startswith("@DSP_"):
        return "display_macro_candidate"
    if command in {"@MOVE_GOM_CHAR", "@REMOVE_CHAR"}:
        return "movement_macro_candidate"
    if command in {"@GOODSIN_PLAYER", "@GET_ORDER_PLAYER"}:
        return "inventory_macro_candidate"
    if command.startswith("@Q_"):
        return "query_macro_candidate"
    return "needs_classification"


def argument_shape(args: str | None) -> str:
    if args is None:
        return "bare"
    stripped = args.strip()
    if not stripped:
        return "empty"
    parts = [part.strip() for part in stripped.split(",")]
    return f"{len(parts)}_arg"


def load_runtime_hints(path: Path) -> dict[str, dict[str, Any]]:
    hints = dict(AUTHORING_HINTS)
    if not path.exists():
        return hints
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for row in manifest.get("authoring_command_hints", []):
        hint = row.get("runtime_hint")
        if hint:
            hints[row["command"]] = hint
    return hints


def collect(source_dir: Path, text_manifest: Path) -> dict[str, Any]:
    runtime_hints = load_runtime_hints(text_manifest)
    files = sorted(source_dir.glob("*.MSG"))
    if not files:
        raise SystemExit(f"no .MSG files found under {source_dir}")

    command_counts: Counter[str] = Counter()
    command_files: dict[str, set[str]] = defaultdict(set)
    command_records: Counter[str] = Counter()
    command_shapes: dict[str, Counter[str]] = defaultdict(Counter)

    for path in files:
        text = read_msg(path)
        records = [match.start() for match in RECORD_START_RE.finditer(text)]
        record_ranges = []
        for index, start in enumerate(records):
            end = records[index + 1] if index + 1 < len(records) else len(text)
            record_ranges.append((start, end))

        for match in COMMAND_RE.finditer(text):
            command = match.group(0).split("(", 1)[0].strip()
            command_counts[command] += 1
            command_files[command].add(path.name)
            command_shapes[command][argument_shape(match.group(1))] += 1
            if any(start <= match.start() < end for start, end in record_ranges):
                command_records[command] += 1

    rows = []
    for command, count in command_counts.most_common():
        hint = runtime_hints.get(command)
        rows.append(
            {
                "command": command,
                "count": count,
                "files": len(command_files[command]),
                "metadata_records": command_records[command],
                "argument_shapes": dict(command_shapes[command].most_common()),
                "runtime_hint": hint,
                "bucket": command_bucket(command, hint is not None),
            }
        )

    bucket_counts = Counter(row["bucket"] for row in rows)
    return {
        "generated_by": "tools/build_localization_authoring_command_frontier.py",
        "source_dir": str(source_dir.relative_to(ROOT) if source_dir.is_relative_to(ROOT) else source_dir),
        "source_manifest": str(text_manifest.relative_to(ROOT) if text_manifest.is_relative_to(ROOT) else text_manifest),
        "summary": {
            "files": len(files),
            "commands": len(rows),
            "total_occurrences": sum(command_counts.values()),
            "runtime_mapped": bucket_counts.get("runtime_mapped", 0),
            "authoring_format_candidates": bucket_counts.get("authoring_format_candidate", 0),
            "branch_macro_candidates": bucket_counts.get("branch_macro_candidate", 0),
            "display_macro_candidates": bucket_counts.get("display_macro_candidate", 0),
            "movement_macro_candidates": bucket_counts.get("movement_macro_candidate", 0),
            "inventory_macro_candidates": bucket_counts.get("inventory_macro_candidate", 0),
            "query_macro_candidates": bucket_counts.get("query_macro_candidate", 0),
            "needs_classification": bucket_counts.get("needs_classification", 0),
        },
        "commands": rows,
    }


def hint_label(hint: dict[str, Any] | None) -> str:
    if not hint:
        return "-"
    opcode = hint["opcode"]
    if "subopcode" in hint:
        opcode = f"{opcode} {hint['subopcode']}"
    return f"`{opcode}` `{hint['name']}` ({hint['confidence']})"


def shape_label(shapes: dict[str, int]) -> str:
    return ", ".join(f"{shape}:{count}" for shape, count in shapes.items()) or "-"


def write_markdown(frontier: dict[str, Any], output_path: Path) -> None:
    s = frontier["summary"]
    lines = [
        "# Localization Authoring Command Frontier",
        "",
        "Generated by `tools/build_localization_authoring_command_frontier.py` from",
        "the ignored recovered `.MSG` source and",
        "`build/text-command-semantics-manifest.json`.",
        "",
        "This note records command names, counts, argument-shape counts, and broad",
        "classification buckets only. It does not check in dialogue bodies or source",
        "records.",
        "",
        "## Summary",
        "",
        f"- `.MSG` files scanned: `{s['files']}`",
        f"- Unique authoring commands: `{s['commands']}`",
        f"- Total command occurrences: `{s['total_occurrences']}`",
        f"- Runtime-mapped commands: `{s['runtime_mapped']}`",
        f"- Authoring/format candidates: `{s['authoring_format_candidates']}`",
        f"- Branch/control macro candidates: `{s['branch_macro_candidates']}`",
        f"- Display macro candidates: `{s['display_macro_candidates']}`",
        f"- Movement macro candidates: `{s['movement_macro_candidates']}`",
        f"- Inventory macro candidates: `{s['inventory_macro_candidates']}`",
        f"- Query macro candidates: `{s['query_macro_candidates']}`",
        f"- Still needs classification: `{s['needs_classification']}`",
        "",
        "## High-Count Runtime Mapped Commands",
        "",
        "| Command | Count | Files | Records | Runtime hint | Argument shapes |",
        "| --- | ---: | ---: | ---: | --- | --- |",
    ]
    for row in frontier["commands"]:
        if row["bucket"] != "runtime_mapped":
            continue
        lines.append(
            f"| `{row['command']}` | {row['count']} | {row['files']} | "
            f"{row['metadata_records']} | {hint_label(row['runtime_hint'])} | "
            f"{shape_label(row['argument_shapes'])} |"
        )

    lines.extend(
        [
            "",
            "## High-Count Unmapped Commands",
            "",
            "| Command | Count | Files | Records | Bucket | Argument shapes |",
            "| --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in frontier["commands"]:
        if row["bucket"] == "runtime_mapped":
            continue
        lines.append(
            f"| `{row['command']}` | {row['count']} | {row['files']} | "
            f"{row['metadata_records']} | `{row['bucket']}` | "
            f"{shape_label(row['argument_shapes'])} |"
        )

    lines.extend(
        [
            "",
            "## Next Manual Seams",
            "",
            "1. Confirm whether the authoring/format candidates expand to printable",
            "   layout bytes or remain source-only markup.",
            "2. Tie branch/control macro candidates to the known `0x06`, `0x08`,",
            "   `0x09`, and `0x0A` text VM branch/call commands.",
            "3. Split display macro candidates into direct `0x1C` leaves versus",
            "   higher-level authoring aliases.",
            "",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--text-manifest", type=Path, default=DEFAULT_TEXT_MANIFEST)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    frontier = collect(args.source_dir, args.text_manifest)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(frontier, indent=2, sort_keys=True), encoding="utf-8")
    write_markdown(frontier, args.markdown_out)
    s = frontier["summary"]
    print(f"wrote {args.json_out}")
    print(f"wrote {args.markdown_out}")
    print(
        "commands={commands} runtime_mapped={runtime_mapped} "
        "needs_classification={needs_classification}".format(**s)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
