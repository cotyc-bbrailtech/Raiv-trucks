# Raiv-T1 — first run of the sensor-only belt build (22 Sep)

**Backup `Y-2026_M-09_D-22_12h46m`. Rev D deployed byte-for-byte unmodified.**
154 logged picks across six sessions, 10:23–12:31.

---

## Headline

**The belt control works. The capture gate is 100% broken, and it is costing 47%
of the run.**

| | |
|---|--:|
| belt starts | **60** |
| beam break edges | **60** |
| → belt starts that ended with a plate at the beam | **60 / 60** |
| runaway stops during production | **0** |
| belt-master heartbeat failures | **0** |
| sensor chatter | **0** |
| **`nCapFovClear` — captures taken with the arm clear of the camera** | **0** |
| `nFovDeclines` | **115** |
| `nFovWait_s` | **3.01 s on every one of 154 rows** |

`WaitFovClear` **never once succeeded.** Every call ran the full
`nFovClearTimeout_s` = 3 s and gave up.

## The belt half — this part is right

Sixty belt starts, sixty beam breaks, one-to-one. Every time the conveyor ran it
ran until a plate reached the pick end, then stopped. No runaways in production,
no heartbeat loss, no chatter, no wait timeouts, no wait alarms.

The lift gate is live and sane: `liftMm` samples span 70–130 mm against the
76.2 mm threshold, so the arm is being measured and the gate is releasing on
height as intended. `nBeltStartHolds` = 351 over 154 picks — about 2.3 per pick
rather than 1, because the episode flag re-arms whenever any hold condition
reappears during a pick. That is a noisy counter, not a fault.

Four nudges fired, all "attempt 1 of 3", none escalated to the alarm — so in
each case the belt moved the obstruction and the next capture succeeded. That
mechanism did its job. (`nBeamNudge_s` was showing 1 s in the log against the
0.75 s I shipped, so you tuned it at runtime; note that did not persist — the
`.dtx` in this backup is byte-identical to what I shipped, so nothing was saved
from SP2 and every counter in it is stale.)

The two runaway stops were both during setup (10:39 and 10:53) on a genuinely
empty feeder, and both latched the alarm — exactly the bring-up annoyance I
flagged. Set `nBeltRunMax_s` to **0** while commissioning.

## The capture half — this is the whole problem

`nStartFoVX_mm` = 1075 puts the "arm is clear of the camera" boundary at world
x = **+550**, your measured figure. **The cycle's capture pose never gets
there.** `nFovHitStart` climbed by **74** over the run — the arm is reported
*inside* the conveyor cube at capture — and `nFovHitEnd` did not move at all.

This is the failure I put at the top of the deploy notes as *"read `fov_declines`
first, it should be 0"*. It is the same defect I introduced on 15 Sep, and I did
not verify the capture pose against the new boundary before shipping rev A.
That was the one thing the README listed as unverified and it is the one thing
that broke.

**It does not merely cost 3 s.** When `WaitFovClear` fails, the guaranteed-capture
block refuses to trigger, `bTrajectoryFound` is forced false, and the pick routes
into Branch B. The correlation is exact:

| | picks | median cycle |
|---|--:|--:|
| no decline | 93 | **4.43 s** |
| decline, no Branch B | 24 | 8.18 s |
| decline **and** Branch B | 36 | **13.41 s** |

**36 of 36 Branch B passes had a FoV decline. There were zero Branch B passes
without one.** Not a correlation — the declines are causing them.

Run total 1295 s of cycle for 154 picks. At the clean 4.43 s that is 682 s.
**613 s lost, 47% of the run.**

The 51 log lines reading *"capture with arm INSIDE the APERA view — this capture
images the gripper"* are the branch tails, which capture regardless of the gate.
That is why the cell kept producing at all, and why `plates_found` never read 0
(median 5.0) — the scenes are full, APERA just keeps being handed pictures with
a gripper in them.

## What to do

**Now, from the data editor — no redeploy:**

1. **`nStartFoVX_mm` → 835**, then **restart the application** (the cube is built
   at task start, so this one needs the restart). That puts the boundary back at
   +310, where `nFovHitStart` read **0 for the entire project** until 15 Sep —
   i.e. the taught capture pose is demonstrably outside that cube. Expect
   `nCapFovClear` to start counting and Branch B to collapse toward zero.
2. **`nFovClearTimeout_s` 3 → 0.5.** Cheap insurance either way, no restart.
3. **`nBeltRunMax_s` → 0** while you are still commissioning.

Nothing here touches the belt: `_bStartFoV` is not read by the belt master, so
the conveyor behaviour is unaffected by all three.

**The honest trade in (1):** at 835 the camera can still see the gripper at the
capture pose — that is exactly what your +550 measurement established. The
difference from before is that **the belt no longer depends on the plate count**,
so the phantom's main consequence is gone. What is left is APERA occasionally
planning a grip on the held plate, which shows up as Branch B rather than as a
belt error.

**The durable fix is one of these two, and they are alternatives:**

- **Teach a capture pose that is genuinely past +550** and use it for
  `jApera_Trigger_pos`. Then the boundary can go back to 1075 and the gate means
  what it says. This is a pendant job and it is the clean answer.
- **Wire the `BeltFill` search region** on the APERA side. Then the gripper being
  in frame stops mattering at all, wherever the arm is, and the FoV gate becomes
  a nicety rather than a requirement. Still the highest-value item on the list.

## Two defects of mine to fix in the next revision

- **`nNoPickOnBeam` is unreadable in the log.** `tkCycle` zeroes it on a
  successful pick *before* `LogCycleCSV` runs, so CSV line L records 0 on all 154
  rows even though it demonstrably reached 2 at least four times (the nudges
  prove it). It needs to be snapshotted before the zero.
- **`sensorStops`, `cameraStops`, `nSensorAgree`, `nSensorDisagree` all read 0**
  and will stay that way — they belonged to the retired `tkBeltScan`. They should
  be dropped from the CSV or repointed, because right now they read as "the
  sensor is doing nothing", which is the opposite of the truth.

## What the clean picks say about cycle time

The 93 picks that avoided the gate ran at **4.43 s median** — better than the
4.56 s baseline from 11 Sep, with the belt under sensor control and a capture on
a stopped belt every pick. That is the number to hold onto: the design is sound
and the geometry is what is wrong.
