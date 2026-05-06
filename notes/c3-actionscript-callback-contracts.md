# C3 Actionscript Callback Contracts

This note is the human front door for the callback layer now emitted by
`tools/build_c3_actionscript_semantics_audit.py`.

## Main Result

The C3 event/actionscript bytecode layer is syntactically closed. Native
behavior enters the script VM in two different ways:

- `EVENT_CALLROUTINE` reads inline script arguments, calls a native helper, and
  returns a condition/result to the script.
- callback installers such as `EVENT_SET_TICK_CALLBACK`,
  `EVENT_SET_POSITION_CHANGE_CALLBACK`, and `EVENT_SET_PHYSICS_CALLBACK` bind
  per-frame native behavior that keeps running after the current instruction.

The audit now tracks each `EVENT_CALLROUTINE` native target with:

- preferred local name
- semantic group
- call count
- inline argument byte count
- named argument schema, where known
- current argument/behavior contract

It also tracks installed callback targets separately with preferred local names,
semantic groups, install counts, and first-pass behavior contracts. That makes
the next C3 phase a contract-polish pass instead of a blind callback hunt.

## Current Callback Groups

The regenerated audit currently buckets `86` `EVENT_CALLROUTINE` contract seeds
and `17` installed callback targets:

| Group | Meaning |
| --- | --- |
| `timed-delivery` | EF helpers for delivery row state, retry policy, queued pointers, and arrival/departure speeds |
| `visual-profile` | current-slot visual refresh, animation pulse, display phase, and release helpers |
| `current-slot-state` | helpers that read/write current-slot script fields, anchors, or staged values |
| `movement` | direction, angle, vector, and movement-timer helpers |
| `collision` | footprint, terrain, and neighbor-cache collision refresh helpers |
| `entity-spawn` | script helpers that spawn or initialize entities from current-slot context |
| `text-presentation` | text handoff, queued text pointer, and yield-to-text helpers |
| `presentation-render` | C4 render/presentation callbacks that support visual script effects |
| `neighbor-cache` | explicit `$289E[current_slot]` cache sentinel helpers |
| `world-state-restore` | transition/display state restore helpers |
| `party-facing` | party-look/attention callbacks |
| `battle-runtime` | C2 callbacks used by C3 event flow |
| `intro-integrity` | intro-only checksum/control-flow helper |

The installed callback signal is now explicit in
`notes/c3-actionscript-semantics-audit.md`. The top installed targets are the
movement/presentation callbacks scripts repeatedly bind for entity motion and
screen placement: `C0:A37A`, `C0:9FC8`, `C0:A360`, `C0:A039`, `C4:8BE1`,
`C0:9FF0`, `C4:8C2B`, and `C0:9FF1`.

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
- `C0:A039` -> `ReturnFromPositionChangeCallback_NoProjection`
- `C0:9FF0` -> `ReturnFromPhysicsCallback_NoMovement`
- `C4:8BE1` -> `SimpleScreenPositionCallback`
- `C4:8C02` -> `SimpleScreenPositionCallbackOffset`
- `C4:8C2B` -> `CentreScreenOnEntityCallback`

The important point is not just nicer names. These names now appear directly in
decode excerpts, so script-family notes can quote the generated audit without
re-introducing older `UNKNOWN_*` labels.

## Source-Pilot Attention Helpers

Several callback contracts now feed the C3 source-pilot frontier even when they
do not change the current source-map audit row set:

- `C0:C48F` -> `GateWidePlayerDistanceBucket`: a wide player-distance gate
  proved in `notes/pathfinding-consumers-direction-helpers-c0bd96-c0c7db.md`.
  C3 attention scripts use it as the wait/engage boundary before direction or
  route handoff.
- `C0:D77F` -> `MarkOtherSlotsAttentionLocked`: marks other eligible slots'
  attention/interaction flags before scripted object-interaction cleanup.
- `C0:D7B3` -> `Save_CurrentSlotAttentionPosition`: snapshots the current slot
  position into the NPC-attention saved-position fields.
- `C0:D7C7` -> `Restore_CurrentSlotAttentionPosition`: restores that saved
  NPC-attention position back to the current slot.
- `C0:D7E0` -> `Normalize_CurrentSlotAttentionState`: collapses a nonzero
  current-slot attention marker to state `1`.

The `C0:D77F/D7B3/D7C7/D7E0` contracts are imported from
`notes/npc-attention-path-coordinator-c0d19b-c0d98f.md`. They unblock the
bus-driver and compact NPC-attention pilots without promoting any C0 runtime
implementation into C3 ownership.

