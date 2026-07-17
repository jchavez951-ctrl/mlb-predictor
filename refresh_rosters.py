"""
refresh_rosters.py

Nightly refresh script for the MLB prop simulator's roster data.

WHAT THIS DOES
---------------
Pulls current 40-man rosters and season stat lines for all 30 MLB teams from
the free, public MLB Stats API (https://statsapi.mlb.com/api/v1/ -- no API key
required), computes the same derived rate stats the simulator's ROSTER_DATABASE
already uses (BB_RATE, K_RATE, HR_PA_RATE, BABIP, 1B/2B/3B hit-type splits,
BB_ALLOWED_RATE, K_ALLOWED_RATE, HR_PA_ALLOWED_RATE, BABIP_ALLOWED, etc.), and
writes the result out as roster_data.json in the same folder.

WHAT THIS DOES NOT DO (be aware of these before wiring it into your cron job)
-------------------------------------------------------------------------------
1. It does NOT know today's actual starting 9 -- real teams typically don't
   release lineups until 1-3 hours before first pitch. This script refreshes
   the full-season RATE STATS for every player on the 40-man (so numbers stay
   current), but you still pick which 9 hitters/which pitcher are "in the
   game" the same way you do now.
2. SPD (speed rating, 0-100 scale) isn't in this API in a directly usable
   form -- true sprint speed lives in Statcast/Baseball Savant, a different
   data source. This script assigns a neutral default (55) for every player;
   if you want real speed differentiation, that's a separate follow-up.
3. Pitcher "Role" (SP vs RP vs Closer) isn't an explicit field anywhere in
   the API -- it's inferred here from games-started ratio and saves count.
   This heuristic will occasionally misclassify a swingman or a committee
   closer situation; spot-check it after the first run.
4. This has NOT been run against the live API yet (this environment has no
   network access). Test it yourself before trusting it -- see "HOW TO TEST"
   at the bottom of this file.

REQUIREMENTS
------------
pip install requests --break-system-packages   (on PythonAnywhere)
"""

import json
import time
import sys
import os
import base64
from datetime import datetime

try:
    import requests
except ImportError:
    print("This script needs the 'requests' library. On PythonAnywhere, run:")
    print("    pip install requests --break-system-packages")
    sys.exit(1)

# ----------------------------------------------------
# GITHUB PUBLISH CONFIG
# ----------------------------------------------------
# This script runs on PythonAnywhere, but the Streamlit app is deployed from
# GitHub -- writing roster_data.json locally isn't enough, it has to actually
# land in the repo for Streamlit Cloud to pick it up. This uses the GitHub
# API directly (no git command-line setup needed on PythonAnywhere).
#
# The token is read from an environment variable, NEVER hardcoded here --
# see the "HOW TO SET THIS UP" notes at the bottom of this file.
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = "jchavez951-ctrl/mlb-predictor"       # owner/repo
GITHUB_FILE_PATH = "MLB_Predictor/roster_data.json"  # path within the repo, alongside spot_check.py
GITHUB_BRANCH = "main"


