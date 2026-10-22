# 3RT51 — Raiv-T3 robot truck (fleet unit T-51)

Stäubli TX2-140 arm on a CS9 controller (controller S/N `F_24_0064095_C_002`) mounted on robot truck T-51. It runs the VAL3 application `PlateSorter`, which uses Apera vision to pick tie plates from a belt and place them at accept or reject stations. A CLICK PLUS PLC runs the tie-plate laying (TPS), and two C-more HMI panels are attached. The cell is called "Raiv-T3" / "RAIV-T3" in the source files.

All data below was pulled on 2026-10-22 from the user's OneDrive (driveId `b!YRe-w6bwZkWI3wwpdfrTWTMaV4ekysxNk4P8wjLriM6iYlZILgXoQ5REXLewPjqU`). `manifest.csv` has one row per file seen: its OneDrive path, size, item URI, whether it was pulled, and where the local copy is. Local copies keep the OneDrive folder structure under this directory.

## Where the OneDrive folders are

| OneDrive folder | Item id | What is in it |
|---|---|---|
| `Claude_project- Optimize Robot Cycle/3RT51/` | 01DTCSEEGQ4USDWMOKLFCJOGFOR7ZAA5YF | `3RT51_Apera` (empty), `3RT51_Code_Updates` (3 VAL3 bundles), `3RT51_Notes` (DATA_ARCHITECTURE.md), `3RT51_PLC_HMI` (PLC .ckp, HMI .cmpv, 4 PDF exports), `3RT51_SRS` (Stäubli Robotics Studio cell `RAIV_T3`, which mirrors the controller `usr/` tree and logs), `3RT51_Staubli_Backups/F_24_0064095_C_002/` (4 controller backups) |
| `Claude_project- Optimize Robot Cycle/Metrics_3RT51_F_24_0064095_C_002/` | 01DTCSEEBIUYE5ALZR3JHZWQKYKECZ3QOL | Cycle-metrics pipeline: parsed CSVs, xlsx workbook, Python scripts, raw `user.log` per backup, and `backups/` (4 empty folders) |
| `Robot Trucks/3RT51/` | 01DTCSEECEGGZ4AJMRZVEJQ6HR5QT7OE36 | `backups`, `code`, `notes`, `videos`: **all four are empty** |
| `Documents/Staubli/backups/3RT51/` | 01DTCSEEGZSLGYEXIG7FHYBVYWYRKQGHX4 | `F_24_0064095_C_002.zip` (36,421,584 B). Binary, listed only |

## What was pulled and what was only listed

- **341 files seen** (plus 54 folder rows). **33 pulled**: 24 in full and 9 partially. 308 were listed only.
- **Pulled in full** (byte sizes match OneDrive):
  - Metrics: README, `cycles_ALL.csv`, `runs_ALL.csv`, `errors_summary.csv`, `state_by_backup.csv`, and three raw `user.log` files
  - All notes and READMEs: `DATA_ARCHITECTURE.md`, `README_DEPLOY_THIS.md`, and two `README.md` files
  - SRS files: `val3version.xml`, `arm.json`, two `user.log` files, `dsiParams.json`, `3d.json`, nginx logs
  - Backups: three `backup_OK` logs and the 2026-09-21 backup's `val3version.xml`
- **Pulled in part**:
  - Files over 400 KB, where the first and last pages were kept and a `##### [PARTIAL PULL]` marker line shows the gap: `events_ALL.csv`, the 2026-09-21 raw `user.log`, and the SRS `system.log`. For the physical controller's `192.168.0.254/system.log` only page 1 was saved.
  - The xlsx workbook, saved as one `__<sheet>.tsv` per sheet. The Cycle Data and Backup History sheets were not saved because they repeat the CSVs.
  - The four PLC/HMI PDFs, saved as text excerpts. The ladder pages convert to page headers only.
- **Could not be pulled:**
  - **All VAL3 source files** (`.pgx`, `.dtx`, `.pjx`, `.ltx`), all Stäubli config files (`.cfx`, `.controller`, `.cell`, `.cuo`, `.3DCell`, `.old`) and the `.py` scripts. The Microsoft 365 connector reports these as `application/octet-stream` and refuses to return their text. The robot code itself is therefore **not** in this folder. It exists on OneDrive in four copies: the SRS cell, the backups, and the code-update bundles. `manifest.csv` flags copies with the same name and size.
