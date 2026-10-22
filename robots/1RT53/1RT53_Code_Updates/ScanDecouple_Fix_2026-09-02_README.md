# Raiv-T1 — Scan/Cycle decoupling fix (binpick_TiePlates)

Prepared: September 2, 2026 · Controller `F_24_0064095_C_004`
Built on the `Y-2026_M-09_D-02_14h14m` backup — the build you are running now.

**Three files. Copy over the existing ones and do a full application reload**
(the `.dtx` changed). The other eight files from yesterday's bundle are
unchanged — leave them alone.

| File | Was | Now |
|---|---|---|
| `tkBeltScan.pgx` | 14,017 | 15,384 |
| `tkCycle.pgx` | 43,625 | 46,754 |
| `binpick_TiePlates.dtx` | 35,379 | 37,263 |

---

## Your answer: `nCapDeferred` is not the problem, and I found a real defect

First, the deployment checked out. All 11 files are on the controller at exactly
the byte sizes I shipped, and the `.pjx` kept `autoload="true"` on both
libraries and the `s8.20.2cs9_BS4270` version string.

I said `nCapDeferred` must stay 0 **with the kick off**. The log shows
`bEarlyBeltKick` is **on** — so a deferral on every last-part pick is the design
working, not a fault. But it led straight to a real defect, so thank you for
reporting it.

## The headline: the change is working, and it is much faster

From `mnt/log/user.log`, comparing pick-to-pick intervals:

| Build | Window | Median | Mean |
|---|---|---|---|
| Yesterday's (`BeltCameraSeq`) | 07:19 → 11:04, 91 picks | **35.0 s** | 53.9 s |
| This one (`BeltScanParallel`) | 13:52 → 13:59, 22 picks | **15.0 s** | 20.4 s |

Median pick time went **35 s → 15 s**. Caveat worth stating: the new window is
only seven minutes against nearly four hours, so treat 15 s as promising rather
than settled. But it is a clean, large difference on contiguous intervals.

The scan itself is doing exactly what you asked for — belt on at the lift, belt
off on detection about 4.4 s later, robot moving the whole time:

```
13:58:14  early belt kick, lift 76 mm - belt scan armed
13:58:19  belt scan stopped belt on 1 plate(s)      (+4.4s)
13:58:29  early belt kick, lift 77 mm - belt scan armed
```

## The defect: `tkBeltScan` was corrupting the "last part" test

21 out of 21 scans logged **"stopped belt on 1 plate(s)"** — always exactly 1.
That is not a coincidence, it is structural: the scan stops on the *first* plate
it sees, so the count is always 1. And I had it writing that count into the
shared `nCountPlatesFound`.

`tkCycle` then evaluates, at the top of the **next** pick:

```
bLastPart=(bTrajectoryFound==true and nCountPlatesFound<=1)
```

So a 1 written by the scan made the next pick a "last part" pick, which fired
the kick, which ran the scan, which wrote 1 again. **Self-sustaining.** The log
shows 22 consecutive kicks — one per pick, no gaps.

Worse, the two counts mean different things. `nCountPlatesFound` belongs to
`AperaPartsFound` and the detect loops, which read the **pick** pipeline
(`sPipeline`). `tkBeltScan` reads the **detect** pipeline
(`"14in_plate det"`). I was letting one overwrite the other.

`tkBeltScan` now uses its own `nScanPartsDet` / `nScanClassesFound` /
`sScanClassID` and a local count, and touches none of
`nCountPlatesFound`, `sFounds`, `nPartsDet`, `nClassesFound`, `sClassID`. It
publishes `nScanPlates` as a diagnostic only. I verified mechanically that no
write to any of those five names remains in that file.

**What to expect after this fix:** the kick should fire only when the scene
actually goes down to one plate, not on every pick. If it still fires every
pick, that is real information — it means the belt genuinely presents one plate
at a time, and the feature is simply always applicable.

## The remaining 20 s: every 4th pick, and I can now show why

The new build's intervals are strikingly bimodal — three picks at ~14.5 s, then
one at ~35 s, repeating:

```
14, 14, 15, 14, [35], 15, 14, [35], 15, 14, [36], 14, 15, [35], ...
```

There were **6** of those 35 s picks, and **6** occurrences of my
`INSIDE a camera FoV cube` log line — a perfect 1:1 match. Looking inside one:

```
13:58:29  early belt kick - belt scan armed
13:58:33  belt scan stopped belt on 1 plate(s)
13:58:40  capturing with the arm reported INSIDE a camera FoV cube ...
13:59:04  The previous message appeared %d time(s)     <-- controller de-dup
13:59:04  early belt kick - belt scan armed
```

That de-dup line is the controller collapsing my message repeating many times
over 24 seconds. Two things follow:

1. **The cell is looping in a detect branch.** That message exists in only two
   places in the build you are running — the "No parts detected" tail and the
   "No Pickable Parts Found" tail. Repeating it means repeated passes through
   one of them. It is **not** in the deferred-capture block, so the deferred
   capture on the kick path is running clean.
