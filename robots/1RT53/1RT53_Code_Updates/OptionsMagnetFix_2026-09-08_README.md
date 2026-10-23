# Raiv-T1 — Options-page magnet fix

**One file. `HMI/uOptions.pgx`. Nothing else changes.**

Controller `F_24_0064095_C_004`, application `binpick_TiePlates`.
Built against backup `Y-2026_M-09_D-08_11h34m`.

---

## The fault you reported

> while SP2 displays Options screen, gripper will not cycle to pick part

Confirmed, root cause found, and it is **not** in anything we added. Here is the
block, unchanged in every backup back to 2026-08-26, at the bottom of the
`uOptions` loop:

```
if bMagnetManual==true and dioGet(dDOTool)==0
  call tGripperEMH("ON")
elseIf bMagnetManual==false and dioGet(dDOTool)==1
  call tGripperEMH("OFF")
endIf
```

That is not a button handler — it is a **servo**. On every pass of the loop it
forces the magnet to match `bMagnetManual`. And `dDOTool` is not a request:
`tkIOMonitor` latches it from the coils themselves.

```
if dioGet(dDOemh_gripperON)==1
  dioSet(dDOTool,1)
endIf
if dioGet(dDOemh_gripperOFF)==1
  dioSet(dDOTool,0)
endIf
```

So the servo watches the magnet's **actual** state and drives it back to the
button. With the Options page up and the cycle running, every pick goes:

| | | |
|---|---|---|
| 1 | `tkCycle` | `dioSet(dDOemh_gripperON,1)` then `delay(nEMH_onDelay)` — a 0.5 s grip pulse |
| 2 | `tkIOMonitor` | runs `delay(0)`, so within a tick: `dDOTool = 1` |
| 3 | `uOptions` | `delay(0)` too. Sees `bMagnetManual==false and dDOTool==1` → **`call tGripperEMH("OFF")`** |

The release pulse lands **inside the 0.5 s grip pulse — both coils energised at
once** — and the plate is demagnetised at the moment it was meant to be picked.
There is no part-present check anywhere in `tkCycle`, `Part_Accept` or
`Part_Reject`, so the cell does not fault: it picks air and carries on. From the
pendant that is exactly "the gripper will not cycle to pick a part".

It only happens on that page because `tkHMI` only runs `uOptions` while
`nUserPage==2`.

The mirror image is just as bad. Leave the manual button **on** and the loop
re-magnetises immediately after `Part_Accept` releases — the plate stays stuck to
the tool, or the next one is snatched on the approach.

### Why it surfaced now

The code is original and untouched. What changed is that there is now a reason to
sit on the Options page during production — the sensor lamps, the raw input and
the heartbeat readout we added there. A latent fault that needed someone to be
watching that page finally got someone watching it.

---

## The fix

Two changes, both inside `uOptions.pgx`:

**Edge, not level.** The magnet is pulsed only when `bMagnetManual` actually
changes — only when the operator presses the button. `l_bMagLast` is seeded from
the button on entry, so opening the page never pulses anything. The magnet's own
state is no longer read at all, so there is nothing left to fight over. An
ignored press still updates `l_bMagLast`, so the button and the detector cannot
drift apart.

**Cycle-gated.** `taskStatus("cycle")==-1` — the same test `monitoring()` and
`killAllTask()` already use for "the cycle task is not running". A press while a
cycle is live is ignored and logged, **in both directions**: an ON mid-cycle
would grab a plate on the approach, an OFF mid-cycle would drop the one in the
tool. Ignoring it is the safe outcome. A suspended cycle task also reads as "not
-1", so it is blocked too — correct, the arm may be holding a plate.

The button keeps doing what it is for: jogging the magnet at the pendant with the
cell stopped.

`bStart` is deliberately **not** the gate. It ships `true` in the `.dtx`, so it
reads true on a fresh boot with the cell idle and would block the button when it
should work. `taskStatus` is the real state.

```
if bMagnetManual==true and l_bMagLast==false
  l_bMagLast=true
  l_bMagEdge=true
elseIf bMagnetManual==false and l_bMagLast==true
  l_bMagLast=false
  l_bMagEdge=true
endIf
if l_bMagEdge==true
  l_bMagEdge=false
  if taskStatus("cycle")==-1
    if bMagnetManual==true
      call tGripperEMH("ON")
    else
      call tGripperEMH("OFF")
    endIf
  else
    logMsg("RAIV/T1: manual magnet button IGNORED - the cycle task is running. Stop the cycle before using it.",2)
  endIf
endIf
```

Everything above that block — `userPage`, the `nUserPage` switch, `call uDate()`,
`delay(0)`, the `until` — is byte-for-byte the original. Diffed and checked.

---

## What was checked here, and what was not

Checked mechanically:

- XML parses; BOM present; all 148 line endings CRLF, matching the file on the controller
- the three locals (`l_bPage`, `l_bMagLast`, `l_bMagEdge`) are declared
- every global used (`nUserPage`, `bMagnetManual`, `bExit`) exists in `binpick_TiePlates.dtx`
- `if`/`endIf`/`switch`/`do..until` nesting balances
- executable-line diff against the original shows only the intended change
- only `==` and `and` on plain bool reads — nothing depends on VAL3 short-circuiting an `and`, which the reference manual does not promise
- `logMsg` is well under the 255-byte limit

**Not checked, because nothing here can compile or run VAL3.** In the IDE,
confirm `l_bMagLast` / `l_bMagEdge` compile as bool locals and that
`taskStatus("cycle")` is accepted in the HMI task.

## Test it

1. **Cell stopped.** Open Options, press the magnet button. Magnet makes. Press
   again. Magnet breaks. Once per press — no chatter, no repeat pulsing.
2. **Open the page with the magnet already energised.** Nothing should happen.
3. **Cycle running, Options page up.** Plates get picked normally. Press the
   button: nothing happens to the magnet, and one line appears in the log —
   `manual magnet button IGNORED - the cycle task is running`.

## Deploy

Copy `uOptions.pgx` over `usr/usrapp/binpick_TiePlates/HMI/uOptions.pgx`.
No `.dtx` change, no `.pjx` change, no new data, no new task. Reload the
application.

To back out, restore `uOptions.pgx.orig` (included) — it is the file currently on
the controller, byte for byte.
