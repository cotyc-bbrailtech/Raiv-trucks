# Raiv-T1 — the dwell sweep, and a number that reframes the whole week

Controller `F_24_0064095_C_004` · backup `Y-2026_M-09_D-09_09h13m`
Two new runs, **328 picks**. My 09-09 code is not deployed; this is the `14h19m` build.

---

## The sweep worked, and it is measured per pick

You edited the three dwells at runtime, and lines E and F caught every one of
them. Three clean blocks in run 8 — **295 picks in 27 minutes at full speed,
zero errors, zero warnings.**

| on / settle / off | picks | total dwell | median cycle | plates/min |
|---|---|---|---|---|
| 0.50 / 0.35 / 0.50 | 155 | 1.35 s | **4.88 s** | 12.3 |
| 0.50 / **0.00** / 0.50 | 54 | 1.00 s | **4.54 s** | 13.2 |
| **0.25** / 0.00 / **0.25** | 86 | 0.50 s | **4.29 s** | **14.0** |

**0.59 s a pick, 12% of the cycle.** The middle block's spread is the tightest
this cell has ever produced — standard deviation 0.19 s over 54 consecutive picks.

## But only half of the second step reached the cycle, and that is the useful bit

| step | dwell removed | cycle saved | pass-through |
|---|---|---|---|
| settle → 0 | 0.35 s | 0.34 s | **97%** |
| both magnets halved | 0.50 s | 0.25 s | **50%** |

The missing 0.25 s is fully accounted for:

- **magnet-ON** 0.50 → 0.25 came off cleanly. −0.25 s.
- **magnet-OFF** 0.50 → 0.25 bought **nothing**. `AperaPartsFound` went
  0.00 → **0.11 s** and vision wait 0.73 → **0.88 s**.

The release dwell had been **free cover for the APERA round-trip.** Shorten it
and vision simply becomes the constraint instead. So:

> **`nEMH_offDelay` is spent. Going below 0.25 s will not buy cycle time — it
> only hands the time to the vision pipeline.** `nEMH_onDelay` is the one that
> still pays, and `nGripSettle` is finished at 0 (`delay(0)` still yields a
> scheduler tick; there is nothing left under it).

That reverses my own ranking. I had the magnet dwells as one 1.35 s target;
they are actually three knobs with completely different economics.

## The number that reframes the week: 09-03 was never at 100%

Run 8's first block ran the **original** dwells — 0.50 / 0.35 / 0.50, same code
build as 09-03. Pure speed comparison:

| median s | 09-03 "full speed" | 09-09 run 8 | |
|---|---|---|---|
| cycle | 5.91 | **4.88** | 17% faster |
| approach | 1.00 | **0.60** | 40% |
| linear approach | 0.62 | **0.47** | 24% |
| retreat | 1.74 | **1.26** | 28% |
| descend | 0.37 | **0.31** | 16% |

Every motion segment is faster, the dwells are identical. **The 5.91 s I have
been calling full speed was at less than 100% override.** With `_nSpeed` = 100
and the pendant off, this is the first run that plausibly reached it — which is
exactly what yesterday's `setMonitorSpeed` finding predicts, and it is why the
instrumentation in the undeployed bundle matters.

So the cell's real capability is **4.88 s at the shipped dwells, 4.29 s at the
swept ones** — not 5.91 s. Every figure I have quoted this week was low.

---

## What this run does NOT show, and it is the thing the sweep was for

**No plate was demonstrably picked.** Across all 295 cycles:

| counter | value for the whole run |
|---|---|
| beam break edges | **0** |
| sensor stops / camera stops | **0 / 0** |
| branch-B passes | **0** |
| FoV end hits | **0** |
| early captures | **0** |
| `plates_found` | **3 on 294 of 295 picks** |

The belt never moved once and the detector saw the same three plates throughout.
Compare run 7 the previous afternoon — 33 picks, 76 break edges, 23 sensor stops,
8 camera stops, branch-B firing — which is what a real feed looks like in this log.

If 295 plates had actually been lifted and placed, the field of view would have
emptied and the belt would have had to advance hundreds of times. **The log
cannot distinguish 295 successful picks from 295 cycles that went through the
motions.** `bDryCycle` is false and the coil was pulsed, so the dwells were real
— but whether the magnet *made*, *held* and *broke* is not in this data.

Which means the bench-test question — *does 0.25 s make the magnet against a
steel tie plate, does 0.25 s break it* — is **still open.** The timing result is
solid. The safety result does not exist yet.

I am flagging this hard because of what it would cost to get wrong, and because
of one more thing:

> **Application data was saved from SP2 before this backup, so these are no
> longer runtime edits.** The `.dtx` now boots at on 0.25 / settle 0 / off 0.25.
> The swept values are the cell's persistent defaults until someone changes them
> back.

## The instrument that closes it is already on the machine

`dDIemh_Gripper_PartAvailable` — **Term 2, %I6** — is declared in the `.dtx` and
read by **nothing but one lamp on the Options page.** No VAL3 code touches it.
Same for `dDIemh_Gripper_MagnetizationStatus` (%I4). The gripper has told this
cell whether it is holding a plate, on every pick, for as long as it has been
running, and nobody has ever listened.

Log part-available per pick and every future dwell sweep verifies itself: grip
confirmed or not, 86 rows, no interpretation needed. It is two fields on line H
in the bundle that is already sitting in your folder undeployed — I can add them
before you upload it. Say the word.

A cheap physical check in the meantime: run the 0.25/0/0.25 setting with the
belt actually feeding for 50 picks and watch the drop station. If the count of
plates arriving matches the pick count, the dwells are fine.

---

## Also worth knowing

- **Run 7** (09-08 14:30–16:14, 33 picks) is a genuine feed run and reads
  healthy: 23 sensor stops, 8 camera stops, no errors. Reduced override
  (descend 0.89) — pendant connected, per yesterday's finding.
- **Four app stop/starts** during run 8, and `nCsvSeq` ran 1 → 295 straight
  through all of them. A program stop/start does **not** reinitialise
  application data — only a full reload does. Both edit methods worked: the
  08:44 change was made live in the data editor, the 08:50 one across a restart.
- `nEMH_gripperDelay` still reads 0.5 in the saved `.dtx`, confirming it is dead
  and unreferenced exactly as documented.

## Workbook

`Raiv-T1_CycleMetrics_F_24_0064095_C_004.xlsx` is updated: **537 picks across
nine runs**, a new **Phase Budget block 5b** for the sweep with the
pass-through arithmetic and the caveat above, and runs 7 and 8 in the per-run
table.

One structural fix while I was in there: the sheet's row ranges were **hard-coded
literals** — `36:103` for the full-speed block and a table of row pairs per run.
Those were correct until a backup added picks, at which point every one of them
would have pointed at the wrong rows silently. They are now derived from the data,
with an assertion that the full-speed block is still exactly 68 rows. This backup
is what would have broken them.

## Where I would go next

1. **Validate the grip.** Either log part-available (two fields, I can add them
   now) or run 50 picks with the belt feeding and count plates at the drop
   station. Nothing else on this list matters until the 0.25 s dwells are known
   to be safe — and they are the boot defaults now.
2. **Confirm what run 8 actually was.** If plates *were* being picked and
   replaced by hand, say so and I will treat 4.29 s as a validated capability
   figure rather than a bench number.
3. **Re-measure branch-B at true full speed.** It was 0 in run 8, so the 0.63 s
   amortised cost still comes from the slower 09-03 run and is probably
   understated as a fraction of a 4.3 s cycle.
4. **Stop shortening `nEMH_offDelay`.** It is at the point where vision, not the
   coil, sets the pace.
