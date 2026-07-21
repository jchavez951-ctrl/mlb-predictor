"""
refresh_rosters.py

Nightly refresh script for the MLB prop simulator's roster data. Designed to
run inside GitHub Actions (see .github/workflows/refresh_rosters.yml) rather
than on PythonAnywhere -- Actions runners have unrestricted internet access
and already have git write access to this repo, so no proxy allowlist issues
and no personal access token needed.

WHAT THIS DOES
---------------
Pulls current active rosters and season stat lines for all 30 MLB teams from
the free, public MLB Stats API (https://statsapi.mlb.com/api/v1/ -- no API key
required), computes the same derived rate stats the simulator's ROSTER_DATABASE
already uses (BB_RATE, K_RATE, HR_PA_RATE, BABIP, 1B/2B/3B hit-type splits,
BB_ALLOWED_RATE, K_ALLOWED_RATE, HR_PA_ALLOWED_RATE, BABIP_ALLOWED, etc.), and
writes the result out as MLB_Predictor/roster_data.json. The GitHub Actions
workflow that calls this script handles committing and pushing that file --
this script itself just writes it locally.

WHAT THIS DOES NOT DO (be aware of these before trusting the output)
----------------------------------------------------------------------
1. It does NOT know today's actual starting 9 -- real teams typically don't
   release lineups until 1-3 hours before first pitch. This script refreshes
   the full-season RATE STATS for every player currently on the active roster
   (so numbers stay
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
4. This has NOT been run against the live API yet. Test it (see the
   workflow's manual-trigger option) before trusting it.
"""

import json
import time
import sys
import os
from datetime import datetime

try:
    import requests
except ImportError:
    print("This script needs the 'requests' library:  pip install requests")
    sys.exit(1)

BASE_URL = "https://statsapi.mlb.com/api/v1"
CURRENT_SEASON = datetime.now().year

# Output path: alongside spot_check.py in the MLB_Predictor folder. Adjust
# this if your repo layout is different.
OUTPUT_PATH = os.path.join("MLB_Predictor", "roster_data.json")

# MLB's official numeric team IDs. Stable and don't change year to year.
# Verify against https://statsapi.mlb.com/api/v1/teams?sportId=1 if anything
# looks off after a test run.
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
    """Thin wrapper around requests.get with basic retry/backoff."""
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


def get_active_roster(team_id):
    """Fetches the ACTIVE roster (not the full 40-man). This is the key fix
    for a real bug: the 40-man roster includes players currently optioned to
    Triple-A (e.g. a hot prospect sent down after a slow start) or on the
    injured list -- those players are still part of the organization and
    have season stats, but they're not actually with the big-league club
    right now. The active roster, by definition, only includes players
    truly active with the MLB team today, which fixes this at the source
    instead of trying to guess every possible "not really here" status
    string after the fact."""
    data = api_get(f"teams/{team_id}/roster", {"rosterType": "active"})
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
    data = api_get(f"people/{player_id}")
    if not data or "people" not in data or not data["people"]:
        return "R", "R"
    person = data["people"][0]
    bats = person.get("batSide", {}).get("code", "R")
    throws = person.get("pitchHand", {}).get("code", "R")
    return bats, throws


def safe_div(numerator, denominator, default=0.0):
    return (numerator / denominator) if denominator else default


def build_hitter_entry(name, bats, stat, player_id=None):
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
            "Player": name, "PlayerID": player_id, "Pos": "", "Bats": bats,
            "BB_RATE": LEAGUE_BASELINE["BB_RATE"], "K_RATE": LEAGUE_BASELINE["K_RATE"],
            "HR_PA_RATE": LEAGUE_BASELINE["HR_PA_RATE"], "BABIP": LEAGUE_BASELINE["BABIP"],
            "1B_H_RATE": 0.66, "2B_H_RATE": 0.22, "3B_H_RATE": 0.02, "HR_H_RATE": 0.10,
            "SPD": 55, "PA": 0,
        }

    balls_in_play = ab - so - hr
    babip = safe_div(h - hr, balls_in_play, LEAGUE_BASELINE["BABIP"])

    return {
        "Player": name, "PlayerID": player_id, "Pos": "", "Bats": bats,
        "BB_RATE": round(safe_div(bb, pa, LEAGUE_BASELINE["BB_RATE"]), 3),
        "K_RATE": round(safe_div(so, pa, LEAGUE_BASELINE["K_RATE"]), 3),
        "HR_PA_RATE": round(safe_div(hr, pa, LEAGUE_BASELINE["HR_PA_RATE"]), 3),
        "BABIP": round(babip, 3),
        "1B_H_RATE": round(safe_div(singles, h, 0.66), 2),
        "2B_H_RATE": round(safe_div(doubles, h, 0.22), 2),
        "3B_H_RATE": round(safe_div(triples, h, 0.02), 2),
        "HR_H_RATE": round(safe_div(hr, h, 0.10), 2),
        "SPD": 55,
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
        return {
            "Player": name, "Pos": "P", "Role": "RP", "Throws": throws,
            "BB_ALLOWED_RATE": LEAGUE_BASELINE["BB_RATE"], "K_ALLOWED_RATE": LEAGUE_BASELINE["K_RATE"],
            "HR_PA_ALLOWED_RATE": LEAGUE_BASELINE["HR_PA_RATE"], "BABIP_ALLOWED": LEAGUE_BASELINE["BABIP"],
            "OAVG": LEAGUE_BASELINE["AVG"], "IP": "0.0", "ERA": 4.50, "Fatigue": 0.0,
        }

    # Role heuristic: mostly-starts -> SP, meaningful saves -> Closer, else RP.
    # Inferred, not an explicit API field -- spot check after each run.
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
    roster = get_active_roster(team_id)
    hitting, pitching = [], []

    # Statuses that mean "not actually available right now" -- these were
    # already being fetched from the API (player["status"]) but never
    # actually checked anywhere, which is exactly why injured players with a
    # lot of accumulated season innings/plate-appearances (from before they
    # got hurt) could still out-rank healthy active players in the
    # sort-by-playing-time selection below. Substring match (not exact),
    # since MLB's exact phrasing varies ("Injured List - 60-Day", "60-Day
    # IL", etc.) and this is safer than trying to match every exact variant.
    UNAVAILABLE_KEYWORDS = ["injured", "suspended", "restricted", "bereavement", "family medical", "non-roster"]

    def is_available(player):
        status = player.get("status", "").lower()
        return not any(kw in status for kw in UNAVAILABLE_KEYWORDS)

    for player in roster:
        if not player["id"] or not player["name"]:
            continue
        if not is_available(player):
            print(f"  Skipping {player['name']} (status: {player['status']})")
            continue
        time.sleep(0.1)  # be polite to the API

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
            entry = build_hitter_entry(player["name"], bats, stat, player_id=player["id"])
            entry["Pos"] = player["position"]
            hitting.append(entry)

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

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(roster_database, f, indent=2)
    total_players = sum(len(v["hitting"]) + len(v["pitching"]) for v in roster_database.values())
    print(f"\nDone. Wrote {OUTPUT_PATH} ({total_players} total players across {len(roster_database)} teams).")


if __name__ == "__main__":
    main()
  
 
