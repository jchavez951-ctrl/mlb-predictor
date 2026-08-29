"""calibration_report.py

Read-only analysis of MLB_Predictor/predictions_log.jsonl. Writes nothing,
commits nothing -- safe to run any time.

WHAT IT ANSWERS
----------------
1. Is the model calibrated? When it says 15%, does 15% happen? Predictions are
   bucketed by predicted probability and each bucket's predicted rate is
   compared against what actually occurred.
2. Does it beat a dumb baseline? Brier score against a constant "everyone gets
   the league average" predictor. A model that can't beat that constant is
   adding noise, not information, no matter how sophisticated it looks.
3. Does recalibrate.calibrate() help? If both a raw and a calibrated
   probability were logged, both are scored so you can see whether the
   calibration step earns its place.

WHY BUCKETS AND NOT ONE NUMBER
-------------------------------
A single overall hit rate hides direction. A model can be right on average
while being badly overconfident at the top and underconfident at the bottom --
and the top is exactly where you'd be betting. Buckets show where it breaks.

RUN FROM THE REPO ROOT:  python MLB_Predictor/calibration_report.py
"""

import json
import os
import sys
from collections import defaultdict

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "predictions_log.jsonl")

# Candidate key names for the predicted probability. The log is written by
# prediction_log.py, which may normalize the display names used in the app, so
# several spellings are tried and the full key list is printed at startup to
# make any mismatch a one-pass fix.
CALIBRATED_KEYS = ["hr_prob", "hr_over_05", "hr_over_0.5", "HR Over 0.5%",
                   "hr_p", "calibrated_prob", "prob", "predicted"]
RAW_KEYS = ["hr_raw", "hr_raw_pct", "HR Raw%", "hr_p_raw", "raw_prob"]

# Bucket edges as probabilities. Deliberately narrow at the low end (where most
# predictions live) and open-ended at the top.
BUCKETS = [(0.00, 0.05), (0.05, 0.10), (0.10, 0.15),
           (0.15, 0.20), (0.20, 0.25), (0.25, 1.01)]

# Below this many graded rows, a bucket's observed rate is noise. Flagged, not
# hidden -- seeing "n=6" next to a wild number is the useful part.
MIN_BUCKET_N = 30


def load_rows():
    if not os.path.exists(LOG_PATH):
        print(f"No log at {LOG_PATH}.")
        sys.exit(1)
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


def find_key(rows, candidates):
    keys = set()
    for r in rows[:200]:
        keys.update(r.keys())
    for c in candidates:
        if c in keys:
            return c
    lower = {k.lower(): k for k in keys}
    for c in candidates:
        if c.lower() in lower:
            return lower[c.lower()]
    return None