def push_to_github(local_json_path):
    """Uploads the freshly-written roster_data.json to the GitHub repo that
    Streamlit Cloud deploys from, using the GitHub Contents API. This is a
    normal "create or update file" API call -- it needs the file's current
    SHA if it already exists (to update it) or no SHA at all (to create it
    for the first time)."""
    if not GITHUB_TOKEN:
        print("\n[WARN] No GITHUB_TOKEN environment variable found -- skipping GitHub push.")
        print("       roster_data.json was written locally but NOT published to your repo.")
        print("       See 'HOW TO SET THIS UP' at the bottom of this file.")
        return False

    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    with open(local_json_path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode("utf-8")

    # Check whether the file already exists in the repo, to get its SHA
    # (required by GitHub's API when updating an existing file).
    existing_sha = None
    resp = requests.get(api_url, headers=headers, params={"ref": GITHUB_BRANCH}, timeout=15)
    if resp.status_code == 200:
        existing_sha = resp.json().get("sha")

    payload = {
        "message": f"Nightly roster refresh -- {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "content": content_b64,
        "branch": GITHUB_BRANCH,
    }
    if existing_sha:
        payload["sha"] = existing_sha

    put_resp = requests.put(api_url, headers=headers, json=payload, timeout=30)
    if put_resp.status_code in (200, 201):
        print(f"\nPushed roster_data.json to GitHub ({GITHUB_REPO}, branch {GITHUB_BRANCH}).")
        return True
    else:
        print(f"\n[ERROR] GitHub push failed ({put_resp.status_code}): {put_resp.text[:300]}")
        return False

BASE_URL = "https://statsapi.mlb.com/api/v1"
CURRENT_SEASON = datetime.now().year

# MLB's official numeric team IDs. These are stable and don't change year to
# year. Verify these against https://statsapi.mlb.com/api/v1/teams?sportId=1
# if anything looks off after a test run -- team IDs are the one thing that
# absolutely must be exactly right for this whole script to work.
TEAM_IDS = {
    "Arizona Diamondbacks": 109, "Atlanta Braves": 144, "Baltimore Orioles": 110,
    "Boston Red Sox": 111, "Chicago Cubs": 112, "Chicago White Sox": 145,
    "Cincinnati Reds": 113, "Cleveland Guardians": 114, "Colorado Rockies": 115,
    "Detroit Tigers": 116, "Houston Astros": 117, "Kansas City Royals": 118,
    "Los Angeles Angels": 108, "Los Angeles Dodgers": 119, "Miami Marlins": 146,
    "Milwaukee Brewers": 158, "Minnesota Twins": 142, "New York Mets": 121,
    "New York Yankees": 147, "Athletics": 133, "Philadelphia Phillies": 143,
    "Pittsburgh Pirates": 134, "San Diego Padres": 135, "San Francisco Giants": 137,
    "Seattle Mariners": 136, "St. Louis Cardinals": 138, "Tampa Bay Rays": 139,
    "Texas Rangers": 140, "Toronto Blue Jays": 141, "Washington Nationals": 120,
}

LEAGUE_BASELINE = {
    "AVG": 0.244, "BABIP": 0.290, "BB_RATE": 0.085, "K_RATE": 0.225, "HR_PA_RATE": 0.030,
}


def api_get(path, params=None):
    """Thin wrapper around requests.get with basic retry/backoff. Every call
    into the MLB Stats API should go through this so rate-limit/network
    hiccups get one retry instead of killing the whole nightly run."""
    url = f"{BASE_URL}/{path}"
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params or {}, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt == 2:
                print(f"  [WARN] Failed to fetch {url} after 3 attempts: {e}")
                return None
            time.sleep(1.5 * (attempt + 1))
    return None


def get_40man_roster(team_id):
    """Returns a list of {id, fullName, position} for a team's 40-man roster."""
    data = api_get(f"teams/{team_id}/roster/40Man")
    if not data or "roster" not in data:
        return []
    out = []
    for entry in data["roster"]:
        person = entry.get("person", {})
        out.append({
            "id": person.get("id"),
            "name": person.get("fullName"),
            "position": entry.get("position", {}).get("abbreviation", ""),
            "status": entry.get("status", {}).get("description", ""),
        })
    return out


def get_season_hitting_stats(player_id):
    """Returns the raw season hitting counting stats for a player, or None if
    they have none yet this season (e.g. a pitcher, or a brand-new call-up)."""
    data = api_get(
        f"people/{player_id}",
        {"hydrate": f"stats(group=[hitting],type=[season],season={CURRENT_SEASON})"}
    )
    if not data or "people" not in data or not data["people"]:
        return None
    stats_blocks = data["people"][0].get("stats", [])
    for block in stats_blocks:
        splits = block.get("splits", [])
        if splits:
            return splits[0].get("stat", {})
    return None


def get_season_pitching_stats(player_id):
    """Returns the raw season pitching counting stats for a player, or None."""
    data = api_get(
        f"people/{player_id}",
        {"hydrate": f"stats(group=[pitching],type=[season],season={CURRENT_SEASON})"}
    )
    if not data or "people" not in data or not data["people"]:
        return None
    stats_blocks = data["people"][0].get("stats", [])
    for block in stats_blocks:
        splits = block.get("splits", [])
        if splits:
            return splits[0].get("stat", {})
    return None


def get_handedness(player_id):
    """Returns (bats, throws) as single letters ('L'/'R'/'B' for bats,
    'L'/'R' for throws), defaulting to right-handed if unknown."""
    data = api_get(f"people/{player_id}")
    if not data or "people" not in data or not data["people"]:
        return "R", "R"
    person = data["people"][0]
    bats = person.get("batSide", {}).get("code", "R")
    throws = person.get("pitchHand", {}).get("code", "R")
    return bats, throws


def safe_div(numerator, denominator, default=0.0):
    return (numerator / denominator) if denominator else default


def build_hitter_entry(name, bats, stat):
    """Converts raw MLB Stats API counting stats into the rate-stat schema
    the simulator expects. Falls back to league-average rates if a player's
    sample is empty (e.g. hasn't recorded a plate appearance yet this year)."""
    ab = stat.get("atBats", 0)
    pa = stat.get("plateAppearances", ab)
    h = stat.get("hits", 0)
    doubles = stat.get("doubles", 0)
    triples = stat.get("triples", 0)
    hr = stat.get("homeRuns", 0)
    bb = stat.get("baseOnBalls", 0)
    so = stat.get("strikeOuts", 0)
    singles = max(0, h - doubles - triples - hr)

    if pa < 20:  # not enough of a sample to compute anything meaningful
        return {
            "Player": name, "Pos": "", "Bats": bats,
            "BB_RATE": LEAGUE_BASELINE["BB_RATE"], "K_RATE": LEAGUE_BASELINE["K_RATE"],
            "HR_PA_RATE": LEAGUE_BASELINE["HR_PA_RATE"], "BABIP": LEAGUE_BASELINE["BABIP"],
            "1B_H_RATE": 0.66, "2B_H_RATE": 0.22, "3B_H_RATE": 0.02, "HR_H_RATE": 0.10,
            "SPD": 55, "PA": 0,
        }

    balls_in_play = ab - so - hr  # rough BABIP denominator (excludes K/HR, ignores SF for simplicity)
    babip = safe_div(h - hr, balls_in_play, LEAGUE_BASELINE["BABIP"])

    return {
        "Player": name, "Pos": "", "Bats": bats,
        "BB_RATE": round(safe_div(bb, pa, LEAGUE_BASELINE["BB_RATE"]), 3),
        "K_RATE": round(safe_div(so, pa, LEAGUE_BASELINE["K_RATE"]), 3),
        "HR_PA_RATE": round(safe_div(hr, pa, LEAGUE_BASELINE["HR_PA_RATE"]), 3),
        "BABIP": round(babip, 3),
        "1B_H_RATE": round(safe_div(singles, h, 0.66), 2),
        "2B_H_RATE": round(safe_div(doubles, h, 0.22), 2),
        "3B_H_RATE": round(safe_div(triples, h, 0.02), 2),
        "HR_H_RATE": round(safe_div(hr, h, 0.10), 2),
        "SPD": 55,  # placeholder -- see module docstring, needs Statcast Sprint Speed for real values
        "PA": pa,
    }


def build_pitcher_entry(name, throws, stat):
    ip_str = stat.get("inningsPitched", "0.0")
    try:
        whole, _, frac = ip_str.partition(".")
        ip = float(whole) + (int(frac) / 3.0 if frac else 0.0)
    except ValueError:
        ip = 0.0
    bf = stat.get("battersFaced", ip * 4.3)
    bb = stat.get("baseOnBalls", 0)
    so = stat.get("strikeOuts", 0)
    hr = stat.get("homeRuns", 0)
    h = stat.get("hits", 0)
    era = stat.get("era", "0.00")
    games_started = stat.get("gamesStarted", 0)
    games_pitched = stat.get("gamesPitched", 1)
    saves = stat.get("saves", 0)

    if bf < 15:
        role = "RP"
        return {
            "Player": name, "Pos": "P", "Role": role, "Throws": throws,
            "BB_ALLOWED_RATE": LEAGUE_BASELINE["BB_RATE"], "K_ALLOWED_RATE": LEAGUE_BASELINE["K_RATE"],
            "HR_PA_ALLOWED_RATE": LEAGUE_BASELINE["HR_PA_RATE"], "BABIP_ALLOWED": LEAGUE_BASELINE["BABIP"],
            "OAVG": LEAGUE_BASELINE["AVG"], "IP": "0.0", "ERA": 4.50, "Fatigue": 0.0,
        }

    # Role heuristic: mostly-starts -> SP, meaningful saves -> Closer, else RP.
    # This is inferred (not an explicit API field) -- spot check after each run.
    start_ratio = safe_div(games_started, games_pitched)
    if start_ratio > 0.5:
        role = "SP"
    elif saves >= 5:
        role = "Closer"
    else:
        role = "RP"

    balls_in_play_faced = bf - so - bb - hr
    babip_allowed = safe_div(h - hr, balls_in_play_faced, LEAGUE_BASELINE["BABIP"])

    return {
        "Player": name, "Pos": "P", "Role": role, "Throws": throws,
        "BB_ALLOWED_RATE": round(safe_div(bb, bf, LEAGUE_BASELINE["BB_RATE"]), 3),
        "K_ALLOWED_RATE": round(safe_div(so, bf, LEAGUE_BASELINE["K_RATE"]), 3),
        "HR_PA_ALLOWED_RATE": round(safe_div(hr, bf, LEAGUE_BASELINE["HR_PA_RATE"]), 3),
        "BABIP_ALLOWED": round(babip_allowed, 3),
        "OAVG": round(safe_div(h, bf - bb, LEAGUE_BASELINE["AVG"]), 3),
        "IP": str(round(ip, 1)),
        "ERA": float(era) if era not in (None, "-", "") else 4.50,
        "Fatigue": 0.0,
    }


def refresh_team(team_name, team_id):
    print(f"Fetching {team_name} (id={team_id})...")
    roster = get_40man_roster(team_id)
    hitting, pitching = [], []

    for player in roster:
        if not player["id"] or not player["name"]:
            continue
        time.sleep(0.15)  # be polite to the API -- avoid hammering it 30 teams x 40 players in a row

        if player["position"] == "P":
            stat = get_season_pitching_stats(player["id"])
            if stat is None:
                continue
            _, throws = get_handedness(player["id"])
            pitching.append(build_pitcher_entry(player["name"], throws, stat))
        else:
            stat = get_season_hitting_stats(player["id"])
            if stat is None:
                continue
            bats, _ = get_handedness(player["id"])
            entry = build_hitter_entry(player["name"], bats, stat)
            entry["Pos"] = player["position"]
            hitting.append(entry)

    # Trim to a 9-hitter / 5-SP+5-RP shape matching the existing simulator schema,
    # sorted by playing-time proxy (PA for hitters, IP for pitchers) so the
    # players who've actually been playing are the ones that make the cut.
    hitting.sort(key=lambda p: p["PA"], reverse=True)
    hitting = hitting[:9]

    starters = sorted([p for p in pitching if p["Role"] == "SP"], key=lambda p: float(p["IP"]), reverse=True)[:5]
    closer = [p for p in pitching if p["Role"] == "Closer"][:1]
    relievers = sorted([p for p in pitching if p["Role"] == "RP"], key=lambda p: float(p["IP"]), reverse=True)
    relief_needed = 5 - len(closer)
    bullpen = closer + relievers[:relief_needed]
    pitching_final = starters + bullpen

    return hitting, pitching_final


def main():
    roster_database = {}
    for team_name, team_id in TEAM_IDS.items():
        hitting, pitching = refresh_team(team_name, team_id)
        roster_database[team_name] = {"hitting": hitting, "pitching": pitching}
        print(f"  -> {len(hitting)} hitters, {len(pitching)} pitchers")

    out_path = "roster_data.json"
    with open(out_path, "w") as f:
        json.dump(roster_database, f, indent=2)
    print(f"\nDone. Wrote {out_path} ({sum(len(v['hitting'])+len(v['pitching']) for v in roster_database.values())} total players across {len(roster_database)} teams).")

    push_to_github(out_path)


if __name__ == "__main__":
    main()

# HOW TO SET THIS UP
# -------------------
# 1. On PythonAnywhere, go to the "Files" or "Consoles" area and set an
#    environment variable called GITHUB_TOKEN with your GitHub personal
#    access token (Settings -> Developer settings -> Personal access tokens
#    -> Tokens (classic) -> Generate new token, scope: "repo"). Do NOT paste
#    the token directly into this file.
#
#    If you're running this from a scheduled task (Tasks tab on
#    PythonAnywhere), you can set the env var right in that task's command,
#    e.g.:
#      GITHUB_TOKEN=ghp_xxxxxxxx python3.11 /home/yourusername/refresh_rosters.py
#
# 2. Double check GITHUB_REPO and GITHUB_FILE_PATH above match your actual
#    repo name and the folder spot_check.py lives in.
#
# HOW TO TEST
# -----------
# 1. On PythonAnywhere (or anywhere with real internet access), run:
#      pip install requests --break-system-packages
#      GITHUB_TOKEN=ghp_xxxxxxxx python3 refresh_rosters.py
# 2. This will take a while (30 teams x ~40 players x a few API calls each,
#    with a small delay between calls to be polite to MLB's servers) --
#    expect several minutes, not seconds.
# 3. Open the resulting roster_data.json and spot check a few teams you know
#    well against what you'd expect -- especially the pitcher Role
#    classification (SP/RP/Closer), since that part is a heuristic guess,
#    not a direct API field.
# 4. Confirm it actually shows up in your GitHub repo (refresh the
#    MLB_Predictor folder page) -- if GITHUB_TOKEN wasn't set correctly,
#    you'll see a [WARN] message instead of a "Pushed to GitHub" confirmation.
# 5. Once it looks right, reboot your Streamlit app once to pick up the new
#    file, then wire this script into your existing cron-job.org schedule
#    (same pattern as your other nightly scripts) to run once a day.
