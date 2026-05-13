from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from decode_event_script import (
    ACTIONSCRIPT_ANIMATION_IDS,
    ACTIONSCRIPT_DIRECTION_WORDS,
    ACTIONSCRIPT_ENTITY_SCRIPT_IDS,
    ACTIONSCRIPT_FIELD2B32_WORDS,
    ACTIONSCRIPT_SOUND_EFFECT_IDS,
    ACTIONSCRIPT_SPRITE_POSE_DESCRIPTOR_WORDS,
    ACTIONSCRIPT_SURFACE_FLAGS_BYTES,
    ACTIONSCRIPT_VISUAL_COUNTDOWN_BYTES,
    ACTIONSCRIPT_VISUAL_STATE_BYTES,
    Address,
    CALL_ARG_COUNTS,
    CALL_TARGET_SEMANTICS,
    OPCODES,
    OPCODE_ARG_FIELDS,
    decode_script,
    load_names,
    parse_address,
)
from rom_tools import find_rom, hirom_to_file_offset, load_rom


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "earthbound-decomp.c3-actionscript-semantics-audit.v1"
DEFAULT_SOURCE_MAP = ROOT / "build" / "c3-source-data-map.json"
DEFAULT_INDEX = ROOT / "build" / "ref-index.json"
DEFAULT_JSON_OUT = ROOT / "build" / "c3-actionscript-semantics-audit.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "c3-actionscript-semantics-audit.md"

SCRIPT_CLASSES = {
    "event-script-asset",
    "event-bytecode-asset",
    "event-bytecode-label",
}

CALLROUTINE_RE = re.compile(r"EVENT_CALLROUTINE\s+\$([0-9A-F]{2}:[0-9A-F]{4})")
INSTALLED_CALLBACK_RE = re.compile(
    r"EVENT_SET_(?:TICK|DRAW|POSITION_CHANGE|PHYSICS)_CALLBACK\s+(?:[a-z_]+=\s*)?\$([0-9A-F]{2}:[0-9A-F]{4})"
)
TARGET_RE = re.compile(r"\$([0-9A-F]{2}:[0-9A-F]{4})")
UNKNOWN_OPCODE_RE = re.compile(r"^([0-9A-F]{2}:[0-9A-F]{4}).*unknown event opcode")
UNKNOWN_CALL_TARGET_RE = re.compile(
    r"EVENT_CALLROUTINE\s+\$([0-9A-F]{2}:[0-9A-F]{4}).*args unknown"
)
ANIMATION_ID_RE = re.compile(r"EVENT_SET_ANIMATION\s+animation_id=\$([0-9A-F]{2})")
FIELD2B32_WORD_RE = re.compile(r"field2b32_word=\$([0-9A-F]{4})")
TEMPVAR_WORD_RE = re.compile(r"EVENT_WRITE_WORD_TEMPVAR\s+value_word=\$([0-9A-F]{4})")
VISUAL_STATE_BYTE_RE = re.compile(r"visual_state_byte=\$([0-9A-F]{2})")
VISUAL_COUNTDOWN_BYTE_RE = re.compile(r"countdown_byte=\$([0-9A-F]{2})")
SURFACE_FLAGS_BYTE_RE = re.compile(r"surface_flags_byte=\$([0-9A-F]{2})")
SPRITE_POSE_DESCRIPTOR_WORD_RE = re.compile(r"sprite_pose_descriptor_word=\$([0-9A-F]{4})")
ENTITY_SCRIPT_ID_WORD_RE = re.compile(r"entity_script_id_word=\$([0-9A-F]{4})")
SOUND_EFFECT_ID_WORD_RE = re.compile(r"sound_effect_id_word=\$([0-9A-F]{4})")
DECODED_ADDRESS_RE = re.compile(r"^([0-9A-F]{2}:[0-9A-F]{4})")
RANDOM_CHOICES_RE = re.compile(r"EVENT_CALLROUTINE\s+\$C0:9F82\b.*choices=\d+\s+\[([^\]]+)\]")

DIRECTION_TEMPVAR_CONSUMERS = {
    "C0:A65F": "SetCurrentSlotDirectionClassIfActive",
    "C0:C83B": "InstallScriptMovementVectorFromDirection",
}

FIELD2B32_CONSUMERS = {
    "C0:C83B": "InstallScriptMovementVectorFromDirection",
    "C0:CA4E": "SetMovementTaskTimerFromActiveVector",
    "C0:A6A2": "Script_SetMovementStateCA4E",
    "C0:A6AD": "Script_SetMovementStateCBD3",
    "C0:CBD3": "SetMovementTaskTimerFromSpeedScale",
}

TEMPVAR_REPLACING_OPCODES = {
    "EVENT_WRITE_WORD_TEMPVAR",
    "EVENT_WRITE_WRAM_TEMPVAR",
    "EVENT_WRITE_VAR_TO_TEMPVAR",
}

TEMPVAR_MUTATING_OPCODES = {
    "EVENT_BINOP_TEMPVAR",
    "EVENT_LOOP_TEMPVAR",
}


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def address_sort_key(address: str) -> int:
    parsed = parse_address(address)
    return parsed.long


def rom_offset_for(rom: bytes, address: Address) -> int | None:
    offset = hirom_to_file_offset(address.bank, address.offset, len(rom))
    if offset is None or offset >= len(rom):
        return None
    return offset


def raw_preview(rom: bytes, address: Address, length: int = 16) -> str:
    offset = rom_offset_for(rom, address)
    if offset is None:
        return ""
    return " ".join(f"{byte:02X}" for byte in rom[offset : offset + length])


def first_opcode(rom: bytes, address: Address) -> dict[str, Any]:
    offset = rom_offset_for(rom, address)
    if offset is None:
        return {"byte": None, "name": "unmapped", "known": False}
    value = rom[offset]
    opcode = OPCODES.get(value)
    return {
        "byte": f"${value:02X}",
        "name": opcode.name if opcode else "UNKNOWN_EVENT_OPCODE",
        "known": opcode is not None,
        "operands": list(opcode.args) if opcode else [],
        "operand_fields": list(OPCODE_ARG_FIELDS.get(opcode.name, ())) if opcode else [],
        "terminal": bool(opcode.terminal) if opcode else False,
    }


