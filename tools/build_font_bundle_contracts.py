from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSON_OUT = ROOT / "build" / "font-bundle-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "font-bundle-contracts.md"
MANIFEST_PATHS = [
    ROOT / "asset-manifests" / "bank-e0-assets.json",
    ROOT / "asset-manifests" / "bank-e1-assets.json",
]
REF_FONT_DIR = ROOT / "refs" / "eb-decompile-4ef92" / "Fonts"
LEGACY_MAIN_FONT = ROOT / "refs" / "earthbound-disasm-legacy" / "Earthbound Decomp" / "EB" / "Tables" / "Fonts" / "MainFont.txt"


CORE_FONTS: list[dict[str, Any]] = [
    {
        "id": "font.main",
        "label": "Main text font",
        "metric_asset": "asset.e1.main_font_data",
        "graphics_asset": "asset.e1.main_font_gfx",
        "build_metric_path": "build/assets/e1/fonts/main.bin",
        "build_graphics_path": "build/assets/e1/fonts/main.gfx",
        "ref_width_id": 0,
        "ref_png": "0.png",
        "runtime_role": "Primary proportional text/window font.",
    },
    {
        "id": "font.mr_saturn",
        "label": "Mr. Saturn font",
        "metric_asset": "asset.e0.mrsaturn_font_data",
        "graphics_asset": "asset.e0.mrsaturn_font_gfx",
        "build_metric_path": "build/assets/e0/fonts/mrsaturn.bin",
        "build_graphics_path": "build/assets/e0/fonts/mrsaturn.gfx",
        "ref_width_id": 1,
        "ref_png": "1.png",
        "runtime_role": "Alternate proportional font selected by script/localization font commands.",
    },
    {
        "id": "font.large",
        "label": "Large font",
        "metric_asset": "asset.e1.large_font_data",
        "graphics_asset": "asset.e1.large_font_gfx",
        "build_metric_path": "build/assets/e1/fonts/large.bin",
        "build_graphics_path": "build/assets/e1/fonts/large.gfx",
        "ref_width_id": 2,
        "ref_png": "2.png",
        "runtime_role": "Large proportional UI font.",
    },
    {
        "id": "font.battle",
        "label": "Battle font",
        "metric_asset": "asset.e1.battle_font_data",
        "graphics_asset": "asset.e1.battle_font_gfx",
        "build_metric_path": "build/assets/e1/fonts/battle.bin",
        "build_graphics_path": "build/assets/e1/fonts/battle.gfx",
        "ref_width_id": 3,
        "ref_png": "3.png",
        "runtime_role": "Fixed-width battle text font; shares its first 96 metric bytes with the tiny font.",
    },
    {
        "id": "font.tiny",
        "label": "Tiny font",
        "metric_asset": "asset.e1.tiny_font_data",
        "graphics_asset": "asset.e1.tiny_font_gfx",
        "build_metric_path": "build/assets/e1/fonts/tiny.bin",
        "build_graphics_path": "build/assets/e1/fonts/tiny.gfx",
        "ref_width_id": 4,
        "ref_png": "4.png",
        "runtime_role": "Compact fixed-width UI font; shares its first 96 metric bytes with the battle font.",
    },
]


SUPPORT_FONTS: list[dict[str, Any]] = [
    {
        "id": "font.romaji",
        "label": "MOTHER 2 romaji font",
        "graphics_asset": "asset.e0.mother2_romaji_font",
        "palette_asset": None,
        "build_graphics_path": "build/assets/e0/fonts/romaji.gfx",
        "runtime_role": "Raw romaji glyph payload without a paired checked metric table.",
        "status": "graphics-only",
    },
    {
        "id": "font.staff_credits",
        "label": "Staff credits font",
        "graphics_asset": "asset.e1.staff_credits_font_graphics",
        "palette_asset": "asset.e1.staff_credits_font_palette",
        "build_graphics_path": "build/assets/e1/ending/credits_font.gfx",
        "runtime_role": "Ending/staff credits scene font with a dedicated 16-byte palette.",
        "status": "scene-font-with-palette",
        "ref_png": "credits.png",
    },
]


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_assets() -> dict[str, dict[str, Any]]:
    assets: dict[str, dict[str, Any]] = {}
    for manifest_path in MANIFEST_PATHS:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for asset in manifest["assets"]:
            assets[str(asset["id"])] = asset
    return assets


def load_width_ref(ref_id: int) -> list[int]:
    path = REF_FONT_DIR / f"{ref_id}_widths.yml"
    if not path.exists():
        raise FileNotFoundError(f"Missing font width ref: {rel(path)}")
    values: list[int] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, value = line.split(":", 1)
        index = int(key.strip())
        if index != len(values):
            raise ValueError(f"Non-contiguous width index in {rel(path)}: {index}")
        values.append(int(value.strip()))
    if len(values) != 128:
        raise ValueError(f"Expected 128 width entries in {rel(path)}, got {len(values)}")
    return values


