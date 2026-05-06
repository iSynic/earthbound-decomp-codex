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


SCHEMA = "earthbound-decomp.d0-table-splits.v1"
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
    return f"D0:{cpu_addr:04X}"


def hex_label(value: int) -> str:
    return f"0x{value:X}"


def read_word(rom: bytes, cpu_addr: int) -> int:
    offset = D0_FILE_BASE + cpu_addr
    return rom[offset] | (rom[offset + 1] << 8)


def read_long(rom: bytes, cpu_addr: int) -> int:
    offset = D0_FILE_BASE + cpu_addr
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
    file_start = D0_FILE_BASE + cpu_start
    file_end = D0_FILE_BASE + cpu_end
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


def tile_event_chain_end(rom: bytes, start: int) -> int:
    cursor = start
    while True:
        event_flag = read_word(rom, cursor)
        cursor += 2
        if event_flag == 0:
            return cursor
        count = read_word(rom, cursor)
        cursor += 2 + count * 4


def build_splits(rom_path: Path | None) -> dict[str, object]:
    rom = rom_tools.load_rom(rom_path or rom_tools.find_rom(None))

    door_pointer_count = 40 * 32
    door_pointer_start = 0x0000
    door_pointer_end = door_pointer_start + door_pointer_count * 4
    door_pointer_values = [
        read_long(rom, door_pointer_start + index * 4)
        for index in range(door_pointer_count)
    ]
    if not all((value & 0xFF0000) == 0xCF0000 for value in door_pointer_values):
        raise ValueError("D0 door pointer table contains non-CF pointers")

    screen_transition_start = door_pointer_end
    screen_transition_count = 34
    screen_transition_stride = 12
    event_control_pointer_start = screen_transition_start + screen_transition_count * screen_transition_stride
    if event_control_pointer_start != 0x1598:
        raise ValueError(f"Unexpected D0 event control pointer start: {event_control_pointer_start:04X}")

    event_control_pointer_count = 20
    event_control_pointer_values = [
        read_word(rom, event_control_pointer_start + index * 2)
        for index in range(event_control_pointer_count)
    ]
    tile_event_start = event_control_pointer_start + event_control_pointer_count * 2
    if tile_event_start != 0x15C0:
        raise ValueError(f"Unexpected D0 tile-event table start: {tile_event_start:04X}")
    tile_event_end = max(tile_event_chain_end(rom, pointer) for pointer in event_control_pointer_values)
    if tile_event_end != 0x1880:
        raise ValueError(f"Unexpected D0 tile-event table end: {tile_event_end:04X}")

    map_enemy_placement_start = tile_event_end
    map_enemy_placement_count = 20480
    map_enemy_placement_stride = 2
    enemy_group_pointer_start = map_enemy_placement_start + map_enemy_placement_count * map_enemy_placement_stride
    if enemy_group_pointer_start != 0xB880:
        raise ValueError(f"Unexpected D0 enemy group pointer start: {enemy_group_pointer_start:04X}")

    enemy_group_pointer_count = 203
    enemy_group_pointer_values = [
        read_long(rom, enemy_group_pointer_start + index * 4)
        for index in range(enemy_group_pointer_count)
    ]
    if not all((value & 0xFF0000) == 0xD00000 for value in enemy_group_pointer_values):
        raise ValueError("D0 enemy placement group pointer table contains non-D0 pointers")
    enemy_group_table_start = min(value & 0xFFFF for value in enemy_group_pointer_values)
    if enemy_group_table_start != 0xBBAC:
        raise ValueError(f"Unexpected D0 enemy placement group table start: {enemy_group_table_start:04X}")

    battle_entry_pointer_start = 0xC60D
    if battle_entry_pointer_start <= max(value & 0xFFFF for value in enemy_group_pointer_values):
        raise ValueError("Battle entry pointer table overlaps enemy placement group pointers")

    battle_entry_count = 484
    battle_entry_stride = 8
    battle_groups_start = battle_entry_pointer_start + battle_entry_count * battle_entry_stride
    if battle_groups_start != 0xD52D:
        raise ValueError(f"Unexpected D0 battle groups start: {battle_groups_start:04X}")

    battle_entry_pointer_values = [
        read_long(rom, battle_entry_pointer_start + index * battle_entry_stride)
        for index in range(battle_entry_count)
    ]
    nonzero_battle_pointers = [value & 0xFFFF for value in battle_entry_pointer_values if value]
    if min(nonzero_battle_pointers) != battle_groups_start:
        raise ValueError(
            f"Unexpected minimum D0 battle group pointer: {min(nonzero_battle_pointers):04X}"
        )

    generated_end = 0xDFB4

    rows = [
        make_split(
            rom,
            "DOOR_POINTER_TABLE",
            "data/map/door_pointer_table.asm",
            0x0000,
            door_pointer_count * 4,
            door_pointer_count,
            4,
            "exact",
            "D0 long pointers into CF door sector lists",
            "40x32 long-pointer grid into CF:264F..CF:58EE.",
        ),
        make_split(
            rom,
            "SCREEN_TRANSITION_CONFIG_TABLE",
            "data/screen_transition_config_table.asm",
            screen_transition_start,
            screen_transition_count * screen_transition_stride,
            screen_transition_count,
            screen_transition_stride,
            "corroborated",
            "ebsrc screen_transition_config struct size and EVENT_CONTROL_PTR_TABLE anchor",
            "34 fixed-size screen transition configuration rows.",
        ),
        make_split(
            rom,
            "EVENT_CONTROL_PTR_TABLE",
            "data/event_control_ptr_table.asm",
            event_control_pointer_start,
            event_control_pointer_count * 2,
            event_control_pointer_count,
            2,
            "exact",
            "refs/ebsrc-main/ebsrc-main/src/data/event_control_ptr_table.asm",
            "20 word offsets to MAP_TILE_EVENT_* chains.",
        ),
        make_split(
            rom,
            "MAP_TILE_EVENT_CONTROL_TABLE",
            "data/map/tile_event_control_table.asm",
            tile_event_start,
            tile_event_end - tile_event_start,
            event_control_pointer_count,
            None,
            "exact-variable-chains",
            "EVENT_CONTROL_PTR_TABLE and map_tile_event chain terminators",
            "20 variable event chains, each terminated by a zero event flag word.",
        ),
        make_split(
            rom,
            "MAP_ENEMY_PLACEMENT",
            "data/map/enemy_placement.asm",
            map_enemy_placement_start,
            map_enemy_placement_count * map_enemy_placement_stride,
            map_enemy_placement_count,
            map_enemy_placement_stride,
            "corroborated",
            "refs/eb-decompile-4ef92/map_enemy_placement.yml row count",
            "20480 word enemy-map-group entries.",
        ),
        make_split(
            rom,
            "ENEMY_PLACEMENT_GROUPS_PTR_TABLE",
            "data/map/enemy_placement_groups_pointer_table.asm",
            enemy_group_pointer_start,
            enemy_group_pointer_count * 4,
            enemy_group_pointer_count,
            4,
            "exact",
            "refs/eb-decompile-4ef92/map_enemy_groups.yml row count",
            "203 long pointers into ENEMY_PLACEMENT_GROUPS_TABLE.",
        ),
        make_split(
            rom,
            "ENEMY_PLACEMENT_GROUPS_TABLE",
            "data/map/enemy_placement_groups.asm",
            enemy_group_table_start,
            battle_entry_pointer_start - enemy_group_table_start,
            enemy_group_pointer_count,
            None,
            "exact-variable-lists",
            "enemy placement group pointers and next battle-entry anchor",
            "203 variable enemy placement group lists.",
        ),
        make_split(
            rom,
            "BTL_ENTRY_PTR_TABLE",
            "data/map/battle_entry_pointer_table.asm",
            battle_entry_pointer_start,
            battle_entry_count * battle_entry_stride,
            battle_entry_count,
            battle_entry_stride,
            "corroborated",
            "ebsrc battle_entry_ptr_entry struct size and enemy_groups.yml count",
            "484 battle-entry pointer records with run-away and letterbox metadata.",
        ),
        make_split(
            rom,
            "ENEMY_BATTLE_GROUPS_TABLE",
            "data/map/battle_groups_table.asm",
            battle_groups_start,
            generated_end - battle_groups_start,
            battle_entry_count,
            None,
            "exact-variable-lists",
            "BTL_ENTRY_PTR_TABLE minimum pointer and first audio-pack anchor",
            "Variable battle group payloads addressed by BTL_ENTRY_PTR_TABLE.",
        ),
        make_split(
            rom,
            "AUDIO_PACK_139",
            "INSERT_AUDIO_PACK 139",
            0xDFB4,
            8180,
            1,
            8180,
            "manifest-backed",
            "build/asset-bank-d0.json",
            "US retail audio payload after generated map/battle data.",
        ),
        make_split(
            rom,
            "D0_TAIL_SLACK",
            "implicit bank tail slack",
            0xFFA8,
            88,
            None,
            None,
            "exact",
            "bank end after AUDIO_PACK_139",
            "Unclaimed 88-byte bank tail.",
        ),
    ]

    for previous, current in zip(rows, rows[1:]):
        previous_end = int(previous.cpu_end.split(":")[1], 16)
        current_start = int(current.cpu_start.split(":")[1], 16)
        if previous_end + 1 != current_start:
            raise ValueError(f"Split gap/overlap: {previous.label} -> {current.label}")

    generated_bytes = sum(split.size for split in rows[:9])
    if generated_bytes != generated_end:
        raise ValueError(f"Generated D0 byte count mismatch: {generated_bytes}")

    return {
        "schema": SCHEMA,
        "bank": "D0",
        "generated_region": {
            "cpu_start": "D0:0000",
            "cpu_end": "D0:DFB3",
            "size": generated_end,
        },
        "summary": {
            "splits": len(rows),
            "generated_bytes": generated_bytes,
            "door_pointers": door_pointer_count,
            "screen_transition_rows": screen_transition_count,
            "tile_event_chains": event_control_pointer_count,
            "enemy_placement_rows": map_enemy_placement_count,
            "enemy_placement_groups": enemy_group_pointer_count,
            "battle_entry_rows": battle_entry_count,
            "audio_bytes": 8180,
            "tail_slack_bytes": 88,
        },
        "splits": [asdict(split) for split in rows],
    }


