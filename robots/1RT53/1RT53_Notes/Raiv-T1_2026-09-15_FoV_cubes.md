# Raiv-T1 — the FoV cubes, and why no cube adjustment gets the arm out of frame

Answering: *"adjust end_FOV in Stäubli so the robot arm is truly NOT in the
APERA camera FoV."*

Short version: **the cubes are wrong, and fixing them will not do what you
want** — because there is no point in the current cycle where the arm is out of
that camera's view. Measured, below.

---

## 1. What the two cubes actually are

`tkCheckZone` L16–18, with the points out of the live `.dtx`:

```
createCube(pStartCnvyrFoV, 835, 835, 1000)   anchor (-525,-1250,-236)
createCube(pEndCnvyrFoV,   600, 800, 1030)   anchor ( 310,-1250,-250)
```

`createCube` anchors at the point (a corner) and zeroes the rotation, so in
world mm:

| cube | flag | x | y | z |
|---|---|---|---|---|
| START | `_bStartFoV` | **−525 … +310** | −1250 … −415 | −236 … +764 |
| END | `_bEndFoV` | **+310 … +910** | −1250 … −450 | −250 … +780 |

**They tile.** They share the face at x = +310 and together cover x −525…+910.
The names say it plainly — *Start* Conveyor FoV and *End* Conveyor FoV. They are
the two halves of one camera's field of view.

## 2. The false premise, and it is mine

`tkBeltScan` L98, in shipped code:

> `_bEndFoV` is deliberately NOT checked: that is the cube over the drop /
> reject station, where the robot is SUPPOSED to be during this scan.

That is wrong. The END cube is the **downstream half of the conveyor FoV**. It
happens to contain the drop station (x +563) as well, which is how I talked
myself into it. `tkCycle` logs the same error to your screen twice:

```
"capture with arm inside the END (drop station) FoV cube"
```

So the gate in `Part_Accept` — and the early-trigger gate in `tkBeltScan` — wait
only for `_bStartFoV` to clear and then treat the arm as out of shot. It is not.
It has just crossed into the other half.

`nFovHitEnd` = 66–79 and `nFovHitStart` = 0. That diagnostic has been reporting
this the whole time; I read it as a drop-station curiosity.

## 3. Why moving the capture does not help — the measurement

Every capture in run 20, grouped by where the TCP actually was:

| capture position | n | mean reported | mean pickable | **phantom offset** | min count |
|---|--:|--:|--:|--:|--:|
| x ≈ 340 — cube exit (Capture @ FoV **ON**) | 76 | 4.38 | 3.13 | **1.25** | 1 |
| x ≈ 440 — mid | 29 | 3.55 | 2.48 | **1.07** | 2 |
| x ≈ 630 — drop approach (Capture @ FoV **OFF**) | 75 | 4.08 | 3.03 | **1.05** | 2 |

**The phantom is present at every position, essentially undiminished**, from
326 mm to 670 mm — the full span the cycle uses. All 180 captures are inside the
END cube. At the drop approach, 320 mm past the START cube's far face, the held
plate is *still* being detected.

There is no capture point in the current motion path where the arm is out of
that camera's view. Even `jApera_Trigger_pos` — the pose taught as "out of
shot", used by the empty-scene path — sits inside the END cube, which is why
`nFovHitEnd` keeps firing there.

So: **no resizing of END, and no moving of the capture, removes the phantom.**
Only the search region does, because it makes the arm's presence irrelevant
rather than trying to avoid it.

## 4. What I would actually change

**First: `BeltFill`.** Unchanged from the last note, and this measurement is the
argument for it. The plate is 0.71 m above the belt; a search region shaped
around the belt excludes it with a large margin, wherever the arm happens to be.

**Second: stop the flags lying.** Three things, all cheap:

- correct the two log strings — they say "drop station" and mean "downstream
  conveyor". You read those messages; they should not mislead.
- correct the `tkBeltScan` L98 comment and the matching note in `Part_Accept`,
  because the *reasoning* is what future edits will lean on.
- optionally a tunable, shipping off, that makes the Capture @ FoV gate require
  **both** cubes clear. Be aware what that does: the arm never leaves both
  cubes before the drop, so the wait would run to `nFovClearTimeout_s` every
  cycle. It is only worth having as a way to prove the point, not to run.

**Do not resize the START cube.** Three programs read `_bStartFoV` — `clickAbort`,
`tkBeltScan`, `tkCycle` — and `verify.py` §7k pins 835 × 835 × 1000 at
`pStartCnvyrFoV` deliberately, because the FoV-exit arithmetic that produced
`fov_exit_x` and `fov_vel_x` depends on it. Resizing it silently invalidates
that whole measurement series.

**And turn Capture @ FoV off.** It measured −0.07 s, p = 0.18 on steel, and we
now know precisely why it could never work as designed: it fires the instant the
arm crosses x = +310 into the other half of the same camera's view.

## 5. The number you would need, and how to get it

If you do want the cubes to describe the camera honestly, the missing figure is
**how far in +x the camera can still see a held plate.** This data gives a lower
bound of 670 mm and no upper bound — every capture we have is inside the view.

Five minutes at the cell gets it: hold a plate on the magnet, jog along +x in
50 mm steps from 300 to 1000, and read the APERA count at each step. The x where
the count drops by one is the true edge of the view. Then the cube can be set to
that, and `_bStartFoV`/`_bEndFoV` will mean what they say.

Worth doing regardless of `BeltFill`, because `tkBeltScan`'s early trigger is
gated on the same flag and is firing 26 times a run with the arm in view.
