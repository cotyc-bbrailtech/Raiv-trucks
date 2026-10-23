# Raiv-T1 — what the two backups show, and edits for tomorrow

Controller `F_24_0064095_C_004` · analysed September 2, 2026
Backups: `Y-2026_M-09_D-02_17h43m` (before upload) and `17h48m` (after the short run)

---

## First, a correction: I was wrong about globals and backups

I have said repeatedly this session — and baked it into `LogCycleCSV.pgx`'s
header and the last README — that **ordinary VAL3 globals do not survive into a
backup**. That is **wrong**, and the `17h43m` backup proves it.

That `.dtx` came back at **53,654 bytes** against the 39,377 I shipped, and
every counter is in it with a live value:

| | |
|---|---|
| `nPickLiftSeq` | **145** (picks) |
| `nCapAtPlace` | **140** |
| `nCapEarly` | **5** |
| `nCapAtTrigPos` | **0** |
| `nCapDeferred` | **4** |
| `nBranchBPasses` | **10** |
| `nFovHitEnd` | **15** |
| `nFovHitStart` | **0** |
| `nScanHeartbeat` | **49,036** |
| `nTCP_beltLift_mm` | **76.468** |
| `bEarlyBeltKick` | **true** |

`<Value>` elements went 280 → 775. So **saving the application data from SP2
writes every live global into the `.dtx`**, and a backup taken afterwards
carries them. That was available the whole time and I did not know it. The
counters I asked you to read off the pendant were sitting in the backups.

**What this changes:** the `.dtx` gives you a *point-in-time snapshot*; the CSV
logging gives you the *per-cycle time series*. Both are worth having — the
snapshot is free and needs no code, the series is what shows a trend. I have
corrected the reasoning in the code comment.

**One real cost, worth knowing before you save data again:** the save
**stripped all 17 of my `.dtx` comments** (17 → 0) — the notes on why
`mNomSpeed` sits at defaults, the socket protocol, the counter semantics. It
**preserved every `.pgx` comment** (tkCycle 519, tkBeltScan 249, both exact).
So: **documentation belongs in the `.pgx` files, never in the `.dtx`.** I will
move the important `.dtx` notes into program headers.

The `.pgx` files came back with `<Local>` declarations re-sorted alphabetically
and some loop bodies re-indented — cosmetic normalisation, no content change,
verified by code-only diff. But note the side effect: **file size is no longer
a reliable build fingerprint** after SP2 has re-saved. I will identify builds by
content from now on.

## Deployment verified

All five files of `CycleDataLogging` are on the controller at exactly the sizes
I shipped: `LogCycleCSV.pgx` 4,439 · `tkCycle.pgx` 49,585 ·
`Part_Accept.pgx` 5,962 · `.dtx` 41,340 · `.pjx` 1,954.

The logging works. 68 lines = **17 complete cycles**, all four lines present for
every one, format exactly as designed:

```
RAIV/CSV,A,     1,15.31,3.96,1.43,0.85,0
RAIV/CSV,B,     1,6.26,2.8 ,     0,     3,1
RAIV/CSV,C,     1,     0,     2,     0,     0
RAIV/CSV,D,     1,     0,     0,     0,     2,  76
```

`cycles_ALL.csv` on your OneDrive now has 17 rows, `complete = yes` on all of
them.

## The numbers

Cycle time falls through the run and settles hard:

```
15.31  10.28  7.31  7.28  7.08  5.58  5.35  4.74  4.91  4.88
 5.08   4.86  4.87  4.66  4.66  4.66  7.07
```

