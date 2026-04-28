# C3 Actionscript Callback Contracts

This note is the human front door for the callback layer now emitted by
`tools/build_c3_actionscript_semantics_audit.py`.

## Main Result

The C3 event/actionscript bytecode layer is syntactically closed, but
`EVENT_CALLROUTINE` is where the VM crosses into native game behavior. The audit
now tracks each native target with:

- preferred local name
- semantic group
- call count
- inline argument byte count
- named argument schema, where known
- current argument/behavior contract

That makes the next C3 phase a contract-polish pass instead of a blind callback
hunt.

## Current Callback Groups

The regenerated audit currently buckets `85` native callback contract seeds:

| Group | Meaning |
| --- | --- |
| `timed-delivery` | EF helpers for delivery row state, retry policy, queued pointers, and arrival/departure speeds |
| `visual-profile` | current-slot visual refresh, animation pulse, display phase, and release helpers |
| `current-slot-state` | helpers that read/write current-slot script fields, anchors, or staged values |
| `movement` | direction, angle, vector, and movement-timer helpers |
| `collision` | footprint, terrain, and neighbor-cache collision refresh helpers |
| `text-presentation` | text handoff, queued text pointer, and yield-to-text helpers |
| `presentation-render` | C4 render/presentation callbacks that support visual script effects |
| `neighbor-cache` | explicit `$289E[current_slot]` cache sentinel helpers |
| `world-state-restore` | transition/display state restore helpers |
| `party-facing` | party-look/attention callbacks |
| `battle-runtime` | C2 callbacks used by C3 event flow |
| `intro-integrity` | intro-only checksum/control-flow helper |

## Promotion From Prior Notes

The first semantic override set intentionally imports names that were already
proved elsewhere in the repository but were not flowing into C3 decodes:

- `EF:0CA7` -> `CheckCurrentDeliveryRetryThreshold`
- `EF:0D23` -> `GetCurrentDeliveryRetryWait`
- `EF:0D8D` -> `QueueCurrentDeliveryPointer1`
- `EF:0DFA` -> `QueueCurrentDeliveryPointer2`
- `EF:0E67` -> `GetCurrentDeliveryEnterSpeed`
- `EF:0E8A` -> `GetCurrentDeliveryExitSpeed`
- `EF:0F60` -> `CheckDeliveryServiceReadyForArrival`
- `EF:0FDB` -> `BeginDeliverySuccessArrivalState`
- `EF:0FF6` -> `ResetDeliveryArrivalState`
- `C4:8B3B` -> `MakePartyLookAtActiveEntityCallback`
- `C4:800B` -> `UndrawFlyoverTextAndRestoreWorldDisplay`
- `C2:0000` -> `RunEnemySunstrokeCheck`
- `C1:FFD3` -> `ComputeBankC1ChecksumTail`

The important point is not just nicer names. These names now appear directly in
decode excerpts, so script-family notes can quote the generated audit without
re-introducing older `UNKNOWN_*` labels.

## Next Contract Work

The remaining high-value work is to replace generic argument schemas such as
`arg0_byte, arg1_byte` with named fields.

Good first targets:

- `C0:5E76` collision-cache argument words
- `C0:A912`, `C0:A9B3`, `C0:A9CF`, `C0:A9EB`, `C0:AA07`, `C0:AA23`, and
  `C0:AAB5` multi-word wrapper fields
- the generic `presentation-render` wrapper names that still mirror callee
  addresses instead of final gameplay roles

Those are the contracts that will make C3 scripts genuinely source-like rather
than only byte-equivalent macro streams.
