# C2 Battle Trace Oracle Results Summary

Status: no source or behavior promotion. Local results are collected
only when ignored `build/c2/battle-trace-oracles/` result files exist.

## Summary

- jobs: `10`
- result files found: `10`
- valid results: `10`
- trace-observed results: `0`
- proof-grade results: `0`
- stub results: `10`
- proof-capable results: `0`
- statuses: `{'unsupported': 10}`
- validation: `{'valid': 10}`
- classifications: `{'unresolved': 10}`
- remaining blockers: `{'not_first_trace_pass': 5, 'oracle_contract_unresolved': 10, 'runtime_trace_proof': 10}`
- source promotion allowed: `False`
- behavior change allowed: `False`

## Acceptance Policy

- Stub unsupported/unresolved results validate runner plumbing only and never count as trace-observed evidence.
- A result counts as trace-observed only when it validates, is non-stub, is status ok, has a non-empty trace, matches packet job/trace paths, includes every packet capture field, and classifies the contract as confirmed_contract, refined_contract, contradicted_plan, or needs_followup.
- A result counts as proof-grade only when it satisfies the trace-observed gate and classifies the contract as confirmed_contract, refined_contract, or contradicted_plan.
- Contradicted results require manual review before any source-facing promotion.
- This summary cannot directly promote source names, source comments, C-port helper contracts, or behavior changes.

## Results

| Oracle | Priority | First pass | Status | Valid | Stub | Proof capable | Classification | Remaining blockers | Result path |
| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- |
| `c1_c2_target_action_staging` | `1` | `True` | `unsupported` | `True` | `True` | `False` | `unresolved` | `['runtime_trace_proof', 'oracle_contract_unresolved']` | `build/c2/battle-trace-oracles/c1_c2_target_action_staging/result.json` |
| `c2_40a4_current_action_payload` | `1` | `True` | `unsupported` | `True` | `True` | `False` | `unresolved` | `['runtime_trace_proof', 'oracle_contract_unresolved']` | `build/c2/battle-trace-oracles/c2_40a4_current_action_payload/result.json` |
| `c2_724a_affliction_writer_matrix` | `1` | `True` | `unsupported` | `True` | `True` | `False` | `unresolved` | `['runtime_trace_proof', 'oracle_contract_unresolved']` | `build/c2/battle-trace-oracles/c2_724a_affliction_writer_matrix/result.json` |
| `c2_8125_damage_abi_boundary` | `1` | `True` | `unsupported` | `True` | `True` | `False` | `unresolved` | `['runtime_trace_proof', 'oracle_contract_unresolved']` | `build/c2/battle-trace-oracles/c2_8125_damage_abi_boundary/result.json` |
| `resource_amount_pair_magnet_vs_pp_loss` | `2` | `True` | `unsupported` | `True` | `True` | `False` | `unresolved` | `['runtime_trace_proof', 'oracle_contract_unresolved']` | `build/c2/battle-trace-oracles/resource_amount_pair_magnet_vs_pp_loss/result.json` |
| `battle_text_payload_join` | `2` | `False` | `unsupported` | `True` | `True` | `False` | `unresolved` | `['runtime_trace_proof', 'oracle_contract_unresolved', 'not_first_trace_pass']` | `build/c2/battle-trace-oracles/battle_text_payload_join/result.json` |
| `healing_ladder_gamma_omega` | `2` | `False` | `unsupported` | `True` | `True` | `False` | `unresolved` | `['runtime_trace_proof', 'oracle_contract_unresolved', 'not_first_trace_pass']` | `build/c2/battle-trace-oracles/healing_ladder_gamma_omega/result.json` |
| `hp_roller_collapse_boundary` | `2` | `False` | `unsupported` | `True` | `True` | `False` | `unresolved` | `['runtime_trace_proof', 'oracle_contract_unresolved', 'not_first_trace_pass']` | `build/c2/battle-trace-oracles/hp_roller_collapse_boundary/result.json` |
| `psi_flash_and_status_gate_family` | `2` | `False` | `unsupported` | `True` | `True` | `False` | `unresolved` | `['runtime_trace_proof', 'oracle_contract_unresolved', 'not_first_trace_pass']` | `build/c2/battle-trace-oracles/psi_flash_and_status_gate_family/result.json` |
| `numeric_stat_edge_behavior` | `3` | `False` | `unsupported` | `True` | `True` | `False` | `unresolved` | `['runtime_trace_proof', 'oracle_contract_unresolved', 'not_first_trace_pass']` | `build/c2/battle-trace-oracles/numeric_stat_edge_behavior/result.json` |

## Next Work

- replace stub results with a real emulator or trace harness for the five first-pass jobs
- review proof-grade results in the owning C2 subsystem notes before touching source comments
- keep non-first-pass oracle jobs queued until the first-pass contracts stop moving
