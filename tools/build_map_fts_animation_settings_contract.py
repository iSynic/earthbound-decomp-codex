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


def audit_row(row: str) -> dict[str, Any]:
    blocks = [row[index * 58 : (index + 1) * 58] for index in range(5)]
    row_id = row[:2]
    return {
        "row_id": row_id,
        "row_id_base32_value": base32_value(row_id),
        "row_group": row_id[0],
        "row_slot": row_id[1],
        "row_sha1": sha1_text(row),
        "block_count": len(blocks),
        "block_length": 58,
        "block_sha1s": [sha1_text(block) for block in blocks],
        "unique_block_count": len(set(blocks)),
        "zero_only_block_count": sum(1 for block in blocks if set(block) == {"0"}),
        "character_set": "".join(sorted(set(row))),
    }


def audit_tileset(path: Path) -> dict[str, Any]:
    match = re.fullmatch(r"(\d{2})\.fts", path.name)
    tileset_id = int(match.group(1)) if match else None
    rows = extract_rows(path)
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


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    row_count_total = sum(int(row["row_count"]) for row in rows)
    block_count_total = sum(int(row["block_count"]) for row in rows)
    row_ids = [row_id for tileset in rows for row_id in tileset["row_ids"]]
    row_groups = Counter(row_id[0] for row_id in row_ids)
    row_slots = Counter(row_id[1] for row_id in row_ids)
    row_count_values = [int(row["row_count"]) for row in rows]
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
        "character_set": "".join(sorted(set("".join(row["character_set"] for row in rows)))),
    }


def build_contract(args: argparse.Namespace) -> dict[str, Any]:
    tileset_dir = Path(args.tileset_dir)
    rows = [audit_tileset(path) for path in sorted(tileset_dir.glob("*.fts"))]
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
                "refs/community-earthbound-docs/ROM_map.txt",
            ],
        },
        "evidence": [
            "All present .fts exports place the 290-character rows between tile-pixel rows and arrangement/collision rows.",
            "Each 290-character row splits evenly into 5 blocks of 58 base32-like characters.",
            "Row IDs use the same 0-v alphabet seen in the row payload and are unique across the local export set.",
            "ebsrc and community ROM maps expose adjacent map tile animation graphics/properties labels near the tileset data.",
        ],
        "summary": summarize(rows),
        "tilesets": rows,
    }


def write_markdown(contract: dict[str, Any], path: Path) -> None:
    summary = contract["summary"]
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
        f"- character set: `{summary['character_set']}`",
        "",
        "## Row ID Distribution",
        "",
        f"- groups: {group_counts}",
        f"- slots: {slot_counts}",
        "",
        "## Per-Tileset Shape",
        "",
        "| Tileset | Rows | Blocks | Row IDs |",
        "| ---: | ---: | ---: | --- |",
    ]
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
