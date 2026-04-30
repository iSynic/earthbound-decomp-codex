#!/usr/bin/env python3
"""Diagnostic snes_spc adapter harness.

This does not link or execute Blargg's snes_spc library yet. It consumes the
diagnostic SPC snapshots emitted by the native ares harness, copies the matching
snapshot into the snes_spc job output directory, and writes a readiness JSON so
the lightweight backend contract can be exercised end-to-end.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SNAPSHOT_INDEX = ROOT / "build" / "audio" / "backend-jobs" / "diagnostic-spc-snapshots.json"
SPC_SIGNATURE = b"SNES-SPC700 Sound File Data v0.30"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a diagnostic snes_spc adapter job.")
    parser.add_argument("--job", required=True, help="Backend job JSON path.")
    parser.add_argument("--result", required=True, help="Result JSON path to write.")
    parser.add_argument(
        "--snapshot-index",
        default=str(DEFAULT_SNAPSHOT_INDEX),
        help="Diagnostic SPC snapshot index produced by collect_audio_diagnostic_spc_snapshots.py.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha1_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_snapshot(index: dict[str, Any], track_id: int) -> dict[str, Any]:
    for record in index.get("records", []):
        if int(record.get("track_id", -1)) == track_id and record.get("snapshot"):
            return record
    raise ValueError(f"diagnostic SPC snapshot not found for track {track_id}")


def inspect_spc(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    ram = data[0x100:0x10100] if len(data) >= 0x10100 else b""
    dsp = data[0x10100:0x10180] if len(data) >= 0x10180 else b""
    return {
        "bytes": len(data),
        "sha1": hashlib.sha1(data).hexdigest(),
        "signature_ok": data.startswith(SPC_SIGNATURE),
        "pc": f"0x{data[0x26]:02X}{data[0x25]:02X}" if len(data) > 0x26 else None,
        "a": f"0x{data[0x27]:02X}" if len(data) > 0x27 else None,
        "x": f"0x{data[0x28]:02X}" if len(data) > 0x28 else None,
        "y": f"0x{data[0x29]:02X}" if len(data) > 0x29 else None,
        "psw": f"0x{data[0x2A]:02X}" if len(data) > 0x2A else None,
        "sp": f"0x{data[0x2B]:02X}" if len(data) > 0x2B else None,
        "ram_sha1": hashlib.sha1(ram).hexdigest() if len(ram) == 65536 else None,
        "dsp_register_sha1": hashlib.sha1(dsp).hexdigest() if len(dsp) == 128 else None,
        "dsp_nonzero_count": sum(1 for byte in dsp if byte) if len(dsp) == 128 else None,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    job_path = Path(args.job)
    result_path = Path(args.result)
    snapshot_index_path = Path(args.snapshot_index)
    job = load_json(job_path)
    snapshot_index = load_json(snapshot_index_path)
    source_record = find_snapshot(snapshot_index, int(job["track_id"]))
    source_snapshot = source_record["snapshot"]
    source_spc_path = Path(source_snapshot["path"])
    output_dir = Path(job["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    copied_spc_path = output_dir / "diagnostic-input.spc"
    shutil.copyfile(source_spc_path, copied_spc_path)
    copied = inspect_spc(copied_spc_path)
    if not copied["signature_ok"]:
        raise ValueError(f"copied SPC has invalid signature: {copied_spc_path}")
    if copied["sha1"] != source_snapshot["sha1"]:
        raise ValueError("copied SPC SHA-1 does not match source snapshot index")

    readiness_path = output_dir / "snes-spc-readiness.json"
    readiness = {
        "schema": "earthbound-decomp.snes-spc-readiness.v1",
        "job_id": job["job_id"],
        "track_id": job["track_id"],
        "track_name": job["track_name"],
        "source_snapshot_index": str(snapshot_index_path),
        "source_snapshot_job_id": source_record["job_id"],
        "source_snapshot_path": str(source_spc_path),
        "copied_snapshot_path": str(copied_spc_path),
        "snapshot": copied,
        "adapter_status": "container_ready_renderer_not_linked",
        "renderer_library": {
            "id": "snes_spc",
            "linked": False,
            "reason": "Dependency not vendored/fetched yet; this harness validates the input contract before LGPL integration.",
        },
        "faithfulness": "diagnostic_container_only_not_runtime_faithful",
    }
    write_json(readiness_path, readiness)
    readiness_bytes = readiness_path.read_bytes()

    result = {
        "schema": "earthbound-decomp.audio-backend-result.v1",
        "job_id": job["job_id"],
        "backend_id": job["backend_id"],
        "backend_version": "snes-spc-diagnostic-adapter-0.1",
        "status": "unsupported",
        "input_fixture_path": job["fixture_path"],
        "input_apu_ram_sha1": job["input_apu_ram_sha1"],
        "outputs": [
            {
                "kind": "complete_spc_snapshot",
                "path": str(copied_spc_path),
                "bytes": copied["bytes"],
                "sha1": copied["sha1"],
            },
            {
                "kind": "render_hash_json",
                "path": str(readiness_path),
                "bytes": len(readiness_bytes),
                "sha1": hashlib.sha1(readiness_bytes).hexdigest(),
            },
        ],
        "diagnostics": {
            "execution_mode": "diagnostic_snapshot_adapter_no_renderer",
            "handshake_policy": "inherits_diagnostic_ares_snapshot_preseed",
            "timing_basis": "not_rendered",
            "message": "Validated and copied a diagnostic SPC container for future snes_spc playback experiments. No PCM/WAV was rendered.",
        },
    }
    write_json(result_path, result)
    print(f"Wrote snes_spc diagnostic adapter result -> {result_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
