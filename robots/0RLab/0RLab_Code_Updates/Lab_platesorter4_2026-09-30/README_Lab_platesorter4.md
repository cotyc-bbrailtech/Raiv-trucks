# Lab_platesorter4 — complete SRS application

**Date:** 2026-09-30 (rev B — load fix) · **Cell:** Raiv-Lab · **Controller:** CS9 `F_24_0060113_C_001`
**Purpose:** roll the new Apera driver (`…\Staubli\apera3`) into the LAB_PlateSorter2
application and deliver it as a standalone, deployable SRS application named
`Lab_platesorter4`.

> **Rev B replaces rev A.** Rev A was refused with
> `invalid application: check program parameters in call() or spawn instructions.`
> Cause and fix are in §4.2b. Three files changed; nothing else.

---

## 1. What this is

A complete VAL3 application — 76 files, nothing to merge on your side. Import
`Lab_platesorter4/` into SRS, transfer to the controller, run `start`.

```
Lab_platesorter4/
  Lab_platesorter4.pjx / .dtx / .ltx      project, data dictionary, extern list
  32 × *.pgx                             application programs
  interface/  BASIC, DETAIL, LRC, PHASES  (.html + .bindings.json)
  RaivLog/    RaivLog.pjx + .dtx          retain library (unchanged)
  VAL3apera3/ apera3.pjx + .dtx + 29 pgx  NEW Apera driver
```

## 2. Baseline it was built from

| Source | Contributed |
|---|---|
| Backup `F_24_0060113_C_001 / Y-2026_M-08_D-31_15h07m` | the whole application |
| `StowSelect_Pick0_Fix_2026-08-31` | `tkAbort.pgx`, `MoveToStow.pgx`, `tkCycle.pgx` |
| `ToolDwell_PhaseGroups_2026-08-31` | `tTool.pgx`, `tkMetrics.pgx`, `tkScreenHmi.pgx`, `.dtx`, `interface/PHASES.*` |
| `…\Staubli\apera3` | the new driver, as `VAL3apera3/` |

The 15h07 backup predates both patch bundles (its `tkAbort.pgx` still lacks
`bTskSelected["Abort"]=true`, and `tTool.pgx` has no dwell booking), so the bundles
you confirmed working were overlaid on top of it. 59 of 76 files are byte-identical
to those sources; 17 were modified, listed in §5.

## 3. Library wiring — what changed

The old project loaded **three** libraries. Two of them were Apera drivers:

| Before | After |
|---|---|
| `Apera` → `./apera/apera.pjx` (stale, 2024 driver) | **removed** |
| `apera2` → `./VAL3aperaNEW/apera2.pjx` | **replaced** |
| — | `apera3` → `./VAL3apera3/apera3.pjx` |
| `RaivLog` → `./RaivLog/RaivLog.pjx` | unchanged |

The stale `apera` library was referenced exactly once, by
`Init.pgx: clearBuffer(Apera:sAperaConn)`. Both drivers link the same
`Socket\sAperaSocket` resource, so that call now reads `apera3:sAperaConn` and behaves
identically. The alias was renamed `apera2` → `apera3` in all 19 call sites
(`PartPick`, `tkPartFinder`, `Apera_TestPipeline`, `tkRoCAL`) plus one HMI callback
in `BASIC.bindings.json`. Zero `apera2:` or `Apera:` references remain.

The driver's own `apera.pjx`/`apera.dtx` were renamed `apera3.pjx`/`apera3.dtx` so the
project file basename matches its alias and cannot collide with any other Apera
library you load later.

## 4. Driver differences — and the three that would have bitten

The new driver is a superset of `apera2`: all 23 programs the old one registered are
present with compatible signatures, plus six new ones. Data dictionary is identical
(`sAperaConn`, `sPipeline`, `bAperaError`, `sAperaErrorMsg`, `jATraj[250]`,
`nATrajSect[4]`, `mSampleJMove`, `mSampleLMove`, `mNomSpeed`).

### 4.1 New capability — multi-candidate pipelines

| Program | What it does |
|---|---|
| `apera_trig_a(pipeline)` | trigger, process **all** candidates (`-a` flag) |
| `apera_trigtrj_a(pipeline, jStart, jEnd)` | same, with trajectory planning |
| `apera_waitpck_i(pipeline, group, &found, &pose, &poseTrans, &pickID, index)` | fetch candidate *N*'s pick |
| `apera_waittrj_i(pipeline, group, &found, &pose, &poseTrans, &pickID, index)` | fetch candidate *N*'s trajectory |
| `apera_binpick_a`, `apera_autoplt_a` | Apera sample programs for the above |

**Nothing in `Lab_platesorter4` calls these yet.** The cycle runs exactly the single-candidate
sequence it runs today. See §7 for why they matter.

