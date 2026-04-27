from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TILESET_DIR = ROOT / "refs" / "eb-decompile-4ef92" / "Tilesets"
DEFAULT_JSON_OUT = ROOT / "notes" / "map-fts-animation-settings-contract.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "map-fts-animation-settings-contract.md"
SCHEMA = "earthbound-decomp.map-fts-animation-settings-contract.v1"
ROW_RE = re.compile(r"^[0-9a-v]{290}$")
BASE32_ALPHABET = "0123456789abcdefghijklmnopqrstuv"
COMMUNITY_RAM_MAP = ROOT / "refs" / "community-earthbound-docs" / "RAM_map.txt"
COMMUNITY_ROM_MAP = ROOT / "refs" / "community-earthbound-docs" / "ROM_map.txt"
EBSRC_BANK2F_SYMBOLS = ROOT / "refs" / "ebsrc-main" / "ebsrc-main" / "include" / "symbols" / "bank2f.inc.asm"
EBSRC_MAP_SYMBOLS = ROOT / "refs" / "ebsrc-main" / "ebsrc-main" / "include" / "symbols" / "map.inc.asm"
BANK_DE_ASSET_MAP = ROOT / "notes" / "bank-de-asset-data-map.md"
BANK_DF_ASSET_MAP = ROOT / "notes" / "bank-df-asset-data-map.md"
BANK_EF_ASSET_MAP = ROOT / "notes" / "bank-ef-asset-data-map.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit the 290-character EBDecomp .fts tile-animation/settings rows."
    )
    parser.add_argument("--tileset-dir", default=str(DEFAULT_TILESET_DIR))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def base32_value(text: str) -> int | None:
    value = 0
    for char in text:
        if char not in BASE32_ALPHABET:
            return None
        value = value * 32 + BASE32_ALPHABET.index(char)
    return value


def extract_rows(path: Path) -> list[str]:
    rows = [line.lower() for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if len(line) == 290]
    bad = [row for row in rows if ROW_RE.fullmatch(row) is None]
    if bad:
        raise ValueError(f"{path} has non-base32-like 290-character rows")
    return rows


def counter_items(counter: Counter[str]) -> list[dict[str, Any]]:
    return [{"char": char, "count": count} for char, count in sorted(counter.items())]


def most_common_items(counter: Counter[str], limit: int = 8) -> list[dict[str, Any]]:
    return [{"char": char, "count": count} for char, count in counter.most_common(limit)]


def audit_row(row: str) -> dict[str, Any]:
    blocks = [row[index * 58 : (index + 1) * 58] for index in range(5)]
    row_id = row[:2]
    block_counts = [Counter(block) for block in blocks]
    return {
        "row_id": row_id,
        "row_id_base32_value": base32_value(row_id),
        "row_group": row_id[0],
        "row_group_base32_value": base32_value(row_id[0]),
        "row_slot": row_id[1],
        "row_slot_base32_value": base32_value(row_id[1]),
        "row_sha1": sha1_text(row),
        "block_count": len(blocks),
        "block_length": 58,
        "block_sha1s": [sha1_text(block) for block in blocks],
        "block_zero_counts": [counts["0"] for counts in block_counts],
        "block_nonzero_char_counts": [len(block) - counts["0"] for block, counts in zip(blocks, block_counts)],
        "block_distinct_char_counts": [len(counts) for counts in block_counts],
        "block_character_sets": ["".join(sorted(counts)) for counts in block_counts],
        "unique_block_count": len(set(blocks)),
        "zero_only_block_count": sum(1 for block in blocks if set(block) == {"0"}),
        "character_set": "".join(sorted(set(row))),
    }


