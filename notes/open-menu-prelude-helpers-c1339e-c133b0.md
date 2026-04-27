# Open Menu Prelude Helpers (`C1:339E-C1:33B0`)

This note covers the three remaining unknown starts between the named `CHECK` routine and the named `OPEN_MENU_BUTTON` / `OPEN_MENU_BUTTON_CHECKTALK` includes in reference bank `01`.

The reference symbols name only the first two:

- `C1:339E` / `UNKNOWN_C1339E`
- `C1:33A7` / `UNKNOWN_C133A7`
- `C1:33B0`

## Main result

These routines are menu-entry preparation helpers.

Source-scaffold promotion:

- `C1:339E..33A7` is now decoded source in
  `src/c1/c1_339e_build_check_menu_entries_wrapper.asm`.
- `C1:33A7..33B0` is now decoded source in
  `src/c1/c1_33a7_build_open_menu_entries_wrapper.asm`.
- `C1:33B0..4103` is now decoded source in
  `src/c1/c1_33b0_rebuild_open_menu_text_entry_records.asm`.
- The promoted source validates through the durable C1 scaffold:
  `C1 byte-equivalence: OK, 172 module(s), 0 mismatch(es).`

## Working Names

- `C1:339E` = `BuildCheckMenuEntriesWrapper`
- `C1:33A7` = `BuildOpenMenuEntriesWrapper`
- `C1:33B0` = `RebuildOpenMenuTextEntryRecords`

- `C1:339E` is a tiny wrapper around `C1:98DE` with `X = 2`.
- `C1:33A7` is the same wrapper with `X = $2C`.
- `C1:33B0` rebuilds the active menu text-entry records from debug/menu option tables and then refreshes the entry chain through `C1:163C`.

## Two Narrow Dispatch Wrappers

`C1:339E`:

```asm
REP #$31
LDX #$0002
JSR C1:98DE
RTL
```

`C1:33A7`:

```asm
REP #$31
LDX #$002C
JSR C1:98DE
RTL
```

`C1:98DE` is now source-backed as `RenderCharacterInventoryOrEquipmentRows` inside `src/c1/c1_9437_close_target_selection_prompt_label.asm`. It is the broader menu/text construction helper already seen from text command family `0x1A`. These two starts are therefore not independent systems; they are fixed-argument entry points into the existing menu builder.

## Menu Entry Record Builder

`C1:33B0` exits early if `$5E6C` is already nonzero, otherwise it walks menu selector values `1..6` and installs typed text-entry records with `C1:1596`.

For each selector it:

- skips selector `3` when `C1:C373` returns zero
- chooses a metadata byte of `1` for selectors `1`, `5`, and some selector-`2` cases, otherwise `$1B`
- uses selector - 1 as an index into `C3:E964`, which the reference data names `DEBUG_MENU_ELEMENT_SPACING_DATA`
- uses the same index into a ten-byte row table rooted at `EF:A37A`
- passes the derived source pointer, display byte, and type byte into `C1:1596`

The selector-`2` special case checks `$98A4` and `$986F`, then calls `C3:E977`. Existing notes now identify `$98A4` as the active party-member count and `$986F` as the active overworld entity-type source array, so this branch is likely deciding whether a party-dependent menu option gets the compact metadata byte.

The routine ends by clearing `$5E6C` and calling `C1:163C`, matching the active-entry-chain refresh path documented with the `$89D4` text-entry records.

## Why this belongs with Open Menu

The reference include order is the useful external corroboration:

```asm
.INCLUDE "overworld/check.asm"
.INCLUDE "unknown/C1/C1339E.asm"
.INCLUDE "unknown/C1/C133A7.asm"
.INCLUDE "unknown/C1/C133B0.asm"
.INCLUDE "overworld/open_menu.asm"
```

Mechanically, the code also matches that placement. It does not read controller state or run the open-menu state machine itself; it prepares the menu-visible records that the following open-menu routines consume.

## Practical Conclusion

`C1:339E`, `C1:33A7`, and `C1:33B0` are now covered as open-menu prelude helpers: two fixed-argument calls into `C1:98DE`, plus a local menu-entry record rebuild over the debug/menu option tables. The adjacent `C1:34A7..4103` body is also source-backed now, tying those prepared records to the open-menu selection loop, the checking-object path at `C1:3C32`, and the small name-entry pointer helpers at `C1:4012`, `C1:4049`, and `C1:4070`.
