# Text Command Family `1C`: Print / Display

This note is the top-level overview for bank-`01` text command family `0x1C`.

See also [jeff-repair-item-name-bridge.md](notes/jeff-repair-item-name-bridge.md).

## Main result

The safest current local read is that `0x1C` is the broad bank-`01` print / display family.

In the live parser path, top-level command byte `0x1C` dispatches through `C1:8AE4`, which installs callback low word `C1:7D94`. The body at `C1:7D94` then dispatches on the one-byte `0x1C` subselector in `X`.

## Best current family shape

The currently strongest pinned `0x1C` leaves are:

- `0x1C 01` -> best current fit `PRINT_STAT`
- `0x1C 02` -> best current fit `PRINT_CHAR_NAME`
- `0x1C 03` -> best current fit `PRINT_CHAR`
- `0x1C 05` -> `PRINT_ITEM_NAME`
- `0x1C 06` -> best current fit town / teleport-destination name printer
- `0x1C 07` -> best current fit horizontal text-string printer
- `0x1C 08` -> battle-only special-graphics print branch
- `0x1C 0A` -> best current fit `PRINT_NUMBER`
- `0x1C 0C` -> best current fit vertical text-string printer
- `0x1C 0D` -> strong local fit `PRINT_ACTION_USER_NAME`
- `0x1C 0E` -> strong local fit `PRINT_ACTION_TARGET_NAME`
- `0x1C 0F` -> strong local fit `PRINT_ACTION_AMOUNT`
- `0x1C 12` -> strong local fit `PRINT_PSI_NAME`
- `0x1C 13` -> strong local fit `DISPLAY_PSI_ANIMATION`
- `0x1C 14/15` -> special selector loaders used before `JUMP_MULTI`

Some edge leaves remain narrower or more cautious:

- `0x1C 09` is now named `SET_ACTIVE_WINDOW_TEXT_MODE`; it is runtime-only in the exposed `text_data` corpus, but its live write to `$8662` is pinned
- `0x1C 00` and `0x1C 0B` are real live-context setters or printers, but their exact player-facing names are still weaker than the central print paths
- `0x1C 11` is still a narrow special-selector loader without a clean final name

## Why this family matters

`0x1C` is the display side of the paired `0x1B / 0x1C` text-engine model.

The clearest local example is Jeff repair:

- `0x1B` changes live text-memory / context slots
- `0x1C 05` reads from those slots through the item-name printer
- `{swap}` plus repeated `[1C 05 00]` prints broken-item first, then repaired-item, without changing the visible item-name selector

So the best current system-level read is that `0x1C` is not a grab-bag of unrelated helpers. It is the main print/data-display family that consumes the current bank-`01` text context.

Source polish update: the `0x1C 0F` branch inside
`src/c1/c1_7b56_dispatch_display_text_dynamic_source_selector.asm` now names
the getter through `C1:AD26`, the `$9D12/$9D14` staged action-amount payload,
the handoff into `$0E/$10`, and the final `C1:0DF6` number printer. This
matches the `C1:DC66` display wrapper contract used by C2 amount-result
callers.

## Best current interpretation

The safest current interpretation is that `0x1C` is the bank-`01` print / display family, covering ordinary text substitution, item and character naming, numeric/stat printing, and a narrower battle-facing action / PSI display tail.
