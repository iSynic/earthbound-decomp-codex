# Audio Sequence Walk Frontier

Status: provisional N-SPC-family static walk built; 0x00 terminator candidates and EF edges are explicit, but exact duration promotion still needs EarthBound-local proof.

## Summary

- sequence packs walked: `119`
- walk statuses: `{'blocked': 160, 'falls_through_segment': 1835, 'terminates': 782}`
- EF call edges: `1092`
- EF edges outside block: `15` (`0.0137`)
- terminator candidates reached: `922`
- terminator counts by command: `{'0x00': 922}`
- blocker counts: `{'0xFF': 150}`
- priority packs with full walk samples: `29`
- zero-review priority packs: `10`
- semantic status: `provisional_n_spc_static_walk_zero_terminators_unpromoted`

## Commands Seen By Walker

| Command | Count | Current hypothesis |
| --- | ---: | --- |
| `0x00` | 922 | phrase_termination_or_end_of_subroutine_candidate |
| `0xE0` | 1466 | set_instrument_candidate |
| `0xE1` | 3206 | set_pan_candidate |
| `0xE2` | 542 | pan_fade_candidate |
| `0xE3` | 664 | vibrato_on_candidate |
| `0xE4` | 142 | vibrato_off_candidate |
| `0xE5` | 166 | master_volume_or_channel_state_candidate |
| `0xE6` | 52 | volume_or_master_fade_candidate |
| `0xE7` | 249 | tempo_or_tuning_candidate |
| `0xE8` | 15 | tempo_fade_candidate |
| `0xE9` | 16 | global_transpose_candidate |
| `0xEA` | 42 | channel_transpose_candidate |
| `0xEB` | 70 | tremolo_or_modulation_on_candidate |
| `0xEC` | 18 | tremolo_or_modulation_off_candidate |
| `0xED` | 1640 | set_channel_volume_candidate |
| `0xEE` | 359 | channel_volume_fade_candidate |
| `0xEF` | 1092 | subroutine_call_candidate |
| `0xF0` | 17 | modulation_fade_candidate |
| `0xF1` | 356 | pitch_envelope_or_portamento_candidate |
| `0xF2` | 270 | pitch_envelope_off_candidate |
| `0xF3` | 212 | tuning_or_detune_candidate |
| `0xF4` | 797 | driver_toggle_or_extended_control_candidate |
| `0xF5` | 191 | echo_or_voice_param_candidate |
| `0xF6` | 12 | echo_off_or_effect_disable_candidate |
| `0xF7` | 161 | echo_or_effect_setup_candidate |
| `0xF8` | 10 | echo_or_effect_fade_candidate |
| `0xF9` | 271 | pitch_slide_candidate |
| `0xFA` | 156 | earthbound_extended_command_candidate |
| `0xFB` | 9 | loop_start_or_control_candidate |
| `0xFC` | 16 | loop_end_or_control_candidate |
| `0xFD` | 7 | loop_or_jump_control_candidate |
| `0xFE` | 15 | jump_or_long_control_candidate |
| `0xFF` | 150 | end_or_sentinel_candidate |

## Priority Packs

