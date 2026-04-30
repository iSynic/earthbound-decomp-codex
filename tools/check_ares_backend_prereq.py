#!/usr/bin/env python3
"""Check the local ares checkout/build prerequisite for audio backend work."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ARES_ROOT = ROOT.parent / "ares-earthbound-audio-backend"
DEFAULT_STATUS = ROOT / "build" / "audio" / "ares-backend-status.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check local ares backend prerequisite state.")
    parser.add_argument("--ares-root", default=str(DEFAULT_ARES_ROOT), help="Sibling ares source checkout.")
    parser.add_argument("--json", default=str(DEFAULT_STATUS), help="Ignored status JSON output path.")
    return parser.parse_args()


def run_git(ares_root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(ares_root), *args],
            text=True,
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return result.stdout.strip()


def read_git_head(ares_root: Path) -> str | None:
    head_path = ares_root / ".git" / "HEAD"
    if not head_path.exists():
        return None
    head = head_path.read_text(encoding="utf-8", errors="ignore").strip()
    if head.startswith("ref: "):
        ref = head.removeprefix("ref: ").strip()
        ref_path = ares_root / ".git" / Path(ref.replace("/", "\\"))
        if ref_path.exists():
            return ref_path.read_text(encoding="utf-8", errors="ignore").strip()
        packed_refs = ares_root / ".git" / "packed-refs"
        if packed_refs.exists():
            for line in packed_refs.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.split()
                if len(parts) == 2 and parts[1] == ref:
                    return parts[0]
        return None
    return head if head else None


def read_git_remote(ares_root: Path) -> str | None:
    config_path = ares_root / ".git" / "config"
    if not config_path.exists():
        return None
    in_origin = False
    for raw_line in config_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if line.startswith("[remote "):
            in_origin = line == '[remote "origin"]'
            continue
        if in_origin and line.startswith("url ="):
            return line.split("=", 1)[1].strip()
    return None


def file_record(path: Path) -> dict[str, Any]:
    exists = path.exists()
    return {
        "path": str(path),
        "exists": exists,
        "bytes": path.stat().st_size if exists else None,
        "mtime": path.stat().st_mtime if exists else None,
    }


def build_status(ares_root: Path) -> dict[str, Any]:
    build_root = ares_root / "build_msvc"
    core_lib = build_root / "ares" / "RelWithDebInfo" / "ares.lib"
    desktop_exe = build_root / "desktop-ui" / "rundir" / "ares.exe"
    link_smoke_exe = ROOT / "build" / "audio" / "ares-link-smoke-msvc" / "RelWithDebInfo" / "earthbound_ares_link_smoke.exe"
    audio_harness_exe = (
        ROOT
        / "build"
        / "audio"
        / "ares-audio-harness-msvc"
        / "RelWithDebInfo"
        / "earthbound_ares_audio_harness.exe"
    )
    commit = run_git(ares_root, "rev-parse", "HEAD") or read_git_head(ares_root)
    remote_origin = run_git(ares_root, "remote", "get-url", "origin") or read_git_remote(ares_root)
    ready = core_lib.exists() and desktop_exe.exists() and link_smoke_exe.exists() and audio_harness_exe.exists()
    return {
        "schema": "earthbound-decomp.ares-backend-prereq-status.v1",
        "ares_root": str(ares_root),
        "ares_root_exists": ares_root.exists(),
        "git": {
            "is_checkout": (ares_root / ".git").exists(),
            "remote_origin": remote_origin,
            "commit": commit,
            "short_commit": commit[:9] if commit else None,
            "status_short": run_git(ares_root, "status", "--short"),
        },
        "build": {
            "generator": "Visual Studio 17 2022",
            "preset": "windows-msvc",
            "build_dir": str(build_root),
            "core_target": "ares",
            "core_library": file_record(core_lib),
            "desktop_target": "desktop-ui",
            "desktop_executable": file_record(desktop_exe),
        },
        "backend_contract": {
            "job_runner": "tools/run_audio_backend_job.py",
            "batch_runner": "tools/run_audio_backend_batch.py",
            "expected_external_shape": 'python <harness> --job "{job}" --result "{result}"',
            "native_ares_mode": "python tools/run_audio_backend_job.py ares-track-046-onett --mode native-ares",
        },
        "link_smoke": {
            "source": "tools/ares_link_smoke",
            "build_dir": str(ROOT / "build" / "audio" / "ares-link-smoke-msvc"),
            "executable": file_record(link_smoke_exe),
        },
        "audio_harness": {
            "source": "tools/ares_audio_harness",
            "build_dir": str(ROOT / "build" / "audio" / "ares-audio-harness-msvc"),
            "executable": file_record(audio_harness_exe),
            "current_capability": "validates and imports APU RAM seeds into ares::SuperFamicom::dsp.apuram; does not render PCM yet",
        },
        "status": "ready" if ready else "missing_build_outputs",
    }


def main() -> int:
    args = parse_args()
    status = build_status(Path(args.ares_root))
    output_path = Path(args.json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    print(
        "ares backend prerequisite: "
        f"{status['status']} at {status['ares_root']} "
        f"({status['git']['short_commit'] or 'no git revision'})"
    )
    print(f"Wrote {output_path}")
    return 0 if status["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
