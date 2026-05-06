# EF Battle Text Row-Pointer Recovery Frontier

This note captures the exact evidence gap behind the remaining
`D5:7B68` row-message frontier. It is scoped to EF battle-text naming and the
C1/C2 consumer contract; it does not promote D5 source or edit C1/C2.

## Current Local Blocker

The current checkout does not contain enough local row bytes to recover new
row `+4` action-message pointers directly:

- `src/d5/table_battle_action_table.asm` proves the table span
  `D5:7B68..D5:8A50`, row count `318`, and stride `0x0C`, but preserves the
  table as a data gap rather than checked-in row bytes.
- `tools/inspect_battle_action.py` can recover row metadata, row `+4` message
  pointer, row `+8` C2 behavior pointer, and a short text preview, but it needs
  a local ROM.
- In this checkout, `python tools/inspect_battle_action.py 32` fails because no
  ROM is present at `EarthBound (USA).sfc` or `baserom/EarthBound (USA).sfc`.
- The older `refs/eb-decompile-4ef92/battle_action_table.yml` reference path is
  not present in this worktree, so it cannot supply row metadata here either.

That means the remaining frontier should stay framed as pointer recovery rather
than EF source renaming.

## Recovery Command

Once a local ROM is available, run targeted row inspections first:

```powershell
python tools\inspect_battle_action.py 10
python tools\inspect_battle_action.py 31
python tools\inspect_battle_action.py 32
python tools\inspect_battle_action.py 35
python tools\inspect_battle_action.py 48
python tools\inspect_battle_action.py 49
python tools\inspect_battle_action.py 64
python tools\inspect_battle_action.py 65
python tools\inspect_battle_action.py 95
python tools\inspect_battle_action.py 98
python tools\inspect_battle_action.py 119
python tools\inspect_battle_action.py 134
python tools\inspect_battle_action.py 251
python tools\inspect_battle_action.py 258
```

For a focused behavior-body scan, use the code-address selector:

```powershell
python tools\inspect_battle_action.py C2:9AC6 --limit 8
python tools\inspect_battle_action.py C2:9AD8 --limit 8
python tools\inspect_battle_action.py C2:8F21 --limit 8
python tools\inspect_battle_action.py C2:9033 --limit 24
python tools\inspect_battle_action.py C2:A821 --limit 8
```

Record each recovered row as:

- row id
- row `+0..+3` direction/target/type/cost metadata
- row `+4` message pointer and bank
- row `+8` C2 behavior pointer
- secondary result scripts emitted by the behavior body

## Inspection Output Triage

Sort each recovered row into exactly one row-message bucket before editing any
EF source label:

| Bucket | Condition | Follow-up |
| --- | --- | --- |
| Proved EF row message | Row `+4` points to `EF:*` and row `+8` is known | Add or update the concrete row table in `notes/ef-battle-text-row-message-crosswalk.md`. |
| Non-EF row message | Row `+4` points to `C7:*`, `C8:*`, or `C9:*` | Add or update the non-EF row-message lane table; do not create EF anchors. |
| Result-only EF emission | Row `+4` is unknown/non-EF, but row `+8` emits `EF:*` through `DC1C`/`DC66` | Document the EF script as a direct/amount result payload, not a row message. |
| Still behavior-only | Row `+8` behavior is known, but row `+4` is not recovered | Keep the row in this frontier. |

Use `notes/ef-battle-text-consumer-lane-contracts.md` as the lane decision
table when a recovered row looks ambiguous.

## First Rows To Recover

Recover these before any broader action-table sweep:

| Priority | Rows | Why they matter |
| ---: | --- | --- |
| `1` | `32..35` | Lifeup/healing bodies are known, but the PSI-side row `+4` action messages are not locally joined. |
| `2` | `95..98`, `48`, `49`, `96`, `233`, `234` | Numeric-effect bodies and C8 amount-result lanes are known; row messages are still unrecovered. |
| `3` | `64`, `65` | Explosive behavior is known and nearby EF flavor text exists, but exact row messages are not proved. |
| `4` | `119..134`, `186..188`, `257`, `260..266` | `C2:9033` no-op flavor rows need row-message pointers to separate pure presentation from missing mechanics. |
| `5` | `251..258` | Neighboring tiny no-op tails need row-message pointers and bank classification. |

## Lifeup Caution

Rows `32..35` are deliberately kept in the pointer-recovery frontier even though
several neighboring PSI rows already use `EF:8543`:

- local notes prove `EF:8543` for early PSI examples such as rows `10..31` and
  later PSI-status rows `53` and `58`;
- local C2 notes prove the Lifeup behavior wrappers at `C2:9AC6`, `C2:9ACF`,
  `C2:9AD8`, and `C2:9AE1`;
- no current local note proves the row `+4` message pointer for Lifeup rows
  `32..35`;
- EF Lifeup explanation text at `EF:5173..51BB` and enemy-action flavor text
  at `EF:8D4C` are separate anchors and should not be treated as row `32..35`
  presentation messages without table evidence.

This is exactly the kind of case where the row `+8` behavior body is strong,
but the `C1:DD9F` presentation text still needs the row `+4` pointer.

## Promotion Rules

Use the recovered row `+4` bank to decide the follow-up:

- `EF:*`: add the row to `notes/ef-battle-text-row-message-crosswalk.md` only
  when the row id, EF message pointer, and row `+8` behavior pointer are all
  known.
- `C7:*`, `C8:*`, or `C9:*`: add the row to the non-EF row-message lane table;
  do not create or rename EF anchors for it.
- Behavior body emits `EF:*` through `DC1C` or `DC66`: document that as a
  secondary result payload, not as the row `+4` action-message pointer.
- Behavior body emits C8/C9 amount or narrative text: keep the row-message
  anchor conservative and point the result lane to the C2-focused note.

## Source Boundary

Do not promote D5 source data or regenerate broad table docs as part of an EF
battle-text row-message pass. If D5 table bytes are later promoted in a separate
owned pass, this EF note can consume that result, but it should not drive broad
source/manifold churn from within the EF battle-text scope.
