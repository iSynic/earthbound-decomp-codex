# Runtime Semantic Polish Plans

This is the queue-level index for the first runtime semantic polish lane called
out by `notes/source-readiness-triage.md` and `notes/project-status.md`.

## Scope

- Priority banks: `C0`, `C1`, `C2`, `C4`, and `EF`.
- Outcome: one small execution plan per bank before source edits begin.
- Non-goals: no scaffold regeneration, no symbol promotion, no runtime source
  changes, and no generated manifest updates in this planning pass.

## Plan Set

| Bank | Plan | Runtime focus |
| --- | --- | --- |
| `C0` | `notes/c0-runtime-semantic-polish-plan.md` | overworld entity/task, movement, interaction, collision, teleport, presentation |
| `C1` | `notes/c1-runtime-semantic-polish-plan.md` | text engine, menus, battle front ends, file select, C2/C4/EF joins |
| `C2` | `notes/c2-runtime-semantic-polish-plan.md` | battle action dispatch, targeting, status/effects, PSI, Final Prayer, visuals |
| `C4` | `notes/c4-runtime-semantic-polish-plan.md` | renderer contracts, text tiles, HDMA/color/window helpers, presentation |
| `EF` | `notes/ef-runtime-semantic-polish-plan.md` | save/SRAM, debug menus, text/glyph/data corridors, battle-text payload joins |

## Shared Execution Rules

- Treat existing notes as evidence, not as a replacement for local source
  review when implementation starts.
- Promote names and comments subsystem by subsystem; do not run bank-wide
  semantic churn as one monolith.
- Record cross-bank contracts where the caller and callee semantics are both
  understood enough to hold a stable name.
- Keep byte-equivalence validation as the backstop after any future source
  conversion or source-facing semantic edit.

## Shared Documentation Checks

- Each bank plan links back to the primary queue/status docs and the bank
  handoff or synthesis notes that define current state.
- Each bank plan identifies first-pass order, evidence inputs, expected outputs,
  and validation gates.
- This index remains a planning document only; source and manifest changes
  belong to later implementation passes.

## Implementation Status

- 2026-04-30: C0 movement/collision first slice landed as byte-neutral source
  comments plus `notes/c0-movement-collision-runtime-polish.md`.
- 2026-04-30: C0 entity/visual lifecycle second slice landed as byte-neutral
  source comments plus `notes/c0-entity-visual-runtime-polish.md`.
- 2026-04-30: C0 interaction runtime third slice landed as byte-neutral source
  comments plus `notes/c0-interaction-runtime-polish.md`.
- 2026-04-30: C0 teleport state/setup fourth slice landed as byte-neutral
  source comments plus `notes/c0-teleport-state-runtime-polish.md`.
- 2026-04-30: C0 teleport callback fifth slice landed as byte-neutral source
  comments plus `notes/c0-teleport-callback-runtime-polish.md`.
- 2026-04-30: C0 presentation queue/NMI sixth slice landed as byte-neutral
  source comments plus `notes/c0-presentation-queue-runtime-polish.md`.
- 2026-04-30: C0 task allocator/runtime seventh slice landed as byte-neutral
  source comments plus `notes/c0-task-pool-runtime-polish.md`.
- 2026-04-30: C1 battle front-end first slice landed as byte-neutral source
  comments plus `notes/c1-battle-front-end-runtime-polish.md`.
- 2026-04-30: C1 battle PSI second slice landed as byte-neutral source
  comments plus `notes/c1-battle-psi-runtime-polish.md`.
- 2026-04-30: C1 text gate third slice landed as byte-neutral source comments
  plus `notes/c1-text-gates-runtime-polish.md`.
- 2026-04-30: C1 text entry fourth slice landed as byte-neutral source comments
  plus `notes/c1-text-entry-runtime-polish.md`.
- 2026-04-30: C1 selection prompt fifth slice landed as byte-neutral source
  comments plus `notes/c1-selection-prompt-runtime-polish.md`.
