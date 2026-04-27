from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from emit_linear_source_module import (
    collect_instructions,
    parse_address_list,
    parse_cpu_address,
    parse_label_list,
    parse_symbol_list,
    render_module,
)
from rom_tools import find_rom, load_rom


ROOT = Path(__file__).resolve().parent.parent


def default_manifest(bank: str) -> Path:
    return ROOT / "build" / f"{bank.lower()}-build-candidate-ranges.json"


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def title_from_name(name: str) -> str:
    spaced = name.replace("_", " ")
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", spaced)
    return spaced


def segment_from_module(module: dict[str, Any]) -> dict[str, Any]:
    if module.get("source_segments"):
        segment = dict(module["source_segments"][0])
    elif module.get("data_gaps"):
        segment = dict(module["data_gaps"][0])
    else:
        segment = {
            key: module[key]
            for key in (
                "start",
                "end",
                "size",
                "file_offset_start",
                "file_offset_end",
                "sha1",
                "first_bytes",
                "last_bytes",
                "labels",
                "evidence",
            )
            if key in module
        }
    segment["kind"] = "source"
    return segment


def recompute_summary(manifest: dict[str, Any]) -> None:
    ranges = manifest.get("ranges", [])
    summary = manifest.setdefault("summary", {})
    summary["ranges"] = len(ranges)
    summary["total_bytes"] = sum(int(item.get("size", 0)) for item in ranges)
    summary["source_bytes"] = sum(int(item.get("source_size", 0)) for item in ranges)
    summary["data_gap_bytes"] = sum(int(item.get("data_gap_size", 0)) for item in ranges)
    summary["anchor_model"] = "mixed decoded source and byte corridors"


def find_module(manifest: dict[str, Any], module_filter: str) -> dict[str, Any]:
    matches = [
        item
        for item in manifest.get("ranges", [])
        if module_filter.lower()
        in f"{item.get('source_path', '')} {item.get('start', '')} {item.get('end', '')} {' '.join(item.get('labels', []))}".lower()
    ]
    if not matches:
        raise SystemExit(f"No range matched {module_filter!r}")
    if len(matches) > 1:
        choices = ", ".join(f"{item['start']} {item['source_path']}" for item in matches[:12])
        raise SystemExit(f"Ambiguous range filter {module_filter!r}; matched {choices}")
    return matches[0]


def module_name(module: dict[str, Any]) -> str:
    if module.get("source_segments"):
        return str(module["source_segments"][0].get("name") or Path(module["source_path"]).stem)
    if module.get("data_gaps"):
        return str(module["data_gaps"][0].get("name") or Path(module["source_path"]).stem)
    labels = module.get("labels", [])
    if labels:
        return labels[0].split(" ", 1)[-1].strip().replace(" ", "_")
    return Path(module["source_path"]).stem


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Promote one byte-corridor range into decoded linear 65816 source."
    )
    parser.add_argument("--bank", required=True, help="bank name, e.g. C0")
    parser.add_argument(
        "--module",
        required=True,
        help="substring matching source path, address, or label",
    )
    parser.add_argument("--manifest", type=Path, help="range manifest path")
    parser.add_argument("--rom", help="explicit ROM path")
    parser.add_argument("--subsystem", default="decoded-source")
    parser.add_argument("--title", help="human-readable title for the source header")
    parser.add_argument("--force-m16-at", action="append", default=[])
    parser.add_argument("--force-m8-at", action="append", default=[])
    parser.add_argument("--force-x16-at", action="append", default=[])
    parser.add_argument("--force-x8-at", action="append", default=[])
    parser.add_argument("--symbol", action="append", default=[], help="additional symbol mapping, NAME=$ADDR")
    parser.add_argument("--label", action="append", default=[], help="semantic label mapping, C0:1234=Name")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    bank = args.bank.upper()
    manifest_path = resolve(args.manifest) if args.manifest else default_manifest(bank)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    module = find_module(manifest, args.module)
    start_bank, start_address = parse_cpu_address(module["start"])
    end_bank, end_address = parse_cpu_address(module["end"])
    if start_bank != end_bank or start_bank != int(bank, 16):
        raise SystemExit(f"Module range {module['start']}..{module['end']} is not in bank {bank}")

    rom = load_rom(find_rom(args.rom))
    instructions = collect_instructions(
        rom,
        start_bank,
        start_address,
        end_address,
        force_m16_at=parse_address_list(args.force_m16_at),
        force_m8_at=parse_address_list(args.force_m8_at),
        force_x16_at=parse_address_list(args.force_x16_at),
        force_x8_at=parse_address_list(args.force_x8_at),
    )
    name = module_name(module)
    output = resolve(Path(module["source_path"]))
    output.write_text(
        render_module(
            start_bank,
            start_address,
            end_address,
            name,
            instructions,
            title=args.title or title_from_name(name),
            symbols=parse_symbol_list(args.symbol),
            entry_labels=parse_label_list(args.label),
        ),
        encoding="utf-8",
    )

    segment = segment_from_module(module)
    module["subsystem"] = args.subsystem
    module["source_size"] = int(module["size"])
    module["data_gap_size"] = 0
    module["source_segments"] = [segment]
    module["data_gaps"] = []
    recompute_summary(manifest)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        f"Promoted {module['start']}..{module['end']} -> {output.relative_to(ROOT).as_posix()} "
        f"with {len(instructions)} instruction(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
