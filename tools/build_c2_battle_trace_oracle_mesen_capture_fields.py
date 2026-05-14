#!/usr/bin/env python3
"""Build reviewed capture fields from a rich C2 Mesen oracle trace."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import rom_tools


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PACKET = ROOT / "manifests" / "c2-battle-trace-oracle-packet.json"
SUPPORTED_ORACLES = {
    "c1_c2_target_action_staging",
    "c2_724a_affliction_writer_matrix",
    "c2_8125_damage_abi_boundary",
    "c2_40a4_current_action_payload",
    "hp_roller_collapse_boundary",
    "resource_amount_pair_magnet_vs_pp_loss",
}
ROUTINE_LABELS = {
    "C0:9279": "C09279_DispatchBattleActionPayload",
    "C1:ADB4": "C1ADB4_DetermineBattleTargetting",
    "C1:CE85": "C1CE85_ResolveSelectedBattleItemAction",
    "C1:CFC6": "C1CFC6_OpenBattleItemSelectionLoop",
    "C1:DC1C": "C1DC1C_DisplayBattleTextFromPointer",
    "C1:DC66": "C1DC66_DisplayBattleTextWithSubstitutionPayload",
    "C1:AD0A": "C1AD0A_StageBattleTextSubstitutionPointer",
    "C1:AD26": "C1AD26_ReadBattleTextSubstitutionPointer",
    "C1:7EED": "C17EED_PrintActionAmountConsumer",
    "C1:0DF6": "C10DF6_PrintNumber",
    "C2:3D05": "C23D05_BuildBattleTargetTextContext",
    "C2:3E32": "C23E32_BuildBattleTargetTextContext_SelectedTargetName",
    "C2:40A4": "C240A4_ApplyBattleActionSecondPointerPayload",
    "C2:40F2": "C240F2_ApplyBattleActionSecondPointerPayload_DispatchActorDomainPayload",
    "C2:4147": "C24147_ApplyBattleActionSecondPointerPayload_DispatchBattlerDomainPayload",
    "C2:416F": "C2416F_FilterBattleActionTargetMaskByRowState",
    "C2:4703": "C24703_BattleTargetPresentationNeighbor",
    "C2:724A": "C2724A_ApplySelectedRowAfflictionSlotValue",
    "C2:8125": "C28125_ApplyDamageToSelectedTarget",
    "C2:7EAF": "C27EAF_RunHitResolutionAndStatusActionCluster",
    "C2:7550": "C27550_StartSelectedBattlerCollapseAfflictionPath",
    "C2:7680": "C27680_DisplayEnemyDeathText",
    "C2:7191": "C27191_SetBattlerPpTarget",
    "C2:721D": "C2721D_ReduceBattlerPpTarget",
    "C2:7318": "C27318_ApplyBattlerPpRecoveryFeedback",
    "C2:8E42": "C28E42_RunPpReductionAction",
    "C2:9051": "C29051_QueuedBattlerStatShieldNormalizationCallback",
    "C2:98A1": "C298A1_GateSelectedBattlerForRandomStatusAction",
    "C2:9F5E": "C29F5E_RunHpSuckerStylePpDrainAction",
    "C2:9FE1": "C29FE1_RunPpDrainIfTargetCanActWrapper",
    "C2:9917": "C29917_TryApplyNumbStatusToSelectedBattler",
    "C2:90C6": "C290C6_RunBattlerNormalizationActionWrapper",
    "C2:915C": "C2915C_RunBattlerNormalizationActionWrapper_InvokeSecondPointerPayload",
    "C2:B360": "C2B360_ApplyBattlePpRecoveryConsequence",
    "C2:77CA": "C277CA_RunSelectedBattlerCollapsePresentationTail",
    "C2:941D": "C2941D_CheckSelectedBattlerTimedSubstateBlocker",
    "C2:BB18": "C2BB18_PromoteCandidateToCollapseAfflictionController",
    "C2:BC5C": "C2BC5C_ClearInactiveCandidateLiveSlotTransientFields",
    "C2:B930": "C2B930_ExportBattleSelectionSnapshot",
    "C2:BAC5": "C2BAC5_CountFilteredSecondStageRows",
}
BATTLE_ROW_FIELD_OFFSETS = {
    "row_word_plus_0x00": 0x00,
    "row_word_plus_0x02": 0x02,
    "row_word_plus_0x04": 0x04,
    "active_gate_byte_plus_0x0c": 0x0C,
    "route_state_byte_plus_0x0d": 0x0D,
    "ally_enemy_or_collapse_route_byte_plus_0x0e": 0x0E,
    "collapse_text_route_byte_plus_0x0f": 0x0F,
    "hp_live_word_plus_0x11": 0x11,
    "hp_target_word_plus_0x13": 0x13,
    "hp_max_word_plus_0x15": 0x15,
    "affliction_primary_byte_plus_0x1d": 0x1D,
    "affliction_slot_1_byte_plus_0x1e": 0x1E,
    "affliction_slot_2_byte_plus_0x1f": 0x1F,
    "affliction_slot_3_byte_plus_0x20": 0x20,
    "affliction_slot_4_byte_plus_0x21": 0x21,
    "affliction_slot_5_byte_plus_0x22": 0x22,
    "timed_substate_byte_plus_0x23": 0x23,
    "special_damage_halving_flag_plus_0x24": 0x24,
    "shield_countdown_byte_plus_0x25": 0x25,
    "offense_word_plus_0x26": 0x26,
    "defense_word_plus_0x28": 0x28,
    "paralysis_resistance_byte_plus_0x37": 0x37,
    "freeze_resistance_byte_plus_0x38": 0x38,
    "flash_resistance_byte_plus_0x39": 0x39,
    "fire_resistance_byte_plus_0x3a": 0x3A,
    "brainshock_resistance_byte_plus_0x3b": 0x3B,
    "hypnosis_resistance_byte_plus_0x3c": 0x3C,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build C2 Mesen trace capture fields.")
    parser.add_argument("--oracle-id", default="c2_8125_damage_abi_boundary")
    parser.add_argument("--packet", default=str(DEFAULT_PACKET))
    parser.add_argument("--trace", help="Raw trace JSONL path. Defaults to packet raw_trace_path.")
    parser.add_argument("--rom", help="EarthBound ROM path. Defaults to rom_tools discovery.")
    parser.add_argument("--output", help="Captured-fields JSON path. Defaults beside the trace.")
    parser.add_argument(
        "--classification",
        default="needs_followup",
        choices=["confirmed_contract", "refined_contract", "contradicted_plan", "needs_followup"],
    )
    parser.add_argument("--classification-evidence", help="Override generated classification evidence.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_job(packet: dict[str, Any], oracle_id: str) -> dict[str, Any]:
    for job in packet.get("jobs", []):
        if job.get("oracle_id") == oracle_id:
            return job
    raise ValueError(f"could not find oracle {oracle_id!r}")


def read_trace(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_no}: trace row must be object")
        rows.append(row)
    return rows


def first_row(rows: list[dict[str, Any]], *, event_type: str, pc: str | None = None) -> dict[str, Any] | None:
    for row in rows:
        if row.get("type") != event_type:
            continue
        if pc is not None and row.get("pc") != pc:
            continue
        return row
    return None


def first_after(rows: list[dict[str, Any]], start_index: int, *, event_type: str, pc: str | None = None) -> dict[str, Any] | None:
    for row in rows[start_index + 1 :]:
        if row.get("type") != event_type:
            continue
        if pc is not None and row.get("pc") != pc:
            continue
        return row
    return None


def row_index(rows: list[dict[str, Any]], target: dict[str, Any]) -> int:
    for index, row in enumerate(rows):
        if row is target:
            return index
    raise ValueError("target row not found")


def require_text(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    if value is None or value == "":
        raise ValueError(f"trace row missing {key}")
    return str(value)


def parse_hex_bytes(hex_text: str) -> bytes:
    tokens = hex_text.split()
    if not tokens:
        return b""
    return bytes(int(token, 16) for token in tokens)


def hex_byte(value: int | None) -> str | None:
    if value is None:
        return None
    return f"0x{value:02X}"


def hex_word(value: int | None) -> str | None:
    if value is None:
        return None
    return f"0x{value:04X}"


def u8(data: bytes, offset: int) -> int | None:
    if offset >= len(data):
        return None
    return data[offset]


def u16le(data: bytes, offset: int) -> int | None:
    if offset + 1 >= len(data):
        return None
    return data[offset] | (data[offset + 1] << 8)


def pointer_word(data: bytes, offset: int) -> dict[str, str | None]:
    value = u16le(data, offset)
    return {"offset": f"+0x{offset:02X}", "word": hex_word(value)}


def format_far_pointer(lo: int | None, hi: int | None) -> str:
    if lo is None or hi is None:
        return "not_captured"
    bank = hi & 0x00FF
    return f"{bank:02X}:{lo:04X}"


def decode_battle_row(row_hex: str, *, pointer: str | None = None) -> dict[str, Any]:
    data = parse_hex_bytes(row_hex)
    fields: dict[str, Any] = {
        "pointer": pointer or "not_captured",
        "captured_byte_count": len(data),
    }
    for name, offset in BATTLE_ROW_FIELD_OFFSETS.items():
        if "_word_" in name:
            fields[name] = hex_word(u16le(data, offset))
        else:
            fields[name] = hex_byte(u8(data, offset))
    fields["c28125_source_gate_summary"] = {
        "active_gate_plus_0x0c_must_be_0x01": fields["active_gate_byte_plus_0x0c"],
        "primary_affliction_plus_0x1d_blocks_if_0x01": fields["affliction_primary_byte_plus_0x1d"],
        "collapse_call_candidate_when_hp_live_plus_0x11_becomes_zero_after_calc_damage": fields["hp_live_word_plus_0x11"],
    }
    return fields


def hex_word_to_int(value: Any) -> int | None:
    text = str(value or "")
    if text.startswith("0x"):
        try:
            return int(text, 16)
        except ValueError:
            return None
    if not text.startswith("$"):
        return None
    try:
        return int(text[1:], 16)
    except ValueError:
        return None


def word_delta(before: Any, after: Any) -> int | None:
    before_int = hex_word_to_int(before)
    after_int = hex_word_to_int(after)
    if before_int is None or after_int is None:
        return None
    return after_int - before_int


def hp_delta(before: dict[str, Any] | str, after: dict[str, Any] | str) -> dict[str, Any] | str:
    if not isinstance(before, dict) or not isinstance(after, dict):
        return "not_available"
    live_before = before.get("hp_live_word_plus_0x11")
    live_after = after.get("hp_live_word_plus_0x11")
    target_before = before.get("hp_target_word_plus_0x13")
    target_after = after.get("hp_target_word_plus_0x13")
    max_before = before.get("hp_max_word_plus_0x15")
    max_after = after.get("hp_max_word_plus_0x15")
    return {
        "hp_live_before": live_before,
        "hp_live_after": live_after,
        "hp_live_delta": word_delta(live_before, live_after),
        "hp_target_before": target_before,
        "hp_target_after": target_after,
        "hp_target_delta": word_delta(target_before, target_after),
        "hp_max_before": max_before,
        "hp_max_after": max_after,
    }


def selected_row_hp_changed(before: dict[str, Any], after: dict[str, Any]) -> bool:
    return (
        before.get("hp_live_word_plus_0x11") != after.get("hp_live_word_plus_0x11")
        or before.get("hp_target_word_plus_0x13") != after.get("hp_target_word_plus_0x13")
    )


def first_selected_row_hp_change_after(
    rows: list[dict[str, Any]],
    start_index: int,
    *,
    pointer: str,
    before_row: dict[str, Any],
) -> dict[str, Any] | None:
    for row in rows[start_index + 1 :]:
        if row.get("type") != "breakpoint_hit":
            continue
        row_hex = str(row.get("selectedTargetRowHex") or "")
        if not row_hex:
            continue
        if str(row.get("selectedTargetPointer") or "") != pointer:
            continue
        decoded = decode_battle_row(row_hex, pointer=pointer)
        if selected_row_hp_changed(before_row, decoded):
            return {"trace_row": row, "decoded_row": decoded}
    return None


def decode_c1_text_entry(row: dict[str, Any]) -> dict[str, Any]:
    pc = str(row.get("pc") or "")
    data = parse_hex_bytes(str(row.get("directPageHex") or ""))
    primary_lo = u16le(data, 0x0E)
    primary_hi = u16le(data, 0x10)
    payload_lo = u16le(data, 0x12)
    payload_hi = u16le(data, 0x14)
    event: dict[str, Any] = {
        "frame": row.get("frame"),
        "pc": pc,
        "routine_label": ROUTINE_LABELS.get(pc, "unknown_c1_text_entry"),
        "cpu_dp": row.get("cpuDP"),
        "cpu_sp": row.get("cpuSP"),
        "primary_text_pointer_0e_10": row.get("callerDpPrimaryTextPointer") or format_far_pointer(primary_lo, primary_hi),
        "dp_words": {
            "caller_primary_text_lo_plus_0x0e": pointer_word(data, 0x0E),
            "caller_primary_text_hi_plus_0x10": pointer_word(data, 0x10),
            "caller_payload_lo_plus_0x12": pointer_word(data, 0x12),
            "caller_payload_hi_plus_0x14": pointer_word(data, 0x14),
        },
        "runner_decoded_slots": {
            "caller_dp_primary_text_pointer": row.get("callerDpPrimaryTextPointer"),
            "caller_dp_payload_pointer": row.get("callerDpPayloadPointer"),
            "caller_dp_payload_lo": row.get("callerDpPayloadLo"),
            "caller_dp_payload_hi": row.get("callerDpPayloadHi"),
            "wram9d11": row.get("wram9d11"),
            "wram9d12": row.get("wram9d12"),
            "wram9d14": row.get("wram9d14"),
            "text_payload_slots_hex": row.get("textPayloadSlotsHex"),
        },
    }
    if pc == "C1:DC66":
        event.update(
            {
                "text_call_kind": "display_with_substitution_payload",
                "substitution_payload_12_14": {
                    "lo": hex_word(payload_lo),
                    "hi": hex_word(payload_hi),
                    "as_far_pointer_if_pointer_payload": format_far_pointer(payload_lo, payload_hi),
                    "amount_low_word_if_amount_payload": hex_word(payload_lo),
                },
                "contract_note": (
                    "C1:DC66 reads caller $0E/$10 as the primary EF script pointer and caller $12/$14 "
                    "as the payload committed through C1:AD0A into $9D12/$9D14."
                ),
            }
        )
    elif pc == "C1:DC1C":
        event.update(
            {
                "text_call_kind": "direct_text_pointer_display",
                "substitution_payload_12_14": "not_committed_by_c1_dc1c",
                "contract_note": "C1:DC1C reads caller $0E/$10 as the EF script pointer and does not commit a secondary payload.",
            }
        )
    else:
        event["text_call_kind"] = "unknown"
    return event


def build_c1_text_events(rows: list[dict[str, Any]], *, start_index: int = -1) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for row in rows[start_index + 1 :]:
        if row.get("type") != "breakpoint_hit":
            continue
        if row.get("pc") in {"C1:DC1C", "C1:DC66"}:
            events.append(decode_c1_text_entry(row))
    return events


def build_text_payload_slot_samples(rows: list[dict[str, Any]], *, start_index: int = -1) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for row in rows[start_index + 1 :]:
        if row.get("type") != "breakpoint_hit":
            continue
        pc = str(row.get("pc") or "")
        if pc not in {"C1:DC1C", "C1:DC66", "C1:AD0A", "C1:AD26", "C1:7EED", "C1:0DF6"}:
            continue
        samples.append(
            {
                "frame": row.get("frame"),
                "pc": pc,
                "routine_label": ROUTINE_LABELS.get(pc, "unknown_text_payload_join"),
                "caller_dp_primary_text_pointer": row.get("callerDpPrimaryTextPointer"),
                "caller_dp_payload_pointer": row.get("callerDpPayloadPointer"),
                "caller_dp_payload_lo": row.get("callerDpPayloadLo"),
                "caller_dp_payload_hi": row.get("callerDpPayloadHi"),
                "wram9d11": row.get("wram9d11"),
                "wram9d12": row.get("wram9d12"),
                "wram9d14": row.get("wram9d14"),
                "text_payload_slots_hex": row.get("textPayloadSlotsHex"),
                "consumer_role": {
                    "C1:DC1C": "direct display wrapper entry",
                    "C1:DC66": "display wrapper with payload entry",
                    "C1:AD0A": "payload slot setter",
                    "C1:AD26": "payload slot getter",
                    "C1:7EED": "1C 0F action amount text consumer",
                    "C1:0DF6": "number printer reached from amount consumer",
                }.get(pc, "unknown"),
            }
        )
    return samples


def build_c2_8125_samples(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if row.get("type") != "breakpoint_hit" or row.get("pc") != "C2:8125":
            continue
        row_hex = str(row.get("selectedTargetRowHex") or "")
        pointer = str(row.get("selectedTargetPointer") or "")
        downstream = first_after(rows, index, event_type="breakpoint_hit", pc="C2:7EAF")
        downstream_hex = str((downstream or {}).get("selectedTargetRowHex") or "")
        row_before = decode_battle_row(row_hex, pointer=pointer)
        first_hp_change = first_selected_row_hp_change_after(
            rows,
            index,
            pointer=pointer,
            before_row=row_before,
        )
        first_hp_change_row = (first_hp_change or {}).get("trace_row")
        first_hp_change_decoded = (first_hp_change or {}).get("decoded_row")
        samples.append(
            {
                "frame": row.get("frame"),
                "amount_input": row.get("cpuA"),
                "damage_selector_x": row.get("cpuX"),
                "damage_selector_y": row.get("cpuY"),
                "selected_target_pointer": pointer,
                "row_before": row_before,
                "downstream_pc": (downstream or {}).get("pc", "not_observed"),
                "row_at_downstream": decode_battle_row(downstream_hex, pointer=pointer) if downstream_hex else "not_observed",
                "first_selected_row_hp_change_pc": (first_hp_change_row or {}).get("pc", "not_observed"),
                "first_selected_row_hp_change_frame": (first_hp_change_row or {}).get("frame", "not_observed"),
                "row_at_first_selected_row_hp_change": first_hp_change_decoded or "not_observed",
                "hp_delta_at_first_selected_row_hp_change": hp_delta(row_before, first_hp_change_decoded or "not_observed"),
            }
        )
    return samples


def compact_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def row_brief(row: dict[str, Any] | None) -> dict[str, Any] | str:
    if row is None:
        return "not_observed"
    pc = str(row.get("pc") or "")
    return {
        "frame": row.get("frame"),
        "pc": pc,
        "routine_label": ROUTINE_LABELS.get(pc, "unknown_or_unlabeled_trace_pc"),
        "cpu_a": row.get("cpuA"),
        "cpu_x": row.get("cpuX"),
        "cpu_y": row.get("cpuY"),
        "selected_target_pointer": row.get("selectedTargetPointer"),
        "caller_dp_primary_text_pointer": row.get("callerDpPrimaryTextPointer"),
        "caller_dp_payload_pointer": row.get("callerDpPayloadPointer"),
        "text_payload_slots_hex": row.get("textPayloadSlotsHex"),
    }


def decoded_selected_row(row: dict[str, Any] | None) -> dict[str, Any] | str:
    if row is None:
        return "not_observed"
    row_hex = str(row.get("selectedTargetRowHex") or "")
    if not row_hex:
        return "not_captured"
    return decode_battle_row(row_hex, pointer=str(row.get("selectedTargetPointer") or "not_captured"))


def post_call_snapshot(rows: list[dict[str, Any]], call_pc: str) -> dict[str, Any] | None:
    for row in rows:
        if row.get("type") == "post_call_snapshot" and row.get("callPc") == call_pc:
            return row
    return None


def watch_snapshot(
    rows: list[dict[str, Any]],
    *,
    pc: str,
    watch_id: str,
    start_index: int = -1,
) -> dict[str, Any] | None:
    for row in rows[start_index + 1 :]:
        if row.get("type") == "watch_snapshot" and row.get("pc") == pc and row.get("watchId") == watch_id:
            return row
    return None


def dispatch_samples(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for row in rows:
        if row.get("type") != "breakpoint_hit" or row.get("pc") != "C0:9279":
            continue
        target = str(row.get("dispatchTargetPointer") or row.get("absolute00bcPointer") or row.get("dp00bcPointer") or "")
        samples.append(
            {
                "frame": row.get("frame"),
                "target": target or "not_captured",
                "return_rtl_adjusted": row.get("stackReturnRtlAdjusted"),
                "route_group": row.get("routeGroup"),
                "probe_source": row.get("probeSource"),
                "selected_target_pointer": row.get("selectedTargetPointer"),
                "current_target_mask": row.get("currentTargetMaskHex"),
            }
        )
    return samples


def build_c2_40a4_fields(
    job: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    rom: Path,
    trace: Path,
    classification: str,
    evidence: str | None,
) -> dict[str, Any]:
    runner_start = first_row(rows, event_type="runner_start")
    state_load = first_row(rows, event_type="before_state_load")
    hit = first_row(rows, event_type="breakpoint_hit", pc="C2:40A4")
    if hit is None:
        raise ValueError("trace does not contain a C2:40A4 breakpoint hit")
    hit_index = row_index(rows, hit)
    post = post_call_snapshot(rows, "C2:40A4")
    if post is None:
        raise ValueError("trace does not contain a return_from:C2:40A4 post-call snapshot")
    wrapper = first_breakpoint(rows, "C2:90C6")
    callsite = first_breakpoint(rows, "C2:915C")
    context = first_breakpoint(rows, "C2:3D05")
    dispatches = dispatch_samples(rows)
    loop_dispatches = [
        sample
        for sample in dispatches
        if sample.get("return_rtl_adjusted") in {"C2:4104", "C2:4159"}
    ]
    direct_dispatches = [
        sample
        for sample in dispatches
        if sample.get("return_rtl_adjusted") == "C2:5D3D"
    ]
    observed = sorted(
        {str(row.get("pc")) for row in rows if row.get("type") == "breakpoint_hit" and row.get("pc")}
    )
    generated_evidence = (
        "Fixture-steered Bash-row ROM rewires battle action row 4 to C2:90C6. "
        "The trace observes C2:90C6 -> C2:915C -> C2:40A4, then C2:40A4 "
        "dispatches the C2:9051 payload through C0:9279 and returns through "
        "the target-loop sites C2:4104/C2:4159. This proves wrapper and loop "
        "mechanics only; it is not evidence for vanilla Bash behavior."
    )
    target_mask = {
        "before_lo": post.get("targetMaskBeforeLo"),
        "before_hi": post.get("targetMaskBeforeHi"),
        "after_lo": post.get("targetMaskAfterLo"),
        "after_hi": post.get("targetMaskAfterHi"),
        "hit_mask_hex": hit.get("currentTargetMaskHex"),
    }
    active_rows = {
        "attacker_pointer": post.get("activeAttackerPointer"),
        "attacker_row_hex": post.get("activeAttackerRowHex"),
        "target_pointer": post.get("activeTargetPointer"),
        "target_row_hex": post.get("activeTargetRowHex"),
        "context_builder": row_brief(context),
    }
    busy_gate = {
        "battle_busy_flag_1b9e": post.get("battleBusyFlag1b9e"),
        "effect_countdown_aec2": post.get("effectCountdownAec2"),
        "effect_pointer_aecc_aece": post.get("effectPointerAeccAece"),
        "effect_step_state_hex": post.get("effectStepStateHex"),
    }
    loop_index = {
        "wrapper_entry": row_brief(wrapper),
        "static_callsite": row_brief(callsite),
        "loop_dispatches": loop_dispatches,
        "direct_dispatch_contrast": direct_dispatches,
        "all_dispatches": dispatches,
        "observed_addresses": observed,
        "proof_limit": "Fixture row proves C2:40A4 mechanics and loop dispatch shape, not the real Bash action contract.",
    }
    fields = {
        "trace_id": f"{trace.as_posix()} sha256:{sha256(trace)}",
        "scenario_name": require_text(runner_start or {}, "scenarioName"),
        "rom_sha1": sha1(rom),
        "save_state_id": save_state_id(state_load),
        "frame_or_instruction_counter": f"frame:{hit.get('frame')} return_frame:{post.get('frame')} cycle:{hit.get('cpuCycleCount')}",
        "pc": "C2:40A4",
        "routine_label": ROUTINE_LABELS["C2:40A4"],
        "registers.a": require_text(hit, "cpuA"),
        "registers.x": require_text(hit, "cpuX"),
        "registers.y": require_text(hit, "cpuY"),
        "registers.db": require_text(hit, "cpuDB"),
        "registers.dp": require_text(hit, "cpuDP"),
        "direct_page_snapshot": require_text(hit, "directPageHex"),
        "wram_before": require_text(hit, "selectedTargetRowHex"),
        "wram_after": require_text(post, "activeTargetRowHex"),
        "ef_text_pointer": hit.get("callerDpPrimaryTextPointer", "not_applicable_to_fixture_payload_wrapper"),
        "c1_text_call": "not_applicable_to_c2_40a4_fixture_wrapper",
        "classification": classification,
        "classification_evidence": evidence or generated_evidence,
        "action_row_id": "4 (fixture-patched Bash row)",
        "second_pointer": require_text(post, "callerFrameSecondPayloadPointer"),
        "c2_40a4.static_callsite": compact_json(row_brief(callsite)),
        "c2_40a4.caller_frame_second_payload_pointer": require_text(post, "callerFrameSecondPayloadPointer"),
        "c2_40a4.current_action_payload_pointer": require_text(post, "currentActionPayloadPointer"),
        "c2_40a4.current_target_mask_before_after": compact_json(target_mask),
        "c2_40a4.active_attacker_target_rows": compact_json(active_rows),
        "c2_40a4.effect_busy_gate": compact_json(busy_gate),
        "target_mask_low": f"{post.get('targetMaskBeforeLo')} -> {post.get('targetMaskAfterLo')}",
        "target_mask_high": f"{post.get('targetMaskBeforeHi')} -> {post.get('targetMaskAfterHi')}",
        "selected_row_pointer": str(post.get("activeTargetPointer") or hit.get("selectedTargetPointer") or "not_captured"),
        "payload_pc": require_text(post, "currentActionPayloadPointer"),
        "payload_kind": "fixture_steered_c29051_normalization_callback",
        "per_target_loop_index": compact_json(loop_index),
    }
    missing = set(job.get("capture_fields", [])) - set(fields)
    if missing:
        raise ValueError(f"missing capture fields: {sorted(missing)}")
    return fields


def row_bytes(row_hex: str) -> bytes:
    data = parse_hex_bytes(row_hex)
    if not data:
        raise ValueError("empty row hex")
    return data


def record_byte_word(data: bytes, offset: int) -> str:
    return compact_json(
        {
            "offset": f"+0x{offset:02X}",
            "byte": hex_byte(u8(data, offset)),
            "word": hex_word(u16le(data, offset)),
        }
    )


def build_c1_c2_target_action_fields(
    job: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    rom: Path,
    trace: Path,
    classification: str,
    evidence: str | None,
) -> dict[str, Any]:
    runner_start = first_row(rows, event_type="runner_start")
    state_load = first_row(rows, event_type="before_state_load")
    c1_entry = first_row(rows, event_type="breakpoint_hit", pc="C1:ADB4")
    natural_callsite = next(
        (
            row
            for row in rows
            if row.get("type") == "breakpoint_hit"
            and row.get("routeGroup") == "snapshot_export"
            and row.get("pc") != "C2:B930"
        ),
        None,
    )
    hit = first_row(rows, event_type="breakpoint_hit", pc="C2:B930") or natural_callsite
    route_entry = c1_entry or natural_callsite
    if route_entry is None:
        raise ValueError("trace does not contain C1:ADB4 or a snapshot_export C1 callsite breakpoint hit")
    if hit is None:
        raise ValueError("trace does not contain a C2:B930 or snapshot_export callsite breakpoint hit")
    post = post_call_snapshot(rows, "C2:B930")
    if post is None and natural_callsite is not None:
        post = post_call_snapshot(rows, require_text(natural_callsite, "pc"))
    if post is None:
        raise ValueError("trace does not contain a C2:B930/snapshot_export post-call snapshot")
    before_row = require_text(hit, "xDestinationHex")
    after_row = require_text(post, "xDestinationAfterHex")
    after_data = row_bytes(after_row)
    hit_index = row_index(rows, hit)
    candidate_watch = watch_snapshot(rows, pc="C2:B930", watch_id="candidate_rows", start_index=hit_index)
    candidate_data = row_bytes(str((candidate_watch or {}).get("valueHex") or after_row))
    if natural_callsite is not None:
        generated_evidence = (
            f"Trace observed natural C1 snapshot-export callsite {natural_callsite.get('pc')} "
            "with pre-call A/X/Y, source-slot, destination, and post-return snapshot fields. "
            "This can support route proof after review; source promotion still requires local ASM agreement."
        )
    else:
        generated_evidence = (
            "Forced-entry fixture ROM rewrites C1:ADB4 to call C2:B930 with A=1 and X/Y=$9FFA. "
            "The trace proves C2:B930 exports source fields into the $9FFA snapshot row and "
            "captures the post-return destination row. It is mechanics evidence only; the vanilla "
            "C1 target resolver route still needs a natural pre-export capture."
        )
    destination = {
        "x_base": post.get("xDestinationBase"),
        "x_domain": post.get("xDestinationDomain"),
        "y_base": post.get("yDestinationBase"),
        "y_domain": post.get("yDestinationDomain"),
        "return_address": post.get("returnAddress"),
    }
    before_after = {
        "before": before_row,
        "after": after_row,
        "source_slot_base": post.get("sourceSlotBase") or hit.get("b930SourceSlotBase"),
        "source_slot_hex": post.get("sourceSlotHex") or hit.get("b930SourceSlotHex"),
    }
    fields = {
        "trace_id": f"{trace.as_posix()} sha256:{sha256(trace)}",
        "scenario_name": require_text(runner_start or {}, "scenarioName"),
        "rom_sha1": sha1(rom),
        "save_state_id": save_state_id(state_load),
        "frame_or_instruction_counter": f"frame:{hit.get('frame')} return_frame:{post.get('frame')} cycle:{hit.get('cpuCycleCount')}",
        "pc": "C2:B930" if hit.get("pc") == "C2:B930" else f"{hit.get('pc')}->C2:B930",
        "routine_label": ROUTINE_LABELS["C2:B930"]
        if hit.get("pc") == "C2:B930"
        else "C1SnapshotExportCallsiteToC2B930",
        "registers.a": require_text(hit, "cpuA"),
        "registers.x": require_text(hit, "cpuX"),
        "registers.y": require_text(hit, "cpuY"),
        "registers.db": require_text(hit, "cpuDB"),
        "registers.dp": require_text(hit, "cpuDP"),
        "direct_page_snapshot": require_text(hit, "directPageHex"),
        "wram_before": before_row,
        "wram_after": after_row,
        "ef_text_pointer": hit.get("callerDpPrimaryTextPointer", "not_applicable_to_forced_b930_fixture"),
        "c1_text_call": "forced_c1_adb4_entry_no_text_call"
        if natural_callsite is None
        else f"snapshot_export_callsite:{natural_callsite.get('pc')}",
        "classification": classification,
        "classification_evidence": evidence or generated_evidence,
        "input_action_id": "forced_c1_adb4_slot_1_snapshot_export"
        if natural_callsite is None
        else f"natural_snapshot_export_callsite:{natural_callsite.get('pc')}",
        "acting_slot": require_text(hit, "cpuA"),
        "c1_dp.$00_target_byte": require_text(route_entry, "c1Dp0000SelectedTargetByte"),
        "c1_dp.$01_battle_text_substitution_byte": require_text(route_entry, "c1Dp0001TextSubstitutionByte"),
        "c1_dp.$14_$16_action_row_pointer": require_text(route_entry, "c1Dp0014Pointer"),
        "c1_dp.$18_$1a_second_pointer_table_base": require_text(route_entry, "c1Dp0018Pointer"),
        "c1_dp.$1e_$20_selected_action_pointer": require_text(route_entry, "c1Dp001ePointer"),
        "c1_dp.$22_party_loop_index": require_text(route_entry, "c1Dp0022Word"),
        "c1_dp.$2a_acting_slot": require_text(route_entry, "c1Dp002aActingSlotWord"),
        "c1_dp.$2c_item_slot": require_text(route_entry, "c1Dp002cItemSlotWord"),
        "b930.source_slot_row_99ce": compact_json(
            {
                "base": post.get("sourceSlotBase") or hit.get("b930SourceSlotBase"),
                "row_hex": post.get("sourceSlotHex") or hit.get("b930SourceSlotHex"),
            }
        ),
        "b930.destination_base_x_or_y": compact_json(destination),
        "b930.destination_before_after_4e": compact_json(before_after),
        "selection_record_base": str(post.get("xDestinationBase") or "0x009FFA"),
        "selection_record.+0": record_byte_word(after_data, 0x00),
        "selection_record.+1": record_byte_word(after_data, 0x01),
        "selection_record.+2": record_byte_word(after_data, 0x02),
        "selection_record.+4": record_byte_word(after_data, 0x04),
        "selection_record.+5": record_byte_word(after_data, 0x05),
        "candidate_record.+0x07": record_byte_word(candidate_data, 0x07),
        "candidate_record.+0x08": record_byte_word(candidate_data, 0x08),
        "candidate_record.+0x0A": record_byte_word(candidate_data, 0x0A),
        "observed_target_byte": compact_json(
            {
                "c1_entry_dp00": route_entry.get("c1Dp0000SelectedTargetByte"),
                "exported_row_plus_0": hex_byte(u8(after_data, 0x00)),
                "route_context": "natural_snapshot_export_callsite"
                if natural_callsite is not None
                else "forced_c1_adb4_entry",
                "forced_fixture_limit": None
                if natural_callsite is not None
                else "C1:ADB4 was patched to call C2:B930 directly.",
            }
        ),
    }
    missing = set(job.get("capture_fields", [])) - set(fields)
    if missing:
        raise ValueError(f"missing capture fields: {sorted(missing)}")
    return fields


def build_c2_724a_fields(
    job: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    rom: Path,
    trace: Path,
    classification: str,
    evidence: str | None,
) -> dict[str, Any]:
    runner_start = first_row(rows, event_type="runner_start")
    state_load = first_row(rows, event_type="before_state_load")
    writer = first_row(rows, event_type="breakpoint_hit", pc="C2:724A")
    numb = first_row(rows, event_type="breakpoint_hit", pc="C2:9917")
    flash_gate = first_row(rows, event_type="breakpoint_hit", pc="C2:98A1")
    has_wram_patch = any(row.get("type") == "wram_patch" for row in rows)
    fixture_steered = "fixture-rom-tests" in trace.as_posix() or has_wram_patch
    writer_index = row_index(rows, writer) if writer is not None else -1
    post = post_call_snapshot(rows, "C2:724A")
    text_call = first_after(rows, writer_index, event_type="breakpoint_hit", pc="C1:DC1C") if writer_index >= 0 else None
    if writer is None:
        raise ValueError("trace does not contain a C2:724A breakpoint hit")
    if numb is not None:
        if fixture_steered:
            generated_evidence = (
                "Fixture-steered Bash-row ROM routes action row 4 to Flash Beta and patches "
                "the Flash gate/random result to the numb branch. The trace observes "
                "C2:9917 -> C2:724A with X=0 and Y=3, proving the paired numb writer "
                "mechanics. The post-return snapshot captures the writer return value and row "
                "mutation; natural C2:98A1 gate behavior remains follow-up work."
            )
            chance_gate_pc = "forced fixture bypasses natural C2:98A1 gate at C2:99B8"
            resistance_gate_pc = "not_observed_in_forced_numb_fixture"
        else:
            generated_evidence = (
                "Vanilla save-state trace observes the Flash body-numb branch "
                "C2:9917 -> C2:724A with X=0 and Y=3. The post-return snapshot "
                "captures the writer return value and selected-row +0x1D mutation."
            )
            chance_gate_pc = "C2:98A1 observed before C2:9917" if flash_gate is not None else "not_captured_by_this_narrow_writer_runner"
            resistance_gate_pc = "not_separate_for_flash_body_numb_branch_in_this_capture"
        ef_text_pointer_fallback = "source-backed success EF:6AE0 / failure EF:766E; text call not captured in this short runner window"
        success_text_pointer = "EF:6AE0"
        failure_text_pointer = "EF:766E"
    else:
        generated_evidence = (
            "Vanilla save-state trace reaches C2:724A directly, without the C2:9917 "
            "Flash numb helper. The post-return snapshot captures the writer return "
            "value and selected-row status-slot mutation for the direct caller."
        )
        chance_gate_pc = "not_applicable_to_direct_c2_724a_caller"
        resistance_gate_pc = "not_observed_for_direct_c2_724a_caller"
        ef_text_pointer_fallback = "not_captured_for_direct_c2_724a_caller"
        success_text_pointer = "not_captured_for_direct_c2_724a_caller"
        failure_text_pointer = "not_captured_for_direct_c2_724a_caller"
    source_target = {
        "selected_target_pointer_at_9917": (numb or {}).get("selectedTargetPointer"),
        "selected_target_pointer_at_724a": writer.get("selectedTargetPointer"),
        "post_return_selected_target_pointer": (post or {}).get("selectedTargetPointer"),
        "post_return_slot_address": (post or {}).get("statusWriterSlotAddress"),
        "post_return_slot_before": (post or {}).get("statusWriterSlotBefore"),
        "post_return_slot_after": (post or {}).get("statusWriterSlotAfter"),
        "current_target_mask": writer.get("currentTargetMaskHex"),
        "watch_snapshot": (
            watch_snapshot(rows, pc="C2:724A", watch_id="selected_battler_afflictions", start_index=row_index(rows, writer))
            or {}
        ).get("valueHex", "not_captured"),
    }
    fields = {
        "trace_id": f"{trace.as_posix()} sha256:{sha256(trace)}",
        "scenario_name": require_text(runner_start or {}, "scenarioName"),
        "rom_sha1": sha1(rom),
        "save_state_id": save_state_id(state_load),
        "frame_or_instruction_counter": f"frame:{writer.get('frame')} cycle:{writer.get('cpuCycleCount')}",
        "pc": "C2:724A",
        "routine_label": ROUTINE_LABELS["C2:724A"],
        "registers.a": require_text(writer, "cpuA"),
        "registers.x": require_text(writer, "cpuX"),
        "registers.y": require_text(writer, "cpuY"),
        "registers.db": require_text(writer, "cpuDB"),
        "registers.dp": require_text(writer, "cpuDP"),
        "direct_page_snapshot": require_text(writer, "directPageHex"),
        "wram_before": require_text(post or writer, "statusWriterRowBeforeHex")
        if post is not None
        else require_text(writer, "selectedTargetRowHex"),
        "wram_after": require_text(post or writer, "statusWriterRowAfterHex")
        if post is not None
        else require_text(writer, "selectedTargetRowHex"),
        "ef_text_pointer": (text_call or {}).get("callerDpPrimaryTextPointer")
        or ef_text_pointer_fallback,
        "c1_text_call": compact_json(row_brief(text_call)) if text_call is not None else "not_captured_after_c2_724a_return",
        "classification": classification,
        "classification_evidence": evidence or generated_evidence,
        "caller_pc": compact_json(
            {
                "status_helper": row_brief(numb) if numb is not None else "not_observed_direct_c2_724a_caller",
                "writer_stack_return": writer.get("stackReturnRtlAdjusted"),
                "writer_post_return": row_brief(post) if post is not None else "not_captured",
                "dispatch_target": writer.get("dispatchTargetPointer"),
            }
        ),
        "selected_row_source": compact_json(source_target),
        "x_subgroup_slot": require_text(writer, "cpuX"),
        "y_status_value": require_text(writer, "cpuY"),
        "target_field_for_direct_writer": (post or {}).get("statusWriterSlotOffset")
        or "selected battler row +0x1D primary affliction byte",
        "chance_gate_pc": chance_gate_pc,
        "resistance_gate_pc": resistance_gate_pc,
        "writer_return_value": (post or {}).get("postCpuA") or "not_captured_by_current_runner",
        "success_text_pointer": success_text_pointer,
        "failure_text_pointer": failure_text_pointer,
    }
    missing = set(job.get("capture_fields", [])) - set(fields)
    if missing:
        raise ValueError(f"missing capture fields: {sorted(missing)}")
    return fields


def hp_triplet(decoded: dict[str, Any] | str) -> dict[str, Any] | str:
    if not isinstance(decoded, dict):
        return decoded
    return {
        "pointer": decoded.get("pointer"),
        "hp_live_word_plus_0x11": decoded.get("hp_live_word_plus_0x11"),
        "hp_target_word_plus_0x13": decoded.get("hp_target_word_plus_0x13"),
        "hp_max_word_plus_0x15": decoded.get("hp_max_word_plus_0x15"),
        "active_gate_byte_plus_0x0c": decoded.get("active_gate_byte_plus_0x0c"),
        "affliction_primary_byte_plus_0x1d": decoded.get("affliction_primary_byte_plus_0x1d"),
        "timed_substate_byte_plus_0x23": decoded.get("timed_substate_byte_plus_0x23"),
    }


def first_breakpoint(rows: list[dict[str, Any]], pc: str, *, start_index: int = -1) -> dict[str, Any] | None:
    return first_after(rows, start_index, event_type="breakpoint_hit", pc=pc)


def save_state_id(row: dict[str, Any] | None) -> str:
    if row is None:
        return "not_captured"
    path_text = str(row.get("statePath", ""))
    if not path_text:
        return "not_captured"
    path = Path(path_text)
    if path.is_file():
        return f"{path.name} sha256:{sha256(path)}"
    return path.name or path_text


def build_hp_roller_collapse_fields(
    job: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    rom: Path,
    trace: Path,
    classification: str,
    evidence: str | None,
) -> dict[str, Any]:
    runner_start = first_row(rows, event_type="runner_start")
    state_load = first_row(rows, event_type="before_state_load")
    damage = first_breakpoint(rows, "C2:8125")
    if damage is None:
        raise ValueError("trace does not contain a C2:8125 damage breakpoint hit")
    damage_index = row_index(rows, damage)
    collapse = first_breakpoint(rows, "C2:7550", start_index=damage_index)
    if collapse is None:
        raise ValueError("trace does not contain a C2:7550 collapse-start breakpoint hit")
    collapse_index = row_index(rows, collapse)
    death_text = first_breakpoint(rows, "C2:7680", start_index=collapse_index)
    collapse_tail = first_breakpoint(rows, "C2:77CA", start_index=collapse_index)
    promote = first_breakpoint(rows, "C2:BB18", start_index=damage_index)
    cleanup = first_breakpoint(rows, "C2:BC5C", start_index=damage_index)
    second_damage = first_breakpoint(rows, "C2:8125", start_index=damage_index)

    damage_row = decoded_selected_row(damage)
    collapse_row = decoded_selected_row(collapse)
    collapse_tail_row = decoded_selected_row(collapse_tail)
    promote_row = decoded_selected_row(promote)
    second_damage_row = decoded_selected_row(second_damage)
    c1_text_events = build_c1_text_events(rows, start_index=damage_index)
    first_text_event = c1_text_events[0] if c1_text_events else None
    observed = sorted({str(row.get("pc")) for row in rows if row.get("type") == "breakpoint_hit" and row.get("pc")})
    order = [
        row_brief(row)
        for row in rows
        if row.get("type") == "breakpoint_hit"
        and row.get("pc") in {"C2:8125", "C2:7550", "C2:7680", "C2:77CA", "C2:BB18", "C2:BC5C", "C1:DC1C", "C1:DC66"}
    ]
    selected_row_before_after = {
        "damage_entry": damage_row,
        "collapse_start": collapse_row,
        "collapse_tail": collapse_tail_row,
        "first_promote_candidate": promote_row,
        "second_damage_entry": second_damage_row,
        "optional_death_text_path": decoded_selected_row(death_text),
        "optional_cleanup_path": decoded_selected_row(cleanup),
    }
    collapse_hp_delta = hp_delta(damage_row, collapse_row)
    collapse_text_pointer = {
        "c2_7680_death_text_path": row_brief(death_text),
        "c2_77ca_tail_path": row_brief(collapse_tail),
        "first_c1_text_after_damage": first_text_event or "not_observed",
        "note": "This fixture reaches C2:77CA and C1 battle-text entries; C2:7680 was not observed in the neutral state-7 run.",
    }
    generated_evidence = (
        "Natural Mesen trace from the user-provided state 7 observes C2:8125, then C2:7550 and C2:77CA "
        "with C1 battle-text joins and repeated C2:BB18 samples. The observed collapse-boundary order and "
        "hard/collapsed row-state installation are refined contracts; optional C2:7680 descriptor text and "
        "C2:BC5C inactive cleanup remain follow-up paths."
    )
    proof_grade_subcontracts = {
        "hp_to_zero_collapse_boundary": {
            "status": "refined_contract",
            "evidence": "Selected row +0x11/+0x13 are nonzero at C2:8125 and zero by C2:7550/C2:77CA in the natural state-7 trace.",
            "hp_delta": collapse_hp_delta,
        },
        "collapse_start_to_tail_order": {
            "status": "refined_contract",
            "evidence": "Trace order is C2:8125 -> C2:7550 -> C2:77CA -> C1:DC1C, followed by repeated C2:BB18 promotion-controller samples.",
        },
        "hard_collapsed_row_state_install": {
            "status": "refined_contract",
            "evidence": "First C2:BB18 sample observes selected row affliction primary +0x1D == $01 after the collapse-start path.",
            "first_promote_candidate": promote_row,
        },
        "descriptor_text_and_inactive_cleanup": {
            "status": "needs_followup",
            "evidence": "This natural run did not observe C2:7680 or C2:BC5C, so those optional presentation/cleanup paths stay out of the proof-grade claim.",
        },
    }
    fields = {
        "trace_id": f"{trace.as_posix()} sha256:{sha256(trace)}",
        "scenario_name": require_text(runner_start or {}, "scenarioName"),
        "rom_sha1": sha1(rom),
        "save_state_id": save_state_id(state_load),
        "frame_or_instruction_counter": f"frame:{damage.get('frame')} collapse_frame:{collapse.get('frame')} cycle:{damage.get('cpuCycleCount')}",
        "pc": "C2:8125",
        "routine_label": ROUTINE_LABELS["C2:8125"],
        "registers.a": require_text(damage, "cpuA"),
        "registers.x": require_text(damage, "cpuX"),
        "registers.y": require_text(damage, "cpuY"),
        "registers.db": require_text(damage, "cpuDB"),
        "registers.dp": require_text(damage, "cpuDP"),
        "direct_page_snapshot": require_text(damage, "directPageHex"),
        "wram_before": require_text(damage, "selectedTargetRowHex"),
        "wram_after": require_text(collapse, "selectedTargetRowHex"),
        "ef_text_pointer": (first_text_event or {}).get("primary_text_pointer_0e_10", "not_captured_by_current_mesen_runner"),
        "c1_text_call": compact_json(c1_text_events) if c1_text_events else "not_captured_by_current_mesen_runner",
        "classification": classification,
        "classification_evidence": evidence or generated_evidence,
        "damage_call_pc": row_brief(damage),
        "hp_roller_before": hp_triplet(damage_row),
        "hp_roller_after": {
            "at_collapse_start": hp_triplet(collapse_row),
            "at_collapse_tail": hp_triplet(collapse_tail_row),
            "at_first_promote_candidate": hp_triplet(promote_row),
            "at_second_damage_entry": hp_triplet(second_damage_row),
        },
        "candidate_promote_pc": row_brief(promote),
        "inactive_cleanup_pc": row_brief(cleanup),
        "collapse_start_pc": row_brief(collapse),
        "collapse_text_pointer": collapse_text_pointer,
        "selected_row_before_after": selected_row_before_after,
        "hp_collapse_delta": collapse_hp_delta,
        "c1_text_join_samples": c1_text_events,
        "proof_grade_subcontracts": proof_grade_subcontracts,
        "settlement_order": {
            "observed_breakpoint_order": order,
            "observed_addresses": observed,
            "ordering_summary": "State 7 natural trace observes C2:8125 at frame 41, C2:7550/C2:77CA/C1:DC1C at frame 117, then repeated C2:BB18 promotion-controller samples.",
            "proof_limit": "This promotes the observed HP-to-zero/collapse-boundary order, not every HP-roller visual settlement or optional cleanup/death-text path.",
        },
    }
    missing = set(job.get("capture_fields", [])) - set(fields)
    if missing:
        raise ValueError(f"missing capture fields: {sorted(missing)}")
    return fields


def build_c2_8125_fields(job: dict[str, Any], rows: list[dict[str, Any]], *, rom: Path, trace: Path, classification: str, evidence: str | None) -> dict[str, Any]:
    runner_start = first_row(rows, event_type="runner_start")
    state_load = first_row(rows, event_type="before_state_load")
    hit = first_row(rows, event_type="breakpoint_hit", pc="C2:8125")
    if hit is None:
        raise ValueError("trace does not contain a C2:8125 breakpoint hit")
    hit_index = row_index(rows, hit)
    downstream = first_after(rows, hit_index, event_type="breakpoint_hit", pc="C2:7EAF")
    collapse = first_after(rows, hit_index, event_type="breakpoint_hit", pc="C2:7550")
    before_watch = first_after(rows, hit_index, event_type="watch_snapshot", pc="C2:8125")
    after_watch = first_after(rows, hit_index, event_type="watch_snapshot", pc="C2:7EAF")
    observed = sorted({str(row.get("pc")) for row in rows if row.get("type") == "breakpoint_hit" and row.get("pc")})
    target_row = str(hit.get("selectedTargetRowHex") or (before_watch or {}).get("valueHex") or "")
    downstream_row = str((downstream or {}).get("selectedTargetRowHex") or (after_watch or {}).get("valueHex") or target_row)
    if not target_row:
        raise ValueError("trace does not include selected target row data")
    target_pointer = require_text(hit, "selectedTargetPointer")
    decoded_target_row = decode_battle_row(target_row, pointer=target_pointer)
    decoded_downstream_row = decode_battle_row(downstream_row, pointer=target_pointer)
    samples = build_c2_8125_samples(rows)
    c1_text_events = build_c1_text_events(rows, start_index=hit_index)
    text_payload_slot_samples = build_text_payload_slot_samples(rows, start_index=hit_index)
    first_text_event = c1_text_events[0] if c1_text_events else None
    collapse_state = {
        "source_contract": (
            "C2:8125 first requires selected row +0x0C == 0x01 and +0x1D != 0x01; "
            "after CALC_DAMAGE it calls C2:7550 only if row +0x11 is zero."
        ),
        "first_sample": decoded_target_row["c28125_source_gate_summary"],
        "observed_sample_count": len(samples),
        "collapse_start_observed": collapse is not None,
        "proof_limit": "current trace promotes the live damage ABI and amount-text join; collapse-finalization is proven by the separate hp_roller_collapse_boundary result.",
    }
    generated_evidence = (
        "Natural Mesen trace hit C2:8125 with CPU register capture, the pointed-to $A972 target row, "
        "post-call HP row deltas, and C1 amount-text joins. The damage ABI, selected-row HP mutation, "
        "and amount-text payload path are refined contracts; broader caller-family coverage and collapse "
        "finalization stay in separate proof lanes."
    )
    first_changed_samples = [
        sample
        for sample in samples
        if sample.get("row_at_first_selected_row_hp_change") != "not_observed"
    ]
    proof_grade_subcontracts = {
        "damage_entry_abi": {
            "status": "refined_contract",
            "evidence": "C2:8125 entry captures A as staged amount, X as damage/resistance selector, and $A972 as the selected battler row pointer.",
            "first_entry_registers": {"a": require_text(hit, "cpuA"), "x": require_text(hit, "cpuX"), "y": require_text(hit, "cpuY")},
        },
        "selected_row_hp_mutation": {
            "status": "refined_contract",
            "evidence": "Natural samples show selected row +0x11/+0x13 HP words changing after C2:8125 and before the C1 amount text/display joins.",
            "changed_sample_count": len(first_changed_samples),
        },
        "damage_amount_text_join": {
            "status": "refined_contract",
            "evidence": "C1:DC66 commits caller $12/$14 through C1:AD0A, then C1:7EED/C1:AD26/C1:0DF6 consume the amount payload for battle text.",
            "first_text_event": first_text_event or "not_observed",
        },
        "caller_family_breadth": {
            "status": "needs_followup",
            "evidence": "The trace proves the ABI and row/text side effects for natural observed calls; it does not exhaustively classify every action-family caller.",
        },
    }
    fields = {
        "trace_id": f"{trace.as_posix()} sha256:{sha256(trace)}",
        "scenario_name": require_text(runner_start or {}, "scenarioName"),
        "rom_sha1": sha1(rom),
        "save_state_id": save_state_id(state_load),
        "frame_or_instruction_counter": f"frame:{hit.get('frame')} cycle:{hit.get('cpuCycleCount')}",
        "pc": "C2:8125",
        "routine_label": ROUTINE_LABELS["C2:8125"],
        "registers.a": require_text(hit, "cpuA"),
        "registers.x": require_text(hit, "cpuX"),
        "registers.y": require_text(hit, "cpuY"),
        "registers.db": require_text(hit, "cpuDB"),
        "registers.dp": require_text(hit, "cpuDP"),
        "direct_page_snapshot": require_text(hit, "directPageHex"),
        "wram_before": target_row,
        "wram_after": downstream_row,
        "ef_text_pointer": (first_text_event or {}).get("primary_text_pointer_0e_10", "not_captured_by_current_mesen_runner"),
        "c1_text_call": compact_json(c1_text_events) if c1_text_events else "not_captured_by_current_mesen_runner",
        "classification": classification,
        "classification_evidence": evidence or generated_evidence,
        "amount_input": require_text(hit, "cpuA"),
        "damage_selector_x": require_text(hit, "cpuX"),
        "selected_target_row": f"{target_pointer} {target_row}",
        "selected_target_row_decoded": decoded_target_row,
        "selected_target_row_at_downstream_decoded": decoded_downstream_row,
        "damage_entry_samples": samples,
        "damage_hp_delta_samples": first_changed_samples,
        "c1_text_join_samples": c1_text_events,
        "text_payload_slot_samples": text_payload_slot_samples,
        "proof_grade_subcontracts": proof_grade_subcontracts,
        "caller_family": "damage ABI reached from numbered multi-enemy battle fixture; exact caller subfamily still needs call-stack/source join",
        "post_call_hp_roller_state": compact_json({"first_downstream_row": decoded_downstream_row, "sample_count": len(samples)}),
        "collapse_candidate_state": compact_json(collapse_state),
        "result_text_pointer": compact_json({"first_text_event": first_text_event, "all_text_event_count": len(c1_text_events)}),
        "observed_addresses": observed,
        "downstream_routine_label": ROUTINE_LABELS.get(str((downstream or {}).get("pc", "")), "not_observed"),
    }
    missing = set(job.get("capture_fields", [])) - set(fields)
    if missing:
        raise ValueError(f"missing capture fields: {sorted(missing)}")
    return fields


def pp_word(row_hex: str, offset: int) -> str:
    data = parse_hex_bytes(row_hex)
    return hex_word(u16le(data, offset)) or "not_captured"


def pp_delta(before_row: str, after_row: str, *, offset: int) -> dict[str, Any]:
    before = pp_word(before_row, offset) if before_row else "not_captured"
    after = pp_word(after_row, offset) if after_row else "not_captured"
    return {
        "before": before,
        "after": after,
        "delta": word_delta(before, after),
    }


def row_pointer_text(row: dict[str, Any], key: str) -> str:
    return str(row.get(key) or "").lower().replace("0x00", "0x")


def build_resource_amount_fields(
    job: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    rom: Path,
    trace: Path,
    classification: str,
    evidence: str | None,
) -> dict[str, Any]:
    runner_start = first_row(rows, event_type="runner_start")
    state_load = first_row(rows, event_type="before_state_load")
    pp_drain = first_row(rows, event_type="breakpoint_hit", pc="C2:9F5E")
    pp_loss = first_row(rows, event_type="breakpoint_hit", pc="C2:8E42")
    reducer = first_row(rows, event_type="breakpoint_hit", pc="C2:721D")
    hit = pp_drain or pp_loss or reducer
    if hit is None:
        raise ValueError("trace does not contain a resource amount breakpoint hit")
    observed = sorted({str(row.get("pc")) for row in rows if row.get("type") == "breakpoint_hit" and row.get("pc")})
    before_row = str(hit.get("selectedTargetRowHex") or "")
    reducer_post = post_call_snapshot(rows, "C2:721D")
    pp_set_posts = [
        row
        for row in rows
        if row.get("type") == "post_call_snapshot"
        and row.get("callPc") == "C2:7191"
        and int(row.get("frame") or 0) >= int(hit.get("frame") or 0)
    ]
    reducer_row_before = str((reducer_post or {}).get("reducerRowBeforeHex") or (reducer or {}).get("selectedTargetRowHex") or before_row)
    reducer_row_after = str((reducer_post or {}).get("reducerRowAfterHex") or (reducer or {}).get("selectedTargetRowHex") or before_row)
    after_row = reducer_row_after
    active_before = str(hit.get("activeAttackerRowHex") or "")
    active_after = str((reducer_post or reducer or hit).get("activeAttackerRowHex") or active_before)
    hit_target_pointer = row_pointer_text(hit, "selectedTargetPointer")
    hit_active_pointer = row_pointer_text(hit, "activeAttackerPointer")
    pp_setter_deltas: list[dict[str, Any]] = []
    for post in pp_set_posts:
        pointer = row_pointer_text(post, "ppSetterRowPointer")
        before_hex = str(post.get("ppSetterRowBeforeHex") or "")
        after_hex = str(post.get("ppSetterRowAfterHex") or "")
        role = "other_pp_setter"
        if pointer == hit_target_pointer:
            role = "selected_target_pp_setter"
        elif pointer == hit_active_pointer:
            role = "active_attacker_pp_setter"
            active_after = after_hex or active_after
        pp_setter_deltas.append(
            {
                "frame": post.get("frame"),
                "row_pointer": post.get("ppSetterRowPointer"),
                "row_role": role,
                "target_value_x": post.get("ppSetterTargetValue"),
                "pp_delta": pp_delta(before_hex, after_hex, offset=0x19),
            }
        )
    amount_source = reducer or hit
    wram_patches = [row for row in rows if row.get("type") == "wram_patch"]
    if wram_patches and "C2:9F5E" in observed and "C2:721D" in observed:
        generated_evidence = (
            "Controlled WRAM-patched PSI Magnet trace seeds the selected row with nonzero PP, "
            "observes amount payload setup, reaches C2:721D, and captures the post-reducer PP delta. "
            "This is fixture proof of reducer mechanics, not natural vanilla amount evidence."
        )
    elif wram_patches and "C2:8E42" in observed and "C2:721D" in observed:
        generated_evidence = (
            "Controlled WRAM-patched PP-reduction trace seeds the selected row with nonzero PP/max PP, "
            "observes the loss-only C2:8E42 entry reaching C2:721D, and captures the post-reducer PP delta. "
            "This is fixture proof of reducer mechanics, not natural vanilla amount evidence."
        )
    else:
        generated_evidence = (
            "Mesen fixture trace opened the resource-amount lane. The "
            "`bash-row-psi-magnet-force-reducer` ROM steers Bash to C2:9F5E and "
            "forces the zero-PP guard past the early exit, reaching C2:721D. This "
            "proves reducer-path reachability only; a natural nonzero amount and "
            "loss-only comparison remain follow-up work."
        )
    if "C2:9F5E" in observed and "C2:721D" in observed:
        transfer_class = "controlled_transfer_style_reducer_amount_observed_natural_pending" if wram_patches else "forced_transfer_style_reducer_route_observed_amount_pending"
    elif "C2:8E42" in observed:
        transfer_class = "controlled_loss_only_reducer_amount_observed_natural_pending" if "C2:721D" in observed and wram_patches else "loss_only_entry_route_observed_amount_pending"
    else:
        transfer_class = "resource_route_observed_amount_pending"
    target_pp_delta = pp_delta(reducer_row_before, reducer_row_after, offset=0x19)
    source_pp_delta = pp_delta(active_before, active_after, offset=0x19)
    fields = {
        "trace_id": f"{trace.as_posix()} sha256:{sha256(trace)}",
        "scenario_name": require_text(runner_start or {}, "scenarioName"),
        "rom_sha1": sha1(rom),
        "save_state_id": save_state_id(state_load),
        "frame_or_instruction_counter": f"frame:{hit.get('frame')} cycle:{hit.get('cpuCycleCount')}",
        "pc": require_text(hit, "pc"),
        "routine_label": ROUTINE_LABELS.get(require_text(hit, "pc"), "unknown_resource_amount_entry"),
        "registers.a": require_text(hit, "cpuA"),
        "registers.x": require_text(hit, "cpuX"),
        "registers.y": require_text(hit, "cpuY"),
        "registers.db": require_text(hit, "cpuDB"),
        "registers.dp": require_text(hit, "cpuDP"),
        "direct_page_snapshot": require_text(hit, "directPageHex"),
        "wram_before": before_row,
        "wram_after": after_row,
        "ef_text_pointer": str((reducer or hit).get("callerDpPrimaryTextPointer") or "not_captured_by_current_mesen_runner"),
        "c1_text_call": "not_captured_by_current_mesen_runner",
        "classification": classification,
        "classification_evidence": evidence or generated_evidence,
        "source_row_pp_before": source_pp_delta["before"],
        "source_row_pp_after": source_pp_delta["after"],
        "target_row_pp_before": target_pp_delta["before"],
        "target_row_pp_after": target_pp_delta["after"],
        "amount_roll": str(amount_source.get("cpuX") or "not_captured") if reducer else "not_captured_no_reducer",
        "cap_amount": (
            "controlled WRAM-patched nonzero PP amount observed; natural vanilla PP-bearing target evidence remains pending"
            if wram_patches and target_pp_delta["delta"] not in {None, 0}
            else "forced fixture target row has zero current PP, so this trace reaches the reducer without proving a nonzero cap amount"
        ),
        "text_payload_amount": str((reducer or hit).get("textPayloadSlotsHex") or "not_captured_by_current_mesen_runner"),
        "transfer_or_loss_only_classification": transfer_class,
        "wram_patch_events": wram_patches,
        "reducer_post_call_snapshot": reducer_post or "not_observed",
        "pp_setter_post_call_snapshots": pp_set_posts,
        "pp_setter_deltas": pp_setter_deltas,
        "reducer_row_pp_delta": target_pp_delta,
        "active_row_pp_delta": source_pp_delta,
        "observed_addresses": observed,
    }
    missing = set(job.get("capture_fields", [])) - set(fields)
    if missing:
        raise ValueError(f"missing capture fields: {sorted(missing)}")
    return fields


def main() -> int:
    args = parse_args()
    if args.oracle_id not in SUPPORTED_ORACLES:
        raise ValueError(f"{args.oracle_id} is not supported by this Mesen capture assembler yet")
    packet = load_json(Path(args.packet))
    job = find_job(packet, args.oracle_id)
    trace = repo_path(args.trace or str(job["output_paths"]["raw_trace_path"]))
    rom = rom_tools.find_rom(args.rom)
    rows = read_trace(trace)
    if args.oracle_id == "c1_c2_target_action_staging":
        fields = build_c1_c2_target_action_fields(
            job,
            rows,
            rom=rom,
            trace=trace,
            classification=args.classification,
            evidence=args.classification_evidence,
        )
    elif args.oracle_id == "c2_724a_affliction_writer_matrix":
        fields = build_c2_724a_fields(
            job,
            rows,
            rom=rom,
            trace=trace,
            classification=args.classification,
            evidence=args.classification_evidence,
        )
    elif args.oracle_id == "c2_8125_damage_abi_boundary":
        fields = build_c2_8125_fields(
            job,
            rows,
            rom=rom,
            trace=trace,
            classification=args.classification,
            evidence=args.classification_evidence,
        )
    elif args.oracle_id == "c2_40a4_current_action_payload":
        fields = build_c2_40a4_fields(
            job,
            rows,
            rom=rom,
            trace=trace,
            classification=args.classification,
            evidence=args.classification_evidence,
        )
    elif args.oracle_id == "hp_roller_collapse_boundary":
        fields = build_hp_roller_collapse_fields(
            job,
            rows,
            rom=rom,
            trace=trace,
            classification=args.classification,
            evidence=args.classification_evidence,
        )
    elif args.oracle_id == "resource_amount_pair_magnet_vs_pp_loss":
        fields = build_resource_amount_fields(
            job,
            rows,
            rom=rom,
            trace=trace,
            classification=args.classification,
            evidence=args.classification_evidence,
        )
    else:
        raise ValueError(f"{args.oracle_id} is not supported by this Mesen capture assembler yet")
    output = repo_path(args.output) if args.output else trace.parent / "captured-fields.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(fields, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote C2 Mesen capture fields {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
