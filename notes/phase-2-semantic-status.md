# Phase-2 Semantic Status

Phase 2 is the current semantic refinement layer after first-pass bank coverage
and readable source closure. Its goal is not to prove that every byte exists in a
scaffold; that is already tracked elsewhere. Its goal is to state how well the
repo understands behavior, data contracts, and port-facing meaning.

The execution roadmap for this phase is `notes/phase-2-semantic-closure-plan.md`.

## Baseline

- Bank first-pass coverage is complete for `C0..EF`; those notes are historical
  inventory.
- Source scaffolds are byte-equivalent for the configured banks.
- Readable-source closure is complete for the audited source-heavy banks:
  `C0`, `C1`, `C2`, `C4`, and `EF`.
- Current semantic work is organized by subsystem, VM, data contract, and
  reference-alignment lane rather than by first-pass bank note.
- Ghidra-SNES `v1.0.0-rc1` is installed in the dedicated pilot worktree as a
  supporting visual/decode oracle only; local source, traces, and manifests
  remain authoritative for names and behavior. The refreshed pilot kept the
  successful EarthBound HiROM import but did not materially change sampled
  memory blocks, labels, or lane decodes versus `v0.2.0`.

## Live Semantic Lanes

| Lane | Current Confidence | What Is Strong | What Still Needs Work |
| --- | --- | --- | --- |
| C0 overworld/runtime | Medium-high | Many entity, movement, interaction, collision, teleport, task, input, audio-bridge, and presentation routines have caller-backed names and byte-equivalence validation. | Large subsystem surface; some names are intentionally side-effect-oriented and should keep gaining comments/tests around WRAM contracts. |
| C1 text/menu/UI | Medium-high | Text VM dispatch, menu/front-end corridors, file-select joins, and many text command leaves have manifests and local evidence. | Some final names depend on C2 battle semantics, C4 renderer behavior, and EF text/data payload joins. |
| C2 battle runtime | Medium-high | Action dispatch, target/status/effect families, PSI/common handlers, Final Prayer, and battle visual tails have substantial polish. The C-port feedback diary has now been folded into `notes/c-port-feedback-intake.md` as 36 battle-runtime trace/action candidates, with a generated 10-oracle manifest/index, stub-validated execution packet, real-runner emulator handoff for the five first-pass jobs, local Mesen runner wrapper, strict `ok` result validation, save-state probe tooling, fixture-scout tooling, and results summary now showing 6 trace-observed non-stub results with 2 proof-grade `refined_contract` promotions. The generated `notes/battle-action-row-crosswalk.md` now gives all 318 D5 battle-action rows a table-backed C1/C2/EF navigation layer. The numbered `F:\Mesen2\SaveStates` fixture set is a major runtime unblock: the manual probe matrix now validates 194 Mesen/raw-trace summaries across historical, replaced-slot, controlled resource, natural-resource scout, startup-only resource, and collapse-tail helper fixtures. Saves 1, 2, 3, 4, 5, 7, and 8 have produced `c2_8125_damage_abi_boundary` minimum hits across physical damage, PSI damage, Healing, and Large Pizza recovery; save 8 adds an offensive-PSI damage route with C1 text/display joins; and the replaced save 4 now reaches `C2:724A` for Dread Scorpion poison, though the paired natural `C2:9917` status-gate path remains follow-up. Reviewed natural traces now promote the `C2:8125` damage ABI, selected-row HP mutation, C1 amount-text join, HP-to-zero collapse boundary, `C2:7550 -> C2:77CA` order, and hard/collapsed row-state installation. `tools/build_c2_fixture_roms.py` now adds ignored table-patched ROM fixtures for Runaway Dog `C2:40A4` neutralize/final-action probes, Bash-row `C2:40A4` and resource steering probes, Dread Skelpion poison reruns, direct helper-entry collapse-tail probes, and enemy PP field patch support, reducing the need for manual save-state hunting. `notes/c2-b930-controlled-snapshot-export.md` now records the forced-entry `C2:B930` `$99CE -> $9FFA` snapshot field-export mechanics without treating the C1 route as proven. `notes/c2-snapshot-export-natural-scout.md` records 12 existing-save natural scout attempts that confirm the current saves are mostly `C2:BAC5` neighbors rather than pre-export callsite captures. `notes/c2-resource-amount-controlled-comparison.md` now captures WRAM-seeded, action-row-steered no-WRAM, seeded natural-table, and startup-only PSI Magnet/PP-reduction comparisons; the startup-only captures reach `C2:9F5E`/`C2:8E42` without resource-specific on-hit PP seeding but show selected target PP remains zero, while `notes/c2-resource-amount-natural-candidates.md` still isolates 12 vanilla resource-action candidates for the remaining natural PP proof lane. | Some action leaves and status edge cases still need final naming and proof-oriented comments; the weakest work is now selected-target PP setup for a cleaner scripted-entry resource fixture, natural PP amount proof against Gigantic Ant/Starman/Mobile Sprout and Guardian General/Mad Duck/Armored Frog candidates, natural paired `C2:724A`/`C2:9917` status-gate closure, unpatched `C1:CFC6`/`C2:B930` command-prompt snapshot capture, natural timing for optional collapse tails such as `C2:7680` and `C2:BC5C`, and broader caller-family coverage for the promoted damage ABI. |
| C3 event/actionscript VM | Medium | Raw frontier is closed and opcode/operand audit exists. The durable C3 scaffold now includes the event/actionscript source-pilot scaffold for `C3:0000..E450`; that pilot includes 141 source files, 183 spans, and 56,650 validated bytes after promoting the C3:0100/C3:0142 system-screen helpers, while the full bank remains at `12` protected ranges with `0` mismatches. | VM operand semantics, callback contracts, and script-source emission are not yet as mature as the source-heavy runtime banks. |
| C4 presentation/PPU | Medium-high | Text tile staging, window/color/HDMA helpers, town-map/file-select, credits/photo, and presentation islands have local source and contracts. | PPU/color side effects benefit from more subsystem-level comments and emulator probes. |
| C5..C9 text banks | Medium | Text-bank structure and command usage are decoded enough for regression and extraction. | Port-ready text still depends on complete text-command VM and authoring macro semantics. |
| Data/table banks | Medium-high by shape, medium by gameplay label | CF/D0/D5/D7/D8/DA/DC/DF/E0/E1 have table/subrecord contracts, value counts, and source-emission policies. D5 battle-action rows now have a generated crosswalk that separates row `+4` presentation pointers from row `+8` behavior pointers. | Some second planes, selector meanings, and human-facing labels remain numeric until consumer evidence proves names. |
| Audio/SPC700 | Medium-high for source labels, medium for exact duration | Sound-driver source now backs VCMD labels, arg lengths, and reader paths. | Exact duration promotion remains blocked for commands whose runtime timing/effect is not locally proven. |
| EF mixed runtime/data/text | Medium | Save/SRAM, debug/menu, battle-text, map/text/glyph corridors, and late helper regions have improved source closure. | Large text/help/menu runs and some payload joins still need stronger script/data semantics. |
| ebsrc/community alignment | Medium-high as crosswalk, selective as source | Exact-address ebsrc names are integrated or crosswalked with alias-first policy. | Community-preferred names should be added as compatibility aliases only when exact-address and role-compatible. |

