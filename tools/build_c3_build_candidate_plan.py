from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from decode_snippet import OPCODES


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EMISSION_PLAN = ROOT / "build" / "c3-source-emission-plan.json"
DEFAULT_SIGNATURE_VALIDATION = ROOT / "build" / "c3-source-signature-validation.json"
SCHEMA = "earthbound-decomp.c3-build-candidate-plan.v1"

ASM_MNEMONICS = {mnemonic for mnemonic, _mode in OPCODES.values()}
CONTROL_FLOW = {"bcc", "bcs", "beq", "bmi", "bne", "bpl", "bra", "bvc", "bvs", "jmp", "jsl", "jsr"}
BRANCHES = {"bcc", "bcs", "beq", "bmi", "bne", "bpl", "bra", "bvc", "bvs"}
BUILD_BLOCKER_PATTERNS = (
    "not yet wired into an assembler build",
    "not yet a build-candidate",
    "byte-equivalence harness",
    "assembler dialect",
)
WIDTH_TRAP_PATTERNS = (
    "width-sensitive",
    "linear decode loses",
    "interprocedural width",
    "m=16",
    "accumulator state",
)
REGISTER_NAMES = {"A", "X", "Y", "S"}


@dataclass(frozen=True)
class ModuleCandidate:
    source_path: str
    subsystem: str
    prototype_level: str | None
    assembler_contract: str | None
    range_start: str
    range_end: str | None
    source_units: int
    labels_expected: int
    labels_present: int
    instruction_lines: int
    symbolic_operand_lines: int
    unresolved_symbol_lines: int
    local_control_flow_edges: int
    raw_external_control_flow_edges: int
    constants_defined: int
    signature_errors: int | None
    signature_warnings: int | None
    blocker_count: int
    blockers: tuple[str, ...]
    recommended_next_step: str


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def format_address(value: int | None) -> str | None:
    if value is None:
        return None
    return f"C3:{value:04X}"


def strip_comment(line: str) -> str:
    return line.split(";", 1)[0].strip()


def parse_instruction_line(line: str) -> tuple[str, str] | None:
    code = strip_comment(line)
    if not code:
        return None
    if code.endswith(":") or "=" in code:
        return None
    parts = code.split(None, 1)
    mnemonic = parts[0].lower().split(".", 1)[0]
    if mnemonic not in ASM_MNEMONICS:
        return None
    operand = parts[1].strip() if len(parts) > 1 else ""
    return mnemonic, operand


def has_symbolic_operand(operand: str) -> bool:
    return bool(operand_symbols(operand))


def operand_symbols(operand: str) -> set[str]:
    cleaned = re.sub(r"[\$%][0-9A-Fa-f_]+", " ", operand)
    symbols = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", cleaned))
    return {symbol for symbol in symbols if symbol.upper() not in REGISTER_NAMES}


def find_assembler_contract(text: str) -> str | None:
    match = re.search(r"Assembler contract:\s*([A-Za-z0-9_-]+)", text)
    return match.group(1) if match else None


def expected_labels(module: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    for unit in module.get("units", []):
        for label in unit.get("labels", []):
            labels.append(f"{str(label['address']).replace(':', '')}_{label['name']}:")
    return labels


def find_present_labels(text: str) -> set[str]:
    labels: set[str] = set()
    for line in text.splitlines():
        code = strip_comment(line)
        if re.match(r"^[A-Za-z0-9_]+:$", code):
            labels.add(code)
    return labels


def find_defined_symbols(text: str) -> set[str]:
    symbols: set[str] = set()
    for line in text.splitlines():
        code = strip_comment(line)
        const_match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=", code)
        if const_match:
            symbols.add(const_match.group(1))
            continue
        label_match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):$", code)
        if label_match:
            symbols.add(label_match.group(1))
    return symbols


