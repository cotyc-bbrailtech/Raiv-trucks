# Raiv-Lab — Belt Clears on ~3in Lift, Not Camera-FOV-Clear (LAB_PlateSorter2)

Prepared: August 28, 2026
Scope: refines the last-part belt fast path added in
`LastPartBelt_Update_2026-08-28`. That update started the belt as soon as
the robot cleared the camera's field of view. This update starts it earlier
still — the instant the robot has physically lifted the last part ~3in
(`nBeltClearHeight_m`, tunable) off the conveyor — since that's all the belt
itself needs, independent of the wider clearance camera imaging needs.
**Builds on top of that prior update; both are needed together.**

## What's in this folder

This is a **patch bundle** — only the files that changed, at the top level
of `LAB_PlateSorter2` (no subfolders). It supersedes the `tkPartFinder.pgx`
and `LAB_PlateSorter2.dtx` from `LastPartBelt_Update_2026-08-28` — copy
these three over your project instead of (or in addition to, if you haven't
merged the prior update yet) that bundle's files.

| File | Status | What changed |
|---|---|---|
| `tkPartFinder.pgx` | Modified | Added a "belt kick" at the top of the loop that waits on a new lift-clearance flag instead of the camera-FOV-clear condition, for the last-part case only. |
| `tkMonitor_Robot.pgx` | Modified | Added the lift-clearance monitoring itself — new locally-computed `nTCP_beltLift_m` and `bBeltClear`. |
| `LAB_PlateSorter2.dtx` | Modified | 3 new globals: `bBeltClear`, `nTCP_beltLift_m`, `nBeltClearHeight_m` (public, default `0.0762` = 3in in meters — tune this without touching code). |

## Why this needed a small change outside tkPartFinder

You asked to rewrite `tkPartFinder`, and the belt-kick logic itself is
entirely there. But `tkPartFinder` has no cheap way to ask "how far off the
belt is the part right now" on its own — every other position check in this
app (`bAREA`, `bRobotAT`, `nDis_From`) is computed once per pass in
`tkMonitor_Robot`'s own paced loop and read elsewhere as a plain flag. That
loop was already deliberately paced (see the comment at its bottom, added
after CPU starvation from an earlier unpaced version caused cycle-time
jitter) specifically so extra position checks don't compete with the Cycle
task for CPU. I followed that same pattern rather than having
`tkPartFinder` call `here()` directly itself, which would reintroduce the
kind of unpaced-loop risk this codebase has already had to fix twice.

## The refinement, in detail

**Before this update:** the last-part fast path (previous bundle) waited on
the same condition the vision system needs to trigger a fresh capture:
```
wait(bAREA["conveyor"]==false or bRobotAT["capture"]==true or bAREA["rejectstation"]==true)
```
That's correctly sized for imaging — the camera needs the robot well clear.
But the belt itself doesn't need nearly that much clearance; it just needs
the part physically up off the conveyor surface. Gating the belt on the
camera's requirement means it starts later than it has to.

**Now:** a new flag, `bBeltClear`, goes true the moment the robot's TCP has
lifted **~3in above the exact point this part was picked from**
(`pBelt_START`, the same point `PartPick` computed and possibly nudged by
the vision pose transform for this specific part) — computed in
`tkMonitor_Robot`:
```
nTCP_beltLift_m=l_pHere.trsf.z-pBelt_START.trsf.z
if (getMoveId()>=250 and getMoveId()<300) and nTCP_beltLift_m>=nBeltClearHeight_m
  bBeltClear=true
else
  bBeltClear=false
endIf
```
`tkPartFinder` now waits on that instead, for the last-part case only, right
at the top of the loop, before the camera-FOV wait:
```
if bLastPart==true
  wait(bBeltClear==true)
  doBelt["FWD"]=true
endIf
```
Everything after that — the existing camera-FOV wait, and the "skip the 2
vision-only attempts" fast path from the prior update — is unchanged, just
renumbered/re-commented to make clear the belt is already running by the
time it's reached.

### Why `bBeltClear` is gated to `getMoveId()>=250 and <300`, not just the raw height

