# 2RT57 — Raiv-T2 / RAIV-2, robot truck T-57

Stäubli TX2-140 arm on a CS9 controller (controller ID `F_24_0064095_C_003`), Apera Vue vision, magnetic gripper, sorting tie plates off a belt (VAL3 apps `PlateSorter*`).
Everything here was pulled from the user's OneDrive on 2026-10-22. `manifest.csv` lists every file found (475 rows: 433 files plus 42 folder-level rows) and says which were pulled.

## Where the OneDrive data lives

All paths are on drive `b!YRe-w6bwZkWI3wwpdfrTWTMaV4ekysxNk4P8wjLriM6iYlZILgXoQ5REXLewPjqU`.

| OneDrive folder | What it holds | Local folder |
|---|---|---|
| `Claude_project- Optimize Robot Cycle/2RT57/2RT57_Apera` | empty | — |
| `…/2RT57/2RT57_PLC_HMI` | empty (there are no PLC or HMI exports on file) | — |
| `…/2RT57/2RT57_Code_Updates/PlateSorter3` | PlateSorter3 VAL3 project, DEPLOY_README, HMI user page | `2RT57_Code_Updates/` |
| `…/2RT57/2RT57_Staubli_Backups/F_24_0064095_C_003` | SRS backups `Y-2026_M-09_D-28_10h37m` and `…_13h11m` (full `usr/` trees plus logArchive.zip), plus `s8.20.2cs9_BS4270/Y-2026_M-10_D-13_03h35m` (logArchive.zip only) | `2RT57_Staubli_Backups/` |
| `…/2RT57/Data from Corey` (2.1 GB) | Apera Vue screen recordings (.webm/.REC/.mkv), Stäubli log exports 14–15 Oct, OCR CSVs, the 16 Oct analysis, GoPro SD metadata | `Data from Corey/` |
| `Claude_project- Optimize Robot Cycle/Metrics_2RT57_F_24_0064095_C_003` | cycle-metrics README, CSVs, workbook, raw VAL3 user.logs, backup zips | `Metrics_2RT57_F_24_0064095_C_003/` |
| `Robot Trucks/2RT57/{backups,code,notes,videos}` | all four subfolders are empty | — |
| `Documents/Staubli/backups/2RT57` | path not found (NOT_FOUND) | — |

## What was pulled and what was only listed

- **Pulled verbatim (27 files):**
  - Notes: both READMEs, DEPLOY_README.md.
  - Metrics: every metrics CSV except the events log, and the workbook as `….xlsx.txt` (all 6 sheets).
  - Analysis: `2RT57_pick_cycles_2026-10-12_to_15.csv`, complete with 2845 picks.
  - Backup config: `val3version.xml`, `safetyStruct.json`, `libScpConfig/normal.json`, `doc/safetyStop.csv`, and the backup_OK logs.
  - HMI: `interface/BASIC.html` and `BASIC.bindings.json`.
  - Controller logs: from the 15-Oct log export, `vsftpd.log` (complete), `user.log`, `dpkg.log`, `eeprom.json`/`eeprom.txt` and `diskusage.txt`.
  - GoPro SD: `MISC/sd_info.txt` and `version.txt`.
  - Corey's two microphone CSVs.
  - Some local copies differ in size from the source only because CRLF line endings became LF.
- **Pulled in part (5 files, first and last connector page saved as `__pageNNofMM`):**
  - `F_24_0064095_C_003_events_ALL.csv`: 16,184 lines.
  - The 13h11m VAL3 `user.log`: 16,332 lines.
  - `2RT57_apera_events_2026-10-12_to_15.csv`: 38,649 lines.
  - `auth.log`: page 1 of 4.
  - `daemon.log`: pages 1 and 3 of 3.
- **Listed only:**
  - **All VAL3 source:** `.pgx`, `.dtx`, `.pjx`, `.ltx`, Stäubli `.cfx`/`.old`, `.pmt2`, and also `verify.py`, `parse_backups.py` and `build_workbook_t2.py`. The M365 connector serves these as `application/octet-stream` and will not return their text. **No robot program code could be pulled.** It has to be copied from OneDrive another way.
  - Archives: zips, `.gz`, `.tgz`.
  - Media: `.webm`, `.mkv`, `.REC`, `.jpg`, `.png`.
  - Extensionless or rotated logs, which also come back as octet-stream.
  - `.outlining.json` editor metadata.
  - The 87 OCR CSVs in `_claude_work/ocr_device`. These are the intermediate data behind the analysis; the derived pick_cycles CSV was pulled instead.
  - The 10h37m and 10h45m raw user.logs. Per the Metrics README they repeat the 13h11m log.
  - The 13h11m backup's `usr/` subtrees whose sizes match the 10h37m copies. They are summarised as folder rows.

