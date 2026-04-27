from __future__ import annotations

import argparse
from dataclasses import dataclass


STATUS_GROUP_NAMES = (
    'PERSISTENT_EASYHEAL',
    'PERSISTENT_HARDHEAL',
    'TEMPORARY',
    'STRANGENESS',
    'CONCENTRATION',
    'HOMESICKNESS',
    'SHIELD',
)

EQUIPMENT_SLOT_NAMES = (
    'weapon',
    'body',
    'arms',
    'other',
)


@dataclass(frozen=True)
class FieldSpec:
    name: str
    offset: int
    size: int
    count: int = 1
    note: str = ''
    element_names: tuple[str, ...] = ()

    @property
    def total_size(self) -> int:
        return self.size * self.count

    def contains(self, relative_offset: int) -> bool:
        return self.offset <= relative_offset < self.offset + self.total_size

    def describe(self, relative_offset: int) -> tuple[str, str]:
        within = relative_offset - self.offset
        if self.count == 1:
            suffix = '' if within == 0 else f' +0x{within:X}'
            return f'{self.name}{suffix}', self.note
        index = within // self.size
        item_name = f'{self.name}[{index}]'
        if 0 <= index < len(self.element_names):
            item_name += f' ({self.element_names[index]})'
        element_offset = within % self.size
        if element_offset:
            item_name += f' +0x{element_offset:X}'
        return item_name, self.note


@dataclass(frozen=True)
class RootSpec:
    name: str
    base: int
    stride: int
    count: int
    struct_name: str
    note: str
    fields: tuple[FieldSpec, ...]

    @property
    def limit(self) -> int:
        return self.base + self.stride * self.count

    def contains(self, address: int) -> bool:
        return self.base <= address < self.limit


@dataclass(frozen=True)
class Match:
    root: RootSpec
    address: int
    record_index: int
    record_base: int
    record_offset: int
    field: FieldSpec | None


GAME_STATE_FIELDS = (
    FieldSpec('mother2_playername', 0x000, 1, 12, '12-byte Mother 2 carryover name buffer'),
    FieldSpec('earthbound_playername', 0x00C, 1, 24, '24-byte EarthBound player-name buffer'),
    FieldSpec('pet_name', 0x024, 1, 6, '6-byte pet-name buffer'),
    FieldSpec('favourite_food', 0x02A, 1, 6, '6-byte favourite-food buffer'),
    FieldSpec('favourite_thing', 0x030, 1, 12, '12-byte favourite-thing / PSI naming buffer'),
    FieldSpec('money_carried', 0x03C, 4, note='party money carried'),
    FieldSpec('bank_balance', 0x040, 4, note='bank account balance'),
    FieldSpec('party_psi', 0x044, 1, note='party PSI latch byte'),
    FieldSpec('party_npc_1', 0x045, 1, note='party NPC slot 1 id'),
    FieldSpec('party_npc_2', 0x046, 1, note='party NPC slot 2 id'),
    FieldSpec('party_status', 0x04B, 1, note='party status byte'),
    FieldSpec('wallet_backup', 0x052, 4, note='wallet backup dword'),
    FieldSpec('escargo_express_items', 0x056, 1, 36, note='Escargo Express stored-item queue'),
    FieldSpec('party_members', 0x07A, 1, 6, note='party member ids'),
    FieldSpec('leader_x_coord', 0x082, 2, note='leader X coordinate'),
    FieldSpec('leader_y_coord', 0x086, 2, note='leader Y coordinate'),
    FieldSpec('leader_direction', 0x08A, 2, note='leader facing direction'),
    FieldSpec('trodden_tile_type', 0x08C, 2, note='trodden tile type'),
    FieldSpec('walking_style', 0x08E, 2, note='walking style'),
    FieldSpec('current_party_members', 0x094, 2, note='current party-members word'),
    FieldSpec('party_count', 0x0AE, 1, note='party count'),
    FieldSpec('player_controlled_party_count', 0x0AF, 1, note='player-controlled party count'),
    FieldSpec('text_speed', 0x0C1, 1, note='selected text speed'),
    FieldSpec('sound_setting', 0x0C2, 1, note='sound setting'),
    FieldSpec('timer', 0x1D4, 4, note='global timer dword'),
    FieldSpec('text_flavour', 0x1D8, 1, note='text flavour byte'),
)

