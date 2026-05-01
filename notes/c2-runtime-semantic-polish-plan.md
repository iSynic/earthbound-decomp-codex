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
- Target selection: candidate pool population, row ranking, steal targets,
  random battler selection, front/back row behavior.
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
  The promoted contracts cover `D5:7B68` descriptor metadata use, candidate row
  `+0x09/+0x0A` derived action bytes, `$A96C/$A96E` as the current 32-bit target
  mask, and `C2:40A4` as the second-pointer payload applicator.
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
  shield-clear text, solidification text, shared no-effect text, and HP-sucker
  self/amount messages. The HP-sucker amount path now names the `C1:DC66`
  substitution-payload call and the `EF:7729` `PRINT_ACTION_AMOUNT` script.
- 2026-05-01 thirty-fourth slice: promoted the `A89D..AF1F`
  random-damage/status item cluster with byte-neutral aliases for poison,
  solidification, asleep, strange, and shared no-effect EF scripts; the C8
  doubled-guts and defense-up amount scripts; the C8/C9/EF text banks; and the
  `C1:DC1C` / `C1:DC66` text-dispatch ABIs used by the stable item-side leaves.

## Validation

Future implementation passes should use:

```powershell
python tools\build_source_bank_scaffold.py --bank C2
python tools\validate_source_bank_byte_equivalence.py --bank C2 --module all --combined --scaffold src\c2\bank_c2_helpers_asar.asm --strict
python tools\build_source_bank_candidate_ranges_doc.py --bank C2
python tools\build_source_bank_residual_map.py --bank C2
```

This planning pass does not alter C2 source or generated manifests.
