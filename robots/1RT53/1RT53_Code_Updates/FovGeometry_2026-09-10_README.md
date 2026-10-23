# Raiv-T1 — where the arm actually is when the FoV clears

**Three files**, built on the `Y-2026_M-09_D-10_12h53m` backup. `_original/` is
byte-identical to what is on the controller now. Every change is an addition:

| file | on controller | this build | diff |
|---|---:|---:|---|
| `Part_Accept.pgx` | 15,077 | **20,561** | +103 lines, 0 removed |
| `LogCycleCSV.pgx` | 27,659 | **29,065** | +24, 0 removed |
| `binpick_TiePlates_TEST.dtx` | (53,876) | **54,769** | 7 declarations added, no value changed |

Pure measurement. No motion, no output, no branch — `here()` and `position()`
and some arithmetic. It only runs while **Capture @ FoV** is on, and it logs
nothing at all while that is off.

---

## The question this answers

Run 15 put the number on it: `nFovWait_s` = **0.93 s**. The arm spends nearly a
second inside the conveyor FoV cube after the drop-approach `movej` is queued,
and the capture cannot fire until it leaves. That is why 0.41 s of APERA's
1.37 s is still blocking the cycle.

Shrinking the cube fires the capture earlier. But *which face*, *by how much*,
and *how much margin is left* are not things to guess at with a camera — too
small and you trigger with the gripper still in frame, and the failure mode is
a phantom pick on air.

So: log where the TCP actually is at the instant `_bStartFoV` drops, and how
fast it is leaving.

## What gets logged — line I, seven fields

```
RAIV/CSV,I,<seq>,<exitX>,<exitY>,<exitZ>,<velX>,<velY>,<velZ>,<mismatch>
```

Positions are the TCP relative to the cube's **origin corner**, on world axes,
in mm. Velocities are mm/s over the 0.2 s before the exit, from a rolling
10-sample ring at the existing 20 ms poll.

That is all you need for the sizing arithmetic: **move a face in by N mm and
the capture fires N / |velocity on that axis| seconds earlier.** Everything
else is done offline.

Line I is its own line rather than seven more fields on H — H is already 16
fields and is the batch/speed/grip/latency line, and this is a measurement for
one experiment that should be removable without disturbing anything that
outlives it. It is emitted **only while `bCaptureOnFovClear` is true**, so it
costs nothing when the experiment is off.

## Why the numbers can be trusted — and how you'll know if they can't

`monitorArea`'s `fCube` is `access="private"`, so the cube frame cannot be read
across the library boundary, and adding an accessor means editing a
Stäubli-supplied library to take a measurement. So this reproduces the test
from public data instead:

`createCube` anchors the cube **at** `pStartCnvyrFoV` — it is a corner, not a
centre — and then zeroes the frame's rotation (`createCube.pgx` L59,
`fCube.trsf={x,y,z,0,0,0}`). So the cube is world-axis-aligned and membership
is `0<dx<835, 0<dy<835, 0<dz<1000`, which is precisely the three range tests in
`checkCube.pgx` L41–51.

In world terms that box is **x −525…+310, y −1250…−415, z −236…+764**. The drop
sits at x +563, outside on the far X face, so the exit should be an X crossing
at x = +310 — and `exitX` ≈ 835 with a large positive `velX` will confirm it.

**Reproducing somebody else's geometry is exactly the kind of assumption that
reads plausible and is wrong**, and this one is about to be used to size a
change to that geometry. So the reproduction is checked against the flag it
models, every poll, and `nFovGeomMismatch` counts every disagreement. The
comparison is only made 20 mm clear of every face, so `tkCheckZone`'s own loop
lag at the boundary is not counted.

**`mismatch` must read 0.** If it does not, none of the resize arithmetic is
valid, and that is worth knowing before anybody moves a face.

## What to read off it

| field | expect | means |
|---|---|---|
| `exitX` | ≈ 835 | it exits on the far X face — that is the face to move |
| `exitY`, `exitZ` | well inside 0…835 / 0…1000 | those faces are not the constraint |
| `velX` | large, positive | mm/s; **835 − new X size, divided by this, is the time you buy** |
| `mismatch` | **0** | the geometry model matches the real flag |

Worked example with plausible numbers: if `exitX` reads 838 and `velX` reads
600 mm/s, then pulling the X face in from 835 to 600 mm fires the capture
(838−600)/600 ≈ **0.40 s** earlier — which is the whole remaining vision wait,
and would put the blend back in reach.

