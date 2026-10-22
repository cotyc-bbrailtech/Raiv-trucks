# Raiv-T1 — Per-cycle data logging (binpick_TiePlates)

Prepared: September 2, 2026 · Controller `F_24_0064095_C_004`
Built on the `Y-2026_M-09_D-02_16h25m` backup — the build you are running now.

**Five files. Full application reload** (the `.dtx` and `.pjx` both changed).
The other seven files are unchanged — leave them alone.

| File | Was | Now |
|---|---|---|
| `LogCycleCSV.pgx` | — | **4,439** (new) |
| `tkCycle.pgx` | 48,688 | 49,585 |
| `Part_Accept.pgx` | 4,519 | 5,962 |
| `binpick_TiePlates.dtx` | 39,377 | 41,340 |
| `binpick_TiePlates.pjx` | 1,915 | 1,954 |

The whole change is **three lines of code** in `tkCycle`, one new program, two
new globals, and one `.pjx` line. `Part_Accept` is **comments only** — I
verified that mechanically. **No motion, speeds, or pick/place logic changed.**

---

## 1. First — I got the last analysis wrong, and you caught it

You had plates **staged** on the belt, not a real run. So my headline conclusion
was wrong: the 14.5-minute stall and the plate count climbing 1 → 2 → 3 is not
evidence of a production overflow feed loop. With hand-placed plates, "detected
but not pickable" is the expected outcome, and the cell looping is it doing what
it should with parts it can't pick.

I should have asked what the run was before drawing a conclusion from it. What
still stands from that log: the early trigger fired 5 of 5 with no APERA error,
latency was 0 s from belt-stop to trigger, and two picks came in at 6 s and 8 s.
What does **not** stand is anything I said about the feed loop being the
dominant production cost. **I've dropped the branch-B proposal** — I was asking
you to change a year-old production path on the strength of a staging test.

## 2. Data collection — shipped and tested

`LogCycleCSV.pgx` writes four CSV lines to the controller log on every cycle:

```
RAIV/CSV,A,<seq>,<cycle>,<approach>,<linApproach>,<gripper>,<retreat>
RAIV/CSV,B,<seq>,<placeReturn>,<visionWait>,<scanPlates>,<platesFound>,<visionValid>
RAIV/CSV,C,<seq>,<capEarly>,<capAtPlace>,<capAtTrigPos>,<capDeferred>
RAIV/CSV,D,<seq>,<branchB>,<fovStart>,<fovEnd>,<pickLiftSeq>,<liftMm>
```

**Why the log rather than the data editor.** Ordinary VAL3 globals never reach a
backup — a backup captures on-disk state, and nothing writes live values back to
the `.dtx`. That's why every counter I've added has read as its shipped default
in all thirteen backups, and why the only way to see them so far has been for
you to stand at the pendant. `logMsg()` lands in `mnt/log/user.log` inside
`logArchive.zip`, which *is* captured. Same route the Lab cell uses.

Four short lines rather than one wide one because `logMsg` caps at 255 bytes;
`<seq>` is on each so a dropped line shows as a gap instead of silently
mis-aligning the columns. The segment times are read straight from the
`_sCycleTime[]` strings `UpdateCycleWindow` already wrote — no new arithmetic, so
the logged numbers are exactly what the Cycle Timing page shows.

**On your OneDrive, already updated and re-run:**

- `Metrics_RT-1_F_24_0064095_C_004/parse_backups.py` now emits
  `F_24_0064095_C_004_cycles_ALL.csv` — one row per pick.
- It also accepts backup **folders** now, in the pendant's own
  `Y-2026_M-09_D-02_16h25m` naming, so you can drop them in without re-zipping
  ~10 MB each. I symlinked today's six in; **12 of 13 backups now parse**
  (5,044 unique events, up from 4,390).
- A OneDrive **cloud-only** backup used to abort the whole run with `Errno 22`.
  It's now reported and skipped. One backup (`09h36m`) still has a cloud-only
  `.dtx` — open that folder in Explorer, or right-click → *Always keep on this
  device*, and re-run to pick it up.

I tested the cycle parser end-to-end against a synthetic log in the exact format
the VAL3 code emits, including the leading spaces `toString("6.0",n)` produces.
3 cycles in, 3 complete rows out, columns aligned.

**Three derived columns worth your attention:**

| Column | Meaning |
|---|---|
| `seg_sum_s` | the six segment timers added up |
| `unaccounted_s` | `cycle_s − seg_sum_s` — **time no segment timer covers** |
| `complete` | `yes` only if all four lines survived for that `seq` |

`unaccounted_s` is the one I'd watch. In the synthetic test a 14.2 s cycle had
11.15 s of measured segments and **3.05 s unaccounted** — dwell, interlock waits
and queue latency all land there. If that's where your time is going, it will
show up immediately and it is not something the existing timers can see.

**Read `vision_wait_valid` before averaging `seg_vision_wait_s`.** When the
vision query is skipped, that segment isn't measured and the field carries the
*previous* cycle's number. I added the flag specifically so those rows get
dropped rather than quietly biasing the average. Counters are cumulative —
difference consecutive rows for per-cycle rates.

