# Backup investigation — F_24_0060113_C_001, 08/31 12h23

**The log came out in this backup. We have real cycle history for the first time.**

Extracted alongside this file:
- `raiv_metrics_2026-08-31.csv` — 9 samples, all 54 columns, ready for Excel
- `raiv_csv_raw_2026-08-31.txt` — the 96 raw log lines

---

## First, a correction I owe you

This backup contains **`logArchive.zip`** (4.8 MB). The 08/28 and 08/31 10h29 backups did
not. Inside it, `mnt/log/user.log` holds **96 `RAIV/CSV` lines** and `screenLog.txt` another
72. **Option 1 works.** The CS9 log does reach a backup, provided the backup includes the
log archive.

I got this wrong twice — first saying it would work (right answer, wrong reasoning), then
saying it would not after the 08/28 backup came back empty. The real variable was the log
archive, which that backup simply did not include. Keep including it and option 1 is your
history mechanism.

One practical note: each line is wrapped in JSON with a trailing `"},"hash":"…"}`, so
extraction needs a strip — that is what the two files above are.

**`bLogRetain` is still false**, so the RaivLog ring is empty as expected. Given logArchive
works, retain is now optional. I would leave it off and skip the retain-memory question
entirely unless you want history readable inside the application.

## The abort-latch fix landed

| | b_fault | b_prod | LRC | clean % |
|---|---|---|---|---|
| before the fix | == full s/plate | 0 | undefined | 0 |
| after | 0 – 0.02 | 4.4 – 6.0 | computing | 60 – 85 |

The loss budget spreads and LRC produces numbers. That was the blocker and it is gone.

**But run 1 went 100% FAULT again**, then runs 2 and 3 were clean. So a fault flag is still
being *set* during a run — the Init fix stopped it persisting across restarts, it did not
stop it happening. Run 3's `b_fault` is 0.005 s/plate with `state` reading FAULT at the
sample instant, so brief faults are being asserted repeatedly. Worth finding which of the
three sources trips (`bERROR["schunk"]`, `bMessage["abort"]`, `bRunning["Abort"]`); a one
-line `logMsg` on each would settle it.

## Where the cell actually is

| run | min | plates | s/plate | pl/hr | gap | LRC p10 | best | clean % | state |
|---|---|---|---|---|---|---|---|---|---|
| — | 4.8 | 47 | 6.189 | 582 | 3.224 | — | — | 0 | FAULT |
| — | 3.6 | 41 | 5.311 | 678 | 2.345 | 3.75 | 3.49 | 72.5 | BELT ADV |
| 1 | 3.7 | 29 | 7.606 | 473 | 4.640 | — | — | 0 | FAULT |
| 2 | 2.0 | 16 | 7.457 | 483 | 4.491 | — | 5.75 | 60 | FAULT |
| 3 | 4.5 | 39 | 6.892 | 522 | 3.926 | 5.75 | 5.31 | 78.9 | RUNNING |
| 3 | 9.5 | 104 | 5.469 | 658 | 2.503 | 3.75 | 3.51 | 80.6 | RUNNING |
| 3 | 11.4 | **134** | **5.106** | **705** | 2.141 | 3.75 | **3.51** | **85** | FAULT |

Target is 2.965 s/plate / 1214 pl/hr. Best sustained: **5.106 s/plate, 705 pl/hr, 58% of
target**, and improving steadily through run 3 as clean % climbed.

**The interesting number is LRC best 3.51 s against an actual of 5.106 s.** The machine
already does 3.5 s when nothing interferes. The 1.6 s difference is losses, not capability.

## Your settle-delay change: measurable, and it worked

`b_belt` (belt advance, s/plate) across the change:

| delay | b_belt | batch_mean | cost per belt episode |
|---|---|---|---|
| 2.5 s | 1.633 | 3.4 | 5.55 s |
| 2.5 s | 1.707 | 3.2 | 5.46 s |
| 1.0 s | 1.568 | 2.5 | 3.92 s |
| 1.0 s | 0.818 | 4.6 | 3.76 s |
| 1.0 s | 0.714 | 4.6 | 3.28 s |
| 1.0 s | 0.554 | 4.6 | **2.55 s** |

`b_belt` alone is confounded by batch size, so the right comparison is cost per *episode*
(`b_belt × batch_mean`): **~5.5 s down to ~2.5–3.9 s**. Your 1.5 s accounts for most of it,
the rest is fewer detector tries and bigger batches. `belt_max` (longest episode) also fell
10.6 → 7.9 → 5.7 s.

Belt advance is now down to 0.554 s/plate — **11% of the cycle**. It is no longer where the
time is.

## Correction: do NOT speed up the trajectory pipeline

I told you the next win was `bin1_TCPA200`. **The metrics say otherwise and I was wrong.**

```
b_vision  =  0.002 – 0.116 s/plate      (essentially zero)
cam_mean  =  1.29  – 1.65  s per look   (substantial)
```

`tkMetrics`' own header makes the call: *camera time high with vision wait near zero means
the concurrent PartFinder is covering the look and a faster camera buys nothing.* That is
exactly this picture. The trajectory capture is already hidden behind robot motion. Rewriting
that pipeline would buy ~0.1 s/plate at best. Don't spend the time.

## Where the time actually is

`b_prod` is **4.453 of 5.106 s/plate — 87% of the cycle is productive motion.** Phase means
from run 3's last sample:

| phase | s | |
|---|---|---|
| ph15 **To capture** | **1.469** | the move back to the camera pose |
| ph2 **Pick linear approach** | **1.277** | Apera descent onto the part |
| ph7 Accept linear approach | 0.727 | |
| ph4 Pick retreat | 0.582 | |
| ph1 Pick approach | 0.432 | |
| ph5 Accept start | 0.335 | |
| ph6 Accept approach | 0.320 | |
| ph9 Accept retreat | 0.292 | |
| ph3 Pick linear retreat | 0.244 | |
| ph8 Accept linear retreat | 0.236 | |
| ph10–14 Reject | `--` | no rejects this run |

**ph15 + ph2 = 2.746 s of a 5.106 s cycle — 54%.** Those two moves are the cycle now.
`still_pct` 28.6% and `pick_still` 21.5% say a fifth of the pick is the arm standing still,
which is gripper actuation and `waitEndMove` handshakes.

That is where I would look next, and it is motion work, not vision work.

## Two other things in the log

**The early belt kick is falling back 16% of the time.** 8 × `no clean belt-clear edge in
3s - using FOV-clear belt start this cycle`, plus 1 × the older message. Across ~50 belt
episodes that is roughly one in six cycles silently forfeiting the optimization and running
the old timing. The fallback is doing its job — nothing broke — but the lift edge is not
being seen. Either 76.2 mm is not reached inside the armed window, or 3 s is too short.
`nBeltClearHeight_mm` and `nBeltKickTimeout_s` are both public, so this is testable without
a code change: try 50 mm, or a 5 s timeout, and watch the message rate.

**11 × feeder starved** and **25 × metrics reset**. The resets are what fragment the history
into those short runs — each one discards the accumulators. Less costly now the log
persists, but worth knowing when you read the table above.

## Suggested order from here

1. Find the intermittent fault source — it cost you run 1 entirely and it is corrupting the
   budget whenever it trips.
2. Chase the belt-clear fallback rate with the two public knobs. Free, and it is 1-in-6
   cycles not getting the optimization you already paid for.
3. Then ph15 and ph2. That is the real 54%.
4. Leave the trajectory pipeline alone.
