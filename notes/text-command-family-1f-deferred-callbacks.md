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

- `0x1F 40` -> stage the one-byte special-event argument used by the adjacent
  special-event dispatcher path
- `0x1F 41` -> special-event dispatcher, with local wrapper at `C1:72DA` and
  main dispatcher at `C1:BEFC`
- `0x1F 60` -> wait for the text prompt / system input gate through `C1:00FE`
- `0x1F 81` -> direct item-use compatibility check through `C1:4F6F`
- `0x1F 90` -> phone-contact selection menu builder through `C1:9441`
- `0x1F D0` -> Jeff repair / broken-item callback family
- `0x1F D1` -> immediate nearby magic-truffle direction helper
- `0x1F D2` -> strongest current fit wandering-photographer summon branch
- `0x1F D3` -> timed-delivery callback branch

## Source scaffold promotion

The large `C1:621F..7274` callback corridor is now decoded source in `src/c1/c1_621f_finalize_text_command1_fc0_jump_multi2_target.asm`. That source covers the hidden `1F C0` / `JUMP_MULTI2` finalizer, Jeff repair's `D0` branch, several low-word event-helper leaves in the `0x1F 13..1F` and `E1..F2` bands, and the nearby `1F 04/62/63/66/67` leaves.

The adjacent `C1:7274..7440` corridor is now decoded source in `src/c1/c1_7274_stage_bank_deposit_accumulator_text_value.asm`. It covers `1F 40`, `1F 41`'s local special-event-dispatch wrapper, `1F D2`'s wandering-photographer helper bridge, `1F F3/F4`, the `C1:73C0` battle visual result stager, and `1F 07`. The `C1:7440` timed-delivery callback adapter itself is now decoded source in `src/c1/c1_7440_timed_delivery_row_selector_callback.asm`. The combined C1 scaffold validates byte-for-byte after promotion: `C1 byte-equivalence: OK, 172 module(s), 0 mismatch(es).`

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
