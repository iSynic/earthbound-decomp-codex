from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSON_OUT = ROOT / "build" / "battle-background-scene-bundles.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "battle-background-scene-bundles.md"

EB_SRC = ROOT / "refs" / "ebsrc-main" / "ebsrc-main"
BG_DIR = EB_SRC / "src" / "data" / "battle" / "backgrounds"
BATTLE_DIR = EB_SRC / "src" / "data" / "battle"
CONSTANTS_PATH = EB_SRC / "include" / "constants" / "battlebgs.asm"

POINTER_TABLES = {
    "graphics": BG_DIR / "graphics_pointers.asm",
    "arrangement": BG_DIR / "arrangement_pointers.asm",
    "palette": BG_DIR / "palette_pointers.asm",
}
CONFIG_PATH = BG_DIR / "config_table.asm"
SCROLLING_PATH = BG_DIR / "scrolling_table.asm"
DISTORTION_PATH = BG_DIR / "distortion_table.asm"
BACKGROUND_LAYER_TABLE_PATH = BATTLE_DIR / "background_layer_table.asm"
LOAD_BATTLE_BG_PATH = EB_SRC / "src" / "battle" / "load_battlebg.asm"
MANIFEST_PATHS = [ROOT / "asset-manifests" / f"bank-{bank}-assets.json" for bank in ["ca", "cb"]]

CONFIG_FIELDS = [
    "graphics",
    "palette",
    "bpp",
    "unknown_palette_shift_style",
    "palette_cycle_1_first",
    "palette_cycle_1_last",
    "palette_cycle_2_first",
    "palette_cycle_2_last",
    "palette_change_speed",
    "scrolling_movement_1",
    "scrolling_movement_2",
    "scrolling_movement_3",
    "scrolling_movement_4",
    "distortion_style_1",
    "distortion_style_2",
    "distortion_style_3",
    "distortion_style_4",
]

SCROLLING_FIELDS = [
    "duration",
    "horizontal_movement",
    "vertical_movement",
    "horizontal_acceleration",
    "vertical_acceleration",
]

DISTORTION_FIELDS = [
    "duration",
    "style",
    "ripple_frequency",
    "ripple_amplitude",
    "unknown",
    "compression_rate",
    "ripple_frequency_acceleration",
    "ripple_amplitude_acceleration",
    "speed",
    "compression_rate_acceleration",
]


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def parse_numeric(token: str) -> int:
    token = token.strip()
    if token.startswith("$"):
        return int(token[1:], 16)
    if token.startswith("%"):
        return int(token[1:], 2)
    return int(token, 10)


def split_directive_args(line: str, directive: str) -> list[str]:
    code = line.split(";", 1)[0]
    match = re.search(rf"\.{directive}\s+(.+)", code, flags=re.IGNORECASE)
    if not match:
        return []
    return [arg.strip() for arg in match.group(1).split(",") if arg.strip()]


