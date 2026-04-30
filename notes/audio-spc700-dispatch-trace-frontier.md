# Audio SPC700 Dispatch Trace Frontier

Status: runtime trace hook present; current samples do not yet observe high-command dispatch.

## Summary

- trace records: `5`
- records with hits: `0`
- total hits: `0`
- total sequence reads: `29747`
- total high-byte sequence reads: `5542`
- total control-candidate sequence reads: `430`
- records with sequence FF reads: `2`
- long trace records: `1`
- max long trace instruction limit: `1000000`
- semantic status: `sequence_high_bytes_observed_but_dispatch_handler_pc_not_observed`

## Trace Contract

- field: `spc700_entry_execution_probe.high_command_dispatch_trace`
- sequence read field: `spc700_entry_execution_probe.sequence_read_trace`
- sequence read window: `{'start': '0x2000', 'end_exclusive': '0x6C00'}`
- dispatch PC: `0x12FD`
- table base: `0x16C7`
- FF target window: `{'start': '0x1A81', 'end_exclusive': '0x1ACB'}`
- mapped command rule: For high_command_dispatch_source hits, X is recorded as the table byte offset and even X values below 0x40 are mapped as 0xE0 + X/2.

## Records

| Job | Track | Limit | Executed | Final PC | Key-ons | Dispatch hits | Seq reads | High reads | Control reads | Control counts |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `ares-track-001-gas_station` | `GAS_STATION` | `1000000` | `1000000` | `0x0DB9` | `3` | `0` | `13073` | `2787` | `353` | `{'0xEF': 351, '0xFF': 2}` |
| `ares-track-002-naming_screen` | `NAMING_SCREEN` | `200000` | `200000` | `0x0565` | `5` | `0` | `7509` | `1165` | `34` | `{'0xEF': 34}` |
| `ares-track-046-onett` | `ONETT` | `200000` | `200000` | `0x0E28` | `4` | `0` | `3218` | `509` | `1` | `{'0xEF': 1}` |
| `ares-track-121-onett_intro` | `ONETT_INTRO` | `200000` | `200000` | `0x0703` | `9` | `0` | `3367` | `655` | `1` | `{'0xFF': 1}` |
| `ares-track-187-give_us_strength` | `GIVE_US_STRENGTH` | `200000` | `200000` | `0x0CF4` | `1` | `0` | `2580` | `426` | `41` | `{'0xEF': 40, '0xFE': 1}` |

## Findings

- The native ares audio harness now emits a bounded high-command dispatch trace block in each state capture.
- The native ares audio harness now also emits bounded sequence-region read traces for 0x2000..0x6BFF reads.
- Current sampled captures include live key-on events and thousands of sequence-region reads, including high-byte command-like values and control candidates.
- GAS_STATION and ONETT_INTRO both read 0xFF bytes from sequence/runtime RAM in the sampled windows, while GIVE_US_STRENGTH reads a 0xFE byte.
- Despite those sequence reads, current captures still record no hits at 0x12FD, no live 0x1F opcode hits, and no hits in the provisional FF target window, so the handler bridge is still missing.

## Next Work

- narrow sequence-read tracing to the actual bytecode fetch PC/state rather than broad 0x2000..0x6BFF reads
- run a longer or later-bound trace for one finite FF candidate such as ELEVATOR_DOWN once the all-track native job path accepts per-job instruction limits
- only promote FF semantics after a trace records the dispatch source, X-derived command, and post-dispatch PC/state mutation
