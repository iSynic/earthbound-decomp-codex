# Event 353 Message Tile Builders `C4:810E..8A6D`

This cluster is a small event-facing visual/text tile builder. The two public event-call routines are corroborated by `ebsrc-main`:

- event script `353` calls `C4:880C`, then repeatedly pauses and calls `C4:8A6D` until the stepper returns false.
- event script `670` separately calls `C4:8B2C` after writing `PSI_TELEPORT_DESTINATION = 0x000E`.

The `C4:810E..8A6D` family is not ordinary text rendering. It builds a custom tile block in `$7F` work RAM, queues it through the C3 visual tile transfer helper, and uses event script polling to animate or reveal the result.

## Tile expansion helper

`C4:810E` is the low-level tile-cell expander used only by `C4:880C` locally.

The caller supplies:

- A: cell/tile index
- caller direct-page `$0E/$10`: output pointer

The routine derives a `$7F:0000` source offset from the tile index, reads paired bytes from source rows, extracts two-bit values through shift helper `C0:9251`, writes word entries to the caller's output pointer, and returns the advanced output pointer through the caller-visible direct-page locations.

It is safest to treat this as a `$7F` tile-cell/nibble-row expansion helper, not as a general font routine.

## Glyph/table renderer

`C4:827B` draws one encoded byte into the `$3492` tile buffer family.

It:

- normalizes caller X with `(X - 0x50) & 0x7F`
- uses a 12-byte record table rooted at `C3:F054`
- resolves glyph source pointers and width/advance data from that table
- adds `$5E6D` as a small variant offset
- calls `C4:4B3A` to merge spans into the `$3492` buffer
- advances the local `$9E23/$9E25` cursor family used by this custom renderer

`C4:838A` is the one local orchestrator for `C4:827B`.

It:

- clears a 0x400-byte buffer at `$3492` with `#$FF`
- clears `$9E23/$9E25`
- reads a byte/string source at `$99CE`
- clamps one string-length/count to at most `5`
- renders fixed byte tables at `C4:8037` and `C4:803B`
- renders bytes from `$99CE`
- fills/pads remaining rows in `$3492`
- converts the accumulated row count into `$9E23`
- returns the amount needed by the event-353 tile block initializer

The fixed data at `C4:8037` is byte/text-like input to this custom renderer. I am leaving the player-facing string identity open until the encoding table is reconciled.

## Event 353 init and step

`C4:880C` is the event-353 initializer.

It:

- calls `C4:838A(0)` to build the custom `$3492` tile buffer
- clears a `$7F:4000` tile work block
- calls `C4:810E` repeatedly to expand selected tile cells into that block
- reads `$99CE` length/count again and appends additional expanded cells
- builds a `$7F:1000` stream from the `$7F:4000` tile block
- writes a small header at `$7F:0000` (`08 1E`)
- stores the current-slot limit in `$0E5E[current]`

`C4:8A6D` is the event-353 stepper.

It:

- chooses a source row from `$7F:1000` or `$7F:4000` based on `$0E9A[current]`
- copies an 8-by-0x1E word window into `$7F:0002`
- queues the tile block through `C3:F705` with source `$7F:0000`, `X = #$024C`, and `A = #$0328`
- increments `$0E9A[current]`
- returns `1` once `$0E9A[current]` reaches `$0E5E[current]`, otherwise `0`

This matches the event script pattern exactly: initialize once, then poll the stepper once per short pause until done.

## Teleport event helper

`C4:8B2C` is not part of event 353. It is called by event script `670` immediately after:

- `EVENT_WRITE_WORD_WRAM .LOWORD(PSI_TELEPORT_DESTINATION), $000E`

The routine itself only writes:

- `$9F41 = 5`
- `$987F = 2`

The local name therefore keeps the event-side staging role without claiming that the routine writes the destination id itself.

## Working Names

- `C4:810E` = `ExpandEvent353TileCellTo7fRows`
- `C4:827B` = `DrawEvent353EncodedGlyphTo3492`
- `C4:838A` = `BuildEvent353MessageTileBuffer`
- `C4:880C` = `InitEvent353MessageTileReveal`
- `C4:8A6D` = `StepEvent353MessageTileReveal`
- `C4:8B2C` = `SetTeleportEvent670LandingMode`

## Confidence boundaries

### Locally proved

- `C4:880C` and `C4:8A6D` are paired by event script `353`.
- `C4:8A6D` returns the loop-completion flag used by the script.
- `C4:838A` is called only by `C4:880C` locally.
- `C4:827B` is called by `C4:838A` and consumes byte/table entries to draw into `$3492`.
- `C4:810E` is called only by `C4:880C` locally and expands tile-cell rows into `$7F` output.
- `C4:8B2C` belongs to event script `670`, not event script `353`.

### Still open

- exact decoded player-facing text for the byte tables at `C4:8037 / C4:803B`
- exact visual name of event `353`
- exact final meaning of `$9F41 = 5`, beyond its existing landing-mode role in nearby transition notes
