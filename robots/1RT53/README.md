# 1RT53 — Raiv-T1 robot truck (fleet unit T-53)

Stäubli TX2-140 arm on a CS9 controller (`F_24_0064095_C_004`), Apera Vue stereo vision, magnetic gripper, hydraulic conveyor with an end-of-belt laser sensor, bin-picking steel tie plates. Names used for the same truck in the files: 1RT53, Raiv-T1, Raiv-1, T53, TR53 (`RobotTrucks_1RT53/notes/1RT53_binpick_full_session_record_2026-10-19_20.md`). The cycle-metrics series is `F_24_0064095_C_004`.

Everything here was copied out of Coty's OneDrive on 2026-10-22. `manifest.csv` lists every file found (one row per file, or one summary row per bulk folder), with its OneDrive URI and whether it was pulled.

## Where the data lives on OneDrive

All paths are on drive `b!YRe-w6bwZkWI3wwpdfrTWTMaV4ekysxNk4P8wjLriM6iYlZILgXoQ5REXLewPjqU`.

| OneDrive folder | Local folder here | What it holds |
|---|---|---|
| `Claude_project- Optimize Robot Cycle/1RT53/` (root files) | `./` | Cycle-programme deck, metrics workbook v2, SRS physical I/O database, 59-page VAL3 printout, one depth image |
| `…/1RT53/1RT53_Notes/` | `1RT53_Notes/` | 20 analysis notes, 2 Sep – 14 Oct 2026 |
| `…/1RT53/1RT53_Code_Updates/` | `1RT53_Code_Updates/` | 18 code-update bundles (zip + extracted folder + README), `VERSIONING.md`, `VERSION_LOG.md`, AR70 install package |
| `…/1RT53/1RT53_Staubli_Backups/` | `1RT53_Staubli_Backups/` | 42 CS9 backups under `F_24_0064095_C_004/` (2026-08-26 → 2026-10-21), SRS baseline backup of 2026-08-25, 3 backup zips |
| `…/1RT53/1RT53_PLC_HMI/` | `1RT53_PLC_HMI/` | PLC project `.ckp`, Modbus address map, HMI `.eapv`, CM5-10 tag names |
| `…/1RT53/1RT53_Apera/` | `1RT53_Apera/` | Apera config export, 23.6 GB `APERA VGR` export + zip (recordings, Vue backups), daily Apera journals, Apera/robot KPI tables |
| `…/1RT53/Claude outputs/` | `Claude outputs/` | `IDEAS_LOG.md` |
| `…/1RT53/Raiv-T1_exportLogs/` | — | empty |
| `Claude_project- Optimize Robot Cycle/Metrics_1RT53_F_24_0064095_C_004/` | `Metrics_1RT53_F_24_0064095_C_004/` | Parsed cycle/event/run/error CSVs, metrics workbook, 40 raw `user.log` files, 7 backup zips, 32 empty backup stubs, parser scripts |
| `Robot Trucks/1RT53/` (item `01DTCSEEBY4VARDHMWVBCKXDBNXYJRFIDV`) | `RobotTrucks_1RT53/` | 19–20 Oct session notes and per-pick log, full source bundles for v2.0.0–v2.4.0, app folders v2.1.0–v2.4.0, 8 backups (Oct 6–20); `videos/` is empty |
| `Documents/Staubli/backups/1RT53` | — | not found on this drive. The session record says those backups are on Corey's laptop (`C:\Users\CoreyEngland\Documents\Staubli\backups\Raiv-1\…`) |

## What was pulled and what was only listed

- **Pulled verbatim (79 files):** all notes, all code-update READMEs, `VERSIONING.md`/`VERSION_LOG.md`/`CHANGES.md`, the Metrics README, backup review, runs/errors/state CSVs, the Apera pipelines JSON, the Apera KPI tables, the PLC Modbus map, the latest backup's `val3version.xml`/`safetyStruct.json`/app READMEs, the five VAL3 source bundles (v2.0.0–v2.4.0, about 0.5 MB each, byte-exact), and the 19–20 Oct per-pick log. Office and PDF files were saved as connector text (`<name>.<ext>.txt`) and workbooks as one CSV per sheet (`<name>__<sheet>.csv`).
- **Partial (5):** `cycles_ALL.csv` (first and last pages of 3,287 rows), `events_ALL.csv` (first and last pages of 30,239 rows), `apera_picks_2026-09-10_to_10-20.csv` (first and last pages), and both metrics workbooks. The connector truncated their `Cycle Data` sheets: 1,924 of 3,069 rows in v2, 650 of 3,293 in the Metrics workbook.
- **Listed only:** zips, images, PLC/HMI binaries, the Apera VGR export (about 16 GB plus a 7.7 GB zip, summarised by folder), raw `user.log` files (0.5–4 MB each; their content is already parsed into `events_ALL`/`cycles_ALL`), parser/tool scripts, and the CS9 backup trees. The connector cannot read VAL3 `.pgx`/`.dtx`/`.pjx` or `.cfx` files (it returns `application/octet-stream`). The same code is available as text in `RobotTrucks_1RT53/code/source_bundles/`. All backups except the latest (2026-10-21) are one summary row each.

