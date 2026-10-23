# Phase Budget — audit and rebuild

`Raiv-T1_CycleMetrics_F_24_0064095_C_004.xlsx`, 2026-09-08

You were right, and it was worse than outdated. Three separate problems.

---

## 1. Wrong, not just stale

The **Retreat** row's description read:

> *MEASURES THE MOTION QUEUE, NOT THE MOTION — movej only queues and returns.
> The real retreat is inside place+return.*

That was the pre-2026-09-03 defect, and we fixed it that day. The cell beside
that sentence reads **1.72 s — the largest phase in the cycle, 29% of it**.
Anyone reading the sheet as written would have discounted the biggest number on
it. That's the one that would have cost you a decision.

Three more in the same class:

- **Place+return** still called itself an *"opaque composite"* containing the
  retreat and drop approach. Neither has been true since the split — that motion
  is in the Retreat row now, and rows 19–24 broke the rest out.
- **Gripper dwell** named `nEMH_gripperDelay` and *"tkCycle's hard-coded
  delay(0.35)"*. Both retired on 09-03 — and rows 31–33 of the **same sheet**
  already said `nEMH_onDelay` / `nGripSettle`. The sheet disagreed with itself.
- The **magnet callout** compared itself against *"place+return at 2.13 s"*, the
  pre-split figure, while the cell above it read **0.94 s**.

## 2. Self-contradictory

The unaccounted row computed **12.7%** of the cycle. The note beside it asserted
**99.6% coverage — "every second is in a named phase"**. Both were true, of
different things, and the sheet said which of neither.

The resolution turns out to be the most useful thing on the sheet, so it now has
its own block: **unaccounted time is the branch-B feed loop.**

| | clean picks | branch-B picks |
|---|---|---|
| picks | 56 of 68 | 12 of 68 |
| mean unaccounted | **0.22 s** | **3.81 s** |
| median unaccounted, all 68 | **0.03 s** | |

0.03 s median is the 99.6% claim, and it holds — it's a statement about a typical
pick. The 12.7% is the feed loop, which runs *between* picks and so falls outside
every named phase. Amortised: **0.63 s a pick, 11% of the cycle.** Nothing was
missing from the instrumentation; the time was real and unlabelled.

## 3. Incomplete — and misleading where it was complete

The "whole-run mean / best / worst" columns spanned rows 3:211: **seven runs,
four code builds, three speed regimes and two pendant stalls.** What they
reported:

- **"Best retreat: 0.00 s"** — that's the *pre-fix build* where the timer was
  broken. Twenty rows of it.
- **"Worst cycle: 648.32 s"** — the 625-second pendant stall at run 2 seq 10.
- Worst approach 64.34 s, worst linear approach 82.98 s, worst place+return
  97.30 s — all stalls.

None of those is a performance figure. Meanwhile **86 picks of laser-sensor work
across runs 3–6 appeared nowhere on the sheet**, the twenty sensor and batch
columns had no representation at all, and a superseded 25-cycle controller
snapshot held three columns of the main table.

---

## What it looks like now

Eight blocks, every figure a live formula against Cycle Data:

1. **Phase budget, full-speed block** — median beside mean, percentages off the
   median, plus a clean-pick column
2. **Where the unaccounted time goes** — the branch-B block above
3. **Inside the phases** — the 09-03 split, with both self-checks
4. **Fixed magnet dwell** — 1.35 s, 23% of the median cycle, and how to sweep it
5. **Per-run view** — all seven runs, each with its speed read off Descend
6. **Belt end laser sensor** — per run, with agreement and belt-run comparison
7. **Belt batch** — per run, reading `-` until the batch build runs
8. **Superseded snapshot** — moved to the bottom and labelled

**Median added beside every mean, and the percentages moved onto the median.**
The means here have long right tails — one branch-B pass moves a mean and not a
median — and the old sheet was taking percentages off one. Median cycle 5.91 s,
mean 6.73 s, and the 0.82 s between them is block 2.

Block 5 replaces the whole-run columns. It keeps the runs separate and derives
each one's speed from **Descend** — a bare 50 mm `movel`, so it scales with the
override while the three dwells don't. That column now shows a **ratio to full
speed** rather than an asserted percentage: 1.0× in run 2, 1.35× in run 3, 2.4×
in runs 4–6. It's a ratio and not an override percentage on purpose — how a move
scales depends on whether it's velocity- or acceleration-limited, and these are
mixed.

Block 6 has one number worth calling out. Agreement is now **agree ÷ (agree +
disagree)** — 43% in run 3, **91% in run 6** after the beam moved. That's the
clearest result the sensor programme has produced. Belt run sensor-vs-camera sits
right beside it: 1.73/1.88 then, 1.82/1.66 now. Reliable, and still no time saved.

## Two things I had to fix in my own rebuild

Worth saying, because both are the same class of error I just criticised.

**I broke Summary.** Its "Fixed magnet dwell" cell pointed at `'Phase
Budget'!B34`, which was the old total row. The rebuild moved that total to B46,
so both that cell and the share-of-cycle cell below it read **0**. Repointed —
and the Phase Budget anchors are now located by *label* in the build script, not
by remembered row number, so the next rebuild can't do it again.

**My first draft subtracted medians.** The median column computed Phase sum and
Unaccounted by summing and subtracting the medians above them, which gave
"unaccounted median 0.395 s" against a true 0.03 s. Medians aren't additive.
Both now read the median of Cycle Data's own per-row column, with a note that
they consequently don't close on the median cycle — the mean column does, to
0.000. Two smaller ones: a mislabelled "Median cycle" row that was actually
`AVERAGEIF`, and a batch count using `MAX−MIN+1`, which counts the span
including empty advances rather than the batches.

## Also updated

**Summary's narrative was stale on the same axis** — "cycle time settles at
4.66 s" (three cycles of a staged run), "place+return was 2.13 s", "magnet dwell
29%", "99.6% on 16 of 17 cycles", branch-B at the 09-03 rate, and the sensor
described as "phase 1 run 09-04". Eight findings and the ranked-edit list are
rewritten against the current 209 picks, with the shipped items marked. Two
headline rows added: branch-B amortised cost, and the median cycle beside the
mean.

**Two new Cycle Data columns** — `Belt run - sensor s` and `Belt run - camera s`
(BJ, BK) — so block 6's comparison is a live `MEDIAN` down a column instead of a
number I computed once and pasted in. Which trigger ended a belt run is only
knowable from *which cumulative counter moved on that row*, so it had to be done
in `parse_backups.py`; regression-tested at zero value changes across all 209
existing rows. Both columns are documented on Header Key.

Every formula in the workbook recalculated: **0 errors on all eight sheets**, and
the two split residuals still read 0.000 (gripper, exactly, on all 188 rows that
have it) and ≤0.010 (place, rounding).
