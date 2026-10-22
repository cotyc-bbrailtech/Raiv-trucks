# Raiv-T1 — belt batch tracking

**Six files.** Controller `F_24_0064095_C_004`, application `binpick_TiePlates`.
Built against backup `Y-2026_M-09_D-08_14h19m` — every original in `_original/`
is byte-identical to what is on the controller now, verified with `cmp`.

| file | 14h19m | this build |
|---|---|---|
| `tkBeltSensor.pgx` | 12,631 | **15,035** |
| `tkCycle.pgx` | 65,673 | **66,914** |
| `LogCycleCSV.pgx` | 15,830 | **21,430** |
| `binpick_TiePlates.dtx` | 49,238 | **50,487** |
| `interface/UserPageOptions.html` | 8,363 | **10,622** |
| `interface/UserPageOptions.bindings.json` | 3,019 | **3,707** |

No new program, no new task, no `.pjx` change. Reload the application.

---

## What a "batch" is

**One belt advance = one batch of plates.** That boundary already existed in the
code; nothing new had to be invented to find it. `tkBeltSensor` was already
detecting the belt's off→on edge to start the `nBeltRun_s` clock, and that edge
*is* the batch boundary.

So the whole feature is four numbers:

```
tkBeltSensor   nBeltBatchNo        +1 on the belt off->on edge  (the batch number)
tkCycle        _nBatchAtPick       = nBeltBatchNo, stamped when APERA returns
                                     this pick's trajectory
LogCycleCSV    nBeltBatchPicks     picks in the current batch
               nBeltBatchPicksLast picks in the last completed batch
```

**`_nBatchAtPick` is stamped at the TOP of the pick, and that matters.** The belt
can advance *during* a pick — that is exactly what the early kick is for, and it
fires on 64% of picks at the moment. Stamping at the end of the pick would push
the last pick of every batch into the *next* batch's group whenever the kick
fired, which is most of them. Stamping when the trajectory comes back means the
pick is attributed to the batch the plate actually came from.

## Where the numbers show up

### CSV log — new line H

```
RAIV/CSV,H,<seq>,<batchAtPick>,<batchNoNow>,<batchPicks>,<lastBatch>,<scanPlates>
```

`<batchAtPick>` is **the join key**. Group log rows on it and the size of the
group *is* the batch size. No single row can know its own batch size — a batch
is not finished until the next advance — so don't try to read it off one row.

Two fields earn their place beyond the obvious:

- **`<batchNoNow>`** is the batch number at the instant the line was written.
  When it is ahead of `<batchAtPick>`, the belt advanced mid-pick. The rate of
  that across a run is a direct measure of how much feed time the early kick is
  hiding under the place move.
- **`<scanPlates>`** is what the belt scan's own confirm detect counted. Compare
  it with the eventual group size: the scan says what **arrived**, the group says
  what got **picked**, and the difference is plates the pipeline couldn't use.

**A batch that gets no pick leaves a gap** in the sequence — 14, 14, 16 — and
that gap is the most useful number here. It means the belt advanced and delivered
nothing pickable. The 09-08 run had two feeder-empty events costing ~150 s of
602 s; this is the metric that would have counted them without needing an
analysis.

Line H is **not** gated by `nCsvCounterEvery`, unlike C and D. Those are
cumulative counters, so sampling them loses nothing; `<batchAtPick>` is per-pick
attribution, and a sampled row makes its batch read one plate smaller than it
was. Cost: 8 log lines per pick instead of 7 — 6.3 MB/day at the 5.91 s cycle,
against 5.5. If that matters for a long run, `nCsvCounterEvery=10` drops C and D
and nets 6.2 lines average / 4.9 MB/day, still below what today's build writes.

### Options page — a "Belt Batch" block

Four read-only readouts at (15, 436), below the TestPipeline button:

```
Belt Batch (per advance)
  batch #:  147     picks:  2
  last:       3     found:  3
```

`batch #` = advances this session, `picks` = picks in the current batch,
`last` = the last completed batch's size (the current one isn't knowable yet),
`found` = `nScanPlates`.

**Layout is untested — I can't render a VAL3 page from here.** I placed it in
verified-free space: `btn1` ends at y=430, `btnCycleStats` starts at y=505, and
`btn2` starts at x=207, so (15,436)–(200,494) collides with nothing. If it looks
wrong on the pendant, move the eight elements in the SP2 page editor; the ids are
`lblBeltBatch`, `lblBatchNo`/`txtBatchNo`, `lblBatchPicks`/`txtBatchPicks`,
`lblBatchLast`/`txtBatchLast`, `lblBatchScan`/`txtBatchScan`.

## Deliberate design decisions worth knowing

**Nothing resets `nBeltBatchNo` — not `ResetCycleStats`, not `init()`.** It is an
identity, not a statistic. Resetting it mid-session would not lose a number, it
would silently *merge two different batches into one group* in every later
analysis. This matches the existing sensor counters, which `ResetCycleStats`
also leaves alone. A full application reload re-initialises it from the `.dtx`,
and the parser handles that the same way it handles `nCsvSeq` restarting — batch
grouping is keyed on `(backup, run, batch #)`, never on the batch number alone.

**It saturates at 16,000,000 rather than wrapping.** VAL3 `num` is single
precision, so integers are exact only to 2^24 and past that `+1` is a no-op.
Saturation merges batches, which is visible; a wrap would make batch 3 appear
twice in one log and scramble the grouping silently. Merging beats scrambling.
Neither happens in practice — at one advance per pick that's ~17k/day against a
16.7M ceiling, and the app reloads daily.

