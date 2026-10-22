# Project note — IDS belt camera capture failures (2026-10-14)

Source: Apera vision container log (`f9634c28f94f`), 11:09:10–11:09:35 local
(18:09 UTC), pasted by Coty. Pipeline `Pick_IdsBelt_new`, camera `4108577719`.

## Symptom

Every pick attempt fails with `er,Image capture error,-1` returned to the robot.
Three consecutive cycles in the excerpt, all identical. No successful capture in
the window.

## What happens each cycle

| step | time | event |
|---|--:|---|
| 1 | t0 | Robot sends `l,g.Pick_IdsBelt_new,<pose>, -t -s … -e …`; capture queued, server replies `ok,0,0` |
| 2 | +0.55 s | Robot sends `w.Pick_IdsBelt_new.detector` and blocks |
| 3 | +~7.3 s | `camera.cpp:278` — *Timed out grabbing image from 4108577719: Could not grab camera buffer as it is incomplete* |
| 4 | +~7.4 s | `ImgCap Pipeline` fails (7.32–7.43 s); pipeline error; robot unblocked after **6.76–6.87 s** with `er,Image capture error,-1` |
| 5 | +15–50 ms | Robot's follow-up `w.motion_planner` and `w.detector` get the cached failure instantly (µs) |
| 6 | +~1.5 s | Robot re-triggers `g.` — loop repeats |

Loop period ≈ **8.8–9.0 s per failed attempt**, no retry limit observed.

For contrast: normal capture on this pipeline is ~405 ms of a ~1236 ms cycle
(see `Raiv-T1_2026-09-16_apera_call_note.md`). The 7.4 s here is the grab
timeout, not slow capture.

## Correction to first read

From the first log fragment alone, the µs-scale `Robot movement blocked` timers
looked like the server never attempted a capture, and the ~38 ms spacing looked
like a robot retry storm. Both wrong: those are the follow-up wait calls
receiving an already-failed result. The capture *is* attempted every cycle.

## Diagnosis

The camera enumerates and starts streaming, so it is present and powered.
"Incomplete buffer" = frame transfer began but packets were lost before the
frame completed. On an IDS GigE camera this is a network-transport fault, not a
vision-pipeline fault.

Likely causes, most → least probable on a truck:

1. **Link negotiated down to 100 Mb/s** — damaged pair in cable/connector
   (vibration). Full frame cannot arrive within the timeout.
   Check: `ethtool <nic>` → Speed.
2. **Packet size / MTU mismatch** — camera sending jumbo packets
   (GevSCPSPacketSize ~8–9k) through a NIC or switch at MTU 1500. Classic after
   a host reboot/update that didn't persist jumbo-frame config.
   Check: `ip link show <nic>` vs packet size in IDS peak Cockpit.
3. **NIC/switch dropping packets under load** — small RX buffers, bad
   switch/PoE injector.
   Check: `ethtool -S <nic>` rx_missed / rx_dropped climbing during a capture.

Isolation test: stop the vision container, run continuous acquisition in IDS
peak Cockpit. Incomplete frames there too → link/cable/network settings, not
the pipeline. Dropping packet size to 1500 or setting a throughput limit should
make frames complete if it's MTU/bandwidth (diagnostic, not the fix).

## Robot side (VAL3)

Each failed attempt costs ~9 s and the cell retries indefinitely with no fault
raised. Proposed: cap retries at 2–3, then raise a distinct "vision capture
fault" and stop — surfaces the problem to the operator in ~30 s instead of a
silent loop. Keeps the handling in VAL3, not the PLC.

Minor: pose strings are fixed-width formatted with embedded spaces
(`-804.95 ,`, `1.18 ,`). The server parses them fine today; worth trimming so a
stricter parser doesn't trip later.

## Open items

- Find the first occurrence of the error in the log and what preceded it.
- Run the ethtool / MTU / Cockpit checks above.
- What changed on the truck before onset? Timing is close to the AR70 install
  (`1RT53_Code_Updates/AR70_Install_2026-10-13`). Robot code can't produce
  incomplete GigE buffers by itself, but a power cycle, vision-PC reboot or
  cabinet/cable work during the install would be relevant.
- VAL3 retry cap + vision fault — not yet built.
