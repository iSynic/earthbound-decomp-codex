from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TILESET_DIR = ROOT / "refs" / "eb-decompile-4ef92" / "Tilesets"
DEFAULT_OUT_DIR = ROOT / "build" / "map-fts-tile-previews"
HEX_TILE_RE = re.compile(r"^[0-9A-Fa-f]{64}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render EBDecomp .fts 64-character tile rows to ignored grayscale BMP previews."
    )
    parser.add_argument("--tileset-dir", default=str(DEFAULT_TILESET_DIR))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--tileset", type=int, action="append", help="Render only one or more tileset IDs.")
    parser.add_argument("--tiles-per-row", type=int, default=32)
    parser.add_argument("--scale", type=int, default=2)
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def extract_tile_rows(path: Path) -> list[str]:
    rows: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line:
            continue
        if len(line) == 64 and HEX_TILE_RE.fullmatch(line) is not None:
            rows.append(line.lower())
            continue
        if rows:
            break
    if len(rows) != 1024:
        raise ValueError(f"{path} has {len(rows)} 64-character tile rows, expected 1024")
    return rows


def render_rows(rows: list[str], tiles_per_row: int, scale: int) -> tuple[int, int, bytearray]:
    if tiles_per_row <= 0:
        raise ValueError("--tiles-per-row must be positive")
    if scale <= 0:
        raise ValueError("--scale must be positive")
    palette = [0, 24, 48, 72, 96, 120, 144, 168, 184, 200, 216, 224, 232, 240, 248, 255]
    tile_rows = (len(rows) + tiles_per_row - 1) // tiles_per_row
    width = tiles_per_row * 8
    height = tile_rows * 8
    pixels = bytearray(width * height)
    for tile_index, row_text in enumerate(rows):
        tx = (tile_index % tiles_per_row) * 8
        ty = (tile_index // tiles_per_row) * 8
        for offset, char in enumerate(row_text):
            x = offset % 8
            y = offset // 8
            pixels[(ty + y) * width + tx + x] = palette[int(char, 16)]

    if scale == 1:
        return width, height, pixels
    scaled_width = width * scale
    scaled_height = height * scale
    scaled = bytearray(scaled_width * scaled_height)
    for y in range(height):
        for x in range(width):
            value = pixels[y * width + x]
            for dy in range(scale):
                out_row = (y * scale + dy) * scaled_width
                for dx in range(scale):
                    scaled[out_row + x * scale + dx] = value
    return scaled_width, scaled_height, scaled


def write_bmp(path: Path, width: int, height: int, pixels: bytes) -> None:
    row_stride = (width * 3 + 3) & ~3
    pixel_data_size = row_stride * height
    file_size = 14 + 40 + pixel_data_size
    out = bytearray()
    out.extend(b"BM")
    out.extend(file_size.to_bytes(4, "little"))
    out.extend((0).to_bytes(4, "little"))
    out.extend((14 + 40).to_bytes(4, "little"))
    out.extend((40).to_bytes(4, "little"))
    out.extend(width.to_bytes(4, "little", signed=True))
    out.extend(height.to_bytes(4, "little", signed=True))
    out.extend((1).to_bytes(2, "little"))
    out.extend((24).to_bytes(2, "little"))
    out.extend((0).to_bytes(4, "little"))
    out.extend(pixel_data_size.to_bytes(4, "little"))
    out.extend((2835).to_bytes(4, "little", signed=True))
    out.extend((2835).to_bytes(4, "little", signed=True))
    out.extend((0).to_bytes(4, "little"))
    out.extend((0).to_bytes(4, "little"))
    pad = bytes(row_stride - width * 3)
    for y in range(height - 1, -1, -1):
        row = pixels[y * width : (y + 1) * width]
        for value in row:
            out.extend((value, value, value))
        out.extend(pad)
    path.write_bytes(out)


def render_file(path: Path, out_dir: Path, tiles_per_row: int, scale: int) -> dict[str, Any]:
    match = re.fullmatch(r"(\d{2})\.fts", path.name)
    tileset_id = int(match.group(1)) if match else None
    rows = extract_tile_rows(path)
    width, height, pixels = render_rows(rows, tiles_per_row=tiles_per_row, scale=scale)
    out_path = out_dir / f"tileset_{tileset_id:02d}_tile_pixels.bmp"
    write_bmp(out_path, width, height, pixels)
    return {
        "tileset_id": tileset_id,
        "source": rel(path),
        "source_sha1": hashlib.sha1(path.read_bytes()).hexdigest(),
        "tile_rows_sha1": hashlib.sha1("\n".join(rows).encode("utf-8")).hexdigest(),
        "tile_count": len(rows),
        "tiles_per_row": tiles_per_row,
        "scale": scale,
        "width": width,
        "height": height,
        "output": rel(out_path),
    }


def main() -> None:
    args = parse_args()
    tileset_dir = Path(args.tileset_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    wanted = set(args.tileset or [])
    rows: list[dict[str, Any]] = []
    for path in sorted(tileset_dir.glob("*.fts")):
        match = re.fullmatch(r"(\d{2})\.fts", path.name)
        if match is None:
            continue
        tileset_id = int(match.group(1))
        if wanted and tileset_id not in wanted:
            continue
        rows.append(render_file(path, out_dir, tiles_per_row=args.tiles_per_row, scale=args.scale))

    index_path = out_dir / "index.json"
    index_path.write_text(json.dumps({"previews": rows}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} previews and {rel(index_path)}")


if __name__ == "__main__":
    main()
