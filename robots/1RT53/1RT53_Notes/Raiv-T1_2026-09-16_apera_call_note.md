# Project note — call with Quinten, Apera AI (2026-09-16)

## What was discussed

Goal: start the belt conveyor while the robot is still picking the last part in
the scene, so the belt advance overlaps the pick instead of serialising behind
it.

Problem raised: APERA's `apera_inspect` counts parts detected anywhere in the
vision region, including parts at the edge that will not be pickable when the
trajectory call is made. That count is what the cell uses to decide "this is the
last part", so the decision is made on the wrong number.

Quinten understood it immediately and confirmed the distinction: **a detected
part at the edge of the vision region is not the same as a pickable part for
trajectory planning.**

He said a solution already exists for the **Fanuc** drivers — a new call that
returns a **count of pickable parts**, not merely a boolean "is there one". He
is raising a request with Apera engineering to have the equivalent developed for
the **Stäubli** driver.

## Why this is the right fix, in our numbers

This is the root cause of the whole Branch B chain, and we have it measured from
Apera's own recordings (180 frames of `Pick_IdsBelt_new`, run 20):

| | |
|---|--:|
| mean count reported to the robot | **4.12** |
| mean that actually pass "Valid Pick-Points" | **2.98** |
| **over-report** | **+1.14** |
| frames where the reported count was 0 | **0 of 180** |
| frames with ≥1 detection rejected as Unpickable | **180 of 180** |

Two frames (111 and 137) had a **provably empty belt** — zero pickable parts —
and the pipeline still reported **1**.

Consequence in the cell:

- `bLastPart` tests `nCountPlatesFound <= 1`. With a permanent +1 it can almost
  never arm, so the early belt kick does not fire.
- **34 of 63 belt advances** then fall through to the slow path, at **3.36 s
  each with the arm parked**.
- **+0.56 s on every pick**, in a ~4.4 s cycle. About **12%**.
- 24 of 180 frames planned no trajectory at all — one in 7.5.

## The point worth making to Apera engineering

**The number already exists inside the pipeline.** It is not new computation.

Every `annotations/<n>.json` records the part-selection filter chain, and the
first filter is exactly the right one:

```
"filters": [
  { "name": "Valid Pick-Points",
    "results": [ {"candidate_uid": 0, "passed": false, "score": "Unpickable"},
                 {"candidate_uid": 1, "passed": true,  "score": "Pickable"}, ... ] },
  { "name": "Max Pick Attempts", ... },
  { "name": "Visibility", ... }
]
```

The count of candidates with `passed: true` on **Valid Pick-Points** is the
number being asked for. It is computed on every cycle and written to the
recording; it is simply not exposed over the driver interface.

Two refinements worth asking about while the request is open:

1. **Which filter stage?** "Valid Pick-Points" alone is the geometric answer.
   The count after **Visibility** would be closer to "parts we will actually
   plan for" — in our data Visibility rejects a further 0–3 per frame. Being
   able to ask for either, or being told which one the number represents,
   matters for how the robot uses it.
2. **Cost.** The count-only path should not require trajectory planning.
   Apera's own accounting on our pipelines: `Pick_IdsBelt_new` reports a
   1236 ms cycle of which only ~447 ms is named (405 capture + 32 detect +
   10 pickability); the detector-only pipeline `14in_plate det`, which has no
   motion planner, reports 446 ms with 434 named. **~790 ms of the pick
   pipeline is trajectory/grip planning.** A pickable-count call that skips it
   would return in ~0.45 s instead of ~1.24 s.

## What this supersedes on our side

- **`nLastPartThreshold`** (built, ships at 1, not deployed) is a workaround for
  exactly this. If the driver call lands, it stays at 1 and can be retired.
- The **`BeltFill` search region** remains worth doing regardless — it stops the
  held plate and anything outside the belt volume being counted at all, which is
  a different failure from edge-of-region parts. The two fixes are
  complementary, not alternatives.
- The **FoV boundary move to +550** stays; it is about the robot being in shot,
  not about the count.

## Open items

- Quinten → Apera engineering: Stäubli driver, pickable-part count call.
- Ask which filter stage the Fanuc implementation counts at.
- Ask whether the call can skip trajectory planning (the ~790 ms above).
- No date or commitment yet — treat as requested, not scheduled.
