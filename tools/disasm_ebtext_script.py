from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from extract_ebtext import US_EBTEXT_CHARMAP, parse_snes_address
from rom_tools import find_rom, hirom_to_file_offset, load_rom


@dataclass(frozen=True)
class ScriptLine:
    address: int
    size: int
    text: str


TOP_LEVEL_NAMES: dict[int, str] = {
    0x00: 'LINE_BREAK',
    0x01: 'START_NEW_LINE',
    0x02: 'END_BLOCK',
    0x03: 'HALT_WITH_PROMPT',
    0x04: 'SET_EVENT_FLAG',
    0x05: 'CLEAR_EVENT_FLAG',
    0x06: 'JUMP_IF_FLAG_SET',
    0x07: 'CHECK_EVENT_FLAG',
    0x08: 'CALL_TEXT',
    0x09: 'JUMP_MULTI',
    0x0A: 'JUMP',
    0x0B: 'TEST_IF_WORKMEM_TRUE',
    0x0C: 'TEST_IF_WORKMEM_FALSE',
    0x0D: 'COPY_TO_ARGMEM',
    0x0E: 'STORE_TO_ARGMEM',
    0x0F: 'INCREMENT_WORKMEM',
    0x10: 'PAUSE',
    0x11: 'CREATE_SELECTION_MENU',
    0x12: 'CLEAR_TEXT_LINE',
    0x13: 'HALT_WITHOUT_PROMPT',
    0x14: 'HALT_WITH_PROMPT_ALWAYS',
    0x15: 'COMPRESSED_BANK_1',
    0x16: 'COMPRESSED_BANK_2',
    0x17: 'COMPRESSED_BANK_3',
    0x18: 'WINDOW_MANAGEMENT',
    0x19: 'DATA_AND_SUBSTITUTION',
    0x1A: 'MENU_AND_SELECTION',
    0x1B: 'MEMORY_CONTEXT',
    0x1C: 'PRINT_DISPLAY',
    0x1D: 'INVENTORY_MONEY_CHECKS',
    0x1E: 'STAT_RECOVERY',
    0x1F: 'DEFERRED_CALLBACKS_AND_EVENTS',
}

