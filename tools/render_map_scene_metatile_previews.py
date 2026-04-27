from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from rom_tools import find_rom, hirom_to_file_offset, load_rom
from snes_palette import PaletteEntry, decode_snes_bgr555_palette


ROOT = Path(__file__).resolve().parent.parent
REFS = ROOT / "refs" / "eb-decompile-4ef92"
DEFAULT_MAP_TILES = REFS / "map_tiles.map"
DEFAULT_TILESET_DIR = REFS / "Tilesets"
DEFAULT_CONTRACT = ROOT / "notes" / "map-scene-composition-contract.json"
DEFAULT_PALETTE_MANIFEST = ROOT / "asset-manifests" / "bank-da-assets.json"
DEFAULT_OUT_DIR = ROOT / "build" / "map-scene-metatile-previews"
DEFAULT_COLOR_OUT_DIR = ROOT / "build" / "map-scene-palette-previews"
MAP_TILE_GRID_WIDTH = 320
MAP_TILE_GRID_HEIGHT = 256
SECTOR_TILE_WIDTH = 8
SECTOR_TILE_HEIGHT = 8
METATILE_CELLS_PER_SIDE = 4
TILE_SIDE = 8
SECTOR_PIXEL_WIDTH = SECTOR_TILE_WIDTH * METATILE_CELLS_PER_SIDE * TILE_SIDE
SECTOR_PIXEL_HEIGHT = SECTOR_TILE_HEIGHT * METATILE_CELLS_PER_SIDE * TILE_SIDE
MAP_PALETTE_VARIANT_BYTES = 192
MAP_PALETTE_VARIANT_COLORS = MAP_PALETTE_VARIANT_BYTES // 2
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
    parser.add_argument(
        "--color-palette",
        action="store_true",
        help="Render RGB previews from bank DA map palette assets instead of grayscale indices.",
    )
    parser.add_argument("--palette-manifest", default=str(DEFAULT_PALETTE_MANIFEST))
    parser.add_argument("--rom", help="EarthBound US ROM path for --color-palette mode.")
    parser.add_argument(
        "--palette-subpalette-offset",
        type=int,
        default=-2,
        help=(
            "Offset applied to descriptor palette bits before indexing the six "
            "16-color map subpalettes. Default -2 maps SNES BG descriptor "
            "palettes 2-7 to the six bank DA map subpalettes."
        ),
    )
    parser.add_argument(
        "--palette-overflow-rgb",
        default="FF00FF",
        help="Fallback RGB hex for descriptor palettes outside the 96-color map palette variant.",
    )
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
                    "palette": (descriptor_word >> 10) & 0x07,
                    "priority": 1 if descriptor_word & 0x2000 else 0,
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


def write_rgb_bmp(path: Path, width: int, height: int, pixels: bytes) -> None:
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
        row = pixels[y * width * 3 : (y + 1) * width * 3]
        for pos in range(0, len(row), 3):
            out.extend((row[pos + 2], row[pos + 1], row[pos]))
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


def scale_rgb_pixels(source: bytes, width: int, height: int, scale: int) -> tuple[int, int, bytearray]:
    if scale <= 0:
        raise ValueError("--scale must be positive")
    if scale == 1:
        return width, height, bytearray(source)
    out_width = width * scale
    out_height = height * scale
    out = bytearray(out_width * out_height * 3)
    for y in range(height):
        for x in range(width):
            source_pos = (y * width + x) * 3
            rgb = source[source_pos : source_pos + 3]
            for dy in range(scale):
                out_row = (y * scale + dy) * out_width * 3
                for dx in range(scale):
                    out_pos = out_row + (x * scale + dx) * 3
                    out[out_pos : out_pos + 3] = rgb
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


def parse_rgb(text: str) -> tuple[int, int, int]:
    value = text.strip()
    if value.startswith("#"):
        value = value[1:]
    if len(value) != 6 or re.fullmatch(r"[0-9A-Fa-f]{6}", value) is None:
        raise ValueError("--palette-overflow-rgb must be six hex digits")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def parse_cpu_range_start(text: str) -> tuple[int, int]:
    start = text.split("..", 1)[0]
    bank_text, address_text = start.split(":", 1)
    return int(bank_text, 16), int(address_text, 16)


