# Cycle metrics — unit F_24_0064095_C_004  (1RT53 cell)

Every controller backup pulled from this unit, plus what can currently be parsed
out of them. Layout mirrors `Metrics_0RLab_F_24_0060113_C_001` (0RLab) so the two
units can be compared file to file.

```
backups/                                 every backup pulled from this unit, one zip each
raw/                                     the VAL3 application log from each backup, verbatim
parse_backups.py                         regenerates every CSV below from backups/
F_24_0064095_C_004_events_ALL.csv        every unique log entry, all backups
F_24_0064095_C_004_runs_ALL.csv          application start/stop pairs -> run sessions
F_24_0064095_C_004_errors_summary.csv    error classes, counts, first/last seen
F_24_0064095_C_004_state_by_backup.csv   cycle-time state found in each backup's .dtx
_to_delete/                              a stray zip temp file; safe to delete
```

Re-run after adding a backup: `python3 parse_backups.py .`

## READ THIS FIRST — there is no cycle-metrics data in these backups yet

**This unit emits no `RAIV/CSV` lines.** The 0RLab pipeline parses `RAIV/CSV,D1..D4`
records that `LogMetrics()` writes via `logMsg()`. 1RT53 has no `LogMetrics`,
no `LogLine`, no `tkMetrics` and no `RaivLog` retain library, so there is nothing
of that kind to parse — a grep for `RAIV/CSV` across all six backups returns zero.

What these CSVs therefore contain is **everything else the current build already
records**: application run sessions, faults, vision errors and controller events.
That is real, useful operating history, but it is not cycle-time telemetry. The
cycle-time and per-segment numbers exist only in controller memory while the robot
runs, and are visible on the pendant or in the IDE live data view — see the state
table below for proof they never reach a backup.

## Where the data comes from

A controller backup contains a **nested** zip:

```
<backup>.zip  ->  Y-…/logArchive.zip  ->  mnt/log/user.log
```

`mnt/log/user.log` is the VAL3 application log — what `logMsg()` writes. The
Debian syslog at `var/log/user.log` in the same archive is a different, unrelated
file and is not used. Each line is JSON, `{"entry":{…}}`, most with a trailing
`"hash"` field; the parser tolerates both forms.

The `13h49m_logsonly` entry is an "export logs" pull, not a full backup — it has
the log archive but no `usr/usrapp`, so it contributes events but no state row.

## The log is cumulative — the newest backup is the whole history

| backup | entries |
|---|---|
| 2026-08-25 17h52m (baseline, pre-change) | 4375 |
| 2026-08-26 12h45m | 4383 |
| 2026-08-26 13h49m (logs only) | 4385 |
| 2026-08-26 14h13m | 4385 |
| 2026-08-26 14h28m | 4387 |
| 2026-08-26 14h58m | 4390 |
| **unique across all six** | **4390** |

Unique total equals the newest backup exactly, and every earlier backup verified
as a strict subset of it — **one backup is normally enough**. The log reaches back
to 2024-12-17 and has not rolled. Watch for the total to stop climbing; that is
the roll, and that is when older backups stop being redundant.

## What the run log settles

`runs_ALL.csv` is the authoritative record of what actually executed. On 8/26 it
shows three runs of the **REWRITE** project:

| app | start | stop | min |
|---|---|---|---|
| `binpick_TiePlates_REWRITE08262026` | 12:15:50 | 12:17:26 | 1.6 |
| `binpick_TiePlates_REWRITE08262026` | 12:17:33 | 12:29:43 | 12.2 |
| `binpick_TiePlates_REWRITE08262026` | 13:26:30 | 13:48:18 | 21.8 |
| `binpick_TiePlates` (merged) | 14:13:06 | 14:29:04 | 16.0 |
| `binpick_TiePlates` (merged) | 14:31:28 | 14:42:42 | 11.2 |

So the new instrumentation **did** run, on both the REWRITE project and the merged
one. An earlier reading of the backups concluded it had never run; that conclusion
was wrong, and this is the record that corrects it.

## The state table is the proof the .dtx never captures live data

`state_by_backup.csv` carries one row per project per backup. Every row —
including the 8/25 baseline taken **before any of this work** — is identical:

```
_nCycleTimeIndex = 4     AverageSec = 6.22     BestSec = 3.96     WorseSec = 16.2
_nCycleTime      = the same ten samples, unchanged
new_windows_populated = False   (every 25/50/100/1000 and Seg* field empty)
```

Unchanged across six backups spanning runs that definitely happened. A backup
captures the project files as last **saved to disk**, not live task memory, and
ordinary VAL3 globals are never written back. This is not a naming, location or
code fault — it is a storage-class property. 0RLab solved it with a library
project declared `retain="true"` (`RaivLog`), whose data does survive into a backup.

## Adding the next backup

Drop the zip in `backups/` — name it `F_24_0064095_C_004_<YYYY-MM-DD>_<HHhMMm>.zip`
so it sorts and labels correctly — then run `python3 parse_backups.py .`

## What changes once the emitter is built

When `LogLine` / `LogMetrics` / `LogMetricsHdr` / `tkMetrics` and a `RaivLog`
retain library are added to 1RT53, `RAIV/CSV` records start landing in
`mnt/log/user.log` and this same folder gains the Lab's D1–D4 sample CSVs. The
parser has a clear place to grow into: add a `RAIV/CSV` branch that reassembles
D1–D4 into one row per sample, exactly as the Lab pipeline does. Note 1RT53's metric
set is cycle-time and per-segment data (`_sCycleTime`), not the Lab's plate-sorting
`_sM[]` fields, so D1–D4 will need defining for this cell and only the shared
cycle-time columns will be directly comparable between units.

