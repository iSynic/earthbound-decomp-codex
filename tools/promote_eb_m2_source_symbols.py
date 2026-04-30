from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CROSSWALK = Path("manifests") / "eb-m2-name-crosswalk.json"


def load_promotions(crosswalk: Path, bank: str) -> dict[str, dict[str, Any]]:
    payload = json.loads(crosswalk.read_text(encoding="utf-8"))
    promotions: dict[str, dict[str, Any]] = {}
    for entry in payload["entries"]:
        if entry["bank"] != bank:
            continue
        if entry.get("recommended_action") != "promote":
            continue
        new_symbol = entry.get("new_symbol") or entry.get("canonical_name")
        if not new_symbol or str(new_symbol).startswith("UNKNOWN_"):
            continue
        old_symbols = sorted(
            {
                str(name)
                for name in entry.get("local_names", [])
                if str(name).startswith(entry["address"] + "_")
            }
        )
        if not old_symbols:
            continue
        promotions[entry["address"]] = {
            "new_symbol": str(new_symbol),
            "primary_old_symbol": str(entry.get("old_symbol") or old_symbols[0]),
            "old_symbols": old_symbols,
        }
    return promotions


def replacement_regex(old_symbols: list[str]) -> re.Pattern[str]:
    return re.compile(r"\b(" + "|".join(re.escape(symbol) for symbol in sorted(old_symbols, key=len, reverse=True)) + r")\b")


def is_terminal_boundary_alias(lines: list[str], index: int, address: str) -> bool:
    """Return true when a source file only exposes an end label for this address."""

    bank = address[:2]
    offset = address[2:]
    range_pattern = re.compile(rf";\s*-\s*{bank}:([0-9A-F]{{4}})\.\.{bank}:{offset}\b")
    terminal_range = False
    for line in lines[:index]:
        match = range_pattern.search(line)
        if match and match.group(1) != offset:
            terminal_range = True
            break
    if not terminal_range:
        return False

    for previous in lines[:index]:
        previous_stripped = previous.strip()
        if not previous_stripped or previous_stripped.startswith(";"):
            continue
        if previous_stripped.startswith("org ") or previous_stripped == "hirom":
            continue
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*=", previous_stripped):
            continue
        return False
    return True


