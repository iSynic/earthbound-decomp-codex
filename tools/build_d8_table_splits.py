from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import rom_tools


SCHEMA = "earthbound-decomp.d8-table-splits.v1"
D8_FILE_BASE = 0x180000
EF_FILE_BASE = 0x2F0000
EF_TILE_COLLISION_PTR_TABLE = 0x117B


@dataclass(frozen=True)
class Split:
    label: str
    include: str
    cpu_start: str
    cpu_end: str
    file_start: str
    file_end: str
    size: int
    count: int | None
    stride: int | None
    confidence: str
    evidence: str
    note: str
    first_bytes: str


def cpu_label(cpu_addr: int) -> str:
    return f"D8:{cpu_addr:04X}"


def hex_label(value: int) -> str:
    return f"0x{value:X}"


def read_long(rom: bytes, file_base: int, cpu_addr: int) -> int:
    offset = file_base + cpu_addr
    return (
        rom[offset]
        | (rom[offset + 1] << 8)
        | (rom[offset + 2] << 16)
        | (rom[offset + 3] << 24)
    )


def make_split(
    rom: bytes,
    label: str,
    include: str,
    cpu_start: int,
    size: int,
    count: int | None,
    stride: int | None,
    confidence: str,
    evidence: str,
    note: str,
) -> Split:
    cpu_end = cpu_start + size - 1
    file_start = D8_FILE_BASE + cpu_start
    file_end = D8_FILE_BASE + cpu_end
    first = rom[file_start : file_start + min(size, 8)]
    return Split(
        label=label,
        include=include,
        cpu_start=cpu_label(cpu_start),
        cpu_end=cpu_label(cpu_end),
        file_start=hex_label(file_start),
        file_end=hex_label(file_end),
        size=size,
        count=count,
        stride=stride,
        confidence=confidence,
        evidence=evidence,
        note=note,
        first_bytes=" ".join(f"{byte:02X}" for byte in first),
    )


def build_splits(rom_path: Path | None) -> dict[str, object]:
    rom = rom_tools.load_rom(rom_path or rom_tools.find_rom(None))

    pointer_table_starts = [
        read_long(rom, EF_FILE_BASE, EF_TILE_COLLISION_PTR_TABLE + index * 4) & 0xFFFF
        for index in range(20)
    ]
    if pointer_table_starts[0] != 0x8F50:
        raise ValueError(f"Unexpected first D8 pointer table start: {pointer_table_starts[0]:04X}")
    if pointer_table_starts[-1] != 0xEC2E:
        raise ValueError(f"Unexpected final D8 pointer table start: {pointer_table_starts[-1]:04X}")
    if pointer_table_starts != sorted(pointer_table_starts):
        raise ValueError("D8 pointer table starts are not monotonic")

    generated_end = 0xF05E
    table_bounds = pointer_table_starts + [generated_end]

    rows: list[Split] = [
        make_split(
            rom,
            "MAP_TILE_COLLISION_DATA",
            "data/map/tile_collision_data.asm",
            0x0000,
            pointer_table_starts[0],
            None,
            None,
            "exact-boundary",
            "EF:117B tileset collision pointer table first D8 pointer",
            "Raw tile collision data block before the 20 tileset collision pointer tables.",
        )
    ]

    for index, (start, next_start) in enumerate(zip(table_bounds, table_bounds[1:])):
        size = next_start - start
        if size % 2:
            raise ValueError(f"Odd-sized D8 collision pointer table {index:02d}: {size}")
        rows.append(
            make_split(
                rom,
                f"MAP_DATA_TILE_COLLISION_POINTERS_{index}",
                f"data/map/tile_collision_pointers_{index:02d}.asm",
                start,
                size,
                size // 2,
                2,
                "exact",
                "EF:117B tileset collision pointer table and next D8 pointer/table asset anchor",
                "Word offsets into MAP_TILE_COLLISION_DATA for one tileset/profile collision table.",
            )
        )

    rows.extend(
        [
            make_split(
                rom,
                "ANTI_PIRACY_NOTICE_ARRANGEMENT",
                "errors/antipiracy.arr.lzhal",
                0xF05E,
                431,
                1,
                431,
                "manifest-backed",
                "build/asset-bank-d8.json",
                "Compressed anti-piracy warning tile arrangement.",
            ),
            make_split(
                rom,
                "ANTI_PIRACY_NOTICE_GRAPHICS",
                "errors/antipiracy.gfx.lzhal",
                0xF20D,
                433,
                1,
                433,
                "manifest-backed",
                "build/asset-bank-d8.json",
                "Compressed anti-piracy warning graphics.",
            ),
            make_split(
                rom,
                "WARNING_PALETTE",
                "errors/shared.pal",
                0xF3BE,
                8,
                1,
                8,
                "manifest-backed",
                "build/asset-bank-d8.json",
                "Shared system-warning palette block.",
            ),
            make_split(
                rom,
                "FAULTY_GAME_PAK_ARRANGEMENT",
                "errors/faulty.arr.lzhal",
                0xF3C6,
                510,
                1,
                510,
                "manifest-backed",
                "build/asset-bank-d8.json",
                "Compressed faulty-game-pak warning tile arrangement.",
            ),
            make_split(
                rom,
                "FAULTY_GAME_PAK_GRAPHICS",
                "errors/faulty.gfx.lzhal",
                0xF5C4,
                243,
                1,
                243,
                "manifest-backed",
                "build/asset-bank-d8.json",
                "Compressed faulty-game-pak warning graphics.",
            ),
            make_split(
                rom,
                "AUDIO_PACK_61",
                "INSERT_AUDIO_PACK 61",
                0xF6B7,
                2354,
                1,
                2354,
                "manifest-backed",
                "build/asset-bank-d8.json",
                "US retail audio payload after warning assets.",
            ),
            make_split(
                rom,
                "D8_TAIL_SLACK",
                "implicit bank tail slack",
                0xFFE9,
                23,
                None,
                None,
                "exact",
                "bank end after AUDIO_PACK_61",
                "Unclaimed 23-byte bank tail.",
            ),
        ]
    )

    for previous, current in zip(rows, rows[1:]):
        previous_end = int(previous.cpu_end.split(":")[1], 16)
        current_start = int(current.cpu_start.split(":")[1], 16)
        if previous_end + 1 != current_start:
            raise ValueError(f"Split gap/overlap: {previous.label} -> {current.label}")

    generated_bytes = sum(split.size for split in rows[:21])
    if generated_bytes != generated_end:
        raise ValueError(f"Generated D8 byte count mismatch: {generated_bytes}")

    return {
        "schema": SCHEMA,
        "bank": "D8",
        "generated_region": {
            "cpu_start": "D8:0000",
            "cpu_end": "D8:F05D",
            "size": generated_end,
        },
        "ef_pointer_table": {
            "address": "EF:117B",
            "count": 20,
            "targets": [cpu_label(start) for start in pointer_table_starts],
        },
        "summary": {
            "splits": len(rows),
            "generated_bytes": generated_bytes,
            "collision_data_bytes": pointer_table_starts[0],
            "collision_pointer_tables": 20,
            "collision_pointer_bytes": generated_end - pointer_table_starts[0],
            "warning_asset_bytes": 431 + 433 + 8 + 510 + 243,
            "audio_bytes": 2354,
            "tail_slack_bytes": 23,
        },
        "splits": [asdict(split) for split in rows],
    }


