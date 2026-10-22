# Lab_platesorter4 — rev C, plus a bisect build

**Date:** 2026-09-30 · **Cell:** Raiv-Lab · **Controller:** CS9 `F_24_0060113_C_001`

Rev B still refused to load. Rev C changes strategy: instead of another single guess, it
**shrinks the delta from the application that does load down to almost nothing**, fixes the
one structural anomaly the evidence points at, and ships a second build that isolates the
fault in one test if it still fails.

Import `Lab_platesorter4/`. Keep `LAB_PlateSorter2` on the controller as the fallback.

---

## 1. First: the `.outlining.json` you spotted

Good catch, and it is now included (application and both libraries) — but it is **not** the
cause. It holds nothing but SRS editor code-folding state: a list of character offsets per
program, `{"start": 233, "end": 5710, "isCollapsed": false}`. Nothing references it, and it
carries no program, parameter or symbol information. I had omitted it because SRS regenerates
it; it costs nothing to ship, so it is back.

## 2. What the evidence actually says

I stopped guessing and compared rev B against the application the controller **does** run
(the 8/31 15h07 backup plus your two bundles), building the full link graph of both: every
program signature, every `call` and `taskCreate` site, every argument resolved to its declared
type, application and libraries.

**The two link graphs are equivalent.** Same calls, same argument counts, same argument types.
The only difference is a parameter *name* (`l_pPoseTrans` → `x_pPoseTrans`), which VAL3 binds
positionally. Library globals: no new unresolved symbols. Extern list: matches the library.

So the problem is not *what* the code calls. It is *how a program declares that it has no
parameters*.

### The anomaly

| | empty `<Parameters>` | empty `<Locals>` |
|---|---|---|
| **All 301 `.pgx` in your 8/31 controller backup** — every application, every library, every Stäubli template | **0** | **0** |
| `apera2` driver you run today (35 files) | 0 | 0 |
| Your application programs (32 files) | 0 | 0 |
| **New apera3 driver (29 files)** | **3** | **2** |

Stock apera3 writes a parameterless program like this:

```xml
<Program name="apera_setup_cap" access="public">
  <Parameters xmlns="http://www.staubli.com/robotics/VAL3/Param/1">
  </Parameters>
```

Every file on your controller — including apera2's version of that same program — omits the
element entirely:

```xml
<Program name="apera_setup_cap" access="public">
  <Locals>
```

301 to 0 is not a style preference. And `apera_setup_cap` is the one driver program bound to
an HMI callback in `BASIC.bindings.json`, which is the kind of thing the error means by
`call()`.

Rev C strips those five empty elements — `apera.pgx`, `apera_debug_tcp.pgx`,
`apera_setup_cap.pgx`, `apera_send.pgx`, `start.pgx`. No semantic change whatsoever; the files
now have the same shape as the apera2 files that load today.

## 3. Rev C is a minimal-delta build

Rev A and rev B changed more than they needed to. Rev C changes almost nothing, so that if it
fails, the surface left to search is tiny.

**The application is byte-identical to the one you run**, except for five files:

| File | Change |
|---|---|
| `Lab_platesorter4.pjx` | `<Data file>` points at the renamed `.dtx`. **Libraries block untouched.** |
| `tkMetrics.pgx` | comma removed from the ABORT state string (breaks CSV parsing); header comment |
| `tkScreenHmi.pgx`, `LogLine.pgx`, `LogMetricsHdr.pgx` | comment text only |

`Lab_platesorter4.dtx` and `.ltx` are **renamed, not edited** — byte-identical contents.

**Reverted from rev A/B**, because none of it was needed and all of it was risk:

- alias stays **`apera2`** — all 19 call sites, the HMI binding and the extern list are untouched
- the stale **`apera` library stays**, byte-identical — `Init.pgx` is untouched
- the driver stays in **`VAL3aperaNEW/`** as `apera2.pjx` + `apera2.dtx`
- the **`.dtx` is apera2's**, not apera3's — the two are semantically identical (same nine items,
  same types and sizes; apera3 only spells defaults explicitly), so the proven one is used

The names are less tidy than rev A. That is deliberate: once it loads, renaming is a
five-minute follow-up, and doing it now costs nothing but risk.

**So the only real difference from your working application is the contents of the driver
program files.**

