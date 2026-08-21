"""Probability recalibration for the HR simulator.

WHY THIS EXISTS
Measured over 1,483 graded predictions (2026-08-14 to 2026-08-20), the raw
simulation was systematically overconfident: it predicted a mean 14.7% HR
probability against an observed 10.5%. The distortion grows with the
prediction -- the 5-10% range was roughly honest, while the 25%+ range ran
about double the true rate. That is the region you'd actually bet, so the
error was concentrated exactly where it hurt most.

This applies a logistic (Platt) correction fit on that data:

    calibrated_logodds = A * raw_logodds + B

WHAT IT DOES AND DOESN'T FIX
It makes the displayed numbers honest. It does NOT create predictive edge --
cross-validated Brier improves only from 0.0955 to 0.0933 against a 0.0936
base-rate baseline. The model's ranking ability (AUC 0.586) is unchanged by
recalibration; a monotonic transform can't reorder anything. Real improvement
has to come from better inputs, not better scaling.

REFITTING
Coefficients were stable in direction across leave-one-day-out fits (slope
0.73-0.89, intercept always negative) but league-wide scoring drifts -- the
observed rate fell from 11.9% to 9.0% across a single week. Refit monthly by
re-running calibration.py and updating A and B here. Note FIT_THROUGH below
so you can tell how stale these are.
"""

import math

# Fit on 1,483 graded predictions, 2026-08-14 through 2026-08-20.
A = 0.803
B = -0.721
FIT_THROUGH = "2026-08-20"
FIT_N = 1483


def calibrate(p):
    """Map a raw simulation probability to a calibrated one.

    Returns None unchanged so a missing prediction stays missing rather than
    becoming a confident-looking number.
    """
    if p is None:
        return None
    try:
        p = float(p)
    except (TypeError, ValueError):
        return None
    p = min(max(p, 1e-6), 1 - 1e-6)
    logodds = math.log(p / (1 - p))
    return 1 / (1 + math.exp(-(A * logodds + B)))


if __name__ == "__main__":
    print(f"Recalibration fit through {FIT_THROUGH} on {FIT_N} graded predictions")
    print(f"  calibrated_logodds = {A} * raw_logodds + {B}\n")
    print("  raw     calibrated")
    for raw in (0.05, 0.075, 0.10, 0.125, 0.15, 0.20, 0.25, 0.30):
        print(f"  {raw:5.1%}  ->  {calibrate(raw):5.1%}")