2. **The capture is being taken with the arm reported inside a camera FoV
   cube**, every pass. A capture with the arm in shot gives no pickable
   trajectory, which sends the cell straight back into that branch. That is the
   loop.

This is not new — yesterday's build logged the equivalent message **93 times**,
and it waited 3 s before capturing anyway each time. It was costing you on every
pick. This change fixed three picks in four; the fourth is this.

I checked and ruled out the obvious alternative: there are **zero**
`Error Creating AREAS` / `Error Area` entries in the whole log, so the zone
cubes are being created and checked correctly. The FOV flags are real, not
stuck. (`_bStartFoV` does ship as `true` in the `.dtx`, which had me worried,
but the scan takes readings normally so it is clearly being updated.)

**What I could not determine, and what these three files now measure:** which
cube. My log line said "a cube" without saying which, and the controller's
de-duplication hid how often. So:

| New value | Meaning |
|---|---|
| `nFovHitStart` | captures taken with the arm inside `pStartCnvyrFoV` (835×835×1000) |
| `nFovHitEnd` | captures taken with the arm inside `pEndCnvyrFoV` (600×800×1030) |
| `nBranchBPasses` | passes through "No Pickable Parts Found" — bursts here mean the loop |
| `nScanPlates` | what the last scan stopped on |

Counters do not de-duplicate. The log line now also prints both flags and the
count. One short run tells us which cube contains `jApera_Trigger_pos`, and then
the fix is a geometry decision — re-teach the pose, or shrink that cube — which
is yours to make, not something I should guess at in code.

Those cubes are large: 835 mm and 600–800 mm on a side, over 1 m tall. It would
not be surprising if the trigger pose sits inside one.

## What I did not change

- **No motion, speeds, or pick/place logic**, same as before.
- **The branch-B feed loop is still not fixed.** It is now the prime suspect for
  the 20 s excursions rather than a theoretical concern, and `nBranchBPasses`
  will confirm it. The fix I would propose is still the same: feed only when the
  scene is genuinely empty, and when plates are present but unpickable, use the
  existing `l_nNOTrajectoryFound==2` jog to reshuffle instead of adding parts. I
  want your decision before touching production logic that has run this way for
  a year.
- **`AperaPartsFound` still does not zero `nPartsDet`** before its
  `apera_inspect`, so it can re-sum a stale reading — the same library
  behaviour that made the scan misfire. I deliberately left it: fixing it would
  make `nCountPlatesFound` read a true zero more often, which pushes the cell
  into the no-pickable-parts branch more often, and that branch is the one with
  the feed loop. It should be fixed *after* the branch-B decision, not before.

## After reload, confirm

`nScanPlates`, `nFovHitStart`, `nFovHitEnd`, `nBranchBPasses` all exist and read
0. If they are missing the `.dtx` did not take and `tkCycle` will not compile.

## Then run it and send me

1. **`nFovHitStart` vs `nFovHitEnd`** after a few minutes — this is the one I
   most want. It names the cube.
2. **`nBranchBPasses`** — and whether it jumps in bursts when the cell hesitates.
3. **Kick frequency.** Is it still every pick, or only when the belt runs down?
4. **Pick interval.** Still ~15 s on the good ones? Are the ~35 s ones gone,
   fewer, or unchanged?
5. A backup when you have one — the log has been better evidence than anything
   I could reason out from the source.

---

## Correction — first attempt at this file did not compile

The `.zip` you first received failed with `'_bStartFoV' : invalid type` at
`tkCycle.pgx` 617 and 747. That was mine: I wrote the new diagnostic as

```
logMsg("... Start="+toString("",_bStartFoV)+" End="+toString("",_bEndFoV)+" ...")
```

and VAL3's `toString()` formats a **num**, not a **bool**. There is no implicit
cast, so both call sites were type errors.

Fixed by naming the cube in words instead, which reads better anyway:

```
if _bStartFoV==true and _bEndFoV==true
  logMsg("RAIV/T1: capture with arm inside BOTH FoV cubes, nCount=...")
elseIf _bStartFoV==true
  logMsg("RAIV/T1: capture with arm inside the START (conveyor) FoV cube, nCount=...")
elseIf _bEndFoV==true
  logMsg("RAIV/T1: capture with arm inside the END (drop station) FoV cube, nCount=...")
endIf
```

So you get the cube named in the log as well as in the counters.

My pre-flight checks covered XML, BOMs, block balance, undeclared identifiers
and library references, but nothing checked **argument types on builtins** —
which is why this got through. I've added that check: it parses the real `type=`
attribute from the `.dtx` and each program's `<Local>`/`<Parameter>` blocks and
verifies every `toString()` argument is a `num`, plus flags any `bool` used in a
numeric comparison or arithmetic assignment. The whole bundle is clean under it
now.

The `.zip` and this file are the corrected versions; the byte size of
`tkCycle.pgx` in the table above is the corrected one.
