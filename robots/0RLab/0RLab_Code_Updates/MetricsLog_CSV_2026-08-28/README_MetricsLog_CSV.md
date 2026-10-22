# MetricsLog_CSV — 2026-08-28  (option 1)

Writes the cycle-optimization metrics to the CS9 system log as CSV, so a run survives a
restart. Closes the gap found in `MetricsAudit_2026-08-28.md`: until now nothing in the
application persisted a single metric anywhere.

Based on the deployed `LAB_PlateSorter2.zip` you uploaded — i.e. on top of
`BeltKickSeq_Fix` and the HMI toggle, not the original project.

## What's in this folder

| File | Change |
|---|---|
| `LogMetrics.pgx` | **NEW.** Emits one CSV sample as 4 lines, `D1`..`D4` |
| `LogMetricsHdr.pgx` | **NEW.** Emits the matching column headers, `H1`..`H4`, once per run |
| `tkMetrics.pgx` | Emits a sample every `nLogPeriodSec`; emits one more **just before RESET zeroes the counters** |
| `stop.pgx` | Emits a final sample before `Init()` / `KillAllTasks()` tear the run down |
| `LAB_PlateSorter2.dtx` | Adds `bLogEnable` (public bool, **default true**) and `nLogPeriodSec` (public num, **default 300** s) |
| `LAB_PlateSorter2.pjx` | Registers the two new programs — **required, or they will not load** |

## How it works

`tkMetrics` accumulates as before. Every `nLogPeriodSec` it calls `LogMetricsHdr()` once
per application run, then `LogMetrics()`, which emits four `logMsg()` lines:

```
RAIV/CSV,H1,runmin,plates,act_spc,act_pph,tgt_spc,gap_spc,lrc_p10,lrc_best,lrc_mean,clean_ct,int_ct,clean_pct,state
RAIV/CSV,D1,  12.5, 253,  2.980, 1208,  2.965,  0.015,  3.02,  2.81,  2.95, 201,  52, 79.4,RUNNING
RAIV/CSV,D2,...   loss budget, ms/plate: prod, belt, starve, accept, reject, vision, fault, other + batch/belt stats
RAIV/CSV,D3,...   all 16 phase means
RAIV/CSV,D4,...   counts by part type, accept %, camera, TCP peak, still/move %
```

To pull a run out of an exported controller log:

```
grep "RAIV/CSV" <exported log>
```

Three sample points, so a run is never lost:

1. **Every `nLogPeriodSec`** (default 5 min → 4 lines per sample, 48 lines/hour).
2. **Immediately before RESET** — `ResetMetrics()` discards all 85 accumulators with no
   way back. The run being thrown away is emitted first, so a press of RESET can no
   longer silently destroy a shift of evidence.
3. **On application stop** — before `Init()` and `KillAllTasks()`.

## Why it's safe

- **`tkMetrics` stays a pure observer.** The only addition is `logMsg()`. No motion, no
  physical output, no variable another program reads. `LogMetrics()` is equally inert and
  is therefore safe to call from `stop()`.
- **Nothing is recomputed.** The logger reads `_sM[]` — the strings `tkScreenHmi` already
  derives for the pendant. So the log cannot disagree with what the operator saw, and the
  p10 histogram bin, the per-plate loss maths and the phase means are not duplicated in a
  second place to drift out of step. All 54 keys used are confirmed produced.
- **Period clamped 30..3600 s in code**, the same defence `nMetricPeriod` already has. Four
  lines per sample, so a mistyped `0` would flood the log and push everything else out of it.
- **`bLogEnable` is public and defaults true**, and is deliberately **not** written by
  `Init.pgx`, so an abort/resume cannot silently switch logging off.
- Header and data blocks verified **field-for-field**: H1/D1 13, H2/D2 11, H3/D3 16,
  H4/D4 14. Worst-case assembled line ~139 chars, well inside the VAL3 string limit.
- All six files parse as well-formed XML; every identifier is declared in the `.dtx` or as
  a program local; BOM and line endings match this project's convention (checked, after
  the `interface/` BOM mistake earlier today).

## Reading the data

Fields are the pendant's own formatted strings, so they are **space padded** and read
**`--`** wherever a figure is not yet defined (fewer than 10 clean cycles for p10, no
plates yet for the per-plate buckets). Import with `skipinitialspace` and treat `--` as
null — a zero there would be a lie.

## Merge steps

1. Back up the current project.
2. Copy all six files into `usr/usrapp/LAB_PlateSorter2/`, overwriting the four existing ones.
3. Full application reload — the `.dtx` and `.pjx` both changed.
4. Confirm in the data editor: `bLogEnable = true`, `nLogPeriodSec = 300`.

## Verification steps

1. Start the application and run a cycle. Within 5 minutes the LOGGER page (Info tab)
   should show an `H1..H4` block followed by a `D1..D4` block.
2. Cross-check one sample against the LRC page on the pendant at the same moment — the
   numbers must be identical, since both read `_sM[]`.
3. Press **RESET** on the LRC page. A `D1..D4` block must appear immediately *before* the
   `RAIV/Metrics reset` line, holding the pre-reset figures.
4. Stop the application. A final `D1..D4` block must appear.
5. Set `nLogPeriodSec` to `0` in the data editor. Logging must continue at 30 s, not flood.
6. Untick `bLogEnable`. Lines stop; metrics keep accumulating on the pendant.
7. Take a controller backup and confirm `grep "RAIV/CSV"` finds the lines in the export.
   **This is the step that proves the whole thing** — if the lines are not in the backup,
   the CS9 log retention is shorter than we need and option 2 becomes urgent.

## On to option 2

Two things still needed for a real file on the controller, neither of which I can see from
the project files:

1. Whether the CS9's I/O configuration exposes a **disk/file `sio` resource**. Every `sio`
   in this project links to `Socket\...` (the Apera TCP connection). If you can open the
   controller's I/O configuration and tell me whether a `Disk\` or `File\` resource exists —
   or can be created — that answers it.
2. The exact VAL3 file-write calls for **s8.15.1cs9_BS3177** (the version in your `.pjx`).
   I would rather read it out of the reference manual for that build than guess; if you
   have the SRS help or the VAL3 reference PDF for it, the `sio`/file section is all I need.

Once those two are known, option 2 is a small change: the same `LogMetrics()` writes to the
file link instead of, or as well as, `logMsg()`. Nothing else in this bundle changes.
