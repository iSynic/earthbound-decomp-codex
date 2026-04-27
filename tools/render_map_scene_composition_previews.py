from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REFS = ROOT / "refs" / "eb-decompile-4ef92"
DEFAULT_MAP_TILES = REFS / "map_tiles.map"
DEFAULT_CONTRACT = ROOT / "notes" / "map-scene-composition-contract.json"
DEFAULT_OUT_DIR = ROOT / "build" / "map-scene-composition-previews"
MAP_TILE_GRID_WIDTH = 320
MAP_TILE_GRID_HEIGHT = 256


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render ignored grayscale preview images from map scene composition data."
    )
    parser.add_argument("--map-tiles", default=str(DEFAULT_MAP_TILES))
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--scale", type=int, default=3)
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def parse_map_tiles(path: Path) -> list[list[int]]:
    rows: list[list[int]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append([int(item, 16) for item in line.split()])
    if len(rows) != MAP_TILE_GRID_WIDTH or any(len(row) != MAP_TILE_GRID_HEIGHT for row in rows):
        raise ValueError(f"Unexpected map_tiles.map shape in {path}")
    return rows


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


def scaled_pixels(source: list[int], width: int, height: int, scale: int) -> tuple[int, int, bytearray]:
    if scale <= 0:
        raise ValueError("--scale must be positive")
    out_width = width * scale
    out_height = height * scale
    out = bytearray(out_width * out_height)
    for y in range(height):
        for x in range(width):
            value = source[y * width + x]
            for dy in range(scale):
                out_row = (y * scale + dy) * out_width
                for dx in range(scale):
                    out[out_row + x * scale + dx] = value
    return out_width, out_height, out


def render_world(map_tiles: list[list[int]], scale: int, out_dir: Path) -> dict[str, object]:
    max_tile = max(max(row) for row in map_tiles)
    source: list[int] = []
    for y in range(MAP_TILE_GRID_HEIGHT):
        for x in range(MAP_TILE_GRID_WIDTH):
            value = map_tiles[x][y]
            source.append(round((value / max_tile) * 255) if max_tile else 0)
    width, height, pixels = scaled_pixels(source, MAP_TILE_GRID_WIDTH, MAP_TILE_GRID_HEIGHT, scale)
    out_path = out_dir / "world_map_tile_ids.bmp"
    write_bmp(out_path, width, height, pixels)
    return {
        "id": "world_map_tile_ids",
        "output": rel(out_path),
        "width": width,
        "height": height,
        "scale": scale,
        "source_shape": {"width": MAP_TILE_GRID_WIDTH, "height": MAP_TILE_GRID_HEIGHT},
    }


def render_tileset_status(contract: dict[str, object], scale: int, out_dir: Path) -> dict[str, object]:
    scenes = contract["scenes"]
    width = 40
    height = 32
    source = [0] * (width * height)
    for scene in scenes:
        sector = scene["sector"]
        x = int(sector["x"])
        y = int(sector["y"])
        status = scene["tileset_dependency"]["direct_contract_status"]
        source[y * width + x] = 220 if status == "direct_fts_contracts_present" else 80
    out_width, out_height, pixels = scaled_pixels(source, width, height, scale * 8)
    out_path = out_dir / "sector_tileset_contract_status.bmp"
    write_bmp(out_path, out_width, out_height, pixels)
    return {
        "id": "sector_tileset_contract_status",
        "output": rel(out_path),
        "width": out_width,
        "height": out_height,
        "scale": scale * 8,
        "legend": {
            "220": "direct .fts contracts present",
            "80": "palette settings only",
        },
    }


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    map_tiles = parse_map_tiles(Path(args.map_tiles))
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    previews = [
        render_world(map_tiles, args.scale, out_dir),
        render_tileset_status(contract, args.scale, out_dir),
    ]
    index_path = out_dir / "index.json"
    index_path.write_text(json.dumps({"previews": previews}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {len(previews)} previews and {rel(index_path)}")


if __name__ == "__main__":
    main()
