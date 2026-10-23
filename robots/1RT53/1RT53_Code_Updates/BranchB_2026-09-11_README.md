# Raiv-T1 — Branch B, and a correction to the run 19 report

**Three files**, built on `Y-2026_M-09_D-11_11h53m`. `_original/` is
byte-identical to what is on the controller now.

| file | on controller | this build | diff |
|---|---:|---:|---|
| `tkCycle.pgx` | 70,240 | **76,325** | +97, **−1** |
| `LogCycleCSV.pgx` | 30,289 | **32,356** | +33, −0 |
| `binpick_TiePlates_TEST.dtx` | (54,264) | **55,393** | 11 declarations added, **no value changed** |

The one removed line is `delay(0.5)`, which becomes `delay(l_nBrSettle)` — a
clamped local seeded from a new tunable that **ships at 0.5**. Deploying this
changes nothing about how the cell runs.

**No HMI files.** The Options page is a fixed 480 × 690 and the only gap left
is 17 px. These are measurements, not options, and they belong in the CSV. I
am not squeezing a 16 px row onto your pendant to save myself a page edit.

---

## First: I named the wrong branch, and you should know before you act on it

The run 19 report said the ~4 s hits were the **empty-scene re-scan** — the
`nCountPlatesFound==0` branch. **That was wrong, and the log says so in one
line:** `plates_found` never logged 0 in the entire run. It ran 1 to 9, never
0. That branch never executed.

What actually ran is **Branch B — "No Pickable Parts Found"**, the
`bTrajectoryFound==false` path. It is already counted by `nBranchBPasses`, and
differencing that counter against the cycle rows gives a clean answer:

| | |
|---|--:|
| passes | 2 → 67 = **65**, one every **4.7 picks** |
| high-unaccounted picks | 47 |
| **of those, preceded by a Branch B pass** | **47 — 100%** |
| median cost | **3.86 s** |
| total | 209 s of a 27.5 min run |
| **amortised** | **+0.68 s on every pick** |

The cost numbers in the report were right. The mechanism was not, and it
matters: an empty scene is a **feeding** problem, and you would have gone and
looked at the belt. Branch B is a **vision** problem — APERA *sees* two or
three plates and plans no pickable trajectory for any of them. Different
cause, different fix, and the sensor remount you are doing now will not touch
it.

There is a note already in that branch from 2026-09-02 reading *"the cell
looping here for ~24 s on roughly every fourth pick"*. Same branch, same
period, three months apart. It has been there the whole time.

## What Branch B actually does

```
movej(jApera_Trigger_pos) + waitEndMove()     travel  - real motion
belt ON, apera_trigger/wait_for_capture/inspect loop   detect  - a full capture per try
belt OFF, delay(0.5)                          settle
apera_trigger_trajectory + AperaPartsFound
  + apera_wait_for_trajectory                 traj    - ARM PARKED
```

Note the last one. On the main path that same wait is hidden behind
`movej(jTrajectoryStart, mReach)` — the arm flies while APERA thinks. On this
path nothing is queued and the arm stands still for the whole round trip.

**That is the obvious thing to fix, and this bundle does not fix it.** Two
reasons. First, I do not know whether it is 0.4 s or 1.6 s of the 3.86, and
the four parts are indistinguishable in today's log. Second, Capture @ FoV was
also obvious, measured −0.34 s on rubber, and delivered **−0.07 s, p = 0.18**
on steel because the saving moved into the approach. Obvious is how that went
wrong. So this measures first.

## The free one nobody has looked at

After Branch B finishes — having *just* done its own
`apera_trigger_trajectory` + `apera_wait_for_trajectory` — the main loop falls
into `if l_bCycleDone==false` and calls **`apera_wait_for_trajectory` again,
with no trigger in between**. It also moves to `jApera_Trigger_pos`, where the
arm already is.

If that second wait returns instantly off a cached result it costs nothing. If
it is another full round trip it is **~0.28 s a pick** on its own. Nothing in
the log can currently tell you which. `nLoopTopWait_s` now does, and it costs
one `clock()` on a path that runs once every 4.7 picks.

## What gets logged — line K, eleven fields

```
RAIV/CSV,K,<seq>,<brPasses>,<brTotal>,<brTravel>,<brDetect>,<brSettle>,
                 <brTraj>,<brTries>,<brPlates>,<brTotalAll>,
                 <loopTopWait>,<loopTopCount>
```

