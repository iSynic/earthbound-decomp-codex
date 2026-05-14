#!/usr/bin/env python3
"""Summarize controlled C2 PP resource amount captures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUTS = {
    "psi_magnet_transfer_controlled": ROOT
    / "build"
    / "c2"
    / "battle-trace-oracles"
    / "manual-probes"
    / "resource-wram-patched"
    / "psi-magnet-target-pp32"
    / "captured-fields.json",
    "pp_reduction_loss_only_controlled": ROOT
    / "build"
    / "c2"
    / "battle-trace-oracles"
    / "manual-probes"
    / "resource-wram-patched"
    / "pp-reduction-target-pp32"
    / "captured-fields.json",
    "psi_magnet_action_steered_no_wram": ROOT
    / "build"
    / "c2"
    / "battle-trace-oracles"
    / "manual-probes"
    / "resource-action-steered-no-wram"
    / "psi-magnet-state1"
    / "captured-fields.json",
    "pp_reduction_action_steered_no_wram": ROOT
    / "build"
    / "c2"
    / "battle-trace-oracles"
    / "manual-probes"
    / "resource-action-steered-no-wram"
    / "pp-reduction-state1"
    / "captured-fields.json",
    "gigantic_ant_forced_magnet_scripted_entry": ROOT
    / "build"
    / "c2"
    / "battle-trace-oracles"
    / "manual-probes"
    / "resource-natural-scripted-entry"
    / "gigantic-ant-force-magnet-onhit-target32-active0-single-confirm"
    / "captured-fields.json",
    "guardian_general_forced_pp_reduction_scripted_entry": ROOT
    / "build"
    / "c2"
    / "battle-trace-oracles"
    / "manual-probes"
    / "resource-natural-scripted-entry"
    / "guardian-general-force-pp-reduction-onhit-9fac-pp32"
    / "captured-fields.json",
    "gigantic_ant_natural_table_magnet_seeded": ROOT
    / "build"
    / "c2"
    / "battle-trace-oracles"
    / "manual-probes"
    / "resource-natural-scripted-entry"
    / "gigantic-ant-natural-magnet-onhit-target32-active0-confirm-cycle"
    / "captured-fields.json",
    "guardian_general_natural_table_pp_reduction_seeded": ROOT
    / "build"
    / "c2"
    / "battle-trace-oracles"
    / "manual-probes"
    / "resource-natural-scripted-entry"
    / "guardian-general-natural-pp-reduction-onhit-target32-confirm-cycle"
    / "captured-fields.json",
}
EVIDENCE_TIERS = {
    "psi_magnet_transfer_controlled": "wram_seeded_controlled",
    "pp_reduction_loss_only_controlled": "wram_seeded_controlled",
    "psi_magnet_action_steered_no_wram": "action_row_steered_no_wram",
    "pp_reduction_action_steered_no_wram": "action_row_steered_no_wram",
    "gigantic_ant_forced_magnet_scripted_entry": "scripted_entry_enemy_action_forced",
    "guardian_general_forced_pp_reduction_scripted_entry": "scripted_entry_enemy_action_forced",
    "gigantic_ant_natural_table_magnet_seeded": "scripted_entry_natural_enemy_action_table_wram_seeded",
    "guardian_general_natural_table_pp_reduction_seeded": "scripted_entry_natural_enemy_action_table_wram_seeded",
}
DEFAULT_MANIFEST = ROOT / "manifests" / "c2-resource-amount-controlled-comparison.json"
DEFAULT_NOTE = ROOT / "notes" / "c2-resource-amount-controlled-comparison.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def capture_status(path: Path) -> tuple[str, dict[str, Any] | None]:
    if not path.exists():
        return "missing_capture", None
    payload = load_json(path)
    required = {
        "observed_addresses",
        "amount_roll",
        "target_row_pp_before",
        "target_row_pp_after",
        "source_row_pp_before",
        "source_row_pp_after",
        "reducer_row_pp_delta",
        "active_row_pp_delta",
        "transfer_or_loss_only_classification",
        "wram_patch_events",
    }
    missing = sorted(required - set(payload))
    if missing:
        return f"capture_missing_fields:{','.join(missing)}", payload
    return "capture_loaded", payload


def first_pp_setter_delta(capture: dict[str, Any], role: str) -> dict[str, Any]:
    for record in capture.get("pp_setter_deltas", []):
        if record.get("row_role") == role and isinstance(record.get("pp_delta"), dict):
            return record["pp_delta"]
    return {}


def build_lane(lane_id: str, path: Path) -> dict[str, Any]:
    status, capture = capture_status(path)
    lane: dict[str, Any] = {
        "lane_id": lane_id,
        "capture_path": repo_path(path),
        "status": status,
        "evidence_tier": EVIDENCE_TIERS.get(lane_id, "wram_seeded_controlled"),
        "source_promotion_allowed": False,
        "behavior_change_allowed": False,
        "natural_vanilla_amount_proven": False,
    }
    if capture is None:
        return lane
    target_delta = first_pp_setter_delta(capture, "selected_target_pp_setter") or capture.get("reducer_row_pp_delta", {})
    active_delta = first_pp_setter_delta(capture, "active_attacker_pp_setter") or capture.get("active_row_pp_delta", {})
    lane.update(
        {
            "classification": capture.get("classification"),
            "classification_evidence": capture.get("classification_evidence"),
            "transfer_or_loss_only_classification": capture.get("transfer_or_loss_only_classification"),
            "observed_addresses": capture.get("observed_addresses", []),
            "amount_roll": capture.get("amount_roll"),
            "text_payload_amount": capture.get("text_payload_amount"),
            "target_pp_before": target_delta.get("before") or capture.get("target_row_pp_before"),
            "target_pp_after": target_delta.get("after") or capture.get("target_row_pp_after"),
            "target_pp_delta": target_delta.get("delta"),
            "active_pp_before": active_delta.get("before") or capture.get("source_row_pp_before"),
            "active_pp_after": active_delta.get("after") or capture.get("source_row_pp_after"),
            "active_pp_delta": active_delta.get("delta"),
            "wram_patch_count": len(capture.get("wram_patch_events", [])),
            "trace_id": capture.get("trace_id"),
            "rom_sha1": capture.get("rom_sha1"),
            "save_state_id": capture.get("save_state_id"),
        }
    )
    return lane


def summarize(lanes: list[dict[str, Any]]) -> dict[str, Any]:
    loaded = [lane for lane in lanes if lane["status"] == "capture_loaded"]
    no_wram = [lane for lane in loaded if lane.get("evidence_tier") == "action_row_steered_no_wram"]
    scripted = [lane for lane in loaded if lane.get("evidence_tier") == "scripted_entry_enemy_action_forced"]
    natural_table = [
        lane
        for lane in loaded
        if lane.get("evidence_tier") == "scripted_entry_natural_enemy_action_table_wram_seeded"
    ]
    magnet = next((lane for lane in lanes if lane["lane_id"] == "psi_magnet_transfer_controlled"), {})
    reduction = next((lane for lane in lanes if lane["lane_id"] == "pp_reduction_loss_only_controlled"), {})
    magnet_no_wram = next((lane for lane in lanes if lane["lane_id"] == "psi_magnet_action_steered_no_wram"), {})
    reduction_no_wram = next((lane for lane in lanes if lane["lane_id"] == "pp_reduction_action_steered_no_wram"), {})
    return {
        "lane_count": len(lanes),
        "loaded_capture_count": len(loaded),
        "controlled_comparison_complete": len(loaded) == len(lanes),
        "action_steered_no_wram_capture_count": len(no_wram),
        "scripted_entry_enemy_action_capture_count": len(scripted),
        "scripted_entry_natural_table_seeded_capture_count": len(natural_table),
        "magnet_target_pp_delta": magnet.get("target_pp_delta"),
        "magnet_active_pp_delta": magnet.get("active_pp_delta"),
        "pp_reduction_target_pp_delta": reduction.get("target_pp_delta"),
        "pp_reduction_active_pp_delta": reduction.get("active_pp_delta"),
        "magnet_no_wram_target_pp_delta": magnet_no_wram.get("target_pp_delta"),
        "pp_reduction_no_wram_target_pp_delta": reduction_no_wram.get("target_pp_delta"),
        "natural_vanilla_amount_proven": False,
        "source_promotion_allowed": False,
        "behavior_change_allowed": False,
    }


def render_note(manifest: dict[str, Any]) -> str:
    lines = [
        "# C2 Resource Amount Controlled Comparison",
        "",
        "Generated by `tools/build_c2_resource_amount_controlled_comparison.py` from ignored local Mesen capture fields.",
        "This is controlled fixture evidence only: it compares reducer mechanics, not a fully natural vanilla battle state.",
        "",
        "## Summary",
        "",
    ]
    summary = manifest["summary"]
    lines.extend(
        [
            f"- controlled comparison complete: `{summary['controlled_comparison_complete']}`",
            f"- loaded captures: `{summary['loaded_capture_count']}` / `{summary['lane_count']}`",
            f"- action-row-steered no-WRAM captures: `{summary['action_steered_no_wram_capture_count']}`",
            f"- scripted-entry enemy-action captures: `{summary['scripted_entry_enemy_action_capture_count']}`",
            f"- scripted-entry natural-table seeded captures: `{summary['scripted_entry_natural_table_seeded_capture_count']}`",
            f"- natural vanilla amount proven: `{summary['natural_vanilla_amount_proven']}`",
            f"- source promotion allowed: `{summary['source_promotion_allowed']}`",
            f"- behavior change allowed: `{summary['behavior_change_allowed']}`",
            "",
            "## Comparison",
            "",
            "| Lane | Tier | Status | Observed | Amount | Target PP | Active PP | Classification |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for lane in manifest["lanes"]:
        observed = ", ".join(lane.get("observed_addresses", [])) or "-"
        target = f"{lane.get('target_pp_before', '-')} -> {lane.get('target_pp_after', '-')} ({lane.get('target_pp_delta', '-')})"
        active = f"{lane.get('active_pp_before', '-')} -> {lane.get('active_pp_after', '-')} ({lane.get('active_pp_delta', '-')})"
        lines.append(
            f"| `{lane['lane_id']}` | `{lane.get('evidence_tier', '-')}` | `{lane['status']}` | {observed} | "
            f"`{lane.get('amount_roll', '-')}` | {target} | {active} | "
            f"`{lane.get('transfer_or_loss_only_classification', '-')}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- PSI Magnet controlled capture shows transfer-style mechanics: target PP decreases and active battler PP increases by the same amount.",
            "- PP reduction controlled capture shows loss-only mechanics: target PP decreases while active battler PP remains unchanged.",
            "- The no-WRAM captures are cleaner amount evidence than the WRAM-seeded probes: the selected target already had PP in save 1, and the fixture-steered actions reduced that row by `5` and `9` PP respectively.",
            "- The scripted-entry forced-action captures keep canonical enemy/action rows in deterministic play: Gigantic Ant row `54` reaches `C2:9F5E -> C2:721D -> C2:7191`, and Guardian General row `95` reaches `C2:8E42 -> C2:721D`.",
            "- The scripted-entry natural-table seeded captures are stronger: they preserve the enemy rows' vanilla action tables, observe Gigantic Ant naturally selecting row `54`, and observe Guardian General naturally selecting row `95`; targeted WRAM PP seeding still keeps them below proof-grade promotion.",
            "- All captures still rely on fixture action steering or local WRAM seeding, so the natural proof lane remains open for real PSI Magnet and PP-reduction enemies.",
            "",
            "## Next Natural Proof Targets",
            "",
            "- PSI Magnet: `Gigantic Ant`, `Starman`, `Mobile Sprout`, or another row `54` user with a PP-bearing target.",
            "- PP reduction: `Guardian General` is the best nonzero-PP row `95` candidate; `Mad Duck` and `Armored Frog` remain route candidates but have zero enemy PP in the source table.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_manifest() -> dict[str, Any]:
    lanes = [build_lane(lane_id, path) for lane_id, path in DEFAULT_INPUTS.items()]
    return {
        "schema": "earthbound-decomp.c2-resource-amount-controlled-comparison.v1",
        "generated_by": "tools/build_c2_resource_amount_controlled_comparison.py",
        "inputs": {lane_id: repo_path(path) for lane_id, path in DEFAULT_INPUTS.items()},
        "summary": summarize(lanes),
        "lanes": lanes,
        "policy": {
            "fixture_or_wram_seeded_evidence_only": True,
            "natural_vanilla_amount_proven": False,
            "source_promotion_allowed": False,
            "behavior_change_allowed": False,
        },
    }


def main() -> int:
    manifest = build_manifest()
    DEFAULT_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    DEFAULT_NOTE.write_text(render_note(manifest), encoding="utf-8")
    print(f"Wrote {DEFAULT_MANIFEST}")
    print(f"Wrote {DEFAULT_NOTE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
