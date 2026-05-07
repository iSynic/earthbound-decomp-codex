#!/usr/bin/env python3
"""Validate one imported audio oracle reference capture package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "manifests" / "audio-oracle-comparison-plan-all-tracks.json"
SPC_SIGNATURE = b"SNES-SPC700 Sound File Data"
EXTERNAL_ORACLE_TOKENS = ("mesen", "bsnes", "higan", "mednafen")
REQUIRED_METADATA_FIELDS = {
    "schema",
    "job_id",
    "track_id",
    "track_name",
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
    "imported_outputs",
    "distribution_policy",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate one audio oracle reference capture.")
    parser.add_argument("metadata", nargs="?", help="Capture metadata JSON path. Defaults to the planned track path.")
    parser.add_argument("--plan", default=str(DEFAULT_PLAN), help="Oracle comparison plan JSON path.")
    parser.add_argument("--track-id", type=int, help="Track id to validate when metadata path is omitted.")
    parser.add_argument("--allow-missing", action="store_true", help="Treat missing metadata as a pending capture instead of an error.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


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


def find_job(plan: dict[str, Any], track_id: int) -> dict[str, Any]:
    for job in plan.get("jobs", []):
        if int(job.get("track_id", -1)) == track_id:
            return job
    raise ValueError(f"track id {track_id} is not in oracle comparison plan")


def planned_metadata_path(plan: dict[str, Any], track_id: int) -> Path:
    return resolve_repo_path(str(find_job(plan, track_id)["reference_capture_outputs"]["capture_metadata"]))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_spc_file(path: Path, expected_sha1: str | None, errors: list[str], label: str) -> None:
    if not path.exists():
        errors.append(f"{label} does not exist: {path}")
        return
    data = path.read_bytes()
    if not data.startswith(SPC_SIGNATURE):
        errors.append(f"{label} is missing SNES-SPC700 signature: {path}")
    if expected_sha1 and sha1_file(path) != expected_sha1:
        errors.append(f"{label} SHA-1 mismatch: {path}")


def validate_wav_file(path: Path, metadata: dict[str, Any], job: dict[str, Any], errors: list[str]) -> None:
    if not path.exists():
        errors.append(f"reference WAV does not exist: {path}")
        return
    try:
        wav = wav_metadata(path)
    except ValueError as error:
        errors.append(str(error))
        return
    if metadata.get("reference_wav_sha1") and sha1_file(path) != metadata.get("reference_wav_sha1"):
        errors.append(f"reference WAV SHA-1 mismatch: {path}")
    for field in ("render_sample_rate", "channels", "bits_per_sample"):
        require(int(metadata.get(field, 0)) == int(wav[field]), f"metadata {field} does not match reference WAV", errors)
    require(abs(float(metadata.get("duration_seconds", 0.0)) - float(wav["duration_seconds"])) <= 0.001, "metadata duration_seconds does not match reference WAV", errors)
    require(int(wav["render_sample_rate"]) == 32000, "reference WAV sample rate must be 32000", errors)
    require(int(wav["channels"]) == 2, "reference WAV must be stereo", errors)
    require(int(wav["bits_per_sample"]) == 16, "reference WAV must be 16-bit", errors)
    planned_duration = float(job.get("source_render", {}).get("metrics", {}).get("rendered_samples", 0)) / 2 / 32000
    require(float(wav["duration_seconds"]) + 0.001 >= planned_duration, "reference WAV is shorter than planned source render", errors)


def validate_capture(metadata_path: Path, plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    metadata = load_json(metadata_path)
    missing_fields = REQUIRED_METADATA_FIELDS - set(metadata)
    if missing_fields:
        errors.append(f"metadata missing fields: {sorted(missing_fields)}")
    track_id = int(metadata.get("track_id", -1))
    job = find_job(plan, track_id)
    outputs = job.get("reference_capture_outputs", {})
    imported = metadata.get("imported_outputs", {})
    spc_record = imported.get("spc_snapshot", {})
    wav_record = imported.get("pcm_wav", {})
    spc_path = resolve_repo_path(str(outputs.get("spc_snapshot", "")))
    wav_path = resolve_repo_path(str(outputs.get("pcm_wav", "")))

    require(metadata.get("schema") == "earthbound-decomp.audio-oracle-reference-capture.v1", "unexpected metadata schema", errors)
    require(metadata.get("job_id") == job.get("job_id"), "metadata job_id does not match plan", errors)
    require(metadata.get("track_name") == job.get("track_name"), "metadata track_name does not match plan", errors)
    require(metadata.get("oracle_kind") == "external_emulator_capture", "oracle_kind must be external_emulator_capture", errors)
    require(metadata.get("independent_emulator_capture") is True, "independent_emulator_capture must be true", errors)
    oracle_id = str(metadata.get("oracle_id", "")).lower()
    require(any(token in oracle_id for token in EXTERNAL_ORACLE_TOKENS), "oracle_id must identify an external emulator", errors)
    require(bool(str(metadata.get("emulator_version", "")).strip()), "emulator_version must be recorded", errors)
    require(bool(str(metadata.get("capture_command", "")).strip()), "capture_command must be recorded", errors)
    require(bool(str(metadata.get("audio_settings", "")).strip()), "audio_settings must be recorded", errors)
    require(metadata.get("source_spc_sha1") == job.get("source_spc", {}).get("sha1"), "source_spc_sha1 does not match plan", errors)
    require(spc_record.get("path") == outputs.get("spc_snapshot"), "imported SPC path does not match plan", errors)
    require(wav_record.get("path") == outputs.get("pcm_wav"), "imported WAV path does not match plan", errors)
    require(str(outputs.get("capture_metadata")) == metadata_path.relative_to(ROOT).as_posix(), "metadata path does not match plan", errors)
    require("do_not_commit" in str(metadata.get("distribution_policy", "")), "distribution policy must keep generated captures uncommitted", errors)

    validate_spc_file(spc_path, spc_record.get("sha1"), errors, "reference SPC")
    validate_wav_file(wav_path, metadata, job, errors)
    return errors


def main() -> int:
    args = parse_args()
    plan = load_json(Path(args.plan))
    if args.metadata:
        metadata_path = resolve_repo_path(args.metadata)
    elif args.track_id is not None:
        metadata_path = planned_metadata_path(plan, args.track_id)
    else:
        raise SystemExit("metadata path or --track-id is required")
    if not metadata_path.exists():
        if args.allow_missing:
            print(f"Audio oracle reference capture pending: {metadata_path}")
            return 0
        raise FileNotFoundError(f"capture metadata does not exist: {metadata_path}")
    errors = validate_capture(metadata_path, plan)
    if errors:
        print("Audio oracle reference capture validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Audio oracle reference capture validation OK: {metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