## Confidence Language

- `High`: byte-equivalent, exact-address, local callers and side effects are
  understood, and external references corroborate or do not conflict.
- `Medium-high`: byte-equivalent and locally well explained, but more comments,
  tests, or edge-case proofs would still improve port confidence.
- `Medium`: structure and key consumers are known, but not every operand,
  table field, timing effect, or gameplay-facing label is proven.
- `Low`: reference vocabulary, macro-only evidence, payload-only labels, or
  names without a local reader-path proof.

## Note Ownership

Use these starting points instead of adding new material to first-pass notes:

- Runtime source banks: `notes/runtime-semantic-polish-plans.md`.
- Phase 2 execution roadmap: `notes/phase-2-semantic-closure-plan.md`.
- C-port feedback: `notes/c-port-feedback-intake.md` and
  `notes/c2-battle-trace-oracle-plan.md`, with generated queue
  `notes/c2-battle-trace-oracle-index.md` and execution packet
  `notes/c2-battle-trace-oracle-packet.md`; real-runner setup starts at
  `notes/c2-battle-trace-oracle-emulator-handoff.md` and
  `notes/c2-battle-trace-oracle-mesen-runner.md`, and result intake lives in
  `notes/c2-battle-trace-oracle-results-summary.md`.
- C3 VM: `notes/c3-actionscript-semantics-audit.md` and
  `notes/c3-actionscript-semantics-roadmap.md`; validate the current
  complete-decode/value-readiness contract with
  `tools/validate_c3_actionscript_semantics_audit.py`.
- Text/localization VM: `notes/text-command-semantics-manifest.md` and
  `notes/text-vm-localization-semantics-closeout.md`.
- Data/assets: `notes/asset-data-contract-frontier.md`,
  `notes/battle-action-row-crosswalk.md`, and the bank-specific contract notes
  linked from them.
- Audio: `notes/audio-sequence-command-semantics.md`,
  `notes/audio-exact-duration-triage.md`, and
  `notes/audio-duration-readiness-rollup.md`.
- ebsrc alignment: `notes/ebsrc-community-crosswalk.md` and
  `notes/ebsrc-knowns-integration-candidates.md`.

## Practical Rule

First-pass notes are inventory. Phase-2 notes are evidence. If new work changes
our understanding of behavior, write or update the relevant phase-2 subsystem
note and leave the first-pass note alone unless its original inventory is wrong.
