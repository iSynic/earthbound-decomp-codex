from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_contracts import load_manifest, parse_address_expression


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INDEX = ROOT / "build" / "ref-index.json"


def normalize_text(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def rel_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def format_entry(entry: dict[str, Any], *, with_address: bool = True) -> str:
    bits = []
    if with_address and entry.get("address"):
        bits.append(f"`{entry['address']}`")
    name = entry.get("name") or entry.get("include") or "<unnamed>"
    bits.append(f"`{name}`")
    bits.append(f"{entry.get('source', '?')}/{entry.get('kind', '?')}")
    location = entry.get("path", "")
    if entry.get("line"):
        location += f":{entry['line']}"
    if location:
        bits.append(location)
    extra = []
    for key in ("confidence", "domain", "struct"):
        if entry.get(key):
            extra.append(f"{key}={entry[key]}")
    if extra:
        bits.append("(" + ", ".join(extra) + ")")
    return " - " + " | ".join(bits)


def load_index(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def looks_like_address(query: str) -> bool:
    text = query.strip().upper()
    if "+" in text:
        text = text.split("+", 1)[0]
    return bool(
        re.fullmatch(r"\$[0-9A-F]{1,6}", text)
        or re.fullmatch(r"[0-9A-F]{2}:[0-9A-F]{4}", text)
        or re.fullmatch(r"[C-F][0-9A-F][0-9A-F]{4}", text)
    )


def address_string(query: str) -> str:
    addr = parse_address_expression(query)
    return f"{addr.bank:02X}:{addr.address:04X}"


def exact_entries(entries: list[dict[str, Any]], address: str) -> list[dict[str, Any]]:
    return [entry for entry in entries if entry.get("address") == address]


def nearby_entries(entries: list[dict[str, Any]], address: str, window: int, limit: int) -> list[tuple[int, dict[str, Any]]]:
    bank, off_text = address.split(":", 1)
    offset = int(off_text, 16)
    near: list[tuple[int, dict[str, Any]]] = []
    for entry in entries:
        candidate = entry.get("address")
        if not candidate or ":" not in candidate:
            continue
        if entry.get("kind") == "note-mention":
            continue
        entry_bank, entry_off_text = candidate.split(":", 1)
        if entry_bank != bank:
            continue
        delta = int(entry_off_text, 16) - offset
        if abs(delta) <= window and delta != 0:
            near.append((delta, entry))
    near.sort(key=lambda item: (abs(item[0]), item[0], item[1].get("source", ""), item[1].get("name", "")))
    return near[:limit]


def name_search(entries: list[dict[str, Any]], query: str, limit: int) -> list[dict[str, Any]]:
    needle = normalize_text(query)
    matches: list[tuple[int, dict[str, Any]]] = []
    for entry in entries:
        hay = normalize_text(str(entry.get("name", "")))
        path_hay = normalize_text(str(entry.get("path", "")))
        if not needle:
            continue
        if hay == needle:
            score = 0
        elif needle in hay:
            score = 1
        elif needle in path_hay:
            score = 2
        else:
            continue
        matches.append((score, entry))
    matches.sort(key=lambda item: (item[0], item[1].get("source", ""), item[1].get("kind", ""), item[1].get("name", "")))
    return [entry for _, entry in matches[:limit]]


def summarize_address(index: dict[str, Any], query: str, *, window: int, limit: int) -> int:
    entries = index.get("entries", [])
    address = address_string(query)
    print(f"Address: `{address}`")
    print()

    try:
        contracts = load_manifest().matches_for_address(parse_address_expression(query))
    except Exception:
        contracts = []
    if contracts:
        print("Data Contracts")
        for match in contracts[:limit]:
            field = match.field.label_at(match.record_offset) if match.field else "<unnamed field>"
            print(
                f"- `{match.contract.id}` record `{match.record_index}` offset `+0x{match.record_offset:X}` "
                f"-> `{field}`"
            )
        print()

    exact = exact_entries(entries, address)
    if exact:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for entry in exact:
            grouped.setdefault(f"{entry.get('source')}/{entry.get('kind')}", []).append(entry)
        print("Exact Hits")
        for group, group_entries in sorted(grouped.items()):
            print(f"- {group}: `{len(group_entries)}`")
            for entry in group_entries[:limit]:
                print(format_entry(entry, with_address=False))
            if len(group_entries) > limit:
                print(f"  - ... {len(group_entries) - limit} more")
        print()
    else:
        print("Exact Hits")
        print("- none")
        print()

    nearby = nearby_entries(entries, address, window, limit)
    if nearby:
        print(f"Nearby Ref Anchors (+/- 0x{window:X})")
        for delta, entry in nearby:
            sign = "+" if delta >= 0 else "-"
            print(f"- {sign}0x{abs(delta):X} " + format_entry(entry).lstrip())
        print()
    return 0


def summarize_name(index: dict[str, Any], query: str, *, limit: int) -> int:
    entries = index.get("entries", [])
    matches = name_search(entries, query, limit)
    print(f"Name Search: `{query}`")
    print()
    if not matches:
        print("- no matches")
        return 0
    for entry in matches:
        print(format_entry(entry))
    return 0


def print_summary(index: dict[str, Any]) -> None:
    summary = index.get("summary", {})
    print(f"Schema: `{index.get('schema')}`")
    print(f"Entries: `{summary.get('entries')}`")
    print(f"Addressed entries: `{summary.get('addressed_entries')}`")
    print()
    for section in ("by_source", "by_kind", "by_bank"):
        print(section)
        for key, value in sorted(summary.get(section, {}).items()):
            print(f"- `{key}`: `{value}`")
        print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Look up reference context for an address or symbol/name.")
    parser.add_argument("query", nargs="*", help="address expression or name search")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--window", type=lambda text: int(text, 0), default=0x80)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    index_path = args.index if args.index.is_absolute() else ROOT / args.index
    index = load_index(index_path)
    if args.summary:
        print_summary(index)
        return 0
    if not args.query:
        raise SystemExit("provide a query or use --summary")
    for i, query in enumerate(args.query):
        if i:
            print()
            print("---")
            print()
        if looks_like_address(query):
            summarize_address(index, query, window=args.window, limit=args.limit)
        else:
            summarize_name(index, query, limit=args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
