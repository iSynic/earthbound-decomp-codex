from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import rom_tools
from render_map_scene_metatile_previews import ROOT, rel


DEFAULT_POINTER_CONTRACT = ROOT / "notes" / "map-collision-pointer-contract.json"
DEFAULT_ATTRIBUTE_CONTEXT = ROOT / "notes" / "map-collision-attribute-context.json"
DEFAULT_JSON_OUT = ROOT / "notes" / "map-collision-runtime-bit-contract.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "map-collision-runtime-bit-contract.md"
SCHEMA = "earthbound-decomp.map-collision-runtime-bit-contract.v1"

SAMPLE_POINT_X_TABLE = (0xC2, 0x00B9)
SAMPLE_POINT_Y_TABLE = (0xC2, 0x00C5)
SINGLE_MODE_MASK_TABLE = (0xC2, 0x00D1)
SAMPLE_POINTS = 6


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Promote the map collision byte from storage validation into a "
            "runtime bit/mask contract from C0 surface probes."
        )
    )
    parser.add_argument("--rom", help="Optional explicit ROM path.")
    parser.add_argument("--pointer-contract", default=str(DEFAULT_POINTER_CONTRACT))
    parser.add_argument("--attribute-context", default=str(DEFAULT_ATTRIBUTE_CONTEXT))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_s16_le(data: bytes, offset: int) -> int:
    value = data[offset] | (data[offset + 1] << 8)
    if value >= 0x8000:
        value -= 0x10000
    return value


