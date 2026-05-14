from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - developer setup guard
    raise SystemExit("PyYAML is required to read enemy_configuration_table.yml") from exc

from rom_tools import (
    EXPECTED_SHA1,
    find_rom,
    hirom_to_file_offset,
    load_rom,
    read_rom_info,
    verify_earthbound_us,
    workspace_root,
)


ENEMY_TABLE_BANK = 0xD5
ENEMY_TABLE_ADDRESS = 0x9589
ENEMY_TABLE_STRIDE = 0x5E
BATTLE_ACTION_TABLE_BANK = 0xD5
BATTLE_ACTION_TABLE_ADDRESS = 0x7B68
BATTLE_ACTION_TABLE_STRIDE = 0x0C

ENEMY_FIELD_OFFSETS = {
    "hp": 0x21,
    "speed": 0x3C,
    "action_order": 0x45,
    "action_1": 0x46,
    "action_2": 0x48,
    "action_3": 0x4A,
    "action_4": 0x4C,
    "final_action": 0x4E,
    "action_1_argument": 0x50,
    "action_2_argument": 0x51,
    "action_3_argument": 0x52,
    "action_4_argument": 0x53,
    "final_action_argument": 0x54,
}

BATTLE_ACTION_FIELD_OFFSETS = {
    "direction": 0x00,
    "target": 0x01,
    "action_type": 0x02,
    "pp_cost": 0x03,
    "message_pointer": 0x04,
    "action_pointer": 0x08,
}

ACTION_NEUTRALIZE_ALL = 248
ACTION_DREAD_SKELPION_POISON = 72
ACTION_ROW_BASH = 4
ACTION_POINTER_BATTLER_NORMALIZATION = (0xC2, 0x90C6)
ACTION_POINTER_PSI_FLASH_BETA = (0xC2, 0x99AE)
ACTION_POINTER_PSI_MAGNET_PP_DRAIN = (0xC2, 0x9F5E)
ACTION_POINTER_PP_REDUCTION = (0xC2, 0x8E42)


@dataclass(frozen=True)
class Patch:
    table: str
    row: int
    row_name: str
    field: str
    cpu_address: str
    file_offset: str
    old: str
    new: str
    reason: str


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    purpose: str
    patches: tuple[dict[str, Any], ...]
    expected_probe: str
    caveats: tuple[str, ...] = ()


