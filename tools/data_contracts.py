from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST = Path(__file__).resolve().parent.parent / "build" / "data-contracts-c0-c4.json"
ALLOWED_WRAM_ROOT_OVERLAPS = {
    frozenset(("GAME_STATE", "PARTY_CHARACTERS")): "documented local saveblock/party live-state overlap",
}


@dataclass(frozen=True)
class CpuAddress:
    bank: int
    address: int

    @property
    def long(self) -> int:
        return (self.bank << 16) | self.address

    @property
    def wram_offset(self) -> int | None:
        if self.bank == 0x7E:
            return self.address
        if self.bank == 0x7F:
            return 0x10000 + self.address
        return None

    def add(self, offset: int) -> "CpuAddress":
        return CpuAddress(self.bank, (self.address + offset) & 0xFFFF)

    def __str__(self) -> str:
        return f"{self.bank:02X}:{self.address:04X}"


@dataclass(frozen=True)
class ContractField:
    name: str
    offset: int
    size: int
    count: int
    note: str
    element_names: tuple[str, ...]

    @property
    def total_size(self) -> int:
        return self.size * self.count

    @property
    def end(self) -> int:
        return self.offset + self.total_size

    def contains(self, relative_offset: int) -> bool:
        return self.offset <= relative_offset < self.end

    def label_at(self, relative_offset: int) -> str:
        within = relative_offset - self.offset
        if self.count == 1:
            if within == 0:
                return self.name
            return f"{self.name}+0x{within:X}"
        index = within // self.size
        label = f"{self.name}[{index}]"
        if 0 <= index < len(self.element_names):
            label += f" ({self.element_names[index]})"
        element_offset = within % self.size
        if element_offset:
            label += f"+0x{element_offset:X}"
        return label


@dataclass(frozen=True)
class DataContract:
    id: str
    domain: str
    address: CpuAddress
    stride: int
    count: int | None
    struct_name: str
    confidence: str
    note: str
    evidence: tuple[str, ...]
    fields: tuple[ContractField, ...]

    @property
    def normalized_id(self) -> str:
        return normalize_name(self.id)

    @property
    def limit(self) -> int | None:
        if self.count is None:
            return None
        return self.address.long + self.stride * self.count

    def contains_address(self, address: CpuAddress) -> bool:
        if self.address.bank != address.bank:
            return False
        if address.long < self.address.long:
            return False
        if self.limit is None:
            return True
        return address.long < self.limit

    def record_index_for(self, address: CpuAddress) -> int:
        return (address.long - self.address.long) // self.stride

    def record_offset_for(self, address: CpuAddress) -> int:
        return (address.long - self.address.long) % self.stride

    def address_for(self, record_index: int = 0, offset: int = 0) -> CpuAddress:
        return self.address.add(record_index * self.stride + offset)

    def field_named(self, name: str) -> ContractField | None:
        normalized = normalize_name(name)
        for field in self.fields:
            if normalize_name(field.name) == normalized:
                return field
        return None

    def field_at(self, offset: int) -> ContractField | None:
        for field in self.fields:
            if field.contains(offset):
                return field
        return None


@dataclass(frozen=True)
class ContractLookup:
    contract: DataContract
    address: CpuAddress
    record_index: int
    record_base: CpuAddress
    record_offset: int
    field: ContractField | None


