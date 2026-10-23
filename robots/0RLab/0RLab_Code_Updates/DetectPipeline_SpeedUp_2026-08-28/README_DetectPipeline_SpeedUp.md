# Raiv-Lab — Belt-Indexing Detect Pipeline Speed-Up (bin1_TCPA200_detect)

Prepared: August 28, 2026
Scope: rewrites the Apera Vue pipeline `bin1_TCPA200_detect` — the pipeline
`tkPartFinder` calls while indexing the feeder belt, purely to count/classify
parts (`apera_inspect` → `nClassesFound`/`sClassID`/`nObjectCount`). **The
real pick-trajectory pipeline, `bin1_TCPA200`, is completely untouched** —
this only changes the fast "is anything on the belt yet" check.

Built by comparing `Raiv-Lab/08282026_Lab_binpick_pipelines.json` against
`Raiv-T1/08252026_Raiv-T1_binpick_pipelines.json`, specifically T1's fast
detection pipeline `14in_plate det`.

## What's in this folder

| File | What it is |
|---|---|
| `Lab_binpick_pipeline_rewrite.json` | A full copy of your Lab pipelines config with exactly 7 fields changed (diffed byte-for-byte against the original — see below). Import this to replace your current Lab pipelines config. |
| `README_DetectPipeline_SpeedUp.md` | This file. |

## What was actually making Lab's detect pipeline slow

I expected the difference between Lab's `bin1_TCPA200_detect` and T1's
`14in_plate det` to be mostly about image resolution or exposure timing.
It's not — the real gap is that **Lab's "detect" pipeline is running the
entire production grasp-planning stack on every single belt-index capture**,
for a call whose result (`nObjectCount`) never uses any of it:

- **`grip_planner_4`** (Lab's current one): `auto_planner_config` samples
  **2,500 grasp candidates × 8 tool-transform orientations**, with up to
  **10,000 candidates run through grasp-collision checking**, against **50
  enumerated pick points** across all 5 part classes.
- **`motion_planner_7`**: full **RRT-based collision-aware motion search**
  (up to a **10-second** `global_timeout_ms`), including building an
  approach/retreat **collision mesh from the depth data** (up to 450
  triangles) before it can even start searching.
- **`part_selector_3`**: the full `fbs_custom` candidate pipeline — priority
  binning, visibility binning, multiple filters, and a pickability sorter.
- **`robot_context`**: ties the above into the real robot geometry, which
  only matters if you're actually going to plan a motion.

T1's `14in_plate det` runs none of that: `motion_planner`, `part_selector`,
and `robot_context` are all **empty strings** in a real, working T1
pipeline, and its `grip_planner_3` has **no `auto_planner_config` and an
empty `pick_points` list** — i.e. a grip planner object that exists (this
field can't be blanked) but does no sampling. T1 also swaps in a dedicated
lightweight 2D `part_detector` + `pose` (2D pose only, no 6D grasp geometry)
+ `static_depth` (cached, not recomputed per frame) instead of the full
stereo/grasp path — but those reference trained AI model files
(`vt24080201_bnb_plate_classifier__detector_v1.0.0`, per-part CAD pose
models) that are specific to what's been deployed on that Apera Vue
installation. **I did not port that part** — see "What I deliberately did
not change" below.

## The 7 changes, and why each one is safe

| Field | Old | New | Why |
|---|---|---|---|
| `bin1_TCPA200_detect.motion_planner` | `motion_planner_7` | `""` | Matches T1's proven pattern exactly (empty string is a valid "off" state for this field — T1's own working pipeline uses it). Eliminates the RRT search + depth-collision-mesh build on every belt-index capture. `apera_inspect()` never reads a planned motion. |
| `bin1_TCPA200_detect.part_selector` | `part_selector_3` | `""` | Same pattern as T1. Eliminates the fbs_custom binning/filtering/sorting pass. `apera_inspect()` doesn't consume a selected/ranked candidate — it just wants the raw class counts. |
| `bin1_TCPA200_detect.robot_context` | `RAIV_pick_belt_1_robot_context_2` | `""` | Same pattern as T1. Only meaningful when a motion is actually being planned against real robot geometry. |
| `bin1_TCPA200_detect.grip_planner` | `grip_planner_4` | `grip_planner_5` (**new**) | New grip planner, cloned from `grip_planner_4` with `pick_points: []` and `auto_planner_config` removed — same shape as T1's `grip_planner_3`. Keeps the field non-empty (T1 never blanks it, so treat it as required) but with nothing to enumerate or sample. |
| `bin1_TCPA200_detect.capture` | `capture_6` | `capture_7` (**new**) | New capture profile, cloned from `capture_6` — **same physical camera** (`stereo_pair_1`), same resolution/ROI/bit depth — with only the first HDR exposure candidate shortened (33333µs → 11111µs, the same ratio T1 uses). Lets auto-exposure converge faster per capture without touching the camera your real pick pipeline (`bin1_TCPA200`) also depends on. |
| `datablocks.grip_planners.grip_planner_5` | *(new)* | see above | Supporting object for the change above. |
| `datablocks.captures.capture_7` | *(new)* | see above | Supporting object for the change above. |

Everything else — `config_collection_7` (the actual classifier model bundle
that produces `nClassesFound`/`sClassID`), `vision_region_3`,
`bin_finding_config`, `pattern_finding_config`, `pose_check_config`,
`range_finding_config`, `continuous_processing` — is untouched. Those are
what actually do the classification; none of them were the bottleneck.

I diffed the full rewritten file against your original field-by-field —
these 7 changes are the only differences anywhere in the file.

## What I deliberately did not change

- **`bin1_TCPA200`** (the real trajectory-finding pipeline `tkPartFinder`
  calls via `apera_trig_traj`/`apera_wait_traj` right before a pick) — not
  touched at all. It still has its full `grip_planner_3` /
  `motion_planner_6` / `part_selector_2` / `robot_context`, because that one
  *does* need to produce a real, collision-checked grasp trajectory.
- **Switching cameras.** Lab's `capture_2` (already in your file, unused by
  this pipeline) points at `stereo_pair_2` — a **different, separately
  calibrated physical camera pair** (`camera_4108818891`/`892`, not
  `camera_4108851213`/`214`). T1's fast pipeline happens to also use
  `stereo_pair_2`-style settings, but for Lab that would mean re-aiming the
  detect pipeline at different hardware, which I can't verify is even
  mounted to see the feeder. I kept `capture_7` on `stereo_pair_1` — the
  same camera your pick pipeline already uses and trusts.
