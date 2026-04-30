# C1 Runtime Semantic Polish Plan

Primary queue context: `notes/source-readiness-triage.md` and
`notes/project-status.md`.

## Current State

`C1` is ready for semantic promotion rather than corridor closure. The main
navigation layer is `notes/bank-c1-subsystem-and-symbol-synthesis.md`, with
candidate names in `notes/bank-c1-working-name-proposals.md`. Some final names
depend on C2 battle internals, C4 renderer behavior, and EF save/text helpers.

## Subsystem Slices

- Text engine and menu core: text entry/wait gates, window focus, low-level
  rendering primitives, character select prompt, menu open helpers.
- Text command leaves: dispatcher leaves for flags, jumps, work memory,
  inventory/money, recovery, teleport, timed events, and special events.
- Battle front ends: target selection, battle PSI user selection, battle item
  action selection, battle text display, HP/PP window redirects.
- Equipment and file-select flows: equipment menu controller, derived equipment
  caches, naming buffer, window-flavour preview, copy/delete/setup menus.
- Cross-bank joins: C2 battle action/result flow, C4 renderer and text-tile
  helpers, EF save/menu data routines and substitution payloads.

## First Pass Order

1. Start from the C1/C2 battle-facing loop recommended by
   `notes/bank-c1-subsystem-and-symbol-synthesis.md`: `C1:ADB4`,
   `C1:CE85`, `C1:CFC6`, and `C1:DC1C`.
2. Promote battle front-end names only with matching C2 action/status evidence.
3. Tighten text command leaves and menu/file-select names after renderer and EF
   calls are labeled with stable contract wording.
4. Leave parser-only compressed-bank pseudo-opcode and localization macro work
   to the existing text VM follow-up queues unless a concrete C1 source edit
   needs it.

## Evidence Inputs

- `notes/bank-c1-subsystem-and-symbol-synthesis.md`
- `notes/bank-c1-working-name-proposals.md`
- `notes/bank-c1-progress-audit.md`
- `notes/text-command-semantics-manifest.md`
- `notes/text-vm-localization-semantics-closeout.md`
- `notes/c2-ef-battle-text-contract-workahead.md`

## Expected Outputs

- Stable promoted names for high-confidence C1 text/menu/battle/file-select
  routines.
- Cross-bank contract notes for C1 callers into C2, C4, and EF, especially
  battle target/result text and file-select save helper paths.
- Deferred-item notes for names that remain provisional because their callee
  side is not yet semantically polished.

## Validation

Future implementation passes should rerun C1 source scaffold validation after
any source-facing edits:

```powershell
python tools\build_source_bank_scaffold.py --bank C1
python tools\validate_source_bank_byte_equivalence.py --bank C1 --module all --combined --scaffold src\c1\bank_c1_helpers_asar.asm --strict
python tools\build_source_bank_candidate_ranges_doc.py --bank C1
python tools\build_source_bank_residual_map.py --bank C1
```

This planning pass is documentation-only.
