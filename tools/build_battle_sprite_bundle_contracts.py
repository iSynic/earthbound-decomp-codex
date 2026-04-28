from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSON_OUT = ROOT / "build" / "battle-sprite-bundle-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "battle-sprite-bundle-contracts.md"

EB_SRC = ROOT / "refs" / "ebsrc-main" / "ebsrc-main"
BATTLE_SPRITES_POINTERS_REF = EB_SRC / "src" / "data" / "battle" / "battle_sprites_pointers.asm"
ENEMIES_REF = EB_SRC / "src" / "data" / "battle" / "enemies.asm"
LOAD_BATTLE_SPRITE_REF = EB_SRC / "src" / "battle" / "load_battle_sprite.asm"
C2_RENDER_DOC = ROOT / "notes" / "c2-battle-sprite-render-and-palette-tail-c2eee7-c2ff9a.md"
MANIFEST_PATHS = [ROOT / "asset-manifests" / f"bank-{bank}-assets.json" for bank in ["cd", "ce"]]

SIZE_DIMENSIONS = {
    "_32X32": {"width": 32, "height": 32},
    "_32X64": {"width": 32, "height": 64},
    "_64X32": {"width": 64, "height": 32},
    "_64X64": {"width": 64, "height": 64},
    "_128X64": {"width": 128, "height": 64},
    "_128X128": {"width": 128, "height": 128},
}

KNOWN_OUT_OF_RANGE_SPRITE_REFS = {
    # Retail US enemy config has no BATTLE_SPRITE_110 pointer row or asset in
    # the checked ebsrc table/manifests, but Evil Eye still references $006E.
    (224, 110): "Evil Eye references sprite id 110 while the pointer table defines 0..109.",
}


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def parse_numeric(token: str) -> int:
    token = token.strip()
    if token.startswith("$"):
        return int(token[1:], 16)
    return int(token, 10)


def load_assets() -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for path in MANIFEST_PATHS:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        bank = path.stem.split("-")[1].upper()
        for asset in manifest["assets"]:
            source = asset.get("source", {})
            if not isinstance(source, dict):
                source = {}
            assets.append(
                {
                    "id": asset["id"],
                    "title": asset["title"],
                    "bank": bank,
                    "category": asset["category"],
                    "range": source.get("range"),
                    "bytes": source.get("bytes"),
                }
            )
    return assets


def asset_ref(asset: dict[str, Any] | None) -> dict[str, Any] | None:
    if asset is None:
        return None
    return {
        "id": asset["id"],
        "title": asset["title"],
        "bank": asset["bank"],
        "range": asset["range"],
        "bytes": asset["bytes"],
    }


def build_asset_maps(assets: list[dict[str, Any]]) -> dict[str, Any]:
    by_title = {asset["title"]: asset for asset in assets}
    palettes_by_index: dict[int, dict[str, Any]] = {}
    for asset in assets:
        title = str(asset["title"])
        asset_id = str(asset["id"])
        if title == "BATTLE_SPRITE_PALETTES":
            palettes_by_index[0] = asset
            continue
        match = re.search(r"battle_sprites/palettes/(\d+)\.pal", title)
        if match:
            palettes_by_index[int(match.group(1))] = asset
            continue
        match = re.search(r"battle_sprites_palettes_(\d+)_pal", asset_id)
        if match:
            palettes_by_index[int(match.group(1))] = asset
    return {"by_title": by_title, "palettes_by_index": palettes_by_index}


