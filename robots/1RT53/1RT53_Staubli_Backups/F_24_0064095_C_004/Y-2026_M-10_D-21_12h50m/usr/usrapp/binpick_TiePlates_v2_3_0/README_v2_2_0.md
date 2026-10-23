# binpick_TiePlates_v2_2_0

Built from v2_1_0 in backup Y-2026_M-10_D-20_09h43m (includes the intentional Part_Reject edit in tkCycle).
Load alongside v2_1_0; backing out = load v2_1_0. Carries all v2.1.0 belt-jog changes (see README_v2_1_0_BELT_JOG.md).
NOT compiled here - open in SRS, compile, then test on the cell.

## 1. No picture on a moving belt (hydraulic belt coasts a load-dependent distance)
- **Race fixed (tkBeltSensor):** the belt stop time is stamped in the same 10 ms pass that switches the belt off.
  Before, capture-ready flashed ON for one poll at the instant of the stop, so a picture could fire with zero settle.
- **nBeltSettle_s 0.35 -> 1.0 s.** Set it to your measured fully-loaded stop time (slow-motion video from the
  conveyor-output light going off). Live from the data editor.
- **Stale-trajectory guard (tkCycle, before every pick):** each trajectory trigger records the belt start count and
  whether the belt was settled. If the belt was not settled, or has started (feed or jog) since the picture, the
  trajectory is thrown away and a new picture is taken from jApera_Trigger_pos. This is not counted as a miss and
  never causes a jog. Count: `nTrajStaleDiscards` (Options page "stale traj", appended to CSV line L).

## 2. Servo power - request on an edge only (tkIOMonitor)
v2.1.0's 2 s throttle did not stop the popups: one request made while a safety restart is pending stays pending and
the controller itself logs the refusal every 4 ms. esStatus() reads 0 in that state.
- `enablePower()` only on the servo switch OFF->ON edge (no Abort) or a Start pushbutton press, and only if not powered.
- Not powered within `nPowerRetry_s` (2 s): request withdrawn with `disablePower()`, one message:
  "arm power refused - reset the safety circuit, then turn the servo switch OFF and ON (or press Start)."
- Opening the app never requests power by itself. **After any e-stop/safety reset the operator must cycle the servo
  switch or press Start.**

## 3. Options (vision) page cleaned up
Removed (earlier experiments / dead controls): Sensor Stops Belt + SENSOR ARMED (variable no longer read),
Belt Batch block, grip/mag/drop and APERA s readouts, Capture @ FoV block, TCP standstill / Stall Sampler,
Early Belt Kick + KICK ARMED. init() now forces bCaptureOnFovClear, bStallSample, bEarlyBeltKick OFF.
Their code is still present but dormant.
Kept: Robot Status, APERA (TestPipeline, RUN Robot Calibration, pipeline list), belt sensor lamps + alive/chatter/raw,
speed actual/requested/REFUSED, Gripper ON / Part Available, Cycle Timing / Production / Exit, date.
Added: CHECK BELT - JOGGING lamp (bBeamJogWarn), jogs count, settle s, stale traj count.

## Test checklist
1. Compile in SRS.
2. Options page: everything lines up, buttons work, no dead lamps.
3. E-stop with servo switch ON: at most ~2 s of messages, then one "power refused" line. Reset safety, cycle switch -> power on.
4. Run plates, loaded belt: watch "stale traj" - occasional counts are the guard working; if it climbs on most picks,
   raise nBeltSettle_s.
5. Pick accuracy: TCP should match the APERA Vue pose on single plates that just stopped at the sensor.
6. Pull a backup afterwards and send it over.
