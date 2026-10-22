# Raiv-T1 — the 2026-09-03 run, and what the split now shows

Controller `F_24_0064095_C_004` · backup `Y-2026_M-09_D-03_13h31m`
100 picks, 12:06 → 12:43, real production feed

---

## Deployment verified, and the instrumentation checks out

All seven files are on the controller at exactly the sizes I shipped —
`tkCycle` 65,673 · `.dtx` 45,917 · `tGripperEMH` 5,106 · `Part_Accept` 8,526 ·
`Part_Reject` 5,417 · `ResetCycleStats` 8,332 · `LogCycleCSV` 12,026. It
compiled and it ran.

The self-checks I built in all pass on all 102 rows:

| check | result |
|---|---|
| `SegPlaceReturn` = its six parts | max residual **0.010 s** (pure rounding) |
| `SegGripperActuate` = its two parts | **0.000 s**, exactly, every row |
| line A retreat = line E retreat | **yes**, 102/102 |
| all six CSV lines present | **123/123** rows across all three runs |

So the numbers below are trustworthy. **Unaccounted time is 0.03 s on a normal
cycle** — every second of a clean pick is now in a named segment.

## First, a parser bug this backup exposed

`nCsvSeq` is an ordinary global, so a **full reload restarts it at 1** — and the
controller log is cumulative, so one backup holds several runs. Keying rows on
`(backup, seq)` silently **merged** them, last writer winning. This backup first
read as 102 rows in which the first 17 carried the previous run's timestamps
next to the new run's numbers, and the previous run's 17 cycles had vanished.

Fixed: a run boundary is a seq that decreases, and there is now a `run` column.
The same backup now yields **123 rows across 3 runs** — 17 (09-02 staging), 4
(09-03 09:31, pre-deploy) and 100 (09-03 12:06, this one). Parser is updated on
your OneDrive and re-run; 14 of 15 backups parse.

---

## The run had three different speeds, and that is most of what you see

Before any conclusion about performance: **the robot did not run at one speed.**
Three blocks, separated by the two long stalls:

| median, seconds | A: seq 1–10 | **B: seq 13–80** | C: seq 82–102 | C ÷ B |
|---|---|---|---|---|
| **cycle** | 28.84 | **5.91** | 13.16 | 2.23× |
| approach | 9.29 | **1.00** | 4.18 | 4.16× |
| linear approach | 3.08 | **0.62** | 1.42 | 2.27× |
| retreat + drop approach | 11.72 | **1.74** | 5.01 | 2.88× |
| descend (50 mm `movel`) | 2.05 | **0.37** | 0.89 | 2.41× |
| — | | | | |
| magnet ON | 0.50 | **0.50** | 0.50 | **1.00×** |
| grip settle | 0.35 | **0.35** | 0.35 | **1.00×** |
| magnet OFF | 0.50 | **0.50** | 0.50 | **1.00×** |

**Every motion segment scaled. Not one dwell moved — standard deviation exactly
0.0000 across all 102 cycles and all three blocks.** That is a speed-override
change and nothing else. A different plate type or a heavier load could not
stretch a bare 50 mm `movel` by 2.4× while leaving three `delay()` calls
untouched.

Roughly: block B is full speed, block C ran at about **30–40%** override, block
A at about **10–20%**. I won't be more precise than that — how a move scales
depends on whether it is velocity- or acceleration-limited, and these are mixed.

**And both long stalls sit exactly on a transition.** The 625 s gap is seq 10,
between blocks A and B; the 149 s gap is seq 81, between B and C. Neither has a
single log line in it. That reads as someone at the pendant: stop, change the
override, restart. If that wasn't you, it's worth knowing what it was — but
nothing in the code or the log suggests a fault, and there are no errors in the
window at all.

**So the performance number for this run is block B: 5.91 s median over 68
consecutive picks = 10.2 PPM.** On the 56 picks with no branch-B pass it is
**5.69 s = 10.6 PPM**, best **4.18 s**. The 145-pick snapshot's 1000-window best
was 4.09 s, so the cell's demonstrated capability hasn't moved — this is the
first time we've seen it *sustained* over 68 cycles of real production feed
rather than 3 cycles of staged plates.

---

## What the place+return split actually found

This is what edit 2 was for, and the answer is clean. At full speed:

| inside place+return | s | % of place |
|---|---|---|
| **magnet OFF dwell** | **0.50** | **57%** |
| descend (50 mm) | 0.37 | 42% |
| trajectory capture | **0.00** | 0% |
| drop-station interlock | **0.00** | 0% |
| `AperaPartsFound` vision | **0.00** | 0% |
| return (retract + queues) | **0.00** | 0% |
| total | 0.88 | |

