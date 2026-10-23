# Raiv-T1 — belt batch tracking + monitor speed

**Seven files.** Controller `F_24_0064095_C_004`, application `binpick_TiePlates`.
Built against backup `Y-2026_M-09_D-08_14h19m`; every file in `_original/` is
byte-identical to what is on the controller now, `cmp`-verified.

| file | on controller | this build |
|---|---|---|
| `tkIOMonitor.pgx` | 5,605 | **9,577** |
| `tkBeltSensor.pgx` | 12,631 | **15,035** |
| `tkCycle.pgx` | 65,673 | **66,914** |
| `LogCycleCSV.pgx` | 15,830 | **23,789** |
| `binpick_TiePlates.dtx` | 49,238 | **51,777** |
| `interface/UserPageOptions.html` | 8,363 | **11,882** |
| `interface/UserPageOptions.bindings.json` | 3,019 | **4,238** |

No new program, no new task, no `.pjx` change. Reload the application.

---

## Part 1 — the speed problem, which is the bigger finding

`setMonitorSpeed()` is **not symmetric**. From the reference: it can always
*reduce* the monitor speed, but to *increase* it the robot must be in remote
working mode **and** the operator must have no access to the monitor speed —
restricted profile, or **MCP disconnected**.

`tkIOMonitor` has exactly two calls:

```
dDI100Speed  →  setMonitorSpeed(100)    an INCREASE — conditional
dDI25Speed   →  setMonitorSpeed(25)     a REDUCTION — always works
```

You've told me the pendant is **disconnected in production and connected while
testing new code.** So:

> **The 100% selector works in production and is silently refused during every
> pendant-connected test.**

That is the opposite of what anyone would guess, and it explains four runs.
Every run from 09-04 to 09-08 was a pendant-connected test run, and every one
sat at reduced override — descend 0.50–0.89 s against 0.37 s at full speed. My
advice in three reports was "confirm the override is at 100% before a production
run". Pressing that button during a test could never have done it. **To raise the
speed at the pendant, use the pendant's own speed control** — that access is
precisely what blocks the instruction.

### And nothing measured it

`getMonitorSpeed()` was called **nowhere in this project**. The cell had no idea
what speed it was running at, and neither did the log. `_nSpeed` is no
substitute: it is written unconditionally immediately *before* each call, so it
records what was **requested**, and it ships at 100 in the `.dtx` — it reads 100
from a cold boot at any actual speed.

Every speed figure in the workbook before this build is therefore an
**inference** from how long the 50 mm descend took. Sound inference, but the
workbook now labels it as one.

### What this build adds — all of it read-only

```
nMonitorSpeedActual = getMonitorSpeed()     one getter, per pass, in tkIOMonitor
```

- **CSV line H** gains `<monSpeed>`, `<monSpeedReq>`, `<speedRejects>`. The
  *pair* is the diagnosis: 25 next to 100 means the instruction was refused.
- **A severity-2 log line** when the 100 selector is on and the actual speed
  stays below it — latched per episode so a `delay(0)` loop can't spam it. This
  is the alarm that would have saved four runs.
- **A readout and a red `SPEED REFUSED` lamp** on the Options page, at (175,292)
  in verified-free space above the TestPipeline button.

**Neither `setMonitorSpeed` call is touched** — same arguments, same order, and
`verify.py` now fails if that ever changes (see below).

## Part 2 — belt batch tracking

Unchanged from what I built yesterday, except that line H grew three fields
before it ever shipped.

**One belt advance = one batch.** `tkBeltSensor` was already detecting the belt's
off→on edge for `nBeltRun_s`, and that edge *is* the batch boundary — so the
whole feature is one increment there, one stamp in `tkCycle`, and a running count
in `LogCycleCSV`.

