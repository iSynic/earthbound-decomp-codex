#!/usr/bin/env python3
"""Build the C2 battle trace-oracle manifest and index note."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "manifests" / "c2-battle-trace-oracle-plan.json"
DEFAULT_NOTES = ROOT / "notes" / "c2-battle-trace-oracle-index.md"

COMMON_CAPTURE_FIELDS = [
    "trace_id",
    "scenario_name",
    "rom_sha1",
    "save_state_id",
    "frame_or_instruction_counter",
    "pc",
    "routine_label",
    "registers.a",
    "registers.x",
    "registers.y",
    "registers.db",
    "registers.dp",
    "direct_page_snapshot",
    "wram_before",
    "wram_after",
    "ef_text_pointer",
    "c1_text_call",
    "classification",
    "classification_evidence",
]

ORACLES: list[dict[str, Any]] = [
    {
        "id": "c1_c2_target_action_staging",
        "priority": 1,
        "status": "trace_plan_ready",
        "question": "Which C1-staged action/target bytes are stable C2 contract fields?",
        "addresses": ["C1:ADB4", "C1:CE85", "C1:CFC6", "C2:B930", "C2:BAC5"],
        "diary_entries": [2, 3, 5, 10, 11, 12],
        "route_groups": {
            "inventory_selection_loop": {
                "addresses": ["C1:CFC6", "C1:CE85"],
                "role": "C1 item inventory loop and selected item-action resolution",
                "status": "linked_route_group",
            },
            "target_resolution_count": {
                "addresses": ["C1:ADB4", "C2:BAC5"],
                "role": "C1 target resolver plus C2 filtered target-row counter",
                "status": "linked_route_group",
            },
            "snapshot_export": {
                "addresses": ["C2:B930"],
                "role": "C2 battle selection snapshot export into the wider target/action overlay",
                "status": "remaining_fixture_gap",
                "next_probe_goal": "Start after the target/action choice is committed but before C1 choice/action text dispatch; prefer an item or PSI action whose D5:7B68 +0x08 second pointer is non-null.",
                "probe_breakpoint_hints": ["C1:B3DB", "C1:B462", "C1:B505", "C1:B859", "C1:B9A9", "C1:BA60", "C2:B930"],
                "watch_hints": [
                    "registers A/X/Y",
                    "C1 direct page $00..$2C",
                    "$99CE source slot row selected by A",
                    "$9FFA..$A047 snapshot block",
                    "$9FAC candidate rows",
                    "$A970/$A972 selected row pointers",
                    "post-return destination row after C2:B930",
                ],
            },
        },
        "capture_fields": [
            "input_action_id",
            "acting_slot",
            "c1_dp.$00_target_byte",
            "c1_dp.$01_battle_text_substitution_byte",
            "c1_dp.$14_$16_action_row_pointer",
            "c1_dp.$18_$1a_second_pointer_table_base",
            "c1_dp.$1e_$20_selected_action_pointer",
            "c1_dp.$22_party_loop_index",
            "c1_dp.$2a_acting_slot",
            "c1_dp.$2c_item_slot",
            "b930.source_slot_row_99ce",
            "b930.destination_base_x_or_y",
            "b930.destination_before_after_4e",
            "selection_record_base",
            "selection_record.+0",
            "selection_record.+1",
            "selection_record.+2",
            "selection_record.+4",
            "selection_record.+5",
            "candidate_record.+0x07",
            "candidate_record.+0x08",
            "candidate_record.+0x0A",
            "observed_target_byte",
        ],
        "evidence_notes": [
            "notes/battle-targetting-resolver-c1adb4-af50.md",
            "notes/battle-item-action-selection-c1ce85-c1cfc6.md",
            "notes/c2-target-selection-runtime-polish.md",
            "notes/c2-battle-contract-workahead.md",
        ],
        "source_paths": [
            "src/c1/c1_adb4_determine_battle_targetting.asm",
            "src/c1/c1_ce85_resolve_selected_battle_item_action.asm",
            "src/c1/c1_cfc6_open_battle_item_selection_loop.asm",
            "src/c2/c2_b930_export_battle_selection_snapshot.asm",
            "src/c2/c2_bac5_count_filtered_second_stage_rows.asm",
        ],
        "acceptance_criteria": [
            "observe target byte shapes 0x11, 0x01, or 0x12 in a local trace before promoting names",
            "record which C1 record fields survive into the C2 consumer path",
            "keep C1:CFC6 inventory selection distinct from C1:CE85 item action resolution",
        ],
    },
    {
        "id": "c2_40a4_current_action_payload",
        "priority": 1,
        "status": "trace_plan_ready",
        "question": "How does C2:40A4 apply second-pointer/current-action payloads over selected targets?",
        "addresses": ["C2:40A4", "C2:3D05", "D5:7B68"],
        "diary_entries": [6, 7, 10, 13, 25, 26, 31],
        "route_groups": {
            "payload_applicator": {
                "addresses": ["C2:40A4"],
                "role": "second-pointer/current-action payload applicator",
                "status": "remaining_fixture_gap",
                "next_probe_goal": "Start immediately before confirming a concrete second-pointer action, preferably a curative, recovery, item-status, or random damage/status item payload.",
                "probe_breakpoint_hints": ["C2:77CA", "C2:90C6", "C2:A89D", "C2:40A4", "C2:3D05", "C0:9279"],
                "watch_hints": ["$1E/$20 second pointer", "$00BC/$00BE payload pointer", "$A21C target mask domain", "$9FAC selected target rows", "$A96C/$A96E action state"],
            },
            "target_text_context_neighbor": {
                "addresses": ["C2:3D05"],
                "role": "nearby selected-target text-context builder reached by many non-payload routes",
                "status": "neighbor_only_until_c2_40a4_observed",
                "next_probe_goal": "Use only as a neighbor signal; do not mark the payload route covered until C2:40A4 itself is observed.",
            },
        },
        "capture_fields": [
            "action_row_id",
            "second_pointer",
            "target_mask_low",
            "target_mask_high",
            "selected_row_pointer",
            "payload_pc",
            "payload_kind",
            "per_target_loop_index",
        ],
        "evidence_notes": [
            "notes/class2-second-pointer-consumer-40a4.md",
            "notes/c2-action-dispatch-runtime-polish.md",
            "notes/c2-late-selected-row-runtime-polish.md",
        ],
        "source_paths": [
            "src/c2/c2_40a4_apply_battle_action_second_pointer_payload.asm",
            "src/c2/c2_3d05_build_battle_target_text_context.asm",
        ],
        "acceptance_criteria": [
            "capture at least one curative or item-status payload crossing C2:40A4",
            "separate target selection, payload application, and result text side effects",
        ],
    },
    {
        "id": "c2_724a_affliction_writer_matrix",
        "priority": 1,
        "status": "trace_plan_ready",
        "question": "Which callers use C2:724A versus adjacent direct status writers?",
        "addresses": ["C2:724A", "C2:9917", "C2:9F06", "C2:9FFE", "C2:A056", "C2:8CF1", "C2:A630", "C2:A82A", "C2:8D5A", "C2:A3D1"],
        "diary_entries": [14, 15, 29, 30, 31, 36, 37],
        "capture_fields": [
            "caller_pc",
            "selected_row_source",
            "x_subgroup_slot",
            "y_status_value",
            "target_field_for_direct_writer",
            "chance_gate_pc",
            "resistance_gate_pc",
            "writer_return_value",
            "success_text_pointer",
            "failure_text_pointer",
        ],
        "evidence_notes": [
            "notes/class2-affliction-apply-helper-724a.md",
            "notes/class2-battler-affliction-crosswalk.md",
            "notes/c2-psi-flash-runtime-polish.md",
            "notes/c2-late-status-runtime-polish.md",
            "notes/c2-concentration-seal-runtime-polish.md",
        ],
        "source_paths": [
            "src/c2/c2_724a_apply_battler_affliction_subgroup_value.asm",
            "src/c2/c2_98a1_gate_selected_battler_for_random_status_action.asm",
            "src/c2/c2_9917_try_apply_numb_status_to_selected_battler.asm",
            "src/c2/c2_9f06_run_resist_checked_asleep_status_action.asm",
            "src/c2/c2_9f57_run_asleep_status_wrapper_action.asm",
            "src/c2/c2_a056_run_resist_checked_strange_status_action.asm",
            "src/c2/c2_a630_apply_solidification_status_from_item_action.asm",
            "src/c2/c2_a82a_run_solidification_item_action.asm",
        ],
        "acceptance_criteria": [
            "record X/Y pairs for each C2:724A caller before broad status enum promotion",
            "keep concentration seal as direct +0x21 = 4 unless a local trace proves otherwise",
            "tie success/failure text to the same captured caller path",
        ],
    },
    {
        "id": "c2_8125_damage_abi_boundary",
        "priority": 1,
        "status": "trace_plan_ready",
        "question": "Where is the selected-target damage ABI boundary, and what remains downstream?",
        "addresses": [
            "C2:8125",
            "C2:7EAF",
            "C2:7550",
            "C2:A57A",
            "C2:A658",
            "C2:A5EC",
            "C2:941D",
            "C1:DC1C",
            "C1:DC66",
            "C1:AD0A",
            "C1:AD26",
            "C1:7EED",
            "C1:0DF6",
        ],
        "diary_entries": [21, 22, 23, 24, 34, 35],
        "capture_fields": [
            "amount_input",
            "damage_selector_x",
            "selected_target_row",
            "selected_target_row_decoded",
            "selected_target_row_at_downstream_decoded",
            "damage_entry_samples",
            "c1_text_join_samples",
            "text_payload_slot_samples",
            "caller_family",
            "post_call_hp_roller_state",
            "collapse_candidate_state",
            "result_text_pointer",
        ],
        "evidence_notes": [
            "notes/c2-hit-resolution-status-runtime-polish.md",
            "notes/c2-bottle-rocket-runtime-polish.md",
            "notes/c2-item-bomb-runtime-polish.md",
            "notes/c2-psi-common-runtime-polish.md",
        ],
        "source_paths": [
            "src/c2/c2_7eaf_run_hit_resolution_and_status_action_cluster.asm",
            "src/c2/c2_a658_run_bomb_common_splash_damage.asm",
            "src/c2/c2_a5ec_run_damage_plus_solidification_item_action.asm",
            "src/c2/c2_941d_check_selected_battler_timed_substate_blocker.asm",
            "src/c2/c2_9516_run_psi_rockin_common.asm",
            "src/c2/c2_957a_run_psi_fire_common.asm",
            "src/c2/c2_95cf_run_psi_freeze_common.asm",
            "src/c2/c2_9a80_run_psi_starstorm_common.asm",
        ],
        "acceptance_criteria": [
            "prove amount and selector inputs at C2:8125 without folding HP roller or collapse into the ABI name",
            "sample one random item, one bottle rocket, one bomb, and one PSI common path",
        ],
    },
    {
        "id": "hp_roller_collapse_boundary",
        "priority": 2,
        "status": "trace_plan_ready",
        "question": "Does collapse finalization occur after HP roller settlement?",
        "addresses": ["C2:8125", "C2:7550", "C2:7680", "C2:77CA", "C2:BB18", "C2:BC5C", "C1:DC1C", "C1:DC66"],
        "diary_entries": [8],
        "capture_fields": [
            "damage_call_pc",
            "hp_roller_before",
            "hp_roller_after",
            "candidate_promote_pc",
            "inactive_cleanup_pc",
            "collapse_start_pc",
            "collapse_text_pointer",
            "selected_row_before_after",
            "c1_text_join_samples",
            "settlement_order",
        ],
        "evidence_notes": [
            "notes/c2-hit-resolution-status-runtime-polish.md",
            "notes/c2-target-selection-runtime-polish.md",
            "notes/class2-handoff-4477-4703.md",
        ],
        "source_paths": [
            "src/c2/c2_7eaf_run_hit_resolution_and_status_action_cluster.asm",
            "src/c2/c2_7550_start_selected_battler_collapse_affliction_path.asm",
            "src/c2/c2_7680_display_enemy_death_text.asm",
            "src/c2/c2_bb18_promote_candidate_to_collapse_affliction_controller.asm",
            "src/c2/c2_bc5c_clear_inactive_candidate_live_slot_transient_fields.asm",
        ],
        "acceptance_criteria": [
            "capture a damage case that reaches collapse handling",
            "record ordering between damage application, HP roller state, and collapse text/action",
        ],
    },
    {
        "id": "resource_amount_pair_magnet_vs_pp_loss",
        "priority": 2,
        "status": "trace_plan_ready",
        "question": "Which PP effects are transfers and which are loss-only?",
        "addresses": ["C2:8E42", "C2:9F5E", "C2:9FE1", "C2:721D", "C2:7318", "C2:B360"],
        "diary_entries": [16, 18],
        "capture_fields": [
            "source_row_pp_before",
            "source_row_pp_after",
            "target_row_pp_before",
            "target_row_pp_after",
            "amount_roll",
            "cap_amount",
            "text_payload_amount",
            "transfer_or_loss_only_classification",
        ],
        "evidence_notes": [
            "notes/psi-magnet-drain-amount.md",
            "notes/c2-late-stat-resource-runtime-polish.md",
            "notes/c2-ef-battle-text-contract-workahead.md",
        ],
        "source_paths": [
            "src/c2/c2_8e42_run_pp_reduction_action.asm",
            "src/c2/c2_9f57_run_asleep_status_wrapper_action.asm",
            "src/c2/c2_7318_apply_battler_pp_recovery_feedback.asm",
            "src/c2/c2_b360_apply_battle_pp_recovery_consequence.asm",
        ],
        "acceptance_criteria": [
            "capture one PSI Magnet per-target transfer",
            "capture one PP reduction loss-only path",
            "do not reuse Magnet recovery wording for PP reduction unless the trace proves recovery",
        ],
    },
    {
        "id": "healing_ladder_gamma_omega",
        "priority": 2,
        "status": "trace_plan_ready",
        "question": "How do broad recovery and full-HP revival differ in the healing ladder?",
        "addresses": ["C2:9AEA", "C2:9B7A", "C2:9C2C", "C2:9CB8", "C2:7397", "C2:7294", "C2:7318"],
        "diary_entries": [25, 26, 32, 33],
        "capture_fields": [
            "recovery_selector",
            "selected_row",
            "hp_before",
            "hp_after",
            "pp_before",
            "pp_after",
            "hard_state_fields_before",
            "hard_state_fields_after",
            "text_branch",
        ],
        "evidence_notes": [
            "notes/c2-lifeup-healing-runtime-polish.md",
            "notes/battle-affliction-recovery-family-c29aea-a39d.md",
            "notes/c2-affliction-recovery-runtime-polish.md",
        ],
        "source_paths": [
            "src/c2/c2_9aea_try_recover_selected_battler_narrow_affliction.asm",
            "src/c2/c2_9b7a_try_recover_selected_battler_curative_afflictions.asm",
            "src/c2/c2_9c2c_try_recover_selected_battler_broad_afflictions.asm",
            "src/c2/c2_9cb8_try_recover_selected_battler_hard_state.asm",
            "src/c2/c2_7397_install_battler_heavy_recovery_reset.asm",
            "src/c2/c2_7294_apply_battler_hp_recovery_feedback.asm",
            "src/c2/c2_7318_apply_battler_pp_recovery_feedback.asm",
        ],
        "acceptance_criteria": [
            "capture Gamma broad recovery separately from Omega full-HP revival",
            "keep fixed PP recovery as a resource-specific trace until source path is locally pinned",
        ],
    },
    {
        "id": "numeric_stat_edge_behavior",
        "priority": 3,
        "status": "trace_plan_ready",
        "question": "Which width/clamp/random edges matter for stat and resource amount leaves?",
        "addresses": ["C2:B2E0", "C2:8EAE", "C2:8F21", "C2:9E38", "C2:9E86", "C2:A056"],
        "diary_entries": [9, 19, 20, 27, 28],
        "capture_fields": [
            "input_amount",
            "random_seed_or_roll",
            "math_width",
            "pre_clamp_value",
            "post_clamp_value",
            "affected_stat_field",
            "text_payload_amount",
        ],
        "evidence_notes": [
            "notes/c2-late-stat-resource-runtime-polish.md",
            "notes/c2-offense-defense-stat-actions-runtime-polish.md",
            "notes/battle-action-stat-change-family-c2b2e0-b5d7.md",
        ],
        "source_paths": [
            "src/c2/c2_b2e0_dispatch_battle_stat_change_consequence.asm",
            "src/c2/c2_8eae_run_guts_reduction_action.asm",
            "src/c2/c2_8f21_run_offense_defense_reduction_action.asm",
            "src/c2/c2_9e38_run_defense_spray_action.asm",
            "src/c2/c2_9e7f_run_defense_shower_action.asm",
            "src/c2/c2_a056_run_resist_checked_strange_status_action.asm",
        ],
        "acceptance_criteria": [
            "capture zero, one, small, and clamp-boundary cases before C-port integer normalization",
            "separate random selector proof from stat write proof",
        ],
    },
    {
        "id": "psi_flash_and_status_gate_family",
        "priority": 2,
        "status": "trace_plan_ready",
        "question": "Which PSI Flash and status gates share host-gate shape versus payload outcome?",
        "addresses": ["C2:98A1", "C2:9917", "C2:9F06", "C2:9FFE", "C2:A056", "C2:724A"],
        "diary_entries": [29, 36, 37],
        "capture_fields": [
            "flash_tier",
            "random_branch",
            "resistance_byte",
            "gate_result",
            "writer_x",
            "writer_y",
            "success_text_pointer",
            "failure_text_pointer",
        ],
        "evidence_notes": [
            "notes/c2-psi-flash-runtime-polish.md",
            "notes/class2-psi-flash-common-local-flow.md",
            "notes/class2-affliction-apply-helper-724a.md",
        ],
        "source_paths": [
            "src/c2/c2_98a1_gate_selected_battler_for_random_status_action.asm",
            "src/c2/c2_9917_try_apply_numb_status_to_selected_battler.asm",
            "src/c2/c2_9f06_run_resist_checked_asleep_status_action.asm",
            "src/c2/c2_9f57_run_asleep_status_wrapper_action.asm",
            "src/c2/c2_a056_run_resist_checked_strange_status_action.asm",
            "src/c2/c2_724a_apply_battler_affliction_subgroup_value.asm",
        ],
        "acceptance_criteria": [
            "capture Flash paralysis as the first compact writer-gate oracle",
            "compare resist-checked asleep/paralysis/strange gates before sharing a C-port host-gate helper",
        ],
    },
    {
        "id": "battle_text_payload_join",
        "priority": 2,
        "status": "trace_plan_ready",
        "question": "How do C2 result routines stage C1/EF battle-text pointer and amount payloads?",
        "addresses": ["C1:DC1C", "C1:DC66", "C1:AD0A", "C1:AD26", "EF:69A1", "EF:75AB"],
        "diary_entries": [24, 25, 26, 31, 34, 35],
        "capture_fields": [
            "c2_caller_pc",
            "direct_text_pointer_0e_10",
            "payload_pointer_12_14",
            "c1_entrypoint",
            "battle_text_consumer_command",
            "ef_script_pointer",
            "substitution_payload_kind",
            "displayed_amount_source",
        ],
        "evidence_notes": [
            "notes/c2-ef-battle-text-contract-workahead.md",
            "notes/battle-text-entry-family-c1dc1c-dd7c.md",
            "notes/class2-concrete-battle-text-call-paths.md",
            "notes/battle-action-row-crosswalk.md",
            "notes/ef-battle-text-consumer-lane-contracts.md",
        ],
        "source_paths": [
            "src/c1/c1_dc1c_display_battle_text_from_pointer.asm",
            "src/c1/c1_dc66_display_battle_text_with_substitution_payload.asm",
            "src/c2/c2_7294_apply_battler_hp_recovery_feedback.asm",
            "src/c2/c2_7318_apply_battler_pp_recovery_feedback.asm",
            "src/ef/ef_4e20_c51b_text_payload_data.asm",
        ],
        "acceptance_criteria": [
            "capture one direct text and one amount-substitution text path",
            "keep EF row/payload naming separate from C2 action behavior naming",
            "treat source/doc lane clarification as safe, but keep runtime proof blocked until an ordinary-battle fixture produces reviewed trace evidence",
        ],
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the C2 battle trace-oracle manifest.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Manifest JSON output.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Markdown index output.")
    return parser.parse_args()


def build_manifest() -> dict[str, Any]:
    oracles = []
    for oracle in ORACLES:
        merged = dict(oracle)
        merged["capture_fields"] = COMMON_CAPTURE_FIELDS + list(oracle["capture_fields"])
        merged["promotion_allowed_by_plan"] = False
        merged["evidence_class"] = "trace_required_before_source_promotion"
        oracles.append(merged)
    return {
        "schema": "earthbound-decomp.c2-battle-trace-oracle-plan.v1",
        "status": "trace_plan_ready_runner_pending",
        "summary": {
            "oracle_count": len(oracles),
            "priority_counts": {
                str(priority): sum(1 for oracle in oracles if oracle["priority"] == priority)
                for priority in sorted({int(oracle["priority"]) for oracle in oracles})
            },
            "promotion_allowed_by_plan": False,
            "runtime_runner_status": "pending",
        },
        "policy": {
            "source_of_truth": "local source, byte-equivalence, generated manifests, and local runtime traces",
            "c_port_diary_role": "intake evidence and prioritization, not source-facing proof",
            "ghidra_role": "visual/decode hint only",
            "source_edits_allowed_from_manifest_alone": False,
        },
        "references": [
            "notes/phase-2-semantic-closure-plan.md",
            "notes/c-port-feedback-intake.md",
            "notes/c2-battle-trace-oracle-plan.md",
            "notes/c2-battle-contract-workahead.md",
            "notes/c2-ef-battle-text-contract-workahead.md",
        ],
        "first_trace_pass": [
            "c1_c2_target_action_staging",
            "c2_40a4_current_action_payload",
            "c2_724a_affliction_writer_matrix",
            "c2_8125_damage_abi_boundary",
            "hp_roller_collapse_boundary",
            "resource_amount_pair_magnet_vs_pp_loss",
        ],
        "oracles": oracles,
    }


def render_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# C2 Battle Trace Oracle Index",
        "",
        "Generated by `tools/build_c2_battle_trace_oracle_manifest.py`.",
        "",
        "This index is the machine-readable companion to",
        "`notes/c2-battle-trace-oracle-plan.md`. It keeps Phase 2 C2 battle",
        "proof lanes in one stable schema before any emulator/runtime runner",
        "exists.",
        "",
        "## Summary",
        "",
        f"- oracles: `{manifest['summary']['oracle_count']}`",
        f"- status: `{manifest['status']}`",
        f"- promotion allowed by plan: `{manifest['summary']['promotion_allowed_by_plan']}`",
        f"- runtime runner status: `{manifest['summary']['runtime_runner_status']}`",
        "",
        "## Oracle Queue",
        "",
        "| Priority | Oracle | Key addresses | Evidence notes |",
        "| ---: | --- | --- | --- |",
    ]
    for oracle in manifest["oracles"]:
        notes = "<br>".join(oracle["evidence_notes"][:3])
        addresses = ", ".join(oracle["addresses"][:6])
        if len(oracle["addresses"]) > 6:
            addresses += ", ..."
        lines.append(f"| {oracle['priority']} | `{oracle['id']}` | `{addresses}` | {notes} |")
    lines.extend(
        [
            "",
            "## First Trace Pass",
            "",
        ]
    )
    for oracle_id in manifest["first_trace_pass"]:
        oracle = next(item for item in manifest["oracles"] if item["id"] == oracle_id)
        lines.append(f"- `{oracle_id}`: {oracle['question']}")
    lines.extend(
        [
            "",
            "## Promotion Policy",
            "",
            "- This manifest does not permit source-facing semantic promotion by itself.",
            "- Each oracle must produce local trace or source evidence before labels,",
            "  comments, or C-port helper names are strengthened.",
            "- Ghidra-SNES observations can be attached as hints only.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    output = Path(args.output)
    notes = Path(args.notes)
    manifest = build_manifest()
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(manifest), encoding="utf-8")
    print(f"Wrote {output} and {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
