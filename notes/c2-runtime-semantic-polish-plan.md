# C2 Runtime Semantic Polish Plan

Primary queue context: `notes/source-readiness-triage.md` and
`notes/project-status.md`.

## Current State

`C2` is fully source-backed for the current scaffold phase. The handoff in
`notes/bank-c2-source-scaffold-handoff.md` reports `65536` source bytes,
`0` preserved data-gap bytes, and byte-equivalence `OK`. Remaining work is
semantic polish: stronger struct names, local labels/comments, and cross-bank
contract notes for C0/C1/C3/C4 consumers.

## Subsystem Slices

- Action dispatch: class-2 derived action code construction, action row
  dispatch, second-pointer payloads, item-side and bomb/action continuations.
- Target selection: battler-table population, ranked target lists, steal
  targets, random battler selection, front/back row behavior.
- Status/effect families: affliction mutation, derived stat consequences,
  HP/PP rollers, status tile lookups, solidification and PP-loss handlers.
- PSI/common handlers: PSI menu joins, PSI animation setup, common target/result
  helpers, reflected-hit context rebuild.
- Battle text result flow: C1 battle text callers, C2 action message lanes, EF
  substitution payloads.
- Final Prayer and battle visuals: Final Prayer stages, battle-background
  update/load, swirl overlays, battle sprite/palette-wave helpers.

## First Pass Order

1. Start with C1-facing target/result text contracts because C1 explicitly
   depends on C2 for stable battle front-end names.
2. Polish action dispatch and target selection together so row structures and
   target records get one vocabulary.
3. Move through status/effect and PSI common handlers once the action/result
   contract is stable.
4. Finish with Final Prayer and battle visuals, keeping visual asset table names
   aligned with C4 and CA-CE contract notes.

## Evidence Inputs

- `notes/bank-c2-source-scaffold-handoff.md`
- `notes/bank-c2-working-name-proposals.md`
- `notes/bank-c2-progress-audit.md`
- `notes/c2-battle-contract-workahead.md`
- `notes/c2-ef-battle-text-contract-workahead.md`
- `notes/battle-visual-asset-contracts.md`
- class-2 notes cited by the C2 working-name proposal table

## Expected Outputs

- Source-facing names and comments for battle action, target, status/effect,
  PSI, and visual helper contracts.
- Cross-bank contract notes tying C1 battle front ends and EF substitution data
  to C2 result text and action-table message lanes.
- A list of class-2 leaves that remain intentionally raw or provisional after
  each slice.

## Implementation Notes

- 2026-04-30 first slice: promoted the C1/C2/EF battle-text ABI into source
  comments and local aliases for `C1:DC1C`, `C1:DC66`, `C1:DD9F`,
  `C1:AD0A`, `C1:AD26`, the C2 HP/PP recovery feedback helpers, and the
  battle-start action-table text lane. This is byte-neutral semantic polish;
  the code still relies on byte-equivalence validation as the guardrail.
- 2026-04-30 second slice: named EF status-result scripts at the C2 call sites
  for crying, solidified, asleep, poison, strange, PP drain, and the timed
  shield/substate message pairs. This keeps the C2 source focused on the
  runtime choice being made rather than only the raw EF pointer value.
- 2026-04-30 third slice: cleaned up the remaining local
  `C1DC66_DisplayBattleTextWithNumber` aliases in C2 stat/resource modules.
  PP reduction, guts reduction, offense/defense reduction, odor offense,
  offense-up, defense-down, and battle IQ-increase callers now use local C8/EF
  message constants plus the shared
  `DisplayBattleTextWithSubstitutionPayload` contract.
- 2026-04-30 third slice: promoted C2 target-selection contracts into
  byte-neutral source comments plus `notes/c2-target-selection-runtime-polish.md`.
  The promoted contracts cover `C2:B930` 0x4E-byte snapshot export, `C2:BAC5`
  filtered row counting over `$9FAC`, `C2:BB18` selected-row promotion into the
  collapse/affliction controller path, and `C2:BC5C` inactive transient-field
  cleanup.
- 2026-04-30 fourth slice: promoted C2 action-dispatch contracts into
  byte-neutral source comments plus `notes/c2-action-dispatch-runtime-polish.md`.
  The promoted contracts cover `D5:7B68` descriptor metadata use, battler
  `+0x09/+0x0A` derived action/target bytes, `$A96C/$A96E` as the current
  32-bit target mask, and `C2:40A4` as the second-pointer payload applicator.
