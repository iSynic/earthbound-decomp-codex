# Character Selection Prompt Dispatch + Core (`C1:242E-C1:2BF3`)

This note follows the earlier selection-prompt cluster note and captures the
next contiguous corridor after `C1:242E` through the boundary at `C1:2BF3`.

## Source Promotion Status

- Promoted to decoded assembly source:
  - `src/c1/c1_242e_dispatch_character_selection_prompt_mode.asm` (`C1:242E..C1:2BF3`)
- Intended validation:
  - `python tools\\validate_source_bank_byte_equivalence.py --bank C1 --module all --combined --scaffold src\\c1\\bank_c1_helpers_asar.asm --strict`

## Entry Points

- `C1:242E` = `DispatchCharacterSelectionPromptMode`
  - Dispatch wrapper described in `notes/character-selection-prompt-cluster-c11f8a-c1242e.md`.
- `C1:244C` = `CharacterSelectPrompt`
  - Second entry point inside the same promoted corridor; this routine is a
    direct `JSR` target elsewhere in bank `C1`.

## High-level Behavior (Current Read)

- `C1:242E` selects between the two existing controllers:
  - if incoming `X != 0`, it calls `C1:2362` (`RunSimpleSideSelectionPrompt`)
  - if incoming `X == 0`, it calls `C1:21B8` (`RunTwoListCharacterSelectionPrompt`)
- `C1:244C` allocates a local direct-page stack frame, binds the active
  interaction-context record via `C1:0301`, and then drives the next stage of
  the character selection prompt flow (window/tile staging + prompt printing).

This corridor clearly continues the selection-prompt family, but the precise
semantic names for all internal subroutines remain intentionally conservative
until the callers at `C1:4666` / `C1:46A8` and the surrounding menu control flow
are documented.

