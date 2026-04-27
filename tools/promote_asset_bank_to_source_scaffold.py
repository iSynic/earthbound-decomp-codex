#!/usr/bin/env python3
"""Promote an asset-bank manifest into source-bank scaffold data corridors."""

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


def default_manifest(asset_manifest_path: Path) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "generated_by": "tools/promote_asset_bank_to_source_scaffold.py",
        "inputs": {
            "rom": "EarthBound (USA).sfc",
            "asset_manifest": asset_manifest_path.as_posix(),
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
    bank = str(data["bank"]).lower()
    evidence = [
        str(data.get("config", "")),
        str(data.get("yml", "")),
        f"build/asset-bank-{bank}.json",
        f"notes/bank-{bank}-asset-data-map.md",
    ]
    evidence.extend(extra)
    return [item for item in evidence if item]


def table_name(include: str) -> str:
    stem = Path(include).stem
    return pascal_case(stem)


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


def gap_suffix(gap: dict[str, Any]) -> str:
    end = exclusive_end(str(gap["cpu_end"]))
    _, end_address = parse_cpu(end)
    if end_address == 0x10000:
        return "TailPadding"
    return "PaddingSlack"


def range_specs(data: dict[str, Any], *, include_gaps: bool) -> list[dict[str, str]]:
    bank = str(data["bank"]).upper()
    specs: list[dict[str, str]] = []

    for asset in data.get("binary_assets", []):
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

    for table in data.get("table_includes", []):
        if "cpu_start" not in table or "cpu_end" not in table:
            continue
        if int(table.get("size", 0)) <= 0:
            continue
        include = str(table["include"])
        name = table_name(include)
        order = int(table.get("order", len(specs)))
        specs.append(
            {
                "source_path": f"src/{bank.lower()}/table_{order:03d}_{slug(include)}.asm",
                "subsystem": f"asset table {include}",
                "start": table["cpu_start"],
                "end": exclusive_end(table["cpu_end"]),
                "name": f"Table{name}",
                "title": f"asset table {include}",
            }
        )

    if include_gaps:
        for index, gap in enumerate(data.get("coverage_gaps", []), start=1):
            suffix = gap_suffix(gap)
            name = f"AssetBank{bank}Gap{index}{suffix}"
            specs.append(
                {
                    "source_path": f"src/{bank.lower()}/asset_bank_{bank.lower()}_gap_{index}_{slug(suffix)}.asm",
                    "subsystem": "asset bank padding/alignment",
                    "start": gap["cpu_start"],
                    "end": exclusive_end(gap["cpu_end"]),
                    "name": name,
                    "title": f"asset bank {bank} {suffix.lower()}",
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


def drop_managed_ranges(manifest: dict[str, Any], bank: str) -> None:
    prefix = f"src/{bank.lower()}/"
    managed_prefixes = ("asset_", "table_", "asset_bank_")
    manifest["ranges"] = [
        item
        for item in manifest.get("ranges", [])
        if not (
            str(item.get("source_path", "")).startswith(prefix)
            and Path(str(item.get("source_path", ""))).name.startswith(managed_prefixes)
        )
    ]
    recalculate_summary(manifest)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bank", help="bank name, e.g. CA")
    parser.add_argument(
        "--asset-manifest",
        type=Path,
        help="asset-bank manifest JSON; defaults to build/asset-bank-<bank>.json",
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
        help="only promote explicit assets/tables; leave coverage gaps residual",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    bank = args.bank.upper()
    asset_manifest_path = args.asset_manifest or ROOT / "build" / f"asset-bank-{bank.lower()}.json"
    source_manifest_path = args.source_manifest or ROOT / "build" / f"{bank.lower()}-build-candidate-ranges.json"
    asset_manifest_path = asset_manifest_path if asset_manifest_path.is_absolute() else ROOT / asset_manifest_path
    source_manifest_path = source_manifest_path if source_manifest_path.is_absolute() else ROOT / source_manifest_path

    data = json.loads(asset_manifest_path.read_text(encoding="utf-8"))
    if str(data["bank"]).upper() != bank:
        raise SystemExit(f"{asset_manifest_path} is for bank {data['bank']}, not {bank}")

    manifest = (
        json.loads(source_manifest_path.read_text(encoding="utf-8"))
        if source_manifest_path.exists()
        else default_manifest(asset_manifest_path.relative_to(ROOT))
    )
    evidence = evidence_for(data, args.evidence)
    rom = load_rom(find_rom(args.rom))
    specs = range_specs(data, include_gaps=not args.no_gaps)
    drop_managed_ranges(manifest, bank)
    for spec in specs:
        register_range(manifest=manifest, rom=rom, bank=bank, spec=spec, evidence=evidence)

    source_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    source_manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"promoted {len(specs)} {bank} asset-bank range(s) into "
        f"{source_manifest_path.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
