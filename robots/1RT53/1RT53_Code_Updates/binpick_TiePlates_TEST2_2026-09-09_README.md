# `binpick_TiePlates_TEST.dtx` (rev 2) — one line changed

Built from the `15h22m` backup's `.dtx` — the file on the controller right now,
`cmp`-confirmed identical to the one I sent last time. **One value changes:**

```
mReach   leave="300" reach="300"   ->   blend="off" leave="0" reach="0"
```

Everything else — the two dwells, the tool, both toggles, all fourteen
instrumentation globals — stays exactly as it is on the machine.

---

## Why: the blend zone costs about a third of a second a pick

Run 13 came in at **4.57 s**, not the 4.2–4.3 s I predicted. The whole miss is
in one segment.

| | approach | place+return | vision wait | cycle | `mReach` |
|---|---:|---:|---:|---:|---|
| run 8, picks 180–294 (steel, off 0.25) | **0.60** | 0.68 | 0.88 | 4.29 | blend off |
| run 10 (rubber, off 0.5) | **0.60** | 0.82 | 0.59 | 4.48 | blend off |
| run 11 + 12 (rubber, off 0.5) | **0.59** | 0.82 | 0.55 | 4.81 | blend off |
| **run 13 (rubber, off 0.25)** | **0.98** | 0.64 | 0.72 | **4.57** | **300 / 300** |
| run 9 (steel, off 1.0) | **1.11** | 1.32 | 0.19 | 4.75 | 300 / 300 |

`seg_approach_s` sits at 0.59–0.60 in every run with `mReach` blended off and at
0.98–1.11 in every run with the 300 mm zones. Six for six, and the two
alternative explanations are both ruled out by the table: run 8's block runs
off-delay 0.25 with a 0.60 approach, so the dwell is not doing it, and runs
10–12 are rubber plates with a 0.60 approach, so the plates are not doing it
either.

**The mechanism.** `seg_approach_s` brackets
`apera_follow_trajectory("APPROACH", tSchunkEMH084, mCycle)` — it uses `mCycle`,
not `mReach`, so this is indirect. `mReach` governs the move *before* it,
`movej(jTrajectoryStart, tSchunkEMH084, mReach)` at `tkCycle` L532. A reach zone
of 300 mm means the controller calls that point reached while the arm is still
up to 300 mm short of it. The approach then has to start from wherever the arm
actually is and cover the shortfall — so the blend does not remove the work, it
moves it into the next segment and adds to it.

The books roughly balance: place+return gives back about 0.04 s at matched
dwell (0.68 → 0.64) while approach costs 0.38 s. **Net ≈ 0.34 s a pick against
you.**

**I got this backwards earlier.** I had `mReach` on the restore list because my
deploy had changed it and changing it was not mine to do. Putting it back was
right; assuming the operator's value was the faster one was not. On the
evidence, the blend-off value my `.dtx` accidentally introduced is the quicker
of the two.

**Which is why this is a test, not a fix.** Somebody set 300/300 on purpose and
I do not know what for. The CTC comment sitting directly above that `movej`
reads *"mReach has better results than mBlend or mCycle... Robot jittered at
point"* — so this descriptor has a history of being tuned for motion quality at
exactly this waypoint. If the arm jitters or knocks at `jTrajectoryStart`, put
300/300 straight back and tell me; 0.34 s is not worth a mark on a plate.

Expect roughly **4.2 s** if the reading is right.

---

## The early-trigger experiment did not run

`cap_early` is still 0, and this time the reason is definite rather than a
mystery. The early trigger at `tkBeltScan` L488 sits **inside the belt-scan
branch**, below `bScanFoundParts=true` at L400 — it only executes when the belt
has advanced and delivered plates.

Run 13 had **no belt movement at all**: `batch_at_pick` stayed 0 across all 45
picks, zero beam-break edges, `scan_plates` 0. With plates hand-staged and the
feeder idle, that branch is unreachable, so turning `bEarlyBeltKick` back on
could not have changed anything.

**That question needs the feeder actually cycling to answer.** It is not a
dwell or descriptor setting, and no amount of static-plate running will reach
it.

## The one number that is now solid

`apera_latency_s` reads **1.37 s** — median 1.37, range 1.30–1.42, across runs
11, 12 and 13, at three different dwell combinations. APERA's round trip is a
constant and does not care what the dwells are set to.

That makes the vision-wait arithmetic simple. After the at-place trigger there
is only `magnet_off` + `place_return` ≈ 0.9 s of motion before the program needs
the answer, so ~0.5–0.7 s of the 1.37 s cannot be hidden. The long off-delay
"solved" it by manufacturing 0.75 s of fake motion, which cost more than it
saved. **With the trigger where it is, this is structural** — the only real fix
is triggering earlier, and the only earlier trigger in the code is the
belt-advance one above.

## Still rubber

`grip_part_at_pick`, `grip_mag_at_pick` and `grip_part_at_drop` are 0 on all 45
picks of run 13, as expected. No cycle time in any of runs 10–13 is a pick rate.

## Verification

`verify.py` **PASS (0 fail, 6 warn)**, `mutate.py` **55/55 caught, 0 missed**.

The `INTENTIONAL` table now holds one entry, and its "changes from" value is
checked against a fresh copy of the `15h22m` live `.dtx` — so if you have
re-tuned `mReach` on the machine since that backup, verification fails rather
than letting this file overwrite you.

*(One repair worth recording: the mutation that strips the reason off an
`INTENTIONAL` entry was passing because it broke `verify.py`'s syntax and the
crash counted as a catch. A mutation that is caught for the wrong reason is not
covered. It now edits cleanly and trips the intended check.)*

## Back out

`_ctrl/binpick_TiePlates_live.dtx` is the 53,337-byte file on the controller
now. Rename and copy it back.
