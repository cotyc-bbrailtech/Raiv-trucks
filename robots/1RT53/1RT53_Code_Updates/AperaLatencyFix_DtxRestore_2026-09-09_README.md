# Raiv-T1 — corrective patch, 2026-09-09

**This is a correction to code and data I shipped you this morning, not a new
feature.** Two independent defects, both mine. Controller `F_24_0064095_C_004`,
application `binpick_TiePlates`.

Everything in `_original/` is byte-identical to what is on the controller
**right now**, taken from backup `Y-2026_M-09_D-09_14h09m` and `cmp`-verified.

| file | on controller now | this patch | what it fixes |
|---|---|---|---|
| `Part_Accept.pgx` | 9,191 | **9,491** | APERA latency stamp |
| `Part_Reject.pgx` | 5,673 | **5,973** | APERA latency stamp |
| `tkBeltScan.pgx` | 34,681 | **35,224** | APERA latency stamp |
| `binpick_TiePlates_RESTORE.dtx` | (`binpick_TiePlates.dtx`, 53,308) | **83,626** | restores the settings my `.dtx` wiped |

No new program, no new task, no `.pjx` change. The three `.pgx` edits are one
`clock()` read each plus comments — no motion, no speed, no descriptor, no
dwell, no IO write.

---

## Defect 1 — `apera_latency_s` was measuring the wrong thing

**Symptom.** In run 10 (13:49, the first run of the new build)
`nAperaLatency_s` read a median of **73.3 s**, max 157 s, climbing steadily
across the run. The true figure should be well under a second.

**Cause.** `_nTrigClk` is stamped after `apera_trigger_trajectory` so that
`nAperaLatency_s` can measure trigger → answer. I stamped **only the four
call sites in `tkCycle.pgx`**. There are **seven** in the project, and the
three I missed are the ones that actually fire in steady state:

| program | trigger | stamped before | now |
|---|---|---|---|
| `Part_Accept.pgx` L96 | the at-place trigger — **294 of 294 picks** in the 09-09 run | no | yes |
| `Part_Reject.pgx` L75 | at-place trigger on the reject path | no | yes |
| `tkBeltScan.pgx` L505 | the early trigger | no | yes |
| `tkCycle.pgx` ×4 | fallback paths, rarely taken | yes | yes |

So `_nTrigClk` was written roughly once per run and the field degenerated into
"seconds since the run started" — a number that looks plausible on the Options
page and is completely wrong.

**Why my own checks passed.** `verify.py` check §7i(d) asserted "every
`apera_trigger_trajectory` is followed by the stamp" but only ever walked
`tkCycle.pgx`. The check was right; its search scope was wrong. It now walks
**all** programs, requires **at least seven** stamped sites so a silently
vanishing call site cannot pass, and a new check (d2) requires the stamp to sit
**before** `bTrajTriggered=true` — the flag that tells `tkCycle` an answer is
coming, so a stamp written after it can be read stale.

`mutate.py` gained three mutations that reproduce exactly this bug, including
one named *"leave the Part_Accept trigger unstamped — the bug that actually
shipped"*.

Current state: **`verify.py` PASS (0 fail, 6 warn)**, **`mutate.py` 52/52 caught, 0 missed**, control clean.

---

## Defect 2 — my `.dtx` overwrote live settings, including a motion descriptor

This is the more serious of the two, and I want to be direct about it: **I
changed a motion descriptor and a tool definition on your robot, having told
you repeatedly that I would not touch either.**

**Cause.** I built the `.dtx` from the `Y-2026_M-09_D-08_14h19m` backup. Between
that backup and the deploy, the controller's `.dtx` was rewritten **twice** by
SP2 "save application data" (visible as `73,467` bytes at the 09h13m backup and
`81,761` at 11h51m, against 49,238 at 14h19m). Those saves captured live tuning.
My file replaced all of it. Nothing in `verify.py` checked whether the baseline
I built against was still the baseline on the controller — it only compared my
file to my own `_original/` copy, which is a tautology.

**What changed.** Nine settings, of which **seven have no code writer** — no
program ever assigns them, so they cannot self-heal and are simply gone:

| setting | on controller before | after my deploy | notes |
|---|---|---|---|
| **`mReach`** | `leave 300, reach 300` (blend **on**) | `blend off, leave 0, reach 0` | motion descriptor, used at `tkCycle` L519 `movej(jTrajectoryStart,…)` — **the exact move you described as "slowing to near stopped"** |
| **`tSchunkEMH084`** | `ioOpen 0.25, ioClose 0.25` | `ioOpen 0.5, ioClose 0.5` | tool definition |
| `nEMH_onDelay` | 0.25 | 0.5 | your sweep value |
| `nEMH_offDelay` | **1.0** | 0.5 | your sweep value |
| `nGripSettle` | 0 | 0.35 | your sweep value |
| `bEarlyBeltKick` | true | *(false)* | early belt kick switched **off** |
| `bBeltSensorStop` | true | false | **the laser-sensor belt stop switched off** |
| `bBeltSensorInvert` | *(false)* | false | no effective change |
| `nDetectorTries` | *(0)* | 0 | no effective change |

Also wiped, but harmless: the rolling cycle-time history (`_nCycleTime25/50/100/1000`,
all the `_nSeg*` windows, `_sCycleTime` display strings, `nCsvSeq`, `nCapAtPlace`).
Statistics only.

**Not affected, despite appearing in the diff.** `pPose`, `pPoseTransform` and
`pGeneralPickPose` are output parameters of `apera_wait_for_trajectory`,
rewritten every pick — and `tkCycle` L142 explicitly zeroes `pPoseTransform` at
startup. `pDropPos` is recomputed in `Part_Accept` L19. `bDryCycle` is forced
false by `init.pgx` L107. None of these are lost data. I checked all 52
programs in the application, not just the ones in the bundle.

**This explains an open question.** `bBeltSensorStop=false` is why run 10 logged
**0 beam-break edges across 4 belt advances** — I had put that down to the
rubber plates. It wasn't the plates. The sensor feature you had switched on was
switched off by my file.

### Two ways to fix it — the manual one is safer

**Option A (recommended). Re-enter nine values by hand.** Use the table above.
`mReach` and `tSchunkEMH084` are two fields each in the SP2 data editor; the
three dwells and the two toggles are on the Options page. This touches nothing
else and cannot repeat the mistake.

**Option B. Deploy `binpick_TiePlates_RESTORE.dtx`** (rename it to
`binpick_TiePlates.dtx`). It is the controller's own 11:51 `.dtx` with my
fourteen new globals spliced in and **nothing else altered** — verified
programmatically: all 221 of the controller's globals preserved with identical
values and attributes, exactly 14 added, XML well-formed.

**Read this before choosing B.** It restores the state as of **11:51 today**.
Anything you have tuned since then it will overwrite, the same way my last file
did. If you have touched anything since, use Option A.

### What I have changed in my own process

`verify.py` §9 checked that no `.dtx` **declaration** was lost and said nothing
about the **values** inside them, which is where machine settings live. New §10
holds a copy of the controller's live `.dtx` in `_ctrl/` and asserts that every
value in it survives into the file being shipped, with an explicit allow-list
for the seventeen names that code genuinely rewrites every run — each entry
carrying the specific write site that justifies it, because "probably
transient" is not a reason. A plain `binpick_TiePlates.dtx` in a bundle now
draws a warning telling you to build it as a merge instead, and the deployable
file is named `_RESTORE` so it cannot be dropped in by reflex.

Five new mutations in `mutate.py` reproduce this defect directly, including
*"ship the .dtx that reverts mReach — a MOTION DESCRIPTOR — to blend off"*. All
five are caught; before §10 existed, all five passed silently.

---

## Test it

1. **Deploy the three `.pgx` files, run a short cycle, watch `APERA s:` on the
   Options page.** It should read a fraction of a second and hold steady — not
   climb. If it still climbs, stop and tell me; the stamp is still being missed
   somewhere.
2. **Then** compare `APERA s:` against the vision wait in the log. Latency ≈
   wait means the trigger is too late and there is time to recover by moving it
   earlier. Latency ≫ wait means most of it is already hidden under motion and
   the remainder is APERA's own floor — the fix would be vision-side, not here.
3. **Restore the nine settings** (Option A or B) and confirm the belt sensor
   lamp comes back to life on the Options page — `sensor stops` should start
   counting again.

## Back out

Copy the three `.pgx` files from `_original/` back over the application. They
are the versions running on the controller now, byte for byte. `_original/`
also contains the 53,308-byte `.dtx` currently on the controller, if you deploy
the restore and want to undo that separately.
