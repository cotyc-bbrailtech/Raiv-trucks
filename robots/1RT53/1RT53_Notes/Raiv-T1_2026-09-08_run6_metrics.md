# Raiv-T1 — the 14h19m backup: 52 new picks, and the sensor's first real test

Controller `F_24_0064095_C_004` · backup `Y-2026_M-09_D-08_14h19m`
Three sessions: 10 picks 11:07–11:27, **19 picks 11:32–11:42**, **33 picks 13:53–14:03**.

---

## The fix is on, and the build is clean

`HMI/uOptions.pgx` on the controller is **7,063 bytes, byte-identical to the file
I shipped**. Every other file is at its shipped size. The `.dtx` is byte-identical
too, which tells you something useful: nobody has saved application data from
SP2, so **`bBeltSensorStop` is still `false` at every reload** — the sensor's
belt-stop authority has to be switched on from the Options page each session.
More on that below, because it turns out to be the key to reading this run.

All the self-checks hold across all 52 new picks:

| check | result |
|---|---|
| all seven CSV lines present | **52 / 52** |
| line A retreat = line E retreat | **52 / 52** |
| `SegGripperActuate` = its two parts | **0.0000 s exactly**, every row |
| `SegPlaceReturn` = its six parts | max residual **0.010 s** (rounding) |
| unaccounted time, median | **0.02 s** (run 5) / **0.03 s** (run 6) |

And run 6 had **zero APERA image-capture errors**, against five in the 11:07
session. That storm was transient.

---

## First, the thing that governs everything else: the speed override

**Run 6 ran at reduced override end to end.** `descend` reads **0.89 s on all 33
picks** (sd 0.0017) against **0.37 s** at full speed, and the three dwells sit at
0.50 / 0.35 / 0.50 exactly, as they always do — that pairing is the override
fingerprint.

| median, s | 09-03 blk B (full) | 09-03 blk C (reduced) | **09-08 run 6** |
|---|---|---|---|
| cycle | **5.91** | 13.16 | **13.88** |
| approach | 1.00 | 4.18 | 3.17 |
| linear approach | 0.62 | 1.42 | 1.29 |
| retreat | 1.74 | 5.01 | 4.79 |
| descend | 0.37 | 0.89 | **0.89** |

Run 6 is the same regime as 09-03 block C, and essentially the same cycle time.
**So no cycle-time conclusion from this run is comparable with 5.91 s.** Four
picks in run 5 (seq 16–19) did briefly go full speed — `descend` 0.31 s — and
one of them came in at **6.76 s**. That is the only full-speed evidence on 09-08
and it is consistent with where we were.

The cell has still never been measured at full speed with the sensor enabled.
That is the single most valuable missing run.

---

## The sensor: the beam move worked

This is the finding, and it is a clean one.

| | 09-04 (before the move) | run 5 | **run 6** |
|---|---|---|---|
| sensor stops | 7 | 15 | 11 |
| **agreed** (confirm found a plate) | 3 | 11 | **10** |
| **disagreed** | 4 | 3 | **1** |
| agreement | **43%** | 79% | **91%** |
| chatter | 0 | 0 | **0** |
| timeouts | 0 | 1 | 3 |

Post-move across both runs: **21 of 26 stops confirmed a plate — 81%, against
43% before.** One further stop was neither (confirm skipped, arm still in the
conveyor FoV — the guard doing its job).

### And the mechanism is confirmed, not just the outcome

I said on 09-04 that the beam was upstream of where plates come to rest, and that
the tell was the **dwell** — how long a plate keeps the beam broken. Every sensor
stop in run 6, with its dwell:

| dwell (s) | 0.15 | 0.24 | 3.99 | 3.99 | 4.70 | 6.48 | 9.32 | 9.72 | 9.78 | 11.86 | 11.93 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| outcome | **disagree** | agree | agree | agree | agree | agree | agree | agree | agree | agree | agree |

**The single disagreement is the single sub-0.2 s dwell.** Ten of eleven stops
left the plate **parked on the beam** (`beam at end` = 1, dwell measured in
seconds); the one that failed is the one where the plate crossed and kept going.
On 09-04 five of ten dwells were 0.03–0.43 s and the two worst disagreements sat
at 0.03 s and 0.06 s.

So the dwell predicts the outcome, the beam is now where plates stop, and the
residual 9% is the occasional plate that still slips past. That is exactly the
result the move was supposed to produce.

### Why the run looks like two different runs

Picks 1–20 were stopped by the **camera**; picks 21–33 by the **sensor**. Nothing
about the plates changed at 13:59:40 — **`bBeltSensorStop` was switched on**.
It ships `false`, it is not persisted in the `.dtx`, and the only control for it
is the button on the Options page. So the belt was camera-driven for the first 20
picks whether or not the sensor was seeing anything, and the short flicker dwells
in that stretch (0.03–0.66 s) are just plates streaming past an unarmed beam.

