from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSON_OUT = ROOT / "build" / "ui-font-town-map-asset-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "ui-font-town-map-asset-contracts.md"


MANIFEST_PATHS = [
    ROOT / "asset-manifests" / "bank-e0-assets.json",
    ROOT / "asset-manifests" / "bank-e1-assets.json",
]


FAMILIES: dict[str, dict[str, Any]] = {
    "text_window_skin": {
        "label": "Text window skins and text palettes",
        "runtime_contract": "C0/C4 text-window upload and palette-flavour callers consume these as window graphics, window-property rows, and palette/font-colour data.",
        "portable_contract": "Expose as a window skin bundle: graphics, property rows, flavour palettes, and movement-text palette rows.",
        "docs": [
            "notes/text-window-rendering-primitives-c1078d-c10d7c.md",
            "notes/active-window-text-tile-pair-placement-c44c8c.md",
            "notes/text-token-glyph-run-stager-c44b3a-c44e61.md",
        ],
    },
    "font_sets": {
        "label": "Font data and glyph graphics",
        "runtime_contract": "Font data assets are fixed-width metric/spacing rows paired with raw or 4bpp glyph graphics consumed by the text and presentation renderers.",
        "portable_contract": "Expose each font as a typed pair: metrics bytes plus glyph graphics, with palette ownership kept separate.",
        "docs": [
            "notes/text-window-rendering-primitives-c1078d-c10d7c.md",
            "notes/text-token-glyph-run-stager-c44b3a-c44e61.md",
            "notes/c4-text-tile-staging-and-vector-helpers-1db6-213f.md",
        ],
    },
    "town_maps": {
        "label": "Town-map graphics, labels, icons, and placement tables",
        "runtime_contract": "C4:D553 selects E0 town-map graphics through E0:2190; C4:D43F walks E1 town-map icon records from E1:F491 and draws icons mapped through E1:F44C.",
        "portable_contract": "Expose each town map as compressed graphics plus shared label graphics, icon palette, icon-id map, blink suppress table, pointer table, and 5-byte placement records.",
        "docs": [
            "notes/town-map-selection-rendering-c4d274-c4d744.md",
            "notes/text-command-1f41-special-event-dispatch-c1befc.md",
        ],
    },
    "intro_and_title_visuals": {
        "label": "Intro, logo, title, and attract visuals",
        "runtime_contract": "C4 intro/presentation loaders consume compressed arrangement, graphics, and palette triples for logos, gas-station intro, title screen, Itoi/Nintendo presentation, and related attract payloads.",
        "portable_contract": "Expose each visual scene as arrangement/graphics/palette components plus any unresolved adjacent compressed payloads until their exact scene role is pinned.",
        "docs": [
            "notes/gas-station-intro-asset-loader-c4a377.md",
            "notes/visual-record-walkers-and-naming-remap-c4cc2f-c4d065.md",
        ],
    },
    "flyover_credits_photo_tables": {
        "label": "Flyover, credits, cast, and photographer tables",
        "runtime_contract": "These table spans feed scripted flyover text, cast formatting, photographer records, and credits/cast display helpers rather than raw image decoding.",
        "portable_contract": "Expose as structured table assets first; only split into higher-level records once field roles have caller proof.",
        "docs": [
            "notes/c3-flyover-intro-text-release-paths-source-pilot.md",
            "notes/your-sanctuary-location-coordinate-table-c4de78.md",
        ],
    },
    "audio_pack_tails": {
        "label": "Embedded audio pack tails",
        "runtime_contract": "E0/E1 end with audio-pack payloads that belong to the broader E2-EE audio-pack contract family, not the UI visual family.",
        "portable_contract": "Keep as raw audio packs until the audio-pack/sample/sequence boundary is chosen.",
        "docs": [
            "notes/bank-e2-ee-audio-pack-run.md",
        ],
    },
    "unresolved_ui_binary_payloads": {
        "label": "Unresolved UI-adjacent binary payloads",
        "runtime_contract": "These ranges are byte-accounted and extractable, but the exact runtime owner is not pinned tightly enough to fold them into a UI/font/town-map family.",
        "portable_contract": "Keep as named raw/decompressed payloads with provenance until a caller or reference split proves the field role.",
        "docs": [
            "notes/bank-e0-asset-data-map.md",
            "notes/bank-e1-asset-data-map.md",
        ],
    },
    "raw_padding": {
        "label": "Bank-end padding and raw gaps",
        "runtime_contract": "Bank-end raw gaps are byte-protected scaffold/padding ranges, not active UI contracts.",
        "portable_contract": "Preserve as raw padding until a build rule proves they can be generated rather than emitted.",
        "docs": [],
    },
}


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


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def output_kinds(asset: dict[str, Any]) -> list[str]:
    outputs = asset.get("outputs", [])
    if not isinstance(outputs, list):
        return []
    return [str(output.get("kind", "unknown")) for output in outputs if isinstance(output, dict)]


