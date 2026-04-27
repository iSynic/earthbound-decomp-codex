from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from rom_tools import find_rom, hirom_to_file_offset, load_rom


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "asset-manifests" / "bank-da-assets.json"
DEFAULT_TILESET_BUNDLES = ROOT / "notes" / "map-tileset-bundles.json"
DEFAULT_JSON_OUT = ROOT / "notes" / "map-palette-pointer-table-contract.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "map-palette-pointer-table-contract.md"
SCHEMA = "earthbound-decomp.map-palette-pointer-table-contract.v1"
TABLE_BANK = 0xDA
TABLE_ADDRESS = 0xFAA7
TABLE_ENTRY_COUNT = 32
TABLE_ENTRY_SIZE = 3
MAP_PALETTE_VARIANT_BYTES = 192


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify and document the DA map palette long-pointer table."
    )
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--tileset-bundles", default=str(DEFAULT_TILESET_BUNDLES))
    parser.add_argument("--rom", help="EarthBound US ROM path.")
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def parse_cpu_range(text: str) -> tuple[int, int, int]:
    start, end = text.split("..", 1)
    bank_text, start_text = start.split(":", 1)
    end_text = end.split(":", 1)[-1]
    return int(bank_text, 16), int(start_text, 16), int(end_text, 16)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def palette_assets_by_id(manifest: dict[str, Any]) -> dict[int, dict[str, Any]]:
    assets: dict[int, dict[str, Any]] = {}
    for asset in manifest["assets"]:
        title = str(asset["title"])
        if not title.startswith("MAP_DATA_PALETTE_"):
            continue
        palette_id = int(title.rsplit("_", 1)[1])
        bank, start, end = parse_cpu_range(str(asset["source"]["range"]))
        byte_count = int(asset["source"]["bytes"])
        assets[palette_id] = {
            "asset_id": asset["id"],
            "title": title,
            "payload_path": next(
                output["path"]
                for output in asset["outputs"]
                if output["kind"] == "raw"
            ),
            "bank": bank,
            "start": start,
            "end": end,
            "range": asset["source"]["range"],
            "bytes": byte_count,
            "sha1": asset["source"]["sha1"],
            "variant_count": byte_count // MAP_PALETTE_VARIANT_BYTES,
            "variant_remainder_bytes": byte_count % MAP_PALETTE_VARIANT_BYTES,
        }
    return assets


def read_pointer_table(rom_data: bytes) -> list[int]:
    offset = hirom_to_file_offset(TABLE_BANK, TABLE_ADDRESS, len(rom_data))
    if offset is None:
        raise ValueError(f"{TABLE_BANK:02X}:{TABLE_ADDRESS:04X} does not map to ROM data")
    raw = rom_data[offset : offset + TABLE_ENTRY_COUNT * TABLE_ENTRY_SIZE]
    if len(raw) != TABLE_ENTRY_COUNT * TABLE_ENTRY_SIZE:
        raise ValueError("ROM ended before the map palette pointer table")
    return [
        raw[index] | (raw[index + 1] << 8) | (raw[index + 2] << 16)
        for index in range(0, len(raw), TABLE_ENTRY_SIZE)
    ]


