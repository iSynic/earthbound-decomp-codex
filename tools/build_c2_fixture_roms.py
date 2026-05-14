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

FIELD_OFFSETS = {
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

ACTION_NEUTRALIZE_ALL = 248
ACTION_DREAD_SKELPION_POISON = 72


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
        default=["all"],
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


def selected_scenarios(raw: list[str]) -> list[Scenario]:
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
    cpu_address = ENEMY_TABLE_ADDRESS + row * ENEMY_TABLE_STRIDE + FIELD_OFFSETS[field]
    offset = hirom_to_file_offset(ENEMY_TABLE_BANK, cpu_address, rom_size)
    if offset is None:
        raise ValueError(f"Enemy row {row} field {field} is not a ROM address")
    return offset


def cpu_label_for_enemy_field(row: int, field: str) -> str:
    return f"{ENEMY_TABLE_BANK:02X}:{ENEMY_TABLE_ADDRESS + row * ENEMY_TABLE_STRIDE + FIELD_OFFSETS[field]:04X}"


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
        rows = matching_enemy_rows(enemy_rows, tuple(patch_spec["enemy_names"]))
        for row in rows:
            reason = f"{scenario.id}: {scenario.purpose}"
            if "hp" in patch_spec:
                record(add_patch(data, enemy_rows, row, "hp", patch_spec["hp"], reason))
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