def parse_pointer_table(path: Path, asset_maps: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    pending_label: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        pointer_match = re.search(r"\.DWORD\s+(BATTLE_SPRITE_(\d+))", line)
        if pointer_match:
            pending_label = pointer_match.group(1)
            continue
        size_match = re.search(r"\.BYTE\s+BATTLE_SPRITE_SIZE::([A-Z0-9_]+)", line)
        if size_match and pending_label is not None:
            sprite_id = int(pending_label.rsplit("_", 1)[1])
            size_label = size_match.group(1)
            dimensions = SIZE_DIMENSIONS.get(size_label)
            if dimensions is None:
                raise ValueError(f"Unknown battle sprite size enum: {size_label}")
            entries.append(
                {
                    "sprite_id": sprite_id,
                    "label": pending_label,
                    "size": size_label,
                    "dimensions": dimensions,
                    "asset": asset_ref(asset_maps["by_title"].get(pending_label)),
                }
            )
            pending_label = None
    return entries


def parse_enemy_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        flag_match = re.search(r"\.BYTE\s+(.+?)\s*;The Flag", line)
        if flag_match:
            if current and "battle_sprite_id" in current and "palette_index" in current:
                current["enemy_index"] = len(rows)
                rows.append(current)
            current = {"flag": flag_match.group(1).strip()}
            continue
        if current is None:
            continue
        name_match = re.search(r'PADDEDEBTEXT\s+"([^"]*)"', line)
        if name_match:
            current["name"] = name_match.group(1)
            continue
        sprite_match = re.search(r"\.WORD\s+([^;\s]+)\s*;Battle sprite", line)
        if sprite_match:
            current["battle_sprite_id"] = parse_numeric(sprite_match.group(1))
            continue
        palette_match = re.search(r"\.BYTE\s+([^;\s]+)\s*;Palette", line)
        if palette_match:
            current["palette_index"] = parse_numeric(palette_match.group(1))
            continue
    if current and "battle_sprite_id" in current and "palette_index" in current:
        current["enemy_index"] = len(rows)
        rows.append(current)
    return rows


def build_bundles() -> dict[str, Any]:
    assets = load_assets()
    asset_maps = build_asset_maps(assets)
    sprites = parse_pointer_table(BATTLE_SPRITES_POINTERS_REF, asset_maps)
    enemies = parse_enemy_rows(ENEMIES_REF)
    sprites_by_id = {sprite["sprite_id"]: sprite for sprite in sprites}

    usage_by_sprite: dict[int, list[dict[str, Any]]] = defaultdict(list)
    palette_usage: Counter[int] = Counter()
    out_of_range_sprite_refs: list[dict[str, Any]] = []
    out_of_range_palette_refs: list[dict[str, Any]] = []
    for enemy in enemies:
        sprite_id = int(enemy["battle_sprite_id"])
        palette_index = int(enemy["palette_index"])
        if sprite_id not in sprites_by_id:
            outlier_key = (int(enemy["enemy_index"]), sprite_id)
            out_of_range_sprite_refs.append(
                {
                    **enemy,
                    "known_outlier": outlier_key in KNOWN_OUT_OF_RANGE_SPRITE_REFS,
                    "outlier_note": KNOWN_OUT_OF_RANGE_SPRITE_REFS.get(outlier_key),
                }
            )
        if palette_index not in asset_maps["palettes_by_index"]:
            out_of_range_palette_refs.append(enemy)
        palette_usage[palette_index] += 1
        usage_by_sprite[sprite_id].append(
            {
                "enemy_index": enemy["enemy_index"],
                "name": enemy.get("name", ""),
                "palette_index": palette_index,
                "palette_asset": asset_ref(asset_maps["palettes_by_index"].get(palette_index)),
            }
        )

    bundles = []
    for sprite in sprites:
        usage = usage_by_sprite.get(sprite["sprite_id"], [])
        palette_indices = sorted({item["palette_index"] for item in usage})
        bundles.append(
            {
                **sprite,
                "enemy_usage_count": len(usage),
                "used_palette_indices": palette_indices,
                "used_palette_assets": [
                    asset_ref(asset_maps["palettes_by_index"].get(index)) for index in palette_indices
                ],
                "sample_enemies": usage[:8],
            }
        )

    size_counts = Counter(sprite["size"] for sprite in sprites)
    bank_counts = Counter(sprite["asset"]["bank"] for sprite in sprites if sprite.get("asset"))
    unused_sprites = [bundle["sprite_id"] for bundle in bundles if bundle["enemy_usage_count"] == 0]
    only_known_out_of_range_sprite_refs = all(
        ref.get("known_outlier") for ref in out_of_range_sprite_refs
    )

    return {
        "schema": "earthbound-decomp.battle-sprite-bundle-contracts.v1",
        "scope": "CD/CE battle sprite graphics, CE sprite pointer rows, CE palettes, and ebsrc enemy palette usage",
        "inputs": [
            rel(BATTLE_SPRITES_POINTERS_REF),
            rel(ENEMIES_REF),
            rel(LOAD_BATTLE_SPRITE_REF),
            rel(C2_RENDER_DOC),
            *[rel(path) for path in MANIFEST_PATHS],
        ],
        "generated_json": rel(DEFAULT_JSON_OUT),
        "tracked_markdown": rel(DEFAULT_MARKDOWN_OUT),
        "totals": {
            "battle_sprite_rows": len(sprites),
            "enemy_rows": len(enemies),
            "palette_assets": len(asset_maps["palettes_by_index"]),
            "matched_sprite_assets": sum(1 for sprite in sprites if sprite.get("asset")),
            "used_sprite_rows": sum(1 for bundle in bundles if bundle["enemy_usage_count"] > 0),
            "unused_sprite_rows": len(unused_sprites),
            "used_palette_assets": len(palette_usage),
        },
        "validation": {
            "all_sprite_pointer_assets_matched": all(sprite.get("asset") for sprite in sprites),
            "all_enemy_sprite_refs_in_range": not out_of_range_sprite_refs,
            "only_known_out_of_range_sprite_refs": only_known_out_of_range_sprite_refs,
            "out_of_range_sprite_refs": out_of_range_sprite_refs,
            "all_enemy_palette_refs_matched": not out_of_range_palette_refs,
            "out_of_range_palette_refs": out_of_range_palette_refs,
        },
        "size_counts": dict(sorted(size_counts.items())),
        "sprite_asset_bank_counts": dict(sorted(bank_counts.items())),
        "palette_usage_counts": {
            str(index): palette_usage[index] for index in sorted(palette_usage)
        },
        "known_semantics": [
            "`BATTLE_SPRITES_POINTERS` rows are 5 bytes: 24-bit compressed graphics pointer plus one `BATTLE_SPRITE_SIZE` byte.",
            "`LOAD_BATTLE_SPRITE` resolves enemy sprite ids through this table before decompression and row allocation.",
            "Enemy configuration rows carry both the battle sprite id and battle sprite palette index.",
            "Battle sprite palettes are 32-byte SNES BGR555 palette payloads at `BATTLE_SPRITE_PALETTES + palette_index * 0x20`.",
            "The C2 render/palette tail uses loaded sprite slots and the selected palette data for row rendering and enemy color-wave effects.",
        ],
        "open_questions": [
            "Enemy config row 224 / Evil Eye references battle sprite id 110, but the checked ebsrc pointer table and manifests define ids 0..109 only.",
            "Enemy-table names are used only as usage hints; renderer-facing identity remains the numeric battle sprite id and palette index.",
            "Rendered battle sprite previews remain local user-ROM-derived outputs and are not checked in.",
        ],
        "battle_sprite_bundles": bundles,
    }


def render_asset(asset: dict[str, Any] | None) -> str:
    if asset is None:
        return "-"
    return f"`{asset['id']}`"


def render_bool(value: bool) -> str:
    return "yes" if value else "no"


def md_escape(text: str) -> str:
    return text.replace("|", "\\|")


def render_markdown(contract: dict[str, Any]) -> str:
    totals = contract["totals"]
    validation = contract["validation"]
    lines = [
        "# Battle Sprite Bundle Contracts",
        "",
        "Generated by `tools/build_battle_sprite_bundle_contracts.py` from the CD/CE asset manifests, ebsrc battle-sprite pointer table, and ebsrc enemy configuration rows.",
        "",
        "No ROM-derived sprite graphics, palette bytes, or rendered previews are checked in by this report.",
        "",
        "## Snapshot",
        "",
        f"- battle sprite pointer rows: `{totals['battle_sprite_rows']}`",
        f"- matched sprite graphics assets: `{totals['matched_sprite_assets']}`",
        f"- enemy config rows scanned: `{totals['enemy_rows']}`",
        f"- palette assets: `{totals['palette_assets']}`",
        f"- used sprite rows from enemy configs: `{totals['used_sprite_rows']}`",
        f"- unused sprite rows in enemy configs: `{totals['unused_sprite_rows']}`",
        f"- used palette assets from enemy configs: `{totals['used_palette_assets']}`",
        "",
        "## Validation",
        "",
        f"- all sprite pointer assets matched: `{render_bool(validation['all_sprite_pointer_assets_matched'])}`",
        f"- all enemy sprite refs are in range: `{render_bool(validation['all_enemy_sprite_refs_in_range'])}`",
        f"- out-of-range enemy sprite refs are documented known outliers: `{render_bool(validation['only_known_out_of_range_sprite_refs'])}`",
        f"- all enemy palette refs matched assets: `{render_bool(validation['all_enemy_palette_refs_matched'])}`",
        "",
        "## Runtime Contract",
        "",
    ]
    for item in contract["known_semantics"]:
        lines.append(f"- {item}")

    lines.extend(["", "## Size Mix", ""])
    for size, count in contract["size_counts"].items():
        lines.append(f"- `{size}`: `{count}` rows")
    lines.append("")
    lines.append("## Asset Bank Mix")
    lines.append("")
    for bank, count in contract["sprite_asset_bank_counts"].items():
        lines.append(f"- `{bank}`: `{count}` sprite graphics assets")

    lines.extend(
        [
            "",
            "## Battle Sprite Bundles",
            "",
            "| Sprite | Asset | Size | Palettes observed | Enemy uses | Sample enemies |",
            "| ---: | --- | --- | --- | ---: | --- |",
        ]
    )
    for bundle in contract["battle_sprite_bundles"]:
        palettes = ", ".join(f"`{index}`" for index in bundle["used_palette_indices"]) or "-"
        samples = ", ".join(
            f"{enemy['enemy_index']}: {md_escape(enemy['name'])}" for enemy in bundle["sample_enemies"]
        )
        lines.append(
            "| {sprite} | {asset} | `{size}` | {palettes} | {uses} | {samples} |".format(
                sprite=bundle["sprite_id"],
                asset=render_asset(bundle["asset"]),
                size=bundle["size"],
                palettes=palettes,
                uses=bundle["enemy_usage_count"],
                samples=samples or "-",
            )
        )

    lines.extend(
        [
            "",
            "## Palette Usage",
            "",
            "| Palette | Asset | Enemy uses |",
            "| ---: | --- | ---: |",
        ]
    )
    palette_assets = {
        int(index): next(
            (
                palette
                for bundle in contract["battle_sprite_bundles"]
                for palette in bundle["used_palette_assets"]
                if palette and palette["id"].endswith(f"_{index}_pal")
            ),
            None,
        )
        for index in range(32)
    }
    for bundle in contract["battle_sprite_bundles"]:
        for palette in bundle["used_palette_assets"]:
            if palette and palette["title"] == "BATTLE_SPRITE_PALETTES":
                palette_assets[0] = palette
    for index_text, count in contract["palette_usage_counts"].items():
        index = int(index_text)
        lines.append(f"| {index} | {render_asset(palette_assets.get(index))} | {count} |")

    lines.extend(["", "## Open Questions", ""])
    for question in contract["open_questions"]:
        lines.append(f"- {question}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build CD/CE battle sprite bundle contracts.")
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    args = parser.parse_args()

    contract = build_bundles()
    json_out = Path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

    markdown_out = Path(args.markdown_out)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(render_markdown(contract), encoding="utf-8")

    totals = contract["totals"]
    print(
        "battle sprite bundle contracts: "
        f"{totals['battle_sprite_rows']} sprite rows, "
        f"{totals['enemy_rows']} enemies, "
        f"{totals['used_palette_assets']} palettes used"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