- 2026-04-30 fifth slice: promoted C2 stat-consequence contracts into
  byte-neutral source comments plus `notes/c2-stat-consequence-runtime-polish.md`.
  The promoted contracts cover the `C2:B2E0` selector map, HP/PP feedback helper
  reuse, IQ/guts/speed/vitality/luck row and live-stat mirrors, derived-stat
  refresh calls, amount-bearing battle text, and affliction-recovery tails.
- 2026-04-30 sixth slice: promoted C2 affliction-recovery contracts into
  byte-neutral source comments plus `notes/c2-affliction-recovery-runtime-polish.md`.
  The promoted contracts cover the `C2:9AEA/9B7A/9C2C/9CB8` recovery ladder,
  selected-row `+0x1D` ailment values 1..7 within that family, subgroup bytes
  `+0x1F/+0x20`, timed-substate neighbor fields, and poison-only `C2:A39D`.
- 2026-04-30 seventh slice: promoted selected-row controller contracts into
  byte-neutral source comments plus `notes/c2-selected-row-controller-runtime-polish.md`.
  The promoted contracts cover the `C2:7294/7318` HP/PP feedback pair,
  `C2:7397` heavy recovery reset behavior, and the `C2:7550` startup boundary
  into the late selected-row controller.
- 2026-04-30 eighth slice: promoted late selected-row controller contracts into
  byte-neutral source comments plus `notes/c2-late-selected-row-runtime-polish.md`.
  The promoted contracts cover the `C2:7680` descriptor text continuation,
  `C2:77CA` source-entry claim scan, nested `D5:7B68` action pass, and selected
  row marker/state effects.
- 2026-04-30 ninth slice: promoted early PSI common-helper contracts into
  byte-neutral source comments plus `notes/c2-psi-common-runtime-polish.md`.
  The promoted contracts cover the `C2:941D/94CE` shared blocker/cleanup pair,
  Rockin/Fire/Freeze/Starstorm one-parameter helpers, Thunder's two-parameter
  multi-hit target-mask loop, and Thunder's reflection tail at `C2:97A5`.
- 2026-04-30 tenth slice: promoted PSI Flash contracts into byte-neutral source
  comments plus `notes/c2-psi-flash-runtime-polish.md`. The promoted contracts
  cover the `C2:724A` affliction writer ABI, Flash gate `C2:98A1`, strange/numb/
  crying helper parameter pairs, and Alpha/Beta/Gamma/Omega random branch maps.
- 2026-04-30 eleventh slice: promoted late status-action contracts into
  byte-neutral source comments plus `notes/c2-late-status-runtime-polish.md`.
  The promoted contracts cover persistent subgroup `+0x1E`, temporary subgroup
  `+0x1F`, strange subgroup `+0x20`, and the adjacent PP-drain/primary-affliction
  bodies that share the late status source corridor.
- 2026-04-30 twelfth slice: promoted PSI animation tick contracts into
  byte-neutral source comments plus `notes/c2-psi-animation-runtime-polish.md`.
  The promoted contracts cover the `C2:E6B3` source prefix, `C2:E6B6` frame
  timer/source pointer, palette cycling state, VRAM `$5800` uploads, and
  enemy-color/alternate-palette timers.
- 2026-04-30 thirteenth slice: promoted battle overlay tail contracts into
  byte-neutral source comments plus `notes/c2-battle-overlay-runtime-polish.md`.
  The promoted contracts cover the `C2:E8C4` overlay latch, `C2:E8E0/E9C8`
  wrapper/predicate, `C2:E9ED` clear/reset body, `C2:EA15/EA74` open/close
  script selectors, and `C2:EAAA` final clear.
- 2026-04-30 fourteenth slice: promoted battle-background palette contracts
  into byte-neutral source comments plus
  `notes/c2-battle-bg-palette-runtime-polish.md`. The promoted contracts cover
  `C2:DE0F` dimming, `C2:DE96` restore, `C2:DF2E` literal/restore/stepped
  palette commands, protected palette-cycle windows, and `C2:E08E` layer
  fanout.
- 2026-04-30 fifteenth slice: promoted battle-background load/update contracts
  into byte-neutral source comments plus
  `notes/c2-battle-bg-load-update-runtime-polish.md`. The promoted contracts
  cover `C2:CFE5` config-to-struct import, `LOAD_BATTLE_BG` table joins,
  `C2:D0AC` letterbox HDMA construction, `C2:DAE3` distortion priming, and
  `C2:DB3F` per-frame visual updates.
- 2026-04-30 sixteenth slice: promoted Final Prayer contracts into
  byte-neutral source comments plus `notes/c2-final-prayer-runtime-polish.md`.
  The promoted contracts cover action-table rows `291..299`, shared helpers
  `C2:C37A/C3E2/C41F`, `$A97A` phase progression, staged damage amounts, and
  finale joins to battle-background distortion and overlay helpers.
