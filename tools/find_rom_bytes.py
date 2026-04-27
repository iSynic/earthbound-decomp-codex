from __future__ import annotations

import argparse
import re

from rom_tools import canonical_bank_for_file_offset, find_rom, load_rom


def parse_snes_address(text: str) -> int:
    cleaned = text.strip().upper()
    bank_addr = re.fullmatch(r"([0-9A-F]{2}):([0-9A-F]{4})", cleaned)
    if bank_addr:
        bank = int(bank_addr.group(1), 16)
        addr = int(bank_addr.group(2), 16)
        return (bank << 16) | addr

    long_addr = re.fullmatch(r"([0-9A-F]{6})", cleaned)
    if long_addr:
        return int(long_addr.group(1), 16)

    raise argparse.ArgumentTypeError("address must look like C6:4BBF or C64BBF")


def parse_hex_bytes(text: str) -> bytes:
    cleaned = re.sub(r"[^0-9A-Fa-f]", "", text)
    if not cleaned or len(cleaned) % 2 != 0:
        raise argparse.ArgumentTypeError(
            "hex byte pattern must contain an even number of hex digits"
        )
    return bytes.fromhex(cleaned)


def format_cpu_address(file_offset: int) -> str:
    bank = canonical_bank_for_file_offset(file_offset)
    address = file_offset & 0xFFFF
    return f"{bank:02X}:{address:04X}"


def iter_matches(haystack: bytes, needle: bytes) -> list[int]:
    matches: list[int] = []
    start = 0
    while True:
        offset = haystack.find(needle, start)
        if offset == -1:
            return matches
        matches.append(offset)
        start = offset + 1


def build_patterns(args: argparse.Namespace) -> list[tuple[str, bytes]]:
    patterns: list[tuple[str, bytes]] = []

    if args.bytes is not None:
        patterns.append(("raw", parse_hex_bytes(args.bytes)))

    if args.ptr24 is not None:
        long_addr = parse_snes_address(args.ptr24)
        bank = (long_addr >> 16) & 0xFF
        address = long_addr & 0xFFFF
        patterns.append(
            (
                f"ptr24 {bank:02X}:{address:04X}",
                bytes((address & 0xFF, (address >> 8) & 0xFF, bank)),
            )
        )

    if args.word is not None:
        long_addr = parse_snes_address(args.word)
        address = long_addr & 0xFFFF
        patterns.append(
            (f"word {address:04X}", bytes((address & 0xFF, (address >> 8) & 0xFF)))
        )

    if not patterns:
        raise SystemExit("pass one of --bytes, --ptr24, or --word")

    return patterns


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find raw byte or pointer patterns inside the EarthBound ROM."
    )
    parser.add_argument("--rom", help="path to the ROM; defaults to workspace autodetect")
    parser.add_argument("--bytes", help="raw hex byte pattern, e.g. 'BF 4B C6'")
    parser.add_argument("--ptr24", help="search for a 24-bit little-endian SNES pointer")
    parser.add_argument("--word", help="search for a 16-bit little-endian word from a SNES address")
    parser.add_argument(
        "--limit", type=int, default=50, help="maximum matches to print per pattern"
    )
    args = parser.parse_args()

    rom_path = find_rom(args.rom)
    rom = load_rom(rom_path)
    patterns = build_patterns(args)

    print(f"ROM: {rom_path}")
    for label, pattern in patterns:
        print()
        print(f"Pattern ({label}): {' '.join(f'{b:02X}' for b in pattern)}")
        matches = iter_matches(rom, pattern)
        print(f"Matches: {len(matches)}")
        for file_offset in matches[: args.limit]:
            cpu_addr = format_cpu_address(file_offset)
            print(f"  file 0x{file_offset:06X} -> {cpu_addr}")
        if len(matches) > args.limit:
            print(f"  ... {len(matches) - args.limit} more")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
