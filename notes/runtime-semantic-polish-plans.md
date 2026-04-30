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
- 2026-04-30: C1 display-helper sixth slice landed as byte-neutral source
  comments plus `notes/c1-display-helper-runtime-polish.md`.
- 2026-04-30: C1 equipment-menu seventh slice landed as byte-neutral source
  comments plus `notes/c1-equipment-runtime-polish.md`.