- 2026-04-30 seventeenth slice: promoted battle sprite contracts into
  byte-neutral source comments plus `notes/c2-battle-sprite-runtime-polish.md`.
  The promoted contracts cover current battle-group sprite loading, loaded slot
  lookup, width-budget trimming, enemy row layout, render-order arrays, row
  render commits, and enemy sprite palette-wave state.
- 2026-04-30 eighteenth slice: promoted `SHOW_PSI_ANIMATION` setup contracts
  into byte-neutral source comments plus
  `notes/c2-show-psi-animation-runtime-polish.md`. The promoted contracts cover
  CC PSI config row joins, graphics/arrangement/palette setup, `$1B9E..$1BD4`
  state seeding, battle-background dimming, and affected enemy-row marking.
- 2026-04-30 nineteenth slice: promoted loaded battle-background frame generator
  contracts into byte-neutral source comments plus
  `notes/c2-loaded-bg-frame-generator-runtime-polish.md`. The promoted
  contracts cover `C2:C92D` as the loaded-bg struct interpreter, palette cycle
  consumption, CA scrolling and distortion row joins, offset commits, and the
  cautious display-setup role of `C2:C8C8`.
- 2026-04-30 twentieth slice: promoted STEAL helper contracts into byte-neutral
  source comments plus `notes/c2-steal-runtime-polish.md`. The promoted
  contracts cover `$A9D4` stealable-item candidates, random selection,
  stale-pending-item validation, row `+0x07/+0x08` slot/item fields, and the
  `C1:DDC6` pending slot application path.
- 2026-04-30 twenty-first slice: promoted call-for-help contracts into
  byte-neutral source comments plus `notes/c2-call-for-help-runtime-polish.md`.
  The promoted contracts cover PP/HP target-loss siblings, active enemy sprite
  width budgets, enemy config max-called limits, call-for-help probability,
  placement fallback, and inserted enemy row fields.
- 2026-04-30 twenty-second slice: promoted item/bomb action contracts into
  byte-neutral source comments plus `notes/c2-item-bomb-runtime-polish.md`.
  The promoted contracts cover item-side concentration seal, damage-plus-
  solidification, the `C2:724A` solidification text tail, bomb/super-bomb base
  damage constants, and splash targeting by sprite width/position.
- 2026-04-30 twenty-third slice: promoted Lifeup/fixed-amount healing contracts
  into byte-neutral source comments plus
  `notes/c2-lifeup-healing-runtime-polish.md`. The promoted contracts cover
  `C2:9AB8` as the selected-row fixed HP recovery common helper, the four
  canonical PSI-side Lifeup literals, and the distinction between PSI naming and
  later item/other action-table reuses.
- 2026-04-30 twenty-fourth slice: promoted asleep-status contracts into
  byte-neutral source comments plus `notes/c2-asleep-status-runtime-polish.md`.
  The promoted contracts cover the `C2:9F06` selected-row `+0x3C` resistance
  gate, `C2:724A` temporary subgroup write `+0x1F = 1`, and the reusable
  `C2:9F57` action-table wrapper.
- 2026-04-30 twenty-fifth slice: corrected and promoted the `C2:9E38..9F06`
  offense/defense stat-action corridor into byte-neutral source comments plus
  `notes/c2-offense-defense-stat-actions-runtime-polish.md`. The promoted
  contracts cover `9E38/9E7F` as offense-up body/wrapper and `9E86/9EFF` as
  defense-down body/wrapper.
- 2026-04-30 twenty-sixth slice: promoted late stat/resource action contracts
  into byte-neutral source comments plus
  `notes/c2-late-stat-resource-runtime-polish.md`. The promoted contracts cover
  `8E42` PP reduction, `8EAE` guts reduction, and `8F21` paired offense/defense
  reduction over selected-row fields and amount-bearing battle text.
- 2026-04-30 twenty-seventh slice: promoted direct-strange embedded status tails
  into byte-neutral source labels/comments plus
  `notes/c2-direct-strange-embedded-status-runtime-polish.md`. The promoted
  contracts cover `8DBB` direct strange, `8DFC` all-target crying, and `8E3B`
  as the asleep wrapper into `C2:9F06`.
- 2026-04-30 twenty-eighth slice: promoted enemy-side concentration/PSI-seal
  contracts into byte-neutral source comments plus
  `notes/c2-concentration-seal-runtime-polish.md`. The promoted contracts cover
  `8D41` as the luck threshold helper and `8D5A` as the enemy-side `+0x21 = 4`
  seal writer paired with item-side `A3D1`.