SUBCOMMAND_NAMES: dict[int, dict[int, str]] = {
    0x18: {
        0x00: 'CLOSE_WINDOW',
        0x01: 'OPEN_WINDOW',
        0x02: 'SAVE_WINDOW_STATE',
        0x03: 'SWITCH_TO_WINDOW',
        0x04: 'CLOSE_ALL_WINDOWS',
        0x05: 'FORCE_TEXT_ALIGNMENT',
        0x06: 'CLEAR_WINDOW',
        0x07: 'CHECK_FOR_INEQUALITY',
        0x08: 'CREATE_WINDOW_SELECTION_MENU_UNCANCELLABLE',
        0x09: 'CREATE_WINDOW_SELECTION_MENU',
        0x0A: 'SHOW_WALLET_WINDOW',
        0x0D: 'PRINT_CHARACTER_STATUS_INFO',
    },
    0x19: {
        0x02: 'LOAD_STRING_TO_MEMORY',
        0x04: 'CLEAR_LOADED_STRINGS',
        0x05: 'INFLICT_STATUS',
        0x10: 'GET_CHARACTER_NUMBER',
        0x11: 'GET_CHARACTER_NAME_LETTER',
        0x16: 'GET_CHARACTER_STATUS',
        0x18: 'GET_EXPERIENCE_NEEDED_TO_LEVEL_UP',
        0x19: 'ADD_ITEM_ID_TO_WORK_MEMORY',
        0x14: 'ENUMERATE_ESCARGO_STORAGE_ITEM',
        0x1A: 'GET_ESCARGO_STORAGE_ITEM',
        0x1B: 'GET_WINDOW_LOADED_STRING_COUNT',
        0x1C: 'QUEUE_ITEM_FOR_DELIVERY_OR_PICKUP',
        0x1D: 'QUEUE_PICKUP_OR_DELIVERY_ITEM',
        0x1E: 'LOAD_POINTER_SUBSTITUTION',
        0x1F: 'LOAD_BYTE_SUBSTITUTION',
        0x20: 'UNKNOWN_CC_19_20',
        0x21: 'IS_ITEM_DRINK',
        0x22: 'GET_DIRECTION_OF_OBJECT_FROM_CHARACTER',
        0x23: 'GET_DIRECTION_OF_OBJECT_FROM_NPC',
        0x24: 'GET_DIRECTION_OF_OBJECT_FROM_SPRITE',
        0x25: 'IS_ITEM_CONDIMENT',
        0x26: 'SNAPSHOT_TRANSITION_LANDING_TARGET',
        0x27: 'GET_STATISTIC_VALUE',
        0x28: 'GET_STATISTIC_LETTER',
    },
    0x1A: {
        0x00: 'PARTY_MEMBER_SELECTION_MENU_UNCANCELLABLE',
        0x01: 'PARTY_MEMBER_SELECTION_MENU_UNCANCELLABLE',
        0x02: 'POSSIBLE_ALT_MENU_COMMAND_02',
        0x04: 'PARTY_MEMBER_SELECTION_MENU',
        0x05: 'SHOW_CHARACTER_INVENTORY',
        0x06: 'DISPLAY_SHOP_MENU',
        0x07: 'DISPLAY_ESCARGO_ITEM_MENU',
        0x08: 'SELECTION_MENU_UNCANCELLABLE',
        0x09: 'SELECTION_MENU',
        0x0A: 'OPEN_PHONE_MENU',
    },
    0x1B: {
        0x00: 'COPY_ACTIVE_MEMORY_TO_STORAGE',
        0x01: 'COPY_STORAGE_MEMORY_TO_ACTIVE',
        0x02: 'JUMP_IF_FALSE',
        0x03: 'JUMP_IF_TRUE',
        0x04: 'SWAP_WORKING_AND_ARG_MEMORY',
        0x05: 'COPY_ACTIVE_MEMORY_TO_WORKING_MEMORY',
        0x06: 'COPY_WORKING_MEMORY_TO_ACTIVE',
    },
    0x1C: {
        0x00: 'TEXT_COLOUR_EFFECTS',
        0x01: 'PRINT_STAT',
        0x02: 'PRINT_CHAR_NAME',
        0x03: 'PRINT_CHAR',
        0x04: 'OPEN_HP_PP_WINDOWS',
        0x05: 'PRINT_ITEM_NAME',
        0x06: 'PRINT_TELEPORT_DESTINATION_NAME',
        0x07: 'PRINT_HORIZONTAL_TEXT_STRING',
        0x08: 'PRINT_SPECIAL_GFX',
        0x0A: 'PRINT_NUMBER',
        0x0B: 'PRINT_MONEY_AMOUNT',
        0x0C: 'PRINT_VERTICAL_TEXT_STRING',
        0x0D: 'PRINT_ACTION_USER_NAME',
        0x0E: 'PRINT_ACTION_TARGET_NAME',
        0x0F: 'PRINT_ACTION_AMOUNT',
        0x11: 'MAKE_ROOM_TO_DISPLAY_TEXT_CHARACTER',
        0x12: 'PRINT_PSI_NAME',
        0x13: 'DISPLAY_PSI_ANIMATION',
        0x14: 'LOAD_SPECIAL',
        0x15: 'LOAD_SPECIAL_FOR_JUMP_MULTI',
    },
    0x1D: {
        0x00: 'GIVE_ITEM_TO_CHARACTER',
        0x01: 'TAKE_ITEM_FROM_CHARACTER',
        0x02: 'GET_PLAYER_HAS_INVENTORY_FULL',
        0x03: 'GET_PLAYER_HAS_INVENTORY_ROOM',
        0x04: 'CHECK_IF_CHARACTER_DOESNT_HAVE_ITEM',
        0x05: 'CHECK_IF_CHARACTER_HAS_ITEM',
        0x06: 'ADD_TO_ATM',
        0x07: 'TAKE_FROM_ATM',
        0x08: 'ADD_TO_WALLET',
        0x09: 'TAKE_FROM_WALLET',
        0x0A: 'GET_BUY_PRICE_OF_ITEM',
        0x0B: 'GET_SELL_PRICE_OF_ITEM',
        0x0C: 'CHECK_ESCARGO_STORAGE_STATUS',
        0x0D: 'CHARACTER_HAS_AILMENT',
        0x0E: 'GIVE_ITEM_TO_CHARACTER_B',
        0x0F: 'REMOVE_INVENTORY_ITEM_BY_SLOT',
        0x10: 'CHECK_ITEM_EQUIPPED',
        0x11: 'CHECK_SELECTED_ITEM_USABLE_OR_EQUIPPABLE',
        0x12: 'STORE_SELECTED_ITEM_WITH_ESCARGO',
        0x13: 'WITHDRAW_STORED_ITEM_FROM_ESCARGO',
        0x14: 'HAVE_ENOUGH_MONEY',
        0x15: 'PUT_VAL_IN_ARGMEM',
        0x17: 'HAVE_ENOUGH_MONEY_IN_ATM',
        0x18: 'ADD_ITEM_ID_TO_ESCARGO_STORAGE',
        0x19: 'HAVE_X_PARTY_MEMBERS',
        0x20: 'TEST_IS_USER_TARGETTING_SELF',
        0x21: 'GENERATE_RANDOM_NUMBER',
        0x22: 'TEST_IF_EXIT_MOUSE_USABLE',
        0x23: 'CHECK_EQUIPMENT_OFFENSIVE_CLASS',
        0x24: 'GET_STAGED_BANK_DEPOSIT_TOTAL',
    },
    0x1E: {
        0x00: 'RECOVER_HP_PERCENT',
        0x01: 'DEPLETE_HP_PERCENT',
        0x02: 'RECOVER_HP_AMOUNT',
        0x03: 'DEPLETE_HP_AMOUNT',
        0x04: 'RECOVER_PP_PERCENT',
        0x05: 'DEPLETE_PP_PERCENT',
        0x06: 'RECOVER_PP_AMOUNT',
        0x07: 'DEPLETE_PP_AMOUNT',
        0x08: 'SET_CHARACTER_LEVEL',
        0x09: 'GIVE_EXPERIENCE',
        0x0A: 'BOOST_IQ',
        0x0B: 'BOOST_GUTS',
        0x0C: 'BOOST_SPEED',
        0x0D: 'BOOST_VITALITY',
        0x0E: 'BOOST_LUCK',
    },
    0x1F: {
        0x00: 'PLAY_MUSIC',
        0x01: 'STOP_MUSIC',
        0x02: 'PLAY_SOUND',
        0x03: 'RESTORE_DEFAULT_MUSIC',
        0x04: 'SET_TEXT_PRINTING_SOUND',
        0x05: 'DISABLE_SECTOR_MUSIC_CHANGE',
        0x06: 'ENABLE_SECTOR_MUSIC_CHANGE',
        0x07: 'APPLY_MUSIC_EFFECT',
        0x11: 'ADD_PARTY_MEMBER',
        0x12: 'REMOVE_PARTY_MEMBER',
        0x13: 'CHANGE_CHARACTER_DIRECTION',
        0x14: 'CHANGE_PARTY_DIRECTION',
        0x15: 'GENERATE_ACTIVE_SPRITE',
        0x16: 'CHANGE_TPT_ENTRY_DIRECTION',
        0x17: 'GENERATE_ACTIVE_TPT_ENTRY',
        0x18: 'NO_OP_7_ARG_BYTES',
        0x19: 'NO_OP_7_ARG_BYTES_ALT',
        0x1A: 'CREATE_FLOATING_SPRITE_NEAR_TPT_ENTRY',
        0x1B: 'DELETE_FLOATING_SPRITE_NEAR_TPT_ENTRY',
        0x1C: 'CREATE_FLOATING_SPRITE_NEAR_CHARACTER',
        0x1D: 'DELETE_FLOATING_SPRITE_NEAR_CHARACTER',
        0x1E: 'DELETE_TPT_INSTANCE',
        0x1F: 'DELETE_GENERATED_SPRITE',
        0x20: 'TRIGGER_PSI_TELEPORT',
        0x21: 'TELEPORT_TO',
        0x23: 'TRIGGER_BATTLE',
        0x30: 'USE_NORMAL_FONT',
        0x31: 'USE_MR_SATURN_FONT',
        0x41: 'TRIGGER_EVENT',
        0x50: 'DISABLE_CONTROLLER_INPUT',
        0x51: 'ENABLE_CONTROLLER_INPUT',
        0x52: 'CREATE_NUMBER_SELECTOR',
        0x61: 'TRIGGER_MOVEMENT_CODE',
        0x62: 'SET_BLINKING_TRIANGLE_FLAG',
        0x63: 'SCREEN_RELOAD_PTR',
        0x64: 'DELETE_ALL_NPCS',
        0x65: 'DELETE_FIRST_NPC',
        0x66: 'ACTIVATE_HOTSPOT',
        0x67: 'DEACTIVATE_HOTSPOT',
        0x68: 'STORE_COORDINATES_TO_MEMORY',
        0x69: 'TELEPORT_TO_STORED_COORDINATES',
        0x71: 'REALIZE_PSI',
        0x83: 'EQUIP_ITEM_TO_CHARACTER',
        0xA0: 'SET_TPT_DIRECTION_UP',
        0xA1: 'SET_TPT_DIRECTION_DOWN',
        0xA2: 'CHECK_TPT_ENTRY_FLAG',
        0xB0: 'SAVE_GAME',
        0xC0: 'JUMP_MULTI2',
        0xD0: 'TRY_FIX_ITEM',
        0xD1: 'GET_DIRECTION_OF_NEARBY_TRUFFLE',
        0xD2: 'SUMMON_WANDERING_PHOTOGRAPHER',
        0xD3: 'TRIGGER_TIMED_EVENT',
        0xE1: 'CHANGE_MAP_PALETTE',
        0xE4: 'CHANGE_GENERATED_SPRITE_DIRECTION',
        0xE5: 'SET_PLAYER_LOCK',
        0xE6: 'DELAY_TPT_APPEARANCE',
        0xE7: 'FREEZE_SPRITE_ENTRY_MOVEMENT',
        0xE8: 'UNFREEZE_CHARACTER_MOVEMENT',
        0xE9: 'UNFREEZE_TPT_ENTRY_MOVEMENT',
        0xEA: 'UNFREEZE_SPRITE_ENTRY_MOVEMENT',
        0xEB: 'MAKE_INVISIBLE',
        0xEC: 'MAKE_VISIBLE',
        0xED: 'RESTORE_MOVEMENT',
        0xEE: 'WARP_PARTY_TO_TPT_ENTRY',
        0xEF: 'FOCUS_CAMERA_ON_GENERATED_SPRITE',
        0xF0: 'RIDE_BICYCLE',
        0xF1: 'SET_TPT_MOVEMENT_CODE',
        0xF2: 'SET_SPRITE_MOVEMENT_CODE',
        0xF3: 'CREATE_FLOATING_SPRITE_NEAR_ENTITY',
        0xF4: 'DELETE_FLOATING_SPRITE_NEAR_ENTITY',
    },
}


