#!/usr/bin/env python3
"""Summarize the controlled C2:B930 battle-selection snapshot export capture."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = (
    ROOT
    / "build"
    / "c2"
    / "battle-trace-oracles"
    / "c1_c2_target_action_staging"
    / "result.json"
)
DEFAULT_MANIFEST = ROOT / "manifests" / "c2-b930-controlled-snapshot-export.json"
DEFAULT_NOTE = ROOT / "notes" / "c2-b930-controlled-snapshot-export.md"


def repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def decode_embedded_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return {}
        if isinstance(decoded, dict):
            return decoded
    return {}


def hex_bytes_len(value: str | None) -> int:
    if not value:
        return 0
    return len([part for part in value.split() if part])


def load_result(path: Path) -> tuple[str, dict[str, Any] | None]:
    if not path.exists():
        return "missing_result", None
    result = load_json(path)
    required = {"oracle_id", "status", "contract_classification", "observed_addresses", "captured_fields"}
    missing = sorted(required - set(result))
    if missing:
        return f"result_missing_fields:{','.join(missing)}", result
    return "result_loaded", result


def build_manifest(input_path: Path = DEFAULT_INPUT) -> dict[str, Any]:
    status, result = load_result(input_path)
    manifest: dict[str, Any] = {
        "schema": "earthbound-decomp.c2-b930-controlled-snapshot-export.v1",
        "generated_by": "tools/build_c2_b930_controlled_snapshot_export.py",
        "input": repo_path(input_path),
        "status": status,
        "policy": {
            "forced_entry_fixture_only": True,
            "natural_c1_route_proven": False,
            "source_promotion_allowed": False,
            "behavior_change_allowed": False,
        },
    }
    if result is None:
        manifest["summary"] = {
            "controlled_snapshot_export_observed": False,
            "source_slot_copied_to_destination": False,
            "natural_c1_route_proven": False,
        }
        return manifest

    fields = result.get("captured_fields", {})
    source_row = decode_embedded_json(fields.get("b930.source_slot_row_99ce"))
    destination = decode_embedded_json(fields.get("b930.destination_base_x_or_y"))
    before_after = decode_embedded_json(fields.get("b930.destination_before_after_4e"))
    observed_target = decode_embedded_json(fields.get("observed_target_byte"))

    destination_before = before_after.get("before")
    destination_after = before_after.get("after")
    source_hex = source_row.get("row_hex") or before_after.get("source_slot_hex")
    rewritten = bool(
        source_hex
        and destination_before
        and destination_after
        and destination_before != destination_after
    )

    evidence = {
        "oracle_id": result.get("oracle_id"),
        "result_status": result.get("status"),
        "contract_classification": result.get("contract_classification"),
        "observed_addresses": result.get("observed_addresses", []),
        "promotion_allowed_by_result": result.get("promotion_allowed_by_result"),
        "behavior_change_allowed": result.get("behavior_change_allowed"),
        "trace_id": fields.get("trace_id"),
        "rom_sha1": fields.get("rom_sha1"),
        "save_state_id": fields.get("save_state_id"),
        "classification_evidence": fields.get("classification_evidence"),
    }
    snapshot = {
        "input_action_id": fields.get("input_action_id"),
        "routine_label": fields.get("routine_label"),
        "pc": fields.get("pc"),
        "return_address": destination.get("return_address"),
        "registers": {
            "a": fields.get("registers.a"),
            "x": fields.get("registers.x"),
            "y": fields.get("registers.y"),
            "db": fields.get("registers.db"),
            "dp": fields.get("registers.dp"),
        },
        "source_slot": {
            "base": source_row.get("base") or before_after.get("source_slot_base"),
            "byte_count": hex_bytes_len(source_hex),
            "row_hex": source_hex,
        },
        "destination_slot": {
            "base": fields.get("selection_record_base") or destination.get("x_base"),
            "x_base": destination.get("x_base"),
            "x_domain": destination.get("x_domain"),
            "y_base": destination.get("y_base"),
            "y_domain": destination.get("y_domain"),
            "before_byte_count": hex_bytes_len(destination_before),
            "after_byte_count": hex_bytes_len(destination_after),
            "before_hex": destination_before,
            "after_hex": destination_after,
        },
        "observed_target_byte": observed_target,
        "selection_record_plus_0": decode_embedded_json(fields.get("selection_record.+0")),
    }
    natural_gaps = [
        "Capture the unpatched C1 path from committed target/action selection into C2:B930.",
        "Observe C1:CE85 and C1:CFC6 in the same route context as the export.",
        "Confirm whether the natural destination base is $9FFA and which caller owns A/X/Y setup.",
        "Only then consider source comments beyond forced-entry wrapper mechanics.",
    ]

    manifest.update(
        {
            "summary": {
                "controlled_snapshot_export_observed": result.get("status") == "ok"
                and "C2:B930" in result.get("observed_addresses", []),
                "source_fields_exported_to_destination": rewritten,
                "source_slot_base": snapshot["source_slot"]["base"],
                "destination_base": snapshot["destination_slot"]["base"],
                "return_address": snapshot["return_address"],
                "natural_c1_route_proven": False,
                "source_promotion_allowed": False,
                "behavior_change_allowed": False,
            },
            "evidence": evidence,
            "snapshot_export": snapshot,
            "natural_route_gaps": natural_gaps,
        }
    )
    return manifest


def render_note(manifest: dict[str, Any]) -> str:
    summary = manifest.get("summary", {})
    policy = manifest.get("policy", {})
    evidence = manifest.get("evidence", {})
    snapshot = manifest.get("snapshot_export", {})
    source = snapshot.get("source_slot", {})
    destination = snapshot.get("destination_slot", {})
    registers = snapshot.get("registers", {})
    observed = ", ".join(evidence.get("observed_addresses", [])) or "-"

    lines = [
        "# C2 B930 Controlled Snapshot Export",
        "",
        "Generated by `tools/build_c2_b930_controlled_snapshot_export.py` from the ignored local `c1_c2_target_action_staging` Mesen result.",
        "This is forced-entry fixture evidence only: it proves `C2:B930` field-export mechanics, not the natural C1 menu route.",
        "",
        "## Summary",
        "",
        f"- result loaded: `{manifest['status']}`",
        f"- controlled snapshot export observed: `{summary.get('controlled_snapshot_export_observed')}`",
        f"- source fields exported to destination: `{summary.get('source_fields_exported_to_destination')}`",
        f"- natural C1 route proven: `{summary.get('natural_c1_route_proven')}`",
        f"- source promotion allowed: `{summary.get('source_promotion_allowed')}`",
        f"- behavior change allowed: `{summary.get('behavior_change_allowed')}`",
        "",
        "## Observed Mechanics",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Observed addresses | {observed} |",
        f"| Routine label | `{snapshot.get('routine_label', '-')}` |",
        f"| Return address | `{snapshot.get('return_address', '-')}` |",
        f"| Source slot | `{source.get('base', '-')}` ({source.get('byte_count', 0)} bytes captured) |",
        f"| Destination slot | `{destination.get('base', '-')}` ({destination.get('before_byte_count', 0)} -> {destination.get('after_byte_count', 0)} bytes captured) |",
        f"| Registers | A={registers.get('a', '-')} X={registers.get('x', '-')} Y={registers.get('y', '-')} DB={registers.get('db', '-')} DP={registers.get('dp', '-')} |",
        "",
        "## Interpretation",
        "",
        "- The forced-entry fixture rewrites `C1:ADB4` so it calls `C2:B930` directly with `A=1` and `X/Y=$9FFA`.",
        "- The capture shows the `$99CE` source battle row feeding the rewritten `$9FFA` selection snapshot row and returning to `C1:ADC3`.",
        "- The direct-page and target-byte values in this capture are wrapper-context artifacts; they should not be treated as natural C1 target-selection behavior.",
        "- The result remains `needs_followup` because the unpatched `C1:CE85` / `C1:CFC6` pre-export route is not yet captured with `C2:B930`.",
        "",
        "## Natural Route Gaps",
        "",
    ]
    lines.extend(f"- {gap}" for gap in manifest.get("natural_route_gaps", []))
    lines.extend(
        [
            "",
            "## Runner Follow-Up",
            "",
            "- The generated Mesen runner now captures pre-call and post-return rows for C1 `snapshot_export` route-hint callsites.",
            "- The next clean pre-export save can therefore produce a natural callsite result without patching `C1:ADB4` into the helper.",
            "",
            "## Policy",
            "",
            f"- forced-entry fixture only: `{policy.get('forced_entry_fixture_only')}`",
            f"- natural C1 route proven: `{policy.get('natural_c1_route_proven')}`",
            f"- source promotion allowed: `{policy.get('source_promotion_allowed')}`",
            f"- behavior change allowed: `{policy.get('behavior_change_allowed')}`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    manifest = build_manifest()
    DEFAULT_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    DEFAULT_NOTE.write_text(render_note(manifest), encoding="utf-8")
    print(f"Wrote {DEFAULT_MANIFEST}")
    print(f"Wrote {DEFAULT_NOTE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
