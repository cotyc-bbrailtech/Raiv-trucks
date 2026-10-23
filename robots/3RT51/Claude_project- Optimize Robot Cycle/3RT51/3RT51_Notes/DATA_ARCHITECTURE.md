# RAIV-T3 — Data Ownership & Robot-Log Architecture

*Source review: `3RT51_PLC-pdf.pdf` (174p, CLICK PLUS C0-10DD2E-D ladder program), `3RT51_HMI 4-pdf.pdf` + `3RT51_HMI 10-pdf.pdf` (two HMI panel exports), and the `CycleDataLogging_2026-09-04` VAL3 bundle / `Metrics_RT-3_F_24_0064095_C_002` parser in this project folder. Written 2026-09-28.*

## 1. The three systems and how they actually talk

- **Robot controller ("CS9", Stäubli, VAL3)** — runs `PlateSorter`, does the pick/place motion, vision/part-finding, and is the only device that gets **backed up and parsed** (`parse_backups.py`).
- **PLC (CLICK PLUS, IP `192.168.0.10:502`)** — the Modbus TCP **server**. Runs the tie-plate-laying (TPS), encoder/travel, and all counters/timers.
- **HMI** — two panels, both plain Modbus TCP **clients** of the same PLC (`DEV001`): a 4.3" mini panel ("RAIV_Truck_mini") and the 10" in-cab panel ("RAIV_Truck_2"). Neither panel has any direct link to the robot.

The robot and PLC talk **only** over Modbus TCP — CS9 is a client polling/writing named PLC coils (all rungs explicitly commented "From CS9" / "To CS9 Coil xxxx": X401-404, X502-509, X601-709 read robot state into the PLC; Y501-503/Y508 write job selection back to the robot). There is no hardwired robot I/O and no EtherNet/IP CIP messaging — EtherNet/IP, MQTT and OPC-UA are all present in the PLC's config screen but disabled. So **the robot is already set up to read and write arbitrary PLC registers** — nothing new needs to be wired, only new VAL3 logic that uses the link it already has.

## 2. Who owns what today

| Data | Owner | Why | Retentive? |
|---|---|---|---|
| Per-cycle motion segments (approach, linear-approach, tool-on/off, return, vision wait, finder wait) | **Robot** | Only the robot's task timing has this granularity; PLC never sees inside a cycle | n/a (robot log) |
| Parts found / classes found (vision) | **Robot** | Comes straight from the part-finder pipeline | n/a |
| Plate laid/picked/accepted/rejected counts, by type (14in/18in/Pandral/OTM) | **PLC** | Counted from physical sensors (Magnet_ON, PartAccepted, tie detector) that only the PLC reads | **Yes** |
| Travel distance (encoder-derived, cumulative + daily, PLC and servo odometer paths) | **PLC** | Only the PLC reads the railwheel encoder (X001/X002 quadrature → DD1) | **Yes** |
| Cycle/motion time statistics (move vs. non-move vs. powered %, avg time per accept/reject/pick) | **PLC** | The PLC's own "Timers" subroutine derives these from the robot's pass-through motion flags | **Yes** |
| Jam / crash / abort counts (`TPSjam`, `ARM_CRASH pick/place`, `ClickAborMASTER`) | **PLC** | Reliability/downtime data, PLC-side | **Yes** |
| Operator setpoints (tie spacing `DS30`, tie-detector offset `DS1`, double-lay offset `DS15`, job type) | **PLC** | Entered on HMI, written straight into PLC registers — HMI has no recipe DB of its own | **Yes** |
| Alarm/message history, screen-capture JPGs | **HMI SD card only** | Panel-local logging, never written back to PLC or robot | n/a |
| ~15 derived efficiency %s (cycle-time %, accept/reject rate) | **HMI internal tags only** | Computed every second on-panel from PLC tags, never written anywhere else | **No — lost on refresh, never historized** |

Two things worth flagging on their own:

