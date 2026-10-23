# Raiv-T1 — end-of-belt laser sensor, phase 1 (binpick_TiePlates)

Prepared September 3, 2026 · Controller `F_24_0064095_C_004`
Built on the `Y-2026_M-09_D-03_13h31m` backup — verified byte-identical to what
is running now.

**Deploying this changes nothing.** `bBeltSensorStop` ships **false**, so the
sensor is read, counted and logged but controls nothing. You get a run of
validation data first, then flip one button on the Options page.

| File | Was | Now |
|---|---|---|
| `tkBeltSensor.pgx` | — | **12,631** (new) |
| `tkBeltScan.pgx` | 22,309 | **34,681** |
| `LogCycleCSV.pgx` | 12,026 | **15,830** |
| `monitoring.pgx` | 3,389 | **3,996** |
| `killAllTask.pgx` | 3,367 | **3,918** |
| `binpick_TiePlates.dtx` | 45,917 | **49,238** |
| `binpick_TiePlates.pjx` | 1,954 | **1,994** (one line) |
| `interface/UserPageOptions.html` | 5,572 | **8,363** |
| `interface/UserPageOptions.bindings.json` | 1,799 | **3,019** |

Full application reload — the `.dtx` and `.pjx` both changed, and there is a new
program to register.

---

## 1. The input

```
dDIBeltPartPresent  ->  J206_EtherCAT\Term_2_(D24403100)\%I7
```

That is Term 2, **channel 8** — the module is zero-addressed, so Ch.8 is `%I7`.
It is the only unused input on that module: `%I0..%I6` are DropClear,
StartRemote, AbortRemote, EndCycleRemote and the three gripper feedbacks, and
Term 1 is full at `%I0..%I7`. So the address follows from the map rather than
from a guess — but **confirm it on the SP2 I/O page before the first run**
anyway. The check suite now also refuses any new input that collides with an
occupied channel.

**Polarity is a data-editor setting, not a code change.** A through-beam sensor
can be light-on or dark-on, NPN or PNP:

- `bBeltSensorInvert = false` → input HIGH means plate present
- `bBeltSensorInvert = true` → input LOW means plate present

Set it by watching the **`raw:`** readout on the Options page — that is the
undebounced, un-inverted input — with the belt empty and then with a plate on
the beam. Then check the two lamps agree with reality.

---

## 2. What is on the Options page

A block under the pipeline selector:

```
Belt End Laser Sensor
[ BEAM CLEAR ]  [ PLATE ON BEAM ]     [ Sensor Stops Belt ]
alive: 123456   chatter: 0   raw: 1     [ SENSOR ARMED ]
```

- **The two lamps** are the beam state after polarity. Wave a hand through the
  beam while aiming — that is the aiming test.
- **`alive:`** is the sensor task's heartbeat. **If that number is not
  counting, the task is dead** and nothing else on this block means anything.
  This is here because the lamps genuinely cannot tell you that: a dead task
  just leaves its last state published, so it would show a steady "BEAM CLEAR"
  that is indistinguishable from a healthy empty belt. (My first cut claimed
  the two-lamp pair could detect a dead task. It can't — the review caught it,
  and the heartbeat readout is the honest fix.)
- **`chatter:`** must stay **0**. See §5.
- **`Sensor Stops Belt`** toggles `bBeltSensorStop`; **`SENSOR ARMED`** lights
  when it is on.

---

## 3. How to run phase 1

1. Mount and aim the sensor at the pick position. Set `bBeltSensorInvert` so
   the lamps match reality.
2. Confirm `alive:` is counting and `chatter:` is 0.
3. **Leave `Sensor Stops Belt` OFF** and run a normal batch. The sensor is
   logged on every pick as CSV line G while the camera does all the work.
4. Send me the backup. I want to see, before anything depends on it:
   - `chatter` = 0 throughout;
   - `beam_break_edges` climbing about one per pick;
   - `belt_run_s` — how long the belt actually runs to fetch a plate. **This is
     the number that says whether the photo-eye beats the camera poll**, which
     is the whole case for doing this.
5. Then turn `Sensor Stops Belt` on and run again. Now `sensor_stops`,
   `sensor_agree` and `sensor_disagree` start moving, and `agree : disagree` is
   what decides whether the sensor could ever replace the camera outright.

---

## 4. What happens when you turn it on

