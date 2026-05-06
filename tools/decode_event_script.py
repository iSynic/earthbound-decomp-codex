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
    "C0:9FF0": {
        "name": "ReturnFromPhysicsCallback_NoMovement",
        "group": "movement",
        "contract": "passive physics callback entry that returns without integrating movement",
    },
    "C0:9FF1": {
        "name": "Integrate_XYAndZVelocity_WithSpriteRefresh",
        "group": "movement",
        "contract": "integrate XY and Z velocity, then refresh the current-slot footprint/sprite mask",
    },
    "C0:9FC8": {
        "name": "Integrate_XYVelocityOnly",
        "group": "movement",
        "contract": "integrate fractional/current-slot XY velocity into world X/Y position",
    },
    "C0:A039": {
        "name": "ReturnFromPositionChangeCallback_NoProjection",
        "group": "presentation-render",
        "contract": "passive position-change callback entry that returns without screen projection",
    },
    "C0:A03A": {
        "name": "ProjectWorldToScreen_FromCamera31AndHeight",
        "group": "presentation-render",
        "contract": "project current slot world coordinates through camera $31 and height state into screen coordinates",
    },
    "C0:A26B": {
        "name": "PhysicsCallback_TargetComparisonAndProjection",
        "group": "movement",
        "contract": "physics callback that compares current slot against active target context and falls back to camera projection",
    },
    "C0:5200": {
        "name": "Tick_OverworldPlayerPositionAndCallbacks",
        "group": "overworld-runtime",
        "contract": "normal overworld tick callback for player/object position and registered callbacks",
    },
    "C0:4D78": {
        "name": "Tick_Event2SnapshotObjectReconcile",
        "group": "overworld-runtime",
        "contract": "intro/event snapshot tick callback that reconciles object state against saved coordinates",
    },
    "C0:A055": {
        "name": "ProjectWorldToScreen_FromCamera39",
        "group": "presentation-render",
        "contract": "project current slot world X/Y through camera $39/$3B",
    },
    "C0:A0A0": {
        "name": "ProjectWorldToScreen_FromCamera39AndHeight",
        "group": "presentation-render",
        "contract": "project current slot world X/Y through camera $39/$3B and subtract height from screen Y",
    },
    "C0:A360": {
        "name": "UpdatePosition_WhenNoNeighbor_WithSpriteRefresh",
        "group": "movement",
        "contract": "per-frame no-neighbor position updater that integrates movement and refreshes footprint state",
    },
    "C0:A37A": {
        "name": "UpdatePosition_WhenNoNeighbor_WithSpriteRefresh_CurrentSlot",
        "group": "movement",
        "contract": "current-slot entry that reloads the active slot and joins the no-neighbor sprite-refresh updater",
    },
    "C0:A384": {
        "name": "UpdatePosition_WhenNoNeighbor",
        "group": "movement",
        "contract": "per-frame no-neighbor position updater that integrates movement without the footprint refresh tail",
    },
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
    "C0:A6A2": {
        "name": "Script_SetMovementStateCA4E",
        "group": "movement",
        "contract": "read one script word into the movement timer scale latch and derive the movement task timer from the active vector via C0:CA4E",
        "args": "movement_timer_word",
    },
    "C0:A6AD": {
        "name": "Script_SetMovementStateCBD3",
        "group": "movement",
        "contract": "read one script word into the movement timer scale latch and derive the movement task timer from speed scale via C0:CBD3",
        "args": "movement_timer_word",
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
    "C0:A65F": {
        "name": "SetCurrentSlotDirectionClassIfActive",
        "group": "movement",
        "contract": "copy the tempvar direction/class into the current slot when the slot is active",
    },
    "C0:A68B": {
        "name": "StoreAInCurrentSlotField2B32",
        "group": "current-slot-state",
        "contract": "store the accumulator value into current slot movement/visual field $2B32",
    },
    "C0:A691": {
        "name": "GetCurrentSlotField2B32",
        "group": "current-slot-state",
        "contract": "return current slot movement/visual field $2B32 for script-side tests",
    },
    "C0:A6B8": {
        "name": "GetCurrentSlotHasNoCachedNeighborFlag",
        "group": "neighbor-cache",
        "contract": "test whether the current slot has no cached neighbor/attention target",
    },
    "C0:A6E3": {
        "name": "WatchAndRefreshCompanionVisualPhase",
        "group": "visual-profile",
        "contract": "poll companion visual state and refresh the current slot phase while the watcher remains active",
    },
    "C0:A838": {
        "name": "MarkCurrentSlotCollisionStateFFFF",
        "group": "collision",
        "contract": "mark the current slot collision/neighbor state with the #$FFFF sentinel",
    },
    "C0:9451": {
        "name": "RestoreSavedCoordinateState",
        "group": "world-state-restore",
        "contract": "restore saved coordinate/world state after transitions or script presentation",
    },
    "C0:9F82": {
        "name": "ChooseRandomScriptWord",
        "group": "overworld-runtime",
        "contract": "read an inline choice count followed by that many words, choose one at random, and leave it in the tempvar/result latch",
        "args": "choice_count_byte, choice_words[]",
    },
    "C0:9FAE": {
        "name": "ActionScript_FadeInWrapper",
        "group": "presentation-render",
        "contract": "read one display-transition word and pass it to the fade-in transition helper at C0:886C",
        "args": "fadein_effect_word",
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
    "C2:FF9A": {
        "name": "CheckOverworldPositionHashThreshold3Of8",
        "group": "battle-runtime",
        "contract": "test the overworld position hash against the 3-of-8 threshold used by encounter/battle gating",
    },
    "C3:0100": {
        "name": "DisplayAntiPiracyScreen",
        "group": "other",
        "contract": "display the anti-piracy screen and terminate the script path",
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
    "C4:0023": {
        "name": "StoreLowNibble1a42ToCurrentScriptField1372",
        "group": "presentation-render",
        "contract": "copy the low nibble of display/script latch $1A42 into current script field $1372",
    },
    "C4:681A": {
        "name": "QueueCurrentVisualTypeMovementScript",
        "group": "visual-profile",
        "contract": "queue the movement script associated with the current slot visual type",
    },
    "C4:68B5": {
        "name": "TestValueLeftOfCurrentAnchorX",
        "group": "presentation-render",
        "contract": "compare a staged value against the current anchor X and report whether it is left of the anchor",
    },
    "C4:68DC": {
        "name": "TestValueAboveCurrentAnchorY",
        "group": "presentation-render",
        "contract": "compare a staged value against the current anchor Y and report whether it is above the anchor",
    },
    "C4:6914": {
        "name": "GetCurrentVisualTypeRecordByte03",
        "group": "visual-profile",
        "contract": "return byte $03 from the current visual-type record",
    },
    "C4:6957": {
        "name": "UpdateCurrentSlotFrameSelector",
        "group": "visual-profile",
        "contract": "update the current slot frame selector from visual-type animation state",
    },
    "C4:6ADB": {
        "name": "ComputeCurrentSlotTargetDirectionOctant",
        "group": "movement",
        "contract": "compute the direction octant from the current slot toward its cached target",
    },
    "C4:6B0A": {
        "name": "RoundAngleToOctantAndCacheCurrentSlot",
        "group": "movement",
        "contract": "round the active angle to a direction octant and cache it on the current slot",
    },
    "C4:6B37": {
        "name": "RotateDirectionOctantHalfTurn",
        "group": "movement",
        "contract": "rotate the current direction octant by a half turn",
    },
    "C4:6C45": {
        "name": "SnapshotCurrentSlotAnchorToStagedPosition",
        "group": "current-slot-state",
        "contract": "copy the current slot anchor position into the staged position fields used by movement callbacks",
    },
    "C4:6C87": {
        "name": "RestoreCurrentSlotAnchorFromCachedTarget",
        "group": "current-slot-state",
        "contract": "restore the current slot anchor from the cached target position fields",
    },
    "C4:6E74": {
        "name": "CheckStagedPositionWithinPlayerProximityThreshold",
        "group": "proximity-gate",
        "contract": "test staged position against the player proximity threshold",
    },
    "C4:6EF8": {
        "name": "CheckCurrentSlotWithinPlayerProximityThreshold",
        "group": "proximity-gate",
        "contract": "test the current slot anchor against the player proximity threshold",
    },
    "C4:7044": {
        "name": "ProjectAngleIntoCurrentSlotVectorWords",
        "group": "movement",
        "contract": "project the active angle into current-slot movement vector words",
    },
    "C4:7269": {
        "name": "ClassifyCurrentSlotAgainstAreaBounds",
        "group": "current-slot-state",
        "contract": "classify the current slot against the active area-bounds rectangle and return the result in the tempvar",
    },
    "C4:7333": {
        "name": "ReadActiveOverworldRegistryCount",
        "group": "overworld-runtime",
        "contract": "read the active overworld registry count used by landing/profile scripts",
    },
    "C4:7A9E": {
        "name": "LoadCurrentEntityIndexedWindowGfxToVram",
        "group": "text-presentation",
        "contract": "load the current entity's indexed window graphics variant into VRAM",
    },
    "C4:7B77": {
        "name": "LoadIndexedWindowGfxAndReadVariantByte",
        "group": "text-presentation",
        "contract": "load indexed window graphics and return the selected variant byte to the script",
    },
    "C4:800B": {
        "name": "UndrawFlyoverTextAndRestoreWorldDisplay",
        "group": "world-state-restore",
        "contract": "restore world display state after flyover/text presentation",
    },
    "C4:ECE7": {
        "name": "IsEntityStillOnCastScreen",
        "group": "presentation-render",
        "contract": "test whether the current entity remains on the cast-screen presentation viewport",
    },
    "C4:8B3B": {
        "name": "MakePartyLookAtActiveEntityCallback",
        "group": "party-facing",
        "contract": "make party members face or track the active entity",
    },
    "C4:8BE1": {
        "name": "SimpleScreenPositionCallback",
        "group": "presentation-render",
        "contract": "tick callback that keeps the active entity at a simple screen-projected position",
    },
    "C4:8C02": {
        "name": "SimpleScreenPositionCallbackOffset",
        "group": "presentation-render",
        "contract": "tick callback that keeps the active entity at a simple screen-projected position with offset handling",
    },
    "C4:8C2B": {
        "name": "CentreScreenOnEntityCallback",
        "group": "presentation-render",
        "contract": "tick callback that centers the screen around the active entity",
    },
    "C4:8C3E": {
        "name": "CentreScreenOnEntityCallbackOffset",
        "group": "presentation-render",
        "contract": "tick callback that centers the screen around the active entity with offset handling",
    },
    "C0:A841": {
        "name": "Script_PlaySoundEffectParameter",
        "group": "text-presentation",
        "contract": "read one script word as a sound/effect id and play it through C0:ABE0",
        "args": "sound_effect_id_word",
    },
    "C0:A84C": {
        "name": "ActionScript_TestEventFlag_ReadWord",
        "group": "event-flag",
        "contract": "read one script word and test it through C2:1628",
        "args": "event_flag_word",
    },
    "C0:A857": {
        "name": "ActionScript_SetOrClearEventFlag_ReadWordPreserveMode",
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
    "C0:A87A": {
        "name": "Script_SetCameraRelativeAnchor_ReadTwoWords",
        "group": "current-slot-state",
        "contract": "read X/Y offset words, place the current slot at camera origin plus those offsets, and set the current-slot anchor flags",
        "args": "camera_relative_x_word, camera_relative_y_word",
    },
    "C0:A88D": {
        "name": "ActionScript_QueueTextPointer",
        "group": "text-presentation",
        "contract": "read two script words as text pointer pieces and queue text record type #$0008",
        "args": "text_pointer_low_word, text_pointer_bank_word",
    },
    "C0:A8B3": {
        "name": "Script_SetStagedPositionOffset_ReadTwoWords",
        "group": "current-slot-state",
        "contract": "read X/Y offset words and apply them to the staged position used by script presentation helpers",
        "args": "staged_offset_x_word, staged_offset_y_word",
    },
    "C0:A8C6": {
        "name": "StepCurrentSlotTowardCachedTarget",
        "group": "movement",
        "contract": "step current slot toward cached target through C4:7143 and report arrival",
    },
    "C0:A8D1": {
        "name": "StepCurrentSlotTowardCachedTarget_WithHalfTurnFacing",
        "group": "movement",
        "contract": "step current slot toward cached target, applying the C4:7143 half-turn facing postprocess",
    },
    "C0:A8DC": {
        "name": "StepCurrentSlotTowardCachedTarget_NoFacingRefresh",
        "group": "movement",
        "contract": "step current slot toward cached target without refreshing the current slot facing selector, and report arrival",
    },
    "C0:20F1": {
        "name": "ScriptRelease_CurrentEntityVisualState",
        "group": "visual-profile",
        "contract": "release the current entity/visual slot state at the end of a script-controlled actor sequence",
    },
    "C0:3DAA": {
        "name": "Sync_CurrentSlotToPartyCharacterRecord",
        "group": "current-slot-state",
        "contract": "sync current slot position/state into the matching party character record",
    },
    "C0:4EF0": {
        "name": "Restore_CurrentSlotFromSnapshotRecord",
        "group": "current-slot-state",
        "contract": "restore the current slot position/state from its saved snapshot record",
    },
    "C0:5E82": {
        "name": "Update_CurrentSlotCollisionCache_WithTerrainCompatibility",
        "group": "collision",
        "contract": "refresh current slot collision cache using terrain-compatibility rules",
    },
    "C0:5ECE": {
        "name": "Update_CurrentSlotCollisionCache_FromHorizontalEdges",
        "group": "collision",
        "contract": "refresh current slot collision cache from horizontal edge probes",
    },
    "C0:6478": {
        "name": "Update_CurrentSlotNeighborCache_Priority",
        "group": "neighbor-cache",
        "contract": "refresh current slot neighbor-cache priority before attention/collision routing",
    },
    "C0:C19B": {
        "name": "CopyPathToLane_FromPartyMemberRequest",
        "group": "overworld-runtime",
        "contract": "copy a party-member path request into the active movement lane",
    },
    "C0:C251": {
        "name": "CopyPathToLane_FromCurrentEntityRequestReverse",
        "group": "overworld-runtime",
        "contract": "copy the current entity path request into the active movement lane in reverse order",
    },
    "C0:C6B6": {
        "name": "CheckCurrentSlotInsideLiveAreaWindow",
        "group": "proximity-gate",
        "contract": "test whether the current slot is inside the live-area/window bounds used by event scripts",
    },
    "C0:C48F": {
        "name": "GateWidePlayerDistanceBucket",
        "group": "proximity-gate",
        "contract": "gate the wide player-distance bucket for the current slot, suppressing attention when the current slot state or global movement gate says to wait",
    },
    "C0:C7DB": {
        "name": "UpdateCurrentSlotFootprintMask",
        "group": "collision",
        "contract": "refresh the current slot footprint/collision mask after position or visual-state changes",
    },
    "C0:C83B": {
        "name": "InstallScriptMovementVectorFromDirection",
        "group": "movement",
        "contract": "install current-slot movement vector words from the script direction and speed state",
    },
    "C0:CA4E": {
        "name": "SetMovementTaskTimerFromActiveVector",
        "group": "movement",
        "contract": "derive the movement task timer from the active movement vector and cache it for script waits",
    },
    "C0:CBD3": {
        "name": "SetMovementTaskTimerFromSpeedScale",
        "group": "movement",
        "contract": "derive the movement task timer from the current speed scale and cache it for script waits",
    },
    "C0:D15C": {
        "name": "HasUsableOverlapNeighborContext",
        "group": "neighbor-cache",
        "contract": "test whether the current overlap/neighbor context can drive a scripted movement decision",
    },
    "C0:D59B": {
        "name": "Check_NpcAttentionCoordinatorActive",
        "group": "overworld-runtime",
        "contract": "test whether the NPC-attention coordinator is still active for the current script actor",
    },
    "C0:D5B0": {
        "name": "Gate_NpcAttentionCoordinatorFromScript",
        "group": "overworld-runtime",
        "contract": "start or advance the NPC-attention coordinator and return whether the script should keep waiting",
    },
    "C0:D77F": {
        "name": "MarkOtherSlotsAttentionLocked",
        "group": "current-slot-state",
        "contract": "mark other eligible slots' attention/interaction flags with the high bits before scripted object-interaction cleanup",
    },
    "C0:D7B3": {
        "name": "Save_CurrentSlotAttentionPosition",
        "group": "current-slot-state",
        "contract": "save the current slot position into the NPC-attention saved-position fields for a later scripted restore",
    },
    "C0:D7C7": {
        "name": "Restore_CurrentSlotAttentionPosition",
        "group": "current-slot-state",
        "contract": "restore the current slot position from the NPC-attention saved-position fields after scripted handoff",
    },
    "C0:D7E0": {
        "name": "Normalize_CurrentSlotAttentionState",
        "group": "current-slot-state",
        "contract": "normalize the current slot attention marker to state 1 when the marker is nonzero",
    },
    "C0:D7F7": {
        "name": "Consume_CurrentSlotAttentionPath",
        "group": "current-slot-state",
        "contract": "consume the current slot attention path into live movement target state",
    },
    "C0:D98F": {
        "name": "Export_CurrentSlotAttentionTarget",
        "group": "current-slot-state",
        "contract": "export the current slot attention target into the script-visible cached target fields",
    },
    "C0:A907": {
        "name": "ActionScript_PrepareNewEntityAtTeleportDestination",
        "group": "overworld-runtime",
        "contract": "read one teleport-destination selector byte and prepare a new entity at that destination",
        "args": "teleport_destination_selector_byte",
    },
    "C0:A912": {
        "name": "ActionScript_PrepareNewEntity",
        "group": "overworld-runtime",
        "contract": "read explicit X/Y position words plus a facing/selector byte and stage a new entity through C4:6E37",
        "args": "new_entity_x_word, new_entity_y_word, new_entity_facing_byte",
    },
    "C0:A92D": {
        "name": "Script_SetTargetToVisualTypeSlotPosition_ReadWord",
        "group": "current-slot-state",
        "contract": "read one visual-type slot word and copy that slot position into the active script target",
        "args": "visual_type_slot_word",
    },
    "C0:A938": {
        "name": "Script_SetTargetToPoseDescriptorSlotPosition_ReadWord",
        "group": "current-slot-state",
        "contract": "read one pose-descriptor slot word and copy that slot position into the active script target",
        "args": "pose_descriptor_slot_word",
    },
    "C0:A943": {
        "name": "ActionScript_GetPositionOfPartyMember",
        "group": "current-slot-state",
        "contract": "read one party-member selector byte and copy that member position into script state",
        "args": "party_member_selector_byte",
    },
    "C0:A94E": {
        "name": "FaceVisualTypeSlotTowardCurrentSlot_ReadWord",
        "group": "presentation-render",
        "contract": "read one visual-type id word, resolve that slot, and face it toward the current slot",
        "args": "visual_type_id_word",
    },
    "C0:A959": {
        "name": "FacePoseDescriptorSlotTowardCurrentSlot_ReadWord",
        "group": "presentation-render",
        "contract": "read one pose-descriptor id word, resolve that slot, and face it toward the current slot",
        "args": "pose_descriptor_id_word",
    },
    "C0:A964": {
        "name": "SetCurrentSlotAreaBoundsFromRadii_ReadTwoWords",
        "group": "movement",
        "contract": "read X/Y radius words and build an area-bounds rectangle around the current slot",
        "args": "radius_x_word, radius_y_word",
    },
    "C0:A977": {
        "name": "Movement_LoadBattleBg",
        "group": "presentation-render",
        "contract": "read battle-background animation and presentation-sprite resource words, then load the battle-bg presentation state for a movement script",
        "args": "battle_bg_animation_word, presentation_sprite_resource_word",
    },
    "C0:A98B": {
        "name": "SpawnEntityAtCurrentSlotAnchor_ReadTwoWords",
        "group": "entity-spawn",
        "contract": "read two entity initializer words and spawn or initialize an entity at the current slot anchor",
        "args": "entity_visual_type_word, entity_initializer_word",
    },
    "C0:A99F": {
        "name": "SpawnEntityRelative_ReadTwoWords",
        "group": "entity-spawn",
        "contract": "read visual-type and initializer words, then spawn a cast-scene entity at the staged script var0/var1 position relative to the live BG3 scroll",
        "args": "entity_visual_type_word, entity_initializer_word",
    },
    "C0:A9B3": {
        "name": "PrintCastNameParty_ReadThreeWords",
        "group": "text-presentation",
        "contract": "read cast-name source and tile-position words, then print the party cast-name row through the ending cast-name tilemap helpers",
        "args": "cast_name_source_word, cast_name_tile_x_word, cast_name_tile_y_word",
    },
    "C0:A9CF": {
        "name": "PrintCastNameEntityVar0_ReadThreeWords",
        "group": "text-presentation",
        "contract": "read cast-name source and tile-position words, then print the entity-var0 cast-name row through the ending cast-name tilemap helpers",
        "args": "cast_name_source_word, cast_name_tile_x_word, cast_name_tile_y_word",
    },
    "C0:A9EB": {
        "name": "PrintCastNameCurrentThreshold_ReadThreeWords",
        "group": "text-presentation",
        "contract": "read cast-name print words, replace the source selector with the current cast-scroll threshold, and print through the ending cast-name tilemap helpers",
        "args": "cast_name_source_word, cast_name_tile_x_word, cast_name_tile_y_word",
    },
    "C0:9FBB": {
        "name": "ActionScript_FadeOutWrapper",
        "group": "presentation-render",
        "contract": "read one fade-out effect word and pass it to C0:887A",
        "args": "fadeout_effect_word",
    },
    "C0:AA07": {
        "name": "ActionScript_FadeOutWithMosaic",
        "group": "presentation-render",
        "contract": "read three display-transition words and pass them to the mosaic fade-out transition helper at C0:8814",
        "args": "display_transition_mode_word, display_transition_x_word, display_transition_y_word",
    },
    "C0:AA23": {
        "name": "Script_StageMosaicWh0Mask_ReadThreeWords",
        "group": "presentation-render",
        "contract": "read left-X, Y, and right-X words, then forward them as A/X/Y to the C4:7765 WH0 mosaic/window-mask starter",
        "args": "mask_left_x_word, mask_y_word, mask_right_x_word",
    },
    "C0:AA3F": {
        "name": "Script_SetVisualSetupBytesByMode",
        "group": "presentation-render",
        "contract": "read fixed-color red/green/blue bytes into $9E37-$9E39, then apply color math using the caller-supplied mode selector",
        "args": "fixed_color_red_byte, fixed_color_green_byte, fixed_color_blue_byte",
    },
    "C0:AAB5": {
        "name": "Script_RunLandingPaletteFade_ReadWordByteByte",
        "group": "presentation-render",
        "contract": "read a palette selector word, palette scale byte, and fade frame-count byte, then forward them to C4:97C0",
        "args": "landing_palette_selector_word, palette_scale_byte, fade_frame_count_byte",
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

EVENT_TARGET_SEMANTICS: dict[str, str] = {
    "C3:A159": "LoopActiveEntityWalkPulseVar4Countdown_WaitAndRestart",
    "C3:A425": "ReturnFromNpcAttentionNeighborCacheCheck",
}

SCRIPT_VAR_NAMES = {index: f"var{index}" for index in range(8)}

ACTIONSCRIPT_DIRECTION_WORDS: dict[int, dict[str, str]] = {
    0x0000: {
        "name": "direction_down",
        "contract": "down/south-facing direction class word, runtime-backed by C0:A65F/C0:C83B callback-boundary evidence",
    },
    0x0002: {
        "name": "direction_right",
        "contract": "right/east-facing direction class word, runtime-backed by C0:A65F/C0:C83B callback-boundary evidence",
    },
    0x0004: {
        "name": "direction_up",
        "contract": "up/north-facing direction class word, runtime-backed by C0:A65F/C0:C83B callback-boundary evidence",
    },
    0x0006: {
        "name": "direction_left",
        "contract": "left/west-facing direction class word, runtime-backed by C0:A65F/C0:C83B callback-boundary evidence",
    },
}

ACTIONSCRIPT_ANIMATION_IDS: dict[int, dict[str, str]] = {
    0x00: {
        "name": "animation_frame0",
        "contract": "default/first script animation frame selector; often alternated with $01 for pulses",
    },
    0x01: {
        "name": "animation_frame1",
        "contract": "alternate/second script animation frame selector; often paired with $00",
    },
    0xFF: {
        "name": "animation_hidden_or_off",
        "contract": "sentinel/off-frame animation selector used by blink or disappearance-style pulses",
    },
}

ACTIONSCRIPT_FIELD2B32_WORDS: dict[int, dict[str, str]] = {
    0x0040: {
        "name": "field2b32_step_0040",
        "contract": "small movement/vector magnitude written to current slot $2B32; boundary-audited through movement/timer consumers",
    },
    0x0060: {
        "name": "field2b32_step_0060",
        "contract": "observed movement/vector magnitude written to current slot $2B32; boundary-audited through movement/timer consumers",
    },
    0x0080: {
        "name": "field2b32_step_0080",
        "contract": "observed movement/vector magnitude written to current slot $2B32; boundary-audited through movement/timer consumers",
    },
    0x00C0: {
        "name": "field2b32_step_00c0",
        "contract": "observed movement/vector magnitude written to current slot $2B32; boundary-audited through movement/timer consumers",
    },
    0x0100: {
        "name": "field2b32_step_0100",
        "contract": "standard movement/vector magnitude written to current slot $2B32; boundary-audited through movement/timer consumers",
    },
    0x0140: {
        "name": "field2b32_step_0140",
        "contract": "observed movement/vector magnitude written to current slot $2B32; boundary-audited through movement/timer consumers",
    },
    0x0160: {
        "name": "field2b32_step_0160",
        "contract": "larger movement/vector magnitude written to current slot $2B32; boundary-audited through movement/timer consumers",
    },
    0x0180: {
        "name": "field2b32_step_0180",
        "contract": "observed movement/vector magnitude written to current slot $2B32; boundary-audited through movement/timer consumers",
    },
    0x0200: {
        "name": "field2b32_step_0200",
        "contract": "large movement/vector magnitude written to current slot $2B32; boundary-audited through movement/timer consumers",
    },
    0x0280: {
        "name": "field2b32_step_0280",
        "contract": "observed movement/vector magnitude written to current slot $2B32; boundary-audited through movement/timer consumers",
    },
    0x0600: {
        "name": "field2b32_step_0600",
        "contract": "very large movement/vector magnitude written to current slot $2B32; boundary-audited through movement/timer consumers",
    },
}

BINOP_OPERATION_NAMES = {
    0x00: "AND",
    0x01: "OR",
    0x02: "ADD",
    0x03: "EOR",
}

WRAM_FIELD_NAMES = {
    0x5D9A: "queue_pending_or_special_state_flag",
}

OPCODE_ARG_FIELDS: dict[str, tuple[str, ...]] = {
    "EVENT_LOOP": ("count",),
    "EVENT_LONGJUMP": ("jump_target",),
    "EVENT_LONGCALL": ("call_target",),
    "EVENT_PAUSE": ("frames",),
    "EVENT_START_TASK": ("task_script",),
    "EVENT_SET_TICK_CALLBACK": ("tick_callback",),
    "EVENT_SHORTCALL_CONDITIONAL": ("conditional_call_target",),
    "EVENT_SHORTCALL_CONDITIONAL_NOT": ("inverted_conditional_call_target",),
    "EVENT_SET_VAR": ("script_var", "value_word"),
    "EVENT_SWITCH_JUMP_TEMPVAR": ("switch_jump_targets",),
    "EVENT_SWITCH_CALL_TEMPVAR": ("switch_call_targets",),
    "EVENT_WRITE_BYTE_WRAM": ("wram_addr", "value_byte"),
    "EVENT_BINOP": ("script_var", "operation_byte", "value_word"),
    "EVENT_WRITE_WORD_WRAM": ("wram_addr", "value_word"),
    "EVENT_BREAK_IF_FALSE": ("break_target",),
    "EVENT_BREAK_IF_TRUE": ("break_target",),
    "EVENT_BINOP_WRAM": ("wram_addr", "operation_byte", "script_var"),
    "EVENT_SHORTJUMP": ("jump_target",),
    "EVENT_SHORTCALL": ("call_target",),
    "EVENT_SET_ANIMATION_POINTER": ("animation_pointer",),
    "EVENT_WRITE_WORD_TEMPVAR": ("value_word",),
    "EVENT_WRITE_WRAM_TEMPVAR": ("wram_addr",),
    "EVENT_WRITE_TEMPVAR_TO_VAR": ("script_var",),
    "EVENT_WRITE_VAR_TO_TEMPVAR": ("script_var",),
    "EVENT_WRITE_VAR_TO_WAIT_TIMER": ("script_var",),
    "EVENT_SET_DRAW_CALLBACK": ("draw_callback",),
    "EVENT_SET_POSITION_CHANGE_CALLBACK": ("position_change_callback",),
    "EVENT_SET_PHYSICS_CALLBACK": ("physics_callback",),
    "EVENT_SET_ANIMATION_FRAME_VAR": ("script_var",),
    "EVENT_BINOP_TEMPVAR": ("operation_byte", "value_word"),
    "EVENT_SET_X": ("x_word",),
    "EVENT_SET_Y": ("y_word",),
    "EVENT_SET_Z": ("z_word",),
    "EVENT_SET_X_RELATIVE": ("x_delta_word",),
    "EVENT_SET_Y_RELATIVE": ("y_delta_word",),
    "EVENT_SET_Z_RELATIVE": ("z_delta_word",),
    "EVENT_SET_X_VELOCITY_RELATIVE": ("x_velocity_delta_word",),
    "EVENT_SET_Y_VELOCITY_RELATIVE": ("y_velocity_delta_word",),
    "EVENT_SET_Z_VELOCITY_RELATIVE": ("z_velocity_delta_word",),
    "EVENT_SET_ANIMATION": ("animation_id",),
    "EVENT_SKIP_N_ANIMATION_FRAMES": ("frame_count",),
    "EVENT_SET_X_VELOCITY": ("x_velocity_word",),
    "EVENT_SET_Y_VELOCITY": ("y_velocity_word",),
    "EVENT_SET_Z_VELOCITY": ("z_velocity_word",),
    "EVENT_SET_PRIORITY": ("priority",),
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
        "local-script-payloads": 1,
        "local-c3-source-pilot": 2,
        "local-notes": 3,
        "ebsrc-main": 4,
        "earthbound-disasm-legacy": 5,
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
    for address, name in EVENT_TARGET_SEMANTICS.items():
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


def format_script_var(value: int) -> str:
    return SCRIPT_VAR_NAMES.get(value, format_byte(value))


def format_signed_word(value: int) -> str:
    signed = value - 0x10000 if value & 0x8000 else value
    if signed == 0:
        return format_word(value)
    prefix = "+" if signed >= 0 else ""
    return f"{format_word(value)} ({prefix}{signed})"


def format_wram_addr(value: int) -> str:
    name = WRAM_FIELD_NAMES.get(value)
    if name:
        return f"{format_word(value)} <{name}>"
    return format_word(value)


def format_operation_byte(value: int) -> str:
    name = BINOP_OPERATION_NAMES.get(value)
    if name:
        return f"{format_byte(value)} <{name}>"
    return format_byte(value)


def format_named_word(value: int, names: dict[int, dict[str, str]]) -> str:
    item = names.get(value)
    if item:
        return f"{format_word(value)} <{item['name']}>"
    return format_word(value)


def format_named_byte(value: int, names: dict[int, dict[str, str]]) -> str:
    item = names.get(value)
    if item:
        return f"{format_byte(value)} <{item['name']}>"
    return format_byte(value)


def semantic_field(opcode_name: str, index: int) -> str | None:
    fields = OPCODE_ARG_FIELDS.get(opcode_name)
    if not fields or index >= len(fields):
        return None
    return fields[index]


def format_semantic_value(field: str | None, spec: str, value: int) -> str:
    if field is None:
        return format_byte(value) if spec == "byte" else format_word(value)
    if field == "script_var":
        return f"{field}={format_script_var(value)}"
    if field == "operation_byte":
        return f"{field}={format_operation_byte(value)}"
    if field == "wram_addr":
        return f"{field}={format_wram_addr(value)}"
    if field == "animation_id":
        return f"{field}={format_named_byte(value, ACTIONSCRIPT_ANIMATION_IDS)}"
    if field.endswith("_velocity_word") or field.endswith("_delta_word"):
        return f"{field}={format_signed_word(value)}"
    if spec == "byte":
        return f"{field}={format_byte(value)}"
    return f"{field}={format_word(value)}"


def format_pointer_value(field: str | None, target: Address, names: dict[str, list[str]]) -> str:
    rendered = format_target(target, names)
    if field is None:
        return rendered
    return f"{field}={rendered}"


def call_arg_fields(target_key: str) -> list[str]:
    schema = CALL_TARGET_SEMANTICS.get(target_key, {}).get("args", "")
    return [field.strip() for field in schema.split(",") if field.strip()]


def call_arg_width(field: str) -> int | None:
    if field.endswith("_byte"):
        return 1
    if field.endswith("_word"):
        return 2
    if field.endswith("_long"):
        return 3
    return None


def format_call_arg_value(
    field: str,
    raw_args: list[int],
    cursor: int,
    names: dict[str, list[str]],
) -> tuple[str, int] | None:
    width = call_arg_width(field)
    if width is None or cursor + width > len(raw_args):
        return None
    if width == 1:
        value = raw_args[cursor]
        if field == "direction_class_byte":
            return f"{field}={format_named_byte(value, ACTIONSCRIPT_DIRECTION_WORDS)}", cursor + 1
        return f"{field}={format_byte(value)}", cursor + 1
    if width == 2:
        value = raw_args[cursor] | (raw_args[cursor + 1] << 8)
        if field == "field2b32_word":
            return f"{field}={format_named_word(value, ACTIONSCRIPT_FIELD2B32_WORDS)}", cursor + 2
        return f"{field}={format_word(value)}", cursor + 2
    target = Address(raw_args[cursor + 2], raw_args[cursor] | (raw_args[cursor + 1] << 8))
    return f"{field}={format_target(target, names)}", cursor + 3


def format_callroutine_args(target: Address, raw_args: list[int], names: dict[str, list[str]]) -> list[str]:
    fields = call_arg_fields(target.key)
    if not fields:
        return [format_byte(value) for value in raw_args]

    cursor = 0
    rendered: list[str] = []
    for field in fields:
        formatted = format_call_arg_value(field, raw_args, cursor, names)
        if formatted is None:
            return [format_byte(value) for value in raw_args]
        value, cursor = formatted
        rendered.append(value)
    if cursor != len(raw_args):
        return [format_byte(value) for value in raw_args]
    return rendered


def decode_args(
    rom: bytes,
    pos: int,
    bank: int,
    opcode_name: str,
    specs: tuple[str, ...],
    names: dict[str, list[str]],
) -> tuple[list[str], int, bool]:
    args: list[str] = []
    complete = True
    for index, spec in enumerate(specs):
        field = semantic_field(opcode_name, index)
        if spec == "byte":
            if pos >= len(rom):
                return args, pos, False
            args.append(format_semantic_value(field, spec, rom[pos]))
            pos += 1
        elif spec == "word":
            if pos + 1 >= len(rom):
                return args, pos, False
            args.append(format_semantic_value(field, spec, read_u16(rom, pos)))
            pos += 2
        elif spec == "shortptr":
            if pos + 1 >= len(rom):
                return args, pos, False
            target = Address(bank, read_u16(rom, pos))
            args.append(format_pointer_value(field, target, names))
            pos += 2
        elif spec == "callbackptr":
            if pos + 1 >= len(rom):
                return args, pos, False
            target = Address(0xC0, read_u16(rom, pos))
            args.append(format_pointer_value(field, target, names))
            pos += 2
        elif spec == "ptr3":
            if pos + 2 >= len(rom):
                return args, pos, False
            target = Address(rom[pos + 2], read_u16(rom, pos))
            args.append(format_pointer_value(field, target, names))
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
            field_prefix = f"{field}=" if field else ""
            args.append(f"{field_prefix}count={count} [" + ", ".join(values) + "]")
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
                raw_args.append(rom[pos])
                pos += 1
            if raw_args:
                rendered_args = format_callroutine_args(target, raw_args, names)
                args.append(f"{format_target(target, names)}, " + ", ".join(rendered_args))
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
        args, pos, complete = decode_args(rom, pos, start.bank, opcode.name, opcode.args, names)
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