`_nBatchAtPick` is stamped when APERA returns the trajectory — when the plate is
chosen — not at the end of the pick. The belt advances *during* a pick on 64% of
picks (that's the early kick), so an end-of-pick stamp would push the last pick of
every batch into the next batch's group.

```
RAIV/CSV,H,<seq>,<batchAtPick>,<batchNoNow>,<batchPicks>,<lastBatch>,<scanPlates>,
                 <monSpeed>,<monSpeedReq>,<speedRejects>
```

`<batchAtPick>` is the **join key** — group rows on it and the group size *is* the
batch size. A batch that gets no pick leaves a **gap** (14, 14, 16), and that gap
is the feed-starvation signal: a belt advance that delivered nothing pickable.
Run 6 lost ~150 s of 602 s to that.

Line H is now the per-pick **state** line — which batch, and what speed. Both are
properties of the pick rather than timings, which is why neither is on A or B.
Putting the speed fields here rather than on a ninth line cost ~15 bytes instead
of a whole `logMsg`: 8 lines per pick, 6.3 MB/day at full speed. Set
`nCsvCounterEvery=10` for a long run — it drops C and D and nets 4.9 MB/day,
still below what today's build writes.

**Line H must never be sampled.** `<batchAtPick>` is the grouping key; a missing
row makes its batch read one plate smaller.

## Deliberate decisions

**Nothing resets `nBeltBatchNo`** — not `ResetCycleStats`, not `init()`. It is a
join key, not a statistic; resetting it mid-session would silently merge two
different batches in every later analysis. Matches the sensor counters, which are
also left alone. It **saturates** at 16,000,000 rather than wrapping — merging is
visible, a wrap would scramble the grouping silently.

**`bSpeedNotApplied` does two jobs on purpose.** It is true for exactly as long as
an unresolved mismatch stands, which makes it both the log latch and the lamp.

**The warning message carries no percent sign** and is 189 bytes. `logMsg` caps at
255 and truncates *silently*; no other message in this project uses a `%`, and
format handling is not something I can test from here.

**`tkBeltSensor` is still an observer** — it reads `bOUTPUTS["Output3"]` and never
writes it. `verify.py` fails if that changes.

## One label was wrong, and is now fixed

Not code — documentation, but it was feeding a wrong conclusion. The workbook
described **`Cum picks` / `nPickLiftSeq`** as *"Picks since the application
started"*. It isn't: `tkCheckZone` only increments it inside
`if bBeltLiftArmed==true`, when the TCP clears `nBeltClearHeight_mm`. It's an
**early-belt-kick lift counter**. Run 4 reads 2, 3, 4, 5, 6, 6, 6, 7, 8 across
nine picks. The pick counter is `Seq` (`nCsvSeq`).

## Verification

`verify.py` — **PASS, 0 fail.** The 7 warnings are context files kept in the
check workspace so the belt-safety invariants still run; they are unchanged and
correctly **not** in this bundle.

**The most important thing this suite gained is a hole it didn't have:**
`setMonitorSpeed` was **missing from the MOTION token list**, so a speed call
could have been added, removed, retargeted or reordered and nothing would have
noticed — while "no motion, speed or descriptor change" is the standing promise
for every bundle. It's in now. `getMonitorSpeed` deliberately isn't: it's a pure
read, and the word boundary keeps the two apart.

New invariants — 10 for batch (§7g), 7 for speed (§7h):

| | |
|---|---|
| a | the two `setMonitorSpeed(_nSpeed)` calls are exactly the original two, unchanged and in order |
| b | `getMonitorSpeed` is read once, into `nMonitorSpeedActual`, in `tkIOMonitor` |
| c | `nMonitorSpeedActual` and `nSpeedRejects` have one writer each |
| d | the warning stays nested ifs — no `and`/`or`, since VAL3 doesn't promise short-circuiting — and **both** else arms clear the latch |
| e | the message has no `%` and stays inside the `logMsg` cap |
| f | line H's nine fields, in order |
| g | the FORMAT header documents them |

`mutate.py` — **32 injected defects, 32 caught, control clean.** Including:
changing a `setMonitorSpeed` argument, adding a third call, deleting one,
swapping the two selectors, collapsing the nested ifs into an `and`, dropping an
else arm so the lamp latches forever, putting a `%` back in the message, and
letting the touchscreen write `_nSpeed`.

### Two mistakes of my own, both worth recording

**Adding the warning tripped seven of my own checks at once.** Its message text
names `setMonitorSpeed` and `getMonitorSpeed` in prose, and the checks were
matching tokens in code that still contained string literals. A check a sentence
inside quotes can fool is not a check — so literals are now blanked wherever a
check is looking for code, and the allowlist comparisons still use whole lines,
so nothing is loosened.

**One check caught a mutation for the wrong reason.** The and/or ban used a
fixed 14-line window; when a mutation removed an `endIf` the window slid two
sections away and reported the failure against an unrelated `bOUTPUTS` line.
Caught, but with a message that would send the next person to the wrong place.
It is now bounded by the block's own nesting.

*(Also, the first run of `mutate.py` reported 0/32 caught. The harness copied the
tree but `verify.py` hard-codes `WORK` as an absolute path, so every mutant was
checked against the pristine originals. Fixed, and commented in `run()`.)*

### Not verified — nothing here compiles or runs

In the VAL3 IDE, confirm:

- the nine new `.dtx` globals resolve (`nBeltBatchNo`, `nBeltBatchPicks`,
  `nBeltBatchPicksLast`, `_nBatchAtPick`, `_nBatchNoSeen`,
  `nMonitorSpeedActual`, `nSpeedRejects`, `nSpeedWarnBelow`,
  `bSpeedNotApplied`)
- `getMonitorSpeed()` is callable from a non-motion task
- `toString("4.0", …)` accepts each line-H field — all nums, never a bool, since
  `toString` on a bool is a compile error and has broken this build twice
- the Options page renders both new blocks where you want them

## Test it

1. **Pendant connected, press the 100 selector.** Expect the Options page to show
   `monitor speed` below 100 with `req: 100`, the red **SPEED REFUSED** lamp lit,
   and one severity-2 line in the log. That is the fault reproducing on purpose.
2. **Raise the speed with the pendant's own control.** The lamp should clear and
   `monitor speed` should read 100.
3. **Disconnect the pendant and press 100.** It should apply, and `Speed applied`
   in the workbook should read `yes` for those picks.
4. **Run some picks.** `batch #` climbs by one per belt advance; `picks` counts
   within a batch and resets when the belt advances.
5. **Let the feeder run dry.** A gap appears in `<batchAtPick>` — `Batch gap` ≥ 2
   in the workbook.

## Parser and workbook

`parse_backups.py` parses all nine line-H fields, plus derived `batch_size`,
`batch_pick_index`, `batch_gap`, `batch_advanced_in_pick` and `speed_applied`.
Regression-tested against all 209 existing rows: **zero value changes**, new
columns blank. Also tested against synthetic line-H logs covering a two-pick
batch, a skipped batch, a mid-pick advance, and a refused-then-applied speed
change — all read correctly.

The workbook has the **Belt batch** (AZ–BI), **Belt run by stop trigger**
(BJ–BK) and **Monitor speed** (BL–BO) column groups, with Header Key rows for
every one. Phase Budget block 5's speed column now reads the **measured**
override where line H carries one and `inferred N.Nx` where it doesn't — every
run to date reads "inferred", which makes the first run with real instrumentation
obvious at a glance.

## Back out

Copy the seven files from `_original/` back over the application. They are the
`14h19m` versions, byte for byte. The `.dtx` revert removes all nine new globals,
so revert it **with** the four `.pgx` files, never alone.