SCENARIOS: dict[str, Scenario] = {
    "adb4-force-b930-snapshot-export": Scenario(
        id="adb4-force-b930-snapshot-export",
        title="C1:ADB4 forced-entry C2:B930 battle selection snapshot export",
        purpose=(
            "Replace the C1:ADB4 target resolver entry with a tiny controlled "
            "call into C2:B930 using A=1 and X/Y=$9FFA. This exercises the "
            "battle selection snapshot exporter from an already route-observed "
            "C1 entrypoint without depending on a hand-made pre-export save."
        ),
        patches=(
            {
                "raw_cpu_patch": "C1:ADB4",
                "bytes": (
                    0xC2,
                    0x31,
                    0xA9,
                    0x01,
                    0x00,
                    0xA2,
                    0xFA,
                    0x9F,
                    0xA0,
                    0xFA,
                    0x9F,
                    0x22,
                    0x30,
                    0xB9,
                    0xC2,
                    0x6B,
                ),
                "field": "forced_b930_call_stub",
            },
        ),
        expected_probe=(
            "Any save that reaches C1:ADB4 should immediately call C2:B930, "
            "copy source slot 1 from $99CE into the $9FFA snapshot block, and "
            "emit a post-return C2:B930 snapshot."
        ),
        caveats=(
            "This is a forced-entry mechanics fixture, not normal target resolver behavior.",
            "Use it to review C2:B930 row export fields only; do not promote a vanilla C1 route from this trace.",
        ),
    ),
    "runaway-dog-neutralize-c240a4": Scenario(
        id="runaway-dog-neutralize-c240a4",
        title="Runaway Dog normal action forces Neutralize/all C2:40A4 lane",
        purpose=(
            "Turn both Runaway Dog enemy rows into deterministic C2:90C6 "
            "normalization actions so early-game dog encounters should route "
            "through C2:40A4 without hunting for a rare enemy/action."
        ),
        patches=(
            {
                "enemy_names": ("Runaway Dog",),
                "normal_actions": (ACTION_NEUTRALIZE_ALL,) * 4,
                "normal_arguments": (0, 0, 0, 0),
                "action_order": 0,
            },
        ),
        expected_probe=(
            "A Runaway Dog turn should hit C2:90C6 -> C2:40A4 -> C0:9279, "
            "with C2:40A4 iterating the selected target mask."
        ),
        caveats=(
            "This is a table fixture, not a gameplay-balanced hack.",
            "The action text/effect may look odd when assigned to a dog.",
        ),
    ),
    "bash-row-neutralize-c240a4": Scenario(
        id="bash-row-neutralize-c240a4",
        title="Bash action row points at C2:90C6 C2:40A4 lane",
        purpose=(
            "Patch battle action row 4, the ordinary Bash row, so any existing "
            "command-menu save that confirms Bash can exercise the "
            "C2:90C6 -> C2:40A4 wrapper without depending on a matching enemy "
            "configuration row."
        ),
        patches=(
            {
                "battle_action_row": ACTION_ROW_BASH,
                "battle_action_field_values": {
                    "action_pointer": ACTION_POINTER_BATTLER_NORMALIZATION,
                },
            },
        ),
        expected_probe=(
            "Confirming Bash should dispatch battle action row 4 through "
            "C2:90C6, then hit C2:40A4."
        ),
        caveats=(
            "This is a behavior-table fixture for tracing, not a plausible "
            "gameplay edit.",
            "Use only with local Mesen traces; do not infer real Bash semantics "
            "from this patched row.",
        ),
    ),
    "bash-row-flash-beta-force-numb": Scenario(
        id="bash-row-flash-beta-force-numb",
        title="Bash action row routes to Flash Beta forced numb branch",
        purpose=(
            "Patch battle action row 4 to run the Flash Beta wrapper, then "
            "force the Flash gate and random result so the action reaches "
            "C2:9917 and its C2:724A affliction writer call. This is a compact "
            "paired-status mechanics fixture for the C2:9917 lane."
        ),
        patches=(
            {
                "battle_action_row": ACTION_ROW_BASH,
                "battle_action_field_values": {
                    "action_pointer": ACTION_POINTER_PSI_FLASH_BETA,
                },
            },
            {
                "raw_cpu_patch": "C2:99B8",
                "bytes": (0xA9, 0x01, 0x00, 0xEA, 0xEA, 0xEA, 0xEA, 0xEA),
                "field": "force_flash_gate_pass",
            },
            {
                "raw_cpu_patch": "C2:99C0",
                "bytes": (0xA9, 0x01, 0x00, 0xEA, 0xEA, 0xEA, 0xEA),
                "field": "force_flash_random_numb_branch",
            },
        ),
        expected_probe=(
            "Confirming Bash should dispatch Flash Beta, enter C2:9917, then "
            "call C2:724A with the numb/paralysis subgroup/value pair."
        ),
        caveats=(
            "This bypasses the natural Flash resistance/precondition gate.",
            "Use it to capture paired C2:9917/C2:724A mechanics; do not promote natural Flash probabilities from this trace.",
        ),
    ),
    "bash-row-psi-magnet-pp-drain": Scenario(
        id="bash-row-psi-magnet-pp-drain",
        title="Bash action row routes to PSI Magnet PP drain action",
        purpose=(
            "Patch battle action row 4 to run the PSI Magnet-style PP drain "
            "body at C2:9F5E. This gives the resource-amount oracle a compact "
            "route to the PP drain amount setup and shared PP reducer without "
            "requiring a hand-authored PSI Magnet save."
        ),
        patches=(
            {
                "battle_action_row": ACTION_ROW_BASH,
                "battle_action_field_values": {
                    "action_pointer": ACTION_POINTER_PSI_MAGNET_PP_DRAIN,
                },
            },
        ),
        expected_probe=(
            "Confirming Bash should dispatch C2:9F5E and, when the selected "
            "target has PP, reach the shared C2:721D PP reducer and the "
            "amount-bearing battle-text path."
        ),
        caveats=(
            "This is action-row steering only; it does not prove vanilla Bash or PSI command routing.",
            "If the selected target has no PP, the fixture still proves the entry path but not amount flow.",
        ),
    ),
    "bash-row-psi-magnet-force-reducer": Scenario(
        id="bash-row-psi-magnet-force-reducer",
        title="Bash action row routes to forced PSI Magnet reducer path",
        purpose=(
            "Patch battle action row 4 to run C2:9F5E, then force the early "
            "selected-target PP check to continue into the random amount and "
            "C2:721D reducer path. This is a reducer-route fixture for saves "
            "whose selected enemy row has zero current PP."
        ),
        patches=(
            {
                "battle_action_row": ACTION_ROW_BASH,
                "battle_action_field_values": {
                    "action_pointer": ACTION_POINTER_PSI_MAGNET_PP_DRAIN,
                },
            },
            {
                "raw_cpu_patch": "C2:9F6C",
                "bytes": (0x80,),
                "field": "force_pp_drain_nonzero_branch",
            },
        ),
        expected_probe=(
            "Confirming Bash should dispatch C2:9F5E, skip the no-PP text "
            "early exit, and reach the C2:721D PP reducer path."
        ),
        caveats=(
            "This is a forced reducer-route fixture; it does not prove a nonzero vanilla PP drain amount.",
            "Use it only to separate transfer-style routing from loss-only routing before later amount-proof traces.",
        ),
    ),
    "bash-row-pp-reduction": Scenario(
        id="bash-row-pp-reduction",
        title="Bash action row routes to PP reduction action",
        purpose=(
            "Patch battle action row 4 to run the direct PP reduction action "
            "at C2:8E42. This is the PP-loss side of the resource-amount lane "
            "and should expose the C2:721D reducer plus EF:7755 amount text "
            "when the selected target row has PP to reduce."
        ),
        patches=(
            {
                "battle_action_row": ACTION_ROW_BASH,
                "battle_action_field_values": {
                    "action_pointer": ACTION_POINTER_PP_REDUCTION,
                },
            },
        ),
        expected_probe=(
            "Confirming Bash should dispatch C2:8E42 and, for a PP-bearing "
            "target, reach C2:721D with a rolled PP-loss amount."
        ),
        caveats=(
            "This is action-row steering only; it does not prove vanilla Bash or item/PSI command routing.",
            "If the selected target has zero current PP or zero max-PP range, the result remains a route-only probe.",
        ),
    ),
    "runaway-dog-final-neutralize-c240a4": Scenario(
        id="runaway-dog-final-neutralize-c240a4",
        title="Runaway Dog KO final action forces Neutralize/all C2:40A4 lane",
        purpose=(
            "Give both Runaway Dog enemy rows 1 HP and a final action that "
            "routes through C2:90C6, making KO cleanup a practical C2:40A4 "
            "fixture."
        ),
        patches=(
            {
                "enemy_names": ("Runaway Dog",),
                "hp": 1,
                "final_action": ACTION_NEUTRALIZE_ALL,
                "final_action_argument": 0,
            },
        ),
        expected_probe=(
            "Killing a Runaway Dog should enter the C2 final-action path "
            "and then C2:90C6 -> C2:40A4."
        ),
        caveats=(
            "If instant-win or encounter setup bypasses normal KO resolution, "
            "use the normal-action fixture instead.",
        ),
    ),
    "dread-skelpion-poison-fast": Scenario(
        id="dread-skelpion-poison-fast",
        title="Dread Skelpion normal action repeats poison-sting status lane",
        purpose=(
            "Make Dread Skelpion repeatedly choose its poison-sting action. "
            "This preserves a known C2:724A affliction fixture while making "
            "reruns easier."
        ),
        patches=(
            {
                "enemy_names": ("Dread Skelpion",),
                "normal_actions": (ACTION_DREAD_SKELPION_POISON,) * 4,
                "normal_arguments": (0, 0, 0, 0),
                "action_order": 0,
            },
        ),
        expected_probe=(
            "A Dread Skelpion turn should hit the poison affliction lane, "
            "including C2:724A on successful status write."
        ),
        caveats=(
            "This fixture is for the status-write lane, not the C2:40A4 "
            "second-pointer payload lane.",
        ),
    ),
    "scripted-entry-group0-force-enemy-action": Scenario(
        id="scripted-entry-group0-force-enemy-action",
        title="Scripted battle group 0 autostarts a deterministic Runaway Dog action",
        purpose=(
            "Patch the post-init C0:B9B4 GAME_INIT tail to call C2:2F38 "
            "with A=0 instead of entering MAIN_LOOP, patch the group-0 "
            "scripted battle payload at D0:D52D to contain one Runaway Dog "
            "enemy row, then make that row repeatedly choose the Neutralize/all "
            "action that enters C2:90C6 and C2:40A4."
        ),
        patches=(
            {
                "raw_cpu_patch": "C0:B9B4",
                "bytes": (
                    0xA9,
                    0x00,
                    0x00,
                    0x22,
                    0x38,
                    0x2F,
                    0xC2,
                    0x60,
                ),
                "field": "autostart_init_battle_scripted_group0",
            },
            {
                "scripted_battle_group_payload": "D0:D52D",
                "entries": (
                    {
                        "enemy_row": 121,
                        "repeat_count": 1,
                    },
                ),
                "field": "group0_enemy_list_payload",
            },
            {
                "enemy_rows": (121,),
                "hp": 999,
                "speed": 255,
                "normal_actions": (ACTION_NEUTRALIZE_ALL,) * 4,
                "normal_arguments": (0, 0, 0, 0),
                "action_order": 0,
            },
        ),
        expected_probe=(
            "Booting the fixture ROM should hit C2:2F38, scripted battle group "
            "0 should expand to one Runaway Dog row, and the enemy turn should "
            "reach C2:90C6 -> C2:40A4."
        ),
        caveats=(
            "The C0:B9B4 hook replaces GAME_INIT's STZ DEBUG, JSL MAIN_LOOP, and RTS tail in this generated ROM only.",
            "The hook runs after SRAM, music, NMI/joypad, hardware check, and two frame waits, but before MAIN_LOOP intro/file-select setup.",
            "The Runaway Dog row is made durable and fast so a simple command-confirm input pattern can reach the fixture action lane.",
            "Use the first successful run as reachability smoke evidence before promoting this as a stable oracle fixture.",
            "The enemy action is fixture-steered and must not be promoted as vanilla Runaway Dog behavior.",
        ),
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build ignored table-patched EarthBound fixture ROMs for C2 runtime probes."
    )
    parser.add_argument("--rom", help="Path to a clean EarthBound (USA).sfc ROM")
    parser.add_argument(
        "--scenario",
        action="append",
        choices=sorted([*SCENARIOS.keys(), "all"]),
        default=None,
        help="Scenario to build. May be repeated. Defaults to all.",
    )
    parser.add_argument(
        "--output-root",
        default="build/c2/fixture-roms",
        help="Output directory for generated fixture ROMs and manifests.",
    )
    return parser.parse_args()


def load_enemy_rows(root: Path) -> dict[int, dict[str, Any]]:
    path = root / "refs" / "eb-decompile-4ef92" / "enemy_configuration_table.yml"
    if not path.is_file():
        raise FileNotFoundError(f"Missing enemy table reference: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Unexpected enemy table YAML shape: {path}")
    return {int(key): value for key, value in payload.items()}


def selected_scenarios(raw: list[str] | None) -> list[Scenario]:
    if not raw:
        return [SCENARIOS[key] for key in sorted(SCENARIOS)]
    if "all" in raw:
        return [SCENARIOS[key] for key in sorted(SCENARIOS)]
    return [SCENARIOS[key] for key in raw]


def checksum16(data: bytes | bytearray) -> int:
    return sum(data) & 0xFFFF


def write_u16_le(data: bytearray, offset: int, value: int) -> bytes:
    old = bytes(data[offset : offset + 2])
    data[offset] = value & 0xFF
    data[offset + 1] = (value >> 8) & 0xFF
    return old


def write_u8(data: bytearray, offset: int, value: int) -> bytes:
    old = bytes(data[offset : offset + 1])
    data[offset] = value & 0xFF
    return old


def normalize_snes_checksum(data: bytearray) -> dict[str, str]:
    data[0xFFDC:0xFFE0] = b"\x00\x00\x00\x00"
    checksum = checksum16(data)
    complement = checksum ^ 0xFFFF
    write_u16_le(data, 0xFFDC, complement)
    write_u16_le(data, 0xFFDE, checksum)
    return {
        "checksum": f"0x{checksum:04X}",
        "complement": f"0x{complement:04X}",
    }


def enemy_row_file_offset(row: int, field: str, rom_size: int) -> int:
    cpu_address = ENEMY_TABLE_ADDRESS + row * ENEMY_TABLE_STRIDE + ENEMY_FIELD_OFFSETS[field]
    offset = hirom_to_file_offset(ENEMY_TABLE_BANK, cpu_address, rom_size)
    if offset is None:
        raise ValueError(f"Enemy row {row} field {field} is not a ROM address")
    return offset


def cpu_label_for_enemy_field(row: int, field: str) -> str:
    return f"{ENEMY_TABLE_BANK:02X}:{ENEMY_TABLE_ADDRESS + row * ENEMY_TABLE_STRIDE + ENEMY_FIELD_OFFSETS[field]:04X}"


def battle_action_row_file_offset(row: int, field: str, rom_size: int) -> int:
    cpu_address = BATTLE_ACTION_TABLE_ADDRESS + row * BATTLE_ACTION_TABLE_STRIDE + BATTLE_ACTION_FIELD_OFFSETS[field]
    offset = hirom_to_file_offset(BATTLE_ACTION_TABLE_BANK, cpu_address, rom_size)
    if offset is None:
        raise ValueError(f"Battle action row {row} field {field} is not a ROM address")
    return offset


def cpu_label_for_battle_action_field(row: int, field: str) -> str:
    return (
        f"{BATTLE_ACTION_TABLE_BANK:02X}:"
        f"{BATTLE_ACTION_TABLE_ADDRESS + row * BATTLE_ACTION_TABLE_STRIDE + BATTLE_ACTION_FIELD_OFFSETS[field]:04X}"
    )


def parse_cpu_label(label: str) -> tuple[int, int]:
    if ":" not in label:
        raise ValueError(f"CPU label must be BANK:ADDR: {label}")
    bank_text, address_text = label.split(":", 1)
    return int(bank_text, 16), int(address_text, 16)


def format_bytes(data: bytes) -> str:
    return " ".join(f"{byte:02X}" for byte in data)


def matching_enemy_rows(enemy_rows: dict[int, dict[str, Any]], names: tuple[str, ...]) -> list[int]:
    wanted = set(names)
    rows = [row for row, payload in enemy_rows.items() if payload.get("Name") in wanted]
    if not rows:
        raise ValueError(f"No enemy rows found for names: {', '.join(names)}")
    return rows


def add_patch(
    data: bytearray,
    enemy_rows: dict[int, dict[str, Any]],
    row: int,
    field: str,
    value: int,
    reason: str,
) -> Patch | None:
    width = 2 if field in {"hp", "action_1", "action_2", "action_3", "action_4", "final_action"} else 1
    offset = enemy_row_file_offset(row, field, len(data))
    if width == 2:
        new = bytes((value & 0xFF, (value >> 8) & 0xFF))
        old = bytes(data[offset : offset + 2])
        if old == new:
            return None
        write_u16_le(data, offset, value)
    else:
        new = bytes((value & 0xFF,))
        old = bytes(data[offset : offset + 1])
        if old == new:
            return None
        write_u8(data, offset, value)
    return Patch(
        table="ENEMY_CONFIGURATION_TABLE",
        row=row,
        row_name=str(enemy_rows[row].get("Name")),
        field=field,
        cpu_address=cpu_label_for_enemy_field(row, field),
        file_offset=f"0x{offset:06X}",
        old=format_bytes(old),
        new=format_bytes(new),
        reason=reason,
    )


def encode_battle_action_value(field: str, value: Any) -> bytes:
    if field in {"direction", "target", "action_type", "pp_cost"}:
        return bytes((int(value) & 0xFF,))
    if field in {"message_pointer", "action_pointer"}:
        bank, address = value
        return bytes((address & 0xFF, (address >> 8) & 0xFF, bank & 0xFF, 0x00))
    raise ValueError(f"Unsupported battle action field: {field}")


def add_battle_action_patch(
    data: bytearray,
    row: int,
    field: str,
    value: Any,
    reason: str,
) -> Patch | None:
    new = encode_battle_action_value(field, value)
    offset = battle_action_row_file_offset(row, field, len(data))
    old = bytes(data[offset : offset + len(new)])
    if old == new:
        return None
    data[offset : offset + len(new)] = new
    return Patch(
        table="BATTLE_ACTION_TABLE",
        row=row,
        row_name=f"battle_action_{row}",
        field=field,
        cpu_address=cpu_label_for_battle_action_field(row, field),
        file_offset=f"0x{offset:06X}",
        old=format_bytes(old),
        new=format_bytes(new),
        reason=reason,
    )


def add_raw_cpu_patch(
    data: bytearray,
    label: str,
    new: bytes,
    field: str,
    reason: str,
    table: str = "RAW_CPU_CODE_PATCH",
    row_name: str | None = None,
) -> Patch | None:
    bank, address = parse_cpu_label(label)
    offset = hirom_to_file_offset(bank, address, len(data))
    if offset is None:
        raise ValueError(f"Raw CPU patch address is not a ROM address: {label}")
    old = bytes(data[offset : offset + len(new)])
    if old == new:
        return None
    data[offset : offset + len(new)] = new
    return Patch(
        table=table,
        row=0,
        row_name=row_name or label,
        field=field,
        cpu_address=label,
        file_offset=f"0x{offset:06X}",
        old=format_bytes(old),
        new=format_bytes(new),
        reason=reason,
    )


def encode_scripted_battle_group_payload(
    enemy_rows: dict[int, dict[str, Any]],
    entries: tuple[dict[str, Any], ...],
) -> tuple[bytes, str]:
    output = bytearray()
    labels: list[str] = []
    for entry in entries:
        row = int(entry["enemy_row"])
        if row not in enemy_rows:
            raise ValueError(f"Unknown enemy row for battle group payload: {row}")
        repeat_count = int(entry.get("repeat_count", 1))
        if not 0 <= repeat_count <= 0xFE:
            raise ValueError(f"Battle group repeat_count must fit one non-FF byte: {repeat_count}")
        output.append(repeat_count)
        output.extend((row & 0xFF, (row >> 8) & 0xFF))
        labels.append(f"{repeat_count}x {enemy_rows[row].get('Name')} (enemy row {row})")
    output.append(0xFF)
    return bytes(output), "; ".join(labels)


def apply_scenario(
    clean_rom: bytes,
    enemy_rows: dict[int, dict[str, Any]],
    scenario: Scenario,
) -> tuple[bytearray, list[Patch]]:
    data = bytearray(clean_rom)
    patches: list[Patch] = []
    def record(patch: Patch | None) -> None:
        if patch is not None:
            patches.append(patch)

    for patch_spec in scenario.patches:
        reason = f"{scenario.id}: {scenario.purpose}"
        if "raw_cpu_patch" in patch_spec:
            record(
                add_raw_cpu_patch(
                    data,
                    str(patch_spec["raw_cpu_patch"]),
                    bytes(int(byte) & 0xFF for byte in patch_spec["bytes"]),
                    str(patch_spec.get("field", "raw_bytes")),
                    reason,
                )
            )
            continue

        if "scripted_battle_group_payload" in patch_spec:
            new, row_name = encode_scripted_battle_group_payload(
                enemy_rows,
                tuple(patch_spec["entries"]),
            )
            record(
                add_raw_cpu_patch(
                    data,
                    str(patch_spec["scripted_battle_group_payload"]),
                    new,
                    str(patch_spec.get("field", "scripted_battle_group_payload")),
                    reason,
                    table="ENEMY_BATTLE_GROUPS_TABLE",
                    row_name=row_name,
                )
            )
            continue

        if "battle_action_row" in patch_spec:
            row = int(patch_spec["battle_action_row"])
            for field, value in patch_spec.get("battle_action_field_values", {}).items():
                record(add_battle_action_patch(data, row, field, value, reason))
            continue

        if "enemy_rows" in patch_spec:
            rows = [int(row) for row in patch_spec["enemy_rows"]]
            for row in rows:
                if row not in enemy_rows:
                    raise ValueError(f"Unknown enemy row for fixture patch: {row}")
        else:
            rows = matching_enemy_rows(enemy_rows, tuple(patch_spec["enemy_names"]))
        for row in rows:
            reason = f"{scenario.id}: {scenario.purpose}"
            if "hp" in patch_spec:
                record(add_patch(data, enemy_rows, row, "hp", patch_spec["hp"], reason))
            if "speed" in patch_spec:
                record(add_patch(data, enemy_rows, row, "speed", patch_spec["speed"], reason))
            if "action_order" in patch_spec:
                record(add_patch(data, enemy_rows, row, "action_order", patch_spec["action_order"], reason))
            for index, action in enumerate(patch_spec.get("normal_actions", ())):
                record(add_patch(data, enemy_rows, row, f"action_{index + 1}", action, reason))
            for index, argument in enumerate(patch_spec.get("normal_arguments", ())):
                record(add_patch(data, enemy_rows, row, f"action_{index + 1}_argument", argument, reason))
            if "final_action" in patch_spec:
                record(add_patch(data, enemy_rows, row, "final_action", patch_spec["final_action"], reason))
            if "final_action_argument" in patch_spec:
                record(
                    add_patch(
                        data,
                        enemy_rows,
                        row,
                        "final_action_argument",
                        patch_spec["final_action_argument"],
                        reason,
                    )
                )
    return data, patches


def ensure_workspace_child(path: Path, root: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside the workspace: {resolved}") from exc
    return resolved


def write_manifest(
    output_dir: Path,
    scenario: Scenario,
    clean_info: dict[str, Any],
    patched_path: Path,
    patched_data: bytes,
    patches: list[Patch],
    checksum_info: dict[str, str],
) -> None:
    manifest = {
        "schema": "c2_fixture_rom.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scenario": {
            "id": scenario.id,
            "title": scenario.title,
            "purpose": scenario.purpose,
            "expected_probe": scenario.expected_probe,
            "caveats": list(scenario.caveats),
        },
        "clean_rom": clean_info,
        "patched_rom": {
            "path": str(patched_path),
            "size": len(patched_data),
            "sha1": hashlib.sha1(patched_data).hexdigest(),
            "snes_header": checksum_info,
        },
        "patches": [patch.__dict__ for patch in patches],
        "source_evidence": [
            "refs/EB-M2-Listing-v1/US/bank15.txt documents ENEMY_CONFIGURATION_TABLE field offsets",
            "notes/d0-variable-list-contracts.md documents D0:D52D enemy battle-group payload entries",
            "notes/c2-scripted-battle-fixture-workahead.md describes the scripted-entry fixture boundary",
            "refs/ebsrc-main/ebsrc-main/src/unknown/C2/C240A4.asm documents the two-pass target loop",
            "refs/ebsrc-main/ebsrc-main/src/unknown/C2/C290C6.asm calls C2:40A4 with TARGET_ALL",
            "notes/c2-battle-trace-manual-probe-matrix.md tracks remaining C2:40A4 fixture gap",
        ],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_readme(output_dir: Path, scenario: Scenario, patches: list[Patch]) -> None:
    rows = "\n".join(
        f"- `{patch.cpu_address}` `{patch.field}` row {patch.row} "
        f"({patch.row_name}): `{patch.old}` -> `{patch.new}`"
        for patch in patches
    )
    output = f"""# {scenario.title}

Scenario id: `{scenario.id}`

{scenario.purpose}

Expected probe:

{scenario.expected_probe}

Patch summary:

{rows}

Caveats:

{chr(10).join(f'- {item}' for item in scenario.caveats) if scenario.caveats else '- None'}

Generated files in this directory are build artifacts and should not be committed.
"""
    (output_dir / "README.md").write_text(output, encoding="utf-8")


def main() -> int:
    args = parse_args()
    root = workspace_root()
    rom_path = find_rom(args.rom)
    rom_info = read_rom_info(rom_path)
    problems = verify_earthbound_us(rom_info)
    if problems:
        raise SystemExit("Input ROM is not the clean EarthBound (USA) ROM:\n- " + "\n- ".join(problems))
    if rom_info.sha1 != EXPECTED_SHA1:
        raise SystemExit(f"Unexpected clean ROM SHA-1: {rom_info.sha1}")

    enemy_rows = load_enemy_rows(root)
    clean_rom = load_rom(rom_path)
    output_root = ensure_workspace_child(root / args.output_root, root, "output root")
    output_root.mkdir(parents=True, exist_ok=True)

    built: list[dict[str, str]] = []
    for scenario in selected_scenarios(args.scenario):
        scenario_dir = ensure_workspace_child(output_root / scenario.id, output_root, "scenario output")
        if scenario_dir.exists():
            shutil.rmtree(scenario_dir)
        scenario_dir.mkdir(parents=True)

        patched_data, patches = apply_scenario(clean_rom, enemy_rows, scenario)
        checksum_info = normalize_snes_checksum(patched_data)

        patched_path = scenario_dir / f"EarthBound-USA-{scenario.id}.sfc"
        patched_path.write_bytes(patched_data)
        write_manifest(
            scenario_dir,
            scenario,
            {
                "path": str(rom_path),
                "size": rom_info.size,
                "sha1": rom_info.sha1,
            },
            patched_path,
            patched_data,
            patches,
            checksum_info,
        )
        write_readme(scenario_dir, scenario, patches)
        built.append(
            {
                "scenario": scenario.id,
                "rom": str(patched_path),
                "sha1": hashlib.sha1(patched_data).hexdigest(),
            }
        )

    print(json.dumps({"built": built}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
