from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
REFS = ROOT / "refs" / "eb-decompile-4ef92"
DEFAULT_SECTOR_BUNDLES = ROOT / "notes" / "map-sector-bundles.json"
DEFAULT_TILESET_DIR = REFS / "Tilesets"
DEFAULT_PALETTE_SETTINGS = REFS / "map_palette_settings.yml"
DEFAULT_JSON_OUT = ROOT / "notes" / "map-tileset-bundles.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "map-tileset-bundles.md"
SCHEMA = "earthbound-decomp.map-tileset-bundles.v1"
TILESET_ID_COUNT = 32


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Catalog map tileset IDs, EBDecomp .fts exports, palette settings, and sector use."
    )
    parser.add_argument("--sector-bundles", default=str(DEFAULT_SECTOR_BUNDLES))
    parser.add_argument("--tileset-dir", default=str(DEFAULT_TILESET_DIR))
    parser.add_argument("--palette-settings", default=str(DEFAULT_PALETTE_SETTINGS))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def scalar(value: str) -> object:
    value = value.strip()
    if value == "null":
        return None
    if re.fullmatch(r"0x[0-9A-Fa-f]+", value):
        return int(value, 16)
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def catalog_fts_files(path: Path) -> dict[int, dict[str, object]]:
    files: dict[int, dict[str, object]] = {}
    for file_path in sorted(path.glob("*.fts")):
        match = re.fullmatch(r"(\d{2})\.fts", file_path.name)
        if match is None:
            continue
        tileset_id = int(match.group(1))
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        line_lengths: Counter[int] = Counter(len(line) for line in lines if line)
        files[tileset_id] = {
            "path": rel(file_path),
            "byte_count": file_path.stat().st_size,
            "sha1": hashlib.sha1(file_path.read_bytes()).hexdigest(),
            "nonblank_line_count": sum(1 for line in lines if line),
            "blank_line_count": sum(1 for line in lines if not line),
            "line_length_counts": {str(key): value for key, value in sorted(line_lengths.items())},
            "inferred_component_counts": {
                "tile_graphic_rows_64_hex_chars": line_lengths.get(64, 0),
                "metatile_or_collision_rows_96_hex_chars": line_lengths.get(96, 0),
                "palette_or_settings_rows_290_chars": line_lengths.get(290, 0),
            },
        }
    return files


def parse_palette_settings(path: Path) -> dict[int, list[dict[str, object]]]:
    settings: dict[int, list[dict[str, object]]] = defaultdict(list)
    current_tileset: int | None = None
    current_variant: int | None = None
    current: dict[str, object] | None = None
    in_event_palette = False

    def finish_variant() -> None:
        nonlocal current, current_variant, in_event_palette
        if current_tileset is not None and current_variant is not None and current is not None:
            current["variant"] = current_variant
            settings[current_tileset].append(current)
        current = None
        current_variant = None
        in_event_palette = False

    for line in path.read_text(encoding="utf-8").splitlines():
        tileset_match = re.fullmatch(r"(\d+):", line)
        if tileset_match is not None:
            finish_variant()
            current_tileset = int(tileset_match.group(1))
            continue
        variant_match = re.fullmatch(r"  (\d+):", line)
        if variant_match is not None:
            finish_variant()
            current_variant = int(variant_match.group(1))
            current = {}
            continue
        if current is None:
            continue
        if re.fullmatch(r"    Event Palette:", line):
            current["has_event_palette"] = True
            in_event_palette = True
            continue
        event_field_match = re.fullmatch(r"      ([^:]+):\s*(.+)", line)
        if event_field_match is not None and in_event_palette:
            key = f"Event Palette {event_field_match.group(1)}"
            current[key] = scalar(event_field_match.group(2))
            continue
        field_match = re.fullmatch(r"    ([^:\s][^:]*):\s*(.+)", line)
        if field_match is not None:
            current[field_match.group(1)] = scalar(field_match.group(2))
            in_event_palette = False
    finish_variant()
    return dict(settings)


