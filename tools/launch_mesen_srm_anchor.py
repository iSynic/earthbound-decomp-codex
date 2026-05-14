#!/usr/bin/env python3
"""Install a cataloged SRM anchor and visibly launch EarthBound in Mesen."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import rom_tools


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = ROOT / "manifests" / "mesen-srm-anchor-catalog.json"
DEFAULT_MESEN = Path(r"F:\Mesen2\Mesen.exe")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--anchor-id", default="31-StonehBase", help="SRM anchor id from the catalog.")
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    parser.add_argument("--mesen", default=str(DEFAULT_MESEN))
    parser.add_argument("--rom", help="EarthBound ROM path. Defaults to tools.rom_tools discovery.")
    parser.add_argument("--backup", action="store_true", help="Back up any existing target SRM before replacement.")
    parser.add_argument("--dry-run", action="store_true", help="Install nothing and launch nothing; print planned paths.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_anchor(catalog: dict[str, Any], anchor_id: str) -> dict[str, Any]:
    for anchor in catalog.get("anchors", []):
        if anchor.get("anchor_id") == anchor_id:
            return anchor
    raise ValueError(f"anchor not found: {anchor_id}")


def repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    args = parse_args()
    mesen = Path(args.mesen)
    if not mesen.is_file():
        raise FileNotFoundError(f"Mesen executable not found: {mesen}")
    rom = rom_tools.find_rom(args.rom)
    catalog = load_json(Path(args.catalog))
    anchor = find_anchor(catalog, args.anchor_id)
    source_srm = repo_path(str(anchor["working_srm_path"]))
    if not source_srm.is_file():
        raise FileNotFoundError(f"anchor SRM missing; rebuild catalog first: {source_srm}")
    save_dir = mesen.parent / "Saves"
    save_dir.mkdir(parents=True, exist_ok=True)
    target_srm = save_dir / f"{rom.stem}.srm"
    expected_hash = str(anchor["srm_sha256"])
    source_hash = sha256(source_srm)
    if source_hash != expected_hash:
        raise ValueError(f"anchor SRM hash mismatch: expected {expected_hash}, got {source_hash}")
    print(f"anchor={anchor['anchor_id']} {anchor['archive_name']}")
    print(f"rom={rom}")
    print(f"mesen={mesen}")
    print(f"target_srm={target_srm}")
    print(f"source_srm_sha256={source_hash}")
    if args.dry_run:
        print("dry_run=true")
        print(f"launch_command={[str(mesen), str(rom)]}")
        return 0
    if args.backup and target_srm.is_file():
        backup = target_srm.with_suffix(f".{sha256(target_srm)}.srm")
        shutil.copy2(target_srm, backup)
        print(f"backup_srm={backup}")
    shutil.copy2(source_srm, target_srm)
    print(f"installed_srm_sha256={sha256(target_srm)}")
    subprocess.Popen([str(mesen), str(rom)], cwd=mesen.parent)
    print("launch=started")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
