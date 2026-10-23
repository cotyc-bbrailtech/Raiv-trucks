# MetricsRetain_Fix — 2026-08-28  (option 2, attempt 2)

Fixes the two errors from the first attempt. **Replace 4 files from
`MetricsRetain_2026-08-28`; everything else in that bundle stays as deployed.**

```
sLine: system memory full            Disk://LAB_PlateSorter2/RaivLog/RaivLog.dtx
./RaivLog/RaivLog.pjx : invalid library   Disk://LAB_PlateSorter2/LAB_PlateSorter2.pjx
```

## What those two errors mean

**They are one fault, not two.** The path on the first error shows SRS found and parsed
`RaivLog/RaivLog.dtx` and got as far as allocating `sLine` — so the library structure and
path are fine. The allocation failed, the library could not load, and *that* is why the
application then reports `invalid library`. Fix the memory and both should clear.

I also diffed `RaivLog.pjx` against Stäubli's own `usr/templates/retain/retain.pjx`: byte
identical apart from the project name and version string. So the `retain="true"` project
form is right.

**I sized it wrong.** Retain is a small fixed memory budget, and a VAL3 string array is
the most expensive thing you can put in it — each element reserves its maximum length, so
200 strings reserve 200 maximum-length strings whether or not they are used. I asked for
too much in one go.

## The fix — two changes

**1. Ring 200 → 20.** Deliberately small. See "finding the ceiling" below.

**2. Only `D1` is retained now.** Previously all four blocks went to the ring — four
retained lines per sample. `D1` is the headline row: s/plate, pl/hr, gap to target, the
three LRC figures, clean percentage, plate count, state. That is what evidences a
cycle-time change. `D2` loss budget, `D3` phase times and `D4` part counts are diagnostics
you read live, so they now go to the **system log only**, exactly as before.

One retained line per sample instead of four is **four times the history for the same
memory**, and it is the change I should have made before reaching for a big array.

`LogLine()` takes a second parameter, `x_bRetain`. `H1`/`D1` pass `true`, `H2`-`H4` and
`D2`-`D4` pass `false`. `bLogEnable` still gets every line.

## What's in this folder

| File | Change |
|---|---|
| `RaivLog/RaivLog.dtx` | `sLine` 200 → **20**, `nRing` default 20 |
| `RaivLog/RaivLog.pjx` | unchanged — included so the folder is complete |
| `LogLine.pgx` | new `x_bRetain` parameter; ring write gated on it |
| `LogMetrics.pgx` | `D1` retained, `D2`-`D4` log only |
| `LogMetricsHdr.pgx` | `H1` retained, `H2`-`H4` log only |

**Unchanged, keep what you deployed:** `tkMetrics.pgx`, `stop.pgx`,
`LAB_PlateSorter2.dtx`, `LAB_PlateSorter2.pjx`.

Verified: all files well-formed XML, H/D parity 14/12/17/15, all 8 `LogLine` call sites
match the 2-parameter signature, all 5 `RaivLog:` symbols declared, all 54 `_sM` keys
produced, longest retained line ~140 chars.

## Merge steps

1. Copy the four changed files over, keeping the `RaivLog/` folder structure.
2. Full application reload.
3. **The error list must be clean before you go any further.** `bLogRetain` is still
   false, so nothing is being written yet.

## Finding the ceiling — do this rather than guessing

20 entries at `nLogPeriodSec` 300 is only ~100 minutes of history. That is enough to prove
the mechanism, not enough for a shift. Once the project loads clean:

1. Set `bLogRetain` true, run, confirm `RaivLog:nWrite` advances **1 per sample** now (not
   4) and `nLines` climbs.
2. Power cycle. `nLines` and `sLine[]` must survive. **If they do not, stop and tell me** —
   retain is not doing what the template implies and we go to the socket option.
3. Then raise `sLine` size in steps — 20 → 50 → 100 → 200 — reloading each time, until SRS
   says `system memory full` again. Set `nRing` to match, and back off one step. Write the
   number down; it is a property of your controller and worth knowing.
4. Meanwhile `nLogPeriodSec` 900 gives 5 hours even at size 20, if you would rather buy
   history with sample rate than with memory.

## If `invalid library` persists after this

Then it is not the memory and my read above is wrong. One thing to try before anything
else: every real library on this controller — `apera` and `VAL3aperaNEW` — has a
`start.pgx` and a `stop.pgx`. The `retain` template has neither, because it is a standalone
project template rather than a library. Adding two no-op programs to `RaivLog` and listing
them in its `<Programs>` block would make it match the working libraries. I did not do it
pre-emptively because changing two things at once makes the next failure ambiguous, and the
error path pointed clearly at the allocation.

Tell me what the error list says and I will follow it from there.