def build_contract(args: argparse.Namespace) -> dict[str, object]:
    sector_bundles_path = Path(args.sector_bundles)
    tileset_dir = Path(args.tileset_dir)
    palette_settings_path = Path(args.palette_settings)
    sector_bundles = json.loads(sector_bundles_path.read_text(encoding="utf-8"))
    fts_files = catalog_fts_files(tileset_dir)
    palette_settings = parse_palette_settings(palette_settings_path)

    sector_ids_by_tileset: dict[int, list[int]] = defaultdict(list)
    palette_counts_by_tileset: dict[int, Counter[int]] = defaultdict(Counter)
    town_map_counts_by_tileset: dict[int, Counter[str]] = defaultdict(Counter)
    for sector in sector_bundles["sectors"]:
        tileset_id = int(sector["metadata"]["Tileset"])
        sector_ids_by_tileset[tileset_id].append(int(sector["sector"]["linear_index"]))
        palette_counts_by_tileset[tileset_id][int(sector["metadata"]["Palette"])] += 1
        town_map_counts_by_tileset[tileset_id][str(sector["metadata"]["Town Map"])] += 1

    rows: list[dict[str, object]] = []
    for tileset_id in range(TILESET_ID_COUNT):
        fts = fts_files.get(tileset_id)
        variants = palette_settings.get(tileset_id, [])
        rows.append(
            {
                "tileset_bundle_id": f"map_tileset.{tileset_id:02d}",
                "tileset_id": tileset_id,
                "sector_count": len(sector_ids_by_tileset.get(tileset_id, [])),
                "sector_ids": sector_ids_by_tileset.get(tileset_id, []),
                "sector_palette_counts": [
                    {"palette": key, "sector_count": value}
                    for key, value in palette_counts_by_tileset.get(tileset_id, Counter()).most_common()
                ],
                "town_map_counts": [
                    {"town_map": key, "sector_count": value}
                    for key, value in town_map_counts_by_tileset.get(tileset_id, Counter()).most_common()
                ],
                "palette_setting_count": len(variants),
                "palette_settings": variants,
                "has_direct_fts_export": fts is not None,
                "direct_fts_export": fts,
                "dependency_status": "direct_fts_export" if fts is not None else "palette_settings_only",
            }
        )

    used_tileset_ids = {int(row["metadata"]["Tileset"]) for row in sector_bundles["sectors"]}
    direct_export_ids = set(fts_files)
    return {
        "schema": SCHEMA,
        "title": "Map Tileset Bundle Contract",
        "generator": "tools/build_map_tileset_bundle_contract.py",
        "source_policy": (
            "Reference-derived tileset inventory. The contract records .fts file hashes, "
            "line profiles, palette settings, and sector dependencies; it does not commit "
            "decoded graphics/collision payloads."
        ),
        "sources": {
            "sector_bundles": rel(sector_bundles_path),
            "tileset_dir": rel(tileset_dir),
            "palette_settings": rel(palette_settings_path),
        },
        "summary": {
            "tileset_id_domain": TILESET_ID_COUNT,
            "tileset_ids_used_by_sectors": len(used_tileset_ids),
            "direct_fts_export_count": len(direct_export_ids),
            "used_tileset_ids_with_direct_fts_export": len(used_tileset_ids & direct_export_ids),
            "used_tileset_ids_without_direct_fts_export": len(used_tileset_ids - direct_export_ids),
            "unused_direct_fts_export_ids": sorted(direct_export_ids - used_tileset_ids),
            "used_tileset_ids_without_direct_fts_export_list": sorted(used_tileset_ids - direct_export_ids),
            "unused_tileset_ids": sorted(set(range(TILESET_ID_COUNT)) - used_tileset_ids),
            "palette_setting_tileset_count": len(palette_settings),
            "palette_setting_variant_count": sum(len(rows) for rows in palette_settings.values()),
            "top_tilesets_by_sector_count": [
                {"tileset_id": row["tileset_id"], "sector_count": row["sector_count"], "status": row["dependency_status"]}
                for row in sorted(rows, key=lambda item: (-int(item["sector_count"]), int(item["tileset_id"])))[:20]
            ],
        },
        "tilesets": rows,
    }


def write_markdown(contract: dict[str, object], path: Path) -> None:
    summary = contract["summary"]
    lines = [
        "# Map Tileset Bundle Contract",
        "",
        "This first-pass tileset contract catalogs the EBDecomp `.fts` exports,",
        "palette-setting groups, and the sector `Tileset` IDs that depend on them.",
        "",
        "It is intentionally conservative: sector tileset IDs `20`, `22-30` have",
        "palette settings and sector use, but no direct `.fts` export in the local",
        "ref checkout. The contract records that gap instead of inventing a mapping.",
        "",
        "## Summary",
        "",
        f"- tileset ID domain: `{summary['tileset_id_domain']}`",
        f"- tileset IDs used by sectors: `{summary['tileset_ids_used_by_sectors']}`",
        f"- direct `.fts` exports in refs: `{summary['direct_fts_export_count']}`",
        f"- used IDs with direct `.fts` export: `{summary['used_tileset_ids_with_direct_fts_export']}`",
        f"- used IDs without direct `.fts` export: `{summary['used_tileset_ids_without_direct_fts_export']}`",
        f"- palette-setting tileset groups: `{summary['palette_setting_tileset_count']}`",
        f"- palette-setting variants: `{summary['palette_setting_variant_count']}`",
        f"- unused direct `.fts` export IDs: `{', '.join(str(item) for item in summary['unused_direct_fts_export_ids'])}`",
        f"- used IDs without direct `.fts` export: `{', '.join(str(item) for item in summary['used_tileset_ids_without_direct_fts_export_list'])}`",
        f"- unused tileset IDs: `{', '.join(str(item) for item in summary['unused_tileset_ids'])}`",
        "",
        "## Top Tilesets By Sector Count",
        "",
        "| Tileset | Sectors | Status |",
        "| ---: | ---: | --- |",
    ]
    for row in summary["top_tilesets_by_sector_count"]:
        lines.append(f"| {row['tileset_id']} | {row['sector_count']} | `{row['status']}` |")

    lines.extend(
        [
            "",
            "## `.fts` Export Shape",
            "",
            "All present `.fts` exports have a stable line profile:",
            "",
            "- `1024` nonblank rows of length `64`",
            "- `1024` nonblank rows of length `96`",
            "- a variable number of nonblank rows of length `290`",
            "",
            "The contract stores these as inferred component counts and SHA-1 hashes for",
            "future decoders. The exact split into graphics, metatiles, collision, and",
            "palette/setting data remains a follow-up decoding step.",
            "",
            "## Machine-Readable Data",
            "",
            "`notes/map-tileset-bundles.json` records one row per tileset ID with:",
            "",
            "- stable `map_tileset.NN` bundle ID",
            "- sector IDs and sector palette/town-map counts",
            "- direct `.fts` export metadata when present",
            "- palette-setting variants from `map_palette_settings.yml`",
            "- dependency status for downstream sector consumers",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    contract = build_contract(args)
    json_out = Path(args.json_out)
    markdown_out = Path(args.markdown_out)
    contract["sources"]["json_out"] = rel(json_out)
    json_out.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(contract, markdown_out)


if __name__ == "__main__":
    main()