- 2026-04-30 twenty-ninth slice: promoted the C1/C2 battle
  action-selection record join into byte-neutral source aliases/comments. The
  promoted contracts cover `$A97D..$A982` as the battle action-selection record,
  `$A97C` as the resolved selected-item scratch byte, and the `C1:DE31/DE37/DE3D`
  far-call wrapper joins used by the battle-start present/message controller.
- 2026-04-30 thirtieth slice: continued `C2:311B` battle-start
  present/message controller polish with byte-neutral local aliases for the C1
  menu far wrappers, C2 selection snapshot/count helpers, C4 PSI/target
  candidate helpers, party/snapshot stride constants, and the Final Prayer
  phase-to-action row map (`$A97A` phases `4..12` -> action rows
  `0x123..0x12B`).
- 2026-04-30 thirty-first slice: joined CoilSnake `text_misc.yml` Battle Menu /
  Auto Fight to the local runtime path. `C2:311B` now names the `C4:9FE1`
  battle-menu text base and the `+0x20` Auto Fight row passed to the C1
  selection-menu builder.
- 2026-04-30 thirty-second slice: promoted the direct stat-increase and
  A056 stat-up amount-text callers into byte-neutral source aliases. The
  promoted contracts cover the selected-row stat offsets, live character mirror
  bytes, derived-stat refresh helper calls, C8 amount-bearing message scripts,
  and the `C1:DC66` substitution-payload ABI used to print the staged amount.
- 2026-04-30 thirty-third slice: promoted the `A3D1..A5EC` item-side text
  contracts with byte-neutral aliases for concentration/PSI-seal text,
  shield-expired/clear text, solidification text, shared no-effect text, and HP-sucker
  self/amount messages. The HP-sucker amount path now names the `C1:DC66`
  substitution-payload call and the `EF:7729` `PRINT_ACTION_AMOUNT` script.
- 2026-05-01 thirty-fourth slice: promoted the `A89D..AF1F`
  random-damage/status item cluster with byte-neutral aliases for poison,
  solidification, asleep, strange, and shared no-effect EF scripts; the C8
  doubled-guts and defense-up amount scripts; the C8/C9/EF text banks; and the
  `C1:DC1C` / `C1:DC66` text-dispatch ABIs used by the stable item-side leaves.
- 2026-05-01 thirty-fifth slice: promoted the small A-range item/status helper
  leaves (`A39D`, `A630`, `A82A`, `A86B`) with byte-neutral aliases for the
  poison-only cure row byte/value, solidification subgroup writes, random
  damage gates, typed damage helper, EF status-result scripts, and `C1:DC1C`
  direct-text dispatch ABI.
- 2026-05-01 thirty-sixth slice: promoted the late normalization/odor
  continuation seam (`AF1F`, `B172`) with byte-neutral aliases for the
  metamorphosis snapshot staging block, enemy mirror-success byte, EF
  metamorphose success/failure scripts, condiment lookup/removal helpers, C9
  spice hit/miss scripts, D5 item/condiment table anchors, and the shared
  `C1:DC1C` direct-text dispatch ABI.
- 2026-05-01 thirty-seventh slice: promoted the `A57A/A5D1/A5DA/A5E3`
  bottle-rocket family with byte-neutral aliases for the shared speed-gated
  hit loop, per-hit damage scaling, 25-percent variance helper, resist-adjusted
  damage helper, no-effect text fallback, and wrapper attempt counts `1`, `5`,
  and `20`.
- 2026-05-01 thirty-eighth slice: promoted the `7EAF..8BBE`
  hit-resolution/status-action cluster with byte-neutral aliases for C1
  battle-text dispatch, EF damage/miss/dodge/Spy/status scripts, C2 probability
  and HP/status helpers, reflected-hit context swaps, Time Stop return text,
  and the diamondize/paralyze/nausea/poison/cold primary-status tails. See
  `notes/c2-hit-resolution-status-runtime-polish.md`.
- 2026-05-01 thirty-eighth slice follow-up: aligned the physical shield tail
  with the EF payload split by naming row `+0x23` substates `3/4`, row `+0x25`
  shield countdown, `EF:70B1` power-shield physical reflection text, and
  `EF:7099` shared shield-expired cleanup text. The same pass corrected
  remaining `C1:DD7C` local aliases in `C2:92EE` and `C2:941D` to the
  byte-substitution staging contract.