---

## Per-cycle metrics (added Sep 2, 2026)

`<unit>_cycles_ALL.csv` — one row per pick, stitched from the four
`RAIV/CSV,A|B|C|D,<seq>,...` lines that `LogCycleCSV.pgx` writes to the
controller log on every cycle.

**Why it goes through the log.** Ordinary VAL3 globals never reach a backup. A
backup captures the project's on-disk state, and nothing writes live global
values back to the `.dtx` — which is why `_nCycleTime`, the `_nSeg*` rings and
every counter we added read as their shipped defaults in `state_by_backup.csv`
for every backup here. `logMsg()` output lands in `mnt/log/user.log` inside
`logArchive.zip`, which *is* captured. So the log is the transport. (The other
option is a `retain="true"` library like the Lab cell's `RaivLog`, which does
survive a power cycle and does appear in the `.dtx` — but it holds a small ring,
where the log holds the whole run.)

**Columns.** `cycle_s` plus the six segment timers
(`seg_approach_s`, `seg_linear_approach_s`, `seg_gripper_s`, `seg_retreat_s`,
`seg_place_return_s`, `seg_vision_wait_s`), the capture-path counters
(`cap_early`, `cap_at_place`, `cap_at_trigpos`, `cap_deferred`),
`branch_b_passes`, `fov_hit_start`, `fov_hit_end`, `scan_plates`,
`plates_found`, `pick_lift_seq`, `tcp_lift_mm`, and three derived columns:

- `seg_sum_s` — the six segments added up.
- `unaccounted_s` — `cycle_s - seg_sum_s`. **This is the interesting one:** time
  inside the cycle that no segment timer covers. Dwell, interlock waits and
  queue latency all land here.
- `complete` — `yes` only when all four log lines survived for that `seq`. The
  controller de-duplicates repeated log lines, so a burst can lose some; rows
  marked `no` have gaps and should be excluded from averages.

**Read `vision_wait_valid` before averaging `seg_vision_wait_s`.** When the
vision query is skipped (End Cycle, stop, socket refused) that segment is not
measured, and the field carries the *previous* cycle's number. Rows with
`vision_wait_valid = 0` must be dropped rather than averaged in.

The counters are cumulative, not per-cycle — difference consecutive rows to get
per-cycle rates.

## Backups can now be folders, not just zips

`backups/` accepts either a `.zip` or a directory (or a symlink to one) in the
pendant's own `Y-2026_M-09_D-02_16h25m` naming, so backups pulled straight off
the controller can be parsed in place without re-zipping ~10 MB of
`logArchive` per backup onto OneDrive. Labels from both conventions normalise to
`YYYY-MM-DD_HHhMMm` so the CSVs still sort chronologically.

## If a backup reports UNREADABLE

That is almost always a **OneDrive cloud-only placeholder** — the file is listed
but its bytes are not on this disk, and the read fails with `Errno 22`. The
parser reports those and carries on with the rest rather than aborting. Fix by
opening the backup folder in Explorer, or right-click → *Always keep on this
device*, then re-run.

## The workbook — `1RT53_CycleMetrics_F_24_0064095_C_004.xlsx`

Everything above, combined into one report. Same conventions as the 0RLab
workbook (`Metrics_0RLab_F_24_0060113_C_001`), so the two units read the same way:
two-row grouped headers, frozen panes, an editable **TARGETS** block, and a
**Header Key** sheet that explains every column and where it comes from.

| sheet | what it is |
|---|---|
| **Summary** | Headline KPIs, all formula-linked. Findings and the ranked next edits. |
| **Cycle Data** | One row per pick — the 17 complete cycles from the 17h48m log. |
| **Phase Budget** | Where the 4.66 s goes, steady state vs whole run, with the controller's own 25-cycle window beside it. Magnet dwell called out. |
| **Backup History** | One row per backup: what build was on the controller, what the `.dtx` carried, and whether the globals in it are live or shipped defaults. |
| **Code Changes** | The build timeline. The *New globals* column is derived by diffing `<Data name=...>` between consecutive backups' `.dtx` files, so each column traces to the build that introduced it — not to memory. Also records the two changes that were built and reverted. |
| **Runs** | All 301 application run sessions, with a per-month rollup. |
| **Errors** | The eight error classes across the whole retained log. |
| **Header Key** | Editable targets, how to read the data, and every column defined. |

Two things worth knowing before quoting a number out of it:

- **`AverageSec` is not a run average.** It is the mean of the 10-slot
  `_nCycleTime` ring — the last ten cycles only. The 145-pick run's own average
  is the 1000-window figure, **6.63 s**, not the 7.84 s that shows on the
  pendant. The workbook labels that column *10-sample avg s* for this reason.
- **Two different runs are in here.** Cycle Data is the 17h48m run with plates
  properly fed (steady state 4.66 s). The `.dtx` snapshot is a separate 145-pick
  run with plates **staged by hand**, which is slower and is not a production
  rate. The Header Key sheet says where each one applies.

**No customer target has been supplied for 1RT53**, so `Header Key!B5` is
pre-filled with the cell's own demonstrated best (4.09 s) and the Summary's
gap-to-target is a placeholder until a real budget is entered there. Everything
derived from it recalculates.

### Rebuilding it

`parse_backups.py` first (it produces the CSVs), then the workbook is built from
those CSVs plus a `.dtx` global-extraction pass over the backup folders. Adding
a backup means dropping it into `backups/`, re-running the parser, and
re-running the build.