CHAR_STRUCT_FIELDS = (
    FieldSpec('name', 0x00, 1, 5, '5-byte party member name buffer'),
    FieldSpec('level', 0x05, 1, note='level'),
    FieldSpec('exp', 0x06, 4, note='experience dword'),
    FieldSpec('max_hp', 0x0A, 2, note='max HP'),
    FieldSpec('max_pp', 0x0C, 2, note='max PP'),
    FieldSpec('afflictions', 0x0E, 1, 7, 'char_struct affliction-group bytes', STATUS_GROUP_NAMES),
    FieldSpec('offense', 0x15, 1, note='display-facing offense'),
    FieldSpec('defense', 0x16, 1, note='display-facing defense'),
    FieldSpec('speed', 0x17, 1, note='display-facing speed'),
    FieldSpec('guts', 0x18, 1, note='display-facing guts'),
    FieldSpec('luck', 0x19, 1, note='display-facing luck'),
    FieldSpec('vitality', 0x1A, 1, note='display-facing vitality'),
    FieldSpec('iq', 0x1B, 1, note='display-facing IQ'),
    FieldSpec('base_offense', 0x1C, 1, note='base offense before equipment refresh'),
    FieldSpec('base_defense', 0x1D, 1, note='base defense before equipment refresh'),
    FieldSpec('base_speed', 0x1E, 1, note='base speed'),
    FieldSpec('base_guts', 0x1F, 1, note='base guts'),
    FieldSpec('base_luck', 0x20, 1, note='base luck'),
    FieldSpec('base_vitality', 0x21, 1, note='base vitality'),
    FieldSpec('base_iq', 0x22, 1, note='base IQ'),
    FieldSpec('items', 0x23, 1, 14, note='inventory item ids'),
    FieldSpec('equipment', 0x31, 1, 4, 'equipped item ids by slot family', EQUIPMENT_SLOT_NAMES),
    FieldSpec('position_index', 0x3D, 2, note='position index word'),
    FieldSpec('current_hp_fraction', 0x43, 2, note='HP rolling fraction'),
    FieldSpec('current_hp', 0x45, 2, note='current HP'),
    FieldSpec('current_hp_target', 0x47, 2, note='HP target'),
    FieldSpec('current_pp_fraction', 0x49, 2, note='PP rolling fraction'),
    FieldSpec('current_pp', 0x4B, 2, note='current PP'),
    FieldSpec('current_pp_target', 0x4D, 2, note='PP target'),
    FieldSpec('hp_pp_window_options', 0x4F, 2, note='HP/PP window options'),
    FieldSpec('miss_rate', 0x51, 1, note='miss-rate byte'),
    FieldSpec('fire_resist', 0x52, 1, note='fire resistance'),
    FieldSpec('freeze_resist', 0x53, 1, note='freeze resistance'),
    FieldSpec('flash_resist', 0x54, 1, note='flash resistance'),
    FieldSpec('paralysis_resist', 0x55, 1, note='paralysis resistance'),
    FieldSpec('hypnosis_brainshock_resist', 0x56, 1, note='hypnosis/brainshock resistance'),
    FieldSpec('boosted_speed', 0x57, 1, note='boosted speed adder'),
    FieldSpec('boosted_guts', 0x58, 1, note='boosted guts adder'),
    FieldSpec('boosted_vitality', 0x59, 1, note='boosted vitality adder'),
    FieldSpec('boosted_iq', 0x5A, 1, note='boosted IQ adder'),
    FieldSpec('boosted_luck', 0x5B, 1, note='boosted luck adder'),
)

