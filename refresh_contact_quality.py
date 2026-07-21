"""
refresh_contact_quality.py

Pulls real Statcast contact-quality metrics (Barrel%, Hard-Hit%, xwOBA,
average exit velocity) for MLB hitters from Baseball Savant's free, public
"custom leaderboard" CSV export -- this is a different, more commonly-used
export than the park-factors leaderboard that failed previously (that one
returned an HTML page instead of CSV; this "leaderboard/custom" endpoint is
the same one referenced by pybaseball and various other established public
tools that pull Statcast data successfully, so there's more real-world
precedent behind this URL pattern working).

STILL UNTESTED LIVE -- same caveat as before: this environment has no
network access, so this hasn't been run against the actual live site. The
script prints every column it finds immediately at the start specifically
so any mismatch is easy to catch and fix in one pass.

WHAT THIS DOES
---------------
1. Downloads the Statcast custom batter leaderboard CSV for the current
   season (minimum plate appearance qualifier applied so bench/rookie
   samples aren't wildly noisy).
2. Writes MLB_Predictor/contact_quality.json, keyed by player full name
   (matching the "Player" field already used in roster_data.json), with
   barrel_pct, hardhit_pct, xwoba, and avg_exit_velo for each hitter found.
3. This is a SEPARATE file from roster_data.json (not merged into it) --
   the app loads it independently and enriches views like the HR
   leaderboard with it when available, falling back gracefully to not
   showing these columns if this file is missing.

Unlike park factors, this DOES benefit from being refreshed on the same
nightly schedule as rosters -- contact-quality stats accumulate and shift
as the season progresses, same as any other rate stat.
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

# Savant's "custom leaderboard" CSV export. The `selections` list picks which
# stat columns come back; `min=50` requires at least 50 batted-ball events so
# small samples don't produce noisy/meaningless percentages.
SAVANT_URL = (
    "https://baseballsavant.mlb.com/leaderboard/custom"
    f"?year={CURRENT_SEASON}&type=batter&min=50"
    "&selections=barrel_batted_rate,hard_hit_percent,xwoba,exit_velocity_avg"
    "&csv=true"
)

# Candidate column names to try, in priority order. Savant's custom
# leaderboard exports commonly use these exact names, but this is the same
# defensive pattern as the roster script -- if the real export uses
# something slightly different, the printed column list at runtime is the
# fast way to catch and fix it.
#
# CONFIRMED from a live run: Savant returns separate "last_name" and
# "first_name" columns (not one combined field), and the raw header row has
# a UTF-8 BOM + stray quote characters stuck to the first couple of column
# names (e.g. '\ufeff"last_name"') -- both handled below.
NAME_COLUMN_CANDIDATES = ["player_name", "name"]
LAST_NAME_COLUMN_CANDIDATES = ["last_name"]
FIRST_NAME_COLUMN_CANDIDATES = ["first_name"]
PLAYER_ID_COLUMN_CANDIDATES = ["player_id", "playerid", "mlbid", "mlb_id"]
BARREL_COLUMN_CANDIDATES = ["barrel_batted_rate", "brl_percent", "barrel_pct"]
HARDHIT_COLUMN_CANDIDATES = ["hard_hit_percent", "hardhit_percent"]
XWOBA_COLUMN_CANDIDATES = ["xwoba", "est_woba"]
EXIT_VELO_COLUMN_CANDIDATES = ["exit_velocity_avg", "avg_hit_speed"]


def clean_column_name(name):
    """Strips the UTF-8 BOM character and stray quote marks that Savant's
    CSV export sticks onto some header names (confirmed from a live run --
    e.g. the raw first column comes back as '\\ufeff"last_name"' instead of
    just 'last_name'), so column matching below works reliably."""
    return name.replace("\ufeff", "").replace('"', "").strip()


def fetch_csv_rows(url):
    resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    reader = csv.DictReader(io.StringIO(resp.text))
    raw_rows = list(reader)
    cleaned_fieldnames = [clean_column_name(f) for f in reader.fieldnames]
    # Re-key every row using the cleaned column names so the rest of the
    # script never has to deal with the BOM/quote artifacts again.
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
    """Savant's custom leaderboard sometimes returns a single combined name
    field as 'Last, First' -- this converts that to 'First Last' to match
    roster_data.json's format. If the name doesn't contain a comma, it's
    returned unchanged (already in the right format). Not used when
    first_name/last_name come back as separate columns (see main()) --
    those get combined directly instead."""
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
    print("^ If the fields below show as 'None', send this column list back")
    print("  and the field names in this script can be corrected in one pass.\n")

    if not rows:
        print("[ERROR] No rows returned -- check the URL/params above against what's")
        print("        actually on https://baseballsavant.mlb.com/leaderboard/custom")
        sys.exit(1)

    id_col = find_column(fieldnames, PLAYER_ID_COLUMN_CANDIDATES)
    name_col = find_column(fieldnames, NAME_COLUMN_CANDIDATES)
    last_name_col = find_column(fieldnames, LAST_NAME_COLUMN_CANDIDATES)
    first_name_col = find_column(fieldnames, FIRST_NAME_COLUMN_CANDIDATES)
    barrel_col = find_column(fieldnames, BARREL_COLUMN_CANDIDATES)
    hardhit_col = find_column(fieldnames, HARDHIT_COLUMN_CANDIDATES)
    xwoba_col = find_column(fieldnames, XWOBA_COLUMN_CANDIDATES)
    velo_col = find_column(fieldnames, EXIT_VELO_COLUMN_CANDIDATES)

    print(f"Using columns -> id: {id_col}, name: {name_col}, last/first: {last_name_col}/{first_name_col}, "
          f"barrel: {barrel_col}, hardhit: {hardhit_col}, xwoba: {xwoba_col}, exit velo: {velo_col}\n")
    if not id_col:
        print("[ERROR] Could not find a player ID column. Can't key the output reliably without one")
        print("        (name-only matching against roster_data.json is fragile -- 'Matt' vs")
        print("        'Matthew' style formatting differences between data sources cause silent")
        print("        mismatches, which is exactly the bug this ID-based keying fixes).")
        sys.exit(1)

    contact_quality = {}
    for row in rows:
        player_id = row.get(id_col, "").strip()
        if not player_id:
            continue

        # Name is still captured for readability/debugging in the output file,
        # but PlayerID (matched against roster_data.json's PlayerID field) is
        # what the app actually keys off of -- this is what actually fixes
        # the "every value shows None" bug, not the name itself.
        if name_col:
            name = normalize_name(row.get(name_col, ""))
        elif last_name_col and first_name_col:
            name = f"{row.get(first_name_col, '').strip()} {row.get(last_name_col, '').strip()}"
        else:
            name = ""

        contact_quality[player_id] = {
            "name": name,
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
