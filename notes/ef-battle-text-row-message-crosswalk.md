# EF Battle Text Row-Message Crosswalk

This note is the first concrete crosswalk from the EF action-message islands to
source-backed `D5:7B68` battle-action rows. It expands the frontier note by
recording rows whose `+4` EF message pointer and `+8` C2 behavior pointer are
already joined by focused C2 notes.

Scope:

- EF row-message anchors in `src/ef/ef_4e20_c51b_text_payload_data.asm`
- C1 display lane: `C1:DD9F` row-message display from `C2:5C66`
- C2 behavior lane: `D5:7B68` row `+8` behavior pointers consumed through
  the C2 action-payload path

Pointer-recovery follow-up:

- `notes/ef-battle-text-consumer-lane-contracts.md`
- `notes/ef-battle-text-row-pointer-recovery-frontier.md`

This is a consumer crosswalk, not an EB text macro decode. Exact `MSG_BTL_*`
labels remain stable unless the C2 behavior body proves a narrower result name.

Evidence boundary:

- The local `src/d5/table_battle_action_table.asm` scaffold proves the
  `D5:7B68` action-table span, row count, and `0x0C` stride, while
  `tools/inspect_battle_action.py` can recover exact row bytes from a local
  ROM.
- C2 late-action notes often prove row `+8` behavior bodies. Those bodies are
  enough to document direct result scripts, but not enough to rename an EF
  row-message anchor unless the row `+4` pointer is also known.
- Rows below are promoted only when local notes, source-backed C2 evidence, or
  ROM-backed row inspection already join the row id, row `+4` EF message
  pointer, and row `+8` behavior pointer.

## Status-Action Row Messages

These rows are the highest-value EF/C2 joins because the row message, behavior
body, success text, and fallback text are all visible.

| Row | Row `+4` EF message | Row `+8` C2 body | Behavior result payloads |
| ---: | --- | --- | --- |
| `53` | `EF:8543` shared PSI `ByteSubstitution` text | `C2:9F57 -> C2:9F06` | PSI-side asleep/affliction+2 value `1`; emits `EF:6C55` or `EF:766E` |
| `58` | `EF:8543` shared PSI `ByteSubstitution` text | `C2:A056` | PSI-side strange/affliction+3 value `1`; emits `EF:6C3A` or `EF:766E` |
| `75` | `EF:9C30` `MushroomSporesRowPresentationText` | `C2:8BBE` | Mushroomized/affliction+1 value `1`; emits `EF:6B81` or `EF:766E` |
| `76` | `EF:9C51` `PossessedStatusRowPresentationText` | `C2:8BFD` | Possessed/affliction+1 value `2`; emits `EF:6B98` or `EF:766E` |
| `78` | `EF:9CAD` `CryingMoldSporesRowPresentationText` | `C2:8C69` | Crying/affliction+2 value `2`; emits `EF:6BBB` or `EF:766E` |
| `79..82` | `EF:9CD1/9CF1/9D14/9D3E` immobilizing `RowPresentationText` variants | `C2:8CB8` | Immobilized/affliction+2 value `3`; emits `EF:6BD3` or `EF:766E` |
| `83` | `EF:9D62` `SolidificationScaryWordsRowPresentationText` | `C2:8CF1` | Solidified/affliction+2 value `4`; emits `EF:6BEF` or `EF:766E` |
| `84` | `EF:9D81` `StrangeStatusSuspiciousThingRowPresentationText` | `C2:8D3A -> C2:A056` | Strange/affliction+3 value `1`; emits `EF:6C3A` or `EF:766E` |
| `85` | `EF:9DA1` `ConcentrationPsiSealRowPresentationText` | `C2:8D5A` | Concentration/PSI-seal affliction+4 value `4`; emits `EF:6C0B` or `EF:766E` |
| `86` | `EF:9DBD` `StrangeStatusThoughtRowPresentationText` | `C2:8DBB` | Direct strange/affliction+3 value `1`; emits `EF:6C3A` or `EF:766E` |
| `87` | `EF:9DDA` `CryingBreathRowPresentationText` | `C2:8DFC` | All-target crying-family sibling; grouped with the affliction+2 crying body |
| `90` | `EF:9E47` `AsleepMusicRowPresentationText` | `C2:9F57 -> C2:9F06` | Asleep/affliction+2 value `1`; emits `EF:6C55` or `EF:766E` |
| `159` | `EF:8E3C` `ConcentrationPsiSealRowPresentationText` | `C2:A3D1` | Item-side concentration/PSI-seal; emits `EF:6C0B` or `EF:766E` |
| `207` | `EF:83A8` `StrangeStatusLaughRowPresentationText` | `C2:8D3A -> C2:A056` | Strange-status wrapper reuse; emits `EF:6C3A` or `EF:766E` |

