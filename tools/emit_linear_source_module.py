from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from decode_snippet import CONTROL_FLOW, BRANCHES, CpuState, OPCODES, decode_instruction, parse_cpu_address
from rom_tools import find_rom, load_rom


ROOT = Path(__file__).resolve().parent.parent
BASE_SYMBOLS = {
    "$C018F3": "C018F3_CloseOrResetPresentationState",
    "$C01A69": "C01A69_ResetEntitySlotStateTables",
    "$C01A86": "C01A86_ResetEntityBytePool467E",
    "$C01C11": "C01C11_InitializeEntityStateMask",
    "$C01E49": "C01E49_CreateEntityFromDescriptor",
    "$C019B2": "C019B2_RestorePartyStateAfterTransition",
    "$C064D4": "C064D4_ResetEntityOverlapAndCollisionState",
    "$C06B21": "C06B21_RunPostTransitionDeferredScriptQueue",
    "$C07B52": "C07B52_RebuildPartyRecordsOrEntityState",
    "$C0856B": "C0856B_WaitFramesOrTransitionDelay",
    "$C085B7": "C085B7_QueueChunkedVramDma",
    "$C08616": "C08616_QueueVramTransfer_FromDpSource",
    "$C08726": "C08726_BlankWaitAndDisableHdma",
    "$C08744": "C08744_OpenDisplayTransitionBracket",
    "$C08756": "C08756_WaitOneFrameAndPollInput",
    "$C08814": "C08814_SetDisplayTransitionMode",
    "$C0886C": "C0886C_SetDisplayTransitionState",
    "$C0887A": "C0887A_ClearDisplayTransitionState",
    "$C0888B": "C0888B_WaitForDisplayTransition",
    "$C088A5": "C088A5_SetRendererWorkBank",
    "$C088B1": "C088B1_ResetRendererFrameState",
    "$C08B26": "C08B26_FlushQueuedSpriteOrTileWork",
    "$C08C54": "C08C54_DrawTilemapIconAtPosition",
    "$C08CD5": "C08CD5_DrawTileStagingBlock",
    "$C08D92": "C08D92_UpdateObjSizeAndBaseRegister",
    "$C08D79": "C08D79_UpdateBgModeRegisterFromQueue",
    "$C08D9E": "C08D9E_UpdateBg1ScreenBaseRegistersFromQueue",
    "$C08E1C": "C08E1C_UpdateBg2ScreenBaseRegistersFromQueue",
    "$C08ED2": "C08ED2_QueueOrTransferDynamicTileBlock",
    "$C08EED": "C08EED_CopyToVramOrRendererBuffer",
    "$C08EFC": "C08EFC_CommitTileBufferToStaging",
    "$C08F15": "C08F15_ClearVramOrRendererBuffer",
    "$C08FF7": "C08FF7_ResolveIndexedPointerOffset",
    "$C08E9A": "C08E9A_GetRandom16",
    "$C09032": "C09032_DivideUnsignedWordByIndex",
    "$C090FF": "C090FF_AddLongPointerOffset",
    "$C0915B": "C0915B_DivideUnsignedWordByY",
    "$C09231": "C09231_ModUnsignedWordByIndex",
    "$C092F5": "C092F5_AllocateEntityOrSpriteSlot",
    "$C0943C": "C0943C_SaveCurrentCoordinateState",
    "$C09451": "C09451_RestoreSavedCoordinateState",
    "$C09466": "C09466_RefreshActiveEntitySpriteState",
    "$C093F9": "C093F9_RunEntityScriptRecordForSlot",
    "$C0B65F": "C0B65F_SeedPlayerOverworldStartPosition",
    "$C0ABC6": "C0ABC6_ClearPresentationQueues",
    "$C0AC0C": "C0AC0C_QueuePresentationSfxOrCounter",
    "$C0AFCD": "C0AFCD_SetPresentationFadeOrMode",
    "$C1004E": "C1004E_WaitWhileFileSelectEntityScriptBusy",
    "$C0A48F": "C0A48F_RefreshVisualProfileForSlot",
    "$C0B400": "C0B400_ProjectPresentationXOffset",
    "$C0B40B": "C0B40B_ProjectPresentationYOffset",
    "$C186B1": "C186B1_PrintTextFromPointer",
    "$C1DD5F": "C1DD5F_WaitForTextOrMenuAcknowledge",
    "$C200D9": "C200D9_ClearBattleOrPresentationState",
    "$C21628": "C21628_CheckEventFlag",
    "$C2165E": "C2165E_SetEventFlagOrState",
    "$C2C8C8": "C2C8C8_ResetBattleVisualPresentationState",
    "$C2C92D": "C2C92D_QueueOrApplyBattleVisualScript",
    "$C2D121": "C2D121_LoadPresentationSpriteResource",
    "$C2EA15": "C2EA15_BeginBattleSwirlOverlayScript",
    "$C2EA74": "C2EA74_SwitchBattleSwirlOverlayToClosingScript",
    "$C2EAAA": "C2EAAA_FinishBattleSwirlOverlay",
    "$C2EACF": "C2EACF_PollBattleSwirlOverlayBusy",
    "$C41A9E": "C41A9E_GraphicsDecompressionRoutines_Main",
    "$C426ED": "C426ED_ApplyPaletteComponentInterpolationStep",
    "$C4283F": "C4283F_CopySecondaryVisualProfileFrameWords",
    "$C42884": "C42884_CopyPrimaryVisualProfileFrameWords",
    "$C428D1": "C428D1_Copy7fWordsEvery16ByCount",
    "$C428FC": "C428FC_MergeMasked7fTileColumnRows",
    "$C42965": "C42965_MergeMasked7fTileColumnPair",
    "$C429AE": "C429AE_GenerateVisualProfileRenderDmaStrips",
    "$C42A63": "C42A63_VisualProfileFootprintWidthTable",
    "$C3FB45": "C3FB45_NamingVowelRemapTable",
    "$C44963": "C44963_ResetActiveTextGlyphRun",
    "$C46028": "C46028_FindEntitySlotByCachedPoseDescriptorId",
    "$C47C3F": "C47C3F_ClearWindowOrMenuMaskState",
    "$C47F87": "C47F87_RefreshWindowFlavorPalette",
    "$C49208": "C49208_BuildLandingInterpolationPlanesFrom7f7800",
    "$C492D2": "C492D2_RunLandingInterpolationFrame",
    "$C4954C": "C4954C_SeedPaletteFadeWorkBuffer",
    "$C496E7": "C496E7_StartPaletteFadeFromWorkBuffer",
    "$C49740": "C49740_FinishPaletteFadeWorkBuffer",
    "$C4800B": "C4800B_RestoreWorldDisplayState",
    "$C4A7B0": "C4A7B0_StepBattleOverlayScriptState",
    "$C4FBBD": "C4FBBD_PlaySoundStoneMelody",
}


