#!/usr/bin/env python3
"""Extract proposed routine names from local Markdown notes.

The notes corpus often ends focused writeups with bullets like:

    - `C1:F07E` = `OpenFileSelectActionMenu`

This tool turns those scattered "Working Names" sections into a compact
proposal table that can be reviewed before labels are promoted into source.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


NOTE_GLOB = "notes/*.md"
ADDR_RE = re.compile(r"`?((?:C[0-9A-Fa-f])[:_]?[0-9A-Fa-f]{4})`?")
ASSIGN_RE = re.compile(
    r"^\s*[-*]\s+`?(C[0-9A-Fa-f][:_]?[0-9A-Fa-f]{4})`?\s*(?:=|->)\s*`?([^`]+?)`?\s*$"
)
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$")
WORKING_NAMES_RE = re.compile(r"working names?", re.IGNORECASE)
SKIP_NOTE_NAMES = {
    "bank-0-1-progress-audit.md",
    "bank-c0-progress-audit.md",
    "bank-c1-progress-audit.md",
    "bank-c2-progress-audit.md",
    "bank-c0-c2-closure.md",
    "bank-c0-working-name-proposals.md",
    "bank-c1-working-name-proposals.md",
    "bank-c2-working-name-proposals.md",
}


@dataclass(frozen=True)
class WorkingName:
    address: str
    name: str
    note: str
    line: int
    section: str


def workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def normalize_address(raw: str) -> str:
    raw = raw.upper().replace("_", ":")
    if ":" not in raw:
        raw = f"{raw[:2]}:{raw[2:]}"
    return raw


def iter_notes(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.glob(NOTE_GLOB)
        if path.is_file() and path.name not in SKIP_NOTE_NAMES
    )


def parse_notes(root: Path, include_all_assignments: bool = False) -> list[WorkingName]:
    results: list[WorkingName] = []
    for note in iter_notes(root):
        rel = note.relative_to(root).as_posix()
        current_section = ""
        in_working_names = False
        for line_no, line in enumerate(
            note.read_text(encoding="utf-8", errors="ignore").splitlines(),
            start=1,
        ):
            heading = HEADING_RE.match(line)
            if heading:
                current_section = heading.group(1).strip()
                in_working_names = WORKING_NAMES_RE.search(current_section) is not None
                continue

            match = ASSIGN_RE.match(line)
            if not match:
                continue

            # Default to explicit "Working Names" sections. Broader assignment
            # scraping is useful for audits, but it also catches "A calls B"
            # evidence bullets that are not intended as symbol proposals.
            if not in_working_names and not include_all_assignments:
                continue

            address = normalize_address(match.group(1))
            name = match.group(2).strip()
            results.append(
                WorkingName(
                    address=address,
                    name=name,
                    note=rel,
                    line=line_no,
                    section=current_section,
                )
            )
    return results


def render_markdown(entries: list[WorkingName], bank: str | None) -> str:
    filtered_entries = [
        entry for entry in entries if bank is None or entry.address.startswith(f"{bank}:")
    ]
    grouped: dict[tuple[str, str], list[WorkingName]] = {}
    for entry in filtered_entries:
        grouped.setdefault((entry.address, entry.name), []).append(entry)

    rows: list[tuple[str, str, list[WorkingName]]] = []
    for (address, name), group in grouped.items():
        group.sort(key=lambda entry: (entry.note, entry.line))
        rows.append((address, name, group))
    rows.sort(key=lambda row: (row[0], row[1]))

    title_bank = bank or "All Banks"
    lines = [
        f"# Working Name Proposals ({title_bank})",
        "",
        "Generated from local note bullets that use `ADDRESS = Name` or `ADDRESS -> Name`.",
        "",
        f"- Proposals: `{len(rows)}`",
        "",
        "| Address | Proposed Name | Evidence Notes |",
        "| --- | --- | --- |",
    ]
    for address, name, group in rows:
        evidence = "<br>".join(
            f"`{entry.note}:{entry.line}`" for entry in group[:4]
        )
        if len(group) > 4:
            evidence += f"<br>`+{len(group) - 4} more`"
        lines.append(
            f"| `{address}` | `{name}` | {evidence} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bank",
        help="Optional bank filter such as C0 or C1.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write Markdown output to this path instead of stdout.",
    )
    parser.add_argument(
        "--include-all-assignments",
        action="store_true",
        help="Also include assignment-looking bullets outside Working Names sections.",
    )
    args = parser.parse_args()

    bank = args.bank.upper() if args.bank else None
    root = workspace_root()
    entries = parse_notes(root, include_all_assignments=args.include_all_assignments)
    markdown = render_markdown(entries, bank)

    if args.output:
        out_path = args.output if args.output.is_absolute() else root / args.output
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(markdown, encoding="utf-8")
    else:
        print(markdown, end="")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
