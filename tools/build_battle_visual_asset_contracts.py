from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSON_OUT = ROOT / "build" / "battle-visual-asset-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "battle-visual-asset-contracts.md"
MANIFEST_PATHS = [ROOT / "asset-manifests" / f"bank-{bank}-assets.json" for bank in ["ca", "cb", "cc", "cd", "ce"]]


FAMILIES: dict[str, dict[str, Any]] = {
    "battle_background_graphics": {
        "label": "Battle background graphics",
        "runtime_contract": "Compressed 4bpp graphics payloads selected by battle-background graphics pointers and uploaded by the C2 battle-background loader.",
        "portable_contract": "Expose as indexed battle-background graphics assets with raw, decompressed, tile-preview, and palette-preview recipes where available.",
        "docs": ["notes/c2-battlebg-load-and-palette-effect-corridor-c2cfe5-c2e0e7.md"],
    },
    "battle_background_arrangements": {
        "label": "Battle background arrangements",
        "runtime_contract": "Compressed arrangement/tilemap payloads selected alongside background graphics to compose battle-background scenes.",
        "portable_contract": "Expose as indexed arrangement assets and keep composed preview recipes tied to their source indices.",
        "docs": ["notes/c2-battlebg-load-and-palette-effect-corridor-c2cfe5-c2e0e7.md"],
    },
    "battle_background_palettes": {
        "label": "Battle background palettes",
        "runtime_contract": "Palette payloads and palette pointers used by C2 palette/effect setup during battle-background loading.",
        "portable_contract": "Expose as indexed SNES palette assets with JSON and swatch recipes.",
        "docs": [
            "notes/c2-battlebg-load-and-palette-effect-corridor-c2cfe5-c2e0e7.md",
            "notes/title-screen-logo-palette-event-helpers-c0ebe0-c0ee53.md",
        ],
    },
    "battle_background_runtime_tables": {
        "label": "Battle background runtime tables",
        "runtime_contract": "Pointer, config, scrolling, distortion, and battle-entry background tables that bind battle backgrounds to runtime effects.",
        "portable_contract": "Expose as structured scene-layer bundles that join battle entries to graphics, arrangement, palette, scrolling, and distortion rows.",
        "docs": [
            "notes/battle-background-scene-bundles.md",
            "notes/c2-battlebg-load-and-palette-effect-corridor-c2cfe5-c2e0e7.md",
        ],
    },
    "psi_animation_sequences": {
        "label": "Scripted animation data",
        "runtime_contract": "Named animation data payloads for Car Painter lightning, Starman Jr teleport, Boom, Zombies, and The End sequences.",
        "portable_contract": "Keep as animation bytecode/data assets until the animation VM record shape is decoded.",
        "docs": ["notes/c3-battle-visual-effect-dispatch-source-contract-f981.md"],
    },
    "psi_animation_arrangements": {
        "label": "PSI animation arrangements",
        "runtime_contract": "Compressed PSI animation arrangement payloads selected by PSI animation config/pointer tables.",
        "portable_contract": "Expose as indexed PSI arrangement assets with decompressed outputs and visual previews.",
        "docs": [
            "notes/c2-psi-swirl-overlay-tail-c2e6b3-c2ea74.md",
            "notes/c3-battle-psi-menu-data-contracts.md",
        ],
    },
    "psi_animation_graphics_sets": {
        "label": "PSI animation graphics sets",
        "runtime_contract": "Compressed graphics sets shared by PSI animation arrangements.",
        "portable_contract": "Expose as PSI graphics-set assets, separate from arrangement and palette selection.",
        "docs": ["notes/c2-psi-swirl-overlay-tail-c2e6b3-c2ea74.md"],
    },
    "psi_animation_palettes": {
        "label": "PSI animation palettes",
        "runtime_contract": "Small SNES palette payloads used by PSI animation rendering.",
        "portable_contract": "Expose as indexed palette assets with JSON/swatch recipes.",
        "docs": ["notes/c2-psi-swirl-overlay-tail-c2e6b3-c2ea74.md"],
    },
    "psi_animation_runtime_tables": {
        "label": "PSI animation runtime tables",
        "runtime_contract": "Animation sequence, PSI config, and PSI pointer tables joining animation payloads to runtime effects.",
        "portable_contract": "Expose as structured runtime tables before assigning engine-ready animation schema fields.",
        "docs": ["notes/c3-battle-visual-effect-dispatch-source-contract-f981.md"],
    },
    "battle_sprite_graphics": {
        "label": "Battle sprite graphics",
        "runtime_contract": "Compressed battle sprite graphics payloads selected by the CE pointer table and rendered by the C2 battle-sprite path.",
        "portable_contract": "Expose as indexed battle sprite graphics with decompressed, tile-preview, palette-preview, and composed battle-sprite preview recipes where available.",
        "docs": ["notes/c2-battle-sprite-render-and-palette-tail-c2eee7-c2ff9a.md"],
    },
    "battle_sprite_palettes": {
        "label": "Battle sprite palettes",
        "runtime_contract": "SNES palettes consumed by the battle sprite renderer and palette tail.",
        "portable_contract": "Expose as indexed battle sprite palette assets with JSON/swatch recipes.",
        "docs": ["notes/c2-battle-sprite-render-and-palette-tail-c2eee7-c2ff9a.md"],
    },
    "battle_sprite_runtime_tables": {
        "label": "Battle sprite runtime tables",
        "runtime_contract": "Battle sprite pointer tables that bind sprite ids to compressed graphics payloads.",
        "portable_contract": "Expose as structured pointer tables and join them to sprite graphics/palette ids.",
        "docs": ["notes/c2-battle-sprite-render-and-palette-tail-c2eee7-c2ff9a.md"],
    },
    "swirl_payloads": {
        "label": "Swirl frame payloads",
        "runtime_contract": "Swirl data payloads selected by battle/overworld swirl transition code.",
        "portable_contract": "Expose as grouped swirl frame sequences using pointer-table and reference-frame counts.",
        "docs": [
            "notes/c2-psi-swirl-overlay-tail-c2e6b3-c2ea74.md",
            "notes/file-select-entity-scripts-and-swirl-transition-c4d830-c4d989.md",
        ],
    },
    "swirl_runtime_tables": {
        "label": "Swirl runtime tables",
        "runtime_contract": "Swirl pointer and primary tables that sequence the CE swirl payloads.",
        "portable_contract": "Expose as structured sequence tables before generating engine-ready swirl animation bundles.",
        "docs": [
            "notes/c2-psi-swirl-overlay-tail-c2e6b3-c2ea74.md",
            "notes/file-select-entity-scripts-and-swirl-transition-c4d830-c4d989.md",
        ],
    },
    "sound_stone_assets": {
        "label": "Sound Stone visual assets",
        "runtime_contract": "Compressed Sound Stone graphics and palette payloads used by presentation/display code.",
        "portable_contract": "Expose as a small named graphics/palette bundle.",
        "docs": ["notes/your-sanctuary-location-coordinate-table-c4de78.md"],
    },
    "embedded_audio_pack_tails": {
        "label": "Embedded audio pack tails",
        "runtime_contract": "Audio pack payloads embedded in otherwise visual banks; they belong to the broader audio-pack contract lane.",
        "portable_contract": "Keep as raw audio packs until the audio-pack/sample/sequence boundary is chosen.",
        "docs": ["notes/bank-e2-ee-audio-pack-run.md"],
    },
    "raw_padding": {
        "label": "Bank-end padding and raw gaps",
        "runtime_contract": "Small byte-protected tail gaps/slack ranges.",
        "portable_contract": "Preserve as raw padding until a build rule proves they can be generated.",
        "docs": [],
    },
}


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_assets() -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for manifest_path in MANIFEST_PATHS:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        bank = manifest_path.stem.split("-")[1].upper()
        for asset in manifest["assets"]:
            asset = dict(asset)
            asset["bank"] = bank
            asset["manifest_path"] = rel(manifest_path)
            assets.append(asset)
    return assets


