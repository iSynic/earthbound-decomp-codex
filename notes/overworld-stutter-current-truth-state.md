# Overworld Stutter Current Truth State

This note reconciles the March 27 decomp-side investigation with the later March 30 patch-thread follow-up work, so the overworld walking microstutter lane has one current baseline again.

See also [overworld-walking-stutter-producer-split-c01558-c01ca8.md](overworld-walking-stutter-producer-split-c01558-c01ca8.md).
See also [overworld-a794-watcher-gate-safe-v4.md](overworld-a794-watcher-gate-safe-v4.md).
See also [overworld-companion-family-priority-a794.md](overworld-companion-family-priority-a794.md).
See also [overworld-timing-scroll-commit-slice-c08b20-c08284.md](overworld-timing-scroll-commit-slice-c08b20-c08284.md).
See also [overworld-visible-entity-refresh-slice-c07b52-c07c5a.md](overworld-visible-entity-refresh-slice-c07b52-c07c5a.md).
See also [overworld-live-walking-controller-c04c45-c04d33.md](overworld-live-walking-controller-c04c45-c04d33.md).
See also [rom-patch-overworld-stutter-plan.md](rom-patch-overworld-stutter-plan.md).

## Main result

The March 27 and March 30 results fit together cleanly.

The healthiest current model is:

- the visible hitch is not mainly a stale-camera or stale-scroll-commit problem
- the hitch is not fully explained by redundant strip uploads either
- the strongest remaining render-side culprit is still the companion visual family around `C0:A794`
- but the narrow timer-only `A6E3` gate was too small to matter visibly
- so the best current companion-side patch seam is the broader watcher rerun site at `C0:A750`, not the timer-only sub-branch and not the shared queue core

So the current best reconciled read is:

- camera motion path looks healthy
- scroll publish and NMI commit path look healthy
- strip dedupe helped somewhat but did not solve the issue
- remaining hitch is most likely aggregate presentation workload, with the `A794` companion family still the sharpest patchable sub-family inside that workload

## Locally proved

### Camera and scroll-state timing are no longer the leading failure model

The combined decomp and emulator work now supports this chain:

1. `C0:17EA..18F2` advances live camera position in `$4380/$4382`
2. `C0:1558` reacts after camera motion and writes runtime scroll shadows in `$31/$33/...`
3. `C0:8B20..8B8D`, especially `C0:8B51 / C0:8B57`, publish those into alternating NMI shadow slots `$41/$45/...`
4. `C0:8284..82CA` commits those shadow slots to the real PPU scroll registers during NMI

The later timing and camera notes make the following points materially stronger:

- `C0:8012` is startup only, not a frame pacing seam
- `C0:834E` is NMI bookkeeping, not a main-loop wait seam
- diagonal-walk emulator traces showed smooth advancing values at the movement-time writers and normal publish into the NMI shadow pairs
- `17EA..18F2` is the real camera-step accumulator ahead of `1558`

So the older "stale scroll publish" theory is now weakened substantially.

### The two-producer-family model still holds

The March 27 decomp note remains structurally sound:

- strip family:
  - `C0:0E16 / 0FCB / 1181`
  - observed VRAM family `58xx / 5Axx / 5Bxx / 5Cxx / 5Exx`
- companion family:
  - seeded through `C0:2A50 -> 2957 -> 1E49`
  - direct uploader `C0:1CA8..1D37`
  - broader descriptor producers `C0:A4C4` and especially `C0:A794`
  - observed VRAM family `4040 / 4120 / 42A0`

This split still best explains why the safe strip-dedupe patch helped but did not eliminate the visible hitch.

### `A794` is still the strongest residual companion-side culprit

The combined notes now support a cleaner hierarchy:

- `1CA8..1D37` proves the companion family really reaches the `0x4000+` VRAM band directly
- `A4C4` is the simpler descriptor producer
- `A794` is the more dynamic movement-time producer because it uses `$10F2` phase bias and is rerun by the watcher logic at `A6E3..A753`

The main structural facts still holding up are:

- `A794` consumes seeded descriptor state including `$298E`, `$2A7E`, `$2ABA`, `$2A42`, `$29CA`, `$2AF6`, and `$2BAA`
- `A56E` can split a logical companion update into two queued descriptors on page crossing
- `A794` writes the raw descriptor header to `$341A`
- `A6E3..A753` can rerun `A794` both on composite-state changes and on cadence-driven phase refreshes

So `A794` still looks like the sharpest patchable sub-family inside the remaining presentation load.

### The timer-only gate result is now a meaningful negative result, not a dead end

The timer-only patch around the `A723..A750` sub-branch was safe but did not visibly improve the hitch.

That means:

- timer-only `A794` reruns are real
- they are not, by themselves, the dominant visible problem

This does not clear `A794` as a whole. It only clears the narrowest attempted gate.

### The broader watcher-side `A750` rerun site is now the best current companion-side patch seam

The `safe-v4` patch note materially improves the patch target ranking:

- it broadened the gate from the timer-only leg to the common watcher-side rerun site at `C0:A750`
- it intentionally left the immediate state-change rerun at `C0:A6F7` intact
- it used a fuller compare tuple than the timer-only experiment:
  - raw descriptor header
  - VRAM base `$298E`
  - transfer size `$2A7E`
  - transfer count `$2ABA`
  - packed source-bank plus auxiliary-prepass state from `$2A42 / $2BAA`
  - effective selector pointer from `$29CA + 4*DATA_C0A623[$2AF6] + $10F2`

That is now the healthiest current patch-prep seam because it is:

- broader than the failed timer-only experiment
- narrower than a global `A794` hook
- still safely above `A56E / 8643 / 8677`

### The best remaining render-side decomp seam is downstream of smooth camera motion

The newer visible-entity note strengthens the visual interpretation:

- `C0:7B52..7C5A` refreshes a small high-priority visible-entry set
- it computes screen-space coordinates by subtracting the smooth camera shadows `$31/$33`
- then it immediately calls `C0:A780`, inside the same companion descriptor family that later reaches `A794`

So the render-side story is now healthier too:

- the camera can be smooth
- the visible entity or companion visual layer can still look uneven downstream

## Ref-backed and locally consistent

### Best current high-level interpretation

The current healthiest blended explanation is:

- diagonal walking increases total presentation work because both axis lanes and both visual families can be active in the same frame
- the generic scroll-state timing path is functioning normally in the tested walking cases
- the remaining hitch is therefore more likely presentation workload than stale state publication
- inside that workload, `A794` remains the strongest targeted patch seam because it is narrower than the strip family as a whole and narrower than the generic queue helpers

### Why the old March 27 patch-prep conclusion needed updating

The March 27 decomp pass correctly identified `A6E3..A753` as the right family, but its first "best next patch" conclusion was too narrow:

- timer-only rerun gating was a good first experiment
- the March 30 follow-up now shows it was not broad enough to matter visibly

So the updated conclusion is not "the decomp note was wrong." It is:

- the decomp note found the right family
- the first patch experiment targeted too small a sub-branch of that family

## Still uncertain

### Whether the broader `A750` watcher-side gate is enough on its own

`safe-v4` is a materially better experiment than the old timer-only gate, but the current notes still stop short of proving it is enough by itself to remove the visible hitch.

### Whether the eye is mainly catching descriptor emission cadence or visible-entry refresh cadence

The current render-side story has two adjacent open substeps:

- screen-space recompute cadence in `7B52..7C5A`
- downstream descriptor emission through `A780 / A794`

Those are now adjacent enough that the next round of work can be much more targeted.

### How much strip-family work still matters after the companion-side refinements

The strip family is no longer the whole story, but it is also not cleared. The best current model remains aggregate load, not a single magical culprit.

## Current best target ranking

### Patch seams

1. `C0:A750` watcher-side rerun gate over `A794`
2. broader `C0:A6E3..A753` watcher-family analysis if the `A750` gate is still not enough
3. only after that, revisit strip-family refinements around `0E16 / 0FCB / 1181`

### Decomp seams

1. `C0:7B52..7C5A`
2. `C0:A780 / A794`
3. caller-family attribution around the hottest `A794` reruns during diagonal walking

If the investigation returns to walking-state cadence before the visual
descriptor family, the live stack note for `C0:4C45 -> C0:5F82 -> C0:400E/4010`
is the cleaner upstream entry point.

## Practical guidance before moving on

If we return to patching first, the current best instruction is:

- do not go back to timer-only gating as the main experiment
- do not jump down into `A56E / 8643 / 8677`
- prefer the broader watcher-side `A750` gate with the fuller compare tuple

If we return to ROM-first decomp first, the current best instruction is:

- treat camera and scroll publish as mostly cleared
- focus on the visible-entry refresh and companion descriptor seam at `7B52 -> A780 -> A794`

## Bottom line

The March 27 and March 30 work now reconcile into a cleaner current truth state:

- the stutter is not primarily a stale-camera or stale-scroll-commit issue
- the stutter is not fully solved by strip dedupe either
- `A794` remains the strongest patchable residual producer family
- the timer-only `A6E3` gate was safe but too narrow
- the best current companion-side patch seam is the broader watcher rerun site at `A750`
- the best current render-side decomp seam is `7B52..7C5A -> A780 -> A794`