- 2026-05-01 thirty-ninth slice: promoted the early
  window/HPPP/menu-selection corridor with byte-neutral aliases for HP/PP dirty
  party-window redraw state, open-window ticking, menu-cell classifier/scanner
  constants, current-window record fields, managed text-event snapshot layout,
  and HP/PP roller current/target/dirty fields. See
  `notes/c2-window-hppp-and-menu-selection-helpers-c20266-c2108c.md`.
- 2026-05-01 fortieth slice: promoted the C2 event-flag and party-status
  utility wrappers with byte-neutral aliases for the `$9C08` event-flag
  bitfield, C4 bitmask table, `$9C88` current interaction flag id, `$5D64`
  refresh target, `$988B` party status registry, `$99DC` state byte, and
  state-1/state-2 filters. See
  `notes/c2-party-inventory-status-utility-corridor-c216ad-c2307b.md`.
- 2026-05-01 forty-first slice: promoted the C2 equipment-preview and
  temporary party-source utility helpers with byte-neutral aliases for the
  `$9CD0..$9CD6` preview slot block, live equipped-slot bytes
  `$99FF/$9A00/$9A01/$9A02`, `C1:A1D8` preview renderer, temporary source
  save/restore block `$983A..$9849`, and the small respawn/warp target
  snapshot helper at `C2:30F3`. See
  `notes/equipment-preview-slot-block-9cd0-9cd6.md`,
  `notes/c2-party-inventory-status-utility-corridor-c216ad-c2307b.md`, and
  `notes/respawn-warp-target-snapshot-helper-c230f3.md`.
- 2026-05-01 forty-second slice: promoted the early window-title and HP/PP
  tilemap reset helpers with byte-neutral aliases for the default title tile
  run at `C3:E40E`, `$8272` title tile upload buffer, `$8650` window record
  title fields, `$894E` registered upload-slot table, `$7700` title VRAM
  destination base, and HP/PP tilemap/scratch clear ranges. See
  `notes/c2-window-hppp-and-menu-selection-helpers-c20266-c2108c.md`.
- 2026-05-01 forty-third slice: promoted the party overlay arbitration helper
  with byte-neutral aliases for `$986F` active entity source entries, `$98A4`
  active party count, `$99CE` party-character inventory slots, `D5:5000` item
  config row fields, overlay entity types `0x10/0x11`, and the C2 registry
  insert/remove calls. See `notes/party-overlay-arbitration-c216db-c3ebca.md`.
- 2026-05-01 forty-fourth slice: promoted the HP/PP status-tile lookup and
  item-subtype classifier tails with byte-neutral aliases for the seven-byte
  status slice scan, C4 status tile tables, no-status fallback values, `D5:5000`
  item config rows, packed item byte `+0x19`, equipment-slot subtype mask
  `0x0C`, and slot ordinal returns. See
  `notes/c2-party-inventory-status-utility-corridor-c216ad-c2307b.md`.
- 2026-05-01 forty-fifth slice: promoted the decimal digit and HP/PP
  tile-buffer staging helpers with byte-neutral aliases for `$8966..$8968`
  digit bytes, `$896D/$8975` tile buffer roots, digit tile source offsets,
  blank/visible digit tile offsets, and the `C2:0F08/0F26` HP/PP wrapper
  entries. See `notes/c2-window-hppp-and-menu-selection-helpers-c20266-c2108c.md`
  and `notes/c2-symbol-only-stragglers-c200d1-c20d3f.md`.
- 2026-05-01 forty-sixth slice: returned to the C1/C2 battle-text payload
  joins in the battle-start controller and instant-win handler. The promoted
  contracts cover direct `C1:DC1C` status/result text, `C1:DC66`
  substitution-payload victory text, `C1:DD7C` byte-substitution staging,
  EF/C8 battle-script constants, and the `$AA10 -> $9D11 -> EF:7BDF`
  present-item bridge. See
  `notes/c2-battle-start-payload-join-runtime-polish.md`.
- 2026-05-01 forty-seventh slice: promoted the call-for-help result text exits
  with byte-neutral aliases for the `C1:DC1C` direct-text ABI, EF battle-text
  bank, and the four ordinary/seed-flavored reinforcement scripts at `EF:77FD`,
  `EF:7810`, `EF:7824`, and `EF:7830`. See
  `notes/c2-call-for-help-runtime-polish.md`.
- 2026-05-01 forty-eighth slice: promoted the Rainbow Colors and Final Prayer
  direct battle-text exits with byte-neutral aliases for the `C1:DC1C` ABI,
  C8/C9 text banks, C8 Belch/Pokey scripts, and the C9 prayer/finale narrative
  scripts staged by `C2:C37A`, `C2:C41F`, `C2:C572`, and `C2:C6F0`. See
  `notes/class2-special-event-results-c29298-c2c14e.md` and
  `notes/c2-final-prayer-runtime-polish.md`.
