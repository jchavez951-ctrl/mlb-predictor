"""
refresh_park_factors.py

Pulls park factor data from Baseball Savant's free, public Statcast Park
Factors leaderboard (baseballsavant.mlb.com -- owned by MLB, no paywall, no
API key needed) and converts it into the run_mult / hr_mult / babip_mult
format the simulator's BALLPARK_ENV already uses.

UNLIKE refresh_rosters.py, THIS IS NOT MEANT TO RUN NIGHTLY. Park factors
(stadium dimensions, altitude, typical wind patterns) barely change year to
year -- there's no injury-list-style daily churn to chase here. Run this
manually every once in a while (start of season, or if you notice something
looks off), not on an automated daily schedule.

IMPORTANT CAVEAT -- READ BEFORE RUNNING
------------------------------------------
This has NOT been tested against the live Baseball Savant export (this
environment has no network access). Savant's exact CSV column names are
based on documented patterns from other tools that use this same data
source, but they could be slightly different in practice. The script prints
every column it finds in the raw CSV right at the start specifically so you
can check that against what it ends up using -- if the numbers look wrong
or it can't find a column it needs, send me that printed column list and
I'll fix the exact field names in one pass, same as we did with the roster
script.

WHAT THIS DOES
---------------
1. Downloads the Statcast Park Factors CSV export for the current season.
2. For each team, converts Savant's index values (100 = league average,
   e.g. 108 = 8% above average) into the multiplier format this simulator
   uses (1.0 = league average, e.g. 1.08 = 8% above average) -- literally
   just dividing by 100.
3. Writes MLB_Predictor/ballpark_env.json in the same team-name-keyed shape
   as the existing hardcoded BALLPARK_ENV dict.
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
OUTPUT_PATH = os.path.join("MLB_Predictor", "ballpark_env.json")

# Savant's CSV export URL for the Statcast Park Factors leaderboard. The
# leaderboard itself supports a &csv=true suffix on its normal browser URL
# to get raw data instead of the rendered page -- this is the same pattern
# used by pybaseball and other established Savant-scraping tools.
SAVANT_URL = (
    "https://baseballsavant.mlb.com/leaderboard/statcast-park-factors"
    f"?type=year&year={CURRENT_SEASON}&batSide=&stat=index_wOBA&condition=All&rolling=no&csv=true"
)

# Maps Savant's team abbreviations to this app's full team names. If Savant's
# actual export uses full names instead of abbreviations, the lookup logic
# below tries both, but this table needs to exist either way for the
# abbreviation case.
TEAM_ABBR_TO_NAME = {
    "ARI": "Arizona Diamondbacks", "ATL": "Atlanta Braves", "BAL": "Baltimore Orioles",
    "BOS": "Boston Red Sox", "CHC": "Chicago Cubs", "CWS": "Chicago White Sox",
    "CIN": "Cincinnati Reds", "CLE": "Cleveland Guardians", "COL": "Colorado Rockies",
    "DET": "Detroit Tigers", "HOU": "Houston Astros", "KC": "Kansas City Royals",
    "LAA": "Los Angeles Angels", "LAD": "Los Angeles Dodgers", "MIA": "Miami Marlins",
    "MIL": "Milwaukee Brewers", "MIN": "Minnesota Twins", "NYM": "New York Mets",
    "NYY": "New York Yankees", "ATH": "Athletics", "OAK": "Athletics", "PHI": "Philadelphia Phillies",
    "PIT": "Pittsburgh Pirates", "SD": "San Diego Padres", "SF": "San Francisco Giants",
    "SEA": "Seattle Mariners", "STL": "St. Louis Cardinals", "TB": "Tampa Bay Rays",
    "TEX": "Texas Rangers", "TOR": "Toronto Blue Jays", "WSH": "Washington Nationals",
    "WAS": "Washington Nationals",
}

# Candidate column names to try, in priority order, for each stat we need.
# Savant CSV exports for this leaderboard commonly use an "index_" prefix
# (e.g. "index_hr", "index_woba"), but the exact set of columns included can
# vary. Printing the real header list at runtime (see main()) is the safety
# net if none of these guesses match.
TEAM_COLUMN_CANDIDATES = ["team", "team_abbrev", "home_team", "abbreviation"]
HR_COLUMN_CANDIDATES = ["index_hr", "hr_index", "index_HR", "HR"]
RUNS_COLUMN_CANDIDATES = ["index_woba", "index_runs", "woba_index", "index_R", "runs_index"]
BABIP_COLUMN_CANDIDATES = ["index_1b", "index_babip", "babip_index", "index_hits"]


def fetch_csv_rows(url):
    resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    return rows, reader.fieldnames


def find_column(fieldnames, candidates):
    for c in candidates:
        if c in fieldnames:
            return c
    # case-insensitive fallback pass
    lower_map = {f.lower(): f for f in fieldnames}
    for c in candidates:
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    return None


def to_multiplier(raw_value, default=1.0):
    try:
        return round(float(raw_value) / 100.0, 3)
    except (TypeError, ValueError):
        return default


def main():
    print(f"Fetching park factors from Baseball Savant for {CURRENT_SEASON}...")
    print(f"URL: {SAVANT_URL}\n")

    rows, fieldnames = fetch_csv_rows(SAVANT_URL)
    print(f"Columns found in the raw CSV: {fieldnames}\n")
    print("^ If the script below reports missing columns, send that list back and the")
    print("  field names in this script can be corrected in one pass.\n")

    if not rows:
        print("[ERROR] No rows returned -- check the URL/params above against what's")
        print("        actually on https://baseballsavant.mlb.com/leaderboard/statcast-park-factors")
        sys.exit(1)

    team_col = find_column(fieldnames, TEAM_COLUMN_CANDIDATES)
    hr_col = find_column(fieldnames, HR_COLUMN_CANDIDATES)
    runs_col = find_column(fieldnames, RUNS_COLUMN_CANDIDATES)
    babip_col = find_column(fieldnames, BABIP_COLUMN_CANDIDATES)

    print(f"Using columns -> team: {team_col}, HR: {hr_col}, runs/wOBA: {runs_col}, BABIP-like: {babip_col}\n")
    if not team_col:
        print("[ERROR] Could not find a team identifier column. Can't proceed without one.")
        sys.exit(1)

    ballpark_env = {}
    for row in rows:
        raw_team = row.get(team_col, "").strip()
        team_name = TEAM_ABBR_TO_NAME.get(raw_team.upper()) or (raw_team if raw_team in TEAM_ABBR_TO_NAME.values() else None)
        if not team_name:
            print(f"  [WARN] Unrecognized team identifier '{raw_team}' -- skipping this row")
            continue

        hr_mult = to_multiplier(row.get(hr_col)) if hr_col else 1.0
        run_mult = to_multiplier(row.get(runs_col)) if runs_col else 1.0
        babip_mult = to_multiplier(row.get(babip_col)) if babip_col else 1.0

        ballpark_env[team_name] = {
            "run_mult": run_mult,
            "hr_mult": hr_mult,
            "babip_mult": babip_mult,
        }

    print(f"\nBuilt park factors for {len(ballpark_env)} teams (expected 30).")
    if len(ballpark_env) < 30:
        missing = set(TEAM_ABBR_TO_NAME.values()) - set(ballpark_env.keys())
        print(f"[WARN] Missing teams: {missing}")

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(ballpark_env, f, indent=2)
    print(f"\nWrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
