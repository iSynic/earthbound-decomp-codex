# EF Battle Text Consumer Lane Contracts

This note is the compact EF-side contract for how C1 display wrappers and C2
action/result bodies consume battle text. It is intentionally about lanes and
payload semantics, not EB text macro decoding.

Primary companions:

- `notes/ef-battle-text-row-message-crosswalk.md`
- `notes/ef-battle-text-row-pointer-recovery-frontier.md`
- `notes/ef-battle-text-action-island-consumer-frontier.md`
- `notes/c2-ef-battle-text-contract-workahead.md`

## Lane Summary

| Lane | Entry point | Producer | Text pointer source | Payload consumed by text |
| --- | --- | --- | --- | --- |
| Row presentation | `C1:DD9F` | `C2:5C66` | `D5:7B68` row `+4` | Optional script-local commands such as PSI byte substitution |
| Direct result | `C1:DC1C` | C2 behavior bodies | Hardcoded EF/C8/C9 pointer staged in `$0E/$10` | None beyond ordinary text context |
| Amount result | `C1:DC66` or direct C1 staging | C2 behavior bodies or C1 level-up leaves | Hardcoded EF/C8/C9 pointer staged in `$0E/$10`, or fixed EF level-up pointer | Secondary payload staged through `$9D12/$9D14`, commonly consumed by `PRINT_ACTION_AMOUNT (1C 0F)` |
| Byte substitution | `C1:DD7C` then display | C2 setup/body code | Later `DC1C`/`DD9F` display target | `$9D11`, consumed by `LOAD_BYTE_SUBSTITUTION (19 1F)` |
| Pointer substitution | Usually `C1:DC66` setup | C2 setup/body code | Later display target | `$9D12/$9D14`, consumed by `LOAD_POINTER_SUBSTITUTION (19 1E)` |

The most important separation is that the row `+4` message pointer is
presentation text, while the row `+8` pointer is the C2 behavior payload. A
behavior body may emit additional result text, but that result text does not
rename the row `+4` action message by itself.

## Row `+4` Presentation Lane

`C1:DD9F` displays the action-table row message selected by `C2:5C66`. Treat
this as the only lane that proves an EF action-message anchor for a specific
`D5:7B68` row.

Promotion requirements:

- row id is known;
- row `+4` pointer is known and points into EF;
- row `+8` behavior pointer is known or already source-backed by C2 notes;
- any secondary result scripts are documented separately from the row message.

Examples:

- row `100 -> EF:7EAC -> C2:8F97` is a poison-on-hit physical row message;
  `EF:6B18` is the later poison-result script.
- row `140 -> EF:8E27 -> C2:9AD8` and row `247 -> EF:8E27 -> C2:90C6`
  intentionally reuse one EF row-message anchor with different C2 behavior
  bodies.
- rows `53` and `58` reuse shared `EF:8543` PSI `ByteSubstitution`
  presentation text, while their behavior bodies emit asleep or strange result
  text through `DC1C`.

## Direct Result Lane

`C1:DC1C` displays a pointer directly staged by C2. Use this lane for status,
miss, event, and result scripts selected by a behavior body after the row
presentation has already happened.

Examples:

- `EF:6C55`, `EF:6C3A`, `EF:6C0B`, and `EF:766E` are status success/failure
  result scripts emitted by C2 behavior bodies.
- `StatusResultText` EF anchors such as `EF:6AC7..6C55` and `EF:766E` are
  direct-result lane names; they should not be promoted as row `+4` action
  messages without separate `D5:7B68` row-pointer evidence.
- `RecoveryResultText` and `RemovalResultText` EF anchors such as
  `EF:6E4A..6F64` are the cleanup side of the same direct-result lane.
- Revive, shield, Neutralizer, and Franklin Badge anchors in `EF:6F7C..7160`
  are also direct result lane text; `EF:70D2/70FA` additionally keep the
  `ByteSubstitution` suffix because they consume the staged PSI-name byte.
- EBATTLE4 action-blocking status anchors in `EF:7186..720C` explain a blocked
  turn; the adjacent PSI-seal result at `EF:7221` is a
  `ByteSubstitutionResultText` consumer, not a row presentation anchor.
- `EF:72F6` and `EF:7415` are special-event row `+4` presentation anchors for
  rows `243` and `244`; `EF:72F7`, `EF:733D`, and `EF:743B` are the separate
  C2 behavior-emitted result continuations.
