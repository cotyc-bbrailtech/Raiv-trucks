# Raiv-T1 — TCP standstill sampler

**Six files**, built on `Y-2026_M-09_D-10_13h53m`. `_original/` is byte-identical
to what is on the controller now.

| file | on controller | this build | diff |
|---|---:|---:|---|
| `tkIOMonitor.pgx` | 9,577 | **13,717** | +85, **−0** |
| `Part_Accept.pgx` | 20,561 | **23,801** | +57, −2 *(the capture bound, previous bundle)* |
| `LogCycleCSV.pgx` | 29,065 | **30,290** | +23, −1 |
| `interface/UserPageOptions.html` | 15,575 | **18,649** | +15, −0 |
| `interface/UserPageOptions.bindings.json` | 5,748 | **7,076** | +62, −0 |
| `binpick_TiePlates_TEST.dtx` | (54,769) | **56,473** | 13 declarations added, no value changed |

This supersedes `CaptureBound_2026-09-10` — it contains that bundle too, so
deploy this one instead if you have not already deployed that.

**Both experiments ship off.** `bStallSample` false, `nCapFovX_mm` 9999.

---

## What the Stäubli document told us

Three things, and the first one settles an open question.

**1. It explains the `mReach` result.** From the blending slide: *"Since wait is
a blocking instruction, the program pointer can never reach the waitEndMove to
cancel the leave... only a portion of the trajectory is drawn... the robot will
stop on trajectory since it cannot reach the higher % of completion."*

A blend needs its **successor move queued**. `movej(jTrajectoryStart, mReach)`
is followed by a blocking wait in `apera_wait_for_trajectory`, so nothing gets
queued, the blend cannot execute, and the arm decelerates and stops *inside* the
300 mm zone — short of the point. The approach then pays for the shortfall.
That is the +0.39 s I measured, and the mechanism is now the vendor's rather
than my guess.

**2. Do NOT repeat that experiment on `mCycle`.** `apera_follow_trajectory`
turns out to be a pure queuing loop:

```
for l_nLoop=0 to nAperaTrajectorySections[l_nSection]-1
  movej(jAperaTrajectory[l_nIndex+l_nLoop],x_tTool,x_mSpeed)
endFor
```

So `mCycle`'s 100 mm zone is doing real work *between the trajectory's own
waypoints*. Zeroing it would stop the arm at every intermediate point. `mReach`
governed a single move with a blocking wait behind it — pure waste. Identical
setting, opposite verdict, and the difference is only visible once you read the
library.

**3. The asymmetry.** Your outbound path stops dead twice; the inbound path
never stops.

```
APPROACH (mCycle, blend 100)  -> waitEndMove()                 <- FULL STOP
dioSet(dDOAirStream,1)
LINEAR_APPROACH (mLinearMove) -> waitEndMove() + isSettled()   <- FULL STOP
[grip]
LINEAR_RETREAT -> RETREAT -> drop-approach movej               <- no stop, blended
```

`tkCycle` L281–286: the comment reads *"Turn on AirSteream to clear pick point
of dibris"*, and the `waitEndMove()` sits between that comment and the `dioSet`.
**The arm comes to a complete standstill so an output can be toggled.** That is
exactly the case `getMoveId()` exists for — assert the IO at a percentage of the
move and let the two blend. The second stop is a real settle before the magnet
grips and should stay.

## Why this bundle measures instead of fixing

I do not know whether that standstill costs 0.05 s or 0.35 s, and it is the
motion path. So: how many seconds a pick is actually spent standing still, and
where.

`tkIOMonitor` samples the TCP every pass, differentiates with `distance()`, and
times every interval below `nStallSpeed_mms`. New **line J**:

```
RAIV/CSV,J,<seq>,<stallCount>,<stallTotal>,<stallLast>,<stallLastX>,<stallMax>,<loopMs>,<loopMax>
```

