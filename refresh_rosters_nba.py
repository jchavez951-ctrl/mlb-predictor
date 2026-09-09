#!/usr/bin/env python3
"""
refresh_rosters_nba.py

Pulls active NBA rosters from ESPN's public JSON API and writes
NBA_Predictor/nba_roster_data.json, keyed by team abbreviation.

Lives at the REPO ROOT. Workflow runs it as: python refresh_rosters_nba.py

Replaces the stats.nba.com version, which tarpits GitHub Actions runner IPs
(every request timed out, no response at all). ESPN's site.api endpoints are
the same ones its own scoreboard pages call and do not appear to discriminate
by IP.

FAILS FAST by design: short timeouts, two attempts, and an early abort if the
first few teams all fail. The previous version would have ground for 45 minutes
before giving up. This one quits in about one.

IMPORTANT: the IDs here are ESPN athlete IDs, NOT NBA PERSON_IDs. If a later
data source keys on NBA IDs you will need a name-based crosswalk built once and
cached - the same matching problem you solved on the Savant side by keying on
PlayerID.

Exit codes:
  0  success, JSON written
  1  hard failure - nothing written, existing JSON untouched
"""

import json
import os
import random
import sys
import time
from datetime import datetime, timezone

import requests

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

OUT_PATH = os.path.join("NBA_Predictor", "nba_roster_data.json")

BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"

MIN_TEAMS = 28          # of 30
MIN_PLAYERS = 400       # 30 teams x ~15

REQUEST_TIMEOUT = 15    # short on purpose - a hang is a failure, not a wait
MAX_RETRIES = 2
BASE_SLEEP = 0.6
BACKOFF = 3.0

# Abort the whole run if the first N teams all fail. No point burning 30
# timeouts to learn what the first three already told us.
EARLY_ABORT_AFTER = 3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def current_season() -> str:
    """NBA season label, e.g. '2026-27'. Flips over in October."""
    override = os.environ.get("NBA_SEASON")
    if override:
        return override
    now = datetime.now(timezone.utc)
    start = now.year if now.month >= 10 else now.year - 1
    return f"{start}-{str(start + 1)[-2:]}"


SEASON = current_season()


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------

def fetch(url: str, label: str) -> dict:
    """GET JSON with retries. Raises RuntimeError on total failure."""
    last_err = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return resp.json()

            last_err = f"HTTP {resp.status_code}"
            print(f"    [{label}] {resp.status_code} on attempt {attempt}", flush=True)

        except requests.exceptions.Timeout:
            last_err = "timeout"
            print(f"    [{label}] timeout on attempt {attempt}", flush=True)
        except requests.exceptions.RequestException as exc:
            last_err = str(exc)
            print(f"    [{label}] error on attempt {attempt}: {exc}", flush=True)
        except ValueError as exc:
            last_err = f"bad JSON: {exc}"
            print(f"    [{label}] response was not JSON on attempt {attempt}", flush=True)

        if attempt < MAX_RETRIES:
            time.sleep(BACKOFF + random.uniform(0, 1.0))

    raise RuntimeError(f"{label} failed after {MAX_RETRIES} attempts: {last_err}")


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------

def get_team_list() -> list:
    """[(espn_team_id, abbrev, display_name)] for all 30 teams."""
    payload = fetch(f"{BASE}/teams", "teams")

    teams = []
    groups = payload.get("sports", [])[0].get("leagues", [])[0].get("teams", [])
    for wrapper in groups:
        team = wrapper.get("team", {})
        team_id = team.get("id")
        abbrev = team.get("abbreviation")
        if team_id and abbrev:
            teams.append((str(team_id), abbrev, team.get("displayName", abbrev)))
    return teams


def iter_athletes(payload: dict):
    """
    ESPN returns 'athletes' either as a flat list (NBA) or grouped by position
    with an 'items' key (NFL-style). Handle both so this does not silently
    return zero players if the shape changes.
    """
    athletes = payload.get("athletes", [])
    for entry in athletes:
        if isinstance(entry, dict) and "items" in entry:
            for item in entry.get("items", []):
                yield item
        else:
            yield entry


def build_player_entry(athlete: dict) -> dict:
    espn_id = athlete.get("id")
    if not espn_id:
        return None

    position = athlete.get("position") or {}
    experience = athlete.get("experience") or {}
    injuries = athlete.get("injuries") or []

    status = "active"
    if injuries:
        first = injuries[0] or {}
        status = (first.get("status") or "injured").lower()

    return {
        "espn_id": str(espn_id),
        "name": athlete.get("fullName") or athlete.get("displayName"),
        "short_name": athlete.get("shortName"),
        "position": position.get("abbreviation") or "",
        "jersey": str(athlete.get("jersey") or ""),
        "height_in": athlete.get("height"),
        "weight_lb": athlete.get("weight"),
        "age": athlete.get("age"),
        "experience": experience.get("years", 0),
        "status": status,
    }


def pull_team(team_id: str, abbrev: str) -> list:
    payload = fetch(f"{BASE}/teams/{team_id}/roster", f"roster {abbrev}")

    players = []
    for athlete in iter_athletes(payload):
        entry = build_player_entry(athlete)
        if entry is not None:
            players.append(entry)
    return players


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main() -> int:
    print(f"refresh_rosters_nba.py | ESPN | season label {SEASON}", flush=True)
    print(f"output -> {OUT_PATH}\n", flush=True)

    # First call doubles as the reachability test. If this fails, nothing else
    # is worth attempting.
    try:
        teams = get_team_list()
    except RuntimeError as exc:
        print(f"\nFAILED on the team list: {exc}", flush=True)
        print("ESPN is unreachable from this runner. Nothing written.", flush=True)
        return 1

    print(f"team list OK: {len(teams)} teams\n", flush=True)

    rosters = {}
    failed = []

    for index, (team_id, abbrev, _name) in enumerate(teams):
        try:
            players = pull_team(team_id, abbrev)
        except RuntimeError as exc:
            print(f"  {abbrev}: FAILED - {exc}", flush=True)
            failed.append(abbrev)

            if index + 1 >= EARLY_ABORT_AFTER and len(rosters) == 0:
                print(
                    f"\nABORTING: first {index + 1} teams all failed. "
                    "Roster endpoint is not reachable from here.",
                    flush=True,
                )
                return 1

            time.sleep(BASE_SLEEP)
            continue

        active = sum(1 for p in players if p["status"] == "active")
        print(f"  {abbrev}: {len(players)} players ({active} active)", flush=True)
        rosters[abbrev] = players

        time.sleep(BASE_SLEEP + random.uniform(0, 0.4))

    total_players = sum(len(v) for v in rosters.values())

    print("\n" + "=" * 52, flush=True)
    print(f"teams pulled : {len(rosters)} / {len(teams)}", flush=True)
    print(f"players      : {total_players}", flush=True)
    if failed:
        print(f"failed teams : {', '.join(failed)}", flush=True)
    print("=" * 52 + "\n", flush=True)

    if len(rosters) < MIN_TEAMS or total_players < MIN_PLAYERS:
        print(
            "REFUSING TO WRITE: pull is incomplete.\n"
            "Existing JSON left untouched.",
            flush=True,
        )
        return 1

    out = {
        "meta": {
            "source": "espn",
            "season": SEASON,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "team_count": len(rosters),
            "player_count": total_players,
            "failed_teams": failed,
            "id_namespace": "espn_athlete_id",
        },
        "teams": rosters,
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)

    print(f"wrote {OUT_PATH}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
