#!/usr/bin/env python3
"""Run non-mutating checks for the independent external-emulator oracle campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CAMPAIGN = ROOT / "manifests" / "audio-independent-oracle-campaign-plan.json"
DEFAULT_SUMMARY = ROOT / "build" / "audio" / "independent-oracle-campaign-runs" / "independent-oracle-campaign-run-summary.json"
SPC_SIGNATURE = b"SNES-SPC700 Sound File Data"
REQUIRED_METADATA_FIELDS = {
    "oracle_id",
    "oracle_kind",
    "independent_emulator_capture",
    "emulator_version",
    "capture_command",
    "audio_settings",
    "source_spc_sha1",
    "reference_wav_sha1",
    "render_sample_rate",
    "channels",
    "bits_per_sample",
    "duration_seconds",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run independent oracle campaign checks.")
    parser.add_argument("--campaign", default=str(DEFAULT_CAMPAIGN), help="Committed independent oracle campaign JSON.")
    parser.add_argument(
        "--mode",
        default="dry-run-plan",
        choices=["dry-run-plan", "audit-existing-captures"],
        help="Emit checklist records only, or audit existing planned capture metadata without modifying it.",
    )
    parser.add_argument("--phase", action="append", help="Campaign phase to include. May be repeated.")
    parser.add_argument("--track-id", type=int, action="append", help="Track id to include. May be repeated.")
    parser.add_argument("--job-id", action="append", help="Oracle job id to include. May be repeated.")
    parser.add_argument("--limit", type=int, help="Maximum selected jobs to include.")
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY), help="Ignored run summary output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha1_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_u16(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "little")


def read_u32(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "little")


def wav_metadata(path: Path) -> dict[str, float | int]:
    data = path.read_bytes()
    if len(data) < 44 or data[0:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError(f"reference WAV is missing RIFF/WAVE header: {path}")
    if data[12:16] != b"fmt ":
        raise ValueError(f"reference WAV is missing canonical fmt chunk: {path}")
    fmt_size = read_u32(data, 16)
    data_offset = 20 + fmt_size
    if len(data) < data_offset + 8 or data[data_offset : data_offset + 4] != b"data":
        raise ValueError(f"reference WAV is missing canonical data chunk: {path}")
    channels = read_u16(data, 22)
    sample_rate = read_u32(data, 24)
    bits_per_sample = read_u16(data, 34)
    data_bytes = read_u32(data, data_offset + 4)
    bytes_per_frame = max(1, channels * bits_per_sample // 8)
    return {
        "render_sample_rate": sample_rate,
        "channels": channels,
        "bits_per_sample": bits_per_sample,
        "duration_seconds": round(data_bytes / bytes_per_frame / sample_rate, 6) if sample_rate else 0.0,
    }


def resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def select_jobs(campaign: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    phases = set(args.phase or [])
    track_ids = set(args.track_id or [])
    job_ids = set(args.job_id or [])
    jobs: list[dict[str, Any]] = []
    for job in campaign.get("campaign_jobs", []):
        if phases and job.get("phase") not in phases:
            continue
        if track_ids and int(job.get("track_id", -1)) not in track_ids:
            continue
        if job_ids and job.get("job_id") not in job_ids:
            continue
        jobs.append(job)
    available_job_ids = {str(job.get("job_id")) for job in campaign.get("campaign_jobs", [])}
    available_track_ids = {int(job.get("track_id", -1)) for job in campaign.get("campaign_jobs", [])}
    missing_jobs = job_ids - available_job_ids
    missing_tracks = track_ids - available_track_ids
    if missing_jobs:
        raise ValueError(f"requested job ids not found: {', '.join(sorted(missing_jobs))}")
    if missing_tracks:
        raise ValueError(f"requested track ids not found: {sorted(missing_tracks)}")
    jobs.sort(key=lambda item: int(item.get("execution_order", 0)))
    if args.limit is not None:
        jobs = jobs[: args.limit]
    return jobs


def metadata_audit(job: dict[str, Any]) -> dict[str, Any]:
    outputs = job.get("reference_capture_outputs", {})
    metadata_path_text = str(outputs.get("capture_metadata", ""))
    metadata_path = resolve_repo_path(metadata_path_text)
    record: dict[str, Any] = {
        "capture_metadata_path": metadata_path_text,
        "capture_metadata_exists": metadata_path.exists(),
        "missing_metadata_fields": sorted(REQUIRED_METADATA_FIELDS),
        "independent_emulator_capture": False,
        "oracle_id": None,
        "oracle_kind": None,
        "source_spc_sha1_matches": False,
        "spc_exists": False,
        "spc_sha1_matches": False,
        "spc_signature_ok": False,
        "wav_exists": False,
        "wav_sha1_matches": False,
        "wav_metadata_matches": False,
        "wav_format_matches_policy": False,
        "duration_covers_planned": False,
    }
    if not metadata_path.exists():
        return record
    metadata = load_json(metadata_path)
    missing_fields = REQUIRED_METADATA_FIELDS - set(metadata)
    imported = metadata.get("imported_outputs", {})
    spc_record = imported.get("spc_snapshot", {})
    wav_record = imported.get("pcm_wav", {})
    spc_path = resolve_repo_path(str(outputs.get("spc_snapshot", "")))
    wav_path = resolve_repo_path(str(outputs.get("pcm_wav", "")))
    spc_exists = spc_path.exists()
    wav_exists = wav_path.exists()
    wav_meta: dict[str, float | int] = {}
    if wav_exists:
        try:
            wav_meta = wav_metadata(wav_path)
        except ValueError:
            wav_meta = {}
    record.update(
        {
            "missing_metadata_fields": sorted(missing_fields),
            "independent_emulator_capture": bool(metadata.get("independent_emulator_capture")),
            "oracle_id": metadata.get("oracle_id"),
            "oracle_kind": metadata.get("oracle_kind"),
            "source_spc_sha1_matches": metadata.get("source_spc_sha1") == job.get("source_spc", {}).get("sha1"),
            "spc_exists": spc_exists,
            "spc_sha1_matches": spc_exists and spc_record.get("sha1") == sha1_file(spc_path),
            "spc_signature_ok": spc_exists and spc_path.read_bytes().startswith(SPC_SIGNATURE),
            "wav_exists": wav_exists,
            "wav_sha1_matches": wav_exists and metadata.get("reference_wav_sha1") == sha1_file(wav_path),
            "wav_metadata_matches": bool(wav_meta)
            and all(
                int(metadata.get(field, 0)) == int(wav_meta[field])
                for field in ("render_sample_rate", "channels", "bits_per_sample")
            ),
            "wav_format_matches_policy": (
                int(metadata.get("render_sample_rate", 0)) == 32000
                and int(metadata.get("channels", 0)) == 2
                and int(metadata.get("bits_per_sample", 0)) == 16
            ),
            "duration_covers_planned": float(metadata.get("duration_seconds", 0.0)) >= float(job.get("duration_seconds", 0.0)),
        }
    )
    return record


def blocking_reasons(audit: dict[str, Any], *, mode: str) -> list[str]:
    if mode == "dry-run-plan":
        return ["independent_capture_not_audited"]
    if audit.get("capture_metadata_exists") is not True:
        return ["missing_capture_metadata"]
    reasons: list[str] = []
    checks = {
        "independent_emulator_capture": "metadata_not_marked_independent",
        "source_spc_sha1_matches": "source_spc_sha1_mismatch",
        "spc_exists": "missing_reference_spc",
        "spc_sha1_matches": "reference_spc_sha1_mismatch",
        "spc_signature_ok": "reference_spc_signature_invalid",
        "wav_exists": "missing_reference_wav",
        "wav_sha1_matches": "reference_wav_sha1_mismatch",
        "wav_metadata_matches": "reference_wav_metadata_mismatch",
        "wav_format_matches_policy": "reference_wav_format_mismatch",
        "duration_covers_planned": "reference_wav_too_short",
    }
    for field, reason in checks.items():
        if audit.get(field) is not True:
            reasons.append(reason)
    if audit.get("missing_metadata_fields"):
        reasons.append("missing_required_metadata_fields")
    return reasons


def run_one(job: dict[str, Any], *, mode: str) -> dict[str, Any]:
    audit = metadata_audit(job) if mode == "audit-existing-captures" else {}
    ready = (
        mode == "audit-existing-captures"
        and audit.get("capture_metadata_exists") is True
        and audit.get("independent_emulator_capture") is True
        and not audit.get("missing_metadata_fields")
        and audit.get("source_spc_sha1_matches") is True
        and audit.get("spc_exists") is True
        and audit.get("spc_sha1_matches") is True
        and audit.get("spc_signature_ok") is True
        and audit.get("wav_exists") is True
        and audit.get("wav_sha1_matches") is True
        and audit.get("wav_metadata_matches") is True
        and audit.get("wav_format_matches_policy") is True
        and audit.get("duration_covers_planned") is True
    )
    status = "independent_capture_ready" if ready else "pending_independent_capture"
    reasons = [] if ready else blocking_reasons(audit, mode=mode)
    return {
        "execution_order": int(job["execution_order"]),
        "campaign_job_id": job["campaign_job_id"],
        "job_id": job["job_id"],
        "track_id": int(job["track_id"]),
        "track_name": job["track_name"],
        "phase": job["phase"],
        "diagnostic_focus": job["diagnostic_focus"],
        "primary_uncertainty": job["primary_uncertainty"],
        "mode": mode,
        "status": status,
        "blocking_reasons": reasons,
        "import_command": job["import_command"],
        "capture_validator_command": job["capture_validator_command"],
        "collect_command": job["collect_command"],
        "result_validator": job["result_validator"],
        "capture_metadata_path": job.get("reference_capture_outputs", {}).get("capture_metadata"),
        "promotion_allowed_by_run": False,
        "audit": audit,
    }


def write_summary(campaign: dict[str, Any], summary_path: Path, args: argparse.Namespace, runs: list[dict[str, Any]]) -> None:
    independent_ready_count = sum(1 for run in runs if run.get("status") == "independent_capture_ready")
    pending_count = sum(1 for run in runs if run.get("status") == "pending_independent_capture")
    status_counts: Counter[str] = Counter(str(run.get("status")) for run in runs)
    phase_counts: Counter[str] = Counter(str(run.get("phase")) for run in runs)
    focus_counts: Counter[str] = Counter(str(run.get("diagnostic_focus")) for run in runs)
    uncertainty_counts: Counter[str] = Counter(str(run.get("primary_uncertainty")) for run in runs)
    blocking_reason_counts: Counter[str] = Counter()
    for run in runs:
        for reason in run.get("blocking_reasons", []):
            blocking_reason_counts[str(reason)] += 1
    summary = {
        "schema": "earthbound-decomp.audio-independent-oracle-campaign-run.v1",
        "campaign_plan": "manifests/audio-independent-oracle-campaign-plan.json",
        "campaign_status": campaign.get("status"),
        "mode": args.mode,
        "selected_count": len(runs),
        "independent_capture_ready_count": independent_ready_count,
        "pending_independent_capture_count": pending_count,
        "status_counts": dict(sorted(status_counts.items())),
        "phase_counts": dict(sorted(phase_counts.items())),
        "diagnostic_focus_counts": dict(sorted(focus_counts.items())),
        "primary_uncertainty_counts": dict(sorted(uncertainty_counts.items())),
        "blocking_reason_counts": dict(sorted(blocking_reason_counts.items())),
        "promotion_allowed_by_run": False,
        "release_quality_claim_ready_by_run": False,
        "selection": {
            "phase": args.phase or [],
            "track_id": args.track_id or [],
            "job_id": args.job_id or [],
            "limit": args.limit,
        },
        "runs": runs,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    campaign = load_json(Path(args.campaign))
    selected = select_jobs(campaign, args)
    print(f"Selected {len(selected)} independent oracle campaign jobs for {args.mode} mode")
    runs = [run_one(job, mode=args.mode) for job in selected]
    for run in runs:
        print(f"- {run['execution_order']:03d} {run['job_id']}: {run['status']}")
    write_summary(campaign, Path(args.summary), args, runs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
