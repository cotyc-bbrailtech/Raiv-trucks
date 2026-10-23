# Raiv-T1 — Early trajectory trigger (binpick_TiePlates)

Prepared: September 2, 2026 · Controller `F_24_0064095_C_004`
Built on the `Y-2026_M-09_D-02_15h26m` backup — the build you are running now.

**Five files. Full application reload** (the `.dtx` changed). The other six from
the earlier bundles are unchanged — leave them alone.

| File | Was | Now |
|---|---|---|
| `tkBeltScan.pgx` | 15,384 | 22,309 |
| `tkCycle.pgx` | 46,754 | 48,688 |
| `Part_Accept.pgx` | 4,682 | 4,519 |
| `Part_Reject.pgx` | 4,491 | 4,218 |
| `binpick_TiePlates.dtx` | 37,263 | 39,377 |

**No motion parameters, speeds, or pick/place logic were changed.** One motion
is *removed* on the fast path — see below, and it removes it back to what the
original did.

---

## Your `nFovHitStart` vs `nFovHitEnd` answer, which settles the design

From the 14:28→15:11 run: **39 out of 39** "arm inside a FoV cube at capture"
reports named the **END (drop station)** cube. **Zero** named the START
(conveyor) cube.

That is the whole answer. The cube the old both-cubes test kept waiting on was
the **drop-station** cube — and the drop station does not obstruct the camera
the pick pipeline uses, which images the **conveyor**. So the wait was for
nothing. `pStartCnvyrFoV` is the only cube that can occlude the capture, and it
is clear at that point in the cycle.

That is exactly what makes your request safe to implement.

## What this does

`tkBeltScan` now fires the trajectory trigger **itself**, the instant its scan
completes. At that moment all three of your conditions are true at once:

- **the detector has run** — it just ran, that is why we are there;
- **the belt is stopped and settled** — `Output3` went false and the
  `nPartsSettle` delay has been served;
- **the robot is out of the conveyor camera's view** — tested, not assumed.

And a fourth that makes it clean: tkBeltScan **already owns the APERA socket**,
so no handshake is needed. It triggers, sets `bTrajTriggered`, then releases.

The robot is still mid-place-motion, carrying the part it just picked. It no
longer has to finish the drop and drive to `jApera_Trigger_pos` before vision is
asked anything. APERA computes during the place-and-return move, so the
`apera_wait_for_trajectory` in `tkCycle` should come back with the answer already
done instead of blocking.

Measured from your log, the gap from scan-complete to the next pick's lift is
about 10 s. That is the window this reclaims most of.

## The bonus: it removes a move I had added

When the early trigger fires, `tkCycle`'s park-and-capture block is skipped —
including its `movej(jApera_Trigger_pos)`. That park move was **mine**, added
for the deferred capture. Your original code goes:

```
Part_Accept (drop)  →  AperaPartsFound()  →  movej(jTrajectoryStart, mReach)
```

with no park in between. I verified that against the untouched original. So the
fast path now runs the **original motion path** — one fewer move than the build
you are running, on a path with a year of production behind it.

## Two things to watch, and one flag to kill it

**This is the only APERA call in the project made from a moving robot.**
`apera_trigger_trajectory` embeds `here(flange,world)` in its request, so the
pose it sends is sampled mid-motion. Reasons to expect that to be fine: the plan
is anchored on the explicit `jTrajectoryStart`/`jTrajectoryEnd` joints passed as
`-s`/`-e`, the current pose is a field every apera routine sends identically,
and `tkBeltScan`'s own detect calls already send a mid-motion pose — 108 scans
worth. But it is new, and whether APERA uses that pose to mask the robot out of
the point cloud is a vendor question I cannot answer from the source.

Second: `_bStartFoV` is checked, and the exposure happens some tens of
milliseconds later while the arm is still moving. Every previous capture in the
project had a `waitEndMove()` immediately before it, so "clear at the check"
implied "clear at the exposure" for free. It no longer does. Directionally the
arm is retreating *out* of the conveyor cube toward the drop, so it should be
benign — but the source cannot prove the place path never swings back through.

**`bEarlyTrigger = false`** reverts to capturing after the drop. Public, takes
effect on the next pick, no reload. **Turn it off first if trajectories start
coming back unpickable.** And the new log line
`early trajectory trigger returned an APERA ERROR` is there specifically to tell
you if the moving-robot capture is being rejected.

## What the review caught before this reached you

An adversarial pass over just this change found six defects, all in the new
code. Two mattered:

**The park-and-capture would have re-triggered over the early trigger.**
`tkCycle` tested `bTrajTriggered` *before* the scan could set it. If `tkCycle`
got there first — a coin flip, since its path is the place move plus the
`dDIDropClear` wait while tkBeltScan's is plate travel plus 1 s — it entered the
block, waited out the scan inside `AperaOwnSocket` (by which time the early
trigger *had* fired), and issued a **second** trigger for the same pick. Not a
socket hazard, but it would have thrown away the entire benefit *and* still made
the park move. On a starved feeder it would have won essentially always.

Fixed by hoisting the socket handshake **above** the `bTrajTriggered` test, so
the flag is final when it is read.

**That same hoist fixed a second one:** on the early path the handshake was
being skipped, so the `AperaPartsFound()` gate below could find `bScanDone`
still false and silently skip a call the original made unconditionally — leaving
`nCountPlatesFound` holding the *previous* pick's count, which then feeds
`bLastPart` and the branch routing.

The other four: the liveness heartbeat was frozen across the new block (a longer
`nFovClearTimeout_s` would have made `tkCycle` read the scan as dead and end the
cycle); the stand-down flags were sampled up to 3 s before the trigger, so an
Abort landing in that window still got a socket round-trip — `bAbort` is now
re-tested, for the same reason `tkCheckZone` tests it; there was no
`bAperaError` log after the new trigger; and the counters double-counted so the
change would not have been measurable.

## Counters, now mutually exclusive

| Value | Meaning |
|---|---|
| `nCapEarly` | fired by `tkBeltScan`, mid-place-motion — **this should dominate** |
| `nCapAtPlace` | fired in `Part_Accept` at the drop approach (the non-kick path) |
| `nCapAtTrigPos` | fired at `jApera_Trigger_pos` after the drop — should be near zero |
| `nCapDeferred` | `Part_Accept` **declined**; a cross-check, not a bucket |

`nCapEarly + nCapAtPlace + nCapAtTrigPos` = picks that captured.
`nCapDeferred` should equal `nCapEarly + nCapAtTrigPos`.

If `nCapAtTrigPos` is the one climbing, the early trigger is being declined and
the `early trajectory trigger skipped` log line says why.

## Also confirmed from this run

- **The kick fires on every pick, and that is correct.** 108 kicks, 108 scans,
  and the scan stopped on 1 plate 106 times and 2 plates twice. So
  `nCountPlatesFound<=1` is genuinely true nearly always — the belt really does
  present about one plate at a time. Last week's decoupling fix did not change
  the frequency, which means the every-pick kick was never an artifact. Good
  news: the feature is simply always applicable here.
- **Pick intervals: 69 of 107 at 14–15 s, 32 at 34–35 s.** Median 14 s, mean
  24 s. Still bimodal, still every fourth pick.
- **The 20 s excursions are the branch loop, not the capture.** Each slow pick
  brackets a burst of the same log line collapsed by the controller's
  de-duplication — repeated passes through a detect branch. `nBranchBPasses`
  will now count them. This is the branch-B feed loop, still awaiting your
  decision, and it is now the largest remaining item: roughly 30% of picks
  paying ~20 s.

## Merge

Copy the five files into `usr/usrapp/binpick_TiePlates/`, full reload. Then
confirm `bEarlyTrigger` reads **true** and `nCapEarly` / `nCapAtTrigPos` exist
and read 0. If they are missing the `.dtx` did not take and `tkCycle` will not
compile.

Note `bEarlyTrigger` ships true but **inert** while `bEarlyBeltKick` is false —
nothing sets `bScanForParts`, so there is no scan for it to act on.

## Test, supervised, reduced speed, hand on the stop

1. Kick **off** first. `nCapAtPlace` should track picks; `nCapEarly` and
   `nCapAtTrigPos` stay 0. Regression check.
2. Kick **on**. Watch the first few approaches after an early trigger closely —
   this is the one place a bad plan would reach `movej()`. Confirm the arm goes
   to `jTrajectoryStart` and approaches normally, with no jump.
3. Then send me: `nCapEarly` / `nCapAtPlace` / `nCapAtTrigPos` / `nCapDeferred`,
   `nBranchBPasses`, `nFovHitStart` / `nFovHitEnd`, and the pick interval.
   Any `APERA ERROR` or `trigger skipped` lines are the ones that matter most.
4. End Cycle, Stop and Abort each landing while a scan is running — belt must
   stop once and stay stopped, both `dDOConveyorON[0]` and `[1]`.

I would like a backup after this one too. The log has been better evidence than
anything I can reason out from the source, three times running now.
