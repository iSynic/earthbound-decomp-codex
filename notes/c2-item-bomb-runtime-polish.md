# C2 Item And Bomb Runtime Polish

This note records the byte-neutral C2 item/bomb action polish slice. It promotes
the item-side concentration seal, damage-plus-solidification item action, and
bomb/super-bomb splash-damage contracts.

Primary source modules:

- `src/c2/c2_a3d1_run_item_side_concentration_seal_action.asm`
- `src/c2/c2_a5ec_run_damage_plus_solidification_item_action.asm`
- `src/c2/c2_a630_apply_solidification_status_from_item_action.asm`
- `src/c2/c2_a658_run_bomb_common_splash_damage.asm`
- `src/c2/c2_a818_run_bomb_action.asm`
- `src/c2/c2_a821_run_super_bomb_action.asm`

Related evidence notes:

- `notes/class2-concentration-seal-family-c28d5a-c2a3d1.md`
- `notes/class2-solidification-item-action-c2a5ec-a630.md`
- `notes/class2-bomb-common-family-c2a658-c2a821.md`
- `notes/c2-late-status-runtime-polish.md`
- `notes/c2-action-dispatch-runtime-polish.md`

## Item-Side Concentration Seal

`C2:A3D1` is the item-side sibling of the concentration/PSI-seal family. It
uses the ordinary target gate at `C2:7CFD` and the local eligibility gate at
`C2:8D41`.

On success it writes value `4` to target row `+0x21` and displays `EF:6C0B`.
If the target is ineligible or the byte is already occupied, it displays
`EF:766E`.

The same source unit also contains neighboring item-side helpers such as
HP-sucker and bottle-rocket common paths. HP-sucker is now source-promoted far
enough to name the `EF:7710` self-drain direct text, the `EF:7729`
amount-bearing drain text, and the `C1:DC66` substitution-payload call that
prints the drained HP amount. Bottle-rocket remains adjacent context for a later
dedicated pass.

## Solidification Item

`C2:A5EC` is the damage-plus-solidification item action, strongest local fit for
`BTLACT_HANDBAG_STRAP`.

The action:

- gates through `C2:7CFD`
- applies `C2:7CAF(0x00FA)`
- computes damage as `0x0064 - target defense`
- applies damage through `C2:8125`
- attempts `C2:724A(target, X=2, Y=4)`

`C2:A630` is the solidification text tail. Success displays `EF:6BEF`; failure
displays `EF:766E`.

## Bomb Common

`C2:A658` is the shared bomb/explosive splash-damage worker. Input A is the base
damage parameter. It applies full shaped damage to the primary target through
`C2:6A44` and `C2:8125`.

When the target is in the battler domain, the helper scans nearby same-side and
same-row battlers, using sprite width and x-position overlap checks. Up to two
secondary targets receive half of the base damage. `$A972` is restored to the
original target before returning.

Wrappers:

- `C2:A818` / `BTLACT_BOMB`: base damage `0x005A` (`90`)
- `C2:A821` / `BTLACT_SUPER_BOMB`: base damage `0x010E` (`270`)

## Decomp Value

This slice tightens several item-side runtime contracts:

- row `+0x21 = 4` has a second concentration/PSI-seal action-table anchor
- row `+0x1F = 4` solidification is tied to item-side damage-plus-status logic
- bomb wrappers now have durable base damage constants
- bomb splash damage is linked to sprite-width and position fields consumed by
  the battle sprite layout/rendering lane

## Remaining Soft Spots

- full runtime polish for the bottle-rocket bodies in the `A3D1..A5EC` source
  unit
- whether all `A821` reuses should be named strictly as Super Bomb or broader
  explosive/projectile clones
- final player-facing names for nearby item entries around `A5D1..A5E3`
