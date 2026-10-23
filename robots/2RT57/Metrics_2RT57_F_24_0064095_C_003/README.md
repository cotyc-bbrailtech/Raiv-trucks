# Cycle metrics — unit F_24_0064095_C_003 (2RT57 / Truck 57)

Every controller backup pulled from this unit, plus what can currently be parsed
out of them. Layout mirrors `Metrics_1RT53_F_24_0064095_C_004` (1RT53) and
`Metrics_3RT51_F_24_0064095_C_002` (3RT51) so all three units can be compared
file to file.

```
backups/                                 every backup pulled from this unit
raw/                                     the VAL3 application log from each backup, verbatim
parse_backups.py                         regenerates every CSV below from backups/
build_workbook_t2.py                     regenerates the .xlsx below from those CSVs
F_24_0064095_C_003_events_ALL.csv        every unique log entry, all backups
F_24_0064095_C_003_runs_ALL.csv          application start/stop pairs -> run sessions
F_24_0064095_C_003_errors_summary.csv    error classes, counts, first/last seen
F_24_0064095_C_003_state_by_backup.csv   snapshot state found in each backup's .dtx
F_24_0064095_C_003_cycles_ALL.csv        per-cycle metrics from RAIVCYC log lines
2RT57_CycleMetrics_F_24_0064095_C_003.xlsx   Summary/Cycle Data/Runs/Errors/Backup History/Header Key
```

Re-run after adding a backup: `python3 parse_backups.py .` then
`python3 build_workbook_t2.py`.

## Status: three backups so far, and a second real test (2026-09-28)

The first two backups (10:37 AM and 10:45 AM) were pulled the same morning, 8
minutes apart, and carry the same underlying `user.log` (the second has
exactly one more line — a `PlateSorter2 stopped.` at 06:39:31 — everything
else is identical). Treat them as one snapshot; that log runs continuously
back to 2026-08-17.

A third backup, pulled 13:11 the same day, captures a **second real test**:
`PlateSorter3` (production `PlateSorter2` plus only cycle telemetry — see its
`DEPLOY_README.md` in `2RT57/PlateSorter3/`) ran supervised, 09:03–09:08
local, picking **rubber tie plates** instead of the steel plates the first
test used. See "What the two cycle samples show" below — the two runs are
not the same build or the same material, so don't average them together.

## The key finding: this truck's production app had no cycle-time telemetry — now it does

