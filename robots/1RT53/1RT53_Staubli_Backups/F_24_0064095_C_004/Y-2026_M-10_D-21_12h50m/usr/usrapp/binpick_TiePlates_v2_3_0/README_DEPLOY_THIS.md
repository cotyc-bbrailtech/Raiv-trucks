# binpick_TiePlates_BeltSensor — the belt sensor owns the conveyor

> ## 22 Sep — rev D. The belt waits for HEIGHT, not for time.
>
> Rev C held the belt for a fixed 0.75 s. Replaced, on your point that TCP
> velocity on this cell is not a constant — it has already changed during this
> project, and any number of seconds that is right today goes silently wrong
> after the next speed change, in the unsafe direction either way.
>
> The belt now waits for the arm to have physically risen clear of the pick:
>
> ```
>   nTCP_beltLift_mm = TCP world z  -  the z THIS plate was gripped at
>   belt may start when that reaches nBeltClearHeight_mm  (ships 76.2 mm = 3 in)
> ```
>
> `nBeltPickZ_mm` is captured by `tkCycle` in the two statements after
> `tGripperEMH("ON")` returns — the true height this plate was gripped from, not
> a taught pose. `tkBeltSensor` recomputes the lift every 10 ms poll and is now
> its sole writer, so CSV line D's `<liftMm>` column is live again.
>
> **This supersedes `bPickInFlight` as the thing that actually governs the
> release.** `bPickInFlight` drops when the RETREAT IS ISSUED — and `movej` only
> queues, so it said "released" while the arm was still down at grip height.
> The lift gate says released when the arm has actually risen 3 inches.
> `bPickInFlight` is kept because it also covers the APPROACH, before any grip.
>
> **Tuning:** change `nBeltClearHeight_mm` from the data editor, read every
> poll, no reload. Watch `nTCP_beltLift_mm` live to see what the arm is actually
> doing. `nBeltStartHolds` counts one per hold episode and should track the pick
> count almost exactly; `nBeltMasterState` **7** is the hold.
>
> **Two things to know.** If the arm never rises — parked at grip height — the
> belt stays stopped, deliberately, with no timeout that starts it anyway. That
> is the correct fail-safe, and it shows as state 7 with `nBeltStartHolds` not
> advancing. And `nBeltStartDelay_s` is still there but now **ships 0 and is
> inert** — a seconds floor on top of the lift gate, if the height ever proves
> necessary but not sufficient. Leave it at 0 unless you need it.
>
> Units are checked now: `verify.py` fails the build if `nBeltClearHeight_mm` is
> outside a plausible millimetre range. Raiv-Lab once shipped this in metres
> (0.0762) and the gate silently vanished.

**New application, deployed alongside `binpick_TiePlates`, not over it.** The old
application stays on the controller untouched, so backing out is "load the other
one".

Built on the backup you sent (controller `F_24_0064095_C_004`, the state with the
FoV boundary at +550 already deployed).

---

## What you asked for, and what it does

> *Belt Sensor is the only responsible device to start and stop belt conveyor. Do
> not rely on last part detected or "no trajectory found". If Belt sensor does not
> detect parts, conveyor should be running. After belt stops, keeping robot out of
> camera FOV, take picture for trajectory to pick new part.*

| | before | now |
|---|---:|---:|
| programs that command the conveyor | **7** | **1** |
| places the conveyor is written | **28** | **1** (+5 fail-safe OFF) |
| belt decisions taken from a plate count | many | **0** |
| belt decisions taken from "no trajectory" | 3 | **0** |
| captures taken with the belt possibly moving | most | **0** |

The rule, in `tkBeltSensor`, and nowhere else:

```
  beam clear   ->  conveyor RUNS
  beam broken  ->  conveyor STOPS
```

## The one exception, and why it is there

The belt also holds while **`bPickInFlight`** is true — from just before the
APPROACH until the RETREAT is issued.

The beam sits at the pick end. A scene can have plates that are all *upstream* of
it, so the beam reads clear while the robot is descending on one of them. Feeding
then slides the target out from under a trajectory APERA has already planned. That
is the Raiv-Lab over-torque failure, and it is the only thing allowed to defer the
rule. It defers it by at most one pick, and the flag is released as the retreat is
issued — so the belt still gets the whole place-and-return move to feed in, which
is where the early kick was earning its 2.6–2.9 s.

