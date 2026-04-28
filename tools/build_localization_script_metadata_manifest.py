#!/usr/bin/env python3
"""Build an ignored manifest from recovered EarthBound localization .MSG source.

The source corpus is intentionally kept under ignored refs/. This manifest is
for local analysis only and does not include dialogue bodies. It preserves
metadata records, labels, control-command names, and symbol references so ROM
maps can be joined to the original authoring format without copying script text
into tracked docs.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = ROOT / "refs" / "earthbound-script-source-1995-03-25"
DEFAULT_JSON = ROOT / "build" / "localization-script-metadata-records.json"
DEFAULT_ACTIONSCRIPT_TSV = ROOT / "build" / "localization-actionscript-descriptors.tsv"

METADATA_KEYS = [
    "Habitat",
    "Person",
    "Figure",
    "AppearanceKey",
    "ActionScript",
    "GoodsMessage",
    "CheckMessage",
    "Message",
]

RECORD_START_RE = re.compile(r"(?m)^;@Habitat:")
METADATA_LINE_RE = re.compile(r"^;@([A-Za-z]+):\s*(.*)$")
LABEL_RE = re.compile(r"(?m)^([A-Za-z_][A-Za-z0-9_]*);")
COMMAND_RE = re.compile(r"@!?[A-Z0-9_]+")
SYMBOL_RE = re.compile(r"\b(?:FLG|PRSN|OBJ|OBJFX|ANIM|GOODS|PSI|SOUND|BGM|MSG)_[A-Za-z0-9_]+\b")


def read_msg(path: Path) -> str:
    return path.read_text(encoding="cp932", errors="replace")


def split_records(text: str) -> list[tuple[int, int, str]]:
    starts = [match.start() for match in RECORD_START_RE.finditer(text)]
    records = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(text)
        records.append((start, end, text[start:end]))
    return records


def parse_record(file_name: str, ordinal: int, start: int, end: int, text: str) -> dict:
    metadata: dict[str, str] = {}
    body_lines = []
    in_metadata = True

    for line in text.splitlines():
        if in_metadata:
            match = METADATA_LINE_RE.match(line)
            if match:
                metadata[match.group(1)] = match.group(2).strip()
                continue
            if line.strip() == "":
                continue
            in_metadata = False
        body_lines.append(line)

    body = "\n".join(body_lines)
    labels = LABEL_RE.findall(body)
    commands = COMMAND_RE.findall(body)
    symbols = SYMBOL_RE.findall(body)

    return {
        "file": file_name,
        "ordinal": ordinal,
        "byte_start_approx": start,
        "byte_end_approx": end,
        "metadata": {key: metadata.get(key, "") for key in METADATA_KEYS},
        "entry_label": labels[0] if labels else "",
        "labels": labels,
        "commands": sorted(set(commands)),
        "symbols": sorted(set(symbols)),
        "command_counts": dict(Counter(commands)),
        "symbol_counts": dict(Counter(symbols)),
        "body_line_count": len(body_lines),
        "jpn_comment_count": len(re.findall(r"(?m)^;jpn:", body)),
    }


def collect(source_dir: Path) -> dict:
    files = sorted(source_dir.glob("*.MSG"))
    if not files:
        raise SystemExit(f"no .MSG files found under {source_dir}")

    records = []
    files_without_records = []
    file_counts = []

    for path in files:
        text = read_msg(path)
        chunks = split_records(text)
        if not chunks:
            files_without_records.append(path.name)
        file_records = [
            parse_record(path.name, ordinal, start, end, chunk)
            for ordinal, (start, end, chunk) in enumerate(chunks, start=1)
        ]
        records.extend(file_records)
        file_counts.append({"file": path.name, "records": len(file_records)})

    metadata_presence: Counter[str] = Counter()
    action_descriptors: Counter[str] = Counter()
    figure_counts: Counter[str] = Counter()
    habitat_prefix_counts: Counter[str] = Counter()
    command_counts: Counter[str] = Counter()
    symbol_prefix_counts: Counter[str] = Counter()

    for record in records:
        metadata = record["metadata"]
        for key, value in metadata.items():
            if value:
                metadata_presence[key] += 1
        if metadata["ActionScript"]:
            action_descriptors[metadata["ActionScript"]] += 1
        if metadata["Figure"]:
            figure_counts[metadata["Figure"]] += 1
        if metadata["Habitat"]:
            habitat_prefix_counts[metadata["Habitat"].split("／", 1)[0]] += 1
        command_counts.update(record["command_counts"])
        for symbol in record["symbols"]:
            symbol_prefix_counts[symbol.split("_", 1)[0]] += 1

    return {
        "source_dir": str(source_dir.relative_to(ROOT) if source_dir.is_relative_to(ROOT) else source_dir),
        "encoding": "cp932",
        "file_count": len(files),
        "record_count": len(records),
        "files_without_records": files_without_records,
        "file_counts": file_counts,
        "metadata_presence": {key: metadata_presence.get(key, 0) for key in METADATA_KEYS},
        "unique_actionscript_descriptors": len(action_descriptors),
        "unique_figures": len(figure_counts),
        "unique_habitat_prefixes": len(habitat_prefix_counts),
        "top_commands": command_counts.most_common(40),
        "symbol_prefix_counts": dict(sorted(symbol_prefix_counts.items())),
        "records": records,
    }


def write_actionscript_tsv(manifest: dict, output_path: Path) -> None:
    descriptor_rows = defaultdict(lambda: {"count": 0, "files": set(), "entry_labels": []})
    for record in manifest["records"]:
        descriptor = record["metadata"]["ActionScript"]
        if not descriptor:
            continue
        row = descriptor_rows[descriptor]
        row["count"] += 1
        row["files"].add(record["file"])
        if record["entry_label"]:
            row["entry_labels"].append(record["entry_label"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerow(["actionscript_descriptor", "count", "files", "sample_entry_labels"])
        for descriptor, row in sorted(
            descriptor_rows.items(),
            key=lambda item: (-item[1]["count"], item[0]),
        ):
            writer.writerow(
                [
                    descriptor,
                    row["count"],
                    ",".join(sorted(row["files"])),
                    ",".join(row["entry_labels"][:12]),
                ]
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--actionscript-tsv", type=Path, default=DEFAULT_ACTIONSCRIPT_TSV)
    args = parser.parse_args()

    manifest = collect(args.source_dir)

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    write_actionscript_tsv(manifest, args.actionscript_tsv)

    print(f"wrote {args.json}")
    print(f"wrote {args.actionscript_tsv}")
    print(
        "records={record_count} unique_actionscript_descriptors={unique_actionscript_descriptors} "
        "files_without_records={files_without_records}".format(**manifest)
    )


if __name__ == "__main__":
    main()
