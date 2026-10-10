"""Extract No Kings protest locations from the Crowd Counting Consortium dataset (CC0 1.0).

Usage: python -I scripts/ccc_dots.py /path/to/ccc-phase3-public.csv
Writes data/map-dots.json (lon/lat per event) and data/map-stats.json (counts for on-screen text).

Source: Crowd Counting Consortium, US Protest Event Data (Harvard Ash Center / UConn),
doi:10.7910/DVN/RI9JFU, v18 — license CC0 1.0.
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NO_KINGS_DAYS = {"2025-06-14", "2025-10-18", "2026-03-28"}
KEYS = ("title", "organizations", "claims_summary", "macroevent", "notes")


def is_no_kings(row):
    if row["date"] not in NO_KINGS_DAYS or row["valence"] != "1":
        return False
    text = " ".join((row.get(k) or "") for k in KEYS).lower()
    return "no king" in text or "nokings" in text


def main(csv_path):
    dots, per_day, states = [], {}, {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not is_no_kings(r):
                continue
            try:
                lat, lon = float(r["lat"]), float(r["lon"])
            except ValueError:
                continue
            dots.append({"lon": round(lon, 4), "lat": round(lat, 4), "d": r["date"]})
            per_day[r["date"]] = per_day.get(r["date"], 0) + 1
            states.setdefault(r["date"], set()).add(r["resolved_state"] or r["state"])
    stats = {
        "source": "Crowd Counting Consortium US Protest Event Data v18 (CC0 1.0), doi:10.7910/DVN/RI9JFU",
        "events_total": len(dots),
        "events_by_day": dict(sorted(per_day.items())),
        "states_by_day": {d: len(s) for d, s in sorted(states.items())},
        "states_all": sorted(set().union(*states.values())) if states else [],
    }
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "map-dots.json").write_text(json.dumps(dots))
    (ROOT / "data" / "map-stats.json").write_text(json.dumps(stats, indent=1))
    print(json.dumps({k: v for k, v in stats.items() if k != "states_all"}, indent=1))
    print("distinct state codes:", len(stats["states_all"]))


if __name__ == "__main__":
    main(sys.argv[1])
