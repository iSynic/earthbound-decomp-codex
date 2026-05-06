from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import extract_assets
from asset_output_recipe_contracts import OUTPUT_RECIPE_CONTRACTS


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "build" / "asset-output-codec-validation"
DEFAULT_JSON_OUT = ROOT / "build" / "asset-output-codec-validation.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "asset-output-codec-validation.md"
PALETTE_RANGE = "C0:1000..C0:1020"
GRAPHICS_RANGE = "C0:2000..C0:2040"
ROM_SIZE = 0x30000


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def literal_lzhal(data: bytes) -> bytes:
    payload = bytearray()
    cursor = 0
    while cursor < len(data):
        chunk = data[cursor : cursor + 32]
        payload.append(len(chunk) - 1)
        payload.extend(chunk)
        cursor += len(chunk)
    payload.append(0xFF)
    return bytes(payload)


def snes_color(red5: int, green5: int, blue5: int) -> int:
    return (red5 & 0x1F) | ((green5 & 0x1F) << 5) | ((blue5 & 0x1F) << 10)


def palette_bytes(colors: int = 16) -> bytes:
    data = bytearray()
    for index in range(colors):
        raw = snes_color(index * 2, 31 - index, (index * 3) & 0x1F)
        data.extend(raw.to_bytes(2, "little"))
    return bytes(data)


def encode_2bpp_tile(seed: int = 0) -> bytes:
    data = bytearray()
    for y in range(8):
        low = 0
        high = 0
        for x in range(8):
            color = (x + y + seed) & 0x03
            bit = 7 - x
            low |= (color & 0x01) << bit
            high |= ((color >> 1) & 0x01) << bit
        data.extend((low, high))
    return bytes(data)


def encode_4bpp_tile(seed: int = 0) -> bytes:
    plane01 = bytearray()
    plane23 = bytearray()
    for y in range(8):
        p0 = p1 = p2 = p3 = 0
        for x in range(8):
            color = (x + y + seed) & 0x0F
            bit = 7 - x
            p0 |= (color & 0x01) << bit
            p1 |= ((color >> 1) & 0x01) << bit
            p2 |= ((color >> 2) & 0x01) << bit
            p3 |= ((color >> 3) & 0x01) << bit
        plane01.extend((p0, p1))
        plane23.extend((p2, p3))
    return bytes(plane01 + plane23)


def make_4bpp_tiles(count: int) -> bytes:
    return b"".join(encode_4bpp_tile(index) for index in range(count))


def make_2bpp_tiles(count: int) -> bytes:
    return b"".join(encode_2bpp_tile(index) for index in range(count))


def make_arrangement(width_tiles: int, height_tiles: int, tile_count: int) -> bytes:
    data = bytearray()
    for index in range(width_tiles * height_tiles):
        data.extend((index % tile_count).to_bytes(2, "little"))
    return bytes(data)


def source_ref(range_text: str, data: bytes) -> dict[str, Any]:
    return {
        "type": "rom-range",
        "range": range_text,
        "bytes": len(data),
        "sha1": hashlib.sha1(data).hexdigest(),
    }


def synthetic_rom(palette: bytes, graphics: bytes) -> bytes:
    rom = bytearray(ROM_SIZE)
    palette_offset = 0x1000
    graphics_offset = 0x2000
    rom[palette_offset : palette_offset + len(palette)] = palette
    rom[graphics_offset : graphics_offset + len(graphics)] = graphics
    return bytes(rom)


