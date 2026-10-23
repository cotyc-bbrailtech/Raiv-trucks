# Robot data

What is on record for each RAIV robot cell (Stäubli TX2-140 arm, CS9 controller, Apera Vue
vision), pulled from the OneDrive project folders. Shown on [`robots.html`](../robots.html).

| Folder | Robot | Fleet unit | OneDrive sources |
| --- | --- | --- | --- |
| [`0RLab/`](0RLab/README.md) | Lab bench | — | `Claude_project- Optimize Robot Cycle/0RLab`, `…/Metrics_0RLab_F_24_0060113_C_001` |
| [`1RT53/`](1RT53/README.md) | Raiv-T1 | T-53 | `Claude_project- Optimize Robot Cycle/1RT53`, `Robot Trucks/1RT53` |
| [`2RT57/`](2RT57/README.md) | Raiv-T2 (RAIV-2) | T-57 | `Claude_project- Optimize Robot Cycle/2RT57`, `…/Metrics_2RT57_F_24_0064095_C_003`, `Robot Trucks/2RT57` |
| [`3RT51/`](3RT51/README.md) | Raiv-T3 | T-51 | `Claude_project- Optimize Robot Cycle/3RT51`, `…/Metrics_3RT51_F_24_0064095_C_002`, `Robot Trucks/3RT51`, `Documents/Staubli/backups/3RT51` |

Each robot folder holds:

- `manifest.csv` — every file seen on OneDrive (path, size, item URI) and whether it was pulled.
  Media and repetitive backup trees are summarised as one row per folder.
- `README.md` — what the robot is, what was pulled, and the key facts with the file each came from.
- `summary.json` — those facts, machine-readable. `null` means no pulled file stated it.
- The pulled files themselves, under the same folder structure as OneDrive. Office and PDF files
  are saved as extracted text (`<name>.<ext>.txt`) or one CSV/TSV per sheet.

`index.json` flattens the four summaries into one schema for the dashboard and for
[unit-info](https://github.com/cotyc-bbrailtech/unit-info). Rebuild it after changing a summary:

```bash
python scripts/build_robot_index.py
```

## What is not here

- **Robot code and controller config.** The Microsoft 365 connector used for the pull serves
  VAL3 (`.pgx`, `.dtx`, `.pjx`, `.ltx`), Stäubli config (`.cfx`, `.pmt2`) and `.py` files as
  binary, so they are listed in each manifest with their OneDrive location but not copied.
  Copy them with OneDrive sync if they are needed in git.
- **Binaries and media:** backup zips, `.ckp`/`.cmpv` PLC/HMI projects, Apera `.state` files,
  images and video (1RT53_Apera alone is ~24 GB).
- **Large logs** over ~400 KB are partly pulled (first and last page); the manifest says which.
- **Keys and certificates** in backup trees were deliberately not copied.
- **"1RT51"** does not exist on OneDrive; truck 1 is `1RT53` (unit T-53).
