from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
from pathlib import Path


BANK_FILE = Path("build/split/banks/bank_C0.bin")
CANONICAL_BANK = 0xC0

OPCODES = {
    0x00: ("brk", "imm8"),
    0x05: ("ora", "dp"),
    0x0A: ("asl", "acc"),
    0x08: ("php", "impl"),
    0x09: ("ora", "imm_m"),
    0x0B: ("phd", "impl"),
    0x0D: ("ora", "abs"),
    0x10: ("bpl", "rel8"),
    0x18: ("clc", "impl"),
    0x1A: ("inc", "acc"),
    0x1B: ("tcs", "impl"),
    0x20: ("jsr", "abs"),
    0x22: ("jsl", "long"),
    0x28: ("plp", "impl"),
    0x29: ("and", "imm_m"),
    0x2B: ("pld", "impl"),
    0x30: ("bmi", "rel8"),
    0x3C: ("bit", "absx"),
    0x38: ("sec", "impl"),
    0x3A: ("dec", "acc"),
    0x40: ("rti", "impl"),
    0x42: ("wdm", "imm8"),
    0x48: ("pha", "impl"),
    0x4A: ("lsr", "acc"),
    0x4B: ("phk", "impl"),
    0x4C: ("jmp", "abs"),
    0x4E: ("lsr", "abs"),
    0x50: ("bvc", "rel8"),
    0x54: ("mvn", "move"),
    0x58: ("cli", "impl"),
    0x5A: ("phy", "impl"),
    0x5B: ("tcd", "impl"),
    0x5C: ("jml", "long"),
    0x6C: ("jmp", "ind"),
    0x60: ("rts", "impl"),
    0x64: ("stz", "dp"),
    0x65: ("adc", "dp"),
    0x68: ("pla", "impl"),
    0x69: ("adc", "imm_m"),
    0x6D: ("adc", "abs"),
    0x6B: ("rtl", "impl"),
    0x70: ("bvs", "rel8"),
    0x78: ("sei", "impl"),
    0x7A: ("ply", "impl"),
    0x7B: ("tdc", "impl"),
    0x7D: ("adc", "absx"),
    0x7F: ("adc", "longx"),
    0x80: ("bra", "rel8"),
    0x84: ("sty", "dp"),
    0x90: ("bcc", "rel8"),
    0x85: ("sta", "dp"),
    0x88: ("dey", "impl"),
    0x87: ("sta", "dp_long"),
    0x86: ("stx", "dp"),
    0x8A: ("txa", "impl"),
    0x8B: ("phb", "impl"),
    0x8C: ("sty", "abs"),
    0x8D: ("sta", "abs"),
    0x8E: ("stx", "abs"),
    0x8F: ("sta", "long"),
    0x98: ("tya", "impl"),
    0x99: ("sta", "absy"),
    0xB0: ("bcs", "rel8"),
    0x9A: ("txs", "impl"),
    0x9B: ("txy", "impl"),
    0x9C: ("stz", "abs"),
    0x9D: ("sta", "absx"),
    0x9E: ("stz", "absx"),
    0x9F: ("sta", "longx"),
    0xA0: ("ldy", "imm_x"),
    0xA2: ("ldx", "imm_x"),
    0xA4: ("ldy", "dp"),
    0xA5: ("lda", "dp"),
    0xA6: ("ldx", "dp"),
    0xA7: ("lda", "dp_long"),
    0xA8: ("tay", "impl"),
    0xA9: ("lda", "imm_m"),
    0xAA: ("tax", "impl"),
    0xAB: ("plb", "impl"),
    0xAC: ("ldy", "abs"),
    0xAD: ("lda", "abs"),
    0xAF: ("lda", "long"),
    0xAE: ("ldx", "abs"),
    0xB0: ("bcs", "rel8"),
    0xB7: ("lda", "dp_long_y"),
    0xB8: ("clv", "impl"),
    0xBB: ("tyx", "impl"),
    0xBC: ("ldy", "absx"),
    0xB9: ("lda", "absy"),
    0xBD: ("lda", "absx"),
    0xBE: ("ldx", "absy"),
    0xBF: ("lda", "longx"),
    0xCD: ("cmp", "abs"),
    0xCE: ("dec", "abs"),
    0xC0: ("cpy", "imm_x"),
    0xC2: ("rep", "imm8"),
    0xC4: ("cpy", "dp"),
    0xC5: ("cmp", "dp"),
    0xCC: ("cpy", "abs"),
    0xC6: ("dec", "dp"),
    0xC8: ("iny", "impl"),
    0xC9: ("cmp", "imm_m"),
    0xCA: ("dex", "impl"),
    0xD0: ("bne", "rel8"),
    0xDA: ("phx", "impl"),
    0xDC: ("jml", "ind_long"),
    0xDE: ("dec", "absx"),
    0xE0: ("cpx", "imm_x"),
    0xE2: ("sep", "imm8"),
    0xE4: ("cpx", "dp"),
    0xE5: ("sbc", "dp"),
    0xE8: ("inx", "impl"),
    0xE9: ("sbc", "imm_m"),
    0xEB: ("xba", "impl"),
    0xEC: ("cpx", "abs"),
    0xED: ("sbc", "abs"),
    0xEE: ("inc", "abs"),
    0xE6: ("inc", "dp"),
    0xF0: ("beq", "rel8"),
    0xF4: ("pea", "abs"),
    0xFA: ("plx", "impl"),
    0xFB: ("xce", "impl"),
    0xFC: ("jsr", "absxind"),
}

