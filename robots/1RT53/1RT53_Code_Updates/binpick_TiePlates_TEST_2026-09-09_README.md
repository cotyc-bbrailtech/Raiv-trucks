# `binpick_TiePlates_TEST.dtx` — 2026-09-09, rubber-plate test

**Rename to `binpick_TiePlates.dtx` and deploy.** 53,337 bytes.

Built by editing **the file that is on the controller right now** — the 53,308-byte
`.dtx` in the `14h48m` backup, confirmed byte-identical to what I shipped this
morning. Seven values changed, nothing else touched. The whole diff is seven
lines and it is printed below so you can check it before it goes on.

```
mReach            blend="off" leave="0"  reach="0"     ->  leave="300" reach="300"
tSchunkEMH084     ioOpen="0.5"  ioClose="0.5"          ->  ioOpen="0.25" ioClose="0.25"
nEMH_onDelay      0.5                                  ->  0.25
nEMH_offDelay     0.5                                  ->  0.25
nGripSettle       0.35                                 ->  0
bEarlyBeltKick    (no value)                           ->  true
bBeltSensorStop   false                                ->  true
```

## Four restores and three test values

**Restores — putting back what my 09-09 deploy wiped.** `mReach`,
`tSchunkEMH084`, `bEarlyBeltKick`, `bBeltSensorStop` are set to the values that
were on the controller at 11:51 today, before my file replaced them. I am not
choosing these; `mReach` is a motion descriptor and `tSchunkEMH084` is the tool,
and both go back to what you had.

**Test values — the three dwells, valid only because the plates are rubber.**

| | | why |
|---|---|---|
| `nGripSettle` | 0.35 → **0** | You zeroed this live during run 10 and the cycle went 4.75 → 4.34 s. Straight 0.35 s. |
| `nEMH_onDelay` | 0.5 → **0.25** | Nothing to pick up, so the coil ramp is pure padding. |
| `nEMH_offDelay` | 0.5 → **0.25** | **This is the one that makes the test work.** |

The off-delay matters more than the 0.25 s it saves. Over runs 8 and 9, raising
it from 0.25 to 1.0 drove the measured vision wait from 0.88 s down to 0.19 s —
the dwell was simply covering APERA's round trip. With the wait buried under
padding you cannot see whether moving the trigger earlier helps, because there
is nothing left to recover. At 0.25 the wait is exposed and the experiment reads
cleanly.

**These three are not release settings.** Before steel plates go back on, sweep
the off-delay back up with `grip_ok` watching — `1 / 1 / 0` on every pick is the
pass condition. `0/1/x` is the plate not coming with the magnet (raise
`nEMH_onDelay` or `nGripSettle`); `x/x/1` is the plate not letting go (raise
`nEMH_offDelay`). That is the whole reason those three fields exist, and they
have never had a steel run to read.

## What this does not change

Everything else in the file is the controller's own current content, byte for
byte, including all fourteen instrumentation globals from this morning's build.
The cycle-time statistics buffers are still empty — my last deploy cleared them
and I have not re-planted stale numbers. Run `ResetCycleStats` if you want the
Options page counters starting clean anyway.

The three patched `.pgx` files are already on the controller (`Part_Accept`
9,491, `Part_Reject` 5,973, `tkBeltScan` 35,224 in the `14h48m` backup), so the
APERA latency field is reading correctly — 1.37 s, flat, across runs 11 and 12.
Nothing more is needed there.

## What I expect to see

At these settings the cycle should land near **4.2 – 4.3 s** (runs 11/12 were
4.81 s with settle 0.35 and both delays at 0.5). The vision wait should come
back up to roughly 0.85 s, which is correct and is the point — it is no longer
hidden.

Then the real question: **`cap_early` has been 0 on all 1,716 logged picks.**
The early trigger has never once fired, and `fov_hit_start` is 0 in every run,
so the branch is not being reached at all. With `bEarlyBeltKick` back on, watch
whether `cap early` starts counting on the Options page. If it does, the 0.55 s
of blocking is recoverable. If it stays at 0, the FoV condition guarding that
branch is the next thing to look at and the dwells are not the lever.

## Verification

`verify.py` **PASS (0 fail, 6 warn)**, `mutate.py` **55/55 caught, 0 missed**.

Section 10 now holds a copy of the controller's live `.dtx` and every value in
it must survive into the shipped file. The seven changes above are declared in
an `INTENTIONAL` table with the value each one changes **from** — so if you have
re-tuned any of them on the machine since the `14h48m` backup, the check fails
rather than letting this file overwrite you. Three new mutations cover exactly
that: an undeclared change, a stale "from" value, and an entry with no reason
attached. All three are caught.

## Back out

`_ctrl/binpick_TiePlates_live.dtx` in the patch bundle is the 53,308-byte file
currently on the controller. Rename and copy it back.