- **Not pulled by choice:**
  - Binaries: `.zip`, `.ckp`, `.cmpv`, `.pdf` originals, `.pmt2` safety file, Hilscher `.nxd`/`.spj`, images
  - The TLS `nginx.key`/`.crt`
  - Large vendor or IDE-generated text: Hilscher and EtherCAT `*.xml`, `DefaultLayout.xml`, `.outlining.json`, pendant `interface/*.html`, `libScpConfig/*.json`, `thread_usage.json`, `safetyStruct.json`
  - `safetyStop.csv`, which was read and turned out to be a generic Stäubli safety-stop code table with nothing specific to this robot
- **Not fully crawled**: Microsoft Graph rate-limited the crawl (HTTP 429). These subtrees are summarised as one row per folder in `manifest.csv`:
  - In the SRS cell: the Hilscher fieldbus firmware folders and the `usr/templates/*` and `configs/templates/*` folders
  - In the backups: everything except the 2026-09-04 13h03m `configs` and `usrapp/PlateSorter` folders and the 2026-09-21 `configs` and `usrapp/PlateSorter` folders (the whole 2026-09-04 17h02m `usr/` tree and most of 2026-09-07)
  - These folders are Stäubli templates or near-identical copies of the SRS `usr/` tree, judging by folder sizes.

## Hardware and software identity

**Arm**
- Type `tx2_140-S2`, version `tx2_140-S2-R2`, **arm S/N `F_24_0064095_A_002`** (source: `3RT51_SRS/RAIV_T3/Controller1/log/192.168.0.254/system.log`).
- The 2026-09-21 backup's arm config file is named `arm.F_24_0064095_A_002.cfx`.
- Arm operation counter: `16299` (`.../192.168.0.254/arm.json`).

**Controller**
- CS9, **S/N `F_24_0064095_C_002`**
  - Configuration version `c2.062.1`
  - REST_API / System `s8.18.2cs9_BS4179`
  - System OS `3.3.1`, System Date `Sep 16 2024`
  - CPU/SBL S/N `28751944`, CPT S/N `28881831`
- Safety board: RSI S/N `28834866`, RSI software `202.102`, RSI name `SCP855`, safety protocol FSoE. The safety parameter file is `configs/safety/tx2_140-S2_202-102.pmt2`.
- Starc drive: Starc S/N `69659`, version `9.3 v1.7.0`, FPGA `2023.1-26`.
- SP2 pendant: S/N `29101068`. S/Ns `29141597` and `29045481` also appear in the log. SP2 firmware `3.01i`, software `3.0.3`.
- DSI: S/N `29235028`. `29144588` also appears in the log.
- Sources: `.../192.168.0.254/system.log`. The RSI, Starc and SP2 firmware lines come from the last page of that log, dated 2026-04-07, which was read but not saved locally (see `manifest.csv`).

**VAL3 version**
- On the controller: `s8.18.2cs9_BS4179`, compatibility 13 (`3RT51_Staubli_Backups/.../Y-2026_M-09_D-21_12h27m.OK/usr/configs/val3version.xml`).
- The SRS emulator copy reads `s8.20.2Cs9_BS4270` / config `c2.105` (`3RT51_SRS/RAIV_T3/Controller1/usr/configs/val3version.xml`, `Controller1/log/system.log`).

**Network**
- The controller is at `192.168.0.254` (J204).
- PLC: CLICK PLUS CPU `C0-10DD2E-D`, Modbus TCP server at `192.168.0.10:502` (`3RT51_PLC_HMI/3RT51_PLC V3.0 groc-pdf.pdf.txt`, pages 176-177).
- The robot reads from and writes to the PLC over a Hilscher netX51 Open Modbus TCP module (J207/J208). There is also an EtherCAT J206 module (`DATA_ARCHITECTURE.md`; manifest listing of `configs/hilscher`, `configs/J206_EtherCAT`).

**VAL3 applications**
- `PlateSorter` is the only one that has run: all 101 logged run sessions (`3RT51_CycleMetrics...__Summary.tsv`).
- `binpick_TiePlates` is on the controller but has never run (Metrics `README.md`).
- Active Apera pipelines at backup time: `RAIV_pick_belt_1` (PlateSorter) and `14in_tieplate` (binpick_TiePlates) (`F_24_0064095_C_002_state_by_backup.csv`).

