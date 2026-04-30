# C1 Battle Front-End Runtime Polish

Status: first C1 battle-facing polish slice.

This note records the byte-neutral source comments added after the C0 runtime
semantic polish slices. The slice focuses on the shared battle target resolver,
the battle item selection/action bridge, and the battle-text pointer wrapper
that joins C1 menu-side selection to C2 battle behavior and EF text payloads.

## Source Modules Touched

| Source module | Runtime contract pinned |
| --- | --- |
| `src/c1/c1_adb4_determine_battle_targetting.asm` | Treats input `A` as a D5:7B68 battle action id, input `X` as acting battler/character slot, reads the 12-byte action row direction/target subtype bytes, and returns selected target plus C0:923E target-class flags. |
| `src/c1/c1_ce85_resolve_selected_battle_item_action.asm` | Resolves a battle item-selection record through C3:E977, indexes the D5:5000 item table at stride 0x27, uses item bytes +0x19/+0x1C/+0x1D to gate usability and select the D5:7B68 action id passed to C1:ADB4. |
| `src/c1/c1_cfc6_open_battle_item_selection_loop.asm` | Opens the battle item inventory loop only when the actor has inventory, renders item rows, stores the chosen slot into the shared selection record, and repeats when C1:CE85 rejects the selected item. |
| `src/c1/c1_dc1c_display_battle_text_from_pointer.asm` | Restages caller-local EF battle-text far pointers into the generic C1:86B1 text dispatch ABI while honoring the shared battle-text gate at `$98B1/$0065`. |

## Evidence Inputs

- `notes/bank-c1-subsystem-and-symbol-synthesis.md`
- `notes/bank-c1-working-name-proposals.md`
- `notes/battle-targetting-resolver-c1adb4-af50.md`
- `notes/battle-item-action-selection-c1ce85-c1cfc6.md`
- `notes/battle-text-entry-family-c1dc1c-dd7c.md`
- `notes/c2-ef-battle-text-contract-workahead.md`

## Runtime Contract

The battle item path uses a small caller-owned selection record:

- byte `+0`: actor/character id
- byte `+1`: selected inventory slot
- word `+2`: action class or resolved item action word
- byte `+4`: mapped target/result byte
- byte `+5`: actor byte copied for downstream battle action state

`C1:CFC6` owns the menu loop around that record. `C1:CE85` resolves the chosen
slot into an item id through C3:E977, reads the D5:5000 item row, and delegates
target selection to `C1:ADB4` when item category/usability bits allow it.

`C1:ADB4` is the shared targetting resolver for D5:7B68 battle action rows. It
uses row byte `+0` as the direction lane and row byte `+1` as the target subtype,
then packs the selected target id with C0:923E target-class flags on return.

`C1:DC1C` remains a text-entry wrapper, not a text VM decoder. Its stable
contract is pointer restaging and battle-text gate handling before dispatching
through C1:86B1.

## Promotion Boundary

This slice promotes comments and local runtime wording only. It does not rename
remaining branch-local labels, assign final symbolic names to individual target
flag bits, or decode every C7 battle-text pointer selected by item failure and
choice-text lanes.

Open followups:

- correlate C0:923E return flag bit names against C2 battle action consumers
- split the adjacent C1:AF73 use-item bridge if future source ownership needs a
  narrower module boundary
- join D5:5000 item field names to CoilSnake diff-confirmed item table probes
- expand `C1:DC66..DD7C` substitution variants after EF payload consumers are
  polished

## Validation

Run after source-comment edits:

```powershell
python tools\validate_source_bank_byte_equivalence.py --bank C1 --module all --combined --scaffold src\c1\bank_c1_helpers_asar.asm --strict
```
