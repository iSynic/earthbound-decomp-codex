from __future__ import annotations

import binascii
import json
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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

    @property
    def hex(self) -> str:
        return f"#{self.red8:02X}{self.green8:02X}{self.blue8:02X}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "raw": f"0x{self.raw:04X}",
            "red5": self.red5,
            "green5": self.green5,
            "blue5": self.blue5,
            "red8": self.red8,
            "green8": self.green8,
            "blue8": self.blue8,
            "hex": self.hex,
        }


def expand_5_to_8(value: int) -> int:
    value &= 0x1F
    return (value << 3) | (value >> 2)


def decode_snes_bgr555_palette(data: bytes, *, offset: int = 0, count: int | None = None) -> list[PaletteEntry]:
    if offset < 0:
        raise ValueError("Palette offset must be non-negative")
    if offset > len(data):
        raise ValueError(f"Palette offset 0x{offset:X} is past data length 0x{len(data):X}")

    available = len(data) - offset
    if count is None:
        if available % 2 != 0:
            raise ValueError(f"SNES palette data must have an even byte count, got {available}")
        count = available // 2
    if count < 0:
        raise ValueError("Palette color count must be non-negative")
    if offset + count * 2 > len(data):
        raise ValueError(
            f"Palette needs {count * 2} bytes at 0x{offset:X}, "
            f"but source has 0x{len(data):X} bytes"
        )

    entries: list[PaletteEntry] = []
    for index in range(count):
        entry_offset = offset + index * 2
        raw = data[entry_offset] | (data[entry_offset + 1] << 8)
        entries.append(
            PaletteEntry(
                index=index,
                raw=raw,
                red5=raw & 0x1F,
                green5=(raw >> 5) & 0x1F,
                blue5=(raw >> 10) & 0x1F,
            )
        )
    return entries


def palette_json_payload(entries: list[PaletteEntry]) -> dict[str, Any]:
    return {
        "schema": "earthbound-decomp.snes-palette.v1",
        "format": "snes-bgr555",
        "color_count": len(entries),
        "colors": [entry.to_dict() for entry in entries],
    }


def write_palette_json(path: Path, entries: list[PaletteEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(palette_json_payload(entries), indent=2) + "\n", encoding="utf-8")


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)
    )


def write_palette_swatch_png(
    path: Path,
    entries: list[PaletteEntry],
    *,
    per_row: int = 16,
    swatch: int = 16,
) -> None:
    if per_row <= 0:
        raise ValueError("Palette swatches per row must be positive")
    if swatch <= 0:
        raise ValueError("Palette swatch size must be positive")

    rows = max(1, (len(entries) + per_row - 1) // per_row)
    width = per_row * swatch
    height = rows * swatch
    pixels = bytearray(width * height * 3)

    for index, entry in enumerate(entries):
        row = index // per_row
        col = index % per_row
        rgb = bytes((entry.red8, entry.green8, entry.blue8))
        for y in range(row * swatch, (row + 1) * swatch):
            for x in range(col * swatch, (col + 1) * swatch):
                pos = (y * width + x) * 3
                pixels[pos : pos + 3] = rgb

    raw = b"".join(
        bytes([0]) + pixels[y * width * 3 : (y + 1) * width * 3]
        for y in range(height)
    )
    payload = b"\x89PNG\r\n\x1a\n"
    payload += png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    payload += png_chunk(b"IDAT", zlib.compress(raw))
    payload += png_chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
