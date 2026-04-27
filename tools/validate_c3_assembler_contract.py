from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from decode_snippet import OPCODES


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "build" / "c3-source-emission-plan.json"
SCHEMA = "earthbound-decomp.c3-assembler-contract-validation.v1"

ASM_MNEMONICS = {mnemonic for mnemonic, _mode in OPCODES.values()}
CONTROL_FLOW = {"bcc", "bcs", "beq", "bmi", "bne", "bpl", "bra", "bvc", "bvs", "jmp", "jsl", "jsr"}
REGISTER_NAMES = {"A", "X", "Y", "S"}
DIRECTIVES = {".A16", ".A8", ".I16", ".I8", ".ADDRSIZE", ".IMPORT", ".EXPORT"}


@dataclass(frozen=True)
class Finding:
    severity: str
    source_path: str
    line: int
    message: str


@dataclass(frozen=True)
class ModuleResult:
    source_path: str
    assembler_contract: str | None
    instruction_lines: int
    symbols_defined: int
    labels_defined: int
    symbolic_operand_lines: int
    unresolved_symbol_lines: int
    raw_external_control_flow_edges: int
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
    mnemonic = parts[0].lower()
    if mnemonic not in ASM_MNEMONICS:
        return None
    return mnemonic, parts[1].strip() if len(parts) > 1 else ""


def find_assembler_contract(text: str) -> str | None:
    match = re.search(r"Assembler contract:\s*([A-Za-z0-9_-]+)", text)
    return match.group(1) if match else None


def collect_defined_symbols(text: str) -> tuple[set[str], set[str]]:
    constants: set[str] = set()
    labels: set[str] = set()
    for line in text.splitlines():
        code = strip_comment(line)
        const_match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=", code)
        if const_match:
            constants.add(const_match.group(1))
            continue
        label_match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):$", code)
        if label_match:
            labels.add(label_match.group(1))
    return constants, labels


def operand_symbols(operand: str) -> set[str]:
    cleaned = re.sub(r"[\$%][0-9A-Fa-f_]+", " ", operand)
    symbols = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", cleaned))
    return {
        symbol
        for symbol in symbols
        if symbol.upper() not in REGISTER_NAMES
        and symbol.upper() not in DIRECTIVES
    }


def validate_module(module: dict[str, Any]) -> ModuleResult:
    source_path = ROOT / str(module["source_path"])
    display_path = rel(source_path)
    text = source_path.read_text(encoding="utf-8", errors="ignore")
    constants, labels = collect_defined_symbols(text)
    defined = constants | labels
    contract = find_assembler_contract(text)
    pilot_ready = contract == "pilot-ready"

    instruction_lines = 0
    symbolic_operand_lines = 0
    unresolved_symbol_lines = 0
    raw_external_edges = 0
    findings: list[Finding] = []

    if pilot_ready and "build/c3-build-candidate-ranges.json" not in text:
        findings.append(
            Finding(
                "error",
                display_path,
                0,
                "pilot-ready modules must name the build-candidate range manifest that protects their bytes",
            )
        )

    for line_number, line in enumerate(text.splitlines(), start=1):
        parsed = parse_instruction_line(line)
        if parsed is None:
            continue
        instruction_lines += 1
        mnemonic, operand = parsed
        symbols = operand_symbols(operand)
        if symbols:
            symbolic_operand_lines += 1
        unresolved = sorted(symbol for symbol in symbols if symbol not in defined)
        if unresolved:
            unresolved_symbol_lines += 1
            findings.append(
                Finding(
                    "error" if pilot_ready else "warning",
                    display_path,
                    line_number,
                    "unresolved assembler symbol(s): " + ", ".join(unresolved),
                )
            )
        if mnemonic in CONTROL_FLOW and re.search(r"\$[A-Fa-f0-9]{6}\b", operand):
            raw_external_edges += 1
            findings.append(
                Finding(
                    "error" if pilot_ready else "warning",
                    display_path,
                    line_number,
                    "raw long control-flow target should be named before assembler-pilot promotion",
                )
            )

    if pilot_ready and not labels:
        findings.append(Finding("error", display_path, 0, "pilot-ready module defines no labels"))

    errors = sum(1 for finding in findings if finding.severity == "error")
    warnings = sum(1 for finding in findings if finding.severity == "warning")
    return ModuleResult(
        source_path=display_path,
        assembler_contract=contract,
        instruction_lines=instruction_lines,
        symbols_defined=len(constants),
        labels_defined=len(labels),
        symbolic_operand_lines=symbolic_operand_lines,
        unresolved_symbol_lines=unresolved_symbol_lines,
        raw_external_control_flow_edges=raw_external_edges,
        errors=errors,
        warnings=warnings,
        findings=tuple(findings),
    )


