# StowSelect_Pick0_Fix — 2026-08-31

Three files. **Supersedes `tkAbort.pgx` in both `AbortHold_Fix` and
`StowRegression_Fix`** — take this one. `MoveToStow.pgx` is unchanged from
`StowRegression_Fix`, included so the folder is self-contained.

## 1. Stow never reaches its branch — found it, and it is not mine

You are right that the press never gets that far. `bTskSelect["stow"]` is never set,
because the branch that would set it cannot match:

```
tkMonitor_IO:73
elseIf bTskSelect["abort"] and bTskSelected["Abort"] and bTskStatus["Secondary"]
       and bTskStatus["Abort"] and bMessage["abort"]
  bTskSelect["stow"]=true
```

**`tkAbort:32` calls `Init()`, and `Init.pgx:155` sets `bTskSelected["Abort"]=false`.**

So by the time Abort is parked and blinking, the flag that branch needs is already gone.
The second press then matches nothing at all: branch 1 needs `!isPowered()`, branch 2 needs
`bTskSelected["Cycle"]` which `Init()` also cleared (`:154`). Press, nothing, no message.

The author already knew `Init()` wipes state here — line 33 is
`bRunning["Abort"]=true`, re-asserted immediately after the `Init()` call for exactly this
reason. **One flag was missed.** Fix is the line beside it:

```
call Init()
bRunning["Abort"]=true
bTskSelected["Abort"]=true      <-- added
```

`bTskStatus["Abort"]` and `["Secondary"]` need no such treatment — `tkMonitor_IO` recomputes
both from `taskStatus()` every pass, so `Init()` clearing them heals itself. Only
`bTskSelected["Abort"]` is set once and expected to persist.

This is pre-existing and independent of the bounded-wait regression. Both had to be fixed
before Stow could work: that one stopped `MoveToStow` from doing anything once reached, this
one stops it being reached at all.

## 2. Pick0Start — now measuring what you described

You wanted ph0 to be *time the robot spends waiting for the next part pose* — moving to
capture while the belt runs, or waiting on the trajectory image. That time exists and is
substantial, but it was being added to **ph15**:

```
tkCycle else branch:   setMoveId(750) ; movej(jBelt["capt"]) ; delay(nLoopPace)
```

Tagged 750 the whole time, so ph15 "To capture" was **travel plus the wait at capture
combined** — 1.469 s, second largest phase in the cycle, with no way to see which half. And
once the arm is at capture that `movej` is a no-op being re-issued every pass, so the wait
was booked as travel.

Now it splits on arrival:

| | |
|---|---|
| **ph0** | waiting at capture for the next pose — belt running, or Apera processing the image |
| **ph15** | the move to get there |

`setMoveId(50)` lands in the 50–99 band → `bRobotMotion["Pick0_Start"]` → ph0. That band has
been empty since the ladder port because nothing was ever tagged in it.

**Tag only.** The `movej`, target, speed and pacing are untouched. Checked before writing it:
nothing in VAL3 branches on `Pick0_Start` or `to_capture` — both are published to the PLC as
status bits only (`doToClickMOTION["PickPart0"]`, `doToClick["Motion_toCapture"]`), and
`PickPart0` has never been able to go true until now. Nothing else reads the 750 band; the
only other `getMoveId()` test in the application is `PartPick:77` on 250–300.

Expect ph15 to drop and ph0 to pick up the difference. Their sum should stay near the
current 1.469 s, and that is your check that the split is a split and not a change.

## 3. tTool ON/OFF — not done, and why

Timing the gripper needs its own moveId band around `call tTool("ON")` in `PartPick` and
`call tTool("OFF")` in `PartPlace`, restoring the surrounding tag afterwards. It is worth
having — `pick_still` is 21.5% of the pick and gripper actuation is most of it, currently
buried inside ph2.

I have not done it. Both edits sit directly around the gripper on the pick path, which is
where my belt-kick changes caused the over-torque, and `PartPick:77` waits on the very
moveId window an insertion there would disturb. It wants its own change with its own test
run, not a rider on this one. Say the word and I will do it as a standalone.

## Merge and verify

1. Copy the three files in. Reload. (`tkAbort.pgx` replaces the version from either earlier
   bundle.)
2. **Abort once** → arm home, gripper releases, pendant reads
   `ABORT - press Cycle, or Abort again to Stow`.
3. **Abort again** → `bTskSelect["stow"]` goes true, arm moves to stow, power drops.
   Both halves of the Stow fault are then closed.
4. **Or press Cycle** → resumes, `Abort` leaves Tasks Manager before `Cycle` appears.
5. On the PHASES page, **ph0 shows a number for the first time** and ph15 falls. Check
   `ph0 + ph15` against the 1.469 s you have now.
