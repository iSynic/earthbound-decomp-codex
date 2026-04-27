# Asset Pipeline Plan

This project should keep source control focused on documentation, source scaffolds, manifests, and tools. Copyrighted game payloads should be generated locally from a user-supplied EarthBound ROM and stay under ignored output directories such as `build/assets/`.

## Goals

- Preserve enough ROM provenance that every generated asset can be traced back to a byte range, table, decompressor, or source include.
- Give future ports stable semantic asset IDs instead of forcing engine code to depend on SNES bank addresses.
- Support a legal installer/build flow: the end user supplies the base ROM, the project extracts or decodes assets locally, and no ROM-derived binary payloads are committed.
- Let reference checkouts under `refs/` accelerate naming and format decisions without making them part of the distributable project.
- Keep raw extraction available even before each format decoder is mature, so manifests can land early and decoded outputs can improve over time.

## Contract Layers

1. **ROM recipe layer**: records the source ROM span, table source, expected SHA-1, and any required decoder.
2. **Portable asset layer**: emits local files such as raw `.bin`, preview `.png`, decoded maps, BRR/audio intermediates, text JSON, or engine-ready bundles.
3. **Semantic ID layer**: exposes stable IDs like `asset.debug.cursor_graphics`, `table.map.tileset_pointers`, or `SPRITE_GROUP_NESS_BICYCLE` to tools and eventual ports.
4. **Validation layer**: checks the supplied ROM identity, byte counts, range hashes, and generated output hashes.

Ports should consume the semantic IDs and generated output paths, not hard-code `C0`-style bank ranges except in compatibility shims.

## Repository Policy

- Track manifests, extraction tools, decoder tools, docs, and small generated reports only when they are not ROM-derived payloads.
- Do not track extracted graphics, audio, text dumps, map data, or binary slices from the retail ROM.
- Keep `refs/` ignored. Use it as corroborating evidence for names, formats, and expected asset families.
- Prefer deterministic extraction. The same ROM plus the same manifest should produce the same local outputs and hashes.

## Manifest Shape

Manifests live under `asset-manifests/` and use JSON first, so the tooling needs no third-party YAML dependency. Each asset entry should include:

- `id`: stable engine-facing identifier.
- `title`: human-facing short label.
- `source`: ROM range, expected byte count, expected SHA-1, and evidence links.
- `outputs`: one or more generated files, starting with raw extraction and adding decoded forms as decoders become trustworthy.
- `notes`: uncertainty, likely format, and relationships to source files or reference assets.

The first seed manifest is `asset-manifests/ef-debug-assets.json`, because bank EF already has two small named debug graphics payloads and a validated byte-equivalent scaffold.

## Decoder Roadmap

- **Done in the base pipeline**: raw ROM slices, LZHAL decompression, 2bpp/4bpp tile preview PNGs, SNES BGR555 palette JSON, palette swatch PNGs, first-pass battle-background and battle-sprite palette-aware tile previews, composed battle-background arrangement previews, size-aware composed battle sprite previews, default-palette overworld sprite previews, overworld sprite group payload/metadata contracts with enum aliases, ROM-extracted overworld sprite frame/slot pointer contracts with named low-bit renderer effects, generated overworld slot preview sheets, secondary visual descriptor contracts, prototype composed overworld preview sheets with optional priority-band overlays, extraction reports.
- **Next**: name or visualize the secondary descriptor trailing byte, add optional overworld palette variants, split palette tables, then continue into tilemaps, BRR/sample packs, text tables, and map sector data.
- **Later**: engine-ready asset bundles with IDs, dependency metadata, and loaders that can target native ports or ROM rebuilding.

## Tooling Path

- `tools/build_asset_extraction_manifest.py` converts the existing `asset-bank-xx.json` layout data into checked-in extraction manifests.
- `tools/extract_assets.py` consumes those manifests and writes local ROM-derived outputs under `build/assets/`.
- `tools/snes_palette.py` provides the shared SNES BGR555 palette decoder used by the extraction pipeline.
- `tools/build_overworld_sprite_group_manifest.py` consumes ignored refs and checked-in D1-D5 manifests to produce `notes/overworld-sprite-groups.json` without committing ROM-derived payload bytes.
- `tools/build_overworld_sprite_frame_contract.py` consumes the sprite group contract, the user-supplied ROM, and D1-D5 manifests to resolve EF sprite grouping pointer slots to concrete payload assets and named renderer flag effects for ports and editors.
- `tools/build_overworld_sprite_preview_sheets.py` consumes the frame contract and generated asset previews to write ignored overworld slot contact sheets under `build/overworld-sprite-preview-sheets/`.
- `tools/build_secondary_visual_descriptor_contract.py` consumes the user-supplied ROM to decode the C4 secondary visual descriptor pointer table, per-pass piece records, priority-band counts, and adjacent support table ranges.
- `tools/build_overworld_sprite_composed_previews.py` consumes the frame contract, secondary visual descriptor contract, and generated D1-D5 previews to write ignored prototype composed overworld sheets under `build/overworld-sprite-composed-previews/`.
- `tools/validate_asset_manifests.py` validates all checked-in manifests, checks duplicate asset IDs, and can run a full local extraction pass.
- Seed generated manifests should land in small, representative batches until the schema is settled, then the remaining asset banks can be generated mechanically.

Existing refs are useful for this phase:

- `refs/eb-decompile-4ef92` has extracted battle sprites, fonts, music, sprite groups, tilesets, town maps, and window graphics.
- `refs/earthbound-disasm-legacy/Earthbound Decomp/EB` has graphics, map data, ROM maps, compressed tilemaps, and font tables.
- `notes/bank-*-asset-data-map.md` already gives us bank-local asset boundaries to convert into manifests.

## Practical Port Path

An eventual port can ship an installer or first-run setup command that:

1. Locates or asks for the user's EarthBound ROM.
2. Verifies the ROM identity.
3. Runs the checked-in asset manifests through extraction and decoder tools.
4. Writes generated assets under a local cache or build directory.
5. Builds or runs the engine against generated local assets.

That keeps the port free to use native formats while preserving a ROM-rebuild path for ROM hacking work.
