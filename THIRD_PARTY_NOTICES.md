# Third-Party Notices

This repository is an independent research scaffold. It does not vendor a ROM,
game assets, local reference checkouts, generated audio, or emulator source.

## EarthBound / Mother 2

EarthBound and Mother 2 are copyrighted works owned by their respective rights
holders. This project requires users to provide their own legally obtained US
headerless EarthBound ROM for validation or local asset/audio generation.

## Local Reference Material

The ignored `refs/` directory may contain local checkouts, extracted references,
or recovered source archives used during research. Those materials are not part
of this repository. Public notes should cite conclusions and provenance without
copying private/local dumps wholesale.

Known reference families used during research include:

- Yoshifanatic1's EarthBound disassembly work
- eb-decompile / EB source-style references
- Starmen / Tomato script dumps and recovered localization script material

These references are accelerators and corroboration sources, not vendored
dependencies.

## Audio And Emulator Tooling

The audio backend research uses external local checkouts for emulator/audio
rendering experiments:

- ares: accuracy-first SNES/APU reference and diagnostic harness target
- libgme / snes_spc: lightweight SPC playback/export renderer path
- bsnes/higan, Mesen 2, and Mednafen: optional reference-oracle candidates

See `notes/audio-dependency-policy.md` for the current dependency posture. In
short: keep GPL/reference tools optional and out-of-process unless the project
intentionally changes license posture; respect LGPL obligations for libgme if
shipping binaries; review ares bundled third-party notices before vendoring or
binary distribution.

## Generated Outputs

Generated SPC, WAV, PCM, extracted graphics, raw payloads, and build artifacts
are ROM-derived local outputs. They belong under ignored paths such as
`build/`, `asm/`, `dumps/`, or `refs/` and should not be committed.