**Five VAL3 applications exist on this controller's disk**: `binpick_TiePlates`
(present, never run), `PlateSorter` (the original app), `PlateSorter2`
(production through 2026-09-28 — every 2026-dated run before that date in
`runs_ALL.csv` is `PlateSorter2`), `PlateSorterREWRITE_2` (a validation build,
added 2026-08-21/22, that introduced per-plate cycle logging — `LogCycle.pgx`
and `PublishCycle.pgx` — ran once, later withdrawn), and `PlateSorter3`
(deployed 2026-09-28: `PlateSorter2`'s own code, unmodified, plus `LogCycle`/
`PublishCycle` grafted on — see its `DEPLOY_README.md` for exactly what
changed and what didn't).

`LogCycle.pgx`'s own comment explains why it exists: 2RT57's per-plate timing had
previously been reverse-engineered from an instrumented build that isn't in
any archived project, so nobody could reproduce where the "catastrophic tail"
cycles on 2026-08-20 came from. This drop closed that gap — **but only inside
`PlateSorterREWRITE_2`**, which ran exactly once (2026-08-21, ~7 minutes,
plates 2–29) and has not run again. `PlateSorter2`, the app in production
every day since, has no `LogCycle`/`PublishCycle`/`bLogCycle` code at all — its
`.dtx` doesn't even declare the globals. So `bLogCycle`, `AverageSec`, etc.
reading blank for `PlateSorter`/`PlateSorter2` on `state_by_backup.csv` isn't
missing data — it's the instrumentation gap itself.

**As of 2026-09-28, this is fixed going forward — if `PlateSorter3` stays the
selected app.** Until then, the only live number was the C-more panel
(`PublishCycle.pgx` feeds the PLC's own `DF94`/`DF95` rolling average), and a
controller backup doesn't capture PLC registers.

## What the two cycle samples show — do not average these together

**Run 1 — 2026-08-21, 13:06–13:13 local, `PlateSorterREWRITE_2` (withdrawn), STEEL 14in plates.**
29 `RAIVCYC` lines, one continuous run (plates 2–29; the very first attempt at
13:06:48 was killed and restarted at 13:08:00 — that's `run` 0 vs `run` 1 in
`cycles_ALL.csv`). Cycle time ramps down from a cold start (26.73s, 21.18s,
12.83s...) to a steady ~5.2–6.5s once warmed up (plate 7 on) — **~5.76s mean,
~10.4 plates/min steady state**. All 29 cycles picked and accepted a 14in
plate; nothing was rejected or missed. This build had a magnet pre-energize
optimization and other behavior changes production doesn't have — see the
withdrawn build's history in this conversation before comparing its numbers
to run 2's.

**Run 2 — 2026-09-28, 09:03–09:08 local, `PlateSorter3` (production code + telemetry), RUBBER tie plates.**
29 `RAIVCYC` lines, one continuous supervised run, no cold-start ramp, zero
errors/faults logged. Baseline cycle time (25 of 29 cycles) is **~6.05s mean,
~9.9 plates/min** — a bit slower than run 1's steady state, consistent with
this build *not* having run 1's magnet pre-energize optimization. The other
4 cycles (plates 6, 12, 18, 24 — every 6th, exactly) ran ~14.0s instead of
~6.0s, with no error or log line explaining why; most likely the belt re-jog
("no trajectory found") branch taking an extra pass on this material. Worth
watching whether that 1-in-6 rate holds over a longer run. All 29 cycles
classified `ACCEPT`, `14in` (a size class — this vision pipeline has no
material-specific classification, so this doesn't distinguish rubber from
steel).

**Read before trusting the "all ACCEPT, zero reject" line as proof rubber
plates were physically handled correctly:** this truck's gripper runs blind
— `tTool.pgx`/`PartPick.pgx` have no part-detect feedback at all (confirmed
while building `PlateSorter3` — see its `DEPLOY_README.md`). A completed,
non-erroring cycle in this log means the *motion sequence* ran to completion
and vision classified the item — it does not by itself confirm a plate was
actually retained by the magnet the whole way, which matters most exactly
when testing a new, possibly less magnetic material. If this run wasn't
watched in person, worth confirming separately (checked accept bin, etc.)
before calling rubber tie plates validated on this gripper.

See the Summary and Cycle Data sheets in the workbook for the exact numbers.

## Reliability picture (real, 2020+ dates — see clock-reset caveat below)

- `io_no_answer` (ERR 125, "No answer from input-output") — 56 times,
  2026-08-17 through 2026-09-03, then **zero** since. Looks like a comms issue
  that stopped recurring after early September.
- `calib_instability` + `calib_handeye_error` (Apera hand-eye calibration
  faults) — 12 + 8 times, clustered 2026-08-24 through 2026-09-11, then none
  since.
- `motion_stack_conflict` (ERR 35) — 14 times, 2026-08-31 through 2026-09-22
  (most recent of the recurring classes).
- `val3_err60_timeout`, `workspace_out_of_range` — 5 and 4 times respectively,
  scattered through early September.
- `motion_cancelled` ("Application has ended, the pending motion was
  cancelled") — 15 times; this is normal operator/app-stop noise, not
  necessarily a fault, since it fires whenever the app is stopped mid-motion.
- `apera_bad_pipeline_id` — 6 real occurrences, all during the 2026-08-21
  `PlateSorterREWRITE_2` test window (`RAIV_pick_belt_1` pipeline missing) —
  not seen since.

See `F_24_0064095_C_003_errors_summary.csv` / the Errors sheet for exact
counts, first/last-seen, and example lines.

## Caveat: 2019-02-14 clock-reset dates

This log carries a large block of entries dated **2019-02-14** — the
controller's placeholder clock before it syncs to real time on boot, not a
real 2019 event. It inflates a couple of error classes hugely if you look at
raw all-time counts (`apera_bad_pipeline_id`: 1,763 total vs. 6 real;
`apera_pipeline_missing`: 1,755 total vs. 0 real) and is the main reason
`PlateSorter`'s own run history can't be trusted from this log — different
real reboots can collide on the same placeholder timestamp, so its true 2026
run count/duration can't be reconstructed, only that it was the app in use
before `PlateSorter2` took over. `errors_summary.csv` carries both `count`
(all-time, includes this noise) and `count_since_2020` (the trustworthy
figure) for this reason — use `count_since_2020`. Cycle data, `PlateSorter2`'s
run history, and every other real-dated figure in this workbook are
unaffected.

## Where the data comes from

A controller backup contains a **nested** zip:

```
<backup>.zip  ->  Y-…/logArchive.zip  ->  mnt/log/user.log
```

`mnt/log/user.log` is the VAL3 application log — what `logMsg()` writes. The
Debian syslog at `var/log/user.log` in the same archive is a different,
unrelated file and is not used. Each line is JSON, `{"entry":{…}}`, most with
a trailing `"hash"` field; the parser tolerates both forms.

## The `RAIVCYC` field layout — two versions have shipped

`LogCycle.pgx` writes ONE line per plate (not split across multiple tags the
way 1RT53/3RT51's `RAIV/CSV` A–G layout is — logMsg's 255-byte cap was never a
concern here). Two builds, two field counts, same tag:

```
PlateSorterREWRITE_2 (run 1, withdrawn):
  RAIVCYC,<plate#>,<cycleSec>,<ppm>,<partPicked>,<accept/reject>,<hasPart 0/1>,<speedStep>,<blendStep>

PlateSorter3 (run 2, current):
  RAIVCYC,<plate#>,<cycleSec>,<ppm>,<partPicked>,<accept/reject>
```

`PlateSorter3`'s version dropped `hasPart`/`speedStep`/`blendStep` because
production has no part-detect feedback or speed-stepping to report — rather
than log fake zeros. `parse_backups.py` fills those three as blank/`None` for
any row shorter than the full 7-field layout, so `CYC_FIELDS`/`NUMERIC` and
every downstream sheet still work with either format side by side — no code
changes needed when a shorter-format row shows up.

`plate#` (`nPlateCount`) resets to 0 on every application restart and does not
persist across restarts, so `parse_backups.py` starts a new `run` group
whenever a row's plate number is not strictly greater than the previous one —
same idea as 1RT53/3RT51's sequence-decrease check.

## Backups can be folders, not just zips

`backups/` accepts either a `.zip`, a directory, or a symlink to one, in the
pendant's own `Y-2026_M-09_D-28_10h45m` naming. **All three backup folders
here are plain copies, not symlinks**, unlike 1RT53/3RT51's pattern — this
machine's local shell access (needed to create the symlinks without
duplicating the ~12–13 MB `logArchive.zip` per backup) has been unavailable
while building this (a Windows update issue blocking Claude's local shell
tools).
Once that's resolved, these can be swapped for symlinks into
`2RT57/F_24_0064095_C_003/` the same way 1RT53/3RT51 do it, to stop duplicating
the zip per backup. Labels from both conventions normalise to
`YYYY-MM-DD_HHhMMm` so the CSVs sort chronologically.

## Adding the next backup

Once IT/you pull the next backup for this controller into
`2RT57/F_24_0064095_C_003/`, either symlink it into this folder's
`backups/` (matching its pendant folder name) or drop a renamed `.zip` there,
then run `python3 parse_backups.py .` followed by
`python3 build_workbook_t2.py`. If the backup was just pulled it may be a
cloud-only OneDrive placeholder on first read — open it in Explorer (or
right-click → *Always keep on this device*) or ask Claude to stage it first.

## About the workbook

`build_workbook_t2.py` is deliberately simple, like 3RT51's first-backup build —
one cycle-time sample, one continuous test run, no phase/segment breakdown
(this cell's `LogCycle.pgx` logs a single whole-cycle number, not per-phase
timings the way 1RT53/3RT51's `PartPick`/`PartPlace` instrumentation does), so
there's no "Phase Budget" sheet here. If `LogCycle` gets deployed to
`PlateSorter2` and real ongoing telemetry starts flowing, this can grow a
trend-across-builds view the way 1RT53's did.
