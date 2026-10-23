# Raiv-Lab — Last-Part Belt Fast Path (LAB_PlateSorter2)

Prepared: August 28, 2026
Scope: `tkPartFinder` now starts the feeder belt immediately once it knows the
part the robot just picked was the last one visible, instead of waiting
through 2 vision-only capture attempts first. **No motion speeds, motion
descriptors, pick/place logic, or the belt-runaway safety cap
(`nDetectorTries`) were changed.** This is a pure scheduling change inside
`tkPartFinder`, plus one new global flag.

Built from `B&B LAB 08282026.zip`, path
`B&B LAB/Lab Test/usr/usrapp/LAB_PlateSorter2/`.

## What's in this folder

This is a **patch bundle**, not a full copy of the app: it contains only the
2 files that changed, at the top level of `LAB_PlateSorter2` (no
subfolders). Copy these into your project, overwriting the same-named files.

| File | Status | What changed |
|---|---|---|
| `tkPartFinder.pgx` | Modified | Added a "last-part fast path" at the top of the main loop, and one line where `nPartsFound` is tallied. See below. |
| `LAB_PlateSorter2.dtx` | Modified | Added one new global: `bLastPart` (private bool, size 1), inserted alphabetically between `bGripper` and `bMessage`. Nothing else in the data dictionary was touched. |

## The problem this addresses

`tkPartFinder` runs as its own task, looping forever. Each pass starts with:

```
wait(bAREA["conveyor"]==false or bRobotAT["capture"]==true or bAREA["rejectstation"]==true)
```

That's the earliest point the task can act after a pick — `bAREA["conveyor"]`
goes false the moment the robot's TCP clears the conveyor's XY zone, which
happens during `PartPick`'s retreat move, right after the part is lifted off
the belt.

But once unblocked, the existing logic (`nPartFinderLoop`) always spends its
first 2 passes (loop values 0–1) re-triggering a vision-only trajectory
capture before it will even consider indexing the belt (loop values 2–4).
That's the right call when another part is still sitting in the camera's
view — there's no reason to jog the feeder if vision can just see the next
part immediately. But if the part just picked was the *only* part visible,
the feeder is now known to be empty, and those 2 capture round-trips are
pure dead time: there is nothing new to see until the belt physically moves
a part into view.

## The fix

1. **Flag it when we already know** — right where `tkPartFinder` tallies
   `nPartsFound` for the part it just found a trajectory for (the same tally
   used to classify `sPart["Picked"]`), it now also sets:
   ```
   bLastPart=(nPartsFound<=1)
   ```
   i.e. "the part about to be handed to `PartPick` is the last one visible."

2. **Act on it the instant the robot clears the belt** — at the top of the
   loop, right after the existing `wait(...)` unblocks (robot has lifted the
   part off the belt):
   ```
   if bLastPart==true
     nPartFinderLoop=2
     bLastPart=false
   endIf
   ```
   Forcing `nPartFinderLoop` to 2 skips the two vision-only attempts and
   drops straight into the existing belt-indexing branch, so `doBelt["FWD"]`
   goes true right away — overlapping the belt index with `PartPlace`
   instead of waiting for 2 more vision cycles to fail first.

Everything downstream is untouched: the belt-indexing branch still runs the
same detector loop, still caps out at `nDetectorTries` attempts, still stops
the belt and raises `bMessage["Feeder"]` if nothing is found, exactly as
before. This only changes *when* that branch is entered on the pass right
after emptying the feeder — not how it behaves once entered.

## One thing to verify before deploying

`bLastPart` is a brand-new global — double check `LAB_PlateSorter2.dtx`
merges cleanly with whatever your project's data dictionary looks like
today if it has diverged from the `08282026` backup this was built from
(the insertion point is called out above so a manual re-add is quick if the
automatic merge doesn't take). **Open the project in the VAL3 IDE and
confirm it compiles clean before running it on the robot.**

## Merge steps

1. Back up your current `usrapp/LAB_PlateSorter2` folder (or keep the dated
   backup this was built from: `B&B LAB 08282026.zip`).
2. Copy `tkPartFinder.pgx` and `LAB_PlateSorter2.dtx` from this bundle into
   your live `LAB_PlateSorter2` project, overwriting the existing files.
3. Open the project in the Stäubli VAL3 IDE, let it re-scan, and
   **build/compile before touching the real robot**.
4. Test in manual/reduced-speed mode first: run the feeder down to its last
   part on purpose and confirm the belt starts moving as soon as that part
   clears the conveyor area, well before the arm reaches the accept/reject
   station.
5. Confirm the existing "feeder starved" behavior still works unchanged:
   run the feeder empty for real and check `bMessage["Feeder"]` still comes
   on after `nDetectorTries` failed attempts, same as before this change.
6. Only then run it in normal production mode and compare cycle time.

## Design notes

- This only ever fast-forwards *into* the existing belt-indexing branch — it
  never changes what that branch does, so the 20-August runaway-belt
  protection (`nDetectorTries`, belt stopped unconditionally after the
  detector loop) applies exactly as it did before.
- `bLastPart` is deliberately consumed (`=false`) the first time it's read,
  so a stale `true` can't re-trigger the fast path on a later pass for a
  different pick.
- If you'd rather this only fire below some threshold other than "1 part
  visible" (e.g. also fast-path when 2 are left, to get a head start before
  the very last one), change the `nPartsFound<=1` line — everything else
  follows from that one comparison.
