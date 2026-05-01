from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import rom_tools


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CROSSWALK = ROOT / "manifests" / "coilsnake-crosswalk.json"
DEFAULT_FIELD_SEMANTICS = ROOT / "manifests" / "coilsnake-field-semantics.json"
DEFAULT_BASELINE_REBUILD = ROOT / "build" / "coilsnake" / "baseline-rebuild.sfc"
DEFAULT_JSON_OUT = ROOT / "build" / "coilsnake" / "reports" / "coilsnake-rebuild-original-layout-report.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "coilsnake-rebuild-original-layout-report.md"

RANGE_RE = re.compile(
    r"(?P<start_bank>[0-9A-Fa-f]{2}):(?P<start>[0-9A-Fa-f]{4,5})\.\."
    r"(?P<end_bank>[0-9A-Fa-f]{2}):(?P<end>[0-9A-Fa-f]{4,5})"
)


@dataclass(frozen=True)
class Address:
    offset: int

    @property
    def bank(self) -> int:
        return rom_tools.canonical_bank_for_file_offset(self.offset)

    @property
    def address(self) -> int:
        return self.offset % 0x10000

    @property
    def offset_text(self) -> str:
        return f"0x{self.offset:06X}"

    @property
    def hirom(self) -> str:
        return f"{self.bank:02X}:{self.address:04X}"


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_hex(value: str) -> int:
    return int(value, 16)


def joinable_experiments(crosswalk: dict[str, Any]) -> list[dict[str, Any]]:
    experiments: list[dict[str, Any]] = []
    controlled = crosswalk.get("controlled_experiments", {})
    if not isinstance(controlled, dict):
        return experiments

    for experiment_id, experiment in sorted(controlled.items()):
        if not isinstance(experiment, dict):
            continue
        diff = experiment.get("diff")
        if not isinstance(diff, dict):
            continue
        if experiment.get("evidence_level") != "diff-confirmed":
            continue
        if diff.get("status") != "different":
            continue
        offset_text = diff.get("first_changed_offset")
        if not isinstance(offset_text, str):
            continue
        experiments.append(
            {
                "experiment_id": experiment_id,
                "source_file": experiment.get("source_file"),
                "edit": experiment.get("edit"),
                "resource_family": experiment.get("resource_family"),
                "offset": parse_hex(offset_text),
                "changed_bytes": diff.get("changed_bytes"),
                "contiguous_changed_runs": diff.get("contiguous_changed_runs"),
            }
        )
    return experiments


def load_field_semantics(path: Path) -> dict[str, dict[str, Any]]:
    data = load_json(path)
    semantics = data.get("field_semantics", {})
    if not isinstance(semantics, dict):
        return {}
    return {str(key): value for key, value in semantics.items() if isinstance(value, dict)}


def parse_range(line: str) -> list[tuple[int, int, int, int]]:
    ranges: list[tuple[int, int, int, int]] = []
    for match in RANGE_RE.finditer(line):
        ranges.append(
            (
                int(match.group("start_bank"), 16),
                int(match.group("start"), 16),
                int(match.group("end_bank"), 16),
                int(match.group("end"), 16),
            )
        )
    return ranges


def address_in_range(address: Address, parsed_range: tuple[int, int, int, int]) -> bool:
    start_bank, start, end_bank, end = parsed_range
    return start_bank == end_bank and address.bank == start_bank and start <= address.address < end


def range_span(parsed_range: tuple[int, int, int, int]) -> int:
    start_bank, start, end_bank, end = parsed_range
    if start_bank != end_bank:
        return 0x1000000
    return max(0, end - start)


def find_contract_matches(address: Address) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for path in sorted((ROOT / "notes").glob("*.md")):
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for line_number, line in enumerate(lines, start=1):
            parsed_ranges = parse_range(line)
            hits = [item for item in parsed_ranges if address_in_range(address, item)]
            if not hits:
                continue
            label_match = re.search(r"`([^`]+)`", line)
            matches.append(
                {
                    "path": rel(path),
                    "line": line_number,
                    "label": label_match.group(1) if label_match else None,
                    "ranges": [
                        f"{start_bank:02X}:{start:04X}..{end_bank:02X}:{end:04X}"
                        for start_bank, start, end_bank, end in hits
                    ],
                    "span": min(range_span(item) for item in hits),
                }
            )
    return sorted(matches, key=lambda item: (item["span"], item["path"], item["line"]))[:8]


