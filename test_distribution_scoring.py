"""Tests for the distribution scoring engine.

These are deliberately Tk-free: the engine works on the plain PairingNode
model, so its behaviour can be pinned without a GUI. That is the point of
having a Tk-free domain model in the first place.
"""

from __future__ import annotations

import math

import pytest

from qtr_pairing_process.distribution_scoring import (
    DistributionScorer,
    Outcome,
    contributes_to_total,
    mix,
    point_mass,
    prob_at_least,
    shift,
    softmax,
    win_threshold,
)
from qtr_pairing_process.pairing_model import PairingNode


def _node(
    text,
    base,
    depth,
    is_opponent_choice=False,
    parent=None,
    *,
    counts_toward_total=False,
    base_for_our_team=None,
):
    node = PairingNode(
        text=text, base=base, depth=depth,
        is_opponent_choice=is_opponent_choice, parent=parent,
        counts_toward_total=counts_toward_total,
        base_for_our_team=base if base_for_our_team is None else base_for_our_team,
    )
    if parent is not None:
        parent.children.append(node)
    return node


# --------------------------------------------------------------------------
# threshold derivation
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "rating_range, games, expected",
    [
        ((1, 3), 5, 10.0),
        ((1, 5), 5, 15.0),
        ((1, 10), 5, 27.5),
        ((1, 5), 3, 9.0),
    ],
)
def test_win_threshold_is_the_midpoint_of_the_rating_range(rating_range, games, expected):
    """A dead-even round scores the midpoint rating in every game.

    Each shipped rating system's own documented "even" value is the midpoint
    of its range, so this generalises rather than being tuned per system.
    """
    assert win_threshold(rating_range, games) == expected


@pytest.mark.parametrize(
    "threshold, need",
    [(15.0, 16), (27.5, 28), (10.0, 11), (9.0, 10)],
)
def test_win_need_is_the_smallest_integer_total_that_wins(threshold, need):
    """Totals are integers, so "> 15.0" is exactly ">= 16"."""
    assert DistributionScorer(threshold=threshold).win_need == need


# --------------------------------------------------------------------------
# distribution algebra
# --------------------------------------------------------------------------

def test_algebra_preserves_probability_mass():
    a, b = point_mass(3), point_mass(7)
    combined = mix([a, b, shift(a, 2)], [0.5, 0.25, 0.25])
    assert math.isclose(sum(combined.values()), 1.0, rel_tol=1e-12)


def test_shift_translates_support_without_changing_shape():
    dist = mix([point_mass(1), point_mass(4)], [0.3, 0.7])
    moved = shift(dist, 5)
    assert moved == {6: 0.3, 9: 0.7}


def test_softmax_is_overflow_safe_on_large_lambda():
    """Naive exp() overflows here; the result must stay a valid distribution."""
    weights = softmax([1000.0, 0.0, -1000.0], lam=50.0)
    assert math.isclose(sum(weights), 1.0, rel_tol=1e-12)
    assert math.isclose(weights[0], 1.0, abs_tol=1e-9)


def test_softmax_evaluates_the_documented_infinite_lambda_limit():
    """``lam -> infinity`` is documented as pure minimax.

    Taken literally in the exponential it gives ``inf * 0 == nan`` for the
    maximising entries, which then silently poisons every downstream
    statistic instead of raising. Not reachable from the app (QTR_RISK_LAMBDA
    rejects non-finite values) but ``softmax`` is a public helper.
    """
    weights = softmax([5.0, 5.0, 3.0], lam=float("inf"))

    assert not any(math.isnan(w) for w in weights)
    assert math.isclose(sum(weights), 1.0, rel_tol=1e-12)
    # All mass on the joint maximisers, shared evenly.
    assert math.isclose(weights[0], 0.5)
    assert math.isclose(weights[1], 0.5)
    assert weights[2] == 0.0


