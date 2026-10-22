# Raiv-T1 — what EarlyBeltKick was worth on 9/11, steel plates, live belt

Answering: *how much did EarlyBeltKick impact cycle time when the sensor was working
as expected?*

**Short answer: about 2.6–2.9 s off every belt advance, and it only got to do that on
20 of the 35 advances — so roughly 0.28 s/pick realised, with about the same amount
still on the table.**

---

## 1. Which window counts as "sensor working as expected"

9/11 has two steel runs. They are not equally clean:

| | run 19 (10:42–11:21) | **run 20 (14:00–14:19)** |
|---|--:|--:|
| picks | 318 | **203** |
| laser belt stops | 11 | **26** |
| sensor agreed with confirm-detect | 11 / 11 | **26 / 26** |
| sensor disagree / chatter | 0 / 0 | **0 / 0** |
| **sensor timeouts** | **2** | **0** |
| **camera fallbacks** | **1** | **0** |
| lift-not-seen (kick armed, no lift) | 3 | 0 |

Run 19 is the knocked-about period — twice the beam saw no new plate inside the
timeout and the scan fell back to the camera poll. **Run 20 is the clean window** and
everything below is measured there.

Run 20 also carries the Branch B instrumentation, which run 19 does not, so it is the
only window where the two ways a belt advance can happen are separately visible.

Toggles were unchanged all day: `bEarlyBeltKick` **true**, `bBeltSensorStop` **true**,
`bCaptureOnFovClear` **false**.

## 2. What the kick is being compared against

A scene runs out. The belt has to advance. Two ways that happened:

- **Kick-led** — `bLastPart` armed, the lift watcher fired at 76.2 mm, the conveyor
  started during the place motion, `tkBeltScan` ran the detect loop in parallel.
- **Serial** — `bLastPart` never armed, so the robot placed, asked APERA for a
  trajectory, got none, and fell into **Branch B**: travel to trigger pose, belt on,
  detect, belt off, settle, re-trigger — **with the arm parked the whole time.**

Run 20 had **35 belt-advance episodes: 20 kick-led, 15 serial.** (Adjacent disrupted
cycles are grouped into one episode; without that, consecutive Branch B passes get
double-counted.)

## 3. The measurement

Baseline cycle — no advance, no Branch B: **4.56 s**, n = 154.

| | n | episode excess over baseline (median) |
|---|--:|--:|
| **Kick-led advance** | 20 | **3.95 s** |
| **Serial advance** | 15 | **7.65 s** |
| difference | | **−3.70 s**, Mann-Whitney **p = 0.0023** |

That raw 3.70 s is too generous. Serial episodes are not a fair control — they land on
smaller batches (median batch 2 vs 4) and longer belt runs (4.2 s vs 2.8 s median),
both of which cost time on their own. Adjusting:

| model | kick effect | p |
|---|--:|--:|
| unadjusted | −3.12 s | 0.018 |
| + batch size | **−2.85 s** | 0.031 |
| + batch size + belt run time | −2.59 s | 0.070 |

**Take −2.6 to −2.9 s per belt advance.** The 95% interval on the fullest model is wide
(−5.4 to +0.2) on 35 episodes; the effect is real but the size is ±1 s at best.

### Why that number is believable

It sits just under the mechanistic ceiling. The kick cannot save belt travel — that is
physical — it can only overlap it with work the robot was doing anyway: place + return
(~1.2 s), the failed trajectory round trip (~1.24 s), and Branch B's travel to the
trigger pose (0.65 s) ≈ **3.1 s of overlap available**. An adjusted estimate of 2.6–2.9 s
fits inside that. The unadjusted 3.70 s does not, which is the reason to prefer the
adjusted one.

### And the segment split shows the mechanism directly

Median segments on the episode's first cycle:

| | kick-led | serial |
|---|--:|--:|
| `seg_place_return_s` | **3.60** | 0.82 |
| `seg_return_s` | **2.28** | 0.00 |
| `br_total_s` (arm parked) | — | **3.68** |
| — of which detect | — | 1.31 |
| — of which trajectory | — | 1.24 |

On a kick cycle the belt wait is absorbed into motion the robot is already making. On a
serial cycle the same wait appears as 3.68 s of Branch B with the arm stationary. That
is the whole feature, visible in the segment columns.

## 4. What it actually delivered, and what it did not

- **Realised:** 20 kick-led advances × ~2.85 s ≈ **57 s saved across 203 picks
  ≈ 0.28 s/pick**, about **5%** of run 20's 5.63 s mean cycle.
- **Left on the table:** the kick armed on only **20 of 35** advances (57%). Every miss
  is the phantom — `bLastPart` needs `nCountPlatesFound <= 1` and the held plate keeps
  the count off 1. Closing that is worth roughly another **43 s / 0.21 s per pick**.
- **Partial failures:** **5 of 27** kicks (19%) fired and *still* ended in Branch B —
  the belt ran, but the rescan did not produce a pickable scene. Those cycles cost
  10.68 s median, the worst class in the run.

## 5. Caveats worth keeping attached to these numbers

- **This is not an A/B.** `bEarlyBeltKick` was true all day; the split is by whether
  `bLastPart` armed. Kick-led and serial episodes therefore differ systematically, which
  is why the adjusted estimate is the one to quote.
- **Run 19 cannot replicate it.** All 11 of its belt advances were kick-led, so there is
  no comparison group. Its kick episodes cost 2.41 s excess over a 4.43 s baseline,
  consistent but not independent evidence.
- **n = 35 episodes.** Worth re-measuring on a longer clean run, especially once the
  count is trustworthy and the kick arms every time.
