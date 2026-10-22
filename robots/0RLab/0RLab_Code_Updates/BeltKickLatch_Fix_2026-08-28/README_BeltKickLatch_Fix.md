# BeltKickLatch_Fix — 2026-08-28

Fixes the stall behind **"jogged conveyor one part into FOV for pick, will not jog
conveyor for next part."**

This is a defect in my own `BeltClear3in_Update` change, not in your original code.
Three separate faults in the same trigger, all fixed here.

## What's in this folder

| File | Change |
|---|---|
| `tkPartFinder.pgx` | Belt-kick wait is now **bounded** and consumes the latch; can no longer block forever |
| `tkMonitor_Robot.pgx` | `bBeltClear` is now a **set-only latch**, measured from the real grip height, correct units |
| `PartPick.pgx` | **New** in this bundle. Arms the latch and records the true belt pick height at gripper close |
| `LAB_PlateSorter2.dtx` | `nBeltClearHeight_m`→`nBeltClearHeight_mm` (**76.2**, was 0.0762); `nTCP_beltLift_m`→`_mm`; adds `bBeltLiftArmed`, `nBeltPickZ_mm`, `nBeltKickTimeout_s` |
| `Init.pgx` | Resets `bBeltClear`, `bBeltLiftArmed`, `nBeltPickZ_mm`, `nTCP_beltLift_mm` |

Bases: `tkPartFinder.pgx` and `Init.pgx` from `LastPartHang_Fix_2026-08-28`;
`tkMonitor_Robot.pgx` and `LAB_PlateSorter2.dtx` from `BeltClear3in_Update_2026-08-28`;
`PartPick.pgx` from `B&B LAB 08282026.zip` (untouched until now).

## Root cause

The old trigger was:

```
nTCP_beltLift_m=l_pHere.trsf.z-pBelt_START.trsf.z
if (getMoveId()>=250 and getMoveId()<300) and nTCP_beltLift_m>=nBeltClearHeight_m
```

consumed by a bare `wait(bBeltClear==true)`. Three things wrong with it:

**1. Units off by 1000x.** `nBeltClearHeight_m` was `0.0762` — metres. `l_pHere.trsf.z`
and `pBelt_START.trsf.z` are **millimetres**. The threshold was effectively 0.076 mm,
not 76.2 mm.

**2. Wrong datum, and a moving one.** I measured lift above `pBelt_START`. But
`pBelt_START` is the *approach* pose **above** the belt, not the grip height — during
the retreat the TCP is climbing back up *toward* it, so the delta is ~0 or negative.
Worse, `PartPick` **rewrites that global on every pick**:

```
pBelt_START=jointToPoint(tGripper,world,jBelt["start"])
pBelt_START.trsf=pBelt_START.trsf*pPoseTransform.trsf
```

so the datum shifted by an arbitrary vision transform part to part. That is the
intermittency: the first part happened to satisfy it, the next did not.

**3. Level-triggered inside a window that closes, behind an unbounded wait.**
`apera_exec_traj("LINEAR_RETREAT")` does **not** `waitEndMove()` (only
`LINEAR_APPROACH` does), and `PartPick` queues the moveId-300 `movej(pBelt_END,…)`
straight behind it with `mBlend`. So the `getMoveId() 250-300` window is short and
blend-dependent. A consumer arriving a few ms late missed the edge permanently, and
`wait(bBeltClear==true)` had no way out.

### Why that stalled the whole cell

`tkPartFinder` blocked at the top of its loop, before `bRunning["PartFinder"]=true`.
Nothing else in the project ever sets `bTrajectoryLOGIC` — only `tkPartFinder`, further
down the same loop body it could no longer reach. So `tkCycle` stayed in its else
branch (`setMoveId(750); movej(jBelt["capt"],…)`) forever, the detector branch that
normally runs the belt was never reached, and the conveyor never indexed again.

This matches the live SP2 state exactly: `nMoveID` **751**, `atCAPTURE` lit,
`Trajectory Found` still lit and `nPartsFound` still **1** — both stale, frozen at the
values from the last completed pass — and `RAIV/PartFinder: detector found nothing in
12 tries` in the logger from the one detector pass that did run at 11:43:50. The
Tasks Manager now shows `Cycle` and `PartFinder` gone with `Abort` running, i.e. the
cell had to be aborted out of the stall.

## The fix

