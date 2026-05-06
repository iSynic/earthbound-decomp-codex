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

## Implementation Notes

- 2026-04-30: First C1 battle front-end slice landed as byte-neutral source
  comments plus `notes/c1-battle-front-end-runtime-polish.md`. The promoted
  contracts cover the D5:7B68 target resolver, D5:5000 item action bridge,
  battle item-selection loop, and C1:DC1C battle-text pointer wrapper.
- 2026-04-30: Second C1 battle PSI slice landed as byte-neutral source
  comments plus `notes/c1-battle-psi-runtime-polish.md`. The promoted
  contracts cover the D5:8A50 PSI ability row fields, PSI user/category/entry
  selection helpers, PP guard, target handoff, and final menu-selection
  writeback.
- 2026-04-30: First C1 text/menu-core slice landed as byte-neutral source
  comments plus `notes/c1-text-gates-runtime-polish.md`. The promoted
  contracts cover pointer staging, wait-frame pumping, focus/window drains,
  prompt gates, halt-control handling, text-state waits, and active descriptor
  lookup.
- 2026-04-30: Second C1 text/menu-core slice landed as byte-neutral source
  comments plus `notes/c1-text-entry-runtime-polish.md`. The promoted
  contracts cover `$89D4` active text-entry records, constructors,
  chain count/layout/render helpers, selection update helpers, and active-window
  clear behavior.
- 2026-04-30: Third C1 text/menu-core slice landed as byte-neutral source
  comments plus `notes/c1-selection-prompt-runtime-polish.md`. The promoted
  contracts cover `$AD56/$AD58` candidate counts, `$AD5A/$AD6A` candidate
  bytes, scan/eligibility helpers, two-list prompt control, simple side prompt
  control, and the conservative C1:242E dispatcher boundary.
- 2026-04-30: C1 display-helper slice landed as byte-neutral source comments
  plus `notes/c1-display-helper-runtime-polish.md`. The promoted contracts
  cover item-name, statistic-selector, PSI/small-label, and target-prompt
  display adapters.
- 2026-04-30: C1 equipment-menu slice landed as byte-neutral source comments
  plus `notes/c1-equipment-runtime-polish.md`. The promoted contracts cover
  item byte `+0x19` slot-family dispatch, item parameter `+0x1F` preview and
  comparison use, live slots `$99FF/$9A00/$9A01/$9A02`, shadow slots
  `$9CD0..$9CD3`, comparison markers `$9A1D..$9A20`, shop item selection joins,
  and the top-level party equipment controller.
- 2026-04-30: C1 file-select slice landed as byte-neutral source comments plus
  `notes/c1-file-select-runtime-polish.md`. The promoted contracts cover
  save-slot status bytes `$B49E..$B4A0`, selected slot `$B4A1`, action/copy/delete
  menu results, EF save-copy/delete/setup helper calls, setup bytes
  `$98B6/$98B7/$99CD`, the file-select session wrapper, and the lead-entity
  redraw predicate.
- 2026-04-30: C1 inventory/recovery helper slice landed as byte-neutral source
  comments plus `notes/c1-inventory-recovery-runtime-polish.md`. The promoted
  contracts cover the 14-byte inventory list `$99F1..$99FE`, live equipment-slot
  index maintenance during removal, active-party wildcard scans from `$986F`,
  item-family insertion/removal side effects, and the HP/PP recovery/depletion
  target-selection quartet.
- 2026-04-30: C1/C2 battle action-selection join polish landed as byte-neutral
  source aliases/comments. The promoted contracts name the C1 far-call wrapper
  table entries for menu, character prompt, item selection, and PSI category
  selection, plus the `C1:CFC6/CE85` battle item-selection record and
  `D5:5000` item-row fields consumed by the target/action resolver.
- 2026-05-01: C1 battle-text wrapper contract polish landed as byte-neutral
  source aliases. The promoted contracts name the caller-frame pointer slots,
  `$98B1/$0065` battle-text gate, `$9643` mode latch, prompt-wait and
  mode-1/no-prompt display values, and the primary script versus substitution
  payload argument pairs for `C1:DC1C`, `C1:DC66`, `C1:DD82`, and `C1:DD9F`.
- 2026-05-01: C1 substitution-slot leaf polish landed as byte-neutral source
  aliases. The promoted contracts tighten the `0x19 0x1E/0x1F`
  display-text loaders, `$9D11` byte payload, `$9D12/$9D14` pointer payload,
  DP-frame alias shifts, and the `DD7C/DD82` far wrappers that bridge C2/EF
  battle-text scripts into the local display-text engine.
- 2026-05-01: C1 text-command `0x19` tail polish landed as byte-neutral source
  aliases. The promoted contracts name the `0x19 21..28` helper-pointer tail,
  the mushroomized selector byte loader, item equipment-class return values,
  and the `0x19 27` statistic-selector value staging path through `C3:EE7A`
  and `C1:045D`.
- 2026-05-01: C1 statistic-selector character polish landed as byte-neutral
  source aliases. The promoted contracts name the `0x19 28` `C4:550F`
  selector-table walk, current text-context character index, out-of-range zero
  result, and display-text staging pair used before `C1:045D`.