def load_palette_sources(path: Path) -> dict[int, dict[str, Any]]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    sources: dict[int, dict[str, Any]] = {}
    for asset in manifest["assets"]:
        title = str(asset["title"])
        if not title.startswith("MAP_DATA_PALETTE_"):
            continue
        palette_id = int(title.rsplit("_", 1)[1])
        sources[palette_id] = asset
    return sources


def load_palette_variant(
    tileset_id: int,
    palette_id: int,
    palette_sources: dict[int, dict[str, Any]],
    rom_data: bytes,
) -> list[PaletteEntry]:
    source = palette_sources.get(tileset_id)
    if source is None:
        raise ValueError(f"No MAP_DATA_PALETTE_{tileset_id} source in palette manifest")
    source_info = source["source"]
    bank, address = parse_cpu_range_start(str(source_info["range"]))
    offset = hirom_to_file_offset(bank, address, len(rom_data))
    if offset is None:
        raise ValueError(f"{source_info['range']} does not map to ROM data")
    byte_count = int(source_info["bytes"])
    variant_count = byte_count // MAP_PALETTE_VARIANT_BYTES
    if byte_count % MAP_PALETTE_VARIANT_BYTES != 0:
        raise ValueError(f"MAP_DATA_PALETTE_{tileset_id} size is not a multiple of 192 bytes")
    if not 0 <= palette_id < variant_count:
        raise ValueError(
            f"Palette variant {palette_id} is outside MAP_DATA_PALETTE_{tileset_id} "
            f"variant count {variant_count}"
        )
    variant_offset = offset + palette_id * MAP_PALETTE_VARIANT_BYTES
    return decode_snes_bgr555_palette(
        rom_data,
        offset=variant_offset,
        count=MAP_PALETTE_VARIANT_COLORS,
    )


def draw_color_tile(
    pixels: bytearray,
    tile_pixels: list[int],
    dest_x: int,
    dest_y: int,
    hflip: bool,
    vflip: bool,
    descriptor_palette: int,
    palette_entries: list[PaletteEntry],
    palette_subpalette_offset: int,
    overflow_rgb: tuple[int, int, int],
) -> int:
    overflow_pixels = 0
    subpalette = descriptor_palette + palette_subpalette_offset
    for y in range(TILE_SIDE):
        src_y = TILE_SIDE - 1 - y if vflip else y
        for x in range(TILE_SIDE):
            src_x = TILE_SIDE - 1 - x if hflip else x
            color_index = tile_pixels[src_y * TILE_SIDE + src_x]
            palette_index = subpalette * 16 + color_index
            if 0 <= palette_index < len(palette_entries):
                entry = palette_entries[palette_index]
                rgb = (entry.red8, entry.green8, entry.blue8)
            else:
                rgb = overflow_rgb
                overflow_pixels += 1
            pos = ((dest_y + y) * SECTOR_PIXEL_WIDTH + dest_x + x) * 3
            pixels[pos : pos + 3] = bytes(rgb)
    return overflow_pixels


