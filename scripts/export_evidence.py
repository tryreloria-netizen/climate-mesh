"""Export reproducible evidence from the current Climate Mesh database.

Writes, into an ``evidence/`` folder:
    readings.csv       every sensor reading captured this run
    risk_scores.csv    every risk score computed
    alerts.csv         every alert raised (with its action playbook)
    run_summary.json   headline stats + run metadata for judges

Run this after a demo (``python run.py --mode demo --scenario flood
--judge-mode`` for a while) so judges can inspect exactly what the system
produced. Honest by construction: each row keeps its ``source`` and
``quality_flag`` so simulated/API/hardware data is never confused.
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.database import (
    count_rows, fetch_all, get_latest_run_meta, get_risk_scores, init_db,
)

OUT_DIR = Path(__file__).parent.parent / "evidence"


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")  # still create the file so its absence isn't ambiguous
        return
    # Union of keys preserves any column that appears in any row.
    fieldnames: list[str] = []
    for r in rows:
        for k in r:
            if k not in fieldnames:
                fieldnames.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    init_db()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    readings = fetch_all("sensor_readings")
    risks = fetch_all("risk_scores")
    alerts = fetch_all("alerts")

    _write_csv(OUT_DIR / "readings.csv", readings)
    _write_csv(OUT_DIR / "risk_scores.csv", risks)
    _write_csv(OUT_DIR / "alerts.csv", alerts)

    latest_risks = get_risk_scores()
    avg_risk = round(sum(r["score"] for r in latest_risks) / len(latest_risks), 1) if latest_risks else 0.0
    sources = sorted({r["source"] for r in readings}) if readings else []
    run_meta = get_latest_run_meta() or {}

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run": {
            "mode": run_meta.get("mode"),
            "scenario": run_meta.get("scenario"),
            "judge_mode": bool(run_meta.get("judge_mode")),
            "source": run_meta.get("source"),
            "notes": run_meta.get("notes"),
            "started_at": run_meta.get("started_at"),
        },
        "totals": {
            "readings": count_rows("sensor_readings"),
            "risk_scores": count_rows("risk_scores"),
            "alerts": count_rows("alerts"),
            "nodes_online": len({r["node_id"] for r in readings}),
        },
        "latest": {
            "average_risk": avg_risk,
            "highest_risk_node": (latest_risks[0]["node_id"] if latest_risks else None),
            "highest_risk_score": (latest_risks[0]["score"] if latest_risks else None),
            "data_sources_present": sources,
        },
    }
    (OUT_DIR / "run_summary.json").write_text(json.dumps(summary, indent=2))

    print(f"[evidence] Wrote 4 files to {OUT_DIR}")
    print(f"           readings={summary['totals']['readings']} "
          f"risk_scores={summary['totals']['risk_scores']} "
          f"alerts={summary['totals']['alerts']} "
          f"nodes_online={summary['totals']['nodes_online']}")
    print(f"           average_risk={avg_risk} sources={sources}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
