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


SCHEMA = "earthbound-decomp.cf-table-splits.v1"

CF_FILE_BASE = 0x0F0000
D0_FILE_BASE = 0x100000


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
    return f"CF:{cpu_addr:04X}"


def hex_label(value: int) -> str:
    return f"0x{value:X}"


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
    file_start = CF_FILE_BASE + cpu_start
    file_end = CF_FILE_BASE + cpu_end
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


def read_word(rom: bytes, file_base: int, cpu_addr: int) -> int:
    offset = file_base + cpu_addr
    return rom[offset] | (rom[offset + 1] << 8)


def read_long(rom: bytes, file_base: int, cpu_addr: int) -> int:
    offset = file_base + cpu_addr
    return (
        rom[offset]
        | (rom[offset + 1] << 8)
        | (rom[offset + 2] << 16)
        | (rom[offset + 3] << 24)
    )


def list_end_from_counted_records(rom: bytes, start: int, record_size: int) -> int:
    count = read_word(rom, CF_FILE_BASE, start)
    return start + 2 + count * record_size


def build_splits(rom_path: Path | None) -> dict[str, object]:
    rom = rom_tools.load_rom(rom_path or rom_tools.find_rom(None))

    door_pointer_count = 40 * 32
    door_pointer_values = [
        read_long(rom, D0_FILE_BASE, index * 4) & 0xFFFF
        for index in range(door_pointer_count)
    ]
    if min(door_pointer_values) != 0x264F:
        raise ValueError(f"Unexpected first CF door-list pointer min: {min(door_pointer_values):04X}")
    door_config_start = min(door_pointer_values)
    door_config_end = max(
        list_end_from_counted_records(rom, pointer, 5)
        for pointer in door_pointer_values
    )
    if door_config_end != 0x58EF:
        raise ValueError(f"Unexpected CF door config end: {door_config_end:04X}")

    event_music_pointer_start = door_config_end
    event_music_pointer_count = 165
    event_music_table_start = event_music_pointer_start + event_music_pointer_count * 2
    if event_music_table_start != 0x5A39:
        raise ValueError(f"Unexpected CF event music table start: {event_music_table_start:04X}")

    inline_start = 0x61DD
    inline_bytes = bytes([0x00, 0x00, 0x08, 0x09, 0x12, 0x00, 0x12, 0x12, 0x12, 0x12])
    actual_inline = rom[CF_FILE_BASE + inline_start : CF_FILE_BASE + inline_start + len(inline_bytes)]
    if actual_inline != inline_bytes:
        raise ValueError(f"Inline CF byte block not found at CF:{inline_start:04X}")

    sprite_pointer_start = inline_start + len(inline_bytes)
    sprite_pointer_count = 40 * 32
    sprite_pointer_values = [
        read_word(rom, CF_FILE_BASE, sprite_pointer_start + index * 2)
        for index in range(sprite_pointer_count)
    ]
    nonzero_sprite_pointers = [pointer for pointer in sprite_pointer_values if pointer]
    if min(nonzero_sprite_pointers) != 0x6BE7:
        raise ValueError(
            f"Unexpected first CF sprite-placement pointer: {min(nonzero_sprite_pointers):04X}"
        )
    sprite_table_start = sprite_pointer_start + sprite_pointer_count * 2
    if sprite_table_start != 0x6BE7:
        raise ValueError(f"Unexpected CF sprite placement table start: {sprite_table_start:04X}")
    sprite_table_end = max(
        list_end_from_counted_records(rom, pointer, 4)
        for pointer in nonzero_sprite_pointers
    )
    if sprite_table_end != 0x8985:
        raise ValueError(f"Unexpected CF sprite placement table end: {sprite_table_end:04X}")

    npc_config_count = 1584
    npc_config_stride = 17
    npc_config_start = sprite_table_end
    npc_config_end = npc_config_start + npc_config_count * npc_config_stride
    if npc_config_end != 0xF2B5:
        raise ValueError(f"Unexpected CF NPC config end: {npc_config_end:04X}")

    rows = [
        make_split(
            rom,
            "DOOR_DATA",
            "data/map/door_data.asm",
            0x0000,
            door_config_start,
            None,
            None,
            "exact-boundary",
            "D0 door pointer table minimum pointer plus ebsrc source order",
            "Door payload block before the 1280 sector door-list records.",
        ),
        make_split(
            rom,
            "DOOR_CONFIG_TABLE",
            "data/map/door_config_table.asm",
            door_config_start,
            door_config_end - door_config_start,
            door_pointer_count,
            None,
            "exact-variable-lists",
            "D0:0000 door pointer table and counted five-byte records",
            "1280 sector lists; each list is a word count followed by five-byte entries.",
        ),
        make_split(
            rom,
            "OVERWORLD_EVENT_MUSIC_POINTER_TABLE",
            "data/map/overworld_event_music_pointer_table.asm",
            event_music_pointer_start,
            event_music_pointer_count * 2,
            event_music_pointer_count,
            2,
            "exact",
            "map_music.yml row count and pointer-table/table adjacency",
            "165 little-endian selectors into the event-music context table; selector 0 is the observed null row.",
        ),
        make_split(
            rom,
            "OVERWORLD_EVENT_MUSIC_TABLE",
            "data/map/overworld_event_music_table.asm",
            event_music_table_start,
            inline_start - event_music_table_start,
            None,
            None,
            "exact-boundary",
            "next inline byte block from bank0f.asm",
            "Variable-length current-position event-music context rows up to the inline bankconfig block.",
        ),
        make_split(
            rom,
            "CF_INLINE_EVENT_MUSIC_TRAILER",
            "inline .BYTE block",
            inline_start,
            len(inline_bytes),
            10,
            1,
            "exact",
            "refs/ebsrc-main/ebsrc-main/src/bankconfig/common/bank0f.asm",
            "Inline ten-byte block between event music data and sprite placement pointers.",
        ),
        make_split(
            rom,
            "SPRITE_PLACEMENT_POINTER_TABLE",
            "data/map/sprite_placement_pointer_table.asm",
            sprite_pointer_start,
            sprite_pointer_count * 2,
            sprite_pointer_count,
            2,
            "exact",
            "map_sprites.yml sector grid shape and first nonzero pointer",
            "1280 two-byte sector pointers into the sprite placement table; zero means empty.",
        ),
        make_split(
            rom,
            "SPRITE_PLACEMENT_TABLE",
            "data/map/sprite_placement_table.asm",
            sprite_table_start,
            sprite_table_end - sprite_table_start,
            len(nonzero_sprite_pointers),
            None,
            "exact-variable-lists",
            "sprite placement pointer table and counted four-byte records",
            "627 non-empty sector lists; each list is a word count followed by sprite_placement rows.",
        ),
        make_split(
            rom,
            "NPC_CONFIG_TABLE",
            "data/map/npc_config.asm",
            npc_config_start,
            npc_config_count * npc_config_stride,
            npc_config_count,
            npc_config_stride,
            "corroborated",
            "npc_config_table.yml row count and ebsrc npc_config struct size",
            "1584 fixed-size npc_config rows ending exactly at the first audio pack.",
        ),
        make_split(
            rom,
            "AUDIO_PACK_94",
            "INSERT_AUDIO_PACK 94",
            0xF2B5,
            3203,
            1,
            3203,
            "manifest-backed",
            "build/asset-bank-cf.json",
            "US retail audio payload after generated map data.",
        ),
        make_split(
            rom,
            "AUDIO_PACK_96",
            "INSERT_AUDIO_PACK 96",
            0xFF38,
            193,
            1,
            193,
            "manifest-backed",
            "build/asset-bank-cf.json",
            "US retail audio payload after AUDIO_PACK_94.",
        ),
        make_split(
            rom,
            "CF_TAIL_SLACK",
            "implicit bank tail slack",
            0xFFF9,
            7,
            None,
            None,
            "exact",
            "bank end after AUDIO_PACK_96",
            "Unclaimed seven-byte bank tail.",
        ),
    ]

    for previous, current in zip(rows, rows[1:]):
        previous_end = int(previous.cpu_end.split(":")[1], 16)
        current_start = int(current.cpu_start.split(":")[1], 16)
        if previous_end + 1 != current_start:
            raise ValueError(f"Split gap/overlap: {previous.label} -> {current.label}")

    generated_bytes = sum(split.size for split in rows[:8])
    if generated_bytes != 0xF2B5:
        raise ValueError(f"Generated CF byte count mismatch: {generated_bytes}")

    return {
        "schema": SCHEMA,
        "bank": "CF",
        "generated_region": {
            "cpu_start": "CF:0000",
            "cpu_end": "CF:F2B4",
            "size": 0xF2B5,
        },
        "summary": {
            "splits": len(rows),
            "generated_bytes": generated_bytes,
            "door_sector_lists": door_pointer_count,
            "sprite_sector_lists": len(nonzero_sprite_pointers),
            "npc_config_rows": npc_config_count,
            "audio_bytes": 3203 + 193,
            "tail_slack_bytes": 7,
        },
        "splits": [asdict(split) for split in rows],
    }


