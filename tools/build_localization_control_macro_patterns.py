#!/usr/bin/env python3
"""Build command-sequence pattern evidence for localization control macros.

This reads ignored recovered `.MSG` source and writes command-name-only pattern
summaries for the text-VM control macro lane. It intentionally records command
names and argument-shape classes only; dialogue text, labels, and full recovered
source records are not emitted.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = ROOT / "refs" / "earthbound-script-source-1995-03-25"
DEFAULT_MACRO_FRONTIER = ROOT / "build" / "localization-macro-expansion-frontier.json"
DEFAULT_JSON = ROOT / "build" / "localization-control-macro-patterns.json"
DEFAULT_MARKDOWN = ROOT / "notes" / "localization-control-macro-patterns.md"

COMMAND_RE = re.compile(r"@!?[A-Z0-9_]+(?:\s*\(([^)]*)\))?")
RECORD_START_RE = re.compile(r"(?m)^;@Habitat:")

FOCUS_MOTIFS = [
    ("@SET_LOOPREG", "@GOSUB"),
    ("@SET_LOOPREG", "@SET_LOOPREG"),
    ("@CMP", "@ONGOSUB"),
    ("@ONGOSUB", "@CMP"),
    ("@CMP", "@FALSE_GOTO"),
    ("@CMP", "@TRUE_GOTO"),
    ("@DSP_ITEM", "@SELGOTO"),
    ("@GOSUB", "@SELGOTO"),
    ("@SELGOTO", "@GOTO"),
    ("@SELGOTO", "@KEY"),
    ("@SELGOTO", "@KEYNP"),
    ("@SEL_TEL_GOSUB", "@GOSUB"),
]


def read_msg(path: Path) -> str:
    return path.read_text(encoding="cp932", errors="replace")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


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
    return [
        text[start : starts[index + 1] if index + 1 < len(starts) else len(text)]
        for index, start in enumerate(starts)
    ]


def load_control_macros(path: Path) -> list[str]:
    frontier = json.loads(path.read_text(encoding="utf-8"))
    return [
        row["command"]
        for row in frontier["rows"]
        if row.get("expansion_lane") == "text_vm_control_macro"
    ]


def tokenize(record: str) -> list[dict[str, str]]:
    return [
        {
            "command": command_name(match.group(0)),
            "shape": argument_shape(match.group(1)),
        }
        for match in COMMAND_RE.finditer(record)
    ]


def label_sequence(commands: Iterable[str], focus: str | None = None) -> str:
    labels = [f"[{command}]" if command == focus else command for command in commands]
    return " > ".join(labels)


def compact_sequence(commands: list[str], limit: int = 14) -> str:
    if len(commands) <= limit:
        return label_sequence(commands)
    head = commands[:7]
    tail = commands[-4:]
    return f"{label_sequence(head)} > ...({len(commands)} commands)... > {label_sequence(tail)}"


def shape_sequence(tokens: Iterable[dict[str, str]]) -> str:
    return " > ".join(f"{token['command']}({token['shape']})" for token in tokens)


def sorted_counter(counter: Counter[str], limit: int | None = None) -> list[list[Any]]:
    rows = [[key, count] for key, count in counter.most_common(limit)]
    return rows


def collect(source_dir: Path, macro_frontier: Path, window: int) -> dict[str, Any]:
    target_macros = set(load_control_macros(macro_frontier))
    focus_motifs = {tuple(motif) for motif in FOCUS_MOTIFS}

    macro_windows: dict[str, Counter[str]] = defaultdict(Counter)
    macro_shape_windows: dict[str, Counter[str]] = defaultdict(Counter)
    macro_pairs: dict[str, Counter[str]] = defaultdict(Counter)
    macro_triples: dict[str, Counter[str]] = defaultdict(Counter)
    macro_record_sequences: dict[str, Counter[str]] = defaultdict(Counter)
    motif_counts: Counter[str] = Counter()
    motif_files: dict[str, Counter[str]] = defaultdict(Counter)
    record_count = 0
    records_with_targets = 0

    for path in sorted(source_dir.glob("*.MSG")):
        for record in split_records(read_msg(path)):
            tokens = tokenize(record)
            if not tokens:
                continue
            record_count += 1
            commands = [token["command"] for token in tokens]
            target_sequence = [command for command in commands if command in target_macros]
            if target_sequence:
                records_with_targets += 1
                sequence_label = compact_sequence(target_sequence)
                for command in set(target_sequence):
                    macro_record_sequences[command][sequence_label] += 1

            for index, command in enumerate(commands):
                if command not in target_macros:
                    continue
                start = max(0, index - window)
                end = min(len(commands), index + window + 1)
                macro_windows[command][label_sequence(commands[start:end], focus=command)] += 1
                macro_shape_windows[command][shape_sequence(tokens[start:end])] += 1

            for index in range(len(commands) - 1):
                pair = (commands[index], commands[index + 1])
                pair_label = label_sequence(pair)
                if pair in focus_motifs:
                    motif_counts[pair_label] += 1
                    motif_files[pair_label][path.name] += 1
                for command in set(pair) & target_macros:
                    macro_pairs[command][pair_label] += 1

            for index in range(len(commands) - 2):
                triple = commands[index : index + 3]
                triple_label = label_sequence(triple)
                for command in set(triple) & target_macros:
                    macro_triples[command][triple_label] += 1

    macros = []
    for command in sorted(target_macros):
        macros.append(
            {
                "command": command,
                "top_windows": sorted_counter(macro_windows[command], 8),
                "top_shape_windows": sorted_counter(macro_shape_windows[command], 5),
                "top_pairs": sorted_counter(macro_pairs[command], 10),
                "top_triples": sorted_counter(macro_triples[command], 10),
                "top_control_sequences": sorted_counter(macro_record_sequences[command], 8),
            }
        )

    motifs = [
        {
            "motif": motif,
            "count": count,
            "file_count": len(motif_files[motif]),
            "top_files": motif_files[motif].most_common(5),
        }
        for motif, count in motif_counts.most_common()
    ]

    return {
        "generated_by": "tools/build_localization_control_macro_patterns.py",
        "source_dir": rel(source_dir),
        "source_frontier": rel(macro_frontier),
        "summary": {
            "control_macros": len(target_macros),
            "records_scanned": record_count,
            "records_with_control_macros": records_with_targets,
            "focus_motifs": len(FOCUS_MOTIFS),
            "focus_motif_hits": sum(motif_counts.values()),
            "window_radius": window,
        },
        "focus_motifs": motifs,
        "macros": macros,
    }


def pair_label(pairs: list[list[Any]] | list[tuple[Any, Any]]) -> str:
    if not pairs:
        return "-"
    return ", ".join(f"`{name}`:{count}" for name, count in pairs)


def write_markdown(patterns: dict[str, Any], output_path: Path) -> None:
    s = patterns["summary"]
    lines = [
        "# Localization Control Macro Patterns",
        "",
        "Generated by `tools/build_localization_control_macro_patterns.py` from",
        "the ignored recovered `.MSG` source and",
        "`build/localization-macro-expansion-frontier.json`.",
        "",
        "This report records only command names, argument-shape classes, local",
        "command windows, and adjacency/motif counts. It does not include dialogue",
        "bodies, labels, or full recovered source records.",
        "",
        "## Summary",
        "",
        f"- Control macros tracked: `{s['control_macros']}`",
        f"- Records scanned: `{s['records_scanned']}`",
        f"- Records with control macros: `{s['records_with_control_macros']}`",
        f"- Focus motifs tracked: `{s['focus_motifs']}`",
        f"- Focus motif hits: `{s['focus_motif_hits']}`",
        f"- Command-window radius: `{s['window_radius']}`",
        "",
        "## Focus Motifs",
        "",
        "| Motif | Count | Files | Top files |",
        "| --- | ---: | ---: | --- |",
    ]
    for row in patterns["focus_motifs"]:
        lines.append(
            f"| `{row['motif']}` | {row['count']} | {row['file_count']} | "
            f"{pair_label(row['top_files'])} |"
        )

    lines.extend(
        [
            "",
            "## Macro Pattern Evidence",
            "",
            "Record-level control-only sequence summaries are kept in the generated",
            "`build/localization-control-macro-patterns.json` for deeper analysis;",
            "the checked-in note keeps the readable local command evidence.",
            "",
            "| Command | Top command windows | Top adjacent pairs | Top triples |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in sorted(patterns["macros"], key=lambda item: item["command"]):
        lines.append(
            f"| `{row['command']}` | {pair_label(row['top_windows'][:3])} | "
            f"{pair_label(row['top_pairs'][:4])} | "
            f"{pair_label(row['top_triples'][:4])} |"
        )

    lines.extend(
        [
            "",
            "## Expansion Read",
            "",
            "- `@CMP` and `@ONGOSUB` form the clearest compiler-like pair: their",
            "  dominant local windows and adjacent motifs alternate between compare",
            "  setup and multi-way call dispatch.",
            "- `@SET_LOOPREG` is mostly a staging macro for repeated calls or another",
            "  staged register value. Its useful model is likely a source-level loop",
            "  or register initializer over existing text-VM working-memory commands.",
            "- `@SELGOTO` clusters around selection/display setup and direct prompt or",
            "  jump commands, so it should be treated as a selection-result branch",
            "  macro rather than a new text opcode.",
            "",
            "## Next Proof",
            "",
            "Use this report with `notes/localization-control-macro-context.md` to",
            "write exact lowering hypotheses for one motif at a time. The best next",
            "targets are `@CMP > @ONGOSUB`, then `@SET_LOOPREG > @GOSUB`, then",
            "`@DSP_ITEM > @SELGOTO` / `@SELGOTO > @GOTO`.",
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
    parser.add_argument("--window", type=int, default=2)
    args = parser.parse_args()

    patterns = collect(args.source_dir, args.macro_frontier, args.window)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(patterns, indent=2, sort_keys=True), encoding="utf-8")
    write_markdown(patterns, args.markdown_out)
    s = patterns["summary"]
    print(f"wrote {args.json_out}")
    print(f"wrote {args.markdown_out}")
    print(
        "control_macros={control_macros} records_with_control_macros={records_with_control_macros} "
        "focus_motif_hits={focus_motif_hits}".format(**s)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
