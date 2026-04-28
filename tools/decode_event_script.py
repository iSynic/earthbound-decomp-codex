from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rom_tools import find_rom, hirom_to_file_offset, load_rom


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INDEX = ROOT / "build" / "ref-index.json"


@dataclass(frozen=True)
class Address:
    bank: int
    offset: int

    @property
    def key(self) -> str:
        return f"{self.bank:02X}:{self.offset:04X}"

    @property
    def long(self) -> int:
        return (self.bank << 16) | self.offset


@dataclass(frozen=True)
class Opcode:
    name: str
    args: tuple[str, ...] = ()
    terminal: bool = False


OPCODES: dict[int, Opcode] = {
    0x00: Opcode("EVENT_END", terminal=True),
    0x01: Opcode("EVENT_LOOP", ("byte",)),
    0x02: Opcode("EVENT_LOOP_END"),
    0x03: Opcode("EVENT_LONGJUMP", ("ptr3",), terminal=True),
    0x04: Opcode("EVENT_LONGCALL", ("ptr3",)),
    0x05: Opcode("EVENT_LONG_RETURN", terminal=True),
    0x06: Opcode("EVENT_PAUSE", ("byte",)),
    0x07: Opcode("EVENT_START_TASK", ("shortptr",)),
    0x08: Opcode("EVENT_SET_TICK_CALLBACK", ("ptr3",)),
    0x09: Opcode("EVENT_HALT", terminal=True),
    0x0A: Opcode("EVENT_SHORTCALL_CONDITIONAL", ("shortptr",)),
    0x0B: Opcode("EVENT_SHORTCALL_CONDITIONAL_NOT", ("shortptr",)),
    0x0C: Opcode("EVENT_END_TASK", terminal=True),
    0x0E: Opcode("EVENT_SET_VAR", ("byte", "word")),
    0x0F: Opcode("EVENT_CLEAR_TICK_CALLBACK"),
    0x10: Opcode("EVENT_SWITCH_JUMP_TEMPVAR", ("wordlist",)),
    0x11: Opcode("EVENT_SWITCH_CALL_TEMPVAR", ("wordlist",)),
    0x12: Opcode("EVENT_WRITE_BYTE_WRAM", ("word", "byte")),
    0x13: Opcode("EVENT_END_LAST_TASK"),
    0x14: Opcode("EVENT_BINOP", ("byte", "byte", "word")),
    0x15: Opcode("EVENT_WRITE_WORD_WRAM", ("word", "word")),
    0x16: Opcode("EVENT_BREAK_IF_FALSE", ("shortptr",)),
    0x17: Opcode("EVENT_BREAK_IF_TRUE", ("shortptr",)),
    0x18: Opcode("EVENT_BINOP_WRAM", ("word", "byte", "byte")),
    0x19: Opcode("EVENT_SHORTJUMP", ("shortptr",), terminal=True),
    0x1A: Opcode("EVENT_SHORTCALL", ("shortptr",)),
    0x1B: Opcode("EVENT_SHORT_RETURN", terminal=True),
    0x1C: Opcode("EVENT_SET_ANIMATION_POINTER", ("ptr3",)),
    0x1D: Opcode("EVENT_WRITE_WORD_TEMPVAR", ("word",)),
    0x1E: Opcode("EVENT_WRITE_WRAM_TEMPVAR", ("word",)),
    0x1F: Opcode("EVENT_WRITE_TEMPVAR_TO_VAR", ("byte",)),
    0x20: Opcode("EVENT_WRITE_VAR_TO_TEMPVAR", ("byte",)),
    0x21: Opcode("EVENT_WRITE_VAR_TO_WAIT_TIMER", ("byte",)),
    0x22: Opcode("EVENT_SET_DRAW_CALLBACK", ("callbackptr",)),
    0x23: Opcode("EVENT_SET_POSITION_CHANGE_CALLBACK", ("callbackptr",)),
    0x24: Opcode("EVENT_LOOP_TEMPVAR"),
    0x25: Opcode("EVENT_SET_PHYSICS_CALLBACK", ("callbackptr",)),
    0x26: Opcode("EVENT_SET_ANIMATION_FRAME_VAR", ("byte",)),
    0x27: Opcode("EVENT_BINOP_TEMPVAR", ("byte", "word")),
    0x28: Opcode("EVENT_SET_X", ("word",)),
    0x29: Opcode("EVENT_SET_Y", ("word",)),
    0x2A: Opcode("EVENT_SET_Z", ("word",)),
    0x2B: Opcode("EVENT_SET_X_RELATIVE", ("word",)),
    0x2C: Opcode("EVENT_SET_Y_RELATIVE", ("word",)),
    0x2D: Opcode("EVENT_SET_Z_RELATIVE", ("word",)),
    0x2E: Opcode("EVENT_SET_X_VELOCITY_RELATIVE", ("word",)),
    0x2F: Opcode("EVENT_SET_Y_VELOCITY_RELATIVE", ("word",)),
    0x30: Opcode("EVENT_SET_Z_VELOCITY_RELATIVE", ("word",)),
    0x39: Opcode("EVENT_SET_VELOCITIES_ZERO"),
    0x3B: Opcode("EVENT_SET_ANIMATION", ("byte",)),
    0x3C: Opcode("EVENT_NEXT_ANIMATION_FRAME"),
    0x3D: Opcode("EVENT_PREV_ANIMATION_FRAME"),
    0x3E: Opcode("EVENT_SKIP_N_ANIMATION_FRAMES", ("byte",)),
    0x3F: Opcode("EVENT_SET_X_VELOCITY", ("word",)),
    0x40: Opcode("EVENT_SET_Y_VELOCITY", ("word",)),
    0x41: Opcode("EVENT_SET_Z_VELOCITY", ("word",)),
    0x42: Opcode("EVENT_CALLROUTINE", ("callroutine",)),
    0x43: Opcode("EVENT_SET_PRIORITY", ("byte",)),
    0x44: Opcode("EVENT_WRITE_TEMPVAR_WAITTIMER"),
}


