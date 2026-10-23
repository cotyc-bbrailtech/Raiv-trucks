# 1RT53 Apera KPIs and robot match (built 21 Oct 2026)

Source data: `..\apera_daily\1RT53_apera_journal_<date>.zip` (Apera container log, saved daily by apera_journal.py on the Apera PC) and the robot log in `1RT53_Staubli_Backups\F_24_0064095_C_004\Y-2026_M-10_D-21_12h50m\logArchive.zip`.

| File | What it is |
|---|---|
| apera_picks_2026-09-10_to_10-20.csv | One row per pick from the Apera log (3,499 picks). A pick = the robot fetching a new trajectory (`t,<id>,0`). Trigger and fetch times (UTC), trigger pose (place or trigger), vision latency, robot wait, stage times, cycle to the next pick. |
| robot_cycles_from_backup_2026-10-21_12h50m.csv | One row per robot cycle from the RAIV/CSV lines (cycle and segment times). |
| robot_vs_apera_matched.csv | Robot cycles matched to their Apera pick, 7–20 Oct. |
| parse_apera.py, robot_cycles.py, match_robot_apera.py | The scripts. Re-run in that order after new zips or a new backup. |

**Robot clock.** The controller clock is not synced. It runs about 4 h 15 m 40 s behind UTC and gains on Apera by about 1 s a day (offset 15,337.4 s on 7 Oct, 15,347.3 s on 20 Oct). The matcher finds each day's offset itself: the one where the robot's vision-wait timer agrees with Apera's "robot movement blocked" for the same pick. At the chosen offset they agree within 0.05 s on every matched cycle, and the robot's cycle time matches Apera's fetch-to-fetch interval within 0.04–0.05 s (median).

**Match rate.** 19 Oct 319 of 330 robot cycles, 20 Oct 301 of 323, 14 Oct 63 of 140, 7 Oct 68 of 85. 8 Oct did not match (Apera camera faults that day).