**`tkBeltSensor` is still an observer.** It reads `bOUTPUTS["Output3"]` and never
writes it. The belt has exactly three writers and adding a fourth that runs on
its own clock is the defect that had to be fixed in `tkCycle` in Sep 2026.
`verify.py` fails if that ever changes.

## One label was wrong, and is now fixed

Not a code change — a documentation one, but worth flagging because it was
feeding a wrong conclusion. The workbook's Header Key described **`Cum picks` /
`nPickLiftSeq`** as *"Picks since the application started"*. It isn't.
`tkCheckZone` increments it only inside `if bBeltLiftArmed==true`, when the TCP
clears `nBeltClearHeight_mm` — it is an **early-belt-kick lift counter** and it
lags the pick count whenever `bEarlyBeltKick` is off or the lift isn't seen. You
can see it in the data: run 4 reads 2, 3, 4, 5, 6, 6, 6, 7, 8 across nine picks.

The pick counter is `Seq` (`nCsvSeq`), which `LogCycleCSV` increments once per
pick. The numbers in that column were always right; the sentence explaining them
wasn't. Corrected in the Header Key, and noted in `LogCycleCSV`'s history block.

## Verification

`verify.py` — **PASS, 0 fail.** The 8 warnings are context files (`tkBeltScan`,
`tkCheckZone`, `monitoring`, `init`, `.pjx` and friends) that I kept in the check
workspace so the belt-safety invariants could still run; they are unchanged and
correctly **not** in this bundle.

Ten new checks for this feature, in section 7g:

| # | invariant |
|---|---|
| a | `nBeltBatchNo` has exactly one writer, in `tkBeltSensor`, and it is the `+1` |
| b | that increment sits inside the saturation guard, inside the belt off→on edge block that already existed |
| c | `_nBatchAtPick` written once in `tkCycle` from `nBeltBatchNo`; read only by `LogCycleCSV` |
| d | it is stamped **before** the APPROACH move — drifting below it silently changes the metric's meaning |
| e | line H's nesting depth equals line G's, so it can never end up sampled |
| f | the batch-edge block is exactly its four statements; the increment is outside it and happens once |
| g | line H carries exactly six fields in the documented order |
| h | the FORMAT header documents line H |

Plus the existing suite extended: the HMI write-ban list now covers all four
batch globals and `nScanPlates`, and the `.pjx` check now accepts "no delta" as a
pass for a bundle that adds no program (with a byte comparison behind it so a
lost BOM still fails).

**`mutate.py` — 19 injected defects, 19 caught, control clean.** Worth naming the
ones that would otherwise have shipped silently: moving the increment out of the
belt edge, sampling line H with `nCsvCounterEvery`, stamping the batch from the
wrong source, a second writer in `tkBeltScan`, and a click event that lets the
touchscreen zero the batch number.

*(The first run of `mutate.py` reported 0/19 caught. The harness was copying the
tree but `verify.py` hard-codes `WORK` as an absolute path, so every mutant was
being checked against the pristine originals. Fixed, and the fix is commented in
`run()` — a mutation suite that reports everything caught by accident is worse
than none.)*

### What is NOT verified

Nothing here can be compiled or run. In the VAL3 IDE, confirm:

- the five new `.dtx` globals resolve (`nBeltBatchNo`, `nBeltBatchPicks`,
  `nBeltBatchPicksLast`, `_nBatchAtPick`, `_nBatchNoSeen`)
- `toString("4.0", ...)` accepts these nums — every line-H field is a num, never
  a bool, because `toString` on a bool is a compile error and has broken this
  build twice
- the Options page renders with the new block where you want it

## Test it

1. **Run a few picks.** `batch #` on the Options page should climb by one every
   time the belt moves, and `picks` should count up within a batch and reset to 1
   when the belt advances again.
2. **Grep the log** for `RAIV/CSV,H` and check `<batchAtPick>` repeats for picks
   in the same batch.
3. **Let the feeder run dry.** You should see a gap in `<batchAtPick>` — the belt
   advanced, nothing pickable arrived. That is `batch_gap` ≥ 2 in the workbook.
4. **With `bEarlyBeltKick` on**, `<batchNoNow>` should be ahead of
   `<batchAtPick>` on a good fraction of picks. That is the kick overlapping the
   feed with the place move.

## Parser and workbook

`parse_backups.py` on the OneDrive is updated: line H parsed, `has_batch` flag,
and the derived grouping — `batch_size`, `batch_pick_index`, `batch_gap`,
`batch_advanced_in_pick`. Regression-tested against all 209 existing rows:
**zero value changes** on every pre-existing column, ten new columns blank.
Also tested against a synthetic line-H log covering a two-pick batch, a skipped
batch (gap 2) and a mid-pick advance — all three read correctly.

`Raiv-T1_CycleMetrics_F_24_0064095_C_004.xlsx` has a new **Belt batch** column
group (AZ–BI) and ten Header Key rows. Appended at the end deliberately: Summary
and Phase Budget address Cycle Data by column letter and every letter they use is
unchanged, so their numbers are byte-for-byte what they were (full-speed mean
6.73 s, 209 picks, residuals 0.000 / ≤0.010). Every existing row reads
`Has batch` = no with the batch columns blank, which is correct rather than
missing data.

## Back out

Copy the six files from `_original/` back over the application. They are the
`14h19m` versions, byte for byte. The `.dtx` revert removes the five new globals,
so revert it **with** the three `.pgx` files, never on its own.
