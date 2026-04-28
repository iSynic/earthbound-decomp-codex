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
    "C0:5E76": 4,
    "C0:64A6": 0,
    "C0:3DAA": 0,
    "C0:4EF0": 0,
    "C0:A06C": 0,
    "C0:A443": 0,
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
    "C0:A679": 1,
    "C0:A6DA": 0,
    "C0:A6E3": 0,
    "C0:A82F": 0,
    "C0:A841": 2,
    "C0:A84C": 2,
    "C0:A857": 2,
    "C0:A864": 1,
    "C0:A86F": 2,
    "C0:A88D": 4,
    "C0:A8A0": 4,
    "C0:A8C6": 0,
    "C0:A8D1": 0,
    "C0:A8DC": 0,
    "C0:A907": 1,
    "C0:A92D": 2,
    "C0:A938": 2,
    "C0:A943": 1,
    "C0:A94E": 2,
    "C0:A959": 2,
    "C0:A964": 4,
    "C0:A98B": 4,
    "C0:9F82": 0,
    "C0:9FBB": 2,
    "C0:9451": 0,
    "C0:AA3F": 3,
    "C0:AA6E": 2,
    "C0:AAAC": 0,
    "C0:AACD": 0,
    "C0:C19B": 0,
    "C0:C251": 0,
    "C0:C4F7": 0,
    "C0:C6B6": 0,
    "C0:C7DB": 0,
    "C0:C83B": 0,
    "C0:CA4E": 0,
    "C0:CBD3": 0,
    "C0:CC11": 0,
    "C0:D15C": 0,
    "C0:D59B": 0,
    "C0:D5B0": 0,
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
    "C2:FF9A": 0,
    "C3:0100": 0,
    "C4:6C87": 0,
    "C4:6ADB": 0,
    "C4:6EF8": 0,
    "C4:0015": 0,
    "C4:0023": 0,
    "C4:240A": 0,
    "C4:248A": 0,
    "C4:681A": 0,
    "C4:68B5": 0,
    "C4:68DC": 0,
    "C4:6914": 0,
    "C4:6957": 0,
    "C4:6B37": 0,
    "C4:6C45": 0,
    "C4:6E46": 0,
    "C4:6E74": 0,
    "C4:7044": 0,
    "C4:6B0A": 0,
    "C4:7269": 0,
    "C4:7333": 0,
    "C4:7499": 0,
    "C4:7A9E": 0,
    "C4:7A6B": 0,
    "C4:7B77": 0,
    "C4:800B": 0,
    "C4:8B3B": 0,
    "C4:DD28": 0,
    "C4:DDD0": 0,
    "C4:ECE7": 0,
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
