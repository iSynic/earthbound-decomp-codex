# Overworld Walking Stutter Patch Plan

See also [overworld-stutter-current-truth-state.md](/F:/Earthbound%20Decomp%20-%20Codex/notes/overworld-stutter-current-truth-state.md).

## Current status

This note preserves the earlier strip-first patch design that led to the safe dedupe work.

The healthiest current next experiment is now narrower and later in the companion family:

- prefer the watcher-side `C0:A750 -> A794` gate described in [overworld-a794-watcher-gate-safe-v4.md](/F:/Earthbound%20Decomp%20-%20Codex/notes/overworld-a794-watcher-gate-safe-v4.md)
- treat the timer-only `A6E3` gate as a safe but insufficient negative result
- treat the strip-first plan below as the historical first-pass roadmap, not the current primary recommendation

## Main theory

The stutter looks like a combined bandwidth and gating problem:

- visible overworld updates are funneled through the NMI VRAM transfer queue at `C0:8240`
- map and collision strips are refreshed incrementally during movement
- the engine uses staged movement and timer callbacks, so motion is not fully free-running when supporting work is still pending
- the engine appears conservative about exposing visible state before required strip updates are ready

So the best first patch is probably not a risky async redesign. It is to reduce the amount of work entering the VRAM queue.

## Concrete hook chain

### NMI-side sink

From [bank-c0-entry-notes.md](/F:/Earthbound%20Decomp%20-%20Codex/notes/bank-c0-entry-notes.md):

- `C0:8240` drains the WRAM `$0400` transfer queue during NMI
- each command is an 8-byte DMA/VRAM transfer descriptor

This is the final sink, but probably not the best first hook. It is too generic and touches all systems.

### Generic VRAM-copy API

From `refs/ebsrc-main/include/symbols/bank00.inc.asm` and the legacy disasm:

- `C0:8616` = strongest current fit for `TRANSFER_TO_VRAM`
- `C0:865F` = helper under the descriptor-list path
- `C0:86DE` = scratch or buffer allocator/helper repeatedly used by map-strip upload paths
- `PREPARE_VRAM_COPY` and related helpers sit adjacent in the same `86xx` cluster

The `COPY_TO_VRAM*` macros in `refs/ebsrc-main/include/macros.asm` all funnel into this layer.

This is a plausible second-stage hook if we want generic coalescing or dedupe later.

### Overworld loader surface from bank `00`

From `refs/ebsrc-main/src/bankconfig/US/bank00.asm`, the overworld loading sequence includes:

- `overworld/load_map_row.asm`
- `overworld/load_map_column.asm`
- `overworld/load_collision_row.asm`
- `overworld/load_collision_column.asm`
- `overworld/reload_map_at_position.asm`
- `overworld/load_map_at_position.asm`
- `overworld/refresh_map_at_position.asm`
- `overworld/reload_map.asm`
- `overworld/initialize_map.asm`

That tells us the intended subsystem structure even when the body files are not present in the checked-in `refs` tree.

## Strongest current address mapping

Using include order plus the legacy disasm call graph:

- `C0:0AC5` = strongest current fit for one map-strip generator
- `C0:0BDC` = strongest current fit for the sibling map-strip generator
- `C0:0CF3` = strongest current fit for one collision or companion-strip generator
- `C0:0D7E` = strongest current fit for the sibling collision or companion-strip generator
- `C0:0E16` = one row/column VRAM upload helper over freshly built strip data
- `C0:0FCB` = the sibling row/column VRAM upload helper
- `C0:1558` = incremental scroll or movement refresh controller that calls the strip generators and upload helpers
- `C0:1731` = broader map-position refresh controller that repeatedly calls `C0:122A` and `C0:1181`
- `C0:17EA` = broader map reload/refresh side that eventually routes through `C0:1558` and later full refresh helpers like `C0:13F6`

### Why this mapping is useful

The key practical result is:

- the map-strip generation stage and the visible VRAM upload stage are separate
- that gives us two patch layers

## Best first patch target

### Recommended v1 target