## Cast-Scroll Source-Pilot Wrappers

The large event-801 cast-scroll pilot now has field-shaped wrappers for its
high-volume C0 helper calls:

- `C0:A99F` -> `SpawnEntityRelative_ReadTwoWords`: reads visual-type and
  initializer words, then calls the C4 cast-scene spawn helper that combines
  staged script `var0/var1` with the live BG3 scroll.
- `C0:A9B3` -> `PrintCastNameParty_ReadThreeWords`
- `C0:A9CF` -> `PrintCastNameEntityVar0_ReadThreeWords`
- `C0:A9EB` -> `PrintCastNameCurrentThreshold_ReadThreeWords`

Those cast-name helpers render as
`cast_name_source_word, cast_name_tile_x_word, cast_name_tile_y_word`; the
entity spawner renders as `entity_visual_type_word, entity_initializer_word`.
The contracts are imported from the C0 wrapper strip and
`notes/cast-scene-scroll-helpers-c4e4da-c4e583.md`, then applied only as C3
decoder/source-pilot metadata.

Source polish: `src/c4/actionscript_camera_and_screen_position_callbacks.asm`
now names the current-slot index, action-script callback flag bit, active
entity registry scan tables/count, live world/screen/offset coordinate tables,
camera origin pair, facing-direction table, and half-octant rounding constants
used by the party-look and screen-position callbacks.

## Operand Labels In Decodes

`tools/decode_event_script.py` now also prints first-pass operand field labels
for the most common event/actionscript VM operands. For example, generated
decode excerpts use `script_var=var4`, `frames=$08`, `animation_id=$01`, and
named callback arguments such as `event_flag_word=$000C` or
`neighbor_cache_callback_long=$C0:64A6 <...>`.

Pointer-shaped operands are labeled too. Short branches/calls now distinguish
`jump_target`, `call_target`, `conditional_call_target`, and
`inverted_conditional_call_target`; task launchers use `task_script`; callback
installers use `tick_callback`, `draw_callback`, `position_change_callback`,
and `physics_callback`. The audit renders this as an opcode operand catalog so
port/reassembler work can separate byte width from VM role without reading the
Python decoder first.

The decoder also applies a deliberately small value-symbol layer where the
evidence is already bank-local or cross-referenced:

- mutation operation bytes use the C0 interpreter table names:
  `$00 <AND>`, `$01 <OR>`, `$02 <ADD>`, `$03 <EOR>`
- `$5D9A` is shown as `queue_pending_or_special_state_flag`, matching the C0/EF
  queue and transient special-state notes
- velocity and relative-position words show signed decimal meaning beside the
  raw hex value
- the generated audit now has a direction callback boundary table: C3 tempvar
  writes or `C0:9F82` random-choice word lists are counted as direction values
  only when they reach `C0:A65F` and, for movement-vector cases, `C0:C83B`
  inside the same decoded source-map span
- the same audit now records `$2B32` movement magnitudes from `C0:A685` only
  when the decoded span carries them into movement-vector or timer consumers
  such as `C0:C83B`, `C0:CA4E`, `C0:A6A2`, `C0:A6AD`, or `C0:CBD3`

This is intentionally a readability layer, not a new byte format. The raw bytes
remain printed on every decoded line, and the source-pilot emitters still
revalidate against the ROM byte-for-byte.

## Good-Enough Boundary

C3 is good enough for this milestone when generated reports are truthful and
useful, not when every literal has a perfect story. Animation ids, direction
classes, and per-family variable meanings should stay literal unless a local
script family or native callback proves the symbolic meaning. That keeps the
decoder from laundering guesses into source.

## Next Contract Work

The current audit has no remaining generic `argN_byte` schemas among the C3
callback seeds. The last awkward case, `C0:5E76`, is now named using the ebsrc
macro shape:

```asm
EVENT_UNKNOWN_C05E76 $F1, UNKNOWN_C064A6
```

That means the remaining C3 callback work is semantic polish rather than byte
shape discovery. The live C3 wrapper seeds have already absorbed the C4 names
for current-slot stepping, facing other resolved slots toward the current slot,
area-bounds setup, current-anchor entity spawning, screen-position callbacks,
and passive no-op callback returns.

Good next targets:

- move to the next milestone with the current C3 semantics as the baseline
- return later only for targeted, evidence-backed constants or localization
  crosswalk improvements
- continue naming unused C0 wrapper entries as broader C0 polish unless they
  appear in the C3 callback audit

Those refinements will make C3 scripts more readable to ROM hackers without
changing the already byte-equivalent source scaffold.
