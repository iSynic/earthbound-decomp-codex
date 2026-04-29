from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSON_OUT = ROOT / "build" / "text-window-skin-bundle-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "text-window-skin-bundle-contracts.md"
TABLE_BIN = ROOT / "build" / "assets" / "e0" / "tables" / "006_data_text_window_properties_asm.bin"
FLAVOR_NAMES = ROOT / "refs" / "eb-decompile-4ef92" / "WindowGraphics" / "flavor_names.txt"
WINDOW_GRAPHICS_REFS = ROOT / "refs" / "eb-decompile-4ef92" / "WindowGraphics"

TABLE_START = 0x1FB9
SELECTOR_OFFSET = 0x0000
SELECTOR_BYTES = 0x000F
PALETTE_BLOCK_OFFSET = 0x000F
PALETTE_BLOCK_SIZE = 0x0040
PALETTE_BLOCK_COUNT = 7
MOVEMENT_PALETTE_OFFSET = PALETTE_BLOCK_OFFSET + PALETTE_BLOCK_SIZE * PALETTE_BLOCK_COUNT
MOVEMENT_PALETTE_BYTES = 0x0008
TOWN_MAP_POINTER_OFFSET = MOVEMENT_PALETTE_OFFSET + MOVEMENT_PALETTE_BYTES
TOWN_MAP_POINTER_BYTES = 0x0018


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def table_range(offset: int, size: int) -> str:
    start = TABLE_START + offset
    end = start + size
    return f"E0:{start:04X}..E0:{end:04X}"


def read_table() -> bytes:
    if not TABLE_BIN.exists():
        raise FileNotFoundError(f"Missing local E0 table bytes: {rel(TABLE_BIN)}")
    data = TABLE_BIN.read_bytes()
    expected = SELECTOR_BYTES + PALETTE_BLOCK_SIZE * PALETTE_BLOCK_COUNT + MOVEMENT_PALETTE_BYTES + TOWN_MAP_POINTER_BYTES
    if len(data) != expected:
        raise ValueError(f"Expected {expected} text-window property bytes, got {len(data)}")
    return data


