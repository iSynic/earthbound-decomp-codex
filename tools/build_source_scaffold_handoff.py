#!/usr/bin/env python3
"""Render a concise handoff note for a byte-complete source-bank scaffold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def default_manifest(bank: str) -> Path:
    return ROOT / "build" / f"{bank.lower()}-build-candidate-ranges.json"


def default_validation(bank: str) -> Path:
    return ROOT / "build" / f"{bank.lower()}-byte-equivalence-validation.json"


def default_residual(bank: str) -> Path:
    return ROOT / "build" / f"{bank.lower()}-source-residual-map.json"


def default_output(bank: str) -> Path:
    return ROOT / "notes" / f"bank-{bank.lower()}-source-scaffold-handoff.md"


def scaffold_path(bank: str) -> str:
    lower = bank.lower()
    return f"src/{lower}/bank_{lower}_helpers_asar.asm"


def promoter_command(bank: str, promoter: str) -> list[str]:
    if promoter == "asset":
        return [f"python tools\\promote_asset_bank_to_source_scaffold.py {bank}"]
    if promoter == "table":
        return [f"python tools\\promote_table_splits_to_source_scaffold.py {bank}"]
    if promoter == "mixed-asset-table":
        return [f"python tools\\promote_mixed_asset_table_bank_to_source_scaffold.py {bank}"]
    if promoter == "text":
        return [f"python tools\\promote_text_bank_to_source_scaffold.py {bank}"]
    return [f"# run the bank-specific promoter for {bank}"]


def render(bank: str, ranges: dict[str, Any], validation: dict[str, Any], residual: dict[str, Any], args: argparse.Namespace) -> str:
    summary = ranges["summary"]
    validation_summary = validation["summary"]
    residual_summary = residual["summary"]
    scaffold = scaffold_path(bank)
    commands = []
    if args.rebuild_command:
        commands.extend(args.rebuild_command)
    commands.extend(promoter_command(bank, args.promoter))
    commands.extend(
        [
            f"python tools\\build_source_bank_scaffold.py --bank {bank}",
            f"python tools\\validate_source_bank_byte_equivalence.py --bank {bank} --module all --combined --scaffold {scaffold.replace('/', '\\')} --strict",
            f"python tools\\build_source_bank_candidate_ranges_doc.py --bank {bank}",
            f"python tools\\build_source_bank_residual_map.py --bank {bank}",
        ]
    )
    command_block = "\n".join(commands)
    expected = (
        f"{bank} byte-equivalence: {validation_summary['status']}, "
        f"{validation_summary['modules']} module(s), {validation_summary['mismatch_count']} mismatch(es)."
    )

    lines = [
        f"# Bank {bank} Source Scaffold Handoff",
        "",
        "## Status",
        "",
        f"Bank `{bank}` is byte-complete for the current source-scaffold phase.",
        "",
        f"- durable scaffold: `{scaffold}`",
        f"- manifest: `build/{bank.lower()}-build-candidate-ranges.json`",
        f"- protected bytes: `{residual_summary['protected_bytes']} / {residual_summary['bank_bytes']}`",
        f"- residual bytes: `{residual_summary['residual_bytes']}`",
        f"- modules: `{summary['ranges']}`",
        f"- source bytes: `{summary['source_bytes']}`",
        f"- preserved data-gap bytes: `{summary['data_gap_bytes']}`",
        f"- byte-equivalence: `{validation_summary['status']}`, `{validation_summary['mismatch_count']}` mismatches",
        "",
        args.description,
        "",
        "## Regenerate And Validate",
        "",
        "Use these commands from the repository root:",
        "",
        "```powershell",
        command_block,
        "```",
        "",
        "Expected validation:",
        "",
        f"- `{expected}`",
        f"- `notes/{bank.lower()}-source-residual-map.md` reports `{residual_summary['residual_bytes']}` residual bytes and `{residual_summary['residual_ranges']}` residual ranges.",
        "",
        "## Remaining Semantic Work",
        "",
    ]
    for item in args.remaining:
        lines.append(f"- {item}")
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bank")
    parser.add_argument("--promoter", choices=["asset", "table", "mixed-asset-table", "text", "custom"], default="asset")
    parser.add_argument("--description", required=True)
    parser.add_argument("--remaining", action="append", required=True)
    parser.add_argument("--rebuild-command", action="append", default=[])
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--validation", type=Path)
    parser.add_argument("--residual", type=Path)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    bank = args.bank.upper()
    manifest_path = args.manifest or default_manifest(bank)
    validation_path = args.validation or default_validation(bank)
    residual_path = args.residual or default_residual(bank)
    output_path = args.output or default_output(bank)
    manifest_path = manifest_path if manifest_path.is_absolute() else ROOT / manifest_path
    validation_path = validation_path if validation_path.is_absolute() else ROOT / validation_path
    residual_path = residual_path if residual_path.is_absolute() else ROOT / residual_path
    output_path = output_path if output_path.is_absolute() else ROOT / output_path

    output_path.write_text(
        render(
            bank,
            load_json(manifest_path),
            load_json(validation_path),
            load_json(residual_path),
            args,
        ),
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {rel(output_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
