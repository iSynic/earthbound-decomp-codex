from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CROSSWALK = ROOT / "manifests" / "coilsnake-crosswalk.json"
DEFAULT_FIELD_SEMANTICS = ROOT / "manifests" / "coilsnake-field-semantics.json"

EVIDENCE_LEVELS = {
    "coilsnake-observed",
    "local-range-confirmed",
    "diff-confirmed",
    "runtime-correlated",
}

REQUIRED_FIELDS = {
    "coilsnake_field",
    "edited_value",
    "local_field",
    "field_evidence_level",
    "promotion_status",
    "runtime_consumers",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def validate_consumer(
    *,
    experiment_id: str,
    index: int,
    consumer: Any,
) -> list[str]:
    problems: list[str] = []
    if not isinstance(consumer, dict):
        return [f"{experiment_id}: runtime_consumers[{index}] must be an object"]

    for key in ("kind", "routine", "source", "detail"):
        if not isinstance(consumer.get(key), str) or not consumer[key]:
            problems.append(f"{experiment_id}: runtime_consumers[{index}].{key} must be a nonempty string")

    source = consumer.get("source")
    if isinstance(source, str) and source:
        source_path = ROOT / source
        if not source_path.is_file():
            problems.append(f"{experiment_id}: runtime consumer source does not exist: {source}")

    return problems


def validate_semantics(crosswalk_path: Path, field_semantics_path: Path) -> list[str]:
    problems: list[str] = []
    crosswalk = load_json(crosswalk_path)
    semantics_doc = load_json(field_semantics_path)

    controlled_experiments = crosswalk.get("controlled_experiments", {})
    if not isinstance(controlled_experiments, dict):
        return ["crosswalk controlled_experiments must be an object"]

    field_semantics = semantics_doc.get("field_semantics", {})
    if not isinstance(field_semantics, dict):
        return ["field_semantics must be an object"]

    for experiment_id, semantics in sorted(field_semantics.items()):
        if experiment_id not in controlled_experiments:
            problems.append(f"{experiment_id}: no matching controlled experiment in {rel(crosswalk_path)}")
        if not isinstance(semantics, dict):
            problems.append(f"{experiment_id}: semantics entry must be an object")
            continue

        missing = sorted(REQUIRED_FIELDS - set(semantics))
        if missing:
            problems.append(f"{experiment_id}: missing required field(s): {', '.join(missing)}")

        for key in ("coilsnake_field", "edited_value", "local_field", "promotion_status"):
            if key in semantics and (not isinstance(semantics[key], str) or not semantics[key]):
                problems.append(f"{experiment_id}: {key} must be a nonempty string")

        evidence = semantics.get("field_evidence_level")
        if evidence not in EVIDENCE_LEVELS:
            problems.append(f"{experiment_id}: invalid field_evidence_level: {evidence}")

        consumers = semantics.get("runtime_consumers")
        if not isinstance(consumers, list):
            problems.append(f"{experiment_id}: runtime_consumers must be a list")
            consumers = []
        for index, consumer in enumerate(consumers):
            problems.extend(validate_consumer(experiment_id=experiment_id, index=index, consumer=consumer))

        if evidence == "runtime-correlated" and not consumers:
            problems.append(f"{experiment_id}: runtime-correlated field needs at least one runtime consumer")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CoilSnake field semantics manifest.")
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--field-semantics", type=Path, default=DEFAULT_FIELD_SEMANTICS)
    args = parser.parse_args()

    crosswalk = args.crosswalk.resolve()
    field_semantics = args.field_semantics.resolve()
    if not crosswalk.is_file():
        print(f"Crosswalk manifest not found: {crosswalk}", file=sys.stderr)
        return 2
    if not field_semantics.is_file():
        print(f"Field semantics manifest not found: {field_semantics}", file=sys.stderr)
        return 2

    problems = validate_semantics(crosswalk, field_semantics)
    if problems:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        return 1

    entries = len(load_json(field_semantics).get("field_semantics", {}))
    print(f"Validated {rel(field_semantics)}: {entries} field semantic entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