@dataclass(frozen=True)
class Instruction:
    address: int
    size: int
    text: str
    raw: bytes


def parse_address_list(values: list[str]) -> set[tuple[int, int]]:
    out: set[tuple[int, int]] = set()
    for value in values:
        out.add(parse_cpu_address(value))
    return out


def parse_symbol_list(values: list[str]) -> dict[str, str]:
    symbols: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit(f"--symbol must look like NAME=$ADDR, got {value!r}")
        name, raw_address = value.split("=", 1)
        name = name.strip()
        raw_address = raw_address.strip().upper()
        if not name or not raw_address.startswith("$"):
            raise SystemExit(f"--symbol must look like NAME=$ADDR, got {value!r}")
        symbols[raw_address] = name
    return symbols


def parse_label_list(values: list[str]) -> dict[int, str]:
    labels: dict[int, str] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit(f"--label must look like C4:1234=Name, got {value!r}")
        raw_address, name = value.split("=", 1)
        bank, address = parse_cpu_address(raw_address)
        if not name.strip():
            raise SystemExit(f"--label must include a label name, got {value!r}")
        labels[(bank << 16) | address] = name.strip()
    return labels


def operand_width_suffix(text: str, raw: bytes) -> str:
    if " #$" not in text:
        return text
    mnemonic, operand = text.split(" ", 1)
    if mnemonic in {"rep", "sep", "brk", "wdm", "pea"}:
        return text
    if len(raw) == 2:
        return f"{mnemonic}.b {operand}"
    if len(raw) == 3:
        return f"{mnemonic}.w {operand}"
    return text


