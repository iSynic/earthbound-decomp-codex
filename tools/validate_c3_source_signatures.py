from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from decode_snippet import CpuState, OPCODES, decode_instruction
from rom_tools import find_rom, load_rom


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "build" / "c3-source-emission-plan.json"
SCHEMA = "earthbound-decomp.c3-source-signature-validation.v1"

ASM_MNEMONICS = {mnemonic for mnemonic, _mode in OPCODES.values()}
LABEL_RE = re.compile(r"^C3([0-9A-F]{4})_[A-Za-z0-9_]+(?::|\s*=)")
M16_RETURN_CALLS = {
    "$C08616",  # QueueVramTransfer_FromDpSource
    "$C088B1",  # ResetRendererFrameState
    "$C3EAD0",  # tracked-item family present handler
    "$C3EB1C",  # tracked-item family absent handler
}


@dataclass(frozen=True)
class Finding:
    severity: str
    source_path: str
    line: int
    address: str | None
    message: str


@dataclass(frozen=True)
class ModuleResult:
    source_path: str
    subsystem: str
    instruction_lines_checked: int
    labels_checked: int
    errors: int
    warnings: int
    findings: tuple[Finding, ...]


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
    return line.split(";", 1)[0].strip()


def parse_instruction_line(line: str) -> tuple[str, str] | None:
    code = strip_comment(line)
    if not code or code.endswith(":") or "=" in code:
        return None
    parts = code.split(None, 1)
    mnemonic = parts[0].lower().split(".", 1)[0]
    if mnemonic not in ASM_MNEMONICS:
        return None
    return mnemonic, parts[1].strip() if len(parts) > 1 else ""


def expected_module_addresses(module: dict[str, Any]) -> set[int]:
    addresses: set[int] = set()
    for unit in module.get("units", []):
        for label in unit.get("labels", []):
            raw = str(label["address"])
            if raw.startswith("C3:"):
                addresses.add(int(raw.split(":", 1)[1], 16))
    return addresses


def validate_module(module: dict[str, Any], rom: bytes) -> ModuleResult:
    source_path = ROOT / str(module["source_path"])
    display_path = rel(source_path)
    text = source_path.read_text(encoding="utf-8", errors="ignore")
    expected_labels = expected_module_addresses(module)
    state = CpuState()
    state.enforce_forces()

    current_address: int | None = None
    labels_checked = 0
    instruction_lines_checked = 0
    findings: list[Finding] = []
    seen_expected_labels: set[int] = set()

    for line_number, line in enumerate(text.splitlines(), start=1):
        code = strip_comment(line)
        label_match = LABEL_RE.match(code)
        if label_match:
            label_address = int(label_match.group(1), 16)
            is_expected_boundary = label_address in expected_labels
            if current_address is not None and current_address != label_address and not is_expected_boundary:
                findings.append(
                    Finding(
                        "error",
                        display_path,
                        line_number,
                        f"C3:{label_address:04X}",
                        f"source label is at C3:{label_address:04X}, but decoded stream expected C3:{current_address:04X}",
                    )
                )
            current_address = label_address
            labels_checked += 1
            if is_expected_boundary:
                seen_expected_labels.add(label_address)
            # Most C3 helper entry labels immediately establish flags with REP.
            # When a label jumps across adjacent data, this fresh native state
            # keeps the verifier useful without pretending to model callers.
            if is_expected_boundary:
                state = CpuState()
                state.enforce_forces()
            continue

        parsed = parse_instruction_line(line)
        if parsed is None:
            continue
        instruction_lines_checked += 1
        if current_address is None:
            findings.append(
                Finding(
                    "error",
                    display_path,
                    line_number,
                    None,
                    "instruction appears before an address-prefixed C3 label",
                )
            )
            continue

        decoded = decode_instruction(rom, 0xC3, current_address, state)
        source_mnemonic, _ = parsed
        decoded_mnemonic = decoded.text.split(None, 1)[0].lower()
        if decoded_mnemonic != source_mnemonic:
            findings.append(
                Finding(
                    "error",
                    display_path,
                    line_number,
                    f"C3:{current_address:04X}",
                    f"mnemonic mismatch: source `{source_mnemonic}` vs ROM `{decoded.text}`",
                )
            )
        if decoded_mnemonic in {"jsl", "jsr"} and any(target in decoded.text.upper() for target in M16_RETURN_CALLS):
            state.m8 = False
            state.enforce_forces()
        current_address = (current_address + decoded.size) & 0xFFFF

    missing_expected = expected_labels - seen_expected_labels
    for address in sorted(missing_expected):
        findings.append(
            Finding(
                "error",
                display_path,
                0,
                f"C3:{address:04X}",
                "expected source-emission label was not seen in source file",
            )
        )

    errors = sum(1 for finding in findings if finding.severity == "error")
    warnings = sum(1 for finding in findings if finding.severity == "warning")
    return ModuleResult(
        source_path=display_path,
        subsystem=str(module["subsystem"]),
        instruction_lines_checked=instruction_lines_checked,
        labels_checked=labels_checked,
        errors=errors,
        warnings=warnings,
        findings=tuple(findings),
    )