Patch the overworld strip upload path at `C0:0E16` and `C0:0FCB`.

Why this is the best first target:

- still overworld-specific enough to avoid destabilizing unrelated systems
- later than the raw map-data extraction stage, so we can compare the actual strip payload that would be uploaded
- earlier than the generic `TRANSFER_TO_VRAM` sink, so we avoid affecting battle, menus, and other VRAM users

### Recommended v1 behavior

Before enqueuing or issuing the strip upload:

1. compare the generated strip payload against the last uploaded payload for that same destination class
2. if identical, skip the upload entirely
3. otherwise continue normally and update the cache

This is effectively a same-strip dedupe patch.

## Why not hook the final NMI queue first

Hooking the generic `$0400` queue drain or `TRANSFER_TO_VRAM` first would be broader, but riskier:

- battle and menu systems also use the same VRAM-copy layer
- distinguishing harmless duplicates from intentional repeated uploads would be harder at that level
- queue-level dedupe is better as patch v2 once we have a safe overworld-specific v1

## Candidate cache design

A practical first cache can be small and local:

- one cached payload for the `0E16` path
- one cached payload for the `0FCB` path
- include destination selector metadata, not just bytes

Minimum comparison inputs:

- strip orientation or path id (`0E16` vs `0FCB`)
- destination VRAM base derived from the current path
- payload length
- payload bytes

If all match the previous upload, skip.

## Strong signs this can help

`C0:1558` performs repeated incremental edge updates while screen position converges. That is exactly the kind of path where redundant strip uploads can happen if the engine revisits the same boundary state or recomputes a strip that is already current.

We also have overworld loaded-state globals from `refs/ebsrc-main/include/symbols/globals.inc.asm` and `ram.asm`:

- `LOADED_MAP_TILESET`
- `LOADED_ROWS_X`, `LOADED_ROWS_Y`
- `LOADED_COLUMNS_X`, `LOADED_COLUMNS_Y`
- `SCREEN_LEFT_X`, `SCREEN_TOP_Y`
- `TILEMAP_UPDATE_*`

That makes an even earlier dedupe possible later, but the upload-layer dedupe is simpler and lower risk for patch v1.

## Patch roadmap

### Patch v1

- hook `C0:0E16` and `C0:0FCB`
- add per-path strip-payload cache
- skip exact duplicate uploads

Expected result:

- lower VRAM queue pressure during walking
- fewer visible hitches when repeatedly crossing strip boundaries or revisiting equivalent edge states

### Patch v2

- coalesce adjacent strip uploads at the `86xx` VRAM-copy layer when possible
- still restrict logic to overworld callers if feasible

### Patch v3

- add lightweight priority shedding for cosmetic overworld uploads when map-edge uploads are pending

### Patch v4, only if needed

- revisit movement gating and allow more overlap between motion and non-critical visual refresh

## Exact next implementation step

Before writing assembly, pin the call contracts for:

- `C0:0E16`
- `C0:0FCB`
- `C0:8616`
- `C0:86DE`

Then identify where each upload helper's generated payload lives in WRAM so the patch can compare bytes cheaply before enqueueing.

That is the cleanest point to turn this plan into an actual ROM patch.

## Refined loader mapping

The strongest current address split is now:

- `C0:0AC5` = vertical strip generator, strongest current fit for `LOAD_MAP_ROW`
- `C0:0BDC` = horizontal strip generator, strongest current fit for `LOAD_MAP_COLUMN`
- `C0:0CF3` = companion vertical strip generator, strongest current fit for `LOAD_COLLISION_ROW` or an equivalent companion strip builder
- `C0:0D7E` = companion horizontal strip generator, strongest current fit for `LOAD_COLLISION_COLUMN` or an equivalent companion strip builder

This mapping comes from the include order in `bank00.asm` plus the caller pattern in `C0:1558`:

- the vertical update side calls `C0:0AC5`, `C0:0CF3`, `C0:0E16`, and the later companions
- the horizontal update side calls `C0:0BDC`, `C0:0D7E`, `C0:0FCB`, and the later companions

