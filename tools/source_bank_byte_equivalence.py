from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from rom_tools import find_rom, hirom_to_file_offset, load_rom


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ASAR = ROOT / "build" / "tmp-yoshifanatic1-earthbound-disassembly" / "Global" / "asar.exe"
SCHEMA = "earthbound-decomp.source-bank-byte-equivalence.v1"


CONST_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$")
LABEL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):$")
COMMENT_RE = re.compile(r";.*$")


@dataclass(frozen=True)
class Mismatch:
    address: str
    file_offset: str
    expected: str
    actual: str


@dataclass(frozen=True)
class ModuleResult:
    source_path: str
    range_start: str
    range_end: str
    size: int
    status: str
    assembler: str
    generated_asm: str
    patched_rom: str
    mismatches: tuple[Mismatch, ...]
    mismatch_count: int
    asar_stdout: str
    asar_stderr: str


def default_ranges_for_bank(bank: str) -> Path:
    return ROOT / "build" / f"{bank.lower()}-build-candidate-ranges.json"


def default_out_dir_for_bank(bank: str) -> Path:
    return ROOT / "build" / f"{bank.lower()}-byte-equivalence"


def default_json_out_for_bank(bank: str) -> Path:
    return ROOT / "build" / f"{bank.lower()}-byte-equivalence-validation.json"


def default_markdown_out_for_bank(bank: str) -> Path:
    return ROOT / "notes" / f"{bank.lower()}-byte-equivalence-validation.md"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def strip_comment(line: str) -> str:
    return COMMENT_RE.sub("", line).rstrip()


def parse_bank_address(raw: str) -> tuple[int, int]:
    bank, address = raw.split(":", 1)
    return int(bank, 16), int(address, 16)


def format_bank_address(bank: int, address: int) -> str:
    return f"{bank:02X}:{address:04X}"


def slug_for_source(source_path: str) -> str:
    return Path(source_path).stem.replace("_helpers", "").replace("_", "-")


def choose_modules(ranges: dict[str, Any], module_filter: str) -> list[dict[str, Any]]:
    if module_filter.lower() == "all":
        return list(ranges.get("ranges", []))

    matches = [
        module
        for module in ranges.get("ranges", [])
        if module_filter.lower() in f"{module['source_path']} {module.get('subsystem', '')}".lower()
    ]
    if not matches:
        raise SystemExit(f"No build-candidate range matched --module {module_filter!r}")
    if len(matches) > 1:
        choices = ", ".join(module["source_path"] for module in matches)
        raise SystemExit(f"Ambiguous --module {module_filter!r}; matched {choices}")
    return matches


def collect_constants(lines: list[str]) -> set[str]:
    constants: set[str] = set()
    for line in lines:
        code = strip_comment(line).strip()
        match = CONST_RE.match(code)
        if match:
            constants.add(match.group(1))
    return constants


def normalize_asar_expression_spacing(code: str) -> str:
    code = re.sub(r"\s+\+\s+", "+", code)
    code = re.sub(r"\s+-\s+", "-", code)
    return code


def replace_constants(code: str, constants: set[str]) -> str:
    for name in sorted(constants, key=len, reverse=True):
        code = re.sub(rf"(?<![!A-Za-z0-9_]){re.escape(name)}\b", f"!{name}", code)
    return normalize_asar_expression_spacing(code)


def render_db_bytes(data: bytes) -> list[str]:
    lines: list[str] = []
    for index in range(0, len(data), 16):
        chunk = data[index : index + 16]
        lines.append("db " + ",".join(f"${byte:02X}" for byte in chunk))
    return lines


def data_gap_bytes(module: dict[str, Any], rom: bytes) -> dict[int, bytes]:
    gaps: dict[int, bytes] = {}
    for gap in module.get("data_gaps", []):
        start_bank, start_address = parse_bank_address(gap["start"])
        end_bank, end_address = parse_bank_address(gap["end"])
        if start_bank != end_bank:
            raise ValueError(f"Data gap crosses banks: {gap['start']}..{gap['end']}")
        start_offset = hirom_to_file_offset(start_bank, start_address, len(rom))
        end_offset = hirom_to_file_offset(end_bank, end_address, len(rom))
        if start_offset is None or end_offset is None:
            raise ValueError(f"Unable to convert data gap {gap['start']}..{gap['end']} to ROM offsets")
        gaps[end_address] = rom[start_offset:end_offset]
    return gaps


