from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rom_tools import find_rom, read_rom_info, read_vectors, verify_earthbound_us


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dump the EarthBound ROM header and vector table."
    )
    parser.add_argument("--rom", help="Path to the ROM file to inspect.")
    parser.add_argument(
        "--json-out",
        help="Optional path to write machine-readable JSON output.",
    )
    parser.add_argument(
        "--markdown-out",
        help="Optional path to write a Markdown summary.",
    )
    return parser.parse_args()


def build_payload(rom_path: Path) -> dict[str, object]:
    info = read_rom_info(rom_path)
    vectors = read_vectors(rom_path)
    problems = verify_earthbound_us(info)
    return {
        "rom": info.to_dict(),
        "verified": not problems,
        "problems": problems,
        "vectors": [vector.to_dict() for vector in vectors],
    }


def build_markdown(payload: dict[str, object]) -> str:
    rom = payload["rom"]
    vectors = payload["vectors"]
    lines = [
        "# EarthBound Header and Vectors",
        "",
        f"- ROM: `{rom['path']}`",
        f"- Verified: `{payload['verified']}`",
        f"- SHA-1: `{rom['sha1']}`",
        f"- Title: `{rom['title']}`",
        f"- Map mode: `{rom['map_mode']}`",
        f"- Cart type: `{rom['cart_type']}`",
        f"- Checksum: `{rom['checksum']}`",
        f"- Complement: `{rom['complement_check']}`",
        "",
        "## Interrupt / Reset Vectors",
        "",
        "| Vector | Header Offset | CPU Address | File Offset | Canonical ROM Mirror |",
        "| --- | --- | --- | --- | --- |",
    ]

    for vector in vectors:
        if vector["canonical_long_address"]:
            canonical = f"{vector['canonical_long_address']} ({vector['canonical_bank']})"
        else:
            canonical = "not directly mapped in ROM"
        lines.append(
            "| {name} | {header_offset} | {cpu_long_address} | {rom_file_offset} | {canonical} |".format(
                name=vector["name"],
                header_offset=vector["header_offset"],
                cpu_long_address=vector["cpu_long_address"],
                rom_file_offset=vector["rom_file_offset"] or "n/a",
                canonical=canonical,
            )
        )

    reset_vector = next(vector for vector in vectors if vector["name"] == "emulation_reset")
    native_nmi = next(vector for vector in vectors if vector["name"] == "native_nmi")
    native_irq = next(vector for vector in vectors if vector["name"] == "native_irq")
    lines.extend(
        [
            "",
            "## Notes",
            "",
            f"- The reset vector starts execution at CPU address `{reset_vector['cpu_long_address']}`.",
            f"- On this HiROM cart, that reset trampoline mirrors to `{reset_vector['canonical_long_address']}` and lives at file offset `{reset_vector['rom_file_offset']}`.",
            f"- The native NMI and IRQ trampolines likewise mirror to `{native_nmi['canonical_long_address']}` and `{native_irq['canonical_long_address']}`.",
            "- Several other exception vectors point to `00:5FFF`, which is not directly mapped to ROM in bank `00`; treat those as unresolved until code tracing proves otherwise.",
            "- The useful first-pass disassembly targets are the canonical bank `C0` routines reached by those trampolines: `C0:8000`, `C0:814F`, and `C0:8170`.",
        ]
    )

    if payload["problems"]:
        lines.extend(["", "## Verification Problems", ""])
        for problem in payload["problems"]:
            lines.append(f"- {problem}")

    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()

    try:
        rom_path = find_rom(args.rom)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 2

    payload = build_payload(rom_path)

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(payload, indent=2) + "\n", encoding="ascii")
    if args.markdown_out:
        Path(args.markdown_out).write_text(build_markdown(payload), encoding="ascii")

    print(json.dumps(payload, indent=2))
    return 0 if payload["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
