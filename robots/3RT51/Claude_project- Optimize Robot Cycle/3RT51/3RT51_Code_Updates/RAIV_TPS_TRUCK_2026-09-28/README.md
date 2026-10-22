# Raiv-T3 / RAIV_TPS_TRUCK — PLC Counter Snapshot ("push to robot" bundle)

**Status: DRAFT. Nothing here is on the physical controller yet, and none of
the new I/O is wired.** This is a set of file edits for you to load into
Staubli Robotics Studio and deploy to F_24_0064095_C_002 yourself, the same
way every past T1/T3 bundle has been handled. Mechanically verified (see
below), but not compiled by SRS or run on real hardware.

## What this does

Follows on from `DATA_ARCHITECTURE.md` and your direction to push as much
as possible onto the robot side, since VAL3 rewrites are far easier to
iterate on than PLC ladder logic. Robot backups currently carry zero PLC
data — everything physically counted (plates laid, travel, jams, crashes,
tie spacing) lives only on the CLICK PLUS and never reaches a robot backup.
This bundle adds a second log stream, `PLCStatsSnapshot.pgx`, that reads the
PLC's own counters over the same Modbus link the existing `aoToClick` /
`diFromClick` / `doToClick` I/O already uses, and writes them out as
`RAIV/PLC,...` lines the same way `LogCycleCSV.pgx` writes `RAIV/CSV,...`
lines — so a single robot backup can eventually give a complete performance
picture (plates/mile, jam rate, crash counts) without a separate PLC or HMI
pull.

It also renames the project from `PlateSorter` to `RAIV_TPS_TRUCK`, per your
instruction to begin drafting this as a new VAL3 project. See "Merge
instructions" below for what that does and doesn't mean mechanically.

**This first pass adds the plumbing but does not go live on its own.** The
new PLC-facing I/O collection (`aiFromClick`) ships completely **unbound** —
no `link` GUID to any Modbus channel — because that binding can only be done
inside Robotics Studio's I/O Configuration tool, not from VAL3 source files.
Until you do that binding and flip one bool, `PLCStatsSnapshot.pgx` runs
harmlessly every cycle and logs all-zero lines. See "PLC register mapping /
what you need to do in Robotics Studio" below.

## Files changed / added

| File | Before | After | What changed |
|---|---:|---:|---|
| `RAIV_TPS_TRUCK.dtx` (was `PlateSorter.dtx`) | 36,379 B | 38,547 B | New unbound `aiFromClick` collection (14 keys, `aio` type) added right after the existing `aoToClick` collection. New globals `bPLCSnapshot_IOBound` (bool), `nPlcSnapSeq` (num), `_nPLCSnap` (num collection, 14 keys mirroring `aiFromClick`) added right after the existing `_sCycleTime` collection, before `nClassesFound`. No existing declaration touched, moved, or removed. |
| `RAIV_TPS_TRUCK.pjx` (was `PlateSorter.pjx`) | 1,451 B | 1,498 B | One new `<Program file="PLCStatsSnapshot.pgx" />` entry, added immediately after `PartPlace.pgx`. `<Data file="...">` updated to point at the renamed `.dtx`. Every other program entry, and everything else outside the program list (Libraries/Types/Parameters), is untouched. |
| `tkCycle.pgx` | 5,042 B | 5,477 B | One new line — `call PLCStatsSnapshot()` — inserted immediately after the existing `call LogCycleCSV()`. Nothing else in the file touched; no motion, wait, or IO statement added, removed, or reordered (confirmed by `verify.py`, see below). |
| `PLCStatsSnapshot.pgx` | — (new) | 5,993 B | New program. Reads the 14 PLC counters through `aiFromClick` (gated behind `bPLCSnapshot_IOBound`) and emits two `RAIV/PLC` log lines per completed cycle, same convention as `LogCycleCSV.pgx`. |

Every other file in the project (`PartPick.pgx`, `PartPlace.pgx`,
`LogCycleCSV.pgx`, `UpdateCycleWindow.pgx`, `apera/`, `interface/`, and the
rest) is **completely unchanged** from the Sep-21-2026 `.OK` backup this
bundle was built against — they aren't included in this folder at all,
since there's nothing to merge for them.

## PLC register mapping / what you need to do in Robotics Studio

`aiFromClick` ships with 14 keys and no bindings. Each one needs to be
bound, in Robotics Studio's I/O Configuration tool, to the matching CLICK
PLUS register over the existing Hilscher netX51 "Open Modbus TCP" module —
the same fieldbus `aoToClick`/`diFromClick`/`doToClick` already use, so no
new fieldbus module or network config is needed, only new channel bindings
on the existing one.

