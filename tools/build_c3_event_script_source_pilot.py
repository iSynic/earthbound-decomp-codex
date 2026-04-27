from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from decode_event_script import CALL_ARG_COUNTS, OPCODES, Address, Opcode, load_names, read_u16
from rom_tools import find_rom, hirom_to_file_offset, load_rom


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_MAP = ROOT / "build" / "c3-source-data-map.json"
DEFAULT_REF_INDEX = ROOT / "build" / "ref-index.json"
DEFAULT_OUTPUT = ROOT / "src" / "c3" / "event_scripts" / "movement_pulse_presets.asar.asm"
DEFAULT_REPORT = ROOT / "notes" / "c3-event-script-source-pilot.md"
DEFAULT_MANIFEST = ROOT / "build" / "c3-event-script-source-pilot.json"

FAMILY_ID = "movement-pulse-presets"

SCRIPT_ROWS = [
    "C3:A09F",
    "C3:A0B2",
    "C3:A0C5",
    "C3:A0D8",
    "C3:A12E",
    "C3:A15E",
    "C3:A17B",
    "C3:A18F",
    "C3:A1A3",
    "C3:A1B7",
    "C3:A1CB",
    "C3:A1DF",
    "C3:A1F3",
]

PRESET_ROWS = [
    "C3:AA38",
    "C3:AA46",
    "C3:AA5A",
    "C3:AA6E",
    "C3:AA82",
    "C3:AA96",
    "C3:AAAA",
    "C3:AAB8",
    "C3:AAC2",
    "C3:AAD6",
    "C3:AAEA",
    "C3:AAFE",
    "C3:AB12",
    "C3:AB26",
]

