# EF Battle Text Payload Runtime Polish

This note records the first EF text-payload split driven by the C1/C2
battle-text contract work.

## Source Slice

Primary source module:

- `src/ef/ef_4e20_c51b_text_payload_data.asm`

The module is still ROM-preserved text data, not decoded text macro source. The
new labels are zero-byte scaffold anchors that split the coarse
`EF:4E20..C51B` data gap around battle-text scripts already proved by C1/C2
callers.

## Promoted Payload Anchors

- `EF:69A1`, `EF:69BA`, and `EF:69D2` now mark HP maxed, HP recovered amount,
  and PP recovered amount text. The two amount scripts are consumed through
  `C1:DC66 -> C1:AD0A -> $9D12/$9D14 -> 1C 0F`.
- `EF:69EA` and `EF:69FF` now mark the Spy offense and defense amount
  readouts. Both scripts are `1C 0F` amount consumers reached through the C2
  Spy setup and the `C1:DC66` amount-print contract.
- `EF:6A0D`, `EF:6A24`, `EF:6A3C`, `EF:6A54`, `EF:6A6C`, and `EF:6A7F`
  now mark the Spy vulnerability/susceptibility direct readout text for fire,
  freeze, flash, paralysis, hypnosis, and Brain Shock. C2 gates these direct
  scripts from battler resistance bytes before issuing the `DC1C` display call.
- `EF:6A99` and `EF:6AB3` now mark metamorphose success/failure text used by
  the C2 normalization tail. `EF:6AC7` now marks the diamondized inflicted
  text adjacent to the existing paralysis/status payload split.
- `EF:6AE0`, `EF:6B18`, `EF:6BEF`, `EF:6C3A`, and `EF:6C55` now mark
  paralysis, poison, solidification, strange, and asleep inflicted text. The EF
  decode shows `EF:6AE0` as the body-numb/paralysis message used by
  `BTLACT_PARALYSIS_A`, while actual poison remains the separate `EF:6B18`
  script used by the item/status cluster.
- `EF:6AFB..6C0B` is now split around the adjacent sick/cold/mushroomized,
  possessed, crying, immobilized, solidification, and PSI-seal status payloads
  instead of one broad affliction corridor.
- `EF:6C6B..6E31` now splits the post-status EBATTLE5 death-result corridor:
  player collapse, Flying Man/teddy-bear NPC death payloads, and enemy defeat
  flavor text now have source anchors instead of one anonymous status tail.
- `EF:6E4A`, `EF:6E67`, `EF:6E81`, `EF:6E97`, `EF:6EBC`, `EF:6ED1`,
  `EF:6EED`, `EF:6F0B`, `EF:6F1E`, `EF:6F38`, `EF:6F54`, and `EF:6F64`
  now mark the EBATTLE5 recovery/removal scripts for diamondized, paralysis,
  nausea, poison, cold, crying, immobilized, frozen, strange, sunstroke,
  asleep, and PSI-seal states. These line up with the C2 affliction-recovery
  helper families.
- `EF:6F7C` and `EF:6F8E` now mark revive success/failure text immediately
  before the shield-result block.
- `EF:6F9A/6FBD`, `EF:6FD3/6FF4`, `EF:700C/7032`, and `EF:7050/707A`
  now mark the installed/strengthened text pairs for shield, power shield,
  psychic shield, and psychic power shield.
- `EF:7099`, `EF:70B1`, `EF:70D2`, `EF:70FA`, `EF:7123`, `EF:7142`, and
  `EF:7160` now mark the shield-expired, shield-reflection, PSI-name
  shield-nullify, Neutralizer, and Franklin Badge text tail used by C2 timed
  substate and Thunder reflection helpers.
- `EF:7186..7249` now splits EBATTLE4 action-blocking status text for
  diamondized, paralysis, nausea, poison, asleep, immobilized, and PSI-seal
  turns, including the PSI-seal player-side sound branch and `19 1F` byte
  substitution before `PRINT_PSI_NAME 0`.
- `EF:7249..75AB` now splits EBATTLE4 guard, Fly Honey, homesickness,
  Runaway Five, Poo/Starstorm, Pokey, and companion event text before the
  central damage block.
- `EF:75AB`, `EF:75C2`, `EF:75D9`, `EF:75F0`, and `EF:7607` now mark the
  amount-bearing damage and SMAAAASH damage scripts selected by the C2
  hit-resolution cluster. These are `1C 0F` amount consumers.