def notes_text(asset: dict[str, Any]) -> str:
    notes = asset.get("notes", [])
    if not isinstance(notes, list):
        return ""
    return " ".join(str(note) for note in notes)


def classify(asset: dict[str, Any]) -> str:
    asset_id = str(asset.get("id", "")).lower()
    title = str(asset.get("title", "")).lower()

    if asset_id.startswith("gap."):
        return "raw_padding"
    if "audio_pack" in asset_id:
        return "audio_pack_tails"
    if "town_map" in asset_id or "town_maps" in notes_text(asset).lower() or "e1f203" in asset_id:
        return "town_maps"
    if asset_id.startswith("table.e1.000") or "credits" in asset_id or "photographer" in asset_id or "cast_sequence" in asset_id:
        return "flyover_credits_photo_tables"
    if "compressed_sram" in asset_id:
        return "unresolved_ui_binary_payloads"
    if "font" in asset_id or "font" in title or "romaji" in asset_id or "mrsaturn" in asset_id:
        return "font_sets"
    if "text_window" in asset_id or "flavoured_text" in asset_id or "movement_text_string_palette" in notes_text(asset).lower():
        return "text_window_skin"
    if any(
        token in asset_id
        for token in [
            "ape",
            "halken",
            "nintendo",
            "gas_station",
            "produced_itoi",
            "title_screen",
            "unknown_e1ae7c",
            "unknown_e1c6e5",
            "unknown_e1cfaf",
            "unknown_e1d4f4",
            "unknown_e1d5e8",
            "unknown_e1d6e1",
            "compressed_palette_unknown",
        ]
    ):
        return "intro_and_title_visuals"
    return "flyover_credits_photo_tables"


