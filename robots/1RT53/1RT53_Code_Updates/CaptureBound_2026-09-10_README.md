# Raiv-T1 — a tunable capture bound, and what run 16 measured

**Five files**, built on `Y-2026_M-09_D-10_13h53m`. `_original/` is byte-identical
to what is on the controller now.

| file | on controller | this build | diff |
|---|---:|---:|---|
| `Part_Accept.pgx` | 20,561 | **23,801** | +57, −2 |
| `LogCycleCSV.pgx` | 29,065 | **29,231** | +4, −1 |
| `interface/UserPageOptions.html` | 15,575 | **16,364** | +4, −0 |
| `interface/UserPageOptions.bindings.json` | 5,748 | **6,088** | +16, −0 |
| `binpick_TiePlates_TEST.dtx` | (54,769) | **55,032** | 2 declarations added, no value changed |

The two removed `Part_Accept` lines are the wait condition and the trigger gate,
both restructured below. Nothing else is touched.

**Ships inert.** `nCapFovX_mm` defaults to **9999** — a position nothing is ever
at — so the wait ends exactly where it does today.

---

## What run 16 measured

61 picks, and the geometry reproduction agreed with the real flag on **all 42
samples: `mismatch` 0**. So the numbers are good.

| | value | spread |
|---|---:|---|
| `fov_exit_x` | **849 mm** | 846–856 |
| `fov_exit_y` | 426 mm | 426–427 |
| `fov_exit_z` | 295 mm | 291–296 |
| **`fov_vel_x`** | **+669 mm/s** | 633–685 |
| `fov_vel_y` / `fov_vel_z` | −126 / −267 | |

Exactly the predicted picture: the arm leaves through the **far X face** (849
against a 835 bound), with Y and Z several hundred mm clear of their faces. So X
is the only axis that matters, and the exchange rate is **669 mm/s**.

| pull the bound to | saves | vision wait left |
|---:|---:|---:|
| 750 mm | 0.15 s | 0.30 s |
| **700 mm** | **0.22 s** | 0.23 s |
| 650 mm | 0.30 s | 0.15 s |
| 600 mm | 0.37 s | 0.08 s |
| 548 mm | 0.45 s | 0.00 s |

## Why this is not a change to the cube

My last note said "shrink the conveyor FoV cube". **That would have been a
mistake and I want to correct it before you act on it.** `_bStartFoV` is not
ours — `clickAbort`, `tkBeltScan` and `tkCycle` read it across eleven call
sites, and `tkBeltScan`'s belt-stop and early-trigger logic are built on it
meaning *the arm is over the conveyor*. Resizing that cube to buy cycle time
would silently change three other programs' behaviour.

So the bound is **separate and applies to this one wait**. The cube, the flag,
and everything reading it are untouched. The arithmetic is the same
reproduction run 16 validated 42 times against the real flag — which is the
only reason it is trusted enough to gate a capture on.

The wait now has two legitimate exits, so "is the view clear" is computed
explicitly rather than read off one flag:

```
l_bFovClear=false
if _bStartFoV==false        -> l_bFovClear=true
if l_nDx>=nCapFovX_mm       -> l_bFovClear=true, and count nCapFovEarlyX
if l_bFovClear==true and bStart==true and bEndCycleRobot==false and bAbort==false
```

Both arms are set separately rather than combined into one `or`, so a mutation
cannot drop a term and leave a condition that still looks whole. All three
stand-down guards survive unchanged.

## How to sweep it, and how low is too low

Set `nCapFovX_mm` in the SP2 data editor — it is live, no reload. The Options
page shows it (`boundX`) and how many picks the bound actually bought anything
on (`earlyX`, counted only when the bound fires while the shared cube still
says "inside").

**Where the arm is**, extrapolated along the measured exit vector:

| bound | world x | world z | vs the plates |
|---:|---:|---:|---|
| 849 (today) | +324 | +59 | past the belt entirely |
| 750 | +225 | +86 | past the furthest plate pose (+97) |
| 700 | +175 | +112 | past it, 310 mm up |
| 650 | +123 | +139 | just past it, 340 mm up |
| 600 | +75 | +166 | **level with the plates** |

