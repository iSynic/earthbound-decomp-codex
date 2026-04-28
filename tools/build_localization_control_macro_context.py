#!/usr/bin/env python3
"""Summarize structural context for recovered localization control macros.

This reads ignored `.MSG` source and emits command-name-only context for the
control macro lane. No dialogue bodies or full source records are written.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = ROOT / "refs" / "earthbound-script-source-1995-03-25"
DEFAULT_MACRO_FRONTIER = ROOT / "build" / "localization-macro-expansion-frontier.json"
DEFAULT_JSON = ROOT / "build" / "localization-control-macro-context.json"
DEFAULT_MARKDOWN = ROOT / "notes" / "localization-control-macro-context.md"

COMMAND_RE = re.compile(r"@!?[A-Z0-9_]+(?:\s*\(([^)]*)\))?")
RECORD_START_RE = re.compile(r"(?m)^;@Habitat:")


def read_msg(path: Path) -> str:
    return path.read_text(encoding="cp932", errors="replace")


def command_name(match_text: str) -> str:
    return match_text.split("(", 1)[0].strip()


def argument_shape(args: str | None) -> str:
    if args is None:
        return "bare"
    stripped = args.strip()
    if not stripped:
        return "empty"
    return f"{len([part for part in stripped.split(',')])}_arg"


def split_records(text: str) -> list[str]:
    starts = [match.start() for match in RECORD_START_RE.finditer(text)]
    if not starts:
        return [text]
    records = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(text)
        records.append(text[start:end])
    return records


def load_control_macros(path: Path) -> list[str]:
    frontier = json.loads(path.read_text(encoding="utf-8"))
    return [
        row["command"]
        for row in frontier["rows"]
        if row.get("expansion_lane") == "text_vm_control_macro"
    ]


def collect(source_dir: Path, macro_frontier: Path) -> dict[str, Any]:
    target_macros = set(load_control_macros(macro_frontier))
    rows: dict[str, dict[str, Any]] = {
        command: {
            "command": command,
            "hits": 0,
            "files": Counter(),
            "records": 0,
            "argument_shapes": Counter(),
            "previous_commands": Counter(),
            "next_commands": Counter(),
            "record_cooccurrence": Counter(),
        }
        for command in sorted(target_macros)
    }

    for path in sorted(source_dir.glob("*.MSG")):
        for record in split_records(read_msg(path)):
            tokens = [
                {
                    "command": command_name(match.group(0)),
                    "shape": argument_shape(match.group(1)),
                }
                for match in COMMAND_RE.finditer(record)
            ]
            if not tokens:
                continue
            commands_in_record = Counter(token["command"] for token in tokens)
            record_targets = sorted(set(commands_in_record) & target_macros)
            for command in record_targets:
                rows[command]["records"] += 1
                for other, count in commands_in_record.items():
                    if other != command:
                        rows[command]["record_cooccurrence"][other] += count
            for index, token in enumerate(tokens):
                command = token["command"]
                if command not in target_macros:
                    continue
                row = rows[command]
                row["hits"] += 1
                row["files"][path.name] += 1
                row["argument_shapes"][token["shape"]] += 1
                if index > 0:
                    row["previous_commands"][tokens[index - 1]["command"]] += 1
                if index + 1 < len(tokens):
                    row["next_commands"][tokens[index + 1]["command"]] += 1

    serial_rows = []
    for command, row in rows.items():
        serial_rows.append(
            {
                "command": command,
                "hits": row["hits"],
                "file_count": len(row["files"]),
                "record_count": row["records"],
                "top_files": row["files"].most_common(5),
                "argument_shapes": row["argument_shapes"].most_common(),
                "previous_commands": row["previous_commands"].most_common(8),
                "next_commands": row["next_commands"].most_common(8),
                "record_cooccurrence": row["record_cooccurrence"].most_common(12),
            }
        )

    return {
        "generated_by": "tools/build_localization_control_macro_context.py",
        "source_dir": str(source_dir.relative_to(ROOT) if source_dir.is_relative_to(ROOT) else source_dir),
        "source_frontier": str(macro_frontier.relative_to(ROOT) if macro_frontier.is_relative_to(ROOT) else macro_frontier),
        "summary": {
            "control_macros": len(serial_rows),
            "total_hits": sum(row["hits"] for row in serial_rows),
            "records_with_control_macros": sum(row["record_count"] for row in serial_rows),
        },
        "macros": sorted(serial_rows, key=lambda row: (-row["hits"], row["command"])),
    }


def pair_label(pairs: list[list[Any]] | list[tuple[Any, Any]]) -> str:
    if not pairs:
        return "-"
    return ", ".join(f"`{name}`:{count}" for name, count in pairs)


def write_markdown(context: dict[str, Any], output_path: Path) -> None:
    s = context["summary"]
    lines = [
        "# Localization Control Macro Context",
        "",
        "Generated by `tools/build_localization_control_macro_context.py` from",
        "the ignored recovered `.MSG` source and",
        "`build/localization-macro-expansion-frontier.json`.",
        "",
        "This note records only command names, counts, argument-shape counts, and",
        "adjacency/co-occurrence summaries. It does not include dialogue bodies or",
        "full recovered source records.",
        "",
        "## Summary",
        "",
        f"- Control macros tracked: `{s['control_macros']}`",
        f"- Total control macro hits: `{s['total_hits']}`",
        f"- Macro-record memberships: `{s['records_with_control_macros']}`",
        "",
        "## Macro Context",
        "",
        "| Command | Hits | Files | Records | Argument shapes | Common previous | Common next | Common co-occurring commands |",
        "| --- | ---: | ---: | ---: | --- | --- | --- | --- |",
    ]
    for row in context["macros"]:
        lines.append(
            f"| `{row['command']}` | {row['hits']} | {row['file_count']} | "
            f"{row['record_count']} | {pair_label(row['argument_shapes'])} | "
            f"{pair_label(row['previous_commands'][:4])} | "
            f"{pair_label(row['next_commands'][:4])} | "
            f"{pair_label(row['record_cooccurrence'][:6])} |"
        )

    lines.extend(
        [
            "",
            "## Expansion Read",
            "",
            "- Register helpers such as `@SET_LOOPREG`, `@LOAD_REG`, `@SAVE_REG`,",
            "  `@SET_REG`, `@CMP`, `@EQ`, `@INC`, `@SUB`, and `@NOT` should be",
            "  modeled as source-level helpers around the existing work/arg memory",
            "  text VM commands before assigning exact byte sequences.",
            "- Multi-way branch helpers such as `@ONGOSUB`, `@ONGOTO`, `@SELGOTO`,",
            "  and `@SEL_TEL_GOSUB` should be checked against `CALL_TEXT`, `JUMP`,",
            "  `JUMP_MULTI`, `JUMP_IF_TRUE`, and `JUMP_IF_FALSE` families.",
            "- The next useful manual proof is not another command count; it is a",
            "  small expansion note for one macro pair, preferably `@SET_LOOPREG`",
            "  plus `@CMP`, because that pair is frequent and structurally central.",
            "",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--macro-frontier", type=Path, default=DEFAULT_MACRO_FRONTIER)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    context = collect(args.source_dir, args.macro_frontier)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(context, indent=2, sort_keys=True), encoding="utf-8")
    write_markdown(context, args.markdown_out)
    s = context["summary"]
    print(f"wrote {args.json_out}")
    print(f"wrote {args.markdown_out}")
    print(
        "control_macros={control_macros} total_hits={total_hits}".format(**s)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
