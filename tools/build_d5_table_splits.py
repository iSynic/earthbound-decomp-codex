from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import rom_tools


ROOT = Path(__file__).resolve().parent.parent
REF_YAML = ROOT / "refs" / "eb-decompile-4ef92"


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
    source: str
    note: str
    first_bytes: str


def bank_to_file(cpu_addr: int) -> int:
    return 0x150000 + cpu_addr


def cpu_label(cpu_addr: int) -> str:
    return f"D5:{cpu_addr:04X}"


def hex_label(value: int) -> str:
    return f"0x{value:X}"


def count_yaml_rows(stem: str) -> int:
    text = (REF_YAML / f"{stem}.yml").read_text(encoding="utf-8")
    rows = [int(match.group(1)) for match in re.finditer(r"^([0-9]+):", text, re.MULTILINE)]
    if not rows:
        raise ValueError(f"No top-level numeric rows found in {stem}.yml")
    expected = list(range(max(rows) + 1))
    if rows != expected:
        raise ValueError(f"Non-contiguous rows in {stem}.yml: first={rows[:5]}, last={rows[-5:]}")
    return len(rows)


def make_split(
    rom: bytes,
    label: str,
    include: str,
    cpu_start: int,
    size: int,
    count: int | None,
    stride: int | None,
    confidence: str,
    source: str,
    note: str,
) -> Split:
    cpu_end = cpu_start + size - 1
    file_start = bank_to_file(cpu_start)
    file_end = bank_to_file(cpu_end)
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
        source=source,
        note=note,
        first_bytes=" ".join(f"{byte:02X}" for byte in first),
    )


