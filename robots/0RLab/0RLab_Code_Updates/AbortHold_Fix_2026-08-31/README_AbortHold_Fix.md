# AbortHold_Fix — 2026-08-31

Abort/Stow is a deliberate two-press operator sequence. The metrics were treating it as a
fault, and a missing task guard let it corrupt whole runs. Both fixed.

## What was actually wrong

**Your design, as stated:** one press → safe path home, gripper off (part dropped), Init,
then park and wait for the operator to either press Cycle or press Abort/Stow again for
Stow. `bMessage["abort"]` and `bRunning["Abort"]` are the handshake that gates exactly
those two branches in `tkMonitor_IO`. **Parked is finished-pending-you, not a hang.** My
earlier "the Abort task ran and did not finish" read was backwards.

**Defect 1 — tkMetrics was measuring the abort button, not faults.** Rule 1 was:

```
bERROR["schunk"] or bMessage["abort"] or bRunning["Abort"]  ->  FAULT
```

`bERROR["schunk"]` is never assigned true anywhere in the application. So the fault bucket
was really "abort routine active or parked", sitting at the top of the precedence chain
where it outranks productive, belt, and both station holds.

**Defect 2 — and this is what made it destructive.** Accumulation is gated on
`if bTskStatus["Cycle"]==true`. A clean park kills Cycle, so a normal abort accumulates
nothing — it excludes itself. **For a run to read 100% FAULT with plates being made, Cycle
and Abort had to be alive simultaneously.** They can be, because
`TaskCommand.pgx:63` created Cycle with no `taskStatus("Abort")==-1` check:

| line | guard |
|---|---|
| `:58` RoCal | `... taskStatus("RoCal")==-1 and taskStatus("Cycle")==-1 and taskStatus("Abort")==-1` |
| `:63` Cycle | `bTskSelected["Cycle"]==true and taskStatus("Cycle")==-1 and isPowered()` |

Cycle was created the instant `bTskSelected["Cycle"]` went true — the same flag tkAbort's
`until` is polling — so Cycle started while Abort had not exited, with `bRunning["Abort"]`
still set from `tkAbort:16` and cleared only at `:63`, its last line. Result: run 1, 29
plates, `b_prod` 0, `b_fault` 100%, LRC undefined.

## What's in this folder

| File | Change |
|---|---|
| `tkMetrics.pgx` | New **state 7 OPERATOR HOLD** split out of FAULT; `HoldSec` accumulates **outside RunSec**; hold added to the clean-cycle test; new pendant state string |
| `TaskCommand.pgx` | Cycle guard gains `taskStatus("Abort")==-1` |
| `tkAbort.pgx` | `wait(bRobotAT["home"]==true)` bounded by `nAbortHomeTimeout_s` |
| `tkScreenHmi.pgx` | Formats `_sM["Bhold"]` |
| `LogMetrics.pgx` / `LogMetricsHdr.pgx` | `b_hold` added to the `H2`/`D2` block |
| `LAB_PlateSorter2.dtx` | `nAbortHomeTimeout_s` (public, **20 s**); `_nM["HoldSec"]` key |

## The measurement decision, as you chose it

Hold time gets its own figure **and is kept out of the rate**:

- `RunSec` is now the **production** denominator. `act_spc`, `act_pph` and LRC reflect what
  the cell does when it is being asked to run.
- `HoldSec` is tracked separately. **Wall time = RunSec + HoldSec**, so availability is
  still visible — you have both axes rather than one blended number.
- The loss buckets still sum to `RunSec`, so tkMetrics' partition self-test is intact.
- The pending balance is written off to `OtherSec` on entering hold rather than dropped — a
  gap spanning an operator hold is not attributable, and `OtherSec` must be able to see it.
- **`HoldSec` is in the clean-cycle test**, so a plate-to-plate interval straddling an
  abort is interrupted, not clean. Without that, LRC would count a cycle spanning a hold.

**This changes what `act_spc` means versus the log you already have.** Samples before this
fix have hold time inside the rate; samples after do not. Note the changeover in the CSV —
`b_hold` appearing in `D2` is the marker, same as the `run` column was last time.

A real fault still wins: rule 1 (`bERROR["schunk"]`) is checked before rule 7. That flag is
currently dead code, so if `FAULT` ever appears now it means something genuinely set it.

## The bounded wait

`bRunning["Abort"]` is set at `tkAbort:16` and cleared only at `:63`, so anything parking
the task in between latches it. On timeout it **carries on to the operator prompt** rather
than holding the flag — the arm has been commanded home and the gripper is released on the
next lines either way, and a logged near-miss beats a silent park. Watch for
`RAIV/Abort: not at home within 20s`. Motion is unchanged; only the wait is bounded.

## Merge and verify

1. Copy the seven files in. Full reload — `.dtx` changed.
2. **Press Abort once.** Pendant must read `ABORT - press Cycle, or Abort again to Stow`,
   not `FAULT`. That string is the fix, visible.
3. **Press Cycle to resume.** In Tasks Manager, `Abort` must disappear *before* `Cycle`
   appears — never both at once. That is defect 2 closed.
4. **Press Abort again instead** — Stow still works, gated on the same handshake.
5. Run a batch with one abort/resume in the middle. `b_fault` must stay 0, `b_hold` must
   pick up the hold, and `int_ct` must gain one for the straddling interval.
6. Confirm `act_spc` no longer moves when you park the cell and walk away.

## Still open

`nBeltKickTimeout_s` 3 s and `nBeltClearHeight_mm` 76.2 are unchanged, so the 1-in-6
belt-clear fallback rate is still there — separate item, and free to test since both are
public. After this, the cycle-time work is ph15 (to capture, 1.469 s) and ph2 (pick linear
approach, 1.277 s), which are 54% of the cycle between them.