## Key facts (each with its source file)

**Hardware and versions**
- Arm: Stäubli **TX2-140**. Safety program robot `tx2_140-S2`, safety version `202.102`, programCRC 206780900. Sources: `usr/configs/safetyStruct.json`, `libScpConfig/normal.json`, and the safety file name `tx2_140-S2_202-102.pmt2`. The workbook Summary calls the cell "Stäubli TX2 / CS9, controller F_24_0064095_C_003".
- Controller: CS9, ID `F_24_0064095_C_003`. Its syslog hostname is `F-24-0064095-C-003` (`var/log/user.log`). The eeprom reports licence "VAL 3" and MAC `00-13-95-59-e7-3e` (`var/log/eeprom.json`).
- VAL3 / system version: `s8.20.2Cs9_BS4270`, compatibility 13.0 (`usr/configs/val3version.xml`, the same in the 10h37m and 13h11m backups). The log-export folder is also named `s8.20.2cs9_BS4270`.
- HMI user page: `BASIC.html` has meta `src-version` 8.15.1. It has buttons Robot Calibration, Cycle TiePlates, Move to Clear Position, TEST PipeLine and RESTART VUE, plus J1–J6 and DSI temperature fields (`2RT57_Code_Updates/PlateSorter3/interface/BASIC.html`).
- Apera: the active pipeline is `RAIV_pick_AR70` for PlateSorter2 and PlateSorter3 (`state_by_backup.csv`). The gripper is a Magswitch AR70 (`README_2RT57_Apera_Log_Analysis.md`). **No Apera Vue serial number or version appears in any readable file**, and `2RT57_Apera` is empty.
- PLC / HMI panel: there are no program files. The only mention is that `PublishCycle.pgx` feeds the PLC's `DF94`/`DF95` rolling average shown on the C-more panel (Metrics `README.md`). No PLC or C-more program version was found.
- GoPro used for filming: HERO5 Black, firmware HD5.02.02.60.00, serial C3161355977543 (`Data from Corey/MISC/version.txt`). Per the Analysis README the SD card has no footage.

**VAL3 applications on the controller** (Metrics `README.md`, `runs_ALL.csv`)
- On disk:
  - `binpick_TiePlates`: never run.
  - `PlateSorter`: the original app.
  - `PlateSorter2`: production through 2026-09-28.
  - `PlateSorterREWRITE_2`: validation build from 2026-08-21, later withdrawn.
  - `PlateSorter3`: deployed 2026-09-28. It is PlateSorter2 byte-for-byte plus the `LogCycle`/`PublishCycle` telemetry (`DEPLOY_README.md`).
- `vsftpd.log` (FTP, covering 2026-08-25 to 2026-10-10 06:05) shows uploads to `/usr/usrapp/PlateSorter2` on Aug 25, `PlateSorter3` on Sep 28, and **`PlateSorter4` on Oct 9 and Oct 10**.
- PlateSorter4 is not anywhere in OneDrive (`README_2RT57_Apera_Log_Analysis.md` §7).

**Backups and code updates**
- Full SRS backups on file:
  - 2026-09-28 10:37: "Backup of SRC controller 'F_24_0064095_C_003' has ended successfully" (`backup_OK_F_24_0064095_C_003.log`).
  - 2026-09-28 10:45: zip in Metrics `backups/`.
  - 2026-09-28 13:11: backup_OK log. **This is the latest full backup.**
- Log-archive-only exports (no `usr/` tree):
  - `Y-2026_M-10_D-13_03h35m` in 2RT57_Staubli_Backups.
  - `Y-2026_M-10_D-14_03h44m`, `Y-2026_M-10_D-15_03h35m`, `…_03h36m` and `…_12h14m` in Data from Corey/exportLogs. The 12h14m one has been extracted to `var/log`.
- Latest code update on file: `2RT57_Code_Updates/PlateSorter3`, "revised 2026-09-28" (`DEPLOY_README.md`). PlateSorter4 (Oct 9/10) is the newer program actually loaded, but it is not on file.