def translate_source_to_asar(
    source_path: Path,
    module: dict[str, Any],
    rom: bytes,
    *,
    generated_by: str = "tools/source_bank_byte_equivalence.py",
    module_purpose: str = "Scratch Asar translation for byte-equivalence validation only.",
) -> str:
    text = source_path.read_text(encoding="utf-8", errors="ignore")
    source_lines = text.splitlines()
    constants = collect_constants(source_lines)
    start_bank, start_address = parse_bank_address(module["start"])
    gaps_by_next_label = data_gap_bytes(module, rom)

    out: list[str] = [
        f"; Generated by {generated_by}",
        f"; {module_purpose}",
        f"; Source: {rel(source_path)}",
        "",
        "hirom",
        f"org ${start_bank:02X}{start_address:04X}",
        "",
    ]

    for line in source_lines:
        code = strip_comment(line)
        if not code.strip():
            continue
        stripped = code.strip()
        const_match = CONST_RE.match(stripped)
        if const_match:
            out.append(f"!{const_match.group(1)} = {const_match.group(2).strip()}")
            continue
        if LABEL_RE.match(stripped):
            bank_prefix = f"{start_bank:02X}"
            label_address_match = re.match(rf"^{bank_prefix}([0-9A-F]{{4}})_", stripped)
            if label_address_match:
                label_address = int(label_address_match.group(1), 16)
                gap_data = gaps_by_next_label.pop(label_address, None)
                if gap_data:
                    out.append("")
                    out.append(f"; Original data gap before {stripped}")
                    out.extend(render_db_bytes(gap_data))
                    out.append("")
            out.append(stripped)
            continue

        leading = code[: len(code) - len(code.lstrip())]
        body = code.strip()
        out.append(leading + replace_constants(body, constants))

    for end_address, gap_data in sorted(gaps_by_next_label.items()):
        if gap_data:
            out.append("")
            out.append(f"; Original terminal data gap ending at ${start_bank:02X}{end_address:04X}")
            out.extend(render_db_bytes(gap_data))

    return "\n".join(out).rstrip() + "\n"


def render_combined_scaffold(
    modules: list[dict[str, Any]],
    rom: bytes,
    *,
    generated_by: str,
    purpose: str,
    ranges_path: str,
    rebuild_command: str,
) -> str:
    chunks = [
        f"; Generated by {generated_by}",
        f"; {purpose}",
        ";",
        "; This file is generated from the ca65-like source modules listed in",
        f"; {ranges_path}. Rebuild with:",
        f";   {rebuild_command}",
        "",
    ]
    for module in modules:
        source_path = ROOT / str(module["source_path"])
        chunks.append(
            translate_source_to_asar(
                source_path,
                module,
                rom,
                generated_by=generated_by,
                module_purpose="Asar module translation for this scaffold.",
            )
        )
        chunks.append("")
    return "\n".join(chunks).rstrip() + "\n"


def compare_range(original: bytes, patched: bytes, module: dict[str, Any]) -> list[Mismatch]:
    start_bank, start_address = parse_bank_address(module["start"])
    end_bank, end_address = parse_bank_address(module["end"])
    if start_bank != end_bank:
        raise ValueError(f"Byte-equivalence range crosses banks: {module['start']}..{module['end']}")

    start_offset = hirom_to_file_offset(start_bank, start_address, len(original))
    end_offset = hirom_to_file_offset(end_bank, end_address, len(original))
    if start_offset is None or end_offset is None:
        raise ValueError(f"Unable to convert range {module['start']}..{module['end']} to ROM offsets")

    mismatches: list[Mismatch] = []
    for offset in range(start_offset, end_offset):
        if original[offset] == patched[offset]:
            continue
        address = start_address + (offset - start_offset)
        mismatches.append(
            Mismatch(
                address=format_bank_address(start_bank, address),
                file_offset=f"0x{offset:06X}",
                expected=f"{original[offset]:02X}",
                actual=f"{patched[offset]:02X}",
            )
        )
    return mismatches


