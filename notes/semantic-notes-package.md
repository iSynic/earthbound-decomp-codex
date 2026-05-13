# Semantic Notes Package

This note defines the current documentation package for semantic work after the
bank first-pass sweep. The `bank-*-first-pass.md` files are retained as
historical inventory notes: they prove every configured bank was classified, but
they are no longer the right place for ongoing subsystem findings.

## Current Package Layers

| Layer | Role | Primary Notes |
| --- | --- | --- |
| Historical bank inventory | First-pass bank classification and artifact lists. Treat as stable background, not the live work log. | `notes/bank-first-pass-coverage-index.md`, `notes/bank-*-first-pass.md` |
| Structural/source closure | Byte-equivalence, preserved-corridor closure, and source-readiness state. | `notes/source-scaffold-status.md`, `notes/readable-source-bank-closure.md`, `notes/source-readiness-triage.md` |
| Phase-2 semantic status | Live map of subsystem understanding, weak zones, and next semantic lanes. | `notes/phase-2-semantic-status.md`, `notes/project-status.md` |
| Runtime semantic polish | C0/C1/C2/C4/EF subsystem execution plans and follow-up notes. | `notes/runtime-semantic-polish-plans.md`, `notes/c0-runtime-semantic-polish-plan.md`, `notes/c1-runtime-semantic-polish-plan.md`, `notes/c2-runtime-semantic-polish-plan.md`, `notes/c4-runtime-semantic-polish-plan.md`, `notes/ef-runtime-semantic-polish-plan.md` |
| VM and localization semantics | Event/actionscript, text-command, localization, and script export semantics. | `notes/c3-actionscript-semantics-audit.md`, `notes/text-command-semantics-manifest.md`, `notes/text-vm-localization-semantics-closeout.md` |
| Data and asset contracts | Table, subrecord, audio, graphics, and source-emission contracts. | `notes/asset-data-contract-frontier.md`, `notes/ui-font-town-map-asset-contracts.md`, `notes/audio-sequence-command-semantics.md`, bank-specific contract notes |
| Community/reference alignment | ebsrc and EB-M2 compatibility, aliases, and conflict review. | `notes/ebsrc-community-crosswalk.md`, `notes/ebsrc-knowns-integration-candidates.md`, `notes/eb-m2-name-crosswalk.md`, `notes/eb-m2-needs-review-triage.md` |

## Naming Policy Going Forward

- Do not append new semantic discoveries to a `bank-*-first-pass.md` note unless
  the discovery corrects the original inventory.
- Use subsystem notes for live work: `c2-*-runtime-polish.md`,
  `c4-*-presentation-contracts.md`, `ef-*-runtime-closure.md`, and similar
  names that say what was studied.
- Use `phase-2` only for orientation/status notes, not every leaf note. Leaf
  notes should be named by subsystem or evidence target.
- If a note supersedes an old first-pass claim, link both ways and state that
  the newer note is authoritative for semantics.
- Keep generated dashboards generated. Human-written status notes should point
  to generated reports rather than duplicate all of their tables.

## How To Read The Old First-Pass Notes

The first-pass notes answer:

- What spans/assets/code regions did we identify first?
- What references or generated manifests were available at that time?
- What was the original follow-up queue?

They should not be read as the latest semantic truth for a subsystem. For live
semantic confidence, start with `notes/phase-2-semantic-status.md`, then follow
the runtime, VM, data-contract, or crosswalk note listed there.
