from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASELINE_PROJECT = ROOT / "build" / "coilsnake" / "baseline-project"
DEFAULT_SCRIPTDUMP_PROJECT = ROOT / "build" / "coilsnake" / "scriptdump-project"
DEFAULT_BASELINE_REBUILD = ROOT / "build" / "coilsnake" / "baseline-rebuild.sfc"
DEFAULT_SCRIPTDUMP_REBUILD = ROOT / "build" / "coilsnake" / "scriptdump-rebuild.sfc"
DEFAULT_JSON_OUT = ROOT / "build" / "coilsnake" / "reports" / "coilsnake-scriptdump-report.json"
DEFAULT_MANIFEST_OUT = ROOT / "manifests" / "coilsnake-scriptdump-summary.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "coilsnake-scriptdump-report.md"


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_bytes(path: Path) -> bytes | None:
    if not path.is_file():
        return None
    return path.read_bytes()


def file_offset_to_hirom(offset: int | None) -> str | None:
    if offset is None:
        return None
    return f"{0xC0 + (offset // 0x10000):02X}:{offset & 0xFFFF:04X}"


def diff_bytes(base_path: Path, other_path: Path) -> dict[str, Any]:
    base = load_bytes(base_path)
    other = load_bytes(other_path)
    if base is None:
        return {"base": rel(base_path), "other": rel(other_path), "status": "missing-base"}
    if other is None:
        return {"base": rel(base_path), "other": rel(other_path), "status": "missing-other"}

    limit = min(len(base), len(other))
    changed_bytes = 0
    runs: list[dict[str, int | str]] = []
    run_start: int | None = None
    for offset in range(limit):
        if base[offset] != other[offset]:
            changed_bytes += 1
            if run_start is None:
                run_start = offset
        elif run_start is not None:
            runs.append({"start": run_start, "end_exclusive": offset, "length": offset - run_start})
            run_start = None
    if run_start is not None:
        runs.append({"start": run_start, "end_exclusive": limit, "length": limit - run_start})

    if len(base) != len(other):
        runs.append(
            {
                "start": limit,
                "end_exclusive": max(len(base), len(other)),
                "length": abs(len(base) - len(other)),
                "kind": "size-delta",
            }
        )
        changed_bytes += abs(len(base) - len(other))

    first_changed = int(runs[0]["start"]) if runs else None
    last_changed = int(runs[-1]["end_exclusive"]) if runs else None
    return {
        "base": rel(base_path),
        "other": rel(other_path),
        "status": "identical" if changed_bytes == 0 else "different",
        "base_size": len(base),
        "other_size": len(other),
        "changed_bytes": changed_bytes,
        "contiguous_changed_runs": len(runs),
        "first_changed_offset": f"0x{first_changed:06X}" if first_changed is not None else None,
        "first_changed_hirom": file_offset_to_hirom(first_changed),
        "last_changed_offset_exclusive": f"0x{last_changed:06X}" if last_changed is not None else None,
        "last_changed_hirom_exclusive": file_offset_to_hirom(last_changed),
        "sample_runs": [
            {
                "start": f"0x{int(run['start']):06X}",
                "start_hirom": file_offset_to_hirom(int(run["start"])),
                "end_exclusive": f"0x{int(run['end_exclusive']):06X}",
                "end_hirom_exclusive": file_offset_to_hirom(int(run["end_exclusive"])),
                "length": run["length"],
                **({"kind": run["kind"]} if "kind" in run else {}),
            }
            for run in runs[:20]
        ],
    }


def file_records(root: Path) -> list[dict[str, Any]]:
    if not root.is_dir():
        return []
    records = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        text_line_count: int | None = None
        if path.suffix.lower() in {".ccs", ".txt"}:
            try:
                text_line_count = len(path.read_text(encoding="utf-8").splitlines())
            except UnicodeDecodeError:
                text_line_count = None
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "extension": path.suffix.lower() or "<none>",
                "size": path.stat().st_size,
                "line_count": text_line_count,
            }
        )
    return records


