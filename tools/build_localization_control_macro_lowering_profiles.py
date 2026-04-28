#!/usr/bin/env python3
"""Build argument-category profiles for localization control macro lowering.

This profiler reads ignored recovered `.MSG` source and emits sanitized
argument-category evidence for high-value macro motifs. It records only command
names, argument arities, and coarse argument categories, never raw argument
values, dialogue, labels, or full recovered source records.
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
DEFAULT_JSON = ROOT / "build" / "localization-control-macro-lowering-profiles.json"
DEFAULT_MARKDOWN = ROOT / "notes" / "localization-control-macro-lowering-profiles.md"

COMMAND_RE = re.compile(r"@!?[A-Z0-9_]+(?:\s*\(([^)]*)\))?")
RECORD_START_RE = re.compile(r"(?m)^;@Habitat:")
TARGETS = {
    "@CMP",
    "@DSP_ITEM",
    "@GOSUB",
    "@GOTO",
    "@KEY",
    "@KEYNP",
    "@ONGOSUB",
    "@ONGOTO",
    "@SELGOTO",
    "@SET_LOOPREG",
}
FOCUS_PAIRS = [
    ("@CMP", "@ONGOSUB"),
    ("@SET_LOOPREG", "@GOSUB"),
    ("@DSP_ITEM", "@SELGOTO"),
    ("@GOSUB", "@SELGOTO"),
    ("@SELGOTO", "@GOTO"),
    ("@SELGOTO", "@KEY"),
    ("@SELGOTO", "@KEYNP"),
]


def read_msg(path: Path) -> str:
    return path.read_text(encoding="cp932", errors="replace")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def split_records(text: str) -> list[str]:
    starts = [match.start() for match in RECORD_START_RE.finditer(text)]
    if not starts:
        return [text]
    return [
        text[start : starts[index + 1] if index + 1 < len(starts) else len(text)]
        for index, start in enumerate(starts)
    ]


def command_name(match_text: str) -> str:
    return match_text.split("(", 1)[0].strip()


def split_args(args: str | None) -> list[str]:
    if args is None:
        return []
    stripped = args.strip()
    if not stripped:
        return []
    return [part.strip() for part in stripped.split(",")]


def classify_arg(value: str) -> str:
    if not value:
        return "empty"
    upper = value.upper()
    if re.fullmatch(r"\$[0-9A-F]+", upper):
        return "hex"
    if re.fullmatch(r"-?\d+", value):
        return "decimal"
    if re.fullmatch(r"0X[0-9A-F]+", upper):
        return "hex"
    if upper.startswith("MSG_"):
        return "message_label"
    if upper.startswith("FLAG_"):
        return "flag_symbol"
    if upper.startswith("GOODS_") or upper.startswith("ITEM_"):
        return "item_symbol"
    if upper.startswith("PSI_"):
        return "psi_symbol"
    if re.fullmatch(r"[A-Z0-9_]+", upper):
        return "symbol"
    if any(char in value for char in "+-*/&|<>"):
        return "expression"
    return "other"


def arg_profile(args: list[str]) -> str:
    if not args:
        return "empty"
    categories = [classify_arg(arg) for arg in args]
    if len(categories) > 8 and len(set(categories)) == 1:
        return f"{categories[0]}x{len(categories)}"
    if len(categories) > 10:
        head = ",".join(categories[:5])
        tail = ",".join(categories[-3:])
        return f"{head},...x{len(categories) - 8},{tail}"
    return ",".join(categories)


def tokenize(record: str) -> list[dict[str, Any]]:
    tokens = []
    for match in COMMAND_RE.finditer(record):
        args = split_args(match.group(1))
        tokens.append(
            {
                "command": command_name(match.group(0)),
                "arity": len(args),
                "profile": arg_profile(args),
            }
        )
    return tokens


def counter_rows(counter: Counter[str], limit: int | None = None) -> list[list[Any]]:
    return [[key, count] for key, count in counter.most_common(limit)]


def collect(source_dir: Path) -> dict[str, Any]:
    command_profiles: dict[str, Counter[str]] = defaultdict(Counter)
    command_arities: dict[str, Counter[str]] = defaultdict(Counter)
    pair_profiles: dict[str, Counter[str]] = defaultdict(Counter)
    pair_files: dict[str, Counter[str]] = defaultdict(Counter)
    target_hits = 0
    records_scanned = 0

    focus_pairs = set(FOCUS_PAIRS)
    for path in sorted(source_dir.glob("*.MSG")):
        for record in split_records(read_msg(path)):
            tokens = tokenize(record)
            if not tokens:
                continue
            records_scanned += 1
            for token in tokens:
                command = token["command"]
                if command not in TARGETS:
                    continue
                target_hits += 1
                command_arities[command][str(token["arity"])] += 1
                command_profiles[command][token["profile"]] += 1

            for index in range(len(tokens) - 1):
                left = tokens[index]
                right = tokens[index + 1]
                pair = (left["command"], right["command"])
                if pair not in focus_pairs:
                    continue
                label = f"{left['command']}({left['profile']}) > {right['command']}({right['profile']})"
                pair_profiles[f"{pair[0]} > {pair[1]}"][label] += 1
                pair_files[f"{pair[0]} > {pair[1]}"][path.name] += 1

    commands = []
    for command in sorted(TARGETS):
        commands.append(
            {
                "command": command,
                "arity_counts": counter_rows(command_arities[command]),
                "argument_profiles": counter_rows(command_profiles[command], 12),
            }
        )

    pairs = []
    for pair in [f"{left} > {right}" for left, right in FOCUS_PAIRS]:
        pairs.append(
            {
                "pair": pair,
                "profile_counts": counter_rows(pair_profiles[pair], 12),
                "file_count": len(pair_files[pair]),
                "top_files": pair_files[pair].most_common(5),
                "hits": sum(pair_profiles[pair].values()),
            }
        )

    return {
        "generated_by": "tools/build_localization_control_macro_lowering_profiles.py",
        "source_dir": rel(source_dir),
        "summary": {
            "records_scanned": records_scanned,
            "target_commands": len(TARGETS),
            "target_command_hits": target_hits,
            "focus_pairs": len(FOCUS_PAIRS),
            "focus_pair_hits": sum(row["hits"] for row in pairs),
        },
        "commands": commands,
        "pairs": pairs,
    }


def pair_label(rows: list[list[Any]] | list[tuple[Any, Any]]) -> str:
    if not rows:
        return "-"
    return ", ".join(f"`{name}`:{count}" for name, count in rows)


def write_markdown(profiles: dict[str, Any], output_path: Path) -> None:
    s = profiles["summary"]
    lines = [
        "# Localization Control Macro Lowering Profiles",
        "",
        "Generated by `tools/build_localization_control_macro_lowering_profiles.py`",
        "from the ignored recovered `.MSG` source.",
        "",
        "This report records only command names, argument arities, and coarse",
        "argument categories. It does not include dialogue, labels, raw argument",
        "values, or full recovered source records.",
        "",
        "## Summary",
        "",
        f"- Records scanned: `{s['records_scanned']}`",
        f"- Target commands: `{s['target_commands']}`",
        f"- Target command hits: `{s['target_command_hits']}`",
        f"- Focus pairs: `{s['focus_pairs']}`",
        f"- Focus pair hits: `{s['focus_pair_hits']}`",
        "",
        "## Focus Pair Profiles",
        "",
        "| Pair | Hits | Files | Top argument profiles | Top files |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for row in profiles["pairs"]:
        lines.append(
            f"| `{row['pair']}` | {row['hits']} | {row['file_count']} | "
            f"{pair_label(row['profile_counts'][:6])} | {pair_label(row['top_files'])} |"
        )

    lines.extend(
        [
            "",
            "## Command Argument Profiles",
            "",
            "| Command | Arity counts | Argument-category profiles |",
            "| --- | --- | --- |",
        ]
    )
    for row in profiles["commands"]:
        lines.append(
            f"| `{row['command']}` | {pair_label(row['arity_counts'])} | "
            f"{pair_label(row['argument_profiles'])} |"
        )

    lines.extend(
        [
            "",
            "## Lowering Read",
            "",
            "- `@CMP` is consistently a two-argument source macro. In the strongest",
            "  pair, it feeds `@ONGOSUB` entries whose arguments are overwhelmingly",
            "  message labels.",
            "- `@ONGOSUB` has a broad arity spread overall, but the dominant",
            "  `@CMP > @ONGOSUB` pair is one-argument label-call syntax repeated in",
            "  compare/table runs.",
            "- `@SET_LOOPREG > @GOSUB` is also a one-argument staging macro followed",
            "  by one-argument call syntax, matching a source loop/list convenience.",
            "- `@DSP_ITEM > @SELGOTO`, `@GOSUB > @SELGOTO`, and the",
            "  `@SELGOTO` continuations are two-argument selection/branch forms",
            "  over item display or helper-call setup and branch destinations.",
            "",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    profiles = collect(args.source_dir)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(profiles, indent=2, sort_keys=True), encoding="utf-8")
    write_markdown(profiles, args.markdown_out)
    s = profiles["summary"]
    print(f"wrote {args.json_out}")
    print(f"wrote {args.markdown_out}")
    print(
        "target_command_hits={target_command_hits} focus_pair_hits={focus_pair_hits}".format(
            **s
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