def render_markdown(manifest: dict[str, object]) -> str:
    summary = manifest["summary"]
    assert isinstance(summary, dict)
    splits = manifest["splits"]
    assert isinstance(splits, list)

    lines = [
        "# Bank CF Table Splits",
        "",
        "Generated by `tools/build_cf_table_splits.py` from ebsrc source order, eb-decompile YAML shapes, D0 cross-bank pointer tables, and local ROM verification.",
        "",
        "## Main result",
        "",
        "The `CF:0000..CF:F2B4` generated map-data region now reconciles exactly.",
        "",
        f"- generated region bytes: `{summary['generated_bytes']}`",
        f"- split rows: `{summary['splits']}`",
        f"- door sector lists: `{summary['door_sector_lists']}`",
        f"- non-empty sprite sector lists: `{summary['sprite_sector_lists']}`",
        f"- NPC config rows: `{summary['npc_config_rows']}`",
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
            "- `D0:0000..D0:13FF` is the 1280-entry long-pointer table that anchors the CF door sector lists.",
            "- `notes/cf-door-data-contracts.md` decodes the consumer-backed `DOOR_DATA` type `0`, type `2`, and type `6` payload variants.",
            "- `notes/cf-movement-trigger-contracts.md` decodes `DOOR_CONFIG_TABLE` trigger payload meanings for all source-order physical rows.",
            "- `DOOR_CONFIG_TABLE` and `SPRITE_PLACEMENT_TABLE` are variable-length counted sector lists.",
            "- `notes/cf-event-music-context-contracts.md` decodes `OVERWORLD_EVENT_MUSIC_POINTER_TABLE` and `OVERWORLD_EVENT_MUSIC_TABLE` as selector-addressed current-position music/SFX context chains.",
            "- `NPC_CONFIG_TABLE` uses the ebsrc `npc_config` struct size of 17 bytes and the eb-decompile row count of 1584.",
            "- `CF:F2B5` is the first audio-pack byte, so all generated map data ends exactly at `CF:F2B4`.",
            "",
            "## Recommended next move",
            "",
            "Use the stable CF table shapes and promoted row contracts for source emission planning, then continue with optional gameplay labels or source-emission tooling that consumes the checked-in artifacts.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build exact CF generated-data table splits.")
    parser.add_argument("--rom", type=Path, default=None)
    parser.add_argument("--json-out", default="build/cf-table-splits.json")
    parser.add_argument("--markdown-out", default="notes/cf-table-splits.md")
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