**Three of my four hypotheses were wrong, and it's worth saying so plainly:**

- **The `dDIDropClear` interlock costs nothing. 0.00 s on all 102 cycles.** The
  drop station is never the constraint. I had it as a live suspect.
- **The second vision round-trip costs nothing.** `AperaPartsFound` reads 0.00.
  I called it "a second hidden vision cost" — it isn't a cost at all.
- **The trajectory capture in `Part_Accept` costs nothing.** 0.00 on every
  cycle. The at-place capture is already effectively free, which also means
  there is no capture latency for the early trigger to save.
- **What was right:** the magnet-off dwell. It is 57% of the window, and it was
  invisible before.

So place+return went from 2.13 s of mystery to **0.88 s of which 0.50 is one
`delay()`**. The reason it looked like 46% of the cycle before is edit 3 —
1.74 s of retreat and drop-approach motion was being counted inside it.

## And `SegRetreat` was hiding a third of the cycle

It read **0.00 on every cycle** for the last week. It now reads **1.74 s — the
single largest segment, 29% of the cycle.** That is the fix earning its keep: a
third of the cycle was being attributed to the wrong place, which is why every
estimate I gave you about where the time went was skewed.

Where 5.91 s goes now:

| segment | s | % |
|---|---|---|
| retreat + drop approach | 1.74 | 29% |
| approach | 1.00 | 17% |
| place (descend + release) | 0.88 | 15% |
| gripper (ON + settle) | 0.85 | 14% |
| linear approach | 0.62 | 10% |
| vision wait | 0.41 | 7% |
| unaccounted | 0.03 | 1% |
| **branch-B, amortised** | **0.68** | **11%** |

**Total fixed dwell is 1.35 s = 23% of the cycle**, in three buckets now, each
dead constant. Edit 1's target is confirmed as the largest single non-motion
cost. Nothing has changed about the bench test — I still need the two magnet
thresholds before I touch those numbers.

---

## Two other things the run settled

**The branch-B feed loop is bigger than I measured before.** It fired on **12 of
68 full-speed picks (18%)**, and a pass costs **3.8 s** — median cycle 9.52 s
with one against 5.69 s without. Amortised that is **0.68 s per pick, 11% of the
cycle.** I previously measured 7% of picks from the staging run and dropped it
as minor; at 18% of picks in production it is the **second-largest target after
the dwell**, and unlike the dwell it needs no bench test. Worth revisiting.

**The early trigger works, and it fully hides the vision wait when it fires.**
It went 3.4% of picks (5/145) to **13% (13/100)** now that the belt kick is on:
14 kicks armed, 13 fired, no APERA errors. On the 5 full-speed picks where it
fired, **vision wait was 0.00 s**; on the other 63 it was 0.41 s. That is direct
evidence for the ranked edit 4 — trigger on *every* pick, not just last-part —
worth about 7% of the cycle. (Note block C's vision wait is also 0.01 s: at 35%
override the motion is slow enough that APERA always finishes first. The 0.41 s
is a real serial cost only at full speed, which is where it matters.)

Also: `nFovHitStart` = 0, `nFovHitEnd` = 39/100. Still only ever the
drop-station cube, never the conveyor camera — the gate we built the early
trigger on continues to hold.

One minor thing: *"belt scan — arm still in conveyor FoV after 3 s"* fired 5
times, **all of them in block A**, where the retreat alone takes 11.7 s so
`nFovClearTimeout_s` = 3 could never be enough. At full speed it never fires. No
action needed, but if you expect to run at low override for long stretches that
timeout wants raising.

---

## Where I'd go next

1. **Branch-B, 18% of picks × 3.8 s.** No bench test, no motion change, and it
   is now measured properly rather than inferred from a staging run. This is the
   one I'd pick up first.
2. **The magnet dwells, 1.35 s = 23%.** Ready to wire the moment you have the
   two thresholds. Still the biggest single number.
3. **Early trigger on every pick, ~0.41 s = 7%.** Now backed by 13 successful
   fires with the vision wait measured at zero on each.
4. **Not the motion descriptors.** Motion is 3.36 s of the 5.91 s cycle, so it
   is where the time is — but the run just demonstrated that the cell is
   override-sensitive across the board, and the first useful thing is simply to
   **confirm the override is at 100% for a production run**. Block C cost 7.25 s
   a pick against block B for no reason visible in the code.

One housekeeping note: the log is now six lines per pick. If you're going to run
a long batch, set **`nCsvCounterEvery` = 10** first — it drops the volume below
what the old four-line build wrote, and loses nothing, because lines C and D are
cumulative counters.