- `EF:7624`, `EF:7630`, `EF:763C`, and `EF:7655` now mark the player/monster
  SMAAAASH presentation scripts and shooting/physical dodge scripts used by the
  same C2 hit-resolution lane.
- `EF:766E`, `EF:7696`, and `EF:773F` now mark shared no-effect, no-visible
  effect, and PP-drain amount text. `EF:773F` is another `1C 0F` amount
  consumer.
- `EF:76B3`, `EF:76C7`, `EF:76D8`, `EF:76FD`, `EF:7710`, and `EF:7729`
  now split the adjacent EBATTLE4 no-effect/miss/target-gone/HP-sucker text
  tail. `EF:7729` is an HP-sucker `1C 0F` amount consumer.
- `EF:7755`, `EF:7768`, `EF:7787`, `EF:77B1`, and `EF:77DB` now split the
  target-side PP drain and periodic status damage text before EBATTLE8.
- `EF:77FD`, `EF:7810`, `EF:7824`, and `EF:7830` now mark the four
  call-for-help result scripts selected by the C2 reinforcement prefix/body:
  ordinary success, seed/sprout success, ordinary failure, and seed/sprout
  failure. They are direct `C1:DC1C` text exits.
- `EF:7843` now marks the Time Stop return text used by the C2 hit-resolution
  cluster.
- `EF:7858..790B` now splits the EBATTLE8 encounter-opening text variants:
  ordinary attack, blocked-way, came-after-you, trapped-you, final-encounter
  wording, and surprise-opening messages.
- `EF:790B..79D7` now splits the group-actor helper branches used by those
  encounter-opening messages.
- `EF:79D7..7A66` now splits ordinary/boss/forced player victory,
  monster-victory, homesick, and experience-gain text.
- `EF:7A66..7B64` now splits the level-up and stat-gain amount text consumed
  by the C1 level-up stat narration family.
- `EF:7B64` now marks the learned-PSI lead-in that falls through to the
  existing `EF:7B77` PSI-name byte-substitution text.
- `EF:7B77`, `EF:7B85`, `EF:7BA2`, `EF:7BC1`, `EF:7BDF`, and `EF:7DD5` now
  mark the byte and pointer substitution examples in `EBATTLE8`: `19 1F` byte
  substitution for present item names and `19 1E` pointer substitution branches.
- `EF:7C42`, `EF:7C73`, `EF:7C89`, `EF:7CB4`, `EF:7CED`, `EF:7CF8`,
  `EF:7D0F`, `EF:7D83`, and `EF:7DBE` now split the `MSG_BTL_PRESENT`
  result continuation into dead-recipient, full-inventory, abandon, drop, and
  forbidden-drop text paths.
- `EF:7E25..843F` now splits EBATTLE2 action-flavor narration into
  symbol-derived `MSG_BTL_*` anchors, covering enemy attack descriptions,
  guard/flavor actions, gases/breath/light/sound effects, and the last
  `MSG_BTL_CHOU_ONPA` payload before EBATTLE0 begins.
- `EF:843F`, `EF:8444`, `EF:8445`, `EF:845D`, and `EF:8477` now mark
  battle-start and random-action status text used by C2 direct `DC1C` callers.
- `EF:848C..8814` now splits the EBATTLE1 battle-command front into
  Bash/attack, Shoot, Guard, Metamorphose, flee success/failure, Spy/check,
  shared PSI action text, and the first PSI animation/effect dispatch branches.

## Correction

The EF decode corrected one local C2 naming drift: `C2:9FFE` is the
`BTLACT_PARALYSIS_A` body and its success script at `EF:6AE0` prints the
body-numb/paralysis result text. The source now names that path as paralysis
rather than poison. The actual poison-inflicted text remains the separate
`EF:6B18` script used by the item/status cluster.

## Spy Readout Follow-up

The C2 Spy refinement proved that the coarse `EF:69EA..6AE0` EBATTLE5 corridor
contains a compact set of distinct scripts, not one generic stat/status
prelude. Offense and defense use the same amount-print path as HP/PP recovery,
while the resistance readouts are direct display scripts selected only when C2
finds a vulnerable/susceptible resistance byte. The metamorphose and diamondized
neighbors were split in the same pass so the late C2 primary-status tail no
longer lands in an anonymous gap.

## Call-For-Help And Time Stop Follow-up