Belt behaviour becomes **identical to today except for the stop trigger.** Same
belt-on gate, term for term. Same arm-in-cube cap. Same belt-off on every exit.
The gain is entirely in the *poll*: one digital read in milliseconds instead of
an `apera_trigger` / `wait_for_capture` / `inspect` round-trip, up to
`nScanTries` (25) of them.

Then, per your choice, **one** confirming camera detect runs after the belt
stops (`bBeltSensorConfirm`, ships true). It populates the belt-scan task's own
plate count for the log and the agree/disagree counters. It deliberately does
**not** write `nCountPlatesFound` — that stays `tkCycle`'s, so `bLastPart` and
the accept/reject routing are completely unaffected.

### The tunables

| Global | Ships | What it is |
|---|---|---|
| `bBeltSensorStop` | **false** | the master switch |
| `bBeltSensorConfirm` | true | run one camera detect after a sensor stop |
| `bBeltSensorInvert` | false | polarity |
| `nBeltSensorStable_n` | 2 | debounce, in **polls** (≈20 ms) |
| `nBeltSensorPoll_s` | 0.01 | sensor task poll period |
| `nBeltChatterFlips` | 20 | flips without a clean edge before crying chatter |
| `nBeltSensorTimeout_s` | 15 | no new plate in this long → hand back to the camera |

The debounce counts **polls, not seconds**, on purpose. VAL3 `num` is single
precision, so once `clock()` reaches ~1e6 s — eleven days of controller uptime,
which this cell will see — the gap between representable values is ~0.06 s and a
0.02 s threshold stops being a filter at all. A poll counter has no such
failure mode. I'd otherwise have shipped a debounce that quietly stopped
debouncing after a fortnight.

---

## 5. Three things that will bite, and what the code does about them

An adversarial pass over my first cut found all three. They are worth reading
before anyone simplifies this.

**A permanently occluded beam.** My first version tested "is the beam broken"
as a **level**. Anything the pick pipeline doesn't recognise as a plate — a
plate lying wrong, a bolt, a plate half past the beam — occludes the beam for
good. A level test then stops the belt *before it ever moves*, on every scan,
for ever; no new plate can arrive; the timeout that was supposed to hand back
to the camera sat in the `else` of the level test so it could **never fire**;
and the cell reported "found parts" to `tkCycle` on an empty belt with the
feeder-starved indication suppressed. Unrecoverable and near-silent.
Now: the exit requires the **break-edge count to have moved since this scan
started**, and the fallbacks are evaluated on every pass regardless. A
permanent occlusion produces no new edge, times out, raises `bFeederStarved`
and hands the scan to the camera.

**Chatter freezing the state.** If the input flips faster than the debounce
window, no edge is ever accepted and the published state **freezes** — with no
timeout and no alarm. Frozen "plate present" stalls the belt; frozen "clear"
runs it. Now detected: `nBeltChatterFlips` flips without a clean edge
increments `nBeltSensorChatter` and logs a severity-3 warning. **If that
counter is moving, don't enable the sensor** — clean or re-aim it first. It is
on the Options page and in CSV line G for exactly this reason.

**A dead sensor task.** Everything it publishes is an ordinary global that holds
its last value for ever. `tkBeltScan` now samples the heartbeat at scan start
and, if it hasn't moved, logs severity 3 and uses the camera. Plus the `alive:`
readout on the page.

---

## 6. The one thing I got wrong that mattered most

My first cut had the sensor path **skip** the "arm still in conveyor FoV" stall,
on the argument that a photo-eye doesn't need to see past the arm and the test
was only ever about camera visibility.

The first half is true. The second half is wrong, and the original comment in
that very file says so in its own words: *"arm parked in shot, aborted
retreat... rather than run it blind."* That stall is the **only** thing in the
whole application that bounds how long the belt may run with the arm sitting in
the pick zone — `tkIOMonitor` gates only on `bAbort` and `isPowered()`, and
`AperaOwnSocket`'s watchdog bounds *heartbeat silence*, which the sensor loop
keeps advancing, so it can never fire there. Skipping it replaced a 3 s cap
with a 15 s one and deleted the cell's only detector for a parked arm, while
driving steel plates into the tooling. It also let a mid-scan toggle of the
sensor re-energise the belt into exactly the state the stall had just made
belt-off.

It is back, hoisted so it applies to **both** paths, and the check suite now
fails if anyone moves it, disables it, or stops it dropping the belt.

