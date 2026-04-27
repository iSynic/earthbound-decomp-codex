#!/usr/bin/env python3
"""Promote exact table-split manifests into source-bank scaffold corridors."""

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


def slug(raw: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "_", raw).strip("_").lower()
    return value or "range"


def pascal_case(raw: str) -> str:
    parts = re.split(r"[^A-Za-z0-9]+", raw)
    return "".join(part[:1].upper() + part[1:].lower() for part in parts if part)


def default_manifest(split_manifest_path: Path) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "generated_by": "tools/promote_table_splits_to_source_scaffold.py",
        "inputs": {
            "rom": "EarthBound (USA).sfc",
            "table_splits": split_manifest_path.as_posix(),
        },
        "summary": {
            "ranges": 0,
            "total_bytes": 0,
            "source_bytes": 0,
            "data_gap_bytes": 0,
        },
        "ranges": [],
    }


def evidence_for(data: dict[str, Any], split_manifest_path: Path, extra: list[str]) -> list[str]:
    bank = str(data["bank"]).lower()
    evidence = [
        split_manifest_path.as_posix(),
        f"notes/{bank}-table-splits.md",
    ]
    evidence.extend(extra)
    return [item for item in evidence if item]


def source_prefix(split: dict[str, Any]) -> str:
    include = str(split.get("include") or "")
    label = str(split["label"])
    if include.startswith("INSERT_AUDIO_PACK"):
        return "asset"
    if "tail" in include.lower() or "slack" in label.lower():
        return "padding"
    return "table"


def range_specs(data: dict[str, Any]) -> list[dict[str, str]]:
    bank = str(data["bank"]).upper()
    specs: list[dict[str, str]] = []
    for split in data.get("splits", []):
        label = str(split["label"])
        prefix = source_prefix(split)
        include = str(split.get("include") or "")
        if prefix == "asset":
            subsystem = f"audio asset {label}"
            title = f"audio asset {label}"
        elif prefix == "padding":
            subsystem = "table-split bank padding/alignment"
            title = f"table split padding {label}"
        else:
            subsystem = f"table split {include}"
            title = f"table split {label}"
        specs.append(
            {
                "source_path": f"src/{bank.lower()}/{prefix}_{slug(label)}.asm",
                "subsystem": subsystem,
                "start": split["cpu_start"],
                "end": exclusive_end(split["cpu_end"]),
                "name": pascal_case(label),
                "title": title,
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
    parser.add_argument("bank", help="bank name, e.g. CF")
    parser.add_argument(
        "--split-manifest",
        type=Path,
        help="table split JSON; defaults to build/<bank>-table-splits.json",
    )
    parser.add_argument(
        "--source-manifest",
        type=Path,
        help="source-bank range manifest; defaults to build/<bank>-build-candidate-ranges.json",
    )
    parser.add_argument("--rom", help="explicit ROM path")
    parser.add_argument("--evidence", action="append", default=[])
    return parser


def main() -> int:
    args = build_parser().parse_args()
    bank = args.bank.upper()
    split_manifest_path = args.split_manifest or ROOT / "build" / f"{bank.lower()}-table-splits.json"
    source_manifest_path = args.source_manifest or ROOT / "build" / f"{bank.lower()}-build-candidate-ranges.json"
    split_manifest_path = split_manifest_path if split_manifest_path.is_absolute() else ROOT / split_manifest_path
    source_manifest_path = source_manifest_path if source_manifest_path.is_absolute() else ROOT / source_manifest_path

    data = json.loads(split_manifest_path.read_text(encoding="utf-8"))
    if str(data["bank"]).upper() != bank:
        raise SystemExit(f"{split_manifest_path} is for bank {data['bank']}, not {bank}")

    manifest = (
        json.loads(source_manifest_path.read_text(encoding="utf-8"))
        if source_manifest_path.exists()
        else default_manifest(split_manifest_path.relative_to(ROOT))
    )
    evidence = evidence_for(data, split_manifest_path.relative_to(ROOT), args.evidence)
    rom = load_rom(find_rom(args.rom))
    specs = range_specs(data)
    for spec in specs:
        register_range(manifest=manifest, rom=rom, bank=bank, spec=spec, evidence=evidence)

    source_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    source_manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"promoted {len(specs)} {bank} table-split range(s) into "
        f"{source_manifest_path.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
