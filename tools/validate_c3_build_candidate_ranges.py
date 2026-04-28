from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rom_tools import find_rom, hirom_to_file_offset, load_rom


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RANGES = ROOT / "build" / "c3-build-candidate-ranges.json"
DEFAULT_SIGNATURES = ROOT / "build" / "c3-source-signature-validation.json"
SIGNATURE_EXEMPT_SOURCES = {
    "src/c3/script_event_payloads_0000_e450.asm",
    "src/c3/data_debug_menu_mixed_inventory_prefix.asm",
    "src/c3/data_battle_menu_tables_ef23_f1ec.asm",
    "src/c3/data_battle_visual_tables_f2b1_f5f9.asm",
    "src/c3/data_battle_tail_and_delivery_payloads_fb1f_10000.asm",
}


@dataclass(frozen=True)
class Finding:
    severity: str
    source_path: str
    message: str


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_address(text: str) -> int:
    bank, address = text.split(":", 1)
    if bank != "C3":
        raise ValueError(f"expected C3 address, got {text}")
    return int(address, 16)


def signature_by_source(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    signatures = load_json(path)
    return {str(module["source_path"]): module for module in signatures.get("modules", [])}


def requires_source_signature(source_path: str) -> bool:
    return source_path not in SIGNATURE_EXEMPT_SOURCES


def validate_bytes(item: dict[str, Any], rom: bytes, source_path: str, label: str) -> list[Finding]:
    findings: list[Finding] = []
    start = parse_address(str(item["start"]))
    end = parse_address(str(item["end"]))
    file_start = hirom_to_file_offset(0xC3, start, len(rom))
    file_end = hirom_to_file_offset(0xC3, end - 1, len(rom))
    if file_start is None or file_end is None:
        return [Finding("error", source_path, f"{label} cannot be mapped into the ROM")]
    data = rom[file_start : file_end + 1]
    if len(data) != int(item["size"]):
        findings.append(Finding("error", source_path, f"{label} size mismatch: manifest {item['size']} vs ROM {len(data)}"))
    sha1 = hashlib.sha1(data).hexdigest()
    if sha1 != item["sha1"]:
        findings.append(Finding("error", source_path, f"{label} SHA-1 mismatch: manifest {item['sha1']} vs ROM {sha1}"))
    return findings


def validate_range(item: dict[str, Any], rom: bytes, signatures: dict[str, dict[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    source_path = str(item["source_path"])
    start = parse_address(str(item["start"]))
    end = parse_address(str(item["end"]))
    findings.extend(validate_bytes(item, rom, source_path, "range"))
    if item.get("level") != "build-candidate":
        findings.append(Finding("error", source_path, f"range level is `{item.get('level')}`, expected `build-candidate`"))
    if not item.get("labels"):
        findings.append(Finding("error", source_path, "range has no labels recorded"))

    source_segments = list(item.get("source_segments", []))
    data_gaps = list(item.get("data_gaps", []))
    if not source_segments and not data_gaps:
        findings.append(Finding("error", source_path, "range has no protected parts recorded"))
    source_size = sum(int(segment["size"]) for segment in source_segments)
    data_gap_size = sum(int(gap["size"]) for gap in data_gaps)
    if source_size != int(item.get("source_size", 0)):
        findings.append(Finding("error", source_path, f"source segment size mismatch: summary {item.get('source_size')} vs parts {source_size}"))
    if data_gap_size != int(item.get("data_gap_size", 0)):
        findings.append(Finding("error", source_path, f"data-gap size mismatch: summary {item.get('data_gap_size')} vs parts {data_gap_size}"))
    if source_size + data_gap_size != int(item["size"]):
        findings.append(Finding("error", source_path, f"parts do not cover protected span: parts {source_size + data_gap_size} vs range {item['size']}"))

    parts = sorted(source_segments + data_gaps, key=lambda part: parse_address(str(part["start"])))
    cursor = start
    for part in parts:
        part_start = parse_address(str(part["start"]))
        part_end = parse_address(str(part["end"]))
        if part_start != cursor:
            findings.append(Finding("error", source_path, f"non-contiguous protected parts near C3:{cursor:04X}; next part starts at {part['start']}"))
        if part_end <= part_start:
            findings.append(Finding("error", source_path, f"invalid part range {part['start']}..{part['end']}"))
        cursor = part_end
        findings.extend(validate_bytes(part, rom, source_path, f"{part.get('kind', 'part')} {part['start']}..{part['end']}"))
    if cursor != end:
        findings.append(Finding("error", source_path, f"protected parts end at C3:{cursor:04X}, expected {item['end']}"))

    signature = signatures.get(source_path)
    if source_segments and requires_source_signature(source_path):
        if signature is None:
            findings.append(Finding("error", source_path, "missing source signature validation result"))
        elif int(signature.get("errors", 0)) != 0:
            findings.append(Finding("error", source_path, f"source signature validation has {signature.get('errors')} error(s)"))
    return findings


def render_markdown(findings: list[Finding], checked: int) -> str:
    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]
    lines = [
        "# C3 build-candidate range validation",
        "",
        f"- status: `{'OK' if not errors else 'FAIL'}`",
        f"- ranges checked: `{checked}`",
        f"- errors: `{len(errors)}`",
        f"- warnings: `{len(warnings)}`",
    ]
    if findings:
        lines.extend(["", "| Severity | Source Path | Message |", "| --- | --- | --- |"])
        for finding in findings:
            lines.append(f"| `{finding.severity}` | `{finding.source_path}` | {finding.message} |")
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate C3 build-candidate byte ranges against ROM and signature reports.")
    parser.add_argument("--ranges", type=Path, default=DEFAULT_RANGES)
    parser.add_argument("--signatures", type=Path, default=DEFAULT_SIGNATURES)
    parser.add_argument("--rom", help="explicit ROM path")
    parser.add_argument("--markdown-out", type=Path, default=ROOT / "notes" / "c3-build-candidate-range-validation.md")
    parser.add_argument("--strict", action="store_true", help="exit nonzero on validation errors")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    ranges_path = resolve_path(args.ranges)
    signatures_path = resolve_path(args.signatures)
    ranges = load_json(ranges_path)
    rom = load_rom(find_rom(args.rom))
    signatures = signature_by_source(signatures_path)

    findings: list[Finding] = []
    for item in ranges.get("ranges", []):
        findings.extend(validate_range(item, rom, signatures))

    markdown_out = resolve_path(args.markdown_out)
    markdown_out.write_text(render_markdown(findings, len(ranges.get("ranges", []))), encoding="utf-8")

    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]
    print(f"Validated C3 build-candidate ranges: {len(errors)} errors, {len(warnings)} warnings.")
    print(f"Wrote {rel(markdown_out)}.")
    return 1 if args.strict and errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