def audit_tileset(path: Path, rows: list[str]) -> dict[str, Any]:
    match = re.fullmatch(r"(\d{2})\.fts", path.name)
    tileset_id = int(match.group(1)) if match else None
    row_contracts = [audit_row(row) for row in rows]
    block_hashes = [block_hash for row in row_contracts for block_hash in row["block_sha1s"]]
    row_groups = Counter(row["row_group"] for row in row_contracts)
    row_slots = Counter(row["row_slot"] for row in row_contracts)
    return {
        "tileset_id": tileset_id,
        "path": rel(path),
        "file_sha1": hashlib.sha1(path.read_bytes()).hexdigest(),
        "animation_settings_rows_sha1": sha1_text("\n".join(rows)),
        "row_count": len(rows),
        "row_length": 290,
        "block_count": len(rows) * 5,
        "block_length": 58,
        "unique_row_count": len(set(rows)),
        "unique_block_count": len(set(block_hashes)),
        "row_ids": [row["row_id"] for row in row_contracts],
        "row_group_counts": [{"group": group, "count": count} for group, count in sorted(row_groups.items())],
        "row_slot_counts": [{"slot": slot, "count": count} for slot, count in sorted(row_slots.items())],
        "character_set": "".join(sorted(set("".join(rows)))) if rows else "",
        "rows": row_contracts,
    }


def summarize_block_position_profiles(raw_rows: list[str]) -> list[dict[str, Any]]:
    profiles = []
    for block_index in range(5):
        blocks = [row[block_index * 58 : (block_index + 1) * 58] for row in raw_rows]
        block_counts = Counter(blocks)
        char_counts = Counter("".join(blocks))
        constant_positions = []
        low_variance_positions = []
        for position in range(58):
            position_counts = Counter(block[position] for block in blocks)
            distinct = "".join(sorted(position_counts))
            if len(position_counts) == 1:
                constant_positions.append({"position": position, "char": distinct})
            if len(position_counts) <= 4:
                low_variance_positions.append(
                    {
                        "position": position,
                        "character_set": distinct,
                        "char_counts": counter_items(position_counts),
                    }
                )
        profiles.append(
            {
                "block_index": block_index,
                "block_length": 58,
                "sample_count": len(blocks),
                "unique_block_count": len(block_counts),
                "zero_only_block_count": sum(
                    count for block, count in block_counts.items() if set(block) == {"0"}
                ),
                "character_set": "".join(sorted(char_counts)),
                "common_char_counts": most_common_items(char_counts, 10),
                "constant_positions": constant_positions,
                "constant_zero_positions": [
                    item["position"] for item in constant_positions if item["char"] == "0"
                ],
                "low_variance_positions": low_variance_positions,
            }
        )
    return profiles


