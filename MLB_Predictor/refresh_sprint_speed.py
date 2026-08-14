"""
refresh_sprint_speed.py

Pulls real Statcast Sprint Speed (feet/second) for MLB hitters from Baseball
Savant's free, public "custom leaderboard" CSV export -- the same data
source and endpoint pattern as refresh_contact_quality.py, reused here
specifically because that script's bugs are already found and fixed:

1. `min=1` (not a larger number) -- an arbitrary raw integer for the
   minimum-qualifier filter gets misinterpreted by Savant's backend and
   returns almost no rows; min=1 is the safest, most inclusive value.
2. Savant's data rows merge last_name and first_name into ONE combined
   field (e.g. "Moore, Christian") despite the header listing them as two
   separate columns, which shifts every subsequent column one position
   EARLIER than the header names suggest. This script detects that shift
   per-row (checking for a comma in the last_name field) and corrects for
   it automatically, exactly like refresh_contact_quality.py does.

WHAT THIS DOES
---------------
1. Downloads the Statcast custom batter leaderboard CSV for sprint speed.
2. Converts Savant's raw feet/second value into this app's existing 0-100
   SPD scale (the scale roster_data.json/ROSTER_DATABASE hitters already
   use, currently a flat default of 55 for everyone since real speed data
   was never wired in): SPD = 55 + (sprint_speed_ft_s - 27.0) * 12.5,
   clamped to [1, 99]. 27.0 ft/s is roughly league average, so this keeps
   an average-speed player landing right at the app's existing default of
   55 -- burners like Elly De La Cruz (~30+ ft/s) land near 95-99, and slow
   players (~23-24 ft/s) land near 10-20.
3. Writes MLB_Predictor/sprint_speed.json, keyed by MLB PlayerID (matching
   roster_data.json's PlayerID field, NOT by name -- name-formatting
   differs between MLB Stats API and Savant, which is exactly the bug that
   broke contact-quality matching before ID-based keying fixed it).

STILL UNTESTED LIVE -- same caveat as always: this environment has no
network access, so this hasn't been run against the real live site. It
reuses a data-fetching pattern already proven correct against this exact
endpoint, which is why this version skips straight to the shift-correction
logic instead of needing another round of trial and error -- but the exact
Savant column name for sprint speed ("sprint_speed") is still a
best-guess, not confirmed. The script prints every column it finds and the
total row count immediately, so if that guess is wrong, one screenshot is
enough to fix it in a single pass.
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
OUTPUT_PATH = os.path.join("MLB_Predictor", "sprint_speed.json")

SAVANT_URL = (
    "https://baseballsavant.mlb.com/leaderboard/custom"
    f"?year={CURRENT_SEASON}&type=batter&min=1"
    "&selections=sprint_speed"
    "&csv=true"
)

NAME_COLUMN_CANDIDATES = ["player_name", "name"]
LAST_NAME_COLUMN_CANDIDATES = ["last_name"]
FIRST_NAME_COLUMN_CANDIDATES = ["first_name"]
PLAYER_ID_COLUMN_CANDIDATES = ["player_id", "playerid", "mlbid", "mlb_id"]
SPRINT_SPEED_COLUMN_CANDIDATES = ["sprint_speed", "sprint_speed_ft_sec", "r_sprint_speed_top50percent"]

LEAGUE_AVG_SPRINT_SPEED = 27.0  # feet/second, roughly league average


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


def sprint_speed_to_spd_scale(sprint_speed_ft_s):
    """Converts raw Statcast feet/second into this app's existing 0-100 SPD
    scale, keeping the app's prior default (55 = league average) as the
    calibration anchor point."""
    if sprint_speed_ft_s is None:
        return None
    spd = 55 + (sprint_speed_ft_s - LEAGUE_AVG_SPRINT_SPEED) * 12.5
    return round(max(1, min(99, spd)))


def get_shifted_value(row, fieldnames, col_name, shift=-1):
    """Reads from the column `shift` positions before col_name in header
    order -- corrects for Savant's last_name/first_name merge shifting
    every subsequent value one position earlier than the header names
    suggest. See module docstring for the full explanation; this is the
    exact fix already proven correct in refresh_contact_quality.py."""
    if col_name not in fieldnames:
        return None
    idx = fieldnames.index(col_name) + shift
    if 0 <= idx < len(fieldnames):
        return row.get(fieldnames[idx])
    return None


def main():
    print(f"Fetching Sprint Speed from Baseball Savant for {CURRENT_SEASON}...")
    print(f"URL: {SAVANT_URL}\n")

    rows, fieldnames = fetch_csv_rows(SAVANT_URL)
    print(f"Columns found in the raw CSV: {fieldnames}")
    print(f"Total rows returned: {len(rows)}  (should be several hundred, one per qualifying hitter)")
    if rows:
        print(f"First row (for inspection): {rows[0]}\n")
    print("^ If the fields below show as 'None', or the row count looks wrong, send this")
    print("  block back and the script can be corrected in one pass.\n")

    if not rows:
        print("[ERROR] No rows returned -- check the URL/params above against what's")
        print("        actually on https://baseballsavant.mlb.com/leaderboard/custom")
        sys.exit(1)

    id_col = find_column(fieldnames, PLAYER_ID_COLUMN_CANDIDATES)
    name_col = find_column(fieldnames, NAME_COLUMN_CANDIDATES)
    last_name_col = find_column(fieldnames, LAST_NAME_COLUMN_CANDIDATES)
    first_name_col = find_column(fieldnames, FIRST_NAME_COLUMN_CANDIDATES)
    speed_col = find_column(fieldnames, SPRINT_SPEED_COLUMN_CANDIDATES)

    print(f"Using columns -> id: {id_col}, name: {name_col}, last/first: {last_name_col}/{first_name_col}, "
          f"sprint_speed: {speed_col}\n")
    if not id_col:
        print("[ERROR] Could not find a player ID column. Can't key the output reliably without one.")
        sys.exit(1)
    if not speed_col:
        print("[ERROR] Could not find a sprint speed column. The guessed column name is wrong --")
        print("        check the printed column list above and update SPRINT_SPEED_COLUMN_CANDIDATES.")
        sys.exit(1)

    sprint_speed_data = {}
    shift_detected_count = 0
    missing_speed_count = 0          
    for row in rows:
        last_name_raw = row.get(last_name_col, "").strip() if last_name_col else ""
        shift_detected = "," in last_name_raw

        if shift_detected:
            shift_detected_count += 1
            name = normalize_name(last_name_raw)
            raw_id = get_shifted_value(row, fieldnames, id_col, shift=-1) if id_col else None
            player_id = (raw_id or "").strip()
            speed_val = get_shifted_value(row, fieldnames, speed_col, shift=-1) if speed_col else None
        else:
            player_id = row.get(id_col, "").strip() if id_col else ""
            if name_col:
                name = normalize_name(row.get(name_col, ""))
            elif last_name_col and first_name_col:
                name = f"{row.get(first_name_col, '').strip()} {last_name_raw}"
            else:
                name = ""
            speed_val = row.get(speed_col) if speed_col else None

        if not player_id:
            continue

        sprint_speed_ft_s = to_float(speed_val)
       if sprint_speed_ft_s is None:
            missing_speed_count += 1
            continue
        sprint_speed_data[player_id] = {
            "name": name,
            "sprint_speed_ft_s": sprint_speed_ft_s,
            "SPD": sprint_speed_to_spd_scale(sprint_speed_ft_s),
        }

    print(f"Rows where the name/column shift was detected and corrected: {shift_detected_count} of {len(rows)}")
    print(f"Skipped {missing_speed_count} players with no sprint speed reported by Savant.")
    print(f"Built sprint speed data for {len(sprint_speed_data)} hitters.")

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(sprint_speed_data, f, indent=2)
    print(f"\nWrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