def parse_pointer_table(path: Path, kind: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        args = split_directive_args(line, "DWORD")
        for label in args:
            match = re.search(r"_(\d+)$", label)
            index = int(match.group(1)) if match else len(entries)
            entries.append({"index": index, "label": label, "kind": kind})
    return entries


def parse_config_table(path: Path) -> list[dict[str, Any]]:
    values: list[int] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        for arg in split_directive_args(line, "BYTE"):
            values.append(parse_numeric(arg))
    if len(values) % len(CONFIG_FIELDS):
        raise ValueError(f"{rel(path)} does not divide into {len(CONFIG_FIELDS)}-byte config rows")

    rows: list[dict[str, Any]] = []
    for index in range(0, len(values), len(CONFIG_FIELDS)):
        raw = values[index : index + len(CONFIG_FIELDS)]
        row = dict(zip(CONFIG_FIELDS, raw, strict=True))
        row["index"] = index // len(CONFIG_FIELDS)
        row["scrolling_movements"] = [row[f"scrolling_movement_{i}"] for i in range(1, 5)]
        row["distortion_styles"] = [row[f"distortion_style_{i}"] for i in range(1, 5)]
        rows.append(row)
    return rows


def parse_word_rows(path: Path, fields: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        args = split_directive_args(line, "WORD")
        if not args:
            continue
        if len(args) != len(fields):
            raise ValueError(f"{rel(path)} row has {len(args)} values; expected {len(fields)}")
        row = {field: parse_numeric(arg) for field, arg in zip(fields, args, strict=True)}
        row["index"] = len(rows)
        rows.append(row)
    return rows


def parse_distortion_rows(path: Path) -> list[dict[str, Any]]:
    values: list[Any] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        for directive in ["WORD", "BYTE"]:
            for arg in split_directive_args(line, directive):
                if arg.startswith("DISTORTION_STYLE::"):
                    values.append(arg.split("::", 1)[1])
                else:
                    values.append(parse_numeric(arg))
    if len(values) % len(DISTORTION_FIELDS):
        raise ValueError(f"{rel(path)} does not divide into {len(DISTORTION_FIELDS)}-field distortion rows")

    rows: list[dict[str, Any]] = []
    for index in range(0, len(values), len(DISTORTION_FIELDS)):
        raw = values[index : index + len(DISTORTION_FIELDS)]
        row = dict(zip(DISTORTION_FIELDS, raw, strict=True))
        row["index"] = index // len(DISTORTION_FIELDS)
        rows.append(row)
    return rows


def parse_battlebg_layer_constants(path: Path) -> dict[str, int]:
    constants: dict[str, int] = {}
    inside = False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == ".ENUM BATTLEBG_LAYER":
            inside = True
            continue
        if inside and stripped == ".ENDENUM":
            break
        if not inside:
            continue
        match = re.match(r"([A-Z0-9_]+)\s*=\s*(\d+)", stripped)
        if match:
            constants[match.group(1)] = int(match.group(2))
    return constants


def parse_background_layer_table(path: Path, constants: dict[str, int]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        refs = re.findall(r"BATTLEBG_LAYER::([A-Z0-9_]+)", line)
        if not refs:
            continue
        comment = re.search(r";\s*(\d+)", line)
        entry_index = int(comment.group(1)) if comment else len(entries)
        resolved = []
        for layer_name in refs:
            layer_index = constants[layer_name]
            resolved.append(
                {
                    "label": layer_name,
                    "layer_config_index": layer_index,
                    "enabled": layer_index != 0,
                }
            )
        entries.append({"battle_entry_index": entry_index, "layers": resolved})
    return entries


def load_asset_title_map() -> dict[str, dict[str, Any]]:
    by_title: dict[str, dict[str, Any]] = {}
    for manifest_path in MANIFEST_PATHS:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        bank = manifest_path.stem.split("-")[1].upper()
        for asset in manifest["assets"]:
            source = asset.get("source", {})
            if not isinstance(source, dict):
                source = {}
            by_title[str(asset["title"])] = {
                "id": asset["id"],
                "bank": bank,
                "range": source.get("range"),
                "bytes": source.get("bytes"),
            }
    return by_title


def join_pointer_assets(
    pointer_entries: list[dict[str, Any]], by_title: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    joined = []
    for entry in pointer_entries:
        asset = by_title.get(entry["label"])
        joined.append({**entry, "asset": asset})
    return joined


def asset_ref(joined: list[dict[str, Any]], index: int) -> dict[str, Any] | None:
    by_index = {entry["index"]: entry.get("asset") for entry in joined}
    return by_index.get(index)


def build_layer_configs(
    config_rows: list[dict[str, Any]],
    graphics: list[dict[str, Any]],
    arrangements: list[dict[str, Any]],
    palettes: list[dict[str, Any]],
    scrolling_rows: list[dict[str, Any]],
    distortion_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    scrolling_count = len(scrolling_rows)
    distortion_count = len(distortion_rows)
    layers = []
    for row in config_rows:
        graphics_index = int(row["graphics"])
        palette_index = int(row["palette"])
        arrangement_index = graphics_index
        scroll_refs = [
            {"index": ref, "valid": ref < scrolling_count} for ref in row["scrolling_movements"]
        ]
        distortion_refs = [
            {"index": ref, "valid": ref < distortion_count} for ref in row["distortion_styles"]
        ]
        layers.append(
            {
                "layer_config_index": row["index"],
                "graphics_index": graphics_index,
                "arrangement_index": arrangement_index,
                "palette_index": palette_index,
                "bpp": row["bpp"],
                "unknown_palette_shift_style": row["unknown_palette_shift_style"],
                "palette_cycle_1": [row["palette_cycle_1_first"], row["palette_cycle_1_last"]],
                "palette_cycle_2": [row["palette_cycle_2_first"], row["palette_cycle_2_last"]],
                "palette_change_speed": row["palette_change_speed"],
                "scrolling_movements": scroll_refs,
                "distortion_styles": distortion_refs,
                "assets": {
                    "graphics": asset_ref(graphics, graphics_index),
                    "arrangement": asset_ref(arrangements, arrangement_index),
                    "palette": asset_ref(palettes, palette_index),
                },
            }
        )
    return layers


def attach_entry_layers(
    battle_entries: list[dict[str, Any]], layer_configs: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_layer = {layer["layer_config_index"]: layer for layer in layer_configs}
    joined = []
    for entry in battle_entries:
        layers = []
        for layer in entry["layers"]:
            config = by_layer.get(layer["layer_config_index"])
            layers.append({**layer, "config": config if layer["enabled"] else None})
        joined.append({**entry, "layers": layers})
    return joined


def counter_from_refs(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for item in items:
        counts[str(item[key])] += 1
    return dict(sorted(counts.items(), key=lambda entry: (int(entry[0]) if entry[0].isdigit() else entry[0])))


def build_contract() -> dict[str, Any]:
    by_title = load_asset_title_map()
    pointers = {kind: parse_pointer_table(path, kind) for kind, path in POINTER_TABLES.items()}
    graphics = join_pointer_assets(pointers["graphics"], by_title)
    arrangements = join_pointer_assets(pointers["arrangement"], by_title)
    palettes = join_pointer_assets(pointers["palette"], by_title)
    config_rows = parse_config_table(CONFIG_PATH)
    scrolling_rows = parse_word_rows(SCROLLING_PATH, SCROLLING_FIELDS)
    distortion_rows = parse_distortion_rows(DISTORTION_PATH)
    constants = parse_battlebg_layer_constants(CONSTANTS_PATH)
    battle_entries = parse_background_layer_table(BACKGROUND_LAYER_TABLE_PATH, constants)
    layer_configs = build_layer_configs(
        config_rows,
        graphics,
        arrangements,
        palettes,
        scrolling_rows,
        distortion_rows,
    )
    joined_entries = attach_entry_layers(battle_entries, layer_configs)

    used_layer_indices = sorted(
        {
            layer["layer_config_index"]
            for entry in joined_entries
            for layer in entry["layers"]
            if layer["enabled"]
        }
    )
    unmatched_layer_refs = [
        layer["layer_config_index"]
        for entry in joined_entries
        for layer in entry["layers"]
        if layer["enabled"] and layer["config"] is None
    ]
    invalid_scroll_refs = [
        (layer["layer_config_index"], ref["index"])
        for layer in layer_configs
        for ref in layer["scrolling_movements"]
        if not ref["valid"]
    ]
    invalid_distortion_refs = [
        (layer["layer_config_index"], ref["index"])
        for layer in layer_configs
        for ref in layer["distortion_styles"]
        if not ref["valid"]
    ]

    component_match_counts = {
        "graphics_pointer_assets": sum(1 for entry in graphics if entry.get("asset")),
        "arrangement_pointer_assets": sum(1 for entry in arrangements if entry.get("asset")),
        "palette_pointer_assets": sum(1 for entry in palettes if entry.get("asset")),
    }

    return {
        "schema": "earthbound-decomp.battle-background-scene-bundles.v1",
        "scope": "CA/CB battle-background scene-layer joins derived from ebsrc tables and checked-in asset manifests",
        "inputs": [
            rel(CONFIG_PATH),
            rel(SCROLLING_PATH),
            rel(DISTORTION_PATH),
            rel(BACKGROUND_LAYER_TABLE_PATH),
            rel(LOAD_BATTLE_BG_PATH),
            rel(CONSTANTS_PATH),
            *[rel(path) for path in POINTER_TABLES.values()],
            *[rel(path) for path in MANIFEST_PATHS],
        ],
        "generated_json": rel(DEFAULT_JSON_OUT),
        "tracked_markdown": rel(DEFAULT_MARKDOWN_OUT),
        "totals": {
            "graphics_pointer_entries": len(graphics),
            "arrangement_pointer_entries": len(arrangements),
            "palette_pointer_entries": len(palettes),
            "layer_config_rows": len(layer_configs),
            "scrolling_rows": len(scrolling_rows),
            "distortion_rows": len(distortion_rows),
            "battle_entry_rows": len(joined_entries),
            "used_layer_configs": len(used_layer_indices),
            "battle_entries_with_two_layers": sum(
                1
                for entry in joined_entries
                if sum(1 for layer in entry["layers"] if layer["enabled"]) == 2
            ),
            **component_match_counts,
        },
        "validation": {
            "all_used_battle_layers_have_config_rows": not unmatched_layer_refs,
            "unmatched_layer_refs": unmatched_layer_refs,
            "all_scroll_refs_valid": not invalid_scroll_refs,
            "invalid_scroll_refs": invalid_scroll_refs,
            "all_distortion_refs_valid": not invalid_distortion_refs,
            "invalid_distortion_refs": invalid_distortion_refs,
            "pointer_assets_fully_matched": {
                "graphics": component_match_counts["graphics_pointer_assets"] == len(graphics),
                "arrangements": component_match_counts["arrangement_pointer_assets"] == len(arrangements),
                "palettes": component_match_counts["palette_pointer_assets"] == len(palettes),
            },
        },
        "layer_config_usage": {
            "used_indices": used_layer_indices,
            "unused_indices": [layer["layer_config_index"] for layer in layer_configs if layer["layer_config_index"] not in used_layer_indices],
            "graphics_index_counts": counter_from_refs(layer_configs, "graphics_index"),
            "palette_index_counts": counter_from_refs(layer_configs, "palette_index"),
            "bpp_counts": counter_from_refs(layer_configs, "bpp"),
        },
        "component_tables": {
            "graphics": graphics,
            "arrangements": arrangements,
            "palettes": palettes,
            "scrolling": scrolling_rows,
            "distortion": distortion_rows,
        },
        "layer_configs": layer_configs,
        "battle_entries": joined_entries,
        "known_semantics": [
            "LOAD_BATTLE_BG receives layer 1 in A, layer 2 in X, and letterbox style in Y.",
            "Each enabled battle entry layer is a BATTLEBG_LAYER enum value that indexes BG_DATA_TABLE.",
            "BG_DATA_TABLE row byte 0 selects both graphics and arrangement pointer indices in LOAD_BATTLE_BG.",
            "BG_DATA_TABLE row byte 1 selects BATTLEBG_PALETTE_POINTERS.",
            "Row bytes 9-12 select up to four BG_SCROLLING_TABLE movement rows.",
            "Row bytes 13-16 select up to four BG_DISTORTION_TABLE rows.",
        ],
        "open_questions": [
            "Field byte 3 remains named unknown_palette_shift_style until the palette-effect caller is exhaustively named.",
            "Layer enum labels from ebsrc are mostly UNKNOWN###; future polish can alias visible scenes without changing this numeric contract.",
            "The checked-in contract joins table indices to asset manifests, but actual PNG/rendered previews are still generated locally from a user-supplied ROM.",
        ],
    }


def summarize_bool(value: bool) -> str:
    return "yes" if value else "no"


def render_asset(asset: dict[str, Any] | None) -> str:
    if not asset:
        return "-"
    return f"`{asset['id']}`"


def render_markdown(contract: dict[str, Any]) -> str:
    totals = contract["totals"]
    validation = contract["validation"]
    lines = [
        "# Battle Background Scene Bundles",
        "",
        "Generated by `tools/build_battle_background_scene_bundles.py` from checked-in ebsrc tables and the CA/CB asset manifests.",
        "",
        "No ROM-derived payloads or rendered reference images are checked in by this report.",
        "",
        "## Snapshot",
        "",
        f"- graphics pointer entries: `{totals['graphics_pointer_entries']}` (`{totals['graphics_pointer_assets']}` matched to assets)",
        f"- arrangement pointer entries: `{totals['arrangement_pointer_entries']}` (`{totals['arrangement_pointer_assets']}` matched to assets)",
        f"- palette pointer entries: `{totals['palette_pointer_entries']}` (`{totals['palette_pointer_assets']}` matched to assets)",
        f"- layer config rows: `{totals['layer_config_rows']}`",
        f"- scrolling rows: `{totals['scrolling_rows']}`",
        f"- distortion rows: `{totals['distortion_rows']}`",
        f"- battle entry rows: `{totals['battle_entry_rows']}`",
        f"- used layer configs: `{totals['used_layer_configs']}`",
        f"- battle entries with two enabled layers: `{totals['battle_entries_with_two_layers']}`",
        "",
        "## Validation",
        "",
        f"- all used battle layers have config rows: `{summarize_bool(validation['all_used_battle_layers_have_config_rows'])}`",
        f"- all scrolling references are in range: `{summarize_bool(validation['all_scroll_refs_valid'])}`",
        f"- all distortion references are in range: `{summarize_bool(validation['all_distortion_refs_valid'])}`",
        f"- pointer assets fully matched: graphics `{summarize_bool(validation['pointer_assets_fully_matched']['graphics'])}`, arrangements `{summarize_bool(validation['pointer_assets_fully_matched']['arrangements'])}`, palettes `{summarize_bool(validation['pointer_assets_fully_matched']['palettes'])}`",
        "",
        "## Runtime Contract",
        "",
    ]
    for item in contract["known_semantics"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Layer Config Fields",
            "",
            "| Offset | Field | Meaning |",
            "| ---: | --- | --- |",
            "| 0 | `graphics` | Graphics pointer index and arrangement pointer index used by `LOAD_BATTLE_BG`. |",
            "| 1 | `palette` | Palette pointer index. |",
            "| 2 | `bpp` | Tile depth mode consumed by the loader. |",
            "| 3 | `unknown_palette_shift_style` | Palette/effect style byte; retained as unknown until the palette caller is fully named. |",
            "| 4-5 | `palette_cycle_1` | First/last palette cycle range. |",
            "| 6-7 | `palette_cycle_2` | Second palette cycle range. |",
            "| 8 | `palette_change_speed` | Palette-cycle speed. |",
            "| 9-12 | `scrolling_movements` | Four `BG_SCROLLING_TABLE` row references. |",
            "| 13-16 | `distortion_styles` | Four `BG_DISTORTION_TABLE` row references. |",
            "",
            "## Usage Summary",
            "",
        ]
    )
    usage = contract["layer_config_usage"]
    lines.append(f"- unused layer config rows: `{len(usage['unused_indices'])}`")
    lines.append(f"- unique graphics indices in config rows: `{len(usage['graphics_index_counts'])}`")
    lines.append(f"- unique palette indices in config rows: `{len(usage['palette_index_counts'])}`")
    lines.append(
        "- BPP modes: "
        + ", ".join(f"`{key}`: `{value}`" for key, value in usage["bpp_counts"].items())
    )

    lines.extend(
        [
            "",
            "## Sample Layer Configs",
            "",
            "The generated JSON contains all rows. This table keeps the checked-in narrative compact while making the join shape visible.",
            "",
            "| Layer | Graphics | Arrangement | Palette | BPP | Scroll refs | Distortion refs |",
            "| ---: | --- | --- | --- | ---: | --- | --- |",
        ]
    )
    for layer in contract["layer_configs"][:32]:
        lines.append(
            "| {index} | {gfx} | {arr} | {pal} | {bpp} | {scroll} | {distortion} |".format(
                index=layer["layer_config_index"],
                gfx=render_asset(layer["assets"]["graphics"]),
                arr=render_asset(layer["assets"]["arrangement"]),
                pal=render_asset(layer["assets"]["palette"]),
                bpp=layer["bpp"],
                scroll=", ".join(f"`{ref['index']}`" for ref in layer["scrolling_movements"]),
                distortion=", ".join(f"`{ref['index']}`" for ref in layer["distortion_styles"]),
            )
        )

    lines.extend(
        [
            "",
            "## Sample Battle Entries",
            "",
            "| Battle entry | Layer 1 | Layer 2 |",
            "| ---: | --- | --- |",
        ]
    )
    for entry in contract["battle_entries"][:64]:
        rendered_layers = []
        for layer in entry["layers"]:
            if not layer["enabled"]:
                rendered_layers.append("`NONE`")
            else:
                rendered_layers.append(f"`{layer['label']}` -> config `{layer['layer_config_index']}`")
        lines.append(f"| {entry['battle_entry_index']} | {rendered_layers[0]} | {rendered_layers[1]} |")

    lines.extend(["", "## Open Questions", ""])
    for question in contract["open_questions"]:
        lines.append(f"- {question}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build battle-background scene bundle contracts.")
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
        "battle background scene bundles: "
        f"{totals['layer_config_rows']} layer configs, "
        f"{totals['battle_entry_rows']} battle entries, "
        f"{totals['used_layer_configs']} used configs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
