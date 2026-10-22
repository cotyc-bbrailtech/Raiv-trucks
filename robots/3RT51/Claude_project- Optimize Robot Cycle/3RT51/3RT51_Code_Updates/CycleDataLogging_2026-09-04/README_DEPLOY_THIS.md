# Raiv-T3 / PlateSorter — Cycle-Time & Segment Logging

**Status: DRAFT. Nothing here is on the physical controller yet.** This is a
set of file edits for you to load into Staubli Robotics Studio and deploy to
F_24_0064095_C_002 yourself, the same way the Raiv-T1 bundles have been
handled. Mechanically verified (see below), but not run on real hardware.

## What this does

Adds the same kind of per-cycle timing telemetry that Raiv-T1 already has —
a total cycle time plus a segment-by-segment breakdown — to the PlateSorter
project, and starts writing it out as `RAIV/CSV,...` lines via `logMsg()`.
Those lines land in `mnt/log/user.log`, get captured in every backup's
`logArchive.zip`, and `parse_backups.py` (already set up for T3 under
`Metrics_RT-3_F_24_0064095_C_002/`) will start filling in `cycles_ALL.csv`
the next time it's re-run against a backup pulled after this is deployed.
Right now that file exists with a header row and no data, because PlateSorter
has never emitted these lines before today.

This is a **first pass**, scoped to "full segment breakdown" the way you
asked, but PlateSorter's code doesn't have as many existing synchronization
points as T1's does, so the breakdown is coarser than T1's — see "What's
NOT measured" below before you compare the two side by side.

## Files changed / added

| File | Before | After | What changed |
|---|---:|---:|---|
| `PlateSorter.dtx` | 32,709 B | 36,379 B | 18 new global declarations (cycle/segment ring buffers + index counters + `_nSegLast[8]` + `nCsvSeq`) plus 35 new keys in the existing `_sCycleTime` collection (7 segments × 5 keys), added after the existing `_pHere` entry. No existing declaration touched, moved, or removed. |
| `PlateSorter.pjx` | 1,367 B | 1,451 B | 2 new `<Program file="...">` entries (`LogCycleCSV.pgx`, `UpdateCycleWindow.pgx`). Every existing entry, and everything outside the program list (Database/Libraries/Types), is untouched. |
| `tkCycle.pgx` | 2,703 B | 5,042 B | Clock stamps + `_nSegLast[]` writes inserted around the existing `taskCreate`/`wait` calls in the pick branch, plus the cycle-time close and the calls to `UpdateCycleWindow`/`LogCycleCSV` at the end of that branch. The belt-jog (`else`) branch is completely untouched. |
| `PartPick.pgx` | 2,577 B | 3,491 B | Clock stamps + `_nSegLast[]` writes inserted around the two existing `waitEndMove()` calls and around the existing `call tTool("ON")`. |
| `PartPlace.pgx` | 6,356 B | 7,460 B | The same clock-stamp pattern inserted around each of the three branches' existing `waitEndMove()` / `call tTool("OFF")` pair (feed-conveyor, accept, reject). All three branches instrumented identically. |
| `LogCycleCSV.pgx` | — (new) | 5,901 B | New program. Formats and emits the two `RAIV/CSV` log lines once per completed pick+place. |
| `UpdateCycleWindow.pgx` | — (new) | 4,593 B | New program. **Copied verbatim from Raiv-T1's own `UpdateCycleWindow.pgx`** (`CycleTiming_Update_2026-08-26` bundle) — it's fully generic, no T1-specific dependency, so there was no reason to rewrite it. |

## What's measured, and what each segment means

