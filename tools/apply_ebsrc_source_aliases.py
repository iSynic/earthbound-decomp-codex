#!/usr/bin/env python3
"""Apply safe restored-ebsrc compatibility aliases to local source modules."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "ebsrc-knowns-integration-candidates.json"
LABEL_RE = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*):")
ALIAS_RE = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\S+)")
BYTES_ALIAS_RE = re.compile(r"^(\s*)!([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\S+)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="ignore").splitlines()


def newline_for(path: Path) -> str:
    raw = path.read_bytes()
    return "\r\n" if b"\r\n" in raw else "\n"


def write_lines(path: Path, lines: list[str]) -> None:
    newline = newline_for(path)
    path.write_text(newline.join(lines).rstrip() + newline, encoding="utf-8")


def source_symbol_definitions() -> set[str]:
    symbols: set[str] = set()
    for path in sorted((ROOT / "src").rglob("*.asm")):
        for line in read_lines(path):
            match = LABEL_RE.match(line) or ALIAS_RE.match(line) or BYTES_ALIAS_RE.match(line)
            if match:
                symbols.add(match.group(2))
    return symbols


def find_target(lines: list[str], local_name: str) -> tuple[int, str] | None:
    for index, line in enumerate(lines):
        label_match = LABEL_RE.match(line)
        if label_match:
            label = label_match.group(2)
            if label == local_name or label.endswith(f"_{local_name}"):
                return index, label
        alias_match = ALIAS_RE.match(line)
        if alias_match:
            alias = alias_match.group(2)
            if alias == local_name or alias.endswith(f"_{local_name}"):
                return index, alias_match.group(3)
    return None


def find_bytes_target(lines: list[str], local_name: str, source_target: str) -> tuple[int, str] | None:
    for index, line in enumerate(lines):
        label_match = LABEL_RE.match(line)
        if label_match:
            label = label_match.group(2)
            if label == source_target or label == local_name or label.endswith(f"_{local_name}"):
                return index, label
        alias_match = BYTES_ALIAS_RE.match(line)
        if alias_match:
            alias = alias_match.group(2)
            if alias == local_name or alias.endswith(f"_{local_name}"):
                return index, alias_match.group(3)
    return None


def insert_alias(lines: list[str], index: int, symbol: str, target: str, include_path: str, *, bytes_mode: bool) -> bool:
    prefix = "!" if bytes_mode else ""
    alias_line = f"{prefix}{symbol} = {target}"
    if any(line.strip() == alias_line for line in lines):
        return False
    comment = f"; ebsrc: {symbol}"
    if include_path:
        comment += f" ({include_path})"
    insertion = [comment, alias_line]
    if index > 0 and lines[index - 1].strip():
        insertion.insert(0, "")
    lines[index:index] = insertion
    return True


def ready_records(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        record
        for record in data.get("candidates", [])
        if record.get("community_alignment_status") == "source_alias_ready"
        and record.get("source_kind") == "bank-include"
        and record.get("ebsrc_symbol")
        and record.get("local_name")
        and record.get("local_source_path")
    ]


def apply_record(record: dict[str, Any], global_symbols: set[str], *, dry_run: bool) -> tuple[str, list[Path]]:
    symbol = str(record["ebsrc_symbol"])
    local_name = str(record["local_name"])
    source_path = ROOT / str(record["local_source_path"])
    include_path = str(record.get("include_path") or "")
    if symbol in global_symbols:
        return "skipped_global_symbol_exists", []
    if not source_path.exists():
        return "skipped_source_missing", []

    source_lines = read_lines(source_path)
    source_target = find_target(source_lines, local_name)
    if not source_target:
        return "skipped_local_target_missing", []

    source_index, source_alias_target = source_target
    changed: list[Path] = []
    source_changed = insert_alias(
        source_lines,
        source_index,
        symbol,
        source_alias_target,
        include_path,
        bytes_mode=False,
    )
    if source_changed:
        changed.append(source_path)

    bytes_path = source_path.with_name(source_path.name.replace(".asm", ".bytes.asar.asm"))
    if bytes_path.exists():
        bytes_lines = read_lines(bytes_path)
        bytes_target = find_bytes_target(bytes_lines, local_name, source_alias_target)
        if bytes_target:
            bytes_index, bytes_alias_target = bytes_target
            if insert_alias(bytes_lines, bytes_index, symbol, bytes_alias_target, include_path, bytes_mode=True):
                changed.append(bytes_path)
            if not dry_run and bytes_path in changed:
                write_lines(bytes_path, bytes_lines)

    if not dry_run and source_path in changed:
        write_lines(source_path, source_lines)
    if changed:
        global_symbols.add(symbol)
        return "applied", changed
    return "already_present_in_target", []


def main() -> int:
    args = parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    global_symbols = source_symbol_definitions()
    counts: dict[str, int] = {}
    changed_paths: set[Path] = set()
    for record in ready_records(data):
        status, changed = apply_record(record, global_symbols, dry_run=args.dry_run)
        counts[status] = counts.get(status, 0) + 1
        changed_paths.update(changed)
    mode = "DRY RUN" if args.dry_run else "APPLIED"
    print(f"{mode}: ebsrc source aliases")
    for status, count in sorted(counts.items()):
        print(f"- {status}: {count}")
    if changed_paths:
        print("Changed paths:")
        for path in sorted(changed_paths):
            print(f"- {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
