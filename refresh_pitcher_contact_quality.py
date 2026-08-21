"""
refresh_pitcher_contact_quality.py

Pulls pitcher contact-quality-allowed from Baseball Savant's custom leaderboard
and writes pitcher_contact_quality.json, keyed by MLB PlayerID.

Mirror of refresh_contact_quality.py (hitters), with type=pitcher.
Runs nightly via GitHub Actions from the REPO ROOT:  python refresh_pitcher_contact_quality.py
"""

import csv
import io
import json
import sys
from datetime import datetime, timezone

import requests

YEAR = 2026
MIN_BBE = 50          # filter applied AFTER the pull, not via Savant's `min` param
OUT_PATH = "pitcher_contact_quality.json"

# Savant's `min` filter gets misread server-side and can collapse the result to a
# single row. Always pull with min=1 and filter locally.
SELECTIONS = ",".join([
    "pa",
    "bbe",
    "barrels_per_bbe_percent",
    "hard_hit_percent",
    "exit_velocity_avg",
    "launch_angle_avg",
    "xwoba",
    "k_percent",
    "bb_percent",
    "groundballs_percent",
    "flyballs_percent",
    "linedrives_percent",
    "popups_percent",
])

URL = (
    "https://baseballsavant.mlb.com/leaderboard/custom"
    f"?year={YEAR}"
    "&type=pitcher"
    "&filter="
    "&min=1"
    f"&selections={SELECTIONS}"
    "&chart=false"
    "&x=pa&y=pa&r=no&chartType=beeswarm&sort=pa&sortDir=desc"
    "&csv=true"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    )
}

# Savant column name -> our key
FIELD_MAP = {
    "pa": "PA",
    "bbe": "BBE",
    "barrels_per_bbe_percent": "Barrel",
    "hard_hit_percent": "HardHit",
    "exit_velocity_avg": "EV",
    "launch_angle_avg": "LA",
    "xwoba": "xwOBA",
    "k_percent": "K",
    "bb_percent": "BB",
    "groundballs_percent": "GB",
    "flyballs_percent": "FB",
    "linedrives_percent": "LD",
    "popups_percent": "PU",
}

# Fields we average across the league (BBE-weighted where it makes sense).
RATE_FIELDS = ["Barrel", "HardHit", "EV", "LA", "xwOBA", "K", "BB",
               "GB", "FB", "LD", "PU"]


def row_to_dict(header, row):
    """
    Savant's CSV header lists `last_name` and `first_name` as two columns, but the
    DATA rows merge them into a single quoted field. That shifts every subsequent
    value one column earlier than the header implies. Detect the deficit per row
    and collapse the name headers to absorb it.
    """
    if len(row) == len(header):
        return dict(zip(header, row))

    deficit = len(header) - len(row)
    if deficit <= 0:
        return None

    name_idx = next(
        (i for i, h in enumerate(header) if "last_name" in h.lower()), None
    )
    if name_idx is None:
        return None

    collapsed = (
        header[:name_idx] + ["player_name"] + header[name_idx + 1 + deficit:]
    )
    if len(collapsed) != len(row):
        return None
    return dict(zip(collapsed, row))


def to_float(value):
    if value is None:
        return None
    value = value.strip().replace("%", "")
    if value in ("", "NA", "null", "--"):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def fetch_rows():
    resp = requests.get(URL, headers=HEADERS, timeout=60)
    resp.raise_for_status()

    reader = csv.reader(io.StringIO(resp.text))
    rows = list(reader)
    if not rows:
        raise RuntimeError("Savant returned an empty CSV")

    header = [h.strip().strip('"') for h in rows[0]]
    parsed, skipped = [], 0
    for raw in rows[1:]:
        if not any(cell.strip() for cell in raw):
            continue
        rec = row_to_dict(header, raw)
        if rec is None:
            skipped += 1
            continue
        parsed.append(rec)

    print(f"Header columns: {len(header)}")
    print(f"Parsed rows: {len(parsed)}  (skipped {skipped} unparseable)")
    if len(parsed) < 100:
        raise RuntimeError(
            f"Only {len(parsed)} pitcher rows parsed — expected several hundred. "
            "Check the `min` param and the column-shift handling before trusting this."
        )
    return parsed


def build_payload(rows):
    pitchers = {}
    for rec in rows:
        pid = rec.get("player_id") or rec.get("pitcher")
        if not pid or not str(pid).strip().isdigit():
            continue
        pid = str(int(pid))

        entry = {}
        for savant_key, our_key in FIELD_MAP.items():
            entry[our_key] = to_float(rec.get(savant_key))

        if entry.get("BBE") is None or entry["BBE"] < MIN_BBE:
            continue

        entry["Name"] = (rec.get("player_name") or "").strip().strip('"')
        pitchers[pid] = entry

    if not pitchers:
        raise RuntimeError("No pitchers survived the BBE filter — aborting.")

    # BBE-weighted league averages. Stored in the file so the app can regress
    # small-sample pitchers toward league average without recomputing.
    league = {}
    for field in RATE_FIELDS:
        num = den = 0.0
        for e in pitchers.values():
            v, w = e.get(field), e.get("BBE")
            if v is not None and w:
                num += v * w
                den += w
        league[field] = round(num / den, 4) if den else None

    return {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "season": YEAR,
        "min_bbe": MIN_BBE,
        "pitcher_count": len(pitchers),
        "league_avg": league,
        "pitchers": pitchers,
    }


def main():
    payload = build_payload(fetch_rows())

    with open(OUT_PATH, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"\nWrote {OUT_PATH}: {payload['pitcher_count']} pitchers (BBE >= {MIN_BBE})")
    print("League averages:", json.dumps(payload["league_avg"], indent=2))

    sample = list(payload["pitchers"].items())[:3]
    print("\nSample rows (verify these against Savant's site before wiring in):")
    for pid, e in sample:
        print(f"  {pid} {e['Name']}: BBE={e['BBE']} Barrel={e['Barrel']} "
              f"HardHit={e['HardHit']} xwOBA={e['xwOBA']} GB={e['GB']} FB={e['FB']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
