# Cycle-optimization metrics: display + storage check — 2026-08-28

Audited against the deployed `LAB_PlateSorter2.zip` you uploaded.

| | Result |
|---|---|
| **Displayed on the SP2 pendant** | **PASS** — 62 metric fields, 3 pages, all bindings resolve |
| **Stored to a backup log on the CS9** | **DOES NOT EXIST** — no file I/O anywhere in the application |

---

## A. Display — PASS

**Task is live.** `TaskCommand.pgx:37` creates `Metrics` at priority 10 and waits for
`taskStatus("Metrics")==1`. The pendant Tasks Manager showed it `running`.

**Tracking is on by default.** `bMetricEnable` defaults to `true` in the `.dtx`, and
`Init.pgx` does not overwrite it — correct, since `Init()` would otherwise stamp on the
operator's choice every abort/resume. If it is ever unticked on the LRC page,
`_sM["State"]` reads `TRACKING OFF` and nothing accumulates.

**62 metric fields across three pages:**

| Page | Fields | Content |
|---|---|---|
| LRC | 24 | target vs actual pl/hr and s/plate, GAP, LRC p10 / fastest / clean mean, clean %, clean + interrupted counts, all 8 loss buckets, plates per batch, belt episodes, longest belt |
| PHASES | 19 | all 16 phase times (Pick 0-4, Accept 0-4, Reject 0-4, to-capture), pick still %, still/move % of run |
| DETAIL | 17 | plates, accepted / rejected / accept %, counts by part type, camera mean + looks, PartFinder loop, parts in scene, TCP peak + now, MoveID |

**All 111 bindings across the four pages resolve to declared variables. Zero broken
bindings.** Eleven are never written by application code, and all eleven are correct:
`diServo["Disable"]` / `diServo["DoorSwitch"]` are physical inputs, `sClassID[0..4]` is
filled by `apera2:apera_inspect` by reference, and `sCamPair`, `bMetricEnable`,
`bEarlyBeltKick` are operator-set `rw` controls.

**Navigation is a complete ring:** BASIC —(METRICS)→ LRC —→ PHASES —→ DETAIL —→ BASIC,
with RESET on LRC.

**Config values are sane:** `nMetricPeriod` 0.05 s, `nPublishSec` 0.5 s, `nTargetPPH`
1214, `nStarveSec` 30 s, `nTcpMaxMMS` 5000, `nPendMax` 60.

---

## B. Backup log on the CS9 — does not exist

**There is no file I/O anywhere in the application.** No write primitive appears in any
`.pgx`. The only `sio` variables in the project are `sAperaConn` and `siAperaRestart`,
and both link to `Socket\...` resources — the TCP connection to Apera Vue, not disk.

Metrics exist in exactly two places, both volatile:

1. **Controller RAM** — `_nM` / `_sM` collections, `_nPhSec` / `_nPhStill` /
   `_nPhCount` (16 each), `_nCleanBin` (32).
2. **50 Modbus registers** — `aoMetric` (34) + `aoPhaseMs` (16), published every
   `nPublishSec` to the ClickPLC / C-more.

Every figure is lost on **application stop, controller restart, power cycle**, and on
**any press of RESET** on the LRC page — `ResetMetrics()` raises `bMetricReset` and
`tkMetrics` zeroes all 85 accumulators with no archive first.

`logMsg()` is used in five places (`Metrics reset`, two PartFinder messages, two Apera
messages) and writes to the CS9 system logger — the rolling LOGGER page, which caps at
around 100 entries. That is diagnostics. **No metric value is written to it.**

### Why this matters now

The point of this campaign is to prove a change moved the LRC. As it stands there is no
shift history, no before/after record, and nothing to export — the evidence for every
belt-timing and pipeline change made this week exists only until the next restart.

---

## C. What I need before building the logger

I am not going to write this on assumption. Two things need confirming first:

1. **The VAL3 file-write mechanism for s8.15 / CS9.** A web search did not return an
   authoritative answer, and I will not guess at an API that runs on your controller.
2. **Whether the controller's I/O configuration exposes a disk resource.** `sio` links
   point at named controller resources (`Socket\sAperaSocket`). That configuration is not
   in the project files, so I cannot see or create it from here.

### Three options

| Option | Mechanism | Verifiable now? |
|---|---|---|
| **1. CSV lines via `logMsg()`** *(recommended first step)* | One comma-separated metrics line every N minutes, plus one on every reset and on app stop. Lands in the CS9 system log, which persists to controller log files and comes out with a controller backup. | **Yes** — extends a call already used five times in this project. No new mechanism, no new I/O resource. Rolling, so it is a safety net rather than an archive. |
| **2. Real file on the CS9** | `sio` linked to a disk resource, one CSV appended per cycle or per interval. | Needs items 1 and 2 above confirmed. |
| **3. PLC-side** | The 50 registers already reach the ClickPLC every 0.5 s — log or historise them there. | Yes, but it is ladder/HMI work on your side, not VAL3. |

My recommendation: put option 1 in this week so the current optimization work stops
evaporating on restart, and let me confirm the disk-resource question in parallel for
option 2. Tell me which way you want it and whether the CS9 has a disk sio configured —
if you can check the controller's I/O configuration for a `Disk\` or `File\` resource,
that answers it immediately.
