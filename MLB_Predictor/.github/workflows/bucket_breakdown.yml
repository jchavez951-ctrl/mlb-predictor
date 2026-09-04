"""bucket_breakdown.py

Breaks down the 15-20% calibrated HR probability bucket by player
characteristics to find whether specific traits predict when the model
undersells or oversells.

RUN FROM THE REPO ROOT:  python MLB_Predictor/bucket_breakdown.py
"""

import json
import os
import sys
from collections import defaultdict

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "predictions_log.jsonl")

# The bucket to inspect -- these are the players the model thinks are
# most likely to homer and where the 2.4% underprediction gap lives.
BUCKET_LO = 0.15
BUCKET_HI = 0.20

# Also show the 20-25% bucket since that had a 12.7% gap.
BUCKET2_LO = 0.20
BUCKET2_HI = 0.25


def load_graded():
    rows = []
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("actual") not in (0, 1, True, False):
                continue
            if r.get("did_not_play"):
                continue
            p = r.get("pred_prob_cal")
            if p is None:
                continue
            try:
                p = float(p)
            except (TypeError, ValueError):
                continue
            if p > 1.0:
                p = p / 100.0
            r["_p"] = p
            r["_hit"] = 1 if r.get("actual") in (1, True) else 0
            rows.append(r)
    return rows


def safe_float(v, scale=1.0):
    try:
        return float(v) / scale
    except (TypeError, ValueError):
        return None


def breakdown(rows, label):
    if not rows:
        print(f"\n{label}: no rows.")
        return

    n = len(rows)
    hits = sum(r["_hit"] for r in rows)
    pred_mean = sum(r["_p"] for r in rows) / n
    actual_rate = hits / n

    print(f"\n{'=' * 65}")
    print(f"{label}  (n={n}, predicted {pred_mean:.1%}, actual {actual_rate:.1%}, gap {pred_mean - actual_rate:+.1%})")
    print(f"{'=' * 65}")

    def show(title, key, transform=None, buckets=None):
        vals = []
        for r in rows:
            v = r.get(key)
            if v is None:
                continue
            if transform:
                v = transform(v)
            if v is None:
                continue
            vals.append((v, r["_hit"]))
        if not vals:
            print(f"\n  {title}: field not found in log.")
            return

        if buckets:
            print(f"\n  {title}:")
            print(f"  {'Range':<20}{'n':>5}{'Hit rate':>10}{'Model avg':>12}")
            print(f"  {'-' * 47}")
            for lo, hi, lbl in buckets:
                sel = [(v, h) for v, h in vals if lo <= v < hi]
                if not sel:
                    continue
                bn = len(sel)
                bh = sum(h for _, h in sel) / bn
                bm = sum(r["_p"] for r in rows
                         if transform(r.get(key)) is not None
                         and lo <= transform(r.get(key)) < hi) / bn if bn else 0
                flag = " (thin)" if bn < 15 else ""
                print(f"  {lbl:<20}{bn:>5}{bh:>10.1%}{bm:>12.1%}{flag}")
        else:
            # Median split
            vals.sort(key=lambda x: x[0])
            mid = len(vals) // 2
            low_h = sum(h for _, h in vals[:mid]) / mid if mid else 0
            high_h = sum(h for _, h in vals[mid:]) / (len(vals) - mid) if len(vals) - mid else 0
            med = vals[mid][0]
            print(f"\n  {title} (median={med:.1f}):")
            print(f"    Below median (n={mid}): hit rate {low_h:.1%}")
            print(f"    Above median (n={len(vals)-mid}): hit rate {high_h:.1%}")

    # Park factor
    show("Park factor (barrel_pct as proxy for park)",
         "barrel_pct",
         transform=lambda v: safe_float(v),
         buckets=[
             (0, 8,    "Low barrel (<8%)"),
             (8, 12,   "Mid barrel (8-12%)"),
             (12, 100, "High barrel (12%+)"),
         ])

    # Hard hit %
    show("Hard hit %",
         "hardhit_pct",
         transform=lambda v: safe_float(v),
         buckets=[
             (0,  40,  "Low HH (<40%)"),
             (40, 50,  "Mid HH (40-50%)"),
             (50, 100, "High HH (50%+)"),
         ])

    # COMB score
    show("COMB score",
         "comb",
         transform=lambda v: safe_float(v),
         buckets=[
             (0,    0.15, "Low COMB (<0.15)"),
             (0.15, 0.25, "Mid COMB (0.15-0.25)"),
             (0.25, 1.0,  "High COMB (0.25+)"),
         ])

    # Market (home vs away, or specific parks)
    print(f"\n  Market (top venues by hit rate):")
    market_buckets = defaultdict(lambda: [0, 0])
    for r in rows:
        m = r.get("market", "unknown")
        market_buckets[m][0] += 1
        market_buckets[m][1] += r["_hit"]
    ranked = sorted(market_buckets.items(), key=lambda x: x[1][1] / x[1][0] if x[1][0] >= 5 else -1, reverse=True)
    print(f"  {'Market':<30}{'n':>5}{'Hit rate':>10}")
    print(f"  {'-' * 45}")
    for m, (cnt, hits_) in ranked[:10]:
        if cnt < 5:
            continue
        print(f"  {str(m)[:30]:<30}{cnt:>5}{hits_/cnt:>10.1%}")

    # Source (which team's games)
    print(f"\n  Top players by hit rate (min 5 appearances):")
    player_buckets = defaultdict(lambda: [0, 0])
    for r in rows:
        p_name = r.get("player", "unknown")
        player_buckets[p_name][0] += 1
        player_buckets[p_name][1] += r["_hit"]
    ranked_p = sorted(player_buckets.items(), key=lambda x: x[1][1] / x[1][0] if x[1][0] >= 5 else -1, reverse=True)
    print(f"  {'Player':<25}{'n':>5}{'Hit rate':>10}")
    print(f"  {'-' * 40}")
    for name, (cnt, hits_) in ranked_p[:15]:
        if cnt < 5:
            continue
        print(f"  {str(name)[:25]:<25}{cnt:>5}{hits_/cnt:>10.1%}")


def main():
    rows = load_graded()
    print(f"Loaded {len(rows)} graded rows total.")

    bucket1 = [r for r in rows if BUCKET_LO <= r["_p"] < BUCKET_HI]
    bucket2 = [r for r in rows if BUCKET2_LO <= r["_p"] < BUCKET2_HI]

    breakdown(bucket1, f"15-20% calibrated bucket")
    breakdown(bucket2, f"20-25% calibrated bucket")

    print(f"\n{'=' * 65}")
    print("If one segment's hit rate is well above the bucket average,")
    print("that's a real edge the COMB score may not be capturing fully.")
    print("If it's random across all cuts, the underprediction is noise.")


if __name__ == "__main__":
    main()