def classify_module(module: dict[str, Any], signature_by_path: dict[str, dict[str, Any]]) -> ModuleCandidate:
    source_path = ROOT / str(module["source_path"])
    text = source_path.read_text(encoding="utf-8", errors="ignore") if source_path.exists() else ""
    instructions: list[tuple[str, str]] = []
    constants = 0
    for line in text.splitlines():
        code = strip_comment(line)
        if re.match(r"^[A-Z0-9_]+\s*=", code):
            constants += 1
        if parsed := parse_instruction_line(line):
            instructions.append(parsed)

    symbolic_operands = sum(1 for _, operand in instructions if has_symbolic_operand(operand))
    defined_symbols = find_defined_symbols(text)
    unresolved_symbol_lines = sum(
        1
        for _, operand in instructions
        if any(symbol not in defined_symbols for symbol in operand_symbols(operand))
    )
    local_edges = sum(
        1
        for mnemonic, operand in instructions
        if mnemonic in CONTROL_FLOW and re.search(r"\bC3[A-F0-9]{4}_[A-Za-z0-9_]+", operand)
    )
    raw_external_edges = sum(
        1
        for mnemonic, operand in instructions
        if mnemonic in CONTROL_FLOW and re.search(r"\$[A-Fa-f0-9]{6}\b", operand)
    )

    present_labels = find_present_labels(text)
    expected = expected_labels(module)
    labels_present = sum(1 for label in expected if label in present_labels)

    blockers: list[str] = []
    signature_result = signature_by_path.get(str(module["source_path"]))
    signature_errors: int | None = None
    signature_warnings: int | None = None
    if signature_result is None:
        blockers.append("source signature validation has not been run")
    else:
        signature_errors = int(signature_result.get("errors", 0))
        signature_warnings = int(signature_result.get("warnings", 0))
        if signature_errors:
            blockers.append(f"source signature validation reports {signature_errors} error(s)")
    level = module.get("prototype_level")
    if level != "build-candidate":
        blockers.append(f"prototype level is `{level}`")
    if module.get("end") is None:
        blockers.append("module has an open-ended source unit boundary")
    lower_text = text.lower()
    assembler_contract = find_assembler_contract(text)
    for pattern in BUILD_BLOCKER_PATTERNS:
        if pattern in lower_text:
            blockers.append(f"header/body notes still mention `{pattern}`")
    width_note_is_covered = (
        module.get("prototype_level") == "build-candidate"
        and "source signature validation" in lower_text
        and "build/c3-build-candidate-ranges.json" in lower_text
    )
    if any(pattern in lower_text for pattern in WIDTH_TRAP_PATTERNS) and not width_note_is_covered:
        blockers.append("width-sensitive decode note needs byte-match harness coverage")
    if unresolved_symbol_lines:
        blockers.append(f"{unresolved_symbol_lines} instruction line(s) use unresolved assembler symbols")
    if raw_external_edges:
        blockers.append(f"{raw_external_edges} external call/jump edges still use raw long addresses")

    if module.get("end") is None:
        recommended = "close the source/data boundary, then add byte-range extraction to the harness"
    elif signature_errors:
        recommended = "fix source/ROM signature drift before assembler hardening"
    elif unresolved_symbol_lines:
        recommended = "define assembler aliases for unresolved symbolic operands"
    elif raw_external_edges:
        recommended = "replace raw external long control-flow targets with named absolute aliases"
    elif "width-sensitive decode note needs byte-match harness coverage" in blockers:
        recommended = "promote width-sensitive return-state facts into byte-equivalence tests"
    elif assembler_contract == "pilot-ready":
        recommended = "ready for first real assembler byte-equivalence pilot"
    else:
        recommended = "mark as assembler pilot after contract validation"

    return ModuleCandidate(
        source_path=str(module["source_path"]),
        subsystem=str(module["subsystem"]),
        prototype_level=str(level) if level is not None else None,
        assembler_contract=assembler_contract,
        range_start=format_address(int(module["start"])) or "unknown",
        range_end=format_address(module.get("end")),
        source_units=len(module.get("units", [])),
        labels_expected=len(expected),
        labels_present=labels_present,
        instruction_lines=len(instructions),
        symbolic_operand_lines=symbolic_operands,
        unresolved_symbol_lines=unresolved_symbol_lines,
        local_control_flow_edges=local_edges,
        raw_external_control_flow_edges=raw_external_edges,
        constants_defined=constants,
        signature_errors=signature_errors,
        signature_warnings=signature_warnings,
        blocker_count=len(blockers),
        blockers=tuple(dict.fromkeys(blockers)),
        recommended_next_step=recommended,
    )