- 2026-05-01 forty-ninth slice: returned to the Present/Check Present
  byte-substitution bridge and named the source-side item byte explicitly as
  `BattlePresentItemByte`. The promoted contracts cover D5 dropped-item and
  drop-rate offsets, the `C2:3109` UFO fallback records, the battle-start and
  instant-win `EF:7BDF` consumers, and the `C2:8881` Check Present companion
  at `EF:7DD5`. See `notes/c2-battle-start-payload-join-runtime-polish.md`,
  `notes/c2-hit-resolution-status-runtime-polish.md`, and
  `notes/class2-ufo-present-message-family.md`.
- 2026-05-01 fiftieth slice: tightened the `BTLACT_SPY` readout inside the
  hit-resolution/status-action cluster. The promoted contracts cover current
  target pointer use, offense/defense `DC66` amount payloads, the fire/freeze/
  flash/paralysis/hypnosis/brainshock resistance bytes, and the `0xFF`
  vulnerability sentinel that gates the direct readout text scripts. See
  `notes/c2-hit-resolution-status-runtime-polish.md`.
- 2026-05-05 fifty-first slice: tightened the `D5:7B68` battle-action row
  text lane across the battle-start front/back controllers and late selected-row
  nested action controller. The promoted contracts name the row root/bank,
  `0x0C` row size, row `+2/+3/+4/+8` fields, `C1:DD9F` primary current-action
  text display, and the separate companion payload pointer. See
  `notes/c2-battle-start-payload-join-runtime-polish.md`.
- 2026-05-05 fifty-second slice: carried the same `D5:7B68` action-row
  vocabulary upstream into `C2:4477`, where battler `current_action` (`+0x04`)
  selects the table row and row bytes `+0/+1` produce battler
  `action_targeting/current_target` (`+0x09/+0x0A`) for `C2:4703`. See
  `notes/c2-action-dispatch-runtime-polish.md`.
- 2026-05-05 fifty-third slice: tightened the `C2:4703` target-mask dispatcher
  and `C2:40A4` second-pointer payload consumer. The promoted contracts name
  the current target mask, derived-action code lanes, battler handoff offsets,
  `$A21C/$9FAC` payload target domains, and the shared `0x4E` row
  stride. See `notes/c2-action-dispatch-runtime-polish.md`.
- 2026-05-05 fifty-fourth slice: carried the same target-mask vocabulary into
  the C2 mask helper family. The promoted contracts name the `C4:A279` one-hot
  bit table, `$A96C/$A96E` current target mask, `$9FAC` battler-table root,
  consciousness/side/type/row/affliction offsets, and `0x4E` stride in the add/test/
  clear and build/remove helper sources. See `notes/class2-mask-helper-family.md`.
- 2026-05-05 fifty-fifth slice: closed the adjacent `6EF8`/`70E4` mask-helper
  tail with the same one-hot target bit, input/output mask, battler-row
  stride, and named test/clear helper contracts. See
  `notes/class2-mask-helper-family.md`.
- 2026-05-05 fifty-sixth slice: promoted the active battler text-context
  builders around `C2:3BCF` and `C2:3D05`. The source now names `$A970/$A972`
  as active attacker/target battler pointers, the `$A983/$A99E/$A9B9` battle
  name buffers, `$5E77/$5E78` article flags, the `D5:9589` enemy-data name
  lookup, party-record fallback through `$99CE + row * 0x5F`, the
  `$AD56/$AD7A/$AD82` front/back battler order lists, and the
  `$A96C/$A96E -> 9FAC + 0x4E * n` target-mask-to-battler rebuild. See
  `notes/c2-action-dispatch-runtime-polish.md` and
  `notes/class2-battlers-table-layout-9f8a-9fac.md`.
- 2026-05-05 fifty-seventh slice: normalized the C2 action/mask source
  vocabulary after the `$9FAC == BATTLERS_TABLE` correction. The affected
  source now names `$9FAC` as `BattlersTableBase`, `0x4E` as `BattlerRowSize`,
  `+0x04/+0x09/+0x0A/+0x0E` as battler action/target/side fields, and the
  mask-helper row tests as consciousness, npc id, row, and affliction bytes.
  Candidate wording is now reserved for the ranked `$AD7A/$AD82` lists in this
  slice. See `notes/c2-action-dispatch-runtime-polish.md` and
  `notes/class2-mask-helper-family.md`.
