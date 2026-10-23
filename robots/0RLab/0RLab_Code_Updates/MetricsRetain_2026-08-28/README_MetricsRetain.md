# MetricsRetain — 2026-08-28  (option 2)

Persists the cycle metrics into **retained VAL3 data**, which is non-volatile and comes
out in a controller backup. Built on the deployed project inside
`Lab_Backup_08282026_F_24_0060113_C_001` — option 1 is already merged there and stays.

`bLogRetain` ships **false**. Nothing changes until you set it true.

---

## First: two corrections from your backup

**1. I was wrong that option 1's lines come out in a backup.** They do not. Your
08/28 15h09 backup contains **no log data at all** — the only `.log` in it is a 90-byte
`backup_OK_...log` receipt reading "Backup of SRC controller … ended successfully". The
CS9 system log is not part of this backup type. So option 1 is live pendant visibility
and the pre-RESET archive — genuinely useful, but it does **not** get numbers off the
machine. Verification step 7 in the option 1 README would have failed; ignore it.

**2. There is no disk/file `sio` resource, and no sign the schema supports one.**
`usr/configs/sio.cfx` contains exactly three entries:

| element | name | detail |
|---|---|---|
| `serialPort` | `portSerial` | 9600 8N1, endOfString 13 |
| `socketClt` | `sAperaRestart` | 192.168.10.10:14050 |
| `socketClt` | `sAperaSocket` | 192.168.10.10:14040 |

Only `serialPort` and `socketClt` element types appear. A file-backed `sio` is not
configured and I have no evidence it can be. **So option 2 is not a file.**

---

## What it is instead: `retain="true"`

`usr/templates/retain/retain.pjx` on your controller:

```xml
<Parameters version="s8.12.1Cs9_BS2449" stackSize="5000" millimeterUnit="true" retain="true" />
```

A data-only library project, no programs, empty `.dtx`. That is Stäubli's own template
for **non-volatile VAL3 data** — it survives application stop and power cycle, and it
lives under `usr/`, so it comes out in exactly the backup you just sent me. Controller
is `s8.15.1Cs9_BS3177`, so the template ships supported on this build.

That is a better answer than a file: no I/O resource to configure, no uncertain file API,
and the data lands somewhere your existing backup routine already collects.

## What's in this folder

| File | Change |
|---|---|
| `RaivLog/RaivLog.pjx` | **NEW library**, `retain="true"` |
| `RaivLog/RaivLog.dtx` | **NEW.** `sLine[200]` ring, `nWrite`, `nLines`, `nRunId`, `nRing` |
| `LogLine.pgx` | **NEW.** Fans one line to both sinks — system log and retained ring |
| `LogMetrics.pgx` | Rewritten to build each line into a local and hand it to `LogLine()`; every line now carries the run id |
| `LogMetricsHdr.pgx` | Rewritten: `run` is now field 1 of every header |
| `tkMetrics.pgx` | Increments `RaivLog:nRunId` once per run; both trigger gates now fire if **either** sink is enabled |
| `stop.pgx` | Same either-sink gate |
| `LAB_PlateSorter2.dtx` | Adds `bLogRetain` (public bool, **default false**) |
| `LAB_PlateSorter2.pjx` | Registers `LogLine.pgx` and the `RaivLog` library |

## Design notes

**Run id on every line.** Ring entries from different runs sit next to each other and
`clock()` is the only time source on this controller — I checked, there is no wall-clock
date call in use anywhere in it. So each line is stamped with a retained, ever-increasing
run id, and `_sM["RunMin"]` in `D1` gives position within the run. Anchor a run to a wall
clock using the pendant LOGGER, which does timestamp its entries.

**The ring cannot walk off the end.** `size(sLine)` is the authority for wrapping, never
`nRing`; `nRing` is published for the reader and a stale value cannot index past the
array. `nWrite` is bounds-checked before use, so a hand-edited value is corrected rather
than obeyed. `nLines` is the total ever written, so you can tell a part-filled ring from
one that has wrapped.

**Either-sink gating.** The sample trigger now fires when `bLogEnable` **or**
`bLogRetain` is on, and `LogLine()` decides per sink. Without this, turning off the
noisy system-log lines would also have silently stopped the retained archive.

**Still a pure observer.** `logMsg()` and the `RaivLog` ring only. No motion, no physical
output, no variable another program reads.

**Sizing.** 200 lines = 4 lines per sample = 50 samples. At `nLogPeriodSec` 300 that is
~4 hours; set it to 900 for ~12 hours.

## Three things I could not verify from the backup — check these on the bench

1. **Retain capacity.** I do not know how much retained storage this controller allows.
   A 200-element string array may or may not fit. **If it is too large the application
   may fail to load**, which is why step 1 below is "does it load at all" and why 200 is
   deliberately modest rather than the 400 I first wanted.
2. **Write endurance.** If retained data is flash-backed, 4 writes per sample is roughly
   1,150 writes/day at a 5-minute period. Probably fine; I cannot prove it. If you want
   to be cautious, run `nLogPeriodSec` at 900 to start.
3. **Where the values actually land in a backup.** I expect them as populated `<Value>`
   entries in `usr/usrapp/LAB_PlateSorter2/RaivLog/RaivLog.dtx`. Step 6 is the test.

## Merge steps

1. Back up the current project (you have one — keep it).
2. Copy the six loose files into `usr/usrapp/LAB_PlateSorter2/`, overwriting.
3. Copy the `RaivLog` folder into `usr/usrapp/LAB_PlateSorter2/RaivLog/`.
4. Full application reload — `.dtx`, `.pjx` and a new library all changed.

## Verification steps — staged, stop at the first failure

1. **Does the application load?** With `bLogRetain` still false. If it refuses, the
   retain array is too big: drop `sLine` size (and `nRing`) to 100 or 50 and retry. This
   is the capacity question and it must be settled before anything else.
2. Run a cycle with `bLogRetain` false. Behaviour must be identical to now: `RAIV/CSV`
   blocks on the LOGGER page, `run` as the new first field, `H1` showing 14 columns.
3. Set `bLogRetain` **true**. Confirm in the data editor that `RaivLog:nWrite` advances by
   4 per sample and `RaivLog:nLines` climbs, and spot-read a couple of `RaivLog:sLine[]`
   entries — they should match the LOGGER lines exactly.
4. **Power cycle the controller.** `RaivLog:nLines` and the `sLine[]` contents must
   survive. This is the whole point — if they do not, retain is not doing what the
   template implies and stop here, tell me.
5. Let it wrap past 200 lines. `nWrite` must return to 0 and keep going; `nLines` must
   keep climbing past 200.
6. **Take a controller backup and open
   `usr/usrapp/LAB_PlateSorter2/RaivLog/RaivLog.dtx`.** The `sLine` values must be in it.
   That is the step that proves "stored to backup logCS9".
7. Press RESET on the LRC page. A pre-reset `D1..D4` block must land in the ring before
   the counters zero.

## If retain does not survive step 4 or does not appear at step 6

There is a third path, and your controller is already configured for it: `sio.cfx` has
working `socketClt` entries, and the Apera library shows the `open()` / `sioGet()` pattern
in use. Adding one more `socketClt` pointing at a log collector on the network would let
`LogLine()` push the same CSV to a PC that just appends to a file. That needs a listener
on your side, but it uses only mechanisms this controller demonstrably supports. Say the
word and I will write it.
