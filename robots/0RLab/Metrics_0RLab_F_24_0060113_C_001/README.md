# Cycle metrics — unit F_24_0060113_C_001  (0RLab cell)

Every `RAIV/CSV` sample this controller has logged, parsed into one place.

```
F_24_0060113_C_001_ALL.csv              <- start here: every unique sample
F_24_0060113_C_001_<date>_<time>.csv    <- one per backup, named for the backup it came from
raw/                                    <- the unparsed RAIV/CSV log lines, per backup
superseded/                             <- earlier hand-named exports, kept only for traceability
```

`ALL` carries a `source_backup` column so any row traces back to the backup it came from.

## Where the data actually comes from

The controller writes no CSV. `LogMetrics()` emits `logMsg()` lines, which land in the CS9
system log and are captured in each backup inside a **nested** zip:

```
<backup>/Y-…/logArchive.zip  ->  mnt/log/user.log   (and screenLog.txt, same lines)
```

Each line is wrapped in JSON with a trailing `"},"hash":"…"}` that has to be stripped, and
one sample is four lines (`D1`–`D4`) that reassemble into one row. That parse is what these
files are.

## The log is cumulative — the newest backup is the whole history

| backup | samples | raw lines |
|---|---|---|
| 2026-08-28 15h09 | 2 | 12 |
| 2026-08-31 10h29 | 5 | 36 |
| 2026-08-31 12h23 | 9 | 96 |
| 2026-08-31 15h07 | 15 | 160 |
| **unique across all four** | **15** | — |

31 rows collapsed to 15 unique: every earlier sample is still present in the 15h07 log. So
**one backup is normally enough** — parse the latest and you have everything, until the log
rolls far enough to drop the oldest entries. Watch for the total stopping its climb; that is
the roll, and that is when older backups stop being redundant and start being the only copy.

## Schema drifts, on purpose

Columns were added as the metrics grew, and the parser fills blanks rather than shifting
fields:

| added | column | marks |
|---|---|---|
| — | 13 fields, no `run` | the original build |
| 8/31 | `run` | run-id build (`MetricsRetain`) |
| 8/31 | `b_hold` | operator hold split out of fault (`AbortHold_Fix`) |

Blank `run` = pre-run-id. Blank `b_hold` = before hold had its own bucket, when that time
was inside `b_fault`. **Do not compare `act_spc` across the `b_hold` boundary** — hold time
is inside the rate before it and outside after.

Also: values are the pendant's own formatted strings, so they are space padded and read
`--` where undefined. Import with `skipinitialspace` and treat `--` as null, not zero.

## Adding the next backup

Send it and I will parse it in. Or by hand: unzip `logArchive.zip`, then
`grep "RAIV/CSV" mnt/log/user.log`, and reassemble `D1`–`D4`.

For a second unit — 1RT53 is `F_24_0064095_C_004` — the same layout beside this one as
`Metrics_1RT53_F_24_0064095_C_004`, so the two can be compared file to file.