LABEL_OVERRIDES = {
    "C3:43DB": "LoopTimedDeliveryDeparturePulseUntilOffscreen",
    "C3:43E8": "TimedDeliveryDeparturePulseAnimation0Half",
    "C3:4402": "Event500_TimedDeliveryExistingRowGate",
    "C3:441A": "Event499_TimedDeliverySetup",
    "C3:4432": "TimedDeliveryCommonCountdownLoop",
    "C3:443E": "TimedDeliveryRetryWaitLoop",
    "C3:444D": "TimedDeliveryReadinessGate",
    "C3:4457": "TimedDeliverySuccessGateAndPresentationSetup",
    "C3:447A": "StartTimedDeliveryArrivalMovementTask",
    "C3:447D": "TimedDeliveryFailureTeardown",
    "C3:4488": "PrepareTimedDeliveryActorForPresentation",
    "C3:4499": "WaitTimedDeliveryActorPresentationPrep",
    "C3:44A7": "ReturnFromTimedDeliveryActorPrep",
    "C3:44A8": "RunTimedDeliveryDepartureMovement",
    "C3:44C1": "LoopTimedDeliveryDepartureMovement",
    "C3:44D2": "FinishTimedDeliveryDepartureAndYieldText",
    "C3:44DE": "RunTimedDeliveryArrivalMovement",
    "C3:44EE": "LoopTimedDeliveryArrivalMovement",
    "C3:44FF": "HoldTimedDeliveryArrivalCompletion",
    "C3:4508": "Event547_CameraOffsetPulseAndYield",
    "C3:4555": "Event547_VerticalCameraOffsetPulseTask",
    "C3:456F": "Event550_ReleaseCurrentVisualEntity",
    "C3:4572": "Event548_FourDirectionIdlePresentation",
    "C3:459E": "Event549_DownwardMovementToYield",
    "C3:45CA": "Event551_ServiceMovementPath",
    "C3:4635": "Event552_ServiceMovementPath",
    "C3:4693": "Event553_ServiceMovementPath",
    "C3:46F1": "Event554_ServiceMovementPathAndFade",
    "C3:474E": "Event555_BrightnessFadeOut",
    "C3:4767": "Event559_ServiceMovementPath",
    "C3:47C1": "Event558_ServiceMovementPath",
    "C3:4810": "Event557_ServiceMovementPath",
    "C3:486A": "Event556_ServiceMovementPath",
    "C3:48C4": "PlayDownRightLeftDownFacingGesture",
    "C3:48FC": "Event563_FacingCountdownSequence",
    "C3:4964": "LoopReadScriptWords0201Task",
    "C3:4975": "Event562_ServiceAnimationWithReadTask",
    "C3:4A61": "LoopReadScriptWord01Task",
    "C3:4A55": "WaitUntilCurrentSlotInsideLiveAreaWindow",
    "C3:4A6C": "Event561_ServiceAnimationWithReadTask",
    "C3:4AF6": "Event560_ServiceFacingSequence",
    "C3:4B62": "PlayDirectionCountdownCompassCycle",
    "C3:4BAB": "Event564_StaticFacingPresentationRelease",
    "C3:4BCD": "Event565_RightThenUpFacingHalt",
    "C3:4BF7": "Event566_MoveThenFaceUpHalt",
    "C3:4C3A": "Event567_MoveToFixedAnchorPartyLookAt",
    "C3:4C86": "Event568_MoveFromPartyMemberLeftToAnchor",
    "C3:4CE0": "Event569_MoveFromPartyMemberRightToAnchor",
    "C3:4D39": "RunFallingBouncePresentation",
    "C3:4D5C": "Event570_FallingBouncePositionA",
    "C3:4D65": "Event571_FallingBouncePositionB",
    "C3:4D6E": "Event572_FallingBouncePositionC",
    "C3:4D77": "Event573_HoldFacingPositionA",
    "C3:4D7D": "HoldDownFacingTwoSecondsAndRelease",
    "C3:4D92": "Event574_HoldFacingPositionB",
    "C3:4D9B": "Event575_HoldFacingPositionC",
    "C3:4DA4": "Event576_ReleaseCurrentVisualEntity",
    "C3:4DA7": "Event577_TrafficLightWaitPositionA",
    "C3:4DB0": "Event578_TrafficLightWaitPositionB",
    "C3:4DB9": "Event579_TrafficLightWaitPositionC",
    "C3:4DC2": "Event580_TrafficLightWaitPositionD",
    "C3:4DCB": "Event581_DoseiBoxAppearFlagGate",
    "C3:4DE0": "Event582_DownFacingWindowEffect",
    "C3:4DEA": "Event583_UpFacingWindowEffect",
    "C3:4DF1": "RunWh0ColorWindowRiseAndFallEffect",
    "C3:4E66": "LoopMovementVectorFromDirectionTask",
    "C3:6E2D": "Event606_DoseiBoxAppearFallback",
    "C3:A2B8": "Event8_Entry2WaitUntilOffscreenRelease",
    "C3:A09F": "LoopActiveEntityWalkAnimationPulse",
    "C3:A0B2": "LoopActiveEntityWalkPulse24Frame",
    "C3:A0C5": "LoopActiveEntityWalkPulse12Frame",
    "C3:A0D8": "LoopActiveEntityWalkPulse9FrameConditional",
    "C3:A0EB": "LoopActiveEntityWalkPulse6FrameConditional",
    "C3:A0FE": "LoopActiveEntityWalkPulse2FrameConditional",
    "C3:A111": "LoopActiveEntityWalkPulseVar4Gate",
    "C3:A11E": "LoopActiveEntityWalkPulseVar4Gate_OffHalf",
    "C3:A12E": "LoopActiveEntityWalkPulseVar4Countdown",
    "C3:A159": "LoopActiveEntityWalkPulseVar4Countdown_WaitAndRestart",
    "C3:A15E": "LoopC40015Var4GatedPulseUntilRelease",
    "C3:A162": "LoopC40015Var4GatedPulseUntilRelease_Loop",
    "C3:A16F": "LoopC40015Var4GatedPulseUntilRelease_CheckRelease",
    "C3:A17B": "LoopC40015SlowPulseUntilRelease",
    "C3:A18F": "LoopC40015FastPulseUntilRelease",
    "C3:A1A3": "LoopC40015Pulse12FrameUntilRelease",
    "C3:A1B7": "LoopC40015Pulse9FrameUntilRelease",
    "C3:A1CB": "LoopC40015Pulse6FrameUntilRelease",
    "C3:A1DF": "LoopActiveEntityWalkPulse2FrameC40015Branch",
    "C3:A1F3": "LoopC40015Pulse16FrameUntilRelease",
    "C3:A204": "ReleaseCurrentVisualEntityAndEnd",
    "C3:AA38": "InitActionScriptMovementState",
    "C3:AA46": "InitMovementPreset40_00Pulse24Frame",
    "C3:AA5A": "InitMovementPreset00_01Pulse12Frame",
    "C3:AA6E": "InitMovementPreset60_01Pulse9Frame",
    "C3:AA82": "InitMovementPreset00_02Pulse6Frame",
    "C3:AA96": "InitMovementPreset00_06Pulse2Frame",
    "C3:AAAA": "InitMovementPresetVar4Countdown",
    "C3:AAB8": "InitMovementPresetC40015Pulse16Frame",
    "C3:AAC2": "InitMovementPreset40_00C40015FastPulse",
    "C3:AAD6": "InitMovementPreset00_01C40015Pulse12Frame",
    "C3:AAEA": "InitMovementPreset60_01C40015Pulse9Frame",
    "C3:AAFE": "InitMovementPreset00_02C40015Pulse6Frame",
    "C3:AB12": "InitMovementPreset00_06C40015Branch",
    "C3:AB26": "InitAlternatePhysicsVar4WalkPulse",
    "C0:A82F": "DisableCurrentEntityCollision2",
    "C0:9FF0": "PhysicsCallback_C09FF0",
    "C0:AA3F": "Script_SetVisualSetupBytesByMode",
    "C0:C83B": "InstallScriptMovementVectorFromDirection",
    "C4:240A": "SetFullscreenColorWindowRangePreset",
    "C4:248A": "StopWh0HdmaChannel4AndClearWhsel",
    "C4:7499": "ApplyCurrentSlot0e5eBrightnessToPaletteRows",
    "C4:7A27": "StageBaseSlotRelativeWh0BoxMask",
    "C4:7A6B": "MirrorCurrentEntityYAroundTarget1002",
    "C4:8B3B": "MakePartyLookAtActiveEntity",
    "C4:8C3E": "CentreScreenOnEntityCallbackOffset",
    "EF:0C87": "ReadActivePartySlotCacheWord",
    "EF:0C97": "ClearActivePartySlotCacheWord",
    "EF:0CA7": "CheckCurrentDeliveryRetryThreshold",
    "EF:0D23": "GetCurrentDeliveryRetryWait",
    "EF:0D46": "SeedCurrentDeliveryCountdown",
    "EF:0D73": "DecrementCurrentDeliveryCountdown",
    "EF:0D8D": "QueueCurrentDeliveryPointer1",
    "EF:0DFA": "QueueCurrentDeliveryPointer2",
    "EF:0E67": "GetCurrentDeliveryEnterSpeed",
    "EF:0E8A": "GetCurrentDeliveryExitSpeed",
    "EF:0F60": "CheckDeliveryServiceReadyForArrival",
    "EF:0FDB": "BeginDeliverySuccessArrivalState",
    "EF:0FF6": "ResetDeliveryArrivalState",
}

