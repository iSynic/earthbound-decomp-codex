# C2 Call For Help Runtime Polish

This note records the byte-neutral C2 call-for-help polish slice. It promotes
the PP/HP target-loss sibling, enemy sprite width budget helper, call-for-help
probability prefix, and reinforcement placement body.

Primary source modules:

- `src/c2/c2_bcb9_apply_battler_pp_target_loss.asm`
- `src/c2/c2_bd13_sum_active_enemy_battle_sprite_widths.asm`
- `src/c2/c2_bd5e_call_for_help_enemy_selection_and_message_body.asm`
- `src/c2/c2_be6c_run_call_for_help_enemy_selection_body.asm`

Related evidence notes:

- `notes/c2-pp-loss-and-call-for-help-width-helpers-c2bcb9-c2bd13.md`
- `notes/c2-battle-sprite-runtime-polish.md`
- `notes/class2-d59589-enemy-data-crosswalk.md`
- `notes/c2-target-selection-runtime-polish.md`

## Target Loss Siblings

`C2:BCB9` subtracts X from battler row `+0x19` (`pp_target`), floors at zero,
and commits through `SET_PP` at `C2:7191`.

The adjacent body has the same shape for row `+0x13` (`hp_target`) and commits
through `SET_HP` at `C2:7126`.

## Width Budget

`C2:BD13` scans enemy battler slots `8..31` starting at `$A21C`. It counts only
rows whose consciousness byte `+0x0C` is `1`, reads each active enemy's battle
sprite id at row `+0x02`, calls the local battle-sprite width helper, and
returns the accumulated width in A.

The call-for-help body uses this total plus the candidate enemy width to reject
reinforcements when the screen sprite budget would reach or exceed `0x20`.

## Prefix And Probability

`C2:BD5E` is the call-for-help prefix. Input A selects the message flavor.

The prefix:

- reads the active action row at `$A970`
- uses row `+0x08` as the enemy id/type being called
- finds that id in the current battle group enemy list
- counts already-present conscious enemies of the same type
- reads enemy config `+0x5C` as the max-called limit
- scales the probability by `max_called - already_present`
- routes failure to EF text and the shared `C2:C13A` action tail

The two failure scripts are now named at the source sites:

- `EF:7824` / `MSG_BTL_NAKAMA_NO` for the ordinary "no one came" path.
- `EF:7830` / `MSG_BTL_TANEMAKI_NO` for the seed/sprout-flavored failure path.

## Placement

`C2:BE6C` performs the successful selection and placement path:

- starts with the generic `C2:6BB8` / `RollActionChanceGate` probability check
- rechecks the width budget using `C2:BD13`
- scans active enemy rows for placement bounds
- computes x position and row side when the candidate can fit
- falls back to replacing a matching solidified/inactive row when possible
- finds the first empty enemy battler slot
- initializes the row through `C2:B6EB`
- writes row `+0x44/+0x45` position, `+0x10` row side, `+0x43` loaded sprite
  slot, and `+0x0D` active/new marker
- emits the success message selected by the wrapper input

The two success scripts are now named at the source sites:

- `EF:77FD` / `MSG_BTL_NAKAMA_KITA` for the ordinary joined-battle path.
- `EF:7810` / `MSG_BTL_TANEMAKI_HAETA` for the seed/sprout-flavored success
  path.

## Decomp Value

This slice connects enemy config, battle-group data, battler rows, and battle
sprite layout:

- enemy config `+0x5C` is documented as the max-called limit consumer
- call-for-help validates both probability and sprite width before insertion
- new enemy placement writes the same position and loaded-sprite fields consumed
  by battle sprite rendering
- failure and success EF text paths are separated from placement mechanics
- the `C1:DC1C` dispatch ABI is explicit on all four call-for-help result text
  exits

## Remaining Soft Spots

- exact message distinction for the two wrapper inputs
- final naming of row `+0x0D` in the called enemy insertion path
- whether the duplicated `BD5E` body inside the `BD13..BE6C` source unit should
  be split or represented once in a later source cleanup
