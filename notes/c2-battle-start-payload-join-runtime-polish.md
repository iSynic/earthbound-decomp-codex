# C2 Battle-Start Payload Join Runtime Polish

Primary queue context: `notes/c2-runtime-semantic-polish-plan.md`,
`notes/c2-ef-battle-text-contract-workahead.md`,
`notes/source-readiness-triage.md`, and `notes/project-status.md`.

## Scope

This pass covers the battle-start controller and instant-win text payload joins
in:

- `src/c2/c2_5024_run_battle_start_candidate_controller_front.asm`
- `src/c2/c2_5afb_run_battle_start_candidate_controller_back.asm`
- `src/c2/c2_6189_fill_instant_win_tile_buffer_and_upload.asm`

The edit is semantic source polish only. It promotes local aliases, constants,
and comments while preserving byte-equivalence.

## Promoted Contracts

- `C1:DC1C` is named as the direct `$0E/$10` battle-text pointer dispatch.
- `C1:DC66` is named as the `$12/$14` substitution-payload display wrapper.
- `C1:DD7C` is named as the byte-substitution setter for `$9D11`.
- The battle-start front half now names `EF:78F7`, `EF:84F3`, and `EF:8511`
  as the Sensei Monster and player-flee result scripts.
- The battle-start back half now names the C8 PSI-cannot script, EF target/
  status/victory scripts, and the `EF:7BDF` present script.
- The instant-win handler now names `EF:7A28` as the forced-win script and
  reuses the `EF:7BDF` present script for the optional present item byte.
- Follow-up action-table polish now names the local `D5:7B68` row root/bank,
  the `0x0C` row size, the `+2/+3/+4/+8` row fields used by battle-start, and
  the `C1:DD9F` primary-message lane versus the later companion-payload lane.

## Payload Joins

The newly named `BattlePresentItemByte` paths are the concrete C2 side of the
byte-substitution bridge:

- `C2:4A8A` preserves the enemy record dropped-item byte from D5 record
  offset `+0x58`, applies the D5 drop-rate byte at `+0x57`, and falls back to
  the UFO-specific present table at `C2:3109` when the ordinary drop byte is
  empty.
- `BattlePresentItemByte` (`$AA10`) is loaded as an 8-bit value by the
  battle-start and instant-win present paths.
- `C1:DD7C` stages it into `$9D11`.
- `EF:7BDF` (`MSG_BTL_PRESENT`) later consumes it through the `0x19 0x1F`
  byte-substitution command before printing the item name.
- `C2:8881` uses the same byte slot for the Check Present / Spy companion
  script at `EF:7DD5`, then clears the slot after display.

The victory scripts continue to use `C1:DC66` with `$12/$14` populated from the
accumulated result pointer/value pair, keeping them separate from direct
`C1:DC1C` status-result text.

## Action-Table Text Lane

`D5:7B68` is now treated consistently as a `0x0C`-byte battle-action row table
inside the C2 battle-start front/back halves and the late selected-row nested
action controller:

- row `+2` gates battle-start action-type/presentation branches;
- row `+3` is the PP-cost byte checked before the C8 PSI-cannot script;
- row `+4` is the primary action text far pointer staged into `$0E/$10` and
  displayed through `C1:DD9F`;
- row `+8` is the companion action payload pointer applied after target
  validation.

This keeps the C1 `DD9F` wrapper as the explicit current-action text lane and
separates it from ordinary direct text (`DC1C`) and substitution payload
(`DC66`) callers.

## Evidence Inputs

- `notes/c2-ef-battle-text-contract-workahead.md`
- `notes/class2-ufo-present-message-family.md`
- `notes/class2-battle-text-cluster-overview.md`
- `refs/EB-M2-Listing-v1/US/bank08.txt`
- `refs/EB-M2-Listing-v1/US/bank2F.txt`

## Validation

Future implementation gates remain the normal C2 scaffold and byte-equivalence
checks:

```powershell
python tools\build_source_bank_scaffold.py --bank C2
python tools\validate_source_bank_byte_equivalence.py --bank C2 --module all --combined --scaffold src\c2\bank_c2_helpers_asar.asm --strict
```