**Cycle-time metrics**
- Controller RAIVCYC telemetry (`F_24_0064095_C_003_cycles_ALL.csv`, workbook Summary):
  - **Run 1**, 2026-08-21, PlateSorterREWRITE_2, steel 14in plates:
    - 29 cycles.
    - Mean 7.93 s overall.
    - Steady-state mean 5.76 s (10.41 plates/min).
    - Best cycle 5.204 s.
  - **Run 2**, 2026-09-28 09:04–09:07, PlateSorter3, rubber tie plates:
    - 29 cycles, all ACCEPT, 14in.
    - Mean 7.15 s.
    - Baseline mean 6.05 s (9.92/min).
    - 4 cycles of about 14.0 s at plates 6, 12, 18 and 24.
    - Computed from the CSV: median 6.061 s, p90 (nearest rank) 13.97 s, min 5.84 s, max 14.071 s.
- Apera Vue log OCR, 12–15 Oct 2026, 2,845 picks over 4 h 02 m of active picking (`README_2RT57_Apera_Log_Analysis.md`, `2RT57_pick_cycles_2026-10-12_to_15.csv`):
  - Median pick-to-pick 4.31 s.
  - Steady 13.9 picks/min, average while running 11.8/min.
  - Vision wait 1.82 s per pick: capture 0.24 s, detector 0.39 s, motion planning 1.19 s.
  - Robot motion median 2.45 s.
  - From the CSV, over the 2,825 rows that have a pick_to_next value: mean 5.055 s, median 4.31 s, p90 6.703 s.
  - Only 81 of 2,926 vision requests (3%) returned no part.

**Error history, 2026-08-17 to 2026-09-28** (`F_24_0064095_C_003_errors_summary.csv`, count_since_2020)

| Error | Count | Dates seen |
|---|---|---|
| io_no_answer (ERR 125) | 56 | last 2026-09-03 |
| motion_cancelled | 15 | |
| motion_stack_conflict (ERR 35) | 14 | 2026-08-31 to 2026-09-22 |
| calib_instability | 12 | 2026-08-24 to 2026-09-11 |
| calib_handeye_error | 8 | 2026-08-24 to 2026-09-11 |
| apera_bad_pipeline_id | 6 | 2026-08-21 |
| val3_err60_timeout | 5 | |
| workspace_out_of_range | 4 | |
| apera_image_capture | 1 | |

Entries dated 2019-02-14 are the controller's placeholder clock (Metrics `README.md`).

## Open issues (as stated in the files)

1. Production `tkPartFinder.pgx` still has the `"Detector"` pipeline defect behind the 2026-08-20 incident: 9 restarts, about 2 h, about 3,500 pipeline errors, 2 plates. PlateSorter3 does not carry the fix, which would set `sPipelineDet` to `"RAIV_pick_belt_1"` (`DEPLOY_README.md`).
2. The gripper has no part-detect feedback. "All ACCEPT" therefore does not prove a plate was retained, and the rubber tie plates are not yet validated (`DEPLOY_README.md`, Metrics `README.md`).
3. Every 6th plate took about 14 s in the PlateSorter3 run and the log has no explanation. It may be the belt re-jog branch; worth watching (Metrics `README.md`).
4. PlateSorter4, loaded Oct 9 and 10, is not on file. The analysis asks for:
   - a full SRS backup;
   - Apera Vue's own log files;
   - Corey's notes on "spot B" and on the 12-Oct 16:37 stop (`README_2RT57_Apera_Log_Analysis.md`).
5. Apera motion planning takes a flat ~1.19 s per pick. A quarter of cycles start from "spot B" and cost about 1.7 s more. The analysis sets out what it would take to reach 20 picks/min (`README_2RT57_Apera_Log_Analysis.md` §2–4).
6. Downtime:
   - On 12 Oct the log froze after 16:37.
   - On 13 Oct there were 7 stops totalling about 39 min.
   - The controller booted 32 times between 28 Sep and 15 Oct, including mid-day boots on 14 and 15 Oct.
   - Sources: `README_2RT57_Apera_Log_Analysis.md`; boots are also visible in `var/log/dpkg.log`.
7. The 4 new `aoToClick` keys (`nCycleSec_x10`, `nPPM_x10`, `nAvgSec_x10`, `nPlateCount`) are unbound, so nothing reaches the C-more panel until they are bound (`DEPLOY_README.md`).
8. The VAL3 log partition `/mnt/log` is 86% full (19M size, 2.6M free) (`logArchive/diskusage.txt`, 2026-10-15 export).