- 2026-05-06: C1 selection-prompt dispatch/core follow-up landed as
  byte-neutral named helper-call polish plus
  `notes/character-selection-prompt-dispatch-c1242e-c12bf3.md`.
- 2026-05-06: C1 debug/window tick follow-up landed as byte-neutral named
  helper-call polish plus
  `notes/debug-menu-window-tick-helpers-c12bf3-c12d17.md`.
- 2026-05-06: C1 open-menu/debug tail follow-up named the reference-backed
  `OPEN_HPPP_DISPLAY`, `SHOW_TOWN_MAP`, debug flag/guide/level/goods helpers,
  and the C0 overworld button edges into those C1 contracts. See
  `notes/open-menu-prelude-helpers-c1339e-c133b0.md` and
  `notes/debug-menu-reachability-c0-c1-ef.md`.
- 2026-05-06: C1 open-menu helper-call follow-up named the main
  `C1:33B0..4103` text-entry, selection, target-prompt, item-transfer,
  HP/PP focus, PSI/equipment/teleport, tick, and cleanup helper edges, with a
  follow-up closing the final AF74/03DC/0FEA raw edges. See
  `notes/open-menu-prelude-helpers-c1339e-c133b0.md`.
- 2026-05-06: C1 small helper cleanup named local edges in the
  interaction-output selectors, active-window descriptor initializer, and
  `$89D4` text-entry constructor chain. See
  `notes/interaction-result-consumers.md` and
  `notes/text-entry-record-builder-neighbors-c10f40-c11887.md`.
- 2026-05-06: C1 low text-command strip follow-up named helper-call edges
  across `C1:4103..4558`: 24-bit target assembly, `JUMP_MULTI` context reads,
  event-flag high-byte assembly, flag set/clear/check, call-text dispatch,
  number selection, context installs, focus/window wrappers, and C4
  glyph/cursor staging. See
  `notes/lower-bank01-text-control-strip-00-17.md`.
- 2026-05-06: C1 adjacent low text-command/inventory follow-up named helper
  edges across `C1:4558..4EAB`, covering workmem/argmem staging,
  character-selection queue builders, print/layout helpers, item-class tests,
  wallet mutations, HP/PP wrappers, inventory give/take/search helpers, and
  preset teleport joins. The current text-context workmem setter label is now
  corrected to `C1:0443`. See
  `notes/lower-bank01-text-control-strip-00-17.md` and
  `notes/text-command-family-1d-inventory-money.md`.
- 2026-05-06: C1 `C1:4EAB..575D` text-command corridor follow-up named the
  helper-call surface for parameterized pause, shop/inventory menus, item
  buy/sell price wrappers, item compatibility, character-name and
  number/money printing, status/ailment helpers, special-selector loaders,
  required-experience staging, Escargo storage cleanup, item insertion, and
  inventory-slot removal. See `notes/text-command-10-parameterized-pause.md`,
  `notes/text-command-family-1c-print-display.md`, and
  `notes/text-command-family-1d-inventory-money.md`.
- 2026-04-30: C1 display-helper sixth slice landed as byte-neutral source
  comments plus `notes/c1-display-helper-runtime-polish.md`.
- 2026-04-30: C1 equipment-menu seventh slice landed as byte-neutral source
  comments plus `notes/c1-equipment-runtime-polish.md`.
- 2026-04-30: C1 file-select eighth slice landed as byte-neutral source
  comments plus `notes/c1-file-select-runtime-polish.md`.
- 2026-04-30: C1 inventory/recovery ninth slice landed as byte-neutral source
  comments plus `notes/c1-inventory-recovery-runtime-polish.md`.
- 2026-04-30: C2 target-selection first slice landed as byte-neutral source
  comments plus `notes/c2-target-selection-runtime-polish.md`.
- 2026-04-30: C2 action-dispatch second slice landed as byte-neutral source
  comments plus `notes/c2-action-dispatch-runtime-polish.md`.
- 2026-04-30: C2 stat-consequence third slice landed as byte-neutral source
  comments plus `notes/c2-stat-consequence-runtime-polish.md`.
