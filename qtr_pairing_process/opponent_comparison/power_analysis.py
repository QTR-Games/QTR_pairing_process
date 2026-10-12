"""
How much pairing data would we need to calibrate an opponent model?

Answers three *different* questions that are easy to conflate:

  Q1  Does the rival's recovered utility GENERALISE beyond the one team we
      recovered it from?  (re-recovery per team)
  Q2  Does a given opponent model PREDICT better than the zero-sum mirror our
      engine assumes today?  (single-model accuracy)
  Q3  Does model AGREEMENT carry information -- i.e. is accuracy higher when
      two models converge than when they diverge?  (the ensemble claim)

Q3 is the expensive one and it is the one the user asked about.

Observed structure, measured from the WTC 2026 USA logs (not assumed):
  5 rounds, 25 cells, 1 team, 1 event
  9 forced + 1 suboptimal cells
  4 free opponent decisions per round = 20 observed opponent decisions

CORRECTION, recorded rather than quietly applied
------------------------------------------------
An earlier revision of this file set OPP_DECISIONS_PER_ROUND = 2 and
OPP_DECISIONS_NOW = 10, derived from the 10 cells marked
'nominated_selected_by_them' in wtc2026_usa_pairing_cells.csv. Both numbers
were wrong, for two separate reasons:

  1. UNDERCOUNT. That CSV is a lossy projection of the original logs. The logs
     record FOUR opponent decision points per round (two proffers and two
     nominate-or-counter choices), each with the rival tool's verdict on it.
     The 'nominated_selected_by_them' flag captures only the nomination half.
     Measured from the logs: 20 free opponent decisions, not 10.

  2. CONFLATION. 'Observed' is not 'evaluable'. A decision is only evaluable
     for a given model if the corpus supplies that model's inputs. For the
     mirror models that means a rating matrix, which this corpus does not
     contain at all; for the label model it means a label on the road not
     taken, which the rival tool never prints. So the number of decisions on
     which the two models can actually be RACED is zero, regardless of whether
     20 or 10 were observed. See backtest.py, which counts and names each gap.

The 20 is used below because it is the honest observed count. It does not
rescue the comparison -- it just makes the arithmetic match the artefact.
"""

from math import ceil, sqrt

Z_A = 1.959963985  # two-sided alpha = 0.05
Z_B = 0.8416212336  # power = 0.80

# ---------------------------------------------------------------- observed
ROUNDS_PER_EVENT = 5  # WTC format, per team
OPP_DECISIONS_PER_ROUND = 4  # measured from the logs: 20 free decisions / 5 rounds
OPP_DECISIONS_NOW = 20  # observed. NOT evaluable -- see the correction above.