def build_manifest(plan_path: Path, module_filter: str | None) -> dict[str, Any]:
    plan = load_json(plan_path)
    modules = []
    for module in plan.get("modules", []):
        source_path = str(module["source_path"])
        subsystem = str(module["subsystem"])
        if module_filter and module_filter.lower() not in f"{source_path} {subsystem}".lower():
            continue
        modules.append(validate_module(module))
    return {
        "schema": SCHEMA,
        "generated_by": "tools/validate_c3_assembler_contract.py",
        "inputs": {
            "source_emission_plan": rel(plan_path),
            "module_filter": module_filter,
        },
        "summary": {
            "modules": len(modules),
            "pilot_ready_modules": sum(1 for module in modules if module.assembler_contract == "pilot-ready"),
            "instruction_lines": sum(module.instruction_lines for module in modules),
            "symbolic_operand_lines": sum(module.symbolic_operand_lines for module in modules),
            "unresolved_symbol_lines": sum(module.unresolved_symbol_lines for module in modules),
            "raw_external_control_flow_edges": sum(module.raw_external_control_flow_edges for module in modules),
            "errors": sum(module.errors for module in modules),
            "warnings": sum(module.warnings for module in modules),
        },
        "modules": [asdict(module) for module in modules],
    }


def render_markdown(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    lines = [
        "# C3 assembler contract validation",
        "",
        "This report checks the assembler-facing contract for C3 source prototypes. It does not prove byte-equivalent assembly; it verifies that pilot-ready files have defined local symbols and named external control-flow targets while the source signature/range harness protects ROM bytes separately.",
        "",
        f"- status: `{'OK' if summary['errors'] == 0 else 'FAIL'}`",
        f"- modules: `{summary['modules']}`",
        f"- pilot-ready modules: `{summary['pilot_ready_modules']}`",
        f"- instruction lines: `{summary['instruction_lines']}`",
        f"- symbolic operand lines: `{summary['symbolic_operand_lines']}`",
        f"- unresolved symbol lines: `{summary['unresolved_symbol_lines']}`",
        f"- raw external control-flow edges: `{summary['raw_external_control_flow_edges']}`",
        f"- errors: `{summary['errors']}`",
        f"- warnings: `{summary['warnings']}`",
        "",
        "## Modules",
        "",
        "| Status | Contract | Source Path | Symbols | Labels | Symbolic | Unresolved | Raw External Edges | Errors | Warnings |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for module in manifest["modules"]:
        status = "OK" if module["errors"] == 0 else "FAIL"
        lines.append(
            f"| `{status}` | `{module.get('assembler_contract') or ''}` | `{module['source_path']}` | {module['symbols_defined']} | {module['labels_defined']} | {module['symbolic_operand_lines']} | {module['unresolved_symbol_lines']} | {module['raw_external_control_flow_edges']} | {module['errors']} | {module['warnings']} |"
        )

    findings = [
        finding
        for module in manifest["modules"]
        for finding in module["findings"]
    ]
    if findings:
        lines.extend(["", "## Findings", "", "| Severity | Path | Line | Message |", "| --- | --- | ---: | --- |"])
        for finding in findings[:200]:
            lines.append(
                f"| `{finding['severity']}` | `{finding['source_path']}` | {finding['line']} | {finding['message']} |"
            )
        if len(findings) > 200:
            lines.append(f"| `info` |  |  | {len(findings) - 200} additional findings omitted from markdown; see JSON. |")
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the C3 assembler-facing source contract.")
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--module", help="substring filter for source path/subsystem")
    parser.add_argument("--json-out", type=Path, default=ROOT / "build" / "c3-assembler-contract-validation.json")
    parser.add_argument("--markdown-out", type=Path, default=ROOT / "notes" / "c3-assembler-contract-validation.md")
    parser.add_argument("--strict", action="store_true", help="exit nonzero when errors are found")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    plan_path = resolve_path(args.plan)
    manifest = build_manifest(plan_path, args.module)

    json_out = resolve_path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    markdown_out = resolve_path(args.markdown_out)
    markdown_out.write_text(render_markdown(manifest), encoding="utf-8")

    summary = manifest["summary"]
    print(
        f"Validated {summary['modules']} C3 assembler contract module(s): "
        f"{summary['errors']} errors, {summary['warnings']} warnings."
    )
    print(f"Wrote {rel(json_out)} and {rel(markdown_out)}.")
    return 1 if args.strict and summary["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
