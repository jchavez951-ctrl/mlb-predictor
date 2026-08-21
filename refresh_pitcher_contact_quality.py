"""
refresh_pitcher_contact_quality.py

Pitcher-side companion to refresh_contact_quality.py. Pulls contact quality
ALLOWED (Barrel%, Hard-Hit%, xwOBA, avg exit velo) for MLB pitchers from
Baseball Savant's custom leaderboard CSV export.

Writes MLB_Predictor/pitcher_contact_quality.json, keyed by MLB PlayerID.

SAMPLE SIZE -- read this before changing the filter
----------------------------------------------------
Confirmed from a live run: Savant ACCEPTS `bbe` as a pitcher selection but
returns an empty column for it. `pa` comes back populated, so PA is used as
the sample-size measure for both the minimum-workload filter and the
weighting of league averages. `attempts` is also requested in case that's
the real column id for batted-ball events on the pitcher leaderboard -- if
it populates, it's preferred automatically and PA becomes the fallback.

This matters because pitcher contact quality allowed is far noisier than
the hitter version. Hitters largely own their contact; pitchers only partly
do. Barrel%-allowed doesn't stabilize until well north of 200 batted-ball
events, so a reliever with 40 PA has numbers that look like signal and
aren't. Without a working filter every one of those pitchers lands in the
file at equal weight.

RUN FROM THE REPO ROOT:  python refresh_pitcher_contact_quality.py
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
OUTPUT_PATH = os.path.join("MLB_Predictor", "pitcher_contact_quality.json")

CORE_SELECTIONS = "barrel_batted_rate,hard_hit_percent,xwoba,exit_velocity_avg"
EXTRA_SELECTIONS = "bbe,attempts,pa,groundballs_percent,flyballs_percent"

SAVANT_URL = (
    "https://baseballsavant.mlb.com/leaderboard/custom"
    f"?year={CURRENT_SEASON}&type=pitcher&min=1"
    f"&selections={CORE_SELECTIONS},{EXTRA_SELECTIONS}"
    "&csv=true"
)

NAME_COLUMN_CANDIDATES = ["player_name", "name"]
LAST_NAME_COLUMN_CANDIDATES = ["last_name"]
FIRST_NAME_COLUMN_CANDIDATES = ["first_name"]
PLAYER_ID_COLUMN_CANDIDATES = ["player_id", "playerid", "mlbid", "mlb_id", "pitcher"]
BARREL_COLUMN_CANDIDATES = ["barrel_batted_rate", "brl_percent", "barrel_pct"]
HARDHIT_COLUMN_CANDIDATES = ["hard_hit_percent", "hardhit_percent"]
XWOBA_COLUMN_CANDIDATES = ["xwoba", "est_woba"]
EXIT_VELO_COLUMN_CANDIDATES = ["exit_velocity_avg", "avg_hit_speed"]
BBE_COLUMN_CANDIDATES = ["attempts", "bbe", "batted_balls"]
PA_COLUMN_CANDIDATES = ["pa", "plate_appearances"]
GB_COLUMN_CANDIDATES = ["groundballs_percent", "gb_percent"]
FB_COLUMN_CANDIDATES = ["flyballs_percent", "fb_percent"]

# Minimum workload to be included at all, measured in whichever sample
# column actually populates. Roughly a month of starts, or most of a
# season for a reliever. Everything below this is noise dressed as data.
MIN_SAMPLE = 100


def clean_column_name(name):
    return name.replace("\ufeff", "").replace('"', "").strip()


def fetch_csv_rows(url):
    resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
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
    print(f"Fetching PITCHER contact-quality-allowed from Baseball Savant for {CURRENT_SEASON}...")
    print(f"URL: {SAVANT_URL}\n")

    rows, fieldnames = fetch_csv_rows(SAVANT_URL)
    print(f"Columns found in the raw CSV: {fieldnames}")
    print(f"Total rows returned: {len(rows)}")
    if rows:
        print(f"First row (for inspection): {rows[0]}\n")

    if not rows:
        print("[ERROR] No rows returned -- check the URL/params.")
        sys.exit(1)

    id_col = find_column(fieldnames, PLAYER_ID_COLUMN_CANDIDATES)
    name_col = find_column(fieldnames, NAME_COLUMN_CANDIDATES)
    last_name_col = find_column(fieldnames, LAST_NAME_COLUMN_CANDIDATES)
    first_name_col = find_column(fieldnames, FIRST_NAME_COLUMN_CANDIDATES)
    barrel_col = find_column(fieldnames, BARREL_COLUMN_CANDIDATES)
    hardhit_col = find_column(fieldnames, HARDHIT_COLUMN_CANDIDATES)
    xwoba_col = find_column(fieldnames, XWOBA_COLUMN_CANDIDATES)
    velo_col = find_column(fieldnames, EXIT_VELO_COLUMN_CANDIDATES)
    bbe_col = find_column(fieldnames, BBE_COLUMN_CANDIDATES)
    pa_col = find_column(fieldnames, PA_COLUMN_CANDIDATES)
    gb_col = find_column(fieldnames, GB_COLUMN_CANDIDATES)
    fb_col = find_column(fieldnames, FB_COLUMN_CANDIDATES)

    print(f"Using columns -> id: {id_col}, last/first: {last_name_col}/{first_name_col}")
    print(f"                 barrel: {barrel_col}, hardhit: {hardhit_col}, "
          f"xwoba: {xwoba_col}, exit velo: {velo_col}")
    print(f"                 bbe: {bbe_col}, pa: {pa_col}, gb: {gb_col}, fb: {fb_col}\n")

    if not id_col:
        print("[ERROR] Could not find a player ID column.")
        sys.exit(1)

    def get_shifted_value(row, col_name, shift=-1):
        """Savant's data rows merge last_name and first_name into one field
        even though the header lists them separately, pushing every later
        value one position earlier than the header implies."""
        if col_name not in fieldnames:
            return None
        idx = fieldnames.index(col_name) + shift
        if 0 <= idx < len(fieldnames):
            return row.get(fieldnames[idx])
        return None

    # First pass: parse everything, no filtering yet, so we can see which
    # sample column actually has data before deciding what to filter on.
    parsed = []
    shift_detected_count = 0

    for row in rows:
        last_name_raw = row.get(last_name_col, "").strip() if last_name_col else ""
        shift_detected = "," in last_name_raw

        if shift_detected:
            shift_detected_count += 1
            name = normalize_name(last_name_raw)

            def get(col, _row=row):
                return get_shifted_value(_row, col, shift=-1) if col else None
        else:
            if name_col:
                name = normalize_name(row.get(name_col, ""))
            elif last_name_col and first_name_col:
                name = f"{row.get(first_name_col, '').strip()} {last_name_raw}"
            else:
                name = ""

            def get(col, _row=row):
                return _row.get(col) if col else None

        player_id = (get(id_col) or "").strip()
        if not player_id:
            continue

        parsed.append((player_id, {
            "name": name,
            "barrel_pct_allowed": to_float(get(barrel_col)),
            "hardhit_pct_allowed": to_float(get(hardhit_col)),
            "xwoba_allowed": to_float(get(xwoba_col)),
            "avg_exit_velo_allowed": to_float(get(velo_col)),
            "gb_pct": to_float(get(gb_col)),
            "fb_pct": to_float(get(fb_col)),
            "bbe": to_float(get(bbe_col)),
            "pa": to_float(get(pa_col)),
        }))

    print(f"Rows where the name/column shift was detected and corrected: "
          f"{shift_detected_count} of {len(rows)}")

    # Pick whichever sample column actually populated. Confirmed live:
    # `bbe` comes back empty on the pitcher leaderboard, `pa` does not.
    bbe_populated = sum(1 for _, e in parsed if e["bbe"] is not None)
    pa_populated = sum(1 for _, e in parsed if e["pa"] is not None)
    print(f"Sample columns populated -> bbe: {bbe_populated}, pa: {pa_populated}")

    if bbe_populated > len(parsed) * 0.5:
        sample_field = "bbe"
    elif pa_populated > len(parsed) * 0.5:
        sample_field = "pa"
    else:
        print("\n[ERROR] Neither bbe nor pa populated. Without a sample-size column")
        print("        there's no way to filter noise or weight the league average,")
        print("        and every pitcher would be treated as equally trustworthy.")
        print("        Check the column dump above for the real name and stop here.")
        sys.exit(1)

    print(f"Using '{sample_field}' as the sample-size measure "
          f"(minimum {MIN_SAMPLE} to be included).\n")

    pitcher_quality = {}
    dropped_low_sample = 0
    for player_id, entry in parsed:
        sample = entry.get(sample_field)
        if sample is None or sample < MIN_SAMPLE:
            dropped_low_sample += 1
            continue
        entry["sample_field"] = sample_field
        pitcher_quality[player_id] = entry

    print(f"Dropped for {sample_field} < {MIN_SAMPLE}: {dropped_low_sample}")
    print(f"Built contact-quality-allowed data for {len(pitcher_quality)} pitchers.")

    if len(pitcher_quality) < 100:
        print("\n[WARN] Fewer than 100 pitchers survived -- that may be too aggressive")
        print("       a threshold to cover every day's probable starters. Check that")
        print("       your usual starters are present before wiring this in.")

    league_avg = {}
    for field in ("barrel_pct_allowed", "hardhit_pct_allowed", "xwoba_allowed",
                  "avg_exit_velo_allowed", "gb_pct", "fb_pct"):
        num = den = 0.0
        for entry in pitcher_quality.values():
            v, w = entry.get(field), entry.get(sample_field)
            if v is not None and w:
                num += v * w
                den += w
        league_avg[field] = round(num / den, 4) if den else None

    print(f"\nLeague averages ({sample_field}-weighted): {json.dumps(league_avg, indent=2)}")

    print("\nSample rows -- look these three up on baseballsavant.mlb.com:")
    for pid, e in list(pitcher_quality.items())[:3]:
        print(f"  {pid} {e['name']}: {sample_field}={e[sample_field]} "
              f"barrel={e['barrel_pct_allowed']} hardhit={e['hardhit_pct_allowed']} "
              f"xwoba={e['xwoba_allowed']} velo={e['avg_exit_velo_allowed']} "
              f"gb={e['gb_pct']} fb={e['fb_pct']}")

    pitcher_quality["_league_avg"] = league_avg
    pitcher_quality["_sample_field"] = sample_field

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(pitcher_quality, f, indent=2)
    print(f"\nWrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
