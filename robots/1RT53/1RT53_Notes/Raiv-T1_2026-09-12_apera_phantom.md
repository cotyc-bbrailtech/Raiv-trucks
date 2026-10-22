# Raiv-T1 — the phantom plate, found in APERA's own records

Source: `binpick_pipelines.json` (both copies identical), plus `annotations/` and
`pipeline_input/` from both recordings — **253 frames**, no imagery needed.

Your eye was right, and the records are more specific than the eye could be.

---

## 1. The two pipelines do not count the same way

| | `14in_plate det` | `Pick_IdsBelt_new` |
|---|---|---|
| frames | 73 | 180 |
| **reports a count of 0** | **23 times** | **never** |
| minimum count | **0** | **1** |
| median count | 1 | 4 |
| always ≥1 "Unpickable" detection | no | **YES — every frame** |
| cycle time (median) | **0.446 s** | **1.236 s** |

Those two cycle times are the numbers I measured from the controller log
yesterday without knowing where they came from: Branch B's detector loop costs
**0.44 s per try**, and `br_traj` / `apera_latency` sit at **1.24 s**. The
recordings and the VAL3 log are describing the same machine.

## 2. The pick pipeline over-reports by almost exactly one

Across 180 frames of `Pick_IdsBelt_new`:

| | mean |
|---|--:|
| candidates reported | **4.12** |
| candidates that actually pass "Valid Pick-Points" | **2.98** |
| **offset** | **1.14** |

And the count distribution never touches zero:

```
reported : {1:2, 2:31, 3:43, 4:40, 5:30, 6:13, 7:10, 8:8, 9:3}
pickable : {0:2, 1:35, 2:43, 3:38, 4:33, 5:13, 6:10, 7:3, 8:3}
```

The whole distribution is shifted right by one. I inferred a **+0.42** offset
from the cycle log; the ground truth is **+1.14**, and it is present on every
single frame rather than intermittently.

## 3. Frames 111 and 137 are the proof

Two frames in the pick recording where the belt was genuinely empty — zero
pickable parts:

```
frame 111:  candidates 1  ·  pickable 0  ·  Valid Pick-Points: "Unpickable"
            Max Pick Attempts: []   Visibility: []   sorter: null
            annotations: []   →  no trajectory planned
```

**APERA reported one part. There was nothing on the belt.**

`nCountPlatesFound` therefore reads 1, not 0. `tkCycle` tests
`if nCountPlatesFound!=0`, takes the "parts exist" path,
`apera_wait_for_trajectory` comes back with nothing reachable — and that is
**Branch B**, 3.36 s with the arm parked.

The rate agrees too: **24 of 180 frames planned no trajectory — one in 7.5.**
I measured one Branch B pass every 6.0 picks from the log.

## 4. Why the detector can count to zero and the pick pipeline cannot

Same camera (`capture_2`). The difference is *when* each one fires.

`14in_plate det` runs **inside Branch B's loop**, after `Part_Accept` has
finished — the magnet is **empty**. It reads 0 on 23 of 73 frames.

`Pick_IdsBelt_new` fires from `apera_trigger_trajectory`, which in this cell
always happens **with a plate on the magnet** — at the drop approach with
Capture @ FoV off, or a second earlier with it on. It never reads 0, and it
always carries at least one detection with no valid pick point.

A plate held against the magnet face is exactly what that looks like: the
detector recognises a 14in_plate, and the grip planner finds no valid
pick-point on it because the gripper is already occupying the approach.

## 5. The configuration reason — and it is a one-line fix

Both pipelines:

```
exclude_depth_outside_vision_region : false
vision_region_6 (pick)   search_region : ""     ← empty
vision_region_7 (detect) search_region : ""     ← empty
```

**Neither pipeline has a search region.** Detection runs over the whole frame,
so anything plate-shaped anywhere in view becomes a candidate.

And a search region already exists, fully defined, wired to nothing:

```
search_regions.cuboids.BeltFill
  reference frame : robot
  width 0.568 m · height 0.4514 m · depth -0.18 m
  pose z = -0.227 m
```

The TCP at capture time sits at **z = +0.085 to +0.23 m** in the same robot
frame, well above that box. So a plate on the gripper should fall outside
`BeltFill` while plates on the belt fall inside it.

**Caveat, and it matters:** the cuboid carries a rotation (`p -177.9°,
w -89.5°`), so I cannot say from the JSON alone which axis the 0.4514 m
"height" runs along, and I have not seen the region drawn. The direction is
right; someone who can open this in the APERA UI should confirm the box
actually contains the belt and excludes the gripper before switching it on.

## 6. What to do

1. **Set `vision_region_6.search_region = BeltFill`** (and likely
   `exclude_depth_outside_vision_region = true`) in the APERA UI, after
   confirming the region visually. This is the root-cause fix: the count starts
   meaning "plates on the belt".
2. **Then `nCountPlatesFound` reaches 0 honestly**, `bLastPart` arms on the real
   last plate, the early kick fires, and those 34-of-63 belt advances move off
   Branch B. Worth **−0.56 s a pick**.
3. **The `nLastPartThreshold` bundle becomes unnecessary** if step 1 works —
   leave it at 1. It is a workaround for exactly this, and the README already
   says so. If the pipeline cannot be changed, set it to 2 and the arithmetic
   works out the same way, for a worse reason.
4. Worth knowing separately: the **empty-scene branch in `tkCycle` is dead
   code**. `nCountPlatesFound==0` has been unreachable because the pick pipeline
   cannot report 0. After the fix it becomes live again — which is correct, but
   it is a path that has not executed in production for a long time.

## 7. The one thing still unproven

I have not *seen* the phantom. Everything above is counts and filter outcomes:
a detection that is present on all 180 frames, always unpickable, absent from
the pipeline that fires with an empty gripper.

**One PNG would close it**: `capture/…/111.png` (or `137.png`) from the
`Pick_IdsBelt_new` recording — a frame where the belt was empty and APERA still
reported one part. A single file out of the 7 GB. If that image shows a plate
hanging off the magnet, there is nothing left to argue about.