## Key facts (with sources)

**Hardware and software**
- Arm: Stäubli **TX2-140**. The safety configuration names the robot `tx2_140-S2` (`1RT53_Staubli_Backups/…/Y-2026_M-10_D-21_12h50m/usr/configs/safetyStruct.json`, safety struct version `202.102`, programCRC 206780900). Controller: CS9, ID **F_24_0064095_C_004**. The arm serial number is not in any readable file because `arm.cfx` cannot be read through the connector.
- VAL3: **s8.20.2Cs9_BS4270**, compatibility 13.0 (`…/usr/configs/val3version.xml`). The `.pjx` files say `s8.20.2cs9_BS4270` (source bundles).
- Apera Vue: config **version 4.147.0**. Stereo pair `stereo_pair_2` uses cameras **4108760121** and **4108577719**, 8 mm lenses, eye-to-hand. Robot server port 14040. Pipelines: `14in_plate det`, `Pick_IdsBelt`, `Pick_IdsBelt_deformable`, `Pick_IdsBelt_depth`, `Pick_IdsBelt_new`. Robot context `TX2_140`. Search region `BeltFill` is defined but not wired: `vision_region_6.search_region` is empty (`1RT53_Apera/08252026_Raiv-T1_binpick_pipelines.json`). No Apera hardware serial appears in the files.
- PLC: **"T-53 TPS Robotics V2.1 (Ver3.40)"**, file dated 05/25/2026, in the filenames `05252026_Raiv-T1_plc_T-53 TPS Robotics V2.1(Ver3.40).ckp` and `…_Modbus_Addresses.csv`. The tag export is `Raiv-T1_CM5-10_TagNames.XLS`. HMI: **"HMI-10 T-53 TPS Robotics v2.2"**, read from the panel, file dated 08/25/2026 (`08252026_Raiv-T1_HMI-10_T-53 TPS Robotics v2.2_(ReadFromPanel).eapv`). The PLC→robot tags include `Robot_Enable_Power` Y005, `ROBOT RUNNING`/`Conveyor On` X008 and `Drop Enabled` Y004 (`1RT53_PLC_HMI/Raiv-T1_CM5-10_TagNames.XLS.txt`).
- Gripper: Schunk EMH084 electromagnet (`tSchunkEMH084`). The AR70 package of 2026-10-14 (v2.0.0) switches to a Magswitch AR70 on valve2 with tool `tAR70`, z=241 (TCP still to be verified) (`1RT53_Code_Updates/AR70_Install_2026-10-13/CHANGES.md`). The 19–20 Oct session record still describes the gripper as "magnetic gripper (EMH)".

**VAL3 application versions** (`1RT53_Code_Updates/VERSION_LOG.md`, `VERSIONING.md`, session record)
- v1.0.0 = `binpick_TiePlates_BeltSensor` rev D, the baseline in backup 2026-10-12.
- v2.0.0 = AR70 install (2026-10-14).
- v2.1.0, v2.2.0 and v2.3.0 were built on 19–20 Oct. v2.3.0 ran on 20 Oct.
- **v2.4.0 was built on 20 Oct and has not been tested.** Its README says "NOT compiled here — compile in SRS first".
- The latest backup (2026-10-21 12h50m) holds apps `binpick_TiePlates`, `_BeltSensor`, `_BeltSensor - Claude` and v2_0_0 to v2_3_0. It does not contain v2_4_0.

