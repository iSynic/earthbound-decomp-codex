from __future__ import annotations

import argparse
import fnmatch
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INDEX = ROOT / "build" / "ref-index.json"
GENERATED_NOTE_PATTERNS = (
    "bank-*-reference-frontier.md",
    "bank-*-working-name-proposals.md",
    "bank-*-progress-audit.md",
    "bank-0-1-progress-audit.md",
    "bank-*-closure.md",
    "script-payloads-*.md",
    "data-contracts-*.md",
)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_index(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def bank_entries(index: dict[str, Any], bank: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for entry in index.get("entries", []):
        if entry.get("bank") == bank:
            entries.append(entry)
            continue
        address = entry.get("address")
        if isinstance(address, str) and address.startswith(f"{bank}:"):
            entries.append(entry)
    return entries


def is_generated_note_mention(entry: dict[str, Any]) -> bool:
    if entry.get("kind") != "note-mention":
        return False
    path = str(entry.get("path", ""))
    if not path.startswith("notes/"):
        return False
    name = Path(path).name
    return any(fnmatch.fnmatch(name, pattern) for pattern in GENERATED_NOTE_PATTERNS)


def include_key(entry: dict[str, Any]) -> int:
    address = entry.get("address")
    if isinstance(address, str) and ":" in address:
        return int(address.split(":", 1)[1], 16)
    return 0x10000


def format_entry(entry: dict[str, Any]) -> str:
    address = entry.get("address", "")
    addr = f"`{address}` " if address else ""
    name = entry.get("name", "")
    path = entry.get("path", "")
    line = f":{entry['line']}" if entry.get("line") else ""
    return f"- {addr}`{name}` ({entry.get('source')}/{entry.get('kind')}) - `{path}{line}`"


def render_report(index: dict[str, Any], bank: str, limit: int) -> str:
    entries = [
        entry for entry in bank_entries(index, bank)
        if not is_generated_note_mention(entry)
    ]
    by_kind = Counter(entry.get("kind", "") for entry in entries)
    by_source = Counter(entry.get("source", "") for entry in entries)

    includes = [
        entry for entry in entries
        if entry.get("kind") == "bank-include" and entry.get("source") == "ebsrc-main"
    ]
    globals_ = [
        entry for entry in entries
        if entry.get("kind") == "global-symbol" and entry.get("source") == "ebsrc-main"
    ]
    legacy = [
        entry for entry in entries
        if entry.get("kind") == "legacy-label"
    ]
    local_notes = [
        entry for entry in entries
        if entry.get("kind") == "note-mention"
    ]
    working = [
        entry for entry in entries
        if entry.get("kind") == "working-name"
    ]

    exact_note_by_addr: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in local_notes:
        if entry.get("address"):
            exact_note_by_addr[entry["address"]].append(entry)

    include_rows = sorted(includes, key=include_key)
    unknown_includes = [
        entry for entry in include_rows
        if "/unknown/" in str(entry.get("name", "")).lower() or "/unknown/" in str(entry.get("path", "")).lower()
    ]
    unnoted_unknown = [
        entry for entry in unknown_includes
        if entry.get("address") and not exact_note_by_addr.get(entry["address"])
    ]
    named_without_addr = [
        entry for entry in include_rows
        if entry.get("named") and not entry.get("address")
    ]
    exact_ref_addrs = {
        entry["address"]
        for entry in entries
        if entry.get("address") and entry.get("source") in {"ebsrc-main", "earthbound-disasm-legacy"}
    }
    noted_ref_addrs = sorted(addr for addr in exact_ref_addrs if exact_note_by_addr.get(addr))

    lines = [
        f"# Bank {bank} reference frontier",
        "",
        "Generated from `build/ref-index.json`. Generated frontier, proposal, audit, and closure notes are excluded from local coverage counts.",
        "",
        "## Summary",
        "",
        f"- entries: `{len(entries)}`",
        f"- exact local working names: `{len(working)}`",
        f"- local note mentions: `{len(local_notes)}`",
        "",
        "By source:",
    ]
    for source, count in sorted(by_source.items()):
        lines.append(f"- `{source}`: `{count}`")
    lines.extend(["", "By kind:"])
    for kind, count in sorted(by_kind.items()):
        lines.append(f"- `{kind}`: `{count}`")

    lines.extend(
        [
            "",
            "## Ebsrc Include Queue",
            "",
            f"- include entries: `{len(include_rows)}`",
            f"- named includes without encoded address: `{len(named_without_addr)}`",
            f"- unknown address-bearing includes: `{len(unknown_includes)}`",
            f"- unknown address-bearing includes without exact local note mention: `{len(unnoted_unknown)}`",
            "",
        ]
    )
    for entry in include_rows[:limit]:
        lines.append(format_entry(entry))
    if len(include_rows) > limit:
        lines.append(f"- ... {len(include_rows) - limit} more")

    lines.extend(["", "## Named Ref Families Without Encoded Address", ""])
    for entry in named_without_addr[:limit]:
        lines.append(format_entry(entry))
    if len(named_without_addr) > limit:
        lines.append(f"- ... {len(named_without_addr) - limit} more")

    lines.extend(["", "## Unnoted Unknown Include Starts", ""])
    for entry in unnoted_unknown[:limit]:
        lines.append(format_entry(entry))
    if len(unnoted_unknown) > limit:
        lines.append(f"- ... {len(unnoted_unknown) - limit} more")

    lines.extend(["", "## Local Coverage Of Ref Addresses", ""])
    for address in noted_ref_addrs[:limit]:
        examples = exact_note_by_addr[address][:3]
        notes = ", ".join(f"`{item['path']}:{item.get('line', '?')}`" for item in examples)
        extra = len(exact_note_by_addr[address]) - len(examples)
        suffix = f", +{extra} more" if extra else ""
        lines.append(f"- `{address}` -> {notes}{suffix}")
    if len(noted_ref_addrs) > limit:
        lines.append(f"- ... {len(noted_ref_addrs) - limit} more")

    lines.extend(["", "## Legacy Anchors", ""])
    for entry in sorted(legacy, key=include_key)[:limit]:
        lines.append(format_entry(entry))
    if len(legacy) > limit:
        lines.append(f"- ... {len(legacy) - limit} more")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a bank-specific reference frontier report.")
    parser.add_argument("bank", help="canonical bank, e.g. C3")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--limit", type=int, default=120)
    args = parser.parse_args()

    bank = args.bank.upper()
    index_path = args.index if args.index.is_absolute() else ROOT / args.index
    index = load_index(index_path)
    markdown = render_report(index, bank, args.limit)
    output = args.output or (ROOT / "notes" / f"bank-{bank.lower()}-reference-frontier.md")
    output = output if output.is_absolute() else ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")
    print(f"Wrote {rel(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