def output_kinds(asset: dict[str, Any]) -> list[str]:
    outputs = asset.get("outputs", [])
    if not isinstance(outputs, list):
        return []
    return [str(output.get("kind", "unknown")) for output in outputs if isinstance(output, dict)]


def classify(asset: dict[str, Any]) -> str:
    asset_id = str(asset.get("id", "")).lower()
    title = str(asset.get("title", "")).lower()

    if asset_id.startswith("gap."):
        return "raw_padding"
    if "audio_pack" in asset_id:
        return "embedded_audio_pack_tails"
    if "sound_stone" in asset_id:
        return "sound_stone_assets"
    if asset_id.startswith("asset.ce.swirl_data_"):
        return "swirl_payloads"
    if "swirl" in asset_id:
        return "swirl_runtime_tables"
    if "battle_sprites_pointers" in asset_id:
        return "battle_sprite_runtime_tables"
    if "battle_sprites_palette" in asset_id or "battle_sprite_palettes" in asset_id:
        return "battle_sprite_palettes"
    if "battle_sprite_" in asset_id and "palette" not in asset_id:
        return "battle_sprite_graphics"
    if "psi_anim_pointers" in asset_id or "psi_anim_cfg" in asset_id or "animation_sequence_pointers" in asset_id:
        return "psi_animation_runtime_tables"
    if "psianims_palette" in asset_id or "psi_anim_palettes" in asset_id:
        return "psi_animation_palettes"
    if "psi_anim_gfx_set" in asset_id:
        return "psi_animation_graphics_sets"
    if "psi_arrangement" in asset_id:
        return "psi_animation_arrangements"
    if "animationdata" in asset_id:
        return "psi_animation_sequences"
    if "battle_background_gfx" in asset_id:
        return "battle_background_graphics"
    if "battle_background_arr" in asset_id:
        return "battle_background_arrangements"
    if "background_palette" in asset_id or "battle_background_palette" in asset_id or "_palettes_" in asset_id:
        return "battle_background_palettes"
    if "battle_background" in asset_id or "battle_bg" in asset_id or "backgrounds_" in asset_id:
        return "battle_background_runtime_tables"
    if str(asset.get("category")) == "raw-table":
        return "battle_background_runtime_tables"
    raise ValueError(f"Could not classify battle visual asset: {asset_id} ({title})")