- **Pixel format / resolution.** T1's fast capture uses `mono8` (8-bit,
  half the data of Lab's `mono12p`) and doesn't use Lab's manual full-sensor
  ROI. I left `capture_7` at `mono12p` and the same ROI as `capture_6`,
  because `config_collection_7`'s classifier may have been tuned against
  that bit depth/resolution, and I have no way to verify that from a config
  file alone. If you want to chase this further, it's a small additional
  edit once someone can confirm the classifier tolerates 8-bit input.
- **A lightweight 2D `part_detector`/`pose` stage** like T1's
  `plate_classifier` + per-part CAD pose models. Lab's config has **no
  `part_detectors` or `pose_estimators` section at all today** — porting
  this would mean either those exact trained model files
  (`vt24080201_bnb_plate_classifier__detector_v1.0.0`,
  `vt24032602_B_and_B_14inch__cad_v1.0.0`, etc.) already exist in Lab's
  Apera Vue model library, or training/uploading new ones for Lab
  specifically. That's a bigger, higher-stakes change I didn't want to
  guess at.

## Merge steps

1. Back up your current Lab pipelines config (or keep
   `08282026_Lab_binpick_pipelines.json`, which this was built from).
2. Import `Lab_binpick_pipeline_rewrite.json` into Apera Vue for the Lab
   cell (Apera Vue's config import/restore — check with whoever normally
   pushes these `.json` exports for the exact import path on your install).
3. In Apera Vue, open `bin1_TCPA200_detect` and confirm it shows
   `capture_7` / `grip_planner_5` / motion planner, part selector, and robot
   context all blank, and that it still lists `config_collection_7` and
   `vision_region_3` exactly as before.
4. **Test with the robot in manual/reduced-speed mode first.** Run the
   feeder with a part on it and confirm `tkPartFinder`'s detector loop
   (`nPartsFound`, `bMessage["Feeder"]`) still classifies parts correctly —
   this changes *how fast* the detect pipeline runs, not what it's supposed
   to find, but it's still an Apera Vue config change and deserves a real
   look before production.
5. Time a handful of belt-indexing cycles before/after (e.g. via the
   per-segment cycle timing added in
   `Raiv-T1/CycleTiming_Update_2026-08-26`, if something equivalent exists
   for Lab) to confirm the improvement is real on your hardware.
6. Confirm the starved-feeder path still works: run the feeder empty and
   check `bMessage["Feeder"]` still comes on after `nDetectorTries` attempts
   (unrelated to this change, but worth re-confirming after any pipeline
   edit).
7. Only then run it in normal production mode.

## If you want to go further

The biggest remaining lever is the one I didn't take: a real lightweight 2D
detector + pose stage like T1's, instead of reusing the full stereo/grasp
`config_collection_7` path just to get a count. That requires confirming
(with Apera support or whoever manages Lab's Vue model library) whether the
same or equivalent trained models T1 uses are available for Lab's camera/
part set — happy to draft that pipeline definition once that's confirmed.
