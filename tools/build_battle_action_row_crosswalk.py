#!/usr/bin/env python3
"""Build a source-facing crosswalk for D5:7B68 battle action rows."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import inspect_battle_action
from rom_tools import find_rom, load_rom


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "manifests" / "battle-action-row-crosswalk.json"
DEFAULT_NOTES = ROOT / "notes" / "battle-action-row-crosswalk.md"
ROW_COUNT = 318
ROLE_TOKENS = [
    "RowPresentationText",
    "FlavorRowPresentationText",
    "ActionAmount",
    "ByteSubstitution",
    "PointerSubstitution",
    "StatusResult",
    "ResultText",
    "ItemUsePayloadText",
    "OpeningText",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build D5 battle action row crosswalk manifest/note.")
    parser.add_argument("--rom", help="Path to EarthBound (USA).sfc.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--notes", default=str(DEFAULT_NOTES))
    parser.add_argument("--row-count", type=int, default=ROW_COUNT)
    return parser.parse_args()


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def manifest_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def source_label_map() -> dict[str, list[dict[str, Any]]]:
    labels: dict[str, list[dict[str, Any]]] = defaultdict(list)
    label_re = re.compile(r"^([A-F0-9]{6}_[A-Za-z0-9_]*):")
    alias_re = re.compile(r"^([A-F0-9]{6}_[A-Za-z0-9_]*)\s*=")
    for path in sorted((ROOT / "src").glob("**/*.asm")):
        if path.name.endswith(".bytes.asar.asm"):
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for lineno, line in enumerate(lines, start=1):
            match = label_re.match(line) or alias_re.match(line)
            if not match:
                continue
            name = match.group(1)
            prefix = name[:6].upper()
            addr = f"{prefix[:2]}:{prefix[2:]}"
            labels[addr].append(
                {
                    "name": name,
                    "source": manifest_path(path),
                    "line": lineno,
                }
            )
    return dict(labels)


def pointer_bank(addr_text: str) -> str:
    return addr_text.split(":", 1)[0]


def message_lane(addr_text: str) -> str:
    bank = pointer_bank(addr_text)
    if addr_text == "00:0000":
        return "no_message_pointer"
    if bank == "EF":
        return "ef_row_message"
    if bank in {"C6", "C7", "C8", "C9"}:
        return "non_ef_row_message"
    return "other_message_bank"


def action_lane(addr_text: str) -> str:
    bank = pointer_bank(addr_text)
    if addr_text == "00:0000":
        return "no_action_pointer"
    if bank == "C2":
        return "c2_behavior_body"
    return "other_action_bank"


def role_hints(labels: list[dict[str, Any]]) -> list[str]:
    found: list[str] = []
    for label in labels:
        name = str(label["name"])
        for token in ROLE_TOKENS:
            if token in name and token not in found:
                found.append(token)
    return found


def row_record(entry: inspect_battle_action.BattleActionEntry, labels: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    message = inspect_battle_action.fmt_addr(entry.message_ptr)
    action = inspect_battle_action.fmt_addr(entry.action_ptr)
    message_labels = labels.get(message, [])
    action_labels = labels.get(action, [])
    return {
        "row": entry.index,
        "table_address": entry.cpu_address,
        "direction": {
            "value": entry.direction,
            "name": inspect_battle_action.DIRECTION_NAMES.get(entry.direction, "unknown"),
        },
        "target": {
            "value": entry.target,
            "name": inspect_battle_action.TARGET_NAMES.get(entry.target, "unknown"),
        },
        "action_type": {
            "value": entry.action_type,
            "name": inspect_battle_action.TYPE_NAMES.get(entry.action_type, "unknown"),
        },
        "cost": entry.cost,
        "message_pointer": message,
        "message_bank": pointer_bank(message),
        "message_lane": message_lane(message),
        "message_source_labels": message_labels,
        "message_role_hints": role_hints(message_labels),
        "action_pointer": action,
        "action_bank": pointer_bank(action),
        "action_lane": action_lane(action),
        "action_source_labels": action_labels,
        "source_promotion_allowed": False,
        "behavior_change_allowed": False,
    }


def build_manifest(rom: bytes, row_count: int) -> dict[str, Any]:
    labels = source_label_map()
    rows = [row_record(inspect_battle_action.load_entry(rom, index), labels) for index in range(row_count)]
    message_lanes = Counter(row["message_lane"] for row in rows)
    action_lanes = Counter(row["action_lane"] for row in rows)
    message_banks = Counter(row["message_bank"] for row in rows)
    action_banks = Counter(row["action_bank"] for row in rows)
    rows_with_ef_labels = sum(1 for row in rows if row["message_lane"] == "ef_row_message" and row["message_source_labels"])
    rows_with_c2_labels = sum(1 for row in rows if row["action_lane"] == "c2_behavior_body" and row["action_source_labels"])
    return {
        "schema": "earthbound-decomp.battle-action-row-crosswalk.v1",
        "status": "generated_from_local_rom_and_source_labels",
        "table": {
            "contract_id": "BATTLE_ACTION_TABLE",
            "address": f"{inspect_battle_action.TABLE_BANK:02X}:{inspect_battle_action.TABLE_ADDR:04X}",
            "stride": inspect_battle_action.ENTRY_SIZE,
            "row_count": row_count,
        },
        "source_inputs": [
            "src/d5/table_battle_action_table.asm",
            "src/ef/ef_4e20_c51b_text_payload_data.asm",
            "src/c2/",
            "notes/ef-battle-text-row-message-crosswalk.md",
            "notes/ef-battle-text-row-pointer-recovery-frontier.md",
        ],
        "summary": {
            "row_count": len(rows),
            "message_lanes": dict(sorted(message_lanes.items())),
            "action_lanes": dict(sorted(action_lanes.items())),
            "message_banks": dict(sorted(message_banks.items())),
            "action_banks": dict(sorted(action_banks.items())),
            "ef_message_rows_with_source_labels": rows_with_ef_labels,
            "c2_action_rows_with_source_labels": rows_with_c2_labels,
            "source_promotion_allowed": False,
            "behavior_change_allowed": False,
        },
        "rows": rows,
    }


def short_label(labels: list[dict[str, Any]]) -> str:
    if not labels:
        return ""
    name = str(labels[0]["name"])
    if len(name) <= 52:
        return name
    return name[:49] + "..."


def render_bank_counts(title: str, counts: dict[str, int]) -> list[str]:
    lines = [f"## {title}", "", "| Key | Rows |", "| --- | ---: |"]
    for key, value in counts.items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.append("")
    return lines


def render_note(data: dict[str, Any]) -> str:
    summary = data["summary"]
    rows = data["rows"]
    lines = [
        "# Battle Action Row Crosswalk",
        "",
        "Generated by `tools/build_battle_action_row_crosswalk.py` from the local",
        "`D5:7B68` battle action table and checked-in source labels. This is a",
        "Phase 2 navigation artifact: it classifies row `+4` message pointers and",
        "row `+8` behavior pointers, but it does not promote source names or claim",
        "runtime behavior by itself.",
        "",
        "## Summary",
        "",
        f"- rows: `{summary['row_count']}`",
        f"- EF row-message pointers: `{summary['message_lanes'].get('ef_row_message', 0)}`",
        f"- non-EF row-message pointers: `{summary['message_lanes'].get('non_ef_row_message', 0)}`",
        f"- C2 behavior pointers: `{summary['action_lanes'].get('c2_behavior_body', 0)}`",
        f"- EF message rows with source labels: `{summary['ef_message_rows_with_source_labels']}`",
        f"- C2 behavior rows with source labels: `{summary['c2_action_rows_with_source_labels']}`",
        f"- source promotion allowed: `{str(summary['source_promotion_allowed']).lower()}`",
        "",
        "Use this together with `notes/ef-battle-text-row-message-crosswalk.md`",
        "and `notes/ef-battle-text-row-pointer-recovery-frontier.md`. If row `+4`",
        "points outside EF, do not rename EF anchors; if row `+8` emits a later EF",
        "result script, document that as a secondary result lane instead.",
        "",
        *render_bank_counts("Message Lanes", summary["message_lanes"]),
        *render_bank_counts("Message Banks", summary["message_banks"]),
        *render_bank_counts("Action Lanes", summary["action_lanes"]),
        "## Rows",
        "",
        "| Row | Type | Target | Cost | Message | Message lane | Message label | Action | Action label |",
        "| ---: | --- | --- | ---: | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| `{row}` | `{action_type}` | `{target}` | `{cost}` | `{message}` | `{message_lane}` | `{message_label}` | `{action}` | `{action_label}` |".format(
                row=row["row"],
                action_type=row["action_type"]["name"],
                target=row["target"]["name"],
                cost=row["cost"],
                message=row["message_pointer"],
                message_lane=row["message_lane"],
                message_label=short_label(row["message_source_labels"]),
                action=row["action_pointer"],
                action_label=short_label(row["action_source_labels"]),
            )
        )
    lines.extend(
        [
            "",
            "## Validation",
            "",
            "```powershell",
            "python tools\\build_battle_action_row_crosswalk.py",
            "python tools\\validate_battle_action_row_crosswalk.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    rom = load_rom(find_rom(args.rom))
    manifest = build_manifest(rom, args.row_count)
    output = Path(args.output)
    notes = Path(args.notes)
    write_json(output, manifest)
    write_text(notes, render_note(manifest))
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    print(
        "Battle action row crosswalk: "
        f"{manifest['summary']['row_count']} rows, "
        f"{manifest['summary']['message_lanes'].get('ef_row_message', 0)} EF messages"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