def as_prob(value):
    """Accepts 0-1 or 0-100 and returns 0-1. A logged 19.6 means 19.6%."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v > 1.0:
        v = v / 100.0
    if v < 0.0 or v > 1.0:
        return None
    return v


def brier(pairs):
    """Mean squared error between predicted probability and 0/1 outcome.
    Lower is better. This is the standard scoring rule for probabilistic
    forecasts -- it punishes both miscalibration and lack of sharpness."""
    if not pairs:
        return None
    return sum((p - a) ** 2 for p, a in pairs) / len(pairs)


def report_for(label, pairs):
    if not pairs:
        print(f"\n{label}: no usable rows.")
        return

    n = len(pairs)
    observed = sum(a for _, a in pairs) / n
    predicted = sum(p for p, _ in pairs) / n

    print(f"\n{'=' * 72}")
    print(f"{label}   (n = {n})")
    print(f"{'=' * 72}")
    print(f"  Mean predicted: {predicted:.1%}     Actually happened: {observed:.1%}")

    gap = predicted - observed
    if abs(gap) < 0.01:
        print("  Overall bias:   negligible.")
    elif gap > 0:
        print(f"  Overall bias:   OVERPREDICTS by {gap:.1%} -- the model is too optimistic.")
    else:
        print(f"  Overall bias:   UNDERPREDICTS by {-gap:.1%} -- the model is too pessimistic.")

    model_brier = brier(pairs)
    # Baseline: predict the observed base rate for every single player, always.
    # A model only earns its complexity if it beats this.
    base_pairs = [(observed, a) for _, a in pairs]
    base_brier = brier(base_pairs)
    skill = (base_brier - model_brier) / base_brier if base_brier else 0.0

    print(f"\n  Brier score:    {model_brier:.4f}")
    print(f"  Baseline:       {base_brier:.4f}  (predicting {observed:.1%} for everyone)")
    if skill > 0.001:
        print(f"  Skill:          +{skill:.1%} better than the baseline.")
    elif skill < -0.001:
        print(f"  Skill:          {skill:.1%} WORSE than the baseline.")
        print("                  The per-player differentiation is currently costing accuracy.")
    else:
        print("  Skill:          indistinguishable from the baseline.")
        print("                  Player-level HR probabilities aren't adding information yet.")

    print(f"\n  {'Bucket':<14}{'n':>6}{'Predicted':>12}{'Actual':>10}{'Gap':>10}")
    print(f"  {'-' * 52}")
    for lo, hi in BUCKETS:
        sel = [(p, a) for p, a in pairs if lo <= p < hi]
        if not sel:
            continue
        bn = len(sel)
        bp = sum(p for p, _ in sel) / bn
        ba = sum(a for _, a in sel) / bn
        flag = "  (thin)" if bn < MIN_BUCKET_N else ""
        label_txt = f"{lo:.0%}-{hi:.0%}" if hi <= 1.0 else f"{lo:.0%}+"
        print(f"  {label_txt:<14}{bn:>6}{bp:>11.1%}{ba:>10.1%}{bp - ba:>+10.1%}{flag}")

    thin = sum(1 for lo, hi in BUCKETS
               if 0 < len([1 for p, _ in pairs if lo <= p < hi]) < MIN_BUCKET_N)
    if thin:
        print(f"\n  {thin} bucket(s) marked (thin) have under {MIN_BUCKET_N} rows -- treat")
        print("  those observed rates as noise, not signal.")


def main():
    rows = load_rows()
    print(f"Loaded {len(rows)} logged rows from {LOG_PATH}")

    if rows:
        print(f"\nKeys present: {sorted(rows[0].keys())}")
        print("^ If the probability field isn't picked up below, it's named something")
        print("  not in CALIBRATED_KEYS / RAW_KEYS -- add it there and rerun.\n")

    graded = [r for r in rows
              if r.get("actual") in (0, 1, True, False) and not r.get("did_not_play")]
    dnp = sum(1 for r in rows if r.get("did_not_play"))
    ungraded = len(rows) - len(graded) - dnp

    print(f"Graded: {len(graded)}   Did not play: {dnp}   Still pending: {ungraded}")

    if not graded:
        print("\nNothing graded yet -- let the nightly grader run a few more days.")
        return

    dates = sorted({r.get("game_date") for r in graded if r.get("game_date")})
    if dates:
        print(f"Date range: {dates[0]} to {dates[-1]}  ({len(dates)} days)")

    cal_key = find_key(rows, CALIBRATED_KEYS)
    raw_key = find_key(rows, RAW_KEYS)
    print(f"Using calibrated field: {cal_key}    raw field: {raw_key}")

    if not cal_key and not raw_key:
        print("\n[ERROR] Couldn't find a probability field. Check the key list printed above.")
        sys.exit(1)

    def pairs_for(key):
        out = []
        for r in graded:
            p = as_prob(r.get(key))
            if p is None:
                continue
            out.append((p, 1 if r.get("actual") in (1, True) else 0))
        return out

    if cal_key:
        report_for(f"CALIBRATED  (field: {cal_key})", pairs_for(cal_key))
    if raw_key:
        report_for(f"RAW, pre-calibration  (field: {raw_key})", pairs_for(raw_key))

    if cal_key and raw_key:
        cb, rb = brier(pairs_for(cal_key)), brier(pairs_for(raw_key))
        if cb is not None and rb is not None:
            print(f"\n{'=' * 72}")
            if cb < rb:
                print(f"recalibrate.calibrate() IS helping: {rb:.4f} -> {cb:.4f}")
            elif cb > rb:
                print(f"recalibrate.calibrate() is HURTING: {rb:.4f} -> {cb:.4f}")
                print("The raw simulated probabilities score better than the calibrated ones.")
            else:
                print("Calibration is making no measurable difference.")

    print(f"\n{'=' * 72}")
    print("Reminder on sample size: one HR is worth roughly 1 percentage point")
    print("per 100 rows, so gaps smaller than a few points are not yet real.")


if __name__ == "__main__":
    main()
