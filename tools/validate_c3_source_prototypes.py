from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "build" / "c3-source-emission-plan.json"
VALID_LEVELS = {"contract-sketch", "annotated-asm", "build-candidate"}


@dataclass(frozen=True)
class Finding:
    severity: str
    path: str
    message: str


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_plan(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compact_address(address: str) -> str:
    return address.replace(":", "")


def format_address(value: int | None) -> str | None:
    if value is None:
        return None
    return f"C3:{value:04X}"


def range_text(unit: dict[str, Any]) -> str | None:
    start = format_address(unit.get("start"))
    end = format_address(unit.get("end"))
    if start is None or end is None:
        return None
    return f"{start}..{end}"


def find_level(text: str) -> str | None:
    match = re.search(r"Prototype level:\s*([A-Za-z0-9_-]+)", text)
    if not match:
        return None
    return match.group(1)


def expected_label_variants(label: dict[str, Any]) -> tuple[str, ...]:
    address = str(label["address"])
    name = str(label["name"])
    compact = compact_address(address)
    return (
        f"{compact}_{name}:",
        f"{compact}_{name}",
        f"{address} {name}",
        f"{address}` `{name}",
    )


def text_contains_any(text: str, variants: tuple[str, ...]) -> bool:
    return any(variant in text for variant in variants)


def validate_present_module(module: dict[str, Any], path: Path) -> list[Finding]:
    findings: list[Finding] = []
    text = path.read_text(encoding="utf-8", errors="ignore")
    display_path = rel(path)

    level = find_level(text)
    if level is None:
        findings.append(Finding("error", display_path, "missing `Prototype level: ...` header"))
    elif level not in VALID_LEVELS:
        findings.append(Finding("error", display_path, f"unknown prototype level `{level}`"))

    if "notes/c3-source-emission-plan.md" not in text:
        findings.append(Finding("error", display_path, "missing link/reference to notes/c3-source-emission-plan.md"))

    for unit in module.get("units", []):
        expected_range = range_text(unit)
        if expected_range and expected_range not in text:
            findings.append(
                Finding(
                    "error",
                    display_path,
                    f"missing planned range `{expected_range}` for {unit['address']} {unit['name']}",
                )
            )
        for label in unit.get("labels", []):
            if not text_contains_any(text, expected_label_variants(label)):
                findings.append(
                    Finding(
                        "error",
                        display_path,
                        f"missing planned label `{label['address']}` `{label['name']}`",
                    )
                )

    if level == "contract-sketch" and "pseudocode" not in text.lower():
        findings.append(
            Finding(
                "warning",
                display_path,
                "`contract-sketch` file should explicitly describe pseudocode-only bodies",
            )
        )
    if level == "annotated-asm":
        lower_text = text.lower()
        if "original instruction flow" not in lower_text:
            findings.append(
                Finding(
                    "error",
                    display_path,
                    "`annotated-asm` file should explicitly state that original instruction flow is preserved",
                )
            )
        if "pseudocode-only" in lower_text:
            findings.append(
                Finding(
                    "error",
                    display_path,
                    "`annotated-asm` file still describes its bodies as pseudocode-only",
                )
            )

    return findings


def validate_plan(plan: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    for module in plan.get("modules", []):
        source_path = ROOT / str(module["source_path"])
        status = str(module.get("artifact_status", "planned"))
        exists = source_path.exists()
        display_path = rel(source_path)

        if status == "planned" and exists:
            findings.append(Finding("error", display_path, "emission plan says `planned`, but file exists"))
            findings.extend(validate_present_module(module, source_path))
            continue
        if status != "planned" and not exists:
            findings.append(Finding("error", display_path, f"emission plan says `{status}`, but file is missing"))
            continue
        if status != "planned":
            findings.extend(validate_present_module(module, source_path))
    return findings


def render_markdown(findings: list[Finding]) -> str:
    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]
    lines = [
        "# C3 source prototype validation",
        "",
        f"- status: `{'OK' if not errors else 'FAIL'}`",
        f"- errors: `{len(errors)}`",
        f"- warnings: `{len(warnings)}`",
    ]
    if findings:
        lines.extend(["", "| Severity | Path | Message |", "| --- | --- | --- |"])
        for finding in findings:
            lines.append(f"| `{finding.severity}` | `{finding.path}` | {finding.message} |")
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate C3 source prototype files against the emission plan.")
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--markdown-out", type=Path, default=ROOT / "notes" / "c3-source-prototype-validation.md")
    parser.add_argument("--strict", action="store_true", help="exit nonzero when errors are found")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    plan_path = resolve_path(args.plan)
    plan = load_plan(plan_path)
    findings = validate_plan(plan)
    markdown_out = resolve_path(args.markdown_out)
    markdown_out.write_text(render_markdown(findings), encoding="utf-8")

    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]
    print(f"Validated C3 source prototypes: {len(errors)} errors, {len(warnings)} warnings.")
    print(f"Wrote {rel(markdown_out)}.")
    return 1 if args.strict and errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