def opcode_control_flow_role(opcode: Any) -> str:
    if opcode.terminal:
        return "terminal"
    if opcode.name in {
        "EVENT_LONGJUMP",
        "EVENT_SHORTJUMP",
        "EVENT_SWITCH_JUMP_TEMPVAR",
        "EVENT_BREAK_IF_FALSE",
        "EVENT_BREAK_IF_TRUE",
    }:
        return "branch"
    if opcode.name in {
        "EVENT_LONGCALL",
        "EVENT_SHORTCALL",
        "EVENT_SHORTCALL_CONDITIONAL",
        "EVENT_SHORTCALL_CONDITIONAL_NOT",
        "EVENT_SWITCH_CALL_TEMPVAR",
    }:
        return "script call"
    if opcode.name in {
        "EVENT_SET_TICK_CALLBACK",
        "EVENT_SET_DRAW_CALLBACK",
        "EVENT_SET_POSITION_CHANGE_CALLBACK",
        "EVENT_SET_PHYSICS_CALLBACK",
        "EVENT_CLEAR_TICK_CALLBACK",
    }:
        return "callback binding"
    if opcode.name in {"EVENT_START_TASK", "EVENT_END_TASK", "EVENT_END_LAST_TASK"}:
        return "task control"
    if opcode.name in {"EVENT_LOOP", "EVENT_LOOP_END", "EVENT_LOOP_TEMPVAR"}:
        return "loop control"
    return "state/operand"


def build_opcode_catalog() -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    for opcode_byte, opcode in sorted(OPCODES.items()):
        fields = list(OPCODE_ARG_FIELDS.get(opcode.name, ()))
        catalog.append(
            {
                "opcode": f"${opcode_byte:02X}",
                "name": opcode.name,
                "byte_shape": list(opcode.args),
                "semantic_fields": fields,
                "control_flow_role": opcode_control_flow_role(opcode),
                "terminal": opcode.terminal,
                "confidence": "high",
            }
        )
    return catalog


