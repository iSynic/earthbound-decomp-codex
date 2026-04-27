from __future__ import annotations

import argparse
from pathlib import Path

from rom_tools import find_rom, load_rom
from source_bank_byte_equivalence import (
    ROOT,
    choose_modules,
    default_ranges_for_bank,
    load_json,
    rel,
    render_combined_scaffold,
    resolve_path,
)


def default_output_for_bank(bank: str) -> Path:
    return ROOT / "src" / bank.lower() / f"bank_{bank.lower()}_helpers_asar.asm"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a durable Asar helper scaffold from a source bank range manifest."
    )
    parser.add_argument("--bank", default="C3", help="bank name used for default output path")
    parser.add_argument("--ranges", type=Path, help="build-candidate range manifest")
    parser.add_argument("--module", default="all", help="range substring filter, or 'all'")
    parser.add_argument("--rom", help="explicit ROM path")
    parser.add_argument("--output", type=Path, help="output Asar scaffold path")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    bank = args.bank.upper()
    ranges_path = resolve_path(args.ranges) if args.ranges else default_ranges_for_bank(bank)
    ranges = load_json(ranges_path)
    modules = choose_modules(ranges, args.module)
    rom = load_rom(find_rom(args.rom))
    output = resolve_path(args.output) if args.output else default_output_for_bank(bank)
    rebuild_parts = ["python", "tools/build_source_bank_scaffold.py", "--bank", bank]
    if args.ranges:
        rebuild_parts.extend(["--ranges", rel(ranges_path)])
    if args.module != "all":
        rebuild_parts.extend(["--module", args.module])
    if args.output:
        rebuild_parts.extend(["--output", rel(output)])

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render_combined_scaffold(
            modules,
            rom,
            generated_by="tools/build_source_bank_scaffold.py",
            purpose=f"Durable {bank} helper source scaffold for byte-equivalence validation.",
            ranges_path=rel(ranges_path),
            rebuild_command=" ".join(rebuild_parts),
        ),
        encoding="utf-8",
    )
    print(f"Wrote {rel(output)} with {len(modules)} module(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
