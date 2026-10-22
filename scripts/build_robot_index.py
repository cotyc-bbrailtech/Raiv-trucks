"""Build robots/index.json from each robot's summary.json.

Every robots/<ID>/summary.json was written while pulling that robot's data off
OneDrive, and they do not share an exact shape: each robot exposed different
facts (one has a PLC export, another only Apera logs). This flattens the
fields the dashboards need into one schema, leaving anything unknown as null
rather than guessing, and keeps a pointer back to the full summary.

    python scripts/build_robot_index.py
"""

import csv
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
ROBOTS = ROOT / "robots"
ORDER = ["0RLab", "1RT53", "2RT57", "3RT51"]


def first(*values):
    for v in values:
        if v not in (None, "", [], {}):
            return v
    return None


def pick(d, *keys):
    """First non-empty value among dotted keys in d."""
    out = []
    for key in keys:
        cur = d
        for part in key.split("."):
            cur = cur.get(part) if isinstance(cur, dict) else None
        out.append(cur)
    return first(*out)


def as_text(v):
    if isinstance(v, dict):
        named = first(v.get("name"), v.get("program"), v.get("version"))
        # A plain mapping such as {app: pipeline} has no name field of its own.
        return named or ", ".join(f"{k}: {x}" for k, x in v.items() if isinstance(x, str)) or None
    if isinstance(v, list):
        return ", ".join(str(x) for x in v) or None
    return v


def manifest_counts(robot_dir):
    path = robot_dir / "manifest.csv"
    if not path.exists():
        return None
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    pulled = [r for r in rows if (r.get("pulled") or "").strip() in ("yes", "partial")]
    return {"rows": len(rows), "pulled": len(pulled)}


def flatten(robot_dir):
    s = json.loads((robot_dir / "summary.json").read_text(encoding="utf-8"))
    m = s.get("metrics") or {}
    # Robots without a per-cycle log (the lab bench) only report their best run.
    best = m.get("best_sustained") or {}
    best_per_hr = best.get("act_plates_per_hr")
    date_range = m.get("date_range")
    if isinstance(date_range, list):
        date_range = " to ".join(str(x) for x in date_range)
    hmi = s.get("hmi") or {}
    panels = hmi.get("panels") if isinstance(hmi, dict) else None
    hmi_text = (
        ", ".join(f"{p.get('file') or p.get('name')}" for p in panels)
        if panels
        else as_text(pick(hmi, "program", "version", "cmore_panel_program"))
    )
    if not hmi_text and isinstance(hmi, dict) and hmi.get("user_page_src_version"):
        hmi_text = f"Controller user page v{hmi['user_page_src_version']}"
    return {
        "id": s.get("id") or robot_dir.name,
        "unit": s.get("truck_unit"),
        "name": s.get("name"),
        "arm_model": pick(s, "arm.model"),
        "arm_serial": pick(s, "arm.serial"),
        "controller_model": pick(s, "controller.model"),
        "controller_serial": pick(s, "controller.serial", "controller.id"),
        "val3_version": as_text(s.get("val3_version")) or pick(s, "controller.system_version"),
        "apera_serial": pick(s, "apera.serial"),
        "apera_version": pick(s, "apera.version"),
        "apera_pipeline": as_text(pick(s, "apera.pipeline", "apera.active_pipeline", "applications.apera_pipelines")),
        "plc": as_text(first(pick(s, "plc.program"), pick(s, "plc.model"))),
        "plc_version": as_text(pick(s, "plc.version")),
        "hmi": hmi_text,
        "metrics": {
            "cycles": m.get("cycles"),
            "mean_s": m.get("mean_cycle_s"),
            "median_s": m.get("median_cycle_s"),
            "p90_s": m.get("p90_cycle_s"),
            "best_s": first(m.get("best_cycle_s"), m.get("min_cycle_s"), best.get("lrc_fastest_clean_s")),
            "per_min": first(
                m.get("plates_per_min_clean"),
                m.get("steady_picks_per_min"),
                m.get("plates_per_min"),
                m.get("real_output_per_min"),
                round(best_per_hr / 60, 2) if best_per_hr else None,
            ),
            "date_range": date_range,
            "source": m.get("source"),
        },
        "latest_backup": as_text(s.get("latest_backup")),
        "latest_backup_date": pick(s, "latest_backup.date"),
        "latest_code": as_text(s.get("latest_code_update")),
        "latest_code_date": pick(s, "latest_code_update.date"),
        "open_issues": s.get("open_issues") or [],
        "files_total": s.get("files_total"),
        "files_pulled": s.get("files_pulled"),
        "manifest": manifest_counts(robot_dir),
        "summary": f"robots/{robot_dir.name}/summary.json",
        "readme": f"robots/{robot_dir.name}/README.md",
    }


def main():
    dirs = [d for d in ROBOTS.iterdir() if (d / "summary.json").exists()]
    dirs.sort(key=lambda d: ORDER.index(d.name) if d.name in ORDER else len(ORDER))
    robots = [flatten(d) for d in dirs]
    out = ROBOTS / "index.json"
    out.write_text(json.dumps({"robots": robots}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} ({len(robots)} robots)")


if __name__ == "__main__":
    main()
