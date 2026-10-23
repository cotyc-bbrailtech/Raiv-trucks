# 1RT53 tie-plate bin pick: full session record (19–20 Oct 2026)

Work done by Corey England with Claude (Cowork). **Truck names: 1RT53 = Raiv-1 = T53 = TR53** (confirmed by Corey, 20 Oct). Shared working folder: Coty's OneDrive `Robot Trucks/1RT53/` (backups, code, notes, videos). Controller **F_24_0064095_C_004**: Stäubli TX2-140 on CS9 (VAL3 s8.20), APERA vision, magnetic gripper (EMH), hydraulic conveyor with an end-of-belt laser sensor.
**Goal:** 17 plates/min without interruptions = **3.53 s per plate**.

## 1. What is in this project

| Path | What it is |
|---|---|
| `claude/1RT53_binpick_full_session_record_2026-10-19_20.md` | This record |
| `claude/1RT53_binpick_tieplates_session_2026-10-20.md` | One-page summary |
| `claude/code/binpick_TiePlates_v2_0_0_source.txt` | Baseline app as found on the controller (not written by Claude) |
| `claude/code/binpick_TiePlates_v2_1_0_source.txt` … `v2_4_0_source.txt` | Full source of each version built in this session |
| `claude/data/per_pick_log_v2x_runs_14-20Oct.csv` | Every logged pick 14–20 Oct (810 rows), parsed from the controller logs |
| Doc: **tkCycle Motion & Wait Map** | https://claude.ai/code/artifact/91b24480-4560-4401-9562-6e641550fe7b (share it separately in claude.ai) |

**Source bundles.** Each bundle contains every file of that app: `.pjx`, `.dtx`, all `.pgx` including `HMI/`, the `interface/` pages, and the READMEs. Each file starts with a line `===== FILE: <relative path> =====`. To rebuild an app, split the bundle back into those files. Libraries `apera/` and `monitorArea8En/` are identical in every version, so they are not included. Copy them from any backup.

**Full backups** (binary safety files, zipped logs, about 60–70 MB each) are too large for a project. They are on Corey's laptop under `C:\Users\CoreyEngland\Documents\Staubli\backups\Raiv-1\F_24_0064095_C_004\`.