def summarize_files(records: list[dict[str, Any]]) -> dict[str, Any]:
    extensions = Counter(str(record["extension"]) for record in records)
    ccs_files = [record for record in records if record["extension"] == ".ccs"]
    data_modules = [
        record
        for record in ccs_files
        if Path(str(record["path"])).stem.startswith("data_")
    ]
    line_counts = [
        int(record["line_count"])
        for record in records
        if isinstance(record.get("line_count"), int)
    ]
    sizes = [int(record["size"]) for record in records]
    return {
        "file_count": len(records),
        "total_file_bytes": sum(sizes),
        "extensions": dict(sorted(extensions.items())),
        "ccs_file_count": len(ccs_files),
        "data_module_count": len(data_modules),
        "main_ccs_present": any(record["path"] == "main.ccs" for record in records),
        "summary_txt_present": any(record["path"] == "summary.txt" for record in records),
        "total_text_lines": sum(line_counts),
        "smallest_file_bytes": min(sizes) if sizes else 0,
        "largest_file_bytes": max(sizes) if sizes else 0,
    }


def compare_file_sets(baseline_records: list[dict[str, Any]], scriptdump_records: list[dict[str, Any]]) -> dict[str, Any]:
    baseline = {str(record["path"]): record for record in baseline_records}
    scriptdump = {str(record["path"]): record for record in scriptdump_records}
    added = sorted(set(scriptdump) - set(baseline))
    removed = sorted(set(baseline) - set(scriptdump))
    common = sorted(set(baseline) & set(scriptdump))
    changed_size = [
        path
        for path in common
        if int(baseline[path]["size"]) != int(scriptdump[path]["size"])
    ]
    return {
        "added_file_count": len(added),
        "removed_file_count": len(removed),
        "common_file_count": len(common),
        "changed_size_count": len(changed_size),
        "added_file_sample": added[:20],
        "removed_file_sample": removed[:20],
        "changed_size_sample": changed_size[:20],
    }