So `0AC5/0BDC` look like the real strip-generation hooks, while `0E16/0FCB` look like the visible upload-side hooks.

## Refined upload-side contracts

### `C0:0E16`

Strongest current local read:

- called from the vertical movement refresh side
- allocates scratch through `C0:86DE` with size `#$0100`
- builds a larger scratch payload from the generated strip tables
- later feeds the generic `TRANSFER_TO_VRAM` path at `C0:8616`
- targets the same tilemap VRAM bands the rest of overworld map drawing uses, including `0x3800/0x5800` or `0x3C00/0x5C00` depending side

So `0E16` is the strongest current vertical strip upload helper.

### `C0:0FCB`

Strongest current local read:

- called from the horizontal movement refresh side
- allocates scratch through `C0:86DE` with size `#$0080`
- builds a smaller scratch payload from the generated strip tables
- later feeds the same `TRANSFER_TO_VRAM` path at `C0:8616`
- also targets the paired overworld tilemap VRAM bands

So `0FCB` is the strongest current horizontal strip upload helper.

## Revised patch recommendation

A cleaner first patch split is now:

### Option A, safest and most focused

Hook `C0:0E16` and `C0:0FCB` after their scratch payloads are built but before their final `JSL C08616` calls.

What to compare:

- orientation: vertical vs horizontal path
- destination VRAM base
- final staged payload bytes

If identical to the last uploaded payload for that path and destination class, skip the `JSL C08616` calls.

### Option B, slightly earlier and slightly trickier

Hook `C0:0AC5` and `C0:0BDC` instead, compare generated strip metadata before the upload helpers even run, and bail out earlier.

This could save more CPU work, but it is riskier because the later helper layers may still have side effects we do not want to skip blindly.

So Option A is still the recommended v1 patch.

## Immediate implementation sketch

1. Let `0E16` or `0FCB` build the candidate strip payload normally.
2. Compute a small checksum or direct byte compare against the cached last payload for that path.
3. If equal, return early instead of issuing the final `C08616` transfers.
4. If different, copy the payload into the cache and continue with the original upload calls.

The simplest cache design is two caches:

- one for the vertical `0E16` path
- one for the horizontal `0FCB` path

This is intentionally conservative. It avoids trying to reason about all generic VRAM queue traffic at once.

## Refined v1 patch architecture

The cleaner v1 patch is narrower than the earlier whole-helper hook idea.

Instead of hijacking all of `C0:0E16` and `C0:0FCB`, patch only the eight overworld-specific `JSL C08616` callsites inside them:

- vertical path in `C0:0E16`
  - `C0:0F40`
  - `C0:0F6C`
  - `C0:0F99`
  - `C0:0FC5`
- horizontal path in `C0:0FCB`
  - `C0:10FA`
  - `C0:1122`
  - `C0:1153`
  - `C0:117B`

That is a better first patch because:

- it only touches overworld strip uploads
- each hook is a same-size `JSL` replacement, so the ROM surgery is simple
- the wrapper sees the final upload contract directly
- it avoids skipping the map-strip builders themselves, which may have side effects we still do not want to bypass

## Wrapper contract

At each of those callsites, the wrapper inherits the same live inputs that `C08616` expects:

- `A` = transfer mode byte
  - vertical helper uses `#$00`
  - horizontal helper uses `#$1B`
- `X` = transfer size, currently `#$0040`
- `Y` = VRAM destination
  - `#$3800`, `#$3C00`, `#$5800`, or `#$5C00`
- direct-page locals `$0E/$10` hold the source pointer pair used by the upload helper

So the wrapper can compare the exact final 64-byte tilemap strip that would be uploaded, then either:

- return early if it is an exact duplicate of the last upload to that destination class, or
- call through to the real `C08616` if it is new

## Runtime cache placement

The small scattered `;unused` WRAM holes in bank `7E` are too small for a robust cache.

But the checked-in RAM map leaves a large unallocated tail in the `RAM2` region:

- `RAM2` starts at `7E:8000`
- declared content ends after `TILE_COLLISION_BUFFER`
- the declared total is `0x14600` bytes, ending around `7F:C600`
- that leaves roughly `0x3A00` bytes of unallocated WRAM tail in `7F:C600..7F:FFFF`

So the safest current patch-private cache is the high tail of that region, for example:

- cache block at `7F:F000`
- total budget about `0x0140` bytes for v1

A practical four-slot layout is:

- slot 0 = VRAM `3800`
- slot 1 = VRAM `3C00`
- slot 2 = VRAM `5800`
- slot 3 = VRAM `5C00`

Per-slot data:

- valid flag
- last transfer mode byte
- last `LOADED_MAP_TILESET`
- last VRAM destination
- last size
- last 64 payload bytes

That is enough to dedupe exact repeated strip uploads while keeping the logic simple.

## Required invalidation

The real correctness risk is stale cache after a full map refresh or any path that rebuilds VRAM contents from scratch.

So v1 should not rely only on payload comparison. It should also clear the cache when the broader map-refresh side runs.

Strongest current invalidation candidates:

- `C0:13F6` full map refresh side
- `C0:17EA` broader map reload or refresh side

The nicest current fixed-width hook is inside `C0:13F6`:

- `C0:1404` is already a `JSL C02194`
- that can become `JSL Overworld_ClearDedupeCache_And_C02194`
- the wrapper clears the patch cache, calls the original `C02194`, then returns

That gives the patch an explicit epoch reset without needing a messy entry-trampoline on `13F6` itself.

As a second safety net, the upload wrapper should also invalidate a slot if `LOADED_MAP_TILESET` differs from the cached tileset.

## Current recommended v1 patch

1. Replace the eight overworld-only `JSL C08616` callsites with `JSL Overworld_DedupeTransfer`.
2. Store per-destination cache records in the unallocated `7F:F000+` tail.
3. Add one invalidation hook on the full refresh side, strongest current candidate `C0:1404`.
4. Keep all other movement, map-strip generation, and NMI queue behavior unchanged.

This is now a safer and more practical v1 than the earlier whole-helper interception idea.

## Implementation note

For patching work specifically, an Asar-style standalone patch is now the fastest path even though the broader `asm/` workspace has not chosen a permanent assembly syntax for decomp purposes.

The simplest patch packaging approach is:

- expand the ROM to 4 MB
- place new code in bank `F0`
- use direct fixed-address hooks in bank `C0`
- keep all patch-private runtime state in the `7F:F000+` WRAM tail

## Current implementation status

The standalone Asar draft now smoke-tests successfully against a disposable expanded ROM copy.

Patch file:

- [asm/overworld_stutter_dedupe_asar_sketch.asm](/F:/Earthbound%20Decomp%20-%20Codex/asm/overworld_stutter_dedupe_asar_sketch.asm)

Smoke test used:

```powershell
Copy-Item 'EarthBound (USA).sfc' 'build\EarthBound-overworld-stutter-test.sfc' -Force
$fs = [System.IO.File]::Open('build\EarthBound-overworld-stutter-test.sfc',[System.IO.FileMode]::Open,[System.IO.FileAccess]::ReadWrite)
$fs.SetLength(4MB)
$fs.Dispose()
& 'refs\earthbound-disasm-legacy\Earthbound Decomp\Global\asar.exe' 'asm\overworld_stutter_dedupe_asar_sketch.asm' 'build\EarthBound-overworld-stutter-test.sfc'
```

Current status means:

- the hook list is syntactically sound
- the callsite-based wrapper layout is assembler-plausible
- the cache layout and invalidation hook are encoded in a real patch draft

It does **not** yet prove gameplay correctness.

The next real validation step is emulator-side testing while walking in open overworld areas, towns, and map-edge transitions to confirm:

- no visual corruption from skipped duplicate uploads
- no stale-cache artifacts after full map refresh
- any actual reduction in visible hitching

## Conservative hardening after first boot test

Because the first gameplay test reported a possible intro-cutscene freeze, the patch draft is now narrowed further.