**Cycle-time metrics** (each figure as stated in the source named)
- Goal: 17 plates/min = 3.53 s/plate (session record 19–20 Oct). The 2026-10-12 backup review uses 20 plates/min (3.0 s).
- 2026-10-20, v2.3.0, 321 picks over 38 min: clean picks **3.93 s**, median **4.63 s**, real output **8.4/min** (`RobotTrucks_1RT53/notes/1RT53_binpick_full_session_record_2026-10-19_20.md`).
- 2026-10-19, v2.0.0, 330 picks: median **4.39 s**, real output **8.0/min** (same source).
- 7–8 Oct, 210 belt-fed picks: median **4.50 s** (13.3 plates/min), with 0.07 s unaccounted. The 3.65 s block on 8 Oct is a dry-cycle motion floor, not a pick rate (`Metrics_…/1RT53_2026-10-12_backup_review.md`).
- 22 Sep, after the sensor-only belt fix, 96 picks: median **4.63 s** (`1RT53_Notes/Raiv-T1_2026-09-22_beltsensor_run2.md`; workbook v2 `Sessions`).
- The 3.87–3.88 s figures from 10–11 Sep were measured on rubber plates with the belt off. The deck says they were "never a production number" (`Raiv-T1 Cycle Programme.pptx.txt`).
- Computed here from `1RT53_Apera/apera_kpi/robot_cycles_from_backup_2026-10-21_12h50m.csv`: 1,014 robot cycles, 2026-10-07 to 2026-10-20, mean 6.11 s, median 4.52 s, p90 8.86 s. These include stalls.
- Error history across the whole log: 608 Apera "pipeline missing" errors, 602 "bad pipeline id", 263 VAL3 ERR 70 / "Userpage not found", 244 "Image capture error", 195 "no trajectory", 86 motion cancelled and 50 ERR 60 timeouts (`Metrics_…/F_24_0064095_C_004_errors_summary.csv`).
- Logged application runs: 358 sessions, 2025-03-21 to 2026-10-12 (`Metrics_…/F_24_0064095_C_004_runs_ALL.csv`).

**Backups and code updates**
- Newest backup: `Y-2026_M-10_D-21_12h50m`. Its log reads "10/21/2026 12:51 PM: Backup of SRC controller 'F_24_0064095_C_004' has ended successfully." The oldest backup is the SRS baseline `05252026_Raiv-T1_SRS Backup-Y-2026_M-08_D-25_17h52m`.
- The controller log rolled before 2026-10-07, so older backups are now the only copy of earlier history (`1RT53_2026-10-12_backup_review.md`).
- Newest code update in `1RT53_Code_Updates`: `AR70_Install_2026-10-13`, built 2026-10-14 (v2.0.0). Newest code overall: v2.4.0, built 2026-10-20 (`RobotTrucks_1RT53/code/binpick_TiePlates_v2_4_0/README_v2_4_0.md`).

**Open issues** (from the notes, newest first)
1. The IDS belt camera 4108577719 fails with "incomplete buffer" grab timeouts and every pick returns `Image capture error`. The cell retries about every 9 s with no fault and no retry cap. Suspected cause is the GigE link, MTU or cable, possibly connected to the AR70 install (`1RT53_Notes/Raiv-T1_2026-10-14_ids_camera_capture_failure.md`).
2. v2.4.0 needs to be compiled and tested. `nCapMinDist_mm` needs tuning (session record).
3. The belt sensor sticks (no new edges for up to 31 picks), and the feeder is starved with often only 1 plate visible (session record).
4. Loaded belt stop time needs measuring to set `nBeltSettle_s` (currently 1.0 s). A hydraulic lock or belt-motion sensor is suggested. Both EtherCAT input terminals are full.
5. Ask Apera whether the ~1.3 s trajectory response can be reduced. The Stäubli-driver pickable-count call has been requested from Apera with no date (`Raiv-T1_2026-09-16_apera_call_note.md`). The `BeltFill` search region is still not wired.
6. Safety stops: about 10 min lost and 6 "arm power refused" messages on 20 Oct.
7. Gripper part-present and magnet-status inputs (%I6/%I4) always read 0, so no pick is verified.
8. The user-page path is reported in lowercase, which gives HMI "page not found" and ERR 70.
9. Review the `PartPicked` slow-descriptor rule (transform over 100 mm → 25–50% speed).
10. `nBeltRunMax_s` runaway cap was 0 (disabled) on 12 Oct. `sPipeline` `Pick_IdsBelt_new` was once rejected by Apera on 8 Oct (`1RT53_2026-10-12_backup_review.md`).
11. The AR70 TCP (z=241, copied from 2RT57) must be measured. An AR70 Apera pipeline is still needed (`AR70_Install_2026-10-13/CHANGES.md`).
12. Accept-station-full is not detected: `SegDropClear` read 0.00 s on all 2,296 picks, so %I0 needs a field check. Idle time is not attributed to causes (`Claude outputs/IDEAS_LOG.md`).