def test_prob_at_least_counts_the_inclusive_tail():
    dist = {14: 0.25, 15: 0.25, 16: 0.5}
    assert math.isclose(prob_at_least(dist, 16), 0.5)
    assert math.isclose(prob_at_least(dist, 15), 0.75)


def test_outcome_orders_floor_expected_and_ceiling():
    dist = mix([point_mass(10), point_mass(20)], [0.5, 0.5])
    outcome = Outcome(dist, threshold=15.0)
    assert outcome.floor == 10
    assert outcome.ceiling == 20
    assert outcome.floor <= outcome.expected <= outcome.ceiling
    assert math.isclose(outcome.win_probability, 0.5)


# --------------------------------------------------------------------------
# the accumulation rule
# --------------------------------------------------------------------------

def test_only_resolutions_and_forced_finals_count_toward_the_total():
    """Offers announce what is on the table; resolutions record what happened.

    Counting both double-counts every game, which inflated round totals from
    ~15 to ~28 and made every opener look like a guaranteed win.
    """
    offer = _node("Dan vs JVM (3/5) OR Brandon (4/5)", 4, 1, counts_toward_total=False)
    resolution = _node("JVM rating 3", 3, 2, parent=offer, counts_toward_total=True)
    assert not contributes_to_total(offer)
    assert contributes_to_total(resolution)
    # A leaf is a forced final pairing: it resolves itself.
    assert contributes_to_total(
        _node(
            "Jack vs Justin (4/5) OR Justin (4/5)",
            4,
            9,
            counts_toward_total=True,
        )
    )


def test_explicit_total_flag_beats_display_text_parsing():
    offer = _node(
        "Chris rating Hunter vs Sam (3/5) OR Lee (4/5)",
        4,
        1,
        counts_toward_total=False,
    )
    resolution = _node(
        "Sam rating 3",
        3,
        2,
        parent=offer,
        counts_toward_total=True,
    )

    assert contributes_to_total(offer) is False
    assert contributes_to_total(resolution) is True


# --------------------------------------------------------------------------
# shift-invariance: the property that decides the memo key
# --------------------------------------------------------------------------

def test_expected_and_floor_are_shift_invariant_but_win_probability_is_not():
    """This is why win probability needs a threshold-indexed memo.

    argmax E[X + c] and argmax min(X + c) do not depend on c, so the game
    state alone is a sufficient memo key. argmax P(X + c > T) DOES depend on
    c, so the same state reached with different banked points is a different
    decision problem.
    """
    safe = mix([point_mass(14), point_mass(16)], [0.5, 0.5])   # E=15, floor 14
    risky = mix([point_mass(10), point_mass(20)], [0.5, 0.5])  # E=15, floor 10

    # Expected value ties regardless of how many points are already banked.
    for banked in (0, 5, 10):
        assert math.isclose(
            sum(v * p for v, p in shift(safe, banked).items()),
            sum(v * p for v, p in shift(risky, banked).items()),
        )

    # Floor prefers `safe` regardless of banked points.
    for banked in (0, 5, 10):
        assert min(shift(safe, banked)) > min(shift(risky, banked))

    # Win probability flips with banked points: needing 16 favours `safe`
    # (0.5 vs 0.5 -- tie), but needing 20 only `risky` can reach.
    assert prob_at_least(safe, 20) == 0.0
    assert prob_at_least(risky, 20) == 0.5


# --------------------------------------------------------------------------
# opponent model
# --------------------------------------------------------------------------

def _two_choice_tree():
    """Root -> our choice of two openers, each with an opponent reply."""
    root = _node("root", 0, 0)
    for opener, (good, bad) in (("A", (6, 2)), ("B", (5, 4))):
        offer = _node(
            f"{opener} vs X (1/5) OR Y (1/5)",
            0,
            1,
            parent=root,
            counts_toward_total=False,
        )
        _node(
            f"X rating {good}",
            good,
            2,
            is_opponent_choice=True,
            parent=offer,
            counts_toward_total=True,
        )
        _node(
            f"Y rating {bad}",
            bad,
            2,
            is_opponent_choice=True,
            parent=offer,
            counts_toward_total=True,
        )
    return root


