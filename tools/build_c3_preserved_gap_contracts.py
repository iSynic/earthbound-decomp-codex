from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from rom_tools import find_rom, hirom_to_file_offset, load_rom


ROOT = Path(__file__).resolve().parent.parent
BANK = "C3"
BANK_NUM = 0xC3
SCHEMA = "earthbound-decomp.c3-preserved-gap-contracts.v1"
DEFAULT_OUTPUT = ROOT / "notes" / "c3-preserved-gap-contracts.json"
DEFAULT_REPORT = ROOT / "notes" / "c3-preserved-gap-contracts.md"


def parse_address(raw: str) -> int:
    bank, offset = raw.split(":", 1)
    if bank.upper() != BANK:
        raise ValueError(f"expected {BANK} address, got {raw}")
    return int(offset, 16)


def address(value: int) -> str:
    return f"{BANK}:{value:04X}"


def address_range(start: int, end: int) -> str:
    return f"{address(start)}..{address(end)}"


def rom_slice(rom: bytes, start: int, end: int) -> bytes:
    start_offset = hirom_to_file_offset(BANK_NUM, start, len(rom))
    end_offset = hirom_to_file_offset(BANK_NUM, end, len(rom))
    if start_offset is None or end_offset is None:
        raise ValueError(f"unable to map {address_range(start, end)}")
    return rom[start_offset:end_offset]


def byte_summary(rom: bytes, start: int, end: int) -> dict[str, Any]:
    raw = rom_slice(rom, start, end)
    return {
        "range": address_range(start, end),
        "size": end - start,
        "sha1": hashlib.sha1(raw).hexdigest(),
        "first_bytes": " ".join(f"{byte:02X}" for byte in raw[:16]),
        "last_bytes": " ".join(f"{byte:02X}" for byte in raw[-16:]),
    }


