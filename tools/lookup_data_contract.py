from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_contracts import ContractLookup, DataContract, load_manifest, parse_address_expression, parse_int


INDEXED_RE = re.compile(
    r"^(?P<contract>[A-Za-z0-9_]+)(?:\[(?P<index>[^]]+)\])?(?:\.(?P<field>[A-Za-z0-9_]+))?(?:\+(?P<offset>.+))?$"
)


def format_lookup(match: ContractLookup) -> list[str]:
    lines = [
        f"  contract: {match.contract.id} ({match.contract.domain}, {match.contract.struct_name})",
        f"  address:  {match.address}",
        f"  record:   {match.record_index} @ {match.record_base}",
        f"  offset:   +0x{match.record_offset:X}",
    ]
    if match.field is not None:
        lines.append(f"  field:    {match.field.label_at(match.record_offset)}")
        lines.append(f"  span:     +0x{match.field.offset:X}..+0x{match.field.end - 1:X}")
        if match.field.note:
            lines.append(f"  note:     {match.field.note}")
    else:
        lines.append("  field:    <no named field at this offset>")
    return lines


def lookup_contract_term(manifest, text: str) -> list[ContractLookup]:
    match = INDEXED_RE.match(text.strip())
    if not match:
        raise ValueError(f"cannot parse contract term: {text}")

    contract = manifest.get(match.group("contract"))
    if contract is None:
        return []

    index = parse_int(match.group("index")) if match.group("index") is not None else 0
    offset = parse_int(match.group("offset")) if match.group("offset") is not None else 0
    if index < 0:
        raise ValueError("record index must be non-negative")
    if contract.count is not None and index >= contract.count:
        raise ValueError(f"{contract.id}[{index}] is outside count {contract.count}")

    field_name = match.group("field")
    field = None
    if field_name is not None:
        field = contract.field_named(field_name)
        if field is None:
            raise ValueError(f"{contract.id} has no field named {field_name}")
        offset += field.offset

    if offset < 0 or offset >= contract.stride:
        raise ValueError(f"{contract.id}[{index}] offset 0x{offset:X} is outside stride 0x{contract.stride:X}")

    address = contract.address_for(index, offset)
    return [
        ContractLookup(
            contract=contract,
            address=address,
            record_index=index,
            record_base=contract.address_for(index),
            record_offset=offset,
            field=field or contract.field_at(offset),
        )
    ]


def lookup_address_term(manifest, text: str) -> list[ContractLookup]:
    address = parse_address_expression(text)
    return manifest.matches_for_address(address)


def lookup_term(manifest, text: str) -> list[ContractLookup]:
    try:
        contract_matches = lookup_contract_term(manifest, text)
    except ValueError:
        contract_matches = []
    if contract_matches:
        return contract_matches
    return lookup_address_term(manifest, text)


def print_contract(contract: DataContract) -> None:
    count = contract.count if contract.count is not None else "unknown"
    print(f"{contract.id}")
    print(f"  domain:     {contract.domain}")
    print(f"  address:    {contract.address}")
    print(f"  stride:     0x{contract.stride:X} ({contract.stride})")
    print(f"  count:      {count}")
    print(f"  struct:     {contract.struct_name}")
    print(f"  confidence: {contract.confidence}")
    print(f"  fields:     {len(contract.fields)}")
    if contract.note:
        print(f"  note:       {contract.note}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Look up C0-C2 data-contract roots, records, addresses, and fields."
    )
    parser.add_argument("query", nargs="*", help="address or contract term")
    parser.add_argument("--manifest", default=None, help="contract manifest path")
    parser.add_argument("--list", action="store_true", help="list known contracts")
    parser.add_argument("--validate", action="store_true", help="validate the manifest and exit")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    manifest = load_manifest(args.manifest)

    if args.validate:
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

    if args.list:
        print(f"Manifest: {manifest.path}")
        print()
        for contract in manifest.contracts:
            print_contract(contract)
            print()
        return 0

    if not args.query:
        parser.error("provide at least one query, or use --list/--validate")

    print(f"Manifest: {manifest.path}")
    print()
    for query in args.query:
        print(f"Query: {query}")
        try:
            matches = lookup_term(manifest, query)
        except Exception as exc:
            print(f"  error: {exc}")
            print()
            continue
        if not matches:
            print("  no matching contract")
            print()
            continue
        for index, match in enumerate(matches):
            if index:
                print("  ---")
            for line in format_lookup(match):
                print(line)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