**Steady state is 4.66 s — three consecutive cycles — which is 12.9 PPM.**
(Cycle 17's 7.07 s is a vision outlier, see below.) The 145-pick `.dtx`
snapshot agrees: 100-window average 6.51 s, best **4.09 s**.

**The instrumentation accounts for 99.6% of the cycle.** Unaccounted is
0.01–0.03 s on 16 of 17 cycles. There is no hidden dwell — every second is in a
named segment. That kills the "3 s unaccounted" idea I floated; it was an
artifact of my synthetic test, not real.

Where 4.66 s actually goes (cycles 14–16):

| segment | s | % | what it is |
|---|---|---|---|
| **place+return** | **2.13** | **46%** | opaque composite — see below |
| gripper | **0.85** | **18%** | pure dwell, zero variance |
| approach | 0.60 | 13% | motion |
| vision wait | 0.59 | 13% | APERA trajectory query |
| linear approach | 0.48 | 10% | motion |
| retreat | 0.00 | 0% | **not measured** |
| unaccounted | 0.01 | 0% | |

Three things fall straight out of that:

**1. `gripper` is 0.85 s on every single cycle, to the centisecond.** Zero
variance across 17 cycles confirms it is pure fixed dwell with no motion in it:
`nEMH_gripperDelay` (0.5) + `tkCycle`'s hard-coded `delay(0.35)`.

**2. The magnet-OFF dwell is another 0.5 s, hidden inside place+return.** So
**total magnet dwell is 1.35 s of a 4.66 s cycle — 29%.** That is the largest
single cost in the cycle and it involves no motion, no path and no acceleration.

**3. `retreat` reads 0.00 and is misleading.** `apera_follow_trajectory` only
*queues* its `movej` calls and returns, and there is no `waitEndMove()` after
it, so that timer measures queue time, not motion. The real retreat motion is
inside place+return. Anyone reading the Cycle Timing page today would conclude
the retreat is free. It isn't; it's just unmeasured.

**Two more, from the counters:**

- **The early trigger fired 0 times in this run** (`cap_early` stayed 0 across
  all 17 cycles; all 17 captures were `at_place`). It only fires on a last-part
  kick, and with plates properly on the belt `bLastPart` was never true. In the
  145-pick snapshot it fired 5 of 145. **So the feature we spent yesterday on is
  reaching ~3% of picks.**
- **The branch-B feed loop is minor.** `nBranchBPasses` = 10 in 145 picks (7%),
  and in the 17-cycle run it incremented exactly once — on cycle 2, which is the
  *only* cycle with meaningful unaccounted time (3.03 s). So a branch-B pass
  costs ~3 s and is invisible to the segment timers. Good to have measured, and
  it confirms dropping that proposal was right.
- `nFovHitStart` = 0, `nFovHitEnd` = 15/145. Same as before: only ever the
  drop-station cube, never the conveyor camera.

## Edits for tomorrow, ranked

### 1. Make both magnet dwells tunable, then sweep them — 29% of the cycle

The single biggest, safest target. No path change, no acceleration change, so it
cannot throw a plate.

- `nEMH_gripperDelay` = 0.5 is **one number used for both the ON and the OFF
  pulse** (`tGripperEMH.pgx`). Grip and release almost certainly do not need the
  same time. **Split it into `nEMH_onDelay` / `nEMH_offDelay`** so they can be
  tuned independently.
- `tkCycle`'s `delay(0.35)` after the gripper arms is **hard-coded**. Make it a
  public `nGripSettle` so it can be swept from the data editor without a reload.

If 0.5 → 0.25 on both and 0.35 → 0.15, that is 0.70 s off a 4.66 s cycle —
**15% faster**, and the segment timers will confirm it immediately.

**This is gated on a bench test** (below). I am not going to guess how long an
electromagnet needs to make and break while it is holding a steel tie plate.

### 2. Split `place+return` into sub-segments — pure instrumentation, zero risk

46% of the cycle is one opaque number. Reading the code, it contains: the
retreat motion completing, the drop approach, `waitEndMove()`, the
`dDIDropClear` interlock wait, the 50 mm descent, the 0.5 s magnet-OFF dwell,
the retract, an **`AperaPartsFound()` vision round-trip** (which is *not* in the
vision-wait segment — a second hidden vision cost), and the move to
`jTrajectoryStart`.

Splitting it tells us whether the 2.13 s is mostly the dwell, mostly the
interlock, or mostly that extra vision call. Right now we are guessing. This is
the highest-information edit available and it changes no behaviour.

### 3. Retire or fix `SegRetreat`

It reads 0.00 because it measures a motion queue, not motion. Either fold it
into the split above or drop it — leaving a timer that reads zero on a segment
that clearly takes time is worse than having no timer.

### 4. Consider extending the early trigger to every pick

`cap_early` = 0/17 here and 5/145 in the snapshot. The trigger only runs when
`tkBeltScan` runs, which only happens on a last-part kick. But the trajectory
could be triggered on **every** pick, right after the plate clears the conveyor
FOV (`_bStartFoV` going false) — the belt is stopped and the scene static on a
normal pick, so nothing is moving. That would hide the 0.59 s vision wait (and
the 3 s outliers on cycles 1 and 17) behind the place motion on all picks
instead of 3% of them. Worth **13–20%**.

Higher risk than 1–3: it is the moving-robot capture, and it needs the same
`_bStartFoV`-only gate we proved. It did work 5 of 5 when it fired, with no
APERA error. I would do this **after** 1–3, on its own, so it can be judged
alone.

### Not doing

- **`mNomSpeed` accel/decel.** Still gated on the magnet hold margin, and now
  clearly not where the time is — the motion segments (approach 0.60, linear
  0.48) total ~1.1 s against 1.35 s of pure dwell. Dwell first.
- **Branch-B feed logic.** 7% of picks, and I over-read it from a staging run.

## The bench test that gates edit 1

With a plate gripped and the arm parked, at the pendant:

1. How short can the **grip** pulse go before pickup becomes unreliable? Step
   `nEMH_gripperDelay` down from 0.5 → 0.4 → 0.3 → 0.2 and pick 10 plates at
   each. Watch for a plate that doesn't come, or comes and slips.
2. How short can the **release** pulse go before a plate stays stuck to the
   magnet? Same steps, watch for a plate that doesn't drop or drops late.
3. Separately, how much of the 0.35 s settle is needed? That one is about the
   plate stopping swinging on the magnet, not the coil — watch the first
   centimetres of the retreat for the plate shifting.

Report the two thresholds and I will wire them in with margin. If the answer is
"0.5 s is genuinely needed for both", then edit 1 is off the table and edits 2–4
are where the remaining time is.

## One housekeeping note

Four log lines per pick at ~4.7 s is roughly **4 MB/day** — considerably more
than the 1.4 MB/day I estimated at 14 s cycles. Worth checking the CS9's
`user.log` rotation size before a long run, so the CSV doesn't evict the
diagnostics it's meant to sit alongside. If it does, the fix is to emit lines C
and D every Nth cycle; the counters are cumulative so they lose nothing by being
sampled.
