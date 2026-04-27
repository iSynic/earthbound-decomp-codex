from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
REFS = ROOT / "refs" / "eb-decompile-4ef92"
DEFAULT_MAP_TILES = REFS / "map_tiles.map"
DEFAULT_TILESET_DIR = REFS / "Tilesets"
DEFAULT_CONTRACT = ROOT / "notes" / "map-scene-composition-contract.json"
DEFAULT_OUT_DIR = ROOT / "build" / "map-scene-metatile-previews"
MAP_TILE_GRID_WIDTH = 320
MAP_TILE_GRID_HEIGHT = 256
SECTOR_TILE_WIDTH = 8
SECTOR_TILE_HEIGHT = 8
METATILE_CELLS_PER_SIDE = 4
TILE_SIDE = 8
SECTOR_PIXEL_WIDTH = SECTOR_TILE_WIDTH * METATILE_CELLS_PER_SIDE * TILE_SIDE
SECTOR_PIXEL_HEIGHT = SECTOR_TILE_HEIGHT * METATILE_CELLS_PER_SIDE * TILE_SIDE
HEX_TILE_RE = re.compile(r"^[0-9A-Fa-f]{64}$")
HEX_ARRANGEMENT_RE = re.compile(r"^[0-9A-Fa-f]{96}$")
GRAYSCALE = [0, 24, 48, 72, 96, 120, 144, 168, 184, 200, 216, 224, 232, 240, 248, 255]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render ignored grayscale sector previews from map scene metatile composition."
    )
    parser.add_argument("--map-tiles", default=str(DEFAULT_MAP_TILES))
    parser.add_argument("--tileset-dir", default=str(DEFAULT_TILESET_DIR))
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--scene", action="append", help="Render one or more scene IDs or numeric sector IDs.")
    parser.add_argument("--limit", type=int, default=24, help="Number of direct .fts scenes to render when --scene is omitted.")
    parser.add_argument("--all", action="store_true", help="Render every direct .fts scene.")
    parser.add_argument("--scale", type=int, default=2)
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


def sector_tile_grid(map_tiles: list[list[int]], sector_x: int, sector_y: int) -> list[list[int]]:
    start_x = sector_x * SECTOR_TILE_WIDTH
    start_y = sector_y * SECTOR_TILE_HEIGHT
    return [
        map_tiles[x][start_y : start_y + SECTOR_TILE_HEIGHT]
        for x in range(start_x, start_x + SECTOR_TILE_WIDTH)
    ]


def extract_tile_pixels(path: Path) -> list[list[int]]:
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
        raise ValueError(f"{path} has {len(rows)} tile-pixel rows, expected 1024")
    return [[int(char, 16) for char in row] for row in rows]


def extract_arrangement_records(path: Path) -> list[list[dict[str, int]]]:
    rows = [
        line.lower()
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if len(line) == 96
    ]
    if len(rows) != 1024 or any(HEX_ARRANGEMENT_RE.fullmatch(row) is None for row in rows):
        raise ValueError(f"{path} has unexpected arrangement row shape")
    records: list[list[dict[str, int]]] = []
    for row in rows:
        raw = bytes.fromhex(row)
        cells: list[dict[str, int]] = []
        for cell_index in range(16):
            offset = cell_index * 3
            descriptor_word = raw[offset] | (raw[offset + 1] << 8)
            cells.append(
                {
                    "tile_index": descriptor_word & 0x03FF,
                    "hflip": 1 if descriptor_word & 0x4000 else 0,
                    "vflip": 1 if descriptor_word & 0x8000 else 0,
                    "attribute_byte": raw[offset + 2],
                }
            )
        records.append(cells)
    return records


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


def scale_pixels(source: bytes, width: int, height: int, scale: int) -> tuple[int, int, bytearray]:
    if scale <= 0:
        raise ValueError("--scale must be positive")
    if scale == 1:
        return width, height, bytearray(source)
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


def draw_tile(
    pixels: bytearray,
    tile_pixels: list[int],
    dest_x: int,
    dest_y: int,
    hflip: bool,
    vflip: bool,
) -> None:
    for y in range(TILE_SIDE):
        src_y = TILE_SIDE - 1 - y if vflip else y
        for x in range(TILE_SIDE):
            src_x = TILE_SIDE - 1 - x if hflip else x
            value = GRAYSCALE[tile_pixels[src_y * TILE_SIDE + src_x]]
            pixels[(dest_y + y) * SECTOR_PIXEL_WIDTH + dest_x + x] = value