CALL_ARG_COUNTS: dict[str, int] = {
    "C0:18F3": 0,
    "C0:5E76": 4,
    "C0:64A6": 0,
    "C0:8E9A": 0,
    "C0:3DAA": 0,
    "C0:3F1E": 0,
    "C0:4EF0": 0,
    "C0:A06C": 0,
    "C0:A443": 0,
    "C0:A480": 0,
    "C0:A4A8": 0,
    "C0:A4B2": 0,
    "C0:A4BF": 0,
    "C0:A4D2": 0,
    "C0:A643": 2,
    "C0:A65F": 0,
    "C0:A651": 1,
    "C0:A685": 2,
    "C0:A691": 0,
    "C0:A673": 0,
    "C0:A6A2": 2,
    "C0:A6AD": 2,
    "C0:A6D1": 0,
    "C0:A679": 1,
    "C0:A6DA": 0,
    "C0:A6E3": 0,
    "C0:A82F": 0,
    "C0:A838": 0,
    "C0:A841": 2,
    "C0:A84C": 2,
    "C0:A857": 2,
    "C0:A864": 1,
    "C0:A86F": 2,
    "C0:A87A": 4,
    "C0:A88D": 4,
    "C0:A8A0": 4,
    "C0:A8B3": 4,
    "C0:A8C6": 0,
    "C0:A8D1": 0,
    "C0:A8DC": 0,
    "C0:A8E7": 0,
    "C0:A8F7": 0,
    "C0:A8FF": 0,
    "C0:A907": 1,
    "C0:A912": 5,
    "C0:A92D": 2,
    "C0:A938": 2,
    "C0:A943": 1,
    "C0:A94E": 2,
    "C0:A959": 2,
    "C0:A964": 4,
    "C0:A977": 4,
    "C0:A98B": 4,
    "C0:A99F": 4,
    "C0:A9CF": 6,
    "C0:A9EB": 6,
    "C0:A9B3": 6,
    "C0:9F82": 0,
    "C0:9FA8": 0,
    "C0:9FAE": 2,
    "C0:9FBB": 2,
    "C0:9451": 0,
    "C0:AA07": 6,
    "C0:AA23": 6,
    "C0:AA3F": 3,
    "C0:AA6E": 2,
    "C0:AAAC": 0,
    "C0:AAB5": 4,
    "C0:AACD": 0,
    "C0:C19B": 0,
    "C0:C251": 0,
    "C0:C353": 0,
    "C0:C35D": 0,
    "C0:C48F": 0,
    "C0:C4AF": 0,
    "C0:C4F7": 0,
    "C0:C62B": 0,
    "C0:C6B6": 0,
    "C0:C682": 0,
    "C0:C7DB": 0,
    "C0:C83B": 0,
    "C0:CA4E": 0,
    "C0:CBD3": 0,
    "C0:CC11": 0,
    "C0:CCCC": 0,
    "C0:CD50": 0,
    "C0:CEBE": 0,
    "C0:CF97": 0,
    "C0:D0D9": 0,
    "C0:D0E6": 0,
    "C0:D195": 0,
    "C0:D15C": 0,
    "C0:D59B": 0,
    "C0:D5B0": 0,
    "C0:D77F": 0,
    "C0:D7B3": 0,
    "C0:D7C7": 0,
    "C0:D7E0": 0,
    "C0:D7F7": 0,
    "C0:D98F": 0,
    "C0:20F1": 0,
    "C0:5E82": 0,
    "C0:5ECE": 0,
    "C0:6478": 0,
    "C0:A68B": 0,
    "C0:A6B8": 0,
    "C1:FFD3": 0,
    "C2:0000": 0,
    "C2:654C": 0,
    "C2:EA15": 0,
    "C2:EA74": 0,
    "C2:EACF": 0,
    "C2:FF9A": 0,
    "C3:0100": 0,
    "C4:6C87": 0,
    "C4:6D23": 0,
    "C4:6D4B": 0,
    "C4:6ADB": 0,
    "C4:6EF8": 0,
    "C4:0015": 0,
    "C4:0023": 0,
    "C4:23DC": 0,
    "C4:240A": 0,
    "C4:248A": 0,
    "C4:24D1": 0,
    "C4:257F": 0,
    "C4:258C": 0,
    "C4:2624": 0,
    "C4:25F3": 0,
    "C4:681A": 0,
    "C4:68A9": 0,
    "C4:68AF": 0,
    "C4:68B5": 0,
    "C4:68DC": 0,
    "C4:6903": 0,
    "C4:6914": 0,
    "C4:6957": 0,
    "C4:6712": 0,
    "C4:675C": 0,
    "C4:67B4": 0,
    "C4:67C2": 0,
    "C4:67E6": 0,
    "C4:6A6E": 0,
    "C4:6A9A": 0,
    "C4:6B65": 0,
    "C4:6B37": 0,
    "C4:6B51": 0,
    "C4:6B2D": 0,
    "C4:6C45": 0,
    "C4:6E46": 0,
    "C4:6E74": 0,
    "C4:7044": 0,
    "C4:733C": 0,
    "C4:734C": 0,
    "C4:7369": 0,
    "C4:730E": 0,
    "C4:6B0A": 0,
    "C4:7269": 0,
    "C4:7333": 0,
    "C4:74A8": 0,
    "C4:7499": 0,
    "C4:7A9E": 0,
    "C4:7A6B": 0,
    "C4:7B77": 0,
    "C4:800B": 0,
    "C4:880C": 0,
    "C4:8A6D": 0,
    "C4:8B3B": 0,
    "C4:8B2C": 0,
    "C4:981F": 0,
    "C4:978E": 0,
    "C4:9841": 0,
    "C4:9EC4": 0,
    "C4:A7B0": 0,
    "C4:DD28": 0,
    "C4:DDD0": 0,
    "C4:DE98": 0,
    "C4:DED0": 0,
    "C4:E2D7": 0,
    "C4:E4DA": 0,
    "C4:E4F9": 0,
    "C4:EC6E": 0,
    "C4:ECE7": 0,
    "EF:027D": 0,
    "EF:0CA7": 0,
    "EF:0C87": 0,
    "EF:0C97": 0,
    "EF:0D23": 0,
    "EF:0D46": 0,
    "EF:0D73": 0,
    "EF:0D8D": 0,
    "EF:0DFA": 0,
    "EF:0E67": 0,
    "EF:0E8A": 0,
    "EF:0F60": 0,
    "EF:0FDB": 0,
    "EF:0FF6": 0,
}

