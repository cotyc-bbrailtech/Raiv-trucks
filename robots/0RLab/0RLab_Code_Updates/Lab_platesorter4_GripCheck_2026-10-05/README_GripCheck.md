# Lab_platesorter4 + GripCheck (Stage 1) - 5 Oct 2026

Measures how often a picked part does not arrive. Observer only: no change to motion, speeds,
delays or the vision path.

## What it adds
- `PartPick`: after the gripper closes, counts the attempt and notes the grip pose and part class.
- `GripRelease` (new): called from `PartPlace` just before each `tTool("OFF")`. Reads the station
  overflow sensor while the part is still in the gripper, then arms the check.
- `tkGripCheck` (new task, priority 10): for `nGrip_Window` seconds (2.5 s) watches the sensor for a
  rising edge, then books one outcome and writes a log row.
- `TaskCommand` starts the task, `KillAllTasks` stops it, `.pjx` and `.dtx` list the new programs
  and globals. Everything else is the 30 Sep `Lab_platesorter4` file for file.

## Outcomes
| Result | Meaning |
|---|---|
| OK | accept path, sensor clear at release, rising edge seen: delivered |
| MISS | accept path, sensor clear at release, no edge: not delivered (never lifted, or dropped in transit) |
| PRE | accept path, sensor already on at release: cannot judge |
| REJ | reject path: logged, not judged (the reject sensor looks like a bin-full level) |

Failure rate = MISS / (OK + MISS).

## Log rows (CS9 system log, same sink as D2..D4)
- `RAIV/CSV,GH,...` header once at task start
- `RAIV/CSV,G1,...` one row per release: run, seq, condition, gripper, class, dest, result, edge time,
  sensor before and after, carry time, grip x y z rz, running totals
- `RAIV/CSV,G2,...` running totals every 10 outcomes

These are system-log lines. Read them live on the pendant LOGGER page, or from `user.log` in a
Staubli backup (the 31 Aug backups held it). Not written to the retained RaivLog ring (small fixed memory).

## Before the first real run (10 minutes, parts by hand)
1. Watch `bAccept_Overflow` in the data viewer. Put a plate on the accept station: it must go true.
   Remove it: it must go false. (Polarity was flipped on 11/20.)
2. Hand-release a plate onto the station with the arm idle: note how long until it goes true. If it is
   longer than 2.5 s, raise `nGrip_Window`.
3. Hold a plate in the gripper at the place pose: if the sensor goes true before release, results will
   come out as PRE and the accept sensor cannot be used as-is.

## Running a test
1. Set `sGrip_Cond` in the SRS data editor: `clean`, `light_rust`, `heavy_rust`, `pitted` or `warped`.
2. Run 100 picks per condition if you can. Same gripper, same speed override, same drop delay.
3. Count the bins by hand. Add a row to `grip_test_log.csv`:
   `run,date,gripper,cond,picks_attempted,plates_accept,plates_reject,notes`.
4. `python3 summarize_grip.py user.log --tally grip_test_log.csv` prints miss rate with a 95% interval,
   from the controller rows and from your tally side by side. If they disagree, trust the tally and
   check the sensor.

## Limits
- MISS does not split "never lifted" from "dropped on the way". Carry time and grip pose help.
- Counters restart when the application starts; use the G1 rows and `sGrip_Cond` to separate runs.
- Built from the 30 Sep code without a controller to test on. Open in SRS and build before use; the
  syntax follows the code around it.
- To disable: `bGrip_Log=false` silences output; removing the `taskCreate "GripCheck"` line stops the task.