def build_report(
    *,
    baseline_project: Path,
    scriptdump_project: Path,
    baseline_rebuild: Path,
    scriptdump_rebuild: Path,
) -> dict[str, Any]:
    baseline_ccscript = baseline_project / "ccscript"
    scriptdump_ccscript = scriptdump_project / "ccscript"
    baseline_records = file_records(baseline_ccscript)
    scriptdump_records = file_records(scriptdump_ccscript)
    return {
        "schema": "earthbound-decomp.coilsnake-scriptdump-summary.v1",
        "generated_by": "tools/build_coilsnake_scriptdump_report.py",
        "safety_note": "This report stores file names, sizes, counts, and ROM diff spans only; it does not store CCScript payload text.",
        "scriptdump": {
            "command": "coilsnake-cli --verbose scriptdump \"EarthBound (USA).sfc\" build/coilsnake/scriptdump-project",
            "project_dir": rel(scriptdump_project),
            "ccscript_dir": rel(scriptdump_ccscript),
            "observed_result": "scriptdump succeeded and populated ccscript files in an ignored project copy",
        },
        "compile_roundtrip": {
            "command": "coilsnake-cli --verbose compile build/coilsnake/scriptdump-project build/coilsnake/base-expanded.sfc build/coilsnake/scriptdump-rebuild.sfc",
            "rebuilt_rom": rel(scriptdump_rebuild),
            "observed_result": "scriptdump project compiled successfully against the expanded base ROM",
            "diff_against_baseline_rebuild": diff_bytes(baseline_rebuild, scriptdump_rebuild),
        },
        "baseline_ccscript_summary": summarize_files(baseline_records),
        "scriptdump_ccscript_summary": summarize_files(scriptdump_records),
        "baseline_to_scriptdump_delta": compare_file_sets(baseline_records, scriptdump_records),
        "scriptdump_files": scriptdump_records,
    }


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def markdown(report: dict[str, Any]) -> str:
    scriptdump = report["scriptdump"]
    roundtrip = report["compile_roundtrip"]
    summary = report["scriptdump_ccscript_summary"]
    baseline_summary = report["baseline_ccscript_summary"]
    delta = report["baseline_to_scriptdump_delta"]
    diff = roundtrip["diff_against_baseline_rebuild"]

    lines = [
        "# CoilSnake Scriptdump Report",
        "",
        "This note records a payload-free summary of CoilSnake `scriptdump` output.",
        "Generated CCScript files, text payloads, and rebuilt ROMs stay under ignored `build/coilsnake/`.",
        "",
        "## Run",
        "",
        f"- Scriptdump project: `{scriptdump['project_dir']}`",
        f"- CCScript directory: `{scriptdump['ccscript_dir']}`",
        f"- Result: {scriptdump['observed_result']}.",
        f"- Compile roundtrip: {roundtrip['observed_result']}.",
        "",
        "## Output Shape",
        "",
        "| Source | Files | `.ccs` files | Data modules | Bytes | Text lines |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        (
            f"| Baseline `ccscript/` | {baseline_summary['file_count']} | "
            f"{baseline_summary['ccs_file_count']} | {baseline_summary['data_module_count']} | "
            f"{baseline_summary['total_file_bytes']} | {baseline_summary['total_text_lines']} |"
        ),
        (
            f"| Scriptdump `ccscript/` | {summary['file_count']} | "
            f"{summary['ccs_file_count']} | {summary['data_module_count']} | "
            f"{summary['total_file_bytes']} | {summary['total_text_lines']} |"
        ),
        "",
        "Delta from the baseline project:",
        "",
        f"- added files: `{delta['added_file_count']}`",
        f"- removed files: `{delta['removed_file_count']}`",
        f"- common files with changed size: `{delta['changed_size_count']}`",
        f"- `main.ccs` present: `{str(summary['main_ccs_present']).lower()}`",
        f"- `summary.txt` present: `{str(summary['summary_txt_present']).lower()}`",
        "",
        "## Roundtrip Diff",
        "",
        f"- Compared against: `{diff.get('base')}`",
        f"- Rebuilt ROM: `{diff.get('other')}`",
        f"- Status: `{diff.get('status')}`",
        f"- Changed bytes: `{diff.get('changed_bytes')}`",
        f"- Changed runs: `{diff.get('contiguous_changed_runs')}`",
        f"- First changed offset: `{diff.get('first_changed_offset')}` (`{diff.get('first_changed_hirom')}`)",
        (
            f"- Last changed offset exclusive: `{diff.get('last_changed_offset_exclusive')}` "
            f"(`{diff.get('last_changed_hirom_exclusive')}`)"
        ),
        "",
        "Interpretation:",
        "",
        "- `scriptdump` is usable as an authoring oracle because its generated project compiles.",
        "- The compiled scriptdump project should be treated as compiler-normalized output unless the diff is byte-identical to `baseline-rebuild.sfc`.",
        "- Any command-lowering claim still needs a tiny edited CCScript experiment; compare that edited rebuild against the unedited scriptdump rebuild to isolate the edit when this broad roundtrip is normalized.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a payload-free CoilSnake scriptdump report.")
    parser.add_argument("--baseline-project", type=Path, default=DEFAULT_BASELINE_PROJECT)
    parser.add_argument("--scriptdump-project", type=Path, default=DEFAULT_SCRIPTDUMP_PROJECT)
    parser.add_argument("--baseline-rebuild", type=Path, default=DEFAULT_BASELINE_REBUILD)
    parser.add_argument("--scriptdump-rebuild", type=Path, default=DEFAULT_SCRIPTDUMP_REBUILD)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--manifest-out", type=Path, default=DEFAULT_MANIFEST_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN_OUT)
    args = parser.parse_args()

    for path, description in (
        (args.baseline_project, "baseline project"),
        (args.scriptdump_project, "scriptdump project"),
        (args.baseline_rebuild, "baseline rebuild ROM"),
        (args.scriptdump_rebuild, "scriptdump rebuild ROM"),
    ):
        if not path.exists():
            raise SystemExit(f"{description} not found: {path}")

    report = build_report(
        baseline_project=args.baseline_project.resolve(),
        scriptdump_project=args.scriptdump_project.resolve(),
        baseline_rebuild=args.baseline_rebuild.resolve(),
        scriptdump_rebuild=args.scriptdump_rebuild.resolve(),
    )
    manifest = {key: value for key, value in report.items() if key != "scriptdump_files"}
    write_json(args.json_out, report)
    write_json(args.manifest_out, manifest)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.write_text(markdown(report), encoding="utf-8")
    print(f"Wrote {rel(args.json_out)}")
    print(f"Wrote {rel(args.manifest_out)}")
    print(f"Wrote {rel(args.markdown_out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