The upload wrapper now bails out to the original `C08616` path unless both of these are zero:

- `$436C`
- `$B4EF`

That keeps the dedupe logic off the helper's visibly special-case paths and makes v1 more strictly "ordinary overworld strip streaming only" instead of "every call that happens to hit these upload sites."

This should reduce regression risk during scripted or presentation-heavy scenes, even if it also trims some of the possible gain.

## Debug build counters

A debug patch variant now exists at:

- [asm/overworld_stutter_dedupe_debug_asar.asm](/F:/Earthbound%20Decomp%20-%20Codex/asm/overworld_stutter_dedupe_debug_asar.asm)

Smoke-tested debug ROM output:

- [EarthBound-overworld-stutter-debug.sfc](/F:/Earthbound%20Decomp%20-%20Codex/build/EarthBound-overworld-stutter-debug.sfc)

This debug variant adds lazy runtime initialization plus the following WRAM counters in `7F:F140+`:

- `7F:F140` = dedupe-eligible upload count
- `7F:F142` = dedupe skip count
- `7F:F144` = guard-fail count (`$436C != 0` or `$B4EF != 0`)
- `7F:F146` = bulk-transfer call count at `C0:09D1` / `C0:09EA`
- `7F:F148` = bulk-transfer large-call count (`X >= $1201`)
- `7F:F14A` = maximum observed bulk-transfer size
- `7F:F14C` = last observed bulk-transfer size

Interpretation:

- if `7F:F142` climbs while walking and the game stays stable, the strip-dedupe patch is doing real work
- if `7F:F146` / `7F:F148` climb during the scenes that still hitch, the `C0:85B7` bulk-transfer lane is likely the next patch target
- if `7F:F144` climbs during intro/cutscene tests, that confirms special scripted paths are hitting the same helpers and validates keeping the ordinary-only guard

## Early interpretation from emulator counter screenshot

The first observed counter snapshot is already useful:

- the first word at `7F:F140` climbed during scrolling, which confirms the dedupe wrapper is being reached during ordinary movement
- the later words around `7F:F146..7F:F14D` changed together during the intro's zone transition, which points toward the bulk-transfer lane becoming active during that scene

That is a good fit for the current two-bottleneck model:

- ordinary walking pressure -> small strip uploads through the `C0:0E16 / 0FCB -> C08616` path
- heavier scripted or zone-transition pressure -> larger synchronous transfers through `C0:85B7`

The immediate implication is:

- the strip-dedupe patch is probably addressing a real part of the problem
- but the intro transition behavior likely reflects the separate `C0:85B7` bulk-transfer lane more strongly than the strip-upload lane

This makes the current strategy look healthier:

1. keep the strip-dedupe patch narrow and stable
2. use the debug counters to decide whether the next patch should target `C0:85B7`
3. avoid merging both ideas into one aggressive patch until each lane is independently proven safe

## Debug v2 split counters

A second debug build now exists specifically for diagonal-scrolling diagnosis:

- [asm/overworld_stutter_dedupe_debug_v2_asar.asm](/F:/Earthbound%20Decomp%20-%20Codex/asm/overworld_stutter_dedupe_debug_v2_asar.asm)
- [EarthBound-overworld-stutter-debug-v2.sfc](/F:/Earthbound%20Decomp%20-%20Codex/build/EarthBound-overworld-stutter-debug-v2.sfc)

This keeps the same dedupe logic but splits the strip counters by path:

- `7F:F140` = vertical dedupe-eligible uploads
- `7F:F142` = vertical dedupe skips
- `7F:F144` = horizontal dedupe-eligible uploads
- `7F:F146` = horizontal dedupe skips
- `7F:F148` = guard-fail count
- `7F:F14A` = bulk-transfer call count at `C0:09D1` / `C0:09EA`
- `7F:F14C` = bulk-transfer large-call count (`X >= $1201`)
- `7F:F14E` = max observed bulk-transfer size
- `7F:F150` = last observed bulk-transfer size

What to look for during diagonal scrolling:

- if both `7F:F140` and `7F:F144` climb together while `7F:F142` / `7F:F146` stay relatively low, diagonal stutter is mostly real dual-axis work
- if one eligible counter climbs but the matching skip counter also climbs heavily, redundant work is still a big part of that lane
- if `7F:F14A` / `7F:F14C` jump during the roughest transitions, the next patch target should likely be the `C0:85B7` bulk-transfer path rather than more strip scheduling

## Confirmed v2 diagnosis after split-path testing

The split-path debug build confirmed the likely diagonal case:

- vertical eligible and horizontal eligible counters climb together during diagonal scrolling
- the matching skip counters remain near zero in limited testing

That strongly suggests diagonal inconsistency is **not** primarily redundant strip uploads.
It is mostly real dual-axis strip work happening in the same refresh window.

So the next patch should not be "more dedupe." It should be a scheduler.

## Recommended v2b scheduler shape

The shared incremental refresh controller at `C0:1558` already gives us the right separation:

- horizontal strip/update lane around `C0:15B0..165D`
  - includes `C0:0BDC`, `C0:0D7E`, `C0:0FCB`, `C0:25CF`, `C0:2B55`
- vertical strip/update lane around `C0:166B..171A`
  - includes `C0:0AC5`, `C0:0CF3`, `C0:0E16`, `C0:255C`, `C0:2A6B`

That means the clean v2b plan is:

1. Detect when both the horizontal and vertical deltas are still nonzero in the same controller pass.
2. Run only one axis's visible strip/upload lane this frame.
3. Record the deferred axis in patch-private WRAM.
4. Run the deferred axis on the next pass or frame.
5. Alternate priority between axes when both are pending, so neither direction starves.

### Best current hook seam

The most promising control seam is the axis handoff boundary between:

- the horizontal completion check at `C0:165D..1668`
- the vertical-entry side at `C0:166B..171A`

That is where the controller currently decides whether horizontal still has work and then continues into the vertical-side loop.

A scheduler hook there can answer one clean question:

- if both axes still have work, do we continue into the other axis now, or defer it once?

That is much cleaner than trying to patch inside `0E16` / `0FCB` themselves.

## v2b runtime state

A tiny patch-private state block is enough:

- pending-axis bitfield
- last-served axis toggle
- optional one-frame cooldown or guard byte

The current best location remains the same `7F:F000+` patch-private WRAM tail.

## v2b safety rules

Keep the same conservative guards as v1:

- bypass when `$436C != 0`
- bypass when `$B4EF != 0`
- bypass on any non-ordinary special path we later identify

And keep the current dedupe patch active underneath the scheduler, because it is still helpful for ordinary one-axis motion.

## Scheduler debug prototype

A first diagonal-specific scheduler prototype now exists at:

- [asm/overworld_stutter_scheduler_debug_asar.asm](/F:/Earthbound%20Decomp%20-%20Codex/asm/overworld_stutter_scheduler_debug_asar.asm)
- [EarthBound-overworld-stutter-scheduler-debug.sfc](/F:/Earthbound%20Decomp%20-%20Codex/build/EarthBound-overworld-stutter-scheduler-debug.sfc)

It keeps the current safe strip-dedupe layer and adds two gate hooks:

- `C0:165D` = horizontal completion gate
- `C0:171A` = vertical completion gate

Current scheduler behavior:

- if only one axis is effectively pending, original behavior is preserved
- if both axes are pending in ordinary overworld mode, the patch picks one axis for the current pass and defers the other
- priority alternates using a patch-private toggle so diagonal scrolling does not keep favoring the same axis
- the same conservative guards remain in place: bypass when `$436C != 0` or `$B4EF != 0`

### Scheduler-specific counters

This build keeps the debug-v2 counters and adds scheduler counters at `7F:F160+`:

- `7F:F160` = dual-pending passes where horizontal was chosen first
- `7F:F162` = dual-pending passes where vertical was chosen first
- `7F:F164` = scheduler-forced early returns after a horizontal pass
- `7F:F166` = scheduler bypass count due to special-mode guards

