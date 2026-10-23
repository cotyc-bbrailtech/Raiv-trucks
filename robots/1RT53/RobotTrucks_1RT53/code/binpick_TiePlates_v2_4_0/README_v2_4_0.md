# binpick_TiePlates_v2_4_0

Built from v2_3_0 in backup Y-2026_M-10_D-20_13h37m. Load alongside v2_3_0; backing out = load v2_3_0.
**NOT compiled here — compile in SRS first.** Motion paths and descriptors are unchanged; only where the
trajectory picture is fired and how the "nothing pickable" passes wait.

## 1. No more hold above the drop (Part_Accept)
v2.3.0 retreat-to-drop = 1.65 s vs 1.25–1.35 s in v2.2: the APERA trigger call waits ~0.4 s for APERA's reply,
and when it fired near the end of the move the arm sat above the drop until the reply came.
- New `WaitMoveCaptureFar`: during the move to the drop the picture is only fired while the TCP is more than
  `nCapMinDist_mm` (ships **300 mm**) from the drop-approach point.
- If still no picture, it is fired right after the descent to the drop is queued (arm descending at the drop, out
  of the camera view), so the reply overlaps the descent and release.
- The drop interlock (`wait(dDIDropClear and dDIPowerEnable)`) is unchanged and still checked with the arm at rest.
- New `CaptureReady` holds the capture conditions; `TryCaptureNow` now uses it (same behaviour).
- Deliberately NOT done: starting the hover move before firing the picture — the arm would head into the camera
  view while APERA may still be taking the image.

Tune `nCapMinDist_mm` live: retreat still > 1.4 s -> raise it (400–500). Pictures moving late (vision wait up) -> lower it.

## 2. "Nothing pickable" passes (tkCycle)
v2.3.0: 18 passes, median 5.3 s (stop 0.94 + detect 2.48 + fixed settle 0.5 + trajectory 1.39), and one 188 s pass
where the detect loop fired the camera 110 times at a moving belt.
- Detect loops (both) take **one picture per belt-ready**: an empty picture always goes back to WaitBeltParts, which
  waits for a plate at the beam (stopped + settled). No more photographing a moving belt.
  A miss (beam blocked + empty) still counts and jogs the belt as in v2.1.
- Fixed `delay(0.5)` (plate-scan path) now uses `nBranchBSettle_s`, which ships **0** (Branch B used it already).
  WaitBeltParts already guarantees the belt has stopped and settled.
- `AperaPartsFound` (~0.5 s) after these trajectory requests now runs only when APERA returns no trajectory.
Expected: pass ~5.3 s -> ~4.3 s; no multi-minute camera spins.

## Test
1. Compile; short run watched.
2. 20–30 min, stocked belt, pendant unplugged; pull a backup.
3. Expect: retreat back to ~1.3 s, clean pick ~3.5 s, Branch B passes shorter, no huge detect-try counts.
