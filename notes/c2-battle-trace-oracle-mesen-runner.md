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

## Local Fixture Status

- `F:\Mesen\Mesen.exe` is the known local Mesen2 executable path used by prior
  testRunner work.
- `EarthBound (USA).sfc` is discoverable through `tools/rom_tools.py` in this
  checkout.
- Local save states exist under `F:\Mesen\SaveStates`, but no save state is
  currently documented as a battle fixture for the C2 first-pass oracle jobs.
- A boot-only smoke run with `c1_c2_target_action_staging` and a 10-frame limit
  launches Mesen and writes an ignored run summary/raw trace successfully. It
  records no C2 proof hits and should not be treated as behavior evidence.

The first useful fixture to create is an ordinary battle state just before
choosing a command. That should target `c1_c2_target_action_staging`, because it
only needs the C1 target/action staging path and C2 candidate export path.

## Commands

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
python tools\run_c2_battle_trace_oracle_mesen.py --oracle-id c1_c2_target_action_staging --state "<local-only battle save state>" --frame-limit 3600
```

Validate the ignored run summary:

```powershell
python tools\validate_c2_battle_trace_oracle_mesen_run_summary.py build\c2\battle-trace-oracles\c1_c2_target_action_staging\mesen-run-summary.json
```

After manual review, assemble and validate a result:

```powershell
python tools\build_c2_battle_trace_oracle_result_from_evidence.py --oracle-id c1_c2_target_action_staging --status ok --classification needs_followup --classification-rationale "<reviewed trace rationale>" --observed-address C1:ADB4 --captured-fields-json "<reviewed captured fields json>"
python tools\validate_c2_battle_trace_oracle_result.py build\c2\battle-trace-oracles\c1_c2_target_action_staging\result.json
python tools\collect_c2_battle_trace_oracle_results.py
python tools\validate_c2_battle_trace_oracle_results_summary.py
```

## Promotion Rule

Do not promote source names or comments from a Mesen run summary alone. The raw
trace has to be reviewed into a non-stub result with all packet capture fields,
then collected as trace-observed or proof-grade evidence.