def find_all(data: bytes, needle: bytes, cap: int) -> tuple[int, list[int], bool]:
    if not needle:
        return 0, [], False
    count = 0
    samples: list[int] = []
    start = 0
    truncated = False
    while True:
        index = data.find(needle, start)
        if index < 0:
            break
        count += 1
        if len(samples) < cap:
            samples.append(index)
        else:
            truncated = True
        start = index + 1
    return count, samples, truncated


def masked_search(
    data: bytes,
    fixed_positions: dict[int, int],
    span: int,
    cap: int,
) -> tuple[int, list[int], bool]:
    count = 0
    samples: list[int] = []
    truncated = False
    if not fixed_positions or span <= 0:
        return count, samples, truncated
    limit = len(data) - span + 1
    for offset in range(max(0, limit)):
        if all(data[offset + rel_offset] == value for rel_offset, value in fixed_positions.items()):
            count += 1
            if len(samples) < cap:
                samples.append(offset)
            else:
                truncated = True
    return count, samples, truncated


def safe_window(data: bytes, center: int, size: int) -> tuple[int, bytes]:
    half = size // 2
    start = max(0, center - half)
    end = min(len(data), start + size)
    start = max(0, end - size)
    return start, data[start:end]


def analyze_experiment(
    experiment: dict[str, Any],
    original: bytes,
    rebuilt: bytes,
    field_semantics: dict[str, dict[str, Any]],
    sample_cap: int,
) -> dict[str, Any]:
    offset = int(experiment["offset"])
    address = Address(offset)
    same_offset_available = offset < len(original)
    changed_byte_same = same_offset_available and original[offset] == rebuilt[offset]
    exact_windows: list[dict[str, Any]] = []
    for size in (4, 8, 16, 32):
        start, needle = safe_window(rebuilt, offset, size)
        count, samples, truncated = find_all(original, needle, sample_cap)
        exact_windows.append(
            {
                "window_size": len(needle),
                "rebuilt_window_start": Address(start).offset_text,
                "original_match_count": count,
                "sample_original_offsets": [Address(sample).offset_text for sample in samples],
                "sample_original_hirom": [Address(sample).hirom for sample in samples],
                "truncated": truncated,
                "same_offset_window_match": same_offset_available
                and start + len(needle) <= len(original)
                and original[start : start + len(needle)] == needle,
            }
        )
    best_exact = next(
        (
            window
            for window in reversed(exact_windows)
            if window["same_offset_window_match"]
        ),
        None,
    )
    return {
        "experiment_id": experiment["experiment_id"],
        "source_file": experiment.get("source_file"),
        "edit": experiment.get("edit"),
        "resource_family": experiment.get("resource_family"),
        "rebuilt_offset": address.offset_text,
        "rebuilt_hirom": address.hirom,
        "changed_bytes": experiment.get("changed_bytes"),
        "same_offset_available_in_original": same_offset_available,
        "changed_byte_matches_original_same_offset": changed_byte_same,
        "best_same_offset_exact_window": best_exact["window_size"] if best_exact else 0,
        "exact_window_searches": exact_windows,
        "field_semantics": field_semantics.get(experiment["experiment_id"]),
    }


def cluster_experiments(experiments: list[dict[str, Any]], max_span: int) -> list[list[dict[str, Any]]]:
    clusters: list[list[dict[str, Any]]] = []
    by_source: dict[str, list[dict[str, Any]]] = {}
    for experiment in experiments:
        by_source.setdefault(str(experiment.get("source_file") or "unknown"), []).append(experiment)

    for source_file in sorted(by_source):
        current: list[dict[str, Any]] = []
        for experiment in sorted(by_source[source_file], key=lambda item: int(item["offset"])):
            if not current:
                current = [experiment]
                continue
            proposed = current + [experiment]
            span = max(int(item["offset"]) for item in proposed) - min(int(item["offset"]) for item in proposed) + 1
            if span <= max_span:
                current = proposed
            else:
                clusters.append(current)
                current = [experiment]
        if current:
            clusters.append(current)
    return clusters


def assess_cluster(match_count: int, samples: list[int], rebuilt_start: int) -> str:
    if match_count == 0:
        return "no-original-pattern-match"
    if match_count == 1 and samples and samples[0] == rebuilt_start:
        return "direct-original-same-offset"
    if match_count == 1:
        return "unique-original-candidate"
    return "ambiguous-original-candidates"


