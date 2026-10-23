# 2RT57 field data from Corey: Apera log analysis, 12-15 Oct 2026

Built 16 Oct 2026 from the USB/micro SD Corey brought back (folder `2RT57\Data from Corey`). Robot: 2RT57 (controller F_24_0064095_C_003), Magswitch AR70, Apera pipeline `RAIV_pick_AR70`.

## What the numbers come from

Corey's four Apera Vue screen recordings show Apera's message log on screen. I cropped the log panel out of every frame and ran OCR on it, then rebuilt the message stream: pick requests from the robot, the capture / detector / motion-planner stages, the "Robot movement blocked" times, detection counts and the robot's trajectory requests. The trajectory IDs count up by one per pick. On 12 and 14 Oct the pick count from OCR matches the ID count exactly, so very few picks were missed.

| Recording | Readable | Log time covered | Picks |
|---|---|---|---|
| 12 Oct (09:01 PC clock) | 3 h 20 m | 16:01-16:37 (log frozen after that) | 394 |
| 13 Oct (`FSCK0001.REC`, recovered) | 1 h 47 m of ~2 h 14 m | 14:04-15:52 | 775 |
| 14 Oct | 1 h 27 m of 4 h 13 m | 13:17-14:44 | 1,038 |
| 15 Oct | 1 h 00 m of 2 h 34 m | 13:16-14:12 | 638 |
| Total | | 4 h 02 m of active picking | 2,845 |

The 14 and 15 Oct files are damaged part way through and nothing after the damage point can be decoded (each file has one keyframe at the start). Apera's log clock reads 7 hours ahead of the PC clock shown in the top bar; times in the CSVs are given in both.

## Findings

**1. Steady running is 13.9 picks/min; the average while running is 11.8/min.** The median time from one pick request to the next is 4.31 s. 64% of cycles are 4.5 s or less, 16% take over 6 s, and 43 took over 12 s. The longer cycles pull the average down: in the active windows, 2RT57 averaged 11.0 to 12.3 picks/min.

**2. The robot waits 1.82 s on vision every pick, and two-thirds of that is motion planning.** Each pick goes: the robot asks for a part, then capture 0.24 s, detector 0.39 s, Apera motion planning 1.19 s, and only then does the robot request its trajectory and move. Planning time is the same, about 1.18 s, whether 1 plate or 8 are in view, so it looks like a fixed overhead or setting in the planner rather than real work. The values were steady across all four days (p10 1.10 s, p90 1.34 s).

**3. Robot motion is 2.45 s median. A quarter of cycles end at a second position and cost 1.7 s more.** When the robot asks for its next pick it is at one of three spots. Spot A (about X 575, Y -880, Z 270) covers 67% of cycles at 2.33 s of motion. Spot B (about X 400-450, Y -790, Z 225) covers 24% at 4.07 s. Spot C (about X 650, Y -855, Z 145) covers 6% at 2.71 s. I can't tell from the log what spot B is (a different place location, a return to a trigger pose, or a belt wait). The PlateSorter4 code would answer it.

**4. The math for 20/min (3.0 s).** Taking planning out of the robot's wait gives 4.31 - 1.19 = 3.12 s, or 19.2/min. Running detection and planning while the robot is still placing the previous plate leaves roughly capture plus motion, 0.24 + 2.45 = 2.7 s, or about 22/min. Bringing spot-B cycles down to spot-A time is worth about another 0.4 s on average. Two ways to get there: ask Apera why planning takes a flat 1.2 s, or use the driver's gripper-pose mode (`apera_wait_for_gripper_pose` is in the library) and let the Stäubli plan its own moves.

**5. Vision almost never comes up empty.** Only 81 of 2,926 requests (3%) returned no part to pick. The reasons were no parts in view, none pickable, or a detected part not selected (usually a spike). "Candidate unpickable, trying next" showed up 153 times but rarely cost a cycle. Median plates in view at each pick was 5. Of everything detected: 14-inch plates 75%, spikes 20%, anchors 3%, pandrol plates 1%, 18-inch plates 1%.

**6. Downtime is the bigger loss on some days.** On 12 Oct the log stops at 16:37 and stays frozen for the remaining ~2 h 45 m of the recording. On 13 Oct there were seven stops, totaling about 39 minutes in a 107-minute window (the longest were 11.8, 8.8 and 6.9 minutes). The 14 and 15 Oct sections had only short stops of 1-1.5 minutes.

**7. What code 2RT57 is running.** The controller's FTP log shows `PlateSorter4` was loaded on 9 Oct and again on 10 Oct at 06:05, with no uploads after that through 15 Oct. That makes it the program behind all four recordings. The newest 2RT57 backup in the project folder is from 28 Sep (autoStart PlateSorter2), and PlateSorter4 isn't anywhere in the project folder.

## Other items on the USB / SD

The Stäubli log exports contain Linux system logs only: boots, safety API calls, FTP, and the encrypted event log `starc.enc`. They have no cycle data. The controller booted 32 times between 28 Sep and 15 Oct, including mid-day boots on 14 and 15 Oct. The micro SD is from a GoPro HERO5 and has no footage on it. The two CSVs are January 2024 microphone data that's unrelated. `.Trash-4444` holds a duplicate of the 12 Oct recording.

## Asks for the next data pull

1. A full SRS backup of 2RT57 so PlateSorter4 is on file.
2. Apera Vue's own log files from the vision PC, which beats recording the screen. If screen recording again, stop each recording properly before copying it.
3. A note from Corey on what spot B is, and what stopped the robot at 16:37 log time (09:37 PC clock) on 12 Oct.

## Files in this folder

`2RT57_pick_cycles_2026-10-12_to_15.csv` has one row per pick with stage times, wait, motion, pick-to-pick, request spot and detection counts. `2RT57_apera_events_2026-10-12_to_15.csv` is the full rebuilt message stream (38,648 events). `2RT57_cycle_breakdown.png` is the chart.

Caveats: the numbers are OCR'd from video, so a few values per thousand may be misread, and medians are used throughout so stray values don't move the results. "Robot waiting" assumes the robot holds still until its trajectory arrives, which is how the Apera follow-trajectory mode works. Confirm it against PlateSorter4.
