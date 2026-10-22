# Raiv-T1 — capture on FoV clear, toggled from SP2

**Five files.** Built on the `Y-2026_M-09_D-10_12h00m` backup — everything in
`_original/` is byte-identical to what is on the controller right now.

| file | on controller | this build | change |
|---|---:|---:|---|
| `Part_Accept.pgx` | 9,491 | **15,077** | +92 lines, 0 removed |
| `LogCycleCSV.pgx` | 27,087 | **27,659** | +10, −1 (the FORMAT header line) |
| `interface/UserPageOptions.html` | 13,869 | **15,575** | +8, 0 removed |
| `interface/UserPageOptions.bindings.json` | 4,922 | **5,748** | +38, 0 removed |
| `binpick_TiePlates_TEST.dtx` | (53,345) | **53,876** | 4 declarations added, **no value changed** |

Rename the `.dtx` to `binpick_TiePlates.dtx`. Every other file drops in as-is.

**It ships OFF.** `bCaptureOnFovClear` defaults false, and with it false
`Part_Accept` is one bool test away from the code that ran run 14. Deploying
this changes nothing until somebody presses the button.

---

## What it does

Today the trajectory capture is taken at `Part_Accept` L96, after
`waitEndMove()` — arm parked 50 mm above the drop. With the toggle on it is
taken instead as soon as **`_bStartFoV` goes false**, which happens during the
RETREAT, roughly a whole place motion earlier.

`_bStartFoV` is the right gate rather than "arm at rest". What the capture
needs is an unobstructed view of the *conveyor*, and `tkCheckZone` already
maintains exactly that flag — true while `tSchunkEMH084` is inside the
conveyor FoV cube, false once it has left. Same flag, same 20 ms poll, same
`nFovClearTimeout_s` bound that `tkBeltScan`'s early trigger already uses, so
there is one idiom in the project rather than two.

### Why this might buy enough to afford blending again

`apera_latency_s` is a constant: **1.37 s**, range 1.30–1.42, across runs 11–14
at every dwell combination. In run 14 the cycle carried **0.72 s** of that as
dead blocking (`SegVisionWait`) and hid 0.65 s under motion — because after the
at-place trigger there is only magnet-off + place+return, about 0.9 s, in front
of the answer.

Trigger at FoV clear and the motion in front of the answer becomes the rest of
the retreat plus the whole place window — comfortably more than 1.37 s. The
wait should collapse.

That is what makes the blend question live again. Restoring `mReach` to
leave/reach 300 costs a measured **0.39 s** in the approach. Today that is not
affordable. If the early capture returns most of 0.72 s, it is.

**Prediction, and my last one was wrong so treat it as arithmetic rather than a
promise:** cycle 4.16 → somewhere near 3.5–3.7 s with the toggle on and blend
still off; then ~3.9–4.1 s if you put the 300 mm zones back. Both better than
4.16. **Test one variable at a time** — toggle on with blend off first, and only
then add the blend.

### Why it cannot lengthen the cycle

This is a property of where the block sits, not a hope.

The block runs **after** the drop-approach `movej` is queued and **before** the
`waitEndMove()` that drains it. `movej` only queues and returns, so the arm is
flying the whole time this polls, and `waitEndMove` was going to block for that
time anyway — every millisecond spent here is a millisecond it does not spend.
`_nPlaceClk[0]`, which closes `SegRetreat`, is taken *after* that
`waitEndMove`, so as long as the FoV clears before the motion finishes,
`SegRetreat` reads exactly as it does today.

Put the same wait *above* the `movej` and the motion queue can drain empty with
the arm stopped in mid-air waiting for a camera — a new dead stop, the opposite
of the point. `verify.py` §7j(a) asserts the ordering, and it is the only check
in the suite that catches a pure move of this block.

If the wait ever *does* outlast the motion, `SegRetreat` inflates and
`nFovWait_s` says by how much. That is the one regression to watch and it is
instrumented.

### It cannot lose a capture

The wait is bounded by `nFovClearTimeout_s` (3 s). On timeout it counts
`nCapFovDecline` and falls straight through to the ordinary at-place block,
which still sees `bTrajTriggered==false` and behaves exactly as it always has.
There is no path where a slow or stuck FoV flag costs you the picture.

### The one real risk

**This is a moving-robot capture, and the first one ever taken from
`Part_Accept`.** `tkBeltScan`'s early trigger is the only other, and it has
never fired in a logged run. If APERA rejects the exposure,
`apera_wait_for_trajectory` takes its early return and leaves
`bTrajectoryFound` at its *previous* value — a phantom pick on air. So the
block logs a severity-3 line on `apera:bAperaError`, and that line names the
toggle to switch back off. **Watch the log on the first run.**

## On the Options page

A button and three readouts go in the empty band at top 522–574, to the right
of `Cycle Stats`:

| control | shows |
|---|---|
| **Capture @ FoV** | the toggle |
| **EARLY CAP** lamp | lit when it is on |
| `fov` | `nCapFovClear` — captures taken at FoV clear |
| `dec` | `nCapFovDecline` — FoV never cleared, fell back to at-place |
| `wt` | `nFovWait_s` — how long the last wait took |

Read `fov` against `cap at place` on the Cycle Stats page: those two should sum
to your pick count, and `fov` should be nearly all of it.

**Note on the layout.** My working copy of `UserPageOptions.html` was stale —
`btn1_Copy1` ("RUN Robot Calibration") has been moved from top 495 to top 335
on the controller, which freed the band these controls now use. Both interface
files in this bundle were rebuilt from the `12h00m` backup, so they are pure
insertions into your current page: `diff` shows 8 added lines and 0 removed in
the HTML, 38 added and 0 removed in the bindings. Nothing you have rearranged
is disturbed.

## Line H is now 16 fields

```
… ,<gripPart>,<gripMag>,<dropPart>,<aperaLatency>,<capFovClear>,<capFovDecline>,<fovWait>
```

**Appended, never inserted.** `parse_backups.py` reads line H with
`zip(names, values)`, so a 13-field line from an older backup still parses
correctly and a 16-field line just fills more columns. Verified both ways
against a synthetic log, and the parser was re-run over all 1,787 existing rows
with **zero value changes**. Worst-case line length is 93 bytes against
`logMsg`'s 255-byte silent-truncation cap.

## Verification

`verify.py` **PASS (0 fail, 6 warn)** · `mutate.py` **67/67 caught, 0 missed**.

New §7j, eleven new mutations. The properties asserted are the safety ones, not
the ones that make it work:

| | |
|---|---|
| a | the block sits **between** the drop-approach `movej` and `waitEndMove` — the whole no-added-time argument |
| b | the wait is bounded by `nFovClearTimeout_s`, measured from `l_nFovT0` — a bare `while _bStartFoV==true` hangs the cycle with a plate on the magnet |
| c | the stand-down flags are **re-tested after** the wait: the gate above was sampled up to 3 s earlier and an Abort, Stop or End Cycle in that window must not still get a socket round-trip |
| d | no motion and no output from inside the block |
| e | `nCapFovClear` / `nCapFovDecline` have exactly one writer each, and it is an increment |
| f | `bCaptureOnFovClear` is **never written by code** — an operator switch a program can flip is a program that can strand the cell in the untested path |
| g | the HMI may toggle it but may not write the counters, and the button is actually bound |

Plus: the trigger-site floor went 7 → 8, and the new site is covered by the
existing rule that every `apera_trigger_trajectory` is followed immediately by
`_nTrigClk=clock()` and that the stamp precedes `bTrajTriggered=true`.

### Two repairs to the suite itself

**A mutation that was passing for the wrong reason.** "Let code switch the
operator toggle on" was inserting its write inside `tkIOMonitor`'s speed block,
so it tripped the *speed-refusal nested-if* check instead of §7j(f). Caught,
but by the wrong assertion and with a message that would send the next person
to the wrong file. Moved outside that block; it now fails on §7j(f).

**A stale `INTENTIONAL` entry.** The `mReach` entry described a change that is
no longer a change — the live `.dtx` holds blend-off itself since 09-10. §10
failed on it, correctly, and it has been retired. `nGripSettle` is listed in
its place as a **live pin** with from == to: not a change, but a tripwire, so
that if anyone re-tunes it on the machine before this ships the suite fails
loudly instead of this file quietly putting it back to 0.

## Not verified — nothing here compiles or runs

- the four new `.dtx` globals resolve, and `l_nFovT0` is accepted as a `num` local
- the Options controls land where you want them
- **most important:** that `_bStartFoV` actually goes false early enough in the
  retreat to be worth anything. `nFovWait_s` is the number that says so — if it
  reads near `nFovClearTimeout_s`, the cube geometry is not what this assumes
  and the answer is in `tkCheckZone`'s `createCube` call, not here.

## Test it

1. Deploy, leave the toggle **off**, run 25 picks. Cycle should read 4.16 s and
   `fov`/`dec` should both stay 0. That is the no-op check.
2. Press **Capture @ FoV**. Watch the log for the severity-3 APERA error line
   on the first few picks — if it appears, switch straight back off.
3. Read `fov` climbing and `cap at place` flat, `SegVisionWait` falling,
   `nFovWait_s` small, and `SegRetreat` unchanged at 1.31.
4. Only if all four hold, put `mReach` back to leave/reach 300 and see whether
   the blend now pays for itself.

## Back out

Copy the four files from `_original/` back over the application; they are what
is on the controller now, byte for byte. `_ctrl/binpick_TiePlates_live.dtx` is
the current `.dtx` if you want to undo that separately. Or just leave the
toggle off — the `.dtx` adds four declarations and changes no existing value.
