# 1RT53 (Raiv-T1) — backup `Y-2026_M-10_D-12_14h07m`

Controller `F_24_0064095_C_004`. First backup since 22 Sep. Running app is
`binpick_TiePlates_BeltSensor` on every one of the nine sessions in it.

---

## Read this first: the log rolled

This archive's `mnt/log/user.log` starts at **2026-10-07 12:58** and ends
2026-10-12 13:48. It is 3,466 entries, not the ~4,400-and-climbing cumulative
history the README describes.

The retained window no longer reaches back past 7 Oct, so **older backups are
no longer redundant** — they are now the only copy of everything before that
date. The README's warning ("watch for the total to stop climbing; that is the
roll") has come true. Nothing was lost here, because the pre-existing CSVs
already hold 22 Sep and earlier, but from now on a missed backup is a
permanently missing window.

---

## Production rate: 4.50 s, from 210 belt-fed picks

| | 22 Sep run 2 | **this backup** |
|---|--:|--:|
| belt-fed picks | 96 | **210** |
| median cycle | 4.63 s | **4.50 s** |
| segment sum | 4.47 s | **4.43 s** |
| unaccounted | 0.15 s | **0.07 s** |
| FoV declines | 0 | **0** |
| runaway stops | 0 | **0** |

Four belt-fed sessions, consistent with each other:

| session | picks | median | Branch B | belt starts | nudges |
|---|--:|--:|--:|--:|--:|
| 07 Oct 12:58–13:10 | 77 | 4.55 s | 36 | 42 | 21 |
| 07 Oct 14:32–14:37 | 59 | 4.47 s | 6 | 29 | 3 |
| 08 Oct 09:55–10:05 | 50 | 4.54 s | **0** | 23 | 0 |
| 08 Oct 13:12–14:51 | 24 | 4.38 s | 1 | 8 | 0 |

**The cell settled down across the two days.** Branch B went 36 → 6 → 0 → 1 and
belt nudges 21 → 3 → 0 → 0. The first session shows the starved shape — 42 belt
starts against only 20 beam-break edges, i.e. the belt kept starting and
delivering nothing. By the third session that is gone.

Zero runaway stops, zero sensor chatter, zero FoV declines and zero
`no_pick_on_beam` across all 210 picks.

### Where the 4.50 s goes

| segment | median |
|---|--:|
| retreat | 1.33 |
| place + return | 0.82 |
| approach | 0.63 |
| linear approach | 0.62 |
| gripper | 0.50 |
| vision wait | 0.53 |
| **sum** | **4.43** |
| **median cycle** | **4.50** |

0.07 s unaccounted — down from 0.15 s on 22 Sep, and effectively zero. The cycle
is fully explained by its segments. APERA latency is 1.34 s median against a
0.53 s vision wait, so most of the planning is still hidden under motion.

4.50 s is **13.3 plates/min** against the 20 plates/min (3.0 s) goal. Retreat is
still the largest single segment, as it was in September.

---

## The 3.65 s block on 8 Oct is not a production number

Between 09:24:51 and 09:35:58 the log carries 81 picks at a median of **3.65 s**,
p90 3.72 s, best 2.59 s. That looks like the breakthrough. It is not. Four
independent signals say the cell was running dry:

1. **The belt never moved.** `belt_master_starts` held at 5 for all 81 picks,
   `beam_break_edges` held at 25, `belt_start_holds` held at 7.
2. **No plate was ever released.** `drop_part` reads 0 on all 81 picks, against
   170 of 210 on the belt-fed picks either side of it.
3. **The pick was somewhere else.** `tcp_lift_mm` is **−145 mm** through the
   block against +180 to +220 either side — below the belt pick reference, not
   on the belt.
4. **Vision was failing throughout.** All 172 `Image capture error` entries and
   92 `Cannot follow trajectory` warnings in this archive fall inside this
   window, starting with *"The provided pipeline id `Pick_IdsBelt_new` does not
   exist"* at 09:21:09.