GROUPS: list[dict[str, Any]] = [
    {
        "start": "C3:0000",
        "end": "C3:0295",
        "name": "C3BankPrefixPalettesSystemScreensAndEarlyScriptData",
        "status": "closed-preserved-data-and-source-adjacent-prefix",
        "summary": (
            "C3's bank prefix is not an event/actionscript source-pilot gap. It is a mixed prefix "
            "containing file-select sprite palettes, two 65816 system-screen helpers, two event-flag "
            "words, a small event-221 prefix island, and the decoded EVENT_221 through EVENT_224 bytecode bundle."
        ),
        "evidence": [
            "refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank03.asm:16",
            "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Routine_Macros_EB.asm:44452",
            "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Routine_Macros_EB.asm:44524",
            "notes/c4-system-error-screen-render-0b51-0b75.md:55",
        ],
        "segments": [
            {
                "start": "C3:0000",
                "end": "C3:0100",
                "name": "FileSelectScreenSpritePalettes",
                "classification": "overworld-sprite-palette-data",
                "source_expectation": "asset/data corridor; keep as palette bytes or generated palette asset",
                "evidence": [
                    "refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank03.asm:16",
                    "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Routine_Macros_EB.asm:44452",
                ],
                "note": "Eight 0x20-byte file-select sprite palettes at the front of bank C3.",
            },
            {
                "start": "C3:0100",
                "end": "C3:0142",
                "name": "DisplayAntiPiracyScreen",
                "classification": "source-helper",
                "source_expectation": "ordinary 65816 helper; already named, but outside the event/actionscript source-pilot corpus",
                "evidence": [
                    "notes/c4-system-error-screen-render-0b51-0b75.md:55",
                    "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Routine_Macros_EB.asm:44459",
                ],
                "note": "Loads/decompresses the copyright-protection graphics and tilemap through the C4 screen helpers.",
            },
            {
                "start": "C3:0142",
                "end": "C3:0184",
                "name": "DisplayFaultyGamePakScreen",
                "classification": "source-helper",
                "source_expectation": "ordinary 65816 helper; already named, but outside the event/actionscript source-pilot corpus",
                "evidence": [
                    "notes/c4-system-error-screen-render-0b51-0b75.md:56",
                    "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Routine_Macros_EB.asm:44492",
                ],
                "note": "Loads/decompresses the incorrect-region/faulty Game Pak screen graphics and tilemap.",
            },
            {
                "start": "C3:0184",
                "end": "C3:0186",
                "name": "EventFlagNoContinueSelected",
                "classification": "event-flag-word",
                "source_expectation": "two-byte data constant; preserve or emit as a named word",
                "evidence": [
                    "refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank03.asm:31",
                    "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Routine_Macros_EB.asm:44524",
                ],
                "note": "Reference include is named data/event_flag_nocontinue_selected.asm.",
            },
            {
                "start": "C3:0186",
                "end": "C3:0188",
                "name": "NessPajamaFlag",
                "classification": "event-flag-word",
                "source_expectation": "two-byte data constant; preserve or emit as a named word",
                "evidence": [
                    "refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank03.asm:33",
                    "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Routine_Macros_EB.asm:44527",
                ],
                "note": "Reference include is named data/ness_pajama_flag.asm; legacy C0 callers read DATA_C30186.",
            },
            {
                "start": "C3:0188",
                "end": "C3:0195",
                "name": "Event221PreludeData",
                "classification": "raw-or-named-data",
                "source_expectation": "13-byte prefix before the EVENT_221 bytecode entry; preserve until exact consumer semantics are pinned",
                "evidence": [
                    "refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank03.asm:35",
                    "notes/c3-event-222-224-movement-helper-cluster.md",
                ],
                "note": "The byte-exact EVENT_221 signature starts at C3:0195, leaving this leading prefix bounded but still semantically cautious.",
            },
            {
                "start": "C3:0195",
                "end": "C3:0295",
                "name": "Event221To224PaulaMovementScripts",
                "classification": "event-bytecode-asset",
                "source_expectation": "event/actionscript bytecode bundle containing EVENT_221 through EVENT_224",
                "evidence": [
                    "notes/c3-event-222-224-movement-helper-cluster.md",
                    "notes/script-payloads-c3.md",
                ],
                "note": "Reference scripts 221-224 byte-match at C3:0195, C3:0235, C3:024A, and C3:0260.",
            },
        ],
    },
    {
        "start": "C3:9FF2",
        "end": "C3:A07F",
        "name": "IntroMovementPatternAndAntiPiracyGate",
        "status": "closed-preserved-movement-pattern-and-decoded-bytecode",
        "summary": (
            "The mid-C3 preserved source-pilot gap is the documented intro movement-pattern table family plus "
            "a decoded intro bytecode tail that calls the C1 checksum/anti-piracy gate and C3:0100 display helper."
        ),
        "evidence": [
            "notes/c3-intro-script-frontier-9ff2-a07f.md:90",
            "notes/script-payloads-c3.md:383",
            "notes/script-payloads-c3.md:435",
        ],
        "segments": [
            {
                "start": "C3:9FF2",
                "end": "C3:A010",
                "name": "IntroMovementPatternPointerTable",
                "classification": "movement-pattern-data",
                "source_expectation": "compact movement-pattern pointer table",
                "evidence": ["notes/c3-intro-script-frontier-9ff2-a07f.md:90"],
                "note": "Pointer table into the immediately following intro movement-pattern records.",
            },
            {
                "start": "C3:A010",
                "end": "C3:A01B",
                "name": "IntroMovementPattern09Loop",
                "classification": "movement-pattern-data",
                "source_expectation": "compact movement-pattern record",
                "evidence": ["notes/c3-intro-script-frontier-9ff2-a07f.md:91"],
                "note": "Movement loop record using step value 0x09.",
            },
            {
                "start": "C3:A01B",
                "end": "C3:A026",
                "name": "IntroMovementPattern08Loop",
                "classification": "movement-pattern-data",
                "source_expectation": "compact movement-pattern record",
                "evidence": ["notes/c3-intro-script-frontier-9ff2-a07f.md:92"],
                "note": "Movement loop record using step value 0x08.",
            },
            {
                "start": "C3:A026",
                "end": "C3:A02D",
                "name": "IntroMovementPatternFFLoop",
                "classification": "movement-pattern-data",
                "source_expectation": "compact movement-pattern record",
                "evidence": ["notes/c3-intro-script-frontier-9ff2-a07f.md:93"],
                "note": "Movement loop record using step value 0xFF.",
            },
            {
                "start": "C3:A02D",
                "end": "C3:A038",
                "name": "IntroMovementPattern08LoopAlt",
                "classification": "movement-pattern-data",
                "source_expectation": "compact movement-pattern record",
                "evidence": ["notes/c3-intro-script-frontier-9ff2-a07f.md:94"],
                "note": "Alternate movement loop record using step value 0x08.",
            },
            {
                "start": "C3:A038",
                "end": "C3:A043",
                "name": "IntroMovementPattern04Loop",
                "classification": "movement-pattern-data",
                "source_expectation": "compact movement-pattern record",
                "evidence": ["notes/c3-intro-script-frontier-9ff2-a07f.md:95"],
                "note": "Movement loop record using step value 0x04.",
            },
            {
                "start": "C3:A043",
                "end": "C3:A04E",
                "name": "IntroCutsceneCameraPanGate",
                "classification": "event-bytecode",
                "source_expectation": "decoded event bytecode; not ordinary 65816 source",
                "evidence": ["notes/script-payloads-c3.md:435"],
                "note": "Calls C1:FFD3, branches into the pan loop, and calls DisplayAntiPiracyScreen if the gate fails.",
            },
            {
                "start": "C3:A04E",
                "end": "C3:A052",
                "name": "StartIntroCameraPanTickLoop",
                "classification": "event-bytecode-label",
                "source_expectation": "decoded event branch label",
                "evidence": ["notes/c3-intro-script-frontier-9ff2-a07f.md:97"],
                "note": "Installs the C0:5200 overworld/player tick callback for the intro pan.",
            },
            {
                "start": "C3:A052",
                "end": "C3:A05E",
                "name": "LoopIntroCameraPanWaitAndC2Step",
                "classification": "event-bytecode-label",
                "source_expectation": "decoded event branch label",
                "evidence": ["notes/c3-intro-script-frontier-9ff2-a07f.md:98"],
                "note": "Wait loop that calls the C2 overworld step helper before jumping back.",
            },
            {
                "start": "C3:A05E",
                "end": "C3:A076",
                "name": "IntroCutsceneSpriteObjectSetup",
                "classification": "event-bytecode",
                "source_expectation": "decoded event bytecode; not ordinary 65816 source",
                "evidence": ["notes/c3-intro-script-frontier-9ff2-a07f.md:99"],
                "note": "Initializes the intro sprite/object presentation path.",
            },
            {
                "start": "C3:A076",
                "end": "C3:A07F",
                "name": "LoopIntroCompanionVisualRefresh",
                "classification": "event-bytecode-label",
                "source_expectation": "decoded event branch label",
                "evidence": ["notes/c3-intro-script-frontier-9ff2-a07f.md:100"],
                "note": "Refresh loop before the following C3:A07F HaltEventScript payload.",
            },
        ],
    },
    {
        "start": "C3:DFE8",
        "end": "C3:E450",
        "name": "MapInteractionMovementAndMenuDataTables",
        "status": "closed-preserved-data-table-corridor",
        "summary": (
            "The late C3 preserved source-pilot gap is a packed data corridor: interaction/pathfinding "
            "tables, map movement direction tables, menu/title cursor tile words, and a four-byte prelude "
            "before the C3:E450 window helper."
        ),
        "evidence": [
            "refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank03.asm:1997",
            "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Routine_Macros_EB.asm:45055",
            "notes/input-direction-and-interaction-probes-c0402b-c04116.md:25",
            "notes/c3-map-movement-parameter-table-e1d8-e240.md:37",
            "notes/c3-menu-cursor-tile-data-e3f8-e450.md:25",
        ],
        "segments": [
            {
                "start": "C3:DFE8",
                "end": "C3:DFF0",
                "name": "PathfindingTileContextGateTable",
                "classification": "contract-backed-data",
                "source_expectation": "rom-table contract PATHFINDING_TILE_CONTEXT_GATE_TABLE",
                "evidence": ["notes/c3-late-interaction-table-contracts.md"],
                "note": "C0:C0B4 and C0:C19B mask the current tile context to 0..7, index these gate bytes, and abort the path consumer if the selected byte is zero.",
            },
            {
                "start": "C3:DFF0",
                "end": "C3:E012",
                "name": "PathfindingContextGatePrefixTail",
                "classification": "raw-or-named-data",
                "source_expectation": "table data; keep raw until the exact downstream pathfinding-context indexing is named",
                "evidence": [
                    "notes/pathfinding-consumers-direction-helpers-c0bd96-c0c7db.md:68",
                    "notes/c3-late-interaction-table-contracts.md",
                ],
                "note": "The first eight gate bytes are promoted; this tail remains part of the larger pathfinding-context table family.",
            },
            {
                "start": "C3:E012",
                "end": "C3:E09A",
                "name": "PathfindingContextGateTable",
                "classification": "raw-or-named-data",
                "source_expectation": "table data; preserve legacy sublabel until record semantics are exact",
                "evidence": ["refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Routine_Macros_EB.asm:45055"],
                "note": "Legacy disassembly sublabels this word-pair corridor as DATA_C3E012.",
            },
            {
                "start": "C3:E09A",
                "end": "C3:E0BC",
                "name": "PathfindingContextGatePaddingOrTail",
                "classification": "raw-or-named-data",
                "source_expectation": "table tail/padding; preserve until consumer indexing distinguishes it",
                "evidence": ["refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Routine_Macros_EB.asm:45076"],
                "note": "Legacy marks C3:E09A as a distinct data anchor without payload comments.",
            },
            {
                "start": "C3:E0BC",
                "end": "C3:E0F4",
                "name": "PathfindingContextGateWordTableA",
                "classification": "raw-or-named-data",
                "source_expectation": "word table; preserve until the C0 consumer field names are promoted",
                "evidence": ["refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Routine_Macros_EB.asm:45082"],
                "note": "Legacy sublabel DATA_C3E0BC; values are repeated 32-bit-looking word pairs.",
            },
            {
                "start": "C3:E0F4",
                "end": "C3:E12C",
                "name": "PathfindingContextGateWordTableB",
                "classification": "raw-or-named-data",
                "source_expectation": "word table; preserve until the C0 consumer field names are promoted",
                "evidence": ["refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Routine_Macros_EB.asm:45091"],
                "note": "Legacy sublabel DATA_C3E0F4; same source-data-map include as C3:DFE8.",
            },
            {
                "start": "C3:E12C",
                "end": "C3:E148",
                "name": "InputDirectionPermissionMaskTable",
                "classification": "contract-backed-data",
                "source_expectation": "rom-table contract INPUT_DIRECTION_PERMISSION_MASK_TABLE",
                "evidence": ["notes/input-direction-and-interaction-probes-c0402b-c04116.md:25"],
                "note": "C0:404F maps active input nibbles through this permission-mask table.",
            },
            {
                "start": "C3:E148",
                "end": "C3:E158",
                "name": "InteractionProbeDirectionXOffsetTable",
                "classification": "contract-backed-data",
                "source_expectation": "rom-table contract INTERACTION_PROBE_DIRECTION_X_OFFSETS",
                "evidence": ["notes/input-direction-and-interaction-probes-c0402b-c04116.md:26"],
                "note": "Signed X offsets for one facing-direction interaction probe.",
            },
            {
                "start": "C3:E158",
                "end": "C3:E168",
                "name": "InteractionProbeDirectionYOffsetTable",
                "classification": "contract-backed-data",
                "source_expectation": "rom-table contract INTERACTION_PROBE_DIRECTION_Y_OFFSETS",
                "evidence": ["notes/input-direction-and-interaction-probes-c0402b-c04116.md:27"],
                "note": "Signed Y offsets for one facing-direction interaction probe.",
            },
            {
                "start": "C3:E168",
                "end": "C3:E178",
                "name": "InteractionResultFacingRemapTable",
                "classification": "contract-backed-data",
                "source_expectation": "rom-table contract INTERACTION_RESULT_FACING_REMAP_TABLE",
                "evidence": ["notes/c3-late-interaction-table-contracts.md"],
                "note": "C0:42C2 maps the player-facing value through these eight words and stores the result to $2AF6[target].",
            },
            {
                "start": "C3:E178",
                "end": "C3:E1D8",
                "name": "InteractionFacingRemapAndResultTables",
                "classification": "raw-or-named-data",
                "source_expectation": "table data; consumer notes exist, but final field names remain cautious",
                "evidence": [
                    "notes/interaction-result-classes.md:18",
                    "notes/interaction-result-consumers.md:106",
                    "notes/c3-late-interaction-table-contracts.md",
                ],
                "note": "The first eight class-1 remap words are promoted; this adjacent table tail remains cautious.",
            },
            {
                "start": "C3:E1D8",
                "end": "C3:E1E0",
                "name": "MapEntityPlacementDirectionParamTable",
                "classification": "contract-backed-data",
                "source_expectation": "rom-table contract MAP_ENTITY_PLACEMENT_DIRECTION_PARAM_TABLE",
                "evidence": ["notes/c3-map-movement-parameter-table-e1d8-e240.md:37"],
                "note": "C0 entity placement/update path reads direction-like parameter words from this prefix.",
            },
            {
                "start": "C3:E1E0",
                "end": "C3:E200",
                "name": "MapEntityPlacementDirectionParamTable_Page1",
                "classification": "contract-backed-data",
                "source_expectation": "rom-table contract MAP_ENTITY_PLACEMENT_DIRECTION_PARAM_TABLE_PAGE1",
                "evidence": ["notes/c3-map-movement-parameter-table-e1d8-e240.md:45"],
                "note": "Second page of C0 entity placement/update direction-like parameter words.",
            },
            {
                "start": "C3:E200",
                "end": "C3:E230",
                "name": "StagedMovementDirectionAndSubtileOffsetTables",
                "classification": "contract-backed-data",
                "source_expectation": "rom-table contracts for staged movement direction/subtile offsets",
                "evidence": ["notes/c3-map-movement-parameter-table-e1d8-e240.md:49"],
                "note": "Primary/alternate direction parameter and 8-pixel subtile offset sets.",
            },
            {
                "start": "C3:E230",
                "end": "C3:E250",
                "name": "DoorCandidateDirectionOffsetTables",
                "classification": "contract-backed-data",
                "source_expectation": "rom-table contracts DOOR_CANDIDATE_DIRECTION_OFFSET_X/Y",
                "evidence": [
                    "notes/c3-map-movement-parameter-table-e1d8-e240.md:52",
                    "notes/c3-late-interaction-table-contracts.md",
                ],
                "note": "Coarse-cell X/Y direction offset tables for C4:334A door candidate probing.",
            },
            {
                "start": "C3:E250",
                "end": "C3:E3F8",
                "name": "FileSelectOrNameEntryCharacterSpriteData",
                "classification": "raw-or-named-data",
                "source_expectation": "sprite/OAM-like data; preserve until exact UI consumer is pinned",
                "evidence": ["refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Routine_Macros_EB.asm:45136"],
                "note": "Legacy comment says this block is related to file select; later comments connect nearby data to name-entry character sprites.",
            },
            {
                "start": "C3:E3F8",
                "end": "C3:E406",
                "name": "MenuCursorTilePrefixTable",
                "classification": "contract-backed-data",
                "source_expectation": "rom-table contract MENU_CURSOR_TILE_PREFIX_TABLE",
                "evidence": ["notes/c3-menu-cursor-tile-data-e3f8-e450.md:25"],
                "note": "Seven tile/attribute words adjacent to the animated menu cursor tables.",
            },
            {
                "start": "C3:E406",
                "end": "C3:E40E",
                "name": "AnimatedMenuCursorPointRightTiles",
                "classification": "contract-backed-data",
                "source_expectation": "rom-table contract ANIMATED_MENU_CURSOR_POINT_RIGHT_TILES",
                "evidence": ["notes/c3-menu-cursor-tile-data-e3f8-e450.md:35"],
                "note": "Legacy right-pointing animated menu cursor tile run.",
            },
            {
                "start": "C3:E40E",
                "end": "C3:E416",
                "name": "TitleNameBufferCursorTileRun",
                "classification": "contract-backed-data",
                "source_expectation": "rom-table contract TITLE_NAME_BUFFER_CURSOR_TILE_RUN",
                "evidence": ["notes/c3-menu-cursor-tile-data-e3f8-e450.md:38"],
                "note": "Four title/name buffer cursor tile words copied by the C2 title/name buffer helper.",
            },
            {
                "start": "C3:E416",
                "end": "C3:E41C",
                "name": "BlinkingTriangleBaseTiles",
                "classification": "contract-backed-data",
                "source_expectation": "rom-table contract BLINKING_TRIANGLE_BASE_TILES",
                "evidence": ["notes/c3-menu-cursor-tile-data-e3f8-e450.md:42"],
                "note": "Three base/down-cursor tile words before the blinking triangle wait frames.",
            },
            {
                "start": "C3:E41C",
                "end": "C3:E43C",
                "name": "BlinkingTriangleWaitFrameTiles",
                "classification": "contract-backed-data",
                "source_expectation": "rom-table contract BLINKING_TRIANGLE_WAIT_FRAME_TILES",
                "evidence": ["notes/c3-menu-cursor-tile-data-e3f8-e450.md:42"],
                "note": "Four blinking/down-cursor tile frames.",
            },
            {
                "start": "C3:E43C",
                "end": "C3:E44C",
                "name": "BlinkingTriangleWaitFramePointerTable",
                "classification": "contract-backed-data",
                "source_expectation": "rom-table contract BLINKING_TRIANGLE_WAIT_FRAME_POINTER_TABLE",
                "evidence": ["notes/c3-menu-cursor-tile-data-e3f8-e450.md:42"],
                "note": "Long pointer table selecting the four blinking triangle wait frames.",
            },
            {
                "start": "C3:E44C",
                "end": "C3:E450",
                "name": "WindowTickTransferPreludeData",
                "classification": "contract-backed-data",
                "source_expectation": "rom-table contract WINDOW_TICK_TRANSFER_PRELUDE_WORDS",
                "evidence": ["notes/c3-menu-cursor-tile-data-e3f8-e450.md:51"],
                "note": "Decoding as code is implausible; the true routine starts at C3:E450.",
            },
        ],
    },
]


