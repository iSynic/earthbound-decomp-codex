#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

ROM_NAME = "EarthBound (USA).sfc"


def cpu_to_file(cpu: str) -> int:
    bank_s, addr_s = cpu.split(":")
    bank = int(bank_s, 16)
    addr = int(addr_s, 16)
    if bank < 0xC0:
        raise ValueError(f"Expected ROM bank >= C0, got {cpu}")
    return (bank - 0xC0) * 0x10000 + (addr & 0xFFFF)


def reverse_bits8(value: int) -> int:
    out = 0
    for _ in range(8):
        out = (out << 1) | (value & 1)
        value >>= 1
    return out


def decompress(data: bytes, src_off: int, dest_base: int = 0) -> tuple[bytes, int]:
    i = src_off
    out = bytearray()
    while True:
        control = data[i]
        i += 1
        if control == 0xFF:
            break

        if (control & 0xE0) == 0xE0:
            cmd = (control << 3) & 0xE0
            count = (((control & 0x03) << 8) | data[i]) + 1
            i += 1
        else:
            cmd = control & 0xE0
            count = (control & 0x1F) + 1

        if cmd < 0x20:
            out.extend(data[i:i + count])
            i += count
            continue

        if cmd == 0x20:
            b = data[i]
            i += 1
            out.extend([b] * count)
            continue

        if cmd == 0x40:
            lo = data[i]
            hi = data[i + 1]
            i += 2
            pair = bytes((lo, hi))
            out.extend(pair * count)
            continue

        if cmd == 0x60:
            b = data[i]
            i += 1
            for _ in range(count):
                out.append(b & 0xFF)
                b = (b + 1) & 0xFF
            continue

        # Backreference family: source offset is stored big-endian relative to dest_base.
        rel = (data[i] << 8) | data[i + 1]
        i += 2
        y = rel + dest_base
        rel_idx = y - dest_base

        if cmd == 0xA0:
            for n in range(count):
                out.append(reverse_bits8(out[rel_idx + n]))
            continue

        if cmd == 0xC0:
            for n in range(count):
                out.append(out[rel_idx - n])
            continue

        # Default negative-mode copy, used by 0x80 and extended 0xE0-like cases.
        for n in range(count):
            out.append(out[rel_idx + n])

    return bytes(out), i - src_off


def main() -> None:
    parser = argparse.ArgumentParser(description="Decompress an EarthBound C4:1A9E-format blob")
    parser.add_argument("source", help="CPU address like DF:C243")
    parser.add_argument("--length", type=int, default=96, help="How many decompressed bytes to print")
    parser.add_argument("--write", help="Optional output file path")
    args = parser.parse_args()

    rom_path = Path(__file__).resolve().parents[1] / ROM_NAME
    rom = rom_path.read_bytes()
    src_off = cpu_to_file(args.source)
    out, consumed = decompress(rom, src_off, dest_base=0xC000)

    print(f"ROM: {rom_path}")
    print(f"Source: {args.source} (file 0x{src_off:06X})")
    print(f"Compressed bytes consumed: 0x{consumed:X} ({consumed})")
    print(f"Decompressed size: 0x{len(out):X} ({len(out)})")
    print(f"First {min(args.length, len(out))} bytes:")
    print(out[:args.length].hex(" "))

    if args.write:
        out_path = Path(args.write)
        out_path.write_bytes(out)
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