### What a healthy test should look like

During diagonal walking, the best-case outcome is:

- `7F:F140` and `7F:F144` no longer climb in the same tightly coupled way every pass
- `7F:F160` and `7F:F162` both climb over time, showing the scheduler is alternating priority
- `7F:F164` climbs during diagonal movement, showing the patch is actually deferring the second axis instead of still doing both in one pass
- ordinary scripted paths keep working, and `7F:F166` may rise in special scenes where the scheduler is intentionally bypassed

If this build improves diagonal smoothness without visual corruption or hangs, the next step is a non-debug safe scheduler build with the same gating logic and without the counter instrumentation.

### Scheduler debug v2: pacing and queue pressure

A second scheduler debug build now exists at:

- [asm/overworld_stutter_scheduler_debug_v2_asar.asm](/F:/Earthbound%20Decomp%20-%20Codex/asm/overworld_stutter_scheduler_debug_v2_asar.asm)
- [EarthBound-overworld-stutter-scheduler-debug-v2.sfc](/F:/Earthbound%20Decomp%20-%20Codex/build/EarthBound-overworld-stutter-scheduler-debug-v2.sfc)

It keeps the scheduler counters and adds two new signals:

- NMI DMA queue pressure sampled right before `DMA_QUEUE_INDEX` is cleared at `C0:8350`
- scroll-controller commit activity sampled when the `C0:1558` incremental refresh path exits through `C0:1725`

Additional counters at `7F:F168+`:

- `7F:F168` = NMI frame count sampled at the queue-reset hook
- `7F:F16A` = last observed `DMA_QUEUE_INDEX` before reset
- `7F:F16C` = max observed `DMA_QUEUE_INDEX`
- `7F:F16E` = scroll-controller commit count
- `7F:F170` = last committed scroll X from `$12`
- `7F:F172` = last committed scroll Y from `$14`

This should help separate two remaining hypotheses:

- if microstutters line up with `7F:F16A` spikes, the remaining issue is broader DMA queue pressure rather than map-strip streaming specifically
- if microstutters happen while `7F:F16A` stays low but `7F:F16E` advances unevenly relative to visible motion, the remaining issue is more likely scroll or movement pacing logic than transfer bandwidth

### Scheduler debug v3: helper-level DMA attribution

A third scheduler debug build now exists at:

- [asm/overworld_stutter_scheduler_debug_v3_asar.asm](/F:/Earthbound%20Decomp%20-%20Codex/asm/overworld_stutter_scheduler_debug_v3_asar.asm)
- [EarthBound-overworld-stutter-scheduler-debug-v3.sfc](/F:/Earthbound%20Decomp%20-%20Codex/build/EarthBound-overworld-stutter-scheduler-debug-v3.sfc)

This build keeps the earlier scheduler, strip, and queue-pressure counters, and adds direct attribution for the four companion helper callsites inside the `C0:1558` incremental scroll controller:

- `C0:15F4` -> `C0:25CF`
- `C0:1606` -> `C0:2B55`
- `C0:16B2` -> `C0:255C`
- `C0:16C4` -> `C0:2A6B`

For each helper, the wrapper records:

- call count
- cumulative growth in `$99` across the call

Helper counters at `7F:F17C+`:

- `7F:F17C` = calls to `C0:25CF`
- `7F:F17E` = cumulative `$99` delta from `C0:25CF`
- `7F:F180` = calls to `C0:2B55`
- `7F:F182` = cumulative `$99` delta from `C0:2B55`
- `7F:F184` = calls to `C0:255C`
- `7F:F186` = cumulative `$99` delta from `C0:255C`
- `7F:F188` = calls to `C0:2A6B`
- `7F:F18A` = cumulative `$99` delta from `C0:2A6B`

Interpretation:

- if one helper family's delta counter climbs much faster during diagonal scrolling, that family is the best next patch target for queue-pressure reduction
- if all four stay relatively flat while `7F:F16A` still spikes, the remaining pressure is probably coming from another producer family outside these four callsites