def load_metric_bytes(path_text: str) -> list[int]:
    path = ROOT / path_text
    if not path.exists():
        raise FileNotFoundError(f"Missing local font metric bytes: {rel(path)}")
    data = list(path.read_bytes())
    if len(data) != 96:
        raise ValueError(f"Expected 96 metric bytes in {rel(path)}, got {len(data)}")
    return data


def local_file_size(path_text: str) -> int | None:
    path = ROOT / path_text
    if not path.exists():
        return None
    return path.stat().st_size


def source_range(asset: dict[str, Any] | None) -> str | None:
    if not asset:
        return None
    source = asset.get("source", {})
    if not isinstance(source, dict):
        return None
    return str(source.get("range"))


def source_bytes(asset: dict[str, Any] | None) -> int:
    if not asset:
        return 0
    source = asset.get("source", {})
    if not isinstance(source, dict):
        return 0
    return int(source.get("bytes", 0) or 0)


def output_kinds(asset: dict[str, Any] | None) -> list[str]:
    if not asset:
        return []
    outputs = asset.get("outputs", [])
    if not isinstance(outputs, list):
        return []
    return [str(output.get("kind", "unknown")) for output in outputs if isinstance(output, dict)]


def width_stats(widths: list[int]) -> dict[str, Any]:
    counts = Counter(widths)
    printable = [value for value in widths if value != 255]
    return {
        "entry_count": len(widths),
        "printable_count": len(printable),
        "sentinel_ff_count": counts[255],
        "min_printable_width": min(printable) if printable else None,
        "max_printable_width": max(printable) if printable else None,
        "width_counts": dict(sorted(counts.items())),
    }


def read_legacy_main_font_map() -> dict[str, Any]:
    if not LEGACY_MAIN_FONT.exists():
        return {"path": rel(LEGACY_MAIN_FONT), "entries": 0, "sample": []}
    entries = []
    for raw_line in LEGACY_MAIN_FONT.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        character, code = line.rsplit("=", 1)
        entries.append({"character": character, "code": f"${int(code, 16):02X}"})
    return {"path": rel(LEGACY_MAIN_FONT), "entries": len(entries), "sample": entries[:12]}


