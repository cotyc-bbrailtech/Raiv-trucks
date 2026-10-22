# Raiv-T1 — run 19: steel plates, belt feeding

Backup `Y-2026_M-09_D-11_11h53m`. **309 picks, 10:46:40 → 11:20:57.**
The full stall-sampler bundle is deployed and compiled — all three program
bodies in the backup are byte-identical to what I shipped (SP2 re-serialised
the `<Locals>` blocks alphabetically; the code is unchanged).

**This is the first run whose cycle time is a real pick rate.** Everything
before it was rubber plates on a static staging area.

---

## 1. Read the log twice — the first read was missing a third of the run

`mnt/log/user.log` had rolled at 10:53:34. The parser only reads `user.log`, so
the 10:42–10:53 block — including the dwell change — was sitting unread in
`user.old`. I pulled it in as a second source. **334 picks today, not 245.**

Worth fixing in the parser: read `user.old` too, oldest first.

## 2. What actually ran

| block | dwells on/settle/off | Capture @ FoV | n | clean median |
|---|---|---|--:|--:|
| 09:00 (rubber, tail of run 18) | 0.25 / 0 / 0.25 | ON | 121 | **3.88** |
| 10:42–10:44 steel | 0.25 / 0 / 0.25 | off | 9 | 4.22 |
| 10:46–10:59 steel | **0.5 / 0 / 0.5** | off | 132 | **4.47** |
| 11:02–11:20 steel | **0.5 / 0 / 0.5** | **ON** + sampler | 176 | **4.42** |

"Clean" = cycles under 6 s. Section 4 is about the rest.

The dwells went back to 0.5/0.5 at 10:46. That is **+0.50 s a pick** and it is
the single largest regression against the 3.88 baseline.

## 3. Capture @ FoV is worth nothing on steel — I was wrong to expect it to carry over

| | FoV off | FoV ON | delta |
|---|--:|--:|--:|
| cycle (clean, mean) | 4.490 | 4.424 | **−0.066 s, p = 0.18** |
| vision wait | 0.46 | 0.05 | −0.41 |
| **approach** | **0.64** | **0.94** | **+0.30** |

On rubber this was −0.34 s a pick, replicated twice. On steel with the belt it
is **−0.07 s and not statistically significant** (permutation test, 112 vs 136
picks). The vision wait still collapses exactly as designed — 0.46 → 0.05 — but
**every bit of it reappears in the approach.**

That is a mechanism, not noise. Firing the capture early means
`apera_wait_for_trajectory` returns while the arm is still flying to the drop.
The `movej(jTrajectoryStart, mReach)` that used to overlap the wait now has
nowhere to hide, and `seg_approach` — measured from the end of the wait —
absorbs it. On rubber the trajectories were shorter (3 plates in frame, median)
and the arm got there first. On steel the scene holds 5 and the trajectories
are longer, so the arm is the constraint and moving the capture earlier buys
nothing.

**Recommendation: run steel production with Capture @ FoV OFF.** It is not
paying for itself here, and it is the one change that takes a camera image with
the robot in motion. Keep the toggle — it is free when off — but there is no
case for carrying the risk for 0.07 s inside the noise.

The geometry is still sound: `mismatch` **0 on all 176 samples**, `exit_x` 848,
`vel_x` 709 mm/s, `cap_fov_decline` 2, no APERA errors. The measurement is
good; the thing it measured just does not help on steel.

## 4. The real cost is the re-scan, and it is new

23% of picks in the last block ran over 6 s. Their segments are all normal —
the time is **unaccounted**, i.e. in the belt/parts-check tail after `_nTimer`
is reset at `tkCycle` L755, which nothing times.

| | |
|---|--:|
| re-scan picks | **47 of 309 — one every ~4 picks** |
| cost, median | **3.87 s** (mean 4.45, max 9.18) |
| total | 3.5 min of 27.5 min = **13% of the run** |
| **amortised** | **+0.68 s on every pick** |

One in four or five picks empties the scene, and the cell then pays ~4 s to
advance the belt, settle, re-trigger and re-wait. That is now a bigger lever
than anything left in the motion path, and **none of it is instrumented** —
`plates_found` is logged before the `apera_inspect` that decides the branch, so
the log cannot even say which of the three exits was taken.