Important modeling point: the row `+4` message is the action presentation text
shown through `C1:DD9F`. The success/failure payloads listed above are separate
result scripts emitted later by the row `+8` behavior body through `DC1C`.

## Physical, Special, Item, And Flavor Row Messages

These rows are also source-backed, but the behavior bodies are damage,
normalization, special-event, or message-only rather than simple affliction
writes.

| Row | Row `+4` EF message | Row `+8` C2 body | Current behavior read |
| ---: | --- | --- | --- |
| `99` | `EF:7E88` `FuelSupplyFullHealRowPresentationText` | `C2:9AD8` | Full-heal reuse over the fixed-amount healing core; fuel-supply presentation text |
| `100` | `EF:7EAC` `PoisonFangsRowPresentationText` | `C2:8F97` | Poison-on-hit physical action; secondary success text `EF:6B18` |
| `101` | `EF:7ED5` `FiredMissileRowPresentationText` | `C2:A821` | Projectile/explosive wrapper over bomb-common splash damage; fired-missile presentation text |
| `102` | `EF:7F02` `AttackContinuouslyRowPresentationText` | `C2:8FF9` | Exact double-bash wrapper over `C2:859F` |
| `104` | `EF:7F32` `FlamingFireballRowPresentationText` | `C2:900B` | One-target fire-damage wrapper |
| `117` | `EF:80C4` `TornadoRowPresentationText` | `C2:902C` | All-target physical wrapper over `C2:8651` |
| `118` | `EF:80E4` `GiganticBlastRowPresentationText` | `C2:902C` | Same all-target physical wrapper reuse |
| `140` | `EF:8E27` `SharedNamedItemRowPresentationText` | `C2:9AD8` | Item-side full-heal reuse over the fixed-amount healing core; named-item presentation wrapper |
| `228` | `EF:8BE8` `DiamondizeBiteRowPresentationText` | `C2:916E` | One-target diamondize action; emits `EF:6AC7` or `EF:7655` |
| `232` | `EF:8C58` `BadSmellOdorRowPresentationText` | `C2:9254` | Odor/offense-reduction family; reports amount through C8 text via `DC66` |
| `243` | `EF:72F6` `RunawayFiveBreakInRowPresentationText` | `C2:9298` | Runaway Five / Clumsy Robot special-event controller; branches to `EF:72F7` or `EF:733D` |
| `244` | `EF:7415` `PooBreakInRowPresentationText` | `C2:92EE` | Master Barf defeat / Poo Starstorm event result; later emits `EF:743B` |
| `247` | `EF:8E27` `SharedNamedItemRowPresentationText` | `C2:90C6` | Battler normalization wrapper; can emit `EF:7142` and queue `EF:7123` |
| `248` | `EF:8D9F` `NeutralizeSparkleRowPresentationText` | `C2:90C6` | Same normalization wrapper reuse |
| `273` | `EF:8EBE` `BadSmellGasRowPresentationText` | `C2:9254` | Odor/offense-reduction family reuse |
| `290` | `EF:8DDE` `RainbowColorsEventRowPresentationText` | `C2:C14E` | Rainbow-colors / Master Belch-side special-event family |

