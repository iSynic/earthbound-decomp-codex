#!/usr/bin/env python3
"""Summarize a raw C2 battle trace-oracle JSONL capture."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PACKET = ROOT / "manifests" / "c2-battle-trace-oracle-packet.json"
DEFAULT_RUNNER_INDEX = ROOT / "build" / "c2" / "battle-trace-oracles" / "mesen-runner-assets" / "index.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize C2 battle trace-oracle raw JSONL.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--job-id", help="Packet job id.")
    target.add_argument("--oracle-id", help="Oracle id.")
    parser.add_argument("--packet", default=str(DEFAULT_PACKET))
    parser.add_argument("--runner-index", default=str(DEFAULT_RUNNER_INDEX))
    parser.add_argument("--trace", help="Raw trace path. Defaults to packet raw trace path.")
    parser.add_argument("--output", help="Summary JSON path. Defaults to raw-trace-summary.json next to trace.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def manifest_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def find_job(packet: dict[str, Any], *, job_id: str | None, oracle_id: str | None) -> dict[str, Any]:
    for job in packet.get("jobs", []):
        if job_id and job.get("job_id") == job_id:
            return job
        if oracle_id and job.get("oracle_id") == oracle_id:
            return job
    raise ValueError(f"could not find packet job for job_id={job_id!r} oracle_id={oracle_id!r}")


def find_runner_job(index_path: Path, *, job_id: str, oracle_id: str) -> dict[str, Any] | None:
    if not index_path.exists():
        return None
    index = load_json(index_path)
    for job in index.get("jobs", []):
        if job.get("job_id") == job_id or job.get("oracle_id") == oracle_id:
            return job
    return None


def read_trace(path: Path) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    invalid = 0
    if not path.exists():
        return rows, invalid
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            invalid += 1
            continue
        if isinstance(row, dict):
            rows.append(row)
        else:
            invalid += 1
    return rows, invalid


def summarize(job: dict[str, Any], trace_path: Path, runner_job: dict[str, Any] | None = None) -> dict[str, Any]:
    rows, invalid_lines = read_trace(trace_path)
    event_counts: Counter[str] = Counter()
    hit_counts: Counter[str] = Counter()
    probe_hit_counts: Counter[str] = Counter()
    probe_route_group_counts: Counter[str] = Counter()
    required_hits = set()
    watch_counts: Counter[str] = Counter()
    frames: list[int] = []
    runner_start: dict[str, Any] | None = None
    runner_summary: dict[str, Any] | None = None
    for row in rows:
        event_type = str(row.get("type", "unknown"))
        event_counts[event_type] += 1
        frame = row.get("frame")
        if isinstance(frame, int):
            frames.append(frame)
        if event_type == "runner_start":
            runner_start = row
        elif event_type == "summary":
            runner_summary = row
        elif event_type == "breakpoint_hit":
            pc = str(row.get("pc", ""))
            if pc:
                if row.get("probeSource") == "route_group_hint":
                    probe_hit_counts[pc] += 1
                    route_group = str(row.get("routeGroup", ""))
                    if route_group:
                        probe_route_group_counts[route_group] += 1
                else:
                    hit_counts[pc] += 1
                    if row.get("required") is True:
                        required_hits.add(pc)
        elif event_type == "watch_snapshot":
            watch_id = str(row.get("watchId", ""))
            if watch_id:
                watch_counts[watch_id] += 1

    # The packet does not mark minimum hits; use the emulator handoff's required
    # hits from the runner assets when available.
    configured_minimum_hits = [str(item) for item in (runner_job or {}).get("minimum_hits", [])]
    missing_required_hits = sorted(set(configured_minimum_hits) - set(hit_counts))
    trace_exists = trace_path.exists()
    trace_nonempty = trace_exists and trace_path.stat().st_size > 0
    return {
        "schema": "earthbound-decomp.c2-battle-trace-raw-summary.v1",
        "status": "raw_trace_summarized",
        "job_id": job["job_id"],
        "oracle_id": job["oracle_id"],
        "trace_path": manifest_path(trace_path),
        "trace_exists": trace_exists,
        "trace_nonempty": trace_nonempty,
        "line_count": len(rows),
        "invalid_line_count": invalid_lines,
        "event_counts": dict(sorted(event_counts.items())),
        "breakpoint_hit_counts": dict(sorted(hit_counts.items())),
        "probe_breakpoint_hit_counts": dict(sorted(probe_hit_counts.items())),
        "probe_route_group_hit_counts": dict(sorted(probe_route_group_counts.items())),
        "watch_snapshot_counts": dict(sorted(watch_counts.items())),
        "observed_addresses": sorted(hit_counts),
        "probe_observed_addresses": sorted(probe_hit_counts),
        "required_hit_addresses": sorted(required_hits),
        "configured_minimum_hits": configured_minimum_hits,
        "missing_minimum_hits": missing_required_hits,
        "minimum_hits_satisfied": bool(trace_nonempty and configured_minimum_hits and not missing_required_hits),
        "first_frame": min(frames) if frames else None,
        "last_frame": max(frames) if frames else None,
        "runner_start": runner_start,
        "runner_summary": runner_summary,
        "source_promotion_allowed": False,
        "behavior_change_allowed": False,
    }


def main() -> int:
    args = parse_args()
    packet = load_json(Path(args.packet))
    job = find_job(packet, job_id=args.job_id, oracle_id=args.oracle_id)
    runner_job = find_runner_job(Path(args.runner_index), job_id=str(job["job_id"]), oracle_id=str(job["oracle_id"]))
    trace_path = repo_path(args.trace or str(job["output_paths"]["raw_trace_path"]))
    output_path = repo_path(args.output) if args.output else trace_path.with_name("raw-trace-summary.json")
    summary = summarize(job, trace_path, runner_job)
    write_json(output_path, summary)
    print(
        "C2 raw trace summary: "
        f"{summary['oracle_id']} lines={summary['line_count']} "
        f"hits={summary['breakpoint_hit_counts']} minimum={summary['minimum_hits_satisfied']}"
    )
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
