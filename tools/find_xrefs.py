from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from typing import Iterable

from rom_tools import canonical_bank_for_file_offset, find_rom, load_rom

CONTROL_FLOW_SAME_BANK = {
    0x20: "JSR",
    0x4C: "JMP",
}

CONTROL_FLOW_LONG = {
    0x22: "JSL",
    0x5C: "JML",
}

ABS_READ = {
    0x0D: "ORA",
    0x2C: "BIT",
    0x2D: "AND",
    0x4D: "EOR",
    0x6D: "ADC",
    0xAC: "LDY",
    0xAD: "LDA",
    0xAE: "LDX",
    0xCC: "CPY",
    0xCD: "CMP",
    0xEC: "CPX",
    0xED: "SBC",
}

ABS_WRITE = {
    0x8C: "STY",
    0x8D: "STA",
    0x8E: "STX",
    0x9C: "STZ",
}

ABS_MODIFY = {
    0x0C: "TSB",
    0x1C: "TRB",
    0x0E: "ASL",
    0x2E: "ROL",
    0x4E: "LSR",
    0x6E: "ROR",
    0xCE: "DEC",
    0xEE: "INC",
}

ABS_X_READ = {
    0x1D: "ORA",
    0x3D: "AND",
    0x5D: "EOR",
    0x7D: "ADC",
    0xBC: "LDY",
    0xBD: "LDA",
    0xDD: "CMP",
    0xFD: "SBC",
}

ABS_X_WRITE = {
    0x9D: "STA",
    0x9E: "STZ",
}

ABS_X_MODIFY = {
    0x1E: "ASL",
    0x3E: "ROL",
    0x5E: "LSR",
    0x7E: "ROR",
    0xDE: "DEC",
    0xFE: "INC",
}

ABS_Y_READ = {
    0x19: "ORA",
    0x39: "AND",
    0x59: "EOR",
    0x79: "ADC",
    0xB9: "LDA",
    0xBE: "LDX",
    0xD9: "CMP",
    0xF9: "SBC",
}

ABS_Y_WRITE = {
    0x99: "STA",
}

LONG_READ = {
    0x0F: "ORA",
    0x2F: "AND",
    0x4F: "EOR",
    0x6F: "ADC",
    0xAF: "LDA",
    0xCF: "CMP",
    0xEF: "SBC",
}

LONG_WRITE = {
    0x8F: "STA",
}

LONG_X_READ = {
    0x1F: "ORA",
    0x3F: "AND",
    0x5F: "EOR",
    0x7F: "ADC",
    0xBF: "LDA",
    0xDF: "CMP",
    0xFF: "SBC",
}

LONG_X_WRITE = {
    0x9F: "STA",
}


@dataclass(frozen=True)
class Target:
    raw: str
    has_bank: bool
    bank: int | None
    address: int
    long_address: int | None
    inferred_kind: str


@dataclass(frozen=True)
class Hit:
    file_offset: int
    source_bank: int
    source_address: int
    mnemonic: str
    category: str
    operand_long: int | None
    operand_word: int | None
    detail: str

    @property
    def source_cpu(self) -> str:
        return f"{self.source_bank:02X}:{self.source_address:04X}"


@dataclass(frozen=True)
class RawPatternHit:
    file_offset: int
    cpu_address: str


SECTION_ORDER = [
    "control_flow",
    "memory_read",
    "memory_write",
    "memory_modify",
    "raw_ptr24",
    "raw_word",
]

SECTION_TITLES = {
    "control_flow": "Direct control-flow references",
    "memory_read": "Likely memory reads",
    "memory_write": "Likely memory writes",
    "memory_modify": "Likely read/modify/write accesses",
    "raw_ptr24": "Raw 24-bit pointer hits",
    "raw_word": "Raw 16-bit word hits",
}


def parse_target(text: str) -> Target:
    cleaned = text.strip().upper()

    bank_addr = re.fullmatch(r"([0-9A-F]{2}):([0-9A-F]{4})", cleaned)
    if bank_addr:
        bank = int(bank_addr.group(1), 16)
        address = int(bank_addr.group(2), 16)
        long_address = (bank << 16) | address
        inferred_kind = "memory" if bank in (0x7E, 0x7F) else "code"
        return Target(
            raw=text,
            has_bank=True,
            bank=bank,
            address=address,
            long_address=long_address,
            inferred_kind=inferred_kind,
        )

    long_addr = re.fullmatch(r"([0-9A-F]{6})", cleaned)
    if long_addr:
        long_address = int(long_addr.group(1), 16)
        bank = (long_address >> 16) & 0xFF
        address = long_address & 0xFFFF
        inferred_kind = "memory" if bank in (0x7E, 0x7F) else "code"
        return Target(
            raw=text,
            has_bank=True,
            bank=bank,
            address=address,
            long_address=long_address,
            inferred_kind=inferred_kind,
        )

    word = re.fullmatch(r"([0-9A-F]{4})", cleaned)
    if word:
        return Target(
            raw=text,
            has_bank=False,
            bank=None,
            address=int(word.group(1), 16),
            long_address=None,
            inferred_kind="memory",
        )

    raise argparse.ArgumentTypeError(
        "target must look like C1:8607, C18607, or 7440"
    )