CALL_TARGET_SEMANTICS: dict[str, dict[str, str]] = {
    "C0:A4A8": {
        "name": "RefreshCurrentSlotVisualProfile_Mode0IfAligned",
        "group": "visual-profile",
        "contract": "refresh current slot visual profile when alignment allows",
    },
    "C0:A4B2": {
        "name": "RefreshCurrentSlotVisualProfile_Mode1IfAligned",
        "group": "visual-profile",
        "contract": "refresh current slot alternate visual profile when alignment allows",
    },
    "C0:A4BF": {
        "name": "RefreshCurrentSlotVisualProfile_Mode0",
        "group": "visual-profile",
        "contract": "force current slot visual profile refresh",
    },
    "C0:5E76": {
        "name": "Update_CurrentSlotCollisionCache",
        "group": "collision",
        "contract": "refresh current slot collision cache using one script mode byte and a long neighbor-cache callback pointer",
        "args": "collision_probe_mode_byte, neighbor_cache_callback_long",
    },
    "C0:A651": {
        "name": "Script_SetDirectionClassAndField1A86",
        "group": "movement",
        "contract": "read one direction/visual class byte, apply it when active, and store it to current slot field $1A86",
        "args": "direction_class_byte",
    },
    "C0:A679": {
        "name": "Script_SetCurrentSlotDisplayControlBits",
        "group": "current-slot-state",
        "contract": "read one display-control byte and store it to current slot field $2BAA",
        "args": "display_control_bits_byte",
    },
    "C0:A685": {
        "name": "Script_SetCurrentSlotField2B32",
        "group": "current-slot-state",
        "contract": "read one script word and store it to current slot field $2B32",
        "args": "field2b32_word",
    },
    "C0:A6DA": {
        "name": "ClearCurrentSlotNeighborCache",
        "group": "neighbor-cache",
        "contract": "write #$FFFF to current slot neighbor cache $289E",
    },
    "C0:A82F": {
        "name": "DisableCurrentSlotNeighborCache",
        "group": "neighbor-cache",
        "contract": "write #$8000 sentinel to current slot neighbor cache $289E",
    },
    "C0:9451": {
        "name": "RestoreSavedCoordinateState",
        "group": "world-state-restore",
        "contract": "restore saved coordinate/world state after transitions or script presentation",
    },
    "C0:AA6E": {
        "name": "Script_ApplyCurrentSlotVisualCountdownState",
        "group": "visual-profile",
        "contract": "read countdown/state bytes and apply current slot visual countdown state",
        "args": "visual_state_byte, countdown_byte",
    },
    "C1:FFD3": {
        "name": "ComputeBankC1ChecksumTail",
        "group": "intro-integrity",
        "contract": "bank-local checksum/integrity tail used by intro control flow",
    },
    "C2:0000": {
        "name": "RunEnemySunstrokeCheck",
        "group": "battle-runtime",
        "contract": "battle-runtime sunstroke/special controller helper; C3 intro use remains unusual",
    },
    "C4:0015": {
        "name": "ClearCurrentSlot10f2RefreshVisualAndCheckLiveArea",
        "group": "visual-profile",
        "contract": "clear current slot $10F2, refresh visual state, and test live-area status",
    },
    "C4:6E46": {
        "name": "SetYieldToTextLatch9641",
        "group": "text-presentation",
        "contract": "set the yield-to-text latch used by event presentation handoff",
    },
    "C4:6E74": {
        "name": "CheckStagedPositionWithinPlayerProximityThreshold",
        "group": "proximity-gate",
        "contract": "test staged position against the player proximity threshold",
    },
    "C4:800B": {
        "name": "UndrawFlyoverTextAndRestoreWorldDisplay",
        "group": "world-state-restore",
        "contract": "restore world display state after flyover/text presentation",
    },
    "C4:8B3B": {
        "name": "MakePartyLookAtActiveEntityCallback",
        "group": "party-facing",
        "contract": "make party members face or track the active entity",
    },
    "C0:A841": {
        "name": "Script_PlaySoundEffectParameter",
        "group": "text-presentation",
        "contract": "read one script word as a sound/effect id and play it through C0:ABE0",
        "args": "sound_effect_id_word",
    },
    "C0:A84C": {
        "name": "ScriptWrapper_C21628_ReadWord",
        "group": "event-flag",
        "contract": "read one script word and test it through C2:1628",
        "args": "event_flag_word",
    },
    "C0:A857": {
        "name": "ScriptWrapper_C2165E_ReadWordPreserveMode",
        "group": "event-flag",
        "contract": "preserve incoming mode in X, read one script word, and call C2:165E",
        "args": "event_flag_word",
    },
    "C0:A864": {
        "name": "Script_CopyRegistrySlotAnchorToCurrentSlot_ReadByte",
        "group": "current-slot-state",
        "contract": "read one script byte and copy that registry slot anchor to current slot state",
        "args": "registry_slot_byte",
    },
    "C0:A86F": {
        "name": "Script_CopyPoseDescriptorSlotAnchorToCurrentSlot_ReadWord",
        "group": "current-slot-state",
        "contract": "read one script word and copy that pose-descriptor slot anchor to current slot state",
        "args": "pose_descriptor_slot_word",
    },
    "C0:A88D": {
        "name": "ActionScript_QueueTextPointer",
        "group": "text-presentation",
        "contract": "read two script words as text pointer pieces and queue text record type #$0008",
        "args": "text_pointer_low_word, text_pointer_bank_word",
    },
    "C0:A907": {
        "name": "ActionScript_PrepareNewEntityAtTeleportDestination",
        "group": "overworld-runtime",
        "contract": "read one teleport-destination selector byte and prepare a new entity at that destination",
        "args": "teleport_destination_selector_byte",
    },
    "C0:A943": {
        "name": "ActionScript_GetPositionOfPartyMember",
        "group": "current-slot-state",
        "contract": "read one party-member selector byte and copy that member position into script state",
        "args": "party_member_selector_byte",
    },
    "C0:A94E": {
        "name": "ScriptWrapper_C46984_ReadWord",
        "group": "presentation-render",
        "contract": "read one script word and forward it to C4:6984",
        "args": "c46984_selector_word",
    },
    "C0:A959": {
        "name": "ScriptWrapper_C469F1_ReadWord",
        "group": "presentation-render",
        "contract": "read one script word and forward it to C4:69F1",
        "args": "c469f1_selector_word",
    },
    "C0:A964": {
        "name": "ScriptWrapper_C47225_ReadTwoWords",
        "group": "presentation-render",
        "contract": "read two script words and forward them to C4:7225",
        "args": "c47225_arg0_word, c47225_arg1_word",
    },
    "C0:A98B": {
        "name": "ScriptWrapper_C46534_ReadThreeWords",
        "group": "presentation-render",
        "contract": "read two script words and forward them to C4:6534; callee consumes the staged third value",
        "args": "c46534_arg0_word, c46534_arg1_word",
    },
    "C0:9FBB": {
        "name": "ActionScript_FadeOutWrapper",
        "group": "presentation-render",
        "contract": "read one fade-out effect word and pass it to C0:887A",
        "args": "fadeout_effect_word",
    },
    "EF:0CA7": {
        "name": "CheckCurrentDeliveryRetryThreshold",
        "group": "timed-delivery",
        "contract": "increment current row retry counter and compare against delivery record word 2",
    },
    "EF:0D23": {
        "name": "GetCurrentDeliveryRetryWait",
        "group": "timed-delivery",
        "contract": "return current delivery row retry-wait word 3",
    },
    "EF:0D8D": {
        "name": "QueueCurrentDeliveryPointer1",
        "group": "timed-delivery",
        "contract": "queue current delivery row pointer 1 as immediate queue type #$0008",
    },
    "EF:0DFA": {
        "name": "QueueCurrentDeliveryPointer2",
        "group": "timed-delivery",
        "contract": "queue current delivery row pointer 2 as deferred queue type #$000A",
    },
    "EF:0E67": {
        "name": "GetCurrentDeliveryEnterSpeed",
        "group": "timed-delivery",
        "contract": "return current delivery row enter-speed word 8",
    },
    "EF:0E8A": {
        "name": "GetCurrentDeliveryExitSpeed",
        "group": "timed-delivery",
        "contract": "return current delivery row exit-speed word 9",
    },
    "EF:0F60": {
        "name": "CheckDeliveryServiceReadyForArrival",
        "group": "timed-delivery",
        "contract": "test delivery/service readiness against busy state and controller latches",
    },
    "EF:0FDB": {
        "name": "BeginDeliverySuccessArrivalState",
        "group": "timed-delivery",
        "contract": "arm success-side delivery arrival state and presentation side effects",
    },
    "EF:0FF6": {
        "name": "ResetDeliveryArrivalState",
        "group": "timed-delivery",
        "contract": "clear transient arrival state and restore/reset delivery controller latch",
    },
}