def asset_summary(asset: dict[str, Any]) -> dict[str, Any]:
    source = asset.get("source", {})
    if not isinstance(source, dict):
        source = {}
    notes = notes_text(asset)
    missing_payload_metadata_units = 0
    asset_id = str(asset.get("id", "")).lower()
    if "yml metadata was missing" in notes.lower():
        missing_payload_metadata_units = 1
    if asset_id == "asset.e1.unknown_e1ae7c":
        missing_payload_metadata_units = 3
    return {
        "id": asset.get("id"),
        "title": asset.get("title"),
        "bank": asset.get("bank"),
        "category": asset.get("category"),
        "range": source.get("range"),
        "bytes": int(source.get("bytes", 0) or 0),
        "output_kinds": output_kinds(asset),
        "manifest_path": asset.get("manifest_path"),
        "missing_payload_metadata_units": missing_payload_metadata_units,
        "notes": asset.get("notes", []),
    }


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
        for asset in family_assets:
            output_counts.update(asset["output_kinds"])
            category_counts[str(asset["category"])] += 1
        families.append(
            {
                "id": family_id,
                "label": family["label"],
                "runtime_contract": family["runtime_contract"],
                "portable_contract": family["portable_contract"],
                "docs": [doc for doc in family["docs"] if (ROOT / doc).exists()],
                "asset_count": len(family_assets),
                "bytes": sum(int(asset["bytes"]) for asset in family_assets),
                "missing_payload_metadata_units": sum(
                    int(asset["missing_payload_metadata_units"]) for asset in family_assets
                ),
                "category_counts": dict(sorted(category_counts.items())),
                "output_kind_counts": dict(sorted(output_counts.items())),
                "assets": family_assets,
            }
        )

    return {
        "schema": "earthbound-decomp.ui-font-town-map-asset-contracts.v1",
        "scope": "E0/E1 UI, font, town-map, intro/title, table, and embedded audio-tail payloads",
        "inputs": [rel(path) for path in MANIFEST_PATHS],
        "generated_json": rel(DEFAULT_JSON_OUT),
        "tracked_markdown": rel(DEFAULT_MARKDOWN_OUT),
        "families": families,
        "totals": {
            "assets": len(assets),
            "bytes": sum(sum(int(asset["bytes"]) for asset in family["assets"]) for family in families),
            "missing_payload_metadata_units": sum(int(family["missing_payload_metadata_units"]) for family in families),
            "families": len(families),
        },
        "known_runtime_shapes": [
            {
                "id": "town_map_pointer_table",
                "source": "notes/town-map-selection-rendering-c4d274-c4d744.md",
                "shape": "E0:2190 pointer table selects one of six E0 town-map graphics payloads for C4:D553.",
            },
            {
                "id": "town_map_icon_records",
                "source": "notes/town-map-selection-rendering-c4d274-c4d744.md",
                "shape": "E1:F491 points to five-byte icon records: x, y, icon id, and event flag word with high-bit polarity.",
            },
            {
                "id": "town_map_icon_animation",
                "source": "notes/town-map-selection-rendering-c4d274-c4d744.md",
                "shape": "E1:F44C maps town-map icon ids, E1:F47A suppresses blink-phase icons, and C4:D2A8 cycles CGRAM entries 0x81..0x86.",
            },
            {
                "id": "font_metric_pairs",
                "source": "asset-manifests/bank-e0-assets.json and asset-manifests/bank-e1-assets.json",
                "shape": "Main, battle, tiny, large, and Mr. Saturn font data are 96-byte metric tables paired with glyph graphics; romaji and credits fonts are graphics-only until caller-specific metrics are proven.",
            },
        ],
        "subrange_contracts": [
            {
                "id": "town_map_gfx_pointer_table",
                "family": "town_maps",
                "range": "E0:2190..E0:21A8",
                "status": "runtime-corroborated",
                "contract": "Six-entry town-map graphics pointer table consumed by C4:D553 before decompressing the selected E0 town-map payload.",
                "evidence": "C4:D553 indexes E0:2190 from the zero-based town-map id in notes/town-map-selection-rendering-c4d274-c4d744.md.",
            },
            {
                "id": "town_map_icon_id_map",
                "family": "town_maps",
                "range": "E1:F44C..E1:F47A",
                "status": "runtime-corroborated",
                "contract": "Icon-id remap table used by C4:D2F0 and C4:D43F before submitting town-map icons through C0:8C54.",
                "evidence": "C4 town-map overlay/static renderers map icon ids through E1:F44C.",
            },
            {
                "id": "town_map_blink_suppress_table",
                "family": "town_maps",
                "range": "E1:F47A..E1:F491",
                "status": "runtime-corroborated",
                "contract": "Blink/suppression table checked before static icon drawing; nonzero entries suppress icons while $B4AE is in the hidden phase.",
                "evidence": "C4:D43F checks E1:F47A before the event-flag test.",
            },
            {
                "id": "town_map_icon_placement_pointer_table",
                "family": "town_maps",
                "range": "E1:F491..E1:F49D",
                "status": "runtime-inferred",
                "contract": "Six 16-bit list pointers, one per town map, used by C4:D43F to find placement records.",
                "evidence": "C4:D43F indexes a pointer table at E1:F491 for the selected zero-based town-map id; six town maps implies six word entries before placement data.",
            },
            {
                "id": "town_map_icon_placement_records",
                "family": "town_maps",
                "range": "E1:F49D..E1:F581",
                "status": "runtime-corroborated-shape",
                "contract": "Variable icon lists made of five-byte records terminated by FF: x, y, icon id, and event flag word with high-bit draw polarity.",
                "evidence": "C4:D43F walks records until FF and interprets the five-byte record shape documented in notes/town-map-selection-rendering-c4d274-c4d744.md.",
            },
        ],
        "next_open_questions": [
            "Split E0 text_window_properties into row-level window skin fields.",
            "Name the exact role of COMPRESSED_SRAM/E0:09B4 after caller corroboration.",
            "Resolve the E1 intro/title UNKNOWN_* compressed payloads into scene-specific graphics, palette, or arrangement roles.",
            "Name the leading E1:F203..F44C town-map-adjacent records before the icon remap/blink/pointer/placement subranges.",
        ],
    }