def render_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# C3 build-candidate hardening plan",
        "",
        "Generated from the C3 source-emission plan and current `src/c3` prototype artifacts. This tracks the gap between annotated source prototypes and build-candidate source that can enter a byte-equivalence harness.",
        "",
        "## Summary",
        "",
    ]
    summary = manifest["summary"]
    for key in (
        "modules",
        "annotated_asm_modules",
        "build_candidate_modules",
        "open_ended_modules",
        "signature_clean_modules",
        "symbolic_operand_lines",
        "unresolved_symbol_lines",
        "local_control_flow_edges",
    ):
        lines.append(f"- {key.replace('_', ' ')}: `{summary[key]}`")

    lines.extend(
        [
            "",
            "## Module Queue",
            "",
            "| Blockers | Signature | Level | Asm Contract | Source Path | Range | Instr. | Symbolic | Unresolved | Raw Ext. | Recommendation |",
            "| ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for module in manifest["modules"]:
        lines.append(
            "| {blockers} | `{signature}` | `{level}` | `{contract}` | `{path}` | `{start}..{end}` | {instructions} | {symbols} | {unresolved} | {raw_external} | {recommendation} |".format(
                blockers=module["blocker_count"],
                signature=(
                    "not-run"
                    if module.get("signature_errors") is None
                    else "OK"
                    if module.get("signature_errors") == 0
                    else f"FAIL:{module.get('signature_errors')}"
                ),
                level=module.get("prototype_level") or "",
                contract=module.get("assembler_contract") or "",
                path=module["source_path"],
                start=module["range_start"],
                end=module.get("range_end") or "unknown",
                instructions=module["instruction_lines"],
                symbols=module["symbolic_operand_lines"],
                unresolved=module["unresolved_symbol_lines"],
                raw_external=module["raw_external_control_flow_edges"],
                recommendation=module["recommended_next_step"],
            )
        )

    lines.extend(["", "## Blockers", ""])
    for module in manifest["modules"]:
        lines.extend([f"### `{module['source_path']}`", ""])
        if module["blockers"]:
            for blocker in module["blockers"]:
                lines.append(f"- {blocker}")
        else:
            lines.append("- none")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_manifest(plan_path: Path, signature_path: Path | None) -> dict[str, Any]:
    plan = load_json(plan_path)
    signature_by_path: dict[str, dict[str, Any]] = {}
    if signature_path and signature_path.exists():
        signature = load_json(signature_path)
        signature_by_path = {
            str(module["source_path"]): module
            for module in signature.get("modules", [])
        }
    modules = [classify_module(module, signature_by_path) for module in plan.get("modules", [])]
    modules.sort(key=lambda module: (module.blocker_count, module.symbolic_operand_lines, module.source_path))
    counter = Counter(module.prototype_level for module in modules)
    manifest = {
        "schema": SCHEMA,
        "generated_by": "tools/build_c3_build_candidate_plan.py",
        "inputs": {
            "source_emission_plan": rel(plan_path),
            "source_signature_validation": rel(signature_path) if signature_path else None,
        },
        "summary": {
            "modules": len(modules),
            "annotated_asm_modules": counter.get("annotated-asm", 0),
            "build_candidate_modules": counter.get("build-candidate", 0),
            "open_ended_modules": sum(1 for module in modules if module.range_end is None),
            "signature_clean_modules": sum(1 for module in modules if module.signature_errors == 0),
            "symbolic_operand_lines": sum(module.symbolic_operand_lines for module in modules),
            "unresolved_symbol_lines": sum(module.unresolved_symbol_lines for module in modules),
            "local_control_flow_edges": sum(module.local_control_flow_edges for module in modules),
        },
        "modules": [asdict(module) for module in modules],
    }
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the C3 build-candidate hardening plan.")
    parser.add_argument("--plan", type=Path, default=DEFAULT_EMISSION_PLAN)
    parser.add_argument("--signature-validation", type=Path, default=DEFAULT_SIGNATURE_VALIDATION)
    parser.add_argument("--json-out", type=Path, default=ROOT / "build" / "c3-build-candidate-plan.json")
    parser.add_argument("--markdown-out", type=Path, default=ROOT / "notes" / "c3-build-candidate-plan.md")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    plan_path = resolve_path(args.plan)
    signature_path = resolve_path(args.signature_validation) if args.signature_validation else None
    manifest = build_manifest(plan_path, signature_path)

    json_out = resolve_path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    markdown_out = resolve_path(args.markdown_out)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(render_markdown(manifest), encoding="utf-8")

    print(
        f"Wrote {rel(json_out)} and {rel(markdown_out)} "
        f"({manifest['summary']['modules']} modules)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