| Backup folder | Taken | Apps on controller | Notes |
|---|---|---|---|
| `Y-2026_M-10_D-06_08h43m` | 6 Oct | binpick_TiePlates, _BeltSensor | Before this session |
| `Y-2026_M-10_D-07_12h18m` | 7 Oct | same | Before this session |
| `Y-2026_M-10_D-09_07h57m` | 9 Oct | + "_BeltSensor - Claude" | Before this session |
| `Y-2026_M-10_D-19_15h34m` | 19 Oct 3:34 PM | + v2_0_0 (running) | Starting point. v2_1_0 was built into this folder |
| `Y-2026_M-10_D-20_09h43m` | 20 Oct 9:43 AM | + v2_1_0 (loaded, Corey's Part_Reject edit) | v2_2_0 was built into this folder |
| `Y-2026_M-10_D-20_11h10m` | 20 Oct 11:10 AM | + v2_2_0 (3-pick test) | v2_3_0 was built into this folder |
| `Y-2026_M-10_D-20_11h50m` | 20 Oct 11:50 AM | + v2_3_0 (short test) | |
| `Y-2026_M-10_D-20_13h37m` | 20 Oct 1:37 PM | v2_3_0 after the 38-min run (321 picks) | v2_4_0 was built into this folder |

Each new app was built as a separate folder next to the previous one, so backing out means loading the previous app.

## 2. How the logs were read

- **Per-pick data.** `LogCycleCSV` writes `RAIV/CSV,<line>,<seq>,…` into `mnt/log/user.log` (inside each backup's `logArchive.zip`) once per pick. Lines A–L hold the timing segments, belt sensor, batch, gripper, Branch B and belt-master fields. The field order is documented in the `LogCycleCSV.pgx` header. The CSV in this project is the parsed result.
- **Clock.** user.log times are controller-local; system.log was cross-checked against the backup times.
- **Live data.** The pendant emulator (`https://172.31.0.120/emulator.html`) exposes the last 100 events at `/api/events`. That was used once to read the live run.

## 3. Baseline: v2.0.0 (19 Oct run, 1:33–2:14 PM, 330 picks)

- **Speed:** median 4.39 s (13.7/min). Only 1 pick was at or under 3.53 s. Real output was **8.0/min**.
- **Stops:** 4 stops between picks totalled ~9 min. One "nothing pickable" loop retried the camera **190 times over 86 s** with the beam blocked. The first 5 picks ran at 25% speed because the pendant was connected.
- **Feed:** vision saw only 1 plate on 40% of picks.
- **Two-speed cycle:**
  - Fast picks, 4.12 s: approach 0.64, linear approach 0.51, grip 0.25, retreat 1.35, place 0.56, vision wait 0.78.
  - Slow picks, 5.97 s: about +1.4 s in place/return and +0.4 s vision.
- **History:**
  - **Best sustained run:** 11 Sep (original app) at 3.88 s median and 15.4/min with no gaps.
  - **Best steady state:** 8 Oct at 3.60 s (~16.7/min), with a full belt (about 10 plates visible).
  - Since the belt-sensor rewrite (22 Sep), normal picks run about 0.6 s slower.

## 4. Findings, in the order they were found

| # | Finding | Evidence | Fixed in |
|---|---|---|---|
| 1 | **Belt never moved when a plate sat on the sensor but wasn't pickable.** The detect loop retried forever (`nDetectorTries`=0), the miss counter was only incremented after the loop, and after 3 nudges the beam-blocked alarm latched. | 19 Oct: 190 pictures in 86 s; 57 in 28 s | v2.1.0 |
| 2 | **Arm-power popup flood.** `tkIOMonitor` (`delay(0)`) called `enablePower()` every pass while the NC servo switch read 1. A request made while a safety restart is pending stays pending, and the controller logs WARN+ERROR every 4 ms. This also wiped the system log history. | ~12,700 pairs in 5 min (19 Oct); floods in every backup since 5 Oct. The v2.1 throttle didn't stop it; `esStatus()` reads 0 in that state. | v2.1.0 (partial), **v2.2.0** |
| 3 | **Capture-ready race.** The belt stop time was stamped one 10 ms poll late, so capture-ready flashed on at the instant the belt was told to stop: zero settle. | Code; over-torque fault on axis 5 on 20 Oct, 9:15 | v2.2.0 |
| 4 | **Hydraulic belt coasts a load-dependent distance.** A fixed settle can't be both safe and fast. | Corey's observation | v2.2.0 (settle 1.0 s + stale guard). Real fix is hydraulic or a motion sensor, see open items |
| 5 | **Wasted motion between drop and next pick.** Full stop at the trigger position, a one-shot capture check, a blocking `AperaPartsFound` (0.5 s), a blend-off hover (`mReach`), and a backtrack to the trigger position. | v2.2 video: 1–1.5 s hover every pick; "capture at place" never increased | v2.3.0 |
| 6 | **APERA trigger call blocks ~0.4 s** waiting for APERA's reply, holding the arm above the drop when fired late. | v2.3 retreat 1.65 s vs 1.25–1.35 s | v2.4.0 |
| 7 | **"Nothing pickable" passes are slow.** Median 5.3 s = stop 0.94 + jog/settle 2.48 + fixed 0.5 + trajectory 1.39. One pass fired the camera 110 times at a moving belt. | v2.3 log, 18 passes | v2.4.0 |
| 8 | **Belt sensor sticks** (no new edges for up to 31 picks); the belt can only jog. | v2.3 run 13:08–13:11 | Open (mechanical) |
| 9 | **Feeder starved:** often 1 plate visible. | Both runs | Open |
| 10 | **Gripper part-present / magnet-status inputs always 0**; "plate still on magnet" sometimes 1. No pick is verified. | All logs | Open |
| 11 | **User page path reported in lowercase** (`/binpick_tieplates_v2_x/interface/userpage….html`). HMI "page not found" + ERR 70 on 19 Oct. | user.log, `/api/applications/running/user_page` | Open |
| 12 | **Pendant connected = speed capped** (25–75%). | Logged warnings | Procedure: unplug the pendant or raise speed at it |
| 13 | **`PartPicked` switches to slow descriptors** (vel 25–50%) when the pick transform is over 100 mm. | Code | Open, review |
| 14 | **Stops and safety:** ~10 min of the 38-min v2.3 run; 6 "arm power refused". | v2.3 log | Open |

## 5. Versions built

All versions were built by Claude, not compiled in SRS by Claude. Each was loaded and compiled by Corey before testing.

### v2.1.0 (19 Oct): jog the belt when the sensor is blocked but nothing is pickable
- **tkCycle:** both detect loops exit after one empty picture on a blocked beam (APERA socket errors are not counted as misses). A miss clears `bBeltReadyForCapture` until the jog has run.
- **tkBeltSensor:**
  - jogs `nBeamNudge_s`=1.0 s after `nBeamNudgeAfter`=1 miss, every miss, no alarm latch (`nBeamNudgeMax`=0 means unlimited);
  - every `nBeamNudgeWarn`=5 jogs in a row: a level-2 message and `bBeamJogWarn`;
  - no capture while a jog is pending.
- **tkIOMonitor:** power-on request throttle (`nPowerRetry_s`=2), which proved insufficient (see v2.2).
- **Tested:** 20 Oct. Jogs fired correctly, no latch.

### v2.2.0 (20 Oct AM)
- **tkBeltSensor:** `l_nStopClk` is stamped in the pass that switches the belt off (race fixed). `nBeltSettle_s` 0.35 → **1.0 s**.
- **Stale-trajectory guard (tkCycle).** Every trajectory trigger records `nBeltMasterStarts` and `bTrajBeltOk`. Before each pick, if the belt wasn't settled or has started since, the trajectory is discarded and a new picture taken (not a miss, no jog). Counter: `nTrajStaleDiscards` (CSV line L).
- **tkIOMonitor:**
  - `enablePower()` only on the servo-switch OFF→ON edge or a Start-pushbutton press, and only if not powered;
  - not powered within 2 s: the request is withdrawn with `disablePower()` and one message logged;
  - **after an e-stop or safety reset the operator must cycle the servo switch or press Start.**
- **Options (vision) page cleaned up:**
  - removed earlier test controls: Capture @ FoV, Stall Sampler, Early Belt Kick, Belt Batch, grip/mag/drop and APERA readouts, Sensor Stops Belt;
  - `init` forces the experiment toggles off;
  - added: jog warning lamp, jog count, settle value, stale-trajectory count.
- **Tested:** 3 picks at ~5.2 s, no popup flood, one clean "power refused" message. The e-stop restart path was not exercised.

### v2.3.0 (20 Oct midday)
- **Capture while moving.** New `TryCaptureNow` (non-blocking) and `WaitMoveCapture` (polls every 10 ms during motion). Used in Part_Accept/Part_Reject and on the return. Counter `nCapInMotion`.
- **No stop at `jApera_Trigger_pos`** when the picture is already taken (blended via point). Stops there only if the belt isn't ready on arrival. The backtrack is gone except as a fallback.
- **Hover move:** `jTrajectoryStart` reached with `mHover` (50 mm blend) instead of `mReach` (blend off).
- **Plate count:** `AperaPartsFound` only when APERA returns no trajectory.
- **Approach blend:** `bBlendApproach` (true) blends APPROACH into LINEAR_APPROACH within `nApproachBlend_mm`=25. The stop and settle before the grip are unchanged.
- **Tested:** 38 min, 321 picks:
  - clean picks 3.93 s (~15.3/min), vision wait 0.10 s;
  - 290 of ~320 pictures taken while moving, 0 stale discards;
  - real output 8.4/min: stops ~590 s, 18 Branch B passes (310 s), stuck sensor, starved feed.

### v2.4.0 (20 Oct PM, built, NOT tested)
- **Part_Accept:**
  - new `WaitMoveCaptureFar` fires the picture only while the TCP is more than `nCapMinDist_mm`=300 mm from the drop-approach point;
  - if there's still no picture, it's fired right after the descent to the drop is queued;
  - the drop interlock is unchanged (checked at rest).
- **CaptureReady:** new program holding the capture conditions; `TryCaptureNow` uses it.
- **Not done on purpose:** starting the hover move before firing the picture. The arm would enter the camera view while APERA may still be capturing.
- **tkCycle "nothing pickable" passes:**
  - detect loops take one picture per belt-ready (no spinning on a moving belt);
  - fixed `delay(0.5)` → `nBranchBSettle_s`=0;
  - `AperaPartsFound` after those trajectory requests only when there's no trajectory.
- **Expected:** retreat ~1.3 s, clean pick ~3.5 s (≈17/min), passes ~5.3 → ~4.3 s.

**Intentional edit by Corey (kept in v2.1 onward):** in tkCycle, plates whose APERA type ≠ the selected type now go to `Part_Reject()`.

## 6. Results by version

| Version | Picks logged | Typical / clean pick | Real output | Notes |
|---|---|---|---|---|
| v2.0.0 (19 Oct) | 330 | 4.39 s median | 8.0/min | Stops, starved feed, endless retry loops |
| v2.1.0 (20 Oct) | 5 | — | — | Axis 5 over-torque at 9:15:51 (suspected picture on a moving belt) |
| v2.2.0 (20 Oct) | 3 | 5.2 s | — | Arm hovered 1–1.5 s waiting on belt + APERA |
| v2.3.0 (20 Oct) | 321 | 3.93 s clean, 4.63 s median | 8.4/min | See findings 6–9 |
| v2.4.0 | — | expected ~3.5 s | — | Not tested yet |

## 7. Open items, highest payoff first

1. **Test v2.4.0:** compile in SRS, run a few cycles at 25–50% watched, then 20–30 min at 100% with a stocked belt and the pendant unplugged. Pull a backup. Tune `nCapMinDist_mm` (retreat still over 1.4 s → raise to 400–500).
2. **Belt sensor sticking:** look for a plate resting or overhanging at the beam; check sensor aim and lens.
3. **Feeder rate:** 17/min needs more than 17 pickable plates per minute arriving.
4. **Measure the fully loaded belt stop time** (slow-motion video from the conveyor-output light going off) and set `nBeltSettle_s`. Longer term: lock the hydraulic motor at stop (closed-centre valve or brake valve), or add a belt-motion pulse sensor. Both EtherCAT input terminals are full (8/8 + 8/8), so the sensor needs another input.
5. **APERA:** ask whether the ~1.3 s trajectory response can come down. It is on the critical path.
6. **Safety stops:** find what trips the safety (~10 min lost, 6 "arm power refused").
7. **Gripper feedback inputs** (part-present, magnet status) always 0: wiring or mapping.
8. **User-page path case bug** (HMI ERR 70).
9. **Review the `PartPicked` slow-descriptor rule** (transform over 100 mm → 25–50% speed).
10. **Lift gate:** `nBeltClearHeight_mm` 76.2 mm (3 in). Lowering it starts the belt sooner if the clearance allows.

## 8. Tunables added or changed (data editor, live)

| Name | Value | Version | Purpose |
|---|---|---|---|
| nBeamNudgeAfter / nBeamNudge_s / nBeamNudgeMax / nBeamNudgeWarn | 1 / 1.0 s / 0 / 5 | 2.1 | Belt jog on a blocked beam |
| bBeamJogWarn | flag | 2.1 | Jog warning (Options page lamp) |
| nPowerRetry_s | 2 | 2.1 / 2.2 | Withdraw a refused power request after this |
| nBeltSettle_s | 1.0 (was 0.35) | 2.2 | Belt settle before a picture |
| nTrajStaleDiscards | counter | 2.2 | Trajectories discarded because the belt moved |
| bBlendApproach / nApproachBlend_mm | true / 25 | 2.3 | Approach blend |
| mHover / mApproachBlend | 50 / 25 mm blend | 2.3 | Motion descriptors |
| nCapInMotion | counter | 2.3 | Pictures taken while moving |
| nCapMinDist_mm | 300 | 2.4 | No picture this close to the drop |
| nBranchBSettle_s | 0 (was 0.5) | 2.4 | Fixed settle in nothing-pickable passes |
