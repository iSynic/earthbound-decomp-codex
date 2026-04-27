#!/usr/bin/env python3
"""Build a residual byte map for source-bank scaffold closure work."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from rom_tools import find_rom, hirom_to_file_offset, load_rom


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "earthbound-decomp.source-bank-residual-map.v1"


def parse_address(raw: str) -> tuple[str, int]:
    bank, address = raw.split(":", 1)
    return bank.upper(), int(address, 16)


def format_address(bank: str, address: int) -> str:
    return f"{bank}:{address:04X}"


def bank_index(bank: str) -> int:
    if bank.upper().startswith("C"):
        return int(bank, 16) - 0xC0
    return int(bank[-2:], 16)


def load_ranges(bank: str) -> list[tuple[int, int, str]]:
    path = ROOT / "build" / f"{bank.lower()}-build-candidate-ranges.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    ranges: list[tuple[int, int, str]] = []
    for entry in data.get("ranges", []):
        start_bank, start = parse_address(entry["start"])
        end_bank, end = parse_address(entry["end"])
        if start_bank != bank or end_bank != bank:
            continue
        ranges.append((start, end, entry["source_path"]))
    return sorted(ranges)


def merge_intervals(intervals: list[tuple[int, int, str]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end, _source in sorted(intervals):
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
            continue
        merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def invert_intervals(intervals: list[tuple[int, int]], bank_end: int = 0x10000) -> list[tuple[int, int]]:
    residuals: list[tuple[int, int]] = []
    cursor = 0
    for start, end in intervals:
        if cursor < start:
            residuals.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < bank_end:
        residuals.append((cursor, bank_end))
    return residuals


def load_ebsrc_entries(bank: str) -> list[dict[str, Any]]:
    path = ROOT / "build" / f"ebsrc-bank-{bank.lower()}-map.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    entries: list[dict[str, Any]] = []
    for entry in data.get("entries", []):
        start_raw = entry.get("start")
        end_raw = entry.get("end")
        start = end = None
        if start_raw:
            entry_bank, start = parse_address(start_raw)
            if entry_bank != bank:
                continue
        if end_raw:
            entry_bank, end = parse_address(end_raw)
            if entry_bank != bank:
                continue
        entries.append({**entry, "_start_int": start, "_end_int": end})
    return entries


def entry_overlaps(entry: dict[str, Any], start: int, end: int) -> bool:
    entry_start = entry.get("_start_int")
    entry_end = entry.get("_end_int")
    if entry_start is None:
        return False
    if entry_end is None:
        return start <= entry_start < end
    return entry_start < end and start < entry_end


def rom_slice(rom: bytes, bank: str, start: int, end: int) -> bytes:
    bank_num = int(bank, 16)
    start_offset = hirom_to_file_offset(bank_num, start, len(rom))
    end_offset = hirom_to_file_offset(bank_num, end, len(rom))
    if start_offset is None or end_offset is None:
        raise ValueError(f"unable to map {bank}:{start:04X}..{bank}:{end:04X}")
    return rom[start_offset:end_offset]


def byte_profile(data: bytes) -> dict[str, Any]:
    size = len(data)
    counts = Counter(data)
    nonzero = sum(1 for value in data if value != 0)
    unique = len(counts)
    common = counts.most_common(4)
    return {
        "size": size,
        "zero_count": counts.get(0, 0),
        "ff_count": counts.get(0xFF, 0),
        "nonzero_count": nonzero,
        "unique_byte_count": unique,
        "first_bytes": " ".join(f"{byte:02X}" for byte in data[:16]),
        "last_bytes": " ".join(f"{byte:02X}" for byte in data[-16:]),
        "most_common_bytes": [
            {"byte": f"{byte:02X}", "count": count, "percent": round(count / size * 100, 2)}
            for byte, count in common
        ]
        if size
        else [],
    }


def classify_residual(entries: list[dict[str, Any]], profile: dict[str, Any]) -> tuple[str, str]:
    if profile["size"] == 0:
        return "empty", "empty interval"
    if profile["zero_count"] == profile["size"]:
        return "blank-data", "all zero bytes"
    if profile["ff_count"] == profile["size"]:
        return "blank-data", "all FF bytes"
    if not entries:
        if profile["unique_byte_count"] <= 4 and profile["size"] >= 16:
            return "table-or-padding", "few unique byte values and no ebsrc span"
        return "unmapped-frontier", "no overlapping ebsrc span"

    kinds = {entry.get("kind") for entry in entries}
    includes = " ".join(str(entry.get("include_path", "")).lower() for entry in entries)
    if all(kind in {"event-script-data", "event-data", "text-data", "map-data", "battle-data", "named-data", "unknown-data"} for kind in kinds):
        if "events/scripts" in includes:
            return "script-data", "overlapping ebsrc event script data"
        if "/text/" in includes:
            return "text-data", "overlapping ebsrc text data"
        if "/battle/" in includes:
            return "battle-data", "overlapping ebsrc battle data"
        return "data", "overlapping ebsrc data includes"
    if any(kind in {"unknown-code", "named-code"} for kind in kinds) and any(str(kind).endswith("data") for kind in kinds):
        return "mixed-code-data", "overlapping ebsrc code and data includes"
    if any(kind in {"unknown-code", "named-code"} for kind in kinds):
        return "source-frontier", "overlapping ebsrc code includes"
    return "unclassified", "overlapping includes need review"


def build_map(bank: str, rom: bytes) -> dict[str, Any]:
    source_ranges = load_ranges(bank)
    merged = merge_intervals(source_ranges)
    residual_intervals = invert_intervals(merged)
    ebsrc_entries = load_ebsrc_entries(bank)
    residuals: list[dict[str, Any]] = []
    by_class: Counter[str] = Counter()
    by_class_bytes: Counter[str] = Counter()

    for start, end in residual_intervals:
        data = rom_slice(rom, bank, start, end)
        profile = byte_profile(data)
        overlaps = [entry for entry in ebsrc_entries if entry_overlaps(entry, start, end)]
        classification, reason = classify_residual(overlaps, profile)
        by_class[classification] += 1
        by_class_bytes[classification] += end - start
        residuals.append(
            {
                "start": format_address(bank, start),
                "end": format_address(bank, end),
                "size": end - start,
                "classification": classification,
                "reason": reason,
                "byte_profile": profile,
                "ebsrc_overlaps": [
                    {
                        "ordinal": entry.get("ordinal"),
                        "include_path": entry.get("include_path"),
                        "kind": entry.get("kind"),
                        "status": entry.get("status"),
                        "start": entry.get("start"),
                        "end": entry.get("end"),
                        "size": entry.get("size"),
                        "ebsrc_symbol": entry.get("ebsrc_symbol"),
                        "local_name": entry.get("local_name"),
                        "promoted": entry.get("promoted"),
                    }
                    for entry in overlaps
                ],
            }
        )

    protected_bytes = sum(end - start for start, end in merged)
    total_bytes = 0x10000
    return {
        "schema": SCHEMA,
        "generated_by": "tools/build_source_bank_residual_map.py",
        "bank": bank,
        "inputs": {
            "source_ranges": f"build/{bank.lower()}-build-candidate-ranges.json",
            "ebsrc_map": f"build/ebsrc-bank-{bank.lower()}-map.json",
            "rom": "EarthBound (USA).sfc",
        },
        "summary": {
            "bank_bytes": total_bytes,
            "protected_bytes": protected_bytes,
            "residual_bytes": total_bytes - protected_bytes,
            "protected_percent": round(protected_bytes / total_bytes * 100, 2),
            "residual_ranges": len(residuals),
            "by_class": dict(sorted(by_class.items())),
            "bytes_by_class": dict(sorted(by_class_bytes.items())),
        },
        "residuals": residuals,
    }


def render_markdown(data: dict[str, Any]) -> str:
    bank = data["bank"]
    summary = data["summary"]
    lines: list[str] = [
        f"# Bank {bank} Source Scaffold Residual Map",
        "",
        "This file lists byte ranges not yet protected by the source-bank scaffold.",
        "Classifications are planning hints, not final semantic proof.",
        "",
        "## Summary",
        "",
        f"- bank bytes: `{summary['bank_bytes']}`",
        f"- protected bytes: `{summary['protected_bytes']}` (`{summary['protected_percent']}%`)",
        f"- residual bytes: `{summary['residual_bytes']}`",
        f"- residual ranges: `{summary['residual_ranges']}`",
        "",
        "## Classification Totals",
        "",
        "| Class | Ranges | Bytes |",
        "| --- | ---: | ---: |",
    ]
    by_class = summary["by_class"]
    bytes_by_class = summary["bytes_by_class"]
    for name in sorted(by_class):
        lines.append(f"| `{name}` | {by_class[name]} | {bytes_by_class.get(name, 0)} |")

    if not data["residuals"]:
        lines.extend(
            [
                "",
                "## Closure Status",
                "",
                "No residual byte ranges remain. The bank is fully protected by the current source-bank scaffold manifest.",
                "",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            "",
            "## Largest Residual Ranges",
            "",
            "| Range | Size | Class | Reason | Top ebsrc overlaps | First bytes |",
            "| --- | ---: | --- | --- | --- | --- |",
        ]
    )
    for item in sorted(data["residuals"], key=lambda entry: entry["size"], reverse=True)[:20]:
        overlaps = item["ebsrc_overlaps"][:3]
        overlap_text = "<br>".join(
            f"`{entry['include_path']}`" for entry in overlaps
        ) or ""
        lines.append(
            "| `{start}..{end}` | {size} | `{classification}` | {reason} | {overlaps} | `{first}` |".format(
                start=item["start"],
                end=item["end"],
                size=item["size"],
                classification=item["classification"],
                reason=item["reason"],
                overlaps=overlap_text,
                first=item["byte_profile"]["first_bytes"],
            )
        )

    lines.extend(
        [
            "",
            "## All Residual Ranges",
            "",
            "| Range | Size | Class | Reason | Overlap Count | First bytes |",
            "| --- | ---: | --- | --- | ---: | --- |",
        ]
    )
    for item in data["residuals"]:
        lines.append(
            "| `{start}..{end}` | {size} | `{classification}` | {reason} | {count} | `{first}` |".format(
                start=item["start"],
                end=item["end"],
                size=item["size"],
                classification=item["classification"],
                reason=item["reason"],
                count=len(item["ebsrc_overlaps"]),
                first=item["byte_profile"]["first_bytes"],
            )
        )

    lines.extend(
        [
            "",
            "## Recommended Closure Order",
            "",
            "1. Promote small `source-frontier` ranges with direct code evidence.",
            "2. Split `mixed-code-data` ranges into explicit source segments and data gaps.",
            "3. Move `script-data`, `text-data`, `battle-data`, and `data` ranges into structured asset manifests.",
            "4. Leave `blank-data` and padding-like ranges as explicit data contracts only when a caller or table boundary needs them.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", required=True)
    parser.add_argument("--rom")
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    args = parser.parse_args()

    bank = args.bank.upper()
    rom = load_rom(find_rom(args.rom))
    data = build_map(bank, rom)

    output_json = args.output_json or ROOT / "build" / f"{bank.lower()}-source-residual-map.json"
    output_md = args.output_md or ROOT / "notes" / f"{bank.lower()}-source-residual-map.md"
    output_json = output_json if output_json.is_absolute() else ROOT / output_json
    output_md = output_md if output_md.is_absolute() else ROOT / output_md
    output_json.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    output_md.write_text(render_markdown(data), encoding="utf-8", newline="\n")
    print(f"Wrote {output_json.relative_to(ROOT)} and {output_md.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