def output_cases() -> list[dict[str, Any]]:
    palette = palette_bytes()
    graphics_4bpp = make_4bpp_tiles(2)
    graphics_2bpp = make_2bpp_tiles(2)
    battle_sprite = make_4bpp_tiles(4)
    arrangement = make_arrangement(2, 2, tile_count=2)
    return [
        {
            "id": "raw-bytes",
            "data": b"raw fixture bytes",
            "spec": {"kind": "raw", "path": "raw.bin"},
        },
        {
            "id": "earthbound-lzhal",
            "data": literal_lzhal(b"decompressed fixture bytes"),
            "spec": {"kind": "earthbound_lzhal", "path": "decoded.bin"},
        },
        {
            "id": "snes-2bpp-tiles",
            "data": graphics_2bpp,
            "spec": {"kind": "snes_2bpp_tiles_png", "path": "tiles_2bpp.png", "columns": 2},
        },
        {
            "id": "snes-2bpp-tiles-trimmed",
            "data": graphics_2bpp + b"\x00",
            "spec": {
                "kind": "snes_2bpp_tiles_png",
                "path": "tiles_2bpp_trimmed.png",
                "columns": 2,
                "trim_trailing_bytes": 1,
            },
            "expected_metadata": {
                "tiles": 2,
                "trimmed_source_bytes": len(graphics_2bpp),
            },
        },
        {
            "id": "snes-4bpp-tiles",
            "data": graphics_4bpp,
            "spec": {"kind": "snes_4bpp_tiles_png", "path": "tiles_4bpp.png", "columns": 2},
        },
        {
            "id": "earthbound-lzhal-snes-4bpp-tiles",
            "data": literal_lzhal(graphics_4bpp),
            "spec": {"kind": "earthbound_lzhal_snes_4bpp_tiles_png", "path": "tiles_4bpp_lz.png", "columns": 2},
        },
        {
            "id": "snes-4bpp-palette-tiles",
            "data": graphics_4bpp,
            "spec": {
                "kind": "snes_4bpp_tiles_palette_png",
                "path": "tiles_4bpp_palette.png",
                "columns": 2,
                "colors": 16,
                "palette_source": source_ref(PALETTE_RANGE, palette),
            },
        },
        {
            "id": "earthbound-lzhal-snes-4bpp-palette-tiles",
            "data": literal_lzhal(graphics_4bpp),
            "spec": {
                "kind": "earthbound_lzhal_snes_4bpp_tiles_palette_png",
                "path": "tiles_4bpp_palette_lz.png",
                "columns": 2,
                "colors": 16,
                "palette_source": source_ref(PALETTE_RANGE, palette),
            },
        },
        {
            "id": "snes-palette-json",
            "data": palette,
            "spec": {"kind": "snes_palette_json", "path": "palette.json", "colors": 16},
        },
        {
            "id": "snes-palette-swatch",
            "data": palette,
            "spec": {"kind": "snes_palette_swatch_png", "path": "palette.png", "per_row": 8, "swatch": 4},
        },
        {
            "id": "earthbound-lzhal-snes-palette-json",
            "data": literal_lzhal(palette),
            "spec": {"kind": "earthbound_lzhal_snes_palette_json", "path": "palette_lz.json", "colors": 16},
        },
        {
            "id": "earthbound-lzhal-snes-palette-swatch",
            "data": literal_lzhal(palette),
            "spec": {"kind": "earthbound_lzhal_snes_palette_swatch_png", "path": "palette_lz.png", "per_row": 8, "swatch": 4},
        },
        {
            "id": "earthbound-lzhal-battle-bg-arrangement",
            "data": literal_lzhal(arrangement),
            "spec": {
                "kind": "earthbound_lzhal_battle_bg_arrangement_png",
                "path": "battle_bg.png",
                "width_tiles": 2,
                "height_tiles": 2,
                "bpp": 4,
                "colors": 16,
                "arrangement_id": 0,
                "graphics_id": 0,
                "palette_id": 0,
                "graphics_source": source_ref(GRAPHICS_RANGE, graphics_4bpp),
                "palette_source": source_ref(PALETTE_RANGE, palette),
            },
        },
        {
            "id": "earthbound-lzhal-battle-sprite",
            "data": literal_lzhal(battle_sprite),
            "spec": {
                "kind": "earthbound_lzhal_battle_sprite_png",
                "path": "battle_sprite.png",
                "width": 16,
                "height": 16,
                "colors": 16,
                "sprite_id": 0,
                "palette_id": 0,
                "palette_source": source_ref(PALETTE_RANGE, palette),
            },
        },
    ]


def verify_case(case: dict[str, Any], result: dict[str, Any], out_root: Path) -> list[str]:
    errors: list[str] = []
    kind = str(case["spec"]["kind"])
    contract = OUTPUT_RECIPE_CONTRACTS[kind]
    output_path = Path(str(result["path"]))
    if not output_path.is_file():
        return [f"{case['id']}: missing output file {output_path}"]
    output_data = output_path.read_bytes()
    if len(output_data) != int(result.get("bytes", -1)):
        errors.append(f"{case['id']}: reported byte count does not match file size")
    if hashlib.sha1(output_data).hexdigest() != result.get("sha1"):
        errors.append(f"{case['id']}: reported SHA-1 does not match file content")
    for field in contract.report_required_fields:
        if field not in result:
            errors.append(f"{case['id']}: missing report metadata field {field}")
    for field, expected in case.get("expected_metadata", {}).items():
        if result.get(field) != expected:
            errors.append(f"{case['id']}: expected {field}={expected!r}, got {result.get(field)!r}")
    try:
        output_path.resolve().relative_to(out_root.resolve())
    except ValueError:
        errors.append(f"{case['id']}: output escaped validation root")
    return errors


