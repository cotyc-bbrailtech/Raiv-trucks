# SettleDelay_Tidy — 2026-08-31

Review of your `nDelay_SettlePartsBelt` change in `B&B LAB (2)`. **The change is right and
in the right places.** Two tidy-ups, and one number that says where the rest of the dwell
actually is.

## Your change checks out

| | |
|---|---|
| Declared in `.dtx` | yes — line 922, self-closing element |
| Set in `Init.pgx` | yes, `=1` |
| Used in `tkPartFinder` | both belt branches — after the detector loop stops the belt (line 199) and after the force-jog pulse (line 207) |
| Replaced | the two hard-coded `delay(2.5)` calls |
| Abort-latch fix | present, `bMessage` reset is in |

Sharing one variable across both branches is correct — both are the same physical thing,
feeder ramp-down plus parts settling.

## Two tidy-ups (in this folder)

**1. The comments got swapped.** In your `Init.pgx` the block reading *"Lift counter (CTC
8/28-5), tkPartFinder edge-detects this…"* now sits above `nDelay_SettlePartsBelt=1`, and
your new *"Switch Pipeline Delay time"* comment sits above `nPickLiftSeq=0`. The new line
went in above your comment instead of below it, displacing `nPickLiftSeq`. Each comment now
describes the wrong variable — the sort of thing that misleads someone in six months.
Un-swapped, and the settle comment expanded to say what the delay is actually guarding.

**2. `access="private"` → `public`, with a dtx default of 1.** Every other tuning knob in
this project is public — `nDetectorTries`, `nBeltClearHeight_mm`, `nBeltKickTimeout_s`,
`nLogPeriodSec`, `nMetricPeriod`, `nLoopPace`. This is the one you will want to trim while
watching the cell, so it should be adjustable from the data editor without an edit and
reload. Also moved from the end of the file into alphabetical position (before
`nDetectorTries`) and given a default value, matching the rest of the dictionary.

Files: `LAB_PlateSorter2.dtx`, `Init.pgx`. Nothing else changes — keep your `tkPartFinder.pgx`.

## Where the rest of the dwell is

The dwell you are watching is **not** just the delay. After the belt stops, `tkPartFinder`
still has to run a full trajectory capture before `bTrajectoryLOGIC` goes true and `tkCycle`
can call `PartPick`:

```
doBelt["FWD"]=false                       <- belt off, what you see
delay(nDelay_SettlePartsBelt)             <- your knob
bRunning["PartFinder_Trajectory"]=true
  apera_trig_traj / apera_wait_traj / apera_inspect
bTrajectoryLOGIC=bTrajectoryFound         <- only now can the robot move
```

`tkMetrics` brackets `CamSec`/`CamRuns` on exactly that `bRunning["PartFinder_Trajectory"]`
window, so your own 08/31 numbers measure it directly:

```
CamSec 79.170487 / CamRuns 57  =  1.389 s per trajectory capture
```

So:

| | settle | trajectory capture | dwell |
|---|---|---|---|
| before | 2.500 | 1.389 | **3.889 s** |
| now | 1.000 | 1.389 | **2.389 s** |
| floor if settle went to 0 | 0 | 1.389 | 1.389 s |

You have taken 1.5 s out of it. Of what remains, **58% is Apera, not your delay.** Worth
knowing before you trim the delay further chasing time that is not there.

## Before trimming further — two things

**1. The delay guards the trajectory image.** The pose Apera computes in that capture is
what `PartPick` drives to. If the parts are still rolling when the image is taken, the pose
is stale and the robot goes to where the part was — the same failure as the 8/28 over-torque,
arrived at from a different direction. Step it down (1.0 → 0.75 → 0.5) and watch, rather
than jumping to the shortest value that appears to work. `bEarlyBeltKick` is now true as
well, so there is less slack in the system than there was.

**2. Fix the measurement before you tune against it.** The abort-latch fix is merged, but
until you have run with it the loss budget still reads 100% FAULT, which means `Bbelt`
(belt advance, s/plate) reads 0 and LRC cannot compute. Run one clean batch first, then:

- **`Bbelt`** is the number this change should move. That is your before/after evidence.
- **`Bvision`** decides whether the 1.389 s is worth attacking at all. `tkMetrics`' own
  header makes the point: camera time high with vision wait near zero means a concurrent
  PartFinder is covering the look and a faster camera buys nothing. Here the robot is parked
  at capture waiting, so I expect it to be on the critical path — but measure it, do not
  take my word for it.

If `Bvision` confirms it, the next win is the **trajectory** pipeline `bin1_TCPA200`, which
still runs the full grasp-planning stack. That is the same job we did on 8/28 for the
detect-only pipeline, and `DetectPipeline_SpeedUp_2026-08-28` is the template.

## One optional split

In the force-jog branch the first `delay(1.5)` is the jog *duration*, not a settle — a
different physical quantity that happens to share a line. If you want to tune how far the
belt shuffles when nothing is pickable, that one wants its own name
(`nDelay_JogFeederRun`). Say so and I will add it; I left it alone because you did not ask.
