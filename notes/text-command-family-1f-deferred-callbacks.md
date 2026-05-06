# Text Command Family `1F`: Deferred Callbacks And Event Helpers

This note is the top-level overview for bank-`01` text command family `0x1F`.

See also [timed-event-callback-family-bank01.md](notes/timed-event-callback-family-bank01.md).
See also [timed-event-callback-invoker-c187cc.md](notes/timed-event-callback-invoker-c187cc.md).
See also [try-fix-item-callback-d0.md](notes/try-fix-item-callback-d0.md).

## Main result

The safest current local read is that `0x1F` is the bank-`01` deferred-callback and event-helper family.

In the live parser path, top-level command byte `0x1F` dispatches through the bank-`01` family rooted at `C1:81BB`. The family includes both immediate helper-style leaves and deferred same-bank callback leaves that later execute through the callback invoker at `C1:87CC`.

## Best current family shape

The strongest currently pinned members are:

- `0x1F 00` -> queue or apply a music track through `C2:16AD`
- `0x1F 01` -> stop music through `C2:16C9`
- `0x1F 02` -> play a sound/effect through `C2:16D0`, then tick the light
  window path through `C1:2E42`
- `0x1F 03` -> restore map music from the current-position music id via
  `C0:69F7` and `C2:16AD`
- `0x1F 40` -> stage the one-byte special-event argument used by the adjacent
  special-event dispatcher path
- `0x1F 41` -> special-event dispatcher, with local wrapper at `C1:72DA` and
  main dispatcher at `C1:BEFC`
- `0x1F 60` -> wait for the text prompt / system input gate through `C1:00FE`
- `0x1F 64` -> save and clear the temporary party source state through
  `C2:3008`
- `0x1F 65` -> restore the temporary party source state through `C2:307B`
- `0x1F 81` -> direct item-use compatibility check through `C1:4F6F`
- `0x1F 90` -> phone-contact selection menu builder through `C1:9441`
- `0x1F A0` -> set the current interaction flag id at `$9C88`, then refresh
  target state from `$5D64` through the C2 wrapper at `C2:26C5/26D0`
- `0x1F A1` -> clear the current interaction flag id at `$9C88`, then refresh
  target state from `$5D64` through the same C2 wrapper
- `0x1F A2` -> read the current interaction flag id at `$9C88` through
  `C2:26E6/26EB` and return it through the text context
- `0x1F B0` -> save the currently selected game slot through `C2:2A2C` and
  `EF:0A4D`
- `0x1F D0` -> Jeff repair / broken-item callback family
- `0x1F D1` -> immediate nearby magic-truffle direction helper
- `0x1F D2` -> strongest current fit wandering-photographer summon branch
- `0x1F D3` -> timed-delivery callback branch

## Source scaffold promotion

The large `C1:621F..7274` callback corridor is now decoded source in `src/c1/c1_621f_finalize_text_command1_fc0_jump_multi2_target.asm`. That source covers the hidden `1F C0` / `JUMP_MULTI2` finalizer, Jeff repair's `D0` branch, several low-word event-helper leaves in the `0x1F 13..1F` and `E1..F2` bands, and the nearby `1F 04/62/63/66/67` leaves.

Source polish follow-up (2026-05-06): the same `C1:621F..7274` corridor now
has no raw helper-call edges. The source names the JUMP_MULTI2 dword builder's
shift helpers, Jeff repair's C3/C1 repair-result pair, the C1 text-mode latch,
the C0 hotspot/movement queue joins, the C2 scripted-battle bridge, and the C4
entity frame, flag, script, attached-child, visual-record, and landing-profile
helpers by contract name.

The lower `C1:461A..4819` text-command source now also names the nearby
`1F 00..02` music/sound leaves, and the dynamic source-selector corridor names
the `1F 03` restore-current-map-music branch. These leaves call the C2 music
track, stop-music, and play-sound/light-window wrappers by contract names
instead of raw far addresses.

The same dynamic source-selector corridor now names the `1F 64/65` temporary
party source save/restore leaves. These call `C2:3008` and `C2:307B`, the
matched C2 helpers that preserve `$983A/$983B/$983C/$983E/$9831/$9833`, remove
the active source ids from `$986F`, and later restore the saved ids and words.

It also names the `1F A0/A1/A2` current-interaction flag leaves. The set/clear
pair stages `1` or `0` into `C2:26C5`, which falls through to the C2 refresh
tail that uses `$9C88` and `$5D64`; the read leaf calls `C2:26E6` and stages
the returned flag state into the active text context.

The `1F B0` save-game leaf now calls the C2 `SaveCurrentGame` wrapper by name.
That wrapper reads the one-based current save slot at `$B4A1`, converts it to
the zero-based slot index expected by `EF:0A4D`, and delegates to the EF
save-slot helper. This matches the recovered authoring hint for `@SAVE_GAME`.

The adjacent `C1:7274..7440` corridor is now decoded source in `src/c1/c1_7274_stage_bank_deposit_accumulator_text_value.asm`. It covers `1F 40`, `1F 41`'s local special-event-dispatch wrapper, `1F D2`'s wandering-photographer helper bridge, `1F F3/F4`, the `C1:73C0` battle visual result stager, and `1F 07`. The `C1:7440` timed-delivery callback adapter itself is now decoded source in `src/c1/c1_7440_timed_delivery_row_selector_callback.asm`. The combined C1 scaffold validates byte-for-byte after promotion: `C1 byte-equivalence: OK, 172 module(s), 0 mismatch(es).`

The `C1:7274..7440` sibling source now names its helper edges as well: the
special-event dispatcher, wandering-photographer C4 helper, pose-descriptor
attached-child spawn/clear helpers, battle visual effect token dispatcher, and
shared context installers are all explicit in source.

The immediate `0x1F D1` branch's target is now semantically polished in
`src/c4/nearby_truffle_and_landing_profile_interpolation_helpers.asm`. The C4
source names the magic-truffle pose descriptor, missing-slot sentinel,
out-of-range and too-close return values, player/live-entity world coordinate
fields, range gates, and octant rounding contract before returning the
direction code to the text-command caller.

The most concretely proved deferred branch is `0x1F D3`:

- script uses `[1F D3 xx]`
- bank `01` resolves the leaf to low word `C1:7440`
- `C1:87CC` invokes that low word with an RTS-as-JSR same-bank callback step
- `C1:7440` forwards `X` into `EF:0EAD`

The callback interface is now locally pinned too:

- callback low word comes from `Y`
- `X` is loaded from `$14`
- `$14` is the first byte fetched from the callback payload stream at `C1:87A7`

So for timed delivery, the payload byte after `0x1F D3` becomes the 1-based delivery row selector.

## Why this family matters

`0x1F` is broader than a timed-delivery-only mechanism.

The manager around `C1:80B2` selects among several small same-bank low-word workers, and the surrounding queue state comes from ordinary bank-`01` text-command machinery such as `$97BA/$97CA`. That makes the family read much better as a deferred text-command callback framework with a few immediate neighboring event helpers, not as one private delivery-state machine.

This matters because it explains why very different gameplay-side effects can share one command family:

- timed delivery
- Jeff repair
- magic-truffle direction
- wandering photographer

They are all being routed through the same bank-`01` deferred-callback / event-helper machinery.

## Best current interpretation

The safest current interpretation is that `0x1F` is the bank-`01` deferred callback family, with same-bank low-word workers executed later by `C1:87CC`, plus a few closely related immediate event-helper branches in the same top-level family.