**Which is also the best evidence available that the magnet fix works.** Someone
was demonstrably sitting on the Options page mid-cycle to press that button, and
**13 consecutive picks then completed normally** — 11.77, 13.05, 13.00, 13.08,
12.55, 12.99 s and so on, the tightest block in the whole run. Under the code
that was on the controller yesterday, every one of those picks would have had its
grip pulse cancelled by the page. No `manual magnet button IGNORED` line appears,
so the blocking path itself was never exercised; that still wants the deliberate
test in the README.

## Belt-run time: still no advantage, third run running

Attributed by which counter incremented, so it is apples to apples:

| | run 6 sensor | run 6 camera | 09-04 sensor | 09-04 camera |
|---|---|---|---|---|
| n | 11 | 10 | 7 | 2 |
| median belt run | **1.82 s** | **1.66 s** | 1.73 s | 1.88 s |

And cycle time says the same: 12.99 s median over the sensor-driven block against
12.12 s over the camera-driven one. **The photo-eye is now reliable, and it still
buys no measurable time.** Three runs have said that. I think the honest reading
is that belt-run time was the wrong thing to sell it on — the camera loop is
simply fast when a plate is arriving. Its value is in the cases the camera cannot
cover at all, which brings us to the next point.

## The feeder, not the cell, was the constraint

Three 15 s sensor timeouts (14:01:31, 14:02:13, 14:03:32) and one in run 5. Every
one handed back to the camera correctly and every one was right — the belt was
empty. Plus run 6 seq 7: a **95.9 s belt run** and a **99.4 s cycle**, with the
sensor still disabled, the camera poll burning its whole retry budget on an empty
belt.

Those four events are ~150 s of the 602 s run. At reduced override the cell wants
a plate every ~13 s and it was not getting one.

## Other things worth a note

- **Branch-B fired on 9 of 33 picks (27%)** in run 6 and 4 of 19 in run 5, against
  18% on 09-03. Still the largest non-dwell target and still needs no bench test.
- **Early capture fired on 21 of 33 picks (64%)**, up from 13% — but that is
  mostly the override. At reduced speed APERA always finishes first, so
  `vision wait` reads 0.01 s median and there is nothing left to hide.
- **`nFovHitStart` = 0 again**, 33 for 33. The gate the early trigger is built on
  continues to hold; it is only ever the drop-station cube.
- Three motion outliers with no error beside them: retreat **19.92 s** (seq 12,
  and `TCP lift` reads 0 on that pick), retreat **14.78 s** (seq 21), approach
  **64.34 s** (run 5 seq 12). All three are single picks; flagging, not chasing.
- The negative `TCP lift` values from the 11:07 session (−180, −137 mm) do **not**
  recur. All 52 new picks read +76/+77. That was the capture-error stretch.

---

## Workbook updated

`Raiv-T1_CycleMetrics_F_24_0064095_C_004.xlsx` is on the OneDrive with the new
data in it:

- **Cycle Data** now 209 picks across 7 runs (was 147 across 4), rows 3–211
- **Backup History** carries the two 09-08 backups
- **Phase Budget / Summary** "all runs" ranges retargeted to row 211. The
  **"Full-speed mean" columns were deliberately left pointing at rows 36–103** —
  folding a reduced-override run into a full-speed statistic would corrupt it
- a footnote on Cycle Data now carries the override warning, so nobody reads
  13.88 s as a regression against 5.91 s
- Header Key untouched, including the expanded phase descriptions

Every formula was recalculated and checked: no errors, and the two residual
columns still read 0.000 (gripper) and ≤0.010 (place) on all 188 rows that carry
the splits.

---

## What I would do next, in order

1. **A full-speed run with the sensor enabled.** Confirm the override is at 100%
   before you start. Everything on 09-08 was reduced-speed, so we still have no
   idea what the sensor does to a 5.9 s cycle.
2. **Decide what to do about `bBeltSensorStop` not persisting.** Either save
   application data from SP2 once, or — now that it has earned it at 81% — I can
   flip its shipped default to `true` in the `.dtx`. One value, no code. Your call;
   it changes what the cell does on a cold reload, so I am not doing it unasked.
3. **Put the disagreement warning back**, with the dwell in the line. This run
   just proved dwell predicts the outcome, so that one log line would let the next
   run diagnose its own geometry instead of needing this analysis. Top of my list,
   and still my outstanding item from last week.
4. **Feed.** Two feeder-empty events in eleven minutes. Whatever the sensor does
   to belt timing is second order next to the belt having nothing on it.
5. **Branch-B**, 27% of picks. Unchanged as the best cycle-time target that needs
   no bench test.