def read_u16_le(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def rom_offset(bank: int, address: int, rom_size: int) -> int:
    offset = rom_tools.hirom_to_file_offset(bank, address, rom_size)
    if offset is None:
        raise ValueError(f"could not map {bank:02X}:{address:04X} to ROM offset")
    return offset


def read_s16_table(rom: bytes, table: tuple[int, int], count: int) -> list[int]:
    start = rom_offset(table[0], table[1], len(rom))
    return [read_s16_le(rom, start + index * 2) for index in range(count)]


def read_u16_table(rom: bytes, table: tuple[int, int], count: int) -> list[int]:
    start = rom_offset(table[0], table[1], len(rom))
    return [read_u16_le(rom, start + index * 2) for index in range(count)]


def parse_value_counts(rows: list[dict[str, Any]]) -> Counter[int]:
    counter: Counter[int] = Counter()
    for row in rows:
        counter[int(str(row["value"]), 16)] += int(row["count"])
    return counter


def hex_rows(counter: Counter[int], width: int = 2) -> list[dict[str, Any]]:
    return [
        {"value": f"0x{value:0{width}X}", "count": count}
        for value, count in sorted(counter.items())
    ]


def mask_count_rows(counter: Counter[int], mask: int) -> list[dict[str, Any]]:
    masked: Counter[int] = Counter()
    for value, count in counter.items():
        masked[value & mask] += count
    width = 4 if mask > 0xFF else 2
    return hex_rows(masked, width)


def mask_summary(counter: Counter[int], mask: int) -> dict[str, Any]:
    width = 4 if mask > 0xFF else 2
    matching = Counter({value: count for value, count in counter.items() if value & mask})
    return {
        "mask": f"0x{mask:0{width}X}",
        "matching_cell_count": sum(matching.values()),
        "matching_values": [f"0x{value:02X}" for value in sorted(matching)],
        "masked_value_counts": mask_count_rows(counter, mask),
    }


def sample_slots(mask: int) -> list[int]:
    return [index for index in range(SAMPLE_POINTS) if mask & (1 << index)]


def possible_probe_results(mask: int) -> list[int]:
    slots = sample_slots(mask)
    results = {0}
    for slot in slots:
        results |= {value | (1 << slot) for value in list(results)}
    return sorted(results)


def sample_mask_row(name: str, mask: int, result_map: dict[int, str]) -> dict[str, Any]:
    possible = possible_probe_results(mask)
    impossible_handled = sorted(set(result_map) - set(possible))
    return {
        "name": name,
        "mask": f"0x{mask:04X}",
        "selected_slots": sample_slots(mask),
        "possible_results": [f"0x{value:02X}" for value in possible],
        "handled_results": [
            {"result": f"0x{value:02X}", "meaning": meaning}
            for value, meaning in sorted(result_map.items())
        ],
        "handled_results_not_possible_for_mask": [
            f"0x{value:02X}" for value in impossible_handled
        ],
    }


def build_contract(args: argparse.Namespace) -> dict[str, Any]:
    rom_path = rom_tools.find_rom(args.rom)
    rom = rom_tools.load_rom(rom_path)
    pointer_path = Path(args.pointer_contract)
    attribute_path = Path(args.attribute_context)
    pointer_contract = load_json(pointer_path)
    attribute_context = load_json(attribute_path)

    d8_counts = parse_value_counts(pointer_contract["value_alphabets"]["d8_pool_value_counts"])
    fts_counts = parse_value_counts(pointer_contract["value_alphabets"]["full_fts_value_counts"])
    scene_counts = parse_value_counts(attribute_context["summary"]["attribute_counts"])

    sample_x_offsets = read_s16_table(rom, SAMPLE_POINT_X_TABLE, SAMPLE_POINTS)
    sample_y_offsets = read_s16_table(rom, SAMPLE_POINT_Y_TABLE, SAMPLE_POINTS)
    single_mode_masks = read_u16_table(rom, SINGLE_MODE_MASK_TABLE, 4)
    sample_points = [
        {"slot": slot, "x_offset": sample_x_offsets[slot], "y_offset": sample_y_offsets[slot]}
        for slot in range(SAMPLE_POINTS)
    ]

    runtime_masks = [
        {
            "mask": "0x00C0",
            "working_name": "high_collision_block_mask",
            "runtime_role": (
                "C0:5769, C0:3C4B, player/bicycle movement, pathfinding, "
                "teleport, and movement-script probes treat any selected bit "
                "as blocking/high collision."
            ),
            "data_observation": (
                "The C0 code tests both 0x40 and 0x80, but the verified D8/"
                ".fts collision data currently uses 0x80 and never uses 0x40."
            ),
            "counts": {
                "d8_pool": mask_summary(d8_counts, 0x00C0),
                "full_fts": mask_summary(fts_counts, 0x00C0),
                "scene_sample": mask_summary(scene_counts, 0x00C0),
            },
        },
        {
            "mask": "0x00D0",
            "working_name": "movement_cache_stop_mask",
            "runtime_role": (
                "Per-slot collision caches store and later gate movement on "
                "$5DA4 & #$00D0, combining the high collision family with the "
                "0x10 special-surface latch bit."
            ),
            "counts": {
                "d8_pool": mask_summary(d8_counts, 0x00D0),
                "full_fts": mask_summary(fts_counts, 0x00D0),
                "scene_sample": mask_summary(scene_counts, 0x00D0),
            },
        },
        {
            "mask": "0x0010",
            "working_name": "special_surface_coord_latch",
            "runtime_role": (
                "C0:54C9 stores the raw probed coordinates into $5DA8/$5DAA "
                "when this bit is present; player movement later calls C0:7526 "
                "with that latched coordinate pair."
            ),
            "counts": {
                "d8_pool": mask_summary(d8_counts, 0x0010),
                "full_fts": mask_summary(fts_counts, 0x0010),
                "scene_sample": mask_summary(scene_counts, 0x0010),
            },
        },
        {
            "mask": "0x000C",
            "working_name": "entity_terrain_compatibility_class",
            "runtime_role": (
                "C0:5DE7 maps A & #$000C into a three-way permission mask "
                "against the entity metadata byte at D5:9589 + mapped_offset + 0x20."
            ),
            "class_mapping": [
                {"masked_value": "0x00", "entity_permission_mask": "0x04"},
                {"masked_value": "0x04", "entity_permission_mask": "0x02"},
                {"masked_value": "0x08", "entity_permission_mask": "0x01"},
                {"masked_value": "0x0C", "entity_permission_mask": "0x01"},
            ],
            "counts": {
                "d8_pool": mask_summary(d8_counts, 0x000C),
                "full_fts": mask_summary(fts_counts, 0x000C),
                "scene_sample": mask_summary(scene_counts, 0x000C),
            },
        },
        {
            "mask": "0x003F",
            "working_name": "returned_surface_modifier_mask",
            "runtime_role": (
                "C0:5B7B strips high collision bits before returning a "
                "movement/surface modifier byte to the player movement caller."
            ),
            "counts": {
                "d8_pool": mask_summary(d8_counts, 0x003F),
                "full_fts": mask_summary(fts_counts, 0x003F),
                "scene_sample": mask_summary(scene_counts, 0x003F),
            },
        },
    ]

    surface_decoders = [
        sample_mask_row(
            "C0:57E8 Resolve_SurfaceMask0007",
            0x0007,
            {
                0x07: "all three upper samples blocked -> #$FF00",
                0x02: "middle upper sample blocked -> #$FF00",
                0x00: "no selected high samples -> #$FFFF",
                0x01: "left upper sample blocked -> mode #$0001",
                0x04: "right upper sample blocked -> mode #$0007",
                0x06: "middle+right upper samples, aligned x -> mode #$0007",
            },
        ),
        sample_mask_row(
            "C0:583C Resolve_SurfaceMask0038",
            0x0038,
            {
                0x07: "defensive/dead compare under this mask -> #$FF00",
                0x10: "middle lower sample blocked -> #$FF00",
                0x00: "no selected high samples -> #$FFFF",
                0x08: "left lower sample blocked -> mode #$0003",
                0x20: "right lower sample blocked -> mode #$0005",
                0x30: "middle+right lower samples, aligned x -> mode #$0005",
            },
        ),
        sample_mask_row(
            "C0:5890 Resolve_SurfaceMask0009",
            0x0009,
            {
                0x00: "no selected left-column high samples; retry after x-4 pixels",
                0x09: "both left-column samples blocked; alignment decides #$FFFF/#$0006",
                0x01: "upper-left sample only; neighbor check can resolve mode #$0005",
                0x08: "lower-left sample only; neighbor check can resolve mode #$0007",
            },
        ),
        sample_mask_row(
            "C0:59EF Resolve_SurfaceMask0024",
            0x0024,
            {
                0x00: "no selected right-column high samples; retry after x+4 pixels",
                0x24: "both right-column samples blocked; alignment decides #$FFFF/#$0002",
                0x04: "upper-right sample only; neighbor check can resolve mode #$0003",
                0x20: "lower-right sample only; neighbor check can resolve mode #$0001",
            },
        ),
        sample_mask_row(
            "C0:5B4E single-mode masks for modes 1/5",
            0x001E,
            {
                0x00: "no selected high samples -> preserve incoming mode",
            },
        ),
        sample_mask_row(
            "C0:5B4E single-mode masks for modes 3/7",
            0x0033,
            {
                0x00: "no selected high samples -> preserve incoming mode",
            },
        ),
    ]

    return {
        "schema": SCHEMA,
        "title": "Map Collision Runtime Bit Contract",
        "generator": "tools/build_map_collision_runtime_bit_contract.py",
        "source_policy": (
            "Reference-derived structural/runtime contract. This records small "
            "runtime tables, masks, counts, and interpretation boundaries only; "
            "it does not commit raw map payloads or collision grids."
        ),
        "sources": {
            "rom": rel(rom_path),
            "collision_pointer_contract": rel(pointer_path),
            "collision_attribute_context": rel(attribute_path),
            "c0_source_scaffold": rel(ROOT / "src" / "c0" / "bank_c0_helpers_asar.asm"),
            "c2_source_scaffold": rel(ROOT / "src" / "c2" / "bank_c2_helpers_asar.asm"),
            "surface_probe_note": rel(ROOT / "notes" / "collision-surface-probes-c052d4-c05e3a.md"),
        },
        "summary": {
            "confidence": "high-structural / medium-semantic",
            "collision_storage_status": (
                "The byte's D8 storage and .fts equivalence are closed by the "
                "pointer contract; this contract promotes runtime bit and mask "
                "roles without claiming every terrain label is final."
            ),
            "supported_high_collision_mask": "0x00C0",
            "observed_high_collision_values": [
                f"0x{value:02X}" for value in sorted(value for value in d8_counts if value & 0x00C0)
            ],
            "runtime_supported_but_unobserved_high_bit": "0x40",
            "observed_special_latch_values": [
                f"0x{value:02X}" for value in sorted(value for value in d8_counts if value & 0x0010)
            ],
            "terrain_class_mask": "0x000C",
            "surface_sample_points": sample_points,
            "single_mode_masks_from_c2_00d1": [f"0x{mask:04X}" for mask in single_mode_masks],
        },
        "runtime_masks": runtime_masks,
        "surface_sample_model": {
            "sample_points": sample_points,
            "x_offset_table": {
                "address": "C2:00B9",
                "values": sample_x_offsets,
            },
            "y_offset_table": {
                "address": "C2:00C5",
                "values": sample_y_offsets,
            },
            "single_mode_mask_table": {
                "address": "C2:00D1",
                "values": [f"0x{mask:04X}" for mask in single_mode_masks],
            },
            "probe_result_rule": (
                "C0:5769 returns a six-bit occupancy result whose bit N is set "
                "when selected sample point N had collision byte & #$00C0."
            ),
            "surface_decoders": surface_decoders,
        },
        "runtime_anchors": [
            {
                "address": "C0:54C9",
                "name": "Read_CollisionByteAndLatchBit10Coord",
                "mask": "0x0010",
                "role": "latches $5DA8/$5DAA when the sampled byte has bit 0x10",
            },
            {
                "address": "C0:5769",
                "name": "Probe_SurfaceMaskCollisionSamples",
                "mask": "0x00C0",
                "role": "converts selected high-collision samples into a six-bit occupancy result and optionally stores raw OR in $5DA4",
            },
            {
                "address": "C0:5B7B",
                "name": "Resolve_MovementSurfaceCollision",
                "mask": "0x003F",
                "role": "returns low six raw collision bits after surface-mode resolution when movement can proceed",
            },
            {
                "address": "C0:5DE7",
                "name": "Classify_EntityTerrainCompatibility",
                "mask": "0x000C",
                "role": "maps raw collision bits 2-3 to an entity metadata permission check",
            },
            {
                "address": "C0:5E3B/C0:5ECE and C0:A360/C0:A384",
                "name": "Per-slot movement cache gate",
                "mask": "0x00D0",
                "role": "caches high collision plus special-surface bit and blocks regular slot movement when nonzero",
            },
            {
                "address": "C0:3C4B, C0:460B, C0:4A11, C0:BA76, C0:D127, C0:E36A, C0:E57F",
                "name": "High-collision consumers",
                "mask": "0x00C0",
                "role": "use high collision bits as current-position, player/bicycle, pathfinding, movement-script, or teleport obstruction checks",
            },
        ],
    }


def count_for_mask(summary: dict[str, Any], source: str) -> int:
    return int(summary["counts"][source]["matching_cell_count"])


def format_values(values: list[str]) -> str:
    return ", ".join(f"`{value}`" for value in values) if values else "`none`"


def write_markdown(contract: dict[str, Any], path: Path) -> None:
    summary = contract["summary"]
    lines: list[str] = [
        "# Map Collision Runtime Bit Contract",
        "",
        "This contract takes the now-verified collision byte and records how C0",
        "actually masks it at runtime. Storage is high confidence; some gameplay",
        "labels remain intentionally provisional.",
        "",
        "## Summary",
        "",
        f"- confidence: `{summary['confidence']}`",
        f"- supported high collision mask: `{summary['supported_high_collision_mask']}`",
        "- observed high-collision values in D8: "
        + format_values(summary["observed_high_collision_values"]),
        f"- runtime-supported but unobserved high bit: `{summary['runtime_supported_but_unobserved_high_bit']}`",
        "- observed special-latch values in D8: "
        + format_values(summary["observed_special_latch_values"]),
        f"- terrain compatibility mask: `{summary['terrain_class_mask']}`",
        "- single-mode masks from `C2:00D1`: "
        + ", ".join(f"`{value}`" for value in summary["single_mode_masks_from_c2_00d1"]),
        "",
        "## Runtime Masks",
        "",
        "| Mask | Working Name | D8 Cells | Full `.fts` Cells | Scene Cells | Role |",
        "| ---: | --- | ---: | ---: | ---: | --- |",
    ]
    for row in contract["runtime_masks"]:
        lines.append(
            f"| `{row['mask']}` | `{row['working_name']}` | "
            f"{count_for_mask(row, 'd8_pool')} | "
            f"{count_for_mask(row, 'full_fts')} | "
            f"{count_for_mask(row, 'scene_sample')} | {row['runtime_role']} |"
        )

    lines.extend(
        [
            "",
            "## Sample Points",
            "",
            "`C0:5769` uses six sample points. It returns a six-bit occupancy",
            "result where bit `N` is set when selected sample point `N` had",
            "`collision_byte & #$00C0`.",
            "",
            "| Slot | X Offset | Y Offset |",
            "| ---: | ---: | ---: |",
        ]
    )
    for point in contract["surface_sample_model"]["sample_points"]:
        lines.append(f"| {point['slot']} | {point['x_offset']} | {point['y_offset']} |")

    lines.extend(
        [
            "",
            "## Surface Decoders",
            "",
            "| Routine | Mask | Slots | Possible Results | Handled-But-Impossible Results |",
            "| --- | ---: | --- | --- | --- |",
        ]
    )
    for row in contract["surface_sample_model"]["surface_decoders"]:
        slots = ", ".join(str(slot) for slot in row["selected_slots"])
        possible = ", ".join(f"`{value}`" for value in row["possible_results"])
        impossible = format_values(row["handled_results_not_possible_for_mask"])
        lines.append(f"| `{row['name']}` | `{row['mask']}` | {slots} | {possible} | {impossible} |")

    lines.extend(
        [
            "",
            "## Bit Role Boundary",
            "",
            "- `0x80` is the observed solid/high-collision bit in the verified D8 and `.fts` data.",
            "- `0x40` is tested by the runtime high-collision mask, but is not present in the verified map collision data.",
            "- `0x10` latches a probed coordinate pair and participates in the per-slot movement cache stop mask.",
            "- `0x04` and `0x08` are proved as entity terrain-compatibility class bits through `C0:5DE7`.",
            "- `0x01` and `0x02` remain low surface modifier bits; they are preserved through the low-six-bit return path, but their final human gameplay labels need more caller-side evidence.",
            "",
            "## Machine-Readable Data",
            "",
            "`notes/map-collision-runtime-bit-contract.json` records mask counts,",
            "sample-point tables, possible surface-probe results, runtime anchors,",
            "and interpretation boundaries.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    contract = build_contract(args)
    json_out = Path(args.json_out)
    markdown_out = Path(args.markdown_out)
    json_out.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(contract, markdown_out)
    print(f"Wrote {rel(json_out)} and {rel(markdown_out)}")


if __name__ == "__main__":
    main()
