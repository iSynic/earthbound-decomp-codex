#!/usr/bin/env python3
"""Promote a text-bank manifest into source-bank scaffold data corridors."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from add_source_bank_range import ROOT, build_entry, recalculate_summary
from promote_source_bank_data_range import default_terminal_label, parse_bank_address, write_data_stub
from rom_tools import find_rom, load_rom


SCHEMA = "earthbound-decomp.source-bank-build-candidate-ranges.v1"


def parse_cpu(raw: str) -> tuple[str, int]:
    bank, address = parse_bank_address(raw)
    return bank, address


def format_cpu(bank: str, address: int) -> str:
    return f"{bank}:{address:04X}"


def exclusive_end(inclusive_end: str) -> str:
    bank, address = parse_cpu(inclusive_end)
    return format_cpu(bank, address + 1)


def pascal_case(raw: str) -> str:
    parts = re.split(r"[^A-Za-z0-9]+", raw)
    return "".join(part[:1].upper() + part[1:].lower() for part in parts if part)


def slug(raw: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "_", raw).strip("_").lower()
    return value or "range"


def default_manifest(bank: str, text_manifest_path: Path) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "generated_by": "tools/promote_text_bank_to_source_scaffold.py",
        "inputs": {
            "rom": "EarthBound (USA).sfc",
            "text_manifest": text_manifest_path.as_posix(),
        },
        "summary": {
            "ranges": 0,
            "total_bytes": 0,
            "source_bytes": 0,
            "data_gap_bytes": 0,
        },
        "ranges": [],
    }


def evidence_for(data: dict[str, Any], extra: list[str]) -> list[str]:
    evidence = [
        str(data.get("config", "")),
        str(data.get("yml", "")),
        f"build/text-bank-{str(data['bank']).lower()}.json",
        f"notes/bank-{str(data['bank']).lower()}-text-data-map.md",
    ]
    evidence.extend(extra)
    return [item for item in evidence if item]


def range_specs(data: dict[str, Any], *, include_gaps: bool) -> list[dict[str, str]]:
    bank = str(data["bank"]).upper()
    specs: list[dict[str, str]] = []
    for segment in data.get("segments", []):
        name = str(segment["name"])
        specs.append(
            {
                "source_path": f"src/{bank.lower()}/text_{slug(name)}.asm",
                "subsystem": f"text segment {name}",
                "start": segment["cpu_start"],
                "end": exclusive_end(segment["cpu_end"]),
                "name": f"TextSegment{pascal_case(name)}",
                "title": f"text segment {name}",
            }
        )
    if include_gaps:
        for index, gap in enumerate(data.get("coverage_gaps", []), start=1):
            start = str(gap["cpu_start"])
            end = exclusive_end(str(gap["cpu_end"]))
            _, start_address = parse_cpu(start)
            _, end_address = parse_cpu(end)
            size = int(gap.get("size", 0))
            if end_address == 0x10000:
                suffix = "TailPadding"
                subsystem = "text bank padding/alignment"
            elif end_address == 0x8000:
                suffix = "AlignmentGap"
                subsystem = "text bank padding/alignment"
            elif size >= 0x400:
                suffix = "NonLocaleDataIsland"
                subsystem = "text bank non-locale data island"
            else:
                suffix = "PaddingSlack"
                subsystem = "text bank padding/alignment"
            name = f"TextBank{bank}Gap{index}{suffix}"
            specs.append(
                {
                    "source_path": f"src/{bank.lower()}/text_bank_{bank.lower()}_gap_{index}_{slug(suffix)}.asm",
                    "subsystem": subsystem,
                    "start": start,
                    "end": end,
                    "name": name,
                    "title": f"text bank {bank} {suffix.lower()}",
                }
            )
    specs.sort(key=lambda item: parse_cpu(item["start"])[1])
    return specs


def register_range(
    *,
    manifest: dict[str, Any],
    rom: bytes,
    bank: str,
    spec: dict[str, str],
    evidence: list[str],
) -> None:
    terminal_label = default_terminal_label(spec["end"], spec["name"])
    source_path = ROOT / spec["source_path"]
    write_data_stub(
        source_path,
        bank=bank,
        start=spec["start"],
        end=spec["end"],
        name=spec["name"],
        title=spec["title"],
        terminal_label=terminal_label,
        force=True,
    )
    entry_args = argparse.Namespace(
        bank=bank,
        source_path=Path(spec["source_path"]),
        subsystem=spec["subsystem"],
        start=spec["start"],
        end=spec["end"],
        name=spec["name"],
        source_segment=[],
        data_gap=[f"{spec['start']},{spec['end']},{spec['name']}"],
        evidence=evidence,
        rom=None,
        manifest=None,
    )
    entry = build_entry(entry_args, rom)
    ranges = [
        item
        for item in manifest.get("ranges", [])
        if item.get("source_path") != entry["source_path"]
    ]
    ranges.append(entry)
    ranges.sort(key=lambda item: parse_cpu(item["start"])[1])
    manifest["ranges"] = ranges
    recalculate_summary(manifest)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bank", help="bank name, e.g. C5")
    parser.add_argument(
        "--text-manifest",
        type=Path,
        help="text-bank manifest JSON; defaults to build/text-bank-<bank>.json",
    )
    parser.add_argument(
        "--source-manifest",
        type=Path,
        help="source-bank range manifest; defaults to build/<bank>-build-candidate-ranges.json",
    )
    parser.add_argument("--rom", help="explicit ROM path")
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument(
        "--no-gaps",
        action="store_true",
        help="only promote text segments; leave coverage gaps residual",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    bank = args.bank.upper()
    text_manifest_path = args.text_manifest or ROOT / "build" / f"text-bank-{bank.lower()}.json"
    source_manifest_path = args.source_manifest or ROOT / "build" / f"{bank.lower()}-build-candidate-ranges.json"
    text_manifest_path = text_manifest_path if text_manifest_path.is_absolute() else ROOT / text_manifest_path
    source_manifest_path = source_manifest_path if source_manifest_path.is_absolute() else ROOT / source_manifest_path

    data = json.loads(text_manifest_path.read_text(encoding="utf-8"))
    if str(data["bank"]).upper() != bank:
        raise SystemExit(f"{text_manifest_path} is for bank {data['bank']}, not {bank}")

    manifest = (
        json.loads(source_manifest_path.read_text(encoding="utf-8"))
        if source_manifest_path.exists()
        else default_manifest(bank, text_manifest_path.relative_to(ROOT))
    )
    evidence = evidence_for(data, args.evidence)
    rom = load_rom(find_rom(args.rom))
    specs = range_specs(data, include_gaps=not args.no_gaps)
    for spec in specs:
        register_range(manifest=manifest, rom=rom, bank=bank, spec=spec, evidence=evidence)

    source_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    source_manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"promoted {len(specs)} {bank} text-bank range(s) into "
        f"{source_manifest_path.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
