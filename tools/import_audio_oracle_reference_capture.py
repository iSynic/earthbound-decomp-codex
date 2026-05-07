#!/usr/bin/env python3
"""Import externally captured audio oracle reference files into planned paths."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "manifests" / "audio-oracle-comparison-plan.json"
SPC_SIGNATURE = b"SNES-SPC700 Sound File Data"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import one audio oracle reference capture.")
    parser.add_argument("--plan", default=str(DEFAULT_PLAN), help="Oracle comparison plan JSON path.")
    parser.add_argument("--track-id", type=int, required=True, help="Music table track id to import.")
    parser.add_argument("--spc", required=True, help="Reference SPC snapshot captured by the oracle emulator.")
    parser.add_argument("--wav", required=True, help="Reference WAV/PCM render captured or exported by the oracle emulator.")
    parser.add_argument("--oracle-id", default="external_reference", help="Reference oracle id/name.")
    parser.add_argument("--oracle-kind", default="external_emulator_capture", help="Reference oracle kind.")
    parser.add_argument("--emulator-version", default="", help="External emulator version/build string.")
    parser.add_argument("--capture-command", default="", help="Command or manual steps used to produce the capture.")
    parser.add_argument("--audio-settings", default="", help="Audio settings used for the external render.")
    parser.add_argument(
        "--not-independent-emulator-capture",
        action="store_true",
        help="Mark this import as non-independent despite using the external capture importer.",
    )
    parser.add_argument("--notes", default="", help="Short capture note.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing reference capture for this planned track.",
    )
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


def find_job(plan: dict[str, Any], track_id: int) -> dict[str, Any]:
    for job in plan.get("jobs", []):
        if int(job.get("track_id", -1)) == track_id:
            return job
    raise ValueError(f"track id {track_id} is not in oracle comparison plan")


def require_input(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"{label} is not a file: {path}")


def validate_spc(path: Path) -> None:
    with path.open("rb") as stream:
        header = stream.read(len(SPC_SIGNATURE))
    if not header.startswith(SPC_SIGNATURE):
        raise ValueError(f"reference SPC is missing SNES-SPC700 signature: {path}")


def validate_wav(path: Path) -> None:
    wav_metadata(path)


def copy_checked(src: Path, dst: Path, *, overwrite: bool) -> None:
    if dst.exists() and not overwrite:
        raise FileExistsError(f"refusing to overwrite existing reference output: {dst}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def main() -> int:
    args = parse_args()
    plan_path = Path(args.plan)
    plan = load_json(plan_path)
    job = find_job(plan, args.track_id)
    outputs = job["reference_capture_outputs"]

    src_spc = Path(args.spc)
    src_wav = Path(args.wav)
    require_input(src_spc, "reference SPC")
    require_input(src_wav, "reference WAV")
    validate_spc(src_spc)
    validate_wav(src_wav)

    dst_spc = resolve_repo_path(outputs["spc_snapshot"])
    dst_wav = resolve_repo_path(outputs["pcm_wav"])
    dst_metadata = resolve_repo_path(outputs["capture_metadata"])
    copy_checked(src_spc, dst_spc, overwrite=args.overwrite)
    copy_checked(src_wav, dst_wav, overwrite=args.overwrite)
    imported_spc_sha1 = sha1_file(dst_spc)
    imported_wav_sha1 = sha1_file(dst_wav)
    wav_fields = wav_metadata(dst_wav)

    metadata = {
        "schema": "earthbound-decomp.audio-oracle-reference-capture.v1",
        "job_id": job["job_id"],
        "track_id": job["track_id"],
        "track_name": job["track_name"],
        "oracle_id": args.oracle_id,
        "oracle_kind": args.oracle_kind,
        "independent_emulator_capture": not args.not_independent_emulator_capture,
        "emulator_version": args.emulator_version,
        "capture_command": args.capture_command,
        "audio_settings": args.audio_settings,
        "source_spc_sha1": job.get("source_spc", {}).get("sha1"),
        "reference_wav_sha1": imported_wav_sha1,
        **wav_fields,
        "notes": args.notes,
        "source_inputs": {
            "spc": str(src_spc),
            "wav": str(src_wav),
            "source_spc_sha1": job.get("source_spc", {}).get("sha1"),
        },
        "imported_outputs": {
            "spc_snapshot": {
                "path": outputs["spc_snapshot"],
                "bytes": dst_spc.stat().st_size,
                "sha1": imported_spc_sha1,
            },
            "pcm_wav": {
                "path": outputs["pcm_wav"],
                "bytes": dst_wav.stat().st_size,
                "sha1": imported_wav_sha1,
            },
        },
        "distribution_policy": "generated_from_user_provided_rom_or_reference_emulator_output_do_not_commit",
    }
    dst_metadata.parent.mkdir(parents=True, exist_ok=True)
    if dst_metadata.exists() and not args.overwrite:
        raise FileExistsError(f"refusing to overwrite existing reference metadata: {dst_metadata}")
    dst_metadata.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Imported oracle reference capture for track {args.track_id:03d} -> {dst_metadata}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