| `aiFromClick` key | Intended PLC register | Notes |
|---|---|---|
| `TotalPlatesLaid` | CTD103 | |
| `TotalPicked` | CTD100 | |
| `TotalAccepted` | CTD101 | |
| `TotalRejected` | CTD102 | |
| `TravelPulses` | DD1 | **Raw encoder pulses**, deliberately not the PLC's pre-converted distance register — see `DATA_ARCHITECTURE.md` for why (unit conversion belongs in `parse_backups.py`, not duplicated in two places). |
| `TPSJamsUsr` | CTD121 | |
| `TPSJamsMaster` | CTD122 | |
| `AbortMaster` | CTD123 | |
| `CrashPickApproach` | CTD80 | |
| `CrashPickRetreat` | CTD81 | |
| `CrashPlaceAccept` | CTD82 | |
| `CrashPlaceReject` | CTD83 | |
| `TieSpacingCount` | CTD30 | |
| `UserTieSpacingSetpoint` | DS30 | A setpoint, not a counter — included so a backup also captures what the operator had it set to at the time. |

**Please double-check every one of these register addresses against the
current CLICK PLUS program before binding anything** — they're my best read
of the PLC documentation you uploaded, not something I could verify against
the live ladder logic itself.

Steps:

1. Open `RAIV_TPS_TRUCK` (or `PlateSorter`, if merging in place) in Robotics
   Studio and open its I/O Configuration for the Hilscher netX51 module.
2. For each `aiFromClick` key above, add a channel bound to the listed PLC
   register, the same way `aoToClick`'s existing channels are bound.
3. Once every key is bound, set `bPLCSnapshot_IOBound` to `true` (either by
   editing its default in the `.dtx`, or from the pendant/HMI once you've
   exposed it there — nothing in this bundle exposes it to the HMI yet).
4. Rebuild/recompile and deploy. Before step 3, this bundle is safe to
   deploy as-is — it just logs zeros.

## CSV format (for `parse_backups.py`, once wired)

```
RAIV/PLC,A,<seq>,<TotalPlatesLaid>,<TotalPicked>,<TotalAccepted>,<TotalRejected>,<TravelPulses>,<TPSJamsUsr>,<TPSJamsMaster>
RAIV/PLC,B,<seq>,<AbortMaster>,<CrashPickApproach>,<CrashPickRetreat>,<CrashPlaceAccept>,<CrashPlaceReject>,<TieSpacingCount>,<UserTieSpacingSetpoint>
```

All fields are raw PLC counter values, no scaling. `<seq>` (`nPlcSnapSeq`)
is on both lines, same stitching/drop-detection convention as `RAIV/CSV`.
Two lines because `logMsg` is capped at 255 bytes and 14 fields fit safely
split 7/7. `parse_backups.py`'s `CYC_FIELDS` table will need a `RAIV/PLC`
entry added before it can parse these — a follow-up step once a backup with
real (non-zero) data exists, not something done in this bundle.

## Safety verification

`verify.py` used for this bundle is adapted from the T3 cycle-timing
bundle's own `verify.py` (itself adapted from Raiv-T1's). It checks the same
things: every file is well-formed XML; every identifier used in the modified
programs is actually declared (global, local, parameter, or an existing
project program); no `toString()` call is ever given a bool where VAL3
requires a num; every `_sCycleTime` key is pre-declared, and — new in this
bundle's check — every `_nPLCSnap` and `aiFromClick` key referenced in code
is pre-declared too, and the two collections carry exactly the same 14 keys;
every literal array index stays inside its declared size; the `.pjx` gained
exactly the one new `PLCStatsSnapshot.pgx` entry and lost nothing else
(aside from the expected `.dtx` filename rename); and — the core safety
check — **the ordered sequence of every motion and IO instruction
(`movej`/`movel`/`movec`/`dioSet`/`aioSet`/`wait`/`waitEndMove`/`stopMove`/
`resetMotion`/`enablePower`/`disablePower`/`taskCreate`/`taskKill`) in
`tkCycle.pgx` is byte-identical to the Sep-21 baseline** — nothing was
added, removed, or reordered. The only change to `tkCycle.pgx` is the one
new `call PLCStatsSnapshot()` line, which touches neither motion nor IO.

Current result, run against this folder:

```
checked 4 files, 120 globals, 44 _sCycleTime keys
new declarations: _nPLCSnap, aiFromClick, bPLCSnapshot_IOBound, nPlcSnapSeq
WARN  NEW FILE (no original to diff): PLCStatsSnapshot.pgx

PASS  (0 fail, 1 warn)
```

