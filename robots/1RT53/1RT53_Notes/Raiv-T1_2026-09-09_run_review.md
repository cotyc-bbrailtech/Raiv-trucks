# Raiv-T1 — 2026-09-09 review

Backup `Y-2026_M-09_D-09_14h09m`, controller `F_24_0064095_C_004`, application
`binpick_TiePlates`. Three runs, 1,262 logged picks. Also read: the `09h13m` and
`11h51m` backups, which turned out to matter more than the pick data.

**The headline is not the rubber-plate run.** It is that the `.dtx` I gave you
this morning overwrote live machine settings — including a motion descriptor and
the tool definition — and that the day's own data shows the cell was running
0.47 s a pick slower than its best measured setting.

---

## 1. My `.dtx` deploy wiped live settings. Restore these nine.

I built that `.dtx` from the `09-08 14h19m` backup. Between then and the deploy,
somebody did an SP2 **save application data** twice — the `.dtx` on the
controller went 49,238 → 73,467 (by 09:13) → 81,761 bytes (by 11:51). Those
saves captured live tuning. My file replaced the lot.

| setting | before my deploy | now | can it self-heal? |
|---|---|---|---|
| **`mReach`** | leave 300, reach 300 (blend **on**) | blend off, leave 0, reach 0 | **no** |
| **`tSchunkEMH084`** | ioOpen/ioClose **0.25** | 0.5 | **no** |
| `nEMH_onDelay` | 0.25 | 0.5 | **no** |
| `nEMH_offDelay` | 1.0 | 0.5 | **no** |
| `nGripSettle` | 0 | 0.35 | **no** |
| `bEarlyBeltKick` | true | false | **no** |
| `bBeltSensorStop` | true | false | **no** |
| `bBeltSensorInvert`, `nDetectorTries` | (unset = 0/false) | 0/false | no change in effect |

I checked all 52 programs in the application: none of the seven marked "no"
is ever assigned in code. They are pure configuration, so they stayed wrong
until somebody re-enters them.

`mReach` is used in exactly one place — `tkCycle` L519,
`movej(jTrajectoryStart, tSchunkEMH084, mReach)`. **That is the move you
described as "slowing to near stopped speed".** Someone had already tuned it to
blend-on with 300 mm leave/reach zones; my file put it back to blend off. I had
been reasoning about that pause from the blend-off value in my stale baseline,
not from what was actually on the machine.

Two other consequences worth naming:

- **The belt laser sensor was switched off.** `bBeltSensorStop=false` is why run
  10 logged 0 beam-break edges across 4 belt advances. I had blamed the rubber
  plates in my last note. That was wrong — the feature was off.
- **The early belt kick was switched off** the same way.

Also wiped, and genuinely harmless: the rolling cycle-time history
(`_nCycleTime25/50/100/1000`, the `_nSeg*` windows, `_sCycleTime`, `nCsvSeq`,
`nCapAtPlace`). Statistics, not settings.

**Not lost, despite showing in the diff:** `pPose`, `pPoseTransform`,
`pGeneralPickPose`, `pDropPos`, `bDryCycle`. Each is rewritten by code every
pick or at init — `apera_wait_for_trajectory` output parameters, `tkCycle` L142
zeroing the transform, `Part_Accept` L19 recomputing the drop, `init.pgx` L107
forcing dry-cycle false. Your taught data is intact.

**How to fix.** The patch bundle carries a merged `binpick_TiePlates_RESTORE.dtx`
(the controller's own 11:51 file plus my fourteen new globals, nothing else
altered, verified value by value). But re-entering nine numbers by hand is
safer and I would do that instead — a `.dtx` deploy is what caused this.

**What I changed in my process** is in the bundle README: `verify.py` only ever
compared my build against my own copy of the baseline, which cannot detect that
the baseline went stale. It now holds a copy of the controller's live `.dtx` and
fails if any value in it would be lost, with an explicit allow-list of the
seventeen names code genuinely rewrites — each carrying the write site that
justifies it. Five new mutations reproduce this exact defect; all five passed
silently before the check existed.

---

## 2. The dwell sweep has a clear answer, and the cell is not using it

Runs 8 and 9 swept the three dwells across 1,225 picks. Grouping every pick by
the settings it actually ran at:

| on / settle / off | picks | cycle median | p90 | approach | retreat | place+return | vision wait |
|---|---:|---:|---:|---:|---:|---:|---:|
| **0.25 / 0 / 0.25** | 86 | **4.29 s** | 4.47 | 0.60 | 1.26 | 0.68 | 0.88 |
| 0.25 / 0 / 0.75 | 39 | 4.35 s | 4.53 | 0.67 | 1.26 | 1.07 | 0.49 |
| 0.5 / 0 / 0.5 | 65 | 4.53 s | 4.72 | 0.60 | 1.26 | 0.82 | 0.73 |
| 0.25 / 0 / **1.0** | 884 | 4.76 s | 4.89 | 1.11 | 1.36 | 1.32 | 0.19 |
| 0.5 / 0.35 / 0.5 *(shipped default — where it sits now)* | 181 | **4.88 s** | 5.05 | 0.60 | 1.26 | 0.82 | 0.73 |

Two things fall out.

**The magnet-off delay is the dominant lever, and it was left at its worst
value.** 884 picks — 70% of the day — ran at `nEMH_offDelay=1.0`, which costs
**0.47 s a pick** against 0.25. At 4.29 s you get 14.0 picks/min; at 4.76 s you
get 12.6. Over an 8-hour shift at the same uptime that is roughly **650 more
plates**.