| Segment | Where it's timed | What it covers |
|---|---|---|
| `cycle` | `tkCycle.pgx` | One full pick+place pass through the `bTrajectoryFound` branch, start to finish. |
| `approach` | `PartPick.pgx` | The `APPROACH` move, from entry through its `waitEndMove()`. **Also absorbs whatever motion was still queued from the end of the previous cycle** (see caveat below) — it is not pure approach time. |
| `linApproach` | `PartPick.pgx` | Air-blast on + `LINEAR_APPROACH` move through its `waitEndMove()`. |
| `toolOn` | `PartPick.pgx` | The blocking `call tTool("ON")` itself — the gripper's own actuation/settle delay. |
| `return` | `PartPlace.pgx` | Entry through the `waitEndMove()` that lands the part at whichever of the three destinations that pick used (feed conveyor / accept / reject). |
| `toolOff` | `PartPlace.pgx` | The blocking `call tTool("OFF")` itself. |
| `visionWait` | `tkCycle.pgx` | `taskCreate "PartFinder"` through `wait(taskStatus("PartFinder")==1)` — time to hand the next detection off to the async PartFinder task. This is a dispatch/launch wait, not the vision result itself. |
| `finderWait` | `tkCycle.pgx` | `wait(bRunning["PartFinder"]==false)` after `PartPlace()` returns — extra time (if any) spent waiting for that async task to actually finish once the pick+place motion was already done. |

### What's NOT measured, and why

There is **no standalone "retreat" segment**. In `PartPlace.pgx`, the retreat
move(s) and the `movej` back to `jApera["Start"]` are only **queued**, never
waited on, before the function returns — and the very next `waitEndMove()`
in the whole project is the one at the top of the *next* cycle's
`PartPick.pgx` (after the `APPROACH` move). That single `waitEndMove()`
drains both the leftover retreat/return motion from the cycle that just
ended *and* the new approach move together — VAL3's motion queue doesn't
let you tell them apart without a new synchronization point in between.

Adding a `waitEndMove()` there would let you split them out, but it would
also be a **new motion/wait instruction** — exactly the kind of change this
bundle's safety verification is built to catch and refuse (see below). So
for this first pass, that time is left folded into the *next* cycle's
`approach` reading rather than invented. It's the same kind of tradeoff
Raiv-T1's own `LogCycleCSV.pgx` header documents for its own fields (its
`<retreat>` field has its own history of measuring the wrong thing before it
was fixed) — worth knowing going in rather than discovering later.

One consequence: the 7 measured segments plus that unmeasured carry-over do
**not** sum exactly to `cycle`. Expect a real, non-bug gap of a few tenths of
a second per cycle. If a future pass wants a true `retreat` segment, that
requires deliberately adding a `waitEndMove()` after the retreat move in
`PartPlace.pgx` — a real (tiny) behavior change that should be a separate,
explicitly-reviewed edit, not bundled into "just logging."

## CSV format (for `parse_backups.py`)

```
RAIV/CSV,A,<seq>,<cycle>,<approach>,<linApproach>,<toolOn>,<return>
RAIV/CSV,B,<seq>,<toolOff>,<visionWait>,<finderWait>,<partsFound>,<classesFound>
```

Two lines per cycle (T1 currently writes six) — smaller log footprint per
cycle here since PlateSorter has fewer existing counters worth reporting.
`<seq>` is on both lines so the parser can stitch them together and detect a
dropped line rather than mis-aligning columns, same convention as T1.
`parse_backups.py`'s existing `CYC_FIELDS` table will need a `T3`/PlateSorter
entry added for tags A/B with this field layout before it can parse these —
that's a follow-up step once you've deployed this and pulled a backup with
real data in it, not something done in this bundle.

## Safety verification

`verify.py` in this folder is adapted from Raiv-T1's own verification suite.
It stands in for the compiler and checks: every file is well-formed XML;
every identifier used in the modified programs is actually declared
somewhere (global, local, parameter, or an existing project program); no
`toString()` call is ever given a bool where VAL3 requires a num; every
`_sCycleTime` key referenced from code is pre-declared in the `.dtx` (VAL3
cannot add collection keys at runtime); every `UpdateCycleWindow` call is
passed a real num array/num index pair of the right size; every literal
array index used stays inside its declared size; the `.pjx` gained exactly
the two new program entries and lost nothing else; and — the core safety
check — **the ordered sequence of every motion and IO instruction
(`movej`/`movel`/`movec`/`dioSet`/`aioSet`/`wait`/`waitEndMove`/`stopMove`/
`resetMotion`/`enablePower`/`disablePower`/`taskCreate`/`taskKill`) in each
modified file is byte-identical to the original** — nothing was added,
removed, or reordered. Only `clock()`/`toString()`/`logMsg()`/array-write
statements and two new `call`s (`LogCycleCSV`, `UpdateCycleWindow`, neither
of which touches motion or IO) were ever inserted.

