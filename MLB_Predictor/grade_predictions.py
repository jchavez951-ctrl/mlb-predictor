"""Nightly grader: fills in what actually happened for logged predictions.

Runs on GitHub Actions (same pattern as the four refresh_*.py scripts).
Reads MLB_Predictor/predictions_log.jsonl, finds rows with actual == None
whose game_date has finished, pulls the real box scores from the MLB Stats
API, and writes back whether each hitter actually homered.

IMPORTANT -- SCRATCHED PLAYERS:
A player in a projected lineup who never appeared (late scratch, benched,
pinch-hit spot that never came up) is marked actual = null and flagged
did_not_play = true, NOT graded as a miss. Counting a scratch as a failed
prediction would make the model look worse than it is and corrupt the
calibration curve.

Only grades dates where every game is Final, so a game still in progress
doesn't get half-graded.
"""

import json
import os
import sys
import time
import datetime as _dt
from collections import defaultdict

import requests

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "predictions_log.jsonl")
SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date}"
BOXSCORE_URL = "https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"

# Don't try to grade today's games -- they haven't been played yet.
GRACE_DAYS = 1


def load_log():
    if not os.path.exists(LOG_PATH):
        print(f"No log at {LOG_PATH} -- nothing to grade yet.")
        return []
    rows = []
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"  ! skipping malformed line {i}: {e}")
    return rows


def get_json(url, tries=3):
    for attempt in range(tries):
        try:
            r = requests.get(url, timeout=25)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == tries - 1:
                print(f"  ! failed {url}: {e}")
                return None
            time.sleep(2 * (attempt + 1))
    return None


def hr_by_player_for_date(date_str):
    """Returns (mapping player_id -> homers hit, all_final: bool).

    all_final is False if any game that day isn't finished, in which case the
    caller should leave that date ungraded and retry tomorrow.
    """
    sched = get_json(SCHEDULE_URL.format(date=date_str))
    if not sched:
        return {}, False

    game_pks, all_final = [], True
    for day in sched.get("dates", []):
        for g in day.get("games", []):
            state = (g.get("status", {}) or {}).get("abstractGameState")
            code = (g.get("status", {}) or {}).get("codedGameState", "")
            # F = Final, D/C = postponed/cancelled (nothing to grade, but not a blocker)
            if state == "Final" or code in ("D", "C"):
                if state == "Final":
                    game_pks.append(g["gamePk"])
            else:
                all_final = False

    if not all_final:
        return {}, False

    homers = defaultdict(int)
    for pk in game_pks:
        box = get_json(BOXSCORE_URL.format(game_pk=pk))
        if not box:
            # One unreadable box score would silently mark real HRs as zero,
            # so bail on the whole date rather than grade it wrong.
            return {}, False
        for side in ("away", "home"):
            players = ((box.get("teams", {}) or {}).get(side, {}) or {}).get("players", {}) or {}
            for _, p in players.items():
                pid = str(((p.get("person", {}) or {}).get("id", "")) or "")
                batting = ((p.get("stats", {}) or {}).get("batting", {}) or {})
                if not pid or not batting:
                    continue  # no batting line == didn't appear as a hitter
                homers[pid] += int(batting.get("homeRuns", 0) or 0)
        time.sleep(0.3)  # be polite to the API

    return dict(homers), True


def main():
    rows = load_log()
    if not rows:
        return

    cutoff = _dt.date.today() - _dt.timedelta(days=GRACE_DAYS)
    pending = defaultdict(list)
    for r in rows:
        if r.get("actual") is not None or r.get("did_not_play"):
            continue
        try:
            d = _dt.date.fromisoformat(r["game_date"])
        except Exception:
            continue
        if d <= cutoff:
            pending[r["game_date"]].append(r)

    if not pending:
        print("Nothing pending to grade.")
        return

    print(f"Dates pending: {sorted(pending)}")
    graded_at = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    total_graded = 0

    for date_str in sorted(pending):
        print(f"\nGrading {date_str} ({len(pending[date_str])} predictions)...")
        homers, all_final = hr_by_player_for_date(date_str)
        if not all_final:
            print("  games not all final (or box scores unavailable) -- leaving for tomorrow.")
            continue

        appeared = set(homers.keys())
        hit, missed, dnp = 0, 0, 0
        for r in pending[date_str]:
            pid = r.get("player_id")
            if not pid or pid not in appeared:
                # Scratched / never batted. Not a miss -- exclude from calibration.
                r["did_not_play"] = True
                r["graded_at"] = graded_at
                dnp += 1
                continue
            r["actual"] = 1 if homers.get(pid, 0) > 0 else 0
            r["graded_at"] = graded_at
            hit += r["actual"]
            missed += (1 - r["actual"])
            total_graded += 1

        print(f"  homered: {hit}   didn't: {missed}   did not play: {dnp}")
        if hit + missed:
            print(f"  observed HR rate: {hit / (hit + missed):.1%}")

    if total_graded == 0:
        print("\nNo rows newly graded.")
        return

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nWrote {LOG_PATH} -- {total_graded} newly graded rows.")


if __name__ == "__main__":
    sys.exit(main())
