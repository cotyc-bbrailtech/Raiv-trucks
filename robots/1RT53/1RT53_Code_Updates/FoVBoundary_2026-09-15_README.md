# Raiv-T1 — move the APERA FoV boundary from +310 to +550

**Six files**, built on `Y-2026_M-09_D-11_14h40m`. `_original/` is byte-identical
to what is on the controller now.

| file | on controller | this build | diff |
|---|---:|---:|---|
| `tkCheckZone.pgx` | 7,863 | **10,531** | +41, −2 |
| `Part_Accept.pgx` | 23,801 | **24,509** | +14, −3 |
| `tkCycle.pgx` | 76,325 | **79,712** | +63, −5 |
| `tkBeltScan.pgx` | 35,224 | **35,840** | +10, −2 |
| `LogCycleCSV.pgx` | 32,356 | **33,302** | +15, −1 |
| `binpick_TiePlates_TEST.dtx` | (55,393) | **55,987** | 3 declarations added, **1 taught point moved — declared** |

**This supersedes `LastPartThreshold_2026-09-11` and contains it.** That bundle
was never deployed, so its `nLastPartThreshold` tunable (ships at 1, inert)
rides along here. Deploy this one instead.

**This one is NOT behaviour-neutral.** Every bundle before it shipped inert. This
moves a monitored-zone boundary, on your measured number, and it changes when
the capture fires and when the belt trigger fires the moment it is deployed.

---

## What changes

```
                       before            after
  "IN the APERA view"   x -525 .. +310    x -525 .. +550
  "PAST the view"       x +310 .. +910    x +550 .. +910
```

One boundary, moved 240 mm downstream. `nStartFoVX_mm` 835 → **1075**, and
`pEndCnvyrFoV.x` 310 → **550** so the two zones still meet exactly.

## Why — and I had the cubes wrong twice before getting here

`tkCheckZone`'s own original comments say what these two cubes are, and they are
right:

```
//APERA IN Field of View        -> pStartCnvyrFoV  -> _bStartFoV
//APERA OUT Field of View       -> pEndCnvyrFoV    -> _bEndFoV
```

They are not two halves of the field of view, and the END cube is not the drop
station — I wrote both of those into shipped comments and this bundle corrects
them. They are *in view* and *past the view*, meeting at one boundary, and
everything that waits for a clear shot waits for `_bStartFoV` to go false there.

**The boundary was 240 mm too early.** You measured the gripper and its plate
clearing the camera at about **+550**; the flag went false at **+310**. For that
240 mm the flag said "clear" while the camera could still see the plate on the
magnet, and every capture taken in that window images the held plate as a plate
on the belt.

The recordings agree. At capture positions x = 326…443 the pick pipeline reports
an unpickable plate on **103 of 105 frames**, including frames **111 and 137**
where the belt was provably empty and the count still came back **1**. Stereo
disparity on frame 111 puts that object 0.39 m from the camera against 1.10 m
for the belt — **0.71 m up in the air**, on the magnet.

That phantom is what keeps `nCountPlatesFound` off 0, which stops `bLastPart`
arming the early belt kick, which sends **34 of 63** belt advances through
Branch B at 3.36 s each: **+0.56 s on every pick.**

## What it will do to the cycle

Two gates wait on `_bStartFoV`, and both now wait 240 mm longer — about
**0.34 s** at the measured 700 mm/s:

- **`tkBeltScan`'s early trigger.** This is the win. It currently fires 26 times
  a run with the gripper still in shot; those captures were contaminated. It now
  fires clean. The wait is overlapped with the place motion, so the 0.34 s
  should cost nothing.
- **`Part_Accept`'s Capture @ FoV.** It now fires 0.34 s later, which removes
  what little advantage it had. It measured −0.07 s (p = 0.18) on steel already.
  **Leave it off.** The toggle ships as it is.

## The change verifies itself

`nFovGeomMismatch` compares Part_Accept's model of the cube against the real
`_bStartFoV` flag on every 20 ms poll, and it has read **0 on every sample since
it was built**. If the new geometry is not what I think it is, that counter goes
non-zero on the first run and the log says so. Read it first.

The X margins in `Part_Accept` are now **derived** from the same `nStartFoVX_mm`
that `tkCheckZone` builds the cube with, rather than being the literals 815/855.
A mutation checks that; two numbers that must agree should not be typed twice.

**`nStartFoVX_mm` is read once, at task start.** Changing it from the data editor
does not resize a cube that already exists — restart the application. If you
change it and do not restart, the self-check disagrees with the flag and
`nFovGeomMismatch` counts every poll, which is the log telling you rather than
the numbers quietly rotting.

## Verification

`verify.py` **PASS (0 fail, 5 warn)** · `mutate.py` **128/128 caught, 0 missed`.

§10 stopped this bundle until the taught-point move was declared — a `pointRx`
changing under a deploy is the exact defect that cost you `mReach` and the tool
definition in September, and the check worked. `pEndCnvyrFoV` is now in
`INTENTIONAL` with the value it changes from, so a stale entry fails loudly.

§7k's pin changed shape rather than being loosened. It used to require the
literal `835,835,1000` — which is precisely the change this bundle had to make.
It now pins Y = 835 and Z = 1000 as literals, requires X to be the tunable, and
adds **§7k(a3): the two zones must meet.** Move one half of the boundary without
the other and the suite fails, naming the gap. Six new mutations, four older ones
retargeted because their text moved.

**`fov_exit_x` from runs before this deploy is against an 835 mm face and is not
comparable with later runs.** `parse_backups.py` now says so in the line-I note.

## Not verified — nothing here compiles or runs

- the three new `.dtx` globals resolve, and `l_nXIn` / `l_nXOut` are accepted
- `createCube` takes a global rather than a literal for its X argument — same
  type, but this is the first call in the project that passes one
- the two log strings no longer say "drop station"; check they read sensibly on
  the pendant

## Test it

1. Deploy, **restart the application** (the cube is built at task start).
2. Run 25 picks. **Read `fov_geom_mismatch` first** — it must be 0. If it is
   not, stop: the cube is not where I think it is and nothing downstream is
   trustworthy.
3. Check `plates_found` now reaches **0** when the belt empties. That is the
   whole point, and it has never happened in 2,600 logged picks.
4. Expect the Branch B rate to fall from one pass per ~6 picks, and
   `last_part_armed` to start climbing. Cycle should move toward ~4.0 s.
5. Send the backup.

If `plates_found` still never reads 0, the boundary needs to go further than
+550 — raise `nStartFoVX_mm` and move `pEndCnvyrFoV.x` with it, or wait for the
`BeltFill` search region, which fixes it from the vision side regardless of
where the arm is.

## Back out

Set `nStartFoVX_mm` back to **835** and `pEndCnvyrFoV.x` back to **310**, then
restart — that is the old geometry exactly. Or copy the six files from
`_original/`.