def fmt_addr(addr: int) -> str:
    return f'{(addr >> 16) & 0xFF:02X}:{addr & 0xFFFF:04X}'


def read_word(data: bytes, i: int) -> int:
    return data[i] | (data[i + 1] << 8)


def read_dword24(data: bytes, i: int) -> int:
    return data[i] | (data[i + 1] << 8) | (data[i + 2] << 16)


def decode_text_run(data: bytes, start: int) -> tuple[str, int]:
    i = start
    out: list[str] = []
    while i < len(data) and data[i] >= 0x20:
        out.append(US_EBTEXT_CHARMAP.get(data[i], f'<{data[i]:02X}>'))
        i += 1
    return ''.join(out), i - start


def parse_command(data: bytes, i: int) -> tuple[str, int]:
    op = data[i]
    name = TOP_LEVEL_NAMES.get(op, f'UNKNOWN_{op:02X}')

    if op in (0x00, 0x01, 0x02, 0x03, 0x0F, 0x11, 0x12, 0x13, 0x14):
        return name, 1
    if op in (0x0B, 0x0C, 0x0D, 0x0E, 0x10, 0x15, 0x16, 0x17):
        return f'{name} 0x{data[i+1]:02X}', 2
    if op in (0x04, 0x05, 0x07):
        return f'{name} 0x{read_word(data, i+1):04X}', 3
    if op == 0x06:
        return f'{name} flag=0x{read_word(data, i+1):04X} dest={fmt_addr(read_dword24(data, i+3))}', 6
    if op in (0x08, 0x0A):
        return f'{name} {fmt_addr(read_dword24(data, i+1))}', 4
    if op == 0x09:
        count = data[i+1]
        return f'{name} count={count}', 2 + (count * 3)

    if op not in SUBCOMMAND_NAMES:
        return name, 1

    sub = data[i+1]
    sub_name = SUBCOMMAND_NAMES[op].get(sub, f'UNKNOWN_{op:02X}_{sub:02X}')
    prefix = f'{sub_name}'

    if op == 0x18:
        if sub in (0x00, 0x02, 0x04, 0x06, 0x0A):
            return prefix, 2
        if sub in (0x01, 0x03, 0x09):
            return f'{prefix} 0x{data[i+2]:02X}', 3
        if sub == 0x05:
            return f'{prefix} x=0x{data[i+2]:02X} y=0x{data[i+3]:02X}', 4
        if sub == 0x07:
            return f'{prefix} ptr={fmt_addr(read_dword24(data, i+2))} value=0x{data[i+5]:02X}', 6
        if sub == 0x08:
            return f'{prefix} ptr={fmt_addr(read_dword24(data, i+2))}', 5
        return prefix, 2

    if op == 0x19:
        if sub in (0x04, 0x1E, 0x1F, 0x20):
            return prefix, 2
        if sub in (0x10, 0x11, 0x18, 0x1A, 0x1B, 0x21, 0x25, 0x26, 0x27, 0x28):
            return f'{prefix} 0x{data[i+2]:02X}', 3
        if sub in (0x05,):
            return f'{prefix} 0x{data[i+2]:02X}, 0x{data[i+3]:02X}, 0x{data[i+4]:02X}', 5
        if sub in (0x16, 0x1C, 0x1D):
            return f'{prefix} 0x{data[i+2]:02X}, 0x{data[i+3]:02X}', 4
        if sub == 0x19:
            return f'{prefix} 0x{data[i+2]:02X}, 0x{data[i+3]:02X}', 4
        if sub == 0x22:
            return f'{prefix} 0x{data[i+2]:02X}, 0x{data[i+3]:02X}, 0x{read_word(data, i+4):04X}', 6
        if sub == 0x23:
            return f'{prefix} 0x{read_word(data, i+2):04X}, 0x{read_word(data, i+4):04X}, 0x{data[i+6]:02X}', 7
        if sub == 0x24:
            return f'{prefix} 0x{read_word(data, i+2):04X}, 0x{read_word(data, i+4):04X}', 6
        return prefix, 2

    if op == 0x1A:
        if sub == 0x01:
            return f'{prefix} ptrs={fmt_addr(read_dword24(data, i+2))},{fmt_addr(read_dword24(data, i+5))},{fmt_addr(read_dword24(data, i+8))},{fmt_addr(read_dword24(data, i+11))} arg=0x{data[i+14]:02X}', 15
        if sub in (0x05, 0x06):
            return f'{prefix} 0x{data[i+2]:02X}, 0x{data[i+3]:02X}' if sub == 0x05 else f'{prefix} 0x{data[i+2]:02X}', 4 if sub == 0x05 else 3
        return prefix, 2

    if op == 0x1B:
        if sub in (0x00, 0x01, 0x04, 0x05, 0x06):
            return prefix, 2
        if sub in (0x02, 0x03):
            return f'{prefix} {fmt_addr(read_dword24(data, i+2))}', 5
        return prefix, 2

    if op == 0x1C:
        if sub in (0x04, 0x0D, 0x0E):
            return prefix, 2
        if sub in (0x00, 0x01, 0x02, 0x03, 0x05, 0x06, 0x07, 0x08, 0x11, 0x12, 0x14, 0x15):
            return f'{prefix} 0x{data[i+2]:02X}', 3
        if sub == 0x13:
            return f'{prefix} 0x{data[i+2]:02X}, 0x{data[i+3]:02X}', 4
        if sub in (0x0A, 0x0B):
            return f'{prefix} {fmt_addr(read_dword24(data, i+2))}', 5
        return prefix, 2

    if op == 0x1D:
        if sub in (0x02, 0x03, 0x0A, 0x0B, 0x18, 0x19, 0x21, 0x23, 0x24):
            return f'{prefix} 0x{data[i+2]:02X}', 3
        if sub in (0x00, 0x01, 0x04, 0x05, 0x0E):
            return f'{prefix} 0x{data[i+2]:02X}, 0x{data[i+3]:02X}', 4
        if sub in (0x06, 0x07, 0x14, 0x17):
            return f'{prefix} {fmt_addr(read_dword24(data, i+2))}', 5
        if sub in (0x08, 0x09, 0x0C, 0x0F, 0x10, 0x11, 0x12, 0x13, 0x15):
            return f'{prefix} 0x{read_word(data, i+2):04X}', 4
        if sub == 0x0D:
            return f'{prefix} 0x{data[i+2]:02X}, 0x{data[i+3]:02X}, 0x{data[i+4]:02X}', 5
        if sub in (0x20, 0x22):
            return prefix, 2
        return prefix, 2

    if op == 0x1E:
        if sub in (0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07):
            return f'{prefix} 0x{data[i+2]:02X}, 0x{data[i+3]:02X}', 4
        if sub == 0x08:
            return f'{prefix} 0x{data[i+2]:02X}, 0x{data[i+3]:02X}', 4
        if sub == 0x09:
            return f'{prefix} 0x{data[i+2]:02X}, {fmt_addr(read_dword24(data, i+3))}', 6
        if sub in (0x0A,0x0B,0x0C,0x0D,0x0E):
            return f'{prefix} 0x{data[i+2]:02X}, 0x{read_word(data, i+3):04X}', 5
        return prefix, 2

    if op == 0x1F:
        if sub in (0x03,0x04,0x05,0x06,0x30,0x31,0x60,0x64,0x65,0xA0,0xA1,0xA2,0xB0,0xD1,0xED,0xF0):
            return prefix, 2
        if sub in (0x01,0x02,0x07,0x11,0x12,0x14,0x1D,0x21,0x41,0x50,0x51,0x52,0x62,0x67,0x71,0x83,0xD0,0xD2,0xD3,0xE5,0xE8):
            return f'{prefix} 0x{data[i+2]:02X}', 3
        if sub in (0x13,0xEB,0xEC):
            return f'{prefix} 0x{data[i+2]:02X}, 0x{data[i+3]:02X}', 4
        if sub in (0x1C,0x1E,0x1F,0xE4,0xF3):
            return f'{prefix} 0x{read_word(data, i+2):04X}, 0x{data[i+4]:02X}', 5
        if sub in (0x15,0x17):
            return f'{prefix} 0x{read_word(data, i+2):04X}, 0x{read_word(data, i+4):04X}, 0x{data[i+6]:02X}', 7
        if sub == 0x16:
            return f'{prefix} 0x{read_word(data, i+2):04X}, 0x{data[i+4]:02X}', 5
        if sub in (0x18,0x19):
            return f'{prefix} bytes={data[i+2]:02X} {data[i+3]:02X} {data[i+4]:02X} {data[i+5]:02X} {data[i+6]:02X} {data[i+7]:02X} {data[i+8]:02X}', 9
        if sub in (0x1E,0xF1,0xF2):
            return f'{prefix} 0x{read_word(data, i+2):04X}, 0x{read_word(data, i+4):04X}', 6
        if sub in (0x1A,):
            return f'{prefix} 0x{read_word(data, i+2):04X}, 0x{data[i+4]:02X}', 5
        if sub in (0x1B,0xE6,0xE7,0xE9,0xEA,0xEE,0xEF,0xF4):
            return f'{prefix} 0x{read_word(data, i+2):04X}', 4
        if sub == 0x20:
            return f'{prefix} 0x{data[i+2]:02X}, 0x{data[i+3]:02X}', 4
        if sub == 0x23:
            return f'{prefix} 0x{read_word(data, i+2):04X}', 4
        if sub == 0x66:
            return f'{prefix} 0x{data[i+2]:02X}, 0x{data[i+3]:02X}, {fmt_addr(read_dword24(data, i+4))}', 7
        if sub == 0x68 or sub == 0x69:
            return prefix, 2
        if sub == 0xC0:
            count = data[i+2]
            return f'{prefix} count={count}', 3 + (count * 3)
        if sub in (0xE1,):
            return f'{prefix} 0x{read_word(data, i+2):04X}, 0x{data[i+4]:02X}', 5
        if sub == 0x63:
            return f'{prefix} 0x{read_word(data, i+2):04X}, 0x{read_word(data, i+4):04X}', 6
        return prefix, 2

    return prefix, 2