def asset_summary(asset: dict[str, Any]) -> dict[str, Any]:
    source = asset.get("source", {})
    if not isinstance(source, dict):
        source = {}
    return {
        "id": asset.get("id"),
        "title": asset.get("title"),
        "bank": asset.get("bank"),
        "category": asset.get("category"),
        "range": source.get("range"),
        "bytes": int(source.get("bytes", 0) or 0),
        "output_kinds": output_kinds(asset),
        "manifest_path": asset.get("manifest_path"),
    }


def checked_ref_counts() -> dict[str, Any]:
    battle_bg_dir = ROOT / "refs" / "eb-decompile-4ef92" / "BattleBGs"
    swirls_dir = ROOT / "refs" / "eb-decompile-4ef92" / "Swirls"
    result: dict[str, Any] = {
        "battle_bg_png_count": len(list(battle_bg_dir.glob("*.png"))) if battle_bg_dir.exists() else None,
        "swirl_groups": [],
    }
    if swirls_dir.exists():
        for group_dir in sorted(path for path in swirls_dir.iterdir() if path.is_dir()):
            result["swirl_groups"].append(
                {"id": group_dir.name, "png_count": len(list(group_dir.glob("*.png")))}
            )
    return result


def build_contract() -> dict[str, Any]:
    assets = load_assets()
    grouped: dict[str, list[dict[str, Any]]] = {family_id: [] for family_id in FAMILIES}
    for asset in assets:
        grouped[classify(asset)].append(asset_summary(asset))

    families = []
    for family_id, family in FAMILIES.items():
        family_assets = grouped[family_id]
        output_counts: Counter[str] = Counter()
        category_counts: Counter[str] = Counter()
        bank_counts: Counter[str] = Counter()
        for asset in family_assets:
            output_counts.update(asset["output_kinds"])
            category_counts[str(asset["category"])] += 1
            bank_counts[str(asset["bank"])] += 1
        families.append(
            {
                "id": family_id,
                "label": family["label"],
                "runtime_contract": family["runtime_contract"],
                "portable_contract": family["portable_contract"],
                "docs": [doc for doc in family["docs"] if (ROOT / doc).exists()],
                "asset_count": len(family_assets),
                "bytes": sum(int(asset["bytes"]) for asset in family_assets),
                "bank_counts": dict(sorted(bank_counts.items())),
                "category_counts": dict(sorted(category_counts.items())),
                "output_kind_counts": dict(sorted(output_counts.items())),
                "assets": family_assets,
            }
        )

    totals = {
        "assets": len(assets),
        "bytes": sum(sum(int(asset["bytes"]) for asset in family["assets"]) for family in families),
        "families": len(families),
        "preview_or_decode_assets": sum(
            1
            for asset in assets
            if any(kind != "raw" for kind in output_kinds(asset))
        ),
    }

    return {
        "schema": "earthbound-decomp.battle-visual-asset-contracts.v1",
        "scope": "CA-CE battle backgrounds, PSI/animation visuals, battle sprites, swirls, Sound Stone visuals, and embedded audio tails",
        "inputs": [rel(path) for path in MANIFEST_PATHS],
        "generated_json": rel(DEFAULT_JSON_OUT),
        "tracked_markdown": rel(DEFAULT_MARKDOWN_OUT),
        "totals": totals,
        "families": families,
        "reference_counts": checked_ref_counts(),
        "known_runtime_shapes": [
            {
                "id": "battle_background_scene_bundle",
                "shape": "battle-entry layer table + BG_DATA_TABLE rows + graphics/arrangement/palette pointers + scroll/distortion rows feed the C2 battle-background loader.",
                "source": "notes/battle-background-scene-bundles.md",
            },
            {
                "id": "battle_sprite_bundle",
                "shape": "CE battle-sprite pointer table selects compressed sprite graphics; CE palette assets supply renderer palettes; C2 renders with palette-tail helpers.",
                "source": "notes/c2-battle-sprite-render-and-palette-tail-c2eee7-c2ff9a.md",
            },
            {
                "id": "swirl_sequence_bundle",
                "shape": "CE swirl payloads plus swirl pointer/primary tables form transition frame sequences; ignored EBDecomp refs already contain six rendered swirl groups.",
                "source": "refs/eb-decompile-4ef92/Swirls/swirls.yml and notes/c2-psi-swirl-overlay-tail-c2e6b3-c2ea74.md",
            },
        ],
        "next_open_questions": [
            "Promote battle-background layer enum labels beyond UNKNOWN### where visible scene names can be corroborated.",
            "Name PSI animation config fields and join arrangement/gfx/palette payloads into animation bundles.",
            "Join CE battle sprite pointer rows to graphics and palette ids.",
            "Use the EBDecomp swirl PNG/frame counts to group CE swirl_data payloads into six sequence bundles without checking in images.",
        ],
    }