**Apera Vue**
- **No serial number or version was found** in any readable file, and `3RT51_Apera` is empty.
- The Apera VAL3 client library sits under each project's `apera/` folder (listed only).

**PLC programs** (`3RT51_PLC_HMI`)
- `3RT51_ PLC V2.1(Ver3.80).ckp`. Its PDF header reads "RAIV_Truck PLC V2.1(Ver3.80)", 174 pages.
- `3RT51_ PLC V3.0 groc revision.ckp`. Its PDF header reads "3RT51_ PLC V3.0 groc revision", 183 pages.
- Both PDF exports are dated 9/22/2026.

**HMI programs**
- `3RT51_ HMI-4 V2.1.cmpv`: the 4.3" mini panel.
- `3RT51_ HMI-10 V2.0.cmpv`: the 10" in-cab panel. Its PDF project path reads `RAIV-T3 HMI 10in (in cab) V 2.0.eapv`.
- Sources: `3RT51_PLC_HMI/*.pdf.txt`, `DATA_ARCHITECTURE.md`.

## Cycle-time metrics

From `Metrics_3RT51_F_24_0064095_C_002/3RT51_CycleMetrics_F_24_0064095_C_002__Summary.tsv` (the workbook says it was compiled 2026-10-03 from 4 backups):

| Metric | Value |
|---|---|
| Cycles logged | 2587 |
| Mean cycle, all logged cycles | 5.38 s |
| Mean cycle, clean (excludes seq 93 at 27.25 s) | 4.93 s |
| Best cycle | 3.34 s |
| Rate (clean) | 12.18 plates/min, 730.8 plates/h |
| Instrumentation coverage | 0.9995 |
| Total events logged | 6050 |
| Run sessions logged | 101 |
| Error classes tracked | 3 |

Computed by the puller from the pulled `F_24_0064095_C_002_cycles_ALL.csv` (2587 rows, all complete):

| Metric | Value |
|---|---|
| Mean | 5.377 s |
| Median | 4.62 s |
| p90 | 6.30 s |
| Max | 203.38 s |
| Date range | 2026-09-04T20:13:19 to 2026-09-20T23:19:12 |
| Rows from the 2026-09-04_17h02m backup | 93 |
| Rows from the 2026-09-07_13h07m backup | 10 |
| Rows from the 2026-09-21_12h27m backup | 2484 |

Phase budget from the `__Phase Budget.tsv` clean means. The sheet text says it is based on the 93 cycles of 2026-09-04.

| Phase | Clean mean |
|---|---|
| approach | 0.857 s |
| linear approach | 0.373 s |
| tool on | 0.5 s |
| return | 1.508 s |
| tool off | 0.997 s |
| vision wait | 0 s |
| finder wait | 0.688 s |
| Sum | 4.924 s |
| Measured cycle | 4.926 s |

The metrics `README.md` describes only the first 93-cycle run ("~4.7 s clean mean cycle, ~12.8 plates/min"). The workbook Summary text still says "one continuous run, 2026-09-04 20:13-20:29" while reporting 2587 cycles. The workbook text has not been updated for the 2026-09-07 and 2026-09-21 backups.

## Backups and code updates

**Controller backups** (`3RT51_Staubli_Backups/F_24_0064095_C_002/`)

| Backup | Notes |
|---|---|
| `Y-2026_M-09_D-04_13h03m` | backup_OK log: "9/4/2026 1:03 PM … ended successfully" |
| `Y-2026_M-09_D-04_17h02m` | backup_OK log: 5:07 PM |
| `Y-2026_M-09_D-07_13h07m` | backup_OK log: 1:12 PM |
| `Y-2026_M-09_D-21_12h27m.OK` | **Latest.** No backup_OK log in the folder. `logArchive.zip` is 10,897,034 B. |

Also: `Documents/Staubli/backups/3RT51/F_24_0064095_C_002.zip` (date unknown, binary).

**Code-update bundles** (`3RT51_Code_Updates/`)