def compact_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "-"
    return ", ".join(f"`{key}` {value}" for key, value in sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def render_markdown(contract: dict[str, Any]) -> str:
    totals = contract["totals"]
    lines = [
        "# UI/Font/Town-Map Asset Contracts",
        "",
        "Generated by `tools/build_ui_font_town_map_asset_contracts.py` from the checked-in E0/E1 asset manifests. It is a contract seed for phase 4: the goal is to group byte-backed assets by runtime role before deeper decoder or port-bundle work.",
        "",
        "No ROM-derived payloads are checked in by this report.",
        "",
        "## Snapshot",
        "",
        f"- assets/tables/gaps represented: `{totals['assets']}`",
        f"- source bytes represented: `{totals['bytes']}`",
        f"- contract families: `{totals['families']}`",
        f"- missing payload metadata units: `{totals['missing_payload_metadata_units']}`",
        "",
        "## Family Contracts",
        "",
        "| Family | Assets | Bytes | Missing metadata | Categories | Output recipes | Runtime contract |",
        "| --- | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for family in contract["families"]:
        lines.append(
            "| {label} | {assets} | {bytes} | {missing} | {categories} | {outputs} | {runtime} |".format(
                label=family["label"],
                assets=family["asset_count"],
                bytes=family["bytes"],
                missing=family["missing_payload_metadata_units"],
                categories=compact_counts(family["category_counts"]),
                outputs=compact_counts(family["output_kind_counts"]),
                runtime=family["runtime_contract"],
            )
        )

    lines.extend(["", "## Known Runtime Shapes", ""])
    for shape in contract["known_runtime_shapes"]:
        lines.append(f"- `{shape['id']}`: {shape['shape']} Source: `{shape['source']}`.")

    lines.extend(["", "## Runtime Subrange Contracts", ""])
    lines.append("| Subrange | Range | Status | Contract | Evidence |")
    lines.append("| --- | --- | --- | --- | --- |")
    for subrange in contract["subrange_contracts"]:
        lines.append(
            "| `{id}` | `{range}` | `{status}` | {contract_text} | {evidence} |".format(
                id=subrange["id"],
                range=subrange["range"],
                status=subrange["status"],
                contract_text=subrange["contract"],
                evidence=subrange["evidence"],
            )
        )

    lines.extend(["", "## Per-Family Assets", ""])
    for family in contract["families"]:
        lines.append(f"### {family['label']}")
        lines.append("")
        lines.append(f"- portable contract: {family['portable_contract']}")
        if family["docs"]:
            lines.append(f"- checked docs: {', '.join(f'`{doc}`' for doc in family['docs'])}")
        lines.append("")
        lines.append("| Asset | Range | Bytes | Outputs | Notes |")
        lines.append("| --- | --- | ---: | --- | --- |")
        for asset in family["assets"]:
            notes = []
            if asset["missing_payload_metadata_units"]:
                notes.append(f"{asset['missing_payload_metadata_units']} missing yml metadata unit(s)")
            if asset["category"] in {"raw-gap", "raw-table"}:
                notes.append(str(asset["category"]))
            lines.append(
                "| `{id}` | `{range}` | {bytes} | {outputs} | {notes} |".format(
                    id=asset["id"],
                    range=asset["range"],
                    bytes=asset["bytes"],
                    outputs=", ".join(f"`{kind}`" for kind in asset["output_kinds"]) or "-",
                    notes=", ".join(notes) or "-",
                )
            )
        lines.append("")

    lines.extend(["## Next Open Questions", ""])
    for question in contract["next_open_questions"]:
        lines.append(f"- {question}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build E0/E1 UI/font/town-map asset contract seeds.")
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
        "ui/font/town-map contracts: "
        f"{totals['assets']} assets, "
        f"{totals['families']} families, "
        f"{totals['missing_payload_metadata_units']} missing metadata units"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