def collect_operand_value_signals(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    animation_ids: Counter[str] = Counter()
    field2b32_words: Counter[str] = Counter()
    visual_state_bytes: Counter[str] = Counter()
    visual_countdown_bytes: Counter[str] = Counter()
    surface_flags_bytes: Counter[str] = Counter()
    sprite_pose_descriptor_words: Counter[str] = Counter()
    entity_script_ids: Counter[str] = Counter()
    sound_effect_ids: Counter[str] = Counter()
    tempvar_direction_word_candidates: Counter[str] = Counter()
    direction_values = set(ACTIONSCRIPT_DIRECTION_WORDS)

    for row in rows:
        for line in row["decoded"]:
            if match := ANIMATION_ID_RE.search(line):
                animation_ids[f"${int(match.group(1), 16):02X}"] += 1
            if match := FIELD2B32_WORD_RE.search(line):
                field2b32_words[f"${int(match.group(1), 16):04X}"] += 1
            if match := VISUAL_STATE_BYTE_RE.search(line):
                visual_state_bytes[f"${int(match.group(1), 16):02X}"] += 1
            if match := VISUAL_COUNTDOWN_BYTE_RE.search(line):
                visual_countdown_bytes[f"${int(match.group(1), 16):02X}"] += 1
            if match := SURFACE_FLAGS_BYTE_RE.search(line):
                surface_flags_bytes[f"${int(match.group(1), 16):02X}"] += 1
            if match := SPRITE_POSE_DESCRIPTOR_WORD_RE.search(line):
                sprite_pose_descriptor_words[f"${int(match.group(1), 16):04X}"] += 1
            if match := ENTITY_SCRIPT_ID_WORD_RE.search(line):
                entity_script_ids[f"${int(match.group(1), 16):04X}"] += 1
            if match := SOUND_EFFECT_ID_WORD_RE.search(line):
                sound_effect_ids[f"${int(match.group(1), 16):04X}"] += 1
            if match := TEMPVAR_WORD_RE.search(line):
                value = int(match.group(1), 16)
                if value in direction_values:
                    tempvar_direction_word_candidates[f"${value:04X}"] += 1

    return {
        "animation_ids": dict(animation_ids.most_common()),
        "field2b32_words": dict(field2b32_words.most_common()),
        "visual_state_bytes": dict(visual_state_bytes.most_common()),
        "visual_countdown_bytes": dict(visual_countdown_bytes.most_common()),
        "surface_flags_bytes": dict(surface_flags_bytes.most_common()),
        "sprite_pose_descriptor_words": dict(sprite_pose_descriptor_words.most_common()),
        "entity_script_ids": dict(entity_script_ids.most_common()),
        "sound_effect_ids": dict(sound_effect_ids.most_common()),
        "tempvar_direction_word_candidates": dict(
            tempvar_direction_word_candidates.most_common()
        ),
    }


def parse_choice_values(text: str) -> list[int]:
    values: list[int] = []
    for match in re.findall(r"\$([0-9A-F]{4})", text):
        value = int(match, 16)
        values.append(value)
    return values


def collect_direction_boundary_signals(
    entries: list[dict[str, Any]],
    rom: bytes,
    names: dict[str, list[str]],
    *,
    max_instructions: int,
    max_bytes: int,
) -> dict[str, Any]:
    events: dict[tuple[str, str, tuple[int, ...]], dict[str, Any]] = {}
    direction_values = set(ACTIONSCRIPT_DIRECTION_WORDS)

    for entry in entries:
        address = parse_address(str(entry["address"]))
        size = entry.get("size")
        decode_bytes = min(size, max_bytes) if isinstance(size, int) and size > 0 else max_bytes
        lines = decode_script(
            rom,
            address,
            max_instructions=max_instructions,
            max_bytes=decode_bytes,
            stop_at_terminal=False,
            names=names,
        )
        pending: list[dict[str, Any]] = []
        for line in lines:
            address_match = DECODED_ADDRESS_RE.match(line)
            if not address_match:
                continue
            line_address = address_match.group(1)

            if match := TEMPVAR_WORD_RE.search(line):
                value = int(match.group(1), 16)
                if value in direction_values:
                    pending.append(
                        {
                            "producer_address": line_address,
                            "source": "EVENT_WRITE_WORD_TEMPVAR",
                            "values": [value],
                        }
                    )
                else:
                    pending = []
                continue

            if match := RANDOM_CHOICES_RE.search(line):
                values = parse_choice_values(match.group(1))
                if values and set(values).issubset(direction_values):
                    pending.append(
                        {
                            "producer_address": line_address,
                            "source": "C0:9F82 choices",
                            "values": values,
                        }
                    )
                else:
                    pending = []
                continue

            target = CALLROUTINE_RE.search(line)
            target_key = target.group(1) if target else None
            if target_key in DIRECTION_TEMPVAR_CONSUMERS and pending:
                for producer in pending:
                    key = (
                        str(producer["producer_address"]),
                        str(producer["source"]),
                        tuple(int(value) for value in producer["values"]),
                    )
                    event = events.setdefault(
                        key,
                        {
                            "producer_address": producer["producer_address"],
                            "source": producer["source"],
                            "values": [f"${int(value):04X}" for value in producer["values"]],
                            "value_names": [
                                ACTIONSCRIPT_DIRECTION_WORDS[int(value)]["name"]
                                for value in producer["values"]
                            ],
                            "consumers": [],
                            "rows": [],
                        },
                    )
                    consumer_label = f"{target_key} {DIRECTION_TEMPVAR_CONSUMERS[target_key]}"
                    if consumer_label not in event["consumers"]:
                        event["consumers"].append(consumer_label)
                    row_label = f"{entry['address']} {entry.get('name') or ''}".strip()
                    if row_label not in event["rows"]:
                        event["rows"].append(row_label)
                if target_key == "C0:C83B":
                    pending = []
                continue

            opcode_name = next(
                (opcode.name for opcode in OPCODES.values() if f" {opcode.name}" in line),
                "",
            )
            if (
                opcode_name in TEMPVAR_REPLACING_OPCODES
                or opcode_name in TEMPVAR_MUTATING_OPCODES
                or (target_key and target_key != "C0:9F82")
            ):
                pending = []

    value_counts: Counter[str] = Counter()
    consumer_counts: Counter[str] = Counter()
    for event in events.values():
        for value in event["values"]:
            value_counts[value] += 1
        for consumer in event["consumers"]:
            consumer_counts[consumer.split()[0]] += 1

    return {
        "producer_count": len(events),
        "value_counts": dict(value_counts.most_common()),
        "consumer_counts": dict(consumer_counts.most_common()),
        "events": sorted(
            events.values(),
            key=lambda item: address_sort_key(str(item["producer_address"])),
        ),
    }


def collect_field2b32_boundary_signals(
    entries: list[dict[str, Any]],
    rom: bytes,
    names: dict[str, list[str]],
    *,
    max_instructions: int,
    max_bytes: int,
) -> dict[str, Any]:
    events: dict[tuple[str, int], dict[str, Any]] = {}

    for entry in entries:
        address = parse_address(str(entry["address"]))
        size = entry.get("size")
        decode_bytes = min(size, max_bytes) if isinstance(size, int) and size > 0 else max_bytes
        lines = decode_script(
            rom,
            address,
            max_instructions=max_instructions,
            max_bytes=decode_bytes,
            stop_at_terminal=False,
            names=names,
        )
        pending: dict[str, Any] | None = None
        for line in lines:
            address_match = DECODED_ADDRESS_RE.match(line)
            if not address_match:
                continue
            line_address = address_match.group(1)
            target = CALLROUTINE_RE.search(line)
            target_key = target.group(1) if target else None

            if target_key == "C0:A685":
                match = FIELD2B32_WORD_RE.search(line)
                if match:
                    pending = {
                        "producer_address": line_address,
                        "value": int(match.group(1), 16),
                    }
                else:
                    pending = None
                continue

            if target_key == "C0:A68B":
                pending = None
                continue

            if target_key in FIELD2B32_CONSUMERS and pending:
                key = (str(pending["producer_address"]), int(pending["value"]))
                event = events.setdefault(
                    key,
                    {
                        "producer_address": pending["producer_address"],
                        "source": "C0:A685 field2b32_word",
                        "value": f"${int(pending['value']):04X}",
                        "value_name": ACTIONSCRIPT_FIELD2B32_WORDS.get(
                            int(pending["value"]),
                            {"name": f"field2b32_step_{int(pending['value']):04x}"},
                        )["name"],
                        "consumers": [],
                        "rows": [],
                    },
                )
                consumer_label = f"{target_key} {FIELD2B32_CONSUMERS[target_key]}"
                if consumer_label not in event["consumers"]:
                    event["consumers"].append(consumer_label)
                row_label = f"{entry['address']} {entry.get('name') or ''}".strip()
                if row_label not in event["rows"]:
                    event["rows"].append(row_label)

    value_counts: Counter[str] = Counter()
    consumer_counts: Counter[str] = Counter()
    for event in events.values():
        value_counts[event["value"]] += 1
        for consumer in event["consumers"]:
            consumer_counts[consumer.split()[0]] += 1

    return {
        "producer_count": len(events),
        "value_counts": dict(value_counts.most_common()),
        "consumer_counts": dict(consumer_counts.most_common()),
        "events": sorted(
            events.values(),
            key=lambda item: address_sort_key(str(item["producer_address"])),
        ),
    }


def observed_total(counts: dict[str, int]) -> int:
    return sum(int(count) for count in counts.values())


def readiness_item(
    *,
    value_class: str,
    status: str,
    catalog: dict[int, dict[str, str]],
    counts: dict[str, int],
    evidence: str,
    next_action: str,
) -> dict[str, Any]:
    return {
        "value_class": value_class,
        "status": status,
        "observed_values": len(counts),
        "observations": observed_total(counts),
        "catalog_values": len(catalog),
        "coverage": dict(counts),
        "evidence": evidence,
        "next_action": next_action,
    }


def build_value_semantics_readiness(
    operand_values: dict[str, dict[str, int]],
    field2b32_boundary_signals: dict[str, Any],
    direction_boundary_signals: dict[str, Any],
) -> list[dict[str, Any]]:
    direction_counts = dict(direction_boundary_signals.get("value_counts", {}))
    field2b32_counts = dict(operand_values.get("field2b32_words", {}))
    for value, count in field2b32_boundary_signals.get("value_counts", {}).items():
        field2b32_counts[value] = max(int(field2b32_counts.get(value, 0)), int(count))

    return [
        readiness_item(
            value_class="direction_class_words",
            status="runtime_boundary_confirmed",
            catalog=ACTIONSCRIPT_DIRECTION_WORDS,
            counts=direction_counts,
            evidence="C3 tempvar/random-choice producers reach C0:A65F and C0:C83B movement/direction consumers.",
            next_action="Promote additional player-facing movement aliases only when a concrete script family needs them.",
        ),
        readiness_item(
            value_class="field2b32_movement_words",
            status="runtime_boundary_confirmed",
            catalog=ACTIONSCRIPT_FIELD2B32_WORDS,
            counts=field2b32_counts,
            evidence="C0:A685 writes inline words to $2B32 and audited C3 spans reach C0:C83B/C0:CA4E/C0:A6AD/C0:CBD3 consumers.",
            next_action="Keep numeric magnitudes unless runtime traces prove a higher-level speed preset name.",
        ),
        readiness_item(
            value_class="animation_ids",
            status="decode_contract_named",
            catalog=ACTIONSCRIPT_ANIMATION_IDS,
            counts=operand_values.get("animation_ids", {}),
            evidence="EVENT_SET_ANIMATION operands are decoded directly from C3 scripts.",
            next_action="Only rename frame selectors when tied to a specific visual asset contract.",
        ),
        readiness_item(
            value_class="visual_countdown_seed_bytes",
            status="reader_path_named",
            catalog=ACTIONSCRIPT_VISUAL_COUNTDOWN_BYTES,
            counts=operand_values.get("visual_countdown_bytes", {}),
            evidence="C0:AA6E reads countdown/state bytes and the zero/nonzero write paths are source-backed.",
            next_action="Trace representative visual-profile rows before calling these player-visible animation states.",
        ),
        readiness_item(
            value_class="sound_effect_ids",
            status="reference_label_correlated",
            catalog=ACTIONSCRIPT_SOUND_EFFECT_IDS,
            counts=operand_values.get("sound_effect_ids", {}),
            evidence="C0:A841 plays script word ids through C0:ABE0 and names are cross-checked against sound-driver reference labels.",
            next_action="Keep sound-driver reference labels as corroboration; do not infer timing or channel behavior here.",
        ),
        readiness_item(
            value_class="entity_script_ids",
            status="payload_join_named",
            catalog=ACTIONSCRIPT_ENTITY_SCRIPT_IDS,
            counts=operand_values.get("entity_script_ids", {}),
            evidence="C0:A98B consumes entity-script ids together with sprite-pose descriptor words for script-driven spawns.",
            next_action="Join to entity-script table records before promoting broader actor identity names.",
        ),
        readiness_item(
            value_class="visual_state_bytes",
            status="bounded_local_unknown",
            catalog=ACTIONSCRIPT_VISUAL_STATE_BYTES,
            counts=operand_values.get("visual_state_bytes", {}),
            evidence="Values are bounded to $00..$07 and stored to current-slot $2AF6 by C0:AA6E before the visual-profile refresh path.",
            next_action="Needs runtime visual-profile row evidence before assigning exact frame/pose meanings.",
        ),
        readiness_item(
            value_class="surface_flags_bytes",
            status="bounded_local_unknown",
            catalog=ACTIONSCRIPT_SURFACE_FLAGS_BYTES,
            counts=operand_values.get("surface_flags_bytes", {}),
            evidence="C0:A679 writes surface flag bytes to current-slot $2BAA; observed values are named by bit shape only.",
            next_action="Trace collision/terrain consumers before splitting bit 0 and bit 1 semantics.",
        ),
        readiness_item(
            value_class="sprite_pose_descriptor_words",
            status="payload_identity_pending",
            catalog=ACTIONSCRIPT_SPRITE_POSE_DESCRIPTOR_WORDS,
            counts=operand_values.get("sprite_pose_descriptor_words", {}),
            evidence="C0:A98B consumes pose descriptor words for recovery/cast-style spawn payloads.",
            next_action="Join descriptor words to sprite/pose tables before naming concrete character poses.",
        ),
    ]


def normalize_evidence(items: Any) -> list[str]:
    evidence: list[str] = []
    if not isinstance(items, list):
        return evidence
    for item in items:
        if isinstance(item, str):
            value = item
        elif isinstance(item, dict):
            note = str(item.get("note", ""))
            line = item.get("line")
            value = f"{note}:{line}" if note and line else note
        else:
            value = str(item)
        if value and value not in evidence:
            evidence.append(value)
    return evidence


def merge_entry(entries: dict[str, dict[str, Any]], entry: dict[str, Any]) -> None:
    address = str(entry["address"])
    current = entries.get(address)
    if current is None:
        entries[address] = entry
        return

    for source in entry.get("sources", []):
        if source not in current["sources"]:
            current["sources"].append(source)
    for extraction_class in entry.get("extraction_classes", []):
        if extraction_class not in current["extraction_classes"]:
            current["extraction_classes"].append(extraction_class)
    if current.get("primary_class") == "event-script-asset" and entry.get("primary_class") != "event-script-asset":
        current["primary_class"] = entry["primary_class"]
    if not current.get("name") and entry.get("name"):
        current["name"] = entry["name"]
    if not current.get("path") and entry.get("path"):
        current["path"] = entry["path"]
    if current.get("size") is None and entry.get("size") is not None:
        current["size"] = entry["size"]
    for evidence in entry.get("evidence", []):
        if evidence not in current["evidence"]:
            current["evidence"].append(evidence)


def load_script_entries(source_map: dict[str, Any]) -> list[dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}

    for row in source_map.get("include_rows", []):
        address = row.get("address")
        extraction_class = str(row.get("extraction_class", ""))
        if not address or extraction_class not in SCRIPT_CLASSES:
            continue
        merge_entry(
            entries,
            {
                "address": str(address),
                "name": row.get("name"),
                "path": row.get("path"),
                "size": row.get("size"),
                "primary_class": extraction_class,
                "extraction_classes": [extraction_class],
                "sources": ["include-row"],
                "source_kind": row.get("source_kind"),
                "source_decode_status": row.get("script_decode_status"),
                "evidence": normalize_evidence(row.get("evidence", [])),
            },
        )

    for label in source_map.get("supplemental_labels", []):
        address = label.get("address")
        extraction_class = str(label.get("extraction_class", ""))
        if not address or extraction_class not in SCRIPT_CLASSES:
            continue
        merge_entry(
            entries,
            {
                "address": str(address),
                "name": label.get("name"),
                "path": None,
                "size": None,
                "primary_class": extraction_class,
                "extraction_classes": [extraction_class],
                "sources": [f"supplemental-{label.get('source', 'label')}"],
                "source_kind": None,
                "source_decode_status": label.get("script_decode_status"),
                "evidence": normalize_evidence(label.get("evidence", [])),
            },
        )

    return sorted(entries.values(), key=lambda item: address_sort_key(str(item["address"])))


def decoded_instruction_count(lines: list[str]) -> int:
    return sum(1 for line in lines if line and not line.startswith(";"))


def decode_status(lines: list[str]) -> str:
    if not lines:
        return "not-decoded"
    joined = "\n".join(lines)
    if "unknown event opcode" in joined:
        return "partial-unknown-opcode"
    if "args unknown" in joined:
        return "partial-unknown-call-args"
    last = lines[-1]
    if last.startswith("; stopped at byte limit"):
        return "limit-byte"
    if last.startswith("; stopped at instruction limit"):
        return "limit-instruction"
    return "complete"


def stop_reason(lines: list[str]) -> str:
    if not lines:
        return "not-decoded"
    joined = "\n".join(lines)
    if "unknown event opcode" in joined:
        match = UNKNOWN_OPCODE_RE.search(joined)
        return f"unknown opcode at {match.group(1)}" if match else "unknown opcode"
    if "args unknown" in joined:
        for line in lines:
            if "args unknown" in line:
                return f"unknown call args in {line.split()[0]}"
        return "unknown call args"
    last = lines[-1]
    if last.startswith("; stopped at byte limit"):
        return "byte limit"
    if last.startswith("; stopped at instruction limit"):
        return "instruction limit"
    return "terminal/control-flow stop"


def extract_targets(lines: list[str]) -> tuple[list[str], list[str], list[str]]:
    callbacks: list[str] = []
    installed_callbacks: list[str] = []
    c3_targets: list[str] = []
    for line in lines:
        if "EVENT_CALLROUTINE" in line:
            match = CALLROUTINE_RE.search(line)
            if match and match.group(1) not in callbacks:
                callbacks.append(match.group(1))
        if "CALLBACK" in line and "EVENT_CALLROUTINE" not in line:
            match = INSTALLED_CALLBACK_RE.search(line)
            if match and match.group(1) not in installed_callbacks:
                installed_callbacks.append(match.group(1))
        for target in TARGET_RE.findall(line):
            if target.startswith("C3:") and target not in c3_targets:
                c3_targets.append(target)
    return callbacks, installed_callbacks, c3_targets


def unknown_callback_target(lines: list[str]) -> str | None:
    for line in lines:
        match = UNKNOWN_CALL_TARGET_RE.search(line)
        if match:
            return match.group(1)
    return None


def inferred_callback_group(target: str, preferred_name: str | None) -> str:
    semantics = CALL_TARGET_SEMANTICS.get(target)
    if semantics:
        return semantics["group"]
    name = preferred_name or ""
    if target.startswith("EF:"):
        return "ef-helper"
    if "Text" in name or "Window" in name or "Presentation" in name:
        return "text-presentation"
    if "Visual" in name or "Animation" in name or "Frame" in name:
        return "visual-profile"
    if "Collision" in name or "Footprint" in name:
        return "collision"
    if "Direction" in name or "Vector" in name or "Movement" in name:
        return "movement"
    if "CurrentSlot" in name or "Slot" in name:
        return "current-slot-state"
    if target.startswith("C2:"):
        return "battle-runtime"
    if target.startswith("C4:"):
        return "presentation-render"
    if target.startswith("C0:"):
        return "overworld-runtime"
    return "other"


def inferred_callback_contract(target: str, arg_bytes: int | None) -> str:
    semantics = CALL_TARGET_SEMANTICS.get(target)
    if semantics:
        return semantics["contract"]
    if arg_bytes is None:
        return "argument byte count is not known"
    if arg_bytes == 0:
        return "no inline argument bytes"
    return f"{arg_bytes} inline argument byte(s); semantic fields not named yet"


def inferred_argument_schema(target: str, arg_bytes: int | None) -> str:
    semantics = CALL_TARGET_SEMANTICS.get(target)
    if semantics and semantics.get("args"):
        return semantics["args"]
    if arg_bytes is None:
        return "unknown"
    if arg_bytes == 0:
        return "-"
    return ", ".join(f"arg{i}_byte" for i in range(arg_bytes))


def audit_entry(
    entry: dict[str, Any],
    rom: bytes,
    names: dict[str, list[str]],
    *,
    max_instructions: int,
    max_bytes: int,
) -> dict[str, Any]:
    address = parse_address(str(entry["address"]))
    size = entry.get("size")
    decode_bytes = max_bytes
    if isinstance(size, int) and size > 0:
        decode_bytes = min(size, max_bytes)

    lines = decode_script(
        rom,
        address,
        max_instructions=max_instructions,
        max_bytes=decode_bytes,
        stop_at_terminal=True,
        names=names,
    )
    callbacks, installed_callbacks, c3_targets = extract_targets(lines)
    unknown_callback = unknown_callback_target(lines)
    return {
        **entry,
        "name": entry.get("name") or (names.get(address.key, [None])[0]),
        "raw_preview": raw_preview(rom, address),
        "first_opcode": first_opcode(rom, address),
        "decode_status": decode_status(lines),
        "stop_reason": stop_reason(lines),
        "unknown_callback_target": unknown_callback,
        "decode_bounds": {
            "max_instructions": max_instructions,
            "max_bytes": decode_bytes,
        },
        "decoded_instruction_count": decoded_instruction_count(lines),
        "callback_targets": callbacks,
        "installed_callback_targets": installed_callbacks,
        "c3_targets": c3_targets,
        "decoded": lines,
    }


def build_audit(
    source_map_path: Path,
    index_path: Path,
    rom_path: str | None,
    *,
    max_instructions: int,
    max_bytes: int,
) -> dict[str, Any]:
    source_map = load_json(source_map_path)
    rom = load_rom(find_rom(rom_path))
    names = load_names(index_path)
    entries = load_script_entries(source_map)
    rows = [
        audit_entry(
            entry,
            rom,
            names,
            max_instructions=max_instructions,
            max_bytes=max_bytes,
        )
        for entry in entries
    ]

    by_class = Counter(str(row["primary_class"]) for row in rows)
    by_status = Counter(str(row["decode_status"]) for row in rows)
    first_opcodes = Counter(
        f"{row['first_opcode']['byte']} {row['first_opcode']['name']}" for row in rows
    )
    callbacks = Counter(target for row in rows for target in row["callback_targets"])
    installed_callbacks = Counter(
        target for row in rows for target in row["installed_callback_targets"]
    )
    unknown_callbacks = Counter(
        str(row["unknown_callback_target"])
        for row in rows
        if row.get("unknown_callback_target")
    )
    c3_targets = Counter(target for row in rows for target in row["c3_targets"])
    callback_contracts = []
    for target, count in callbacks.most_common():
        preferred_name = names.get(target, [None])[0]
        arg_bytes = CALL_ARG_COUNTS.get(target)
        callback_contracts.append(
            {
                "target": target,
                "preferred_name": preferred_name,
                "calls": count,
                "arg_bytes": arg_bytes,
                "semantic_group": inferred_callback_group(target, preferred_name),
                "argument_contract": inferred_callback_contract(target, arg_bytes),
                "argument_schema": inferred_argument_schema(target, arg_bytes),
                "status": "byte-count-known" if target in CALL_ARG_COUNTS else "missing-byte-count",
            }
        )
    callback_groups = Counter(str(contract["semantic_group"]) for contract in callback_contracts)
    installed_callback_contracts = []
    for target, count in installed_callbacks.most_common():
        preferred_name = names.get(target, [None])[0]
        installed_callback_contracts.append(
            {
                "target": target,
                "preferred_name": preferred_name,
                "calls": count,
                "semantic_group": inferred_callback_group(target, preferred_name),
                "contract": inferred_callback_contract(target, CALL_ARG_COUNTS.get(target)),
            }
        )
    installed_callback_groups = Counter(
        str(contract["semantic_group"]) for contract in installed_callback_contracts
    )
    operand_value_signals = collect_operand_value_signals(rows)
    field2b32_boundary_signals = collect_field2b32_boundary_signals(
        entries,
        rom,
        names,
        max_instructions=max_instructions,
        max_bytes=max_bytes,
    )
    direction_boundary_signals = collect_direction_boundary_signals(
        entries,
        rom,
        names,
        max_instructions=max_instructions,
        max_bytes=max_bytes,
    )
    value_semantics_readiness = build_value_semantics_readiness(
        operand_value_signals,
        field2b32_boundary_signals,
        direction_boundary_signals,
    )
    value_semantics_statuses = Counter(
        str(item["status"]) for item in value_semantics_readiness
    )

    return {
        "schema": SCHEMA,
        "generated_by": "tools/build_c3_actionscript_semantics_audit.py",
        "inputs": {
            "source_map": rel(source_map_path),
            "ref_index": rel(index_path),
        },
        "decode_bounds": {
            "max_instructions": max_instructions,
            "max_bytes": max_bytes,
        },
        "summary": {
            "rows": len(rows),
            "by_extraction_class": dict(sorted(by_class.items())),
            "by_decode_status": dict(sorted(by_status.items())),
            "top_first_opcodes": dict(first_opcodes.most_common(12)),
            "top_callback_targets": dict(callbacks.most_common(16)),
            "top_installed_callback_targets": dict(installed_callbacks.most_common(16)),
            "unknown_callback_targets": dict(unknown_callbacks.most_common()),
            "top_c3_targets": dict(c3_targets.most_common(16)),
            "callback_contracts": len(callback_contracts),
            "callback_groups": dict(callback_groups.most_common()),
            "installed_callback_contracts": len(installed_callback_contracts),
            "installed_callback_groups": dict(installed_callback_groups.most_common()),
            "value_semantics_statuses": dict(value_semantics_statuses.most_common()),
        },
        "opcode_catalog": build_opcode_catalog(),
        "operand_value_catalog": operand_value_signals,
        "value_semantics_readiness": value_semantics_readiness,
        "field2b32_boundary_signals": field2b32_boundary_signals,
        "direction_boundary_signals": direction_boundary_signals,
        "callback_contracts": callback_contracts,
        "installed_callback_contracts": installed_callback_contracts,
        "rows": rows,
    }


def markdown_escape(text: Any) -> str:
    return str(text if text is not None else "").replace("|", "\\|")


def format_list(values: list[str], limit: int = 4) -> str:
    if not values:
        return "-"
    visible = values[:limit]
    suffix = f", +{len(values) - limit}" if len(values) > limit else ""
    return ", ".join(f"`{value}`" for value in visible) + suffix


def render_operand_rows(
    catalog: dict[int, dict[str, str]],
    counts: dict[str, int],
    *,
    width: int,
) -> list[str]:
    lines: list[str] = []
    observed_values = {
        int(value.strip("$"), 16)
        for value in counts
        if re.fullmatch(r"\$[0-9A-F]{2,4}", value)
    }
    for value in sorted(set(catalog) | observed_values):
        key = f"${value:0{width}X}"
        item = catalog.get(value)
        lines.append(
            "| `{value}` | `{name}` | {count} | {contract} |".format(
                value=key,
                name=markdown_escape(item["name"] if item else f"unknown_{key[1:].lower()}"),
                count=counts.get(key, 0),
                contract=markdown_escape(
                    item["contract"] if item else "observed in current decode inventory; name not assigned yet"
                ),
            )
        )
    return lines


def render_markdown(audit: dict[str, Any]) -> str:
    summary = audit["summary"]
    rows = audit["rows"]
    frontier_rows = [row for row in rows if row["decode_status"] != "complete"]
    operand_values = audit["operand_value_catalog"]

    lines = [
        "# C3 actionscript semantics audit",
        "",
        "Generated from `notes/c3-source-data-map.md` via `tools/build_c3_actionscript_semantics_audit.py`. This report is the first semantic frontier for C3 event/actionscript payloads after byte-equivalent source-bank closure.",
        "",
        "## Summary",
        "",
        f"- schema: `{audit['schema']}`",
        f"- script rows audited: `{summary['rows']}`",
        f"- by extraction class: `{summary['by_extraction_class']}`",
        f"- by decode status: `{summary['by_decode_status']}`",
        f"- native callback contract seeds: `{summary['callback_contracts']}`",
        f"- installed callback target seeds: `{summary['installed_callback_contracts']}`",
        f"- decode bounds: `{audit['decode_bounds']['max_instructions']}` instructions, `{audit['decode_bounds']['max_bytes']:#x}` bytes per row unless the source-map row is shorter",
        "",
        "## Top opcode and target signals",
        "",
        f"- top first opcodes: `{summary['top_first_opcodes']}`",
        f"- top native callback targets: `{summary['top_callback_targets']}`",
        f"- top installed callback targets: `{summary['top_installed_callback_targets']}`",
        f"- callback semantic groups: `{summary['callback_groups']}`",
        f"- installed callback semantic groups: `{summary['installed_callback_groups']}`",
        f"- unknown callback targets: `{summary['unknown_callback_targets']}`",
        f"- value semantics statuses: `{summary['value_semantics_statuses']}`",
        f"- top C3 script targets: `{summary['top_c3_targets']}`",
        "",
        "## Value semantics readiness",
        "",
        "C3 VM shape is closed at the current decode bounds, so this table separates operand classes that are runtime-boundary confirmed from classes that remain deliberately local-unknown.",
        "",
        "| Value class | Status | Observed values | Observations | Evidence | Next action |",
        "| --- | --- | ---: | ---: | --- | --- |",
    ]
    for item in audit["value_semantics_readiness"]:
        lines.append(
            "| `{value_class}` | `{status}` | {observed_values} | {observations} | {evidence} | {next_action} |".format(
                value_class=item["value_class"],
                status=item["status"],
                observed_values=item["observed_values"],
                observations=item["observations"],
                evidence=markdown_escape(item["evidence"]),
                next_action=markdown_escape(item["next_action"]),
            )
        )

    lines.extend(
        [
            "",
        "## Frontier rows",
        "",
        ]
    )

    if frontier_rows:
        lines.extend(
            [
                "| Address | Name | Class | Decode | Stop reason | Unknown callback | First opcode |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in frontier_rows:
            first = row["first_opcode"]
            lines.append(
                "| `{address}` | `{name}` | `{kind}` | `{decode}` | {reason} | {unknown} | `{opcode}` |".format(
                    address=row["address"],
                    name=markdown_escape(row.get("name") or ""),
                    kind=row["primary_class"],
                    decode=row["decode_status"],
                    reason=markdown_escape(row["stop_reason"]),
                    unknown=f"`{row['unknown_callback_target']}`" if row.get("unknown_callback_target") else "-",
                    opcode=f"{first['byte']} {first['name']}",
                )
            )
    else:
        lines.append("No syntactic decode frontiers at the current bounds.")

    lines.extend(
        [
            "",
            "## Opcode operand catalog",
            "",
            "| Opcode | Name | Byte shape | Semantic fields | Role | Confidence |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for opcode in audit["opcode_catalog"]:
        shape = ", ".join(f"`{value}`" for value in opcode["byte_shape"]) or "-"
        fields = ", ".join(f"`{value}`" for value in opcode["semantic_fields"]) or "-"
        lines.append(
            "| `{opcode}` | `{name}` | {shape} | {fields} | `{role}` | `{confidence}` |".format(
                opcode=opcode["opcode"],
                name=opcode["name"],
                shape=shape,
                fields=fields,
                role=opcode["control_flow_role"],
                confidence=opcode["confidence"],
            )
        )

    lines.extend(
        [
            "",
            "## Operand value seed catalog",
            "",
            "These names are source-pilot readability seeds from recurring decoded C3 actionscript values. Direction-word names are promoted only at callback boundaries where the tempvar or random-choice result reaches the direction/vector runtime helpers.",
            "",
            "### Animation IDs",
            "",
            "| Value | Name | Decode count | Contract |",
            "| --- | --- | ---: | --- |",
        ]
    )
    lines.extend(
        render_operand_rows(
            ACTIONSCRIPT_ANIMATION_IDS,
            operand_values["animation_ids"],
            width=2,
        )
    )
    lines.extend(
        [
            "",
            "### Visual countdown state bytes",
            "",
            "| Value | Name | Decode count | Contract |",
            "| --- | --- | ---: | --- |",
        ]
    )
    lines.extend(
        render_operand_rows(
            ACTIONSCRIPT_VISUAL_STATE_BYTES,
            operand_values["visual_state_bytes"],
            width=2,
        )
    )
    lines.extend(
        [
            "",
            "### Visual countdown seed bytes",
            "",
            "| Value | Name | Decode count | Contract |",
            "| --- | --- | ---: | --- |",
        ]
    )
    lines.extend(
        render_operand_rows(
            ACTIONSCRIPT_VISUAL_COUNTDOWN_BYTES,
            operand_values["visual_countdown_bytes"],
            width=2,
        )
    )
    lines.extend(
        [
            "",
            "### Field $2B32 movement words",
            "",
            "| Value | Name | Observed count | Contract |",
            "| --- | --- | ---: | --- |",
        ]
    )
    field2b32_signals = audit.get("field2b32_boundary_signals", {})
    field2b32_counts = dict(operand_values["field2b32_words"])
    for value, count in field2b32_signals.get("value_counts", {}).items():
        field2b32_counts[value] = max(int(field2b32_counts.get(value, 0)), int(count))
    lines.extend(
        render_operand_rows(
            ACTIONSCRIPT_FIELD2B32_WORDS,
            field2b32_counts,
            width=4,
        )
    )

    lines.extend(
        [
            "",
            "### Field $2B32 movement boundary evidence",
            "",
            "`C0:A685` writes the inline `field2b32_word` into current-slot `$2B32`. The C0 movement-vector note shows `C0:C83B` deriving signed vector words from `$2B32`; timer wrappers such as `C0:A6A2`/`C0:A6AD` and direct `C0:CA4E`/`C0:CBD3` calls then consume the active vector or speed scale. The table records decoded C3 `$2B32` writes that reach one of those movement/timer consumers inside the same source-map span.",
            "",
            f"- boundary-confirmed producers: `{field2b32_signals.get('producer_count', 0)}`",
            f"- value coverage: `{field2b32_signals.get('value_counts', {})}`",
            f"- consumer coverage: `{field2b32_signals.get('consumer_counts', {})}`",
            "",
            "| Producer | Value | Consumers | Rows |",
            "| --- | --- | --- | --- |",
        ]
    )
    field2b32_events = list(field2b32_signals.get("events", []))
    priority_events = [
        event
        for event in field2b32_events
        if any(
            str(consumer).startswith(("C0:C83B ", "C0:A6AD ", "C0:CBD3 "))
            for consumer in event.get("consumers", [])
        )
    ]
    sample_events = [
        event
        for event in field2b32_events
        if event not in priority_events
    ][:20]
    visible_events = priority_events[:24] + sample_events
    for event in visible_events:
        value = f"{event.get('value')} <{event.get('value_name')}>"
        lines.append(
            "| `{producer}` | `{value}` | {consumers} | {rows} |".format(
                producer=event["producer_address"],
                value=markdown_escape(value),
                consumers=format_list(event.get("consumers", []), limit=3),
                rows=format_list(event.get("rows", []), limit=2),
            )
        )
    if len(field2b32_events) > len(visible_events):
        lines.append(
            f"| `...` | - | - | `{len(field2b32_events) - len(visible_events)}` additional boundary-confirmed producer(s) in JSON output |"
        )
    lines.extend(
        [
            "",
            "### Direction-class word candidates",
            "",
            "| Value | Name | Tempvar decode count | Contract |",
            "| --- | --- | ---: | --- |",
        ]
    )
    lines.extend(
        render_operand_rows(
            ACTIONSCRIPT_DIRECTION_WORDS,
            operand_values["tempvar_direction_word_candidates"],
            width=4,
        )
    )

    direction_signals = audit.get("direction_boundary_signals", {})
    lines.extend(
        [
            "",
            "### Direction callback boundary evidence",
            "",
            "C3 direction-class words are backed by the runtime chain documented around `C0:A65F` and `C0:C83B`: `C0:A65F` stores the active direction/class in `$2AF6[current]` and returns it, while `C0:C83B` stores the direction/mode in `$1A86[current]` and derives signed movement vector words from it. The table below records decoded C3 producers that reach those consumers inside the same source-map span.",
            "",
            f"- boundary-confirmed producers: `{direction_signals.get('producer_count', 0)}`",
            f"- value coverage: `{direction_signals.get('value_counts', {})}`",
            f"- consumer coverage: `{direction_signals.get('consumer_counts', {})}`",
            "",
            "| Producer | Source | Values | Consumers | Rows |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    events = list(direction_signals.get("events", []))
    vector_events = [
        event
        for event in events
        if any(str(consumer).startswith("C0:C83B ") for consumer in event.get("consumers", []))
    ]
    sample_events = [
        event
        for event in events
        if event not in vector_events
    ][:24]
    visible_events = vector_events + sample_events
    for event in visible_events:
        values = [
            f"{value} <{name}>"
            for value, name in zip(event.get("values", []), event.get("value_names", []))
        ]
        lines.append(
            "| `{producer}` | `{source}` | {values} | {consumers} | {rows} |".format(
                producer=event["producer_address"],
                source=markdown_escape(event["source"]),
                values=", ".join(f"`{markdown_escape(value)}`" for value in values) or "-",
                consumers=format_list(event.get("consumers", []), limit=3),
                rows=format_list(event.get("rows", []), limit=2),
            )
        )
    if len(events) > len(visible_events):
        lines.append(
            f"| `...` | `summary` | - | - | `{len(events) - len(visible_events)}` additional boundary-confirmed producer(s) in JSON output |"
        )

    lines.extend(
        [
            "",
            "## Native callback contract seed",
            "",
            "| Target | Preferred name | Group | Calls | Arg bytes | Args | Contract | Status |",
            "| --- | --- | --- | ---: | ---: | --- | --- | --- |",
        ]
    )
    for contract in audit["callback_contracts"]:
        arg_bytes = contract["arg_bytes"]
        lines.append(
            "| `{target}` | `{name}` | `{group}` | {calls} | {arg_bytes} | `{argument_schema}` | {argument_contract} | `{status}` |".format(
                target=contract["target"],
                name=markdown_escape(contract.get("preferred_name") or ""),
                group=contract["semantic_group"],
                calls=contract["calls"],
                arg_bytes="-" if arg_bytes is None else arg_bytes,
                argument_schema=markdown_escape(contract["argument_schema"]),
                argument_contract=markdown_escape(contract["argument_contract"]),
                status=contract["status"],
            )
        )

    lines.extend(
        [
            "",
            "## Installed callback target signal",
            "",
            "| Target | Preferred name | Group | Installs | Contract |",
            "| --- | --- | --- | ---: | --- |",
        ]
    )
    for contract in audit["installed_callback_contracts"]:
        lines.append(
            "| `{target}` | `{name}` | `{group}` | {calls} | {contract} |".format(
                target=contract["target"],
                name=markdown_escape(contract.get("preferred_name") or ""),
                group=contract["semantic_group"],
                calls=contract["calls"],
                contract=markdown_escape(contract["contract"]),
            )
        )

    lines.extend(
        [
            "",
            "## Full script inventory",
            "",
            "| Address | Name | Class | Decode | Instr. | First opcode | Callroutines | Installed callbacks | C3 targets |",
            "| --- | --- | --- | --- | ---: | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        first = row["first_opcode"]
        lines.append(
            "| `{address}` | `{name}` | `{kind}` | `{decode}` | {count} | `{opcode}` | {callbacks} | {installed} | {targets} |".format(
                address=row["address"],
                name=markdown_escape(row.get("name") or ""),
                kind=row["primary_class"],
                decode=row["decode_status"],
                count=row["decoded_instruction_count"],
                opcode=f"{first['byte']} {first['name']}",
                callbacks=format_list(row["callback_targets"]),
                installed=format_list(row["installed_callback_targets"]),
                targets=format_list(row["c3_targets"]),
            )
        )

    lines.extend(["", "## Decode excerpts", ""])
    for row in rows:
        if row["decode_status"] == "complete" and row["primary_class"] == "event-script-asset":
            continue
        lines.extend(
            [
                f"### {row['address']} {row.get('name') or ''}".rstrip(),
                "",
                f"- class: `{row['primary_class']}`",
                f"- decode status: `{row['decode_status']}`",
                f"- stop reason: {row['stop_reason']}",
                f"- raw preview: `{row['raw_preview']}`",
                "",
                "```text",
                *row["decoded"][:16],
            ]
        )
        if len(row["decoded"]) > 16:
            lines.append(f"; ... {len(row['decoded']) - 16} more decoded lines in JSON output")
        lines.extend(["```", ""])

    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a C3 event/actionscript semantic frontier audit.")
    parser.add_argument("--source-map", type=Path, default=DEFAULT_SOURCE_MAP)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--rom", help="path to EarthBound (USA).sfc")
    parser.add_argument("--max-instructions", type=int, default=120)
    parser.add_argument("--max-bytes", type=lambda text: int(text, 0), default=0x400)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN_OUT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    audit = build_audit(
        resolve_path(args.source_map),
        resolve_path(args.index),
        args.rom,
        max_instructions=args.max_instructions,
        max_bytes=args.max_bytes,
    )

    json_out = resolve_path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")

    markdown_out = resolve_path(args.markdown_out)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(render_markdown(audit), encoding="utf-8")

    summary = audit["summary"]
    print(
        f"Wrote {json_out} and {markdown_out} "
        f"({summary['rows']} rows, {summary['by_decode_status']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
