# binpick_TiePlates_v2_1_0 — jog the belt when the sensor is blocked but nothing is pickable

Copy of v2_0_0 (backup 2026-10-19 15h34m) with one behaviour change. Load it alongside v2_0_0;
backing out = load v2_0_0 again.

## Why
With the beam broken and APERA seeing no pickable plate, the detector loop in tkCycle retried
captures forever (nDetectorTries = 0 = unlimited). The "no pick on beam" counter was only
incremented after that loop, so tkBeltSensor never jogged. On 19 Oct this cost 86 s (190 captures)
and 28 s (57 captures). Even when it did jog, 3 jogs latched a beam-blocked alarm that stopped the cell.

## New behaviour
1. Beam broken + one capture with nothing pickable (or no trajectory) = one miss.
2. Every miss jogs the belt `nBeamNudge_s` = **1.0 s**, then the belt settles and a new picture is taken.
3. No limit and no stop. Every `nBeamNudgeWarn` = **5** jogs in a row (no successful pick between),
   a level-2 warning is logged and `bBeamJogWarn` is set. A good pick resets the count and the flag.
4. A capture that failed on an APERA socket error is not counted as a miss (no jog for a camera fault).
5. No capture is taken until the jog for the previous miss has run (no double-counting the same scene).

## Tunables (data editor, live)
| variable | v2.0.0 | v2.1.0 | meaning |
|---|---|---|---|
| nBeamNudgeAfter | 2 | 1 | misses before the first jog |
| nBeamNudge_s | 0.6 | 1 | jog length, seconds |
| nBeamNudgeMax | 3 | 0 | 0 = unlimited; >0 = old "N jogs then latch alarm" |
| nBeamNudgeWarn | — | 5 | warn every N jogs in a row; 0 = never |
| bBeamJogWarn | — | flag | true while the warning is active |

## Files changed
tkCycle.pgx (both detector loops + Branch B miss), tkBeltSensor.pgx (jog rule, capture gate),
binpick_TiePlates_v2_1_0.dtx (values above, two new globals), .pjx (dtx file name).

## Not tested on a controller — check before production
- Open in SRS / load on the controller and confirm it compiles.
- Dry test: put an unpickable object (flipped plate, block) on the beam. Expect a 1 s jog after
  each failed picture, a warning at 5, 10, ..., and the belt never latching.
- Watch CSV line L <nudges> climb and <beamAlarm> stay 0.

---

# Change 2 — stop the "arm power" popup storm (tkIOMonitor.pgx)

## Why
tkIOMonitor loops at delay(0) and called `enablePower()` on every pass while `dDIPowerEnable` = 1.
The servo switch is NC, so that input stays 1 while the controller waits for a safety restart.
Each refused request logged "Cannot apply arm power: still in disabling phase" + "Cannot settle
arm power: a safety restart is needed" — about 40 pairs a second, a pendant popup each time.
Found in every backup (Oct 5–8 and 19 Oct: 12,724 pairs in 5 min), and it wiped the system log history.

## New behaviour
- `enablePower()` is called only if the arm is NOT powered, `esStatus()==0` (no safety stop or
  restart pending), and at most once every `nPowerRetry_s` (new, **2 s**).
- While a restart is pending: one level-2 message, then silence.
- After the safety is reset, power is requested automatically (same as before — no switch cycle).
- `disablePower()` is called only while the arm is actually powered.

## Test
1. Hit the e-stop with the servo switch ON: expect ONE "safety restart is pending" message, no repeating popups.
2. Release and reset the safety: arm power should come back within about 2 s.
3. Turn the servo switch OFF and press Abort: power drops as before.
4. Pull a backup afterwards: system.log should no longer contain thousands of "Cannot settle arm power" lines.
