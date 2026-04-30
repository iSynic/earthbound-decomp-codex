# C0 Runtime Semantic Polish Plan

Primary queue context: `notes/source-readiness-triage.md` and
`notes/project-status.md`.

## Current State

`C0` is structurally closed as a working-name anchored source scaffold. The
handoff in `notes/bank-c0-source-scaffold-handoff.md` reports byte-equivalence
as `OK`, but the source surface still preserves byte corridors rather than
claiming decoded source for the overworld/runtime bank. The working-name pool in
`notes/bank-c0-working-name-proposals.md` is the main promotion input.

## Subsystem Slices

- Entity/task lifecycle: entity slot reset, byte-pool allocation, visual state
  reserve/release, spawned entity setup, task callback records.
- Movement runtime: camera steps, map strip refresh, movement record queues,
  surface compatibility, party trail snapshots, scripted movement modes.
- Interaction runtime: directional input, front-facing probes, interactable
  target resolution, post-transition script hooks.
- Collision and terrain: collision byte reads, footprint probes, surface masks,
  cached map-property lookups, collision cache refresh.
- Teleport and transition: teleport selector state, suppression slots, flyover
  and transition staging, post-transition placement.
- Presentation helpers: landing profile rows, PPU/VRAM transfer queues, display
  waits, audio/display frame callbacks, battle-background load bridge.

## First Pass Order

1. Start with movement plus collision because those routines have the clearest
   subsystem boundary and strong local note coverage.
2. Fold in entity/task lifecycle once movement consumers prove stable slot and
   task-field names.
3. Promote interaction and teleport contracts after movement/collision names are
   settled enough to avoid churn.
4. Finish with presentation helpers where C4 and audio-facing side effects need
   cross-bank wording.

## Evidence Inputs

- `notes/bank-c0-source-scaffold-handoff.md`
- `notes/bank-c0-working-name-proposals.md`
- `notes/bank-c0-progress-audit.md`
- `notes/data-contracts-c0-c2.md`
- `notes/data-contracts-c0-c4.md`
- subsystem notes cited from the working-name proposal evidence column

## Expected Outputs

- A per-slice checklist of labels/comments safe to promote from working names.
- Contract notes for WRAM fields, task records, collision masks, and cross-bank
  C2/C4 helper calls when evidence is strong.
- Future source edits that convert byte corridors only after the slice has local
  note evidence, stable naming, and a byte-equivalence validation path.

## Implementation Notes

- 2026-04-30 first slice: added byte-neutral source comments for the movement
  plus collision path centered on `C0:4C45`, `C0:449B`, `C0:54C9`, `C0:5B7B`,
  `C0:5DE7`, and the `$28DA[slot]` collision/terrain cache wrappers. The
  rollup lives in `notes/c0-movement-collision-runtime-polish.md`.
- 2026-04-30 second slice: added byte-neutral source comments for the early
  entity visual lifecycle centered on `$467E` record allocation, `$4A00`
  visual-memory reservations, `EF:133F` sprite-pose descriptors, C0:1E49 slot
  creation, spawn candidate commits, and release paths. The rollup lives in
  `notes/c0-entity-visual-runtime-polish.md`.
- 2026-04-30 third slice: added byte-neutral source comments for interaction
  runtime centered on C0:404F input mapping, C0:4116/C0:42EF single-facing
  probes, C0:41E3/C0:43BC facing-rotation policy, C0:4279/C0:4452 public
  resolvers, and the type-6/C4 door fallback split. The rollup lives in
  `notes/c0-interaction-runtime-polish.md`.
- 2026-04-30 fourth slice: added byte-neutral source comments for teleport
  state/setup centered on `$9F3F..$9F69` PSI teleport state, transition object
  slots `$18..$1D`, `$5156` snapshots, `$10B6` interaction suppression, and
  the C0:EA99 mainloop shell. The rollup lives in
  `notes/c0-teleport-state-runtime-polish.md`.
- 2026-04-30 fifth slice: added byte-neutral source comments for teleport
  movement/restore callbacks centered on C0:E28F, C0:E516, C0:E674, C0:E776,
  C0:E3C1/C0:E6FE snapshot-ring restores, and success/failure setup paths.
  The rollup lives in `notes/c0-teleport-callback-runtime-polish.md`.
- 2026-04-30 sixth slice: added byte-neutral source comments for the C0
  presentation queue/NMI handoff centered on the `$91/$92/$94/$96/$97` transfer
  ABI, `$0400` queued DMA descriptors, `$99` queue byte throttling, `$2C/$2E`
  scroll-buffer flipping, and NMI scroll commits. The rollup lives in
  `notes/c0-presentation-queue-runtime-polish.md`.
- 2026-04-30 seventh slice: added byte-neutral source comments for the task
  allocator/runtime core centered on `$0A50/$0A52/$0A54`, `$0A9E`, `$0ADA`,
  `$125A`, task-slot callbacks, and the C0:DB0F default dispatcher. The rollup
  lives in `notes/c0-task-pool-runtime-polish.md`.

## Validation

Future implementation passes should use:

```powershell
python tools\promote_working_names_to_source_scaffold.py --bank C0 --force
python tools\build_source_bank_scaffold.py --bank C0
python tools\validate_source_bank_byte_equivalence.py --bank C0 --module all --combined --scaffold src\c0\bank_c0_helpers_asar.asm --strict
python tools\build_source_bank_candidate_ranges_doc.py --bank C0
python tools\build_source_bank_residual_map.py --bank C0
```

This planning pass does not run or require those regeneration steps.