- **Retentiveness is correctly designed, not a gap.** All the discrete motion/handshake flags (X/Y/C bits) are non-retentive (right — stale motion state shouldn't survive a reboot), while every counter, timer accumulator, and setpoint that matters (CT/CTD, most TD, DS, DF, DD1) is retentive. The PLC's cumulative numbers are not at risk from power cycles.
- **The HMI's derived efficiency percentages are the one number series that's genuinely unrecoverable** — they only exist in the panel's internal tag table, second to second, with no logging feature turned on (no Data Sampling/Historical Data configured on either panel). If a performance question ever needs "what did the panel say the accept rate was at 2pm," that answer doesn't exist anywhere after the fact.

## 3. The gap for "best performance evaluation from robot backup logs"

`parse_backups.py` only sees what the robot itself logs. Today that's per-cycle segment timing and vision counts (`RAIV/CSV,A/B,...` lines → `cycles_ALL.csv`), plus events/runs/errors/state pulled from the VAL3 project's own log. **None of the PLC's counters, travel distance, or jam/crash data are in a robot backup**, because the robot never reads them — it only reads the small set of handshake flags it needs to run (Magnet_ON, PartAccepted, job-type bits, etc.), not the accumulators built on top of them.

That means a robot backup alone currently cannot answer things like plates-per-mile, jam rate, or lay-rate vs. distance traveled — all PLC-owned numbers — without also pulling PLC/HMI data separately, on a different schedule, from a different source. Given the whole point of the robot-backup pipeline is that it's the one artifact that's easy to pull and parse on a schedule, the fix is to make the robot the single collection point rather than trying to reconcile three logs after the fact.

## 4. Recommended structure

**Design principle (per Coty, 2026-09-28): push as much as possible onto the robot, because a VAL3 rewrite/redeploy is far easier to iterate on than a ladder-logic change.** That reshapes the plan from "log a curated handful of PLC counters" to "make the PLC a frozen, dumb sensor/counter layer, and do everything else — full-register logging, all derived-metric computation, and all future iteration — in VAL3."

**Hard constraint that doesn't move:** the physical sensors are wired only to the PLC (railwheel encoder on X001/X002, tie detector on X003, magnet/part-accept photo-eyes on X502-507). The robot has no way to sense these directly — it can only *read the PLC's count of them* over Modbus. So raw sensing/counting of anything physical stays on the PLC by necessity; what moves to the robot is everything built on top of that raw count: logging, historization, and derived math.

1. **Log the full raw-counter set, not a curated subset.** Since it's cheap to log an extra register and expensive to add a new PLC rung later, have the robot Modbus-read (no writes) essentially everything performance-relevant and log it raw:
   - Plate counts by type: `CTD9/10/13/14/17/18/20/21` (picked/accepted), `CTD100/101/102` (totals)
   - Travel: `DD1` (raw encoder pulses) — log the raw pulse count, not the PLC's pre-converted inch/ft/mile registers, so unit conversion lives in one place (the parser) instead of two
   - Jam/crash/abort: `CTD121/122/123`, `CTD80-83`
   - Tie spacing/offset state: `CTD30`, `DS1/DS15/DS30`
   - TPS-enabled/run-time accumulators (the `TD` hour/minute trackers)
   
   Logging the raw counters (rather than just today's obvious ones) means a metric you think of six months from now can usually be derived from data you're *already* backing up, without touching the PLC again.

2. **Don't poll the PLC's derived-stat registers (`DF1-DF29`, the move/non-move % and avg-time-per-part registers) at all — recompute them in VAL3 instead.** The robot already has finer-grained segment timing per cycle than the PLC does, so anything the PLC's Timers subroutine currently derives (percent moving, avg time per accept/reject) can be computed from the robot's own per-cycle log plus the raw counters above. This also means the PLC's Timers subroutine never needs a future edit to add a new derived stat — that logic effectively migrates to VAL3/`parse_backups.py`, which is exactly the "easier to rewrite" surface Coty wants to be iterating on.

3. **Use two triggers, not one**, since travel and jam counts accumulate even when the robot isn't running a cycle (repositioning, idle, fault):
   - **Per-cycle** (piggybacking on the existing `tkCycle.pgx`/`LogCycleCSV.pgx` trigger): full counter snapshot, aligned 1:1 with that cycle's segment timing.
   - **A lightweight periodic poll** (e.g. every 15-30s on a VAL3 timer task, independent of cycling) so travel/jam data during idle or fault stretches — which is itself useful reliability data — isn't invisible between cycles.
   
   Log both as new structured lines (e.g. `RAIV/PLC,<ts>,<trigger_type>,<laid>,<picked>,<accepted>,<rejected>,<encoder_pulses>,<jams>,<crashes>,...`) using the same `fLogMsg`-style call `tkCycle.pgx` already uses, so both land in the same backup and the same log-parsing path.

4. **Extend `parse_backups.py`** with a `PLC_FIELDS` constant next to `CYC_FIELDS`, a `plc_snapshot_ALL.csv` output, and move the derived-stat math (percent moving, avg times, plates/mile, jam rate) here rather than trusting the PLC's `DF` registers or the HMI's ephemeral internal tags — this also reproduces, and permanently historizes, the efficiency numbers the HMI currently only computes live and throws away, with zero panel changes needed.

5. **This is entirely a read-only addition on the robot side**, which matters because the bundle's own `verify.py` is built to refuse any motion/IO instruction reordering or addition — Modbus reads plus new log lines shouldn't touch anything `verify.py` is guarding, but should still be run through it before deployment to confirm.

6. **When a future metric genuinely needs a signal the PLC doesn't expose yet** (a new physical sensor, or a count that isn't wired to anything today), that's the one case that still requires touching ladder logic — but keep that PLC-side change to the absolute minimum (just expose the raw new signal/count as a register), and do all the logic, thresholds, and math for it in VAL3. That keeps future PLC edits rare and small, and keeps the fast-iteration surface entirely in VAL3 as intended.

## 5. Before any of that — two loose ends

- **`LogCycleCSV.pgx` and `UpdateCycleWindow.pgx` are missing from `CycleDataLogging_2026-09-04` on disk**, even though `PlateSorter.pjx` references both and the bundle's own `README_DEPLOY_THIS.md`/`verify.py` output describes them as part of the 7-file set. Worth tracking down or recreating before building on top of this bundle, since the project won't reflect what's documented until they're back in the folder.
- **HMI SD-card data (alarm log, screen captures, derived efficiency %s) is out of scope for the robot-backup pipeline by design** — it's panel-local and there's no network path from the robot to it. If those ever need to feed a performance evaluation (e.g., correlating an alarm with a cycle-time dip), that's a separate pull from the panel's SD card, not something the robot snapshot above can reach.