def build_manifest(plan: dict[str, Any], rom: bytes, module_filter: str | None) -> dict[str, Any]:
    modules = []
    for module in plan.get("modules", []):
        source_path = str(module["source_path"])
        subsystem = str(module["subsystem"])
        if module_filter and module_filter.lower() not in f"{source_path} {subsystem}".lower():
            continue
        modules.append(validate_module(module, rom))

    return {
        "schema": SCHEMA,
        "generated_by": "tools/validate_c3_source_signatures.py",
        "summary": {
            "modules": len(modules),
            "instruction_lines_checked": sum(module.instruction_lines_checked for module in modules),
            "labels_checked": sum(module.labels_checked for module in modules),
            "errors": sum(module.errors for module in modules),
            "warnings": sum(module.warnings for module in modules),
        },
        "modules": [asdict(module) for module in modules],
    }


def render_markdown(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    lines = [
        "# C3 source signature validation",
        "",
        "This report walks address-prefixed labels in `src/c3` prototypes and compares the annotated instruction mnemonic stream against decoded ROM bytes at the same C3 addresses. It is a byte-equivalence precursor, not an assembler.",
        "",
        f"- status: `{'OK' if summary['errors'] == 0 else 'FAIL'}`",
        f"- modules: `{summary['modules']}`",
        f"- instruction lines checked: `{summary['instruction_lines_checked']}`",
        f"- labels checked: `{summary['labels_checked']}`",
        f"- errors: `{summary['errors']}`",
        f"- warnings: `{summary['warnings']}`",
        "",
        "## Modules",
        "",
        "| Status | Source Path | Instructions | Labels | Errors | Warnings |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for module in manifest["modules"]:
        status = "OK" if module["errors"] == 0 else "FAIL"
        lines.append(
            f"| `{status}` | `{module['source_path']}` | {module['instruction_lines_checked']} | {module['labels_checked']} | {module['errors']} | {module['warnings']} |"
        )

    findings = [
        finding
        for module in manifest["modules"]
        for finding in module["findings"]
    ]
    if findings:
        lines.extend(["", "## Findings", "", "| Severity | Path | Line | Address | Message |", "| --- | --- | ---: | --- | --- |"])
        for finding in findings[:200]:
            lines.append(
                f"| `{finding['severity']}` | `{finding['source_path']}` | {finding['line']} | `{finding.get('address') or ''}` | {finding['message']} |"
            )
        if len(findings) > 200:
            lines.append(f"| `info` |  |  |  | {len(findings) - 200} additional findings omitted from markdown; see JSON. |")
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate C3 source prototype instruction signatures against ROM decode.")
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--rom", help="explicit ROM path")
    parser.add_argument("--module", help="substring filter for source path or subsystem")
    parser.add_argument("--json-out", type=Path, default=ROOT / "build" / "c3-source-signature-validation.json")
    parser.add_argument("--markdown-out", type=Path, default=ROOT / "notes" / "c3-source-signature-validation.md")
    parser.add_argument("--strict", action="store_true", help="exit nonzero when errors are found")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    plan = load_json(resolve_path(args.plan))
    rom = load_rom(find_rom(args.rom))
    manifest = build_manifest(plan, rom, args.module)

    json_out = resolve_path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    markdown_out = resolve_path(args.markdown_out)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(render_markdown(manifest), encoding="utf-8")

    summary = manifest["summary"]
    print(
        f"Validated {summary['modules']} C3 source signature module(s): "
        f"{summary['errors']} errors, {summary['warnings']} warnings."
    )
    print(f"Wrote {rel(json_out)} and {rel(markdown_out)}.")
    return 1 if args.strict and summary["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