def analyze_cluster(
    cluster: list[dict[str, Any]],
    original: bytes,
    rebuilt: bytes,
    sample_cap: int,
) -> dict[str, Any]:
    start = min(int(item["offset"]) for item in cluster)
    end = max(int(item["offset"]) for item in cluster) + 1
    fixed_positions = {int(item["offset"]) - start: rebuilt[int(item["offset"])] for item in cluster}
    count, samples, truncated = masked_search(original, fixed_positions, end - start, sample_cap)
    sample_addresses = [Address(sample) for sample in samples]
    first_candidate = sample_addresses[0] if sample_addresses else None
    per_field_candidates: list[dict[str, Any]] = []
    if first_candidate and count == 1:
        for experiment in sorted(cluster, key=lambda item: int(item["offset"])):
            delta = int(experiment["offset"]) - start
            candidate = Address(first_candidate.offset + delta)
            per_field_candidates.append(
                {
                    "experiment_id": experiment["experiment_id"],
                    "rebuilt_offset": Address(int(experiment["offset"])).offset_text,
                    "rebuilt_hirom": Address(int(experiment["offset"])).hirom,
                    "candidate_original_offset": candidate.offset_text,
                    "candidate_original_hirom": candidate.hirom,
                    "contract_matches": find_contract_matches(candidate),
                }
            )

    return {
        "source_file": cluster[0].get("source_file"),
        "experiment_ids": [item["experiment_id"] for item in cluster],
        "rebuilt_cluster_start": Address(start).offset_text,
        "rebuilt_cluster_hirom": Address(start).hirom,
        "cluster_span_bytes": end - start,
        "fixed_byte_count": len(fixed_positions),
        "original_match_count": count,
        "sample_original_offsets": [address.offset_text for address in sample_addresses],
        "sample_original_hirom": [address.hirom for address in sample_addresses],
        "truncated": truncated,
        "assessment": assess_cluster(count, samples, start),
        "per_field_candidates": per_field_candidates,
    }


