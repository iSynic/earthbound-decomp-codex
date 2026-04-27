from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import find_ebtext_command as finder
import rom_tools


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize exact parsed EarthBound text-command hits for one top-level opcode.")
    parser.add_argument("opcode", help="Top-level command byte, for example 1C")
    parser.add_argument("--rom", help="Optional explicit ROM path")
    parser.add_argument("--yml", default="refs/ebsrc-main/ebsrc-main/earthbound.yml", help="YAML file with text_data segment offsets")
    parser.add_argument("--max-subcommands", type=int, default=64, help="Maximum subcommand values to scan")
    parser.add_argument("--show-zero", action="store_true", help="Include subcommands with zero exact parsed hits")
    parser.add_argument("--limit", type=int, default=3, help="Maximum sample hits per subcommand")
    args = parser.parse_args()

    rom_path = rom_tools.find_rom(args.rom)
    rom = rom_tools.load_rom(rom_path)
    yml_path = Path(args.yml)
    segments = finder.load_segments(yml_path)
    op = finder.parse_hex_byte(args.opcode)

    rows: list[tuple[int, str, int, dict[str, int], list[tuple[str, int, str]]]] = []
    for sub in range(args.max_subcommands):
        hits = finder.find_hits(rom, segments, op, sub)
        if not hits and not args.show_zero:
            continue
        by_segment: dict[str, int] = defaultdict(int)
        for seg_name, _, _ in hits:
            by_segment[seg_name] += 1
        rows.append((
            sub,
            finder.command_name_for(op, sub),
            len(hits),
            dict(sorted(by_segment.items(), key=lambda item: (-item[1], item[0]))),
            hits[:args.limit],
        ))

    print(f"ROM: {rom_path}")
    print(f"YML: {yml_path}")
    print(f"Opcode: 0x{op:02X} ({finder.command_name_for(op, None)})")
    print(f"Subcommands scanned: 0x00-0x{args.max_subcommands - 1:02X}")
    print()

    for sub, name, count, by_segment, sample_hits in rows:
        print(f"0x{sub:02X}  {name}  hits={count}")
        if by_segment:
            segment_bits = ", ".join(f"{seg}:{n}" for seg, n in list(by_segment.items())[:4])
            print(f"  segments: {segment_bits}")
        for seg_name, address, text in sample_hits:
            print(f"  sample: {finder.ebscript.fmt_addr(address)}  {seg_name}  {text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