Current result, run against this folder:

```
checked 7 files, 116 globals, 44 _sCycleTime keys
new declarations: _nCycleTime, _nCycleTimeIndex, _nSegApproach, _nSegApproachIndex,
_nSegFinderWait, _nSegFinderWaitIndex, _nSegLast, _nSegLinearApproach,
_nSegLinearApproachIndex, _nSegReturn, _nSegReturnIndex, _nSegToolOff,
_nSegToolOffIndex, _nSegToolOn, _nSegToolOnIndex, _nSegVisionWait,
_nSegVisionWaitIndex, _sCycleTime, nCsvSeq
WARN  NEW FILE (no original to diff): LogCycleCSV.pgx
WARN  NEW FILE (no original to diff): UpdateCycleWindow.pgx

PASS  (0 fail, 2 warn)
```

The two warnings are expected and harmless — they just note that
`LogCycleCSV.pgx` and `UpdateCycleWindow.pgx` are brand new files, so there's
no original version of them to diff against.

## Merge instructions

1. Open the PlateSorter project in Staubli Robotics Studio (from a current
   backup or your working copy — not from this folder directly).
2. Copy in `PlateSorter.dtx` and `PlateSorter.pjx`, replacing the existing
   ones — or, if you prefer to hand-merge, add the new `<Data>` block (after
   `_pHere`, before `nClassesFound`) and the two new `<Program file=...>`
   lines to your current files instead of overwriting them wholesale.
3. Replace `tkCycle.pgx`, `PartPick.pgx`, `PartPlace.pgx` with the versions
   in this folder.
4. Add `LogCycleCSV.pgx` and `UpdateCycleWindow.pgx` as new programs in the
   project (SRS should pick them up once they're in the project folder and
   listed in the `.pjx`, which they now are).
5. Rebuild/recompile in SRS and let it flag anything before you transfer to
   the controller — that's the real compiler, this bundle's `verify.py` is
   only a stand-in for the checks that can be done without one.
6. Deploy to the controller and watch the first several cycles.

## What to watch on first run

- **No motion should look or sound any different.** Every insertion is a
  clock read, a string format, a log write, or a plain array assignment —
  nothing that touches speed, position, or timing of any move, wait, or IO
  signal. If anything about the physical cycle changes, that's a sign
  something in this bundle is wrong, not expected behavior.
- `nCsvSeq` starts at whatever it currently holds (0, most likely, since
  it's a brand-new global) and increments once per completed pick+place —
  confirm it's counting.
- Check a `user.log` after a few dozen cycles for `RAIV/CSV,A,...` and
  `RAIV/CSV,B,...` lines and sanity-check the numbers look like real seconds
  (not 0.00 across the board, which would mean a clock stamp landed in the
  wrong place).
- `approach` will read a bit high on the very first cycle after startup
  (nothing was queued from a "previous cycle" yet, so no carry-over there —
  actually this makes the very first cycle's `approach` reading the
  *cleanest* one, ironically) and should settle into a fairly stable range
  after that, aside from the carry-over effect described above.
- Log volume is modest (2 short lines per cycle vs. T1's 6), but keep an eye
  on `user.log` rotation/retention the same way you would for any added
  logging.

## Next steps (not done here)

- Add a PlateSorter/T3 entry to `parse_backups.py`'s cycle-line field table
  once a backup with real `RAIV/CSV` data exists to test against.
- No HMI/pendant page changes were made or attempted — same as T1's own
  precedent of deferring that; the new `_sCycleTime` keys exist for a future
  "Cycle Timing" page if you want one, but nothing binds to them yet.
- If a true `retreat` segment is wanted later, it needs a deliberate,
  separately-reviewed `waitEndMove()` addition in `PartPlace.pgx` — flagged
  above as an actual (tiny) behavior change, not a logging-only edit.