def compact_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "-"
    return ", ".join(f"`{key}` {value}" for key, value in sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def render_markdown(contract: dict[str, Any]) -> str:
    totals = contract["totals"]
    lines = [
        "# Battle Visual Asset Contracts",
        "",
        "Generated by `tools/build_battle_visual_asset_contracts.py` from the checked-in CA-CE asset manifests. It groups battle visual assets by runtime-facing family before deeper bundle joins.",
        "",
        "No ROM-derived payloads or reference images are checked in by this report.",
        "",
        "## Snapshot",
        "",
        f"- assets/tables/gaps represented: `{totals['assets']}`",
        f"- source bytes represented: `{totals['bytes']}`",
        f"- contract families: `{totals['families']}`",
        f"- assets with decoder/preview recipes beyond raw extraction: `{totals['preview_or_decode_assets']}`",
        "",
        "## Reference Counts",
        "",
    ]
    refs = contract["reference_counts"]
    if refs.get("battle_bg_png_count") is not None:
        lines.append(f"- ignored EBDecomp BattleBG PNG refs: `{refs['battle_bg_png_count']}`")
    if refs.get("swirl_groups"):
        swirl_summary = ", ".join(f"{item['id']}: {item['png_count']}" for item in refs["swirl_groups"])
        lines.append(f"- ignored EBDecomp swirl frame groups: {swirl_summary}")

    lines.extend(
        [
            "",
            "## Family Contracts",
            "",
            "| Family | Assets | Bytes | Banks | Categories | Output recipes | Runtime contract |",
            "| --- | ---: | ---: | --- | --- | --- | --- |",
        ]
    )
    for family in contract["families"]:
        lines.append(
            "| {label} | {assets} | {bytes} | {banks} | {categories} | {outputs} | {runtime} |".format(
                label=family["label"],
                assets=family["asset_count"],
                bytes=family["bytes"],
                banks=compact_counts(family["bank_counts"]),
                categories=compact_counts(family["category_counts"]),
                outputs=compact_counts(family["output_kind_counts"]),
                runtime=family["runtime_contract"],
            )
        )

    lines.extend(["", "## Known Runtime Shapes", ""])
    for shape in contract["known_runtime_shapes"]:
        lines.append(f"- `{shape['id']}`: {shape['shape']} Source: `{shape['source']}`.")

    lines.extend(["", "## Per-Family Assets", ""])
    for family in contract["families"]:
        lines.append(f"### {family['label']}")
        lines.append("")
        lines.append(f"- portable contract: {family['portable_contract']}")
        if family["docs"]:
            lines.append(f"- checked docs: {', '.join(f'`{doc}`' for doc in family['docs'])}")
        lines.append("")
        lines.append("| Asset | Range | Bytes | Outputs |")
        lines.append("| --- | --- | ---: | --- |")
        for asset in family["assets"]:
            lines.append(
                "| `{id}` | `{range}` | {bytes} | {outputs} |".format(
                    id=asset["id"],
                    range=asset["range"],
                    bytes=asset["bytes"],
                    outputs=", ".join(f"`{kind}`" for kind in asset["output_kinds"]) or "-",
                )
            )
        lines.append("")

    lines.extend(["## Next Open Questions", ""])
    for question in contract["next_open_questions"]:
        lines.append(f"- {question}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build CA-CE battle visual asset contract seeds.")
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
        "battle visual contracts: "
        f"{totals['assets']} assets, "
        f"{totals['families']} families, "
        f"{totals['preview_or_decode_assets']} decoded/previewed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
