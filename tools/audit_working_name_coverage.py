#!/usr/bin/env python3
"""Report working-name coverage for selected banks.

This is a lightweight scout for the naming pass. It compares every bank address
mentioned in each note against the explicit ``## Working Names`` entries parsed
by ``extract_working_names.py`` and lists notes that still have unpromoted
addresses. By default the comparison is note-local: an address mentioned in a
note is covered only when that same note names it. Use ``--scope global`` to
ask a different question: whether an address has a working name anywhere in the
notes corpus. Use ``--mention-kind headings`` to ignore incidental xrefs and
only audit addresses that appear in Markdown headings or titles.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import extract_working_names


SKIP_NOTE_NAMES = {
    "bank-c0-first-pass.md",
    "bank-c0-entry-notes.md",
    "bank-c0-c2-closure.md",
    "bank-c3-closure.md",
    "bank-c4-closure.md",
    "bank-c4-progress-audit.md",
    "bank-c4-reference-frontier.md",
    "bank-c4-working-name-proposals.md",
    "data-contracts-c0-c2.md",
    "data-contracts-c0-c3.md",
    "data-contracts-c0-c4.md",
    "c3-source-data-map.md",
    "c3-source-extraction-candidates.md",
    "script-payloads-c3.md",
    "rom-patch-overworld-stutter-plan.md",
}

DEFAULT_SUPPRESSIONS = Path("notes/working-name-audit-suppressions.json")


def collect_note_mentions(
    root: Path,
    banks: set[str],
    mention_kind: str,
) -> dict[str, set[str]]:
    mentions: dict[str, set[str]] = {}
    for note in extract_working_names.iter_notes(root):
        if note.name in SKIP_NOTE_NAMES:
            continue
        rel = note.relative_to(root).as_posix()
        found: set[str] = set()
        text = note.read_text(encoding="utf-8", errors="ignore")
        in_fence = False
        for line in text.splitlines():
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            if mention_kind == "headings" and not line.startswith("#"):
                continue
            for match in extract_working_names.ADDR_RE.finditer(line):
                address = extract_working_names.normalize_address(match.group(1))
                if address[:2] in banks:
                    found.add(address)
        if found:
            mentions[rel] = found
    return mentions


def collect_named_addresses(root: Path, banks: set[str]) -> dict[str, set[str]]:
    by_note: dict[str, set[str]] = defaultdict(set)
    for entry in extract_working_names.parse_notes(root):
        if entry.address[:2] in banks:
            by_note[entry.note].add(entry.address)
    return by_note


def load_suppressions(root: Path, path: Path | None) -> dict[str, set[str]]:
    if path is None:
        return defaultdict(set)

    resolved = path if path.is_absolute() else root / path
    if not resolved.exists():
        return defaultdict(set)

    payload = json.loads(resolved.read_text(encoding="utf-8"))
    suppressed: dict[str, set[str]] = defaultdict(set)
    for entry in payload.get("suppressions", []):
        note = entry.get("note")
        address = entry.get("address")
        if not note or not address:
            continue
        suppressed[str(note)].add(extract_working_names.normalize_address(str(address)))
    return suppressed


def render_report(
    mentions: dict[str, set[str]],
    named: dict[str, set[str]],
    suppressed: dict[str, set[str]],
    min_missing: int,
    scope: str,
    show_suppressed: bool,
) -> str:
    rows: list[tuple[int, int, int, str, list[str], list[str]]] = []
    global_named = set().union(*named.values()) if named else set()
    for note, addresses in mentions.items():
        named_here = global_named if scope == "global" else named.get(note, set())
        suppressed_here = suppressed.get(note, set())
        missing = sorted(addresses - named_here - suppressed_here)
        hidden = sorted((addresses - named_here) & suppressed_here)
        if len(missing) >= min_missing:
            rows.append((len(missing), len(addresses), len(hidden), note, missing, hidden))

    rows.sort(key=lambda row: (-row[0], row[3]))

    lines = [
        "# Working Name Coverage Audit",
        "",
        "| Note | Mentioned | Suppressed | Unnamed | First Unnamed Addresses |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for missing_count, mentioned_count, hidden_count, note, missing, hidden in rows:
        preview = ", ".join(f"`{address}`" for address in missing[:12])
        if len(missing) > 12:
            preview += f", `+{len(missing) - 12} more`"
        if show_suppressed and hidden:
            hidden_preview = ", ".join(f"`{address}`" for address in hidden[:6])
            preview = f"{preview}<br>suppressed: {hidden_preview}" if preview else f"suppressed: {hidden_preview}"
        lines.append(
            f"| `{note}` | {mentioned_count} | {hidden_count} | {missing_count} | {preview} |"
        )

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--banks",
        nargs="+",
        default=["C0"],
        help="Banks to inspect, e.g. C0 C1 C2.",
    )
    parser.add_argument(
        "--min-missing",
        type=int,
        default=1,
        help="Only show notes with at least this many unpromoted addresses.",
    )
    parser.add_argument(
        "--scope",
        choices=["note", "global"],
        default="note",
        help="Compare mentions against names in the same note or anywhere in the notes corpus.",
    )
    parser.add_argument(
        "--mention-kind",
        choices=["all", "headings"],
        default="all",
        help="Audit all address mentions or only addresses in Markdown headings/titles.",
    )
    parser.add_argument(
        "--suppressions",
        type=Path,
        default=DEFAULT_SUPPRESSIONS,
        help="JSON file with intentional note/address suppressions. Use an empty path to disable.",
    )
    parser.add_argument(
        "--show-suppressed",
        action="store_true",
        help="Show suppressed addresses in each emitted row preview.",
    )
    args = parser.parse_args()

    root = extract_working_names.workspace_root()
    banks = {bank.upper() for bank in args.banks}
    mentions = collect_note_mentions(root, banks, args.mention_kind)
    named = collect_named_addresses(root, banks)
    suppressed = load_suppressions(root, args.suppressions)
    print(
        render_report(
            mentions,
            named,
            suppressed,
            args.min_missing,
            args.scope,
            args.show_suppressed,
        ),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