- 2026-05-01: C1 loaded-string collector polish landed as byte-neutral source
  aliases. The promoted contracts name the `0x19 02` inline byte collector,
  `$97D7/$97CA` loaded-string buffer/count, `$97BA..$97BC` companion-byte queue,
  packed companion metadata path into `C1:13D1`, and the `0x19 14` Escargo
  storage byte staging path.
- 2026-05-01: C1 delivery/pickup queue polish landed as byte-neutral source
  aliases. The promoted contracts name the `0x19 1C/1D` deferred argument
  bytes, three-entry queue rooted at `$97F5`, owner/source and item-byte side
  fields, pending-item versus inventory-removal paths, and primary/secondary
  text-context output staging.
- 2026-05-01: C1 inventory/storage/count text-command polish landed as
  byte-neutral source aliases. The promoted contracts name the `0x19 19`
  character inventory-slot item read, `0x19 1A` Escargo storage item byte read,
  and `0x19 1B` loaded-string count helper, including primary and secondary
  text-context staging outputs.
- 2026-05-01: C1 status/experience text-command polish landed as byte-neutral
  source aliases. The promoted contracts name the `0x19 16` status-group byte
  read through `C4:58AF`, `0x19 05` nonbattle status write through `C4:58FE`,
  and `0x19 18` required-experience remaining helper through `C4:599A`.
- 2026-05-01: C1 character identity text-command polish landed as byte-neutral
  source aliases. The promoted contracts name the `0x19 10` active overworld
  registry type-code read and the `0x19 11` character-name letter lookup
  through `C2:22D3`, including current text-context indexing and primary
  text-context result staging.
- 2026-05-01: C1 battle-text ABI follow-up landed as byte-neutral source
  comments/constants. The promoted contracts now distinguish the one-pointer
  `DC1C` lane, the primary-script plus `$9D12/$9D14` payload lane at `DC66`,
  the pointer-only staging lane at `DD82`, the mode-1/no-prompt action-table
  lane at `DD9F`, and the `19 1E/19 1F/1C 0F` text-command consumers.
- 2026-05-01: C1 display-text payload consumer polish landed as byte-neutral
  comments/constants. The `19 1E` pointer-substitution leaf now names its
  `$9D12/$9D14` source, and the `1C 0F` amount-print branch in the dynamic
  selector corridor now names `C1:AD26`, `$0E/$10` staging, and `C1:0DF6`.
- 2026-05-05: C1 battle item-use bridge follow-up tightened the adjacent
  `C1:AF73..B5B6` lane now that C2 action-table vocabulary is stable. The
  promoted source constants name the `D5:5000` item config row fields,
  `D5:7B68 +0x04/+0x08` action-row text pointers, fixed C7 item-use failure
  text pointers, CF:8985 fallback text lookup, the `$9FAC` handoff row, and the
  `$9FFA` battle selection snapshot copied back into `$99DC`. See
  `notes/battle-targetting-resolver-c1adb4-af50.md`,
  `notes/battle-item-action-selection-c1ce85-c1cfc6.md`, and
  `notes/battle-choice-text-family-c1b2ec-b997.md`.
- 2026-05-05: C1 battle PSI controller/formatter follow-up aligned
  `C1:C8BC` and `C1:CB7F..CE73` with the same D5 action-table vocabulary. The
  promoted constants name `D5:8A50` PSI ability rows, `D5:7B68` action rows,
  action row `+0x03` PP cost, encoded `C3:F124` menu-entry rows, the fixed
  `C3:F11C` tail, the PP guard current-PP mirror, and final battle-menu
  selection record offsets. See `notes/c1-battle-psi-runtime-polish.md`,
  `notes/battle-psi-menu-controller-c1cc39-ce73.md`, and
  `notes/battle-psi-name-builder-family-c1c8bc-ca06-c3f112-f124.md`.
- 2026-05-05: C1 outer battle PSI user-selection follow-up tightened
  `C1:B5B6..BB71` after the lower controller vocabulary stabilized. The
  promoted constants name `$9D16/$9D18/$9D19` as selected-user, fast-path, and
  highlight-row bytes, the PP guard and category-8 blocker/event branch, the
  `D5:8A50` ability-row to `D5:7B68` action-row joins, and the ordinary
  `$9FFA/$A972` snapshot export plus `$99DC` state mirror copyback. See
  `notes/battle-psi-user-selection-front-end-c1b5b6-b7c6.md`,
  `notes/c1-battle-psi-runtime-polish.md`, and
  `notes/battle-selection-snapshot-export-c2b930.md`.
- 2026-05-05: C1 battle text/equipment tail follow-up tightened
  `C1:DD9F..E1A2`. The promoted constants name the `D5:7B68` Bash/Shoot
  text and companion-payload offsets, selected-row item/equipment/stat and
  resistance fields, party inventory and equipped-slot bases, C7 equip-ok and
  cannot-use-weapon scripts, D5 item equipment flags, and the C1/C2/C3/C4
  helper calls used to remove items, refresh equipment subtype caches, convert
  resistance bytes, and redraw focused HP/PP rows. See
  `notes/battle-text-entry-tail-dd82-dd9f.md`,
  `notes/battle-text-entry-family-c1dc1c-dd7c.md`, and
  `notes/c2-ef-battle-text-contract-workahead.md`.
