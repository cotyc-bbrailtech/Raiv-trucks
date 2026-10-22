# 1RT53 tie-plate bin pick — Claude session summary (19–20 Oct 2026)

Controller F_24_0064095_C_004 (Stäubli TX2-140, CS9) · APERA vision · magnetic gripper · hydraulic conveyor with end-of-belt laser sensor.
Goal: **17 plates/min = 3.53 s per plate**, no interruptions.
Backups: `Documents\Staubli\backups\Raiv-1\F_24_0064095_C_004\` (one folder per backup, newest `Y-2026_M-10_D-20_13h37m`).
Living code map: **tkCycle Motion & Wait Map** — https://claude.ai/code/artifact/91b24480-4560-4401-9562-6e641550fe7b (every move/stop/wait line, marked per version).

## Where the cell stands
| Run | Typical pick | Real output | Notes |
|---|---|---|---|
| v2.0.0, 19 Oct | 4.39 s median | 8.0 /min | 9 min of stops in 41 min; feeder thin |
| v2.3.0, 20 Oct (321 picks, 38 min) | 3.93 s on clean picks (~15.3 /min) | 8.4 /min | 26% stops, 18 "nothing pickable" passes (~15 s each), belt sensor stuck for 31 picks |

Clean-pick breakdown v2.3.0: approach+descent 1.31 · grip 0.25 · retreat to drop 1.65 · place/return 0.58 · vision wait 0.10 s.

## Versions built (each deployed alongside the previous one; back out = load the previous)
| Version | Main changes |
|---|---|
| v2.1.0 | Belt jogs 1 s on the first "nothing pickable on a blocked beam" (no alarm latch, warning every 5 jogs); detect loop no longer spins forever; servo-power request throttled |
| v2.2.0 | Capture-ready timing race fixed; belt settle 1.0 s (hydraulic belt coasts); stale-trajectory guard; servo power requested on switch edge / Start only (stops the popup flood); Options (vision) page cleaned of old test controls |
| v2.3.0 | Picture taken while the arm moves; no stop at trigger pos; no backtrack; hover via blended `mHover`; plate count only when no trajectory; approach blends into descent |
| v2.4.0 (built, not tested) | No picture in last 300 mm of move to drop (`nCapMinDist_mm`), fired during descent instead (removes ~0.4 s hold); "nothing pickable" passes: one picture per belt-ready, 0.5 s fixed settles → 0, plate count only when needed |

Tkcycle edit kept: plates whose APERA type ≠ selected type now go to `Part_Reject` (intentional, Corey).

## Open items
1. Test v2.4.0 (compile in SRS, watched run, then 20–30 min stocked belt, pendant unplugged; pull backup).
2. **Belt sensor sticking** (count froze for 31 picks) — check plate resting/overhanging at the beam, sensor aim/lens.
3. **Feeder rate** — vision often sees only 1 plate; 17/min needs >17 pickable plates/min arriving.
4. Measure loaded belt stop time (slow-motion video) → set `nBeltSettle_s` (currently 1.0 s).
5. Ask APERA whether the ~1.3 s trajectory response can be reduced.
6. Find what trips the safety (~10 min of stops, 6 "arm power refused").
7. Gripper part-present / magnet-status inputs read 0 always — wiring or code.
8. User-page path reported in lowercase (HMI "page not found" / ERR 70 on 19 Oct).
