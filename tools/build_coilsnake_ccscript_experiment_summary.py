from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EXPERIMENTS_DIR = ROOT / "build" / "coilsnake" / "edit-experiments"
DEFAULT_MANIFEST_OUT = ROOT / "manifests" / "coilsnake-ccscript-experiments.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "coilsnake-ccscript-experiments.md"


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def file_offset_to_hirom(offset: int | None) -> str | None:
    if offset is None:
        return None
    return f"{0xC0 + (offset // 0x10000):02X}:{offset & 0xFFFF:04X}"


def parse_hex_offset(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    try:
        return int(value, 16)
    except ValueError:
        return None


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_report(path: Path) -> dict[str, Any]:
    report = load_json(path)
    diff = report.get("diff") if isinstance(report.get("diff"), dict) else {}
    compile_result = report.get("compile") if isinstance(report.get("compile"), dict) else {}
    first_offset = parse_hex_offset(diff.get("first_changed_offset"))
    last_offset = parse_hex_offset(diff.get("last_changed_offset_exclusive"))
    return {
        "experiment_id": report.get("experiment_id"),
        "status": report.get("status"),
        "resource_family": report.get("resource_family"),
        "source_file": str(report.get("source_file", "")).replace("\\", "/"),
        "edit": report.get("edit"),
        "evidence_level": report.get("evidence_level"),
        "comparison_base": report.get("comparison_base"),
        "report": rel(path),
        "compile": {
            "returncode": compile_result.get("returncode"),
            "timed_out": bool(compile_result.get("timed_out")),
        },
        "diff": {
            "status": diff.get("status"),
            "changed_bytes": diff.get("changed_bytes"),
            "contiguous_changed_runs": diff.get("contiguous_changed_runs"),
            "first_changed_offset": diff.get("first_changed_offset"),
            "first_changed_hirom": file_offset_to_hirom(first_offset),
            "last_changed_offset_exclusive": diff.get("last_changed_offset_exclusive"),
            "last_changed_hirom_exclusive": file_offset_to_hirom(last_offset),
        },
    }


def find_reports(experiments_dir: Path) -> list[Path]:
    if not experiments_dir.is_dir():
        return []
    return sorted(
        path
        for path in experiments_dir.glob("ccscript-*/experiment-report.json")
        if path.is_file()
    )


def build_summary(experiments_dir: Path) -> dict[str, Any]:
    experiments = [summarize_report(path) for path in find_reports(experiments_dir)]
    return {
        "schema": "earthbound-decomp.coilsnake-ccscript-experiments.v1",
        "generated_by": "tools/build_coilsnake_ccscript_experiment_summary.py",
        "safety_note": "This manifest stores CCScript experiment metadata and ROM diff spans only; it does not store generated CCScript payload text.",
        "experiments_dir": rel(experiments_dir),
        "experiment_count": len(experiments),
        "experiments": experiments,
    }


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# CoilSnake CCScript Experiments",
        "",
        "This note summarizes payload-free CCScript edit experiments.",
        "Generated CCScript projects and rebuilt ROMs remain under ignored `build/coilsnake/`.",
        "",
        "## Summary",
        "",
        f"- Experiments: `{summary['experiment_count']}`",
        f"- Experiment root: `{summary['experiments_dir']}`",
        "",
        "| Experiment | Source | Comparison base | Changed bytes | Changed span | Evidence |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for experiment in summary["experiments"]:
        diff = experiment["diff"]
        changed = diff.get("changed_bytes")
        start = diff.get("first_changed_offset")
        start_hirom = diff.get("first_changed_hirom")
        end = diff.get("last_changed_offset_exclusive")
        end_hirom = diff.get("last_changed_hirom_exclusive")
        if start and end:
            span = f"`{start}` (`{start_hirom}`)..`{end}` (`{end_hirom}`)"
        else:
            span = "-"
        lines.append(
            "| "
            f"`{experiment['experiment_id']}` | "
            f"`{experiment['source_file']}` | "
            f"`{experiment['comparison_base']}` | "
            f"`{changed}` | "
            f"{span} | "
            f"`{experiment['evidence_level']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- CCScript edit probes should compare against an unedited scriptdump rebuild when the scriptdump roundtrip itself is compiler-normalized.",
            "- These probes can prove CCScript lowering behavior, but runtime text VM naming still needs local parser or handler evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a payload-free CoilSnake CCScript experiment summary.")
    parser.add_argument("--experiments-dir", type=Path, default=DEFAULT_EXPERIMENTS_DIR)
    parser.add_argument("--manifest-out", type=Path, default=DEFAULT_MANIFEST_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN_OUT)
    args = parser.parse_args()

    if not args.experiments_dir.exists():
        raise SystemExit(f"Experiments directory not found: {args.experiments_dir}")
    summary = build_summary(args.experiments_dir.resolve())
    write_json(args.manifest_out, summary)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.write_text(markdown(summary), encoding="utf-8")
    print(f"Wrote {rel(args.manifest_out)}")
    print(f"Wrote {rel(args.markdown_out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
