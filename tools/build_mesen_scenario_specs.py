#!/usr/bin/env python3
"""Build sanitized and runnable Mesen scenario specs for C2 proof planning."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = ROOT / "manifests" / "mesen-srm-anchor-catalog.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "mesen-scenario-specs.json"
DEFAULT_NOTE = ROOT / "notes" / "mesen-scenario-specs.md"
DEFAULT_RUNNABLE_ROOT = ROOT / "build" / "mesen-scenarios" / "specs"
DEFAULT_SAVE_STATE_ROOT = Path(r"F:\Mesen2\SaveStates")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--note", default=str(DEFAULT_NOTE))
    parser.add_argument("--runnable-root", default=str(DEFAULT_RUNNABLE_ROOT))
    parser.add_argument("--save-state-root", default=str(DEFAULT_SAVE_STATE_ROOT))
    return parser.parse_args()


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def manifest_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def catalog_anchor(catalog: dict[str, Any], anchor_id: str) -> dict[str, Any]:
    for row in catalog.get("anchors", []):
        if row.get("anchor_id") == anchor_id:
            return row
    raise ValueError(f"anchor not found in SRM catalog: {anchor_id}")


def sanitized_spec(spec: dict[str, Any]) -> dict[str, Any]:
    clean = dict(spec)
    start = dict(clean["start"])
    if start["type"] == "load_state":
        state_path = Path(start.pop("state_path_local_only"))
        start["state_basename"] = state_path.name
        start["state_sha256"] = sha256(state_path)
    if start["type"] == "load_srm_anchor":
        start.pop("working_srm_path_local_only", None)
    clean["start"] = start
    clean.pop("runnable_spec_path", None)
    return clean


def build_specs(catalog: dict[str, Any], save_state_root: Path, runnable_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    srm_anchor = catalog_anchor(catalog, "31-StonehBase")
    save_state_path = save_state_root / "EarthBound (USA)_5.mss"
    runnable_specs = [
        {
            "schema": "earthbound-decomp.mesen-scenario-spec.v1",
            "scenario_id": "mss-large-pizza-party-heal-c2-smoke",
            "title": "Vanilla save-state Large Pizza party heal smoke",
            "evidence_tier": "vanilla_save_state",
            "oracle_id": "hp_roller_collapse_boundary",
            "start": {
                "type": "load_state",
                "state_path_local_only": str(save_state_path),
            },
            "input_pattern": "neutral:900",
            "frame_limit": 1000,
            "watched_routines": ["C2:8125", "C2:BB18", "C1:DC1C", "C1:DC66"],
            "output_dir": "build/mesen-scenarios/runs/mss-large-pizza-party-heal-c2-smoke",
            "expected_use": "Smoke existing vanilla multi-target heal and HP roller capture.",
            "source_promotion_allowed": False,
        },
        {
            "schema": "earthbound-decomp.mesen-scenario-spec.v1",
            "scenario_id": "srm-stonehenge-base-resource-scout",
            "title": "SRM Stonehenge Base resource scout",
            "evidence_tier": "vanilla_srm_plus_input",
            "bootstrap_status": "launch_smoke_only_post_resume_pending",
            "bootstrap_input_pattern": "not_implemented",
            "bootstrap_frame_count": 0,
            "post_resume_snapshot_required": True,
            "resume_proof_status": "not_proven",
            "oracle_id": "resource_amount_pair_magnet_vs_pp_loss",
            "start": {
                "type": "load_srm_anchor",
                "anchor_id": srm_anchor["anchor_id"],
                "archive_name": srm_anchor["archive_name"],
                "srm_sha256": srm_anchor["srm_sha256"],
                "working_srm_path_local_only": str(ROOT / str(srm_anchor["working_srm_path"])),
            },
            "input_pattern": "neutral:600",
            "frame_limit": 720,
            "watched_routines": ["C2:9F5E", "C2:8E42", "C2:721D", "C2:7191"],
            "output_dir": "build/mesen-scenarios/runs/srm-stonehenge-base-resource-scout",
            "expected_use": "Smoke SRM-anchor ROM/SRM pairing before adding title-menu Continue/load bootstrap inputs.",
            "next_step": "Add a fixed resume bootstrap that proves the SRM anchor was loaded before treating this lane as vanilla_srm_plus_input evidence.",
            "source_promotion_allowed": False,
        },
    ]
    sanitized: list[dict[str, Any]] = []
    for spec in runnable_specs:
        path = runnable_root / f"{spec['scenario_id']}.json"
        spec["runnable_spec_path"] = manifest_path(path)
        write_json(path, spec)
        clean = sanitized_spec(spec)
        clean["runnable_spec_path"] = manifest_path(path)
        sanitized.append(clean)
    return sanitized, runnable_specs


def render_note(data: dict[str, Any]) -> str:
    lines = [
        "# Mesen Scenario Specs",
        "",
        "Generated by `tools/build_mesen_scenario_specs.py`. Tracked specs are",
        "sanitized; runnable specs with local paths live under ignored `build/`.",
        "",
        "## Summary",
        "",
        f"- scenarios: `{data['summary']['scenario_count']}`",
        f"- evidence tiers: `{data['summary']['evidence_tiers']}`",
        "- source promotion allowed: `False`",
        "- SRM-anchor specs are launch/bootstrap scaffolds until a post-resume snapshot proves the save was loaded.",
        "",
        "## Scenarios",
        "",
        "| Scenario | Tier | Start | Oracle | Bootstrap | Purpose |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for spec in data["scenarios"]:
        start = spec["start"]
        if start["type"] == "load_state":
            start_text = f"state `{start['state_basename']}`"
        else:
            start_text = f"SRM anchor `{start['anchor_id']}`"
        bootstrap = spec.get("bootstrap_status", "ready")
        lines.append(
            f"| `{spec['scenario_id']}` | `{spec['evidence_tier']}` | {start_text} | `{spec['oracle_id']}` | `{bootstrap}` | {spec['expected_use']} |"
        )
    lines.extend(
        [
            "",
            "## SRM Bootstrap Caveat",
            "",
            "The current SRM scenario copies a cataloged `.srm` beside a local ROM and confirms the paired launch path. It does not yet prove that Mesen selected Continue, loaded the anchor save, or reached a post-resume gameplay state. Treat SRM-anchor outputs as setup plumbing until a scenario records a post-resume snapshot.",
            "",
            "When a Mesen path is supplied, `tools/run_mesen_scenario_spec.py` now installs the cataloged SRM into the portable Mesen `Saves/` directory using the source ROM basename and records the installed SHA-256. Existing target saves with different hashes are backed up under the ignored scenario run directory before replacement.",
            "",
            "The scenario runner now supports a separate bootstrap input phase via local override fields/CLI arguments, but the tracked Stonehenge scenario keeps `launch_smoke_only_post_resume_pending` until a verified Continue/load sequence and save-specific post-resume state are recorded.",
            "",
            "Latest local scout: a bounded Start/A bootstrap sweep records bootstrap completion, input handoff, and C1/C3 file/menu helper hits, but still no `C2:9F5E`/`C2:8E42` resource route and no post-resume proof. The next useful input from a human would be either the exact title-menu Continue/load button sequence for one SRM slot or a Mesen save state created immediately after loading one of the SRM anchors.",
            "",
            "For visible/manual launch, use `python tools/launch_mesen_srm_anchor.py --anchor-id 31-StonehBase`. It installs the cataloged SRM to `F:\\Mesen2\\Saves\\EarthBound (USA).srm` and launches `EarthBound (USA).sfc` with the ROM path passed as a single argument, avoiding PowerShell path-splitting on spaces.",
        ]
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    catalog = load_json(Path(args.catalog))
    runnable_root = Path(args.runnable_root)
    sanitized, _ = build_specs(catalog, Path(args.save_state_root), runnable_root)
    tiers = sorted({spec["evidence_tier"] for spec in sanitized})
    data = {
        "schema": "earthbound-decomp.mesen-scenario-spec-index.v1",
        "status": "scenario_specs_generated_local_paths_ignored",
        "generated_by": "tools/build_mesen_scenario_specs.py",
        "source_inputs": ["manifests/mesen-srm-anchor-catalog.json"],
        "summary": {
            "scenario_count": len(sanitized),
            "evidence_tiers": tiers,
            "source_promotion_allowed": False,
        },
        "scenarios": sanitized,
    }
    write_json(Path(args.output), data)
    write_text(Path(args.note), render_note(data))
    print(f"Wrote {args.output}")
    print(f"Wrote {args.note}")
    print(f"Wrote runnable specs under {runnable_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