def build_core_font(config: dict[str, Any], assets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    metric_asset = assets.get(config["metric_asset"])
    graphics_asset = assets.get(config["graphics_asset"])
    if metric_asset is None or graphics_asset is None:
        raise KeyError(f"Missing core font assets for {config['id']}")

    metrics = load_metric_bytes(config["build_metric_path"])
    ref_widths = load_width_ref(int(config["ref_width_id"]))
    if metrics != ref_widths[:96]:
        raise ValueError(f"{config['id']} metric bytes do not match EBDecomp first 96 widths")

    graphics_size = local_file_size(config["build_graphics_path"])
    if graphics_size is None:
        raise FileNotFoundError(f"Missing local font graphics bytes: {config['build_graphics_path']}")
    if graphics_size % 32 != 0:
        raise ValueError(f"Expected 4bpp graphics size to be divisible by 32: {config['build_graphics_path']}")

    ref_png = REF_FONT_DIR / config["ref_png"]
    if not ref_png.exists():
        raise FileNotFoundError(f"Missing EBDecomp font PNG ref: {rel(ref_png)}")

    return {
        "id": config["id"],
        "label": config["label"],
        "runtime_role": config["runtime_role"],
        "metric_asset": config["metric_asset"],
        "metric_range": source_range(metric_asset),
        "metric_bytes": source_bytes(metric_asset),
        "graphics_asset": config["graphics_asset"],
        "graphics_range": source_range(graphics_asset),
        "graphics_source_bytes": source_bytes(graphics_asset),
        "graphics_output_bytes": graphics_size,
        "graphics_tile_count_4bpp": graphics_size // 32,
        "output_kinds": sorted(set(output_kinds(metric_asset) + output_kinds(graphics_asset))),
        "ref_width_id": config["ref_width_id"],
        "ref_width_path": rel(REF_FONT_DIR / f"{config['ref_width_id']}_widths.yml"),
        "ref_png": rel(ref_png),
        "metric_bytes_match_ref_first_96": True,
        "ref_width_stats": width_stats(ref_widths),
        "metric_stats": width_stats(metrics),
        "metric_bytes_first_16": metrics[:16],
        "ref_tail_96_to_127": ref_widths[96:128],
    }


def build_support_font(config: dict[str, Any], assets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    graphics_asset = assets.get(config["graphics_asset"])
    palette_asset = assets.get(config["palette_asset"]) if config.get("palette_asset") else None
    if graphics_asset is None:
        raise KeyError(f"Missing support font graphics asset for {config['id']}")
    output_size = local_file_size(config["build_graphics_path"])
    result = {
        "id": config["id"],
        "label": config["label"],
        "status": config["status"],
        "runtime_role": config["runtime_role"],
        "graphics_asset": config["graphics_asset"],
        "graphics_range": source_range(graphics_asset),
        "graphics_source_bytes": source_bytes(graphics_asset),
        "graphics_output_bytes": output_size,
        "graphics_tile_count_4bpp": output_size // 32 if output_size is not None and output_size % 32 == 0 else None,
        "palette_asset": config.get("palette_asset"),
        "palette_range": source_range(palette_asset),
        "palette_bytes": source_bytes(palette_asset),
        "output_kinds": sorted(set(output_kinds(graphics_asset) + output_kinds(palette_asset))),
    }
    if config.get("ref_png"):
        ref_png = REF_FONT_DIR / str(config["ref_png"])
        result["ref_png"] = rel(ref_png) if ref_png.exists() else None
    return result


def build_contract() -> dict[str, Any]:
    assets = load_assets()
    core_fonts = [build_core_font(config, assets) for config in CORE_FONTS]
    support_fonts = [build_support_font(config, assets) for config in SUPPORT_FONTS]

    return {
        "schema": "earthbound-decomp.font-bundle-contracts.v1",
        "scope": "E0/E1 metric-backed text fonts, graphics-only romaji font, and staff credits scene font",
        "inputs": {
            "manifests": [rel(path) for path in MANIFEST_PATHS],
            "ebdecomp_fonts": rel(REF_FONT_DIR),
            "legacy_main_font_map": rel(LEGACY_MAIN_FONT),
        },
        "generated_json": rel(DEFAULT_JSON_OUT),
        "tracked_markdown": rel(DEFAULT_MARKDOWN_OUT),
        "totals": {
            "core_fonts": len(core_fonts),
            "support_fonts": len(support_fonts),
            "metric_bytes": sum(font["metric_bytes"] for font in core_fonts),
            "graphics_output_bytes": sum(
                int(font["graphics_output_bytes"] or 0) for font in core_fonts + support_fonts
            ),
            "graphics_tiles_4bpp": sum(
                int(font["graphics_tile_count_4bpp"] or 0) for font in core_fonts + support_fonts
            ),
        },
        "validation": {
            "core_font_metric_bytes_are_96_each": all(font["metric_bytes"] == 96 for font in core_fonts),
            "core_font_metric_bytes_match_ebdecomp_first_96_widths": all(
                font["metric_bytes_match_ref_first_96"] for font in core_fonts
            ),
            "core_font_graphics_outputs_are_4bpp_tile_aligned": all(
                int(font["graphics_output_bytes"]) % 32 == 0 for font in core_fonts
            ),
            "battle_and_tiny_share_first_96_metric_bytes": load_metric_bytes("build/assets/e1/fonts/battle.bin")
            == load_metric_bytes("build/assets/e1/fonts/tiny.bin"),
            "ebdecomp_png_refs_exist_for_all_core_fonts": all((ROOT / font["ref_png"]).exists() for font in core_fonts),
        },
        "core_fonts": core_fonts,
        "support_fonts": support_fonts,
        "legacy_main_font_map": read_legacy_main_font_map(),
        "runtime_context": [
            {
                "source": "notes/text-window-rendering-primitives-c1078d-c10d7c.md",
                "role": "C4:3E31 and C4:4FF3 use C3:F054-adjacent width-table selectors for text measurement; these E0/E1 font metric payloads provide checked asset-level width tables for concrete fonts.",
            },
            {
                "source": "notes/localization-authoring-command-frontier.md",
                "role": "Recovered localization commands include standard-font and Mr. Saturn font commands, matching the need to keep font bundles semantically named.",
            },
            {
                "source": "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Tables/Fonts/MainFont.txt",
                "role": "Legacy character-code map gives a public-facing character/code bridge for the main font.",
            },
        ],
        "open_questions": [
            "Tie each runtime font selector value to these bundle ids from caller-side descriptor fields.",
            "Promote romaji and staff-credits fonts to richer contracts if caller-specific metrics or character maps are found.",
            "Resolve the non-255 special tail entries in EBDecomp battle/tiny width refs 3 and 4; local ROM metric payloads only contain the first 96 bytes.",
        ],
    }


def compact_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "-"
    return ", ".join(f"`{key}` {value}" for key, value in sorted(counts.items(), key=lambda item: int(item[0])))


def render_markdown(contract: dict[str, Any]) -> str:
    totals = contract["totals"]
    lines = [
        "# Font Bundle Contracts",
        "",
        "Generated by `tools/build_font_bundle_contracts.py`. This joins E0/E1 font metric assets, glyph graphics assets, local user-ROM-derived outputs, and ignored EBDecomp font refs into portable font bundles.",
        "",
        "No ROM-derived font graphics or palette payload files are checked in by this report.",
        "",
        "## Snapshot",
        "",
        f"- metric-backed core fonts: `{totals['core_fonts']}`",
        f"- support/scene fonts: `{totals['support_fonts']}`",
        f"- core metric bytes: `{totals['metric_bytes']}`",
        f"- generated local graphics bytes covered: `{totals['graphics_output_bytes']}`",
        f"- 4bpp graphics tiles covered: `{totals['graphics_tiles_4bpp']}`",
        "",
        "## Validation",
        "",
    ]
    for key, value in contract["validation"].items():
        lines.append(f"- `{key}`: `{str(value).lower()}`")

    lines.extend(["", "## Core Font Bundles", ""])
    lines.append(
        "| Font | Metric asset | Metric range | GFX asset | GFX range | 4bpp tiles | EBDecomp widths | Width min/max | Sentinels | Role |"
    )
    lines.append("| --- | --- | --- | --- | --- | ---: | --- | --- | ---: | --- |")
    for font in contract["core_fonts"]:
        stats = font["metric_stats"]
        lines.append(
            "| {label} | `{metric}` | `{metric_range}` | `{gfx}` | `{gfx_range}` | {tiles} | `{ref}` | {min_width}..{max_width} | {sentinels} | {role} |".format(
                label=font["label"],
                metric=font["metric_asset"],
                metric_range=font["metric_range"],
                gfx=font["graphics_asset"],
                gfx_range=font["graphics_range"],
                tiles=font["graphics_tile_count_4bpp"],
                ref=font["ref_width_path"],
                min_width=stats["min_printable_width"],
                max_width=stats["max_printable_width"],
                sentinels=font["ref_width_stats"]["sentinel_ff_count"],
                role=font["runtime_role"],
            )
        )

    lines.extend(["", "## Metric Details", ""])
    for font in contract["core_fonts"]:
        lines.append(f"### {font['label']}")
        lines.append("")
        lines.append(f"- bundle id: `{font['id']}`")
        lines.append(f"- EBDecomp PNG ref: `{font['ref_png']}`")
        lines.append(f"- first 16 metric bytes: `{', '.join(str(value) for value in font['metric_bytes_first_16'])}`")
        lines.append(f"- first-96 width counts: {compact_counts(font['metric_stats']['width_counts'])}")
        tail = ", ".join(str(value) for value in font["ref_tail_96_to_127"])
        lines.append(f"- EBDecomp width ref tail 96..127: `{tail}`")
        lines.append("")

    lines.extend(["## Support Fonts", ""])
    lines.append("| Font | Status | Graphics asset | Graphics range | Palette asset | Palette range | Output bytes | 4bpp tiles | Role |")
    lines.append("| --- | --- | --- | --- | --- | --- | ---: | ---: | --- |")
    for font in contract["support_fonts"]:
        lines.append(
            "| {label} | `{status}` | `{graphics}` | `{graphics_range}` | {palette} | {palette_range} | {output_bytes} | {tiles} | {role} |".format(
                label=font["label"],
                status=font["status"],
                graphics=font["graphics_asset"],
                graphics_range=font["graphics_range"],
                palette=f"`{font['palette_asset']}`" if font.get("palette_asset") else "-",
                palette_range=f"`{font['palette_range']}`" if font.get("palette_range") else "-",
                output_bytes=font["graphics_output_bytes"],
                tiles=font["graphics_tile_count_4bpp"] if font["graphics_tile_count_4bpp"] is not None else "-",
                role=font["runtime_role"],
            )
        )

    legacy = contract["legacy_main_font_map"]
    lines.extend(
        [
            "",
            "## Character-Code Evidence",
            "",
            f"- legacy main-font character map: `{legacy['path']}`",
            f"- parsed entries: `{legacy['entries']}`",
        ]
    )
    if legacy["sample"]:
        sample = ", ".join(f"`{item['character'] or 'space'}` -> `{item['code']}`" for item in legacy["sample"])
        lines.append(f"- sample: {sample}")

    lines.extend(["", "## Runtime Context", ""])
    for item in contract["runtime_context"]:
        lines.append(f"- `{item['source']}`: {item['role']}")

    lines.extend(["", "## Open Questions", ""])
    for question in contract["open_questions"]:
        lines.append(f"- {question}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build E0/E1 font bundle contracts.")
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    args = parser.parse_args()

    contract = build_contract()
    json_out = Path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

    markdown_out = Path(args.markdown_out)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(render_markdown(contract), encoding="utf-8")

    totals = contract["totals"]
    print(
        "font bundles: "
        f"{totals['core_fonts']} core, "
        f"{totals['support_fonts']} support, "
        f"{totals['graphics_tiles_4bpp']} tiles"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
