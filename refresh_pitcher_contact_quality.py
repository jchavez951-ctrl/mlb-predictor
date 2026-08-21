"""
refresh_pitcher_contact_quality.py

Pitcher-side companion to refresh_contact_quality.py. Pulls contact quality
ALLOWED (Barrel%, Hard-Hit%, xwOBA, avg exit velo) for MLB pitchers from
Baseball Savant's custom leaderboard CSV export.

Same structure, same URL pattern, same BOM/column-shift handling as the
hitter script -- the only real differences are type=pitcher, two extra
selections (batted-ball count + batted-ball mix), and the output filename.

WHAT THIS DOES
---------------
1. Downloads the Statcast custom PITCHER leaderboard CSV for the current season.
2. Writes MLB_Predictor/pitcher_contact_quality.json, keyed by MLB PlayerID
   (same keying as contact_quality.json -- names differ in formatting between
   the MLB Stats API and Savant, IDs don't).
3. Also stores a "_league_avg" entry (BBE-weighted). Player IDs are all
   digits so this reserved key can never collide with one, and any lookup
   doing data.get(str(pid)) will simply never see it.

WHY BBE IS PULLED
-----------------
Pitcher contact quality allowed is far noisier than the hitter version --
hitters largely own their contact, pitchers only partly do. Barrel%-allowed
doesn't stabilize until well north of 200 batted-ball events, so an August
starter sitting at 150 BBE is still mostly noise. Storing BBE per pitcher
plus the league average lets the app regress small samples toward league
average later, instead of treating a 40-BBE swingman's 12% barrel rate as
if it meant something.

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

# Core selections -- these four are the exact ones already proven to work on
# the batter leaderboard, and Savant uses the same column ids on the pitcher
# side (they describe the batted ball, not who produced it).
CORE_SELECTIONS = "barrel_batted_rate,hard_hit_percent,xwoba,exit_velocity_avg"

# Extra selections that are NOT proven yet. Batted-ball mix is the single
# biggest pitcher-specific HR lever -- a 55% groundball starter suppresses
# home runs through pure batted-ball profile regardless of how hard he's hit
# -- so it's worth pulling, but the exact column ids are a guess. If they
# come back missing, the script warns and carries on with the core four
# rather than dying; nothing downstream depends on them yet.
EXTRA_SELECTIONS = "bbe,pa,groundballs_percent,flyballs_percent"

SAVANT_URL = (
    "https://baseballsavant.mlb.com/leaderboard/custom"
    f"?year={CURRENT_SEASON}&type=pitcher&min=1"
    f"&selections={CORE_SELECTIONS},{EXTRA_SELECTIONS}"
    "&csv=true"
)

# Same defensive candidate-list pattern as the hitter script: the printed
# column dump at runtime is the fast way to fix any mismatch in one pass.
NAME_COLUMN_CANDIDATES = ["player_name", "name"]
LAST_NAME_COLUMN_CANDIDATES = ["last_name"]
FIRST_NAME_COLUMN_CANDIDATES = ["first_name"]
PLAYER_ID_COLUMN_CANDIDATES = ["player_id", "playerid", "mlbid", "mlb_id", "pitcher"]
BARREL_COLUMN_CANDIDATES = ["barrel_batted_rate", "brl_percent", "barrel_pct",
                            "barrels_per_bbe_percent"]
HARDHIT_COLUMN_CANDIDATES = ["hard_hit_percent", "hardhit_percent"]
XWOBA_COLUMN_CANDIDATES = ["xwoba", "est_woba"]
EXIT_VELO_COLUMN_CANDIDATES = ["exit_velocity_avg", "avg_hit_speed"]
BBE_COLUMN_CANDIDATES = ["bbe", "batted_balls", "attempts"]
PA_COLUMN_CANDIDATES = ["pa", "plate_appearances"]
GB_COLUMN_CANDIDATES = ["groundballs_percent", "gb_percent", "ground_balls_percent"]
FB_COLUMN_CANDIDATES = ["flyballs_percent", "fb_percent", "fly_balls_percent"]

# Pitchers below this many batted-ball events are dropped entirely. Long
# relievers and September call-ups produce numbers that look like signal and
# aren't. Starters clear this comfortably by midseason.
MIN_BBE = 50


def clean_column_name(name):
    """Strips the UTF-8 BOM and stray quote marks Savant sticks onto some
    header names (e.g. '\\ufeff"last_name"'), same as the hitter script."""
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
    print(f"Total rows returned: {len(rows)}  (should be several hundred, one per pitcher)")
    if rows:
        print(f"First row (for inspection): {rows[0]}\n")
    print("^ If fields show as 'None' or the row count looks wrong, send this block back.\n")

    if not rows:
        print("[ERROR] No rows returned -- check the URL/params against")
        print("        https://baseballsavant.mlb.com/leaderboard/custom")
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

    print(f"Using columns -> id: {id_col}, name: {name_col}, last/first: {last_name_col}/{first_name_col}")
    print(f"                 barrel: {barrel_col}, hardhit: {hardhit_col}, xwoba: {xwoba_col}, "
          f"exit velo: {velo_col}")
    print(f"                 bbe: {bbe_col}, pa: {pa_col}, gb: {gb_col}, fb: {fb_col}\n")

    if not id_col:
        print("[ERROR] Could not find a player ID column -- can't key the output reliably.")
        sys.exit(1)

    for label, col in (("BBE", bbe_col), ("GB%", gb_col), ("FB%", fb_col)):
        if not col:
            print(f"[WARN] {label} column not found. Those selection ids were a guess -- "
                  f"check the column dump above for the real")
            print(f"       name and update the candidate list + EXTRA_SELECTIONS. "
                  f"Continuing without it.")

    if not bbe_col:
        print("[WARN] Without BBE there's no sample size to regress on, so every pitcher's")
        print("       numbers get treated as equally trustworthy. Worth fixing before this")
        print("       feeds the simulation.\n")

    def get_shifted_value(row, col_name, shift=-1):
        """Savant's data rows merge last_name and first_name into one field
        (e.g. "Skubal, Tarik") even though the header lists them separately,
        pushing every later value one position earlier than the header
        implies. Reads from the adjusted position when that's detected."""
        if col_name not in fieldnames:
            return None
        idx = fieldnames.index(col_name) + shift
        if 0 <= idx < len(fieldnames):
            return row.get(fieldnames[idx])
        return None

    pitcher_quality = {}
    shift_detected_count = 0
    dropped_low_bbe = 0

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

        bbe_val = to_float(get(bbe_col))
        if bbe_col and bbe_val is not None and bbe_val < MIN_BBE:
            dropped_low_bbe += 1
            continue

        pitcher_quality[player_id] = {
            "name": name,
            "barrel_pct_allowed": to_float(get(barrel_col)),
            "hardhit_pct_allowed": to_float(get(hardhit_col)),
            "xwoba_allowed": to_float(get(xwoba_col)),
            "avg_exit_velo_allowed": to_float(get(velo_col)),
            "gb_pct": to_float(get(gb_col)),
            "fb_pct": to_float(get(fb_col)),
            "bbe": bbe_val,
            "pa": to_float(get(pa_col)),
        }

    print(f"Rows where the name/column shift was detected and corrected: "
          f"{shift_detected_count} of {len(rows)}")
    print(f"Dropped for BBE < {MIN_BBE}: {dropped_low_bbe}")
    print(f"Built contact-quality-allowed data for {len(pitcher_quality)} pitchers.")

    if len(pitcher_quality) < 100:
        print("\n[WARN] Fewer than 100 pitchers survived. Expected roughly 300-450 with")
        print("       any real workload. Don't wire this into the app yet -- a partial")
        print("       pull means starters silently fall back to placeholder values.")

    # BBE-weighted league averages, stored so the app can regress small
    # samples toward the mean without recomputing on every page load.
    league_avg = {}
    for field in ("barrel_pct_allowed", "hardhit_pct_allowed", "xwoba_allowed",
                  "avg_exit_velo_allowed", "gb_pct", "fb_pct"):
        num = den = 0.0
        for entry in pitcher_quality.values():
            v, w = entry.get(field), entry.get("bbe")
            if v is not None and w:
                num += v * w
                den += w
        league_avg[field] = round(num / den, 4) if den else None

    print(f"\nLeague averages (BBE-weighted): {json.dumps(league_avg, indent=2)}")

    print("\nSample rows -- look these three up on baseballsavant.mlb.com before")
    print("wiring this in. If they're plausible but wrong, the values shifted a column:")
    for pid, e in list(pitcher_quality.items())[:3]:
        print(f"  {pid} {e['name']}: bbe={e['bbe']} barrel={e['barrel_pct_allowed']} "
              f"hardhit={e['hardhit_pct_allowed']} xwoba={e['xwoba_allowed']} "
              f"gb={e['gb_pct']} fb={e['fb_pct']}")

    pitcher_quality["_league_avg"] = league_avg

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(pitcher_quality, f, indent=2)
    print(f"\nWrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