A first draft of this compared `nTCP_beltLift_m` to the threshold with no
other condition — and that's unsafe. `tkPartFinder`'s new `wait()` starts
evaluating right when the *previous* loop pass ends, which is essentially
the moment `PartPick` is called for this part — before the robot has even
moved toward the belt yet. At that instant the TCP is still sitting wherever
it was left (typically the capture pose, `jBelt["capt"]`), which — being a
pose chosen to give the camera a clear, unobstructed view — could easily
already be more than 3in above the belt's Z height on its own. A bare
height check would have read `bBeltClear==true` immediately, kicking the
belt on before the robot had even reached over to pick the part.

`getMoveId()` is the same mechanism `PartPick.pgx` already uses to tag its
own motion phases (`100`→`200`→`250`→`300`→`900`; `250`–`300` is
specifically the window between `tTool("ON")` and the retreat's
`movej(pBelt_END,...)`). Restricting `bBeltClear` to that window means the
height check can only ever fire during an actual retreat from a real pick —
never from an unrelated position elsewhere in the cycle. No other code in
this project sets a moveId in the 250–299 range (`PartPlace` uses 500s/600s,
`tkCycle`'s "clear camera FOV" move uses 750), so there's no cross-talk.

## On the belt running before the FOV-clear condition resolves

Once kicked on, the belt keeps running until the existing detector loop
(inside the camera-FOV-gated section) explicitly turns it off — same as
before this change, just starting a little earlier. I did not add a
separate timeout for this specific window, and want to be upfront about why:

`bAREA["conveyor"]` (part of the wait the belt used to depend on) goes false
as soon as the TCP's XY leaves the conveyor's footprint — and that happens
during the *same* retreat move that lifts the part past 3in, typically
within the same motion, well before `PartPlace` even begins (let alone
reaches an accept/reject overflow wait, which is the one place in this app
a cycle can dwell indefinitely). So in the normal case, the extra window
this change opens up — belt on, but not yet inside the tries-capped detector
loop — should be short, on the order of the tail end of one retreat move,
not something that can stretch out across a full place cycle.

That reasoning depends on the geometry of your actual retreat trajectory,
which I can't observe from here. **Please confirm during testing** that
`bAREA["conveyor"]` does in fact go false shortly after `bBeltClear` goes
true (e.g. watch both on a monitor page, or log the gap) — if some retreat
path lifts vertically without moving in X/Y for longer than expected, the
belt would run longer before the existing tries-capped logic takes over. If
that turns out to matter in practice, the fix is a bounded timeout on this
new wait — straightforward to add, just didn't want to guess at a duration
without seeing it run.

If the robot is disabled or faults for any reason during this window,
`tkMonitor_IO`'s existing "ARM NOT POWERED; FEEDER BELT OFF" logic still
forces the belt off unconditionally — that safety net is untouched.

## Merge steps

1. Back up your current `usrapp/LAB_PlateSorter2` folder (or keep whatever
   dated backup you're working from).
2. Copy all 3 files in this bundle into your live project, overwriting the
   existing ones — this supersedes `LastPartBelt_Update_2026-08-28`'s
   `tkPartFinder.pgx`/`LAB_PlateSorter2.dtx`.
3. Open the project in the VAL3 IDE, re-scan, and **build/compile clean
   before touching the real robot**.
4. Test in manual/reduced-speed mode first. Run the feeder down to its last
   part on purpose and confirm:
   - The belt starts noticeably earlier than before (right as the part
     clears the conveyor by ~3in, not after the robot reaches the capture
     pose).
   - It doesn't start too early — specifically, it should not start moving
     while the robot is still approaching to pick the part.
5. Watch `bAREA["conveyor"]` and `bBeltClear` together for a few last-part
   cycles (per the note above) to confirm the gap between them stays short.
6. Re-confirm the starved-feeder path is untouched: run the feeder empty and
   check `bMessage["Feeder"]` still comes on after `nDetectorTries` tries.
7. Only then run normal production and compare cycle time against the prior
   update.

## If 3in isn't the right number

`nBeltClearHeight_m` is a public global (default `0.0762` m = 3in) — adjust
it directly without touching either program file if testing shows the belt
needs a bit more or less clearance before it's safe to start moving.
