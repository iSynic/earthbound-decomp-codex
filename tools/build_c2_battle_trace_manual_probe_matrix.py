#!/usr/bin/env python3
"""Build a sanitized matrix from local C2 manual Mesen probe summaries."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROBE_ROOTS = (
    ROOT / "build" / "c2" / "battle-trace-oracles" / "manual-probes" / "battle-fixtures-1-7",
    ROOT / "build" / "c2" / "battle-trace-oracles" / "collapse-save-state-probes-neutral" / "hp_roller_collapse_boundary",
)
DEFAULT_HANDOFF = ROOT / "manifests" / "c2-battle-trace-oracle-emulator-handoff.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "c2-battle-trace-manual-probe-matrix.json"
DEFAULT_NOTE = ROOT / "notes" / "c2-battle-trace-manual-probe-matrix.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a C2 manual probe matrix from ignored Mesen outputs.")
    parser.add_argument(
        "--probe-root",
        action="append",
        help="Probe root containing fixture/oracle/raw-trace-summary.json or fixture/raw-trace-summary.json trees. May repeat.",
    )
    parser.add_argument("--handoff", default=str(DEFAULT_HANDOFF))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--note", default=str(DEFAULT_NOTE))
    return parser.parse_args()


def repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sanitize_state(path_text: str | None) -> dict[str, str | None]:
    if not path_text:
        return {"basename": None, "sha256": None}
    path = Path(path_text)
    return {"basename": path.name, "sha256": sha256(path)}


def load_oracle_minimums(handoff_path: Path) -> dict[str, list[str]]:
    data = load_json(handoff_path)
    return {str(job["oracle_id"]): [str(item) for item in job.get("minimum_hits", [])] for job in data.get("jobs", [])}


def build_record(probe_root: Path, summary_path: Path, minimums: dict[str, list[str]]) -> dict[str, Any]:
    summary = load_json(summary_path)
    mesen_path = summary_path.with_name("mesen-run-summary.json")
    mesen = load_json(mesen_path) if mesen_path.is_file() else {}
    oracle_id = str(summary.get("oracle_id"))
    observed = [str(item) for item in summary.get("observed_addresses", [])]
    configured_minimum = minimums.get(oracle_id, [str(item) for item in summary.get("configured_minimum_hits", [])])
    missing_minimum = sorted(set(configured_minimum) - set(observed))
    relative_parts = summary_path.relative_to(probe_root).parts
    fixture_id = relative_parts[0] if relative_parts else "unknown-fixture"
    return {
        "probe_group": probe_root.relative_to(ROOT).as_posix() if probe_root.is_relative_to(ROOT) else probe_root.as_posix(),
        "fixture_id": fixture_id,
        "oracle_id": oracle_id,
        "minimum_hits_satisfied": bool(summary.get("minimum_hits_satisfied")) and not missing_minimum,
        "observed_addresses": observed,
        "breakpoint_hit_counts": summary.get("breakpoint_hit_counts", {}),
        "configured_minimum_hits": configured_minimum,
        "missing_minimum_hits": missing_minimum,
        "first_frame": summary.get("first_frame"),
        "last_frame": summary.get("last_frame"),
        "trace_line_count": summary.get("line_count"),
        "trace_nonempty": bool(summary.get("trace_nonempty")),
        "input_pattern": mesen.get("input_pattern"),
        "save_state": sanitize_state(mesen.get("save_state_path_local_only")),
        "raw_trace_summary": summary_path.relative_to(ROOT).as_posix(),
        "source_promotion_allowed": False,
        "behavior_change_allowed": False,
    }


def classify_oracle(records: list[dict[str, Any]], configured_minimum: list[str]) -> str:
    if any(record["minimum_hits_satisfied"] for record in records):
        return "minimum-hit-candidate"
    if any(record["observed_addresses"] for record in records):
        return "partial-route-observed"
    if records:
        return "probed-no-route"
    if configured_minimum:
        return "not-probed"
    return "not-in-handoff"


def summarize_oracles(records: list[dict[str, Any]], minimums: dict[str, list[str]]) -> list[dict[str, Any]]:
    by_oracle: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_oracle[record["oracle_id"]].append(record)
    summaries: list[dict[str, Any]] = []
    for oracle_id in sorted(set(minimums) | set(by_oracle)):
        oracle_records = sorted(by_oracle.get(oracle_id, []), key=lambda item: item["fixture_id"])
        hit_counter: Counter[str] = Counter()
        fixture_hits: list[dict[str, Any]] = []
        for record in oracle_records:
            hit_counter.update(record["observed_addresses"])
            if record["observed_addresses"]:
                fixture_hits.append(
                    {
                        "fixture_id": record["fixture_id"],
                        "minimum_hits_satisfied": record["minimum_hits_satisfied"],
                        "observed_addresses": record["observed_addresses"],
                        "breakpoint_hit_counts": record["breakpoint_hit_counts"],
                        "first_frame": record["first_frame"],
                        "last_frame": record["last_frame"],
                    }
                )
        summaries.append(
            {
                "oracle_id": oracle_id,
                "configured_minimum_hits": minimums.get(oracle_id, []),
                "status": classify_oracle(oracle_records, minimums.get(oracle_id, [])),
                "probe_count": len(oracle_records),
                "minimum_hit_candidate_count": sum(1 for record in oracle_records if record["minimum_hits_satisfied"]),
                "fixtures_with_any_hits": len(fixture_hits),
                "observed_address_counts": dict(sorted(hit_counter.items())),
                "fixture_hits": fixture_hits,
            }
        )
    return summaries


def render_note(manifest: dict[str, Any]) -> str:
    lines = [
        "# C2 Battle Trace Manual Probe Matrix",
        "",
        "Generated by `tools/build_c2_battle_trace_manual_probe_matrix.py` from ignored local Mesen probe summaries.",
        "It records fixture usefulness without storing local save-state paths or raw traces.",
        "",
        "## Summary",
        "",
        f"- probe roots found: `{manifest['summary']['probe_roots_found']}` / `{manifest['summary']['probe_root_count']}`",
        f"- probe records: `{manifest['summary']['record_count']}`",
        f"- oracles summarized: `{manifest['summary']['oracle_count']}`",
        f"- minimum-hit candidates: `{manifest['summary']['minimum_hit_candidate_count']}`",
        f"- source promotion allowed: `{manifest['policy']['source_promotion_allowed']}`",
        f"- behavior change allowed: `{manifest['policy']['behavior_change_allowed']}`",
        "",
        "## Oracle Matrix",
        "",
        "| Oracle | Status | Probes | Ready | Any-hit fixtures | Observed addresses |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for item in manifest["oracles"]:
        observed = ", ".join(f"{addr}:{count}" for addr, count in item["observed_address_counts"].items()) or "-"
        lines.append(
            f"| `{item['oracle_id']}` | `{item['status']}` | `{item['probe_count']}` | "
            f"`{item['minimum_hit_candidate_count']}` | `{item['fixtures_with_any_hits']}` | {observed} |"
        )
    lines.extend(["", "## Fixture Hits", ""])
    for item in manifest["oracles"]:
        if not item["fixture_hits"]:
            continue
        lines.append(f"### `{item['oracle_id']}`")
        lines.append("")
        lines.append("| Fixture | Ready | Frames | Hits |")
        lines.append("| --- | --- | --- | --- |")
        for fixture in item["fixture_hits"]:
            hits = ", ".join(f"{addr}:{count}" for addr, count in fixture["breakpoint_hit_counts"].items())
            frames = f"{fixture['first_frame']}..{fixture['last_frame']}"
            lines.append(f"| `{fixture['fixture_id']}` | `{fixture['minimum_hits_satisfied']}` | `{frames}` | {hits} |")
        lines.append("")
    lines.extend(
        [
            "## Interpretation",
            "",
            "- `minimum-hit-candidate` means the ignored trace reached every configured minimum hit and may be promoted only after canonical rerun plus reviewed capture fields.",
            "- `partial-route-observed` means the fixture reaches useful neighboring code but is not enough for a reviewed oracle result.",
            "- `probed-no-route` means the current local fixtures did not reach the lane.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    probe_roots = [repo_path(path) for path in (args.probe_root or [str(path) for path in DEFAULT_PROBE_ROOTS])]
    minimums = load_oracle_minimums(repo_path(args.handoff))
    records: list[dict[str, Any]] = []
    for probe_root in probe_roots:
        if not probe_root.exists():
            continue
        summary_paths = sorted(probe_root.glob("*/*/raw-trace-summary.json"))
        if not summary_paths:
            summary_paths = sorted(probe_root.glob("*/raw-trace-summary.json"))
        records.extend(build_record(probe_root, path, minimums) for path in summary_paths)
    oracle_summaries = summarize_oracles(records, minimums)
    manifest = {
        "schema": "earthbound-decomp.c2-battle-trace-manual-probe-matrix.v1",
        "generated_by": "tools/build_c2_battle_trace_manual_probe_matrix.py",
        "probe_roots": [
            path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix()
            for path in probe_roots
        ],
        "policy": {
            "source_promotion_allowed": False,
            "behavior_change_allowed": False,
            "local_save_state_paths_redacted": True,
            "raw_traces_tracked": False,
        },
        "summary": {
            "probe_root_count": len(probe_roots),
            "probe_roots_found": sum(1 for path in probe_roots if path.exists()),
            "record_count": len(records),
            "oracle_count": len(oracle_summaries),
            "minimum_hit_candidate_count": sum(item["minimum_hit_candidate_count"] for item in oracle_summaries),
            "status_counts": dict(Counter(item["status"] for item in oracle_summaries)),
        },
        "oracles": oracle_summaries,
        "records": records,
    }
    output = repo_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    note = repo_path(args.note)
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(render_note(manifest), encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Wrote {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