**Not gated on a toggle**, unlike lines I and J. Branch B is not an
experiment — it is production behaviour costing 0.68 s a pick that has been
invisible since the cell was built.

Branch B completes no pick, so it emits no row of its own. These fields
describe the **last** pass and are logged on the next pick — which is the same
pick that carries the unaccounted seconds, so the two line up in the parser
with no extra work. `travel + detect + settle + traj` must equal `brTotal`;
they are differences of the same four stamps, so a disagreement means the code
is wrong, not the cell.

`brTries` counts **detector round trips across all passes** of the outer
`while`, not `l_nTries`, which restarts at 0 each pass — that mistake would
under-report a starved feeder, which is the one case you most want to see.

## The one tunable

`nBranchBSettle_s` replaces the hard-coded `delay(0.5)` after the belt stops.
**It ships at 0.5**, so it is behaviour-neutral until you change it in SP2.

Sweep it downward only with `plates_found` and the APERA error line in view.
That settle exists so the belt has stopped before the capture, and a blurred
capture here does not cost you 0.2 s — it costs a whole extra Branch B pass,
which is 3.86.

The clamp is applied to a **local**, not written back onto the tunable: code
in this project does not overwrite a value you own, so the data editor and the
pendant can never disagree about what you typed.

## Verification

`verify.py` **PASS (0 fail, 6 warn)** · `mutate.py` **111/111 caught, 0 missed**.

New §7n and thirteen new mutations. The invariants are that the timing is
measurement and can only ever be measurement: the settle ships at the number
it replaces (checked in two independent places); the delay is on the clamped
local and no code writes the tunable; **the ordered sequence of every move,
output, wait and `apera_*` call in tkCycle is byte-identical to the
controller's current copy**; the four parts are the exact stamp differences
that sum to the total; each stamp is taken once, in order; the try counter is
reset and counts the detector loop; the loop-top window provably brackets an
`apera_wait_for_trajectory` **with no trigger inside it**; nothing anywhere
branches on any of the ten published values; and line K is not gated, keeps
its field order, and is documented in the header.

### Three repairs to the suite itself

**§10 had a hole and a mutation walked straight through it.** The live-value
check iterated the *live* file's values, so whenever the controller's `.dtx`
carries no `<Value>` element — which, since the reload, is the normal state
for most names — a bundle could **add** one and nothing would say a word.
Deploying that changes the setting. New §10(b2) checks the other direction:
absent is a value, not a gap.

**§7c was demanding the opposite of what it wanted.** It required an explicit
`<Value key="0" value="false"/>` for every ships-disabled name. With the live
file no longer carrying those elements, the only way to pass was to *write
values onto names you own* — the §10 defect entered from the side. It now
accepts an absent element when, and only when, the required value is the type
default; wanting `true` or `9999` still requires a real element.

**`bBeltSensorStop` has left the ships-disabled table.** It is not an
experiment any more — it has been on in production since 09-09, and a rule
saying it must ship false would make every future bundle either fail or quietly
overwrite you. §10 is the check that actually protects it.

Eight existing mutations had gone **SETUP FAIL** against the refreshed `.dtx`
— they edited `<Value>` elements that no longer exist. A mutation that cannot
be applied proves nothing, so all eight were retargeted rather than dropped.

## Not verified — nothing here compiles or runs

- the eleven new `.dtx` globals resolve, and the six new `num` locals are accepted
- `delay()` on a local rather than a literal — used elsewhere in this project
  (`delay(nGripSettle)`, `delay(nBranchBSettle_s)`'s neighbours), but worth a glance
- line K is ~99 bytes, well inside the 255-byte `logMsg` cap

## Test it

1. Deploy and run 50 picks. Cycle should read exactly what it reads today —
   4.42 clean median. That is the no-op check, and it is the whole claim.
2. Read the first line K with a non-zero `brTotal`. Check
   `travel+detect+settle+traj` sums to it.
3. **Read `loopTopWait` first.** If it is ~1.3 s there is a free 0.28 s a pick
   sitting in a duplicated vision query and I will build that next.
4. Send the backup. With 60-odd passes the split will be solid, and then we
   will know whether the parked wait is worth queueing the reach move into —
   and I will build that as a toggle, off, the same way as the last three.

## Back out

Copy the three files from `_original/` back. There is no toggle to switch off
because there is nothing switched on: with `nBranchBSettle_s` at 0.5 this
bundle only writes numbers into the log.
