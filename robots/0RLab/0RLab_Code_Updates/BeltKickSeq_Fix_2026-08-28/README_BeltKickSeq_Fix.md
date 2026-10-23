# BeltKickSeq_Fix — 2026-08-28

**Fixes the over-torque caused by `BeltKickLatch_Fix`. My defect, and a dangerous one.
The early belt kick ships DISABLED in this bundle.**

Reported: *2 parts in scene; belt turned on during the robot's approach to pick the
last part; robot over-torqued at contact because the part had moved relative to the
last trajectory image.*

## What's in this folder

| File | Change |
|---|---|
| `tkPartFinder.pgx` | Kick now **edge-detects a pick counter** instead of reading a latched bool, adds a `bTrajectoryLOGIC` interlock, and is gated behind `bEarlyBeltKick` |
| `tkMonitor_Robot.pgx` | Lift event is **one-shot**: consumes the arm and increments `nPickLiftSeq` exactly once per pick |
| `LAB_PlateSorter2.dtx` | Adds `bEarlyBeltKick` (public bool, **default false**) and `nPickLiftSeq` (private num) |
| `Init.pgx` | Resets `nPickLiftSeq` |

`PartPick.pgx` is **unchanged** from `BeltKickLatch_Fix_2026-08-28` — keep the copy you
already deployed. Bases for all four files here are the `BeltKickLatch_Fix` versions.

## Root cause

`bBeltClear` was a plain latched bool. `tkMonitor_Robot` set it on lift; the only code
that cleared it was inside `tkPartFinder`'s kick block:

```
if bLastPart==true          <-- only runs on the LAST-part cycle
  wait(bBeltClear==true)
  doBelt["FWD"]=true
  bBeltClear=false          <-- so this only ever ran there too
  bBeltLiftArmed=false
endIf
```

With **2 parts in scene** the first pick has `bLastPart==false`, so that block never
ran. `PartPick` armed the latch, the lift set it — and **nothing consumed it.**

Next cycle, one part left, `bLastPart` goes true. `tkPartFinder` reaches
`wait(bBeltClear==true)`, finds it **already true from the previous pick**, and starts
the belt immediately — while `tkCycle`/`PartPick` was still executing
`movej(pBelt_START,…)` on its **approach** to the remaining part. The belt moved that
part out from under the trajectory Apera had already computed for it, and the robot
drove into it at the old coordinates. Over-torque.

A one-bit latch cannot distinguish *"set by the pick I am waiting for"* from *"set by
the previous pick."* That was the design error.

## The fix

**1. One-shot counter instead of a latch.** `tkMonitor_Robot` now clears
`bBeltLiftArmed` and increments `nPickLiftSeq` when the lift threshold is crossed, so
there is exactly one increment per pick and no state left standing.

**2. Edge detection.** `tkPartFinder` snapshots `nPickLiftSeq` **before** waiting and
waits for it to change. Every lift that already happened — including the previous
pick's — is already inside that snapshot, so it cannot satisfy the wait. Only a *new*
lift can. This is structurally immune to the staleness above, not just patched against it.

**3. A second, independent interlock: `bTrajectoryLOGIC==false`.** True means a computed
trajectory is still pending a pick, which is precisely when the belt must not move.
`PartPick` clears it during the retreat, after the gripper has closed. **Either guard
alone would have prevented this incident;** both are in, deliberately.

**4. The whole feature is now switchable.** `bEarlyBeltKick` is a public bool,
**default false**. As shipped, the conveyor is started only by the detector branch after
the camera-FOV-clear wait — the original, proven timing. Set it true from the data
editor or HMI when you are ready to re-validate. No code change to turn it on or off.

The bounded wait from the previous bundle is kept — on timeout it logs and falls
through without starting the belt.

## Why it's safe

- **Ships inert.** With `bEarlyBeltKick=false` nothing in the kick path executes; belt
  behaviour is identical to pre-optimisation. Nothing else reads `bEarlyBeltKick`.
- The belt can only be commanded here after a real lift edge **and** with no trajectory
  pending. On any doubt it does not start the belt at all.
- `nPickLiftSeq` is only ever incremented (never reset except by `Init()`, which runs
  before `PartFinder` is created), so an edge can never be faked by a wraparound.
- Both `.pgx` files parse as well-formed XML; every identifier is declared in the `.dtx`
  or as a program local (verified).
- The `bLastPart` fast path (`nPartFinderLoop=2`) is **not** gated — it only skips two
  vision retries, touches no motion and no belt output, and has run without incident
  since `LastPartBelt_Update`.

## Merge steps

1. Back up the current project.
2. Copy the four files into `usr/usrapp/LAB_PlateSorter2/`, overwriting. Leave the
   `PartPick.pgx` you already deployed in place.
3. Full application reload — the `.dtx` changed.
4. Confirm in the data editor: `bEarlyBeltKick = false`, `nBeltClearHeight_mm = 76.2`,
   `nBeltKickTimeout_s = 3`.

## Verification steps

Run 1-3 with `bEarlyBeltKick` **false**. Only move on if they are clean.

1. **Baseline, 2+ parts in scene.** Full cycles, belt indexing only after the FOV-clear
   wait. The belt must never move while `bRunning["PartPick"]` is true. This is the
   regression test for the incident.
2. **Single part.** Picks, then the detector branch indexes the belt. No stall — confirm
   `nMoveID` keeps cycling and does not park at 750/751.
3. **Empty feeder.** `detector found nothing in 12 tries` and keeps retrying, no hang.
4. **Then enable the kick** (`bEarlyBeltKick=true`) and repeat test 1 with 2 parts, at
   reduced speed, watching the belt during the approach to the *second* part. Expect the
   belt to start only after the last part is ~3 in off the conveyor. Watch
   `nPickLiftSeq` increment once per pick.
5. If you see `no clean belt-clear edge in 3s`, the cell is running the safe fallback
   timing — tell me rather than raising the timeout, it means the lift geometry needs
   looking at.

Given this feature has now failed twice on live equipment, I would leave
`bEarlyBeltKick=false` until you have a session where you can watch step 4 at low speed
with a hand on the stop. The cycle-time gain is not worth another over-torque.
