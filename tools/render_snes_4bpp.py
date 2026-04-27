#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def decode_tile(tile: bytes) -> list[list[int]]:
    if len(tile) != 32:
        raise ValueError('4bpp tile must be 32 bytes')
    rows = []
    for y in range(8):
        p0 = tile[y * 2]
        p1 = tile[y * 2 + 1]
        p2 = tile[16 + y * 2]
        p3 = tile[16 + y * 2 + 1]
        row = []
        for bit in range(7, -1, -1):
            v = ((p0 >> bit) & 1) | (((p1 >> bit) & 1) << 1) | (((p2 >> bit) & 1) << 2) | (((p3 >> bit) & 1) << 3)
            row.append(v)
        rows.append(row)
    return rows


def render_4bpp(data: bytes, tiles_per_row: int = 16, scale: int = 2) -> tuple[int, int, bytearray]:
    num_tiles = len(data) // 32
    rows = (num_tiles + tiles_per_row - 1) // tiles_per_row
    width = tiles_per_row * 8
    height = rows * 8
    img = bytearray(width * height)
    palette = [0, 24, 48, 72, 96, 120, 144, 168, 184, 200, 216, 224, 232, 240, 248, 255]
    for t in range(num_tiles):
        tx = (t % tiles_per_row) * 8
        ty = (t // tiles_per_row) * 8
        tile = data[t * 32:(t + 1) * 32]
        rows8 = decode_tile(tile)
        for y, row in enumerate(rows8):
            for x, px in enumerate(row):
                img[(ty + y) * width + (tx + x)] = palette[px]
    if scale <= 1:
        return width, height, img
    sw, sh = width * scale, height * scale
    scaled = bytearray(sw * sh)
    for y in range(height):
        for x in range(width):
            v = img[y * width + x]
            for dy in range(scale):
                row_off = (y * scale + dy) * sw
                for dx in range(scale):
                    scaled[row_off + x * scale + dx] = v
    return sw, sh, scaled


def write_pgm(path: Path, width: int, height: int, pixels: bytes) -> None:
    header = f'P5\n{width} {height}\n255\n'.encode('ascii')
    path.write_bytes(header + pixels)


def write_bmp(path: Path, width: int, height: int, pixels: bytes) -> None:
    row_stride = (width * 3 + 3) & ~3
    pixel_data_size = row_stride * height
    file_size = 14 + 40 + pixel_data_size
    out = bytearray()
    out.extend(b'BM')
    out.extend(file_size.to_bytes(4, 'little'))
    out.extend((0).to_bytes(4, 'little'))
    out.extend((14 + 40).to_bytes(4, 'little'))
    out.extend((40).to_bytes(4, 'little'))
    out.extend(width.to_bytes(4, 'little', signed=True))
    out.extend(height.to_bytes(4, 'little', signed=True))
    out.extend((1).to_bytes(2, 'little'))
    out.extend((24).to_bytes(2, 'little'))
    out.extend((0).to_bytes(4, 'little'))
    out.extend(pixel_data_size.to_bytes(4, 'little'))
    out.extend((2835).to_bytes(4, 'little', signed=True))
    out.extend((2835).to_bytes(4, 'little', signed=True))
    out.extend((0).to_bytes(4, 'little'))
    out.extend((0).to_bytes(4, 'little'))
    pad = bytes(row_stride - width * 3)
    for y in range(height - 1, -1, -1):
        row = pixels[y * width:(y + 1) * width]
        for v in row:
            out.extend((v, v, v))
        out.extend(pad)
    path.write_bytes(out)


def main() -> None:
    parser = argparse.ArgumentParser(description='Render SNES 4bpp tile data to grayscale image')
    parser.add_argument('input', help='Input binary file')
    parser.add_argument('output', help='Output .pgm or .bmp file')
    parser.add_argument('--offset', type=lambda s: int(s, 0), default=0)
    parser.add_argument('--length', type=lambda s: int(s, 0), default=None)
    parser.add_argument('--tiles-per-row', type=int, default=16)
    parser.add_argument('--scale', type=int, default=2)
    args = parser.parse_args()

    data = Path(args.input).read_bytes()
    data = data[args.offset: args.offset + args.length if args.length is not None else None]
    data = data[: len(data) - (len(data) % 32)]
    width, height, pixels = render_4bpp(data, tiles_per_row=args.tiles_per_row, scale=args.scale)
    out = Path(args.output)
    if out.suffix.lower() == '.bmp':
        write_bmp(out, width, height, pixels)
    else:
        write_pgm(out, width, height, pixels)
    print(f'Wrote {out} ({width}x{height}) from {len(data)//32} tiles')


if __name__ == '__main__':
    main()