**Longer dwell hides vision but never pays for it.** Watch the vision wait
collapse from 0.88 s to 0.19 s as off-delay goes 0.25 → 1.0: APERA's answer is
ready before the arm needs it. But approach grows 0.51 s and place+return grows
0.64 s over the same span. You buy back 0.69 s of waiting and spend 1.15 s to do
it. **The ~0.9 s of vision latency is genuinely hideable — dwell is just the
most expensive way to hide it.** Triggering earlier is the cheap way, which is
what `nAperaLatency_s` was meant to measure and could not (§4).

**The caveat that matters.** None of those 86 picks at 4.29 s had grip
confirmation, so we cannot say whether the plates were actually held and
released. Presumably off-delay was raised to 1.0 *because* plates were sticking.
That is exactly the question the new grip fields answer, and they were not on
the machine yet. Once the patch is in: run 0.25/0/0.25 for a few hundred picks
and read `grip_ok`. If it stays 1/1/0, the 0.47 s is free.

---

## 3. The cell was powered and idle for 4h18m

| window | state |
|---|---|
| 08:30–09:11 | run 8, 355 picks |
| 09:14–10:28 | run 9, 870 picks |
| **10:28–13:46** | application running (130.8 min, then 127.5 min), **zero picks logged, zero errors logged** |
| 13:49–13:52 | run 10, 37 picks |

The application was started and stopped normally at 11:35/11:39 and 13:46/13:48,
and the log is completely silent in between — no faults, no starvation warnings,
no belt activity. Some of that is the deploy and the rubber-plate setup. But
258 minutes of application uptime producing nothing is worth a look at whatever
was happening on the floor: if the cycle task was left stopped while the
application idled, nothing in the current logging says so, and that is a gap
worth closing (a heartbeat line from `tkIOMonitor` when `taskStatus("cycle")==-1`
would cost nothing).

Achieved rates, for reference — these include every stall, so they are the real
numbers, not the cycle medians:

- run 8: 8.07 picks/min (cycle time was only 77% of the elapsed span)
- run 9: **11.82 picks/min** (92% — the cleanest sustained running in the dataset)
- run 10: 12.29 picks/min over 3 minutes

---

## 4. Instrumentation: two of three fields validated, one was broken

**Run 10 was 37 picks on rubber plates that the magnet cannot lift.** No cycle
time from it is a pick-rate figure and I have used none of it that way. What it
*is* good for is testing the new sensors against a known answer.

| field | run 10 | verdict |
|---|---|---|
| `grip_part_at_pick` | 0 on all 37 | **correct.** No plate was on the magnet, and the sensor said so. |
| `grip_part_at_drop` | 0 on all 37 | **correct.** Nothing to release. |
| `grip_mag_at_pick` | 0 on all 37 | **ambiguous.** Either the bit means "magnetised *onto a part*", or it is sampled after the coil pulse ends. A steel run separates the two. |
| `monitor_speed` / `speed_applied` | 100 / yes on all 37 | **first measured proof** the 100% override actually takes with the pendant disconnected. |
| `apera_latency_s` | median 73.3 s, max 157 s, climbing | **broken. My defect.** |

The latency bug: `_nTrigClk` is stamped after `apera_trigger_trajectory`, and I
stamped only the four call sites in `tkCycle`. There are seven. The three I
missed — `Part_Accept` L96, `Part_Reject` L75, `tkBeltScan` L505 — are the ones
that actually fire; the at-place trigger alone ran on 294 of 294 picks in the
morning run. So the clock was set about once per run and the field became "time
since the run started". My own check asserted the right invariant but only
searched `tkCycle`. It now searches every program, requires at least seven
stamped sites, and requires the stamp to precede `bTrajTriggered=true`.

**Also worth noting:** run 10 completed 37 cycles, triggered the at-place capture
37 times, and ran `Part_Accept` every time — while picking up nothing at all.
Nothing in the cell noticed. That is the strongest argument yet for eventually
letting `grip_part_at_pick` gate the cycle rather than only report it. I have
deliberately not done that (a measurement that becomes a gate is a behaviour
change hiding behind instrumentation, and `verify.py` fails if any grip field
appears in a condition) — but it should be a conscious decision, not an
oversight.

---

## What to do, in order

1. **Deploy the three `.pgx` files** in `AperaLatencyFix_DtxRestore_2026-09-09.zip`.
   They fix the latency field and nothing else.
2. **Restore the nine settings** from the table in §1 — by hand, in SP2 and on
   the Options page. Check `mReach` and `tSchunkEMH084` first; those are the two
   that change how the robot moves.
3. **Confirm the belt sensor is alive again** — `sensor stops` should start
   counting on the Options page.
4. **Run a few hundred picks at 0.25 / 0 / 0.25 with steel plates** and read
   `grip_ok`. If it holds 1/1/0, that is 0.47 s a pick and it also settles what
   `grip_mag_at_pick` means.
5. **Then** read `APERA s:` against the vision wait. If they are close, the
   trigger is too late and there is another ~0.9 s a pick to be had by moving it
   earlier rather than by dwelling longer.

## Still outstanding

- **The workbook is not updated for this data.** It holds 537 picks; this parse
  holds 1,504, and run 8 grew from 295 to 355 rows, so existing rows change too.
  That is a full Cycle Data rebuild plus re-anchoring every Summary and Phase
  Budget formula — not a column append. It is its own piece of work and I would
  rather do it properly than bolt it onto this patch.
- `grip_mag_at_pick` needs a steel run to be interpretable.
- The sensor-disagreement warning as its own severity-2 log line with the dwell.
- Extending the sensor read to `tkCycle`'s detector branches and `tkCheckZone`.
- Segment rows on `UserPageCycleStats`.
