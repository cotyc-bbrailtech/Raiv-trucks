# Raiv-T1 — the Options-page magnet fault, and the sensor after the move

Controller `F_24_0064095_C_004` · backup `Y-2026_M-09_D-08_11h34m`
9 picks, 11:07:45 → 11:09:59. App up 08:35, stopped 11:17.

---

## 1. The gripper fault — found, and it is original code

> *while SP2 displays Options screen, gripper will not cycle to pick part*

`uOptions` ends its loop with this, unchanged in every backup back to 2026-08-26:

```
if bMagnetManual==true and dioGet(dDOTool)==0
  call tGripperEMH("ON")
elseIf bMagnetManual==false and dioGet(dDOTool)==1
  call tGripperEMH("OFF")
endIf
```

That is a **servo, not a button handler** — every pass of the loop it forces the
magnet to match `bMagnetManual`. And `dDOTool` is not a request: `tkIOMonitor`
latches it from the coils themselves (`gripperON==1 → dDOTool=1`,
`gripperOFF==1 → dDOTool=0`).

So on every pick, with the page displayed:

1. `tkCycle` grips — `dioSet(dDOemh_gripperON,1)`, then a 0.5 s `delay`.
2. `tkIOMonitor` (it runs `delay(0)`) sets `dDOTool=1` within a tick.
3. `uOptions` (also `delay(0)`) sees `bMagnetManual==false and dDOTool==1` and
   calls **`tGripperEMH("OFF")`**.

The release pulse lands **inside the grip pulse — both coils energised at once** —
and the plate is demagnetised at the moment it should have been picked. Nothing
in `tkCycle`, `Part_Accept` or `Part_Reject` checks part-present, so the cell
does not fault; it picks air and carries on. It happens only on that page because
`tkHMI` runs `uOptions` only while `nUserPage==2`.

Leaving the manual button **on** is the mirror image and just as bad: the loop
re-magnetises straight after `Part_Accept` releases, so the plate stays stuck to
the tool or the next one is snatched on the approach.

**Nothing we shipped touched this file** — I diffed `uOptions.pgx` across
08-26, 09-04 and 09-08 and the code is identical (only SP2's own re-save
whitespace differs). What changed is that the sensor lamps and heartbeat gave you
a reason to sit on the Options page during production. A latent fault that needed
someone watching that page finally got someone watching it.

**Fix is built and in the folder:** `OptionsMagnetFix_2026-09-08.zip` — one file,
`HMI/uOptions.pgx`. The manual magnet becomes **edge-triggered** (only an actual
button press pulses anything) and **gated on `taskStatus("cycle")==-1`** — a press
during a cycle is ignored in both directions and logged. The button still works
for what it is for, jogging the magnet with the cell stopped. README has the test
sequence and the back-out file.

**Until it is deployed: do not leave the Options page up while the cell runs.**
Watch the sensor from there with the cycle stopped, or from the Monitor page.

---

## 2. The sensor after the move — the run can't answer the question

Short version: **the geometry looks better, and there is nowhere near enough
data to say so with any confidence.** Only 9 picks, and the beam saw almost
nothing during them.

| | 09-04 (before the move) | 09-08 (after) |
|---|---|---|
| picks | 24 | **9** |
| beam break edges | 51 | 28 — of which **25 before the first pick** |
| sensor stops | 7 | **1** |
| camera stops | 3 | 0 |
| agree : disagree | 3 : 4 | **1 : 0** |
| chatter / timeouts | 0 / 0 | 0 / 0 |

During the nine picks themselves the counters moved by **3 break edges and zero
new stops.** The plates were already staged in the vision FoV — `plates_found`
ran 3, 3, 3, 2, 3, 3, 2, 1, 1 — so the belt barely had to run and almost nothing
crossed the beam.

### What does look right

The dwell distribution is the number I said would show the geometry, and it has
inverted:

| | 09-04 | 09-08 |
|---|---|---|
| distinct dwells | 0.03, 0.06, 0.08, 0.09, 0.43, 11.4, 23.0, 34.1, 71.7, 72.1 | **471.4, 66.4, 0.19** |
| sub-half-second (a plate *crossing*) | **5 of 10** | **1 of 3** |

The one stop the sensor made — 11:07:13, confirm detect saw **2 plates** — left
a plate **parked on the beam** and it stayed parked through picks 1–3 (`beam at
end` reads 1 on those rows, then clears when it gets picked). That is the
behaviour we wanted and did not get last time: the plate comes to **rest** on the
beam instead of sailing past it. And that stop agreed with the camera, where 4 of
7 disagreed on 09-04.

The single 0.19 s crossing came at 11:09:59, in the stretch where the feed was
running out.

**But it is one stop.** 1-for-1 is not evidence against 3-for-7; it is one
sample. I am not going to call the beam position fixed off this run.

### belt-run time: also one sample

0.54 s on the sensor stop, against 1.73 s median on 09-04 and 1.88 s for the
camera. That would be a real win if it held. n=1.

### The 15 s timeout fired for the first time, and it was right to

11:10:19 — *"belt sensor saw no NEW plate in 15s — falling back to the camera
poll."* Then at 11:10:55, *"belt scan stood down with no plates."* The feeder was
empty. The fallback did exactly its job: it did not hang, it handed back to the
camera, and the camera also found nothing. That is the first live exercise of
that path and it behaved.

---

## 3. Two other things in this run, neither of them the sensor

**APERA image-capture errors.** Five `er,Image capture error,-1` in three
minutes, twice followed by *"Cannot follow trajectory. No valid trajectories were
returned."* This is **not new** — it is a long-standing class, 67 occurrences
first seen 2026-01-15 — but five in a three-minute run is a high rate. It is what
made pick 5 cost 36.6 s (`AperaPartsFound` alone took **19.9 s**) and pick 9
25.7 s. Worth a look at the camera/lighting if it keeps up.

**Negative belt-clear lift.** Picks 6 and 7 logged `tcp_lift_mm` of **−180** and
**−137**; every other pick in every run has been +76/+77. A negative lift means
the TCP sampled *below* its reference, which the early-kick measurement is not
supposed to be able to produce. Both picks are in the middle of the capture-error
stretch, so it may be nothing more than a trajectory that never happened. Flagging
it; not chasing it yet.

**Speed.** `descend` is 0.89 s on all nine picks — the same reduced-speed
signature as 09-04's first block, against 0.37 s at full speed. Cycle times of
7.6–36.6 s here are not comparable with the 5.91 s full-speed median.

---

## Where I would go next

1. **Deploy the Options fix**, and re-run the same test with the page up. That
   also tells you whether any of the picks in this run were fighting the magnet —
   if you were on the Options page for part of it, some of these nine were.
2. **Then a real sensor run**: full speed, plates actually feeding, long enough to
   get 20+ sensor stops. Everything above is 1 stop and 3 edges. Health is clean
   — chatter 0, timeouts behaving, heartbeat alive — so the sensor itself is not
   in question; only whether the beam is now in the right place.
3. **Put the disagreement warning back** as its own severity-2 line with the dwell
   in it. Still my outstanding item from last week, and it is what would let run
   2 above diagnose itself.
4. The standing list is unchanged: branch-B (18% of picks × 3.8 s), the magnet
   dwell bench test, early trigger on every pick.

I have not added these nine rows to the workbook. They would drag the full-speed
statistics without telling anyone anything — say the word if you want them in
anyway for the record.
