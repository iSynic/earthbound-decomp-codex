# Audio 0x00/EF Return Frontier

Status: 0x00 candidates are grouped by EF context; runtime proof is still required.

## Summary

- candidate packs: `10`
- sampled 0x00 walks: `35`
- sampled 0x00 walk classes: `{'end_vs_ef_return_ambiguous': 3, 'phrase_or_song_end_candidate_pending_runtime_proof': 32}`
- pack context classes: `{'needs_ef_return_stack_model': 3, 'zero_phrase_end_candidate_runtime_pending': 7}`
- runtime 0x00 reads: `5931`
- runtime 0x00 reader PCs: `10`
- sequence promotion allowed: `False`

## Packs

| Pack | Tracks | Export classes | 0x00 candidates | EF edges | Context | Sampled walk classes |
| ---: | --- | --- | ---: | ---: | --- | --- |
| `25` | `[32, 33, 34, 35, 36, 37, 38, 39]` | `{'finite_or_transition_review_candidate': 8}` | 32 | 44 | `needs_ef_return_stack_model` | `{'end_vs_ef_return_ambiguous': 1, 'phrase_or_song_end_candidate_pending_runtime_proof': 15}` |
| `136` | `[120, 173]` | `{'unknown_active_preview': 1, 'loop_or_held_candidate': 1}` | 5 | 0 | `zero_phrase_end_candidate_runtime_pending` | `{'phrase_or_song_end_candidate_pending_runtime_proof': 5}` |
| `1` | `[1, 174]` | `{'unknown_active_preview': 1, 'finite_or_transition_review_candidate': 1}` | 2 | 9 | `needs_ef_return_stack_model` | `{'end_vs_ef_return_ambiguous': 1}` |
| `148` | `[143]` | `{'unknown_active_preview': 1}` | 5 | 12 | `zero_phrase_end_candidate_runtime_pending` | `{'phrase_or_song_end_candidate_pending_runtime_proof': 2}` |
| `160` | `[171]` | `{'loop_or_held_candidate': 1}` | 4 | 20 | `needs_ef_return_stack_model` | `{'end_vs_ef_return_ambiguous': 1, 'phrase_or_song_end_candidate_pending_runtime_proof': 1}` |
| `154` | `[157]` | `{'unknown_active_preview': 1}` | 4 | 6 | `zero_phrase_end_candidate_runtime_pending` | `{'phrase_or_song_end_candidate_pending_runtime_proof': 1}` |
| `107` | `[94]` | `{'unknown_active_preview': 1}` | 4 | 3 | `zero_phrase_end_candidate_runtime_pending` | `{'phrase_or_song_end_candidate_pending_runtime_proof': 3}` |
| `18` | `[25]` | `{'unknown_active_preview': 1}` | 3 | 0 | `zero_phrase_end_candidate_runtime_pending` | `{'phrase_or_song_end_candidate_pending_runtime_proof': 3}` |
| `163` | `[175]` | `{'finite_or_transition_review_candidate': 1}` | 2 | 4 | `zero_phrase_end_candidate_runtime_pending` | `{'phrase_or_song_end_candidate_pending_runtime_proof': 1}` |
| `96` | `[85]` | `{'unknown_active_preview': 1}` | 1 | 0 | `zero_phrase_end_candidate_runtime_pending` | `{'phrase_or_song_end_candidate_pending_runtime_proof': 1}` |

## Promotion Policy

- Static 0x00 context can prioritize work, but cannot decide exact end-vs-return semantics alone.
- A 0x00 on a path with an EF call edge remains ambiguous until the EF return stack model is proven.
- A 0x00 on a path without an EF call edge is an end candidate, but still needs EarthBound runtime/disassembly proof before public exact export.
- No record in this frontier directly promotes sequence exact-duration exports.

## Findings

- The new frontier identifies which 0x00 candidates need an EF return stack model first.
- Runtime 0x00 reader evidence is currently taken from the dispatch/control-reader manifests; older traces may report zero reads until regenerated with the widened harness contract.
- Pack-level export promotion remains blocked even for phrase-end-looking candidates.

## Next Work

- regenerate targeted ares traces for the 0x00 review packs using the widened zero-control trace contract
- decode reader PCs that observe 0x00 and record end-vs-return state transitions
- promote only packs whose 0x00 end proof agrees with EF context and track policy
