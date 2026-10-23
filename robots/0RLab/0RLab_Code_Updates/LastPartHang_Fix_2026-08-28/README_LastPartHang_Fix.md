# Raiv-Lab — Real Fix for the wait(bBeltClear) Hang, Plus Init.pgx Scan (LAB_PlateSorter2)

Prepared: August 28, 2026
Scope: the `Init.pgx` fix from `InitReset_Fix_2026-08-28` was necessary but
not sufficient — you're right that it's still hanging. This is the actual
root cause, found in `tkPartFinder` itself, plus a full scan of every
global in the data dictionary against what `Init.pgx` resets (you flagged
`nPartFinderLoop` as worth a look — here's what that scan turned up on it
and everything else).

## The real bug

`bLastPart` was computed as:
```
bLastPart=(nPartsFound<=1)
```
That's true both when **exactly one** part is visible (the intended case -
"the part about to be picked is the last one") **and** when **zero** parts
are visible - an empty feeder, or the detector simply giving up. Those are
completely different situations. Zero parts means nothing is being picked
at all: `bTrajectoryFound` stays `false`, `bTrajectoryLOGIC` stays `false`,
`tkCycle` never calls `PartPick` for anything. But `bLastPart` still went
`true` - so on the very next pass, `tkPartFinder` hits the belt-kick block
added in `BeltClear3in_Update_2026-08-28` and blocks on
`wait(bBeltClear==true)`, a condition that can only become true partway
through a `PartPick` retreat that is now never going to happen. Permanent
hang, and it doesn't matter that `Init.pgx` correctly zeroes `bLastPart` at
startup - this happens live, the first time a vision pass comes back with
zero parts (which is exactly "not parts have been cycled yet": an empty or
not-yet-loaded feeder at power-up detects zero, not one).

**Fix**, in `tkPartFinder.pgx`:
```
bLastPart=(bTrajectoryFound==true and nPartsFound<=1)
```
`bTrajectoryFound==true` only happens when Apera actually computed a real
pick trajectory for a specific part - which can't happen with zero parts in
the scene. Gating on it means `nPartsFound<=1` can now only ever mean
"exactly one, and it's the one about to be picked" - the original intent.

This is the one that actually matters. It fully explains why the problem
persisted after the `Init.pgx` patch: that patch fixed a real but secondary
issue (a stale `true` surviving a restart); this fixes the thing that was
setting `bLastPart` true incorrectly in the first place, every single run.

## The Init.pgx scan you asked for

I parsed every `<Data>` entry in `LAB_PlateSorter2.dtx` (154 globals) and
checked which ones `Init.pgx` never assigns. Most of the ~110 matches are
not bugs - they're taught positions (`jBelt`, `jAccept`, ...), tool/motion
descriptors (`tGripper`, `mBlend`, ...), hardware I/O signals (`diServo`,
`doLamp`, ...) and production counters/tunables that are supposed to
persist across a restart (`aoMetric`, `nDetectorTries`, ...). Init.pgx was
never meant to touch those, and doesn't need to.

Narrowing to things that are genuinely one-shot **cycle-state flags** -
the same category as the ~50 lines already in `Init.pgx`
(`bTrajectoryFound`, `bTrajectoryLOGIC`, every `bRunning[...]`, etc.) -
turned up:

| Variable | In this update? | Why |
|---|---|---|
| `nPartFinderLoop` | **Added** (`=0`) | You flagged this one. It's already zeroed by `tkCycle` right before it creates `PartFinder`, and by `tkAbort` when resuming to Cycle - both of those run after `Init()` in every path that (re)creates `PartFinder`, so I don't believe it's the cause of this specific hang. But its data-dictionary default is `2`, not `0` - worth closing that gap in `Init.pgx` too, for the same defense-in-depth reason everything else in that file is there. |
| `bDelay["reject_overflow"]` | **Added** (`=false`) | Pre-existing gap, not something I introduced: `Init.pgx` already zeroes `bDelay["accept_overflow"]` but never had the matching `reject_overflow` key, even though `PartPlace` sets/uses both symmetrically. Low risk (it's set and cleared within the same `PartPlace` pass), but cheap to close and makes the two sides consistent. |
| `bLastPart` | Already fixed (prior update) | Confirmed still correctly present in `Init.pgx` from `InitReset_Fix_2026-08-28`. |

Everything else the scan flagged, for the record (none of these need action
- listed because you asked me to scan, not because they're bugs):
- **`bRobotAT["clear"]`** and roughly half of `bRobotMotion[...]`'s keys are
  declared in the data dictionary but never assigned anywhere in the
  project, not just `Init.pgx` - they look unused/vestigial rather than
  under-initialized.
- **`trZ["100mm"]`/`trZ["150mm"]`** are declared alongside `trZ["50mm"]`
  (which `Init.pgx` does set) but nothing in the project uses the 100mm/150mm
  ones yet - likely placeholders for future use.
- Everything under `bAREA`, `bRobotAT`, `nDis_From`, `nTCP*`,
  `bAccept_Overflow`/`bReject_overflow`, `sPartsFound`, `nObjectCount`,
  `nPartsFound` is recomputed unconditionally every pass by `tkMonitor_Robot`,
  `tkMonitor_IO`, or `tkPartFinder` itself before it's ever read - stale
  values can't survive a single loop pass, so these don't need an `Init.pgx`
  entry (this is the same reason `bBeltClear`/`nTCP_beltLift_m`, added in
  `BeltClear3in_Update_2026-08-28`, don't need one either).
- `sPart["Desired"]` is never reset - this looks intentional (it's the
  operator's part-type selection from the HMI; you'd want that to survive a
  restart, not force a re-selection every power-up), but flagging it since
  you asked for a full scan.

## Merge steps

1. Copy `tkPartFinder.pgx` and `Init.pgx` from this bundle into your live
   project, overwriting the versions from the last two updates.
2. Build/compile clean in the VAL3 IDE.
3. Power cycle and confirm `tkPartFinder` no longer hangs even when the
   feeder starts empty - watch `bLastPart` and `nPartsFound` on a monitor
   page across a detector cycle that finds zero parts, and confirm
   `bLastPart` stays `false` through that.
4. Re-run the last-part test (feeder down to exactly one part) and confirm
   the belt still kicks on early, same as the last two updates.