The C2 call-for-help polish proved four direct text exits in the front of
`EBATTLE8`: ordinary and seed/sprout success paths at `EF:77FD` and `EF:7810`,
plus ordinary and seed/sprout failure paths at `EF:7824` and `EF:7830`. The
same EBATTLE8 neighborhood also contains the `EF:7843` Time Stop return script
used by the C2 hit-resolution cluster. This split keeps those runtime-facing
messages visible.

## Encounter, Victory, And Level-Up Follow-up

The `EF:7858..7B77` EBATTLE8 island is now split around exact encounter,
group-actor, victory, and level-up labels. This exposes the encounter-opening
message variants and their `LOAD_SPECIAL 2` group-name helper branches, then
the ordinary/boss/forced victory text and monster-win text. The stat-gain tail
at `EF:7A66..7B64` now lines up directly with the C1 level-up narration note:
each stat leaf stages an amount through `C1:AD0A` before dispatching one of
these `PRINT_ACTION_AMOUNT` scripts, while learned PSI falls through into the
existing `EF:7B77` PSI-name byte-substitution payload.

## Damage And Miss Follow-up

The C2 hit-resolution source names a dense EBATTLE4 result set around
`EF:75AB..77FD`: amount-bearing damage variants, SMAAAASH presentation, dodge,
miss, target-gone, HP/PP drain, and periodic status damage. Splitting those
anchors makes the central damage pipeline visible on the EF side.

## EBATTLE4 Status And Event Prelude Follow-up

The remaining `EF:7186..75AB` prelude is now split around exact EBATTLE4
labels. The front status run exposes action-blocking result text for
diamondized, paralysis, nausea, poison, sleep, immobilization, and PSI seal.
The event half exposes guard, Fly Honey, homesick flavor, Runaway Five
intervention, Poo/Starstorm, Pokey random talk branches, and companion text
before the damage pipeline begins at `EF:75AB`.

## Recovery And Death Follow-up

The C2 affliction-recovery source and notes repeatedly dispatch into the
`EF:6E4A..6F64` recovery/removal subrange for poison, nausea, crying, strange,
sunstroke, asleep, and PSI-seal cleanup. Splitting the wider `EF:6C6B..6F9A`
island also exposes the adjacent player/NPC/enemy death-result payloads and the
revive success/failure scripts that sit before the shield-result block.

## Present Result Follow-up

The C2 battle-start and Check Present notes already prove the `$AA10 ->
C1:DD7C -> $9D11 -> 19 1F` byte-substitution bridge into `EF:7BDF` and
`EF:7DD5`. Splitting `EF:7C42..7DD5` exposes the internal `MSG_BTL_PRESENT`
continuations named by the EBATTLE8 listing: recipient-dead fallback,
inventory-full throw-away prompts, abandon confirmation branches, selected-item
drop confirmation, and the no-drop retry path. This keeps the present family
readable without decoding the EB text bytecode into macro source yet.

## EBATTLE2 Action-Flavor Follow-up

The `EF:7E25..843F` EBATTLE2 island is now split around exact listing labels
from `MSG_BTL_PPDOWN` through `MSG_BTL_CHOU_ONPA`. These labels are
intentionally conservative and mostly symbol-derived: the visible English text
shows enemy action narration, but some original symbol names are better kept as
stable anchors until a C2 action-table consumer pass proves narrower runtime
roles. The result is still useful immediately because the large pre-start-battle
blob no longer hides dozens of direct battle-text payload targets.

## EBATTLE1 Battle Command Front Follow-up

The first slice of `EF:848C..C51B` is now split through `EF:8814`. This is the
runtime-facing battle-command front already tied to the C2 action table notes:
`EF:848C` is the Bash/attack text pointer for the table's ordinary attack
entry, `EF:8530` is the Spy/check text pointer, and `EF:8543` is the shared PSI
text pointer reused by many PSI-shaped action rows. The `EF:857E` dispatch and
`EF:864C..8813` branches remain ROM-preserved text/effect bytecode, but now
have stable anchors for later PSI animation/effect consumer work.

## Validation

This slice should validate both touched banks:

```powershell
python tools\build_source_bank_scaffold.py --bank EF
python tools\validate_source_bank_byte_equivalence.py --bank EF --module all --combined --scaffold src\ef\bank_ef_helpers_asar.asm --strict
python tools\build_source_bank_scaffold.py --bank C2
python tools\validate_source_bank_byte_equivalence.py --bank C2 --module all --combined --scaffold src\c2\bank_c2_helpers_asar.asm --strict
```
