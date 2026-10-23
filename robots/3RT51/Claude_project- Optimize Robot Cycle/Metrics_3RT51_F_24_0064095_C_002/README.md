# Cycle metrics — unit F_24_0064095_C_002 (3RT51 cell)

Every controller backup pulled from this unit, plus what can currently be parsed
out of them. Layout mirrors `Metrics_1RT53_F_24_0064095_C_004` (1RT53) so the
two units can be compared file to file.

```
backups/                                 every backup pulled from this unit
raw/                                     the VAL3 application log from each backup, verbatim
parse_backups.py                         regenerates every CSV below from backups/
build_workbook_t3.py                     regenerates the .xlsx below from those CSVs
F_24_0064095_C_002_events_ALL.csv        every unique log entry, all backups
F_24_0064095_C_002_runs_ALL.csv          application start/stop pairs -> run sessions
F_24_0064095_C_002_errors_summary.csv    error classes, counts, first/last seen
F_24_0064095_C_002_state_by_backup.csv   snapshot state found in each backup's .dtx
F_24_0064095_C_002_cycles_ALL.csv        per-cycle metrics from RAIV/CSV log lines
3RT51_CycleMetrics_F_24_0064095_C_002.xlsx   Summary/Cycle Data/Phase Budget/Runs/Errors/Backup History/Header Key
```

Re-run after adding a backup: `python3 parse_backups.py .` then
`python3 build_workbook_t3.py`.

## Status: two backups (2026-09-04, 1:03 PM and 5:02 PM) — cycle telemetry is now LIVE

The first backup (13h03m) predates any cycle-time instrumentation on this
cell. Between that backup and the second (17h02m), Coty deployed the
`3RT51/CycleDataLogging_2026-09-04` bundle (PlateSorter's new
`LogCycleCSV.pgx` / segment-timing code) to the physical controller — the
17h02m backup's `PlateSorter.dtx` is byte-for-byte the size the bundle's
work copy predicted, and its log carries 93 real, clean `RAIV/CSV` cycles
from a single run (2026-09-04 20:13–20:29 UTC). This is the first real
per-cycle data this cell has ever produced. See `3RT51_CycleMetrics_...
.xlsx`'s Summary and Phase Budget sheets for the numbers — headline: ~4.7 s
clean mean cycle, ~12.8 plates/min, and the 7 measured segments plus their
small gaps already account for ~99.95% of the cycle (tighter than 1RT53's own
split, likely because PlateSorter's unmeasured retreat carry-over is small
relative to its cycle time — see the bundle README for why that segment
isn't split out).

**This unit's cell runs two VAL3 applications** — `binpick_TiePlates` and
`PlateSorter` — so `state_by_backup.csv` carries one row per project per
backup, same as 1RT53 does for its REWRITE variant. Only `PlateSorter` has ever
actually run (89 of 89 logged run sessions); `binpick_TiePlates` is present
on disk but dormant.

## The `_sCycleTime`/`state_by_backup.csv` columns are still blank — that's expected

Both backups show every `Seg*`/`AverageSec`/etc. column blank in
`state_by_backup.csv`, even though real cycle data exists in the log. That's
not a bug: those columns only get real values if the application data was
explicitly **saved from SP2** before the backup was pulled (a separate,
manual step Coty hasn't done for 3RT51 yet). The two transports answer
different questions — see `LogCycleCSV.pgx`'s header in the deployed bundle
for the fuller writeup. `cycles_ALL.csv` (the log-based route) is what's
carrying real data right now.

## Field layout note (fixed 2026-09-04)

`CYC_FIELDS` in `parse_backups.py` originally carried a placeholder copied
from 1RT53's A–G tag layout ("ready the day it emits these lines"). PlateSorter's
actual `LogCycleCSV.pgx` uses a different, simpler two-tag format:

```
RAIV/CSV,A,<seq>,<cycle>,<approach>,<linApproach>,<toolOn>,<return>
RAIV/CSV,B,<seq>,<toolOff>,<visionWait>,<finderWait>,<partsFound>,<classesFound>
```

`parse_backups.py` has been updated to match (only tags A/B, 3RT51-specific
segment names, no C–G cumulative counters — this cell doesn't have 1RT53's
equivalents). This is why the second backup's 93 cycles parsed cleanly.

## Where the data comes from

A controller backup contains a **nested** zip:

```
<backup>.zip  ->  Y-…/logArchive.zip  ->  mnt/log/user.log
```

`mnt/log/user.log` is the VAL3 application log — what `logMsg()` writes. The
Debian syslog at `var/log/user.log` in the same archive is a different,
unrelated file and is not used. Each line is JSON, `{"entry":{…}}`, most with
a trailing `"hash"` field; the parser tolerates both forms.

## If a backup reports UNREADABLE

That is almost always a **OneDrive cloud-only placeholder** — the file is
listed but its bytes are not on this disk, and the read fails with `Errno 22`.
This is the normal state for backups pulled onto this OneDrive folder — both
3RT51 backups so far have needed this. The parser reports those and carries on
with the rest rather than aborting. Fix by opening the backup folder in
Explorer (or right-click → *Always keep on this device*), or ask Claude to
stage the files — which hydrates them — before re-running.

## Backups can be folders, not just zips

`backups/` accepts either a `.zip`, a directory, or a symlink to one, in the
pendant's own `Y-2026_M-09_D-02_16h25m` naming. `backups/2026-09-04_13h03m`
and `backups/2026-09-04_17h02m` here are symlinks to the actual pulled
backups under `../../3RT51/3RT51_Staubli_Backups/F_24_0064095_C_002/` rather than
copies, so the ~10 MB `logArchive.zip` per backup isn't duplicated across
OneDrive. Labels from both conventions normalise to `YYYY-MM-DD_HHhMMm` so
the CSVs sort chronologically.

## Adding the next backup

Once IT/you pull the next backup for this controller into
`3RT51/3RT51_Staubli_Backups/F_24_0064095_C_002/`, either symlink it into this folder's
`backups/` (matching its pendant folder name) or drop a renamed `.zip` there,
then run `python3 parse_backups.py .` followed by
`python3 build_workbook_t3.py`. If the backup was just pulled it will likely
be a cloud-only placeholder on this machine — see above.

## About the workbook

`build_workbook_t3.py` is a much smaller script than 1RT53's `build_workbook.py`
— 1RT53's encodes a long history of 1RT53-specific fixes and speed-level splits
that simply don't apply yet here (this is 3RT51's first backup with any cycle
data at all, one continuous run, one speed). As more 3RT51 backups and runs
accumulate, this can grow the same way 1RT53's did — a per-run/per-speed split,
a trend across builds, etc. — once there's enough history to make that
meaningful.