VAR_NAMES = {
    0x00: "!ACTIONSCRIPT_VARS_V0",
    0x01: "!ACTIONSCRIPT_VARS_V1",
    0x02: "!ACTIONSCRIPT_VARS_V2",
    0x03: "!ACTIONSCRIPT_VARS_V3",
    0x04: "!ACTIONSCRIPT_VARS_V4",
    0x05: "!ACTIONSCRIPT_VARS_V5",
    0x06: "!ACTIONSCRIPT_VARS_V6",
    0x07: "!ACTIONSCRIPT_VARS_V7",
}

FAMILY_DEFAULTS = {
    "movement-pulse-presets": {
        "output": DEFAULT_OUTPUT,
        "report": DEFAULT_REPORT,
        "manifest": DEFAULT_MANIFEST,
        "rows": SCRIPT_ROWS + PRESET_ROWS,
        "spans": [],
        "description": "Movement pulse preset family emitted as labeled event/actionscript macro assembly.",
        "next": "Promote another C3 family through this same generator pattern, then teach the bank scaffold to include source-form families in place of their opaque `script_event_payloads_0000_e450.asm` `db` corridors once enough families have stable labels and macro coverage.",
    },
    "timed-delivery-controller": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "timed_delivery_controller.asar.asm",
        "report": ROOT / "notes" / "c3-timed-delivery-source-pilot.md",
        "manifest": ROOT / "build" / "c3-timed-delivery-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:43DB", "C3:4508", "TimedDeliveryControllerAndPulseTask"),
        ],
        "description": "Timed-delivery controller proper emitted as labeled event/actionscript macro assembly. This covers the departure pulse task, event 499/500 setup, shared countdown/retry/readiness gates, success/failure branches, and arrival/departure movement loops.",
        "next": "The adjacent service-event movement scripts are now emitted by `--family service-event-movement`; inspect `C3:48C4..C3:4964` next and decide whether it belongs with that follow-up family or starts a neighboring service animation family.",
    },
    "service-event-movement": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "service_event_movement.asar.asm",
        "report": ROOT / "notes" / "c3-service-event-movement-source-pilot.md",
        "manifest": ROOT / "build" / "c3-service-event-movement-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:4508", "C3:48C4", "ServiceEventMovementScripts"),
        ],
        "description": "Adjacent service-event movement scripts emitted as labeled event/actionscript macro assembly. This covers the event 547 camera-offset pulse, event 548/549 presentation paths, event 551-554 and 556-559 service movement paths, and event 555 brightness fade-out.",
        "next": "The neighboring service animation helpers and events are now emitted by `--family service-animation-helpers`; inspect `C3:4D39..C3:4E73` next.",
    },
    "service-animation-helpers": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "service_animation_helpers.asar.asm",
        "report": ROOT / "notes" / "c3-service-animation-source-pilot.md",
        "manifest": ROOT / "build" / "c3-service-animation-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:48C4", "C3:4D39", "ServiceAnimationHelpersAndEvents"),
        ],
        "description": "Neighboring service animation helpers and events emitted as labeled event/actionscript macro assembly. This covers the reusable down/right/left facing gesture helper, event 560-563 presentation and read-task sequences, the compass direction countdown helper, and event 564-569 fixed-anchor/party-look-at movement presentations.",
        "next": "The neighboring presentation/effect corridor is now emitted by `--family service-presentation-effects`; inspect the larger `C3:4E73..C3:5F8B` payload cluster next.",
    },
    "service-presentation-effects": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "service_presentation_effects.asar.asm",
        "report": ROOT / "notes" / "c3-service-presentation-effects-source-pilot.md",
        "manifest": ROOT / "build" / "c3-service-presentation-effects-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:4D39", "C3:4E73", "ServicePresentationEffects"),
        ],
        "description": "Service presentation/effect corridor emitted as labeled event/actionscript macro assembly. This covers the reusable falling/bounce helper, events 570-583 coordinate variants, traffic-light style offscreen waits, the Dosei-box event-flag gate, and the WH0 fullscreen color-window rise/fall effect sequence.",
        "next": "Inspect `C3:4E73..C3:5F8B` next. It is much larger than this corridor, so split it into referenced sublabels or ebsrc include groups before deciding whether to emit it as one source-form family.",
    },
}


