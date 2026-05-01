from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STUBS = ROOT / "manifests" / "coilsnake-promotion-stubs.json"
DEFAULT_PREJOIN = ROOT / "build" / "coilsnake" / "reports" / "coilsnake-experiment-prejoin-report.json"

REQUIRED_STUB_FIELDS = {
    "experiment_id",
    "source_file",
    "planned_edit",
    "prejoin_status",
    "resource_family",
    "promotion_target",
    "experiment_report",
    "ingest_command",
    "evidence_gate",
    "required_join_fields",
    "tracked_update_targets",
    "candidate_runtime_anchors",
    "field_semantics_action",
    "payload_policy",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def validate(stubs_path: Path, prejoin_path: Path) -> list[str]:
    problems: list[str] = []
    stubs_doc = load_json(stubs_path)
    prejoin_doc = load_json(prejoin_path)
    prejoin_ids = {
        item.get("experiment_id")
        for item in prejoin_doc.get("prejoins", [])
        if isinstance(item, dict)
    }

    stubs = stubs_doc.get("promotion_stubs", [])
    if not isinstance(stubs, list):
        return ["promotion_stubs must be a list"]

    seen: set[str] = set()
    for index, stub in enumerate(stubs):
        if not isinstance(stub, dict):
            problems.append(f"promotion_stubs[{index}] must be an object")
            continue
        experiment_id = stub.get("experiment_id")
        label = str(experiment_id or f"promotion_stubs[{index}]")
        if experiment_id not in prejoin_ids:
            problems.append(f"{label}: no matching prejoin entry")
        if isinstance(experiment_id, str):
            if experiment_id in seen:
                problems.append(f"{label}: duplicate experiment_id")
            seen.add(experiment_id)

        missing = sorted(REQUIRED_STUB_FIELDS - set(stub))
        if missing:
            problems.append(f"{label}: missing required field(s): {', '.join(missing)}")

        for key in (
            "experiment_id",
            "source_file",
            "planned_edit",
            "prejoin_status",
            "resource_family",
            "promotion_target",
            "experiment_report",
            "ingest_command",
            "field_semantics_action",
            "payload_policy",
        ):
            if key in stub and (not isinstance(stub[key], str) or not stub[key]):
                problems.append(f"{label}: {key} must be a nonempty string")

        gate = stub.get("evidence_gate")
        if not isinstance(gate, dict):
            problems.append(f"{label}: evidence_gate must be an object")
        else:
            for key in ("next_required_evidence", "blocking_status", "allowed_promotion_after"):
                if key not in gate:
                    problems.append(f"{label}: evidence_gate missing {key}")
            if "allowed_promotion_after" in gate and not isinstance(gate["allowed_promotion_after"], list):
                problems.append(f"{label}: evidence_gate.allowed_promotion_after must be a list")

        if not isinstance(stub.get("required_join_fields"), list) or not stub.get("required_join_fields"):
            problems.append(f"{label}: required_join_fields must be a nonempty list")
        if not isinstance(stub.get("tracked_update_targets"), list):
            problems.append(f"{label}: tracked_update_targets must be a list")

        for target in stub.get("tracked_update_targets", []):
            if isinstance(target, str) and target.startswith("notes/") and not (ROOT / target).is_file():
                problems.append(f"{label}: tracked update target does not exist: {target}")

        anchors = stub.get("candidate_runtime_anchors")
        if not isinstance(anchors, dict):
            problems.append(f"{label}: candidate_runtime_anchors must be an object")
            continue

        if anchors:
            if anchors.get("status") != "candidate-until-diff-confirmed":
                problems.append(f"{label}: candidate_runtime_anchors.status must be candidate-until-diff-confirmed")
            for key in (
                "candidate_local_ranges",
                "field_hints",
                "source_anchor_paths",
                "note_anchor_paths",
                "runtime_consumer_hints",
            ):
                if key in anchors and not isinstance(anchors[key], list):
                    problems.append(f"{label}: candidate_runtime_anchors.{key} must be a list")

            for range_index, range_hint in enumerate(anchors.get("candidate_local_ranges", [])):
                if not isinstance(range_hint, dict):
                    problems.append(f"{label}: candidate_local_ranges[{range_index}] must be an object")
                    continue
                for key in ("label", "range", "basis"):
                    if not isinstance(range_hint.get(key), str) or not range_hint.get(key):
                        problems.append(f"{label}: candidate_local_ranges[{range_index}].{key} must be nonempty")

            for field_index, field_hint in enumerate(anchors.get("field_hints", [])):
                if not isinstance(field_hint, dict):
                    problems.append(f"{label}: field_hints[{field_index}] must be an object")
                    continue
                for key in ("coilsnake_field", "candidate_local_field", "basis"):
                    if not isinstance(field_hint.get(key), str) or not field_hint.get(key):
                        problems.append(f"{label}: field_hints[{field_index}].{key} must be nonempty")

            for path_key in ("source_anchor_paths", "note_anchor_paths"):
                for path_text in anchors.get(path_key, []):
                    if not isinstance(path_text, str) or not path_text:
                        problems.append(f"{label}: {path_key} entries must be nonempty strings")
                        continue
                    if not (ROOT / path_text).is_file():
                        problems.append(f"{label}: {path_key} target does not exist: {path_text}")

            for consumer_index, consumer in enumerate(anchors.get("runtime_consumer_hints", [])):
                if not isinstance(consumer, dict):
                    problems.append(f"{label}: runtime_consumer_hints[{consumer_index}] must be an object")
                    continue
                for key in ("status", "consumer", "basis"):
                    if not isinstance(consumer.get(key), str) or not consumer.get(key):
                        problems.append(f"{label}: runtime_consumer_hints[{consumer_index}].{key} must be nonempty")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CoilSnake promotion stubs.")
    parser.add_argument("--stubs", type=Path, default=DEFAULT_STUBS)
    parser.add_argument("--prejoin", type=Path, default=DEFAULT_PREJOIN)
    args = parser.parse_args()

    stubs = args.stubs.resolve()
    prejoin = args.prejoin.resolve()
    if not stubs.is_file():
        print(f"Promotion stubs manifest not found: {stubs}", file=sys.stderr)
        return 2
    if not prejoin.is_file():
        print(f"Prejoin report not found: {prejoin}", file=sys.stderr)
        return 2

    problems = validate(stubs, prejoin)
    if problems:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        return 1

    count = len(load_json(stubs).get("promotion_stubs", []))
    print(f"Validated {rel(stubs)}: {count} promotion stubs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
