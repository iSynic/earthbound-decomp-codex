from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from asset_output_recipe_contracts import OUTPUT_RECIPE_CONTRACTS


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST_DIR = ROOT / "asset-manifests"
DEFAULT_JSON_OUT = ROOT / "build" / "asset-output-preview-geometry.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "asset-output-preview-geometry.md"

FAMILIES: list[dict[str, Any]] = [
    {"id": "battle_visual_assets", "label": "Battle visual assets", "banks": ["CA", "CB", "CC", "CD", "CE"]},
    {"id": "mixed_asset_tables", "label": "Mixed asset/table banks", "banks": ["CF", "D0"]},
    {"id": "overworld_sprites", "label": "Overworld sprites", "banks": ["D1", "D2", "D3", "D4", "D5"]},
    {
        "id": "map_tilesets_and_runtime_tables",
        "label": "Map tilesets and runtime tables",
        "banks": ["D6", "D7", "D8", "D9", "DA", "DB", "DC", "DD", "DE", "DF"],
    },
    {"id": "ui_font_town_map_assets", "label": "UI, fonts, and town-map assets", "banks": ["E0", "E1"]},
    {
        "id": "audio_packs",
        "label": "Audio packs",
        "banks": ["E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "EA", "EB", "EC", "ED", "EE"],
    },
    {"id": "ef_debug_and_late_tail", "label": "EF debug and late-tail data", "banks": ["EF"]},
]


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def infer_bank(path: Path, manifest: dict[str, Any]) -> str:
    if path.name.startswith("bank-"):
        return path.name.split("-", 2)[1].upper()
    if path.name.startswith("ef-"):
        return "EF"
    title = str(manifest.get("title", ""))
    for token in title.replace("-", " ").split():
        if len(token) == 2:
            try:
                int(token, 16)
            except ValueError:
                continue
            return token.upper()
    raise ValueError(f"Could not infer bank for {path}")


def family_for_bank(bank: str) -> dict[str, Any]:
    for family in FAMILIES:
        if bank in family["banks"]:
            return family
    raise ValueError(f"No asset-output family for bank {bank}")


def int_field(output: dict[str, Any], key: str, default: int | None = None) -> int | None:
    value = output.get(key, default)
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValueError(f"{output.get('path')}: {key} must be an integer")
    return value


def tile_sheet_geometry(source_bytes: int, tile_size: int, columns: int) -> dict[str, Any]:
    if source_bytes <= 0:
        return {"status": "invalid", "reason": "source byte count is not positive"}
    if source_bytes % tile_size != 0:
        return {
            "status": "invalid",
            "reason": f"source bytes {source_bytes} are not a multiple of {tile_size}",
        }
    tiles = source_bytes // tile_size
    rows = math.ceil(tiles / columns)
    return {
        "status": "known",
        "width": columns * 8,
        "height": rows * 8,
        "tiles": tiles,
    }


def effective_tile_source_bytes(output: dict[str, Any], source_bytes: int) -> int:
    trim = int_field(output, "trim_trailing_bytes", 0)
    if trim is None:
        return source_bytes
    if trim < 0:
        return -1
    return source_bytes - trim


def palette_swatch_geometry(
    output: dict[str, Any],
    source_bytes: int,
    *,
    compressed_source: bool,
) -> dict[str, Any]:
    colors = int_field(output, "colors")
    if colors is None and not compressed_source and source_bytes > 0 and source_bytes % 2 == 0:
        colors = source_bytes // 2
    if colors is None:
        return {
            "status": "requires_decode",
            "reason": "palette color count requires ROM decode",
        }
    per_row = int_field(output, "per_row", 16)
    swatch = int_field(output, "swatch", 16)
    if per_row is None or swatch is None or per_row <= 0 or swatch <= 0:
        return {"status": "invalid", "reason": "palette swatch dimensions require positive per_row and swatch"}
    rows = math.ceil(colors / per_row) if colors else 0
    return {
        "status": "known",
        "width": min(colors, per_row) * swatch if colors else 0,
        "height": rows * swatch,
        "colors": colors,
    }


def preview_geometry(output: dict[str, Any], source_bytes: int) -> dict[str, Any]:
    kind = str(output.get("kind"))
    if kind == "snes_2bpp_tiles_png":
        columns = int_field(output, "columns", 16)
        if columns is None or columns <= 0:
            return {"status": "invalid", "reason": "tile sheet columns must be positive"}
        effective_bytes = effective_tile_source_bytes(output, source_bytes)
        geometry = tile_sheet_geometry(effective_bytes, 16, columns)
        if geometry["status"] == "known" and effective_bytes != source_bytes:
            geometry["source_bytes_after_trim"] = effective_bytes
        return geometry
    if kind in {"snes_4bpp_tiles_png", "snes_4bpp_tiles_palette_png"}:
        columns = int_field(output, "columns", 16)
        if columns is None or columns <= 0:
            return {"status": "invalid", "reason": "tile sheet columns must be positive"}
        return tile_sheet_geometry(source_bytes, 32, columns)
    if kind in {"earthbound_lzhal_snes_4bpp_tiles_png", "earthbound_lzhal_snes_4bpp_tiles_palette_png"}:
        return {
            "status": "requires_decode",
            "reason": "tile count requires LZHAL decompression",
        }
    if kind == "snes_palette_swatch_png":
        return palette_swatch_geometry(output, source_bytes, compressed_source=False)
    if kind == "earthbound_lzhal_snes_palette_swatch_png":
        return palette_swatch_geometry(output, source_bytes, compressed_source=True)
    if kind == "earthbound_lzhal_battle_bg_arrangement_png":
        width_tiles = int_field(output, "width_tiles")
        height_tiles = int_field(output, "height_tiles")
        if width_tiles is None or height_tiles is None or width_tiles <= 0 or height_tiles <= 0:
            return {"status": "invalid", "reason": "battle background dimensions require positive tile counts"}
        return {
            "status": "known",
            "width": width_tiles * 8,
            "height": height_tiles * 8,
            "tiles": width_tiles * height_tiles,
        }
    if kind == "earthbound_lzhal_battle_sprite_png":
        width = int_field(output, "width")
        height = int_field(output, "height")
        if width is None or height is None or width <= 0 or height <= 0:
            return {"status": "invalid", "reason": "battle sprite dimensions must be positive"}
        return {"status": "known", "width": width, "height": height}
    return {"status": "unsupported", "reason": f"{kind} is not a PNG preview recipe"}


def manifest_paths(manifest_dir: Path) -> list[Path]:
    return sorted(manifest_dir.glob("*.json"))


def build_report(manifest_dir: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []

    for manifest_path in manifest_paths(manifest_dir):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        bank = infer_bank(manifest_path, manifest)
        family = family_for_bank(bank)
        assets = manifest.get("assets", [])
        if not isinstance(assets, list):
            raise ValueError(f"{manifest_path}: assets must be a list")
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            source = asset.get("source", {})
            if not isinstance(source, dict):
                source = {}
            source_bytes = int(source.get("bytes", 0) or 0)
            outputs = asset.get("outputs", [])
            if not isinstance(outputs, list):
                outputs = []
            for output in outputs:
                if not isinstance(output, dict):
                    continue
                kind = str(output.get("kind"))
                contract = OUTPUT_RECIPE_CONTRACTS.get(kind)
                if contract is None or contract.renderer is None or contract.extension != ".png":
                    continue
                geometry = preview_geometry(output, source_bytes)
                record = {
                    "asset_id": asset.get("id"),
                    "bank": bank,
                    "family": family["id"],
                    "manifest_path": rel(manifest_path),
                    "category": asset.get("category"),
                    "source_bytes": source_bytes,
                    "kind": kind,
                    "renderer": contract.renderer,
                    "path": output.get("path"),
                    **geometry,
                }
                if record["status"] == "invalid":
                    errors.append(f"{record['asset_id']}: {kind} {output.get('path')}: {record['reason']}")
                records.append(record)

    status_counts = Counter(str(record["status"]) for record in records)
    kind_counts: dict[str, Counter[str]] = defaultdict(Counter)
    family_counts: dict[str, Counter[str]] = defaultdict(Counter)
    dimension_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    known_records = []
    for record in records:
        kind_counts[str(record["kind"])][str(record["status"])] += 1
        family_counts[str(record["family"])][str(record["status"])] += 1
        if record["status"] == "known":
            key = f"{record['width']}x{record['height']}"
            dimension_counts[key] += 1
            known_records.append(record)
        else:
            reason_counts[str(record.get("reason", "unknown"))] += 1

    return {
        "schema": "earthbound-decomp.asset-output-preview-geometry.v1",
        "inputs": {
            "manifest_dir": rel(manifest_dir),
            "recipe_contract_module": "tools/asset_output_recipe_contracts.py",
        },
        "source_policy": {
            "contains_rom_derived_outputs": False,
            "static_geometry_only": True,
        },
        "totals": {
            "png_preview_recipes": len(records),
            "known_geometry_recipes": status_counts["known"],
            "requires_decode_recipes": status_counts["requires_decode"],
            "invalid_geometry_recipes": status_counts["invalid"],
            "distinct_known_dimensions": len(dimension_counts),
        },
        "status_counts": dict(sorted(status_counts.items())),
        "dimension_counts": dict(sorted(dimension_counts.items(), key=lambda item: (-item[1], item[0]))),
        "reason_counts": dict(sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))),
        "kind_status_counts": {kind: dict(sorted(counts.items())) for kind, counts in sorted(kind_counts.items())},
        "family_status_counts": {
            family["id"]: dict(sorted(family_counts[family["id"]].items()))
            for family in FAMILIES
            if family_counts[family["id"]]
        },
        "records": records,
        "errors": errors,
        "status": "ok" if not errors else "invalid",
    }