def decode_script(data: bytes, start_address: int) -> Iterable[ScriptLine]:
    i = 0
    while i < len(data):
        addr = start_address + i
        if data[i] >= 0x20:
            text, size = decode_text_run(data, i)
            yield ScriptLine(addr, size, f'TEXT "{text}"')
            i += size
            continue
        try:
            text, size = parse_command(data, i)
        except IndexError:
            remaining = ' '.join(f'{b:02X}' for b in data[i:])
            suffix = f' bytes={remaining}' if remaining else ''
            yield ScriptLine(addr, len(data) - i, f'TRUNCATED_COMMAND 0x{data[i]:02X}{suffix}')
            break
        yield ScriptLine(addr, size, text)
        i += size


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Decode EarthBound text script bytes into control-code lines.')
    parser.add_argument('address', type=parse_snes_address, help='SNES CPU address, for example EF:7BDF')
    parser.add_argument('--length', type=int, default=128, help='Bytes to decode (default: 128)')
    parser.add_argument('--rom', help='Optional explicit ROM path')
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()
    rom_path = find_rom(args.rom)
    rom = load_rom(rom_path)
    bank = (args.address >> 16) & 0xFF
    addr = args.address & 0xFFFF
    file_offset = hirom_to_file_offset(bank, addr, len(rom))
    if file_offset is None:
        raise SystemExit(f'address {fmt_addr(args.address)} does not map into ROM')
    data = rom[file_offset:file_offset + args.length]
    print(f'ROM: {rom_path}')
    print(f'Start: {fmt_addr(args.address)} (file 0x{file_offset:06X})')
    print()
    for line in decode_script(data, args.address):
        print(f'{fmt_addr(line.address)}  {line.text}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