def build_splits(rom_path: Path | None) -> dict[str, object]:
    rom = rom_tools.load_rom(rom_path or rom_tools.find_rom(None))
    yaml_counts = {
        "item_configuration_table": count_yaml_rows("item_configuration_table"),
        "store_table": count_yaml_rows("store_table"),
        "psi_teleport_dest_table": count_yaml_rows("psi_teleport_dest_table"),
        "telephone_contacts_table": count_yaml_rows("telephone_contacts_table"),
        "battle_action_table": count_yaml_rows("battle_action_table"),
        "psi_ability_table": count_yaml_rows("psi_ability_table"),
        "psi_name_table": count_yaml_rows("psi_name_table"),
        "exp_table": count_yaml_rows("exp_table"),
        "enemy_configuration_table": count_yaml_rows("enemy_configuration_table"),
        "stats_growth_vars": count_yaml_rows("stats_growth_vars"),
        "condiment_table": count_yaml_rows("condiment_table"),
        "teleport_destination_table": count_yaml_rows("teleport_destination_table"),
        "map_hotspots": count_yaml_rows("map_hotspots"),
        "timed_item_transformation_table": count_yaml_rows("timed_item_transformation_table"),
        "dont_care_names": count_yaml_rows("dont_care_names"),
        "initial_stats": count_yaml_rows("initial_stats"),
        "timed_delivery_table": count_yaml_rows("timed_delivery_table"),
    }

    rows: list[tuple[str, str, int, int, int | None, int | None, str, str, str]] = [
        (
            "UNKNOWN_D545C0",
            "inline .REPEAT zero pad",
            0x45C0,
            0x0A40,
            None,
            None,
            "exact",
            "refs/ebsrc-main/ebsrc-main/src/bankconfig/common/bank15.asm",
            "US retail explicit zero-filled pad before D5 gameplay tables.",
        ),
        (
            "ITEM_CONFIGURATION_TABLE",
            "data/items.asm",
            0x5000,
            yaml_counts["item_configuration_table"] * 0x27,
            yaml_counts["item_configuration_table"],
            0x27,
            "corroborated",
            "refs/eb-decompile-4ef92/item_configuration_table.yml",
            "254 item records; this corrects the earlier 256-row assumption.",
        ),
        (
            "STORE_TABLE",
            "data/store_inventories.asm",
            0x76B2,
            yaml_counts["store_table"] * 7,
            yaml_counts["store_table"],
            7,
            "corroborated",
            "refs/eb-decompile-4ef92/store_table.yml",
            "66 store rows, 7 item ids per row.",
        ),
        (
            "PSI_TELEPORT_DEST_TABLE",
            "data/psi_teleport_destinations.asm",
            0x7880,
            yaml_counts["psi_teleport_dest_table"] * 0x1F,
            yaml_counts["psi_teleport_dest_table"],
            0x1F,
            "corroborated",
            "refs/eb-decompile-4ef92/psi_teleport_dest_table.yml",
            "16 PSI teleport destinations; local landing notes also use D5:7880 as a destination-record table.",
        ),
        (
            "UNKNOWN_D57A70",
            "data/unknown/D57A70",
            0x7A70,
            0x3E,
            None,
            None,
            "exact-boundary-unknown",
            "refs/ebsrc-main/ebsrc-main/include/symbols/misc.inc.asm",
            "Named ebsrc unknown island between PSI teleport destinations and telephone contacts.",
        ),
        (
            "TELEPHONE_CONTACTS_TABLE",
            "data/telephone_contacts.asm",
            0x7AAE,
            yaml_counts["telephone_contacts_table"] * 0x1F,
            yaml_counts["telephone_contacts_table"],
            0x1F,
            "corroborated",
            "refs/eb-decompile-4ef92/telephone_contacts_table.yml",
            "6 phone contacts with name, event flag, and text pointer payload.",
        ),
        (
            "BATTLE_ACTION_TABLE",
            "data/battle/action_table.asm",
            0x7B68,
            yaml_counts["battle_action_table"] * 0x0C,
            yaml_counts["battle_action_table"],
            0x0C,
            "corroborated",
            "refs/ebsrc-main/ebsrc-main/src/data/battle/action_table.asm",
            "318 battle action rows; already contract-backed by C1/C2 notes.",
        ),
        (
            "PSI_ABILITY_TABLE",
            "data/battle/psi_abilities.asm",
            0x8A50,
            yaml_counts["psi_ability_table"] * 0x0F,
            yaml_counts["psi_ability_table"],
            0x0F,
            "corroborated",
            "refs/ebsrc-main/ebsrc-main/src/data/battle/psi_abilities.asm",
            "54 PSI ability rows; description pointers target EF help text.",
        ),
        (
            "PSI_NAME_TABLE",
            "data/battle/psi_names.asm",
            0x8D7A,
            yaml_counts["psi_name_table"] * 25,
            yaml_counts["psi_name_table"],
            25,
            "corroborated",
            "refs/ebsrc-main/ebsrc-main/src/data/battle/psi_names.asm",
            "17 fixed-width US PSI names.",
        ),
        (
            "NPC_AI_TABLE",
            "data/battle/npc_ai_table.asm",
            0x8F23,
            38,
            38,
            1,
            "corroborated",
            "refs/ebsrc-main/ebsrc-main/src/data/battle/npc_ai_table.asm",
            "38-byte NPC AI table from existing source include.",
        ),
        (
            "EXP_TABLE",
            "data/exp_table.asm",
            0x8F49,
            yaml_counts["exp_table"] * 100 * 4,
            yaml_counts["exp_table"],
            100 * 4,
            "corroborated",
            "refs/eb-decompile-4ef92/exp_table.yml",
            "4 character EXP curves, 100 little-endian dwords each.",
        ),
        (
            "ENEMY_CONFIGURATION_TABLE",
            "data/battle/enemies.asm",
            0x9589,
            yaml_counts["enemy_configuration_table"] * 0x5E,
            yaml_counts["enemy_configuration_table"],
            0x5E,
            "corroborated",
            "refs/ebsrc-main/ebsrc-main/src/data/battle/enemies.asm",
            "231 enemy records; strongly cross-backed by C2 class2 notes.",
        ),
        (
            "STATS_GROWTH_VARS",
            "data/stats_growth_vars.asm",
            0xEA5B,
            yaml_counts["stats_growth_vars"] * 7,
            yaml_counts["stats_growth_vars"],
            7,
            "corroborated",
            "refs/eb-decompile-4ef92/stats_growth_vars.yml",
            "4 seven-byte stat-growth parameter rows.",
        ),
        (
            "CONDIMENT_TABLE",
            "data/condiment_table.asm",
            0xEA77,
            yaml_counts["condiment_table"] * 7,
            yaml_counts["condiment_table"],
            7,
            "corroborated",
            "refs/ebsrc-main/ebsrc-main/src/data/condiment_table.asm",
            "44 condiment compatibility/effect rows.",
        ),
        (
            "TELEPORT_DESTINATION_TABLE",
            "data/map/teleport_destinations.asm",
            0xEBAB,
            yaml_counts["teleport_destination_table"] * 8,
            yaml_counts["teleport_destination_table"],
            8,
            "corroborated",
            "refs/eb-decompile-4ef92/teleport_destination_table.yml",
            "234 map teleport destinations; record order in ROM is X, Y, direction, warp style, unknown, pad.",
        ),
        (
            "MAP_HOTSPOTS",
            "data/map/hotspot_coordinates.asm",
            0xF2FB,
            yaml_counts["map_hotspots"] * 8,
            yaml_counts["map_hotspots"],
            8,
            "corroborated",
            "refs/eb-decompile-4ef92/map_hotspots.yml",
            "56 hotspot rectangles, four words each.",
        ),
        (
            "TIMED_ITEM_TRANSFORMATION_TABLE",
            "data/timed_item_transformation_table.asm",
            0xF4BB,
            yaml_counts["timed_item_transformation_table"] * 5,
            yaml_counts["timed_item_transformation_table"],
            5,
            "corroborated",
            "refs/eb-decompile-4ef92/timed_item_transformation_table.yml",
            "4 timed item transformation rows.",
        ),
        (
            "DONT_CARE_NAMES",
            "data/dont_care_names.asm",
            0xF4CF,
            yaml_counts["dont_care_names"] * 7 * 6,
            yaml_counts["dont_care_names"],
            7 * 6,
            "corroborated",
            "refs/ebsrc-main/ebsrc-main/src/data/dont_care_names.asm",
            "7 naming categories, 7 fixed-width 6-byte defaults each.",
        ),
        (
            "INITIAL_STATS",
            "data/initial_stats.asm",
            0xF5F5,
            yaml_counts["initial_stats"] * 0x15,
            yaml_counts["initial_stats"],
            0x15,
            "corroborated",
            "refs/eb-decompile-4ef92/initial_stats.yml",
            "4 initial character stat/inventory rows.",
        ),
        (
            "TIMED_DELIVERY_TABLE",
            "data/timed_delivery_table.asm",
            0xF649,
            yaml_counts["timed_delivery_table"] * 0x14,
            yaml_counts["timed_delivery_table"],
            0x14,
            "corroborated",
            "refs/eb-decompile-4ef92/timed_delivery_table.yml",
            "Exact source-order timed-delivery split window; see TIMED_DELIVERY_CONTROLLER_TABLE and notes/d5-timed-delivery-row-contracts.md for the D5:F645 consumer-effective rows.",
        ),
        (
            "D5_POST_TIMED_DELIVERY_ZERO_TAIL",
            "implicit bank tail padding",
            0xF711,
            0x10000 - 0xF711,
            None,
            None,
            "exact-zero-tail",
            "local ROM verification",
            "Zero-filled tail after the final timed-delivery row.",
        ),
    ]

    splits: list[Split] = []
    for row in rows:
        splits.append(make_split(rom, *row))

    for prev, cur in zip(splits, splits[1:]):
        expected = int(prev.cpu_end.split(":", 1)[1], 16) + 1
        actual = int(cur.cpu_start.split(":", 1)[1], 16)
        if expected != actual:
            raise ValueError(f"Non-contiguous D5 split after {prev.label}: expected {expected:04X}, got {actual:04X}")

    zero_labels = {"UNKNOWN_D545C0", "UNKNOWN_D57A70", "D5_POST_TIMED_DELIVERY_ZERO_TAIL"}
    for split in splits:
        if split.label not in zero_labels:
            continue
        start = int(split.file_start, 16)
        end = int(split.file_end, 16)
        unique = set(rom[start : end + 1])
        if unique != {0}:
            raise ValueError(f"{split.label} is not zero-filled: {sorted(unique)[:8]}")

    table_bytes = sum(split.size for split in splits if split.cpu_start >= "D5:5000")
    return {
        "schema": "earthbound-decomp.d5-table-splits.v1",
        "bank": "D5",
        "post_pad_region": {"cpu_start": "D5:5000", "cpu_end": "D5:FFFF", "size": 0xB000},
        "yaml_counts": yaml_counts,
        "summary": {
            "splits": len(splits),
            "post_pad_table_and_tail_bytes": table_bytes,
            "post_pad_region_bytes": 0xB000,
            "zero_tail_bytes": splits[-1].size,
            "unknown_island_bytes": next(split.size for split in splits if split.label == "UNKNOWN_D57A70"),
        },
        "splits": [asdict(split) for split in splits],
    }