def compact_counts(counts: dict[str, int], limit: int = 5) -> str:
    if not counts:
        return "-"
    parts = []
    for key, value in list(counts.items())[:limit]:
        parts.append(f"`{key}` {value}")
    remaining = len(counts) - limit
    if remaining > 0:
        parts.append(f"+{remaining} more")
    return ", ".join(parts)


def render_markdown(report: dict[str, Any]) -> str:
    totals = report["totals"]
    lines = [
        "# Asset Output Preview Geometry",
        "",
        "Generated by `tools/build_asset_output_preview_geometry.py` from checked-in `asset-manifests/*.json` and the typed output recipe registry.",
        "",
        "This is a static geometry contract for PNG preview/render recipes. It contains no ROM-derived payloads; dimensions are predicted only when manifest metadata is sufficient without reading or decompressing a ROM.",
        "",
        "Generated asset-output reports are freshness-checked together with `tools/validate_asset_output_reports.py`.",
        "",
        "## Snapshot",
        "",
        f"- status: `{report['status']}`",
        f"- PNG preview/render recipes: `{totals['png_preview_recipes']}`",
        f"- statically known geometries: `{totals['known_geometry_recipes']}`",
        f"- geometries requiring ROM decode: `{totals['requires_decode_recipes']}`",
        f"- invalid geometries: `{totals['invalid_geometry_recipes']}`",
        f"- distinct known dimensions: `{totals['distinct_known_dimensions']}`",
        "",
        "## Known Dimension Mix",
        "",
        compact_counts(report["dimension_counts"], limit=12),
        "",
        "## Recipe Kind Geometry",
        "",
        "| Recipe kind | Known | Requires decode | Invalid |",
        "| --- | ---: | ---: | ---: |",
    ]
    for kind, counts in report["kind_status_counts"].items():
        lines.append(
            f"| `{kind}` | {counts.get('known', 0)} | {counts.get('requires_decode', 0)} | {counts.get('invalid', 0)} |"
        )

    lines.extend(
        [
            "",
            "## Family Geometry",
            "",
            "| Family | Known | Requires decode | Invalid |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    family_labels = {family["id"]: family["label"] for family in FAMILIES}
    for family_id, counts in report["family_status_counts"].items():
        lines.append(
            f"| {family_labels[family_id]} | {counts.get('known', 0)} | {counts.get('requires_decode', 0)} | {counts.get('invalid', 0)} |"
        )

    if report["reason_counts"]:
        lines.extend(["", "## Decode-Required Reasons", ""])
        for reason, count in report["reason_counts"].items():
            lines.append(f"- `{count}`: {reason}")

    if report["errors"]:
        lines.extend(["", "## Errors", ""])
        for error in report["errors"]:
            lines.append(f"- {error}")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build static preview geometry metadata for typed asset outputs.")
    parser.add_argument("--manifest-dir", default=str(DEFAULT_MANIFEST_DIR))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    args = parser.parse_args()

    report = build_report(Path(args.manifest_dir))

    json_out = Path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    markdown_out = Path(args.markdown_out)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(render_markdown(report), encoding="utf-8")

    totals = report["totals"]
    print(
        "asset output preview geometry: "
        f"{report['status']}, "
        f"{totals['known_geometry_recipes']}/{totals['png_preview_recipes']} known, "
        f"{totals['requires_decode_recipes']} require decode"
    )
    if report["errors"]:
        for error in report["errors"]:
            print(f"ERROR {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