def render_scene(
    scene: dict[str, Any],
    map_tiles: list[list[int]],
    tileset_cache: dict[int, tuple[list[list[int]], list[list[dict[str, int]]]]],
    tileset_dir: Path,
    out_dir: Path,
    scale: int,
    palette_cache: dict[tuple[int, int], list[PaletteEntry]] | None = None,
    palette_sources: dict[int, dict[str, Any]] | None = None,
    rom_data: bytes | None = None,
    palette_subpalette_offset: int = 0,
    overflow_rgb: tuple[int, int, int] = (255, 0, 255),
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
    color_mode = palette_cache is not None
    pixels = bytearray(SECTOR_PIXEL_WIDTH * SECTOR_PIXEL_HEIGHT * (3 if color_mode else 1))
    attribute_values: set[int] = set()
    descriptor_palette_counts: dict[int, int] = {}
    palette_overflow_pixels = 0
    palette_id = int(scene["palette_dependency"]["palette_id"])
    palette_entries: list[PaletteEntry] | None = None
    if color_mode:
        if palette_sources is None or rom_data is None:
            raise ValueError("Palette sources and ROM data are required in color mode")
        cache_key = (tileset_id, palette_id)
        if cache_key not in palette_cache:
            palette_cache[cache_key] = load_palette_variant(tileset_id, palette_id, palette_sources, rom_data)
        palette_entries = palette_cache[cache_key]
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
                descriptor_palette = int(cell["palette"])
                descriptor_palette_counts[descriptor_palette] = descriptor_palette_counts.get(descriptor_palette, 0) + 64
                if color_mode:
                    assert palette_entries is not None
                    palette_overflow_pixels += draw_color_tile(
                        pixels,
                        tile_pixels[cell["tile_index"]],
                        metatile_dest_x + cell_x * TILE_SIDE,
                        metatile_dest_y + cell_y * TILE_SIDE,
                        bool(cell["hflip"]),
                        bool(cell["vflip"]),
                        descriptor_palette,
                        palette_entries,
                        palette_subpalette_offset,
                        overflow_rgb,
                    )
                else:
                    draw_tile(
                        pixels,
                        tile_pixels[cell["tile_index"]],
                        metatile_dest_x + cell_x * TILE_SIDE,
                        metatile_dest_y + cell_y * TILE_SIDE,
                        bool(cell["hflip"]),
                        bool(cell["vflip"]),
                    )
    if color_mode:
        width, height, out_pixels = scale_rgb_pixels(pixels, SECTOR_PIXEL_WIDTH, SECTOR_PIXEL_HEIGHT, scale)
    else:
        width, height, out_pixels = scale_pixels(pixels, SECTOR_PIXEL_WIDTH, SECTOR_PIXEL_HEIGHT, scale)
    scene_id = str(scene["scene_id"])
    if color_mode:
        out_path = out_dir / f"{scene_id}_tileset_{tileset_id:02d}_palette_{palette_id:02d}.bmp"
        write_rgb_bmp(out_path, width, height, out_pixels)
    else:
        out_path = out_dir / f"{scene_id}_tileset_{tileset_id:02d}.bmp"
        write_bmp(out_path, width, height, out_pixels)
    return {
        "scene_id": scene_id,
        "sector": sector,
        "tileset_id": tileset_id,
        "palette_id": palette_id,
        "output": rel(out_path),
        "width": width,
        "height": height,
        "scale": scale,
        "render_mode": "palette_rgb" if color_mode else "grayscale_index",
        "source_shape": {"width": SECTOR_PIXEL_WIDTH, "height": SECTOR_PIXEL_HEIGHT},
        "attribute_values": [f"0x{value:02X}" for value in sorted(attribute_values)],
        "descriptor_palette_pixel_counts": [
            {"descriptor_palette": key, "pixel_count": value}
            for key, value in sorted(descriptor_palette_counts.items())
        ],
        "palette_subpalette_offset": palette_subpalette_offset if color_mode else None,
        "palette_color_count": len(palette_entries) if palette_entries is not None else None,
        "palette_overflow_pixels": palette_overflow_pixels if color_mode else None,
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
    if args.color_palette and out_dir == DEFAULT_OUT_DIR:
        out_dir = DEFAULT_COLOR_OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    tileset_cache: dict[int, tuple[list[list[int]], list[list[dict[str, int]]]]] = {}
    palette_sources: dict[int, dict[str, Any]] | None = None
    palette_cache: dict[tuple[int, int], list[PaletteEntry]] | None = None
    rom_data: bytes | None = None
    overflow_rgb = parse_rgb(args.palette_overflow_rgb)
    if args.color_palette:
        palette_sources = load_palette_sources(Path(args.palette_manifest))
        rom_data = load_rom(find_rom(args.rom))
        palette_cache = {}
    previews = [
        render_scene(
            scene,
            map_tiles,
            tileset_cache,
            tileset_dir,
            out_dir,
            args.scale,
            palette_cache=palette_cache,
            palette_sources=palette_sources,
            rom_data=rom_data,
            palette_subpalette_offset=args.palette_subpalette_offset,
            overflow_rgb=overflow_rgb,
        )
        for scene in select_scenes(contract, args.scene, args.limit, args.all)
    ]
    index_path = out_dir / "index.json"
    index_path.write_text(
        json.dumps(
            {
                "render_mode": "palette_rgb" if args.color_palette else "grayscale_index",
                "palette_subpalette_offset": args.palette_subpalette_offset if args.color_palette else None,
                "palette_overflow_rgb": f"#{overflow_rgb[0]:02X}{overflow_rgb[1]:02X}{overflow_rgb[2]:02X}"
                if args.color_palette
                else None,
                "previews": previews,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(previews)} previews and {rel(index_path)}")


if __name__ == "__main__":
    main()
