from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSON_OUT = ROOT / "build" / "ui-font-town-map-asset-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "ui-font-town-map-asset-contracts.md"
E1_SCAFFOLD = ROOT / "src" / "e1" / "bank_e1_helpers_asar.asm"


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
            "notes/text-window-skin-bundle-contracts.md",
            "notes/text-window-rendering-primitives-c1078d-c10d7c.md",
            "notes/active-window-text-tile-pair-placement-c44c8c.md",
            "notes/text-token-glyph-run-stager-c44b3a-c44e61.md",
        ],
    },
    "font_sets": {
        "label": "Font data and glyph graphics",
        "runtime_contract": "Font data assets are fixed-width metric/spacing rows paired with raw or 4bpp glyph graphics consumed by the text and presentation renderers.",
        "portable_contract": "Expose each metric-backed font as `font.N` bundles with metric bytes, glyph graphics, preview refs, and support-font status for graphics-only scene fonts.",
        "docs": [
            "notes/font-bundle-contracts.md",
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
        "portable_contract": "Expose each visual scene as arrangement/graphics/palette components with title palette-animation and OAM subcontracts.",
        "docs": [
            "notes/intro-title-visual-bundle-contracts.md",
            "notes/title-screen-palette-animation-contracts.md",
            "notes/title-screen-letter-oam-contracts.md",
            "notes/gas-station-intro-asset-loader-c4a377.md",
            "notes/intro-logo-wait-and-gas-station-helpers-c0efe1-c0f21e.md",
            "notes/visual-record-walkers-and-naming-remap-c4cc2f-c4d065.md",
        ],
    },
    "landing_display_visuals": {
        "label": "Saved-coordinate landing display visuals",
        "runtime_contract": "C4:C2DE decompresses E1:CFAF, E1:D5E8, and E1:D4F4 as the saved-coordinate landing display graphics, arrangement, and palette bundle.",
        "portable_contract": "Expose as a landing display scene bundle with graphics, BG tile arrangement, and palette components.",
        "docs": [
            "notes/landing-cast-visual-contracts.md",
            "notes/saved-landing-display-stage-c4c2de-c4c64d.md",
        ],
    },
    "ending_cast_visuals": {
        "label": "Ending cast-name visuals",
        "runtime_contract": "C4:E369 loads E1:D6E1, E1:D815, E1:D835, and E1:E4E6 into the ending cast-name display path.",
        "portable_contract": "Expose as an ending cast-name bundle with prelude graphics, support-table bytes, cast-name glyph graphics, and palette data.",
        "docs": [
            "notes/landing-cast-visual-contracts.md",
            "notes/cast-scene-scroll-helpers-c4e4da-c4e583.md",
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
    "sram_save_template": {
        "label": "Compressed SRAM save-block template",
        "runtime_contract": "E0:09B4 decompresses to eight 0x500-byte save_block records; EF save helpers use blocks 0/1, 2/3, and 4/5 as three primary/backup user save-slot pairs, while blocks 6/7 are preserved reserve template records outside the retail slot loops.",
        "portable_contract": "Expose as a save-template bundle with compressed ROM provenance, decoded block inventory, three slot-pair records, checksum algorithms, and preserved reserve blocks.",
        "docs": [
            "notes/sram-template-contracts.md",
            "notes/bank-e0-asset-data-map.md",
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
        return "sram_save_template"
    if "font" in asset_id or "font" in title or "romaji" in asset_id or "mrsaturn" in asset_id:
        return "font_sets"
    if "text_window" in asset_id or "flavoured_text" in asset_id or "movement_text_string_palette" in notes_text(asset).lower():
        return "text_window_skin"
    if any(token in asset_id for token in ["unknown_e1cfaf", "unknown_e1d4f4", "unknown_e1d5e8"]):
        return "landing_display_visuals"
    if any(
        token in asset_id
        for token in ["unknown_e1d6e1", "data_unknown_e1d815", "cast_names_gfx", "unknown_e1e4e6"]
    ):
        return "ending_cast_visuals"
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
    town_map_tables = build_town_map_table_contracts()
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
                "shape": "E1:F491 points to placement records (x, y, icon id, event flag word), while icon ids map through E1:F44C to E1:F203 five-byte graphics descriptor lists: signed y offset, tile/attribute word, signed x offset, and control flags.",
            },
            {
                "id": "town_map_icon_animation",
                "source": "notes/town-map-selection-rendering-c4d274-c4d744.md",
                "shape": "E1:F44C maps town-map icon ids, E1:F47A suppresses blink-phase icons, and C4:D2A8 cycles CGRAM entries 0x81..0x86.",
            },
            {
                "id": "font_metric_pairs",
                "source": "notes/font-bundle-contracts.md",
                "shape": "Main, Mr. Saturn, large, battle, and tiny fonts each have a 96-byte metric table matched to EBDecomp width refs and paired with raw 4bpp glyph graphics; battle and tiny share the same first-96 metrics but use different graphics sizes.",
            },
            {
                "id": "text_window_skin_bundle",
                "source": "notes/text-window-skin-bundle-contracts.md",
                "shape": "E0:1FB9 selector rows map five selectable window flavours to 0x40-byte palette blocks at E0:1FC8; block 5 is the lead-entity override at E0:2108, block 6 is an EBDecomp-rendered extra block with no known source-backed selector, and the movement-text palette row remains a separate system row.",
            },
            {
                "id": "intro_title_visual_bundles",
                "source": "notes/intro-title-visual-bundle-contracts.md",
                "shape": "E1 intro/title payloads now split into six scene bundles: APE, HALKEN, Nintendo, War-on-Giygas/gas-station, presented/produced-by attract cards, and title screen; E1:AE7C and E1:CE08 are further promoted to title palette animation and TitleScreenLetterOAMData contracts.",
            },
            {
                "id": "landing_cast_visual_bundles",
                "source": "notes/landing-cast-visual-contracts.md",
                "shape": "E1:CFAF/D5E8/D4F4 are the C4:C2DE saved-coordinate landing display graphics/arrangement/palette bundle, while E1:D6E1..D815, E1:D815..D835, E1:D835..E4E6, and E1:E4E6..E528 belong to the C4:E369 ending cast-name visual path.",
            },
            {
                "id": "sram_save_template",
                "source": "notes/sram-template-contracts.md",
                "shape": "E0 COMPRESSED_SRAM decompresses to 0x2800 bytes: eight 0x500-byte ebsrc `save_block` records, with three runtime user save-slot primary/backup pairs, checksum/complement fields verified against EF:0734/077B, and two preserved reserve records outside the retail slot loops.",
            },
        ],
        "subrange_contracts": [
            {
                "id": "text_window_flavor_selector_table",
                "family": "text_window_skin",
                "range": "E0:1FB9..E0:1FC8",
                "status": "runtime-corroborated",
                "contract": "Five 3-byte selector records; C4:7F87 and C1:9D49 use the low word as an offset from E0:1FC8 for the current text-window flavour.",
                "evidence": "notes/text-window-skin-bundle-contracts.md validates the offsets against EBDecomp flavour names and the local C1/C4 callers.",
            },
            {
                "id": "text_window_palette_blocks",
                "family": "text_window_skin",
                "range": "E0:1FC8..E0:2188",
                "status": "runtime-corroborated",
                "contract": "Seven 0x40-byte palette blocks, each split into eight four-colour rows; the first five are selectable flavours, block 5 is the documented lead-entity override, and block 6 is preserved as an unused/nonselectable extra system block.",
                "evidence": "C4:7F87 copies whole 0x40-byte blocks to $0200; C1:9D49 copies selected block row +$18 to $0218; EBDecomp renders block 6 as Windows1_6/Windows2_6, but the source-backed C0/C1/C4/EF palette refresh paths do not select E0:2148.",
            },
            {
                "id": "movement_text_string_palette",
                "family": "text_window_skin",
                "range": "E0:2188..E0:2190",
                "status": "structural-split",
                "contract": "Standalone eight-byte movement-text palette row after the seven window palette blocks.",
                "evidence": "notes/bank-e0-asset-data-map.md identifies this source include as covered by the combined generated E0 table span.",
            },
            {
                "id": "town_map_gfx_pointer_table",
                "family": "town_maps",
                "range": "E0:2190..E0:21A8",
                "status": "runtime-corroborated",
                "contract": "Six-entry town-map graphics pointer table consumed by C4:D553 before decompressing the selected E0 town-map payload.",
                "evidence": "C4:D553 indexes E0:2190 from the zero-based town-map id in notes/town-map-selection-rendering-c4d274-c4d744.md.",
            },
            {
                "id": "town_map_icon_graphic_descriptor_lists",
                "family": "town_maps",
                "range": "E1:F203..E1:F44C",
                "status": "structural-runtime-corroborated",
                "contract": "Twenty-two unique five-byte icon graphics descriptor lists, totaling 117 records. Each record is y offset, tile/attribute word, x offset, and a control byte; bit 7 marks the final descriptor in a list and bit 0 feeds C0:8CD5's packed mask/attribute bit.",
                "evidence": "The span splits exactly on every pointer target from E1:F44C; C4:D2F0 and C4:D43F select icon ids before remapping them through the pointer table, and C0:8CD5 consumes the five-byte row shape while drawing relative to the submitted base X/Y.",
            },
            {
                "id": "town_map_icon_graphic_pointer_table",
                "family": "town_maps",
                "range": "E1:F44C..E1:F47A",
                "status": "runtime-corroborated",
                "contract": "Twenty-three 16-bit local pointers mapping town-map icon ids to E1:F203 five-byte graphics descriptor lists.",
                "evidence": "C4 town-map overlay/static renderers map icon ids through E1:F44C.",
            },
            {
                "id": "town_map_blink_suppress_table",
                "family": "town_maps",
                "range": "E1:F47A..E1:F491",
                "status": "runtime-corroborated",
                "contract": "Twenty-three one-byte blink/suppression flags checked before static icon drawing; nonzero entries suppress icons while $B4AE is in the hidden phase.",
                "evidence": "C4:D43F checks E1:F47A before the event-flag test.",
            },
            {
                "id": "town_map_icon_placement_pointer_table",
                "family": "town_maps",
                "range": "E1:F491..E1:F4A9",
                "status": "runtime-corroborated",
                "contract": "Six four-byte long-pointer entries, one per town map, pointing to placement lists in E1:F4A9..E1:F581.",
                "evidence": "C4:D43F indexes a pointer table at E1:F491 for the selected zero-based town-map id; checked-in bytes resolve to E1:F4A9, E1:F4CD, E1:F4F6, E1:F524, E1:F548, and E1:F562.",
            },
            {
                "id": "town_map_icon_placement_records",
                "family": "town_maps",
                "range": "E1:F4A9..E1:F581",
                "status": "runtime-corroborated-shape",
                "contract": "Six variable icon lists with 42 total five-byte records, terminated by FF: x, y, icon id, and event flag word with high-bit draw polarity.",
                "evidence": "C4:D43F walks records until FF and interprets the five-byte record shape documented in notes/town-map-selection-rendering-c4d274-c4d744.md.",
            },
        ],
        "derived_town_map_tables": town_map_tables,
        "next_open_questions": [
            "Name the seven per-block text-window palette row roles beyond the known +$18 equipment/status row.",
            "Confirm whether SRAM template blocks 6 and 7 have any non-retail, prototype, or tool-facing use before treating them as generated reserve records.",
            "Pin C0:8CD5 control-byte bit 0 as a renderer priority/mask/attribute bit after following the final staging buffer consumer.",
        ],
    }


def extract_scaffold_range(org: str, end_label: str) -> list[int]:
    text = E1_SCAFFOLD.read_text(encoding="utf-8")
    start = text.index(f"org ${org}")
    end = text.index(f"\n{end_label}:", start)
    values: list[int] = []
    for line in text[start:end].splitlines():
        line = line.strip()
        if line.startswith("db "):
            values.extend(int(token[1:], 16) for token in re.findall(r"\$[0-9A-Fa-f]{2}", line))
    return values


def build_town_map_table_contracts() -> dict[str, Any]:
    values = extract_scaffold_range("E1F203", "E1F581_TableE1f203End")
    base = 0xF203

    descriptor_values = values[: 0xF44C - base]
    descriptor_records = [
        descriptor_values[index : index + 5] for index in range(0, len(descriptor_values), 5)
    ]

    icon_pointer_offset = 0xF44C - base
    icon_pointers = []
    for index in range((0xF47A - 0xF44C) // 2):
        lo, hi = values[icon_pointer_offset + index * 2 : icon_pointer_offset + index * 2 + 2]
        icon_pointers.append(hi << 8 | lo)

    icon_list_ranges = []
    unique_starts = sorted(set(icon_pointers))
    for start, end in zip(unique_starts, unique_starts[1:] + [0xF44C]):
        icon_list_ranges.append(
            {
                "range": f"E1:{start:04X}..E1:{end:04X}",
                "record_count": (end - start) // 5,
                "record_size": 5,
            }
        )

    blink_flags = values[0xF47A - base : 0xF491 - base]

    placement_pointer_offset = 0xF491 - base
    placement_pointers = []
    for index in range(6):
        lo, hi, bank, zero = values[placement_pointer_offset + index * 4 : placement_pointer_offset + index * 4 + 4]
        placement_pointers.append({"index": index, "target": f"{bank:02X}:{(hi << 8 | lo):04X}", "zero": zero})

    placement_lists = []
    for pointer in placement_pointers:
        target_bank, target_address = str(pointer["target"]).split(":")
        if target_bank != "E1":
            raise ValueError(f"Unexpected town-map placement pointer bank: {pointer['target']}")
        offset = int(target_address, 16) - base
        records = []
        cursor = offset
        while cursor < len(values):
            if values[cursor] == 0xFF:
                break
            x, y, icon_id, flag_lo, flag_hi = values[cursor : cursor + 5]
            flag = flag_hi << 8 | flag_lo
            records.append(
                {
                    "range": f"E1:{base + cursor:04X}..E1:{base + cursor + 5:04X}",
                    "x": x,
                    "y": y,
                    "icon_id": icon_id,
                    "event_flag": flag & 0x7FFF,
                    "draw_when_flag_set": bool(flag & 0x8000),
                }
            )
            cursor += 5
        placement_lists.append(
            {
                "index": int(pointer["index"]),
                "target": pointer["target"],
                "record_count": len(records),
                "terminator": f"E1:{base + cursor:04X}",
                "records": records,
            }
        )

    return {
        "source": rel(E1_SCAFFOLD),
        "icon_graphic_descriptor_lists": {
            "range": "E1:F203..E1:F44C",
            "record_size": 5,
            "record_count": (0xF44C - 0xF203) // 5,
            "unique_list_count": len(unique_starts),
            "icon_slot_count": len(icon_pointers),
            "record_shape": [
                {
                    "offset": 0,
                    "name": "relative_y_offset",
                    "size": 1,
                    "signed": True,
                    "role": "Signed Y offset added to the base Y submitted to C0:8C54/C0:8CD5, then decremented for renderer staging. Generic value $80 enters a renderer control branch, but it is not present in the E1 town-map icon descriptors.",
                },
                {
                    "offset": 1,
                    "name": "tile_attribute_word",
                    "size": 2,
                    "signed": False,
                    "role": "Tile/attribute word copied by C0:8CD5 into the renderer staging record.",
                },
                {
                    "offset": 3,
                    "name": "relative_x_offset",
                    "size": 1,
                    "signed": True,
                    "role": "Signed X offset added to the base X submitted to C0:8C54/C0:8CD5.",
                },
                {
                    "offset": 4,
                    "name": "control_flags",
                    "size": 1,
                    "signed": False,
                    "role": "Bit 7 terminates the descriptor list after this record; bit 0 feeds C0:8CD5's packed renderer mask/attribute bit. Bits 1..6 are zero in the checked-in E1 town-map descriptors.",
                },
            ],
            "control_byte_values": dict(
                sorted(
                    Counter(f"${record[4]:02X}" for record in descriptor_records).items(),
                    key=lambda item: int(item[0][1:], 16),
                )
            ),
            "terminal_records": sum(1 for record in descriptor_records if record[4] & 0x80),
            "records_with_mask_bit0_set": sum(1 for record in descriptor_records if record[4] & 0x01),
            "records_with_nonzero_bits_1_to_6": sum(1 for record in descriptor_records if record[4] & 0x7E),
            "pointers": [f"E1:{pointer:04X}" for pointer in icon_pointers],
            "lists": icon_list_ranges,
        },
        "icon_graphic_pointer_table": {
            "range": "E1:F44C..E1:F47A",
            "entry_count": len(icon_pointers),
            "entry_size": 2,
        },
        "blink_suppress_table": {
            "range": "E1:F47A..E1:F491",
            "entry_count": len(blink_flags),
            "nonzero_entries": sum(1 for value in blink_flags if value != 0),
            "zero_entries": sum(1 for value in blink_flags if value == 0),
        },
        "placement_pointer_table": {
            "range": "E1:F491..E1:F4A9",
            "entry_count": len(placement_pointers),
            "entry_size": 4,
            "pointers": placement_pointers,
        },
        "placement_lists": {
            "range": "E1:F4A9..E1:F581",
            "list_count": len(placement_lists),
            "record_count": sum(int(item["record_count"]) for item in placement_lists),
            "record_size": 5,
            "lists": placement_lists,
        },
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

    tables = contract["derived_town_map_tables"]
    icon_lists = tables["icon_graphic_descriptor_lists"]
    blink = tables["blink_suppress_table"]
    placement = tables["placement_lists"]
    lines.extend(
        [
            "",
            "## Derived Town-Map Table Counts",
            "",
            f"- icon graphics descriptor lists: `{icon_lists['unique_list_count']}` unique lists, `{icon_lists['icon_slot_count']}` icon slots, `{icon_lists['record_count']}` five-byte records",
            f"- icon descriptor control bytes: {compact_counts(icon_lists['control_byte_values'])}; `{icon_lists['terminal_records']}` terminal records, `{icon_lists['records_with_mask_bit0_set']}` with bit 0 set, `{icon_lists['records_with_nonzero_bits_1_to_6']}` with bits 1..6 set",
            f"- blink/suppress table: `{blink['entry_count']}` entries, `{blink['nonzero_entries']}` nonzero, `{blink['zero_entries']}` zero",
            f"- placement lists: `{placement['list_count']}` town maps, `{placement['record_count']}` five-byte placement records",
            "",
            "## Town-Map Icon Descriptor Record Shape",
            "",
            "| Offset | Field | Size | Role |",
            "| ---: | --- | ---: | --- |",
        ]
    )
    for field in icon_lists["record_shape"]:
        lines.append(f"| `+{field['offset']}` | `{field['name']}` | {field['size']} | {field['role']} |")

    lines.extend(
        [
            "",
            "| Town map index | Placement target | Records | Terminator |",
            "| ---: | --- | ---: | --- |",
        ]
    )
    for item in placement["lists"]:
        lines.append(
            f"| `{item['index']}` | `{item['target']}` | {item['record_count']} | `{item['terminator']}` |"
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
