"""
refresh_contact_quality.py

Pulls real Statcast contact-quality metrics (Barrel%, Hard-Hit%, xwOBA,
average exit velocity) for MLB hitters from Baseball Savant's free, public
"custom leaderboard" CSV export.
"""

import csv
import io
import json
import os
import sys
from datetime import datetime

try:
    import requests
except ImportError:
    print("This script needs the 'requests' library:  pip install requests")
    sys.exit(1)

CURRENT_SEASON = datetime.now().year
OUTPUT_PATH = os.path.join("MLB_Predictor", "contact_quality.json")

SAVANT_URL = (
    "https://baseballsavant.mlb.com/leaderboard/custom"
    f"?year={CURRENT_SEASON}&type=batter&min=50"
    "&selections=barrel_batted_rate,hard_hit_percent,xwoba,exit_velocity_avg"
    "&csv=true"
)

NAME_COLUMN_CANDIDATES = ["player_name", "name"]
LAST_NAME_COLUMN_CANDIDATES = ["last_name"]
FIRST_NAME_COLUMN_CANDIDATES = ["first_name"]
BARREL_COLUMN_CANDIDATES = ["barrel_batted_rate", "brl_percent", "barrel_pct"]
HARDHIT_COLUMN_CANDIDATES = ["hard_hit_percent", "hardhit_percent"]
XWOBA_COLUMN_CANDIDATES = ["xwoba", "est_woba"]
EXIT_VELO_COLUMN_CANDIDATES = ["exit_velocity_avg", "avg_hit_speed"]


def clean_column_name(name):
    return name.replace("\ufeff", "").replace('"', "").strip()


def fetch_csv_rows(url):
    resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    reader = csv.DictReader(io.StringIO(resp.text))
    raw_rows = list(reader)
    cleaned_fieldnames = [clean_column_name(f) for f in reader.fieldnames]
    rename_map = dict(zip(reader.fieldnames, cleaned_fieldnames))
    rows = [{rename_map[k]: v for k, v in row.items()} for row in raw_rows]
    return rows, cleaned_fieldnames


def find_column(fieldnames, candidates):
    for c in candidates:
        if c in fieldnames:
            return c
    lower_map = {f.lower(): f for f in fieldnames}
    for c in candidates:
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    return None


def normalize_name(raw_name):
    raw_name = raw_name.strip()
    if "," in raw_name:
        last, first = [p.strip() for p in raw_name.split(",", 1)]
        return f"{first} {last}"
    return raw_name


def to_float(raw_value, default=None):
    try:
        return round(float(raw_value), 3)
    except (TypeError, ValueError):
        return default


def main():
    print(f"Fetching contact-quality metrics from Baseball Savant for {CURRENT_SEASON}...")
    print(f"URL: {SAVANT_URL}\n")

    rows, fieldnames = fetch_csv_rows(SAVANT_URL)
    print(f"Columns found in the raw CSV: {fieldnames}\n")

    if not rows:
        print("[ERROR] No rows returned.")
        sys.exit(1)

    name_col = find_column(fieldnames, NAME_COLUMN_CANDIDATES)
    last_name_col = find_column(fieldnames, LAST_NAME_COLUMN_CANDIDATES)
    first_name_col = find_column(fieldnames, FIRST_NAME_COLUMN_CANDIDATES)
    barrel_col = find_column(fieldnames, BARREL_COLUMN_CANDIDATES)
    hardhit_col = find_column(fieldnames, HARDHIT_COLUMN_CANDIDATES)
    xwoba_col = find_column(fieldnames, XWOBA_COLUMN_CANDIDATES)
    velo_col = find_column(fieldnames, EXIT_VELO_COLUMN_CANDIDATES)

    print(f"Using columns -> name: {name_col}, last/first: {last_name_col}/{first_name_col}, "
          f"barrel: {barrel_col}, hardhit: {hardhit_col}, xwoba: {xwoba_col}, exit velo: {velo_col}\n")
    if not name_col and not (last_name_col and first_name_col):
        print("[ERROR] Could not find a usable player name column.")
        sys.exit(1)

    contact_quality = {}
    for row in rows:
        if name_col:
            raw_name = row.get(name_col, "")
            if not raw_name:
                continue
            name = normalize_name(raw_name)
        else:
            last = row.get(last_name_col, "").strip()
            first = row.get(first_name_col, "").strip()
            if not last or not first:
                continue
            name = f"{first} {last}"

        contact_quality[name] = {
            "barrel_pct": to_float(row.get(barrel_col)) if barrel_col else None,
            "hardhit_pct": to_float(row.get(hardhit_col)) if hardhit_col else None,
            "xwoba": to_float(row.get(xwoba_col)) if xwoba_col else None,
            "avg_exit_velo": to_float(row.get(velo_col)) if velo_col else None,
        }

    print(f"Built contact-quality data for {len(contact_quality)} hitters.")

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(contact_quality, f, indent=2)
    print(f"\nWrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
