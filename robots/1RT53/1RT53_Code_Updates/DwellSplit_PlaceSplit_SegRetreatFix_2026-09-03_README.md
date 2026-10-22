# Raiv-T1 — edits 1, 2 and 3 (binpick_TiePlates)

Prepared September 3, 2026 · Controller `F_24_0064095_C_004`
Built on the `Y-2026_M-09_D-02_17h48m` backup — verified byte-identical to what
is running now, all five files of `CycleDataLogging` included.

**Seven files plus one user page. Full application reload** (the `.dtx`
changed). **The `.pjx` is unchanged** — no new program was added — so leave it
alone, and the other 29 files with it.

| File | Was | Now |
|---|---|---|
| `tGripperEMH.pgx` | 865 | **5,106** |
| `tkCycle.pgx` | 49,585 | **65,673** |
| `Part_Accept.pgx` | 5,962 | **8,526** |
| `Part_Reject.pgx` | 4,218 | **5,417** |
| `ResetCycleStats.pgx` | 5,283 | **8,332** |
| `LogCycleCSV.pgx` | 4,439 | **12,026** |
| `binpick_TiePlates.dtx` | 41,340 | **45,917** |
| `interface/UserPageCycleStats.html` | 23,781 | **23,791** |

Most of that growth is comments. **No motion, speed, motion descriptor, IO
order or pick/place logic changed** — mechanically verified, see *How this was
checked* at the end.

---

## 1. Both magnet dwells are now tunable — 29% of the cycle

`nEMH_gripperDelay` was **one number serving both pulses**. Split:

| New global | Ships at | Was | Where |
|---|---|---|---|
| `nEMH_onDelay` | **0.5** | `nEMH_gripperDelay` | the GRIP pulse |
| `nEMH_offDelay` | **0.5** | `nEMH_gripperDelay` | the RELEASE pulse |
| `nGripSettle` | **0.35** | hard-coded `delay(0.35)` | the settle after the grip |

All three are `access="public"`, so they sweep from the SP2 data editor with no
reload. **All three ship at exactly the values that were hard-coded, so
deploying this changes nothing until you change a number.**

`nEMH_gripperDelay` stays declared and is now **referenced by no code**.
Changing it does nothing. I grepped the whole project — all 36 programs, both
libraries, both HMI folders — before deciding that was safe: it appeared only
in `tGripperEMH.pgx` and its own declaration, and **nothing anywhere writes
it**. `tGripperEMH` has exactly three callers, and all three are in this
bundle.

### The bench test this is gated on

I am not going to guess how long an electromagnet needs to make and break while
holding a steel tie plate. With a plate gripped and the arm parked:

1. Step `nEMH_onDelay` down 0.5 → 0.4 → 0.3 → 0.2, ten plates at each. Watch
   for a plate that doesn't come, or comes and slips.
2. Step `nEMH_offDelay` down the same way. Watch for a plate that stays stuck
   to the magnet, or drops late.
3. `nGripSettle` is a different question — it is the plate settling on the
   magnet, not the coil. Judge it by watching the first centimetres of the
   retreat for the plate shifting, not by the pick succeeding.

Tell me the two thresholds and I will wire them in with margin. If the answer
is "0.5 s is genuinely needed for both", edit 1 is off the table and edits 2–3
are where the remaining time is.

**One honest caveat about reading the result.** `SegMagnetOn` and `SegMagnetOff`
are each bounded inside their own pulse, so they will read back roughly whatever
you set. They **confirm a sweep took effect; they do not diagnose anything.**
The number that carries information is `SegDescend`, which holds the head start
that asserting `dDOemh_gripperOFF` early during the descent actually buys.

---

## 2. `place+return` is split seven ways

46% of the cycle was one opaque number. Now:

| New segment | What it is |
|---|---|
| `SegRetreat` | retreat off the belt **+ approach to the drop** (see edit 3) |
| `SegCapture` | the APERA trigger round-trip, or ~0 when the belt scan captured early |
| `SegDropClear` | time waiting on the `dDIDropClear` interlock |
| `SegDescend` | the 50 mm `movel` down, motion only |
| `SegMagnetOff` | the **release dwell alone** — the third tunable dwell, which was hiding in here |
| `SegPartsFound` | the `AperaPartsFound()` round-trip — **a second vision cost with no timer until now** |
| `SegReturn` | the remainder: retract queue, deferred-capture block, final `movej` queue |