- 2026-05-05 fifty-eighth slice: returned to the selected-row
  collapse/late-controller route around `C2:7550/7680/77CA`. The promoted
  contracts name the descriptor death-text pointer field, battler
  consciousness/route/row/affliction fields, late active-marker byte `+0x4B`,
  late visual flag `D5:9589 + 0x5A`, active attacker/target pointers, and the
  D5-tagged companion scratch rebuild through `C2:B6EB` at `$A180`. This
  resolves the old `760C` `B6EB` caller bucket as a selected-row companion
  rebuild route, separate from the `4Dxx` battle-start initializer family. See
  `notes/c2-late-selected-row-runtime-polish.md` and
  `notes/class2-b6eb-caller-family-760c.md`.
- 2026-05-05 fifty-ninth slice: tightened the shared PSI timed-substate
  blocker and second-pointer payload consumer after the C1 DD9F tail pointer
  split. `C2:941D` now names the selected/target row pointers, selected-row
  action id and argument byte, `D5:7B68` table root/type byte, PSI action type,
  target timed-substate and countdown bytes, and `$AA94/$AA96` transient flags.
  `C2:40A4` now names `$00BC/$00BE` as the current action-payload pointer and
  `C4:A08D` as the special-case table used by the sibling mask-prune helper.
  See `notes/c2-psi-common-runtime-polish.md`,
  `notes/class2-psi-shield-post-hit-aa96.md`,
  `notes/c2-action-dispatch-runtime-polish.md`, and
  `notes/class2-second-pointer-consumer-40a4.md`.
- 2026-05-05 sixtieth slice: cleaned up two remaining action-table/payload
  edges outside the main action-dispatch modules. `C2:654C` now names the
  Magic Butterfly PP restore amount, party-slot count, PP target/max-PP fields,
  visual pass constants, and its embedded `D5:7B68` action-type helper.
  `C2:A89D..AF1F` now calls the named `C2:40A4` action-payload applicator at
  its local payload tail. See
  `notes/c2-instant-win-and-magic-butterfly-helpers-c26189-c2654c.md`,
  `notes/c2-item-bomb-runtime-polish.md`, and
  `notes/c2-action-dispatch-runtime-polish.md`.
- 2026-05-05 sixty-first slice: finished the nearby A89D payload-tail mask
  vocabulary pass. The embedded `C2:6E00` helper inside the `6C82` source
  module now has a local source label as the all-active battler target-mask
  builder, `C2:90C6` now calls that role by name, and the A89D item/status
  tail now names the `6BFB/6C82/6E00/6E77/6EF8/70E4` mask-helper sequence
  before handing the selected second-pointer payload to `C2:40A4`. The
  hit-resolution `C2:7EAF` retargeting tail also now calls the named `C2:6EF8`
  first-match finder. See
  `notes/class2-mask-helper-family.md`,
  `notes/class2-late-normalization-and-odor-family-c29051-c29254.md`,
  `notes/c2-item-bomb-runtime-polish.md`,
  `notes/c2-hit-resolution-status-runtime-polish.md`, and
  `notes/c2-action-dispatch-runtime-polish.md`.
- 2026-05-06 sixty-second slice: returned to the early HP/PP window composer
  and its battle-presentation blink callers. `C2:03C3` now names the
  party-slot map, character record base/stride, HP/PP window option word,
  current HP/PP and dirty/status fields, focused HP/PP window id, tilemap
  base, HP/PP tile-buffer row bases, `C0:8F22` text-length helper, and local
  `C2:0F08/0F26` HP/PP tile-buffer wrappers. The battle-background per-frame
  and cleanup helpers now call `C2:07E1/07B6` by their HP/PP clear/redraw
  roles while naming `$ADA4/$ADA6` as the HP/PP box blink duration/target pair.
  See `notes/c2-window-hppp-and-menu-selection-helpers-c20266-c2108c.md`,
  `notes/c2-battle-bg-load-update-runtime-polish.md`, and
  `notes/c2-battlebg-load-and-palette-effect-corridor-c2cfe5-c2e0e7.md`.
- 2026-05-06 sixty-third slice: moved to the front-door C2 window/text reset
  initializer at `C2:00D1/00D9`. The source now names the open-window chain,
  window-record index/base/stride, text-entry record base/stride, title-upload
  slot table, current focus id, HP/PP tilemap clear range, text display/sound
  latches, and the `C4:3F53` menu/name-entry mask-table reload into `$1AD6`.
  See `notes/c2-symbol-only-stragglers-c200d1-c20d3f.md` and
  `notes/c2-window-hppp-and-menu-selection-helpers-c20266-c2108c.md`.