def build_report(
    *,
    crosswalk_path: Path,
    field_semantics_path: Path,
    original_rom_path: Path,
    baseline_rebuild_path: Path,
    cluster_span: int,
    sample_cap: int,
) -> dict[str, Any]:
    crosswalk = load_json(crosswalk_path)
    field_semantics = load_field_semantics(field_semantics_path)
    original = original_rom_path.read_bytes()
    rebuilt = baseline_rebuild_path.read_bytes()
    experiments = joinable_experiments(crosswalk)

    experiment_reports = [
        analyze_experiment(experiment, original, rebuilt, field_semantics, sample_cap)
        for experiment in experiments
    ]
    clusters = [
        analyze_cluster(cluster, original, rebuilt, sample_cap)
        for cluster in cluster_experiments(experiments, cluster_span)
        if len(cluster) >= 2
    ]

    return {
        "schema": "earthbound-decomp.coilsnake-rebuild-original-layout-report.v1",
        "generated_by": "tools/map_coilsnake_rebuild_to_original.py",
        "source_crosswalk": rel(crosswalk_path),
        "field_semantics": rel(field_semantics_path),
        "original_rom": {
            "path": rel(original_rom_path),
            "size": len(original),
        },
        "baseline_rebuild": {
            "path": rel(baseline_rebuild_path),
            "size": len(rebuilt),
        },
        "summary": {
            "experiment_count": len(experiment_reports),
            "cluster_count": len(clusters),
            "direct_same_offset_count": sum(
                1 for item in experiment_reports if item["best_same_offset_exact_window"] >= 8
            ),
            "unique_original_cluster_candidate_count": sum(
                1 for item in clusters if item["assessment"] == "unique-original-candidate"
            ),
            "ambiguous_cluster_count": sum(
                1 for item in clusters if item["assessment"] == "ambiguous-original-candidates"
            ),
        },
        "experiments": experiment_reports,
        "clusters": clusters,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = [
        "# CoilSnake Rebuild To Original Layout Report",
        "",
        "Generated by `tools/map_coilsnake_rebuild_to_original.py`.",
        "This report records offsets, candidate addresses, match counts, and evidence status only; it does not include ROM byte payloads.",
        "",
        "## Summary",
        "",
        f"- Experiments analyzed: `{report['summary']['experiment_count']}`",
        f"- Multi-probe clusters analyzed: `{report['summary']['cluster_count']}`",
        f"- Direct same-offset matches with at least an 8-byte exact window: `{report['summary']['direct_same_offset_count']}`",
        f"- Unique moved original cluster candidates: `{report['summary']['unique_original_cluster_candidate_count']}`",
        f"- Ambiguous cluster candidates: `{report['summary']['ambiguous_cluster_count']}`",
        "",
        "## Cluster Matches",
        "",
        "| Source file | Experiments | Rebuilt start | Fixed bytes | Original matches | Candidate | Assessment |",
        "| --- | ---: | --- | ---: | ---: | --- | --- |",
    ]
    for cluster in report["clusters"]:
        candidate = cluster["sample_original_hirom"][0] if cluster["sample_original_hirom"] else "none"
        lines.append(
            "| `{source}` | {experiments} | `{start}` / `{hirom}` | {fixed} | {matches} | `{candidate}` | `{assessment}` |".format(
                source=cluster["source_file"],
                experiments=len(cluster["experiment_ids"]),
                start=cluster["rebuilt_cluster_start"],
                hirom=cluster["rebuilt_cluster_hirom"],
                fixed=cluster["fixed_byte_count"],
                matches=cluster["original_match_count"],
                candidate=candidate,
                assessment=cluster["assessment"],
            )
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `direct-original-same-offset` means the changed-byte cluster also appears at the same offset in the verified original ROM.",
            "- `unique-original-candidate` means the changed-byte cluster appears exactly once in the verified original ROM, but at a different offset than CoilSnake's baseline rebuild.",
            "- `ambiguous-original-candidates` means the pattern is too small or common to promote without more probes.",
            "- A unique candidate is still not `runtime-correlated` until a local routine, pointer table, or contract explains how the original game reaches it.",
            "",
            "## Field Candidate Details",
            "",
        ]
    )
    for cluster in report["clusters"]:
        if not cluster["per_field_candidates"]:
            continue
        lines.extend(
            [
                f"### `{cluster['source_file']}`",
                "",
                f"- Cluster assessment: `{cluster['assessment']}`",
                f"- Rebuilt cluster start: `{cluster['rebuilt_cluster_hirom']}`",
                f"- Candidate original start: `{cluster['sample_original_hirom'][0]}`",
                "",
                "| Experiment | Rebuilt | Candidate original | Best local contract |",
                "| --- | --- | --- | --- |",
            ]
        )
        for field in cluster["per_field_candidates"]:
            contract = field["contract_matches"][0]["label"] if field["contract_matches"] else "none"
            lines.append(
                "| `{experiment}` | `{rebuilt}` | `{candidate}` | `{contract}` |".format(
                    experiment=field["experiment_id"],
                    rebuilt=field["rebuilt_hirom"],
                    candidate=field["candidate_original_hirom"],
                    contract=contract,
                )
            )
        lines.append("")

    lines.extend(
        [
            "## Same-Offset Checks",
            "",
            "| Experiment | Rebuilt HiROM | Changed byte matches original | Best exact same-offset window |",
            "| --- | --- | --- | ---: |",
        ]
    )
    for experiment in report["experiments"]:
        lines.append(
            "| `{experiment}` | `{hirom}` | `{same}` | {window} |".format(
                experiment=experiment["experiment_id"],
                hirom=experiment["rebuilt_hirom"],
                same="yes" if experiment["changed_byte_matches_original_same_offset"] else "no",
                window=experiment["best_same_offset_exact_window"],
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Map CoilSnake baseline-rebuild diff bytes back to verified original ROM candidates."
    )
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--field-semantics", type=Path, default=DEFAULT_FIELD_SEMANTICS)
    parser.add_argument("--original-rom", type=Path)
    parser.add_argument("--baseline-rebuild", type=Path, default=DEFAULT_BASELINE_REBUILD)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN_OUT)
    parser.add_argument("--cluster-span", type=int, default=64)
    parser.add_argument("--sample-cap", type=int, default=16)
    args = parser.parse_args()

    try:
        original_rom = args.original_rom.resolve() if args.original_rom else rom_tools.find_rom()
        baseline_rebuild = args.baseline_rebuild.resolve()
        if not baseline_rebuild.is_file():
            raise FileNotFoundError(f"Baseline rebuild ROM not found: {baseline_rebuild}")
        report = build_report(
            crosswalk_path=args.crosswalk.resolve(),
            field_semantics_path=args.field_semantics.resolve(),
            original_rom_path=original_rom,
            baseline_rebuild_path=baseline_rebuild,
            cluster_span=args.cluster_span,
            sample_cap=args.sample_cap,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 2

    write_json(args.json_out.resolve(), report)
    args.markdown_out.resolve().parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.resolve().write_text(render_markdown(report), encoding="utf-8")
    print(f"Wrote {rel(args.json_out.resolve())}")
    print(f"Wrote {rel(args.markdown_out.resolve())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
