# Lab_platesorter4 — built from the production pull

**Date:** 2026-09-30 · **Cell:** `B&B LAB` / controller `Lab Test` · **Robot:** `F_24_0060113_C_001`

Built from `B&B LAB 09302026.zip` — your live `usr/usrapp/LAB_PlateSorter2`, not from a backup.

---

## ⚠ Delete the existing `Lab_platesorter4` folder before extracting

`usr/usrapp/Lab_platesorter4` in the cell you sent is **four of my builds unzipped on top of one
another**. Rev A and B put the driver in `VAL3apera3/`; rev C and bisect A put it in
`VAL3aperaNEW/`. Unzipping never removes files, so the folder now holds all of them at once:

| Folder | Files present | Files it should have |
|---|---|---|
| `VAL3aperaNEW/` | **44** | 35 (original) or 32 (rev C) |
| `VAL3apera3/` | 31 | should not exist in rev C at all |
| whole application | **158** | ~116 |

That `VAL3aperaNEW/` is the union of the apera3 programs *and* the original driver's leftovers —
`apera_follow_trajectory`, `apera_calibrate`, `apera_wait_for_*`, `apera_trigger*`,
`apera_binpick_auto`, `apera_miscal_check`. On its own that is enough to explain why rev C and
bisect A both failed, and it means **bisect A never actually tested what I designed it to test.**

So, before extracting:

1. Close SRS.
2. **Delete** `Lab Test\usr\usrapp\Lab_platesorter4` entirely.
3. Extract this `Lab_platesorter4/` folder in its place.
4. Open SRS.

`LAB_PlateSorter2` is untouched and remains the fallback.

## What the production pull settled

**Both patch bundles are live and loading.** Production `LAB_PlateSorter2` contains
`bTskSelected["Abort"]=true`, the Stow `REFUSED` log, `setMoveId(750)`, `ToolOnSec`, `HoldSec` and
the `Grp*` phase keys. My suspicion that `ToolDwell_PhaseGroups` had never loaded was wrong — good
thing you sent this before I "fixed" a bundle that was fine. B2 and B3 in the bisect folder are
now pointless; ignore them.

**No application in the workspace carries a `.ltx` file — zero across all twelve.** The `.ltx` is
a controller-side extern cache that only appears in robot backups. Every build I shipped included
one, hand-edited in rev A and rev B. This build has none, which matches every application in your
cell.

**Production is `backup + both bundles`, exactly as I assumed.** 35 of 45 application files are
byte-identical to the 15h07 backup; the 10 that differ are precisely the bundle files. So the
content baseline was right — the packaging was not.

## What this build is

The production application, **byte-for-byte**, with eleven files changed:

| File | Change |
|---|---|
| `Lab_platesorter4.pjx` | renamed; `<Data file>` updated; libraries rewired |
| `Lab_platesorter4.dtx` | **renamed only — byte-identical to production** |
| `PartPick`, `tkPartFinder`, `Apera_TestPipeline`, `tkRoCAL` | 19 call sites `apera2:` → `apera3:` |
| `Init.pgx` | `clearBuffer(Apera:sAperaConn)` → `clearBuffer(apera3:sAperaConn)` |
| `interface/BASIC.bindings.json` | callback `apera2:apera_setup_cap` → `apera3:…` |
| `tkMetrics.pgx` | comma removed from the ABORT state string (it splits the D1 CSV row into 15 fields); header comment |
| `tkScreenHmi`, `LogLine`, `LogMetricsHdr` | comment text only |

The other 34 files are untouched production bytes, including `interface/`, `RaivLog/` and
`.outlining.json`.

**Libraries:** `apera3` → `./VAL3apera3/apera3.pjx`, and `RaivLog`. The two stale Apera libraries
are gone — `apera/` (the 2024 driver, referenced once by that `clearBuffer`) and `VAL3aperaNEW/`
(superseded). One Apera driver, as you asked.

## The apera3 library

`VAL3apera3/` — Apera's driver with `apera3.pjx` + their own `apera3.dtx`. It registers the same
23 programs your `apera2.pjx` registered, all present in apera3, plus the four new multi-candidate
entry points (`apera_trig_a`, `apera_trigtrj_a`, `apera_waitpck_i`, `apera_waittrj_i`). Apera's two
new *sample* programs are on disk but unregistered, the same way your current library leaves
`apera_binpick_auto` and the long-name duplicates unregistered.

### Four site carry-forwards (marked `// SITE CARRY-FORWARD`)

Your apera2 library is **not** stock. These had to come across:

**(a) `apera_exec_traj.pgx` — cycle time.** Stock apera3 calls `waitEndMove()` after *every*
trajectory section. `PartPick` calls it for `LINEAR_APPROACH` and `LINEAR_RETREAT`; blocking on the
retreat destroys the blend into the place move. Restored to your conditional form.

**(b) `apera_calib_prg.pgx` — link break + reach risk.** Stock takes **no parameter** and hardcodes
`sPipeline = "changeme"`, but `tkRoCAL:14` calls it with `sCamPair`. Stock also sweeps J1/J5/J6 by
50/25/25° against your 35/15/20°. Both restored.

**(c) `apera_inspect.pgx` — signature.** Stock declares its two reference arrays `size="50"`; yours
declares them open. Restored to open.

**(d) Five empty `<Parameters>`/`<Locals>` elements stripped** — `apera.pgx`, `apera_debug_tcp.pgx`,
`apera_setup_cap.pgx`, `apera_send.pgx`, `start.pgx`. There is not one empty element of either kind
anywhere in your cell; apera3 writes them for parameterless programs. No semantic change.

## Validation

- 67 XML files parse; BOM correct on every `.pgx`/`.dtx`/`.pjx`, absent on `interface/`
- 32 application and 27 library programs registered, all present; `Data file` resolves
- 18 cross-library and 76 intra-library calls resolve with matching argument counts
- every `taskCreate` target exists and takes no arguments
- every identifier resolves to a local, parameter, dictionary entry, program or VAL3 builtin
- **full link-graph diff against the production application**: equivalent (only a parameter *name*
  differs, which VAL3 binds positionally)
- zero empty `<Parameters>`/`<Locals>`; no `.ltx`

**0 errors, 0 warnings** — and this time the control was your live application rather than another
of my builds.

## First run

1. `Apera_TestPipeline` before `tkCycle` — it triggers, waits and inspects, commands no motion and
   touches no belt output.
2. Then a reduced-speed dry cycle. Leave `bEarlyBeltKick` **false** so you are testing one variable.
3. Do not run RoCal unless you intend to recalibrate — `apera_calib_prg` sweeps the arm.

## Next

The multi-candidate path is registered but unused — one trigger returning every part in the FOV.
Measured `b_vision` is 0.002–0.116 s/plate against a 1.29–1.65 s camera mean, so the win is not
faster vision, it is deleting whole round-trips. It changes `tkPartFinder`, `PartPick` and the
belt-kick interlock, so it belongs in its own measured patch once this is running. `jATraj[250]`
and `nATrajSect[4]` are single-slot globals — a multi-candidate loop must consume each trajectory
before fetching the next index.
