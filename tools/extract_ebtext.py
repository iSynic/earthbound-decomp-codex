from __future__ import annotations

import argparse
from dataclasses import dataclass
import re

from rom_tools import find_rom, hirom_to_file_offset, load_rom

US_EBTEXT_CHARMAP: dict[int, str] = {
    0x50: " ",
    0x51: "!",
    0x52: "&",
    0x53: "{",
    0x54: "$",
    0x55: "%",
    0x56: "}",
    0x57: "'",
    0x58: "(",
    0x59: ")",
    0x5A: "*",
    0x5B: "+",
    0x5C: ",",
    0x5D: "-",
    0x5E: ".",
    0x5F: "/",
    0x6A: ":",
    0x6B: ";",
    0x6C: "<",
    0x6D: "=",
    0x6E: ">",
    0x6F: "?",
    0x70: "@",
    0x8B: "~",
    0x8C: "^",
    0x8D: "[",
    0x8E: "]",
    0x8F: "#",
    0x90: "_",
    0xAC: "|",
}

for code in range(0x60, 0x6A):
    US_EBTEXT_CHARMAP[code] = chr(ord("0") + (code - 0x60))
for code in range(0x71, 0x8B):
    US_EBTEXT_CHARMAP[code] = chr(ord("A") + (code - 0x71))
for code in range(0x91, 0xAB):
    US_EBTEXT_CHARMAP[code] = chr(ord("a") + (code - 0x91))


@dataclass(frozen=True)
class DecodeChunk:
    snes_address: int
    file_offset: int
    data: bytes
    decoded: str
    terminated: bool


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

    raise argparse.ArgumentTypeError("address must look like C2:0998 or C20998")


def decode_ebtext_bytes(data: bytes, *, stop_at_zero: bool) -> tuple[str, bool]:
    chars: list[str] = []
    terminated = False

    for value in data:
        if stop_at_zero and value == 0x00:
            terminated = True
            break
        chars.append(US_EBTEXT_CHARMAP.get(value, f"<{value:02X}>"))

    return "".join(chars), terminated


def read_chunk(
    rom: bytes,
    start_address: int,
    *,
    length: int,
    stop_at_zero: bool,
) -> DecodeChunk:
    bank = (start_address >> 16) & 0xFF
    address = start_address & 0xFFFF
    file_offset = hirom_to_file_offset(bank, address, len(rom))
    if file_offset is None:
        raise ValueError(
            f"address {bank:02X}:{address:04X} does not map to ROM in this HiROM image"
        )

    data = rom[file_offset:file_offset + length]
    decoded, terminated = decode_ebtext_bytes(data, stop_at_zero=stop_at_zero)
    return DecodeChunk(
        snes_address=start_address,
        file_offset=file_offset,
        data=data,
        decoded=decoded,
        terminated=terminated,
    )


def render_chunk(chunk: DecodeChunk) -> str:
    bank = (chunk.snes_address >> 16) & 0xFF
    address = chunk.snes_address & 0xFFFF
    byte_text = " ".join(f"{value:02X}" for value in chunk.data)

    lines = [
        f"{bank:02X}:{address:04X} (file 0x{chunk.file_offset:06X})",
        f"bytes: {byte_text}",
        f'text: "{chunk.decoded}"',
    ]
    if chunk.terminated:
        lines.append("terminated: yes")
    return "\n".join(lines)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Decode EarthBound US text bytes from an SNES CPU address."
    )
    parser.add_argument(
        "address",
        type=parse_snes_address,
        help="SNES CPU address, for example C2:0998 or C20998",
    )
    parser.add_argument(
        "--length",
        type=int,
        default=16,
        help="Bytes to decode per chunk for fixed-length mode (default: 16)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="How many chunks to decode (default: 1)",
    )
    parser.add_argument(
        "--stride",
        type=int,
        default=None,
        help="Address distance between chunks (defaults to --length)",
    )
    parser.add_argument(
        "--until-zero",
        action="store_true",
        help="Stop each chunk at the first 0x00 byte",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=64,
        help="Maximum bytes to scan in --until-zero mode (default: 64)",
    )
    parser.add_argument(
        "--rom",
        help="Optional explicit ROM path",
    )
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()

    rom_path = find_rom(args.rom)
    rom = load_rom(rom_path)

    if args.count < 1:
        raise SystemExit("--count must be at least 1")

    if args.until_zero:
        chunk_length = args.max_length
    else:
        chunk_length = args.length

    if chunk_length < 1:
        raise SystemExit("chunk length must be at least 1")

    stride = args.stride if args.stride is not None else args.length
    if stride < 0:
        raise SystemExit("--stride must be zero or greater")

    chunks: list[DecodeChunk] = []
    for index in range(args.count):
        chunk_address = args.address + (index * stride)
        chunks.append(
            read_chunk(
                rom,
                chunk_address,
                length=chunk_length,
                stop_at_zero=args.until_zero,
            )
        )

    print(f"ROM: {rom_path}")
    print()
    for index, chunk in enumerate(chunks):
        if index:
            print()
        print(render_chunk(chunk))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
