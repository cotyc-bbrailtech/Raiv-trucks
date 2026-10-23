# Raiv-T1 — sensor-only belt, run 2 (22 Sep, 13:33–13:48)

**Backup `Y-2026_M-09_D-22_14h04m`. Rev D programs unchanged; all three tunable
changes applied and saved.** 96 picks in one clean 15-minute session.

---

## All three fixes worked

| | shipped | now |
|---|--:|--:|
| `nStartFoVX_mm` | 1075 | **835** |
| `nFovClearTimeout_s` | 3 | **0.5** |
| `nBeltRunMax_s` | 120 | **0** |

| | 12h46 run | **this run** |
|---|--:|--:|
| picks | 154 | 96 |
| `nFovDeclines` | 115 | **0** |
| `nFovHitStart` | +74 | **0** |
| `fovWait_s` | 3.01 s on every row | **0.000 s** (median and max) |
| "capture with arm INSIDE the APERA view" | 51 | **0** |
| Branch B passes | 40 | **2** |
| median cycle | 4.82 s | **4.63 s** |
| runaways / nudges / alarms | 2 / 4 / 4 | **0 / 0 / 0** |

`WaitFovClear` was called 8 times and succeeded 8 times. In the previous run it
was called 115 times and succeeded **zero**.

**The whole non-CSV log for this run is one line** — a legitimate *"waited 60s
for a plate at the belt sensor and none arrived, conveyor is still feeding"*.
Nothing else. No warnings, no errors.

## The capture path came back to life

`cap_at_place` = **75 of 96**. With the beam broken whenever a plate is at the
pick end, the belt is stopped through the place move, so `bBeltReadyForCapture`
is true and `Part_Accept` captures there again — the overlapped capture, but now
provably on a stopped belt. `cap_at_trigpos` 19, `cap_deferred` 20,
`cap_belt_busy` 20.

That is why Branch B collapsed from 40 to 2: captures are happening, so
`bTrajectoryFound` is no longer being forced false.

## The belt

| | |
|---|--:|
| belt starts | 36 |
| beam break edges | 38 |
| lift-gate holds | 219 (2.3/pick, same ratio as before) |
| nudges · runaways · chatter · master-dead | 0 · 0 · 0 · 0 |
| belt wait timeouts | 1 (the empty-feeder 60 s) |
| belt run per advance | ≤ 1.0 s |

96 picks from 36 advances — 2.7 plates per advance. Belt run time per advance is
at most a second, so plates are arriving essentially as soon as the belt moves.

## The mean is still 8.33 s — here is why, and it is not the code

355 s of excess over the median. **Four picks hold 281 s of it:**

- one pick at **116 s** with `beltDwell` = 165 s — a plate sat on the beam;
- two picks at **74 s / 65 s** — belt waits of 22.7 s and 60.0 s on an empty feeder;
- one at 25 s.

Strip those four and the other **92 picks run at median 4.62 s, mean 5.64 s** —
about **1.0 s/pick** of ordinary variation. For a manned 15-minute test with the
feeder being loaded by hand, that is what it should look like.

Monitor speed was 100% throughout with zero rejects, so none of the tail is the
arm being slowed.

## The cycle is now fully explained by its segments

| segment | median |
|---|--:|
| retreat | 1.31 |
| linear approach | 0.71 |
| approach | 0.64 |
| place + return | 0.82 |
| gripper | 0.50 |
| vision wait | 0.49 |
| **sum** | **4.47** |
| **median cycle** | **4.62** |

0.15 s unaccounted. APERA latency is 1.29 s median against a 0.49 s vision wait,
so most of the planning is hidden under motion — that is working as intended.

**4.63 s median is parity with where the cell was before any of this** (4.56 s
on 11 Sep), but now with the conveyor under sensor control, one belt writer,
every capture on a stopped belt, and no dependence on the plate count.

`plates_found` reached **0** on one pick — the first genuine zero I have seen in
this project outside run 23. The count can now tell an empty scene.

## Three things to do

1. **Put `nBeltRunMax_s` back** — to 180 or so — once you are done commissioning.
   At 0 the runaway cap is off, which is why the 60 s empty-feeder wait just ran
   the belt. That is what you wanted today, but with it off a sensor frozen
   "clear" would run the conveyor indefinitely with nothing to stop it.
2. **The +550 measurement is no longer honoured.** At `nStartFoVX_mm` = 835 the
   camera can still see the gripper at the capture pose. It is demonstrably not
   hurting right now — Branch B twice in 96 picks — but the honest position is
   that we traded a correct boundary for a working cycle. The durable fix is
   still the **`BeltFill` search region** on the APERA side, which makes the
   gripper being in frame irrelevant and would let the boundary go back to 1075.
3. **The duplicated settles are now pure waste.** `nPartsSettle` = 1.0,
   `nBranchBSettle_s` = 0.5, plus two hard-coded `delay(0.5)` in `tkCycle`.
   `WaitBeltParts` already guarantees a stopped, settled belt before any capture,
   so these are settling a belt that is already settled. That is the next
   0.5–1.0 s and it is a code change, not a tunable.

## Unchanged, and still wrong

Grip sensors: `gripPart` 0 of 96, `gripMag` 0 of 96, `dropPart` 72 of 96. Same
polarity/terminal problem as September — untouched by any of this work.