## Numeric, Healing, And Explosive Row Messages

The local ROM-backed inspector recovered the formerly behavior-only row `+4`
joins for the highest-risk amount/healing/explosive rows. Their behavior
bodies still emit separate result or amount text after the `DD9F` presentation.

| Row | Row `+4` EF message | Row `+8` C2 body | Current behavior read |
| ---: | --- | --- | --- |
| `32..35` | `EF:8543` `SharedPsiNameByteSubstitutionRowPresentationText` | `C2:9AC6`, `C2:9ACF`, `C2:9AD8`, `C2:9AE1` | PSI Lifeup alpha/beta/gamma/omega row presentation; HP recovery worker emits result text through `C2:7294` |
| `48` | `EF:8543` `SharedPsiNameByteSubstitutionRowPresentationText` | `C2:9E38` | PSI offense-up row presentation; amount text lives in C8 via `DC66` |
| `49` | `EF:8543` `SharedPsiNameByteSubstitutionRowPresentationText` | `C2:9E7F` | All-target offense-up wrapper over the same amount lane |
| `64` | `EF:9A7E` `ExplosionRowPresentationText` | `C2:A821` | Explosive wrapper over bomb-common splash damage |
| `65` | `EF:9A9E` `BurstIntoFlamesRowPresentationText` | `C2:A821` | Same explosive wrapper over bomb-common splash damage |
| `95` | `EF:7E25` `PpReductionRowPresentationText` | `C2:8E42` | PP reduction family; C8 amount text through `C1:DC66` |
| `96` | `EF:7E3E` `SteamedOffenseUpRowPresentationText` | `C2:9E38` | One-target offense-up family; C8 amount text through `C1:DC66` |
| `97` | `EF:7E55` `DirtyWordsGutsReductionRowPresentationText` | `C2:8EAE` | Guts-cutting family; C8 amount text through `C1:DC66` |
| `98` | `EF:7E70` `MoistureSuckedOffenseDefenseReductionRowPresentationText` | `C2:8F21` | Paired offense/defense reduction family; C8 amount text through `C1:DC66` |
| `233` | `EF:8C75` `LoudVoiceOffenseDefenseReductionRowPresentationText` | `C2:8F21` | Paired offense/defense reduction family; reports amount through C8 text via `DC66` |
| `234` | `EF:8C92` `WarCryOffenseDefenseReductionRowPresentationText` | `C2:8F21` | Same paired offense/defense reduction family |

Rows whose behavior body emits C8/C9 scripts should not force EF result names.
Keep the EF row-message labels presentation-oriented and document the secondary
script bank in the C2-focused note.

`EF:8E27` is intentionally listed twice: row `140` uses it as a named-item
healing presentation wrapper, while row `247` uses the same row-message anchor
with the normalization wrapper. The C2 row `+8` body is what separates those
runtime roles.

## Early Row-Message Anchors

The early row-message joins remain the cleanest `DD9F` examples:

| Row | Row `+4` EF message | Row `+8` C2 body | Current behavior read |
| ---: | --- | --- | --- |
| `4` | `EF:848C` `BashAttackRowPresentationText` | `C2:859F` | Bash |
| `5` | `EF:84B6` `ShootRowPresentationText` | `C2:8740` | Shoot |
| `6` | `EF:8530` `SpyCheckRowPresentationText` | `C2:8770` | Spy |
| `7` | `EF:89E0` `PrayRowPresentationText` | `C2:AD1B` | Pray |
| `10..35`, `48`, `49`, `53`, `58` | `EF:8543` `SharedPsiNameByteSubstitutionRowPresentationText` | PSI wrapper/status/offense families | Shared PSI row message; `ByteSubstitution` PSI name |

## How To Use This Crosswalk

For future EF payload work:

- If a row `+4` message has a row-specific C2 body and a result script, name the
  EF row-message anchor conservatively around the proved presentation role and
  document the behavior/result split in this crosswalk.
- If the C2 body emits a separate EF script through `DC1C` or `DC66`, keep that
  result payload named independently from the row-message text.
