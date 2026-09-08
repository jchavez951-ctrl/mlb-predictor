#!/usr/bin/env python3
"""
refresh_rosters_nba.py

Pulls active NBA rosters from stats.nba.com and writes NBA_Predictor/nba_roster_data.json,
keyed by team abbreviation, with PERSON_ID attached to every player.

Lives at the REPO ROOT. Workflow runs it as: python refresh_rosters_nba.py

Doubles as the datacenter-IP test: stats.nba.com throttles/blocks non-browser and
datacenter traffic aggressively. This script fails LOUDLY and does NOT overwrite a
good existing JSON with a partial pull.

Exit codes:
  0  success, JSON written
  1  hard failure (blocked, timed out, or too few teams returned) - nothing written
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

# Minimum bars for a pull to be considered trustworthy.
MIN_TEAMS = 28          # of 30
MIN_PLAYERS = 400       # 30 teams x ~15

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
BASE_SLEEP = 1.2        # polite pause between team calls
BACKOFF = 4.0           # extra seconds added per retry

# stats.nba.com rejects anything that does not look like a browser XHR.
# These headers are the whole ballgame - do not trim them.
HEADERS = {
    "Host": "stats.nba.com",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
}

TEAMS = {
    1610612737: "ATL", 1610612738: "BOS", 1610612739: "CLE", 1610612740: "NOP",
    1610612741: "CHI", 1610612742: "DAL", 1610612743: "DEN", 1610612744: "GSW",
    1610612745: "HOU", 1610612746: "LAC", 1610612747: "LAL", 1610612748: "MIA",
    1610612749: "MIL", 1610612750: "MIN", 1610612751: "BKN", 1610612752: "NYK",
    1610612753: "ORL", 1610612754: "IND", 1610612755: "PHI", 1610612756: "PHX",
    1610612757: "POR", 1610612758: "SAC", 1610612759: "SAS", 1610612760: "OKC",
    1610612761: "TOR", 1610612762: "UTA", 1610612763: "MEM", 1610612764: "WAS",
    1610612765: "DET", 1610612766: "CHA",
}


def current_season() -> str:
    """NBA season string, e.g. '2026-27'. Season flips over in October."""
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

def fetch(endpoint: str, params: dict) -> dict:
    """GET a stats.nba.com endpoint with retries. Raises on total failure."""
    url = f"https://stats.nba.com/stats/{endpoint}"
    last_err = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(
                url, headers=HEADERS, params=params, timeout=REQUEST_TIMEOUT
            )
            if resp.status_code == 200:
                return resp.json()

            last_err = f"HTTP {resp.status_code}"
            # 403 = blocked outright. 429 = throttled. Both worth naming.
            if resp.status_code in (403, 429):
                print(
                    f"    [{endpoint}] {resp.status_code} on attempt {attempt} "
                    f"- this is the datacenter-IP signature",
                    flush=True,
                )
        except requests.exceptions.Timeout:
            last_err = "timeout"
            print(f"    [{endpoint}] timeout on attempt {attempt}", flush=True)
        except requests.exceptions.RequestException as exc:
            last_err = str(exc)
            print(f"    [{endpoint}] error on attempt {attempt}: {exc}", flush=True)

        if attempt < MAX_RETRIES:
            wait = BACKOFF * attempt + random.uniform(0, 1.5)
            time.sleep(wait)

    raise RuntimeError(f"{endpoint} failed after {MAX_RETRIES} attempts: {last_err}")


def result_set_to_dicts(payload: dict, index: int = 0) -> list:
    """stats.nba.com returns parallel headers/rowSet arrays. Zip them up."""
    rs = payload["resultSets"][index]
    cols = rs["headers"]
    return [dict(zip(cols, row)) for row in rs["rowSet"]]


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------

def build_player_entry(row: dict) -> dict:
    """One roster row -> the shape the simulator consumes."""
    person_id = row.get("PLAYER_ID")
    if person_id is None:
        return None

    exp_raw = row.get("EXP")
    if exp_raw in ("R", None, ""):
        exp = 0
    else:
        try:
            exp = int(exp_raw)
        except (TypeError, ValueError):
            exp = 0

    return {
        "person_id": int(person_id),
        "name": row.get("PLAYER"),
        "position": row.get("POSITION") or "",
        "jersey": str(row.get("NUM") or ""),
        "height": row.get("HEIGHT") or "",
        "weight": row.get("WEIGHT") or "",
        "experience": exp,
        "age": row.get("AGE"),
    }


def pull_team(team_id: int, abbrev: str) -> list:
    payload = fetch(
        "commonteamroster",
        {"TeamID": team_id, "Season": SEASON, "LeagueID": "00"},
    )
    rows = result_set_to_dicts(payload, index=0)

    players = []
    for row in rows:
        entry = build_player_entry(row)
        if entry is not None:
            players.append(entry)
    return players


def main() -> int:
    print(f"refresh_rosters_nba.py | season {SEASON}", flush=True)
    print(f"output -> {OUT_PATH}\n", flush=True)

    rosters = {}
    failed = []

    for team_id, abbrev in TEAMS.items():
        try:
            players = pull_team(team_id, abbrev)
        except RuntimeError as exc:
            print(f"  {abbrev}: FAILED - {exc}", flush=True)
            failed.append(abbrev)
            time.sleep(BASE_SLEEP)
            continue

        with_id = sum(1 for p in players if p["person_id"])
        print(f"  {abbrev}: {len(players)} players ({with_id} with PERSON_ID)", flush=True)
        rosters[abbrev] = players

        time.sleep(BASE_SLEEP + random.uniform(0, 0.6))

    total_players = sum(len(v) for v in rosters.values())

    print("\n" + "=" * 52, flush=True)
    print(f"teams pulled : {len(rosters)} / 30", flush=True)
    print(f"players      : {total_players}", flush=True)
    if failed:
        print(f"failed teams : {', '.join(failed)}", flush=True)
    print("=" * 52 + "\n", flush=True)

    if len(rosters) < MIN_TEAMS or total_players < MIN_PLAYERS:
        print(
            "REFUSING TO WRITE: pull is incomplete.\n"
            "If the failures are 403/429, this IP is blocked or throttled and the\n"
            "refresh needs to run somewhere else. Existing JSON left untouched.",
            flush=True,
        )
        return 1

    out = {
        "meta": {
            "season": SEASON,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "team_count": len(rosters),
            "player_count": total_players,
            "failed_teams": failed,
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