## 3. Motion — I built what you chose, then reverted it. Here's why

You picked flow control **plus** tuning `mNomSpeed`. I implemented both. An
adversarial review then found a **part-drop hazard** in the flow-control half,
and I confirmed it against the source. It is not shipped.

**The hazard.** `Part_Accept` line 99 is
`dioSet(dDOemh_gripperOFF,1)` — the magnet release — and it fires *before*
`tGripperEMH("OFF")`. That's deliberate in your original: it gives the release a
head start during the 50 mm descent. But `movej`/`movel` only **queue** motion
and return immediately, and I confirmed there is **no `waitEndMove()` between
the RETREAT waypoints in `tkCycle` and the `Part_Accept` call**. So that
`waitEndMove()` I wanted to remove is not just holding the arm still for the
camera — it is the **synchronisation point between the task and the motion
queue**. Remove it and the task runs ahead to the release output while the arm
may still be executing the retreat, millimetres above the conveyor, holding the
plate. It would release the plate in flight, over the belt, and then descend
empty into the drop station.

Reduced speed does not help — it drops the plate from a *slower* arm at the same
wrong place. So there was no safe way to test it.

**The descriptor half was wrong too, and for a reason worth recording.** I
claimed `mNomSpeed` couldn't blend because its `leave`/`reach` were at defaults.
The review checked the controller's **own stock template**,
`usr/templates/default/default.dtx`:

```
blend="joint" accel="100" vel="100" decel="100" leave="50" reach="50"
```

So the default `leave`/`reach` are **50, not 0** — that move could already
blend. My "match the neighbours" value of 10 would have made **both corners of
the plate-carrying move about 5× tighter** while raising acceleration 44%. A
tighter corner taken harder is the worst combination for a magnetically held
plate, and the exact opposite of the smoothing you asked for. I had inferred the
default from what SP2 stores in this project; the template settles it, and I
should have looked there first.

`mNomSpeed` is back to defaults, with that finding written into the `.dtx` as a
comment so nobody repeats it. `Part_Accept` keeps its unconditional
`waitEndMove()`, now with a note explaining that it is load-bearing for the
magnet release.

### Where the pause actually is

Re-reading the mag-on → mag-off window with the queue semantics straight, the
retreat waypoints and the drop approach were **already blended** — there is no
`waitEndMove()` between them. So the jerk isn't a missing blend. What's there is
**dwell**:

| Source | Cost per pick |
|---|---|
| `tGripperEMH("ON")` — `waitEndMove()` + `delay(nEMH_gripperDelay)` | 0.5 s |
| `tkCycle`'s extra `delay(0.35)` after the gripper arms | 0.35 s |
| `tGripperEMH("OFF")` — `waitEndMove()` + `delay(nEMH_gripperDelay)` | 0.5 s |
| **total fixed dwell** | **~1.35 s** |

Plus the `waitEndMove()` at the approach and the `dDIDropClear` interlock, both
of which have to stay.

`nEMH_gripperDelay` is one public number used for both the grip and the release
pulse. **If the magnet doesn't need a full 0.5 s to make and break, that is the
biggest safe win available here** — it's a dwell reduction, not a path or
acceleration change, so it cannot throw a plate. But how long the coil actually
needs is a bench measurement, not something I can read out of the source.

### What I'd do next, in order

1. **Deploy this logging and run a real production batch.** `unaccounted_s` will
   tell us whether the dwell is genuinely where the time goes, or whether it's
   somewhere neither of us has looked. That's one run, zero risk.
2. **Bench-test the magnet.** With a plate gripped and the arm parked: how short
   can `nEMH_gripperDelay` go before grip or release becomes unreliable? Tune it
   down in steps from 0.5 s. This is the safe smoothing.
3. **Only then consider `accel`/`decel`.** If you still want it, `mNomSpeed`
   `accel`/`decel` 100 → 144 alone (leaving `leave`/`reach` at 50) is a
   reasonable single-variable change — but it needs the magnet hold margin
   measured first: jog the drop approach with a plate gripped at 25/50/100%
   override and watch for slip. There is nothing in the source about holding
   force, plate mass or contact area, so it cannot be settled on paper.

## Merge

Copy the five files into `usr/usrapp/binpick_TiePlates/`, full reload. Then
confirm `nCsvSeq` and `nVisionWaitValid` exist and read 0. If they're missing,
the `.dtx` didn't take and `tkCycle` won't compile.

## One thing to keep an eye on

Four log lines per pick at ~14 s is roughly **1.4 MB/day** added to
`user.log`. That accelerates rotation, so `logArchive.zip` in a backup will
reach back over a shorter window than before. Worth checking the CS9's
`user.log` size and file count before a multi-day run, so the CSV doesn't evict
the diagnostics it's meant to be read alongside. If it becomes a problem, the
fix is to drop lines C and D to every Nth cycle — the counters are cumulative,
so they lose nothing by being sampled.
