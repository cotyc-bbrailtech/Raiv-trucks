# Request: pickable-part count over the Stäubli driver

**Cell:** Raiv-T1 — Stäubli TX2-140 / CS9, Apera Vue stereo pair, conveyor-fed steel tie plates
**Site:** B & B Metals / Genesis Rail · **Contact:** Coty C. · **Date:** 16 Sep 2026
**Pipelines referenced:** `Pick_IdsBelt_new`, `14in_plate det`

---

## The ask

Expose, over the Stäubli driver, **the number of candidates that pass the "Valid Pick-Points"
filter** — the same capability Quinten confirmed already exists for the Fanuc drivers. Today the
driver returns a detection count, and a detection at the edge of the vision region is not a part
the trajectory call will pick.

## Why it matters here

We want to start the conveyor while the robot is still lifting the **last** part in the scene, so
the belt advance overlaps the pick instead of serialising behind it. That decision is made on the
part count. Because the count includes parts that will not be pickable when the trajectory call is
made, the "last part" condition almost never becomes true, and the overlap never happens.

## Measured — 180 frames of `Pick_IdsBelt_new`

| | |
|---|--:|
| Mean count reported to the robot | **4.12** |
| Mean actually passing "Valid Pick-Points" | **2.98** |
| **Over-report** | **+1.14** |
| Frames where the reported count was 0 | **0 of 180** |
| Frames with ≥1 detection rejected as Unpickable | **180 of 180** |
| Frames where no trajectory was planned at all | 24 of 180 (1 in 7.5) |

Two frames (**111** and **137**) had a **provably empty belt** and the pipeline still reported **1**.
On frame 111 the extra object is the plate held on the magnet: stereo disparity puts it 0.39 m from
the camera against 1.10 m for the belt surface — roughly 0.7 m up in the air.

**Cost to the cell:** the last-part condition cannot arm, so **34 of 63 belt advances** fall to the
slow serial path at **3.36 s each with the arm parked** — about **+0.56 s on every pick** in a
~4.4 s cycle, **≈12%**.

## The number already exists — it is not new computation

Every recording writes the part-selection filter chain to `annotations/<n>.json`, and the first
filter is exactly the right one:

```json
"filters": [
  { "name": "Valid Pick-Points",
    "results": [ {"candidate_uid": 0, "passed": false, "score": "Unpickable"},
                 {"candidate_uid": 1, "passed": true,  "score": "Pickable"} ] },
  { "name": "Max Pick Attempts", "...": "..." },
  { "name": "Visibility",        "...": "..." }
]
```

The count of `passed: true` on **Valid Pick-Points** is the value being requested. It is computed
every cycle and already written to the recording — it is simply not exposed over the driver
interface.

## Two questions for engineering while the request is open

1. **Which filter stage does the Fanuc call count at?** "Valid Pick-Points" alone is the geometric
   answer. The count *after* **Visibility** is closer to "parts we will actually plan for" — in our
   data Visibility rejects a further 0–3 per frame. Either is useful; knowing which one the number
   represents, or being able to ask for both, changes how the robot uses it.
2. **Can the count-only call skip trajectory planning?** Apera's own timing on our pipelines:
   `Pick_IdsBelt_new` reports a **1236 ms** cycle of which only ~447 ms is named (405 capture +
   32 detect + 10 pickability), while the planner-free `14in_plate det` reports **446 ms** with
   434 ms named — i.e. **~790 ms is trajectory and grip planning**. A pickable-count call that
   skips it should return in ~0.45 s rather than ~1.24 s, which would make it cheap enough to ask
   on every cycle.

## What we are doing on our side in the meantime

- Adding a **search region** to the belt vision region so volumes above the belt (the held plate)
  are excluded from detection entirely. This is complementary, not an alternative — it addresses
  the held part, not edge-of-region parts.
- Moved the robot's "clear of camera" boundary 240 mm downstream, to the measured point where the
  gripper and its plate actually leave the camera's view.
- A local threshold workaround is built but inert. **If the driver call lands, it is retired.**

*Happy to share the recordings, the frame-level annotation extracts, or the cycle logs behind any
number above.*
