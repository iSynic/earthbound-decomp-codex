#!/usr/bin/env python3
"""Validate the unified audio zero/nonzero probe campaign plan."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "audio-probe-campaign-plan.json"
REQUIRED_REFERENCES = {
    "manifests/audio-zero-runtime-probe-plan.json",
    "manifests/audio-nonzero-control-probe-plan.json",
    "manifests/audio-sequence-semantics-intake-plan.json",
    "manifests/audio-duration-uncertainty-register.json",
}
REQUIRED_COMMANDS = {"0x00", "0xEF", "0xFD", "0xFE", "0xFF"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate audio probe campaign plan.")
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def count_records(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        counts[str(record.get(key))] += 1
    return dict(sorted(counts.items()))


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-probe-campaign-plan.v1", "unexpected schema")
    require(
        data.get("status") == "probe_campaign_ready_for_external_harness_runs",
        f"unexpected status {data.get('status')}",
    )
    require(REQUIRED_REFERENCES <= set(data.get("references", [])), "missing references")
    jobs = data.get("campaign_jobs", [])
    summary = data.get("summary", {})
    require(int(summary.get("campaign_job_count", -1)) == len(jobs), "campaign job count mismatch")
    require(len(jobs) == 26, f"expected 26 jobs, got {len(jobs)}")
    require(summary.get("lane_job_counts") == count_records(jobs, "lane"), "lane counts mismatch")
    require(summary.get("phase_job_counts") == count_records(jobs, "phase"), "phase counts mismatch")
    require(summary.get("command_job_counts") == count_records(jobs, "command"), "command counts mismatch")
    require(summary.get("sequence_promotion_allowed_by_campaign") is False, "campaign must not allow promotion")
    require(int(summary.get("accepted_intake_candidate_count", -1)) == 0, "expected no accepted intake candidates yet")
    require(summary.get("first_phase") == "nonzero-0957-command-mix", "first campaign phase should target 0x0957")
    require(
        summary.get("first_three_job_ids")
        == ["nonzero-probe-ff-pc-0957", "nonzero-probe-ef-pc-0957", "nonzero-probe-fe-pc-0957"],
        "first three jobs should be the 0x0957 FF/EF/FE mix",
    )

    seen_ids: set[str] = set()
    seen_orders: set[int] = set()
    commands: set[str] = set()
    for job in jobs:
        job_id = str(job.get("job_id", ""))
        lane = str(job.get("lane"))
        order = int(job.get("execution_order", 0))
        commands.add(str(job.get("command")))
        require(order > 0, f"{job_id}: invalid execution order")
        require(order not in seen_orders, f"{job_id}: duplicate execution order {order}")
        seen_orders.add(order)
        require(job_id not in seen_ids, f"duplicate job id {job_id}")
        seen_ids.add(job_id)
        require(lane in {"zero", "nonzero"}, f"{job_id}: unexpected lane {lane}")
        require(job.get("promotion_allowed_by_campaign") is False, f"{job_id}: campaign promotion must be blocked")
        require(job.get("run_command"), f"{job_id}: missing run command")
        require(job.get("stub_shape_command"), f"{job_id}: missing stub command")
        require(job.get("result_validator"), f"{job_id}: missing result validator")
        require(job.get("result_collector"), f"{job_id}: missing result collector")
        require(job.get("intake_refresh") == "python tools/build_audio_sequence_semantics_intake_plan.py", f"{job_id}: bad intake refresh")
        result_path = str(job.get("result_path", "")).replace("\\", "/")
        if lane == "zero":
            require(job_id.startswith("zero-probe-track-"), f"{job_id}: bad zero job id")
            require(str(job.get("command")) == "0x00", f"{job_id}: zero lane must be 0x00")
            require(result_path.startswith("build/audio/zero-runtime-probe/"), f"{job_id}: bad zero result path")
            require("run_audio_zero_runtime_probe_batch.py" in str(job.get("run_command")), f"{job_id}: bad zero runner")
        else:
            require(job_id.startswith("nonzero-probe-"), f"{job_id}: bad nonzero job id")
            require(result_path.startswith("build/audio/nonzero-control-probe/"), f"{job_id}: bad nonzero result path")
            require(
                "run_audio_nonzero_control_probe_batch.py" in str(job.get("run_command")),
                f"{job_id}: bad nonzero runner",
            )
    require(seen_orders == set(range(1, len(jobs) + 1)), "execution orders must be contiguous")
    require(commands == REQUIRED_COMMANDS, "campaign command coverage mismatch")
    require(data.get("execution_policy"), "missing execution policy")
    require(data.get("post_run_validation_commands"), "missing post-run validation commands")
    for command in (
        "python tools/validate_audio_sequence_semantics_intake_plan.py",
        "python tools/validate_audio_duration_uncertainty_register.py",
        "python tools/validate_audio_sequence_command_semantics.py",
    ):
        require(command in data.get("post_run_validation_commands", []), f"missing post-run command {command}")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio probe campaign plan validation OK: "
        f"{data['summary']['campaign_job_count']} jobs, "
        f"{data['summary']['first_phase']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