So the robot cycled through a fixed low position with no plates, no belt and no
working vision. **3.65 s is the motion-only floor of the cell** — a useful
number, and the first clean measurement of it, but it is not a pick rate. It is
the same trap as the 3.87 s rubber-plate figure from 11 Sep.

Worth noting what it implies: with retreat at 0.58 s and linear approach at
0.17 s in that block against 1.33 s and 0.62 s in production, **1.2 s of the
production cycle is lift height and approach distance**, not vision and not the
belt.

---

## Three things that need you

1. **`nBeltRunMax_s` is still 0.** The runaway cap has been off since 22 Sep.
   At 0 a sensor frozen "clear" runs the conveyor indefinitely with nothing to
   stop it. Set it to ~180 unless you are still commissioning.
2. **`sPipeline` is saved as `Pick_IdsBelt_new`, and APERA rejected that name**
   on 8 Oct at 09:21. It evidently works now — the later sessions picked
   normally — but the saved value and the APERA pipeline list disagreed once,
   and a restore of either side will reproduce it.
3. **8 min of 12 Oct ran with zero picks.** Three app starts between 13:28 and
   13:48, no cycles logged, and an `ERR 70` / *"Userpage: Page not found"* pair
   out of the HMI at 13:35. That HMI error class has 263 lifetime occurrences,
   so it is long-standing, not new — but it is worth knowing the 12 Oct run
   produced nothing.

## Closed out

**The settle delays are not costing time.** `nPartsSettle` (1.0) and
`nBranchBSettle_s` (0.5) are still in the deployed `tkCycle`, and the change I
offered on 22 Sep was never built. It no longer matters: unaccounted time on
the production path is 0.07 s/pick, so those delays are not on the hot path.
My original "next 0.5–1.0 s" estimate was wrong, and the corrected 0–0.15 s is
now measured at roughly zero. Nothing to do here.

## Unchanged, and still wrong

Grip sensors. `grip_part` 0 of 291 and `grip_mag` 0 of 291 — same polarity or
terminal problem as September, untouched. `drop_part` does work (170 of 210
belt-fed picks), so the fault is specific to those two inputs.

---

## What changed in the pipeline

`parse_backups.py` only knew CSV lines A–H, and only the first 8 fields of H.
The deployed build emits **A–H, K and L**, with H grown to 15 fields. Everything
past field 8 of H, and all of K and L, was being dropped silently.

Added, by the field order documented in the deployed `LogCycleCSV.pgx`:

- **H, fields 9–15** — `grip_part`, `grip_mag`, `drop_part`, `apera_latency_s`,
  `cap_fov_clear`, `cap_fov_decline`, `fov_wait_s`
- **K** (14 fields) — the Branch B breakdown (`br_passes`, `br_total_s`,
  `br_travel_s`, `br_detect_s`, `br_settle_s`, `br_traj_s`, `br_tries`,
  `br_plates`, `br_total_all_s`), plus `loop_top_wait_s`, `loop_top_count`,
  `last_part_thr`, `count_at_arm`, `last_part_armed`
- **L** (17 fields) — the sensor-only belt master, `belt_master_state` through
  `belt_start_holds`
- **I** and **J** — defined but not present in this archive; the build emits
  them only while `bCaptureOnFovClear` / `bStallSample` are set

Fields were appended, never inserted, so every existing column keeps its
meaning. `cycles_ALL.csv` goes from 68 to 122 columns; the 2,995 earlier rows
read blank in the new ones, which is honest — those builds did not emit them.

**`backups/` is empty.** Every backup directory under
`Metrics_1RT53_F_24_0064095_C_004/backups/` is a 0-byte stub as of 5 Oct, so
`parse_backups.py` can no longer regenerate the history — it would rebuild the
CSVs from whatever single backup is present and silently drop everything else.
This run therefore parsed the new backup on its own and **merged** its rows onto
the existing CSVs rather than re-running the pipeline. Before the next backup,
either repoint `backups/` at the real folders under
`1RT53/1RT53_Staubli_Backups/F_24_0064095_C_004/` or give the parser a manifest
of external paths, so a full re-run stops being destructive.

Merged totals: **3,287 picks across 23 backups**, 358 run sessions.