class ContractManifest:
    def __init__(self, data: dict[str, Any], path: Path):
        self.data = data
        self.path = path
        self.contracts = tuple(parse_contract(item) for item in data.get("contracts", []))
        self.by_id = {contract.normalized_id: contract for contract in self.contracts}

    def get(self, contract_id: str) -> DataContract | None:
        return self.by_id.get(normalize_name(contract_id))

    def require(self, contract_id: str) -> DataContract:
        contract = self.get(contract_id)
        if contract is None:
            raise KeyError(f"unknown contract id: {contract_id}")
        return contract

    def matches_for_address(self, address: CpuAddress) -> list[ContractLookup]:
        matches: list[ContractLookup] = []
        for contract in self.contracts:
            if not contract.contains_address(address):
                continue
            record_index = contract.record_index_for(address)
            record_offset = contract.record_offset_for(address)
            matches.append(
                ContractLookup(
                    contract=contract,
                    address=address,
                    record_index=record_index,
                    record_base=contract.address_for(record_index),
                    record_offset=record_offset,
                    field=contract.field_at(record_offset),
                )
            )
        return sorted(matches, key=match_sort_key)

    def validate(self) -> list[str]:
        errors: list[str] = []
        seen: dict[str, str] = {}
        for contract in self.contracts:
            norm = contract.normalized_id
            if norm in seen:
                errors.append(f"duplicate contract id: {seen[norm]} and {contract.id}")
            seen[norm] = contract.id
            if contract.stride <= 0:
                errors.append(f"{contract.id}: stride must be positive")
            if contract.count is not None and contract.count <= 0:
                errors.append(f"{contract.id}: count must be positive when present")
            for field in contract.fields:
                if field.offset < 0:
                    errors.append(f"{contract.id}.{field.name}: negative offset")
                if field.size <= 0:
                    errors.append(f"{contract.id}.{field.name}: size must be positive")
                if field.count <= 0:
                    errors.append(f"{contract.id}.{field.name}: count must be positive")
                if field.end > contract.stride:
                    errors.append(
                        f"{contract.id}.{field.name}: field ends at 0x{field.end:X}, "
                        f"past stride 0x{contract.stride:X}"
                    )

        roots = [contract for contract in self.contracts if contract.domain == "wram-root" and contract.count]
        for left_index, left in enumerate(roots):
            assert left.limit is not None
            for right in roots[left_index + 1 :]:
                assert right.limit is not None
                if left.address.bank != right.address.bank:
                    continue
                if left.address.long < right.limit and right.address.long < left.limit:
                    overlap_key = frozenset((left.id, right.id))
                    if overlap_key in ALLOWED_WRAM_ROOT_OVERLAPS:
                        continue
                    errors.append(
                        f"wram-root overlap: {left.id} {left.address}-{left.address.add(left.stride * left.count - 1)} "
                        f"and {right.id} {right.address}-{right.address.add(right.stride * right.count - 1)}"
                    )
        return errors


def match_sort_key(match: ContractLookup) -> tuple[int, int, str]:
    contract = match.contract
    exact_base = 0 if match.address.long == contract.address.long else 1
    overlays_first = 0 if contract.domain == "wram-overlay" else 1
    finite_first = 0 if contract.count is not None else 1
    return (exact_base, overlays_first, finite_first, contract.id)


def normalize_name(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def parse_cpu_address(text: str) -> CpuAddress:
    candidate = text.strip().upper()
    if candidate.startswith("$"):
        return CpuAddress(0x7E, int(candidate[1:], 16))
    if candidate.startswith("0X"):
        return CpuAddress(0x7E, int(candidate, 16))
    if ":" in candidate:
        bank_text, addr_text = candidate.split(":", 1)
        return CpuAddress(int(bank_text, 16), int(addr_text, 16))
    if re.fullmatch(r"[0-9A-F]{6}", candidate):
        return CpuAddress(int(candidate[:2], 16), int(candidate[2:], 16))
    if re.fullmatch(r"[0-9A-F]{1,4}", candidate):
        return CpuAddress(0x7E, int(candidate, 16))
    raise ValueError(f"cannot parse address: {text}")


def parse_address_expression(text: str) -> CpuAddress:
    parts = [part.strip() for part in text.split("+") if part.strip()]
    if not parts:
        raise ValueError("empty address expression")
    address = parse_cpu_address(parts[0])
    offset = sum(parse_int(part) for part in parts[1:])
    return address.add(offset)


def parse_address_string(text: str) -> CpuAddress:
    return parse_cpu_address(text)


def parse_int(text: str) -> int:
    candidate = text.strip()
    if candidate.startswith("$"):
        return int(candidate[1:], 16)
    return int(candidate, 0)


def parse_field(data: dict[str, Any]) -> ContractField:
    return ContractField(
        name=str(data["name"]),
        offset=int(data["offset"]),
        size=int(data["size"]),
        count=int(data.get("count", 1)),
        note=str(data.get("note", "")),
        element_names=tuple(str(item) for item in data.get("element_names", ())),
    )


def parse_contract(data: dict[str, Any]) -> DataContract:
    return DataContract(
        id=str(data["id"]),
        domain=str(data["domain"]),
        address=parse_address_string(str(data["address"])),
        stride=int(data["stride"]),
        count=int(data["count"]) if "count" in data else None,
        struct_name=str(data["struct"]),
        confidence=str(data["confidence"]),
        note=str(data.get("note", "")),
        evidence=tuple(str(item) for item in data.get("evidence", ())),
        fields=tuple(parse_field(item) for item in data.get("fields", ())),
    )


def load_manifest(path: str | Path | None = None) -> ContractManifest:
    manifest_path = Path(path) if path is not None else DEFAULT_MANIFEST
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return ContractManifest(data, manifest_path)