`stallCount` and `stallTotal` are cumulative — difference two consecutive picks
and you have **standstills per pick and dead seconds per pick**. `stallLastX`
gives the world X of the most recent one, which separates the pick-side stops
(x −304…+97) from the drop-side (x +563).

### The honesty field

**A standstill shorter than one monitor loop is invisible to this.** So the loop
period is published, and so is its worst case. **Read `loop ms` first**: if
`nMonLoopMax_ms` is large, the counts are floor values, not measurements. Same
discipline as `nFovGeomMismatch` in the last bundle, and it exists for the same
reason — a number that looks like a measurement and is not is worse than none.

### Why it is gated off, and at the bottom of the loop

`tkIOMonitor` services `dDIAbort` at the **top** of every pass. Anything that
slows that loop slows the abort response. So the sampler is the last thing
before `delay(0)`, and `bStallSample` ships **false** — with it false the whole
block is one bool test. **Turn it on only with somebody at the cell**, and turn
it off afterwards. `verify.py` §7m(b) asserts the placement, because "at the
bottom" is a safety property here, not tidiness.

## Reading it

| field | what it tells you |
|---|---|
| stalls per pick | expect ~3–4: the two outbound stops, the drop approach, the vision wait |
| **dead seconds per pick** | the headline. Against a 3.87 s cycle |
| `stallLastX` | world X — which stop it was |
| `max` | the longest single standstill |
| **`loop ms`** | **read first.** Large = the rest are floor values |

If the APPROACH junction turns out to be worth 0.2 s or more, the `getMoveId`
change is worth doing and I will build it. If it is 0.05 s, it is not worth
touching the motion path and we should look at the dwells on steel instead.

## Verification

`verify.py` **PASS (0 fail, 6 warn)** · `mutate.py` **98/98 caught, 0 missed**.

New §7m, ten new mutations. The invariants are about the sampler being inert
when off, honest when on, and unable to touch anything: every write is inside
the gate; it is the last statement before `delay(0)`; no motion or output from
inside it; the speed divide is guarded against a zero interval; it publishes
both its loop period and the worst one; switching it off mid-stall forgets the
partial episode rather than closing it later against a stale `t0` and logging a
fictitious duration; single writer; and **no other program may branch on any of
the eight published values**.

### §11 paid off again, in the direction I did not expect

The unproven-function check flagged `getMonitorSpeed` as a **stale**
`UNPROVEN_OK` entry — it went onto the controller in the 09-09 bundle and
compiled, so it is now in the proven set. `UNPROVEN_OK` is empty again, which
is the healthy state.

Worth being precise about what that means: the bar §11 enforces is *"appears in
code that compiles on this controller"*, and deployed code clears it. `distance()`
is proven by `PartPicked` L19, `here()` and `position()` by the monitorArea
library. `fmod` never cleared it and never will.

**When the `getMoveId` work happens, §11 will stop it**, because `getMoveId` and
`setMoveId` appear **zero times** in all 52 programs. That is correct — they
will go into `UNPROVEN_OK` citing this PDF, deliberately, rather than slipping
in unnoticed.

## Not verified — nothing here compiles or runs

- the thirteen new `.dtx` globals resolve
- `tkIOMonitor` had **no `<Locals>` block at all**; this adds one with ten
  locals. Worth a glance in the IDE, it is the only structural change to that
  file
- `distance(l_pTcpPrev,l_pTcpNow)` on two `here()` results — proven in
  `PartPicked`, but on `point` variables rather than globals
- the eleven new Options controls land in the band freed when `btn1` and
  `btn1_Copy1` moved up to the 124–126 row

## Test it

1. Deploy. Leave both toggles off, run 25 picks — cycle 3.87, no line J. No-op check.
2. Press **Stall Sampler**. Read **`loop ms`** before anything else.
3. Run 50 picks. Difference the first and last `stallCount` / `stallTotal` and
   divide by the picks between them.
4. Switch it back off before leaving the cell.

## Back out

Copy the six files from `_original/` back, or leave both toggles off — with
`bStallSample` false and `nCapFovX_mm` 9999 nothing in this bundle executes.