**Below about 650 the capture is being taken over the plate field.** I would
sweep 750 → 700 → 650 and stop there unless somebody who knows the camera says
otherwise — "downstream of the plates in X" is not the same as "out of frame",
because occlusion is about the line from the camera to the plate and I have no
model of where the camera is.

**How you'll see it go wrong.** An occluded capture shows up two ways, both
already logged: `plates_found` drops below 3, and the severity-3 APERA error
line fires. Watch both while sweeping.

## Where the cycle now stands

Run 16, 61 picks, toggle on, blend off — **3.87 s median, 3.83 mean**, and it
reproduces run 15's ON block exactly (3.88 / 0.41). From 4.81 at the start of
yesterday that is **−0.94 s a pick**.

What is left:

| segment | s | % | |
|---|---:|---:|---|
| retreat (lift + carry to drop) | 1.31 | 34% | real motion |
| approach + linear approach | 1.08 | 28% | real motion |
| **vision wait** | **0.45** | **12%** | **this bundle's target** |
| magnet on + off | 0.50 | 13% | rubber-plate test values, unvalidated on steel |
| descend | 0.31 | 8% | real motion |

62% is now productive motion. The vision wait is the last big non-motion block,
and after that the honest answer is that further gains need either the dwells
validated on steel or a look at the retreat and approach speeds — which I have
not touched and will not without you asking.

## Verification

`verify.py` **PASS (0 fail, 6 warn)** · `mutate.py` **88/88 caught, 0 missed**.

Nine new mutations. The bound-specific invariants: it ships at 9999; the wait
condition actually tests it (or the tunable is inert); `l_nDx` is seeded before
the loop that reads it; `l_bFovClear` is initialised false exactly once and set
true on exactly two named arms; the gate keeps all three stand-down terms; the
bound is never written by code; `nCapFovEarlyX` has one writer and it is an
increment.

### New §12 — interface files must be pure insertions

**The Options page has moved under me twice.** First `btn1_Copy1` from top 495
to 335; this time `btn1` and `btn1_Copy1` both up to the 124–126 band. Both
times my working copy was stale, and both times shipping it would have
**dragged your layout back to an older arrangement** as a side effect of adding
a readout. Both times it was caught by eyeballing a diff, which is not a check.

`_ctrl/interface/` now holds the controller's current page, and an interface
file in a bundle must be that file **plus added lines only** — zero removals,
zero rewrites. A stale page now fails with the offending line quoted.

### Two repairs

**A mutation caught by a crash.** Deleting half a binding object made
`verify.py` throw a `JSONDecodeError`, and the harness scored the non-zero exit
as "caught". Caught by a crash is not caught. JSON parsing is now defensive and
reports a malformed file as a clean failure — which matters beyond mutations,
since that file is hand-edited in SP2.

**A check that crashed on its own mutation.** Removing `l_bFovClear=false`
made an unguarded `.index()` raise. Guarded; it now reports the missing
initialisation.

## Not verified — nothing here compiles or runs

- `nCapFovX_mm` and `nCapFovEarlyX` resolve, and `l_bFovClear` is accepted as a
  `bool` local
- the two new Options readouts land where you want them

## Test it

1. Deploy, leave `nCapFovX_mm` at 9999, run 25 picks with **Capture @ FoV** on.
   Cycle should read 3.87 and `earlyX` should stay 0. That is the no-op check.
2. Set it to 750. Expect ~3.72, `earlyX` climbing with every pick,
   `plates_found` still 3, no APERA error line.
3. 700, then 650, same checks each time. Stop at the first sign of either.
4. If 650 holds clean, the vision wait is down to ~0.15 s and the blend
   (+0.33 s) is still not worth it — but a steel run to validate the dwells is.

## Back out

Copy the four files from `_original/` back, or just leave `nCapFovX_mm` at
9999 — the bound is inert and the `.dtx` changes no existing value.
