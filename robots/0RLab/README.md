# 0RLab — lab bench robot (Stäubli CS9 `F_24_0060113_C_001`)

The Raiv lab test cell ("Raiv-Lab", SRS cell `B&B LAB`, controller name `Lab Test`): a Stäubli
TX2-140 arm on a CS9 controller, picking tie plates off a feeder belt with Apera Vue 3D vision
and placing them on accept/reject stations. It is not a truck unit. This folder holds everything
found for it in the OneDrive project `Claude_project- Optimize Robot Cycle`, pulled on 2026-10-22.

Every file seen is listed in [`manifest.csv`](manifest.csv), with its OneDrive URI, size, whether it
was pulled, and why not when it was not. [`summary.json`](summary.json) holds the key facts in
machine-readable form.

## Where the source folders are

All on drive `b!YRe-w6bwZkWI3wwpdfrTWTMaV4ekysxNk4P8wjLriM6iYlZILgXoQ5REXLewPjqU`.

| OneDrive folder | Item id | Local copy |
|---|---|---|
| `Claude_project- Optimize Robot Cycle/0RLab/0RLab_Apera` | 01DTCSEEFS3BKMYJMZ3VBJ2AWGAM3KNN5Z | `0RLab_Apera/` |
| `…/0RLab/0RLab_Code_Updates` (22 dated bundles) | 01DTCSEEBOEUB7WOZUW5CLAUOI3HFOXHGV | `0RLab_Code_Updates/` |
| `…/0RLab/0RLab_Notes` | 01DTCSEEBL23PNLDL3FRGIW4JYERLCRXUQ | `0RLab_Notes/` |
| `…/0RLab/0RLab_PLC_HMI` | 01DTCSEEGZHW5WCN6NMBAJDGCJLMCZ3BNA | empty in OneDrive (0 bytes, no files) |
| `…/0RLab/0RLab_SRS` (3 SRS cell zips, 116 MB) | 01DTCSEEC22TLBMMLJTFF3FV3ZAIJFPS7Y | listed only |
| `…/0RLab/0RLab_Staubli_Backups` (90 MB) | 01DTCSEEAMOR4TAGLIGVBKA532OSB7OAMI | `0RLab_Staubli_Backups/` (selected text files) |
| `Claude_project- Optimize Robot Cycle/Metrics_0RLab_F_24_0060113_C_001` | 01DTCSEEGPL7IOKDPYDFAZQQO4ZAJQO3ST | `Metrics_0RLab_F_24_0060113_C_001/` |

`Robot Trucks/0RLab` and `Documents/Staubli/backups/0RLab` do not exist (both returned NOT_FOUND).

## What was pulled and what was only listed

- **Pulled verbatim:** both notes, all 22 code-update READMEs, every metrics CSV, the raw
  `RAIV/CSV` log lines, the metrics workbook (as text plus one CSV per sheet), the HMI page files
  (`interface/*.html` and `*.bindings.json`) for the early-belt-kick toggle bundle and the latest
  GripCheck build, `grip_test_log.csv`, and small controller files from the backups
  (`val3version.xml`, `libScpConfig/normal.json`, `ecat/dsiParams.json`, `arm.json`, and the
  `backup_OK_*.log` receipts).
- **Pulled in part:** the two Apera pipeline JSON files (549 KB and 423 KB) and the 2026-03-20
  `user.log` (2.8 MB). The manifest gives the line ranges.
- **Listed only:**
  - **All Stäubli VAL3 source** (`.pgx`, `.dtx`, `.pjx`, `.ltx`), the `.cfx` controller configs and
    the `.py` scripts. The Microsoft 365 connector serves these as `application/octet-stream` and
    will not return their text.
  - **`0RLab_CycleTime_Review_2026-09-01.pptx`.** Graph refused to convert it (`notSupported`).
  - **Zip files and large controller logs.**
  - **Some backup subtrees, recorded as one summary row per folder.** These are the older backups'
    `usr/` and `log/` trees, vendor templates, and duplicate Apera library copies inside the
    backup apps.

## The robot