def asar_operand_syntax(text: str) -> str:
    text = re.sub(r"\[([0-9A-Fa-f]{4})\]", r"[$\1]", text)
    text = re.sub(r"\(([0-9A-Fa-f]{4})\)", r"($\1)", text)
    text = re.sub(r"\(([0-9A-Fa-f]{4}),X\)", r"($\1,X)", text)
    return text


def branch_target(text: str) -> int | None:
    if " " not in text:
        return None
    mnemonic, operand = text.split(" ", 1)
    if mnemonic not in BRANCHES and mnemonic not in {"jmp", "jsr"}:
        return None
    match = re.fullmatch(r"\$([0-9A-Fa-f]{4})", operand.strip())
    return int(match.group(1), 16) if match else None


def same_bank_long_call_target(text: str, bank: int) -> int | None:
    if " " not in text:
        return None
    mnemonic, operand = text.split(" ", 1)
    if mnemonic != "jsl":
        return None
    match = re.fullmatch(r"\$([0-9A-Fa-f]{6})", operand.strip())
    if not match:
        return None
    raw = int(match.group(1), 16)
    target_bank = (raw >> 16) & 0xFF
    return raw & 0xFFFF if target_bank == bank else None


def collect_instructions(
    rom: bytes,
    bank: int,
    start: int,
    end: int,
    *,
    force_m16_at: set[tuple[int, int]],
    force_m8_at: set[tuple[int, int]],
    force_x16_at: set[tuple[int, int]],
    force_x8_at: set[tuple[int, int]],
) -> list[Instruction]:
    state = CpuState()
    address = start
    instructions: list[Instruction] = []
    while address < end:
        key = (bank, address)
        if key in force_m16_at:
            state.m8 = False
        if key in force_m8_at:
            state.m8 = True
        if key in force_x16_at:
            state.x8 = False
        if key in force_x8_at:
            state.x8 = True
        decoded = decode_instruction(rom, bank, address, state)
        instructions.append(
            Instruction(
                address=address,
                size=decoded.size,
                text=operand_width_suffix(decoded.text, decoded.raw),
                raw=decoded.raw,
            )
        )
        address += decoded.size
    if address != end:
        raise SystemExit(f"Decode ended at {bank:02X}:{address:04X}, not requested end {bank:02X}:{end:04X}")
    return instructions