- `EF:7142` and queued `EF:7123` belong to normalization result flow, separate
  from the row `247`/`248` presentation messages.

Naming rule: direct-result scripts can receive gameplay-facing result names
when their C2 caller proves the role, even if the surrounding action-message
island remains an exact `MSG_BTL_*` anchor.

## Amount And Substitution Lanes

`C1:DC66` stages a primary text pointer plus a secondary payload. C1 level-up
leaves can also stage the same `$9D12/$9D14` amount slot through `C1:AD0A`
before dispatching a fixed EF script. EF anchors that consume this payload
should keep the `ActionAmount` suffix when the script uses
`PRINT_ACTION_AMOUNT (1C 0F)`.

Examples:

- HP/PP recovery scripts consume staged recovery amounts.
- damage, drain, stat-up, stat-down, and HP-sucker scripts consume staged
  amount payloads.
- EF periodic damage and PP-loss scripts such as `EF:7755`, `EF:7768`,
  `EF:7787`, `EF:77B1`, and `EF:77DB` are `ActionAmount` result scripts when
  emitted through `DC66`.
- EF level-up stat-gain scripts `EF:7A7D..7B46` are also `ActionAmount`
  consumers, but they are C1 level-up narration scripts rather than C2
  row-message or result emissions.
- C8 amount scripts used by numeric-effect C2 bodies are result lanes, not EF
  row-message anchors.

`C1:DD7C` stages `$9D11` for `LOAD_BYTE_SUBSTITUTION (19 1F)`. EF anchors that
consume that byte should keep the `ByteSubstitution` suffix. Present/item-name
and PSI-name examples are the current high-confidence cases: `EF:7BDF` and
`EF:7DD5` for present item names, `EF:7B77` and shared row text `EF:8543` for
PSI names, plus shield PSI-name result scripts `EF:70D2` and `EF:70FA`.

`LOAD_POINTER_SUBSTITUTION (19 1E)` consumes `$9D12/$9D14`; EF branches that
depend on that pointer should keep the `PointerSubstitution` suffix. Current
high-confidence EF branch consumers are `EF:7B85`, `EF:7BA2`, and `EF:7BC1`;
the adjacent `EF:7B83`, `EF:7BA0`, and `EF:7BBF` anchors are branch-state
separators in the same island, not the parsed `19 1E` command sites.

## Non-EF Row Messages

Some action-table row `+4` presentation messages point outside EF. Those rows
still belong to the row-message lane, but they should not create or rename EF
anchors.

Current examples:

- item healing rows `139` and `141` use the C9 item-use wrapper;
- item solidification row `166` uses a C9 item-strike wrapper, then emits EF
  success/failure result scripts;
- bomb-family item rows `167`, `168`, `310`, and `311` use C9 item
  presentation wrappers;
- Final Prayer rows `291..299` use C9 prayer presentation/narrative text.

Promotion rule: record these in the non-EF row-message lane table, then only
name EF result scripts if the C2 behavior body later emits an EF pointer.

## Do-Not-Mix Rules

- Do not rename an EF row-message anchor from row `+8` behavior alone.
- Do not treat direct `DC1C` result scripts as row `+4` presentation messages.
- Do not treat C8/C9 amount or narrative scripts as EF anchor evidence.
- Do not infer row messages from nearby English-looking EF action flavor text.
- Do not fold Lifeup rows `32..35` into the shared `EF:8543` PSI bucket until
  their row `+4` pointers are recovered.
- Do not treat Lifeup explanation text `EF:5173..51BB`, enemy Lifeup flavor
  `EF:8D4C`, or explosive flavor candidates `EF:9A7E/9A9E` as row-message
  joins for rows `32..35` or `64/65` until row `+4` pointer recovery proves
  them.
- Do not collapse no-op behavior rows into "no effect" result text; a no-op
  row `+8` body can still have meaningful row `+4` presentation text.

## Next Use

When a row pointer is recovered with `tools/inspect_battle_action.py`, classify
it in this order:

1. If row `+4` is EF, add the row to the row-message crosswalk and keep any
   behavior-emitted result scripts separate.
2. If row `+4` is C7/C8/C9, add it to the non-EF lane table and do not create
   EF anchors for it.
3. If only row `+8` behavior is known, keep it in the pointer-recovery frontier.

The recovery frontier has the concrete command list and output buckets:
`notes/ef-battle-text-row-pointer-recovery-frontier.md`.