TERMINAL_NAMES = {
    "EVENT_END",
    "EVENT_LONGJUMP",
    "EVENT_LONG_RETURN",
    "EVENT_HALT",
    "EVENT_END_TASK",
    "EVENT_SHORTJUMP",
    "EVENT_SHORT_RETURN",
}


def parse_address(text: str) -> Address:
    raw = text.strip().upper().replace("$", "")
    if ":" in raw:
        bank_text, off_text = raw.split(":", 1)
        return Address(int(bank_text, 16), int(off_text, 16))
    if not re.fullmatch(r"[0-9A-F]{6}", raw):
        raise argparse.ArgumentTypeError(f"expected BB:AAAA or BBAAAA address, got {text!r}")
    return Address(int(raw[:2], 16), int(raw[2:], 16))


def read_u16(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def load_names(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    index = json.loads(path.read_text(encoding="utf-8"))
    names: dict[str, list[str]] = {}
    preferred_sources = {
        "local-working-names": 0,
        "local-notes": 1,
        "ebsrc-main": 2,
        "earthbound-disasm-legacy": 3,
    }
    candidates: dict[str, list[tuple[int, str]]] = {}
    for entry in index.get("entries", []):
        address = entry.get("address")
        name = entry.get("name") or entry.get("include")
        if not address or not name:
            continue
        if entry.get("kind") == "note-mention":
            continue
        score = preferred_sources.get(entry.get("source", ""), 9)
        candidates.setdefault(address, []).append((score, str(name)))
    for address, items in candidates.items():
        ordered = []
        for _, name in sorted(items):
            if name not in ordered:
                ordered.append(name)
        names[address] = ordered[:4]
    for address, semantics in CALL_TARGET_SEMANTICS.items():
        name = semantics["name"]
        labels = names.setdefault(address, [])
        if name not in labels:
            labels.insert(0, name)
    return names


def format_target(address: Address, names: dict[str, list[str]]) -> str:
    labels = names.get(address.key, [])
    if labels:
        return f"${address.key} <{labels[0]}>"
    return f"${address.key}"


def format_word(value: int) -> str:
    return f"${value:04X}"


def format_byte(value: int) -> str:
    return f"${value:02X}"


def decode_args(
    rom: bytes,
    pos: int,
    bank: int,
    specs: tuple[str, ...],
    names: dict[str, list[str]],
) -> tuple[list[str], int, bool]:
    args: list[str] = []
    complete = True
    for spec in specs:
        if spec == "byte":
            if pos >= len(rom):
                return args, pos, False
            args.append(format_byte(rom[pos]))
            pos += 1
        elif spec == "word":
            if pos + 1 >= len(rom):
                return args, pos, False
            args.append(format_word(read_u16(rom, pos)))
            pos += 2
        elif spec == "shortptr":
            if pos + 1 >= len(rom):
                return args, pos, False
            target = Address(bank, read_u16(rom, pos))
            args.append(format_target(target, names))
            pos += 2
        elif spec == "callbackptr":
            if pos + 1 >= len(rom):
                return args, pos, False
            target = Address(0xC0, read_u16(rom, pos))
            args.append(format_target(target, names))
            pos += 2
        elif spec == "ptr3":
            if pos + 2 >= len(rom):
                return args, pos, False
            target = Address(rom[pos + 2], read_u16(rom, pos))
            args.append(format_target(target, names))
            pos += 3
        elif spec == "wordlist":
            if pos >= len(rom):
                return args, pos, False
            count = rom[pos]
            pos += 1
            values = []
            for _ in range(count):
                if pos + 1 >= len(rom):
                    complete = False
                    break
                target = Address(bank, read_u16(rom, pos))
                values.append(format_target(target, names))
                pos += 2
            args.append(f"count={count} [" + ", ".join(values) + "]")
        elif spec == "callroutine":
            if pos + 2 >= len(rom):
                return args, pos, False
            target = Address(rom[pos + 2], read_u16(rom, pos))
            pos += 3
            if target.key == "C0:9F82":
                if pos >= len(rom):
                    args.append(format_target(target, names))
                    return args, pos, False
                count = rom[pos]
                pos += 1
                choices = []
                for _ in range(count):
                    if pos + 1 >= len(rom):
                        complete = False
                        break
                    choices.append(format_word(read_u16(rom, pos)))
                    pos += 2
                args.append(
                    f"{format_target(target, names)}, choices={count} ["
                    + ", ".join(choices)
                    + "]"
                )
                continue
            count = CALL_ARG_COUNTS.get(target.key)
            if count is None:
                args.append(f"{format_target(target, names)} ; args unknown, stopping")
                complete = False
                break
            raw_args = []
            for _ in range(count):
                if pos >= len(rom):
                    complete = False
                    break
                raw_args.append(format_byte(rom[pos]))
                pos += 1
            if raw_args:
                args.append(f"{format_target(target, names)}, " + ", ".join(raw_args))
            else:
                args.append(format_target(target, names))
        else:
            raise ValueError(f"unhandled arg spec {spec}")
    return args, pos, complete


def decode_script(
    rom: bytes,
    start: Address,
    *,
    max_instructions: int,
    max_bytes: int,
    stop_at_terminal: bool,
    names: dict[str, list[str]],
) -> list[str]:
    file_offset = hirom_to_file_offset(start.bank, start.offset, len(rom))
    if file_offset is None:
        raise ValueError(f"{start.key} is not a mapped HiROM address")
    pos = file_offset
    end = min(len(rom), pos + max_bytes)
    lines: list[str] = []
    for _ in range(max_instructions):
        if pos >= end:
            lines.append(f"; stopped at byte limit (+0x{pos - file_offset:X})")
            break
        address = Address(start.bank, start.offset + (pos - file_offset))
        opcode_byte = rom[pos]
        pos += 1
        opcode = OPCODES.get(opcode_byte)
        raw_start = pos - 1
        if opcode is None:
            lines.append(f"{address.key}  {opcode_byte:02X}          .byte ${opcode_byte:02X} ; unknown event opcode")
            break
        args, pos, complete = decode_args(rom, pos, start.bank, opcode.args, names)
        raw = " ".join(f"{byte:02X}" for byte in rom[raw_start:pos])
        arg_text = " " + ", ".join(args) if args else ""
        lines.append(f"{address.key}  {raw:<20} {opcode.name}{arg_text}")
        if not complete:
            break
        if stop_at_terminal and (opcode.terminal or opcode.name in TERMINAL_NAMES):
            break
    else:
        lines.append(f"; stopped at instruction limit ({max_instructions})")
    return lines


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Decode EarthBound event/actionscript bytecode at a CPU address.")
    parser.add_argument("address", nargs="+", type=parse_address, help="event script address, e.g. C3:AB59")
    parser.add_argument("--rom", help="path to EarthBound (USA).sfc")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX, help="reference index for target labels")
    parser.add_argument("--max-instructions", type=int, default=80)
    parser.add_argument("--max-bytes", type=lambda text: int(text, 0), default=0x200)
    parser.add_argument("--no-stop", action="store_true", help="continue past terminal opcodes until limits")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    rom = load_rom(find_rom(args.rom))
    index_path = args.index if args.index.is_absolute() else ROOT / args.index
    names = load_names(index_path)
    for i, address in enumerate(args.address):
        if i:
            print()
        print(f"; event script decode {address.key}")
        for line in decode_script(
            rom,
            address,
            max_instructions=args.max_instructions,
            max_bytes=args.max_bytes,
            stop_at_terminal=not args.no_stop,
            names=names,
        ):
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
