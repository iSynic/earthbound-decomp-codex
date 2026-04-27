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
DEFAULT_JSON_OUT = ROOT / "notes" / "map-fts-format-audit.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "map-fts-format-audit.md"
SCHEMA = "earthbound-decomp.map-fts-format-audit.v1"
HEX_RE = re.compile(r"^[0-9A-Fa-f]+$")


SECTION_LABELS = {
    64: {
        "component": "tile_pixel_rows_64_chars",
        "interpretation": "8x8 indexed tile rows; 64 hex-like nibbles per row, packable as 32 bytes/tile",
        "confidence": "high",
    },
    96: {
        "component": "arrangement_collision_rows_96_chars",
        "interpretation": "arrangement/collision cell records; 16 three-byte cells per row",
        "confidence": "high",
    },
    290: {
        "component": "palette_or_settings_rows_290_chars",
        "interpretation": "base36-like palette/settings text rows; variable count by tileset",
        "confidence": "medium",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit EBDecomp .fts tileset export shape without committing payload bytes."
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


def sha1_text(lines: list[str]) -> str:
    return hashlib.sha1("\n".join(lines).encode("utf-8")).hexdigest()


def sha1_hex_bytes(lines: list[str]) -> str | None:
    text = "".join(lines)
    if len(text) % 2 != 0 or HEX_RE.fullmatch(text) is None:
        return None
    return hashlib.sha1(bytes.fromhex(text)).hexdigest()


def nonblank_sections(lines: list[str]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current_length: int | None = None
    current_rows: list[str] = []
    blank_runs_inside_section: list[int] = []
    pending_blanks = 0

    def finish_section() -> None:
        nonlocal current_length, current_rows, blank_runs_inside_section
        if current_length is None:
            return
        all_hex = all(HEX_RE.fullmatch(row) is not None for row in current_rows)
        label = SECTION_LABELS.get(
            current_length,
            {
                "component": f"rows_{current_length}_chars",
                "interpretation": "unclassified fixed-width text rows",
                "confidence": "low",
            },
        )
        sections.append(
            {
                "component": label["component"],
                "row_length": current_length,
                "row_count": len(current_rows),
                "unique_row_count": len(set(current_rows)),
                "all_rows_hex_like": all_hex,
                "hex_byte_count_if_packed": len(current_rows) * current_length // 2 if all_hex else None,
                "text_sha1": sha1_text(current_rows),
                "hex_bytes_sha1": sha1_hex_bytes(current_rows) if all_hex else None,
                "character_set": "".join(sorted(set("".join(current_rows)))),
                "blank_runs_inside_section": sorted(Counter(blank_runs_inside_section).items()),
                "interpretation": label["interpretation"],
                "confidence": label["confidence"],
            }
        )
        current_length = None
        current_rows = []
        blank_runs_inside_section = []

    for line in lines:
        if line == "":
            pending_blanks += 1
            continue
        line_length = len(line)
        if current_length is None:
            current_length = line_length
            current_rows = [line]
            pending_blanks = 0
            continue
        if line_length != current_length:
            finish_section()
            current_length = line_length
            current_rows = [line]
            pending_blanks = 0
            continue
        if pending_blanks:
            blank_runs_inside_section.append(pending_blanks)
        current_rows.append(line)
        pending_blanks = 0
    finish_section()
    return sections


def audit_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    nonblank = [line for line in lines if line]
    length_counts = Counter(len(line) for line in nonblank)
    sections = nonblank_sections(lines)
    match = re.fullmatch(r"(\d{2})\.fts", path.name)
    tileset_id = int(match.group(1)) if match else None
    return {
        "tileset_id": tileset_id,
        "path": rel(path),
        "file_byte_count": path.stat().st_size,
        "file_sha1": hashlib.sha1(path.read_bytes()).hexdigest(),
        "line_count": len(lines),
        "nonblank_line_count": len(nonblank),
        "blank_line_count": len(lines) - len(nonblank),
        "line_length_counts": {str(key): value for key, value in sorted(length_counts.items())},
        "section_count": len(sections),
        "sections": sections,
        "matches_current_export_shape": [section["row_length"] for section in sections] == [64, 290, 96]
        and sections[0]["row_count"] == 1024
        and sections[2]["row_count"] == 1024,
    }


def summarize(files: list[dict[str, Any]]) -> dict[str, Any]:
    export_shape_count = sum(1 for item in files if item["matches_current_export_shape"])
    section_totals: dict[str, dict[str, Any]] = {}
    for item in files:
        for section in item["sections"]:
            component = str(section["component"])
            current = section_totals.setdefault(
                component,
                {
                    "files": 0,
                    "row_length": section["row_length"],
                    "row_count_min": section["row_count"],
                    "row_count_max": section["row_count"],
                    "row_count_total": 0,
                    "hex_byte_count_total_if_packed": 0,
                    "all_files_hex_like": True,
                    "character_set": set(),
                },
            )
            current["files"] += 1
            current["row_count_min"] = min(current["row_count_min"], section["row_count"])
            current["row_count_max"] = max(current["row_count_max"], section["row_count"])
            current["row_count_total"] += section["row_count"]
            if section["hex_byte_count_if_packed"] is not None:
                current["hex_byte_count_total_if_packed"] += section["hex_byte_count_if_packed"]
            current["all_files_hex_like"] = current["all_files_hex_like"] and bool(section["all_rows_hex_like"])
            current["character_set"].update(section["character_set"])

    normalized_totals: dict[str, dict[str, Any]] = {}
    for component, values in sorted(section_totals.items()):
        normalized = dict(values)
        normalized["character_set"] = "".join(sorted(normalized["character_set"]))
        if not normalized["all_files_hex_like"]:
            normalized["hex_byte_count_total_if_packed"] = None
        normalized_totals[component] = normalized

    row290_counts = [
        section["row_count"]
        for item in files
        for section in item["sections"]
        if section["row_length"] == 290
    ]
    return {
        "direct_fts_export_count": len(files),
        "matching_current_export_shape_count": export_shape_count,
        "tileset_ids_with_exports": [item["tileset_id"] for item in files],
        "section_totals": normalized_totals,
        "palette_or_settings_row_count_range": [min(row290_counts), max(row290_counts)] if row290_counts else [0, 0],
    }


def build_audit(args: argparse.Namespace) -> dict[str, Any]:
    tileset_dir = Path(args.tileset_dir)
    files = [audit_file(path) for path in sorted(tileset_dir.glob("*.fts"))]
    return {
        "schema": SCHEMA,
        "title": "Map FTS Format Audit",
        "generator": "tools/build_map_fts_format_audit.py",
        "source_policy": (
            "Reference-derived format audit. This records file hashes, section shapes, "
            "row counts, character sets, and section hashes only; it does not commit "
            "raw .fts rows or decoded ROM-derived payloads."
        ),
        "sources": {"tileset_dir": rel(tileset_dir)},
        "summary": summarize(files),
        "files": files,
    }


def write_markdown(audit: dict[str, Any], path: Path) -> None:
    summary = audit["summary"]
    lines = [
        "# Map FTS Format Audit",
        "",
        "This audit maps the local EBDecomp `.fts` tileset export shape without",
        "checking in raw export rows or decoded graphics/data payloads.",
        "",
        "## Summary",
        "",
        f"- direct `.fts` exports audited: `{summary['direct_fts_export_count']}`",
        f"- exports matching current 64/290/96 shape: `{summary['matching_current_export_shape_count']}`",
        f"- tileset IDs with exports: `{', '.join(str(item) for item in summary['tileset_ids_with_exports'])}`",
        f"- variable 290-character row count range: `{summary['palette_or_settings_row_count_range'][0]}-{summary['palette_or_settings_row_count_range'][1]}`",
        "",
        "## Inferred Components",
        "",
        "| Component | Files | Row Length | Rows/File | Packed Bytes Total | Hex-Like | Character Set |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for component, row in summary["section_totals"].items():
        row_range = (
            str(row["row_count_min"])
            if row["row_count_min"] == row["row_count_max"]
            else f"{row['row_count_min']}-{row['row_count_max']}"
        )
        packed = row["hex_byte_count_total_if_packed"]
        packed_text = "" if packed is None else str(packed)
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{component}`",
                    str(row["files"]),
                    str(row["row_length"]),
                    row_range,
                    packed_text,
                    "`yes`" if row["all_files_hex_like"] else "`no`",
                    f"`{row['character_set']}`",
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Current Interpretation",
            "",
            "- `tile_pixel_rows_64_chars`: high-confidence 8x8 indexed tile rows. Each row",
            "  has 64 hex-like nibbles, matching one 4bpp 8x8 tile if packed to 32 bytes.",
            "- `palette_or_settings_rows_290_chars`: variable-count base36-like settings rows.",
            "  These are not hex byte rows and need a dedicated decoder.",
            "- `arrangement_collision_rows_96_chars`: fixed 1024-row arrangement/collision",
            "  records. Each row splits into 16 three-byte cells, matching a 4x4 grid of",
            "  8x8 subtiles per map tile/metatile.",
            "",
            "## Per-File Shape",
            "",
            "| Tileset | Sections | 64 Rows | 290 Rows | 96 Rows | Shape OK |",
            "| ---: | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for item in audit["files"]:
        row_counts = {section["row_length"]: section["row_count"] for section in item["sections"]}
        section_shape = "/".join(str(section["row_length"]) for section in item["sections"])
        lines.append(
            f"| {item['tileset_id']} | `{section_shape}` | {row_counts.get(64, 0)} | "
            f"{row_counts.get(290, 0)} | {row_counts.get(96, 0)} | "
            f"`{'yes' if item['matches_current_export_shape'] else 'no'}` |"
        )

    lines.extend(
        [
            "",
            "## Machine-Readable Data",
            "",
            "`notes/map-fts-format-audit.json` records each file's line profile, section",
            "hashes, packed byte counts where applicable, and conservative component labels.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    audit = build_audit(args)
    json_path = Path(args.json_out)
    markdown_path = Path(args.markdown_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(audit, markdown_path)
    print(f"Wrote {rel(json_path)} and {rel(markdown_path)}")


if __name__ == "__main__":
    main()
