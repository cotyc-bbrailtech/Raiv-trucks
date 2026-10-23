# Raiv-T1 — run 20: your observation is the root cause

Backup `Y-2026_M-09_D-11_14h40m`. **203 picks, 14:00:38 → 14:19:43**, steel on
the belt, dwells 0.5/0/0.5. The Branch B bundle is deployed — `tkCycle` 76,325
and `LogCycleCSV` 32,356, byte-identical to what I shipped — and **line K is on
all 203 picks**.

You spotted the thing the instrumentation was built to find. The data backs you
up, and it closes a chain that runs all the way from APERA's count to 0.56 s a
pick.

---

## 1. The parked wait was free. That hypothesis is dead.

`loop_top_wait_s` = **0.010 s, median and max, on all 203 picks.** The second
`apera_wait_for_trajectory` — the one the main loop does after Branch B with no
trigger in front of it — returns off a cached result. It is not a round trip and
it never was. I estimated it at up to 0.28 s a pick; it is zero. One `clock()`
call to retire it.

## 2. Branch B, split four ways at last

27 clean passes, median **3.36 s**:

| part | s | what it is |
|---|--:|---|
| travel | 0.68 | `movej(jApera_Trigger_pos)` + `waitEndMove` — real motion |
| detect | 0.89 | belt ON + detector loop, **0.44 s per try**, dead linear (1→0.44, 2→0.89, 3→1.31, 6→2.65) |
| settle | 0.50 | exactly, every pass |
| **traj** | **1.24** | trigger + `AperaPartsFound` + wait — **arm parked**, and constant to ±0.1 |

`br_plates` median **2** — APERA reported two plates and then planned a
trajectory for neither.

## 3. Your observation, and what it explains

**Capture @ FoV on raises the mean plate count from 2.89 to 3.31 (+0.42)** and
collapses the "count = 1" bucket from 21% of picks to 10%. And across 511 picks
over two runs, `nCountPlatesFound` has logged **0 exactly three times** — while
the belt genuinely runs empty every six picks.

So the count is not "pickable plates on the belt". It includes the plate in the
gripper, at least intermittently, and moving the capture earlier — where the arm
is still over the conveyor — puts it in frame far more reliably. That is exactly
what you watched.

Here is why it costs real money:

```
bLastPart = (bTrajectoryFound==true and nCountPlatesFound<=1)
```

That is the arming condition for the early belt kick. **92% of early triggers
fire on a pick where the count is ≤ 1, against a 6% baseline** — the gate does
nothing else. So:

- scene empty + phantom held plate → count reads **1**, not 0
- one real plate left + phantom → count reads **2**, and the kick **never arms**

And then the scene runs dry with no belt advance queued, `apera_wait_for_trajectory`
comes back with nothing reachable, and you are in Branch B.

**The two belt-advance paths, run 20:**

| path | advances | cost |
|---|--:|---|
| laser sensor → early kick → early trigger | **26** | ~0, overlapped with the pick |
| **Branch B** | **34** | **3.36 s, arm parked** |
| | 63 total | |

Same job, two routes, and which one you get is decided by whether APERA happened
to count the plate in the gripper. **34 of 63 went the expensive way: +0.56 s on
every pick.**

## 4. The fix is one number

`bLastPart` needs the count to reach 1. With the phantom present it bottoms out
at 2. Raising that threshold to 2 arms the kick one plate earlier and routes
those 34 advances onto the cheap path.

I built exactly this tunable — `nLastPartThreshold`, shipping at 1 so it is
behaviour-neutral — and **dropped it from the last bundle because I had no
evidence for it.** Now there is evidence, and it is the 92%/6% split above.

**The trade you would be accepting, stated plainly:** at threshold 2 the belt
advances while one real plate is still in the field. `tkBeltScan` stops the belt
when it sees new plates, so that plate does not vanish — it moves downstream and
should still be pickable. But "should" is me reasoning about your conveyor
geometry, and I have never seen it. That is your call, not mine, which is why it
ships at 1 and you turn it up.

The proper fix is upstream: mask the gripper out of the APERA pipeline, so the
count means what the code thinks it means. The threshold is a workaround for a
vision problem, and it is worth saying so out loud.

## 5. The sensor remount worked

| | run 19 | **run 20** |
|---|--:|--:|
| sensor belt stops | 11 | **26** |
| agree / disagree / chatter | 11 / 0 / 0 | **26 / 0 / 0** |
| sensor timeouts | 2 | **0** |
| camera-fallback stops | 1 | **0** |
| `cap_early` | 12 | **26** |

Zero timeouts, zero camera fallbacks, zero disagreements. Whatever you did to
the mounting, it took.

## 6. Where the cycle is

| | |
|---|--:|
| clean median (151 of 203 under 6 s) | **4.55 s** |
| throughput | **10.6 picks/min** |
| Branch B amortised | +0.56 s/pick |
| picks per belt advance | 3.2 |

Still open: `grip_part_at_pick` and `grip_mag_at_pick` read **0 on all 203
picks** again, while `grip_part_at_drop` now reads 1 on 39% (was 12%). %I6 is
clearly alive and clearly not meaning what the name says.

And `nFovHitEnd` reached 66 — the arm is reported inside the drop-station FoV
cube at the empty-scene capture. `nFovHitStart` is still 0.

## 7. What I would do next, in order

1. **Mask the gripper in the APERA pipeline.** Root cause. Everything below is
   working around it.
2. **Ship `nLastPartThreshold`** (at 1), then try 2 with someone watching the
   belt. Up to −0.56 s a pick if it moves all 34 advances onto the sensor path.
3. **Overlap the 1.24 s parked wait** in Branch B, as a toggle, off. Worth ~0.21
   s a pick before (2) and much less after it — so do (2) first and re-measure.
4. Drop the `nCountPlatesFound==0` branch from consideration entirely. It has
   executed 3 times in 511 picks. **Branch B is this cell's real end-of-scene
   detector**, and treating it as a fault path is what kept it invisible.
5. %I6 / %I4 on the pendant.
