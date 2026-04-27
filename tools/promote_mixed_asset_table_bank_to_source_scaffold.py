#!/usr/bin/env python3
"""Promote mixed asset-front/table-tail banks into source-bank scaffold corridors."""

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
    return f"{bank}:{address:04X}" if address <= 0xFFFF else f"{bank}:{address:X}"


def exclusive_end(inclusive_end: str) -> str:
    bank, address = parse_cpu(inclusive_end)
    return format_cpu(bank, address + 1)


def slug(raw: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "_", raw).strip("_").lower()
    return value or "range"


def pascal_case(raw: str) -> str:
    parts = re.split(r"[^A-Za-z0-9]+", raw)
    return "".join(part[:1].upper() + part[1:].lower() for part in parts if part)


def default_manifest(bank: str, asset_manifest_path: Path, split_manifest_path: Path) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "generated_by": "tools/promote_mixed_asset_table_bank_to_source_scaffold.py",
        "inputs": {
            "rom": "EarthBound (USA).sfc",
            "asset_manifest": asset_manifest_path.as_posix(),
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


def asset_name(asset: dict[str, Any]) -> str:
    label = asset.get("label")
    if label:
        return str(label)
    payload = str(asset.get("payload_path") or "")
    if payload:
        return payload
    extension = str(asset.get("extension") or "asset")
    name = str(asset.get("name") or asset.get("order") or "unknown")
    return f"{extension}_{name}"


def source_prefix_for_split(split: dict[str, Any]) -> str:
    include = str(split.get("include") or "")
    label = str(split["label"])
    if "tail" in include.lower() or "pad" in include.lower() or "tail" in label.lower():
        return "padding"
    if label.startswith("UNKNOWN_"):
        return "data"
    return "table"


def specs_from_assets(bank: str, asset_manifest: dict[str, Any]) -> list[dict[str, str]]:
    specs: list[dict[str, str]] = []
    for asset in asset_manifest.get("binary_assets", []):
        label = asset_name(asset)
        extension = str(asset.get("extension") or "asset")
        specs.append(
            {
                "source_path": f"src/{bank.lower()}/asset_{slug(label)}.asm",
                "subsystem": f"asset {extension} {label}",
                "start": asset["cpu_start"],
                "end": exclusive_end(asset["cpu_end"]),
                "name": f"Asset{pascal_case(label)}",
                "title": f"asset {label}",
            }
        )
    return specs


def specs_from_splits(bank: str, split_manifest: dict[str, Any]) -> list[dict[str, str]]:
    specs: list[dict[str, str]] = []
    for split in split_manifest.get("splits", []):
        label = str(split["label"])
        prefix = source_prefix_for_split(split)
        include = str(split.get("include") or "")
        if prefix == "padding":
            subsystem = "mixed asset/table bank padding"
            title = f"mixed bank padding {label}"
        elif prefix == "data":
            subsystem = f"bounded table/data island {label}"
            title = f"bounded data island {label}"
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
    return specs


def evidence_for(
    *,
    bank: str,
    asset_manifest: dict[str, Any],
    asset_manifest_path: Path,
    split_manifest_path: Path,
    extra: list[str],
) -> list[str]:
    evidence = [
        str(asset_manifest.get("config", "")),
        str(asset_manifest.get("yml", "")),
        asset_manifest_path.as_posix(),
        f"notes/bank-{bank.lower()}-asset-data-map.md",
        split_manifest_path.as_posix(),
        f"notes/{bank.lower()}-table-splits.md",
    ]
    evidence.extend(extra)
    return [item for item in evidence if item]


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


def assert_contiguous(bank: str, specs: list[dict[str, str]]) -> None:
    cursor = 0
    for spec in sorted(specs, key=lambda item: parse_cpu(item["start"])[1]):
        start_bank, start = parse_cpu(spec["start"])
        end_bank, end = parse_cpu(spec["end"])
        if start_bank != bank or end_bank != bank:
            raise SystemExit(f"range must stay in bank {bank}: {spec['start']}..{spec['end']}")
        if start != cursor:
            raise SystemExit(f"non-contiguous mixed-bank specs: expected {bank}:{cursor:04X}, got {spec['start']}")
        cursor = end
    if cursor != 0x10000:
        raise SystemExit(f"mixed-bank specs end at {bank}:{cursor:04X}; expected {bank}:10000")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bank", help="bank name, e.g. D5")
    parser.add_argument("--asset-manifest", type=Path, help="defaults to build/asset-bank-<bank>.json")
    parser.add_argument("--split-manifest", type=Path, help="defaults to build/<bank>-table-splits.json")
    parser.add_argument("--source-manifest", type=Path, help="defaults to build/<bank>-build-candidate-ranges.json")
    parser.add_argument("--rom", help="explicit ROM path")
    parser.add_argument("--evidence", action="append", default=[])
    return parser


def main() -> int:
    args = build_parser().parse_args()
    bank = args.bank.upper()
    asset_manifest_path = args.asset_manifest or ROOT / "build" / f"asset-bank-{bank.lower()}.json"
    split_manifest_path = args.split_manifest or ROOT / "build" / f"{bank.lower()}-table-splits.json"
    source_manifest_path = args.source_manifest or ROOT / "build" / f"{bank.lower()}-build-candidate-ranges.json"
    asset_manifest_path = asset_manifest_path if asset_manifest_path.is_absolute() else ROOT / asset_manifest_path
    split_manifest_path = split_manifest_path if split_manifest_path.is_absolute() else ROOT / split_manifest_path
    source_manifest_path = source_manifest_path if source_manifest_path.is_absolute() else ROOT / source_manifest_path

    asset_manifest = json.loads(asset_manifest_path.read_text(encoding="utf-8"))
    split_manifest = json.loads(split_manifest_path.read_text(encoding="utf-8"))
    if str(asset_manifest["bank"]).upper() != bank:
        raise SystemExit(f"{asset_manifest_path} is for bank {asset_manifest['bank']}, not {bank}")
    if str(split_manifest["bank"]).upper() != bank:
        raise SystemExit(f"{split_manifest_path} is for bank {split_manifest['bank']}, not {bank}")

    specs = specs_from_assets(bank, asset_manifest) + specs_from_splits(bank, split_manifest)
    specs.sort(key=lambda item: parse_cpu(item["start"])[1])
    assert_contiguous(bank, specs)

    manifest = default_manifest(
        bank,
        asset_manifest_path.relative_to(ROOT),
        split_manifest_path.relative_to(ROOT),
    )
    evidence = evidence_for(
        bank=bank,
        asset_manifest=asset_manifest,
        asset_manifest_path=asset_manifest_path.relative_to(ROOT),
        split_manifest_path=split_manifest_path.relative_to(ROOT),
        extra=args.evidence,
    )
    rom = load_rom(find_rom(args.rom))
    for spec in specs:
        register_range(manifest=manifest, rom=rom, bank=bank, spec=spec, evidence=evidence)

    source_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    source_manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"promoted {len(specs)} {bank} mixed asset/table range(s) into "
        f"{source_manifest_path.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
