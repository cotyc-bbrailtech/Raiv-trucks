# AbortMessageLatch_Fix — 2026-08-31

One file: `Init.pgx`. Adds two lines. Unblocks every metric you just spent two days
building the plumbing for.

## What the 08/31 backup shows

The retain fix worked — `RaivLog` loads clean, no memory error, no invalid library. But
the metrics it is meant to store are currently meaningless:

| | |
|---|---|
| RunSec | 304.397 s |
| **FaultSec** | **304.397 s** |
| ProdSec / BeltSec / StarveSec / AcceptSec / RejectSec / VisionSec / OtherSec | **all 0** |
| Clean cycles | **0** |
| Interrupted | 49 |
| LRC p10 / best / mean | 0 / 0 / `--` |
| Plates | 50, all accepted, all 14in |
| Actual | 6.088 s/plate, 591 pl/hr vs target 2.965 / 1214 |

`RunSec == FaultSec` exactly. **Every sampled instant of that run was charged to FAULT**,
so the loss budget is a single bar, and LRC cannot compute at all — a plate-to-plate
interval only counts as clean if no loss bucket moved during it, and the fault bucket
moved continuously.

The cell was not faulted. It made 50 good plates at a peak TCP of 2011 mm/s.

## Root cause: `bMessage["abort"]` is latched true

Traced through the deployed source:

- `tkAbort.pgx:38` sets `bMessage["abort"]=true` **inside** the `do…until` loop that
  blinks the lamps and waits for the operator to choose Continue-Cycle or Stow.
- `tkAbort.pgx:47` clears it on the line *after* that loop.
- **Nothing else ever clears it** — not `Init.pgx`, not `start.pgx`, not
  `TaskCommand.pgx`, not `KillAllTasks.pgx`, not `stop.pgx`.

So if the Abort task is killed while parked in that loop — application stop,
`KillAllTasks()`, `taskKill("Abort")` — the flag stays true. And because dtx values are
written back to disk, **it survives restarts**. The 08/31 backup has it saved as `true`
with `bERROR["schunk"]=false`, `bRunning["Abort"]=false`, `bAbort["Abort"]=false`,
`bTskSelected["Abort"]=false` — no abort anywhere, just the message flag stuck on.

`tkMetrics` precedence rule 1 is `bERROR["schunk"] or bMessage["abort"] or
bRunning["Abort"]` → FAULT, and FAULT outranks everything. Hence 100%.

This is pre-existing, not from any of this week's changes. It was invisible until the
metrics existed to expose it — which is the metrics work doing its job on day one.

## Second effect, worth watching

`tkMonitor_IO` guards two task-selection transitions on `bMessage["abort"]==true`:

- line 50 — **RESUME FROM ABORT** (`bTskSelect["cycle"]` … `and bMessage["abort"]==true`)
- line 73 — **STOW SELECT**

A stale latch arms both on a cell that is not in abort. So pressing Cycle could take the
resume-from-abort branch instead of the normal select branch. Clearing the flag restores
the intended gating; after the fix, confirm Cycle and Abort/Stow still select normally
from a cold start.

## The fix

```
bMessage["abort"]=false
bMessage["Feeder"]=false
```

added to `Init.pgx` alongside the other ~50 flags it already zeroes.

**Safe by ordering:** `tkAbort` calls `Init()` at line 33, *before* it raises the flag at
line 38. So this reset can never stomp a live "waiting for command" state — it only clears
a latch left over from a previous run.

`bMessage["Feeder"]` is included for consistency. It is self-healing (tkPartFinder sets and
clears it every detector pass) so it is not a bug, but it was the other un-reset key in the
same collection and it costs nothing.

## Merge steps

1. Copy `Init.pgx` into `usr/usrapp/LAB_PlateSorter2/`.
2. Reload. Programs only changed, but reload anyway.
3. **Before running, check the data editor: `bMessage["abort"]` must read false.** If it is
   still true, the saved dtx value is being loaded over the Init reset — clear it by hand
   once, save the application, then restart.

## Verification

1. Run a cycle. `_sM["State"]` must show `RUNNING`, not `FAULT`.
2. On the LRC page the loss budget must spread across the buckets instead of putting
   everything in Fault. **`Bother` (unattributed) should be near zero** — that is
   tkMetrics' own self-test on the partition; if it is large the budget is missing a state.
3. `CleanCt` must start climbing and `LRC p10` must produce a number once you have 10 clean
   cycles. Until this fix, that could never happen.
4. Cold start, then press Cycle, then Abort/Stow — confirm normal selection behaviour per
   the tkMonitor_IO note above.

## Still open: does retain reach a backup?

`RaivLog:sLine` is empty in this backup, which is **expected** — `bLogRetain` is still
false, so nothing has been written to the ring yet.

But `RaivLog:nRunId` reads 0, and it should not. `bLogEnable` is true and `RunSec` reached
304 s against `nLogPeriodSec` 300, so the log trigger fired at least once, and firing
increments `nRunId`. Meanwhile ordinary app data *did* make it into this backup — `_nM` and
`_sM` are saved with real values. So file write-back works for normal dtx data, and the
question is whether retained data goes somewhere a backup does not reach.

**One check settles it.** In the data editor, live, read `RaivLog:nRunId` and check the
pendant LOGGER for `RAIV/CSV` blocks:

| Live `nRunId` | LOGGER has `RAIV/CSV` | Meaning |
|---|---|---|
| ≥ 1 | yes | Retain works in memory but **does not reach a backup** → retain fails the requirement, go to the socket option |
| 0 | yes | The increment is not landing — my bug, send me the value and I will fix it |
| 0 | no | Trigger never fired; the run was shorter in tracking time than it looked |

Do the Init fix first though. Right now every number the log would store reads FAULT.
