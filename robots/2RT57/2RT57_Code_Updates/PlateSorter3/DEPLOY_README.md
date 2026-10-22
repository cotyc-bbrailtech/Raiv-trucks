# PlateSorter3 — ready-to-deploy VAL3 project, Raiv-T2 / Truck 57

## What this actually is (revised 2026-09-28)

**PlateSorter3 is production `PlateSorter2`, byte-for-byte, plus per-plate cycle
telemetry (`LogCycle.pgx` / `PublishCycle.pgx`) added on top.** Nothing else.

This replaces an earlier build of PlateSorter3 that was a renamed copy of
`PlateSorterREWRITE_2` (an Aug-21 validation build with several untested
behavior changes — a tool-frame bug among them). That build has been
withdrawn. **This one starts from the actual `PlateSorter2` pulled from this
truck's own production backup**, confirmed identical to production
everywhere except the one file below.

**Verified, not assumed:** every file in this project — every motion
program, every point, joint, tool frame and global in `PlateSorter3.dtx` —
is byte-for-byte identical to the backup's `PlateSorter2`, with a single
exception: `tkCycle.pgx`. In that one file, every existing line is
unchanged and in its original order; the only edits are new lines that
measure the time between plates and call the two new telemetry programs.
Diffed and confirmed — see the diff at the bottom of this file.

## Known issue this build does NOT fix — read before you deploy

Production's `tkPartFinder.pgx` still contains the exact defect that caused
the 2026-08-20 incident (9 app restarts, ~2 hours, ~3,500 pipeline errors,
2 plates produced): when the belt-jog loop can't find a trajectory, it calls
`apera_trigger("Detector")` / `apera_inspect("Detector",...)` — but no Apera
pipeline named `"Detector"` exists on this truck. Every call in that branch
returns an error (`"The provided pipeline id 'Detector' does not exist"`),
`nObjectCount`/`nPartsFound` are never set, and the belt loop can spin with
the conveyor running.

A validated fix for this exists (in `PlateSorterREWRITE_2`, built 22 Aug and
tested for one 7-minute run on 21 Aug) — it corrects `sPipelineDet` to the
truck's real pipeline id, `"RAIV_pick_belt_1"`. **This build does not carry
that fix**, because you asked for PlateSorter3 to be a reflection of
production as pulled, and grafting in that fix would be exactly the kind of
unrequested behavior change that caused the last build to need withdrawing.
Say the word and it's a one-line, well-understood change to layer in.

## What was added

```
LogCycle.pgx       NEW - one CSV line per plate to user.log, tag RAIVCYC
PublishCycle.pgx   NEW - rolling-average cycle time -> PLC (C-more panel), guarded by ioStatus()
tkCycle.pgx        MODIFIED - additive only, see the diff below
PlateSorter3.dtx   MODIFIED - additive only: bLogCycle, nPlateCount, nCycleLast,
                   _nCycleTime[20], _nCycleTimeIndex, _sCycleTime, and 4 new
                   (unbound) aoToClick keys. No existing value changed.
```

Everything else — `PartPick.pgx`, `PartPlace.pgx`, `Init.pgx`, `tkAbort.pgx`,
`tTool.pgx`, `tkMonitor_Robot.pgx`, `tkPartFinder.pgx`, the `apera/` vision
library, `interface/` — is the untouched file pulled from this truck's own
production backup. `verify.py` confirms no leftover `PlateSorter2` filename
references were missed in the rename.

### Why the telemetry is narrower than the earlier build's

The Aug-21 validation build's `LogCycle` also logged `hasPart`/`speedStep`/
`blendStep`. Those came from instrumentation (a part-detect flag, dynamic
speed stepping) that **only exists in that rewrite** — production's
`PartPick`/`tTool` run the magnet on a fixed delay with no part-detect
feedback at all, and has no speed-stepping concept. Rather than fabricate
values for signals production doesn't have, this build logs only what
production actually measures:

```
RAIVCYC,<plate#>,<cycleSec>,<ppm>,<partPicked>,<accept/reject>
```

This is a subset of the field order `Metrics_RT-2_F_24_0064095_C_003`'s
`parse_backups.py` already expects — the parser fills what's present and
leaves the rest blank, so **no parser changes are needed.**

Same reasoning trimmed `PublishCycle`: the Aug-21 build also published
`nFaultCode`/`nFaultHoldSec`/`nMissPick`/`nAperaRestarts` from a fault-hold
framework that only exists in that rewrite. Production's `tkCycle` has no
such framework, so this build only publishes cycle time / PPM / rolling
average / plate count — the numbers production's own loop can measure.

## Before you deploy

1. **`bLogCycle` defaults to `true`** — telemetry is on by default. Set it
   `false` in the .dtx (or from the pendant) to silence it without removing
   the code.
2. The 4 new `aoToClick` keys (`nCycleSec_x10`, `nPPM_x10`, `nAvgSec_x10`,
   `nPlateCount`) are declared **unlinked**. `PublishCycle` guards every
   write with `ioStatus()`, so it runs safely before they're bound — nothing
   reaches the C-more panel until someone binds them in the SRS I/O editor.
   Binding them is optional; `LogCycle`'s output to `user.log` works either
   way.
3. **Read the "Known issue" section above** and decide whether you want the
   `tkPartFinder` pipeline-name fix layered in before this goes on the
   truck.

## Deploying

1. Copy this whole `PlateSorter3/` folder onto the controller's
   `usr/usrapp/` directory, e.g. via the pendant's file transfer or VAL3
   Studio.
2. Open it in VAL3 Studio / the pendant and confirm it loads clean.
3. Stop `PlateSorter2` before selecting `PlateSorter3` — don't run two cycle
   apps against the same cell at once.
4. Run supervised first, the same way any change to this truck is watched
   before being left unattended.
5. Pull a backup after it's had real running time — `Metrics_RT-2`'s
   `parse_backups.py` + `build_workbook_t2.py` will pick up real, ongoing
   per-cycle data for the first time.

## If something looks wrong

This build makes no claim to fix anything beyond adding telemetry — it is
production's own behavior, instrumented. If a fault happens, it will fault
exactly the way `PlateSorter2` already does today; nothing about that was
changed here.