- **`CycleDataLogging_2026-09-04`** adds cycle and segment logging (`LogCycleCSV.pgx`, `RAIV/CSV,A/B` lines).
  - The metrics README says it was deployed before the 2026-09-04 17h02m backup.
  - On OneDrive the folder holds 7 files, and **`LogCycleCSV.pgx` and `UpdateCycleWindow.pgx` are not among them** (manifest listing).
- **`RAIV_TPS_TRUCK_2026-09-28`** is the latest update. It is a **DRAFT, not on the controller**.
  - It renames PlateSorter to `RAIV_TPS_TRUCK`, adds `PLCStatsSnapshot.pgx` (14 PLC counters logged as `RAIV/PLC,A/B` lines) and adds `call PLCStatsSnapshot()` to `tkCycle.pgx`.
  - The new `aiFromClick` I/O ships unbound, and `bPLCSnapshot_IOBound` must be flipped after binding.
  - `verify.py` result: "PASS (0 fail, 1 warn)".
  - Source: `RAIV_TPS_TRUCK_2026-09-28/README.md`.
- **`RAIV_TPS_TRUCK`** is the same draft as a full project folder: 27 `.pgx` files plus `.dtx`/`.pjx`/`.ltx`. It is missing the `apera/` and `interface/` subfolders (`RAIV_TPS_TRUCK/README.md`).

## Open issues found in the files

1. `LogCycleCSV.pgx` and `UpdateCycleWindow.pgx` are missing from the `CycleDataLogging_2026-09-04` folder even though its `.pjx` references them (`3RT51_Notes/DATA_ARCHITECTURE.md` §5; confirmed by the folder listing).
2. The `RAIV_TPS_TRUCK` / PLC-counter bundle is a draft and not deployed (`RAIV_TPS_TRUCK_2026-09-28/README.md`):
   - All 14 `aiFromClick` channels must be bound in Robotics Studio.
   - The PLC register addresses (CTD100-103, DD1, CTD121-123, CTD80-83, CTD30, DS30) are flagged "please double-check".
   - `parse_backups.py` still needs a `RAIV/PLC` entry.
   - Per-type counters and a periodic (15-30 s) PLC snapshot task are deferred.
3. The `RAIV_TPS_TRUCK` project folder needs `apera/` and `interface/` copied in from the 2026-09-21 backup before it will open or compile (`RAIV_TPS_TRUCK/README.md`).
4. The `Seg*`/`AverageSec` columns in `state_by_backup.csv` are blank in all 4 backups because the application data has never been "saved from SP2" before a backup (Metrics `README.md`; `state_by_backup.csv`).
5. There is no separate "retreat" segment. Retreat time is folded into the next cycle's `approach`, and fixing that needs a reviewed `waitEndMove()` change (`CycleDataLogging_2026-09-04/README_DEPLOY_THIS.md`).
6. The HMI's derived efficiency percentages are never historized and are lost on refresh. No data logging is configured on either panel (`DATA_ARCHITECTURE.md` §2).
7. Logged error classes (`F_24_0064095_C_002_errors_summary.csv`):

   | Error class | Count | Dates |
   |---|---|---|
   | `motion_cancelled` | 30 | 2026-04-07 to 2026-09-10 |
   | `val3_err60_timeout` (ERR 60 Instruction timeout) | 22 | 2026-04-03 to 2026-09-04 |
   | `apera_image_capture` | 1 | 2026-05-19 |

8. The pulled pages of `events_ALL.csv` also show ERROR lines that are not in the summary above:

   | Message | Count | Backups |
   |---|---|---|
   | Apera "Instability detected while performing calibration call" | 28 | 13h03m |
   | same | 3 | 2026-09-21 |
   | "Hand-eye calibration end internal error" | 17 | 13h03m |
   | same | 2 | 2026-09-21 |
   | "ERR 125 No answer from input-output" | about 21 each | PlateSorter~ and Monitor_IO tasks |
   | "ERR 532 The cartesian position is out of the workspace" | 10 | Cycle task |

9. Outlier cycle: seq 93 at 27.25 s, the last cycle before the 17h02m backup, probably the robot sitting idle. The max cycle in `cycles_ALL.csv` is 203.38 s (`__Summary.tsv`, `cycles_ALL.csv`).

## Files in this directory

- `manifest.csv`: every file seen, with pull status.
- `summary.json`: machine-readable key facts.
- `Claude_project- Optimize Robot Cycle/…`: pulled content, mirroring the OneDrive paths.
