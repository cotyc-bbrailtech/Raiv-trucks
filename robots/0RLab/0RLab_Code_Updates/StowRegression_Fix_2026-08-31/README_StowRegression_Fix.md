# StowRegression_Fix — 2026-08-31

Two files. **Stow is my regression from `AbortHold_Fix` — replace `tkAbort.pgx` from that
bundle with this one.** Pick0Start is not a bug; explanation below.

## 1. Stow broken — my fault

In `AbortHold_Fix` I bounded `wait(bRobotAT["home"]==true)` in `tkAbort` so it could time
out and carry on. `MoveToStow.pgx` is:

```
if bRobotAT["home"]==true
  movej(jStow,tGripper,mSlow)
  waitEndMove()
  wait(isSettled())
  disablePower()
  call Init()
endIf              <-- no else
```

**"The arm is at home" was an invariant, guaranteed by that unbounded wait.** I removed the
guarantee and MoveToStow has no else branch, so the second button press reached the Stow
branch with the arm not at home and Stow did **nothing** — no move, no `disablePower()`, no
`Init()`, no message. I traded a visible hang for an arm left powered and un-stowed while
the button behaved as though it had worked. That is strictly worse and I should have read
`MoveToStow` before touching the wait.

**Fix — warn, do not proceed.** The wait holds for home again, because the gripper release
on the following lines depends on it too. What was actually missing was visibility, not an
escape hatch, so it now logs every `nAbortHomeTimeout_s` for as long as it waits:

```
RAIV/Abort: still not at home after 20s - holding. Stow needs home; check jHome/jMaxDistance.
```

**Plus belt and braces in `MoveToStow`:** an `else` that refuses out loud rather than
silently. Power is deliberately **left enabled** there — the arm is somewhere unknown and
dropping power in an unknown pose is not automatically the safe choice.

```
RAIV/Stow: REFUSED - arm not at home. Not stowed, power left enabled.
```

Keep everything else from `AbortHold_Fix` — the tkMetrics hold bucket, the TaskCommand
guard, the dtx. Only `tkAbort.pgx` is superseded, and `MoveToStow.pgx` is new here.

## 2. Pick0Start empty — not a bug, an unused slot

`ph0` ← `bRobotMotion["Pick0_Start"]` ← `getMoveId()` in **[50,100)**.

The complete set of `setMoveId()` values in the application is:

```
0, 100, 200, 250, 300, 500, 510, 520, 530, 540, 600, 610, 620, 630, 640, 700, 750, 900
```

**Nothing is ever tagged 50–99**, so `Pick0_Start` can never go true and `ph0` correctly
shows `--`. The 16-slot index exists to line up with the PLC ladder's X111–X115 / X101–X105
/ X106–X110, and the ladder had five pick phases where `PartPick` has four:

| slot | moveId band | what runs there |
|---|---|---|
| ph0 | 50–99 | **nothing — spare** |
| ph1 | 100–199 | `movej(pBelt_START)` |
| ph2 | 200–249 | Apera linear approach **+ gripper close** |
| ph3 | 250–299 | Apera linear retreat |
| ph4 | 300–399 | `movej(pBelt_END)` |

Nothing is going unmeasured — the move from the capture pose into the pick is `ph1`, and the
gripper close is inside `ph2`. `ph0` is simply an empty slot on the VAL3 side.

**Two ways to close it, your call:**

- **Relabel** the PHASES page field to `(spare)` so it stops looking broken. HMI only,
  zero risk.
- **Repurpose it as grip time** — tag the `tTool("ON")` window with `setMoveId(50)` and
  restore 200 after. That would split the gripper close out of `ph2`, which is worth having
  given `pick_still` is 21.5% of the pick. But it means editing `PartPick` around the
  gripper, and given what my last two `PartPick`-adjacent changes cost you I would rather
  you asked for it explicitly than have me volunteer it.

## Merge and verify

1. Copy both files in. Reload.
2. **Abort once** → arm goes home, gripper releases, pendant reads
   `ABORT - press Cycle, or Abort again to Stow`.
3. **Abort again** → arm moves to stow, power drops. That is the regression closed.
4. **Press Cycle instead** → resumes, and `Abort` leaves Tasks Manager before `Cycle`
   appears.
5. If you ever see `RAIV/Abort: still not at home after 20s`, the arm is not landing within
   `jMaxDistance` of `jHome` — that is the condition the bounded version was hiding, and it
   is a real thing to chase rather than skip past.
