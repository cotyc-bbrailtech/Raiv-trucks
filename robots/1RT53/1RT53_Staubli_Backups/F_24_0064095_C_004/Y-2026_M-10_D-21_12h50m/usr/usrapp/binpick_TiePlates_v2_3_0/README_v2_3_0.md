# binpick_TiePlates_v2_3_0 — remove wasted motion between drop and next pick

Built from v2_2_0 in backup Y-2026_M-10_D-20_11h10m. Load alongside v2_2_0; backing out = load v2_2_0.
Includes everything in v2.1.0 and v2.2.0. **NOT compiled here — compile in SRS first.**

## What the video showed (v2.2.0)
After each drop: full stop at jApera_Trigger_pos -> one-shot capture check (belt usually not settled yet) ->
AperaPartsFound ~0.5 s -> blend-OFF move to jTrajectoryStart (dead stop) -> if not captured, BACK to the
trigger pos to wait and capture -> wait ~0.8 s for APERA -> stop above the plate -> descend.
Log: captures "at place" never increased; every pick deferred its picture until after the drop.

## Changes
1. **Capture while moving.** New `TryCaptureNow` (non-blocking: takes the picture only if belt settled +
   arm out of view + socket free + no picture yet) and `WaitMoveCapture` (polls it every 10 ms until the motion
   queue empties). Used during the move to the drop (Part_Accept/Part_Reject) and the return to
   jApera_Trigger_pos. Counter `nCapInMotion` (appended to CSV line L).
2. **No stop at jApera_Trigger_pos** when the picture is already taken — it stays the via point (same route),
   blended. The arm only stops there if the picture still isn't taken on arrival, waits for the belt, captures.
3. **No backtrack** from jTrajectoryStart to the trigger pos (old fallback only runs if the belt wait times out).
4. **jTrajectoryStart reached with `mHover`** (joint blend 50 mm) instead of `mReach` (blend off). If APERA has
   already answered the arm flows into APPROACH; if not it stops there and waits, as before.
5. **AperaPartsFound only when APERA returns no trajectory** (a trajectory means >=1 plate). Saves ~0.5 s/pick.
6. **No dead stop above the plate**: `bBlendApproach` (ships TRUE) blends APPROACH into LINEAR_APPROACH within
   `nApproachBlend_mm` (ships 25 mm). waitEndMove + isSettled before the grip are unchanged.
   Set bBlendApproach=false to restore the old stop.

## New data (data editor)
| name | default | meaning |
|---|---|---|
| bBlendApproach | true | blend approach into straight-down descent |
| nApproachBlend_mm | 25 | corner rounding at top of the descent (keep small) |
| mHover | leave/reach 50 | descriptor into jTrajectoryStart |
| mApproachBlend | 25 (set from nApproachBlend_mm) | descriptor for APPROACH when blending |
| nCapInMotion | counter | pictures taken while the arm was moving |

## Segment timing note
With blending, "Approach" reads ~0 and its time moves into "Linear Appr." — compare the total cycle, not those two.
"Return" now = time from release until the arm leaves for jTrajectoryStart: ~0 means the picture was taken in motion.

## First test — reduced speed, watch it
1. Compile. Run at 25–50% speed with the cell watched. Check the paths drop -> trigger pos -> hover -> plate:
   no new path near the belt frame, descent still straight onto the plate.
2. 100% speed, stocked belt, pendant unplugged, 20–30 min. Then pull a backup.
3. Expect: no stop at the trigger pos on most picks, no back-and-forth, shorter hover. In the log: capAtPlace low,
   nCapInMotion climbing, capAtTrigPos rare.
4. If the descent looks wrong: bBlendApproach=false (live). If the hover move looks wrong: tell me.
Remaining big lever: nBeltSettle_s (1.0 s) — set to the measured loaded stop time.
