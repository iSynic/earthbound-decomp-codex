from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
ASSESSMENT = ROOT / "manifests" / "coilsnake-phase2c-promotion-assessment.json"
STATUS = ROOT / "manifests" / "coilsnake-phase2c-status.json"

VALID_ASSESSMENTS = {
    "authoring-lowering-only",
    "defer-original-runtime-promotion",
    "promote-to-local-contract",
}
VALID_ACTIONS = {
    "keep-as-oracle-evidence",
    "record-as-rebuilt-layout-evidence",
    "promote-runtime-correlated-field",
    "promote-bounded-insertion-evidence",
    "keep-as-compiler-behavior-constraint",
}
PROMOTABLE_EXPERIMENTS = {
    "bg-data-distortion1-probe",
    "windowgraphics-windows1-copy-probe",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    problems: list[str] = []

    if not ASSESSMENT.is_file():
        print(f"Phase 2C promotion assessment not found: {ASSESSMENT}")
        return 2
    if not STATUS.is_file():
        print(f"Phase 2C status not found: {STATUS}")
        return 2

    assessment = load_json(ASSESSMENT)
    status = load_json(STATUS)

    if assessment.get("schema") != "earthbound-decomp.coilsnake-phase2c-promotion-assessment.v1":
        problems.append("unexpected schema")
    if assessment.get("input_status") != "manifests/coilsnake-phase2c-status.json":
        problems.append("input_status must point at manifests/coilsnake-phase2c-status.json")

    rows = assessment.get("assessments")
    if not isinstance(rows, list):
        problems.append("assessments must be a list")
        rows = []

    status_experiments = status.get("experiments")
    if not isinstance(status_experiments, list):
        problems.append("status experiments must be a list")
        status_experiments = []
    status_ids = {
        experiment.get("experiment_id")
        for experiment in status_experiments
        if isinstance(experiment, dict)
    }

    counts: dict[str, int] = {}
    seen_ids: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            problems.append(f"assessment row {index} is not an object")
            continue

        experiment_id = row.get("experiment_id")
        if not isinstance(experiment_id, str) or not experiment_id:
            problems.append(f"assessment row {index} missing experiment_id")
            continue
        if experiment_id in seen_ids:
            problems.append(f"duplicate experiment_id: {experiment_id}")
        seen_ids.add(experiment_id)
        if experiment_id not in status_ids:
            problems.append(f"{experiment_id}: not present in Phase 2C status")

        row_assessment = row.get("assessment")
        if row_assessment not in VALID_ASSESSMENTS:
            problems.append(f"{experiment_id}: invalid assessment {row_assessment!r}")
        else:
            counts[row_assessment] = counts.get(row_assessment, 0) + 1

        action = row.get("recommended_action")
        if action not in VALID_ACTIONS:
            problems.append(f"{experiment_id}: invalid recommended_action {action!r}")

        local_docs = row.get("local_docs")
        if not isinstance(local_docs, list) or not local_docs:
            problems.append(f"{experiment_id}: local_docs must be a nonempty list")
        else:
            for doc in local_docs:
                if not isinstance(doc, str) or not doc:
                    problems.append(f"{experiment_id}: local doc path is not a string")
                    continue
                if not (ROOT / doc).is_file():
                    problems.append(f"{experiment_id}: local doc does not exist: {doc}")

        if row_assessment == "promote-to-local-contract":
            if experiment_id not in PROMOTABLE_EXPERIMENTS:
                problems.append(f"{experiment_id}: unexpected promote-to-local-contract assessment")
            if action not in {"promote-runtime-correlated-field", "promote-bounded-insertion-evidence"}:
                problems.append(f"{experiment_id}: promotable row has non-promotion action {action!r}")
        elif experiment_id in PROMOTABLE_EXPERIMENTS:
            problems.append(f"{experiment_id}: expected promote-to-local-contract assessment")

    if seen_ids != status_ids:
        missing = sorted(str(experiment_id) for experiment_id in status_ids - seen_ids)
        extra = sorted(str(experiment_id) for experiment_id in seen_ids - status_ids)
        if missing:
            problems.append(f"missing assessments for status experiments: {', '.join(missing)}")
        if extra:
            problems.append(f"assessments without status experiments: {', '.join(extra)}")

    if assessment.get("assessment_counts") != dict(sorted(counts.items())):
        problems.append("assessment_counts are stale")

    if problems:
        for problem in problems:
            print(f"ERROR: {problem}")
        return 1

    print(f"Validated {ASSESSMENT.relative_to(ROOT)}: {len(rows)} assessments")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
