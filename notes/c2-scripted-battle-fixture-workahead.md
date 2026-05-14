# C2 Scripted Battle Fixture Workahead

This note records the next autonomous runtime-proof accelerator after the
numbered Mesen save-state scout. It is a workahead note, not proof-grade
evidence and not a source-promotion basis.

## Goal

Build an ignored fixture ROM that can enter a chosen scripted battle without a
user-provided `.mss` save state, then steer one enemy/action condition for C2
trace-oracle work.

The target entry is `C2:2F38` / `INIT_BATTLE_SCRIPTED`, not the later debug
`C2:4821` battle routine. `INIT_BATTLE_SCRIPTED` still reads the D0 battle-entry
pointer table, expands the enemy-list payload into `$9F8A/$9F8C`, sets `$4DC2`,
runs the battle swirl path, waits for transition completion, and enters common
battle init.

## Proposed Fixture Shape

- Scenario id: `scripted-entry-group0-force-enemy-action`.
- Patch `D0:D52D`, the existing group-0 enemy-list payload, to a compact list:
  `01 <enemy_id lo> <enemy_id hi> FF`.
- Keep `D0:C60D` group 0 pointing at `D0:D52D` unless a later proof requires a
  new payload island.
- Patch the chosen enemy's D5 action fields for deterministic behavior:
  `action_order`, `action_1..4`, optional `final_action`, and optional HP/speed.
- Reuse existing `tools/build_c2_fixture_roms.py` action-row steering helpers
  for lanes such as Flash/status, PSI Magnet, PP reduction, and `C2:40A4`.
- Add the smallest possible autostart hook that loads `A = #$0000` and calls
  `JSL C22F38_InitBattleScripted`.

## Proof Boundary

This fixture can prove fixture reachability and downstream helper mechanics. It
cannot prove ordinary overworld encounter provenance, natural enemy action
probabilities, natural C1 command-menu routing, or any C2 source semantics
without a reviewed trace result.

The first success criterion is only:

- generated ROM boots far enough to call `C2:2F38`
- the trace observes `C2:E8E0` or the common battle-init route
- a chosen downstream target, such as `C2:40A4`, `C2:724A`, `C2:9F5E`, or
  `C2:8E42`, becomes reachable without a user save state

## Files To Touch

- `tools/build_c2_fixture_roms.py`: add the scenario, D0 payload patch, D5 enemy
  row patching, and caveats.
- `tools/run_c2_battle_trace_oracle_mesen.py`: already supports no-state runs,
  but fixture config may need an autostart fixture role.
- `tools/validate_c2_battle_trace_local_fixtures.py`: allow a
  `fixture_rom_autostart` role where `save_state_path` is absent.
- `tools/build_c2_battle_trace_oracle_manifest.py`: optionally add `C2:2F38`,
  `C2:E8E0`, `C2:E9C8`, and `C052AA` as startup provenance hints.

## Safety Rules

- Generated ROMs remain ignored under `build/c2/fixture-roms/`.
- Every byte patch must be recorded in the generated fixture manifest.
- Autostart hooks are reachability tools only.
- Do not promote source comments or names from scripted-entry fixture traces
  until local ASM agreement and reviewed trace results exist.
