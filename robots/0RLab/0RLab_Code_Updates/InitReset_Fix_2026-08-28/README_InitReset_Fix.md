# Raiv-Lab — Fix: bLastPart Never Reset at Startup (LAB_PlateSorter2)

Prepared: August 28, 2026
Scope: one-line fix for the deadlock reported after merging
`BeltClear3in_Update_2026-08-28` — `tkPartFinder` hangs forever at
`wait(bBeltClear==true)` on a cold start, before any part has ever been
cycled, so the belt never moves.

## The bug

`bLastPart` is a plain global bool I added in `LastPartBelt_Update_2026-08-28`.
Global data in this app is **not** guaranteed to come up `false` on its own —
that's exactly why `Init.pgx` explicitly zeroes ~50 other flags
(`bTrajectoryFound`, `bTrajectoryLOGIC`, every `bRunning[...]`, etc.) every
time it runs. I added `bLastPart` to the data dictionary but forgot to add
it to that same reset list. If it comes up (or gets left) `true`, the very
first pass through `tkPartFinder`'s loop hits:
```
if bLastPart==true
  wait(bBeltClear==true)
  ...
```
and blocks forever — `bBeltClear` can only go true partway through an actual
`PartPick` retreat (`getMoveId` 250–300 + the ~3in lift), and with
`tkPartFinder` itself stuck here, no trajectory is ever found, no pick ever
happens, so that retreat never occurs. Nothing else in the app can break the
deadlock on its own.

## The fix

One line added to `Init.pgx`, grouped with the other one-shot bool resets:
```
bLastPart=false
```

## Why this one line is enough (traced through the abort path too)

`Init.pgx` runs in exactly two places, both **before** `tkPartFinder` can
possibly be running:
- `TaskCommand()` calls `Init()` once at controller startup, before the
  `Cycle` task (which is what creates `PartFinder`) is ever created.
- `tkAbort()` calls `Init()` during abort recovery — but by that point
  `TaskCommand()`'s supervisory loop has already force-killed the
  `PartFinder` task outright (`taskKill("PartFinder")`, unconditional -
  it doesn't matter what the task was blocked on). So even if `bLastPart`
  had gone `true` mid-cycle and `PartFinder` was sitting in the new
  `wait(bBeltClear==true)` when an abort was triggered, the task is
  terminated by the kill, not left running - and the next time `Cycle`
  (re)creates `PartFinder`, `bLastPart` has already been reset by `Init()`.

So both paths that can leave `PartFinder` restarting - a genuine cold
start, and a killed-and-recreated task after an abort - already run
through `Init()` first. This one line covers both.

## Merge steps

1. Copy `Init.pgx` from this bundle into your live `LAB_PlateSorter2`
   project, overwriting the existing file. No other file needs to change -
   `bLastPart` itself was already added to the data dictionary in
   `LastPartBelt_Update_2026-08-28`.
2. Build/compile clean in the VAL3 IDE.
3. Power cycle (or re-run `Init()`/`TaskCommand()`) and confirm the belt
   stays off and `tkPartFinder` reaches its normal vision-search logic
   immediately, instead of sitting at `wait(bBeltClear==true)`.
4. Re-run the last-part test from the prior two updates to confirm the fast
   path still works correctly once parts are actually cycling.
