from __future__ import annotations

import argparse
import binascii
import json
import math
import struct
import zlib
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTRACT = ROOT / "notes" / "overworld-sprite-frame-contracts.json"
DEFAULT_ASSET_ROOT = ROOT / "build" / "assets"
DEFAULT_OUT = ROOT / "build" / "overworld-sprite-preview-sheets"

RGBA = tuple[int, int, int, int]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build generated overworld sprite slot preview sheets from the frame contract."
    )
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--asset-root", default=str(DEFAULT_ASSET_ROOT))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument(
        "--group-id",
        action="append",
        type=int,
        default=[],
        help="Only render one overworld sprite id. Can be passed more than once.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Render only the first N groups after filtering.",
    )
    parser.add_argument("--cell-padding", type=int, default=4)
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)
    )


def unfilter_scanline(filter_type: int, row: bytearray, previous: bytes, bpp: int) -> bytes:
    out = bytearray(row)
    for index, value in enumerate(row):
        left = out[index - bpp] if index >= bpp else 0
        up = previous[index] if previous else 0
        up_left = previous[index - bpp] if previous and index >= bpp else 0
        if filter_type == 0:
            out[index] = value
        elif filter_type == 1:
            out[index] = (value + left) & 0xFF
        elif filter_type == 2:
            out[index] = (value + up) & 0xFF
        elif filter_type == 3:
            out[index] = (value + ((left + up) // 2)) & 0xFF
        elif filter_type == 4:
            predictor = paeth(left, up, up_left)
            out[index] = (value + predictor) & 0xFF
        else:
            raise ValueError(f"Unsupported PNG filter type {filter_type}")
    return bytes(out)


def paeth(left: int, up: int, up_left: int) -> int:
    estimate = left + up - up_left
    dist_left = abs(estimate - left)
    dist_up = abs(estimate - up)
    dist_up_left = abs(estimate - up_left)
    if dist_left <= dist_up and dist_left <= dist_up_left:
        return left
    if dist_up <= dist_up_left:
        return up
    return up_left


def read_png_rgba(path: Path) -> list[list[RGBA]]:
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"Not a PNG: {path}")

    offset = 8
    width = height = bit_depth = color_type = None
    idat = bytearray()
    while offset < len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        offset += 12 + length
        if kind == b"IHDR":
            width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
                ">IIBBBBB", payload
            )
            if compression != 0 or filter_method != 0 or interlace != 0:
                raise ValueError(f"Unsupported PNG encoding: {path}")
        elif kind == b"IDAT":
            idat.extend(payload)
        elif kind == b"IEND":
            break

    if width is None or height is None or bit_depth != 8 or color_type not in {2, 6}:
        raise ValueError(f"Unsupported PNG color type in {path}")

    channels = 3 if color_type == 2 else 4
    stride = width * channels
    raw = zlib.decompress(bytes(idat))
    rows: list[list[RGBA]] = []
    previous = b""
    cursor = 0
    for _ in range(height):
        filter_type = raw[cursor]
        cursor += 1
        scanline = unfilter_scanline(
            filter_type, bytearray(raw[cursor : cursor + stride]), previous, channels
        )
        cursor += stride
        previous = scanline
        row: list[RGBA] = []
        for x in range(width):
            base = x * channels
            if channels == 3:
                row.append((scanline[base], scanline[base + 1], scanline[base + 2], 255))
            else:
                row.append(
                    (
                        scanline[base],
                        scanline[base + 1],
                        scanline[base + 2],
                        scanline[base + 3],
                    )
                )
        rows.append(row)
    return rows


def write_png_rgba(path: Path, rows: list[list[RGBA]]) -> None:
    if not rows or not rows[0]:
        raise ValueError("Cannot write an empty PNG")
    width = len(rows[0])
    height = len(rows)
    raw_rows = []
    for row in rows:
        if len(row) != width:
            raise ValueError("PNG rows have inconsistent widths")
        raw = bytearray([0])
        for r, g, b, a in row:
            raw.extend((r, g, b, a))
        raw_rows.append(bytes(raw))

    payload = b"\x89PNG\r\n\x1a\n"
    payload += png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    payload += png_chunk(b"IDAT", zlib.compress(b"".join(raw_rows)))
    payload += png_chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def blank(width: int, height: int, color: RGBA) -> list[list[RGBA]]:
    return [[color for _ in range(width)] for _ in range(height)]


def paste(dest: list[list[RGBA]], src: list[list[RGBA]], left: int, top: int) -> None:
    for y, row in enumerate(src):
        for x, pixel in enumerate(row):
            if pixel[3] == 0:
                continue
            dest[top + y][left + x] = pixel