and `SegGripperActuate` splits into `SegMagnetOn` + `SegGripSettle`.

Two identities hold **exactly** in the underlying numbers, because each group is
differences of *one* reading of the clock:

```
SegPlaceReturn    = SegCapture + SegDropClear + SegDescend
                  + SegMagnetOff + SegPartsFound + SegReturn
SegGripperActuate = SegMagnetOn + SegGripSettle
```

The parser now checks both per row (`seg_place_return_resid`,
`seg_gripper_resid`). Each field is rounded to 2 dp on the controller, so
expect a few hundredths; **more than ~0.05 means a boundary moved without the
arithmetic being updated.**

**Every boundary is a synchronisation point that already existed** — a
`waitEndMove`, an interlock `wait()`, or the return of a blocking socket call.
`Part_Accept`/`Part_Reject` take five clock readings into `_nPlaceClk` and
contain **no logic**; all the arithmetic lives in `tkCycle` in one place.

Two boundaries are *not* sync points, and the code says so rather than
pretending: `_nRetreatT0` is a bare `clock()` before two queue-only calls
(correct as a start — the arm is settled), and the window closes after
`movej(jTrajectoryStart)` is merely **queued**. That is deliberate — the
alternative is a `waitEndMove` that changes the motion — and it is exactly why
**`SegReturn` must not be read as motion time.** One thing to know before
reading a big `SegReturn`: `AperaOwnSocket` also runs in that span and can
legitimately block up to `nScanTimeout_s` (30 s) on a last-part cycle. That is
the cell parked out of shot waiting for the scan, not a slow robot.

---

## 3. `SegRetreat` is fixed

It read **0.00 on all 25 samples** because it timed a motion *queue*:
`movej`/`movel` only queue and return. Anyone reading the Cycle Timing page
concluded the retreat was free. It wasn't — it was unmeasured, and it was being
counted inside `SegPlaceReturn`.

Its end moved to the `waitEndMove()` that is **already there** in `Part_Accept`
with the arm at rest 50 mm above the drop. That drains `LINEAR_RETREAT`,
`RETREAT` and the drop-approach `movej` together.

**No `waitEndMove` was added anywhere.** The obvious fix — one after `RETREAT`
— would stop the arm at the retreat end point and break its blend into the drop
approach. That is a behaviour change, it costs time, and it adds exactly the
jerk you asked me to remove. **The measurement boundary moved; the motion did
not.**

### Schema drift — read before comparing runs

`SegRetreat` and `SegPlaceReturn` **both changed meaning.** `SegRetreat` goes
from 0.00 to a real number; `SegPlaceReturn` loses the retreat and drop-approach
motion it used to hide. The pair covers the same span as before to within a few
milliseconds. **Samples of those two keys from before 2026-09-03 are not
comparable with later ones** — the workbook's Header Key says so too.

---

## Two things that are *not* behaviour-neutral

I would rather name these than have you find them.

**1. The log gets 50% bigger.** Six lines per pick instead of four — roughly
6 MB/day into `user.log` against ~4 MB/day today. That accelerates rotation and
shortens how far back a backup's log reaches. `nCsvCounterEvery` is the relief
valve: lines C and D carry only cumulative counters, so sampling them loses
nothing. **Set it to 10 before a long production run** and volume drops to
~4.3 MB/day, below today's. It ships at **1** on purpose — the default should
reproduce today's line content exactly, and the valve should be a decision
someone makes, not one hidden in a default. The parser treats C and D as
optional, so a sampled row still reads `complete = yes`.

**2. Eight new `UpdateCycleWindow` calls and two extra `logMsg` per cycle.**
Each ring rescan is 25 iterations. Two of the new calls sit between the gripper
close and the retreat being queued, so the arm stands still for that long —
milliseconds, at rest, no blend at risk. I mention it because "no motion
changed" and "the timing is bit-for-bit identical" are not the same claim.

---

## The new segments are not on the pendant page

`UserPageCycleStats` has room for six segment rows and there are now fourteen.
Fitting eight more needs a layout change on a page I cannot render or test from
here, so I did not attempt it. **Read the new segments in the SP2 data editor
(`_sCycleTime` keys) or in the CSV**, lines E and F.

