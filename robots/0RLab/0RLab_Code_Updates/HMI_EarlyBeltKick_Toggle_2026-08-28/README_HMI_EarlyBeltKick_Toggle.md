# HMI_EarlyBeltKick_Toggle — 2026-08-28

> ## CORRECTED 2026-08-28 — re-copy both files
>
> **The first version of this bundle would not load the user page. My mistake: I wrote a
> UTF-8 byte-order mark (BOM) to the front of both files. None of the eight original
> files in `interface/` has one.**
>
> A BOM ahead of `<!DOCTYPE` breaks the strict VALHTML XML parse, and a BOM ahead of `{`
> breaks the strict JSON parse — either one alone stops `userPage("BASIC")` from loading
> at startup, which is exactly the symptom. Nothing was wrong with the widgets, the
> bindings, the variable, or the layout.
>
> Cause: I read and wrote the files as `utf-8-sig`. That is correct for the `.pgx` and
> `.dtx` files, which do carry BOMs, and wrong for the `interface/` files, which do not.
> The `.pgx`/`.dtx` bundles were checked and are unaffected — every one matches the
> original's BOM convention.
>
> The two files in this folder are now rebuilt from the pristine originals and verified:
> no BOM, line endings byte-identical to the originals, `BASIC.html` identical to the
> original apart from the 3 added widget lines, and `BASIC.bindings.json` a purely
> additive +16 lines that parses under a strict (BOM-intolerant) JSON reader.
>
> **Recovery, if you want the page back before re-copying:** restore the original
> `BASIC.html` and `BASIC.bindings.json` from `B&B LAB 08282026.zip`
> (`usr/usrapp/LAB_PlateSorter2/interface/`) and reload. The toggle disappears, but
> `bEarlyBeltKick` still exists in the `.dtx` and is still settable from the data editor.

Adds an on-screen tick box for `bEarlyBeltKick` to the SP2 pendant BASIC page, plus an
orange **EARLY KICK ARMED** banner so the state is obvious without hunting for it.

**Depends on `BeltKickSeq_Fix_2026-08-28`** — that bundle is what declares
`bEarlyBeltKick` in the `.dtx` and reads it in `tkPartFinder`. Deploy it first, or the
binding will have nothing to bind to.

## What's in this folder

| File | Change |
|---|---|
| `interface/BASIC.html` | Adds 3 widgets: `chkEarlyKick` (checkbox), `lblEarlyKick` (caption), `lblEarlyKickON` (armed banner) |
| `interface/BASIC.bindings.json` | Adds 2 bindings: `chkEarlyKick.checked` ↔ `bEarlyBeltKick[0]` (**rw**), `lblEarlyKickON.style.visibility` ← `bEarlyBeltKick[0]` (r) |

No `.pgx` and no `.dtx` changes. No `.pjx` change — the `interface/` files are not listed
in the project file.

## Where it appears

Bottom of the BASIC page, on the empty row under the two pipeline dropdowns:

```
  y 592   [ bin1_TCPA200 v ]              [ bin1_TCPA200 v ]     <- existing
  y 628   [x] Early Belt Kick (last part)  [ EARLY KICK ARMED ]  <- new
```

Layout is `left: 8px, top: 628px` for the box, `260px` for the banner, inside the
existing 480 x 690 body. Nothing was moved and nothing overlaps — verified
geometrically against all 69 widgets on the page.

The banner is only visible while `bEarlyBeltKick` is true, using the same
`style.visibility` pattern as the existing `Trajectory Found` / `areaCONVEYOR`
indicators. Unticked, the row reads as a plain checkbox and nothing else.

## How it's wired

This uses the pattern already in the project — `chkTrack` on the LRC page, an `rw`
`checked` binding to the public bool `bMetricEnable[0]`:

```json
{ "id": "chkEarlyKick", "attribute": "checked",
  "data": "bEarlyBeltKick[0]", "size": 1, "direction": "rw", "refresh": 1 }
```

`bEarlyBeltKick` is already `access="public"`, which is what makes it bindable, and it is
already an `array size="1"` bool, so `[0]` is the correct reference — same form as
`bMetricEnable[0]` and `bTrajectoryFound[0]`.

Same touch sizing as `chkTrack` (`transform: scale(1.65)`), so it is a real target on the
pendant rather than a 13-pixel box.

## Why it's safe

- HMI-only. No motion, no I/O, no task logic touched.
- The toggle changes nothing about the interlocks in `BeltKickSeq_Fix`. With the box
  ticked, the kick still requires a fresh `nPickLiftSeq` edge **and**
  `bTrajectoryLOGIC==false`, and still times out to the safe fallback. Ticking the box
  cannot start the belt; it only stops the feature from being skipped outright.
- `tkPartFinder` reads `bEarlyBeltKick` at the top of its loop, so a mid-cycle change
  takes effect on the next pass and never inside a pick.
- `bEarlyBeltKick` is deliberately **not** written by `Init.pgx`, so ticking it is not
  undone by an abort/resume cycle.
- Widget ids are unique and every bound id exists in the HTML (verified); the bindings
  file still parses as valid JSON with the original CRLF/2-space formatting intact.

## Merge steps

1. Back up the current project.
2. Deploy `BeltKickSeq_Fix_2026-08-28` first if you have not already.
3. Copy both files into `usr/usrapp/LAB_PlateSorter2/interface/`, overwriting.
4. Full application reload so the pendant re-reads the page and its bindings.

## Verification steps

0. **Confirm the page loads at all.** On application start the BASIC page must appear as
   before. If it does not, stop — do not chase the checkbox; check the two files for a
   BOM first (`interface/` files must start with `<` and `{`, no `EF BB BF`).

1. Open the BASIC page. The new row should be at the bottom, box **unticked**, no orange
   banner.
2. Tick it. The **EARLY KICK ARMED** banner should appear immediately. Confirm in the
   data editor that `bEarlyBeltKick` went true — that proves the `rw` direction is live.
3. Untick it. Banner clears, `bEarlyBeltKick` goes false.
4. Set `bEarlyBeltKick` true from the data editor instead. The box should tick itself on
   the next refresh — the binding reads as well as writes.
5. Confirm nothing else on the page shifted or stopped updating (J1-J6, `nMoveID`,
   `nPartsFound`, the pipeline dropdowns).

## One thing to know

The tick is **not persistent**. `bEarlyBeltKick` reverts to its `.dtx` default of false
whenever the application is reloaded, unless you save the application from the pendant
while it is ticked. Given this feature has already caused an over-torque, I would leave
it that way — it means any reload puts the cell back on the proven belt timing, and
arming the early kick is always a deliberate act.

Also worth a thought: a bare tick box is easy to catch with a sleeve on a touch pendant.
The orange banner is the mitigation — if it is showing and you did not mean to arm it,
untick it. If you would rather it took two actions to arm, say so and I will make it a
press-and-confirm pair instead.