## The deadlock this creates, and how it ends

Sensor-only control has exactly one: something breaks the beam that cannot be
picked — a plate lying wrong, a bolt, debris. Belt stopped, no trajectory, for
ever, and every timeout the cell used to have was attached to the count logic that
just got deleted.

So, as you chose: **nudge, then alarm.**

1. `tkCycle` counts captures that found nothing pickable *while the beam was
   broken* into `nNoPickOnBeam`.
2. At `nBeamNudgeAfter` (2), `tkBeltSensor` runs the belt `nBeamNudge_s` (0.6 s) to
   push the obstruction past the beam. Nudges are sequential — each one needs a
   fresh failed capture, so they cannot fire back to back.
3. After `nBeamNudgeMax` (3) nudges it latches `bBeamBlockedAlarm`, stops, and logs
   at level 3. The cycle holds and reminds once a minute. It does **not** home —
   that would just move the arm away from the evidence.
4. Recovery: clear the belt, **Stop, then Start**. The latch clears when the cell
   stops. No reload, no data editor.

There is also a **runaway cap**: `nBeltRunMax_s` (120 s). At half of it you get
`bFeederStarved` and a message and the belt *keeps feeding* — that is what you
asked for. At the full 120 s with nothing having reached the beam it stops and
alarms, because a normal advance measured 1–8 s on 11 Sep. Set it to 0 to disable.

## The capture

Every capture in the cycle now proves two things first: the belt is stopped and
settled with a plate on the beam (`WaitBeltParts`), and the arm is out of the
conveyor camera (`WaitFovClear`). `Part_Accept` and `Part_Reject` no longer capture
during the place move unless both hold — which they usually will not, because the
belt is feeding then. **Expect `cap_at_place` to collapse and `cap_belt_busy` to be
large. That is the change working.**

If nothing captured by the time the trajectory is needed, `tkCycle` moves to
`jApera_Trigger_pos`, waits for the belt, and captures there.

**This one closed a real hazard.** Before this block existed, a pick with no
capture would have fallen through to `apera_wait_for_trajectory` being skipped,
leaving `bTrajectoryFound` holding the *previous* pick's answer — the arm executing
a trajectory planned for a plate that had already been carried away. The old code
was safe from it only because `Part_Accept` captured on essentially every pick,
which this change stops being true. `bTrajectoryFound` is now forced false whenever
no capture was taken.

## Files

| file | was | now |
|---|---:|---:|
| `tkBeltSensor.pgx` | 15,035 | **23,575** — sensor **and** belt master |
| `tkBeltScan.pgx` | 35,840 | **4,480** — retired to a handshake keeper |
| `tkCheckZone.pgx` | 10,531 | **7,149** — early belt kick removed |
| `tkCycle.pgx` | 79,712 | **91,424** — 14 belt writes out, capture gates in |
| `Part_Accept.pgx` | 24,509 | **26,337** — capture gated on a stopped belt |
| `Part_Reject.pgx` | 5,973 | **7,378** — same gate |
| `LogCycleCSV.pgx` | 33,302 | **36,566** — new CSV line L |
| `init.pgx` | 8,563 | **9,250** — clears the two new flags |
| `monitoring.pgx` / `killAllTask.pgx` | | comments corrected |
| `WaitBeltParts.pgx` | — | **4,368** new |
| `WaitFovClear.pgx` | — | **3,493** new |
| `BeltAlarmHold.pgx` | — | **2,640** new |
| `binpick_TiePlates_BeltSensor.dtx` | 55,987 | **58,793** — 26 globals added |

`bEarlyBeltKick` now ships **false** and has no effect either way — the code it
drove is gone. `bLastPart`, `nLastPartThreshold`, `nCountAtArm`, `nPickLiftSeq` and
the rest of the kick's globals are **kept in the .dtx and kept bound to the Options
page**, unwritten, so the historical CSV columns still parse and the page does not
break. Nothing reads them.

## Tunables — they are in the DATA EDITOR, not on a page

I did not touch the HMI pages. The Options page is absolutely-positioned VALHTML at
its full 690 px and editing it to add eight controls is a good way to break a page
that currently works, for no function you cannot get from the data editor. Say the
word and I will do it as its own change.