def test_distribution_uses_our_perspective_for_opponent_side_contributions():
    root = _node("root", 0, 0)
    opener = _node("A vs X (5/5) OR Y (1/5)", 5, 1, parent=root, counts_toward_total=False)
    _node(
        "X rating 5",
        5,
        2,
        is_opponent_choice=True,
        parent=opener,
        counts_toward_total=True,
        base_for_our_team=5,
    )
    _node(
        "Y rating 1",
        1,
        2,
        is_opponent_choice=True,
        parent=opener,
        counts_toward_total=True,
        base_for_our_team=5,
    )

    scorer = DistributionScorer(threshold=15.0, lam=0.0, objective="expected")

    assert math.isclose(scorer.outcome_for(opener).expected, 5.0, abs_tol=1e-9)


def test_large_lambda_converges_to_the_minimax_value():
    """A perfectly sharp opponent always takes our worst branch.

    Opener A yields min(6, 2) = 2; opener B yields min(5, 4) = 4. Against a
    perfect opponent B is correct even though A has the higher ceiling.
    """
    root = _two_choice_tree()
    scorer = DistributionScorer(threshold=15.0, lam=1000.0, objective="expected")
    values = {str(c.text): scorer.outcome_for(c).expected for c in root.children}
    assert math.isclose(min(values.values()), 2.0, abs_tol=1e-6)
    assert math.isclose(max(values.values()), 4.0, abs_tol=1e-6)


def test_lambda_zero_is_a_uniformly_random_opponent():
    """With no skill the opponent picks each reply with equal probability."""
    root = _two_choice_tree()
    scorer = DistributionScorer(threshold=15.0, lam=0.0, objective="expected")
    opener_a = root.children[0]
    assert math.isclose(scorer.outcome_for(opener_a).expected, 4.0, abs_tol=1e-9)


def test_a_weaker_opponent_is_never_worse_for_us():
    """Monotonicity in lambda: sharper opposition cannot help us."""
    root = _two_choice_tree()
    opener_a_expected = []
    for lam in (0.0, 0.5, 2.0, 50.0):
        scorer = DistributionScorer(threshold=15.0, lam=lam, objective="expected")
        opener_a_expected.append(scorer.outcome_for(root.children[0]).expected)
    assert opener_a_expected == sorted(opener_a_expected, reverse=True)


# --------------------------------------------------------------------------
# opener report
# --------------------------------------------------------------------------

@pytest.mark.parametrize("objective", ["win_probability", "expected", "floor"])
def test_opener_report_ranks_every_objective_without_error(objective):
    """Regression: ``opener_report`` dropped the ``need`` argument.

    When win probability stopped being shift-invariant, ``_rank`` gained a
    required ``need`` parameter, but this call site still passed only the
    distribution. Nothing exercised it, so it raised ``TypeError`` the first
    time it was used from the UI rather than from a test.
    """
    root = _two_choice_tree()
    scorer = DistributionScorer(threshold=15.0, lam=1.0, objective=objective)

    report = scorer.opener_report(root)

    assert len(report) == 2
    assert {text for text, _ in report} == {str(c.text) for c in root.children}
    assert all(isinstance(outcome, Outcome) for _, outcome in report)


def test_opener_report_is_sorted_best_first_for_the_active_objective():
    """Against a sharp opponent, B (floor 4) must outrank A (floor 2)."""
    root = _two_choice_tree()
    scorer = DistributionScorer(threshold=15.0, lam=1000.0, objective="expected")

    report = scorer.opener_report(root)

    assert report[0][0].startswith("B vs")
    ranked = [outcome.expected for _, outcome in report]
    assert ranked == sorted(ranked, reverse=True)
