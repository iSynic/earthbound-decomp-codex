# Python Tool Syntax Guide

This guide documents the command shapes used most often in this repository. It
is not a replacement for `--help`; it is a quick reference for the syntax we keep
using during bank work.

## Address Formats

Most tools accept SNES CPU addresses in one of these forms:

```text
C2:8D5A
C28D5A
0xC28D5A
```

Some tools also accept plain 16-bit WRAM or direct-page-style values:

```text
7440
0x99CE
$99CE
```

For bank work, prefer the `BANK:OFFSET` form in notes and commands. It is easier
to read and less error-prone.

## Common Global Options

Many tools support:

- `--rom PATH`: use a specific ROM instead of autodetecting it
- `--json` or `--json-out PATH`: emit machine-readable output
- `--markdown-out PATH`: emit a durable Markdown report
- `--limit N`: cap result count
- `--count N`: inspect a fixed number of records, chunks, or instructions

Run any tool with `--help` to see its exact arguments:

```powershell
python tools/find_xrefs.py --help
```

## ROM Verification

Verify the local ROM:

```powershell
python tools/verify_rom.py
```

Use an explicit path:

```powershell
python tools/verify_rom.py --rom "baserom/EarthBound (USA).sfc"
```

Machine-readable verification:

```powershell
python tools/verify_rom.py --json
```

## Code Inspection

Decode a short 65816 snippet:

```powershell
python tools/decode_snippet.py C1:244C --count 20 --show-state
```

Force register widths when starting in the middle of a routine:

```powershell
python tools/decode_snippet.py C2:7550 --count 16 --force-m16 --force-x16 --show-state
```

Trace direct-page-heavy code with known incoming state:

```powershell
python tools/trace_dp_window.py C2:7550 --count 16 --force-m16 --force-x16 --d 0x99CE --db 0x7E --show-state
```

Useful width flags:

- `--m8`: start with 8-bit accumulator
- `--x8`: start with 8-bit index registers
- `--force-m8` or `--force-m16`: lock accumulator width
- `--force-x8` or `--force-x16`: lock index width
- `--emulation`: start in emulation mode

## Cross-Reference Searches

Find direct calls, memory-style references, and raw pointer hits:

```powershell
python tools/find_xrefs.py C20ABC --limit 12
```

Force a scan mode:

```powershell
python tools/find_xrefs.py C1:8607 --kind code --limit 20
python tools/find_xrefs.py 0x99CE --kind memory --limit 20
```

Skip noisy raw pointer sections:

```powershell
python tools/find_xrefs.py C20ABC --no-raw
```

Find direct routine callers:

```powershell
python tools/find_direct_callers.py C2:D121
```

Search exact ROM bytes:

```powershell
python tools/find_rom_bytes.py --bytes "A9 00 85 0E"
```

## Table And Contract Inspection

Inspect a named data contract:

```powershell
python tools/inspect_table.py --contract ENEMY_CONFIGURATION_TABLE --index 0 --count 1 --field actions:w:0x46
```

Inspect a table manually by base address and stride:

```powershell
python tools/inspect_table.py D5:5000 --stride 39 --index 4 --count 3 --field type:b:25 --field params:d:31
```

Field syntax:

```text
name:kind:offset
name:kind:offset:size
```

Common field kinds:

- `b`: byte
- `w`: little-endian word
- `d`: 24-bit pointer or data value, depending on context

Inspect item records:

```powershell
python tools/inspect_item.py 0x11 --count 2
```

Inspect battle action entries by index:

```powershell
python tools/inspect_battle_action.py 78
```

Inspect action entries that point at a code address:

```powershell
python tools/inspect_battle_action.py C2:8D5A --limit 8
```

Look up WRAM and ROM contracts:

```powershell
python tools/lookup_wram_field.py 99DC 9FAC+1D
python tools/lookup_data_contract.py D5:9589+0x46 "BATTLERS_TABLE[3].afflictions" '$ADD4+0x61'
python tools/validate_data_contracts.py
```

## EarthBound Text And Script Tools

Decode text bytes from a CPU address:

```powershell
python tools/extract_ebtext.py C2:0998 --length 4 --count 2 --stride 4
```

Decode until a zero terminator:

```powershell
python tools/extract_ebtext.py C5:8000 --until-zero --max-length 128
```

Find parsed text commands:

```powershell
python tools/find_ebtext_command.py 1C 05 --limit 12
python tools/find_ebtext_command.py 1D --limit 12
```

Inspect command hits with surrounding decoded context:

```powershell
python tools/inspect_ebtext_hits.py 1D 24 --limit 2 --before 24 --after 56
```

Summarize a command family:

```powershell
python tools/summarize_ebtext_family.py 1C --max-subcommands 22 --limit 2
```

Decode C3-style event/actionscript payloads:

```powershell
python tools/decode_event_script.py C3:0295 C3:AB59
```