Related: I had also read the five *"arm still in conveyor FoV after 3s"* events
in the 09-03 run as five inefficiencies. They are five **anomalies** — that log
only fires after 3 s of the arm sitting in an 835×835×1000 cube — and the belt
was deliberately *off* during them. Deleting an anomaly detector because its
output looked like waste was the actual mistake.

I also **dropped `nBeltRunOn_s`** (a run-on delay after the beam break). With
the beam at the pick position the error is always *overshoot*, never short, so
the knob was unusable for its stated purpose — and it was a belt-on interval
with no stand-down re-check inside it. If the beam ends up upstream after all,
tell me and I'll add it back properly.

**Honest stopping-error budget**, since my first version understated it:
debounce 20 ms + up to one 10 ms sensor poll + one 10 ms belt-scan poll +
scheduler latency on a priority-10 task ≈ **40 ms and up**, so ~8 mm of
overshoot at 200 mm/s, not the 4 mm I first wrote. If that is too much the fix
is mechanical — move the beam a little upstream — not a smaller debounce.

---

## 7. Merge

1. Copy the eight files into `usr/usrapp/binpick_TiePlates/` (the two interface
   files into `interface/`). **`verify.py` is for the repo, not the
   controller** — don't copy it.
2. Full application reload.
3. Confirm in the data editor that `bBeltSensorStop` = **false**,
   `nBeltSensorStable_n` = 2 and `nBeltChatterFlips` = 20 exist. If they're
   missing the `.dtx` didn't take and `tkBeltScan` won't compile.
4. Check the Options page: `alive:` counting, `chatter:` 0.
5. Set `nCsvCounterEvery` = 10 before a long batch — the log is now seven lines
   a pick (§8).

---

## 8. Log volume

Seven lines per pick at the 5.91 s cycle measured on 09-03 is ~5.5 MB/day,
against ~3.2 MB/day for the four-line build. Setting `nCsvCounterEvery` = 10
drops lines C and D from nine cycles in ten and brings it to ~4.1 MB/day. All
the figures in that comment are now on one consistent cycle-time basis — the
previous version compared seven lines at 6 s against four lines at 4.7 s, which
flattered the change, and quoted two different answers for the same setting.

---

## 9. How this was checked

Nothing here can be compiled or run. The check suite (`verify.py`) plus an
adversarial re-read against the pristine originals stands in for the compiler.
Beyond the checks from the last bundle, it now:

- treats **`bOUTPUTS[...]`** as motion/IO. It didn't before, which meant the
  belt was outside the ordered-IO check entirely — I deleted the
  "belt OFF on every exit" statement as a test and the whole suite passed. That
  is the literal runaway-conveyor mutation, and it was invisible;
- checks **every** belt-on in `tkBeltScan` carries all four stand-down terms,
  matching on whitespace-normalised text (the literal match was defeated by
  writing `bOUTPUTS["Output3"] = true` with spaces);
- asserts the **belt safety invariants** structurally: the arm-in-cube cap
  exists, precedes both branches, tests `nFovClearTimeout_s` and drops the
  belt; the sensor stop is gated on a fresh break edge; the fallbacks are not
  nested where they can't fire; and no `if false` anywhere;
- bans `tkBeltScan` (not just the new task) from **writing** `tkCycle`'s state —
  `nCountPlatesFound`, `sFounds`, `nPartsDet`, `nClassesFound`, `sClassID`;
- bans the sensor task from *writing* the belt while still allowing it to
  *read* it;
- validates every **binding target against the `.dtx`** (a typo'd data name is
  a silently dead lamp) and fails if the HMI can write anything the sensor task
  owns;
- checks **dio address uniqueness**, so a new input can't silently steal an
  occupied channel;
- pins the ships-disabled values, including `bBeltPartAtEnd` = false — shipping
  it true would ship the permanent-stall state;
- diffs a **new** file against empty instead of skipping it, and warns on
  write-only globals.

**I mutation-tested it: 19 deliberate defects injected, 19 caught, control
clean.** Including all three hazards above and both control-flow removals that
the first version of the suite missed.

The parser is updated for line G and tested end-to-end against a synthetic log
in the exact format the new code emits — including a 43,210 s overnight dwell,
which is why the two timing fields are `"5.2"` and not `"3.2"`; at `"3.2"` that
value would have overflowed its field and shifted every column after it. Then
re-run against the real 13h31m log: **123 rows, zero regressions**, new columns
blank on old data.