- 2026-04-30: C2 affliction-recovery fourth slice landed as byte-neutral source
  comments plus `notes/c2-affliction-recovery-runtime-polish.md`.
- 2026-04-30: C2 selected-row controller fifth slice landed as byte-neutral
  source comments plus `notes/c2-selected-row-controller-runtime-polish.md`.
- 2026-04-30: C2 late selected-row controller sixth slice landed as byte-neutral
  source comments plus `notes/c2-late-selected-row-runtime-polish.md`.
- 2026-04-30: C2 PSI common-helper seventh slice landed as byte-neutral source
  comments plus `notes/c2-psi-common-runtime-polish.md`.
- 2026-04-30: C2 PSI Flash eighth slice landed as byte-neutral source comments
  plus `notes/c2-psi-flash-runtime-polish.md`.
- 2026-04-30: C2 late status ninth slice landed as byte-neutral source comments
  plus `notes/c2-late-status-runtime-polish.md`.
- 2026-04-30: C2 PSI animation tenth slice landed as byte-neutral source
  comments plus `notes/c2-psi-animation-runtime-polish.md`.
- 2026-04-30: C2 battle overlay eleventh slice landed as byte-neutral source
  comments plus `notes/c2-battle-overlay-runtime-polish.md`.
- 2026-04-30: C2 battle-background palette twelfth slice landed as byte-neutral
  source comments plus `notes/c2-battle-bg-palette-runtime-polish.md`.
- 2026-04-30: C2 battle-background load/update thirteenth slice landed as
  byte-neutral source comments plus
  `notes/c2-battle-bg-load-update-runtime-polish.md`.
- 2026-04-30: C2 Final Prayer fourteenth slice landed as byte-neutral source
  comments plus `notes/c2-final-prayer-runtime-polish.md`.
- 2026-04-30: C2 battle sprite fifteenth slice landed as byte-neutral source
  comments plus `notes/c2-battle-sprite-runtime-polish.md`.
- 2026-04-30: C2 `SHOW_PSI_ANIMATION` sixteenth slice landed as byte-neutral
  source comments plus `notes/c2-show-psi-animation-runtime-polish.md`.
- 2026-04-30: C2 loaded battle-background frame generator seventeenth slice
  landed as byte-neutral source comments plus
  `notes/c2-loaded-bg-frame-generator-runtime-polish.md`.
- 2026-04-30: C2 STEAL helper eighteenth slice landed as byte-neutral source
  comments plus `notes/c2-steal-runtime-polish.md`.
- 2026-04-30: C2 call-for-help nineteenth slice landed as byte-neutral source
  comments plus `notes/c2-call-for-help-runtime-polish.md`.
- 2026-04-30: C2 item/bomb twentieth slice landed as byte-neutral source
  comments plus `notes/c2-item-bomb-runtime-polish.md`.
- 2026-04-30: C2 Lifeup/fixed-amount healing twenty-first slice landed as
  byte-neutral source comments plus `notes/c2-lifeup-healing-runtime-polish.md`.
- 2026-04-30: C2 asleep-status twenty-second slice landed as byte-neutral source
  comments plus `notes/c2-asleep-status-runtime-polish.md`.
- 2026-04-30: C2 offense/defense stat-action twenty-third slice landed as
  byte-neutral source comments plus
  `notes/c2-offense-defense-stat-actions-runtime-polish.md`.
- 2026-04-30: C2 late stat/resource twenty-fourth slice landed as byte-neutral
  source comments plus `notes/c2-late-stat-resource-runtime-polish.md`.
- 2026-04-30: C2 direct-strange embedded-status twenty-fifth slice landed as
  byte-neutral source labels/comments plus
  `notes/c2-direct-strange-embedded-status-runtime-polish.md`.
- 2026-04-30: C2 concentration/PSI-seal twenty-sixth slice landed as
  byte-neutral source comments plus `notes/c2-concentration-seal-runtime-polish.md`.
