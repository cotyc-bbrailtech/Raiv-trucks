# AR70 install - 1RT53 - project binpick_TiePlates v2.0.0

Package built 14 Oct 2026 (folder dated 13 Oct for the install day).

Base: backup `Y-2026_M-10_D-12_14h07m\usr`. `USR_prior_to_update` is an unchanged copy of it (369 files). `USR_2026-10-14` is the same full tree with the changes below.

Correction to the first version of this package: it edited `binpick_TiePlates`, which is not the project the controller runs. `configs\cell.cfx` auto-starts `binpick_TiePlates_BeltSensor`, so this version is built on that project. The first build is kept in `_superseded_partial_files\USR_2026-10-14_wrong_project_binpick_TiePlates` for reference only. Do not load it.

## Project version
`binpick_TiePlates_BeltSensor` (rev D, as deployed 12 Oct) is now baseline v1.0.0. This package renames it to `binpick_TiePlates_v2_0_0` (MAJOR bump: new tool, new TCP, re-teach required). Rules are in `..\VERSIONING.md`; history is in `..\VERSION_LOG.md`.

Rename: folder, `.pjx`, `.dtx`, `.ltx`, the `<Data file=...>` line in the `.pjx`, and the `autoStart` line in `configs\cell.cfx`. No other file in the tree referenced the old name (README_DEPLOY_THIS.md mentions it in text only). Dots are not used in the name because existing application names on the controller contain none and dots are not known to be legal in a VAL3 application name.

## Files that differ (outside the rename)
Everything else in the 369 files is byte-identical to the prior tree.

| File | Lines before | Lines after | Added | Removed |
|---|---|---|---|---|
| usrapp/binpick_TiePlates_v2_0_0/AperaCalibrateProgram.pgx | 14 | 14 | 2 | 2 |
| usrapp/binpick_TiePlates_v2_0_0/HMI/uProduction.pgx | 131 | 131 | 1 | 1 |
| usrapp/binpick_TiePlates_v2_0_0/Part_Accept.pgx | 453 | 453 | 7 | 7 |
| usrapp/binpick_TiePlates_v2_0_0/Part_Reject.pgx | 145 | 145 | 7 | 7 |
| usrapp/binpick_TiePlates_v2_0_0/WarmUp.pgx | 57 | 57 | 16 | 16 |
| usrapp/binpick_TiePlates_v2_0_0/binpick_TiePlates_v2_0_0.dtx | 1080 | 1086 | 6 | 0 |
| usrapp/binpick_TiePlates_v2_0_0/binpick_TiePlates_v2_0_0.pjx | 55 | 55 | 1 | 1 |
| usrapp/binpick_TiePlates_v2_0_0/clickAbort.pgx | 92 | 92 | 12 | 12 |
| usrapp/binpick_TiePlates_v2_0_0/moveToHome.pgx | 31 | 31 | 4 | 4 |
| usrapp/binpick_TiePlates_v2_0_0/tGripperEMH.pgx | 97 | 114 | 17 | 0 |
| usrapp/binpick_TiePlates_v2_0_0/tMagnet.pgx | 32 | 32 | 4 | 4 |
| usrapp/binpick_TiePlates_v2_0_0/tkBeltSensor.pgx | 599 | 599 | 1 | 1 |
| usrapp/binpick_TiePlates_v2_0_0/tkCheckZone.pgx | 137 | 137 | 2 | 2 |
| usrapp/binpick_TiePlates_v2_0_0/tkCycle.pgx | 1485 | 1485 | 17 | 17 |
| usrapp/binpick_TiePlates_v2_0_0/tkIOMonitor.pgx | 332 | 332 | 1 | 1 |
| configs/cell.cfx | 1 line changed (autoStart name) | | | |

## What changed
- `.dtx`: new tool `tAR70` (z=241, flange[0], `ValveIO\valve2`, ioOpen=ioClose=0.25 s, same as 2RT57). New public string `sGripper`, default "AR70".
- `tGripperEMH.pgx`: if `sGripper=="AR70"`, ON runs `open(tAR70)` and OFF runs `close(tAR70)`; otherwise the original Schunk pulses. `waitEndMove()` and the `_nGripSyncClk` stamp are shared, so callers and timing segments are unchanged.
- Every motion that used `tSchunkEMH084` or the old `tTool` now uses `tAR70` (code only, comments untouched). This includes `tMagnet.pgx`, so the manual magnet buttons now fire the AR70 on valve2 instead of the old valve1 tool, and `HMI/uProduction.pgx`, whose gripper-state display now reads `tAR70.gripper`.
- Not touched: `binpick_TiePlates_BeltSensor - Claude` (rev E, grip-verify and same-spot counters, all OFF). It is not the active project and is unchanged in both trees. If you want rev E, it should be re-based on v2.0.0 as v2.1.0.

## Check before the first move (not verified from here; not built in SRS)
1. TCP z=241 is copied from 2RT57. Measure flange face to pole shoe face and edit `tAR70` first. Jog slowly.
2. AR70 is on valve2 (confirmed). `dDOValve1Enable` (init, tkIOMonitor, old tMagnet) was left alone; 2RT57 runs the AR70 on valve2 without an enable.
3. Apera pipeline is still `Pick_IdsBelt_new`; an AR70 pipeline is needed in Apera Vue (2RT57 uses `RAIV_pick_AR70`).
4. 0.25 s dwell is a starting value. `nEMH_onDelay/offDelay` are now ignored; `nGripSettle` still applies.
5. Count grip failures (rust, pitting) before cutting any dwell.
6. Open the package in SRS once and let it verify the project (the edit was text-level and has not been compiled).

## Rollback
Load `USR_prior_to_update` (project `binpick_TiePlates_BeltSensor`, v1.0.0). Setting `sGripper="EMH"` alone restores the Schunk pulses but leaves the motions on tAR70, z=241.