def render_markdown(manifest: dict[str, object]) -> str:
    summary = manifest["summary"]
    assert isinstance(summary, dict)
    splits = manifest["splits"]
    assert isinstance(splits, list)

    lines = [
        "# Bank D0 Table Splits",
        "",
        "Generated by `tools/build_d0_table_splits.py` from ebsrc source order, eb-decompile YAML row counts, pointer-table validation, and local ROM verification.",
        "",
        "## Main result",
        "",
        "The `D0:0000..D0:DFB3` generated map/battle-data region now reconciles exactly.",
        "",
        f"- generated region bytes: `{summary['generated_bytes']}`",
        f"- split rows: `{summary['splits']}`",
        f"- door pointers: `{summary['door_pointers']}`",
        f"- screen transition rows: `{summary['screen_transition_rows']}`",
        f"- tile event chains: `{summary['tile_event_chains']}`",
        f"- enemy placement rows: `{summary['enemy_placement_rows']}`",
        f"- enemy placement groups: `{summary['enemy_placement_groups']}`",
        f"- battle entry rows: `{summary['battle_entry_rows']}`",
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
            "- `DOOR_POINTER_TABLE` is a 40x32 long-pointer grid into CF's door sector-list block.",
            "- `ENEMY_PLACEMENT_GROUPS_TABLE` and `ENEMY_BATTLE_GROUPS_TABLE` now have consumer-backed row-level contracts in `notes/d0-variable-list-contracts.md` / `.json`.",
            "- `MAP_TILE_EVENT_CONTROL_TABLE` is still an exact variable-length region whose chains need row-level semantic expansion.",
            "- `MAP_ENEMY_PLACEMENT` is a 20480-row word table, matching `map_enemy_placement.yml`.",
            "- `BTL_ENTRY_PTR_TABLE` uses the ebsrc `battle_entry_ptr_entry` struct size of 8 bytes.",
            "",
            "## Recommended next move",
            "",
            "Keep the placement/battle variable-list contracts regression-tested, then decode the `MAP_TILE_EVENT_CONTROL_TABLE` chains when D0 needs the next subrecord-level source pass.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build exact D0 generated-data table splits.")
    parser.add_argument("--rom", type=Path, default=None)
    parser.add_argument("--json-out", default="build/d0-table-splits.json")
    parser.add_argument("--markdown-out", default="notes/d0-table-splits.md")
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