def rewrite_text(text: str, promotions: dict[str, dict[str, Any]]) -> tuple[str, int]:
    old_to_new: dict[str, str] = {}
    old_to_entry: dict[str, dict[str, Any]] = {}
    new_to_entry: dict[str, dict[str, Any]] = {}
    new_symbols = {str(entry["new_symbol"]) for entry in promotions.values()}
    for entry in promotions.values():
        new_to_entry[str(entry["new_symbol"])] = entry
        for old in entry["old_symbols"]:
            old_to_new[old] = entry["new_symbol"]
            old_to_entry[old] = entry
    if not old_to_new:
        return text, 0

    pattern = replacement_regex(list(old_to_new))
    changed = 0
    out_lines: list[str] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped.endswith(":") and stripped[:-1] in new_to_entry:
            new_symbol = stripped[:-1]
            entry = new_to_entry[new_symbol]
            indent = line[: len(line) - len(line.lstrip())]
            alias_lines: list[str] = []
            alias_names: set[str] = set()
            scan = index + 1
            while scan < len(lines):
                scan_stripped = lines[scan].strip()
                alias_match = re.match(
                    r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*" + re.escape(new_symbol) + r"\s*$",
                    scan_stripped,
                )
                if not alias_match:
                    break
                alias_name = alias_match.group(1)
                if alias_name != new_symbol:
                    alias_names.add(alias_name)
                    alias_lines.append(lines[scan])
                scan += 1
            if scan > index + 1:
                primary = entry.get("primary_old_symbol")
                previous_has_bytes = False
                for previous in reversed(lines[max(0, index - 8) : index]):
                    previous_stripped = previous.strip()
                    if not previous_stripped or previous_stripped.startswith(";"):
                        continue
                    if previous_stripped.startswith("org ") or previous_stripped == "hirom":
                        continue
                    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*=", previous_stripped):
                        continue
                    previous_has_bytes = True
                    break
                if primary in alias_names and not previous_has_bytes:
                    out_lines.append(line)
                    for alias in entry["old_symbols"]:
                        out_lines.append(f"{indent}{alias} = {new_symbol}")
                else:
                    for alias_line in alias_lines:
                        out_lines.append(alias_line)
                changed += 1
                index = scan
                continue
            if index + 1 < len(lines):
                next_stripped = lines[index + 1].strip()
                if next_stripped == f"{new_symbol} = {new_symbol}":
                    out_lines.append(line)
                    for alias in entry["old_symbols"]:
                        out_lines.append(f"{indent}{alias} = {new_symbol}")
                    changed += 1
                    index += 2
                    continue

        bare_alias_match = re.match(r"^([A-F0-9]{6}_[A-Za-z0-9_]+)\s*=\s*([A-Za-z_][A-Za-z0-9_]*)\s*$", stripped)
        if bare_alias_match and bare_alias_match.group(1) in old_to_entry:
            first_alias, new_symbol = bare_alias_match.groups()
            entry = old_to_entry[first_alias]
            if new_symbol == entry.get("new_symbol"):
                indent = line[: len(line) - len(line.lstrip())]
                alias_lines: list[str] = []
                alias_names: set[str] = set()
                scan = index
                while scan < len(lines):
                    scan_stripped = lines[scan].strip()
                    alias_match = re.match(
                        r"^([A-F0-9]{6}_[A-Za-z0-9_]+)\s*=\s*" + re.escape(new_symbol) + r"\s*$",
                        scan_stripped,
                    )
                    if not alias_match:
                        break
                    alias_names.add(alias_match.group(1))
                    alias_lines.append(lines[scan])
                    scan += 1
                previous_has_bytes = False
                for previous in reversed(lines[max(0, index - 8) : index]):
                    previous_stripped = previous.strip()
                    if not previous_stripped or previous_stripped.startswith(";"):
                        continue
                    if previous_stripped.startswith("org ") or previous_stripped == "hirom":
                        continue
                    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*=", previous_stripped):
                        continue
                    previous_has_bytes = True
                    break
                primary = entry.get("primary_old_symbol")
                terminal_boundary = is_terminal_boundary_alias(lines, index, first_alias[:6])
                if terminal_boundary:
                    out_lines.extend(alias_lines)
                elif primary in alias_names and (not previous_has_bytes or len(alias_names) == 1):
                    out_lines.append(f"{indent}{new_symbol}:")
                    for alias in entry["old_symbols"]:
                        out_lines.append(f"{indent}{alias} = {new_symbol}")
                else:
                    out_lines.extend(alias_lines)
                changed += 1
                index = scan
                continue

        if stripped.endswith(":") and stripped[:-1] in new_symbols and index + 1 < len(lines):
            next_stripped = lines[index + 1].strip()
            alias_match = re.match(r"^([A-F0-9]{6}_[A-Za-z0-9_]+)\s*=\s*" + re.escape(stripped[:-1]) + r"\s*$", next_stripped)
            if alias_match:
                alias = alias_match.group(1)
                entry = old_to_entry.get(alias)
                if entry and alias != entry.get("primary_old_symbol"):
                    changed += 1
                    index += 1
                    continue

        if stripped.endswith(":") and stripped[:-1] in old_to_new:
            old = stripped[:-1]
            entry = old_to_entry[old]
            new_symbol = entry["new_symbol"]
            indent = line[: len(line) - len(line.lstrip())]
            if is_terminal_boundary_alias(lines, index, old[:6]):
                out_lines.append(f"{indent}{old} = {new_symbol}")
            elif old == entry.get("primary_old_symbol"):
                out_lines.append(f"{indent}{new_symbol}:")
                for alias in entry["old_symbols"]:
                    out_lines.append(f"{indent}{alias} = {new_symbol}")
            else:
                out_lines.append(f"{indent}{old} = {new_symbol}")
            changed += 1
            index += 1
            continue

        alias_lhs_match = re.match(r"^(\s*)([A-F0-9]{6}_[A-Za-z0-9_]+)(\s*=\s*)(.*)$", line)
        if alias_lhs_match and alias_lhs_match.group(2) in old_to_new:
            prefix, lhs, middle, rhs = alias_lhs_match.groups()
            new_rhs = pattern.sub(lambda match: old_to_new[match.group(1)], rhs)
            new_line = f"{prefix}{lhs}{middle}{new_rhs}"
            if new_line != line:
                changed += 1
            out_lines.append(new_line)
            index += 1
            continue

        def replace(match: re.Match[str]) -> str:
            return old_to_new[match.group(1)]

        new_line = pattern.sub(replace, line)
        if new_line != line:
            changed += 1
        out_lines.append(new_line)
        index += 1

    suffix = "\n" if text.endswith("\n") else ""
    return "\n".join(out_lines) + suffix, changed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Promote reviewed EB-M2 names into source symbols while preserving old address-prefixed aliases."
    )
    parser.add_argument("--bank", required=True, help="Canonical bank, e.g. C0.")
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--src-root", type=Path, default=Path("src"))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bank = args.bank.upper()
    crosswalk = args.crosswalk if args.crosswalk.is_absolute() else ROOT / args.crosswalk
    src_root = args.src_root if args.src_root.is_absolute() else ROOT / args.src_root
    promotions = load_promotions(crosswalk, bank)
    if not promotions:
        print(f"No ready promotions for {bank}.")
        return 0

    bank_root = src_root / bank.lower()
    paths = sorted(bank_root.rglob("*.asm"))
    touched: list[tuple[Path, int]] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        new_text, changes = rewrite_text(text, promotions)
        if changes == 0:
            continue
        touched.append((path, changes))
        if not args.dry_run:
            path.write_text(new_text, encoding="utf-8")

    action = "Would update" if args.dry_run else "Updated"
    print(f"{action} {len(touched)} file(s) for {bank} with {len(promotions)} promotion address(es).")
    for path, changes in touched[:80]:
        print(f"- {path.relative_to(ROOT).as_posix()} ({changes} changed line(s))")
    if len(touched) > 80:
        print(f"... {len(touched) - 80} additional files omitted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
