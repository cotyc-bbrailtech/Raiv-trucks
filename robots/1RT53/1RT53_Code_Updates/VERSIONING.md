# VAL3 project versioning - binpick_TiePlates (all robots)

## Format
`binpick_TiePlates_v<MAJOR>_<MINOR>_<PATCH>`   example: `binpick_TiePlates_v2_0_0`

Underscores, not dots, because VAL3 application names on the controller contain none and dots are not known to be legal. Read it as 2.0.0 in docs and conversation.
The same string is the project folder name and the `.pjx`, `.dtx`, `.ltx` base name, and it is the `autoStart` name in `configs\cell.cfx`.
Robot prefix stays out of the project name (0RLab, 1RT53, 2RT57, 3RT51 are identified by the folder the package lives in). The version counter is per robot.

## When each number moves
- MAJOR: anything that changes the physical or geometric basis, or the program architecture. New or changed tool (TCP), gripper or valve change, flange/mounting change, new camera or calibration, task or data-structure redesign. After a MAJOR bump, re-teach and slow-jog checks are required.
- MINOR: new behavior or feature, same hardware. New wait, sensor logic, timing change, new HMI function. Cycle behavior is different but teach points are unchanged.
- PATCH: bug fix, parameter or constant tweak, logging or comment change. No new behavior.
A higher number resets the lower ones (2.1.3 -> 3.0.0).

## Rules
1. Every update package gets a new version. Never edit a project in place under the same version.
2. Package folder: `<Name>_<install or change date>` inside `1RT53_Code_Updates`, containing `USR_prior_to_update` (unchanged copy of the previous tree) and `USR_<date of update>` (new full tree). `CHANGES.md` sits beside them.
3. In `USR_<date>` the project is renamed to the new version and `cell.cfx` autoStart points at it. In `USR_prior_to_update` it keeps its old name.
4. One row per package in `VERSION_LOG.md`: version, date, package folder, one-line summary, base version.
5. Experiments and side branches are not versions of the production line. Name them `binpick_TiePlates_<Tag>` (e.g. `_LabTest`) and leave them out of autoStart.
6. Baseline: the project deployed on 12 Oct 2026, `binpick_TiePlates_BeltSensor` rev D, is v1.0.0.
