from __future__ import annotations

import argparse
from pathlib import Path

from source_bank_byte_equivalence import (
    DEFAULT_ASAR,
    default_json_out_for_bank,
    default_markdown_out_for_bank,
    default_out_dir_for_bank,
    default_ranges_for_bank,
    rel,
    resolve_path,
    validate_source_bank,
)


def build_parser(default_bank: str = "C3", default_module: str = "all") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assemble source-bank pilot module(s) and compare them against original ROM bytes."
    )
    parser.add_argument("--bank", default=default_bank, help="bank label used for default paths and report titles")
    parser.add_argument("--module", default=default_module, help="substring filter for a build-candidate range, or 'all'")
    parser.add_argument(
        "--combined",
        action="store_true",
        help="assemble all selected modules through one generated scaffold and one ROM patch",
    )
    parser.add_argument("--scaffold", type=Path, help="existing Asar scaffold to validate in --combined mode")
    parser.add_argument("--ranges", type=Path, help="build-candidate range manifest")
    parser.add_argument("--rom", help="explicit ROM path")
    parser.add_argument("--asar", type=Path, default=DEFAULT_ASAR)
    parser.add_argument("--out-dir", type=Path, help="scratch output directory")
    parser.add_argument("--json-out", type=Path, help="JSON report output path")
    parser.add_argument("--markdown-out", type=Path, help="Markdown report output path")
    parser.add_argument("--strict", action="store_true", help="exit nonzero on assembler failure or byte mismatch")
    return parser


def main(default_bank: str = "C3", default_module: str = "all", generated_by: str | None = None) -> int:
    args = build_parser(default_bank=default_bank, default_module=default_module).parse_args()
    bank = args.bank.upper()
    ranges = resolve_path(args.ranges) if args.ranges else default_ranges_for_bank(bank)
    out_dir = resolve_path(args.out_dir) if args.out_dir else default_out_dir_for_bank(bank)
    json_out = resolve_path(args.json_out) if args.json_out else default_json_out_for_bank(bank)
    markdown_out = resolve_path(args.markdown_out) if args.markdown_out else default_markdown_out_for_bank(bank)
    tool_name = generated_by or "tools/validate_source_bank_byte_equivalence.py"

    manifest = validate_source_bank(
        bank=bank,
        module_filter=args.module,
        combined=args.combined,
        scaffold=args.scaffold,
        ranges=ranges,
        rom=args.rom,
        asar=args.asar,
        out_dir=out_dir,
        json_out=json_out,
        markdown_out=markdown_out,
        generated_by=tool_name,
    )

    summary = manifest["summary"]
    print(
        f"{bank} byte-equivalence: {summary['status']}, "
        f"{summary['modules']} module(s), {summary['mismatch_count']} mismatch(es)."
    )
    print(f"Wrote {rel(json_out)} and {rel(markdown_out)}.")
    return 1 if args.strict and summary["status"] != "OK" else 0


if __name__ == "__main__":
    raise SystemExit(main())
