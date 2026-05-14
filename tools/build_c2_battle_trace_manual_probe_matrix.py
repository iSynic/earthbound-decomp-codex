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
    ROOT / "build" / "c2" / "battle-trace-oracles" / "manual-probes" / "battle-fixtures-8",
    ROOT / "build" / "c2" / "battle-trace-oracles" / "manual-probes" / "battle-fixtures-replaced-slots",
    ROOT / "build" / "c2" / "battle-trace-oracles" / "collapse-save-state-probes-neutral" / "hp_roller_collapse_boundary",
    ROOT / "build" / "c2" / "battle-trace-oracles" / "collapse-save-state-probes-neutral-long" / "hp_roller_collapse_boundary",
    ROOT / "build" / "c2" / "battle-trace-oracles" / "manual-probes" / "hp-roller-collapse-tail",
    ROOT / "build" / "c2" / "battle-trace-oracles" / "route-probes" / "c1-c2-target-action-staging",
    ROOT / "build" / "c2" / "battle-trace-oracles" / "route-probes" / "c2-route-gap-hints" / "c1-c2-target-action-staging",
    ROOT / "build" / "c2" / "battle-trace-oracles" / "route-probes" / "c2-route-gap-hints" / "c2-40a4-current-action-payload",
    ROOT / "build" / "c2" / "battle-trace-oracles" / "manual-probes" / "resource-wram-patched",
    ROOT / "build" / "c2" / "battle-trace-oracles" / "manual-probes" / "resource-natural-scripted-entry",
    ROOT / "build" / "c2" / "battle-trace-oracles" / "manual-probes" / "natural-resource-scout",
    ROOT / "build" / "c2" / "battle-trace-oracles" / "fixture-rom-tests",
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


def sanitize_state(path_text: str | None, stored_sha256: str | None = None) -> dict[str, str | None]:
    if not path_text:
        return {"basename": None, "sha256": None}
    path = Path(path_text)
    return {"basename": path.name, "sha256": stored_sha256}


def load_handoff_metadata(handoff_path: Path) -> tuple[dict[str, list[str]], dict[str, dict[str, dict[str, Any]]]]:
    data = load_json(handoff_path)
    minimums: dict[str, list[str]] = {}
    route_groups: dict[str, dict[str, dict[str, Any]]] = {}
    for job in data.get("jobs", []):
        oracle_id = str(job["oracle_id"])
        minimums[oracle_id] = [str(item) for item in job.get("minimum_hits", [])]
        groups: dict[str, dict[str, Any]] = {}
        for group_id, group in job.get("route_groups", {}).items():
            groups[str(group_id)] = {
                "addresses": [str(item) for item in group.get("addresses", [])],
                "role": group.get("role", ""),
                "status": group.get("status", ""),
                "next_probe_goal": group.get("next_probe_goal", ""),
                "probe_breakpoint_hints": [str(item) for item in group.get("probe_breakpoint_hints", [])],
                "watch_hints": [str(item) for item in group.get("watch_hints", [])],
            }
        if groups:
            route_groups[oracle_id] = groups
    return minimums, route_groups


def build_record(probe_root: Path, summary_path: Path, minimums: dict[str, list[str]]) -> dict[str, Any]:
    summary = load_json(summary_path)
    mesen_path = summary_path.with_name("mesen-run-summary.json")
    mesen = load_json(mesen_path) if mesen_path.is_file() else {}
    oracle_id = str(summary.get("oracle_id"))
    observed = [str(item) for item in summary.get("observed_addresses", [])]
    probe_observed = [str(item) for item in summary.get("probe_observed_addresses", [])]
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
        "probe_observed_addresses": probe_observed,
        "breakpoint_hit_counts": summary.get("breakpoint_hit_counts", {}),
        "probe_breakpoint_hit_counts": summary.get("probe_breakpoint_hit_counts", {}),
        "probe_route_group_hit_counts": summary.get("probe_route_group_hit_counts", {}),
        "dispatch_target_counts": summary.get("dispatch_target_counts", {}),
        "probe_dispatch_target_counts": summary.get("probe_dispatch_target_counts", {}),
        "stack_return_counts": summary.get("stack_return_counts", {}),
        "probe_stack_return_counts": summary.get("probe_stack_return_counts", {}),
        "dispatch_lane_counts": summary.get("dispatch_lane_counts", {}),
        "probe_dispatch_lane_counts": summary.get("probe_dispatch_lane_counts", {}),
        "post_call_snapshot_counts": summary.get("post_call_snapshot_counts", {}),
        "configured_minimum_hits": configured_minimum,
        "missing_minimum_hits": missing_minimum,
        "first_frame": summary.get("first_frame"),
        "last_frame": summary.get("last_frame"),
        "trace_line_count": summary.get("line_count"),
        "trace_nonempty": bool(summary.get("trace_nonempty")),
        "input_pattern": mesen.get("input_pattern"),
        "save_state": sanitize_state(mesen.get("save_state_path_local_only"), mesen.get("save_state_sha256")),
        "raw_trace_summary": summary_path.relative_to(ROOT).as_posix(),
        "source_promotion_allowed": False,
        "behavior_change_allowed": False,
    }


