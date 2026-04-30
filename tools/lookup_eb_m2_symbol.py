from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CROSSWALK = Path("manifests") / "eb-m2-name-crosswalk.json"


def normalize_address(raw: str) -> str | None:
    text = raw.strip().upper().replace("$", "")
    if ":" in text:
        bank_text, offset_text = text.split(":", 1)
        try:
            bank = int(bank_text, 16)
            offset = int(offset_text, 16)
        except ValueError:
            return None
        if bank < 0xC0:
            bank += 0xC0
        return f"{bank:02X}{offset:04X}"
    if re.fullmatch(r"[C-F][0-9A-F]{5}", text):
        return text
    return None


def load_crosswalk(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_index(manifest: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for entry in manifest["entries"]:
        keys = {
            str(entry["address"]).upper(),
            str(entry.get("canonical_name") or "").upper(),
            str(entry.get("old_symbol") or "").upper(),
            str(entry.get("new_symbol") or "").upper(),
        }
        keys.update(str(name).upper() for name in entry.get("eb_m2_names", []))
        keys.update(str(name).upper() for name in entry.get("local_names", []))
        for key in keys:
            if key:
                index.setdefault(key, []).append(entry)
    for alias in manifest.get("aliases", []):
        key = str(alias.get("alias", "")).upper()
        address = str(alias.get("address", ""))
        if key and address:
            match = next((entry for entry in manifest["entries"] if entry["address"] == address), None)
            if match:
                index.setdefault(key, []).append(match)
    return index


def format_entry(entry: dict[str, Any], show_evidence: bool) -> str:
    aliases = sorted(
        {
            *[str(name) for name in entry.get("local_names", [])],
            *[str(name) for name in entry.get("eb_m2_names", []) if str(name) != entry.get("canonical_name")],
        }
    )
    lines = [
        f"Address: {entry['address'][:2]}:{entry['address'][2:]}",
        f"Canonical: {entry.get('canonical_name')}",
        f"Canonical source: {entry.get('canonical_source')}",
        f"Status: {entry.get('status')}",
        f"Recommended action: {entry.get('recommended_action')}",
        f"Review status: {entry.get('review_status')}",
        f"Confidence: {entry.get('confidence')}",
        f"Role: EB-M2={entry.get('role', {}).get('eb_m2')} local={entry.get('role', {}).get('local')} compatible={entry.get('role', {}).get('compatible')}",
        f"Old symbol: {entry.get('old_symbol')}",
        f"New symbol: {entry.get('new_symbol')}",
    ]
    if entry.get("conflict_reason"):
        lines.append(f"Conflict: {entry['conflict_reason']}")
    if aliases:
        lines.append("Aliases:")
        for alias in aliases[:40]:
            lines.append(f"  - {alias}")
        if len(aliases) > 40:
            lines.append(f"  - ... {len(aliases) - 40} more")
    if show_evidence:
        lines.append("EB-M2 evidence:")
        for evidence in entry.get("eb_m2_evidence", []):
            module = f" {evidence.get('module')}" if evidence.get("module") else ""
            lines.append(f"  - {evidence.get('source')}:{evidence.get('line')}{module}")
        lines.append("Local evidence:")
        for evidence in entry.get("local_evidence", []):
            lines.append(f"  - {evidence.get('source')}:{evidence.get('line')} {evidence.get('name')}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve EB-M2 names, local aliases, UNKNOWN_* labels, or addresses through the name crosswalk."
    )
    parser.add_argument("query", help="Address such as C0:0013/C00013, EB-M2 symbol, local symbol, or UNKNOWN_* alias.")
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--evidence", action="store_true", help="Print source evidence lines.")
    parser.add_argument("--json", action="store_true", help="Emit matching crosswalk entries as JSON.")
    parser.add_argument("--limit", type=int, default=12)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    crosswalk = args.crosswalk if args.crosswalk.is_absolute() else ROOT / args.crosswalk
    manifest = load_crosswalk(crosswalk)
    index = build_index(manifest)
    address = normalize_address(args.query)
    key = address or args.query.strip().upper()
    matches = index.get(key, [])
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in matches:
        if entry["address"] in seen:
            continue
        seen.add(entry["address"])
        deduped.append(entry)
    if not deduped:
        print("No matches.")
        return 1
    if args.json:
        print(json.dumps(deduped[: args.limit], indent=2))
        return 0
    for index_no, entry in enumerate(deduped[: args.limit], start=1):
        if len(deduped) > 1:
            print(f"--- match {index_no} ---")
        print(format_entry(entry, args.evidence))
    if len(deduped) > args.limit:
        print(f"... {len(deduped) - args.limit} additional matches omitted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