def enrich_segment(rom: bytes, segment: dict[str, Any]) -> dict[str, Any]:
    start = parse_address(segment["start"])
    end = parse_address(segment["end"])
    return {**segment, **byte_summary(rom, start, end)}


def build_manifest(rom: bytes) -> dict[str, Any]:
    groups: list[dict[str, Any]] = []
    for group in GROUPS:
        start = parse_address(group["start"])
        end = parse_address(group["end"])
        segments = [enrich_segment(rom, segment) for segment in group["segments"]]
        if segments[0]["start"] != group["start"] or segments[-1]["end"] != group["end"]:
            raise ValueError(f"{group['name']} segment endpoints do not cover group")
        for previous, current in zip(segments, segments[1:]):
            if previous["end"] != current["start"]:
                raise ValueError(f"{group['name']} segment gap between {previous['end']} and {current['start']}")
        groups.append({**group, **byte_summary(rom, start, end), "segments": segments})

    total_bytes = sum(group["size"] for group in groups)
    return {
        "schema": SCHEMA,
        "generated_by": "tools/build_c3_preserved_gap_contracts.py",
        "bank": BANK,
        "inputs": {
            "event_script_source_scaffold": "build/c3-event-script-source-scaffold.json",
            "source_data_map": "build/c3-source-data-map.json",
            "rom": "EarthBound (USA).sfc",
        },
        "summary": {
            "preserved_groups": len(groups),
            "preserved_bytes": total_bytes,
            "segments": sum(len(group["segments"]) for group in groups),
            "status": "closed-by-contract",
        },
        "groups": groups,
    }