The one warning is expected and harmless — `PLCStatsSnapshot.pgx` is a brand
new file, so there's no original version of it to diff against.

One thing `verify.py` **cannot** check, flagged here instead: `_nPLCSnap` is
declared as a `type="num"` **collection** (keyed like `_sCycleTime`, which is
a `type="string"` collection) rather than 14 separate `num` arrays. This
mirrors the existing `_sCycleTime` pattern but there was no existing
num-typed collection in PlateSorter to confirm the schema against directly —
SRS's own recompile is the real check for this, same as it is for everything
else in this bundle.

## Merge instructions

You have two reasonable paths here — pick whichever fits how you want to
carry this forward:

**Option A — merge directly into PlateSorter (simplest):**

1. Open the PlateSorter project in Robotics Studio (from a current backup or
   your working copy — not from this folder directly).
2. Add the `aiFromClick` collection and the three new globals
   (`bPLCSnapshot_IOBound`, `nPlcSnapSeq`, `_nPLCSnap`) to your `.dtx`, in
   the same positions this bundle's `RAIV_TPS_TRUCK.dtx` has them (after
   `aoToClick`, and after `_sCycleTime` respectively) — or just copy this
   bundle's `.dtx` over yours if you'd rather not hand-merge.
3. Add the one `<Program file="PLCStatsSnapshot.pgx" />` entry to your
   `.pjx`, in the same position (after `PartPlace.pgx`).
4. Add `PLCStatsSnapshot.pgx` from this folder as a new program in the
   project.
5. Replace your `tkCycle.pgx` with this folder's version (or hand-add the
   single `call PLCStatsSnapshot()` line after the existing
   `call LogCycleCSV()` line).
6. Rebuild/recompile and let SRS flag anything before you transfer to the
   controller.

**Option B — actually create the new `RAIV_TPS_TRUCK` project first:**

1. In Robotics Studio, open PlateSorter and use **Save As** to create a new
   project named `RAIV_TPS_TRUCK` — SRS handles the full duplication
   (including `apera/` and `interface/`, which this bundle deliberately
   doesn't touch or include) far more safely than a manual file copy would.
2. Then follow steps 2–6 of Option A against the new project instead of
   PlateSorter.

Either way, step 5/6's rebuild in SRS is the real compiler — this bundle's
`verify.py` only stands in for the checks that can be done without one.

## What to watch on first run

- **No motion should look or sound any different.** The only new code path
  is `PLCStatsSnapshot.pgx`, and its only side effects are a bool check, up
  to 14 `aioGet()` reads (harmless with unbound I/O — reads as 0), a counter
  increment, string formatting, and two `logMsg()` calls. Nothing touches
  speed, position, or timing of any move, wait, or IO signal.
- Before binding: confirm `user.log` shows `RAIV/PLC,A,...` / `RAIV/PLC,B,...`
  lines with all-zero counter fields, incrementing `<seq>`, once per cycle —
  this confirms the hook fired correctly even with nothing wired yet.
- After binding and flipping `bPLCSnapshot_IOBound`: confirm the numbers
  actually move and look sane against what the PLC/HMI screens show for the
  same counters, before trusting them in analysis.
- Log volume: 2 more short lines per cycle on top of the existing 2 from
  `LogCycleCSV.pgx` — modest, but worth keeping an eye on `user.log`
  rotation/retention same as any added logging.

## Next steps (not done here)

- **Per-type count breakdowns.** This bundle logs only the totals
  (`TotalPicked`/`TotalAccepted`/`TotalRejected`/`TotalPlatesLaid`). The
  PLC's per-type counters (CTD9/10/13/14/17/18/20/21 per the uploaded PLC
  documentation) were deliberately deferred to keep this first bundle small
  and reviewable, per project convention — a follow-up bundle once this one
  is running and confirmed stable.
- **Independent periodic snapshot.** Right now `PLCStatsSnapshot.pgx` only
  runs once per completed cycle, from `tkCycle.pgx`. `DATA_ARCHITECTURE.md`
  recommends also adding an independent ~15–30s timer poll (a new low-priority
  task) so long-running counters like `TravelPulses` and jam/crash counts get
  captured even during an idle stretch between cycles, not just at cycle
  boundaries. Not included here — a new background task is a bigger change
  than this bundle's scope.
- Add a `RAIV/PLC` entry to `parse_backups.py`'s field table once a backup
  with real (post-binding) data exists to test against.
- No HMI/pendant page changes were made or attempted — `bPLCSnapshot_IOBound`
  currently has to be flipped by editing the `.dtx` default and redeploying;
  exposing it as a togglable HMI setting is a reasonable follow-up once
  you're ready to flip it live.