### 4.2 Two site customisations carried forward

The deployed `apera2` library was **not** stock. Two edits in it had to be carried into
the new driver, or the application would have regressed or failed to compile. Both are
marked `// SITE CARRY-FORWARD` in the source with instructions for reverting.

**(a) `apera_exec_traj.pgx` — cycle-time regression.**
Stock apera3 calls `waitEndMove()` unconditionally after every trajectory section.
`PartPick.pgx` calls this program twice: `LINEAR_APPROACH` and `LINEAR_RETREAT`. Under
stock behaviour the retreat would block until the arm fully settles, destroying the blend
into the place move. Only `LINEAR_APPROACH` needs to settle (the gripper closes at the end
of it). Restored to the deployed conditional form.

**(b) `apera_calib_prg.pgx` — compile break + reach risk.**
Stock apera3 takes **no parameter** and hardcodes `sPipeline = "changeme"`. But
`tkRoCAL.pgx:14` calls `apera3:apera_calib_prg(sCamPair)` — one argument. Stock would fail
to link. Stock also sweeps J1/J5/J6 by 50/25/25°; the deployed library uses 35/15/20° for
this cell's envelope. Both restored.

### 4.2b Load failure on rev A, and the fix

Rev A was refused by the controller:
`invalid application: check program parameters in call() or spawn instructions.`

Cause: stock apera3 declares `apera_inspect`'s two reference-array parameters as
**fixed-size** — `size="50"` — where `apera2` declared them **open** (no size). The
application's extern list (`.ltx`) describes the open shape
(`string& x_sClassID[1][1][1]`), so the call no longer linked. The sizes were not the
problem — `sClassID[50]` and `nObjectCount[50]` in the dictionary match 50 exactly; the
*shape of the declaration* was.

Three changes in rev B, so the result is correct whichever side the loader treats as truth:

1. **`apera_inspect.pgx`** — `size="50"` removed from `x_sClassID` and `x_nObjectCount`,
   restoring the exact signature the application has linked against since day one. The body
   is untouched (it still initialises `0 to 49`, which is what the 50-element globals supply).
   This is site carry-forward **(c)**.
2. **`Lab_platesorter4.ltx`** — rev A hand-authored this file, which was a mistake. Rev B
   instead takes the `.ltx` that demonstrably loaded and changes *only* the alias strings
   (`apera2`→`apera3`, `alias="Apera"`→`alias="apera3"`). Nothing else differs, including
   the `l_pPoseTrans` parameter name and the `[1][1][1]` dimension notation. The invented
   `procedure apera3:apera_setup_cap()` entry is gone.
3. **`VAL3apera3/stop.pgx`** — stock apera3 marks the library's `stop` as `access="private"`;
   apera2 left it unqualified. Normalised to the unqualified form to remove the variable.

Nothing else in the application or the driver changed between rev A and rev B.

### 4.3 Everything else

Cosmetic only, and taken as Apera shipped it: comment fixes, re-indentation, explicit
empty `<Parameters>`/`<Locals>` blocks, `x_bParse` marked `use="value"` in `apera_send`,
and the reference parameter in `apera_wait_traj`/`apera_wait_pick` renamed
`l_pPoseTrans` → `x_pPoseTrans` (VAL3 binds positionally — no call site affected).
The one non-cosmetic change, `apera_inspect`'s fixed-size reference arrays, is covered
in §4.2b.

## 5. Files modified relative to the sources in §2

| File | Change |
|---|---|
| `Lab_platesorter4.pjx` | renamed; `Data file` → `.dtx`; libraries rewired |
| `Lab_platesorter4.dtx` | renamed only — content byte-identical |
| `Lab_platesorter4.ltx` | renamed; alias strings only (§4.2b) |
| `Init.pgx` | `clearBuffer(Apera:…)` → `clearBuffer(apera3:…)` |
| `PartPick.pgx`, `tkPartFinder.pgx`, `Apera_TestPipeline.pgx`, `tkRoCAL.pgx` | alias `apera2:` → `apera3:` |
| `interface/BASIC.bindings.json` | callback `apera2:apera_setup_cap` → `apera3:…` |
| `tkMetrics.pgx` | alias; **comma removed from the ABORT state string** (see §6); header comment |
| `tkScreenHmi.pgx`, `LogLine.pgx`, `LogMetricsHdr.pgx` | header/path comments renamed |
| `VAL3apera3/apera3.pjx` | `Data file` → `apera3.dtx` |
| `VAL3apera3/apera_exec_traj.pgx`, `apera_calib_prg.pgx` | carry-forwards, §4.2 |
| `VAL3apera3/apera_inspect.pgx` | open reference arrays restored, §4.2b |
| `VAL3apera3/stop.pgx` | `access` normalised, §4.2b |

