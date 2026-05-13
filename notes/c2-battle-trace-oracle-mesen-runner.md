# C2 Battle Trace Oracle Mesen Runner

This note describes the local Mesen execution bridge for the Phase 2 C2
trace-oracle queue. It is intentionally fixture-light: ROMs, save states, raw
traces, and run summaries stay under ignored local paths.

## Role

The Mesen runner is a runtime evidence collector, not a source authority. It
executes the generated per-job Lua skeletons from
`build/c2/battle-trace-oracles/mesen-runner-assets/`, writes raw JSONL traces
under `build/c2/battle-trace-oracles/<oracle>/`, and optionally writes a
non-proof unresolved result. Reviewed proof-grade results still have to pass
`tools/validate_c2_battle_trace_oracle_result.py` and the collector before any
source-facing semantic promotion.

Generated skeletons accept `C2_ORACLE_INPUT_PATTERN` through the wrapper. The
pattern reuses the prior Mesen route syntax: `atom:frames,atom:frames`. Locally
proven atoms are `neutral`, `none`, `right`, `left`, `up`, `down`,
`down_right`, `up_right`, `up_left`, `down_left`, `a`, `start`, and `a_start`.
Current skeletons emit rich breakpoint rows using `emu.getState()`: CPU
`A/X/Y/DB/DP/P/SP/K/PC`, cycle count, a direct-page byte window, the `$A972`
selected-target pointer, and the pointed-to 96-byte battler row. For the
`selected_target_row` watch, `address` is now the resolved row pointer and
`pointerAddress` records the original `$A972` pointer cell.

## Local Fixture Status

- `F:\Mesen2\Mesen.exe` and `F:\Mesen\Mesen.exe` are known local Mesen2
  executable paths used by testRunner work.
- `EarthBound (USA).sfc` is discoverable through `tools/rom_tools.py` in this
  checkout.
- Older local save states exist under `F:\Mesen\SaveStates`; the current
  battle fixture set is the numbered `F:\Mesen2\SaveStates` set documented
  below.
- A boot-only smoke run with `c1_c2_target_action_staging` and a 10-frame limit
  launches Mesen and writes an ignored run summary/raw trace successfully. It
  records no C2 proof hits and should not be treated as behavior evidence.
- The local save-state probe lane tested all seven currently discoverable
  `F:\Mesen\SaveStates\*.mss` files for `c1_c2_target_action_staging`.
  Mesen loaded every state and produced nonempty traces, but none hit the
  minimum C1/C2 battle-command addresses (`C1:ADB4`, `C1:CE85`, `C1:CFC6`,
  `C2:B930`). Those states are useful runner smoke fixtures, not ready battle
  proof fixtures.
- The fixture scout then tested those same seven states under neutral, confirm,
  and small movement-loop patterns against ordinary battle-entry and command
  PCs. All 21 runs completed, but none reached `C0:D19B`, `C0:D323`,
  `C0:44DA`, `C0:B731`, `C2:E8E0`, `C2:2F38`, `C2:4821`, `C2:311B`,
  `C1:ADB4`, `C1:CE85`, `C1:CFC6`, `C2:B930`, or `C2:BAC5`.
- An overwritten earlier save-state slot captured the start of the first dog
  random battle and proved the Mesen route can reach `C2:BAC5` and `C2:8125`.
  That file is no longer the live numbered fixture. Use the hashes in this note
  for the current `EarthBound (USA)_1..7.mss` set.
- The current numbered fixture set under `F:\Mesen2\SaveStates` is the best
  C2 runtime input so far:

| Save | Local State | SHA-256 | Role |
| --- | --- | --- | --- |
| `1` | `EarthBound (USA)_1.mss` | `6cba602ac4c0c934ce97a1c215a8a1e2f9e9a89c552f9c7fd9cba58e78c84377` | standard command menu, Bash highlighted |
| `2` | `EarthBound (USA)_2.mss` | `a0cee58506e6a361fba56fa7521f502c636830bc5c43ccb230459fffc1e0772c` | target select in a multi-enemy fight |
| `3` | `EarthBound (USA)_3.mss` | `26cd24f40f17a8aa720b9421026a2ee74dfb30922400a6a747a867be883d35fe` | PSI menu, Offense highlighted |
| `4` | `EarthBound (USA)_4.mss` | `30381044ccf3b64523d0f6222fa7c8bd681abe648307dfeecd5129cf5ee0fcbd` | Goods menu, Large Pizza selected |
| `5` | `EarthBound (USA)_5.mss` | `a62a6efa4d9ae7ea216695566fa5f6d31115b49bffb431bfb778cd88a28929fb` | attack selected, before damage numbers |
| `6` | `EarthBound (USA)_6.mss` | `b70d49925f8fbf84b83ed510a0eb324bfd6a8dda1046d1e83f4b216c1d609716` | Paula already has sunstroke |
| `7` | `EarthBound (USA)_7.mss` | `facbb2ebb317a4e92488f564fbccbe44de1392428fd617c6150c66c8719f620c` | Jeff was hit by a SMAAAASH attack; HP is rolling |

- The seven-save fixture scout ran neutral plus one-through-four confirm
  patterns: 35 completed runs, 22 battle-entry candidates, and 0 full command
  candidates. The useful C1 hits are `C1:ADB4` from the PSI/menu target path
  and `C1:CE85` from the Goods path. The current probes still do not hit
  `C1:CFC6` or `C2:B930`, so `c1_c2_target_action_staging` remains split across
  partial traces rather than a single ready fixture.
- Targeted first-pass oracle runs produced 51 valid Mesen/raw-trace summaries.
  The strongest result is `c2_8125_damage_abi_boundary`: saves 1, 2, 3, 4, 5,
  and 7 satisfy the minimum `C2:8125` hit under either a complete-turn confirm
  pattern or a neutral wait. Save 3 also reaches `C2:941D`, giving a useful PSI
  damage/status-gate sample.
- Save 5 has also been rerun through the richer canonical
  `c2_8125_damage_abi_boundary` output path. The reviewed result validates as
  non-stub `ok` / `needs_followup`: it proves `C2:8125` reachability with
  captured amount input `A = 0x0045`, damage selector `X = 0x00FF`, direct page,
  and selected target row pointer `$A21C`, but keeps downstream text/collapse
  interpretation blocked until those fields are decoded.
- `c2_40a4_current_action_payload` does not yet hit its minimum `C2:40A4`, but
  saves 1, 2, 3, 4, 5, and 7 repeatedly hit nearby `C2:3D05`. Treat those as
  route hints only.
- The current set did not satisfy the first-pass affliction-writer or resource
  amount-pair minimums. Save 6 is useful as an already-afflicted-state
  snapshot, but not as proof of the affliction writer.

The first useful fixture to create is an ordinary battle state just before
choosing a command. That should target `c1_c2_target_action_staging`, because it
only needs the C1 target/action staging path and C2 candidate export path.

The least invasive proof route is a normal overworld enemy encounter, then a
local Mesen save at the first battle command prompt. The ordinary-entry
provenance chain to confirm is:

1. `C0:D19B` prepares the encounter slot and battle id.
2. `C0:D323` builds `$9F8A/$9F8C` enemy entries.
3. `C0:44DA` sets `$4DC2 = FFFF` after the encounter countdown.
4. `C0:B731` enters the overworld battle initializer with `$4DC2 != 0`.
5. `C2:4821` reaches the shared battle runtime while skipping the `$4DC2 == 0`
   debug/default seed block at `C2:4830`.

## Commands

Initialize and validate the ignored local fixture config:

```powershell
python tools\run_c2_battle_trace_oracle_mesen.py --init-fixtures-template
python tools\validate_c2_battle_trace_local_fixtures.py --allow-template-placeholders
```

After creating a local ordinary-battle save state, edit
`build/c2/battle-trace-oracles/local-fixtures.json`, replace the placeholder
`save_state_path`, and validate without `--allow-template-placeholders`.

Regenerate runner assets:

```powershell
python tools\build_c2_battle_trace_oracle_runner_assets.py
python tools\validate_c2_battle_trace_oracle_runner_assets.py
```

Dry-run a job against the local Mesen/ROM discovery path:

```powershell
python tools\run_c2_battle_trace_oracle_mesen.py --oracle-id c1_c2_target_action_staging --dry-run
```

Run a local battle fixture:

```powershell
python tools\run_c2_battle_trace_oracle_mesen.py --oracle-id c1_c2_target_action_staging --fixture-id ordinary_battle_pre_command --frame-limit 3600 --summarize-trace
```

Validate the ignored run summary:

```powershell
python tools\validate_c2_battle_trace_oracle_mesen_run_summary.py build\c2\battle-trace-oracles\c1_c2_target_action_staging\mesen-run-summary.json
python tools\summarize_c2_battle_trace_oracle_raw_trace.py --oracle-id c1_c2_target_action_staging
python tools\validate_c2_battle_trace_oracle_raw_trace_summary.py build\c2\battle-trace-oracles\c1_c2_target_action_staging\raw-trace-summary.json
```

Probe existing local Mesen save states without overwriting packet output paths:

```powershell
python tools\probe_c2_battle_trace_save_states.py --mesen F:\Mesen2\Mesen.exe
python tools\validate_c2_battle_trace_save_state_probes.py
python tools\probe_c2_battle_fixture_scout.py --mesen F:\Mesen2\Mesen.exe
python tools\validate_c2_battle_fixture_scout.py
```

Probe output stays under
`build/c2/battle-trace-oracles/save-state-probes/` and
`build/c2/battle-trace-oracles/fixture-scout/`. A probe that satisfies minimum
hits is only a fixture candidate; it still needs manual trace review and the
normal result builder/validator before it can affect source comments.

After manual review, assemble and validate a result:

```powershell
python tools\build_c2_battle_trace_oracle_mesen_capture_fields.py --oracle-id c2_8125_damage_abi_boundary
python tools\build_c2_battle_trace_oracle_result_from_evidence.py --oracle-id c2_8125_damage_abi_boundary --status ok --classification needs_followup --classification-rationale "<reviewed trace rationale>" --observed-address C2:8125 --observed-address C2:7EAF --captured-fields-json build\c2\battle-trace-oracles\c2_8125_damage_abi_boundary\captured-fields.json
python tools\validate_c2_battle_trace_oracle_result.py build\c2\battle-trace-oracles\c2_8125_damage_abi_boundary\result.json
python tools\collect_c2_battle_trace_oracle_results.py
python tools\validate_c2_battle_trace_oracle_results_summary.py
```

## Promotion Rule

Do not promote source names or comments from a Mesen run summary alone. The raw
trace has to be reviewed into a non-stub result with all packet capture fields,
then collected as trace-observed or proof-grade evidence.

## Hook Fallbacks

Do not use a ROM hook for the first fixture unless a manual local battle save
state proves impractical. A cold jump into `C2:4821` / `BATTLE_ROUTINE` is too
late in the setup path for ordinary-battle proof. If a hook lane becomes
necessary later, `C2:2F38` / `INIT_BATTLE_SCRIPTED` is the safer candidate
because it reads the battle-entry pointer table, stages `$9F8A/$9F8C`, sets
`$4DC2`, runs the swirl/setup path, and reaches the shared battle init route.
Do not use EF debug `SHOW BATTLE` as the ordinary fixture, because that path
enters `C2:4821` directly and can fall through the `$4DC2 == 0` debug/default
seed block instead of proving the overworld encounter initializer.

Useful anchors:

- `C0:D19B` / encounter prep: stages the encounter slot and battle id.
- `C0:D323` / enemy-list build: fills `$9F8A/$9F8C`.
- `C0:44DA` / encounter countdown tail: sets `$4DC2 = FFFF`.
- `C0:B731` / `INIT_BATTLE_OVERWORLD`: vanilla overworld battle entry when
  `$4DC2` is set.
- `C2:2F38` / `INIT_BATTLE_SCRIPTED`: scripted battle entry using the
  `D0:C60D` battle-entry pointer table.
- `C2:4821` / `BATTLE_ROUTINE`: battle runtime entry used by debug SHOW BATTLE,
  not a complete ordinary battle initializer.
- `C2:4830`: debug/default seed block to prove skipped for ordinary-entry
  provenance.
