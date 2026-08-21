"""Prediction logging for calibration tracking.

WHY THIS COMMITS TO GITHUB INSTEAD OF WRITING A LOCAL FILE:
Streamlit Cloud's filesystem is ephemeral -- anything written to disk is lost
on reboot or redeploy. Calibration needs months of accumulated history, so
predictions have to leave the container the moment they're made. Committing
to the repo also means the nightly grader (GitHub Actions) can read them.

SETUP (one time):
  1. Create a GitHub fine-grained personal access token with
     "Contents: Read and write" on the mlb-predictor repo only.
  2. In Streamlit Cloud: app -> Settings -> Secrets, add:
         github_token = "github_pat_..."
  3. Nothing else. If the token is missing, logging silently no-ops so the
     app keeps working normally.

WHAT GETS LOGGED:
  Every hitter in every simulated game -- NOT just the top 10. This matters:
  calibration compares predicted probability against observed rate across the
  whole probability range. If you only log the top of the board, every bucket
  is 20%+ and you learn nothing about whether your 5% predictions are honest.
"""

import base64
import datetime as _dt
import json
import os

import requests

REPO = "jchavez951-ctrl/mlb-predictor"
LOG_PATH = "MLB_Predictor/predictions_log.jsonl"
API = f"https://api.github.com/repos/{REPO}/contents/{LOG_PATH}"

# Schema version. Bump if you change the fields so old rows stay interpretable.
SCHEMA = 1


def _token():
    """Pull the token from Streamlit secrets, falling back to env var so the
    same module works when run outside Streamlit."""
    try:
        import streamlit as st
        tok = st.secrets.get("github_token")
        if tok:
            return tok
    except Exception:
        pass
    return os.environ.get("GITHUB_TOKEN")


def _headers(tok):
    return {
        "Authorization": f"Bearer {tok}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _fetch_existing(tok):
    """Returns (text, sha). sha is None when the file doesn't exist yet."""
    r = requests.get(API, headers=_headers(tok), timeout=20)
    if r.status_code == 404:
        return "", None
    r.raise_for_status()
    payload = r.json()
    content = base64.b64decode(payload["content"]).decode("utf-8")
    return content, payload["sha"]


def log_predictions(rows, game_date=None, iterations=None, source="slate"):
    """Appends one JSON object per predicted player to predictions_log.jsonl.

    rows: list of dicts as built by the slate leaderboard, each needing at
          minimum Hitter, Team, and "HR Over 0.5%". PlayerID and the contact
          quality fields are included when present.
    game_date: YYYY-MM-DD the games are played on. Defaults to today.
    iterations: how many Monte Carlo iterations produced these numbers. Worth
          recording -- 300-iteration and 1000-iteration predictions have very
          different noise floors and you may want to analyse them separately.
    source: "slate" or "matchup", so you can tell the two views apart later.

    Returns (ok: bool, message: str). Never raises -- a logging failure should
    never take down a simulation the user is watching.
    """
    tok = _token()
    if not tok:
        return False, "No github_token in secrets -- prediction logging is off."
    if not rows:
        return False, "No rows to log."

    game_date = game_date or _dt.date.today().isoformat()
    logged_at = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")

    lines = []
    for r in rows:
        pred = r.get("HR Over 0.5%")
        if pred is None:
            continue
        lines.append(json.dumps({
            "schema": SCHEMA,
            "game_date": game_date,
            "logged_at": logged_at,
            "source": source,
            "iterations": iterations,
            "player_id": str(r["PlayerID"]) if r.get("PlayerID") else None,
            "player": r.get("Hitter"),
            "team": r.get("Team"),
            "market": "HR_over_0.5",
            "pred_prob": round(float(pred if r.get("HR Raw%") is None else r["HR Raw%"]), 5),
            "pred_prob_cal": round(float(pred), 5),
        
            "comb": r.get("COMB"),
            "barrel_pct": r.get("Barrel%"),
            "hardhit_pct": r.get("HardHit%"),
            # Outcome fields are filled in later by grade_predictions.py.
            "actual": None,
            "graded_at": None,
        }, ensure_ascii=False))

    if not lines:
        return False, "No rows had a prediction value."

    block = "\n".join(lines) + "\n"

    try:
        existing, sha = _fetch_existing(tok)
    except Exception as e:
        return False, f"Couldn't read existing log: {e}"

    # Guard against double-logging if someone taps the button twice.
    if existing and f'"game_date": "{game_date}"' in existing and f'"source": "{source}"' in existing:
        for ln in existing.splitlines():
            try:
                obj = json.loads(ln)
            except Exception:
                continue
            if obj.get("game_date") == game_date and obj.get("source") == source:
                return False, f"Already logged a {source} run for {game_date} -- skipping."

    body = {
        "message": f"Log {len(lines)} predictions for {game_date} ({source})",
        "content": base64.b64encode((existing + block).encode("utf-8")).decode("ascii"),
        "branch": "main",
    }
    if sha:
        body["sha"] = sha

    try:
        r = requests.put(API, headers=_headers(tok), json=body, timeout=30)
        r.raise_for_status()
    except Exception as e:
        return False, f"Couldn't write log: {e}"

    return True, f"Logged {len(lines)} predictions for {game_date}."
