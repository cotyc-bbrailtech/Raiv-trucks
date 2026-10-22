# Raiv-T1 — the phantom is NOT the held plate. Correction.

Frame 111, both cameras of the stereo pair. I asked for this image to confirm a
claim. It refuted it, which is what it was for.

---

## What I said, and what the image shows

**I said:** the ever-present "Unpickable" detection is the tie plate held on the
magnet, and Capture @ FoV makes it worse by firing while the arm is over the
conveyor.

**The image shows no robot and no held plate.** The belt is empty end to end —
bare rubber, no plates on the pick surface at all. There is nothing in either
camera that could be a plate on a gripper.

**What is in frame:** two tie plates lying at the **left edge of the belt**, on
the fixed side rail — the nearer one stamped `HW 24`, both with the
characteristic four square holes, unmistakably 14in plates. Behind them is the
staging rack holding a dozen more. The corner of the nearer plate intrudes over
the belt's left edge.

That is the phantom. It is a **parked plate in the camera's field of view that
is not on the pick surface** — permanent scenery, detected on every frame,
never pickable because it is not reachable on the belt.

And it fits the counts better than my version did. A static object gives a hard
floor of exactly 1, on every single one of 180 frames, which is what the
records show — `{1: 157, 2: 21, 3: 2}`, never zero. A held plate would have come
and gone with the gripper.

## What I got wrong, precisely

The held-plate story was an inference from a correlation: the pick pipeline
(fires with a plate on the magnet) never reads 0, the detector pipeline (fires
after the drop) reads 0 on 23 of 73 frames. I read a mechanism into that gap.

The real explanation for the gap is simpler and duller: **the two pipelines use
different detectors and different vision regions.** `14in_plate det` runs
`plate_classifier` with `pose2d_plate_pose` on `vision_region_7`;
`Pick_IdsBelt_new` runs the `config_collection_7` asset on `vision_region_6`.
They disagree about the edge plate because they are not the same detector, not
because one of them is looking at a gripper.

I should have said "something is always detected and never pickable, and I do
not know what it is" and asked for the image first. Instead I named it, and the
naming was wrong. The counts in the previous report all stand — the offset of
+1.14, frames 111 and 137, the 1-in-7.5 no-trajectory rate. The cause does not.

Also void: my claim that Capture @ FoV makes the phantom worse by bringing the
held plate into frame. **The camera is fixed** — part poses sit at a constant
z ≈ 1.1 m in camera frame across all 156 frames, i.e. a camera looking down at
the belt from about a metre. Moving the capture earlier does not change the
camera's view of the gripper, because the camera does not follow the arm. The
+0.42 count shift I measured with the toggle on needs a different explanation,
and I do not have one.

## What this does not change

The fix is the same, and it is now better founded:

```
exclude_depth_outside_vision_region : false
vision_region_6 (pick)   search_region : ""     ← empty
vision_region_7 (detect) search_region : ""     ← empty

search_regions.cuboids.BeltFill                 ← defined, wired to nothing
```

**Detection runs over the whole frame with no spatial restriction**, so a plate
parked on the side rail counts exactly the same as a plate on the belt. A search
region confined to the belt surface excludes it — which is precisely what a
search region is for, and `BeltFill` already exists.

Chain, unchanged: the phantom keeps `nCountPlatesFound` off 1 → `bLastPart`
never arms → no early belt kick → the scene runs dry with no advance queued →
**Branch B**, 3.36 s with the arm parked, on 34 of 63 belt advances.
**+0.56 s a pick.**

## What this adds — a fix with no software in it

**Move those plates.** They are sitting on the conveyor's side rail inside the
camera's field of view. If they are not meant to be there, taking them off the
rail may remove the phantom today, with no config change, no deploy, and no
risk. That is worth trying before anything else, and it is a two-minute test:
clear the rail, run twenty picks, and see whether `plates_found` ever reads 0
and whether the Branch B rate drops.

If they *are* meant to be there — a staging position, or they simply fell off —
then the search region is the fix.

## Order I would go in now

1. **Clear the plates off the belt's side rail**, run 20 picks, watch
   `plates_found` and the Branch B rate. Free, instant, reversible.
2. If that changes nothing, **wire `BeltFill` into `vision_region_6.search_region`**
   after confirming in the APERA UI that the box covers the belt and not the
   rail. (The cuboid carries a rotation I cannot resolve from the JSON, so it
   needs eyes on it.)
3. `nLastPartThreshold` stays at **1**. It is a workaround for a problem that
   now looks like it has a physical fix, and the README already says it should
   go back to 1 if the pipeline is corrected.
4. The `nCountPlatesFound==0` branch in `tkCycle` is still dead code and still
   becomes live again once the count can reach 0 — worth knowing before it does.

## Standing caveat

I have one frame. It shows the belt empty and plates on the rail, and APERA
reported one unpickable candidate for that frame. I have not proved the
detection sits on those plates — no bounding box is recorded for candidates that
fail the pick-point filter, which is why this took an image at all. Two more
frames from a moment when the rail is clear would settle it completely, and
step 1 above produces exactly that as a side effect.