| Item | Value | Source |
|---|---|---|
| Controller | Stäubli CS9, serial `F_24_0060113_C_001` | every backup folder name; `backup_OK_F_24_0060113_C_001.log` |
| Arm serial | `F_24_0060113_A_001` (counter value 1118248) | `0RLab_Staubli_Backups/F_24_0060113_C_001/Y-2026_M-03_D-20_12h50m/log/arm.json` |
| Arm model | TX2-140 (`tx2_140-S2`) | safety file `usr/configs/safety/tx2_140-S2_202-101.pmt2` (listed); `usr/configs/libScpConfig/normal.json`; Apera `robot_asset: robot_model__staubli_tx2_140_v1.0.0` |
| Safety program | version `202.101`, programCRC 856155967 | `…/Y-2026_M-08_D-31_15h07m/usr/configs/libScpConfig/normal.json` |
| VAL3 | `s8.15.1Cs9_BS3177` (compatibility 11.0) | `…/Y-2026_M-08_D-31_15h07m/usr/configs/val3version.xml` |
| SRS user pages | `src-version 8.15.1` | `interface/*.html` |
| Running application | `LAB_PlateSorter2` (also on the controller: `LAB_PlateSorterNEW`, `LAB_TwoBinCycle`) | 15h07 backup `usr/usrapp/` listing |
| Apera Vue host | `sAperaSocket` 192.168.10.10:14040, `sAperaRestart` 192.168.10.10:14050 (from `sio.cfx`) | `0RLab_Code_Updates/MetricsRetain_2026-08-28/README_MetricsRetain.md` |
| Apera config version | `"version": "4.183.0"` | `0RLab_Apera/08282026_Lab_binpick_pipelines.json.partial.txt` |
| Apera cameras | stereo_pair_1 = cameras 4108851213 / 4108851214 (6 mm lens); stereo_pair_2 = 4108818891 / 4108818892 (8 mm lens) | same file |
| Apera pipelines | `bin1_TCPA200` (pick trajectory), `bin1_TCPA200_detect` (belt detect), `bin1_AGMW80_AR70` | same file |
| Apera Vue serial | not found in any readable file | — |
| PLC / HMI | ClickPLC / C-more receive 50 Modbus registers (`aoMetric` 34 + `aoPhaseMs` 16) | `0RLab_Notes/MetricsAudit_2026-08-28.md`. No PLC/HMI program files exist (the `0RLab_PLC_HMI` folder is empty). |

## Backups

These are the Stäubli controller backups in `0RLab_Staubli_Backups`. The completion times come
from the `backup_OK` receipts.

| Backup folder | Completed |
|---|---|
| `F_24_0060113_C_001/Y-2025_M-11_D-05_08h38m` | 11/5/2025 8:38 AM |
| `F_24_0060113_C_001/Y-2025_M-11_D-20_10h14m` | 11/20/2025 10:14 AM |
| `F_24_0060113_C_001/Y-2026_M-03_D-20_12h50m` | 3/20/2026 12:50 PM |
| `Lab_Backup_08282026_…/Y-2026_M-08_D-28_15h09m` (+ zip) | 8/28/2026 3:09 PM |
| `Lab_Backup_08312026_…/Y-2026_M-08_D-31_10h29m` (+ zip) | 8/31/2026 10:34 AM |
| `F_24_0060113_C_001/Y-2026_M-08_D-31_12h23m` | 8/31/2026 12:28 PM |
| `F_24_0060113_C_001/Y-2026_M-08_D-31_15h07m` (**latest**) | 8/31/2026 3:13 PM |

`0RLab_SRS` holds the SRS cell zips `B&B LAB 08282026.zip`, `B&B LAB 09302026.zip` and `B&B LAB (2).zip`.

## Code updates (dated bundles in `0RLab_Code_Updates`)

**2026-08-28**
- `LastPartBelt_Update`
- `BeltClear3in_Update`
- `InitReset_Fix`
- `LastPartHang_Fix`
- `BeltKickLatch_Fix`
- `BeltKickSeq_Fix`
- `HMI_EarlyBeltKick_Toggle`
- `DetectPipeline_SpeedUp` (Apera Vue pipeline rewrite)
- `MetricsLog_CSV`
- `MetricsRetain`
- `MetricsRetain_Fix`

**2026-08-31**
- `AbortMessageLatch_Fix`
- `SettleDelay_Tidy`
- `AbortHold_Fix`
- `StowRegression_Fix`
- `StowSelect_Pick0_Fix`
- `ToolDwell_PhaseGroups`

**2026-09-30**
- `Lab_platesorter4` (rev B)
- `Lab_platesorter4_2026-09-30_revC` (+ bisect A)
- `AperaDriver3_Patch` (+ bisect ladder B1–B3)
- `Lab_platesorter4_FROM_PRODUCTION`

**2026-10-05** (latest)
- `Lab_platesorter4_GripCheck`. Grip-failure observer, "built from the 30 Sep code without a
  controller to test on" (`README_GripCheck.md`).

## Cycle-time metrics

The controller logs `RAIV/CSV` samples every 300 s, plus one before each RESET and one at stop.
Each row is cumulative since the last RESET; it is not one cycle. In total there are
**15 unique samples, 2026-08-28T15:01:56 to 2026-08-31T15:04:41**, across runs blank, 1, 2, 3, 4
and 5. Sources are `Metrics_0RLab_F_24_0060113_C_001/F_24_0060113_C_001_ALL_v2.csv` and
`raw/F_24_0060113_C_001_2026-08-31_15h07_raw.txt`.

