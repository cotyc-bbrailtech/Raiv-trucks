# ToolDwell_PhaseGroups — 2026-08-31

tTool gripper dwell measured and split pick/place, and the PHASES page gains a group
summary: seconds per plate and % of cycle for Pick / Accept / Reject / No-trajectory /
tTool, plus a total.

## Files

| File | Change |
|---|---|
| `tTool.pgx` | Times the whole call with `clock()`, books it to pick or place |
| `tkMetrics.pgx` | Zeroes the four new counters on RESET |
| `tkScreenHmi.pgx` | Computes the five group figures and their percentages |
| `interface/PHASES.html` | Six-row group block below the nav buttons |
| `interface/PHASES.bindings.json` | 12 new read bindings (20 → 32) |
| `LAB_PlateSorter2.dtx` | Four new `_nM` keys |

## tTool dwell — clock(), not a moveId band

`_nM["ToolOnSec"]/["ToolOnRuns"]` and `_nM["ToolOffSec"]/["ToolOffRuns"]`, timed from the
top of `tTool()` to the end of the switch — output init, the four status waits and the
actuation, because all of it is dwell with the arm standing still.

**No moveId is touched.** You asked for this as a standalone for good reason: the 16-slot
phase array is full, and a `setMoveId` around the gripper would land inside the 250–300
window `PartPick:77` waits on. `clock()` in `tTool.pgx` avoids both problems and touches no
motion, no output, no moveId.

**The split is gated on the caller, not the action string:**

```
if x_sAction=="ON"  and bRunning["PartPick"]==true    -> pick grip
elseIf x_sAction=="OFF" and bRunning["PartPlace"]==true -> place release
```

`tkAbort` also calls `tTool("OFF")` — a safety drop, not a place. Neither flag is set there,
so it is correctly left out of the mean rather than dragging it around.

## Group totals — per plate, not per occurrence

The `ph0..ph15` figures already on the page are `_nPhSec[i]/_nPhCount[i]`: a mean per time
that phase ran. **Summing those would be wrong here** — accept phases only run on accepted
parts, reject phases only on rejected ones, so their per-occurrence means do not add to
anything per plate. The group figures divide raw seconds by `Plates`, which does add up and
puts them on the same footing as the loss buckets on the LRC page.

Groups follow the code paths, not just the labels:

| group | slots | path |
|---|---|---|
| Pick | ph1–ph4 | `PartPick`, approach through retreat |
| Accept | ph5–ph9 | `PartPlace` accept branch |
| Reject | ph10–ph14 | `PartPlace` reject branch |
| No-traj | **ph0 + ph15** | `tkCycle` else branch — the move to capture *and* the wait there for the next pose. One group because they are one branch. |
| tTool | — | gripper dwell, pick grip + place release |

`%` is against actual s/plate, the same denominator as `act_spc` on the LRC page.

**`TOTAL accounted` is the self-check.** It sums the five and shows the percentage. **It
will not read 100%, and should not** — blended moves overlap phase boundaries, and belt
advance and operator hold sit outside the phase index entirely. What matters is that it
lands somewhere stable and plausible; if it drifts far below 100 the cycle is spending time
on a path none of these five accounts for, which is worth chasing.

## Layout

Six rows at y 498–680 in the space below the LRC/DETAIL buttons — nothing moved, nothing
overlaps, max top 660 inside the 690 body. Verified: 71 widgets, no duplicate ids, all 32
bindings resolve, JSON parses.

Both `interface/` files are written **without a BOM** and with CRLF, matching the other six
files in that folder. That is the thing that broke the user page on 8/28 and it is checked
explicitly here.

## Merge and verify

1. Copy all six files in (keep the `interface/` subfolder). Full reload — `.dtx` changed.
2. Run a batch, then open PHASES. All five rows should show numbers.
3. **tTool row** — expect it to be a real number for the first time. Compare it against
   `pick_still` on the same page (21.5% last run); gripper dwell should be a large part of
   why the arm is standing still during the pick.
4. **No-traj row** should be close to `ph0 + ph15` added by hand — that is the arithmetic
   check on the per-plate conversion.
5. **Reject row** reads `0.000` / `0.0%` until you actually reject a part. That is correct,
   not a missing binding — `acc_pct` has been 100 every run so far.
6. Note `TOTAL accounted` on a good run and keep it as the reference. A later drop in it is
   a signal, not noise.

## Not included

The group figures are **not** in the CSV log. All 16 phases already are, plus `Plates`, so
every group figure is derivable from `raiv_metrics_*.csv` without adding a fifth block to
the log. Say so if you would rather have them logged directly.
