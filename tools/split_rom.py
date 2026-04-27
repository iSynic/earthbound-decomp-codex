from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from rom_tools import (
    EXPECTED_BANK_SIZE,
    bank_count,
    find_rom,
    load_rom,
    read_rom_info,
    snes_bank_number,
    verify_earthbound_us,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split the EarthBound ROM into sequential HiROM banks."
    )
    parser.add_argument("--rom", help="Path to the ROM file to split.")
    parser.add_argument(
        "--output-dir",
        default="build/split",
        help="Directory for the split output.",
    )
    parser.add_argument(
        "--bank-size",
        type=lambda value: int(value, 0),
        default=EXPECTED_BANK_SIZE,
        help="Bank size in bytes. Defaults to 0x10000.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing output directory.",
    )
    parser.add_argument(
        "--allow-unverified",
        action="store_true",
        help="Split the ROM even if it does not match the expected EarthBound dump.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        rom_path = find_rom(args.rom)
        info = read_rom_info(rom_path)
        data = load_rom(rom_path)
    except (FileNotFoundError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 2

    problems = verify_earthbound_us(info)
    if problems and not args.allow_unverified:
        print("Refusing to split an unexpected ROM:", file=sys.stderr)
        for problem in problems:
            print(f"- {problem}", file=sys.stderr)
        print("Pass --allow-unverified to override.", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    banks_dir = output_dir / "banks"
    manifest_path = output_dir / "manifest.json"

    if output_dir.exists():
        if not args.force:
            print(
                f"Output directory already exists: {output_dir}. "
                "Use --force to replace it.",
                file=sys.stderr,
            )
            return 1
        shutil.rmtree(output_dir)

    banks_dir.mkdir(parents=True, exist_ok=True)

    banks: list[dict[str, object]] = []
    total_banks = bank_count(info, args.bank_size)

    for index in range(total_banks):
        start = index * args.bank_size
        end = min(start + args.bank_size, len(data))
        bank_data = data[start:end]
        snes_bank = snes_bank_number(index)
        filename = f"bank_{snes_bank:02X}.bin"
        output_path = banks_dir / filename
        output_path.write_bytes(bank_data)

        banks.append(
            {
                "index": index,
                "snes_bank": f"0x{snes_bank:02X}",
                "file_offset": f"0x{start:06X}",
                "size": len(bank_data),
                "path": str(output_path),
            }
        )

    manifest = {
        "rom": info.to_dict(),
        "verified": not problems,
        "problems": problems,
        "bank_size": args.bank_size,
        "bank_count": total_banks,
        "output_dir": str(output_dir.resolve()),
        "banks": banks,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="ascii")

    print(f"ROM: {info.path}")
    print(f"Wrote {total_banks} banks to {banks_dir.resolve()}")
    print(f"Manifest: {manifest_path.resolve()}")
    if problems:
        print("Warning: split completed with verification mismatches.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