def summarize_row_group_ownership(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    owners: dict[str, dict[str, Any]] = {}
    for tileset in rows:
        tileset_id = tileset["tileset_id"]
        for row_id in tileset["row_ids"]:
            group = row_id[0]
            owner = owners.setdefault(group, {"group": group, "tileset_ids": set(), "row_ids": []})
            owner["tileset_ids"].add(tileset_id)
            owner["row_ids"].append(row_id)
    result = []
    for group, owner in sorted(owners.items()):
        slots = [row_id[1] for row_id in owner["row_ids"]]
        result.append(
            {
                "group": group,
                "group_base32_value": base32_value(group),
                "tileset_ids": sorted(owner["tileset_ids"]),
                "row_ids": sorted(owner["row_ids"]),
                "slot_ids": sorted(slots),
                "slot_base32_values": [base32_value(slot) for slot in sorted(slots)],
                "slot_count": len(slots),
                "single_tileset_owner": len(owner["tileset_ids"]) == 1,
            }
        )
    return result


def parse_animation_gfx_assets(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    pattern = re.compile(
        r"\|\s*\d+\s*\|\s*`MAP_DATA_TILE_ANIMATION_GFX_(\d+)`\s*\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|\s*(\d+)\s*\|"
    )
    assets = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.search(line)
        if not match:
            continue
        asset_id, payload, cpu_span, file_offset, byte_count = match.groups()
        assets.append(
            {
                "asset_id": int(asset_id),
                "label": f"MAP_DATA_TILE_ANIMATION_GFX_{asset_id}",
                "payload": payload,
                "cpu_span": cpu_span,
                "file_offset": file_offset,
                "byte_count": int(byte_count),
                "source": rel(path),
            }
        )
    return assets


def build_reference_anchors() -> dict[str, Any]:
    asset_payloads = parse_animation_gfx_assets(BANK_DF_ASSET_MAP) + parse_animation_gfx_assets(BANK_DE_ASSET_MAP)
    asset_payloads = sorted(asset_payloads, key=lambda item: item["asset_id"])
    tiny_payloads = [item["asset_id"] for item in asset_payloads if item["byte_count"] == 25]
    return {
        "wram": [
            {
                "label": "Map tile animation data",
                "wram_span": "$43DC..$445B",
                "byte_count": 0x80,
                "source": rel(COMMUNITY_RAM_MAP),
            }
        ],
        "legacy_rom_map": [
            {
                "label": "Compressed Tile Animation Characters Data Block 1",
                "file_span": "0x1EF2E7..0x1EFEDC",
                "source": rel(COMMUNITY_ROM_MAP),
            },
            {
                "label": "Compressed Tile Animation Characters Data Block 2",
                "file_span": "0x1FC443..0x1FE6E0",
                "source": rel(COMMUNITY_ROM_MAP),
            },
            {
                "label": "Tile Animation Characters Pointer Table",
                "file_span": "0x2F13CB..0x2F141A",
                "source": rel(COMMUNITY_ROM_MAP),
            },
            {
                "label": "Tile Animation Properties Pointer Table",
                "file_span": "0x2F141B..0x2F146A",
                "source": rel(COMMUNITY_ROM_MAP),
            },
            {
                "label": "Tile Animation Properties Table",
                "file_span": "0x2F146B..0x2F153E",
                "source": rel(COMMUNITY_ROM_MAP),
            },
        ],
        "ebsrc_symbols": [
            {
                "symbol": "MAP_DATA_TILE_ANIMATION_PTR_TABLE",
                "source": rel(EBSRC_BANK2F_SYMBOLS),
            },
            {
                "symbol": "MAP_DATA_WEIRD_TILE_ANIMATION_PTR_TABLE",
                "source": rel(EBSRC_BANK2F_SYMBOLS),
            },
            {
                "symbol": "MAP_DATA_TILE_ANIMATION_GFX_0..19",
                "source": rel(EBSRC_MAP_SYMBOLS),
            },
        ],
        "asset_payloads": asset_payloads,
        "asset_payload_summary": {
            "count": len(asset_payloads),
            "asset_id_range": [
                min((item["asset_id"] for item in asset_payloads), default=0),
                max((item["asset_id"] for item in asset_payloads), default=0),
            ],
            "tiny_25_byte_placeholder_asset_ids": tiny_payloads,
            "non_tiny_asset_ids": [item["asset_id"] for item in asset_payloads if item["byte_count"] != 25],
        },
        "ef_table_includes": [
            {
                "include": "data/map/tileset_animation_pointer_table.asm",
                "source": rel(BANK_EF_ASSET_MAP),
            },
            {
                "include": "data/map/tileset_animation_properties_pointer_table.asm",
                "source": rel(BANK_EF_ASSET_MAP),
            },
            {
                "include": "data/map/tileset_animation_properties/00.asm..19.asm",
                "source": rel(BANK_EF_ASSET_MAP),
            },
        ],
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    row_count_total = sum(int(row["row_count"]) for row in rows)
    block_count_total = sum(int(row["block_count"]) for row in rows)
    row_ids = [row_id for tileset in rows for row_id in tileset["row_ids"]]
    row_groups = Counter(row_id[0] for row_id in row_ids)
    row_slots = Counter(row_id[1] for row_id in row_ids)
    row_count_values = [int(row["row_count"]) for row in rows]
    row_group_ownership = summarize_row_group_ownership(rows)
    return {
        "tileset_count": len(rows),
        "row_count_total": row_count_total,
        "row_count_range": [min(row_count_values), max(row_count_values)] if row_count_values else [0, 0],
        "block_count_total": block_count_total,
        "row_shape": "variable rows per tileset; each row is 5 blocks of 58 base32-like characters",
        "unique_row_id_count": len(set(row_ids)),
        "row_id_count": len(row_ids),
        "duplicate_row_ids": [row_id for row_id, count in Counter(row_ids).items() if count > 1],
        "row_group_counts": [{"group": group, "count": count} for group, count in sorted(row_groups.items())],
        "row_slot_counts": [{"slot": slot, "count": count} for slot, count in sorted(row_slots.items())],
        "single_tileset_owned_row_group_count": sum(1 for item in row_group_ownership if item["single_tileset_owner"]),
        "multi_tileset_row_group_count": sum(1 for item in row_group_ownership if not item["single_tileset_owner"]),
        "character_set": "".join(sorted(set("".join(row["character_set"] for row in rows)))),
    }


def build_contract(args: argparse.Namespace) -> dict[str, Any]:
    tileset_dir = Path(args.tileset_dir)
    raw_rows = []
    rows = []
    for path in sorted(tileset_dir.glob("*.fts")):
        tileset_rows = extract_rows(path)
        raw_rows.extend(tileset_rows)
        rows.append(audit_tileset(path, tileset_rows))
    row_group_ownership = summarize_row_group_ownership(rows)
    return {
        "schema": SCHEMA,
        "title": "Map FTS Animation/Settings Contract",
        "generator": "tools/build_map_fts_animation_settings_contract.py",
        "source_policy": (
            "Reference-derived structural contract. This records row IDs, hashes, "
            "character sets, and block counts from the 290-character .fts rows; "
            "it does not commit raw rows or decoded ROM-derived payload arrays."
        ),
        "sources": {
            "tileset_dir": rel(tileset_dir),
            "ref_labels": [
                "refs/ebsrc-main/ebsrc-main/include/symbols/map.inc.asm",
                "refs/ebsrc-main/ebsrc-main/include/symbols/bank2f.inc.asm",
                "refs/community-earthbound-docs/ROM_map.txt",
                "refs/community-earthbound-docs/RAM_map.txt",
                "notes/bank-de-asset-data-map.md",
                "notes/bank-df-asset-data-map.md",
                "notes/bank-ef-asset-data-map.md",
            ],
        },
        "evidence": [
            "All present .fts exports place the 290-character rows between tile-pixel rows and arrangement/collision rows.",
            "Each 290-character row splits evenly into 5 blocks of 58 base32-like characters.",
            "Row IDs use the same 0-v alphabet seen in the row payload, are unique across the local export set, and divide into a structural group/slot model.",
            "Every observed row group is owned by one direct .fts export, matching a tileset-local animation/settings ownership model.",
            "ebsrc and community ROM maps expose map tile animation graphics, pointer tables, properties tables, and WRAM animation state anchors near the tileset data.",
        ],
        "reference_anchors": build_reference_anchors(),
        "summary": summarize(rows),
        "row_group_ownership": row_group_ownership,
        "block_position_profiles": summarize_block_position_profiles(raw_rows),
        "tilesets": rows,
    }


def write_markdown(contract: dict[str, Any], path: Path) -> None:
    summary = contract["summary"]
    anchors = contract["reference_anchors"]
    group_counts = ", ".join(f"`{item['group']}`:{item['count']}" for item in summary["row_group_counts"])
    slot_counts = ", ".join(f"`{item['slot']}`:{item['count']}" for item in summary["row_slot_counts"])
    lines = [
        "# Map FTS Animation/Settings Contract",
        "",
        "This contract maps the variable 290-character section of each local EBDecomp",
        "`.fts` tileset export. It keeps the payload opaque but records the stable",
        "row/block shape needed for a later animation/settings decoder.",
        "",
        "The working interpretation is tile-animation/settings metadata. This is based",
        "on its position in the `.fts` export, its variable row count, and reference",
        "labels for map tile animation graphics/properties near the map tileset data.",
        "",
        "## Summary",
        "",
        f"- tilesets audited: `{summary['tileset_count']}`",
        f"- rows: `{summary['row_count_total']}`",
        f"- row count range per tileset: `{summary['row_count_range'][0]}-{summary['row_count_range'][1]}`",
        f"- blocks: `{summary['block_count_total']}`",
        f"- row shape: `{summary['row_shape']}`",
        f"- unique row IDs: `{summary['unique_row_id_count']}`",
        f"- duplicate row IDs: `{', '.join(summary['duplicate_row_ids']) if summary['duplicate_row_ids'] else 'none'}`",
        f"- single-tileset-owned row groups: `{summary['single_tileset_owned_row_group_count']}`",
        f"- multi-tileset row groups: `{summary['multi_tileset_row_group_count']}`",
        f"- character set: `{summary['character_set']}`",
        f"- referenced animation graphics payloads: `{anchors['asset_payload_summary']['count']}`",
        "",
        "## Row ID Distribution",
        "",
        f"- groups: {group_counts}",
        f"- slots: {slot_counts}",
        "",
        "## Reference Anchors",
        "",
        f"- WRAM runtime state: `$43DC..$445B` (`{anchors['wram'][0]['byte_count']}` bytes) is labeled map tile animation data in `{anchors['wram'][0]['source']}`.",
        "- Legacy ROM map anchors tile-animation character blocks at `0x1EF2E7..0x1EFEDC` and `0x1FC443..0x1FE6E0`, plus EF pointer/property tables at `0x2F13CB..0x2F153E`.",
        "- ebsrc exposes `MAP_DATA_TILE_ANIMATION_PTR_TABLE`, `MAP_DATA_WEIRD_TILE_ANIMATION_PTR_TABLE`, and `MAP_DATA_TILE_ANIMATION_GFX_0..19` symbols.",
        f"- Local bank maps identify `{anchors['asset_payload_summary']['count']}` `MAP_DATA_TILE_ANIMATION_GFX_N` payloads; 25-byte placeholder/tiny payload IDs are `{', '.join(str(item) for item in anchors['asset_payload_summary']['tiny_25_byte_placeholder_asset_ids'])}`.",
        "- Bank EF's include list names the tileset animation pointer table, animation properties pointer table, and per-tileset animation property files `00..19`.",
        "",
        "## Row ID Model",
        "",
        "The leading two characters of each 290-character row are now treated as a",
        "structural row ID: `row_id[0]` is the base32-like animation/settings group",
        "and `row_id[1]` is the slot within that group. This is a strong export-shape",
        "model, not yet a claim that the group number directly equals an EF property",
        "pointer index or compressed graphics ID.",
        "",
        "| Group | Owner tileset(s) | Slots |",
        "| --- | --- | --- |",
    ]
    for owner in contract["row_group_ownership"]:
        lines.append(
            f"| `{owner['group']}` | `{', '.join(str(item) for item in owner['tileset_ids'])}` | "
            f"`{', '.join(owner['slot_ids'])}` |"
        )
    lines.extend(
        [
            "",
            "## Block Position Profiles",
            "",
            "Each row splits into five 58-character blocks. The profile below records",
            "stable position-level shape without committing the raw block text.",
            "",
            "| Block | Unique blocks | Zero-only blocks | Constant zero positions | Common chars |",
            "| ---: | ---: | ---: | --- | --- |",
        ]
    )
    for profile in contract["block_position_profiles"]:
        constant_zero_positions = ", ".join(str(item) for item in profile["constant_zero_positions"]) or "none"
        common_chars = ", ".join(
            f"`{item['char']}`:{item['count']}" for item in profile["common_char_counts"][:5]
        )
        lines.append(
            f"| {profile['block_index']} | {profile['unique_block_count']} | {profile['zero_only_block_count']} | "
            f"`{constant_zero_positions}` | {common_chars} |"
        )
    lines.extend(
        [
            "",
        "## Per-Tileset Shape",
        "",
        "| Tileset | Rows | Blocks | Row IDs |",
        "| ---: | ---: | ---: | --- |",
        ]
    )
    for row in contract["tilesets"]:
        lines.append(
            f"| {row['tileset_id']} | {row['row_count']} | {row['block_count']} | "
            f"`{', '.join(row['row_ids'])}` |"
        )
    lines.extend(
        [
            "",
            "## Machine-Readable Data",
            "",
            "`notes/map-fts-animation-settings-contract.json` records one row per",
            "direct `.fts` export with row IDs, row/block SHA-1 hashes, character sets,",
            "and fixed-shape counts. It intentionally omits raw row content.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    contract = build_contract(args)
    json_path = Path(args.json_out)
    markdown_path = Path(args.markdown_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(contract, markdown_path)
    print(f"Wrote {rel(json_path)} and {rel(markdown_path)}")


if __name__ == "__main__":
    main()
