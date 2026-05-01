# EF Debug Menu Controller And Loader `EF:D6D4..DABD`

## Main Result

`EF:D6D4..DABD` now has a cleaner source/data split:

- `EF:D6D4..EF:D8B5` is decoded source for the debug sound-menu controller.
- `EF:D8B5..EF:D95E` is the reference-backed main debug menu option string
  block.
- `EF:D95E..EF:DABD` is decoded source for debug menu graphics loading,
  palette refresh, and state initialization.

The remaining mixed corridor now begins at `EF:DABD`, where the shared debug
menu text/number drawing helpers start.

## Routines

- `EF:D6D4` = `RunDebugSoundMenuController`
  - Polls debug menu input.
  - Moves between BGM, SE, and effect rows.
  - Updates the displayed row cursor through `$0BCA`.
  - Calls the C0 sound-preview/commit helpers for the selected row.
  - The source now names the controller row scratch at `$02`, window index at
    `$04`, input masks from `$0069/$006D`, BGM/SE/effect state bytes
    `$B54B/$B54D/$B54F`, saved temporary BGM byte `$B545`, and wrap ranges for
    BGM (`0x01..0xBF`), SE (`0x01..0x7F`), and effect (`0x01..0x20`).
- `EF:D95E` = `LoadDebugMenuGraphicsAndPalette`
  - Clears presentation state.
  - Loads the debug menu font from `EF:EB5F`.
  - Queues the debug tile transfer and optionally copies the palette/source
    block at `EF:EF9F`.
- `EF:D9F3` = `RefreshDebugMenuGraphicsIfNeeded`
  - Refreshes the debug menu graphics path when `$B559` requests it, otherwise
    refreshes the window flavor palette.
- `EF:DA05` = `InitializeDebugMenuStateAndGraphics`
  - Clears debug menu state fields.
  - Initializes tilemap/layer regions.
  - Copies the late EF debug data block at `EF:F1BB`.
  - Allocates the debug cursor/sprite slot state.

## Data

`EF:D8B5..EF:D95E` matches
`refs/ebsrc-main/ebsrc-main/src/data/debug/menu_option_strings.asm`, including
the visible strings:

- `MOTHER2 ROM  1994/07/09  VERSION`
- `DEBUG MENU`
- `1 GAME`
- `2 VIEW MAP`
- `3 VIEW CHARACTER`
- `4 VIEW ATTRIBUTE`
- `5 SHOW BATTLE`
- `6 CHECK POSITION`
- `7 SOUND MODE`

## Boundary Notes

The controller ends with `PLD; RTL` at `EF:D8B3..EF:D8B4`, so the string block
starts at `EF:D8B5`. Stopping at `EF:D8B4` would accidentally treat the final
`RTL` byte as string data.

The next preserved seam starts at `EF:DABD`, which is the shared debug menu
text-line helper used by the earlier sound-menu row renderer.

## Current Validation

The debug sound-menu controller source remains byte-equivalent after the
semantic alias pass:

```powershell
python tools\build_source_bank_scaffold.py --bank EF
python tools\validate_source_bank_byte_equivalence.py --bank EF --module all --combined --scaffold src\ef\bank_ef_helpers_asar.asm --strict
```

Result: `EF byte-equivalence: OK, 28 module(s), 0 mismatch(es).`
