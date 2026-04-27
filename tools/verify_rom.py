from __future__ import annotations

import argparse
import json
import sys

from rom_tools import find_rom, read_rom_info, verify_earthbound_us


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify that the ROM matches the expected EarthBound (USA) dump."
    )
    parser.add_argument("--rom", help="Path to the ROM file to verify.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        rom_path = find_rom(args.rom)
        info = read_rom_info(rom_path)
    except (FileNotFoundError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 2

    problems = verify_earthbound_us(info)
    payload = info.to_dict() | {
        "verified": not problems,
        "problems": problems,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"ROM: {info.path}")
        print(f"Size: {info.size} bytes")
        print(f"SHA-1: {info.sha1.upper()}")
        print(f"Title: {info.title}")
        print(f"Map mode: 0x{info.map_mode:02X}")
        print(f"Cart type: 0x{info.cart_type:02X}")
        if problems:
            print("Status: FAILED")
            for problem in problems:
                print(f"- {problem}")
        else:
            print("Status: VERIFIED")

    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