def render_scene(
    scene: dict[str, Any],
    map_tiles: list[list[int]],
    tileset_cache: dict[int, tuple[list[list[int]], list[list[dict[str, int]]]]],
    tileset_dir: Path,
    out_dir: Path,
    scale: int,
) -> dict[str, Any]:
    sector = scene["sector"]
    sector_x = int(sector["x"])
    sector_y = int(sector["y"])
    tileset_id = int(scene["tileset_dependency"]["tileset_id"])
    if tileset_id not in tileset_cache:
        fts_path = tileset_dir / f"{tileset_id:02d}.fts"
        tileset_cache[tileset_id] = (extract_tile_pixels(fts_path), extract_arrangement_records(fts_path))
    tile_pixels, arrangement_records = tileset_cache[tileset_id]
    grid = sector_tile_grid(map_tiles, sector_x, sector_y)
    pixels = bytearray(SECTOR_PIXEL_WIDTH * SECTOR_PIXEL_HEIGHT)
    attribute_values: set[int] = set()
    for local_x in range(SECTOR_TILE_WIDTH):
        for local_y in range(SECTOR_TILE_HEIGHT):
            metatile_id = grid[local_x][local_y]
            cells = arrangement_records[metatile_id]
            metatile_dest_x = local_x * METATILE_CELLS_PER_SIDE * TILE_SIDE
            metatile_dest_y = local_y * METATILE_CELLS_PER_SIDE * TILE_SIDE
            for cell_index, cell in enumerate(cells):
                cell_x = cell_index % METATILE_CELLS_PER_SIDE
                cell_y = cell_index // METATILE_CELLS_PER_SIDE
                attribute_values.add(cell["attribute_byte"])
                draw_tile(
                    pixels,
                    tile_pixels[cell["tile_index"]],
                    metatile_dest_x + cell_x * TILE_SIDE,
                    metatile_dest_y + cell_y * TILE_SIDE,
                    bool(cell["hflip"]),
                    bool(cell["vflip"]),
                )
    width, height, out_pixels = scale_pixels(pixels, SECTOR_PIXEL_WIDTH, SECTOR_PIXEL_HEIGHT, scale)
    scene_id = str(scene["scene_id"])
    out_path = out_dir / f"{scene_id}_tileset_{tileset_id:02d}.bmp"
    write_bmp(out_path, width, height, out_pixels)
    return {
        "scene_id": scene_id,
        "sector": sector,
        "tileset_id": tileset_id,
        "palette_id": scene["palette_dependency"]["palette_id"],
        "output": rel(out_path),
        "width": width,
        "height": height,
        "scale": scale,
        "source_shape": {"width": SECTOR_PIXEL_WIDTH, "height": SECTOR_PIXEL_HEIGHT},
        "attribute_values": [f"0x{value:02X}" for value in sorted(attribute_values)],
    }


def wanted_scene_ids(values: list[str] | None) -> set[int]:
    ids: set[int] = set()
    for value in values or []:
        if value.startswith("map_scene."):
            ids.add(int(value.rsplit(".", 1)[1]))
        else:
            ids.add(int(value, 0))
    return ids


def select_scenes(contract: dict[str, Any], scene_args: list[str] | None, limit: int, render_all: bool) -> list[dict[str, Any]]:
    direct_scenes = [
        scene
        for scene in contract["scenes"]
        if scene["tileset_dependency"]["direct_contract_status"] == "direct_fts_contracts_present"
    ]
    ids = wanted_scene_ids(scene_args)
    if ids:
        by_id = {int(scene["sector"]["linear_index"]): scene for scene in direct_scenes}
        missing = sorted(ids - set(by_id))
        if missing:
            raise ValueError(f"Requested scenes are not direct .fts scenes: {missing}")
        return [by_id[scene_id] for scene_id in sorted(ids)]
    if render_all:
        return direct_scenes
    return direct_scenes[:limit]


def main() -> None:
    args = parse_args()
    map_tiles = parse_map_tiles(Path(args.map_tiles))
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    tileset_dir = Path(args.tileset_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tileset_cache: dict[int, tuple[list[list[int]], list[list[dict[str, int]]]]] = {}
    previews = [
        render_scene(scene, map_tiles, tileset_cache, tileset_dir, out_dir, args.scale)
        for scene in select_scenes(contract, args.scene, args.limit, args.all)
    ]
    index_path = out_dir / "index.json"
    index_path.write_text(json.dumps({"previews": previews}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {len(previews)} previews and {rel(index_path)}")


if __name__ == "__main__":
    main()