- 2026-05-06 sixty-fourth slice: tightened the tiny C2 audio/music wrapper
  strip at `C2:16AD/16C9/16D0` and its C1 text-command callers. `C2:16AD`
  now names `$5DD6` as the current map music track and `$5DD4` as the softer
  latched mirror; `C2:16D0` now retires `PLAY_SOUND_AND_UNKNOWN` in favor of
  `PlaySoundAndTickLightWindow`; C1 `1F 00..03` callers now use named C0/C2
  contracts for play-music, stop-music, play-sound, and restore-current-map
  music. See `notes/c2-party-inventory-status-utility-corridor-c216ad-c2307b.md`
  and `notes/text-command-family-1f-deferred-callbacks.md`.
- 2026-05-06 sixty-fifth slice: carried the same caller/callee polish into
  the temporary party source save/restore leaves. C1 `1F 64/65` now names the
  `C2:3008/307B` contracts directly, tying the dynamic source-selector leaves
  to the C2 block that saves `$983A/$983B/$983C/$983E/$9831/$9833`, removes
  the active source ids from `$986F`, and later restores the saved state. See
  `notes/c2-party-inventory-status-utility-corridor-c216ad-c2307b.md` and
  `notes/text-command-family-1f-deferred-callbacks.md`.
- 2026-05-06 sixty-sixth slice: continued the C1 dynamic source-selector
  caller cleanup with the current-interaction-flag leaves. C1 `1F A0/A1/A2`
  now names the `C2:26C5/26E6` wrappers directly, tying set, clear, and read
  text-command behavior to the C2 `$9C88` flag id and `$5D64` refresh target
  contracts. See
  `notes/c2-party-inventory-status-utility-corridor-c216ad-c2307b.md` and
  `notes/text-command-family-1f-deferred-callbacks.md`.
- 2026-05-06 sixty-seventh slice: named the C2 save-current-game wrapper and
  its C1 callers. `C2:2A2C` now names `$B4A1` as the current save slot and
  `EF:0A4D` as the save-slot helper, while preserving inherited
  `SAVE_CURRENT_GAME`; C1 `1F B0` and the debug menu save command both call the
  wrapper by role. See
  `notes/c2-party-inventory-status-utility-corridor-c216ad-c2307b.md` and
  `notes/text-command-family-1f-deferred-callbacks.md`.
- 2026-05-06 sixty-eighth slice: normalized C2's C4 audio caller vocabulary
  after the C0/C4 music contracts stabilized. Candidate-pool setup, instant
  win, rainbow event, Final Prayer, and battle-swirl presentation callers now
  use `C4FBBD_ChangeMusic`; the instant-win tail also names the bicycle track
  and fallback `C0:6A07` current-position music refresh edge. See
  `notes/c2-party-inventory-status-utility-corridor-c216ad-c2307b.md` and
  `notes/c0-current-position-music-refresh-c068f4-c069af.md`.
- 2026-05-06 sixty-ninth slice: tightened the C2 action-dispatch and
  mask-helper contract names now that `$9FAC` is settled as the battler table.
  The mask family now exposes battler-domain aliases for active typed
  battlers, enemy-side battlers, target-parameter matched battlers, all active
  battlers, active NPC battler removal, affliction-flagged pruning, and
  row-state filtering. `C2:4703`, `C2:40A4`, `C2:3D05`, Thunder,
  normalization, and A89D payload-tail consumers now prefer those aliases while
  preserving older `TARGET_*`/candidate labels as compatibility anchors. See
  `notes/c2-action-dispatch-runtime-polish.md` and
  `notes/class2-mask-helper-family.md`.
- 2026-05-06 seventieth slice: carried the battler-table correction into the
  second-stage target/result corridor. `C2:BAC5` now names its 32-row scan as
  filtered second-stage battler-row counting, while `C2:BB18` and `C2:BC5C`
  distinguish six selected-row source-entry passes from the live battler rows
  they mirror into. The source now names the `$9FB8/$9FBA/$9FBB/$9FBC/$9FC9`
  family as source-entry battler fields, `$A972` as the active target battler
  pointer, the `+0x1D..+0x23` collapse-controller state bytes, and the
  `EF:6C6B` collapse/affliction text edge. See
  `notes/c2-target-selection-runtime-polish.md` and
  `notes/c2-late-selected-row-runtime-polish.md`.

## Validation

Future implementation passes should use:

```powershell
python tools\build_source_bank_scaffold.py --bank C2
python tools\validate_source_bank_byte_equivalence.py --bank C2 --module all --combined --scaffold src\c2\bank_c2_helpers_asar.asm --strict
python tools\build_source_bank_candidate_ranges_doc.py --bank C2
python tools\build_source_bank_residual_map.py --bank C2
```

This planning pass does not alter C2 source or generated manifests.
