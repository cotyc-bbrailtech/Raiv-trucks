# RAIV_TPS_TRUCK — full VAL3 project folder

**Status: DRAFT. Nothing here is on the physical controller yet, and none of
the new PLC I/O is wired.** This folder is meant to be opened directly in
Staubli Robotics Studio as its own project — a consolidated version of the
`RAIV_TPS_TRUCK_2026-09-28` patch bundle, with every unchanged program file
copied in alongside it, so it's one folder instead of a diff to hand-merge.
See that dated bundle's own `README.md` (still in `Raiv-T3/RAIV_TPS_TRUCK_2026-09-28/`)
for the full write-up of what changed and why — this README covers what's
specific to using this as a complete project.

## What's in this folder

All 27 `.pgx` program files PlateSorter's `.pjx` lists (the original 26,
plus the new `PLCStatsSnapshot.pgx`), `RAIV_TPS_TRUCK.dtx`, `RAIV_TPS_TRUCK.pjx`,
and `RAIV_TPS_TRUCK.ltx` (Robotics Studio's cached Apera library signature
list — renamed to match, though SRS will likely regenerate it on its own the
first time it loads the library). 26 of the 27 `.pgx` files, and `.ltx`, are
**byte-identical copies** of the Sep-21-2026 `.OK` backup — only `tkCycle.pgx`
(one new line) and the new `PLCStatsSnapshot.pgx` differ, exactly as
documented in the dated bundle's README, plus the `.dtx`/`.pjx` edits
described there.

## What's NOT in this folder — two folders you need to copy in yourself

I could not reach these two subfolders through the file bridge — Robotics
Studio project folders nest `apera/` and `interface/` deep enough (and
`apera/` itself nests a nested `interface/` and `functions/` one level
deeper again) that they're past a folder-depth limit on the tool that moves
files between your computer and this session, and the usual workaround
(a shell running directly on your machine) has been down since the Sep-8
Windows update issue you may have already seen mentioned elsewhere in this
project. Neither is something I could safely reconstruct by hand — they're
either compiled library content or a web UI bundle, not something to
retype.

1. **`apera/`** — the Apera vision library `RAIV_TPS_TRUCK.pjx` references
   (`<Library alias="Apera" path="./apera/apera.pjx" .../>`). The project
   will not open or compile in Robotics Studio without it.
2. **`interface/`** — contains `BASIC.html` and `BASIC.bindings.json`, the
   custom pendant page `Init_Robot.pgx` loads via `userPage("BASIC")`. The
   project will open and compile without it, but that page won't display
   correctly on the pendant until it's there.

**To finish this folder**, copy both subfolders from the Sep-21 backup into
this one, keeping their names:

```
Raiv-T3\Backups\F_24_0064095_C_002\Y-2026_M-09_D-21_12h27m.OK\usr\usrapp\PlateSorter\apera
Raiv-T3\Backups\F_24_0064095_C_002\Y-2026_M-09_D-21_12h27m.OK\usr\usrapp\PlateSorter\interface
```

into this folder (`Raiv-T3\RAIV_TPS_TRUCK\`), so you end up with
`RAIV_TPS_TRUCK\apera\` and `RAIV_TPS_TRUCK\interface\` alongside the files
already here. That's a plain folder copy in File Explorer or OneDrive — no
VAL3/SRS-specific step, and neither folder is touched or referenced by
anything this bundle changed, so a straight copy is safe.

Once those two folders are in place, this becomes a complete, self-contained
`RAIV_TPS_TRUCK` project you can open in Robotics Studio directly, rebuild/
recompile there (the real compiler and safety gate — this bundle's own
`verify.py`, in the dated bundle folder, only stands in for the checks
possible without one), and deploy.

## Everything else

PLC register mapping, the `bPLCSnapshot_IOBound` gating, the CSV log format,
`verify.py`'s PASS result, and "what to watch on first run" are all in
`RAIV_TPS_TRUCK_2026-09-28/README.md` — unchanged by this consolidation,
so not repeated here to avoid the two drifting out of sync.