@dataclass(frozen=True)
class Operand:
    kind: str
    value: int | Address


@dataclass(frozen=True)
class Instruction:
    address: Address
    opcode_byte: int
    opcode: Opcode
    raw: bytes
    operands: tuple[Operand, ...]
    call_arg_count: int | None = None


@dataclass(frozen=True)
class RowSource:
    address: Address
    key: str
    name: str
    size: int
    raw: bytes
    instructions: tuple[Instruction, ...]
    source: str = "source-data-map"


def parse_address_key(text: str) -> Address:
    bank_text, offset_text = text.split(":", 1)
    return Address(int(bank_text, 16), int(offset_text, 16))


def fmt_byte(value: int) -> str:
    return f"${value & 0xFF:02X}"


def fmt_word(value: int) -> str:
    return f"${value & 0xFFFF:04X}"


def fmt_long(value: int) -> str:
    return f"${value & 0xFFFFFF:06X}"


def sanitize_symbol(text: str) -> str:
    text = text.replace("::", "_")
    text = re.sub(r"[^0-9A-Za-z_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    if not text:
        text = "Target"
    if text[0].isdigit():
        text = f"Addr_{text}"
    return text


def preferred_label(address: Address, names: dict[str, list[str]]) -> str:
    if address.key in LABEL_OVERRIDES:
        return LABEL_OVERRIDES[address.key]
    if names.get(address.key):
        return names[address.key][0]
    return f"Local_{address.bank:02X}{address.offset:04X}"


def row_name(row: dict[str, Any], names: dict[str, list[str]]) -> str:
    address = parse_address_key(row["address"])
    if address.key in LABEL_OVERRIDES:
        return LABEL_OVERRIDES[address.key]
    if row.get("name"):
        return str(row["name"])
    if names.get(address.key):
        return names[address.key][0]
    return f"Script_{address.bank:02X}{address.offset:04X}"


def load_row_map(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows: dict[str, dict[str, Any]] = {}
    for row in payload["include_rows"]:
        address = row.get("address")
        if address:
            rows[address] = row
    return rows


def decode_exact_row(raw: bytes, start: Address) -> tuple[Instruction, ...]:
    instructions: list[Instruction] = []
    pos = 0
    while pos < len(raw):
        address = Address(start.bank, start.offset + pos)
        raw_start = pos
        opcode_byte = raw[pos]
        pos += 1
        opcode = OPCODES.get(opcode_byte)
        if opcode is None:
            raise ValueError(f"unknown opcode ${opcode_byte:02X} at {address.key}")

        operands: list[Operand] = []
        call_arg_count: int | None = None
        for spec in opcode.args:
            if spec == "byte":
                operands.append(Operand(spec, raw[pos]))
                pos += 1
            elif spec == "word":
                operands.append(Operand(spec, read_u16(raw, pos)))
                pos += 2
            elif spec == "shortptr":
                operands.append(Operand(spec, Address(start.bank, read_u16(raw, pos))))
                pos += 2
            elif spec == "callbackptr":
                operands.append(Operand(spec, Address(0xC0, read_u16(raw, pos))))
                pos += 2
            elif spec == "ptr3":
                operands.append(Operand(spec, Address(raw[pos + 2], read_u16(raw, pos))))
                pos += 3
            elif spec == "callroutine":
                target = Address(raw[pos + 2], read_u16(raw, pos))
                pos += 3
                operands.append(Operand(spec, target))
                count = CALL_ARG_COUNTS.get(target.key)
                if count is None:
                    raise ValueError(f"unknown callroutine arg count for {target.key} at {address.key}")
                call_arg_count = count
                for _ in range(count):
                    operands.append(Operand("call_arg_byte", raw[pos]))
                    pos += 1
            elif spec == "wordlist":
                count = raw[pos]
                pos += 1
                operands.append(Operand("wordlist_count", count))
                for _ in range(count):
                    operands.append(Operand("wordlist_shortptr", Address(start.bank, read_u16(raw, pos))))
                    pos += 2
            else:
                raise ValueError(f"unhandled operand spec {spec!r}")

        if pos > len(raw):
            raise ValueError(f"instruction at {address.key} runs past row end")
        instructions.append(
            Instruction(
                address=address,
                opcode_byte=opcode_byte,
                opcode=opcode,
                raw=raw[raw_start:pos],
                operands=tuple(operands),
                call_arg_count=call_arg_count,
            )
        )
    return tuple(instructions)


def load_rows(
    rom: bytes,
    rows_by_address: dict[str, dict[str, Any]],
    row_keys: list[str],
    names: dict[str, list[str]],
) -> list[RowSource]:
    rows: list[RowSource] = []
    for key in row_keys:
        row = rows_by_address.get(key)
        if not row:
            raise KeyError(f"{key} is not an addressed include row in the source/data map")
        address = parse_address_key(key)
        size = int(row["size"])
        file_offset = hirom_to_file_offset(address.bank, address.offset, len(rom))
        if file_offset is None:
            raise ValueError(f"{key} is not a mapped HiROM address")
        raw = rom[file_offset : file_offset + size]
        rows.append(
            RowSource(
                address=address,
                key=key,
                name=sanitize_symbol(row_name(row, names)),
                size=size,
                raw=raw,
                instructions=decode_exact_row(raw, address),
                source=row.get("path") or "source-data-map",
            )
        )
    return rows


def load_spans(
    rom: bytes,
    spans: list[tuple[str, str, str]],
    names: dict[str, list[str]],
) -> list[RowSource]:
    rows: list[RowSource] = []
    for start_key, end_key, name in spans:
        start = parse_address_key(start_key)
        end = parse_address_key(end_key)
        if start.bank != end.bank:
            raise ValueError(f"span cannot cross banks: {start_key}..{end_key}")
        size = end.offset - start.offset
        if size <= 0:
            raise ValueError(f"span must have positive size: {start_key}..{end_key}")
        file_offset = hirom_to_file_offset(start.bank, start.offset, len(rom))
        if file_offset is None:
            raise ValueError(f"{start_key} is not a mapped HiROM address")
        raw = rom[file_offset : file_offset + size]
        display_name = LABEL_OVERRIDES.get(start.key) or names.get(start.key, [name])[0]
        rows.append(
            RowSource(
                address=start,
                key=f"{start.key}..{end.key}",
                name=sanitize_symbol(display_name),
                size=size,
                raw=raw,
                instructions=decode_exact_row(raw, start),
                source="explicit-span",
            )
        )
    return rows


def collect_selected_ranges(rows: list[RowSource]) -> list[tuple[int, int]]:
    return [(row.address.long, row.address.long + row.size) for row in rows]


def in_selected_ranges(address: Address, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= address.long < end for start, end in ranges)


def collect_c3_targets(rows: list[RowSource]) -> set[str]:
    targets: set[str] = set()
    for row in rows:
        for instruction in row.instructions:
            for operand in instruction.operands:
                if isinstance(operand.value, Address) and operand.value.bank == 0xC3:
                    targets.add(operand.value.key)
    return targets


def collect_label_map(rows: list[RowSource], names: dict[str, list[str]]) -> dict[str, str]:
    ranges = collect_selected_ranges(rows)
    labels: dict[str, str] = {row.key: row.name for row in rows}
    instruction_addresses = {
        instruction.address.key
        for row in rows
        for instruction in row.instructions
    }
    for key, label in LABEL_OVERRIDES.items():
        address = parse_address_key(key)
        if key in labels:
            continue
        if in_selected_ranges(address, ranges) and key in instruction_addresses:
            labels[key] = sanitize_symbol(label)
    for key in collect_c3_targets(rows):
        address = parse_address_key(key)
        if key in labels:
            continue
        if in_selected_ranges(address, ranges) and key in instruction_addresses:
            labels[key] = sanitize_symbol(preferred_label(address, names))
    return labels


def constant_name(address: Address, names: dict[str, list[str]]) -> str:
    if address.key in LABEL_OVERRIDES:
        return sanitize_symbol(LABEL_OVERRIDES[address.key])
    if names.get(address.key):
        return sanitize_symbol(names[address.key][0])
    return f"Target_{address.bank:02X}{address.offset:04X}"


def operand_expr(
    operand: Operand,
    *,
    instruction: Instruction,
    index: int,
    labels: dict[str, str],
    names: dict[str, list[str]],
    constants: dict[str, str],
) -> str:
    if operand.kind == "byte":
        value = int(operand.value)
        var_slot_operands = {
            "EVENT_SET_VAR": {0},
            "EVENT_WRITE_VAR_TO_TEMPVAR": {0},
            "EVENT_WRITE_TEMPVAR_TO_VAR": {0},
            "EVENT_WRITE_VAR_TO_WAIT_TIMER": {0},
            "EVENT_SET_ANIMATION_FRAME_VAR": {0},
            "EVENT_BINOP": {0},
        }
        if index in var_slot_operands.get(instruction.opcode.name, set()):
            return VAR_NAMES.get(value, fmt_byte(value))
        return fmt_byte(value)
    if operand.kind in {"word", "call_arg_byte"}:
        value = int(operand.value)
        return fmt_byte(value) if operand.kind == "call_arg_byte" else fmt_word(value)
    if operand.kind == "wordlist_count":
        return str(int(operand.value))

    if not isinstance(operand.value, Address):
        raise TypeError(f"expected address operand, got {operand.value!r}")

    target = operand.value
    if operand.kind in {"shortptr", "wordlist_shortptr"} and target.key in labels:
        return labels[target.key]

    name = constant_name(target, names)
    symbol = f"!{name}"
    if operand.kind in {"shortptr", "callbackptr", "wordlist_shortptr"}:
        constants.setdefault(symbol, fmt_word(target.offset))
    else:
        constants.setdefault(symbol, fmt_long(target.long))
    return symbol


def macro_name(instruction: Instruction) -> str:
    if instruction.opcode.name == "EVENT_CALLROUTINE":
        return f"EVENT_CALLROUTINE_{instruction.call_arg_count or 0}"
    if instruction.opcode.name in {"EVENT_SWITCH_JUMP_TEMPVAR", "EVENT_SWITCH_CALL_TEMPVAR"}:
        return f"{instruction.opcode.name}_{instruction.operands[0].value}"
    return instruction.opcode.name


def render_instruction(
    instruction: Instruction,
    *,
    labels: dict[str, str],
    names: dict[str, list[str]],
    constants: dict[str, str],
) -> str:
    rendered_operands = [
        operand_expr(
            operand,
            instruction=instruction,
            index=index,
            labels=labels,
            names=names,
            constants=constants,
        )
        for index, operand in enumerate(instruction.operands)
    ]
    args = ", ".join(rendered_operands)
    raw = " ".join(f"{byte:02X}" for byte in instruction.raw)
    if args:
        return f"    %{macro_name(instruction)}({args}) ; {instruction.address.key}  {raw}"
    return f"    %{macro_name(instruction)}() ; {instruction.address.key}  {raw}"


def macro_definitions(used_macros: set[str]) -> list[str]:
    bodies = {
        "EVENT_BREAK_IF_FALSE": ["    db $16", "    dw <target>"],
        "EVENT_BINOP": ["    db $14, <var>, <op>", "    dw <value>"],
        "EVENT_BINOP_TEMPVAR": ["    db $27, <op>", "    dw <value>"],
        "EVENT_CALLROUTINE_0": ["    db $42", "    dl <target>"],
        "EVENT_CALLROUTINE_1": ["    db $42", "    dl <target>", "    db <arg0>"],
        "EVENT_CALLROUTINE_2": ["    db $42", "    dl <target>", "    db <arg0>, <arg1>"],
        "EVENT_CALLROUTINE_3": ["    db $42", "    dl <target>", "    db <arg0>, <arg1>, <arg2>"],
        "EVENT_CLEAR_TICK_CALLBACK": ["    db $0F"],
        "EVENT_END": ["    db $00"],
        "EVENT_END_LAST_TASK": ["    db $13"],
        "EVENT_END_TASK": ["    db $0C"],
        "EVENT_HALT": ["    db $09"],
        "EVENT_LOOP": ["    db $01, <count>"],
        "EVENT_LOOP_END": ["    db $02"],
        "EVENT_LOOP_TEMPVAR": ["    db $24"],
        "EVENT_PAUSE": ["    db $06, <frames>"],
        "EVENT_SET_ANIMATION": ["    db $3B, <animation>"],
        "EVENT_SET_PHYSICS_CALLBACK": ["    db $25", "    dw <target>"],
        "EVENT_SET_POSITION_CHANGE_CALLBACK": ["    db $23", "    dw <target>"],
        "EVENT_SET_PRIORITY": ["    db $43, <priority>"],
        "EVENT_SET_TICK_CALLBACK": ["    db $08", "    dl <target>"],
        "EVENT_SET_VAR": ["    db $0E, <var>", "    dw <value>"],
        "EVENT_SET_VELOCITIES_ZERO": ["    db $39"],
        "EVENT_SET_X": ["    db $28", "    dw <value>"],
        "EVENT_SET_Y": ["    db $29", "    dw <value>"],
        "EVENT_SET_Z": ["    db $2A", "    dw <value>"],
        "EVENT_SET_Z_RELATIVE": ["    db $2D", "    dw <value>"],
        "EVENT_SET_Z_VELOCITY": ["    db $41", "    dw <value>"],
        "EVENT_SHORTCALL": ["    db $1A", "    dw <target>"],
        "EVENT_SHORTCALL_CONDITIONAL": ["    db $0A", "    dw <target>"],
        "EVENT_SHORTCALL_CONDITIONAL_NOT": ["    db $0B", "    dw <target>"],
        "EVENT_SHORTJUMP": ["    db $19", "    dw <target>"],
        "EVENT_SHORT_RETURN": ["    db $1B"],
        "EVENT_START_TASK": ["    db $07", "    dw <target>"],
        "EVENT_WRITE_VAR_TO_TEMPVAR": ["    db $20, <var>"],
        "EVENT_WRITE_WORD_TEMPVAR": ["    db $1D", "    dw <value>"],
        "EVENT_WRITE_TEMPVAR_WAITTIMER": ["    db $44"],
    }
    args = {
        "EVENT_BREAK_IF_FALSE": "target",
        "EVENT_BINOP": "var, op, value",
        "EVENT_BINOP_TEMPVAR": "op, value",
        "EVENT_CALLROUTINE_0": "target",
        "EVENT_CALLROUTINE_1": "target, arg0",
        "EVENT_CALLROUTINE_2": "target, arg0, arg1",
        "EVENT_CALLROUTINE_3": "target, arg0, arg1, arg2",
        "EVENT_LOOP": "count",
        "EVENT_PAUSE": "frames",
        "EVENT_SET_ANIMATION": "animation",
        "EVENT_SET_PHYSICS_CALLBACK": "target",
        "EVENT_SET_POSITION_CHANGE_CALLBACK": "target",
        "EVENT_SET_PRIORITY": "priority",
        "EVENT_SET_TICK_CALLBACK": "target",
        "EVENT_SET_VAR": "var, value",
        "EVENT_SET_X": "value",
        "EVENT_SET_Y": "value",
        "EVENT_SET_Z": "value",
        "EVENT_SET_Z_RELATIVE": "value",
        "EVENT_SET_Z_VELOCITY": "value",
        "EVENT_SHORTCALL": "target",
        "EVENT_SHORTCALL_CONDITIONAL": "target",
        "EVENT_SHORTCALL_CONDITIONAL_NOT": "target",
        "EVENT_SHORTJUMP": "target",
        "EVENT_START_TASK": "target",
        "EVENT_WRITE_VAR_TO_TEMPVAR": "var",
        "EVENT_WRITE_WORD_TEMPVAR": "value",
    }
    missing = sorted(used_macros - bodies.keys())
    if missing:
        raise ValueError(f"missing macro definitions for: {', '.join(missing)}")
    lines = ["; Minimal macro vocabulary used by this source pilot."]
    for name in sorted(used_macros):
        lines.append(f"macro {name}({args.get(name, '')})")
        lines.extend(bodies[name])
        lines.append("endmacro")
        lines.append("")
    return lines


def render_source(
    rows: list[RowSource],
    labels: dict[str, str],
    names: dict[str, list[str]],
    *,
    family_id: str,
) -> tuple[str, dict[str, str]]:
    constants: dict[str, str] = {
        symbol: fmt_byte(value)
        for value, symbol in sorted(VAR_NAMES.items())
    }
    used_macros = {macro_name(instruction) for row in rows for instruction in row.instructions}

    rendered_rows: list[str] = []
    for row in rows:
        rendered_rows.append("")
        rendered_rows.append(f"org ${row.address.bank:02X}{row.address.offset:04X}")
        rendered_rows.append(f"{row.name}:")
        for instruction in row.instructions:
            label = labels.get(instruction.address.key)
            if label and label != row.name:
                rendered_rows.append(f"{label}:")
            rendered_rows.append(
                render_instruction(instruction, labels=labels, names=names, constants=constants)
            )

    constant_lines = ["; External constants and action-script variable slots."]
    for symbol, value in sorted(constants.items()):
        constant_lines.append(f"{symbol} = {value}")

    header = [
        "; Generated by tools/build_c3_event_script_source_pilot.py",
        f"; C3 event/actionscript source pilot: {family_id}.",
        "; This file is intentionally not wired into the bank C3 scaffold yet.",
        "hirom",
        "",
    ]
    source = "\n".join(header + constant_lines + [""] + macro_definitions(used_macros) + rendered_rows) + "\n"
    return source, constants


def row_manifest(row: RowSource) -> dict[str, Any]:
    return {
        "address": row.key,
        "name": row.name,
        "size": row.size,
        "sha1": hashlib.sha1(row.raw).hexdigest(),
        "instruction_count": len(row.instructions),
        "ends_at": f"C3:{row.address.offset + row.size:04X}",
    }


def render_report(
    rows: list[RowSource],
    *,
    family_id: str,
    description: str,
    next_step: str,
    output_path: Path,
    manifest_path: Path,
    mismatches: list[str],
) -> str:
    total_bytes = sum(row.size for row in rows)
    total_instructions = sum(len(row.instructions) for row in rows)
    validation = "PASS" if not mismatches else "FAIL"
    lines = [
        "# C3 event script source pilot",
        "",
        "## Summary",
        "",
        f"- Family: `{family_id}`.",
        f"- Source: `{output_path.relative_to(ROOT).as_posix()}`.",
        f"- Manifest: `{manifest_path.relative_to(ROOT).as_posix()}`.",
        f"- Spans emitted: {len(rows)}.",
        f"- Bytes represented: {total_bytes}.",
        f"- Instructions represented: {total_instructions}.",
        f"- ROM byte validation: {validation}.",
        "",
        description,
        "",
        "The source is not wired into `src/c3/bank_c3_helpers_asar.asm` yet. That is deliberate: this pass proves the representation and byte validation before replacing generated byte corridors in the bank scaffold.",
        "",
        "## Covered Spans",
        "",
        "| Address | Label | Bytes | Instructions |",
        "| --- | --- | ---: | ---: |",
    ]
    for row in rows:
        lines.append(f"| `{row.key}` | `{row.name}` | {row.size} | {len(row.instructions)} |")
    lines.extend(
        [
            "",
            "## Validation",
            "",
        ]
    )
    if mismatches:
        for mismatch in mismatches:
            lines.append(f"- {mismatch}")
    else:
        lines.append("- Every emitted span was decoded over its exact byte range and revalidated against the ROM bytes used to generate it.")
    lines.extend(
        [
            "",
            "## Next Promotion Step",
            "",
            next_step,
        ]
    )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a C3 event/actionscript source-form pilot.")
    parser.add_argument("--rom", help="path to EarthBound (USA).sfc")
    parser.add_argument(
        "--family",
        choices=sorted(FAMILY_DEFAULTS),
        default=FAMILY_ID,
        help="script family to emit",
    )
    parser.add_argument("--source-map", type=Path, default=DEFAULT_SOURCE_MAP)
    parser.add_argument("--index", type=Path, default=DEFAULT_REF_INDEX)
    parser.add_argument("--output", type=Path, help="override source output path")
    parser.add_argument("--report", type=Path, help="override markdown report path")
    parser.add_argument("--manifest", type=Path, help="override generated JSON manifest path")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    family = FAMILY_DEFAULTS[args.family]
    source_map = args.source_map if args.source_map.is_absolute() else ROOT / args.source_map
    index_path = args.index if args.index.is_absolute() else ROOT / args.index
    default_output = family["output"]
    default_report = family["report"]
    default_manifest = family["manifest"]
    output_arg = args.output or default_output
    report_arg = args.report or default_report
    manifest_arg = args.manifest or default_manifest
    output_path = output_arg if output_arg.is_absolute() else ROOT / output_arg
    report_path = report_arg if report_arg.is_absolute() else ROOT / report_arg
    manifest_path = manifest_arg if manifest_arg.is_absolute() else ROOT / manifest_arg

    rom = load_rom(find_rom(args.rom))
    names = load_names(index_path)
    rows_by_address = load_row_map(source_map)
    rows = load_rows(rom, rows_by_address, list(family["rows"]), names)
    rows.extend(load_spans(rom, list(family["spans"]), names))
    labels = collect_label_map(rows, names)
    source, constants = render_source(rows, labels, names, family_id=args.family)

    mismatches: list[str] = []
    for row in rows:
        file_offset = hirom_to_file_offset(row.address.bank, row.address.offset, len(rom))
        expected = rom[file_offset : file_offset + row.size] if file_offset is not None else b""
        observed = b"".join(instruction.raw for instruction in row.instructions)
        if observed != expected:
            mismatches.append(f"{row.key}: decoded bytes do not match ROM span")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(source, encoding="utf-8")

    manifest = {
        "schema": "earthbound-decomp.c3-event-script-source-pilot.v1",
        "generated_by": "tools/build_c3_event_script_source_pilot.py",
        "family": args.family,
        "source": output_path.relative_to(ROOT).as_posix(),
        "report": report_path.relative_to(ROOT).as_posix(),
        "rows": [row_manifest(row) for row in rows],
        "constants": constants,
        "validation": {
            "mismatches": mismatches,
            "status": "pass" if not mismatches else "fail",
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(
        render_report(
            rows,
            family_id=args.family,
            description=str(family["description"]),
            next_step=str(family["next"]),
            output_path=output_path,
            manifest_path=manifest_path,
            mismatches=mismatches,
        ),
        encoding="utf-8",
    )

    print(f"wrote {output_path.relative_to(ROOT).as_posix()}")
    print(f"wrote {report_path.relative_to(ROOT).as_posix()}")
    print(f"wrote {manifest_path.relative_to(ROOT).as_posix()}")
    print(f"rows={len(rows)} bytes={sum(row.size for row in rows)} validation={manifest['validation']['status']}")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