- **Target:** 2.965 s/plate, 1214 pl/hr. The Header Key sheet says this budget was set by Genesis Rail.
- **Best sustained run:** run 3, 11.4 min, 134 plates.
  - 5.106 s/plate, 705 pl/hr, which is 58.1% of target.
  - Gap to target: 2.141 s/plate.
  - LRC p10 3.75 s, fastest clean cycle 3.51 s, clean mean 4.59 s, clean 85%.
  - Sources: `F_24_0060113_C_001_ALL_v2.csv` and `0RLab_CycleMetrics_F_24_0060113_C_001.xlsx.txt`.
- **Run 3 loss budget (s/plate):**
  - productive 4.453 (87% of the cycle)
  - belt 0.554
  - vision 0.094
  - fault 0.005
- **Run 3 phase means:**
  - ph15 move to capture: 1.469 s
  - ph2 pick linear approach: 1.277 s
  - Together they are 54% of the cycle (`0RLab_Notes/MetricsFindings_2026-08-31.md`).
- **Worst sample:** run 4 at 3.2 min, 11.209 s/plate (321 pl/hr) with ph2 at 5.705 s.
  Run 4 at 6.2 min logged state `FEED STARVED`, b_starve 0.156 s/plate and belt_max 36.2 s.
- **Settle-delay change (2.5 s to 1.0 s).** Cost per belt episode fell from about 5.5 s to about
  2.5–3.9 s (`MetricsFindings_2026-08-31.md`). Trajectory capture is 1.389 s per look
  (`SettleDelay_Tidy_2026-08-31/README_SettleDelay_Tidy.md`).
- **Camera time.** Mean 1.29–1.65 s per look, but vision wait is only 0.002–0.116 s/plate
  (`MetricsFindings_2026-08-31.md`).
- **Parts.** Every sample is 100% accepted and every plate is a 14-inch tie plate.
- **Per-cycle statistics are not available.** The data are cumulative samples, so mean, median
  and p90 cycle times cannot be computed and are `null` in `summary.json`.

## Open issues, as stated in the notes

1. **The `Lab_platesorter4` build (apera3 driver) has failed to load.**
   - Rev A, rev B, rev C and bisect A were all refused.
   - The FROM_PRODUCTION README found the controller's `Lab_platesorter4` folder held four builds
     unzipped on top of each other. It must be deleted before extracting the new build.
   - `LAB_PlateSorter2` is still the fallback.
   - Sources: `README_Lab_platesorter4_revC.md`, `README_AperaDriver3.md`, the `FROM_PRODUCTION`
     README. No later record of a successful load was found.
2. **A fault flag is still set during runs.** Run 1 read 100% FAULT. The source has not been found
   among `bERROR["schunk"]`, `bMessage["abort"]` and `bRunning["Abort"]` (`MetricsFindings_2026-08-31.md`).
3. **The early belt kick falls back to FOV-clear timing about 1 cycle in 6.**
   `nBeltKickTimeout_s` (3 s) and `nBeltClearHeight_mm` (76.2) are untuned
   (`MetricsFindings_2026-08-31.md`, `README_Lab_platesorter4.md` §10). Early kick caused an
   over-torque on 8/28 and ships disabled (`README_BeltKickSeq_Fix.md`).
4. **`bLogRetain` is still `false`.** The retained RaivLog ring has never been exercised (`README_Lab_platesorter4.md` §10).
5. **`F_24_0060113_C_001_ALL.csv` is a stale copy.** `_v2` is the correct one (`README_Lab_platesorter4.md` §10).
6. **No qualified baseline of 200 or more plates on a fed feeder yet** (`README_Lab_platesorter4.md` §10).
7. **The comma in the tkMetrics ABORT state string splits the D1 CSV row.** It is fixed only in the
   Lab_platesorter4 builds, not in the driver-only patch (`README_AperaDriver3.md`).
8. **ph15 and ph2 (54% of the cycle) are the next motion work.** `pick_still` is 21.5%
   (`MetricsFindings_2026-08-31.md`).
9. **The multi-candidate Apera path is registered but unused.** It uses `apera_trigtrj_a` and
   `apera_waittrj_i` (`README_Lab_platesorter4_revC.md` §8).
10. **The `StowSelect_Pick0_Fix` `setMoveId(50)` was not in the 15h07 backup.** So ph0 is blank on
    all 15 samples (Header Key sheet). The production pull of 9/30 shows both 8/31 bundles are live
    (`FROM_PRODUCTION` README).
11. **GripCheck needs an SRS build and sensor checks before its first run.** It needs the
    `bAccept_Overflow` polarity and timing checked, and `grip_test_log.csv` has a header only, with
    no test runs logged (`README_GripCheck.md`).