### Scheduler debug v4: lane-level queue accounting

A safer replacement for the rejected helper-wrapper build now exists at:

- [asm/overworld_stutter_scheduler_debug_v4_asar.asm](/F:/Earthbound%20Decomp%20-%20Codex/asm/overworld_stutter_scheduler_debug_v4_asar.asm)
- [EarthBound-overworld-stutter-scheduler-debug-v4.sfc](/F:/Earthbound%20Decomp%20-%20Codex/build/EarthBound-overworld-stutter-scheduler-debug-v4.sfc)

This build does **not** wrap deep helper families.
Instead, it only uses the already-stable scheduler gate hooks at `C0:165D` and `C0:171A` to record queue growth across completed horizontal and vertical passes.

Additional counters at `7F:F174+`:

- `7F:F178` = completed horizontal-pass count
- `7F:F17A` = cumulative `$99` growth across completed horizontal passes
- `7F:F17C` = completed vertical-pass count
- `7F:F17E` = cumulative `$99` growth across completed vertical passes

Interpretation:

- if one lane's cumulative delta climbs much faster during diagonal scrolling, that lane is the better next patch target
- if both lanes contribute similarly, the remaining issue is probably aggregate two-axis queue pressure rather than one pathological lane
- because this accounting only uses the scheduler gates, it should be much less invasive than the rejected helper-wrapper approach

### Scheduler debug v5: queue-append destination bucketing

A queue-attribution build now exists at:

- [asm/overworld_stutter_scheduler_debug_v5_asar.asm](/F:/Earthbound%20Decomp%20-%20Codex/asm/overworld_stutter_scheduler_debug_v5_asar.asm)
- [EarthBound-overworld-stutter-scheduler-debug-v5.sfc](/F:/Earthbound%20Decomp%20-%20Codex/build/EarthBound-overworld-stutter-scheduler-debug-v5.sfc)

This build keeps the earlier stable scheduler instrumentation and adds one conservative hook at the queue-append point inside `C0:865F`.
It records queued descriptor count and queued byte totals, bucketed by VRAM destination.

Additional counters at `7F:F180+`:

- `7F:F180` = total queued-descriptor count through the queued `8643/865F` path
- `7F:F182` = total queued bytes (`$92`) through that path
- `7F:F184` / `7F:F186` = descriptor count / bytes for VRAM `3800`
- `7F:F188` / `7F:F18A` = descriptor count / bytes for VRAM `3C00`
- `7F:F18C` / `7F:F18E` = descriptor count / bytes for VRAM `5800`
- `7F:F190` / `7F:F192` = descriptor count / bytes for VRAM `5C00`
- `7F:F194` / `7F:F196` = descriptor count / bytes for all other VRAM destinations

Interpretation:

- if the four overworld tilemap bands dominate the counts and bytes during diagonal scrolling, the remaining queue pressure is still mostly map-plane related
- if `other` dominates, the remaining diagonal hitch is probably coming from adjacent rendering traffic rather than the main strip-upload destinations

## New companion-lane experiment

The strongest current post-dedupe experiment is now narrower than another generic queue probe.

See [overworld-timer-rerun-gate-a6e3-a794.md](/F:/Earthbound%20Decomp%20-%20Codex/notes/overworld-timer-rerun-gate-a6e3-a794.md).

Current best target:

- the timer-only rerun leg at `C0:A723..A750`

Current best v1 compare tuple for that branch:

- post-toggle raw descriptor header derived the same way as `A794`
- cached previous raw header already stored at `$341A`

Why this is the safest first companion-lane experiment:

- it does not touch movement-change reruns
- it does not touch `A56E`, `8643`, `865F`, or `8677`
- the timer-only branch keeps the larger descriptor-source fields locally stable, so `$341A` is a reasonable first proxy for identical queued output

Patch sketch:

- [overworld_stutter_timer_gate_overlay.asm](/F:/Earthbound%20Decomp%20-%20Codex/asm/overworld_stutter_timer_gate_overlay.asm)






