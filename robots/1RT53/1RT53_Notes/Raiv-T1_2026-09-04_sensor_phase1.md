# Raiv-T1 — belt laser sensor, first run

Controller `F_24_0064095_C_004` · backup `Y-2026_M-09_D-04_11h19m`
24 picks, 10:48 → 11:02. Sensor observing for the first 11, armed from 10:54.

---

## Deployed, and the sensor itself is sound

All seven files on the controller at exactly the shipped sizes, `tkBeltSensor`
included. It compiled and ran.

**All three phase-1 health gates pass:**

| gate | result |
|---|---|
| `sensor_chatter` | **0** across 24 cycles and 44 break edges |
| `sensor_timeouts` | **0** — never had to hand back to the camera |
| heartbeat liveness | never stalled (no severity-3 log) |

So the input address is right, the polarity is right, and the poll-counted
debounce is clean. The sensor sees plates: **44 break edges in 14 minutes.**

## But the beam is in the wrong place

This is the finding, and it falls straight out of the dwell measurements. Every
distinct beam-break duration the sensor recorded:

| break duration | count | what it means |
|---|---|---|
| **0.03 – 0.43 s** (median **0.08 s**) | **5 of 10** | a plate went **through** the beam and kept going |
| 11 – 72 s | 5 of 10 | a plate **parked** on the beam |

An 80-millisecond break is not a plate arriving at a stop. It is a plate
crossing. And the totals say the same thing louder:

**Only 7 of 44 break edges (16%) stopped the belt. The other 37 were plates
passing the beam.**

So plates are not coming to rest at the beam — they cross it and settle
somewhere further along. That is the overshoot I flagged when we removed the
run-on delay, except larger than latency alone explains: at ~40 ms of detection
latency the plate should stop within a centimetre of the beam, not sail past.

### And it shows up exactly where you would expect

Of the 7 sensor stops, **4 found no pickable plate at the confirming detect** —
and the two failure modes are cleanly separable:

| | when | dwell | extra edges | reading |
|---|---|---|---|---|
| seq 15 | 10:54:54 | **0.03 s** | +2 | belt stopped **after** the plate was already past |
| seq 23 | 11:01:00 | **0.06 s** | +2 | same |
| seq 18 | 10:59:19 | 71.7 s | +1 | plate parked on the beam, pipeline rejected it |
| seq 22 | 11:00:45 | 72.1 s | +1 | same |

The first pair is the geometry problem. The second pair is a plate lying wrong,
which is a legitimate outcome and exactly what the confirm detect is for — 2 in
7 is not alarming on its own.

## The belt-run time gives the sensor no advantage yet

This was the number I said would decide the case. Both paths are timed by the
sensor task, so it is apples to apples:

| stop trigger | n | median belt run |
|---|---|---|
| laser sensor | 7 | **1.73 s** |
| camera poll | 2 | **1.88 s** |

No meaningful difference. That is worth sitting with: the camera loop usually
needs only one or two round-trips when a plate is already arriving, so the
25-try worst case it looked so bad against is rare. **On this run the photo-eye
has not earned the swap.** Where it should still win is the tail — the
starved-feeder and branch-B cases — and 7 stops is too few to see a tail.

## The sensor only governs the belt during a scan

Those 37 crossings are the other half of the story. `tkBeltScan` only consults
the sensor inside its scan window; outside it the belt is driven by `tkCycle`'s
detector branches and `tkCheckZone`, and **neither of those looks at the
sensor.** So plates stream past the beam whenever the belt runs for any other
reason — 28 break edges in one 80-second stretch at 11:01.

That is the gap between what we built and the grocery-belt behaviour you
described. Closing it means having those two other belt owners consult
`bBeltPartAtEnd` as well, which is a phase-2 code change and not a big one.

## One thing about this run that is not the sensor

The robot ran reduced-speed for the first 11 cycles and faster after
(`descend` 0.89 s → 0.50 s; every motion segment moved, all three dwells stayed
at 0.50/0.35/0.50). So the 12.6 s → 11.4 s cycle change across the run is the
speed selector, not the sensor, and cycle time here is not comparable with
yesterday's 5.91 s. **Belt speed is unaffected** — `setMonitorSpeed` governs the
robot, the conveyor is a plant output — so every sensor number above stands
regardless.

---

## What I would do next, in order

**1. Find out where a plate actually stops.** Run the belt with plates and the
robot parked, and watch the Options page: `raw:` flickering and
`beam break edges` climbing while nothing stops means plates are crossing. Then
look at where they come to rest relative to the beam. That distance is what to
move the beam by — **downstream, toward the rest position.** Nothing in the code
can fix a beam that is upstream of where plates stop.

**2. Let me put the disagreement warning back.** I folded it into the summary
line during the rewrite, so a false stop now shows only as a counter and the log
just says "confirm detect saw 0 plate(s)". Adding a severity-2 line carrying the
dwell would make the next run diagnose itself instead of needing this analysis.
Small, safe, and I should not have dropped it.

**3. Then extend the sensor to the other two belt owners** (phase 2), so it
governs the belt outside a scan too. Worth doing after the beam is in the right
place, not before — otherwise it would stop the belt on crossings.

I would hold off on trusting the sensor as the stop trigger until step 1 is
done. It is doing exactly what it was asked to do; it is being asked about the
wrong point on the belt.
