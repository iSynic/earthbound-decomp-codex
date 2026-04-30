# Audio SPC700 FF Target Review

Status: FF target address reviewed; runtime effect still blocked pending live trace.

## Summary

- FF target: `0x1A81`
- next pointer-run target: `0x1ACB`
- target span bytes: `74`
- word references: `1`
- direct CALL/JMP references: `0`
- span note/rest-like bytes: `46`
- span high-command-like bytes: `7`
- span control-transfer markers: `0`
- first-512 control-transfer markers: `0`
- semantic status: `ff_target_address_identified_effect_blocked_by_data_like_span`

## Dispatch Context

- table base: `0x16C7`
- source indirect jump addresses: `['0x12FD']`
- mapping assumption: FF target uses the current E0..FF zero-based high-command table mapping from the dispatch frontier.

| Command | Target | Current hypothesis |
| --- | ---: | --- |
| `0xFD` | `0x19FB` | `loop_or_jump_control_candidate` |
| `0xFE` | `0x1A32` | `jump_or_long_control_candidate` |
| `0xFF` | `0x1A81` | `end_or_sentinel_candidate` |

## Target Profile

- span profile: `{'base_address': '0x1A81', 'byte_count': 74, 'zero_count': 4, 'high_command_like_count': 7, 'note_or_rest_like_count': 46, 'duration_or_argument_like_count': 19, 'control_transfer_opcode_counts': {}, 'top_bytes': [{'byte': '0xED', 'count': 7}, {'byte': '0x82', 'count': 4}, {'byte': '0x00', 'count': 4}, {'byte': '0x8C', 'count': 4}, {'byte': '0x93', 'count': 3}, {'byte': '0x90', 'count': 3}, {'byte': '0x8B', 'count': 3}, {'byte': '0x89', 'count': 3}, {'byte': '0x87', 'count': 3}, {'byte': '0x85', 'count': 3}, {'byte': '0x84', 'count': 3}, {'byte': '0x0E', 'count': 2}]}`
- first-512 profile: `{'base_address': '0x1A81', 'byte_count': 512, 'zero_count': 23, 'high_command_like_count': 75, 'note_or_rest_like_count': 259, 'duration_or_argument_like_count': 165, 'control_transfer_opcode_counts': {}, 'top_bytes': [{'byte': '0xED', 'count': 46}, {'byte': '0xE1', 'count': 24}, {'byte': '0x00', 'count': 23}, {'byte': '0xBB', 'count': 20}, {'byte': '0xB7', 'count': 19}, {'byte': '0xB0', 'count': 17}, {'byte': '0xC3', 'count': 15}, {'byte': '0xB4', 'count': 13}, {'byte': '0xC0', 'count': 13}, {'byte': '0xB9', 'count': 12}, {'byte': '0xBC', 'count': 12}, {'byte': '0x1E', 'count': 11}]}`
- word references: `['0x1705']`
- direct CALL/JMP references: `[]`

## Findings

- The provisional FF target is only referenced as a little-endian word at the dispatch table entry; no direct CALL/JMP immediate reference to that target was found in the driver payload.
- The span from the FF target to the next pointer-run target is dominated by note/rest-like and high-command-like byte values, which makes static promotion to executable end/return semantics unsafe.
- No RET, JMP, CALL, BRA, or conditional branch marker appears in the target-to-next-pointer span or the first 512 bytes starting at the FF target under this byte-level scan.
- This strengthens the next task definition: capture live execution around the 0x12FD indirect dispatch and prove whether the current table mapping is executed as code, data, or a second-level sequence target.
- The current dispatch trace frontier records sampled sequence-region reads of FF bytes, but no 0x12FD, live 0x1F, or 0x1A81-window hits, so this remains a fetch-to-handler bridge tracing problem.

## Next Work

- instrument the SPC700 probe to record PC hits around 0x12FD, the X index used by the 0x1F dispatch, and the post-dispatch PC for a track that reaches FF
- if post-dispatch PC reaches 0x1A81, disassemble/trace enough live instructions to find the state mutation that ends, returns, stops, or advances the channel
- if runtime never jumps to 0x1A81 for FF, revise the high-command table mapping before promoting any FF terminator candidates