def result_for_assembler_failure(
    module: dict[str, Any],
    asar_path: Path,
    generated_asm: Path,
    patched_rom: Path,
    stdout: str,
    stderr: str,
) -> ModuleResult:
    return ModuleResult(
        source_path=module["source_path"],
        range_start=module["start"],
        range_end=module["end"],
        size=int(module["size"]),
        status="ASSEMBLER-FAIL",
        assembler=rel(asar_path),
        generated_asm=rel(generated_asm),
        patched_rom=rel(patched_rom),
        mismatches=(),
        mismatch_count=0,
        asar_stdout=stdout,
        asar_stderr=stderr,
    )


def result_for_range(
    module: dict[str, Any],
    asar_path: Path,
    generated_asm: Path,
    patched_rom: Path,
    mismatches: list[Mismatch],
    stdout: str,
    stderr: str,
) -> ModuleResult:
    return ModuleResult(
        source_path=module["source_path"],
        range_start=module["start"],
        range_end=module["end"],
        size=int(module["size"]),
        status="OK" if not mismatches else "MISMATCH",
        assembler=rel(asar_path),
        generated_asm=rel(generated_asm),
        patched_rom=rel(patched_rom),
        mismatches=tuple(mismatches[:200]),
        mismatch_count=len(mismatches),
        asar_stdout=stdout,
        asar_stderr=stderr,
    )


