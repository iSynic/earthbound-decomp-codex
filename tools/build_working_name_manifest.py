#!/usr/bin/env python3
"""Build a machine-readable working-name manifest from local notes.

This complements ``extract_working_names.py``. The Markdown proposal tables are
good for review, while this JSON form is intended for later source-labeling,
porting, and tooling passes.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import extract_working_names


DEFAULT_BANKS = ("C0", "C1", "C2")

KEYWORD_TAGS = (
    ("battle-sprite", ("battle-sprite", "sprite-render")),
    ("battlebg", ("battle-visual", "battle-background")),
    ("palette", ("palette", "visual")),
    ("psi", ("battle", "psi")),
    ("battle", ("battle",)),
    ("class2", ("battle", "action-script")),
    ("text-command", ("text", "script")),
    ("text", ("text",)),
    ("window", ("window", "text")),
    ("hppp", ("hp-pp-window", "window")),
    ("hp-pp", ("hp-pp-window", "window")),
    ("menu", ("menu",)),
    ("file-select", ("file-select", "menu")),
    ("equipment", ("equipment", "menu")),
    ("inventory", ("inventory",)),
    ("item", ("item", "inventory")),
    ("overworld", ("overworld",)),
    ("entity", ("overworld", "entity")),
    ("collision", ("overworld", "collision")),
    ("teleport", ("overworld", "teleport")),
    ("sprite", ("sprite",)),
    ("audio", ("audio",)),
)


def infer_tags(note: str, section: str, name: str) -> list[str]:
    haystack = " ".join([note, section, name]).lower()
    tags: set[str] = set()
    for keyword, keyword_tags in KEYWORD_TAGS:
        if keyword in haystack:
            tags.update(keyword_tags)
    return sorted(tags)


def confidence_for(group: list[extract_working_names.WorkingName]) -> str:
    if len(group) >= 2:
        return "corroborated"
    return "proposed"


def build_manifest(root: Path, banks: tuple[str, ...]) -> dict[str, object]:
    entries = extract_working_names.parse_notes(root)
    grouped: dict[tuple[str, str], list[extract_working_names.WorkingName]] = defaultdict(list)
    for entry in entries:
        if entry.address[:2] in banks:
            grouped[(entry.address, entry.name)].append(entry)

    manifest_entries: list[dict[str, object]] = []
    for (address, name), group in sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1])):
        group.sort(key=lambda entry: (entry.note, entry.line))
        tags: set[str] = set()
        for entry in group:
            tags.update(infer_tags(entry.note, entry.section, name))
        manifest_entries.append(
            {
                "address": address,
                "bank": address[:2],
                "name": name,
                "status": "working-name",
                "confidence": confidence_for(group),
                "tags": sorted(tags),
                "evidence": [
                    {
                        "note": entry.note,
                        "line": entry.line,
                        "section": entry.section,
                    }
                    for entry in group
                ],
            }
        )

    by_bank = Counter(entry["bank"] for entry in manifest_entries)
    by_tag = Counter(
        tag
        for entry in manifest_entries
        for tag in entry["tags"]  # type: ignore[index]
    )

    return {
        "schema": "earthbound-decomp.working-names.v1",
        "generated_by": "tools/build_working_name_manifest.py",
        "banks": list(banks),
        "summary": {
            "entries": len(manifest_entries),
            "by_bank": {bank: by_bank.get(bank, 0) for bank in banks},
            "by_tag": dict(sorted(by_tag.items())),
        },
        "entries": manifest_entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--banks",
        nargs="+",
        default=list(DEFAULT_BANKS),
        help="Banks to include, e.g. C0 C1 C2.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("build/working-names-c0-c2.json"),
        help="Output JSON path.",
    )
    args = parser.parse_args()

    root = extract_working_names.workspace_root()
    banks = tuple(bank.upper() for bank in args.banks)
    manifest = build_manifest(root, banks)

    out_path = args.output if args.output.is_absolute() else root / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(
        f"Wrote {out_path.relative_to(root).as_posix()} "
        f"with {manifest['summary']['entries']} entries."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
