# Bank E1 Source Scaffold Handoff

## Status

Bank `E1` is byte-complete for the current source-scaffold phase.

- durable scaffold: `src/e1/bank_e1_helpers_asar.asm`
- manifest: `build/e1-build-candidate-ranges.json`
- protected bytes: `65536 / 65536`
- residual bytes: `0`
- modules: `52`
- source bytes: `0`
- preserved data-gap bytes: `65536`
- byte-equivalence: `OK`, `0` mismatches

E1 is protected as exact flyover/font/intro/title/ending/town-map/audio corridors, including inferred missing pre-title and ending payload spans.

## Regenerate And Validate

Use these commands from the repository root:

```powershell
python tools\promote_asset_bank_to_source_scaffold.py E1
python tools\build_source_bank_scaffold.py --bank E1
python tools\validate_source_bank_byte_equivalence.py --bank E1 --module all --combined --scaffold src\e1\bank_e1_helpers_asar.asm --strict
python tools\build_source_bank_candidate_ranges_doc.py --bank E1
python tools\build_source_bank_residual_map.py --bank E1
```

Expected validation:

- `E1 byte-equivalence: OK, 52 module(s), 0 mismatch(es).`
- `notes/e1-source-residual-map.md` reports `0` residual bytes and `0` residual ranges.

## Remaining Semantic Work

- resolve exact split among E1AE7C.bin.lzhal, E1AE83.bin.lzhal, and E1AEFD.bin.lzhal
- resolve missing metadata for E1D6E1.gfx.lzhal if asset-level extraction needs a named source file
- promote photographer, flyover, town-map icon placement, and unknown table spans into typed contracts
- optional render fixtures for intro/title/ending/town-map assets
