# RAIV Development Ideas Log

Status values: Logged (unclassified) → this week / parked / needs info (set at Monday check-in).

## IDEA-001 — "Yesterday's Report" for field crews
- **Date logged:** 2026-10-16
- **Source:** Coty (chat)
- **Units:** All robot trucks (fleet-wide)
- **Status:** Logged — unclassified (awaiting Monday 2026-10-19 check-in)
- **Idea:** Each robot truck produces a "Yesterday's Report" every morning from Robot/PLC data. The B&B Field Operator reads it aloud to all crew working with the truck. It gives a quick review of what went well and what hurt production. Crews are new to these trucks and don't know what hurts production, so the report includes trend-based, plain-language explanations.
- **Examples given by Coty:**
  - Too many tie plates loaded on the belt conveyor means Apera takes longer to process the image and the pick cycle is delayed.
  - Accept Station full means the robot won't drop the part, which delays the cycle.
- **Data needed:** Robot/PLC collected data, trended, with a brief explanation per issue.
- **Clarifications (Coty, 2026-10-16):**
  - Pilot: 1RT53 can be the pilot (still up for debate).
  - Delivery: emailed report.
  - The belt-overload and Accept-Station-full examples come from human observation. No data exists for them yet, so collection signals must be created.
  - Open (consequence of the above): these conditions need new logging on the robot/PLC before any report can be produced.
- **Related:** [[raiv-t3-data-architecture]] (robot-side PLC counter logging, `RAIV_TPS_TRUCK`)
- **Investigation (Claude, 2026-10-16) — 1RT53 backup `Y-2026_M-10_D-12_14h07m`, app `binpick_TiePlates_v2_0_0` / `_BeltSensor`:**
  - Most of the report can be built from data 1RT53 already logs. `LogCycleCSV` writes RAIV/CSV lines A–L for every pick into `user.log`, and the same log carries capture errors, no-trajectory warnings, belt nudges, beam-blocked alarms, starved-belt waits, VAL3 runtime errors and app start/stop. The backup holds 2,296 logged picks (Sep 11 – Oct 8).
  - **Accept Station full:** the robot already times its wait on `dDIDropClear` (Term_2 %I0, likely PLC Y004 "Drop Enabled") as `SegDropClear` (CSV line E). It read **0.00 s on all 2,296 picks.** So either the station never filled during logged runs, or %I0 does not see the Accept Station. Needs a field check before any new code is written.
  - **Belt overload:** vision wait stays flat at about 0.5 s whether Apera finds 1 or 9 plates, so the hypothesis "more plates means slower vision" is not supported. Overload more likely costs time through stacked or crooked plates. On Oct 6 there were 30 "no valid trajectory" captures and 25 belt nudges. Those events are logged, but they are not tied to a plate count.
  - **Real gap:** idle time is not attributed. On Oct 6, 944 picks were about 72 min of picking across 8.5 h. Some stops have a logged cause (a 102-min stop after VAL3 ERR 70 at 12:43, a 75-min stop after ERR 125 I/O loss at 14:44, a 17-min starved belt, camera capture errors). Others have no event at all, for example 10:32 (11 min) and 10:46 (12 min).
- **Proposed solution (draft, for Monday check-in):**
  1. **Robot: state logger (VAL3, new CSV line M).** Log one line on each change of cell state, with its duration. States: RUNNING, WAIT_BELT (starved), WAIT_DROP (`dDIDropClear` false), WAIT_VISION, NO_PICK/NUDGE, ALARM/HELD, STOPPED (cycle start off / power enable off). This accounts for every second of the day. It goes on the robot, not the PLC, and is append-only so the existing parser keeps working.
  2. **Robot: capture line (CSV line N).** Log one line per capture, not per pick, with plates found, trajectory result and time. A no-pick capture can then be tied to how loaded the belt was. Add the Apera pickable count when the Sep 16 request lands.
  3. **Field check for Accept Station.** On the SP2 I/O page, watch %I0 while the station is full. If it doesn't drop, wire a station-full sensor through the PLC to a spare robot input and log it.
  4. **Pipeline:** pull `user.log` from the controller each night (remote access via StrideLinx or a truck-side PC, to be confirmed). Extend `parse_backups.py` and add a rules file. Each rule has a trigger, a threshold against a 7-day baseline, and a one-sentence crew action. Email by about 05:30 with a 60-second read-aloud script at the top and the detail below it.
  5. **Rollout:** start with a report built from existing data only, run from backups for 1RT53. Then deploy lines M/N as v2.1.0. Hold the trend thresholds until there are about 2 weeks of baseline data.
