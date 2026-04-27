# Nested Text Pointer + Callback Invoker Source Promotion (`C1:86B1..8B2C`)

This note records the promotion of two adjacent working-name byte corridors into decoded source modules:

- `C1:86B1..C1:87CC` `ExecuteNestedTextPointer`
- `C1:87CC..C1:8B2C` `InvokeTextEngineCallbackLowWord`

Both routines are already described semantically in earlier working-name notes:

- `C1:86B1` is the shared nested text-execution helper used by text command `0x08` (`CALL_TEXT`).
- `C1:87CC` is the bank-`01` callback step that invokes same-bank low-word handlers via an RTS-as-JSR stack trick.

See:

- [text-command-08-call-text.md](/F:/Earthbound%20Decomp%20-%20Codex/notes/text-command-08-call-text.md)
- [timed-event-callback-invoker-c187cc.md](/F:/Earthbound%20Decomp%20-%20Codex/notes/timed-event-callback-invoker-c187cc.md)

## Source modules

- `src/c1/c1_86b1_execute_nested_text_pointer.asm`
- `src/c1/c1_87cc_invoke_text_engine_callback_low_word.asm`

## Manifest intent

These two intervals are now treated as full `source` segments in the C1 build-candidate manifest so the scaffold emits assembled instructions instead of preserving the bytes as `db` data gaps.

