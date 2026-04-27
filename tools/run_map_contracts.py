from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class ContractStep:
    name: str
    script: str
    accepts_rom: bool = False


STEPS: tuple[ContractStep, ...] = (
    ContractStep("map-sprite-usage", "build_map_sprite_usage_contract.py", accepts_rom=True),
    ContractStep("map-movement-usage", "build_map_movement_usage_contract.py"),
    ContractStep("map-object-bundles", "build_map_object_bundle_contract.py"),
    ContractStep("map-sector-bundles", "build_map_sector_bundle_contract.py"),
    ContractStep("map-tileset-bundles", "build_map_tileset_bundle_contract.py"),
    ContractStep("map-fts-format", "build_map_fts_format_audit.py"),
    ContractStep("map-fts-arrangement", "build_map_fts_arrangement_contract.py"),
    ContractStep("map-fts-animation-settings", "build_map_fts_animation_settings_contract.py"),
    ContractStep("map-palette-pointer-table", "build_map_palette_pointer_table_contract.py", accepts_rom=True),
    ContractStep("map-fts-palette-variant", "build_map_fts_palette_variant_contract.py", accepts_rom=True),
    ContractStep("map-tile-animation-runtime", "build_map_tile_animation_runtime_contract.py", accepts_rom=True),
    ContractStep("map-scene-composition", "build_map_scene_composition_contract.py"),
    ContractStep("map-palette-descriptor", "build_map_palette_descriptor_context.py"),
    ContractStep("map-collision-attribute", "build_map_collision_attribute_context.py"),
    ContractStep("map-collision-pointer", "build_map_collision_pointer_contract.py", accepts_rom=True),
    ContractStep("map-collision-runtime-bit", "build_map_collision_runtime_bit_contract.py", accepts_rom=True),
    ContractStep("map-palette-command-usage", "build_map_palette_command_usage_contract.py", accepts_rom=True),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Regenerate the checked-in map milestone contracts in dependency order. "
            "This does not render ignored preview assets."
        )
    )
    parser.add_argument("--rom", help="Optional explicit ROM path for ROM-backed contract steps.")
    parser.add_argument("--list", action="store_true", help="List available step names and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without running them.")
    parser.add_argument("--only", nargs="+", choices=[step.name for step in STEPS], help="Run only these steps.")
    parser.add_argument("--start-at", choices=[step.name for step in STEPS], help="Start at this step.")
    parser.add_argument("--stop-after", choices=[step.name for step in STEPS], help="Stop after this step.")
    return parser.parse_args()


def selected_steps(args: argparse.Namespace) -> list[ContractStep]:
    steps = list(STEPS)
    if args.start_at:
        start = next(index for index, step in enumerate(steps) if step.name == args.start_at)
        steps = steps[start:]
    if args.stop_after:
        stop = next(index for index, step in enumerate(steps) if step.name == args.stop_after)
        steps = steps[: stop + 1]
    if args.only:
        wanted = set(args.only)
        steps = [step for step in steps if step.name in wanted]
    return steps


def command_for(step: ContractStep, rom: str | None) -> list[str]:
    command = [sys.executable, str(ROOT / "tools" / step.script)]
    if rom and step.accepts_rom:
        command.extend(["--rom", rom])
    return command


def main() -> None:
    args = parse_args()

    if args.list:
        for step in STEPS:
            suffix = " -- accepts --rom" if step.accepts_rom else ""
            print(f"{step.name}: tools/{step.script}{suffix}")
        return

    steps = selected_steps(args)
    if not steps:
        raise SystemExit("No map contract steps selected.")

    for index, step in enumerate(steps, start=1):
        command = command_for(step, args.rom)
        display = " ".join(command)
        print(f"[{index}/{len(steps)}] {step.name}: {display}")
        if args.dry_run:
            continue
        subprocess.run(command, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