What I did change on that page is two **label strings only**, so it stops
lying: `Retreat` → `Retreat+Appr`, `Place+Return` → `Place (post-appr)`. The
bindings file is untouched and every bound id still exists.

Say the word and I will do the page as its own small change — probably a second
"Place Detail" page rather than squeezing the existing one.

### One display subtlety worth knowing

`SegDropClear` is **exactly 0 whenever the drop station was already clear**,
which is the normal case, and `UpdateCycleWindow` deliberately ignores zero
samples. So on the pendant its Average is a mean over *the cycles where
something actually happened*, and `CountOf` tells you how many of the last 25
those were — "the interlock cost us something on 3 of the last 25 picks". That
is a useful number, but it is **not** the per-cycle mean. **Use the CSV for the
per-cycle mean.**

This is also why the CSV no longer reads the `_sCycleTime` display strings. It
reads `_nSegLast[]`, the raw per-cycle samples, zeroed at the top of each pick.
Reading the strings would have logged the *previous* pick's number for any
segment that measured 0, and an **empty field** for one that had never measured
— putting a `,,` in the line and mis-aligning every column after it. That
would have hit most cycles.

---

## Merge

1. Copy the seven files into `usr/usrapp/binpick_TiePlates/` and the HTML into
   `usr/usrapp/binpick_TiePlates/interface/`. **Do not copy the `.pjx`** — it is
   unchanged.
2. Full application reload (the `.dtx` changed).
3. Confirm in the data editor that `nEMH_onDelay` = 0.5, `nEMH_offDelay` = 0.5,
   `nGripSettle` = 0.35 and `nCsvCounterEvery` = 1 all exist. **If they are
   missing the `.dtx` did not take and `tkCycle` will not compile.**
4. Run a batch. Then **save the application data from SP2 before pulling the
   backup** — that is what puts the live globals in the `.dtx`. Send me the
   backup and I will fold it into the workbook.

Watch on the first run: `seg_place_return_resid` and `seg_gripper_resid` near
zero, and `retreat_agrees = yes`, on every row.

---

## How this was checked

Nothing here can be compiled or run, so a mechanical suite stands in for the
compiler, plus an adversarial re-read of the whole change set against the
pristine originals. The suite (`verify.py`, shipped alongside) checks:

- XML well-formedness of every `.pgx`/`.dtx`/`.pjx`.
- **Every identifier declared** — globals against the `.dtx`, locals and
  parameters against each program.
- **`toString` on a `num` only.** Passing a bool is a compile error and it has
  already cost us two of them in this project.
- **Every `_sCycleTime` key exists in the `.dtx`** — VAL3 collections cannot
  gain keys at runtime. All 115.
- Every ring/index pair declared `num`, indices size 1, and **every literal
  array index inside its declared size**.
- **The ordered sequence of `movej`/`movel`/`dioSet`/`wait`/`waitEndMove` is
  identical to the original in every file.** Any addition, removal *or reorder*
  fails.
- **Dwell changes against an allowlist**, including the value each replacement
  must carry — so a rename cannot smuggle in a different dwell.
- BOM and line endings restored to each file's original convention, and any file
  that ended up byte-identical to the original is flagged so it can be dropped
  from the bundle rather than shipped for no reason.
- The `.pjx` compared as **bytes**, not decoded text.
- Bindings JSON against the ids that actually exist in each HTML page.

The adversarial pass found nine real defects in my first cut, all fixed here.
The two worth recording, because they are the kind that survive a clean check:

- **`SegGripperActuate ≠ SegMagnetOn + SegGripSettle`** in the first version.
  I had taken a fresh `clock()` per publish, so the publishes themselves leaked
  into the children and the identity drifted. Now one stamp, three differences.
- **The CSV read the display strings**, which is wrong for any segment that can
  legitimately be zero — see above. That was most cycles, and it would have
  produced empty fields and mis-aligned columns.

It also found five holes in the verification suite itself, which is why the
list above is longer than last time. The `.pjx` check in particular was
comparing decoded text and passing while the bytes had changed.

The parser was tested end-to-end against a synthetic log in the exact format
the new code emits — VAL3's right-padded `toString("3.2",…)`, a deliberately
dropped line F, C/D sampled away, and a zero-valued interlock — 6 cycles in,
6 rows out, all 16 timing fields matching, both residuals 0.00. Then re-run
against the real 17h48m four-line log: **17 rows, zero regressions**, and the
new columns blank on old data.
