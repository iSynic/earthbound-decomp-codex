# Display-Text Dynamic Source Selector Dispatch (`C1:7B56-C1:866D`)

This note captures the current best local model for the `C1:7B56..866D`
display-text dynamic source selector corridor.

See also:

- [class2-c1-display-text-substitution-handler-7af3.md](notes/class2-c1-display-text-substitution-handler-7af3.md)
- [text-command-family-1a-menus.md](notes/text-command-family-1a-menus.md)
- [text-command-15-compressed-bank-1-pseudo-opcode.md](notes/text-command-15-compressed-bank-1-pseudo-opcode.md)
- [text-command-16-compressed-bank-2-pseudo-opcode.md](notes/text-command-16-compressed-bank-2-pseudo-opcode.md)
- [text-command-17-compressed-bank-3-pseudo-opcode.md](notes/text-command-17-compressed-bank-3-pseudo-opcode.md)

## Source Promotion Status

- Promoted to decoded assembly source:
  - `src/c1/c1_7b56_dispatch_display_text_dynamic_source_selector.asm` (`C1:7B56..C1:866D`)
- Intended validation:
  - `python tools\\validate_source_bank_byte_equivalence.py --bank C1 --module all --combined --scaffold src\\c1\\bank_c1_helpers_asar.asm --strict`

## Entry Points

- `C1:7B56` = `DispatchDisplayTextDynamicSourceSelector`

## High-level Behavior (Current Read)

- The first local routine at `C1:7B56` is a narrow dispatcher that branches on
  small selector values and routes into a menu/selection-oriented helper set.
  The best current map is recorded in `notes/text-command-family-1a-menus.md`.
- The broader corridor through `C1:866D` decodes cleanly as linear 65816 code
  (no embedded tables required for byte-equivalence), but most internal helper
  entry points remain intentionally conservatively named until more callers are
  documented.