def reset_output_root(out_root: Path) -> None:
    build_root = (ROOT / "build").resolve()
    resolved = out_root.resolve()
    try:
        resolved.relative_to(build_root)
    except ValueError as exc:
        raise ValueError(f"validation output root must stay under {rel(build_root)}: {out_root}") from exc
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)


def run_validation(out_root: Path) -> dict[str, Any]:
    reset_output_root(out_root)

    palette = palette_bytes()
    graphics = make_4bpp_tiles(2)
    rom = synthetic_rom(palette, graphics)
    cases = output_cases()
    results = []
    errors: list[str] = []
    for case in cases:
        result = extract_assets.write_output(case["data"], out_root, case["spec"], rom)
        case_errors = verify_case(case, result, out_root)
        errors.extend(case_errors)
        results.append(
            {
                "id": case["id"],
                "kind": case["spec"]["kind"],
                "path": rel(Path(result["path"])),
                "bytes": result["bytes"],
                "sha1": result["sha1"],
                "metadata": {
                    key: value
                    for key, value in result.items()
                    if key not in {"kind", "path", "bytes", "sha1"}
                },
                "spec_options": {
                    key: value
                    for key, value in case["spec"].items()
                    if key not in {"kind", "path"}
                },
                "errors": case_errors,
            }
        )

    covered_kinds = sorted({str(item["kind"]) for item in results})
    missing_kinds = sorted(set(OUTPUT_RECIPE_CONTRACTS) - set(covered_kinds))
    if missing_kinds:
        errors.append(f"missing synthetic coverage for output kinds: {missing_kinds}")

    return {
        "schema": "earthbound-decomp.asset-output-codec-validation.v1",
        "source_policy": {
            "contains_rom_derived_outputs": False,
            "uses_synthetic_payloads_only": True,
        },
        "output_root": rel(out_root),
        "case_count": len(results),
        "trim_trailing_bytes_case_count": sum(
            1 for item in results if "trim_trailing_bytes" in item["spec_options"]
        ),
        "covered_output_kinds": covered_kinds,
        "missing_output_kinds": missing_kinds,
        "status": "ok" if not errors else "invalid",
        "errors": errors,
        "cases": results,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Asset Output Codec Validation",
        "",
        "Generated by `tools/validate_asset_output_codecs.py` from synthetic tile, palette, tilemap, and literal LZHAL payloads.",
        "",
        "This validates the offline renderer/decoder code paths behind typed output recipes without requiring a user-supplied ROM. Generated PNG/JSON/bin outputs stay under ignored `build/` paths.",
        "",
        "Generated asset-output reports are freshness-checked together with `tools/validate_asset_output_reports.py`.",
        "",
        "## Snapshot",
        "",
        f"- status: `{report['status']}`",
        f"- synthetic cases: `{report['case_count']}`",
        f"- trim-trailing-bytes cases: `{report['trim_trailing_bytes_case_count']}`",
        f"- output kinds covered: `{len(report['covered_output_kinds'])}`",
        f"- missing output kinds: `{len(report['missing_output_kinds'])}`",
        f"- output root: `{report['output_root']}`",
        "",
        "## Cases",
        "",
        "| Case | Recipe kind | Bytes | Spec options | Metadata keys |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for case in report["cases"]:
        metadata_keys = ", ".join(f"`{key}`" for key in sorted(case["metadata"])) or "-"
        spec_options = ", ".join(f"`{key}`" for key in sorted(case["spec_options"])) or "-"
        lines.append(
            f"| `{case['id']}` | `{case['kind']}` | {case['bytes']} | {spec_options} | {metadata_keys} |"
        )
    if report["errors"]:
        lines.extend(["", "## Errors", ""])
        for error in report["errors"]:
            lines.append(f"- {error}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate asset output codecs with synthetic fixtures.")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    args = parser.parse_args()

    report = run_validation(Path(args.out))
    json_out = Path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    markdown_out = Path(args.markdown_out)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(render_markdown(report), encoding="utf-8")

    print(
        "asset output codec validation: "
        f"{report['status']}, "
        f"{report['case_count']} cases, "
        f"{len(report['covered_output_kinds'])} kinds"
    )
    if report["errors"]:
        for error in report["errors"]:
            print(f"ERROR {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