def draw_rect(rows: list[list[RGBA]], left: int, top: int, width: int, height: int, color: RGBA) -> None:
    right = left + width - 1
    bottom = top + height - 1
    for x in range(left, left + width):
        rows[top][x] = color
        rows[bottom][x] = color
    for y in range(top, top + height):
        rows[y][left] = color
        rows[y][right] = color


def slug(text: str) -> str:
    return "".join(char.lower() if char.isalnum() else "-" for char in text).strip("-")


def group_slots_with_images(group: dict[str, Any], asset_root: Path) -> list[dict[str, Any]]:
    slots = []
    for slot in group["runtime_slots"]:
        asset = slot["resolved_asset"]
        preview = asset.get("palette_00_preview") if asset else None
        image_path = asset_root / preview if preview else None
        slots.append({**slot, "image_path": image_path})
    return slots


def border_color(flags: int) -> RGBA:
    if flags == 0:
        return (80, 80, 80, 255)
    if flags == 1:
        return (43, 135, 255, 255)
    if flags == 2:
        return (255, 170, 30, 255)
    return (220, 70, 220, 255)


def build_group_sheet(
    group: dict[str, Any], slots: list[dict[str, Any]], out_dir: Path, padding: int
) -> dict[str, Any]:
    images = []
    missing = []
    for slot in slots:
        path = slot["image_path"]
        if path and path.is_file():
            image = read_png_rgba(path)
            images.append((slot, image))
        else:
            missing.append(slot["slot_index"])

    if not images:
        return {
            "group": group["label"],
            "overworld_sprite_id": group["overworld_sprite_id"],
            "rendered": False,
            "missing_slots": missing,
        }

    image_width = max(len(image[0]) for _, image in images)
    image_height = max(len(image) for _, image in images)
    columns = min(8, max(1, len(slots)))
    rows_count = math.ceil(len(slots) / columns)
    cell_width = image_width + (padding * 2)
    cell_height = image_height + (padding * 2)
    sheet = blank(columns * cell_width, rows_count * cell_height, (22, 24, 28, 255))
    cells = []

    image_by_slot = {slot["slot_index"]: image for slot, image in images}
    for slot in slots:
        index = slot["slot_index"]
        column = index % columns
        row = index // columns
        left = column * cell_width
        top = row * cell_height
        draw_rect(sheet, left, top, cell_width, cell_height, border_color(slot["pointer_flags"]))
        image = image_by_slot.get(index)
        if image is not None:
            paste(
                sheet,
                image,
                left + padding + ((image_width - len(image[0])) // 2),
                top + padding + ((image_height - len(image)) // 2),
            )
        cells.append(
            {
                "slot_index": index,
                "direction_hint": slot.get("direction_hint"),
                "phase_hint": slot.get("phase_hint"),
                "pointer_flags": slot["pointer_flags"],
                "pointer_flag_bits": slot["pointer_flag_bits"],
                "sprite_id": slot["resolved_asset"]["sprite_id"],
                "source_range": slot["resolved_asset"]["source_range"],
                "cell": {"x": left, "y": top, "width": cell_width, "height": cell_height},
            }
        )

    filename = f"{int(group['overworld_sprite_id']):04d}-{slug(group['label'])}.png"
    out_path = out_dir / filename
    write_png_rgba(out_path, sheet)
    return {
        "group": group["label"],
        "enum_name": group["enum_name"],
        "overworld_sprite_id": group["overworld_sprite_id"],
        "rendered": True,
        "sheet": rel(out_path),
        "slots": cells,
        "missing_slots": missing,
    }


def main() -> int:
    args = parse_args()
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    asset_root = Path(args.asset_root)
    out_dir = Path(args.out)

    groups = contract["groups"]
    if args.group_id:
        wanted = set(args.group_id)
        groups = [group for group in groups if int(group["overworld_sprite_id"]) in wanted]
    if args.limit is not None:
        groups = groups[: args.limit]

    index = {
        "schema": "earthbound-decomp.overworld-sprite-preview-sheets.v1",
        "source_contract": rel(Path(args.contract)),
        "source_policy": {
            "contains_rom_derived_outputs": True,
            "do_not_commit_generated_outputs": True,
        },
        "output_root": rel(out_dir),
        "groups": [],
    }
    for group in groups:
        slots = group_slots_with_images(group, asset_root)
        index["groups"].append(build_group_sheet(group, slots, out_dir, args.cell_padding))

    rendered = sum(1 for group in index["groups"] if group["rendered"])
    missing = sum(len(group["missing_slots"]) for group in index["groups"])
    index_path = out_dir / "index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Rendered {rendered} overworld sprite preview sheets.")
    print(f"Missing slot preview images: {missing}")
    print(f"Wrote {rel(index_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
