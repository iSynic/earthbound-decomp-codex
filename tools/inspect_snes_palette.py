from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rom_tools import find_rom, load_rom, hirom_to_file_offset


@dataclass(frozen=True)
class CpuAddress:
    bank: int
    address: int

    def __str__(self) -> str:
        return f"{self.bank:02X}:{self.address:04X}"


@dataclass(frozen=True)
class PaletteEntry:
    index: int
    raw: int
    red5: int
    green5: int
    blue5: int

    @property
    def red8(self) -> int:
        return expand_5_to_8(self.red5)

    @property
    def green8(self) -> int:
        return expand_5_to_8(self.green5)

    @property
    def blue8(self) -> int:
        return expand_5_to_8(self.blue5)


@dataclass(frozen=True)
class SourceData:
    label: str
    data: bytes


def expand_5_to_8(value: int) -> int:
    return ((value & 0x1F) << 3) | ((value & 0x1F) >> 2)


def parse_int(text: str) -> int:
    return int(text, 0)


def try_parse_cpu_address(text: str) -> CpuAddress | None:
    candidate = text.strip().upper()
    if ':' in candidate:
        bank_text, addr_text = candidate.split(':', 1)
    else:
        if len(candidate) != 6:
            return None
        bank_text, addr_text = candidate[:2], candidate[2:]
    try:
        bank = int(bank_text, 16)
        address = int(addr_text, 16)
    except ValueError:
        return None
    if not 0 <= bank <= 0xFF or not 0 <= address <= 0xFFFF:
        return None
    return CpuAddress(bank, address)


def read_u16_le(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def decode_entry(raw: int, index: int) -> PaletteEntry:
    return PaletteEntry(
        index=index,
        raw=raw,
        red5=raw & 0x1F,
        green5=(raw >> 5) & 0x1F,
        blue5=(raw >> 10) & 0x1F,
    )


def load_source(spec: str, rom_path: str | None) -> SourceData:
    path = Path(spec)
    if path.is_file():
        return SourceData(label=str(path.resolve()), data=path.read_bytes())

    cpu = try_parse_cpu_address(spec)
    if cpu is None:
        raise FileNotFoundError(
            f"Source '{spec}' is neither a file path nor a CPU address like C4:2000"
        )

    rom = find_rom(rom_path)
    rom_bytes = load_rom(rom)
    file_offset = hirom_to_file_offset(cpu.bank, cpu.address, len(rom_bytes))
    if file_offset is None:
        raise ValueError(f"{cpu} does not map to ROM data")
    return SourceData(
        label=f"{cpu} -> {rom.resolve()} @ 0x{file_offset:06X}",
        data=rom_bytes[file_offset:],
    )


def iter_entries(data: bytes, offset: int, count: int, stride: int) -> Iterable[PaletteEntry]:
    for index in range(count):
        entry_offset = offset + index * stride
        if entry_offset + 2 > len(data):
            raise ValueError(
                f"entry {index} at 0x{entry_offset:X} runs past source length 0x{len(data):X}"
            )
        yield decode_entry(read_u16_le(data, entry_offset), index)


def write_ppm(path: Path, entries: list[PaletteEntry], per_row: int, swatch: int) -> None:
    if per_row <= 0:
        raise ValueError('--per-row must be positive')
    if swatch <= 0:
        raise ValueError('--swatch must be positive')
    rows = (len(entries) + per_row - 1) // per_row
    width = per_row * swatch
    height = max(1, rows) * swatch
    pixels = bytearray(width * height * 3)

    for idx, entry in enumerate(entries):
        row = idx // per_row
        col = idx % per_row
        r = entry.red8
        g = entry.green8
        b = entry.blue8
        for y in range(row * swatch, (row + 1) * swatch):
            for x in range(col * swatch, (col + 1) * swatch):
                pos = (y * width + x) * 3
                pixels[pos:pos + 3] = bytes((r, g, b))

    with path.open('wb') as fh:
        header = f"P6\n{width} {height}\n255\n".encode('ascii')
        fh.write(header)
        fh.write(pixels)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Inspect packed SNES 15-bit color words from ROM or a raw binary file.'
    )
    parser.add_argument('source', help='CPU address like C4:2000 or a raw binary file path')
    parser.add_argument('--rom', help='path to ROM file when source is a CPU address')
    parser.add_argument('--offset', type=parse_int, default=0, help='byte offset into the source (default: 0)')
    parser.add_argument('--count', type=parse_int, default=16, help='number of color entries to decode (default: 16)')
    parser.add_argument('--stride', type=parse_int, default=2, help='byte stride between entries (default: 2)')
    parser.add_argument('--compare', help='optional second source to diff against the primary source')
    parser.add_argument('--compare-offset', type=parse_int, default=0, help='byte offset into the compare source (default: 0)')
    parser.add_argument('--image-out', help='optional path for a PPM swatch preview image')
    parser.add_argument('--per-row', type=parse_int, default=16, help='swatches per row in the preview image (default: 16)')
    parser.add_argument('--swatch', type=parse_int, default=16, help='swatch size in pixels for the preview image (default: 16)')
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.offset < 0:
        parser.error('--offset must be non-negative')
    if args.compare_offset < 0:
        parser.error('--compare-offset must be non-negative')
    if args.count <= 0:
        parser.error('--count must be positive')
    if args.stride <= 0:
        parser.error('--stride must be positive')

    primary = load_source(args.source, args.rom)
    entries = list(iter_entries(primary.data, args.offset, args.count, args.stride))

    compare_entries: list[PaletteEntry] | None = None
    compare_label: str | None = None
    if args.compare:
        secondary = load_source(args.compare, args.rom)
        compare_entries = list(iter_entries(secondary.data, args.compare_offset, args.count, args.stride))
        compare_label = secondary.label

    print(f"Source: {primary.label}")
    print(f"Offset: 0x{args.offset:X}")
    print(f"Count: {args.count}")
    print(f"Stride: {args.stride}")
    if compare_label is not None:
        print(f"Compare: {compare_label}")
        print(f"Compare offset: 0x{args.compare_offset:X}")
    print()

    for entry in entries:
        line = (
            f"{entry.index:03d}: raw=0x{entry.raw:04X} "
            f"R={entry.red5:02d}/{entry.red8:03d} "
            f"G={entry.green5:02d}/{entry.green8:03d} "
            f"B={entry.blue5:02d}/{entry.blue8:03d}"
        )
        if compare_entries is not None:
            other = compare_entries[entry.index]
            line += (
                f" | dRaw={entry.raw - other.raw:+6d} "
                f"dR={entry.red5 - other.red5:+3d} "
                f"dG={entry.green5 - other.green5:+3d} "
                f"dB={entry.blue5 - other.blue5:+3d}"
            )
        print(line)

    if args.image_out:
        out_path = Path(args.image_out).expanduser().resolve()
        write_ppm(out_path, entries, args.per_row, args.swatch)
        print()
        print(f"Wrote preview: {out_path}")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