def wilson(k, n, z=Z_A):
    """Wilson score interval -- honest at small n, unlike normal approximation."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    s = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - s) / d, (c + s) / d)


def n_one_proportion(p_true, half_width):
    """n to estimate a single accuracy to +/- half_width."""
    return ceil(p_true * (1 - p_true) * (Z_A / half_width) ** 2)


def n_two_proportion(p1, p2):
    """n PER GROUP to detect p1 vs p2 at alpha=.05, power=.80."""
    pbar = (p1 + p2) / 2
    num = (Z_A * sqrt(2 * pbar * (1 - pbar)) + Z_B * sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    return ceil(num / (p1 - p2) ** 2)


def as_events(n_decisions):
    rounds = n_decisions / OPP_DECISIONS_PER_ROUND
    return rounds, rounds / ROUNDS_PER_EVENT


def main():
    print(__doc__)
    print("=" * 72)
    print("WHERE WE ARE NOW")
    print("=" * 72)
    n = OPP_DECISIONS_NOW
    for k in (10, 12, 14, 16, 18, 20):
        lo, hi = wilson(k, n)
        print(
            f"  {k}/{n} correct -> accuracy {k/n:.0%}, "
            f"95% CI [{lo:.0%}, {hi:.0%}]  width {hi-lo:.0%}"
        )
    print()
    lo, hi = wilson(9, n)
    print(f"  MEASURED: the opponent took the line worst for us 9/{n} times")
    print(f"  = {9/n:.0%}, 95% CI [{lo:.0%}, {hi:.0%}].")
    print("  That interval contains 50%, so the logged choices are not")
    print("  distinguishable from a coin flip. It also excludes the engine's")
    print("  cumulative2 alpha of 80%, but one event is not grounds to retune.")
    print()
    print("  A coin flip is 50%. Even at n=20 the interval is wide enough to")
    print("  contain both 'useless' and 'good' for most results. This is the")
    print("  arithmetic behind 'the sample cannot support the claim'.")

    print()
    print("=" * 72)
    print("Q2  SINGLE-MODEL ACCURACY  (is the rival utility better than the mirror?)")
    print("=" * 72)
    print("  n needed to pin one model's accuracy to a given precision:")
    print(f"  {'true acc':>9} | {'+/-15pp':>8} {'+/-10pp':>8} {'+/-5pp':>8}")
    for p in (0.60, 0.70, 0.80, 0.90):
        row = [n_one_proportion(p, h) for h in (0.15, 0.10, 0.05)]
        print(f"  {p:>8.0%} | {row[0]:>8} {row[1]:>8} {row[2]:>8}")
    print()
    for n in (35, 50, 123):
        r, e = as_events(n)
        print(f"  {n:>4} opponent decisions = {r:>5.0f} rounds = {e:>4.1f} team-events")

    print()
    print("=" * 72)
    print("Q3  THE ENSEMBLE CLAIM  (does agreement predict correctness?)")
    print("=" * 72)
    print("  n PER GROUP (agree / disagree), alpha=.05, power=.80:")
    print(f"  {'agree':>7} {'disagree':>9} | {'per group':>10} {'total':>7}")
    scenarios = [
        (0.90, 0.50, "huge effect, implausible"),
        (0.85, 0.55, "large"),
        (0.80, 0.60, "moderate -- the realistic target"),
        (0.75, 0.60, "modest"),
        (0.70, 0.60, "small but still useful"),
    ]
    for p1, p2, label in scenarios:
        per = n_two_proportion(p1, p2)
        print(f"  {p1:>7.0%} {p2:>9.0%} | {per:>10} {per*2:>7}   {label}")

    print()
    print("  But you only observe a disagreement when the models actually diverge.")
    print("  Total decisions needed = per_group / min(rate, 1-rate):")
    print()
    print(f"  {'scenario':>34} | {'disagree 50%':>13} {'30%':>8} {'20%':>8} {'10%':>8}")
    for p1, p2, label in scenarios[1:4]:
        per = n_two_proportion(p1, p2)
        cells = [ceil(per / min(r, 1 - r)) for r in (0.50, 0.30, 0.20, 0.10)]
        print(f"  {p1:.0%} vs {p2:.0%} {label:>22} | {cells[0]:>13} {cells[1]:>8} {cells[2]:>8} {cells[3]:>8}")

    print()
    print("=" * 72)
    print("CONVERTED TO EVENTS AND TEAMS")
    print("=" * 72)
    target = n_two_proportion(0.80, 0.60)
    for rate, lbl in ((0.50, "models diverge often"), (0.30, "realistic"), (0.20, "models mostly agree")):
        total = ceil(target / min(rate, 1 - rate))
        r, e = as_events(total)
        print(f"  disagreement {rate:.0%} ({lbl:<20}) -> {total:>5} decisions = {r:>5.0f} rounds = {e:>5.1f} team-events")

    print()
    print("  A 'team-event' is one team's 5 rounds. One WTC has many teams, so a")
    print("  single event with N teams logged yields N team-events -- IF you can")
    print("  obtain their logs, which is the real constraint.")

    print()
    print("=" * 72)
    print("Q1  GENERALISATION  (does +1/0/-10 hold for anyone but this one team?)")
    print("=" * 72)
    print("  The utility has 3 unknowns, so re-recovery needs >=3 rounds with")
    print("  linearly independent label counts, and 5 gives 2 out-of-sample checks")
    print("  -- exactly what we have for USA.")
    print()
    print("  So ONE team-event = one independent re-recovery.")
    print()
    print("  To distinguish 'this is the tool's utility' from 'this is how USA")
    print("  played', you need the SAME constants to fall out of several teams.")
    print("  Rule of thumb for a consistency claim: 8-12 independent recoveries,")
    print("  and they must be teams using the SAME rival tool, or you are pooling")
    print("  different objectives and will recover their average, which is nobody's.")
    print()
    print("  This is the CHEAPEST of the three questions and the one that should")
    print("  be answered first: it needs ~10 team-events of labelled cells, and if")
    print("  it fails, Q2 and Q3 are moot because there is no single rival model")
    print("  to calibrate.")

if __name__ == "__main__":
    main()