BATTLER_FIELDS = (
    FieldSpec('id', 0x00, 2, note='battler id'),
    FieldSpec('sprite', 0x02, 1, note='sprite id'),
    FieldSpec('current_action', 0x04, 2, note='current action id'),
    FieldSpec('action_order_var', 0x06, 1, note='action-order variable'),
    FieldSpec('action_item_slot', 0x07, 1, note='selected item slot'),
    FieldSpec('current_action_argument', 0x08, 1, note='current action argument'),
    FieldSpec('action_targetting', 0x09, 1, note='action targeting mode'),
    FieldSpec('current_target', 0x0A, 1, note='current target id'),
    FieldSpec('the_flag', 0x0B, 1, note='enemy data the_flag copy'),
    FieldSpec('consciousness', 0x0C, 1, note='consciousness gate byte'),
    FieldSpec('has_taken_turn', 0x0D, 1, note='turn-taken latch'),
    FieldSpec('ally_or_enemy', 0x0E, 1, note='ally-or-enemy side byte'),
    FieldSpec('npc_id', 0x0F, 1, note='NPC or enemy id'),
    FieldSpec('row', 0x10, 1, note='front/back row byte'),
    FieldSpec('hp', 0x11, 2, note='battle HP'),
    FieldSpec('hp_target', 0x13, 2, note='battle HP target'),
    FieldSpec('hp_max', 0x15, 2, note='battle max HP'),
    FieldSpec('pp', 0x17, 2, note='battle PP'),
    FieldSpec('pp_target', 0x19, 2, note='battle PP target'),
    FieldSpec('pp_max', 0x1B, 2, note='battle max PP'),
    FieldSpec('afflictions', 0x1D, 1, 7, 'battler affliction-group bytes', STATUS_GROUP_NAMES),
    FieldSpec('guarding', 0x24, 1, note='guarding flag'),
    FieldSpec('shield_hp', 0x25, 1, note='shield HP'),
    FieldSpec('offense', 0x26, 2, note='battle offense'),
    FieldSpec('defense', 0x28, 2, note='battle defense'),
    FieldSpec('speed', 0x2A, 2, note='battle speed'),
    FieldSpec('guts', 0x2C, 2, note='battle guts'),
    FieldSpec('luck', 0x2E, 2, note='battle luck'),
    FieldSpec('vitality', 0x30, 1, note='battle vitality'),
    FieldSpec('iq', 0x31, 1, note='battle IQ'),
    FieldSpec('base_offense', 0x32, 1, note='base offense'),
    FieldSpec('base_defense', 0x33, 1, note='base defense'),
    FieldSpec('base_speed', 0x34, 1, note='base speed'),
    FieldSpec('base_guts', 0x35, 1, note='base guts'),
    FieldSpec('base_luck', 0x36, 1, note='base luck'),
    FieldSpec('paralysis_resist', 0x37, 1, note='paralysis resistance'),
    FieldSpec('freeze_resist', 0x38, 1, note='freeze resistance'),
    FieldSpec('flash_resist', 0x39, 1, note='flash resistance'),
    FieldSpec('fire_resist', 0x3A, 1, note='fire resistance'),
    FieldSpec('brainshock_resist', 0x3B, 1, note='brainshock resistance'),
    FieldSpec('hypnosis_resist', 0x3C, 1, note='hypnosis resistance'),
    FieldSpec('money', 0x3D, 2, note='money drop'),
    FieldSpec('exp', 0x3F, 4, note='experience yield'),
    FieldSpec('vram_sprite_index', 0x43, 1, note='VRAM sprite index'),
    FieldSpec('sprite_x', 0x44, 1, note='battle sprite X'),
    FieldSpec('sprite_y', 0x45, 1, note='battle sprite Y'),
    FieldSpec('initiative', 0x46, 1, note='initiative byte'),
    FieldSpec('use_alt_spritemap', 0x4B, 1, note='alternate spritemap flag'),
    FieldSpec('id2', 0x4D, 1, note='secondary id byte'),
)

ROOTS = (
    RootSpec('GAME_STATE', 0x9801, 0x1D9, 1, 'game_state', 'saveblock game_state root from ebsrc ram.asm', GAME_STATE_FIELDS),
    RootSpec('PARTY_CHARACTERS', 0x99CE, 0x5F, 6, 'char_struct', 'party char_struct array from ebsrc ram.asm', CHAR_STRUCT_FIELDS),
    RootSpec('BATTLERS_TABLE', 0x9FAC, 0x4E, 32, 'battler', 'battler array from ebsrc ram.asm', BATTLER_FIELDS),
)