## Reference Lookups

Build the local reference index:

```powershell
python tools/build_ref_index.py --output build/ref-index.json
```

Look up reference context by address or symbol:

```powershell
python tools/lookup_ref_context.py C3:0188
python tools/lookup_ref_context.py DISPLAY_ANTI_PIRACY_SCREEN
```

Search reference symbols by address-shaped name:

```powershell
python tools/lookup_ref_symbol.py C4:B524 --limit 8
```

Generate a bank-specific reference frontier report:

```powershell
python tools/build_ref_bank_report.py C3 --output notes/bank-c3-reference-frontier.md --limit 160
```

## Working Names And Labels

Build a machine-readable working-name manifest:

```powershell
python tools/build_working_name_manifest.py --banks C0 C1 C2 --output build/working-names-c0-c2.json
```

Emit generated label formats from the manifest:

```powershell
python tools/emit_source_labels.py --manifest build/working-names-c0-c2.json --output-dir build/labels --banks C0 C1 C2
```

Promote working-name corridors into source scaffolds:

```powershell
python tools/promote_working_names_to_source_scaffold.py --bank C2 --working-names build/working-names-c0-c2.json --force
```

Promote one scaffolded byte corridor into decoded linear source:

```powershell
python tools/promote_linear_range_to_decoded_source.py --bank C0 --module c0_0085_install_landing_animated_graphics_strip --subsystem landing-display-decoded-source
```

## Source Scaffold Tools

Generate a source-bank scaffold:

```powershell
python tools/build_source_bank_scaffold.py --bank C2
```

Generate with explicit paths:

```powershell
python tools/build_source_bank_scaffold.py --bank C2 --ranges build/c2-build-candidate-ranges.json --output src/c2/bank_c2_helpers_asar.asm
```

Validate byte-equivalence:

```powershell
python tools/validate_source_bank_byte_equivalence.py --bank C2 --module all --combined --scaffold src/c2/bank_c2_helpers_asar.asm --strict
```

Generate source-bank planning reports:

```powershell
python tools/build_source_bank_candidate_ranges_doc.py --bank C2
python tools/build_source_bank_residual_map.py --bank C2
python tools/build_source_scaffold_status.py
```

## Promoters By Bank Shape

Text bank:

```powershell
python tools/promote_text_bank_to_source_scaffold.py C5
```

Asset bank:

```powershell
python tools/promote_asset_bank_to_source_scaffold.py CA
```

Table-split bank:

```powershell
python tools/promote_table_splits_to_source_scaffold.py CF
```

Mixed asset/table bank:

```powershell
python tools/promote_mixed_asset_table_bank_to_source_scaffold.py D5
```

Promote one data range into a source-bank manifest:

```powershell
python tools/promote_source_bank_data_range.py --bank C4 --source-path src/c4/battle_overlay_transition_data.asm --subsystem visual --start C4:A67E --end C4:AC57 --name battle_overlay_transition_data --title "Battle overlay transition data"
```

## Graphics And Palette Inspection

Inspect SNES palette words:

```powershell
python tools/inspect_snes_palette.py C4:3492 --count 8
```

Generate ROM-backed palette JSON and swatch PNG outputs from checked-in manifests:

```powershell
python tools/validate_asset_manifests.py --extract
```

The same extraction pass also emits first-pass palette-aware battle-background
tile-sheet previews and composed 32x32 battle-background arrangement previews
where matching same-numbered graphics/palette payloads line up mechanically.
Battle sprite graphics also get palette-aware previews for observed
enemy-table sprite/palette combinations, plus size-aware composed sprite
previews using the reference battle sprite pointer table.

Build ignored overworld sprite slot contact sheets from the resolved frame
contract and generated palette-00 tile previews:

```powershell
python tools/build_overworld_sprite_preview_sheets.py
```

Render one or two specific overworld sprite IDs:

```powershell
python tools/build_overworld_sprite_preview_sheets.py --group-id 1 --group-id 7
```

Build the C4 secondary visual descriptor contract used by the in-game
composition path:

```powershell
python tools/build_secondary_visual_descriptor_contract.py
```

Render SNES 4bpp data when a graphics payload boundary is known:

```powershell
python tools/render_snes_4bpp.py --help
```

## Rule Of Thumb

Use tools in this order when exploring a new seam:

1. Check reference context with `lookup_ref_context.py` and
   `lookup_ref_symbol.py`.
2. Find callers and data references with `find_xrefs.py` and
   `find_direct_callers.py`.
3. Decode a small window with `decode_snippet.py` or `trace_dp_window.py`.
4. Inspect related tables or contracts with `inspect_table.py`,
   `lookup_data_contract.py`, and specialized inspectors.
5. Write the note first, then promote names, ranges, or data contracts.
6. Regenerate the scaffold and rerun byte-equivalence validation.