| Pack | ROM range | Tracks | Walk statuses | EF edges | Terminators | Blockers |
| ---: | --- | ---: | --- | ---: | ---: | --- |
| `25` | `EC:E101..EC:EB51` | 8 | `{'falls_through_segment': 80, 'terminates': 32}` | 44 | 32 | `{}` |
| `133` | `EC:B38A..EC:BF28` | 4 | `{'blocked': 3, 'falls_through_segment': 28, 'terminates': 13}` | 18 | 16 | `{'0xFF': 3}` |
| `4` | `DF:EC46..DF:FFEE` | 3 | `{'blocked': 2, 'falls_through_segment': 31, 'terminates': 16}` | 44 | 18 | `{'0xFF': 2}` |
| `103` | `EE:52E6..EE:56DF` | 3 | `{'blocked': 3, 'falls_through_segment': 33, 'terminates': 14}` | 2 | 17 | `{'0xFF': 3}` |
| `132` | `ED:1406..ED:1DFF` | 3 | `{'blocked': 3, 'falls_through_segment': 43, 'terminates': 14}` | 18 | 17 | `{'0xFF': 3}` |
| `83` | `EE:6D36..EE:6FDD` | 3 | `{'blocked': 3, 'falls_through_segment': 33, 'terminates': 11}` | 0 | 14 | `{'0xFF': 3}` |
| `79` | `DC:F8BF..DC:FF92` | 3 | `{'blocked': 2, 'falls_through_segment': 14, 'terminates': 8}` | 10 | 10 | `{'0xFF': 2}` |
| `94` | `CF:F2B5..CF:FF38` | 4 | `{'blocked': 4, 'falls_through_segment': 53, 'terminates': 16}` | 25 | 20 | `{'0xFF': 4}` |
| `14` | `ED:DAFD..ED:E0AE` | 3 | `{'blocked': 2, 'falls_through_segment': 20, 'terminates': 17}` | 8 | 19 | `{'0xFF': 2}` |
| `149` | `E9:F8C8..E9:FF65` | 3 | `{'blocked': 3, 'falls_through_segment': 40, 'terminates': 13}` | 20 | 16 | `{'0xFF': 3}` |
| `19` | `ED:CF55..ED:D539` | 2 | `{'blocked': 2, 'falls_through_segment': 26, 'terminates': 13}` | 15 | 15 | `{'0xFF': 2}` |
| `38` | `ED:6409..ED:6C06` | 2 | `{'blocked': 2, 'falls_through_segment': 17, 'terminates': 12}` | 16 | 14 | `{'0xFF': 2}` |
| `87` | `ED:0A07..ED:1406` | 2 | `{'blocked': 2, 'falls_through_segment': 24, 'terminates': 11}` | 17 | 13 | `{'0xFF': 2}` |
| `28` | `ED:B753..ED:BD60` | 2 | `{'blocked': 2, 'falls_through_segment': 23, 'terminates': 10}` | 10 | 12 | `{'0xFF': 2}` |
| `150` | `ED:53DF..ED:5C01` | 2 | `{'blocked': 2, 'falls_through_segment': 26, 'terminates': 10}` | 10 | 12 | `{'0xFF': 2}` |
| `162` | `ED:A4D7..ED:AB12` | 2 | `{'blocked': 2, 'falls_through_segment': 21, 'terminates': 9}` | 9 | 11 | `{'0xFF': 2}` |
| `55` | `EC:CAA1..EC:D5D8` | 2 | `{'blocked': 3, 'falls_through_segment': 31, 'terminates': 8}` | 15 | 10 | `{'0xFF': 3}` |
| `97` | `EC:BF28..EC:CAA1` | 2 | `{'blocked': 3, 'falls_through_segment': 33, 'terminates': 8}` | 25 | 10 | `{'0xFF': 2}` |
| `77` | `ED:C96E..ED:CF55` | 2 | `{'blocked': 2, 'falls_through_segment': 28, 'terminates': 7}` | 0 | 9 | `{'0xFF': 2}` |
| `23` | `EE:3E9C..EE:42BB` | 2 | `{'blocked': 2, 'falls_through_segment': 30, 'terminates': 6}` | 16 | 8 | `{'0xFF': 2}` |
| `136` | `EE:0000..EE:0554` | 2 | `{'falls_through_segment': 1, 'terminates': 5}` | 0 | 5 | `{}` |
| `1` | `E6:0000..E6:45D8` | 2 | `{'falls_through_segment': 7, 'terminates': 2}` | 9 | 2 | `{}` |
| `148` | `EE:3A7D..EE:3E9C` | 1 | `{'falls_through_segment': 18, 'terminates': 5}` | 12 | 5 | `{}` |
| `107` | `EC:4592..EC:6700` | 1 | `{'blocked': 1, 'falls_through_segment': 15, 'terminates': 4}` | 3 | 4 | `{}` |
| `154` | `EB:E9E4..EB:FE22` | 1 | `{'falls_through_segment': 19, 'terminates': 4}` | 6 | 4 | `{}` |
| `160` | `EE:4ADF..EE:4EEA` | 1 | `{'falls_through_segment': 10, 'terminates': 4}` | 20 | 4 | `{}` |
| `18` | `E2:FC88..E2:FFFD` | 1 | `{'terminates': 3}` | 0 | 3 | `{}` |
| `163` | `EE:0A8B..EE:0FB2` | 1 | `{'falls_through_segment': 7, 'terminates': 2}` | 4 | 2 | `{}` |
| `96` | `CF:FF38..CF:FFF9` | 1 | `{'terminates': 1}` | 0 | 1 | `{}` |

## Findings

- EF call edges are now represented as explicit same-block target edges in a static walk frontier.
- A small number of EF-like bytes are tracked as out-of-block under the provisional width table, which marks operand-width or data/noise uncertainty rather than promoted call semantics.
- N-SPC-family 0x00 candidates are now recorded as phrase termination/end-of-subroutine evidence, but exact end-vs-return meaning still needs EarthBound-local proof.
- FD and FE are N-SPC fast-forward toggle candidates; timing effect is not promoted from driver/runtime evidence yet.
- FF is not treated as a terminator under the N-SPC hypothesis; stock N-SPC marks it invalid unless EarthBound proves a variant-specific effect.
- The walker records offsets, hashes, counts, and edge metadata only; it does not embed ROM-derived sequence payload byte strings.

## Next Work

- trace or disassemble 0x00 phrase/VCMD termination and EF return handling
- tie FD/FE/FF behavior to the SPC700 driver dispatch path
- turn EF call edges into a checked sequence subroutine stack model
- use walker status to narrow exact-duration work to packs without unpromoted blockers first