`bBeltClear` becomes an **armed, set-only latch**:

- **`PartPick`**, immediately after `call tTool("ON")` — the gripper has just closed, so
  the TCP is at the real belt pick height for this part — records
  `nBeltPickZ_mm=here(tGripper,world).trsf.z`, clears `bBeltClear` and sets
  `bBeltLiftArmed=true`.
- **`tkMonitor_Robot`**, only while armed, computes
  `nTCP_beltLift_mm=l_pHere.trsf.z-nBeltPickZ_mm` and **sets** `bBeltClear` once that
  reaches `nBeltClearHeight_mm` (76.2 mm = 3 in). It never clears it.
- **`tkPartFinder`** waits with a timeout, starts the belt, then consumes the latch
  (`bBeltClear=false; bBeltLiftArmed=false`).

Why each fault is now closed:

- **Latch, not level** — `tkPartFinder` cannot miss the event by arriving late.
- **No moveId gate needed** — arming already restricts it to a real pick, so the
  measurement can continue past moveId 300 and will reliably reach 3 in. The gate
  existed only to stop false positives from unrelated poses (e.g. parked at capture);
  `bBeltLiftArmed` does that job properly, since it is true only between the grip and
  the consume.
- **Real datum** — grip height, captured per pick, never rewritten by anything else.
- **Bounded** — on timeout (`nBeltKickTimeout_s`, default 3 s) it logs and **falls
  through**. The normal detector branch below still runs the belt, so the worst case is
  the old pre-optimisation belt timing for one cycle. A missed lift can no longer stall
  the cell.

Lift is now measured slightly later in the retreat than the original intent (it may
complete during the moveId-300 move rather than inside 250-300), but the part is
genuinely ≥3 in above its grip height at that point, and it is still far earlier than
the camera-FOV-clear wait this optimisation replaces — so the cycle-time gain stands.

## Why it's safe

- `PartPick`'s only change is five assignments and one comment block after
  `call tTool("ON")`; no motion, speed, frame, moveId or gripper logic touched.
- `bBeltClear` can only be set while `bBeltLiftArmed` is true, which only `PartPick`
  sets, only with a part in the gripper. No path starts the belt without a real pick.
- Renames are complete: nothing anywhere in the project still references
  `nBeltClearHeight_m` or `nTCP_beltLift_m` (verified by grep across the whole app).
- `Init()` clears both latch halves and both datums, so an abort between grip and lift
  cannot leave a stale set. `tkAbort` calls `Init()`, and `tkAbort` already forces
  `doBelt["FWD"]=false` on entry.
- All five files parse as well-formed XML; every identifier used is declared in the
  `.dtx` or as a program local (verified).
- `clock()`, `logMsg(...,1)` and `toString("",n)` all follow existing usage in this
  project.

## Merge steps

1. Back up the current project.
2. Copy the five files into `usr/usrapp/LAB_PlateSorter2/`, overwriting.
3. Reload the application (the `.dtx` changed, so a full reload is required — a
   program-only refresh will not pick up the new variables).
4. Check the data editor shows `nBeltClearHeight_mm = 76.2` and
   `nBeltKickTimeout_s = 3`.

## Verification steps

1. **Cold start, empty feeder.** `PartFinder` must not hang. Expect the detector branch
   to run the belt in bursts and log `detector found nothing in 12 tries` if nothing
   arrives — never a task stuck at `wait`.
2. **Single part, the exact failure case.** Jog one part into FOV. It should pick, the
   belt should start as the part lifts ~3 in off the conveyor, and the belt **must keep
   indexing afterwards**. Watch `nMoveID` on the HMI cycle through 100/200/250/300/900
   and the 500s — if it parks at 750/751 with `Trajectory Found` lit, the stall is back.
3. **Watch the latch.** In the data editor, on each pick: `bBeltLiftArmed` true at
   gripper close, `nTCP_beltLift_mm` climbing past 76.2, `bBeltClear` set, then both
   cleared. `nTCP_beltLift_mm` should read a sane 0-400 mm, not 0.0x.
4. **Timeout path.** If you ever see `belt-clear lift not seen in 3s`, the cell keeps
   running at the old belt timing — tell me, that means the retreat geometry needs a
   lower `nBeltClearHeight_mm`, and it is now a tunable number rather than a hang.
5. **Abort mid-pick**, then resume Cycle. Belt must not kick on the first pass.