def render_markdown(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    assert isinstance(summary, dict)
    splits = payload["splits"]
    assert isinstance(splits, list)
    lines = [
        "# Bank D5 Table Splits",
        "",
        "Generated by `tools/build_d5_table_splits.py` from D5 first-pass anchors, ebsrc source order, eb-decompile YAML row counts, and local ROM verification.",
        "",
        "## Main result",
        "",
        "The `D5:5000..D5:FFFF` gameplay/table region now reconciles exactly.",
        "",
        f"- post-pad region bytes: `{summary['post_pad_region_bytes']}`",
        f"- accounted table/tail bytes: `{summary['post_pad_table_and_tail_bytes']}`",
        f"- split rows: `{summary['splits']}`",
        f"- remaining zero tail: `{summary['zero_tail_bytes']}` bytes",
        f"- remaining named unknown island: `{summary['unknown_island_bytes']}` bytes at `D5:7A70`",
        "",
        "Important correction: `ITEM_CONFIGURATION_TABLE` is `254` rows, not `256`. At `0x27` bytes per row, it ends at `D5:76B1`, and `STORE_TABLE` starts immediately at `D5:76B2`.",
        "",
        "## Split Table",
        "",
        "| Label | Include | CPU span | Bytes | Count | Stride | Confidence |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for split in splits:
        assert isinstance(split, dict)
        count = "-" if split["count"] is None else str(split["count"])
        stride = "-" if split["stride"] is None else f"`0x{int(split['stride']):X}`"
        lines.append(
            f"| `{split['label']}` | `{split['include']}` | `{split['cpu_start']}..{split['cpu_end']}` | {split['size']} | {count} | {stride} | `{split['confidence']}` |"
        )

    lines.extend(
        [
            "",
            "## Source Notes",
            "",
            "- ebsrc gives the source-order include sequence but lacks several generated source files.",
            "- eb-decompile YAML gives row counts for the missing generated tables.",
            "- Existing local data contracts and C1/C2 notes corroborate the item, battle action, PSI ability, and enemy table anchors.",
            "- `TIMED_DELIVERY_TABLE` is the exact source-order split at `D5:F649..D5:F710`; `TIMED_DELIVERY_CONTROLLER_TABLE` is the consumer-effective row contract at `D5:F645..D5:F70C`.",
            "- `notes/d5-timed-delivery-row-contracts.md` pins the effective timed-delivery fields from EF helper consumers; story-specific row labels remain optional script evidence, not required table semantics.",
            "- `UNKNOWN_D57A70` remains a bounded zero-filled 62-byte island.",
            "- `D5:F711..D5:FFFF` is zero-filled tail padding after the timed delivery table.",
            "",
            "## Recommended next move",
            "",
            "Use the central manifest plus `notes/d5-timed-delivery-row-contracts.md` for source emission. Preserve the source split at `D5:F649` while exposing the row-aligned effective controller fields from `D5:F645`; defer only optional story-specific row labels until script evidence requires them.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build exact D5 gameplay table split artifacts.")
    parser.add_argument("--rom", type=Path)
    parser.add_argument("--json-out", type=Path, default=ROOT / "build" / "d5-table-splits.json")
    parser.add_argument("--markdown-out", type=Path, default=ROOT / "notes" / "d5-table-splits.md")
    args = parser.parse_args()

    payload = build_splits(args.rom)
    json_out = args.json_out if args.json_out.is_absolute() else ROOT / args.json_out
    markdown_out = args.markdown_out if args.markdown_out.is_absolute() else ROOT / args.markdown_out
    json_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    markdown_out.write_text(render_markdown(payload), encoding="utf-8")
    print(f"Wrote {json_out.relative_to(ROOT).as_posix()} and {markdown_out.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