def render_markdown(manifest: dict[str, object]) -> str:
    summary = manifest["summary"]
    assert isinstance(summary, dict)
    splits = manifest["splits"]
    assert isinstance(splits, list)

    lines = [
        "# Bank D8 Table Splits",
        "",
        "Generated by `tools/build_d8_table_splits.py` from ebsrc source order, the EF tileset-collision pointer table, asset manifest anchors, and local ROM verification.",
        "",
        "## Main result",
        "",
        "The `D8:0000..D8:F05D` generated tile-collision region now reconciles exactly.",
        "",
        f"- generated region bytes: `{summary['generated_bytes']}`",
        f"- collision data bytes: `{summary['collision_data_bytes']}`",
        f"- collision pointer tables: `{summary['collision_pointer_tables']}`",
        f"- collision pointer bytes: `{summary['collision_pointer_bytes']}`",
        f"- warning asset bytes: `{summary['warning_asset_bytes']}`",
        f"- audio bytes: `{summary['audio_bytes']}`",
        f"- tail slack bytes: `{summary['tail_slack_bytes']}`",
        "",
        "## Split Table",
        "",
        "| Label | Include | CPU span | Bytes | Count | Stride | Confidence |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]

    for split in splits:
        assert isinstance(split, dict)
        count = "-" if split["count"] is None else split["count"]
        stride = "-" if split["stride"] is None else f"`0x{split['stride']:X}`"
        lines.append(
            "| `{label}` | `{include}` | `{start}..{end}` | {size} | {count} | {stride} | `{confidence}` |".format(
                label=split["label"],
                include=split["include"],
                start=split["cpu_start"],
                end=split["cpu_end"],
                size=split["size"],
                count=count,
                stride=stride,
                confidence=split["confidence"],
            )
        )

    lines.extend(
        [
            "",
            "## Source Notes",
            "",
            "- `EF:117B` is the 20-entry tileset-collision long-pointer table that anchors the D8 pointer-table family.",
            "- `MAP_TILE_COLLISION_DATA` ends at `D8:8F4F`; the first pointer table begins at `D8:8F50`.",
            "- Each `MAP_DATA_TILE_COLLISION_POINTERS_n` span is an exact word-offset table into the D8 collision data family.",
            "- `D8:F05E` is the first warning-screen asset byte, so all generated collision data ends exactly at `D8:F05D`.",
            "",
            "## Recommended next move",
            "",
            "Promote the collision data and pointer tables into the data-contract manifest. The remaining work is semantic decoding of the pointed collision rows, not boundary discovery.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build exact D8 generated collision-data splits.")
    parser.add_argument("--rom", type=Path, default=None)
    parser.add_argument("--json-out", default="build/d8-table-splits.json")
    parser.add_argument("--markdown-out", default="notes/d8-table-splits.md")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    manifest = build_splits(args.rom)

    json_path = Path(args.json_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    markdown_path = Path(args.markdown_out)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(manifest), encoding="utf-8")

    print(f"Wrote {json_path} and {markdown_path}")


if __name__ == "__main__":
    main()