def read_u16_le(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def read_u24_le(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8) | (data[offset + 2] << 16)


def file_offset_to_cpu(file_offset: int) -> tuple[int, int]:
    return canonical_bank_for_file_offset(file_offset), file_offset & 0xFFFF


def format_long_address(long_address: int) -> str:
    return f"{(long_address >> 16) & 0xFF:02X}:{long_address & 0xFFFF:04X}"


def format_word_address(address: int) -> str:
    return f"${address:04X}"


def bytes_preview(data: bytes, offset: int, count: int) -> str:
    snippet = data[offset : offset + count]
    return " ".join(f"{byte:02X}" for byte in snippet)


def iter_pattern_hits(data: bytes, pattern: bytes) -> Iterable[int]:
    start = 0
    while True:
        offset = data.find(pattern, start)
        if offset == -1:
            return
        yield offset
        start = offset + 1


def matches_long_target(operand_long: int, target: Target) -> bool:
    return target.long_address is not None and operand_long == target.long_address


def matches_word_target(operand_word: int, operand_bank: int | None, target: Target) -> bool:
    if operand_word != target.address:
        return False
    if not target.has_bank:
        return True
    return operand_bank == target.bank


def should_include_long_memory_bank(target: Target, operand_bank: int) -> bool:
    if target.has_bank:
        return operand_bank == target.bank
    return operand_bank in (0x7E, 0x7F)


def scan_control_flow(data: bytes, target: Target) -> list[Hit]:
    hits: list[Hit] = []
    for offset in range(len(data) - 3):
        source_bank, source_address = file_offset_to_cpu(offset)
        opcode = data[offset]

        if opcode in CONTROL_FLOW_SAME_BANK:
            operand_word = read_u16_le(data, offset + 1)
            if target.has_bank and target.bank == source_bank and operand_word == target.address:
                hits.append(
                    Hit(
                        file_offset=offset,
                        source_bank=source_bank,
                        source_address=source_address,
                        mnemonic=CONTROL_FLOW_SAME_BANK[opcode],
                        category="control_flow",
                        operand_long=(source_bank << 16) | operand_word,
                        operand_word=operand_word,
                        detail=bytes_preview(data, offset, 3),
                    )
                )

        if opcode in CONTROL_FLOW_LONG:
            operand_long = read_u24_le(data, offset + 1)
            if matches_long_target(operand_long, target):
                hits.append(
                    Hit(
                        file_offset=offset,
                        source_bank=source_bank,
                        source_address=source_address,
                        mnemonic=CONTROL_FLOW_LONG[opcode],
                        category="control_flow",
                        operand_long=operand_long,
                        operand_word=operand_long & 0xFFFF,
                        detail=bytes_preview(data, offset, 4),
                    )
                )

    return hits


def scan_memory_accesses(data: bytes, target: Target) -> list[Hit]:
    hits: list[Hit] = []

    abs_maps = [
        (ABS_READ, "memory_read", "abs", 3),
        (ABS_WRITE, "memory_write", "abs", 3),
        (ABS_MODIFY, "memory_modify", "abs", 3),
        (ABS_X_READ, "memory_read", "abs,X", 3),
        (ABS_X_WRITE, "memory_write", "abs,X", 3),
        (ABS_X_MODIFY, "memory_modify", "abs,X", 3),
        (ABS_Y_READ, "memory_read", "abs,Y", 3),
        (ABS_Y_WRITE, "memory_write", "abs,Y", 3),
    ]

    long_maps = [
        (LONG_READ, "memory_read", "long", 4),
        (LONG_WRITE, "memory_write", "long", 4),
        (LONG_X_READ, "memory_read", "long,X", 4),
        (LONG_X_WRITE, "memory_write", "long,X", 4),
    ]

    for offset in range(len(data) - 4):
        source_bank, source_address = file_offset_to_cpu(offset)
        opcode = data[offset]

        for mapping, category, mode, width in abs_maps:
            mnemonic = mapping.get(opcode)
            if mnemonic is None:
                continue
            operand_word = read_u16_le(data, offset + 1)
            if matches_word_target(operand_word, None, target):
                hits.append(
                    Hit(
                        file_offset=offset,
                        source_bank=source_bank,
                        source_address=source_address,
                        mnemonic=f"{mnemonic} {mode}",
                        category=category,
                        operand_long=None,
                        operand_word=operand_word,
                        detail=bytes_preview(data, offset, width),
                    )
                )

        for mapping, category, mode, width in long_maps:
            mnemonic = mapping.get(opcode)
            if mnemonic is None:
                continue
            operand_long = read_u24_le(data, offset + 1)
            operand_bank = (operand_long >> 16) & 0xFF
            operand_word = operand_long & 0xFFFF
            if not should_include_long_memory_bank(target, operand_bank):
                continue
            if operand_word != target.address:
                continue
            hits.append(
                Hit(
                    file_offset=offset,
                    source_bank=source_bank,
                    source_address=source_address,
                    mnemonic=f"{mnemonic} {mode}",
                    category=category,
                    operand_long=operand_long,
                    operand_word=operand_word,
                    detail=bytes_preview(data, offset, width),
                )
            )

    return hits


def scan_raw_hits(data: bytes, target: Target, include_word_hits: bool) -> dict[str, list[RawPatternHit]]:
    sections: dict[str, list[RawPatternHit]] = {
        "raw_ptr24": [],
        "raw_word": [],
    }

    if target.long_address is not None:
        pattern = bytes(
            (
                target.long_address & 0xFF,
                (target.long_address >> 8) & 0xFF,
                (target.long_address >> 16) & 0xFF,
            )
        )
        for offset in iter_pattern_hits(data, pattern):
            cpu_bank, cpu_address = file_offset_to_cpu(offset)
            sections["raw_ptr24"].append(
                RawPatternHit(
                    file_offset=offset,
                    cpu_address=f"{cpu_bank:02X}:{cpu_address:04X}",
                )
            )

    if include_word_hits:
        pattern = bytes((target.address & 0xFF, (target.address >> 8) & 0xFF))
        for offset in iter_pattern_hits(data, pattern):
            cpu_bank, cpu_address = file_offset_to_cpu(offset)
            sections["raw_word"].append(
                RawPatternHit(
                    file_offset=offset,
                    cpu_address=f"{cpu_bank:02X}:{cpu_address:04X}",
                )
            )

    return sections


def render_hit(hit: Hit) -> str:
    if hit.operand_long is not None:
        operand = format_long_address(hit.operand_long)
    elif hit.operand_word is not None:
        operand = format_word_address(hit.operand_word)
    else:
        operand = "<none>"
    return (
        f"  {hit.source_cpu}  {hit.mnemonic:<12} -> {operand}"
        f"  [file 0x{hit.file_offset:06X}; {hit.detail}]"
    )


def render_raw_hit(hit: RawPatternHit) -> str:
    return f"  {hit.cpu_address}  [file 0x{hit.file_offset:06X}]"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Scan the EarthBound ROM for direct routine calls, likely memory accesses, "
            "and raw pointer/word hits for a target address."
        )
    )
    parser.add_argument("target", type=parse_target, help="target like C1:8607, C18607, or 7440")
    parser.add_argument("--rom", help="path to the ROM; defaults to workspace autodetect")
    parser.add_argument(
        "--kind",
        choices=("auto", "code", "memory"),
        default="auto",
        help="force code-style or memory-style scanning; default infers from the target",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=40,
        help="maximum lines to print per section",
    )
    parser.add_argument(
        "--no-raw",
        action="store_true",
        help="skip raw pointer/word pattern sections",
    )
    parser.add_argument(
        "--raw-word-threshold",
        type=int,
        default=200,
        help="skip raw word hits if the total count exceeds this threshold",
    )
    args = parser.parse_args()

    rom_path = find_rom(args.rom)
    rom = load_rom(rom_path)
    scan_kind = args.kind if args.kind != "auto" else args.target.inferred_kind

    print(f"ROM: {rom_path}")
    if args.target.long_address is not None:
        target_label = format_long_address(args.target.long_address)
    else:
        target_label = format_word_address(args.target.address)
    print(f"Target: {target_label} ({scan_kind})")

    grouped_hits: dict[str, list[Hit]] = {key: [] for key in SECTION_ORDER}

    if scan_kind == "code":
        grouped_hits["control_flow"] = scan_control_flow(rom, args.target)
        if not args.no_raw:
            raw_hits = scan_raw_hits(rom, args.target, include_word_hits=True)
        else:
            raw_hits = {"raw_ptr24": [], "raw_word": []}
    else:
        memory_hits = scan_memory_accesses(rom, args.target)
        for hit in memory_hits:
            grouped_hits[hit.category].append(hit)
        if not args.no_raw:
            include_word_hits = True
            raw_hits = scan_raw_hits(rom, args.target, include_word_hits=include_word_hits)
        else:
            raw_hits = {"raw_ptr24": [], "raw_word": []}

    if len(raw_hits["raw_word"]) > args.raw_word_threshold:
        print()
        print(
            f"Raw 16-bit word hits: {len(raw_hits['raw_word'])} total; skipped because this exceeds "
            f"--raw-word-threshold {args.raw_word_threshold}."
        )
        raw_hits["raw_word"] = []

    printed_any = False
    for section in SECTION_ORDER:
        section_hits: list[str] = []
        if section.startswith("raw_"):
            items = raw_hits.get(section, [])
            if items:
                section_hits = [render_raw_hit(item) for item in items[: args.limit]]
                total = len(items)
            else:
                total = 0
        else:
            items = grouped_hits.get(section, [])
            if items:
                section_hits = [render_hit(item) for item in items[: args.limit]]
                total = len(items)
            else:
                total = 0

        if total == 0:
            continue

        printed_any = True
        print()
        print(f"{SECTION_TITLES[section]}: {total}")
        for line in section_hits:
            print(line)
        if total > args.limit:
            print(f"  ... {total - args.limit} more")

    if not printed_any:
        print()
        print("No matching references found.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