BRANCH_OPS = {"bpl", "bmi", "bvs", "beq", "bne", "bcs", "bcc"}
STOP_OPS = {"jmp", "jml", "rts", "rtl", "rti", "brk"}
CALL_OPS = {"jsr", "jsl"}


@dataclass(frozen=True)
class CpuState:
    emulation: bool
    m8: bool
    x8: bool
    carry: bool | None

    def key(self) -> tuple[bool, bool, bool, bool | None]:
        return (self.emulation, self.m8, self.x8, self.carry)

    def summary(self) -> str:
        carry = "?" if self.carry is None else ("1" if self.carry else "0")
        return f"E{1 if self.emulation else 0} M{8 if self.m8 else 16} X{8 if self.x8 else 16} C{carry}"


ENTRY_POINTS = {
    0x8141: ("ResetVector_008141", CpuState(emulation=True, m8=True, x8=True, carry=None)),
    0x8147: ("NativeNMI_008147", CpuState(emulation=False, m8=True, x8=True, carry=None)),
    0x814B: ("NativeIRQ_00814B", CpuState(emulation=False, m8=True, x8=True, carry=None)),
}

ANALYSIS_ROOTS = {
    0x8501: ("NMI_ServiceAudioQueue", CpuState(emulation=False, m8=True, x8=True, carry=None)),
    0x8518: ("Frame_CallbackDispatcher", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x851B: ("Frame_CallbackReturn", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x851C: ("Set_FrameCallbackPtr", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x8522: ("Reset_FrameCallbackToDefault", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x9279: ("Dispatch_DelayedActionTarget", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x927C: ("Init_DelayedActionPools", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x9321: ("Init_DelayedActionState", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x94AA: ("Process_ActiveTaskSlots", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x94D0: ("Process_TaskSlotRecordChain", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x9C02: ("Alloc_TaskSlotOrFail", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x9C35: ("Release_TaskSlotByIndex", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x9C3B: ("Release_TaskSlot_Core", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x9C57: ("Link_TaskSlotIntoActiveList", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x9C73: ("Detach_TaskSlotLink", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x9C8F: ("Push_TaskSlotToFreeList", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x9C99: ("Restore_TaskRecordChain", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x9CB5: ("Find_TaskSlotPredecessor", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x9D03: ("Pop_TaskRecordFromFreeList", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x9D12: ("Push_TaskRecordToFreeList", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x9D1F: ("Unlink_TaskRecordFromSlotChain", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x9D3E: ("Find_TaskRecordPredecessor", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x9DA1: ("Init_TaskRecordDefaults", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x64D4: ("Reset_StagedMovementQueue", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x64E3: ("Enqueue_StagedMovementQueueEntry", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x6537: ("Peek_StagedMovementQueueType", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x654E: ("Peek_StagedMovementQueuePayload", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x6578: ("Push_PendingPair5E36", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x65A3: ("Flush_PendingPair5E36", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x65C2: ("Probe_FrontType6DoorCandidate", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x41E3: ("Probe_InteractableAlongFacing", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x42C2: ("Prepare_Class1ActorInteraction", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x42EF: ("Probe_FrontInteractionFacing", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x4279: ("Resolve_InteractableAlongFacingTarget", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x43BC: ("Resolve_InteractionFacingRotation", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x4452: ("Resolve_FrontInteractionTarget", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x7477: ("Lookup_MovementTriggerType", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x7526: ("Dispatch_MovementHelperFromLookup", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x6A1B: ("MovementTriggerType0_QueueDoorDestination", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x6A8B: ("MovementTriggerType5Or7_NoOp", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x6A8E: ("MovementTriggerType6_NoOp", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x6A91: ("MovementTriggerType1_SetState07Or08", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x6ACA: ("MovementTriggerType2_QueueDoorTransition", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x6E6E: ("MovementTriggerType3_QueueOffsetStep", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x705F: ("Select_StagedMovementFacing", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x70CB: ("Queue_StagedMovementFromGridCoords", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x75DD: ("Process_StagedMovementQueueEntry", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x6E2C: ("TimerCallback_CommitStagedPosition_State0C", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x6E4A: ("TimerCallback_CommitStagedPosition_ClearMotion", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x6F82: ("TimerCallback_WaitForStagedY_State0D", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0x6FED: ("TimerCallback_WaitForStagedY_ClearMotion", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0xDB0F: ("Dispatch_ActiveTaskSlots", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0xDBE6: ("Queue_DelayedActionTimer", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0xDC38: ("Clear_DelayedActionTimerSlot", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0xDC4E: ("FrameCallback_ProcessDelayedActions", CpuState(emulation=False, m8=False, x8=False, carry=None)),
    0xF41E: ("FrameCallback_ProcessCommandStream", CpuState(emulation=False, m8=False, x8=False, carry=None)),
}



KNOWN_LABELS = {
    0x8000: "Boot_InitHardware",
    0x814F: "IRQ_Prologue",
    0x8170: "NMI_Prologue",
    0x8183: "NMI_FrameUpdate",
    0x8240: "NMI_ProcessTransferQueue",
    0x8281: "NMI_ApplyScrollSetA",
    0x82D6: "NMI_ApplyScrollSetB",
    0x8334: "NMI_FinalizeFrame",
    0x8501: "NMI_ServiceAudioQueue",
    0x8518: "Frame_CallbackDispatcher",
    0x851B: "Frame_CallbackReturn",
    0x851C: "Set_FrameCallbackPtr",
    0x8522: "Reset_FrameCallbackToDefault",
    0x9279: "Dispatch_DelayedActionTarget",
    0x927C: "Init_DelayedActionPools",
    0x9321: "Init_DelayedActionState",
    0x94AA: "Process_ActiveTaskSlots",
    0x94D0: "Process_TaskSlotRecordChain",
    0x9C02: "Alloc_TaskSlotOrFail",
    0x9C35: "Release_TaskSlotByIndex",
    0x9C3B: "Release_TaskSlot_Core",
    0x9C57: "Link_TaskSlotIntoActiveList",
    0x9C73: "Detach_TaskSlotLink",
    0x9C8F: "Push_TaskSlotToFreeList",
    0x9C99: "Restore_TaskRecordChain",
    0x9CB5: "Find_TaskSlotPredecessor",
    0x9D03: "Pop_TaskRecordFromFreeList",
    0x9D12: "Push_TaskRecordToFreeList",
    0x9D1F: "Unlink_TaskRecordFromSlotChain",
    0x9D3E: "Find_TaskRecordPredecessor",
    0x9DA1: "Init_TaskRecordDefaults",
    0x64D4: "Reset_StagedMovementQueue",
    0x64E3: "Enqueue_StagedMovementQueueEntry",
    0x6537: "Peek_StagedMovementQueueType",
    0x654E: "Peek_StagedMovementQueuePayload",
    0x6578: "Push_PendingPair5E36",
    0x65A3: "Flush_PendingPair5E36",
    0x65C2: "Probe_FrontType6DoorCandidate",
    0x41E3: "Probe_InteractableAlongFacing",
    0x42C2: "Prepare_Class1ActorInteraction",
    0x42EF: "Probe_FrontInteractionFacing",
    0x4279: "Resolve_InteractableAlongFacingTarget",
    0x43BC: "Resolve_InteractionFacingRotation",
    0x4452: "Resolve_FrontInteractionTarget",
    0x7477: "Lookup_MovementTriggerType",
    0x7526: "Dispatch_MovementHelperFromLookup",
    0x6A1B: "MovementTriggerType0_QueueDoorDestination",
    0x6A8B: "MovementTriggerType5Or7_NoOp",
    0x6A8E: "MovementTriggerType6_NoOp",
    0x6A91: "MovementTriggerType1_SetState07Or08",
    0x6ACA: "MovementTriggerType2_QueueDoorTransition",
    0x6E6E: "MovementTriggerType3_QueueOffsetStep",
    0x705F: "Select_StagedMovementFacing",
    0x70CB: "Queue_StagedMovementFromGridCoords",
    0x75DD: "Process_StagedMovementQueueEntry",
    0x6E2C: "TimerCallback_CommitStagedPosition_State0C",
    0x6E4A: "TimerCallback_CommitStagedPosition_ClearMotion",
    0x6F82: "TimerCallback_WaitForStagedY_State0D",
    0x6FED: "TimerCallback_WaitForStagedY_ClearMotion",
    0xB99A: "Boot_EnterMainFlow",
    0xDB0F: "Dispatch_ActiveTaskSlots",
    0xDBE6: "Queue_DelayedActionTimer",
    0xDC38: "Clear_DelayedActionTimerSlot",
    0xDC4E: "FrameCallback_ProcessDelayedActions",
    0xF41E: "FrameCallback_ProcessCommandStream",
}




@dataclass
class Instruction:
    address: int
    size: int
    raw_bytes: bytes
    mnemonic: str
    operand_text: str
    state_before: CpuState
    state_after: CpuState
    targets: list[int]
    stop_flow: bool

    def formatted_bytes(self) -> str:
        return " ".join(f"{value:02X}" for value in self.raw_bytes)


@dataclass
class DecodeResult:
    instructions: dict[int, Instruction]
    labels: dict[int, str]
    warnings: list[str]


def read_u16_le(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def read_u24_le(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8) | (data[offset + 2] << 16)


def signed8(value: int) -> int:
    return value - 0x100 if value & 0x80 else value


def is_same_bank_target(long_address: int) -> int | None:
    bank = (long_address >> 16) & 0xFF
    address = long_address & 0xFFFF
    if bank != CANONICAL_BANK:
        return None
    return address


def operand_size(mode: str, state: CpuState) -> int:
    if mode in {"impl", "acc"}:
        return 0
    if mode in {"imm8", "dp", "dp_long", "dp_long_y", "rel8"}:
        return 1
    if mode in {"ind", "ind_long", "absxind"}:
        return 2
    if mode in {"abs", "absx", "absy"}:
        return 2
    if mode == "move":
        return 2
    if mode in {"long", "longx"}:
        return 3
    if mode == "imm_m":
        return 1 if state.m8 else 2
    if mode == "imm_x":
        return 1 if state.x8 else 2
    raise ValueError(f"Unsupported mode: {mode}")


def format_operand(mode: str, operand: bytes, address: int) -> tuple[str, list[int]]:
    if mode == "impl":
        return "", []
    if mode == "acc":
        return "a", []
    if mode == "imm8":
        return f"#${operand[0]:02X}", []
    if mode in {"imm_m", "imm_x"}:
        return f"#${int.from_bytes(operand, 'little'):0{len(operand) * 2}X}", []
    if mode == "dp":
        return f"${operand[0]:02X}", []
    if mode == "dp_long":
        return f"[${operand[0]:02X}]", []
    if mode == "dp_long_y":
        return f"[${operand[0]:02X}],y", []
    if mode == "abs":
        target = read_u16_le(operand, 0)
        return f"${target:04X}", [target]
    if mode == "ind":
        target = read_u16_le(operand, 0)
        return f"(${target:04X})", []
    if mode == "absxind":
        target = read_u16_le(operand, 0)
        return f"(${target:04X},x)", []
    if mode == "ind_long":
        target = read_u16_le(operand, 0)
        return f"[${target:04X}]", []
    if mode == "absx":
        target = read_u16_le(operand, 0)
        return f"${target:04X},x", []
    if mode == "absy":
        target = read_u16_le(operand, 0)
        return f"${target:04X},y", []
    if mode == "long":
        target = read_u24_le(operand, 0)
        return f"${target:06X}", [target]
    if mode == "longx":
        target = read_u24_le(operand, 0)
        return f"${target:06X},x", [target]
    if mode == "rel8":
        target = (address + 2 + signed8(operand[0])) & 0xFFFF
        return f"${target:04X}", [target]
    if mode == "move":
        return f"${operand[1]:02X}, ${operand[0]:02X}", []
    raise ValueError(f"Unsupported mode: {mode}")


def update_state(state: CpuState, mnemonic: str, operand: bytes) -> CpuState:
    emulation = state.emulation
    m8 = state.m8
    x8 = state.x8
    carry = state.carry

    if mnemonic == "clc":
        carry = False
    elif mnemonic == "sec":
        carry = True
    elif mnemonic in {"adc", "bit", "cmp", "cpy", "cpx", "and", "ora", "sbc", "asl", "lsr", "dex", "inx", "iny", "dec", "inc"}:
        carry = None
    elif mnemonic == "xce":
        if carry is None:
            emulation = False
            carry = True
        else:
            emulation, carry = carry, emulation
        if emulation:
            m8 = True
            x8 = True
    elif mnemonic == "rep" and not emulation:
        mask = operand[0]
        if mask & 0x20:
            m8 = False
        if mask & 0x10:
            x8 = False
    elif mnemonic == "sep":
        mask = operand[0]
        if mask & 0x20:
            m8 = True
        if mask & 0x10:
            x8 = True

    return CpuState(emulation=emulation, m8=m8, x8=x8, carry=carry)


def decode_instruction(data: bytes, address: int, state: CpuState) -> Instruction:
    opcode = data[address]
    if opcode not in OPCODES:
        raw = data[address:address + 1]
        return Instruction(
            address=address,
            size=1,
            raw_bytes=raw,
            mnemonic="db",
            operand_text=f"${opcode:02X}",
            state_before=state,
            state_after=state,
            targets=[],
            stop_flow=True,
        )

    mnemonic, mode = OPCODES[opcode]
    size = 1 + operand_size(mode, state)
    operand = data[address + 1:address + size]
    operand_text, raw_targets = format_operand(mode, operand, address)
    state_after = update_state(state, mnemonic, operand)

    targets: list[int] = []
    next_address = (address + size) & 0xFFFF
    if mnemonic in BRANCH_OPS:
        targets.extend(raw_targets)
        targets.append(next_address)
    elif mnemonic == "bra":
        targets.extend(raw_targets)
    elif mnemonic in CALL_OPS:
        targets.append(next_address)
        if raw_targets:
            target = raw_targets[0]
            if mode == "long":
                same_bank = is_same_bank_target(target)
                if same_bank is not None:
                    targets.append(same_bank)
            else:
                targets.append(target)
    elif mnemonic in {"jmp", "jml"}:
        if raw_targets:
            target = raw_targets[0]
            if mode == "long":
                same_bank = is_same_bank_target(target)
                if same_bank is not None:
                    targets.append(same_bank)
            else:
                targets.append(target)
    elif mnemonic not in STOP_OPS:
        targets.append(next_address)

    return Instruction(
        address=address,
        size=size,
        raw_bytes=data[address:address + size],
        mnemonic=mnemonic,
        operand_text=operand_text,
        state_before=state,
        state_after=state_after,
        targets=targets,
        stop_flow=mnemonic in STOP_OPS or mnemonic == "bra" or mnemonic == "db",
    )


def make_label(address: int) -> str:
    return KNOWN_LABELS.get(address, f"Code_C0{address:04X}")


def disassemble(data: bytes, follow_calls: bool = False) -> DecodeResult:
    instructions: dict[int, Instruction] = {}
    labels = {address: label for address, (label, _state) in ENTRY_POINTS.items()}
    labels.update({address: label for address, (label, _state) in ANALYSIS_ROOTS.items()})
    labels.update(KNOWN_LABELS)
    warnings: list[str] = []
    queue: deque[tuple[int, CpuState]] = deque((address, state) for address, (_label, state) in ENTRY_POINTS.items())
    queue.extend((address, state) for address, (_label, state) in ANALYSIS_ROOTS.items())
    seen_states: set[tuple[int, tuple[bool, bool, bool, bool | None]]] = set()

    while queue:
        start_address, start_state = queue.popleft()
        address = start_address
        state = start_state

        while 0 <= address < len(data):
            state_key = (address, state.key())
            if state_key in seen_states:
                break
            seen_states.add(state_key)

            if address in instructions:
                existing = instructions[address]
                if existing.state_before.key() != state.key():
                    warnings.append(
                        f"State mismatch at C0:{address:04X}: saw {existing.state_before.summary()} and {state.summary()}"
                    )
                break

            instruction = decode_instruction(data, address, state)
            instructions[address] = instruction

            next_address = (address + instruction.size) & 0xFFFF
            for target in instruction.targets:
                if target == next_address and not instruction.stop_flow:
                    continue
                if instruction.mnemonic in CALL_OPS and target != next_address and not follow_calls:
                    continue
                if 0 <= target < len(data):
                    labels.setdefault(target, make_label(target))
                    queue.append((target, instruction.state_after))

            if instruction.stop_flow:
                break

            address = next_address
            state = instruction.state_after

    return DecodeResult(instructions=instructions, labels=labels, warnings=warnings)


def render_markdown(result: DecodeResult) -> str:
    lines = [
        "# Bank C0 First-Pass Disassembly",
        "",
        "This is a recursive first-pass disassembly rooted at the reset and interrupt vector trampolines that live in the canonical `C0` ROM mirror.",
        "",
        "## Seed Entry Points",
        "",
    ]

    for address, (label, state) in sorted(ENTRY_POINTS.items()):
        lines.append(f"- `{label}` at `C0:{address:04X}` with assumed state `{state.summary()}`")

    lines.extend([
        "",
        "## Analysis Roots",
        "",
    ])

    for address, (label, state) in sorted(ANALYSIS_ROOTS.items()):
        lines.append(f"- `{label}` at `C0:{address:04X}` with assumed state `{state.summary()}`")

    lines.extend([
        "",
        "## Listing",
        "",
        "```asm",
    ])

    for address in sorted(result.instructions):
        if address in result.labels:
            lines.append(f"{result.labels[address]}:")
        instruction = result.instructions[address]
        operand = f" {instruction.operand_text}" if instruction.operand_text else ""
        lines.append(
            f"C0:{address:04X}  {instruction.formatted_bytes():<11}  {instruction.mnemonic}{operand:<20} ; {instruction.state_before.summary()}"
        )

    lines.append("```")

    if result.warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in sorted(set(result.warnings)):
            lines.append(f"- {warning}")

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Produce a first-pass recursive disassembly of EarthBound bank C0 entry code."
    )
    parser.add_argument(
        "--bank-file",
        default=str(BANK_FILE),
        help="Path to the split canonical C0 bank binary.",
    )
    parser.add_argument(
        "--output",
        help="Optional Markdown output path.",
    )
    parser.add_argument(
        "--follow-calls",
        action="store_true",
        help="Recursively follow same-bank JSR/JSL targets in addition to jumps and branches.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bank_file = Path(args.bank_file)
    data = bank_file.read_bytes()
    result = disassemble(data, follow_calls=args.follow_calls)
    markdown = render_markdown(result)
    if args.output:
        Path(args.output).write_text(markdown, encoding="ascii")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())











