from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TRIAGE = Path("manifests") / "eb-m2-needs-review-triage.json"
DEFAULT_MODULE_CROSSWALK = Path("manifests") / "eb-m2-module-crosswalk.json"
DEFAULT_OUTPUT = Path("notes") / "eb-m2-boundary-review.md"


def addr_key(raw: str) -> int:
    bank, offset = raw.split(":", 1)
    return (int(bank, 16) << 16) | int(offset, 16)


def normalize_address(raw: str) -> str:
    value = raw.strip().upper().replace("$", "")
    if ":" in value:
        bank, offset = value.split(":", 1)
        return f"{bank}{offset}"
    return value


def display_address(raw: str) -> str:
    value = normalize_address(raw)
    return f"{value[:2]}:{value[2:]}"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_ranges(bank: str) -> list[dict[str, Any]]:
    path = ROOT / "build" / f"{bank.lower()}-build-candidate-ranges.json"
    if not path.exists():
        return []
    payload = load_json(path)
    return sorted(payload.get("ranges", []), key=lambda item: addr_key(str(item["start"])))


def find_local_neighbors(bank: str, address: str) -> dict[str, Any]:
    target = display_address(address)
    ranges = load_ranges(bank)
    previous = None
    current = None
    next_range = None
    for index, item in enumerate(ranges):
        start = str(item["start"])
        end = str(item["end"])
        if end == target:
            previous = item
        if start == target:
            current = item
            if index + 1 < len(ranges):
                next_range = ranges[index + 1]
        if addr_key(start) < addr_key(target) < addr_key(end):
            current = item
    return {
        "previous_ending_here": summarize_range(previous),
        "current_starting_here": summarize_range(current),
        "next_after_current": summarize_range(next_range),
    }


def summarize_range(item: dict[str, Any] | None) -> dict[str, Any] | None:
    if not item:
        return None
    return {
        "start": item.get("start"),
        "end": item.get("end"),
        "size": item.get("size"),
        "source_path": item.get("source_path"),
        "subsystem": item.get("subsystem"),
        "source_size": item.get("source_size"),
        "data_gap_size": item.get("data_gap_size"),
        "labels": item.get("labels", []),
    }


def matching_module_rows(module_crosswalk: dict[str, Any], bank: str, address: str) -> list[dict[str, Any]]:
    target = display_address(address)
    rows: list[dict[str, Any]] = []
    for entry in module_crosswalk.get("entries", []):
        if entry.get("bank") != bank:
            continue
        if entry.get("start") == target or entry.get("end") == target:
            rows.append(
                {
                    "start": entry.get("start"),
                    "end": entry.get("end"),
                    "status": entry.get("status"),
                    "role": entry.get("role"),
                    "eb_m2_module": entry.get("eb_m2_module"),
                    "local_overlaps": entry.get("local_overlaps", []),
                }
            )
    return rows


def read_source_head(path: str | None, limit: int = 28) -> list[str]:
    if not path:
        return []
    source_path = ROOT / path
    if not source_path.exists():
        return []
    return source_path.read_text(encoding="utf-8", errors="replace").splitlines()[:limit]


def start_label_recommendation(entry: dict[str, Any], neighbors: dict[str, Any]) -> dict[str, Any]:
    previous = neighbors.get("previous_ending_here")
    current = neighbors.get("current_starting_here")
    old_symbol = entry.get("old_symbol")
    canonical = entry.get("canonical_name")
    if previous and current and old_symbol and canonical:
        return {
            "decision": "candidate-start-label-fix",
            "steps": [
                f"Convert `{old_symbol}:` in the previous terminal-only source to `{old_symbol} = {canonical}`.",
                f"Add `{canonical}:` at the start of `{current['source_path']}`.",
                f"Add `{old_symbol} = {canonical}` beside the new start label so old lookups stay stable.",
                f"Regenerate and validate bank `{entry['bank']}`.",
            ],
        }
    return {
        "decision": "manual-review",
        "steps": [
            "Could not prove both a previous range ending at the address and a current range starting there.",
            "Inspect bytes and references before changing labels.",
        ],
    }