def run_module(
    module: dict[str, Any],
    rom_path: Path,
    asar_path: Path,
    out_dir: Path,
    *,
    generated_by: str,
) -> ModuleResult:
    source_path = ROOT / str(module["source_path"])
    slug = slug_for_source(module["source_path"])
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_asm = out_dir / f"{slug}.byte-equivalence.asar.asm"
    patched_rom = out_dir / f"{slug}.byte-equivalence.sfc"

    original = load_rom(rom_path)
    generated_asm.write_text(
        translate_source_to_asar(source_path, module, original, generated_by=generated_by),
        encoding="utf-8",
    )
    shutil.copyfile(rom_path, patched_rom)

    completed = subprocess.run(
        [str(asar_path), "--fix-checksum=off", str(generated_asm), str(patched_rom)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        return result_for_assembler_failure(
            module,
            asar_path,
            generated_asm,
            patched_rom,
            completed.stdout,
            completed.stderr,
        )

    patched = load_rom(patched_rom)
    return result_for_range(
        module,
        asar_path,
        generated_asm,
        patched_rom,
        compare_range(original, patched, module),
        completed.stdout,
        completed.stderr,
    )


def run_combined(
    modules: list[dict[str, Any]],
    rom_path: Path,
    asar_path: Path,
    out_dir: Path,
    *,
    bank: str,
    generated_by: str,
    ranges_path: Path,
    scaffold_path: Path | None = None,
) -> list[ModuleResult]:
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_asm = scaffold_path or out_dir / f"bank-{bank.lower()}-helper-scaffold.byte-equivalence.asar.asm"
    patched_rom = out_dir / f"bank-{bank.lower()}-helper-scaffold.byte-equivalence.sfc"
    original = load_rom(rom_path)

    if scaffold_path is None:
        generated_asm.write_text(
            render_combined_scaffold(
                modules,
                original,
                generated_by=generated_by,
                purpose=f"Combined {bank.upper()} helper scaffold for byte-equivalence validation only.",
                ranges_path=rel(ranges_path),
                rebuild_command=f"python tools/build_source_bank_scaffold.py --bank {bank.upper()}",
            ),
            encoding="utf-8",
        )
    elif not generated_asm.is_file():
        raise FileNotFoundError(f"Scaffold not found: {generated_asm}")
    shutil.copyfile(rom_path, patched_rom)

    completed = subprocess.run(
        [str(asar_path), "--fix-checksum=off", str(generated_asm), str(patched_rom)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    if completed.returncode != 0:
        return [
            result_for_assembler_failure(
                module,
                asar_path,
                generated_asm,
                patched_rom,
                completed.stdout,
                completed.stderr,
            )
            for module in modules
        ]

    patched = load_rom(patched_rom)
    return [
        result_for_range(
            module,
            asar_path,
            generated_asm,
            patched_rom,
            compare_range(original, patched, module),
            completed.stdout,
            completed.stderr,
        )
        for module in modules
    ]


def build_manifest(results: list[ModuleResult], mode: str, *, bank: str, generated_by: str) -> dict[str, Any]:
    non_ok = sum(1 for result in results if result.status != "OK")
    return {
        "schema": SCHEMA,
        "generated_by": generated_by,
        "bank": bank.upper(),
        "summary": {
            "mode": mode,
            "modules": len(results),
            "status": "OK" if non_ok == 0 else "FAIL",
            "non_ok_modules": non_ok,
            "mismatch_count": sum(result.mismatch_count for result in results),
        },
        "modules": [asdict(result) for result in results],
    }


def render_markdown(manifest: dict[str, Any]) -> str:
    bank = manifest.get("bank", "source bank")
    summary = manifest["summary"]
    description = (
        "This report assembles an existing durable Asar source-bank scaffold into a clean ROM copy, then compares the protected byte ranges against the original ROM."
        if summary["mode"] == "durable-scaffold"
        else f"This report assembles scratch Asar translations of {bank} pilot modules into clean ROM copies at their original `org` addresses, then compares the protected byte ranges against the original ROM."
    )
    lines = [
        f"# {bank} byte-equivalence validation",
        "",
        description,
        "",
        f"- status: `{summary['status']}`",
        f"- mode: `{summary['mode']}`",
        f"- modules: `{summary['modules']}`",
        f"- non-OK modules: `{summary['non_ok_modules']}`",
        f"- mismatches: `{summary['mismatch_count']}`",
        "",
        "## Modules",
        "",
        "| Status | Source Path | Range | Size | Mismatches | Generated ASM |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for result in manifest["modules"]:
        lines.append(
            f"| `{result['status']}` | `{result['source_path']}` | `{result['range_start']}..{result['range_end']}` | {result['size']} | {result['mismatch_count']} | `{result['generated_asm']}` |"
        )

    mismatch_modules = [result for result in manifest["modules"] if result["mismatches"]]
    if mismatch_modules:
        lines.extend(["", "## First Mismatches", ""])
        for result in mismatch_modules:
            lines.extend(
                [
                    f"### `{result['source_path']}`",
                    "",
                    "| Address | File Offset | Expected | Actual |",
                    "| --- | ---: | ---: | ---: |",
                ]
            )
            for mismatch in result["mismatches"]:
                lines.append(
                    f"| `{mismatch['address']}` | `{mismatch['file_offset']}` | `{mismatch['expected']}` | `{mismatch['actual']}` |"
                )
            lines.append("")
    fail_modules = [result for result in manifest["modules"] if result["status"] == "ASSEMBLER-FAIL"]
    if fail_modules:
        lines.extend(["", "## Assembler Output", ""])
        for result in fail_modules:
            lines.extend(["```text", result["asar_stdout"], result["asar_stderr"], "```"])
    return "\n".join(lines).rstrip() + "\n"


def validate_source_bank(
    *,
    bank: str,
    module_filter: str,
    combined: bool,
    scaffold: Path | None,
    ranges: Path,
    rom: str | None,
    asar: Path,
    out_dir: Path,
    json_out: Path,
    markdown_out: Path,
    generated_by: str,
) -> dict[str, Any]:
    ranges = resolve_path(ranges)
    ranges_manifest = load_json(ranges)
    modules = choose_modules(ranges_manifest, module_filter)
    rom_path = find_rom(rom)
    asar_path = resolve_path(asar)
    if not asar_path.is_file():
        raise SystemExit(f"Asar executable not found: {asar_path}")

    if combined:
        results = run_combined(
            modules,
            rom_path,
            asar_path,
            resolve_path(out_dir),
            bank=bank,
            generated_by=generated_by,
            ranges_path=ranges,
            scaffold_path=resolve_path(scaffold) if scaffold else None,
        )
        mode = "durable-scaffold" if scaffold else "combined-scaffold"
    else:
        results = [
            run_module(module, rom_path, asar_path, resolve_path(out_dir), generated_by=generated_by)
            for module in modules
        ]
        mode = "per-module"

    manifest = build_manifest(results, mode, bank=bank, generated_by=generated_by)

    json_out = resolve_path(json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    markdown_out = resolve_path(markdown_out)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(render_markdown(manifest), encoding="utf-8")
    return manifest