def load_flavor_names() -> list[str]:
    if not FLAVOR_NAMES.exists():
        raise FileNotFoundError(f"Missing EBDecomp flavor names: {rel(FLAVOR_NAMES)}")
    names = [line.strip() for line in FLAVOR_NAMES.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(names) != 5:
        raise ValueError(f"Expected 5 selectable flavor names, got {len(names)}")
    return names


def decode_bgr555(value: int) -> dict[str, int | str]:
    red = value & 0x1F
    green = (value >> 5) & 0x1F
    blue = (value >> 10) & 0x1F
    return {
        "snes": f"${value:04X}",
        "r5": red,
        "g5": green,
        "b5": blue,
        "rgb888": f"#{(red << 3) | (red >> 2):02X}{(green << 3) | (green >> 2):02X}{(blue << 3) | (blue >> 2):02X}",
    }


def parse_color_row(data: bytes, offset: int) -> list[dict[str, int | str]]:
    return [
        decode_bgr555(int.from_bytes(data[offset + index * 2 : offset + index * 2 + 2], "little"))
        for index in range(4)
    ]


def parse_selectors(data: bytes, flavor_names: list[str]) -> list[dict[str, Any]]:
    selectors = []
    for index, name in enumerate(flavor_names):
        offset = SELECTOR_OFFSET + index * 3
        block_offset = int.from_bytes(data[offset : offset + 2], "little")
        raw_aux = data[offset + 2]
        expected_offset = index * PALETTE_BLOCK_SIZE
        if block_offset != expected_offset:
            raise ValueError(f"Flavor {index} selector offset ${block_offset:04X} != expected ${expected_offset:04X}")
        selectors.append(
            {
                "flavor_value": index + 1,
                "selectable_index": index,
                "name": name,
                "range": table_range(offset, 3),
                "palette_block_offset": f"${block_offset:04X}",
                "palette_block_index": block_offset // PALETTE_BLOCK_SIZE,
                "raw_aux_byte": f"${raw_aux:02X}",
                "raw_bytes": " ".join(f"{byte:02X}" for byte in data[offset : offset + 3]),
            }
        )
    return selectors


def count_ref_pngs(index: int) -> dict[str, Any]:
    first = WINDOW_GRAPHICS_REFS / f"Windows1_{index}.png"
    second = WINDOW_GRAPHICS_REFS / f"Windows2_{index}.png"
    return {
        "windows1_png": rel(first) if first.exists() else None,
        "windows2_png": rel(second) if second.exists() else None,
        "has_both_png_refs": first.exists() and second.exists(),
    }


def parse_palette_blocks(data: bytes, flavor_names: list[str]) -> list[dict[str, Any]]:
    blocks = []
    names_by_block = {index: name for index, name in enumerate(flavor_names)}
    names_by_block[5] = "lead-entity override / nonselectable system block"
    names_by_block[6] = "unused extra system window block"
    block_notes = {
        5: "C4:7F87 selects this fixed E0:2108 block when the current lead entity class is 1 or 2 and the suppress latch at $B4B6 is clear.",
        6: "EBDecomp renders Windows1_6/Windows2_6, but the checked-in C0/C1/C4/EF source paths have no known direct selector for E0:2148; preserve it as an unused/nonselectable extra block until caller proof appears.",
    }
    for block_index in range(PALETTE_BLOCK_COUNT):
        offset = PALETTE_BLOCK_OFFSET + block_index * PALETTE_BLOCK_SIZE
        rows = []
        for row_index in range(8):
            row_offset = offset + row_index * 8
            roles: list[str] = []
            if row_index == 3 and block_index < 5:
                roles.append("C1:9D49 copies this eight-byte row to $0218 for equipment/status display prep")
            rows.append(
                {
                    "row_index": row_index,
                    "range": table_range(row_offset, 8),
                    "colors": parse_color_row(data, row_offset),
                    "roles": roles,
                }
            )
        ref_counts = count_ref_pngs(block_index)
        if not ref_counts["has_both_png_refs"]:
            raise ValueError(f"Missing WindowGraphics PNG refs for block {block_index}")
        blocks.append(
            {
                "block_index": block_index,
                "name": names_by_block[block_index],
                "range": table_range(offset, PALETTE_BLOCK_SIZE),
                "selectable": block_index < len(flavor_names),
                "flavor_value": block_index + 1 if block_index < len(flavor_names) else None,
                "source_offset_from_palette_base": f"${block_index * PALETTE_BLOCK_SIZE:04X}",
                "selection_evidence": block_notes.get(
                    block_index,
                    "Selectable by the five-row E0:1FB9 flavor selector table and the current window-flavour byte at $99CD.",
                ),
                "rows": rows,
                **ref_counts,
            }
        )
    return blocks


def parse_movement_palette(data: bytes) -> dict[str, Any]:
    return {
        "range": table_range(MOVEMENT_PALETTE_OFFSET, MOVEMENT_PALETTE_BYTES),
        "colors": parse_color_row(data, MOVEMENT_PALETTE_OFFSET),
        "role": "Standalone eight-byte movement-text string palette row identified by the E0 asset map.",
    }


def parse_town_map_pointers(data: bytes) -> list[dict[str, Any]]:
    pointers = []
    for index in range(6):
        offset = TOWN_MAP_POINTER_OFFSET + index * 4
        lo = data[offset]
        hi = data[offset + 1]
        bank = data[offset + 2]
        zero = data[offset + 3]
        target = f"{bank:02X}:{((hi << 8) | lo):04X}"
        pointers.append(
            {
                "index": index,
                "range": table_range(offset, 4),
                "target": target,
                "zero_byte": f"${zero:02X}",
                "raw_bytes": " ".join(f"{byte:02X}" for byte in data[offset : offset + 4]),
            }
        )
    expected = ["E0:21A8", "E0:4920", "E0:6721", "E0:8379", "E0:ADB4", "E0:C7F1"]
    actual = [item["target"] for item in pointers]
    if actual != expected:
        raise ValueError(f"Unexpected town-map graphics pointers: {actual}")
    return pointers


def build_contract() -> dict[str, Any]:
    data = read_table()
    flavor_names = load_flavor_names()
    selectors = parse_selectors(data, flavor_names)
    palette_blocks = parse_palette_blocks(data, flavor_names)
    movement_palette = parse_movement_palette(data)
    town_map_pointers = parse_town_map_pointers(data)

    return {
        "schema": "earthbound-decomp.text-window-skin-bundle-contracts.v1",
        "scope": "E0 text-window flavor selector table, palette blocks, movement-text palette row, and shared town-map pointer tail",
        "inputs": {
            "local_table_bytes": rel(TABLE_BIN),
            "ebdecomp_flavor_names": rel(FLAVOR_NAMES),
            "ebdecomp_window_graphics_refs": rel(WINDOW_GRAPHICS_REFS),
        },
        "generated_json": rel(DEFAULT_JSON_OUT),
        "tracked_markdown": rel(DEFAULT_MARKDOWN_OUT),
        "sections": [
            {
                "id": "flavor_selector_table",
                "range": table_range(SELECTOR_OFFSET, SELECTOR_BYTES),
                "bytes": SELECTOR_BYTES,
                "record_count": len(selectors),
                "record_size": 3,
                "runtime_use": "C4:7F87 and C1:9D49 index this table as `(text_flavour - 1) * 3` and use the low word as an offset from E0:1FC8.",
            },
            {
                "id": "window_palette_blocks",
                "range": table_range(PALETTE_BLOCK_OFFSET, PALETTE_BLOCK_SIZE * PALETTE_BLOCK_COUNT),
                "bytes": PALETTE_BLOCK_SIZE * PALETTE_BLOCK_COUNT,
                "record_count": PALETTE_BLOCK_COUNT,
                "record_size": PALETTE_BLOCK_SIZE,
                "runtime_use": "C4:7F87 copies one 0x40-byte block to $0200; blocks 0..4 are selectable through E0:1FB9, block 5 at E0:2108 is the lead-entity override block, and block 6 at E0:2148 has EBDecomp visual refs but no known source-backed selector.",
            },
            {
                "id": "movement_text_string_palette",
                "range": table_range(MOVEMENT_PALETTE_OFFSET, MOVEMENT_PALETTE_BYTES),
                "bytes": MOVEMENT_PALETTE_BYTES,
                "record_count": 1,
                "record_size": MOVEMENT_PALETTE_BYTES,
                "runtime_use": "Standalone movement-text palette row kept separate from the seven 0x40-byte window palette blocks.",
            },
            {
                "id": "town_map_graphics_pointer_table",
                "range": table_range(TOWN_MAP_POINTER_OFFSET, TOWN_MAP_POINTER_BYTES),
                "bytes": TOWN_MAP_POINTER_BYTES,
                "record_count": len(town_map_pointers),
                "record_size": 4,
                "runtime_use": "C4:D553 indexes these six E0 long pointers before decompressing the selected town-map graphics payload.",
            },
        ],
        "totals": {
            "table_bytes": len(data),
            "selectable_flavors": len(selectors),
            "palette_blocks": len(palette_blocks),
            "palette_rows": len(palette_blocks) * 8 + 1,
            "ebdecomp_window_png_refs": sum(
                1
                for block in palette_blocks
                for key in ["windows1_png", "windows2_png"]
                if block[key] is not None
            ),
            "town_map_pointer_entries": len(town_map_pointers),
        },
        "validation": {
            "selector_offsets_point_to_first_five_palette_blocks": True,
            "seven_palette_blocks_have_windowgraphics_png_refs": True,
            "no_known_source_backed_selector_for_palette_block_6": True,
            "town_map_pointer_tail_matches_e0_town_map_assets": True,
            "section_lengths_sum_to_table_length": True,
        },
        "selectors": selectors,
        "palette_blocks": palette_blocks,
        "movement_text_string_palette": movement_palette,
        "town_map_pointers": town_map_pointers,
        "runtime_context": [
            {
                "source": "notes/window-flavour-palette-block-refresh-c47f87.md",
                "role": "C4:7F87 uses the selector table and copies a 0x40-byte palette block to $0200.",
            },
            {
                "source": "notes/equipment-menu-display-fringe-c19a11-c19f29.md",
                "role": "C1:9D49 selects the same flavor block and copies the row at offset +$18 to $0218.",
            },
            {
                "source": "notes/town-map-selection-rendering-c4d274-c4d744.md",
                "role": "C4:D553 consumes the six long pointers at the tail of this span for town-map graphics loading.",
            },
        ],
        "open_questions": [
            "Name the seven per-block palette row roles beyond the known +$18 equipment/status row.",
            "Rename block 6 only if a future caller or source reference proves a narrower retail runtime role.",
            "Name the unused/adjacent third byte in each three-byte flavor selector record if caller proof appears.",
        ],
    }


def render_colors(colors: list[dict[str, Any]]) -> str:
    return ", ".join(f"`{color['snes']}` {color['rgb888']}" for color in colors)


def render_markdown(contract: dict[str, Any]) -> str:
    totals = contract["totals"]
    lines = [
        "# Text Window Skin Bundle Contracts",
        "",
        "Generated by `tools/build_text_window_skin_bundle_contracts.py`. This splits the combined E0 `data/text_window_properties.asm` manifest span into selector, palette-block, movement-text palette, and town-map pointer contracts.",
        "",
        "No ROM-derived graphics or palette payload files are checked in by this report.",
        "",
        "## Snapshot",
        "",
        f"- table bytes represented: `{totals['table_bytes']}`",
        f"- selectable window flavors: `{totals['selectable_flavors']}`",
        f"- 0x40-byte palette blocks: `{totals['palette_blocks']}`",
        f"- palette rows including movement text row: `{totals['palette_rows']}`",
        f"- ignored EBDecomp WindowGraphics PNG refs checked: `{totals['ebdecomp_window_png_refs']}`",
        f"- town-map pointer entries retained at tail: `{totals['town_map_pointer_entries']}`",
        "",
        "## Validation",
        "",
    ]
    for key, value in contract["validation"].items():
        lines.append(f"- `{key}`: `{str(value).lower()}`")

    lines.extend(["", "## Section Split", ""])
    lines.append("| Section | Range | Bytes | Records | Runtime use |")
    lines.append("| --- | --- | ---: | ---: | --- |")
    for section in contract["sections"]:
        lines.append(
            f"| `{section['id']}` | `{section['range']}` | {section['bytes']} | {section['record_count']} | {section['runtime_use']} |"
        )

    lines.extend(["", "## Selectable Flavor Offsets", ""])
    lines.append("| Flavor value | Name | Selector range | Palette block | Offset | Raw bytes | Raw aux byte |")
    lines.append("| ---: | --- | --- | ---: | --- | --- | --- |")
    for selector in contract["selectors"]:
        lines.append(
            "| {value} | {name} | `{range}` | {block} | `{offset}` | `{raw}` | `{aux}` |".format(
                value=selector["flavor_value"],
                name=selector["name"],
                range=selector["range"],
                block=selector["palette_block_index"],
                offset=selector["palette_block_offset"],
                raw=selector["raw_bytes"],
                aux=selector["raw_aux_byte"],
            )
        )

    lines.extend(["", "## Palette Blocks", ""])
    lines.append("| Block | Name | Selectable | Range | Source offset | EBDecomp refs | Selection evidence | Known row roles |")
    lines.append("| ---: | --- | --- | --- | --- | --- | --- | --- |")
    for block in contract["palette_blocks"]:
        roles = []
        for row in block["rows"]:
            roles.extend(f"row {row['row_index']}: {role}" for role in row["roles"])
        refs = f"`{block['windows1_png']}`, `{block['windows2_png']}`"
        lines.append(
            "| {block_index} | {name} | `{selectable}` | `{range}` | `{offset}` | {refs} | {evidence} | {roles} |".format(
                block_index=block["block_index"],
                name=block["name"],
                selectable=str(block["selectable"]).lower(),
                range=block["range"],
                offset=block["source_offset_from_palette_base"],
                refs=refs,
                evidence=block["selection_evidence"],
                roles="; ".join(roles) or "-",
            )
        )

    lines.extend(["", "## Palette Row Values", ""])
    for block in contract["palette_blocks"]:
        lines.append(f"### Block {block['block_index']} - {block['name']}")
        lines.append("")
        lines.append("| Row | Range | Colors |")
        lines.append("| ---: | --- | --- |")
        for row in block["rows"]:
            lines.append(f"| {row['row_index']} | `{row['range']}` | {render_colors(row['colors'])} |")
        lines.append("")

    movement = contract["movement_text_string_palette"]
    lines.extend(
        [
            "## Movement Text String Palette",
            "",
            f"- range: `{movement['range']}`",
            f"- role: {movement['role']}",
            f"- colors: {render_colors(movement['colors'])}",
            "",
            "## Town-Map Pointer Tail",
            "",
            "| Index | Range | Target | Raw bytes |",
            "| ---: | --- | --- | --- |",
        ]
    )
    for pointer in contract["town_map_pointers"]:
        lines.append(f"| {pointer['index']} | `{pointer['range']}` | `{pointer['target']}` | `{pointer['raw_bytes']}` |")

    lines.extend(["", "## Runtime Context", ""])
    for item in contract["runtime_context"]:
        lines.append(f"- `{item['source']}`: {item['role']}")

    lines.extend(["", "## Open Questions", ""])
    for question in contract["open_questions"]:
        lines.append(f"- {question}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build E0 text-window skin bundle contracts.")
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
        "text-window skin bundles: "
        f"{totals['selectable_flavors']} flavors, "
        f"{totals['palette_blocks']} palette blocks, "
        f"{totals['town_map_pointer_entries']} town-map pointers"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