def classify_oracle(records: list[dict[str, Any]], configured_minimum: list[str]) -> str:
    if any(record["minimum_hits_satisfied"] for record in records):
        return "minimum-hit-candidate"
    if any(record["observed_addresses"] for record in records):
        return "partial-route-observed"
    if any(record["probe_observed_addresses"] for record in records):
        return "probe-route-observed"
    if records:
        return "probed-no-route"
    if configured_minimum:
        return "not-probed"
    return "not-in-handoff"


def summarize_route_groups(oracle_id: str, records: list[dict[str, Any]], route_groups: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    groups = route_groups.get(oracle_id, {})
    if not groups:
        return {}
    fixture_hits: dict[str, set[str]] = defaultdict(set)
    probe_fixture_hits: dict[str, set[str]] = defaultdict(set)
    aggregate_hits: set[str] = set()
    aggregate_probe_hits: set[str] = set()
    for record in records:
        hits = set(record["observed_addresses"])
        probe_hits = set(record["probe_observed_addresses"])
        aggregate_hits.update(hits)
        aggregate_probe_hits.update(probe_hits)
        for group_id, group in groups.items():
            addresses = [str(item) for item in group.get("addresses", [])]
            if set(addresses).issubset(hits):
                fixture_hits[group_id].add(record["fixture_id"])
            probe_hints = {str(item) for item in group.get("probe_breakpoint_hints", [])}
            if probe_hints & probe_hits:
                probe_fixture_hits[group_id].add(record["fixture_id"])
    summary: dict[str, Any] = {}
    for group_id, group in groups.items():
        addresses = [str(item) for item in group.get("addresses", [])]
        missing = sorted(set(addresses) - aggregate_hits)
        summary[group_id] = {
            "addresses": addresses,
            "role": group.get("role", ""),
            "status": group.get("status", ""),
            "next_probe_goal": group.get("next_probe_goal", ""),
            "probe_breakpoint_hints": [str(item) for item in group.get("probe_breakpoint_hints", [])],
            "watch_hints": [str(item) for item in group.get("watch_hints", [])],
            "covered_by_any_probe": not missing,
            "missing_from_all_probes": missing,
            "fixtures_covering_group": sorted(fixture_hits.get(group_id, set())),
            "probe_hint_addresses_observed": sorted(set(group.get("probe_breakpoint_hints", [])) & aggregate_probe_hits),
            "fixtures_with_probe_hints": sorted(probe_fixture_hits.get(group_id, set())),
        }
    return summary


def summarize_oracles(
    records: list[dict[str, Any]],
    minimums: dict[str, list[str]],
    route_groups: dict[str, dict[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    by_oracle: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_oracle[record["oracle_id"]].append(record)
    summaries: list[dict[str, Any]] = []
    for oracle_id in sorted(set(minimums) | set(by_oracle)):
        oracle_records = sorted(by_oracle.get(oracle_id, []), key=lambda item: item["fixture_id"])
        hit_counter: Counter[str] = Counter()
        probe_hit_counter: Counter[str] = Counter()
        probe_route_group_counter: Counter[str] = Counter()
        dispatch_target_counter: Counter[str] = Counter()
        probe_dispatch_target_counter: Counter[str] = Counter()
        stack_return_counter: Counter[str] = Counter()
        probe_stack_return_counter: Counter[str] = Counter()
        dispatch_lane_counter: Counter[str] = Counter()
        probe_dispatch_lane_counter: Counter[str] = Counter()
        post_call_snapshot_counter: Counter[str] = Counter()
        fixture_hits: list[dict[str, Any]] = []
        probe_fixture_hits: list[dict[str, Any]] = []
        for record in oracle_records:
            hit_counter.update(record["observed_addresses"])
            probe_hit_counter.update(record["probe_observed_addresses"])
            probe_route_group_counter.update(record.get("probe_route_group_hit_counts", {}))
            dispatch_target_counter.update(record.get("dispatch_target_counts", {}))
            probe_dispatch_target_counter.update(record.get("probe_dispatch_target_counts", {}))
            stack_return_counter.update(record.get("stack_return_counts", {}))
            probe_stack_return_counter.update(record.get("probe_stack_return_counts", {}))
            dispatch_lane_counter.update(record.get("dispatch_lane_counts", {}))
            probe_dispatch_lane_counter.update(record.get("probe_dispatch_lane_counts", {}))
            post_call_snapshot_counter.update(record.get("post_call_snapshot_counts", {}))
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
            if record["probe_observed_addresses"]:
                probe_fixture_hits.append(
                    {
                        "fixture_id": record["fixture_id"],
                        "probe_observed_addresses": record["probe_observed_addresses"],
                        "probe_breakpoint_hit_counts": record["probe_breakpoint_hit_counts"],
                        "probe_route_group_hit_counts": record.get("probe_route_group_hit_counts", {}),
                        "probe_dispatch_target_counts": record.get("probe_dispatch_target_counts", {}),
                        "probe_stack_return_counts": record.get("probe_stack_return_counts", {}),
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
                "fixtures_with_probe_hits": len(probe_fixture_hits),
                "observed_address_counts": dict(sorted(hit_counter.items())),
                "probe_observed_address_counts": dict(sorted(probe_hit_counter.items())),
                "probe_route_group_counts": dict(sorted(probe_route_group_counter.items())),
                "dispatch_target_counts": dict(sorted(dispatch_target_counter.items())),
                "probe_dispatch_target_counts": dict(sorted(probe_dispatch_target_counter.items())),
                "stack_return_counts": dict(sorted(stack_return_counter.items())),
                "probe_stack_return_counts": dict(sorted(probe_stack_return_counter.items())),
                "dispatch_lane_counts": dict(sorted(dispatch_lane_counter.items())),
                "probe_dispatch_lane_counts": dict(sorted(probe_dispatch_lane_counter.items())),
                "post_call_snapshot_counts": dict(sorted(post_call_snapshot_counter.items())),
                "route_groups": summarize_route_groups(oracle_id, oracle_records, route_groups),
                "fixture_hits": fixture_hits,
                "probe_fixture_hits": probe_fixture_hits,
            }
        )
    return summaries


def build_route_gap_queue(oracle_summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    queue: list[dict[str, Any]] = []
    for oracle in oracle_summaries:
        for group_id, group in oracle.get("route_groups", {}).items():
            status = str(group.get("status", ""))
            missing = [str(item) for item in group.get("missing_from_all_probes", [])]
            if status != "remaining_fixture_gap" and not status.startswith("neighbor_only"):
                continue
            if not missing:
                continue
            queue.append(
                {
                    "oracle_id": oracle["oracle_id"],
                    "route_group": group_id,
                    "status": status,
                    "covered_by_any_probe": bool(group.get("covered_by_any_probe")),
                    "missing_from_all_probes": missing,
                    "fixtures_covering_group": group.get("fixtures_covering_group", []),
                    "probe_hint_addresses_observed": group.get("probe_hint_addresses_observed", []),
                    "fixtures_with_probe_hints": group.get("fixtures_with_probe_hints", []),
                    "next_probe_goal": group.get("next_probe_goal", ""),
                    "probe_breakpoint_hints": group.get("probe_breakpoint_hints", []),
                    "watch_hints": group.get("watch_hints", []),
                }
            )
    return sorted(
        queue,
        key=lambda item: (
            item["status"] != "remaining_fixture_gap",
            item["covered_by_any_probe"],
            item["oracle_id"],
            item["route_group"],
        ),
    )


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
        f"- fixtures with route-hint hits: `{manifest['summary']['route_hint_fixture_count']}`",
        f"- remaining route gaps: `{manifest['summary']['remaining_route_gap_count']}`",
        f"- source promotion allowed: `{manifest['policy']['source_promotion_allowed']}`",
        f"- behavior change allowed: `{manifest['policy']['behavior_change_allowed']}`",
        "",
        "## Oracle Matrix",
        "",
        "| Oracle | Status | Probes | Ready | Any-hit fixtures | Route-hint fixtures | Observed addresses | Route hints | Probe dispatch targets | Probe returns |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- |",
    ]
    for item in manifest["oracles"]:
        observed = ", ".join(f"{addr}:{count}" for addr, count in item["observed_address_counts"].items()) or "-"
        probe_observed = ", ".join(f"{addr}:{count}" for addr, count in item["probe_observed_address_counts"].items()) or "-"
        probe_dispatch = ", ".join(f"{target}:{count}" for target, count in item.get("probe_dispatch_target_counts", {}).items()) or "-"
        probe_returns = ", ".join(f"{target}:{count}" for target, count in item.get("probe_stack_return_counts", {}).items()) or "-"
        lines.append(
            f"| `{item['oracle_id']}` | `{item['status']}` | `{item['probe_count']}` | "
            f"`{item['minimum_hit_candidate_count']}` | `{item['fixtures_with_any_hits']}` | "
            f"`{item['fixtures_with_probe_hits']}` | {observed} | {probe_observed} | {probe_dispatch} | {probe_returns} |"
        )
    lines.extend(["", "## Route Gap Queue", ""])
    route_gap_queue = manifest.get("route_gap_queue", [])
    if route_gap_queue:
        lines.extend(["| Oracle | Group | Status | Missing | Probe hints seen | Next probe | Breakpoints | Watches |", "| --- | --- | --- | --- | --- | --- | --- | --- |"])
        for item in route_gap_queue:
            missing = ", ".join(item.get("missing_from_all_probes", [])) or "-"
            probe_seen = ", ".join(item.get("probe_hint_addresses_observed", [])) or "-"
            next_probe = item.get("next_probe_goal") or "-"
            breakpoints = ", ".join(f"`{address}`" for address in item.get("probe_breakpoint_hints", [])) or "-"
            watches = ", ".join(f"`{watch}`" for watch in item.get("watch_hints", [])) or "-"
            lines.append(
                f"| `{item['oracle_id']}` | `{item['route_group']}` | `{item['status']}` | {missing} | "
                f"{probe_seen} | {next_probe} | {breakpoints} | {watches} |"
            )
    else:
        lines.append("- No remaining route gaps are recorded in the current handoff metadata.")
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
    lines.extend(["## Route-Hint Fixture Hits", ""])
    for item in manifest["oracles"]:
        if not item["probe_fixture_hits"]:
            continue
        lines.append(f"### `{item['oracle_id']}`")
        lines.append("")
        lines.append("| Fixture | Frames | Probe hits | Route groups | Dispatch targets | Returns |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for fixture in item["probe_fixture_hits"]:
            hits = ", ".join(f"{addr}:{count}" for addr, count in fixture["probe_breakpoint_hit_counts"].items())
            route_groups = ", ".join(f"{group}:{count}" for group, count in fixture["probe_route_group_hit_counts"].items()) or "-"
            dispatch = ", ".join(f"{target}:{count}" for target, count in fixture.get("probe_dispatch_target_counts", {}).items()) or "-"
            returns = ", ".join(f"{target}:{count}" for target, count in fixture.get("probe_stack_return_counts", {}).items()) or "-"
            frames = f"{fixture['first_frame']}..{fixture['last_frame']}"
            lines.append(f"| `{fixture['fixture_id']}` | `{frames}` | {hits} | {route_groups} | {dispatch} | {returns} |")
        lines.append("")
    lines.extend(["## Route Group Coverage", ""])
    for item in manifest["oracles"]:
        route_groups = item.get("route_groups", {})
        if not route_groups:
            continue
        lines.append(f"### `{item['oracle_id']}`")
        lines.append("")
        lines.append("| Group | Status | Covered | Missing | Fixtures | Probe hints seen | Next probe |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for group_id, group in route_groups.items():
            missing = ", ".join(group["missing_from_all_probes"]) or "-"
            fixtures = ", ".join(f"`{fixture}`" for fixture in group["fixtures_covering_group"]) or "-"
            probe_seen = ", ".join(group.get("probe_hint_addresses_observed", [])) or "-"
            next_probe = group.get("next_probe_goal") or "-"
            lines.append(
                f"| `{group_id}` | `{group['status']}` | `{group['covered_by_any_probe']}` | "
                f"{missing} | {fixtures} | {probe_seen} | {next_probe} |"
            )
        lines.append("")
    lines.extend(
        [
            "## Interpretation",
            "",
            "- `minimum-hit-candidate` means the ignored trace reached every configured minimum hit and may be promoted only after canonical rerun plus reviewed capture fields.",
            "- `partial-route-observed` means the fixture reaches useful neighboring code but is not enough for a reviewed oracle result.",
            "- Route-hint fixtures hit optional approach breakpoints and are discovery aids only; they do not satisfy minimum hits or permit source promotion.",
            "- The Route Gap Queue lists only groups whose configured minimum addresses are still missing from every local probe. Covered groups can still retain conservative handoff statuses in the coverage table until reviewed.",
            "- Dispatch-target and return columns are captured only for route-hint probes that use trampoline/context breakpoints; they identify the `$00BC` jump target and stack return path without proving the missing minimum address. Raw summaries also classify `C0:9279` lanes by stack return so direct dispatch can be separated from true `C2:40A4` loop dispatch.",
            "- `probed-no-route` means the current local fixtures did not reach the lane.",
            "- `c2_40a4_current_action_payload` now has its first runner-backed `C2:40A4` minimum hit from the ignored `bash-row-neutralize-c240a4` fixture ROM. That run also observed `C2:90C6`, the static pre-call site `C2:915C`, loop returns near `C2:4104`/`C2:4159`, and dispatch target `C2:9051`, which separates the true `C2:40A4` loop from the earlier direct-dispatch `C0:9279 -> C2:5D3D` neighbors.",
            "- The replaced-slot Healing, Dread Scorpion poison, Large Pizza, and Paula Freeze fixtures remain valuable direct-dispatch coverage for `C2:8125`, `C2:724A`, and payload-adjacent targets such as `C2:8B2C`, `C2:9C2C`, and `C2:B27D`, but their `C0:9279` lanes should stay separate from the Bash-row fixture's artificial `C2:40A4` steering proof.",
            "- `c2_724a_affliction_writer_matrix` now has both the Dread Scorpion poison-writer hit and a forced Flash Beta fixture that observes the paired `C2:9917 -> C2:724A` numb-status route. It remains follow-up rather than proof-grade because the natural `C2:98A1` gate and post-write return value still need cleaner evidence.",
            "- `c1_c2_target_action_staging` now has separate partial routes for target setup, item-action resolution, and the inventory-selection loop. The forced-entry `adb4-force-b930-snapshot-export` fixture observes `C2:B930` export mechanics, but the natural unpatched C1 pre-export route still needs a cleaner capture.",
            "- `hp_roller_collapse_boundary` now has a long save-state sweep and scripted-entry startup probes folded into the matrix. The save-state sweep found additional minimum-hit collapse candidates but still no `C2:7680` descriptor-death-text hit. The scripted-entry cleanup scout reaches `C0:B9B4 -> C2:2F38`, `C2:5AFB`, `C2:6088`, and repeated `C2:BB18`, but not `C2:6093`, `C2:6145`, or `C2:BC5C`, so inactive-slot cleanup remains a dedicated fixture/seed follow-up rather than an inferred tail.",
            "- `resource_amount_pair_magnet_vs_pp_loss` now has fixture-steered entry hits for both `C2:9F5E` and `C2:8E42`, controlled WRAM-patched reducer probes that separate PSI Magnet transfer mechanics from PP reduction loss-only mechanics, and scripted-entry enemy fixtures that reach canonical Gigantic Ant row 54 and Guardian General row 95 lanes. Both lanes now have natural enemy-action-table hits, but targeted WRAM PP seeding still keeps them below proof-grade promotion.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    probe_roots = [repo_path(path) for path in (args.probe_root or [str(path) for path in DEFAULT_PROBE_ROOTS])]
    minimums, route_groups = load_handoff_metadata(repo_path(args.handoff))
    records: list[dict[str, Any]] = []
    for probe_root in probe_roots:
        if not probe_root.exists():
            continue
        summary_paths = sorted(probe_root.glob("*/*/raw-trace-summary.json"))
        if not summary_paths:
            summary_paths = sorted(probe_root.glob("*/raw-trace-summary.json"))
        records.extend(build_record(probe_root, path, minimums) for path in summary_paths)
    oracle_summaries = summarize_oracles(records, minimums, route_groups)
    route_gap_queue = build_route_gap_queue(oracle_summaries)
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
            "route_hint_fixture_count": sum(item["fixtures_with_probe_hits"] for item in oracle_summaries),
            "remaining_route_gap_count": sum(
                1
                for item in route_gap_queue
                if item["status"] == "remaining_fixture_gap" and not item["covered_by_any_probe"]
            ),
            "status_counts": dict(Counter(item["status"] for item in oracle_summaries)),
        },
        "route_gap_queue": route_gap_queue,
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