ROOT_LOOKUP = {}
for root in ROOTS:
    ROOT_LOOKUP[root.name.upper()] = root.base
    ROOT_LOOKUP[root.name.upper().replace('_', '')] = root.base


def parse_term(text: str) -> int:
    cleaned = text.strip().upper().replace('_', '')
    if not cleaned:
        raise argparse.ArgumentTypeError('empty address term')
    if cleaned in ROOT_LOOKUP:
        return ROOT_LOOKUP[cleaned]
    if cleaned.startswith('$'):
        return int(cleaned[1:], 16)
    if ':' in cleaned:
        bank_text, addr_text = cleaned.split(':', 1)
        bank = int(bank_text, 16)
        address = int(addr_text, 16)
        if bank == 0x7E:
            return address
        if bank == 0x7F:
            return 0x10000 + address
        raise argparse.ArgumentTypeError('only 7E:xxxx and 7F:xxxx WRAM addresses are supported')
    if cleaned.startswith('0X'):
        return int(cleaned, 16)
    if all(ch in '0123456789ABCDEF' for ch in cleaned):
        return int(cleaned, 16)
    return int(cleaned, 0)


def parse_query(text: str) -> tuple[str, int]:
    parts = [part for part in text.split('+') if part.strip()]
    if not parts:
        raise argparse.ArgumentTypeError('query must not be empty')
    total = sum(parse_term(part) for part in parts)
    return text, total


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Look up high-value WRAM addresses against curated ebsrc struct and RAM roots.'
    )
    parser.add_argument(
        'query',
        nargs='+',
        type=parse_query,
        help='WRAM address or expression like 99DC, 9FAC+1D, PARTY_CHARACTERS+0E, or 7E:99DC',
    )
    return parser


def find_field(root: RootSpec, record_offset: int) -> FieldSpec | None:
    for field in root.fields:
        if field.contains(record_offset):
            return field
    return None


def describe_match(match: Match) -> list[str]:
    root = match.root
    lines = [f'  root: {root.name} ${root.base:04X}  ({root.struct_name}, stride 0x{root.stride:X})']
    if root.count > 1:
        record_text = f'  record: {root.struct_name}[{match.record_index}] base ${match.record_base:04X}'
        if root.name == 'PARTY_CHARACTERS':
            record_text += f'  (slot {match.record_index + 1})'
        lines.append(record_text)
    lines.append(f'  root offset: +0x{match.address - root.base:X}')
    lines.append(f'  record offset: +0x{match.record_offset:X}')
    if match.field is None:
        lines.append('  field: <not covered by the current curated field map>')
        return lines
    field_name, note = match.field.describe(match.record_offset)
    span_end = match.field.offset + match.field.total_size - 1
    lines.append(f'  field: {field_name}')
    lines.append(f'  field span: +0x{match.field.offset:X}..+0x{span_end:X}')
    if note:
        lines.append(f'  note: {note}')
    return lines


def lookup_address(address: int) -> list[Match]:
    matches: list[Match] = []
    for root in ROOTS:
        if not root.contains(address):
            continue
        if root.count == 1:
            record_index = 0
            record_base = root.base
            record_offset = address - root.base
        else:
            record_index = (address - root.base) // root.stride
            record_base = root.base + record_index * root.stride
            record_offset = address - record_base
        matches.append(
            Match(
                root=root,
                address=address,
                record_index=record_index,
                record_base=record_base,
                record_offset=record_offset,
                field=find_field(root, record_offset),
            )
        )
    return matches


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    print('Reference roots: ebsrc include/structs.asm, src/bankconfig/common/ram.asm, include/constants/battle.asm')
    print()
    for raw_query, address in args.query:
        print(f'Query: {raw_query}')
        print(f'  absolute: ${address:04X}')
        matches = lookup_address(address)
        if not matches:
            print('  no match in the current curated roots (GAME_STATE, PARTY_CHARACTERS, BATTLERS_TABLE)')
            print()
            continue
        for match in matches:
            for line in describe_match(match):
                print(line)
        print()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