Whether 600 mm is still clear of the camera is a question for the optics, not
for me. What this gives you is the exchange rate.

## Verification

`verify.py` **PASS (0 fail, 6 warn)** · `mutate.py` **79/79 caught, 0 missed**.

New §7k and §11, twelve new mutations. The properties asserted are about the measurement
being honest, not about it working:

| | |
|---|---|
| a | **the cube constants are pinned.** 835×835×1000 at `pStartCnvyrFoV` is hard-coded in three places — the margins in `Part_Accept`, the line I header, and the note in `parse_backups.py`. Resizing the cube in `tkCheckZone` — the very change this exists to inform — now **fails the suite** rather than silently invalidating all three. It also checks `pStartCnvyrFoV` is still the *first* cube created, since `_bStartFoV` is `fCube[0]`. |
| b | the self-check exists, increments on **both** arms, and has a margin |
| c | **nothing branches on any of the seven values** — a measurement that becomes a gate is a behaviour change wearing instrumentation |
| d | each is written only in `Part_Accept` |
| e | the velocity divide is guarded against a zero age, and all three are zeroed first so a pick that never waited cannot republish the previous pick's velocity |
| f | line I is gated on the toggle, its field order is fixed, and the FORMAT header documents it |

### The compile error, and the check that should have caught it

**`fmod` does not exist in VAL3.** I used `fmod(l_nFovN,10)` to wrap the ring
index and the controller rejected it: *"'fmod' : undefined function",
Part_Accept.pgx line 117*. The index is now wrapped with an explicit
`if l_nRing>9 / l_nRing=0`, which is what the language actually offers.

The part worth fixing was not the line, it was **why the suite was green**.
`BUILTINS` in `verify.py` is a hand-maintained allow-list, and section 2 uses
it to decide a symbol needs no declaration — so a name that is in `BUILTINS`
but is *not* a VAL3 function turns that check into a rubber stamp for exactly
the identifier it should have caught. `fmod` had been sitting in that list
since long before this bundle.

New **§11** closes it: a function call in a bundle must either already appear
somewhere in the original application — code that demonstrably compiles on this
controller, the Stäubli libraries included — or be listed in `UNPROVEN_OK` with
where its existence was confirmed. Guessing at an API from another language is
what went wrong, so "it is obviously standard" is not accepted as a reason.
Re-adding `fmod` to `BUILTINS` and using it now fails with a message naming
this incident. The check immediately paid for itself in a second way: it
flagged `setMonitorSpeed` as a stale `UNPROVEN_OK` entry, because the original
application does call it.

**A second gap the mutation suite found.** Changing the wrap from `>9` to `>10`
writes index 10 into a size-10 array, and *nothing* in the suite saw it — the
index is a variable, so no static bounds check can reach it. §7k(b2) now reads
the four buffers' declared size out of the `<Locals>` block and requires the
wrap test to agree with it. Out-of-bounds on a live controller is not a wrong
number; it was worth a check of its own.

### A repair, recorded

Adding the geometry block broke §7j(c) — the stand-down re-test check searched
from the `while` line for `if _bStartFoV==false`, and the new self-check has
exactly that line inside the loop body. It matched the wrong one and reported
every guard term as missing. Caught, and loudly, but it is the same
wrong-window mistake this suite has made twice before. The search is now bounded
by the `endWhile` that closes the block, not by a landmark that can recur.

Also: `position` was missing from the builtins list, so the suite briefly
reported it as an undeclared symbol.

## Not verified — nothing here compiles or runs

- the seven new `.dtx` globals resolve, and the four size-10 `num` locals are accepted
- `fmod` is available for the ring index
- `here(tSchunkEMH084,world).trsf.x` and `position(pStartCnvyrFoV,world).x`
  are the right member paths — this is the first place in the project that
  reads `.trsf` components off a live `here()`

## Test it

1. Deploy, turn **Capture @ FoV** on, run 25 picks.
2. Check `mismatch` is **0**. If it is not, stop — the rest of the numbers mean
   nothing and I need to look again at the frame.
3. Read `exitX` / `velX`, work the exchange rate, and decide with whoever knows
   the camera's field how far the X face can safely come in.
4. Cycle time should be unchanged from run 15's 3.75 mean — this adds a handful
   of reads inside a poll loop that was already spinning.

## Back out

Copy the three files from `_original/` back over the application. Or just
switch the toggle off: with `bCaptureOnFovClear` false none of this executes
and no line I is logged.
