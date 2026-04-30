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