| global | ships | what it does |
|---|---:|---|
| `bBeltMasterEnable` | **true** | false parks the belt off — maintenance |
| `nBeltClearHeight_mm` | **76.2** | lift above the grip before the belt may start (3 in) |
| `nBeltStartDelay_s` | **0** | secondary seconds floor on top of the lift gate; inert |
| `nBeltSettle_s` | 0.35 | belt-off to capture-allowed |
| `nBeamNudgeAfter` | 2 | failed captures on a broken beam before a nudge |
| `nBeamNudge_s` | 0.6 | nudge duration |
| `nBeamNudgeMax` | 3 | nudges before the alarm |
| `nBeltRunMax_s` | 120 | runaway cap; 0 disables |
| `nBeltWaitTimeout_s` | 60 | how long a wait blocks before rechecking |
| `nBeltAlarmLog_s` | 60 | alarm reminder interval |
| `bBeltSensorInvert` | *unchanged* | **check this first — see below** |

## Before the first automatic run

1. **Polarity.** `bBeltSensorInvert` used to decide whether statistics were right.
   It now decides whether the conveyor runs when it should stop. In manual, watch
   `nBeltSensorRaw` with the beam clear and then with a plate on it, and confirm
   `bBeltPartAtEnd` follows the plate and not its absence.
2. **The address.** `dDIBeltPartPresent` → `%I7` on Term 2. Confirm on the SP2 I/O
   page. If the input never changes state, that is the first suspect.
3. **`nBeltSensorChatter`.** Must not move. If it does, the published state is
   frozen and the conveyor is being commanded from a frozen reading.

## Then, on the first run — read these three, in this order

| counter | expect | if not |
|---|---|---|
| `fov_declines` | **0** | the capture pose is inside the FoV cube. This is the 15 Sep failure repeating — check `nStartFoVX_mm` (1075) against `jApera_Trigger_pos`. It is the pose, not the timeout. |
| `belt_master_dead` | **0** | `tkBeltSensor` is not running; the conveyor is uncontrolled |
| `no_pick_on_beam` | **0** between picks | the beam sees things the camera will not pick |

Then `nBeltNudges`, `nBeltRunawayStops`, `cap_belt_busy`, and `nSensorAgree` vs
`nSensorDisagree`.

CSV **line L** carries all of it, once per pick, ungated. Fields are appended only,
so `parse_backups.py` keeps working on the old lines.

## What I could not check

Nothing here was compiled or run. `verify.py` **PASS (0 fail, 0 warn)** and
`mutate.py` **32/32 caught, 0 missed** — those check XML, BOMs, block balance,
every identifier against the `.dtx`, `toString()`-on-bool, and the invariants this
change exists to create (one belt writer; no belt decision from a vision result; one
writer per new flag; no capture without a stopped belt; no stale trajectory). They
do not check that VAL3 accepts the syntax.

Specifically **unverified**:

- the three new programs and their `use="reference"` parameters compile;
- `toString("",nBeltRunMax_s/2)` — an arithmetic expression as a `toString`
  argument. This is the only construct here the project has not used before. If it
  is rejected, assign it to a local first;
- `tkBeltSensor`'s priority is still **10**. It ran at 10 with a 10 ms poll through
  the 11 Sep runs and agreed with the confirm detect 26 times out of 26, so the
  scheduling is adequate for a 10 ms decision — but that was measured while it was
  an observer. If the belt is slow to stop after a plate reaches the beam, this
  number is the first thing to look at and `nBeltSensorPoll_s` the second.

## Cycle time — expect this to be slower at first

Being straight about it: this trades throughput for correctness.

The overlapped capture is gone. The belt advance no longer starts before the plate
leaves the beam, and the capture waits for a stopped belt rather than happening
during the place move. On 11 Sep the kick was worth **2.6–2.9 s per belt advance**
and it fired on 20 of 35. Some of that comes back — `bPickInFlight` releases at the
retreat, so the belt still feeds across the place-and-return — but not all of it.

What you get for it: no phantom count, no Branch B belt runs, no capture on a
moving belt, and a belt whose state you can predict by looking at the beam. The
duplicated settle delays in both branches (`nBranchBSettle_s`, and two hard-coded
`delay(0.5)`s) are now redundant, since `WaitBeltParts` already guarantees a
settled belt — that is the obvious next 0.5–1.0 s and I left it alone to keep this
change to one subject.

## Back out

Load `binpick_TiePlates`. It is untouched.
