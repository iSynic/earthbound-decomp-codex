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

## Validation

Future implementation passes should use:

```powershell
python tools\build_source_bank_scaffold.py --bank C2
python tools\validate_source_bank_byte_equivalence.py --bank C2 --module all --combined --scaffold src\c2\bank_c2_helpers_asar.asm --strict
python tools\build_source_bank_candidate_ranges_doc.py --bank C2
python tools\build_source_bank_residual_map.py --bank C2
```

This planning pass does not alter C2 source or generated manifests.