def build_contract(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = Path(args.manifest)
    tileset_bundles_path = Path(args.tileset_bundles)
    manifest = load_json(manifest_path)
    tileset_bundles = load_json(tileset_bundles_path)
    rom_data = load_rom(find_rom(args.rom))
    assets = palette_assets_by_id(manifest)
    pointers = read_pointer_table(rom_data)
    tilesets_by_id = {int(row["tileset_id"]): row for row in tileset_bundles["tilesets"]}

    entries: list[dict[str, Any]] = []
    exact_match_count = 0
    for index, pointer in enumerate(pointers):
        asset = assets.get(index)
        expected_pointer = None if asset is None else (int(asset["bank"]) << 16) | int(asset["start"])
        status = "matches_map_data_palette_asset" if pointer == expected_pointer else "mismatch"
        if status == "matches_map_data_palette_asset":
            exact_match_count += 1
        tileset = tilesets_by_id.get(index, {})
        entries.append(
            {
                "index": index,
                "pointer": f"{pointer:06X}",
                "pointer_cpu": f"{pointer >> 16:02X}:{pointer & 0xFFFF:04X}",
                "expected_asset": asset,
                "match_status": status,
                "tileset_dependency": {
                    "tileset_id": index,
                    "sector_count": int(tileset.get("sector_count", 0)),
                    "palette_setting_count": int(tileset.get("palette_setting_count", 0)),
                    "sector_palette_counts": tileset.get("sector_palette_counts", []),
                    "has_direct_fts_export": bool(tileset.get("has_direct_fts_export", False)),
                    "dependency_status": tileset.get("dependency_status"),
                },
            }
        )

    variant_mismatches = [
        entry
        for entry in entries
        if entry["expected_asset"] is not None
        and int(entry["expected_asset"]["variant_remainder_bytes"]) != 0
    ]
    palette_count_mismatches = [
        entry
        for entry in entries
        if entry["expected_asset"] is not None
        and entry["tileset_dependency"]["palette_setting_count"] != int(entry["expected_asset"]["variant_count"])
    ]

    return {
        "schema": SCHEMA,
        "title": "Map Palette Pointer Table Contract",
        "generator": "tools/build_map_palette_pointer_table_contract.py",
        "source_policy": (
            "ROM-verified pointer-table contract. This records pointer targets, "
            "asset IDs, hashes, byte counts, and usage counts only; it does not "
            "commit palette payload bytes."
        ),
        "sources": {
            "manifest": rel(manifest_path),
            "tileset_bundles": rel(tileset_bundles_path),
            "pointer_table": f"{TABLE_BANK:02X}:{TABLE_ADDRESS:04X}..{TABLE_BANK:02X}:{TABLE_ADDRESS + TABLE_ENTRY_COUNT * TABLE_ENTRY_SIZE:04X}",
        },
        "summary": {
            "entry_count": len(entries),
            "entry_size_bytes": TABLE_ENTRY_SIZE,
            "table_bytes": TABLE_ENTRY_COUNT * TABLE_ENTRY_SIZE,
            "exact_pointer_asset_matches": exact_match_count,
            "variant_size_bytes": MAP_PALETTE_VARIANT_BYTES,
            "variant_count_mismatches": len(palette_count_mismatches),
            "variant_remainder_mismatches": len(variant_mismatches),
            "used_palette_asset_count": sum(1 for row in entries if row["tileset_dependency"]["sector_count"] > 0),
            "direct_fts_palette_asset_count": sum(1 for row in entries if row["tileset_dependency"]["has_direct_fts_export"]),
        },
        "entries": entries,
    }


def write_markdown(contract: dict[str, Any], path: Path) -> None:
    summary = contract["summary"]
    lines = [
        "# Map Palette Pointer Table Contract",
        "",
        "This contract verifies the previously inferred DA map palette pointer table.",
        "The 96-byte table at `DA:FAA7..DA:FB07` is a 32-entry long-pointer table,",
        "and each entry points exactly at the corresponding `MAP_DATA_PALETTE_N`",
        "asset in bank DA.",
        "",
        "## Summary",
        "",
        f"- entries: `{summary['entry_count']}`",
        f"- entry size: `{summary['entry_size_bytes']}` bytes",
        f"- table bytes: `{summary['table_bytes']}`",
        f"- exact pointer/asset matches: `{summary['exact_pointer_asset_matches']}`",
        f"- palette variant size: `{summary['variant_size_bytes']}` bytes",
        f"- palette-setting/variant-count mismatches: `{summary['variant_count_mismatches']}`",
        f"- variant-size remainder mismatches: `{summary['variant_remainder_mismatches']}`",
        f"- palette assets used by sectors: `{summary['used_palette_asset_count']}`",
        f"- palette assets with direct `.fts` exports: `{summary['direct_fts_palette_asset_count']}`",
        "",
        "## Entries",
        "",
        "| Index | Pointer | Asset | Bytes | Variants | Sectors | Palette Settings | Status |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for entry in contract["entries"]:
        asset = entry["expected_asset"]
        dependency = entry["tileset_dependency"]
        lines.append(
            f"| {entry['index']} | `{entry['pointer_cpu']}` | `{asset['title']}` | "
            f"{asset['bytes']} | {asset['variant_count']} | "
            f"{dependency['sector_count']} | {dependency['palette_setting_count']} | "
            f"`{entry['match_status']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "This closes the table identity: the table maps palette/tileset IDs to bank DA",
            "map palette payload starts. It does not by itself resolve how the three-bit",
            "arrangement descriptor palette field maps onto the six 16-color subpalettes",
            "inside one selected 192-byte palette variant.",
            "",
            "## Machine-Readable Data",
            "",
            "`notes/map-palette-pointer-table-contract.json` records one row per entry",
            "with pointer target, matched asset metadata, palette variant counts, and",
            "sector/tileset dependency counts.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    contract = build_contract(args)
    json_out = Path(args.json_out)
    markdown_out = Path(args.markdown_out)
    json_out.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(contract, markdown_out)
    print(f"Wrote {rel(json_out)} and {rel(markdown_out)}")


if __name__ == "__main__":
    main()