def build_review(
    triage: dict[str, Any],
    module_crosswalk: dict[str, Any],
    addresses: set[str] | None,
    banks: set[str] | None,
    buckets: set[str] | None,
) -> dict[str, Any]:
    selected: list[dict[str, Any]] = []
    for entry in triage.get("entries", []):
        if addresses and normalize_address(str(entry["address"])) not in addresses:
            continue
        if banks and str(entry["bank"]) not in banks:
            continue
        if buckets and str(entry["bucket"]) not in buckets:
            continue
        neighbors = find_local_neighbors(str(entry["bank"]), str(entry["address"]))
        current = neighbors.get("current_starting_here")
        previous = neighbors.get("previous_ending_here")
        selected.append(
            {
                "address": entry["address"],
                "bank": entry["bank"],
                "bucket": entry["bucket"],
                "priority": entry["priority"],
                "canonical_name": entry["canonical_name"],
                "old_symbol": entry["old_symbol"],
                "role": entry["role"],
                "suggested_action": entry["suggested_action"],
                "boundary_review": start_label_recommendation(entry, neighbors),
                "local_neighbors": neighbors,
                "module_crosswalk": matching_module_rows(module_crosswalk, str(entry["bank"]), str(entry["address"])),
                "previous_source_head": read_source_head(previous.get("source_path") if previous else None),
                "current_source_head": read_source_head(current.get("source_path") if current else None),
            }
        )
    return {
        "schema": "earthbound-decomp.eb-m2-boundary-review.v1",
        "generated_by": "tools/inspect_eb_m2_boundary_review.py",
        "summary": {
            "entries": len(selected),
            "candidate_start_label_fixes": sum(
                1 for entry in selected if entry["boundary_review"]["decision"] == "candidate-start-label-fix"
            ),
        },
        "entries": selected,
    }


def md_table(entries: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| Address | Bucket | Decision | EB-M2 | Old/local | Previous local range | Current local range |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for entry in entries:
        previous = entry["local_neighbors"].get("previous_ending_here") or {}
        current = entry["local_neighbors"].get("current_starting_here") or {}
        lines.append(
            "| `{address}` | `{bucket}` | `{decision}` | `{canonical}` | `{old}` | `{prev}` | `{cur}` |".format(
                address=entry["address"],
                bucket=entry["bucket"],
                decision=entry["boundary_review"]["decision"],
                canonical=entry["canonical_name"],
                old=entry["old_symbol"],
                prev=previous.get("source_path", ""),
                cur=current.get("source_path", ""),
            )
        )
    return lines


def fenced_lines(lines: list[str]) -> list[str]:
    if not lines:
        return ["```text", "(none)", "```"]
    return ["```asm", *lines, "```"]


def write_markdown(path: Path, review: dict[str, Any]) -> None:
    entries = review["entries"]
    lines = [
        "# EB-M2 Boundary Review",
        "",
        "Generated by `tools/inspect_eb_m2_boundary_review.py`.",
        "",
        "This report is evidence only. A `candidate-start-label-fix` still needs a bank rebuild and byte-equivalence validation after editing.",
        "",
        "## Summary",
        "",
        f"- entries: `{review['summary']['entries']}`",
        f"- candidate start-label fixes: `{review['summary']['candidate_start_label_fixes']}`",
        "",
        "## Queue",
        "",
        *md_table(entries),
        "",
    ]
    for entry in entries:
        lines.extend(
            [
                f"## {entry['address']} {entry['canonical_name']}",
                "",
                f"- bucket: `{entry['bucket']}`",
                f"- old/local: `{entry['old_symbol']}`",
                f"- decision: `{entry['boundary_review']['decision']}`",
                f"- suggested action: `{entry['suggested_action']}`",
                "",
                "Review steps:",
                "",
            ]
        )
        for step in entry["boundary_review"]["steps"]:
            lines.append(f"- {step}")
        lines.extend(["", "Previous source head:", "", *fenced_lines(entry["previous_source_head"])])
        lines.extend(["", "Current source head:", "", *fenced_lines(entry["current_source_head"]), ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect EB-M2/local boundary conflict evidence.")
    parser.add_argument("--triage", type=Path, default=DEFAULT_TRIAGE)
    parser.add_argument("--module-crosswalk", type=Path, default=DEFAULT_MODULE_CROSSWALK)
    parser.add_argument("--address", action="append", default=[])
    parser.add_argument("--bank", action="append", default=[])
    parser.add_argument("--bucket", action="append", default=[])
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--notes-out", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    triage_path = args.triage if args.triage.is_absolute() else ROOT / args.triage
    module_path = args.module_crosswalk if args.module_crosswalk.is_absolute() else ROOT / args.module_crosswalk
    notes_out = args.notes_out if args.notes_out.is_absolute() else ROOT / args.notes_out
    addresses = {normalize_address(address) for address in args.address} or None
    banks = {bank.upper() for bank in args.bank} or None
    buckets = set(args.bucket) or None
    review = build_review(load_json(triage_path), load_json(module_path), addresses, banks, buckets)
    write_markdown(notes_out, review)
    if args.json_out:
        json_out = args.json_out if args.json_out.is_absolute() else ROOT / args.json_out
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(review, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Wrote {notes_out.relative_to(ROOT).as_posix()} with {review['summary']['entries']} entrie(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