The other 59 files are byte-for-byte identical to the backup and the two bundles.

## 6. One carried-over defect fixed

`tkMetrics.pgx` set `_sM["State"] = "ABORT - press Cycle, or Abort again to Stow"`.
That comma splits the D1 CSV row into 15 fields instead of 14 and breaks every
downstream parse of `raiv_metrics_*.csv`. Now reads
`"ABORT - press Cycle or Abort again to Stow"`. No behaviour change on the pendant.

## 7. Where the new driver could actually buy cycle time

Not a recommendation to change anything yet — just where to look, against the measured
baseline (5.106 s/plate actual, 2.965 s target, best clean cycle 3.51 s).

The measured vision loss is small: `b_vision` 0.002–0.116 s/plate against a camera mean
of 1.29–1.65 s, i.e. the capture is already hidden behind concurrent motion. So the gain
is **not** from faster vision — it is from *eliminating whole round-trips*.

`apera_trigtrj_a` + `apera_waittrj_i` let one trigger return trajectories for every part
in the field of view. With a full FOV the cell could plan once and pick 3–5 parts before
re-triggering, removing the per-part `apera_trig_traj` / `apera_wait_traj` pair and the
`jATraj` refresh from those cycles. That touches `tkPartFinder` (candidate index and
cache), `PartPick`, and the `bTrajectoryLOGIC` / belt-kick interlock, so it is a real
change to the hot path — worth a separate, measured patch after this driver is proven
running as a drop-in.

**Caution:** `jATraj[250]` and `nATrajSect[4]` are single-slot globals. A multi-candidate
loop must consume each trajectory before fetching the next index, or copy it out.

## 8. Validation performed

All automated, against the assembled tree:

- 68 XML files parse (`.pgx`, `.dtx`, `.pjx`, `.ltx`); every one carries a UTF-8 BOM
- 8 `interface/` files: valid JSON, **no BOM** (the condition that broke the user page before)
- `.pjx` registration: 32 application programs and 29 library programs all listed and all present on disk; every `Data file` resolves
- 18 cross-library calls and 76 intra-library calls resolve to a real program **with matching argument counts** — this is what catches the `apera_calib_prg` signature
- every library-qualified symbol (`apera3:x`) is a declared data item or program
- every binding/callback/event resolves: widget `id` exists in the matching `.html`, and `data` resolves to an app or library symbol
- every `l_*` / `x_*` identifier used in code is a declared Local or Parameter, application and library
- every non-local identifier in application code resolves to the data dictionary, the retain
  library, a program name, or a VAL3 builtin
- every `taskCreate` spawn target exists and its argument count matches
- **every extern header in the `.ltx` matches the library's actual parameter list** — type,
  by-reference-ness, array-ness and array size. This is the check rev A did not have; it
  reproduces the rev A failure and passes on rev B.

Result: **0 errors, 0 warnings.**

Not covered: the VAL3 compiler itself, motion behaviour, and anything requiring the arm.

## 9. Deployment

1. Copy `Lab_platesorter4/` into `usr/usrapp/` (or open the folder in SRS).
2. Transfer to `F_24_0060113_C_001`. `LAB_PlateSorter2` is untouched — you can fall back to it.
3. Confirm the Apera Vue host is reachable: `sAperaSocket` → 192.168.10.10:14040 is
   defined in `sio.cfx` on the controller, not in this application. Nothing to change.
4. First run: `Apera_TestPipeline` before `tkCycle`, to prove the socket and the new
   `apera_trig_traj` / `apera_wait_traj` / `apera_inspect` path.
5. Then a dry cycle with the arm at reduced speed, watching for the RoCal path only if
   you intend to recalibrate — `apera_calib_prg` sweeps the arm.
6. `bEarlyBeltKick` is still **false** by default (BASIC page checkbox). Leave it off for
   the first driver run so you are testing one variable.

**If it still refuses to load:** delete `Lab_platesorter4.ltx` and reopen the project in
SRS. That file is a generated extern cache, nothing in the `.pjx` references it, and SRS
rebuilds it from the real library. That single step isolates the extern list from the
library as the source of any remaining complaint — tell me which way it goes.

## 10. Still open from before

- `bLogRetain` is still `false` — the retain ring has never been exercised.
- Early belt kick falls back to the FOV-clear start roughly 1 cycle in 6
  (`nBeltKickTimeout_s` 3 s, `nBeltClearHeight_mm` 76.2 — untuned).
- `F_24_0060113_C_001_ALL.csv` in the metrics folder is still the stale copy; `_v2` is correct.
- No 200+ plate qualified baseline on a fed feeder yet.
