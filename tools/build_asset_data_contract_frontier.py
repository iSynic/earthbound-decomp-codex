from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST_DIR = ROOT / "asset-manifests"
DEFAULT_JSON_OUT = ROOT / "build" / "asset-data-contract-frontier.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "asset-data-contract-frontier.md"

CONTRACT_COVERED_INFERRED_PAYLOAD_METADATA_BY_BANK = {
    "E0": 1,
    "E1": 4,
}


CONTRACT_FAMILIES: list[dict[str, Any]] = [
    {
        "id": "battle_visual_assets",
        "label": "Battle visual assets",
        "banks": ["CA", "CB", "CC", "CD", "CE"],
        "maturity": "contract-seeded",
        "proof": "extraction manifests, decompression recipes, preview recipes, per-bank asset maps, generated battle visual contracts, battle-background scene-layer joins, PSI animation bundle joins, battle sprite graphics/palette usage joins, and swirl sequence joins",
        "docs": [
            "notes/battle-background-scene-bundles.md",
            "notes/psi-animation-bundle-contracts.md",
            "notes/battle-sprite-bundle-contracts.md",
            "notes/swirl-sequence-bundle-contracts.md",
            "notes/battle-visual-asset-contracts.md",
            "notes/bank-ca-cf-asset-closure.md",
            "notes/bank-ca-asset-data-map.md",
            "notes/bank-cb-asset-data-map.md",
            "notes/bank-cc-asset-data-map.md",
            "notes/bank-cd-asset-data-map.md",
            "notes/bank-ce-asset-data-map.md",
        ],
        "next_contract": "Major battle visual joins are covered for phase 4; remaining work is optional alias polish, the Evil Eye sprite-id-110 edge, and optional internal swirl payload decoding.",
    },
    {
        "id": "mixed_asset_tables",
        "label": "Mixed asset/table banks",
        "banks": ["CF", "D0"],
        "maturity": "contract-backed-with-known-followups",
        "proof": "table split manifests, source scaffolds, CF door-data, movement-trigger source-emission, sector-list, and event-music context/source-emission contracts, and D0 tile-event plus placement/battle variable-list contracts with BTL entry distribution and unpointed-gap accounting cover the highest-risk variable-list subrecords",
        "docs": [
            "notes/bank-cf-asset-data-map.md",
            "notes/bank-d0-asset-data-map.md",
            "notes/cf-door-data-contracts.md",
            "notes/cf-movement-trigger-contracts.md",
            "notes/cf-sector-list-contracts.md",
            "notes/cf-event-music-context-contracts.md",
            "notes/d0-tile-event-contracts.md",
            "notes/d0-variable-list-contracts.md",
        ],
        "next_contract": "CF/D0 table contracts are now useful for source planning; remaining polish is generated source-emission polish, preserving the D0 battle-group gap and CF type-5 no-op numeric payloads, plus optional gameplay labels for the already-bounded CF trigger selectors.",
    },
    {
        "id": "overworld_sprites",
        "label": "Overworld sprites",
        "banks": ["D1", "D2", "D3", "D4", "D5"],
        "maturity": "contract-backed",
        "proof": "group, frame, animation-role, pointer-flag, and preview contracts cover the D1-D5 sprite payloads; D5 table splits and timed-delivery row/source-window contracts cover its post-sprite data tail",
        "docs": [
            "notes/overworld-sprite-group-contracts.md",
            "notes/overworld-sprite-frame-semantics.md",
            "notes/overworld-sprite-animation-roles.md",
            "notes/overworld-sprite-pointer-flag-semantics.md",
            "notes/secondary-visual-descriptor-contracts.md",
            "notes/d5-table-splits.md",
            "notes/d5-timed-delivery-row-contracts.md",
        ],
        "next_contract": "Only polish alias labels, D5 story-specific timed-delivery row labels, and unowned payload explanations as needed for contributor ergonomics.",
    },
    {
        "id": "map_tilesets_and_runtime_tables",
        "label": "Map tilesets and runtime tables",
        "banks": ["D6", "D7", "D8", "D9", "DA", "DB", "DC", "DD", "DE", "DF"],
        "maturity": "contract-backed-with-known-followups",
        "proof": "map object, sector, D7 sector metadata with source-emission/value-count summaries, DA palette subrecords plus metadata/script usage summaries, DC current-position music selector plus numeric-preserve second-plane source-emission summaries, tileset, FTS, D8 collision subrecords with source-emission/value-count summaries, palette, movement, sprite-usage, DF landing palette-animation source-emission rows, and scene-composition contracts exist",
        "docs": [
            "notes/map-milestone-closure.md",
            "notes/map-object-bundles.md",
            "notes/map-sector-bundles.md",
            "notes/cf-event-music-context-contracts.md",
            "notes/d7-sector-metadata-contracts.md",
            "notes/map-tileset-bundles.md",
            "notes/map-fts-format-audit.md",
            "notes/da-map-palette-subrecord-contracts.md",
            "notes/d8-collision-subrecord-contracts.md",
            "notes/map-collision-pointer-contract.md",
            "notes/map-collision-runtime-bit-contract.md",
            "notes/map-palette-descriptor-context.md",
            "notes/bank-df-first-pass.md",
            "notes/df-landing-palette-animation-contracts.md",
            "notes/map-scene-composition-contract.md",
        ],
        "next_contract": "Map contracts are phase-good-enough: D7 sector metadata source-emission rows/value counts, D8 collision source-emission rows/value counts, DA palette subrecords/script joins, DF landing palette profile/payload source-emission rows, and the DC current-position event-music selector plus second-plane numeric-preserve policy are contract-backed, while D7/DC unresolved planes are value-bounded without promoted names; collision low modifier labels, DA event-palette selector runtime behavior, DF profile names, and remaining D7 high-bit/DC second-plane semantics are deferred caller-evidence polish.",
    },
    {
        "id": "ui_font_town_map_assets",
        "label": "UI, fonts, and town-map assets",
        "banks": ["E0", "E1"],
        "maturity": "contract-backed-with-known-followups",
        "proof": "raw/decompressed/preview recipes exist, and the generated UI/font/town-map contract groups assets by runtime-facing family with source-emission rows for E0 text-window selector/palette tables, E0 town-map graphics pointers, E1 town-map descriptor/pointer/blink/variable placement lists, title palette animation subpayloads, title-letter OAM rows, landing/cast visual bundles, and the E0 SRAM save-block template",
        "docs": [
            "notes/ui-font-town-map-asset-contracts.md",
            "notes/text-window-skin-bundle-contracts.md",
            "notes/font-bundle-contracts.md",
            "notes/intro-title-visual-bundle-contracts.md",
            "notes/title-screen-palette-animation-contracts.md",
            "notes/title-screen-letter-oam-contracts.md",
            "notes/landing-cast-visual-contracts.md",
            "notes/sram-template-contracts.md",
            "notes/bank-e0-asset-data-map.md",
            "notes/bank-e1-asset-data-map.md",
            "notes/town-map-selection-rendering-c4d274-c4d744.md",
            "notes/your-sanctuary-location-coordinate-table-c4de78.md",
        ],
        "next_contract": "UI/font/town-map contracts are phase-good-enough for source emission: variable-list town-map rows, title palette/OAM rows, landing/cast visual bundles, and SRAM template blocks have preserve policies. Remaining palette-row, renderer-control flag, flyover/credits/photographer, and public-facing scene names are bounded semantic polish.",
    },
    {
        "id": "audio_packs",
        "label": "Audio packs",
        "banks": ["E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "EA", "EB", "EC", "ED", "EE"],
        "maturity": "raw-pack-manifest",
        "proof": "audio pack ranges are byte-accounted and extractable as user-ROM-derived raw packs",
        "docs": [
            "notes/bank-e2-ee-audio-pack-run.md",
            "notes/bank-e2-asset-data-map.md",
            "notes/bank-ee-asset-data-map.md",
        ],
        "next_contract": "Split EBM/audio packs into pack, sample, sequence, and pointer contracts once the format boundary is selected.",
    },
    {
        "id": "ef_debug_and_late_tail",
        "label": "EF debug and late-tail data",
        "banks": ["EF"],
        "maturity": "seed-contract",
        "proof": "debug font/cursor assets are identified; the large front mixed corridor is intentionally coarse",
        "docs": [
            "notes/bank-ef-asset-data-map.md",
            "src/ef/bank_ef_helpers_asar.asm",
        ],
        "next_contract": "Split EF front mixed data/code into save/debug/map/tile/sprite/text contracts as EF semantics are refined.",
    },
]


def load_manifests(manifest_dir: Path) -> list[dict[str, Any]]:
    manifests = []
    for path in sorted(manifest_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        bank = infer_bank(path.name, data)
        manifests.append({"path": path, "bank": bank, "data": data})
    return manifests


def infer_bank(filename: str, data: dict[str, Any]) -> str:
    if filename.startswith("bank-"):
        return filename.split("-", 2)[1].upper()
    if filename.startswith("ef-"):
        return "EF"
    title = str(data.get("title", ""))
    for token in title.replace("-", " ").split():
        if len(token) == 2:
            try:
                int(token, 16)
            except ValueError:
                continue
            return token.upper()
    raise ValueError(f"Could not infer bank for {filename}")


def existing_docs(paths: list[str]) -> list[str]:
    return [path for path in paths if (ROOT / path).exists()]


def missing_docs(paths: list[str]) -> list[str]:
    return [path for path in paths if not (ROOT / path).exists()]


def summarize_manifest(entry: dict[str, Any]) -> dict[str, Any]:
    data = entry["data"]
    assets = data.get("assets", [])
    if not isinstance(assets, list):
        raise ValueError(f"Manifest assets must be a list: {entry['path']}")

    category_counts: Counter[str] = Counter()
    output_kind_counts: Counter[str] = Counter()
    source_bytes = 0
    assets_with_previews = 0
    assets_with_decoders = 0

    for asset in assets:
        if not isinstance(asset, dict):
            continue
        category_counts[str(asset.get("category", "unknown"))] += 1
        source = asset.get("source", {})
        if isinstance(source, dict):
            source_bytes += int(source.get("bytes", 0) or 0)
        outputs = asset.get("outputs", [])
        if not isinstance(outputs, list):
            outputs = []
        kinds = [str(output.get("kind", "unknown")) for output in outputs if isinstance(output, dict)]
        output_kind_counts.update(kinds)
        if any("png" in kind or "preview" in kind or "swatch" in kind for kind in kinds):
            assets_with_previews += 1
        if any(kind not in {"raw"} for kind in kinds):
            assets_with_decoders += 1

    bank_summary = data.get("bank_summary", {})
    if not isinstance(bank_summary, dict):
        bank_summary = {}
    missing_payload_metadata = int(bank_summary.get("missing_payload_metadata", 0) or 0)
    contract_covered_inferred_payload_metadata = min(
        missing_payload_metadata,
        CONTRACT_COVERED_INFERRED_PAYLOAD_METADATA_BY_BANK.get(entry["bank"], 0),
    )

    return {
        "bank": entry["bank"],
        "manifest_path": rel(entry["path"]),
        "asset_count": len(assets),
        "source_bytes": source_bytes,
        "output_recipe_count": sum(output_kind_counts.values()),
        "category_counts": dict(sorted(category_counts.items())),
        "output_kind_counts": dict(sorted(output_kind_counts.items())),
        "assets_with_previews": assets_with_previews,
        "assets_with_decoders": assets_with_decoders,
        "binary_assets": int(bank_summary.get("binary_assets", 0) or 0),
        "binary_asset_bytes": int(bank_summary.get("binary_asset_bytes", 0) or 0),
        "table_includes": int(bank_summary.get("table_includes", 0) or 0),
        "table_bytes": int(bank_summary.get("table_bytes", 0) or 0),
        "coverage_gaps": int(bank_summary.get("coverage_gaps", 0) or 0),
        "coverage_gap_bytes": int(bank_summary.get("coverage_gap_bytes", 0) or 0),
        "manifest_inferred_payload_metadata": missing_payload_metadata,
        "contract_covered_inferred_payload_metadata": contract_covered_inferred_payload_metadata,
        "unresolved_missing_payload_metadata": max(
            0, missing_payload_metadata - contract_covered_inferred_payload_metadata
        ),
    }


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def family_for_bank(bank: str) -> dict[str, Any]:
    for family in CONTRACT_FAMILIES:
        if bank in family["banks"]:
            return family
    raise ValueError(f"No contract family for bank {bank}")


def build_frontier(manifest_dir: Path) -> dict[str, Any]:
    manifests = load_manifests(manifest_dir)
    bank_summaries = [summarize_manifest(entry) for entry in manifests]
    bank_summaries.sort(key=lambda item: item["bank"])
    banks_by_id = {summary["bank"]: summary for summary in bank_summaries}

    families = []
    for family in CONTRACT_FAMILIES:
        family_banks = [banks_by_id[bank] for bank in family["banks"] if bank in banks_by_id]
        category_counts: Counter[str] = Counter()
        output_kind_counts: Counter[str] = Counter()
        for bank in family_banks:
            category_counts.update(bank["category_counts"])
            output_kind_counts.update(bank["output_kind_counts"])
        families.append(
            {
                "id": family["id"],
                "label": family["label"],
                "banks": family["banks"],
                "maturity": family["maturity"],
                "proof": family["proof"],
                "docs": existing_docs(family["docs"]),
                "missing_docs": missing_docs(family["docs"]),
                "next_contract": family["next_contract"],
                "asset_count": sum(int(bank["asset_count"]) for bank in family_banks),
                "source_bytes": sum(int(bank["source_bytes"]) for bank in family_banks),
                "output_recipe_count": sum(int(bank["output_recipe_count"]) for bank in family_banks),
                "coverage_gap_bytes": sum(int(bank["coverage_gap_bytes"]) for bank in family_banks),
                "manifest_inferred_payload_metadata": sum(
                    int(bank["manifest_inferred_payload_metadata"]) for bank in family_banks
                ),
                "contract_covered_inferred_payload_metadata": sum(
                    int(bank["contract_covered_inferred_payload_metadata"]) for bank in family_banks
                ),
                "unresolved_missing_payload_metadata": sum(
                    int(bank["unresolved_missing_payload_metadata"]) for bank in family_banks
                ),
                "category_counts": dict(sorted(category_counts.items())),
                "output_kind_counts": dict(sorted(output_kind_counts.items())),
            }
        )

    totals = {
        "manifests": len(bank_summaries),
        "assets": sum(int(bank["asset_count"]) for bank in bank_summaries),
        "source_bytes": sum(int(bank["source_bytes"]) for bank in bank_summaries),
        "output_recipes": sum(int(bank["output_recipe_count"]) for bank in bank_summaries),
        "assets_with_previews": sum(int(bank["assets_with_previews"]) for bank in bank_summaries),
        "assets_with_decoders": sum(int(bank["assets_with_decoders"]) for bank in bank_summaries),
        "coverage_gap_bytes": sum(int(bank["coverage_gap_bytes"]) for bank in bank_summaries),
        "manifest_inferred_payload_metadata": sum(
            int(bank["manifest_inferred_payload_metadata"]) for bank in bank_summaries
        ),
        "contract_covered_inferred_payload_metadata": sum(
            int(bank["contract_covered_inferred_payload_metadata"]) for bank in bank_summaries
        ),
        "unresolved_missing_payload_metadata": sum(
            int(bank["unresolved_missing_payload_metadata"]) for bank in bank_summaries
        ),
    }
    totals["maturity_counts"] = dict(Counter(family["maturity"] for family in families))

    for bank in bank_summaries:
        family = family_for_bank(bank["bank"])
        bank["contract_family"] = family["id"]
        bank["contract_maturity"] = family["maturity"]

    return {
        "schema": "earthbound-decomp.asset-data-contract-frontier.v1",
        "source": {
            "manifest_dir": rel(manifest_dir),
            "tracked_markdown": rel(DEFAULT_MARKDOWN_OUT),
            "generated_json": rel(DEFAULT_JSON_OUT),
            "rom_outputs_policy": "Generated ROM-derived outputs remain under ignored build/assets and are not required to build this report.",
        },
        "totals": totals,
        "families": families,
        "banks": bank_summaries,
        "recommended_next_manual_seams": [
            {
                "rank": 1,
                "family": "ui_font_town_map_assets",
                "why": "Phase-good-enough source-emission rows now cover text-window palettes, town-map pointers and variable icon lists, title palette/OAM tables, landing/cast bundles, and SRAM template blocks. Remaining work is narrow semantic naming, not asset/data discovery.",
            },
            {
                "rank": 2,
                "family": "battle_visual_assets",
                "why": "Phase-good-enough contract-seeded; battle backgrounds, PSI animations, battle sprites, and swirls now have joins. Remaining work is optional alias/internal decode polish.",
            },
            {
                "rank": 3,
                "family": "map_tilesets_and_runtime_tables",
                "why": "The map milestone is phase-good-enough; D7 and DC unresolved planes now have numeric-preserve source-emission policy, while DA event-palette selector dispatch remains bounded runtime-semantics polish.",
            },
            {
                "rank": 4,
                "family": "audio_packs",
                "why": "Large byte volume remains raw-pack level; defer until we choose an audio-pack contract boundary.",
            },
        ],
    }


def compact_counts(counts: dict[str, int], limit: int = 4) -> str:
    if not counts:
        return "-"
    parts = []
    for key, value in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]:
        parts.append(f"`{key}` {value}")
    remaining = len(counts) - limit
    if remaining > 0:
        parts.append(f"+{remaining} more")
    return ", ".join(parts)


def render_markdown(frontier: dict[str, Any]) -> str:
    totals = frontier["totals"]
    lines = [
        "# Asset/Data Contract Frontier",
        "",
        "Generated by `tools/build_asset_data_contract_frontier.py` from checked-in `asset-manifests/*.json` and contract notes. It is a phase-4 planning map: it separates byte-accounted asset data from families that already have semantic/runtime contracts.",
        "",
        "ROM-derived asset outputs are still local-only under ignored `build/assets`; this report uses manifest metadata and checked-in docs only.",
        "",
        "## Snapshot",
        "",
        f"- manifests: `{totals['manifests']}`",
        f"- assets/tables/gaps represented: `{totals['assets']}`",
        f"- source bytes represented by manifests: `{totals['source_bytes']}`",
        f"- output recipes: `{totals['output_recipes']}`",
        f"- assets with preview/swatch recipes: `{totals['assets_with_previews']}`",
        f"- assets with decoder recipes beyond raw extraction: `{totals['assets_with_decoders']}`",
        f"- coverage gap bytes still represented as raw gaps: `{totals['coverage_gap_bytes']}`",
        f"- manifest-inferred payload metadata count: `{totals['manifest_inferred_payload_metadata']}`",
        f"- contract-covered inferred payload metadata count: `{totals['contract_covered_inferred_payload_metadata']}`",
        f"- unresolved missing payload metadata count: `{totals['unresolved_missing_payload_metadata']}`",
        "",
        "## Family Frontier",
        "",
        "| Family | Banks | Maturity | Assets | Bytes | Gap bytes | Inferred metadata | Contract-covered | Unresolved metadata | Next contract |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for family in frontier["families"]:
        lines.append(
            "| {label} | `{banks}` | `{maturity}` | {assets} | {bytes} | {gap_bytes} | {inferred} | {covered} | {unresolved} | {next_contract} |".format(
                label=family["label"],
                banks=", ".join(family["banks"]),
                maturity=family["maturity"],
                assets=family["asset_count"],
                bytes=family["source_bytes"],
                gap_bytes=family["coverage_gap_bytes"],
                inferred=family["manifest_inferred_payload_metadata"],
                covered=family["contract_covered_inferred_payload_metadata"],
                unresolved=family["unresolved_missing_payload_metadata"],
                next_contract=family["next_contract"],
            )
        )

    lines.extend(
        [
            "",
            "## Contract Proofs",
            "",
        ]
    )
    for family in frontier["families"]:
        lines.append(f"### {family['label']}")
        lines.append("")
        lines.append(f"- maturity: `{family['maturity']}`")
        lines.append(f"- proof: {family['proof']}")
        if family["docs"]:
            lines.append(f"- checked docs: {', '.join(f'`{doc}`' for doc in family['docs'])}")
        if family["missing_docs"]:
            lines.append(f"- expected docs not found: {', '.join(f'`{doc}`' for doc in family['missing_docs'])}")
        lines.append(f"- category mix: {compact_counts(family['category_counts'])}")
        lines.append(f"- output recipe mix: {compact_counts(family['output_kind_counts'])}")
        lines.append("")

    lines.extend(
        [
            "## Per-Bank Pressure Map",
            "",
            "| Bank | Family | Maturity | Assets | Bytes | Recipes | Categories | Output mix | Gaps | Unresolved metadata |",
            "| --- | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: |",
        ]
    )
    for bank in frontier["banks"]:
        lines.append(
            "| `{bank}` | `{family}` | `{maturity}` | {assets} | {bytes} | {recipes} | {categories} | {outputs} | {gaps} | {missing} |".format(
                bank=bank["bank"],
                family=bank["contract_family"],
                maturity=bank["contract_maturity"],
                assets=bank["asset_count"],
                bytes=bank["source_bytes"],
                recipes=bank["output_recipe_count"],
                categories=compact_counts(bank["category_counts"], limit=3),
                outputs=compact_counts(bank["output_kind_counts"], limit=3),
                gaps=bank["coverage_gap_bytes"],
                missing=bank["unresolved_missing_payload_metadata"],
            )
        )

    lines.extend(
        [
            "",
            "## Recommended Next Manual Seams",
            "",
        ]
    )
    for item in frontier["recommended_next_manual_seams"]:
        lines.append(f"{item['rank']}. `{item['family']}`: {item['why']}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the asset/data contract frontier report.")
    parser.add_argument("--manifest-dir", default=str(DEFAULT_MANIFEST_DIR))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    args = parser.parse_args()

    manifest_dir = Path(args.manifest_dir)
    frontier = build_frontier(manifest_dir)

    json_out = Path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(frontier, indent=2) + "\n", encoding="utf-8")

    markdown_out = Path(args.markdown_out)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(render_markdown(frontier), encoding="utf-8")

    totals = frontier["totals"]
    print(
        "asset/data contract frontier: "
        f"{totals['manifests']} manifests, "
        f"{totals['assets']} assets, "
        f"{totals['output_recipes']} recipes, "
        f"{totals['coverage_gap_bytes']} gap bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
