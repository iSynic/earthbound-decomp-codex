# Intro Logo Wait And Gas Station Helpers (`C0:EFE1-C0:F21E`)

This note covers the remaining unknown entry points around the reference-named intro/logo and gas-station sequences.

Reference corroboration:

- `refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank00.asm` places `C0:EFE1` between `intro/logo_screen_load.asm` and `intro/logo_screen.asm`, then places `C0:F1D2` and `C0:F21E` around `intro/gas_station_load.asm` and `intro/gas_station.asm`.
- `refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Routine_Macros_EB.asm` labels the neighboring named routines as logo and gas-station loaders and gives asset names for the named portions, including the War on Giygas screen used just before `C0:F1D2/F21E`.

## Working Names

- `C0:EFE1` = `WaitFramesWithIntroCancel`
- `C0:F1D2` = `RunIntroTimedPaletteFadeTail`
- `C0:F21E` = `RunGasStationIntroScreenLoop`
- `C4:A377` = `LoadGasStationIntroGraphicsAndTilemap`

## C0:EFE1 Wait Helper

`C0:EFE1` is a counted frame wait with early cancel. It takes a count in `A`, stores it in local `$0E`, and then loops:

- If `$006D` is nonzero, it returns `1`.
- Otherwise it calls `C0:8756`, decrements the count, and continues.
- If the count expires, it returns `0`.

The nearby logo-screen routine calls it with values like `#$00B4` and `#$0078`, using the return value to branch out early when `$006D` indicates input/abort.

## C0:F1D2 Timed Fade/Palette Tail

`C0:F1D2` takes a value in `A`, preserves it in `Y`, stages a pointer at `$7E:0200`, calls `C4:954C` with `A=#$0064`, then calls `C4:96E7` with `X=FFFF` and `A` restored from the original argument. The named gas-station/War-on-Giygas flow calls it near the end of a wait loop, so this is best treated as a timed palette/fade tail helper until `C4:954C/C4:96E7` are fully named locally.

## C0:F21E Gas-Station Screen Loop

`C0:F21E` is the long gas-station/intro screen loop. It:

- Waits up to `#$00EC` frames, each frame checking `$006D`, calling `C2:DB3F`, then `C0:8756`.
- If `$006D` becomes nonzero, returns `1` immediately.
- Otherwise enters a longer loop up to `#$01E0` iterations. Each iteration copies a `$20` byte strip involving `$4476` and the current `$0240` staging pointer through `C0:8ED2`, calls `C4:26ED`, clears `$0030`, calls `C2:DB14`, repeats the `$20` byte copy, calls `C2:DB3F`, writes `$0030=18`, and ticks `C0:8756`.
- After the strip loop, calls `C4:9740`, clears color-math registers through `$2130/$2131`, sets `$001A=1` and `$001B=0`, waits `#$0078` frames through `C0:EFE1`, and exits early with `1` if canceled.
- On normal completion, plays cue `#$00AE` through `C4:FBBD`, creates or starts a timed task through `C0:92F5`, pumps `C0:9466/C0:8756` until the task slot at `$0A62 + task*2` becomes `FFFF`, then calls `C0:F1D2(#$014A)` and returns the local result word, normally zero.

This routine is best understood as the interactive/waiting part of the gas-station intro sequence: it animates/copies strips, handles early input through `$006D`, coordinates palette/color math, starts one timed effect, and then fades/tails out through `C0:F1D2`.

## C4:A377 Gas-Station Asset Loader

The gas-station load block at `C0:F0D2` calls `C4:A377` after the first intro asset decompressions and VRAM transfers, then immediately mirrors the CGRAM shadow through `C4:96F9` and initializes palette interpolation through `C4:96E7`.

`C4:A377` uses the compact selector bytes at `CA:F038` to index the legacy GFX pointer table at `CA:D7A1` and tilemap pointer table at `CA:D93D`, decompresses the selected assets to `$7F:0000`, queues the GFX to VRAM `$6000`, rewrites tilemap attribute bits, and queues the tilemap to VRAM `$7C00`.

So this is now best treated as the C4-side gas-station intro graphics/tilemap loader, not as part of the later battle overlay interpreter that starts around `C4:A67E`.