- If only table order or reference names are known, keep the anchor
  symbol-derived and leave it in the action-island frontier.

## Next Crosswalk Frontier

The immediate frontier has narrowed: Lifeup, numeric-effect, and explosive rows
now have recovered EF row `+4` joins. The remaining row-pointer work is mostly
late no-op/flavor rows whose C2 row `+8` bodies return without direct result
text.

### Behavior-Known No-Op And Flavor Rows

The late flavor-tail note proves several no-op behavior tails, but these are
especially easy to overname from English-looking `MSG_BTL_*` anchors. Treat the
following as behavior-known only:

| Rows | Known row `+8` behavior | Current read | Missing join |
| --- | --- | --- | --- |
| `119..134`, `186..188`, `257`, `260..266` | `C2:9033` | Shared flavor-only no-op tail | Row `+4` EF action message |
| `0..3`, `258` and siblings | `C2:9039` | Default no-op tail | Row `+4` EF action message for each late reuse |
| `9` | `C2:903C` | Isolated no-op row | Row `+4` EF action message |
| `251..256` | `C2:903F`, `C2:9042`, `C2:9045`, `C2:9048`, `C2:904B`, `C2:904E` | Tiny no-op tails in the late run | Row `+4` EF action message |

Modeling rule: a no-op row `+8` body can still have a meaningful row `+4`
presentation message. Do not collapse those messages into "no effect" result
text; the row message is consumed through `C1:DD9F` before the behavior body
returns.

### Remaining Special-Event Rows

Rows `243`, `244`, and `290` are now concrete EF row-message joins because the
local special-event notes prove their row `+4` EF message pointers and row `+8`
C2 bodies.

Final Prayer rows `291..299` remain a separate frontier. Many of their row
messages live outside EF, while secondary result scripts still affect the
battle-text contract through C8/C9 direct-result lanes. Keep them out of EF
row-message rename work unless a local row `+4` EF pointer is proved.

## Non-EF Row-Message Lanes

Some source-backed action rows are important to the C1/C2 display contract but
do not name EF anchors at all. Keep them visible here so they do not get
mistaken for missing EF text splits.

| Rows | Row-message bank | Row `+8` C2 body | EF naming impact |
| --- | --- | --- | --- |
| `139`, `141` | `C9:7B6B` item-use wrapper | `C2:9AC6`, `C2:9AE1` | Item-side healing reuses; not EF row messages |
| `166` | `C9:7F56` item strike wrapper | `C2:A5EC` | Damage-plus-solidification item action; success/failure results still emit `EF:6BEF` or `EF:766E` |
| `167`, `168` | `C9:7EB7` item thrown/fired wrapper | `C2:A818`, `C2:A821` | Bomb-family item rows; not EF row messages |
| `310`, `311` | `C9:7E9E` item fired wrapper | `C2:A818`, `C2:A821` | Bomb-family item rows; not EF row messages |
| `291..299` | C9 prayer message family, including `C9:F0B8` and `C9:F3EC` | `C2:C572..C2:C6F0` | Final Prayer ladder; row presentation and C8/C9 narrative results stay outside EF action-anchor naming |

Modeling rule: non-EF row messages still travel through the same row `+4`
presentation lane, but they should not create or rename EF anchors. Only their
secondary direct-result EF scripts belong in the EF payload map.

## Next Evidence To Add

The fastest way to expand this crosswalk is to add or derive local
action-table row evidence with the recovery process in
`notes/ef-battle-text-row-pointer-recovery-frontier.md`. Record, per row:

- row id and row `+0..+3` metadata
- row `+4` EF message pointer
- row `+8` C2 behavior pointer
- secondary EF/C8/C9 result scripts emitted by the behavior body

Once that exists, promote rows family by family. Numeric-effect rows should be
first because their C2 behavior bodies and amount-result lanes are already well
documented; no-op/flavor rows should follow because they need stricter
separation between presentation text and behavior effects.