def write_report(path: Path, manifest: dict[str, Any]) -> None:
    summary = manifest["summary"]
    lines = [
        "# C3 Preserved Gap Contracts",
        "",
        "Generated by `tools/build_c3_preserved_gap_contracts.py`.",
        "",
        "This report explains the three raw regions preserved by the C3 event/actionscript source-pilot scaffold. They are not unclaimed bytes: each region is covered by checked-in source data, refs, and a byte hash. The remaining work here is semantic polish, not bank closure.",
        "",
        "## Summary",
        "",
        f"- preserved groups: `{summary['preserved_groups']}`",
        f"- preserved bytes: `{summary['preserved_bytes']}`",
        f"- subsegments: `{summary['segments']}`",
        f"- status: `{summary['status']}`",
        "",
        "| Range | Bytes | Name | Status | SHA1 |",
        "| --- | ---: | --- | --- | --- |",
    ]
    for group in manifest["groups"]:
        lines.append(
            f"| `{group['range']}` | {group['size']} | `{group['name']}` | `{group['status']}` | `{group['sha1']}` |"
        )

    for group in manifest["groups"]:
        lines.extend(
            [
                "",
                f"## {group['range']} {group['name']}",
                "",
                group["summary"],
                "",
                "Evidence:",
            ]
        )
        lines.extend(f"- `{item}`" for item in group["evidence"])
        lines.extend(
            [
                "",
                "| Range | Bytes | Class | Name | Source expectation |",
                "| --- | ---: | --- | --- | --- |",
            ]
        )
        for segment in group["segments"]:
            lines.append(
                f"| `{segment['range']}` | {segment['size']} | `{segment['classification']}` | "
                f"`{segment['name']}` | {segment['source_expectation']} |"
            )
        lines.extend(["", "Segment notes:"])
        for segment in group["segments"]:
            evidence = ", ".join(f"`{item}`" for item in segment["evidence"])
            lines.append(f"- `{segment['range']}` `{segment['name']}`: {segment['note']} Evidence: {evidence}.")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build C3 preserved gap contracts.")
    parser.add_argument("--rom")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    rom = load_rom(find_rom(args.rom))
    manifest = build_manifest(rom)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    report = args.report if args.report.is_absolute() else ROOT / args.report
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_report(report, manifest)
    print(
        f"wrote {output.relative_to(ROOT).as_posix()} and {report.relative_to(ROOT).as_posix()}: "
        f"{manifest['summary']['preserved_groups']} groups, "
        f"{manifest['summary']['segments']} segments, "
        f"{manifest['summary']['preserved_bytes']} bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