def render_module(
    bank: int,
    start: int,
    end: int,
    name: str,
    instructions: list[Instruction],
    *,
    title: str,
    symbols: dict[str, str],
    entry_labels: dict[int, str],
) -> str:
    labels: dict[int, str] = {start: f"{bank:02X}{start:04X}_{name}"}
    instruction_addresses = {instruction.address for instruction in instructions}
    for key, label_name in entry_labels.items():
        label_bank = (key >> 16) & 0xFF
        label_address = key & 0xFFFF
        if label_bank == bank and start <= label_address < end:
            labels[label_address] = f"{bank:02X}{label_address:04X}_{label_name}"
    for instruction in instructions:
        target = branch_target(instruction.text)
        if target is None:
            target = same_bank_long_call_target(instruction.text, bank)
        if (
            target is not None
            and start <= target < end
            and target in instruction_addresses
        ):
            labels.setdefault(target, f"{bank:02X}{target:04X}_{name}_L{target:04X}")

    body_text = "\n".join(instruction.text for instruction in instructions)
    external_replacements = dict(BASE_SYMBOLS)
    external_replacements.update(symbols)
    used_symbols = {
        raw: name
        for raw, name in external_replacements.items()
        if raw in body_text
    }

    out = [
        f"; EarthBound {bank:02X} {title}.",
        ";",
        "; Source-emission status:",
        "; - Prototype level: build-candidate",
        "; - Generated by tools/emit_linear_source_module.py from a state-aware",
        ";   linear ROM decode, then intended for byte-equivalence validation.",
        ";",
        "; Source units covered:",
        f"; - {bank:02X}:{start:04X}..{bank:02X}:{end:04X} {name}",
        "",
        "; ---------------------------------------------------------------------------",
        "; External contracts used by this module",
        "",
    ]
    if used_symbols:
        width = max(len(name) for name in used_symbols.values())
        for raw, symbol_name in sorted(used_symbols.items(), key=lambda item: int(item[0][1:], 16)):
            out.append(f"{symbol_name:<{width}} = {raw}")
    else:
        out.append("; No named external contracts were supplied or recognized.")
    out.extend(["", "; ---------------------------------------------------------------------------", f"; {bank:02X}:{start:04X}", ""])

    all_replacements = dict(used_symbols)
    for instruction in instructions:
        if instruction.address in labels:
            out.append(f"{labels[instruction.address]}:")
        text = asar_operand_syntax(instruction.text)
        target = branch_target(text)
        if target is None:
            target = same_bank_long_call_target(text, bank)
        if target is not None and target in labels:
            mnemonic, _operand = text.split(" ", 1)
            text = (
                f"{mnemonic}.w {labels[target]}"
                if mnemonic in {"jmp", "jsr"}
                else f"{mnemonic} {labels[target]}"
            )
        elif target is not None and " " in text and text.split(" ", 1)[0] in BRANCHES:
            raw_bytes = ", ".join(f"${byte:02X}" for byte in instruction.raw)
            out.append(f"    db {raw_bytes}")
            continue
        for raw, replacement in all_replacements.items():
            text = text.replace(raw, replacement)
        out.append(f"    {text}")
    return "\n".join(out).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Emit a linear ca65-like source module from ROM bytes.")
    parser.add_argument("start", type=parse_cpu_address)
    parser.add_argument("end", type=parse_cpu_address)
    parser.add_argument("--name", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rom")
    parser.add_argument("--force-m16-at", action="append", default=[])
    parser.add_argument("--force-m8-at", action="append", default=[])
    parser.add_argument("--force-x16-at", action="append", default=[])
    parser.add_argument("--force-x8-at", action="append", default=[])
    parser.add_argument("--symbol", action="append", default=[], help="additional symbol mapping, NAME=$ADDR")
    parser.add_argument("--label", action="append", default=[], help="semantic label mapping, C4:1234=Name")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    start_bank, start_address = args.start
    end_bank, end_address = args.end
    if start_bank != end_bank:
        raise SystemExit("range must stay in one bank")
    rom = load_rom(find_rom(args.rom))
    instructions = collect_instructions(
        rom,
        start_bank,
        start_address,
        end_address,
        force_m16_at=parse_address_list(args.force_m16_at),
        force_m8_at=parse_address_list(args.force_m8_at),
        force_x16_at=parse_address_list(args.force_x16_at),
        force_x8_at=parse_address_list(args.force_x8_at),
    )
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render_module(
            start_bank,
            start_address,
            end_address,
            args.name,
            instructions,
            title=args.title,
            symbols=parse_symbol_list(args.symbol),
            entry_labels=parse_label_list(args.label),
        ),
        encoding="utf-8",
    )
    print(f"Wrote {output.relative_to(ROOT).as_posix()} with {len(instructions)} instruction(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