## 4. What is in the driver, and the four site carry-forwards

`VAL3aperaNEW/` now holds the apera3 programs. `apera2.pjx` registers the same 23 programs
apera2 registered — all present in apera3 — plus the four new multi-candidate entry points
(`apera_trig_a`, `apera_trigtrj_a`, `apera_waitpck_i`, `apera_waittrj_i`). The two new Apera
*sample* programs (`apera_binpick_a`, `apera_autoplt_a`) are on disk but not registered, the
same way apera2 kept `apera_binpick_auto` and the long-name duplicates unregistered.

Four edits to Apera's files, all marked `// SITE CARRY-FORWARD`:

**(a) `apera_exec_traj.pgx` — cycle time.** Stock apera3 calls `waitEndMove()` after *every*
section. `PartPick` calls it for `LINEAR_APPROACH` and `LINEAR_RETREAT`; blocking on the
retreat destroys the blend into the place move. Restored to the deployed conditional form.

**(b) `apera_calib_prg.pgx` — link break + reach risk.** Stock takes **no parameter** and
hardcodes `sPipeline = "changeme"`, but `tkRoCAL:14` calls it with `sCamPair`. Stock also
sweeps J1/J5/J6 by 50/25/25° against your 35/15/20°. Both restored.

**(c) `apera_inspect.pgx` — signature.** Stock declares the two reference arrays `size="50"`;
apera2 declares them open, and your extern list describes the open shape. Restored to open.
(This was the rev B fix; kept.)

**(d) empty `<Parameters>` / `<Locals>` stripped** — §2.

Everything else is Apera's, unmodified.

## 5. If rev C still will not load — one test, five minutes

`bisect/Lab_platesorter4_bisectA.zip` is **the same application, with your current apera2
driver, completely unmodified.** Only the project rename and those same five comment/`.pjx`
edits. Load it.

- **Bisect A loads** → the rename and packaging are sound, and the fault is in the apera3
  driver content. That is a much smaller haystack, and I will go file by file through it.
- **Bisect A also fails** → the fault is in the rename or packaging itself, and the new driver
  is innocent. Tell me and I will stop looking at Apera's code entirely.

Either answer halves the problem. Please run it before I guess again.

## 6. Validation performed on rev C

- 105 XML files parse; correct BOM on every `.pgx`/`.dtx`/`.pjx`/`.ltx`, none on `interface/`
- 32 application and 27 library programs registered, all present; every `Data file` resolves
- 18 cross-library and 154 intra-library calls resolve, with matching argument counts
- every `taskCreate` target exists and takes no arguments
- extern headers in `.ltx` match the library's real parameter lists (type, by-reference, array shape)
- every identifier resolves to a local, parameter, dictionary entry, program or VAL3 builtin
- full link-graph diff against the working application: equivalent
- zero empty `<Parameters>`/`<Locals>` anywhere

**0 errors, 0 warnings.** Rev B passed all of these except the last, which is new.

I want to be straight with you: rev B passed a clean validation too, and still failed. The
difference this time is that rev C is not resting on the fix being right — the delta is small
enough, and the bisect build specific enough, that we get an answer either way.

## 7. Deployment

1. Import `Lab_platesorter4/`; transfer to `F_24_0060113_C_001`. `LAB_PlateSorter2` is untouched.
2. Run `Apera_TestPipeline` before `tkCycle` — it triggers, waits and inspects, commands no
   motion and touches no belt output.
3. Then a reduced-speed dry cycle. Leave `bEarlyBeltKick` **false** for the first run.
4. Do not run RoCal unless you intend to recalibrate — `apera_calib_prg` sweeps the arm.

## 8. Still open

- The multi-candidate path (`apera_trigtrj_a` + `apera_waittrj_i`) is registered but unused.
  It is the real cycle-time lever — one trigger, every part in the FOV — but it changes
  `tkPartFinder`, `PartPick` and the belt-kick interlock, so it belongs in its own measured
  patch once this loads. Note `jATraj[250]` / `nATrajSect[4]` are single-slot globals.
- `bLogRetain` still `false`; belt kick still falls back ~1 cycle in 6; `F_24_0060113_C_001_ALL.csv`
  still the stale copy; no 200+ plate qualified baseline yet.
