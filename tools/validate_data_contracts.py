from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_contracts import load_manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the generated C0-C4 data contract manifest.")
    parser.add_argument("--manifest", default=None, help="contract manifest path")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    manifest = load_manifest(args.manifest)
    errors = manifest.validate()
    if errors:
        print(f"Manifest: {manifest.path}")
        print(f"Status: INVALID ({len(errors)} issue(s))")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"Manifest: {manifest.path}")
    print(f"Status: OK ({len(manifest.contracts)} contracts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
