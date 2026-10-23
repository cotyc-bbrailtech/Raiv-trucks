# Raiv-T1 — the phantom IS the held plate. Measured, settled.

Supersedes both `Raiv-T1_2026-09-12_apera_phantom.md` and
`Raiv-T1_2026-09-15_phantom_CORRECTION.md`. The second of those was wrong.

---

## The measurement

The two frame-111 images are a stereo pair, so depth is recoverable from
disparity — how far a feature shifts between the two views. Closer objects
shift more. Normalised cross-correlation on feature patches:

| feature | disparity | distance from camera |
|---|--:|--:|
| **`HW 24` plate** | **98 px** | **≈ 0.39 m** |
| belt surface (wear mark) | 35 px | ≈ 1.10 m |
| belt far rail | 36 px | ≈ 1.10 m |
| plates on the rack behind | 20–27 px | **further** than the belt |

The belt distance is independently confirmed: part poses in the annotations sit
at a constant z ≈ 1.1 m in camera frame across all 156 frames.

**The `HW 24` plate has 2.8× the belt's disparity. It is about 0.71 m above the
belt surface, in mid-air.**

Nothing lies on a side rail 0.71 m up. It is on the magnet. You were right.

The depth ordering also corrects my reading of the scene: the second plate that
looked adjacent to it in 2D is *behind* the belt, not beside it — that is the
staging rack on the ground beyond the conveyor, not a plate on the rail.

## What I did wrong

I had this right on 09-12 from the counts alone. Then I looked at a dark 16-bit
image, could not see a gripper in it, and let "I cannot see it" become "it is
not there." I wrote a confident retraction on that basis.

The stereo pair was in front of me both times. Disparity is a five-line
measurement and it settles the question outright. I reached for my eyes when I
should have reached for the arithmetic — in a session whose whole method has
been *measure it, do not argue it*.

Two specific claims in the correction are void:

- "no robot and no held plate in frame" — **wrong**, quantified above.
- "the camera is fixed, so Capture @ FoV cannot change its view of the gripper"
  — the camera is fixed, but that was never the point: **the arm carries the
  plate through the fixed camera's field of view.** Firing the capture earlier
  catches the arm at a different place on that path, which is exactly how the
  toggle shifts the count. The +0.42 I measured stands unexplained no longer.

## What now stands — the whole chain, confirmed

1. `Pick_IdsBelt_new` fires while a plate is on the magnet. The held plate is in
   frame, detected as a `14in_plate`, and **Unpickable** — the gripper occupies
   its own pick point.
2. It appears on **every one of 180 frames**: unpickable counts `{1: 157,
   2: 21, 3: 2}`, never zero. Reported count exceeds pickable count by **+1.14**
   on average, and the distribution never touches 0.
3. Frames **111** and **137**: belt genuinely empty, APERA reports **1**.
4. `nCountPlatesFound` therefore reads 1 instead of 0 → `tkCycle` takes the
   "parts exist" path → `apera_wait_for_trajectory` returns nothing reachable →
   **Branch B**, 3.36 s with the arm parked.
5. And `bLastPart = (… and nCountPlatesFound <= 1)` can almost never arm, so the
   early belt kick does not fire: **34 of 63 belt advances** go the expensive
   way. **+0.56 s on every pick.**

By contrast `14in_plate det` runs *after* the drop, with an empty magnet, and
reads 0 on 23 of its 73 frames. Same camera. That gap is the phantom.

## The fix, now firmly supported

```
exclude_depth_outside_vision_region : false
vision_region_6 (pick)   search_region : ""     ← empty
search_regions.cuboids.BeltFill                 ← defined, wired to nothing
```

Detection has no spatial restriction, so a plate **0.71 m above the belt** is
counted exactly like one lying on it. A search region shaped around the belt
excludes it on geometry alone — and 0.71 m of clearance is a comfortable
margin, not a marginal call. `BeltFill` already exists.

1. **Wire `BeltFill` into `vision_region_6.search_region`** (likely with
   `exclude_depth_outside_vision_region = true`), after confirming in the APERA
   UI that the box covers the belt. The cuboid carries a rotation I cannot
   resolve from the JSON, so it still wants eyes on it — but the plate it needs
   to exclude is now known to be 0.71 m clear.
2. Then `nCountPlatesFound` reaches 0 honestly, `bLastPart` arms on the real
   last plate, and those 34 advances move onto the cheap sensor path.
3. **`nLastPartThreshold` stays at 1.** It is a workaround for exactly this, and
   it goes back in the drawer if step 1 works.
4. The `nCountPlatesFound==0` branch in `tkCycle` becomes live again — it has
   been unreachable, and it has not executed in production for a long time.

Withdraw the suggestion to clear plates off the rail. There was nothing on the
rail; that was the rack, further away than the belt.