## 5. Standstill: 33% of the cycle, and half of it is the dwells

Sampler on, clean picks: **4 stalls, 1.45 s a pick standing still (33% of
4.42 s).** On rubber with the shorter dwells it was 0.70 s (18%).

The +0.75 s is mostly the dwells — the arm is stopped for the whole of
`nEMH_onDelay` and `nEMH_offDelay`, and those went up by 0.50 s. That is a
clean consistency check on the sampler, and it says the dwells are **pure dead
time**, not overlapped with anything.

`mon_loop_ms` median **1.0 ms**, worst per pick 2.2 ms → the stall counts are
measurements, not floor values. `nMonLoopMax_ms` reads 260 ms, but it jumped
across the 98-second program pause at 11:10:28 — it is the pause, not
production. **Two instrumentation flaws of mine:** `nStallMax_s` (45.9 s, then
80.7 s) and `nMonLoopMax_ms` are both sticky maxima that idle time poisons.
They should reset per run.

## 6. The grip sensors did not answer the question they were added for

**`nGripPartAtPick` and `nGripMagAtPick` read 0 on all 245 logged steel picks**
— every one of which picked a plate and dropped it.

Both are wired (`Term_2 %I6` and `%I4`) and %I6 is not dead: `nGripPartAtDrop`,
the same input read after release, reads **1 on 29 picks (12%)**. So the line
toggles — it just never asserts when a plate is actually held.

That is polarity or terminal mapping, not dwell timing. **Until it is sorted,
`grip_ok` cannot validate the dwells**, which was the whole point of raising
them. Worth ten minutes on the pendant I/O page: hold a plate on the magnet by
hand and watch %I6 and %I4.

## 7. The belt instrumentation, on the other hand, works

First run where any of it could do anything.

| | |
|---|--:|
| batches | 32 → 80 (48 advances) |
| beam-break edges | 84 → 448 |
| laser-sensor belt stops | 11 |
| camera belt stops | 1 |
| **sensor agree / disagree / chatter** | **11 / 0 / 0** |
| sensor timeouts | 2 |
| **`cap_early` — early trajectory trigger** | **12 — first time ever non-zero** |

The laser sensor stopped the belt 11 times and the camera confirmed the plate
count every time, with no disagreement and no chatter. Two timeouts fell back
to the camera poll and logged it. The early-trigger path fired 12 times.

One pre-existing diagnostic is loud: **`nFovHitEnd` = 79** — "capture with arm
inside the END (drop station) FoV cube", 56 times this run. The taught
`jApera_Trigger_pos` appears to sit inside the drop-station cube. `nFovHitStart`
is 0.

Also: at 10:44 the 100 selector was on while `getMonitorSpeed()` read 75 — the
warning fired and `speed_rejects` latched 1. Production from 10:46:40 ran at
**100**, so the numbers above are at full speed.

## 8. Where the cycle stands

| | s |
|---|--:|
| rubber, short dwells, FoV on (run 18) | 3.88 |
| **steel, belt, as run today (clean picks)** | **4.42** |
| **steel, belt, amortised over re-scans** | **~5.1** |
| actual throughput, last block | **9.7 picks/min** |

Nothing regressed. Steel plus a live belt is simply a harder problem than the
static rubber test, and it costs about 0.5 s of dwell, 0.2 s of approach and
0.7 s of amortised re-scan.

## 9. What I would do next, in order

1. **Get %I6 / %I4 right.** Without them no dwell number is defensible, and
   0.50 s a pick is sitting on that question.
2. **Then sweep the dwells back down on steel** — 0.5 → 0.4 → 0.3 → 0.25,
   watching `grip_part_at_pick` once it reads 1. Up to −0.50 s a pick.
3. **Instrument the re-scan tail.** Time `tkCycle` L757–1140 and log
   `nCountPlatesFound` *after* the L769 inspect, so the three exits can be told
   apart. +0.68 s a pick is currently invisible.
4. **Turn Capture @ FoV off** for steel production.
5. Fix the two sticky maxima, and teach the parser to read `user.old`.

The `getMoveId()` change at `tkCycle` L282 is still on the table but it is now
the smallest item on this list — the sampler says the outbound standstills are
a fraction of the 1.45 s, and the dwells and the re-scan are both larger and
neither needs the motion path touched.
