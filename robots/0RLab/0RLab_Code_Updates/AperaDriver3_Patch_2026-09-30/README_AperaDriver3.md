# Apera driver 3 — driver-only patch, plus a bisect ladder

**Date:** 2026-09-30 · **Cell:** Raiv-Lab · **Controller:** CS9 `F_24_0060113_C_001`

---

## What bisect A settled

Bisect A was the application with your **current, unmodified apera2 driver** — only the project
files renamed. It failed too. So:

- **The new Apera driver is innocent.** Three rev failures and none of them were Apera's code.
- **My rebuilt application is the problem** — the part I synthesised from backup files.

It also exposes something I should have flagged harder: **the baseline I built everything on was
never a verified-loading application.** The 8/31 15h07 backup is real, but I layered the
`StowSelect_Pick0_Fix` and `ToolDwell_PhaseGroups` bundles on top of it, and no backup exists from
after `ToolDwell` was delivered. I treated that stack as "known good" and used it as the control
in every comparison I ran. Every one of those comparisons was therefore measuring my build
against another unverified build. That is why three clean validations told me nothing.

I should have gone this way from the start, so let me say it plainly: **every delivery in this
project that worked was a patch bundle onto the live application.** Rebuilding a whole application
out of backup files was me over-reaching, and it cost you three load attempts.

## Route 1 — driver-only patch (recommended, gets you testing today)

`AperaDriver3_Patch_2026-09-30/VAL3aperaNEW/` — the new driver, ready to drop in. Same shape as
every patch bundle that has worked on this cell.

1. In **SRS**, open `LAB_PlateSorter2` and use SRS's own **Save As / duplicate** to create
   `Lab_platesorter4`. Let SRS do the rename — do **not** rename `.pjx`/`.dtx`/`.ltx` by hand in
   Explorer. That is exactly what my builds did, and bisect A is the evidence it does not work.
2. Close SRS.
3. In the new application's folder, replace the contents of `VAL3aperaNEW/` with the contents of
   `VAL3aperaNEW/` from this bundle.
4. Reopen `Lab_platesorter4` in SRS and build.

Fall back to `LAB_PlateSorter2` at any point — it is untouched.

### What is in the patch

`apera2.dtx` is **byte-identical** to yours — it is included only so the folder is a complete
drop-in. The data dictionary needs no change: apera3's is semantically identical (same nine
items, same types and sizes).

`apera2.pjx` registers the 23 programs yours registers — all present in apera3 — plus the four
new multi-candidate entry points (`apera_trig_a`, `apera_trigtrj_a`, `apera_waitpck_i`,
`apera_waittrj_i`). Apera's two new *sample* programs are on disk but unregistered, the same way
your current library keeps `apera_binpick_auto` and the long-name duplicates unregistered.

### Four site carry-forwards (all marked `// SITE CARRY-FORWARD`)

Your apera2 library is **not** stock. These edits had to come across or the cell would regress:

**(a) `apera_exec_traj.pgx` — cycle time.** Stock apera3 calls `waitEndMove()` after *every*
trajectory section. `PartPick` calls it for `LINEAR_APPROACH` and `LINEAR_RETREAT`; blocking on
the retreat destroys the blend into the place move. Restored to your conditional form.

**(b) `apera_calib_prg.pgx` — link break + reach risk.** Stock takes **no parameter** and
hardcodes `sPipeline = "changeme"`, but `tkRoCAL:14` calls it with `sCamPair`. Stock also sweeps
J1/J5/J6 by 50/25/25° against your 35/15/20°. Both restored.

**(c) `apera_inspect.pgx` — signature.** Stock declares its two reference arrays `size="50"`;
yours declares them open, and your extern list describes the open shape. Restored to open.

**(d) Five empty `<Parameters>` / `<Locals>` elements stripped** — `apera.pgx`,
`apera_debug_tcp.pgx`, `apera_setup_cap.pgx`, `apera_send.pgx`, `start.pgx`. Across all 301 `.pgx`
files in your 8/31 controller backup there is not one empty element of either kind; apera3 writes
them for parameterless programs. No semantic change, just the shape your controller uses
everywhere else. This one is precautionary — bisect A proves it was never the load failure.

## Route 2 — the bisect ladder, if you want me to find why my rebuild fails

Three builds under `bisect/`. Load them in order and **stop at the first one that fails** — that
names the culprit. Each takes a couple of minutes.

| Build | What it is | If it fails |
|---|---|---|
| **B1_rename_only** | The 8/31 15h07 backup, original libraries, **nothing else changed** except the three filenames and one line in the `.pjx` | Renaming an application by hand is the problem. Route 1 is the only way, and I stop rebuilding applications. |
| **B2_plus_StowSelect** | B1 + `tkAbort` / `MoveToStow` / `tkCycle` from `StowSelect_Pick0_Fix` | That bundle has a defect. Since you have it running, more likely SRS rewrote it on import in a way my files do not reproduce. |
| **B3_plus_ToolDwell** | B2 + `tTool` / `tkMetrics` / `tkScreenHmi` / `.dtx` / `PHASES.*` from `ToolDwell_PhaseGroups` | **The `ToolDwell` bundle has never loaded on the controller** and carries the defect. This is my leading suspicion — there is no backup from after I delivered it. |

B1 is worth running first regardless: its entire difference from a backup your controller produced
is three filenames and `<Data file="LAB_PlateSorter2.dtx" />` → `<Data file="Lab_platesorter4.dtx" />`.
If that will not load, the answer is simply that VAL3 applications cannot be renamed on disk, and
everything I built was doomed from the first line.

If B3 is the one that fails, tell me and I will re-derive the ToolDwell changes as a patch against
your live application instead of against a backup.

## What I still owe you

- The tkMetrics comma fix (`"ABORT - press Cycle, or Abort again to Stow"` splits the D1 CSV row
  into 15 fields) is **not** in Route 1 — it belongs to the application, not the driver. It is a
  one-character edit you can make in SRS, or I will fold it into the next patch.
- The multi-candidate path (`apera_trigtrj_a` + `apera_waittrj_i`) is registered but unused. One
  trigger returning every part in the FOV is the real cycle-time lever, but it changes
  `tkPartFinder`, `PartPick` and the belt-kick interlock, so it belongs in its own measured patch
  once the driver is proven. Note `jATraj[250]` and `nATrajSect[4]` are single-slot globals — a
  multi-candidate loop must consume each trajectory before fetching the next index.
- First run after the driver goes in: `Apera_TestPipeline` before `tkCycle` — it triggers, waits
  and inspects, commands no motion and touches no belt output. Leave `bEarlyBeltKick` false.
