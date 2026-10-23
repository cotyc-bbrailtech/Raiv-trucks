# Raiv-T1 — the early-kick arming threshold

**Three files**, built on `Y-2026_M-09_D-11_14h40m`. `_original/` is
byte-identical to what is on the controller now.

| file | on controller | this build | diff |
|---|---:|---:|---|
| `tkCycle.pgx` | 76,325 | **79,690** | +59, **−1** |
| `LogCycleCSV.pgx` | 32,356 | **33,302** | +15, −1 |
| `binpick_TiePlates_TEST.dtx` | (55,393) | **55,722** | 3 declarations added, **no value changed** |

The two removed lines are `bLastPart=(... nCountPlatesFound<=1)` and one
FORMAT-header line that gained a continuation.

**`nLastPartThreshold` ships at 1** — the number that was hard-coded. Deploying
this cannot change which belt-advance path the cell takes.

---

## What this changes, and what it is worth

```
bLastPart = (bTrajectoryFound==true and nCountPlatesFound <= l_nLPThr)
```

That is the only thing this bundle alters. The threshold was a literal `1`; it
is now a clamped local seeded from a tunable.

Run 20, 203 picks, 63 belt advances:

| path | advances | cost |
|---|--:|--:|
| armed → kick → scan → early trigger, overlapped with the pick | 26 | ~0 |
| **not armed → scene runs dry → Branch B** | **34** | **3.36 s, arm parked** |

**+0.56 s on every pick, decided by that one comparison.** And 92% of early
triggers fire on a pick where the count is ≤ 1, against a 6% baseline — the
gate is doing nothing else.

The count does not reach 1 because it includes the plate in the gripper. You
watched it; the log agrees. `nCountPlatesFound` has read 0 exactly **three
times in 511 picks** while the belt genuinely empties every six, and turning
Capture @ FoV on — which fires the capture with the arm still over the
conveyor — lifts the mean count 2.89 → 3.31 and collapses the "count = 1"
bucket from 21% of picks to 10%. With a phantom plate in the count, an empty
belt reads **1** and one-real-plate-left reads **2**.

## This is a workaround

The real fix is masking the gripper out of the APERA pipeline so the count
means what `bLastPart` thinks it means. Raising this threshold buys the cycle
time back without fixing the cause, and if the pipeline is ever corrected the
threshold should go back to 1. That is worth writing down now rather than
rediscovering it in six months, so it is in the code comment too.

## The trade you are being handed

**At 2 the belt advances while one real plate is still in the field.**
`tkBeltScan` stops the belt as soon as it sees new plates, so that plate moves
downstream rather than disappearing — but whether it is still pickable there is
a question about *your* conveyor, which I have never seen. That is why this
ships at 1 and gets turned up by somebody standing at the cell.

**Clamped 1 to 5, and the low clamp matters.** At 0 the test becomes
"count ≤ 0 **and** a trajectory was found", which can only ever be true on the
zero-part scene the original comment warns about — the Raiv-Lab hang, reachable
by typing a 0 into the data editor. It is now untypeable. The upper clamp is 5:
above that the kick arms on nearly every pick and the belt runs continuously,
which is not a sweep, it is a fault.

The clamp is applied to a **local**. Code here does not write a value you own.

## What gets logged

Three fields **appended** to line K:

```
... ,<loopTopWait>,<loopTopCount>,<lastPartThr>,<countAtArm>,<lastPartArmed>
```

Appended, never inserted. The parser zips names onto values, so a trailing
field an older parser does not know about is dropped harmlessly, while an
inserted one would shift every column after it **and still parse cleanly** —
a silent corruption of the whole history. §7o(g) and a mutation both enforce it.

`countAtArm` is what the gate actually saw. It is the number that separates
"the threshold is too low" from "the scene really was full", and without it a
sweep is guesswork.

## Verification

`verify.py` **PASS (0 fail, 6 warn)** · `mutate.py` **122/122 caught, 0 missed**.

New §7o, eleven new mutations. The invariants: it ships at 1 (checked in two
independent places); **the `bTrajectoryFound` half survives** — losing it is the
Raiv-Lab hang and it gets its own mutation; the test is on the clamped local
and uses `<=`, not `<`; both clamps exist and the low one is 1; no code writes
the tunable; **no other program may read the threshold** — `tkCheckZone` and
`tkBeltScan` act on `bLastPart`, and a second derivation is how two tasks come
to disagree; `LogCycleCSV` may log it but not compare it; the two counters are
single-writer and nothing branches on them; and the first twelve line-K fields
are unchanged.

## Not verified — nothing here compiles or runs

- the three new `.dtx` globals resolve and `l_nLPThr` is accepted as a `num` local
- line K is now ~120 bytes, still well inside the 255-byte `logMsg` cap

## Test it

1. Deploy, leave the threshold at **1**, run 50 picks. `lastPartThr` reads 1,
   and the Branch B rate should be unchanged at roughly one pass per 6 picks.
   That is the no-op check and it is the whole claim.
2. Set it to **2** in SP2 — live, no reload. **Have somebody watching the
   conveyor**, because this is the run where the belt starts moving with a
   plate still out.
3. Expect the Branch B rate to fall sharply and `lastPartArmed` to climb on
   most picks. Watch `plates_found` and the APERA error line, same as the FoV
   sweep.
4. If it holds clean, ~4.55 → ~4.0 s a pick. Send the backup and I will check
   whether the advances really moved onto the sensor path or just moved the
   cost somewhere I have not instrumented yet — that has happened twice now.

## Back out

Set `nLastPartThreshold` back to 1 from the data editor — no reload, no
redeploy. Or copy the three files from `_original/` back.
