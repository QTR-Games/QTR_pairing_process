"""Conservation guard: the engine must not assume the opponent cooperates.

Ratings are strictly zero-sum. The app's own "flip to the opponent's
perspective" feature defines their view of a matchup as ``6 - r`` on the 1-5
scale (ui_manager_v2.py), so for any single game the two teams' points sum to
6, and across ``n`` games their round totals sum to ``6n``. This is not an
assumption -- distribution_scoring.contributes_to_total's docstring already
relies on it.

That yields a test with no external ground truth. Solve the SAME game from both
seats (players swapped, every rating replaced by ``6 - r``, and the "who
chooses first" flag inverted). A propagation rule that neither flatters nor
punishes us must produce two root values summing to ``6n``. A rule that lets
each side assume the other cooperates makes BOTH sides overestimate, so the sum
comes out high; the excess is the cooperation bias in tournament points.

Measured on real event data (Team Irving 2024, six opponents), the excess is:

    optimistic (max at every level)   mean +1.67, never below 0
    minimax    (min at their levels)  mean -1.83, never above 0
    quantal    (what the engine does) mean -0.18

So "just flip max to min" is not the fix -- pure minimax is wrong by about as
much as pure optimism, in the opposite direction. These tests pin that result.
"""

from __future__ import annotations

import pytest

from golden_master_harness import golden_master_environment, tk_treeview
from qtr_pairing_process.distribution_scoring import (
    DistributionScorer,
    contributes_to_total,
)
from qtr_pairing_process.tree_generator import TreeGenerator

FLIP = 6
MODEL_ENV = {"QTR_ENGINE": "model", "QTR_RENDER": "lazy"}

OUR_PLAYERS = ("Ada", "Bo", "Cy", "Di")
OPP_PLAYERS = ("Wu", "Xi", "Ya", "Zo")

# Deliberately uneven so that a biased rule has room to show itself. A flat
# grid would conserve under every rule and prove nothing.
RATING_ROWS = (
    (4, 2, 3, 1),
    (1, 3, 5, 2),
    (3, 4, 2, 4),
    (2, 1, 4, 3),
)

CONSERVED = FLIP * len(OUR_PLAYERS)


def _grids():
    ours = {
        name: {opp: RATING_ROWS[i][j] for j, opp in enumerate(OPP_PLAYERS)}
        for i, name in enumerate(OUR_PLAYERS)
    }
    theirs = {
        opp: {name: FLIP - ours[name][opp] for name in OUR_PLAYERS}
        for opp in OPP_PLAYERS
    }
    return ours, theirs


def _own_value(node):
    if node.parent is None or not contributes_to_total(node):
        return 0
    return int(getattr(node, "base_for_our_team", node.base))


def _propagate_optimistic(root):
    """max() at every level -- the rule tree_generator's 'cumulative' uses."""
    values: dict[int, float] = {}
    stack = [(root, False)]
    while stack:
        node, done = stack.pop()
        if not done:
            stack.append((node, True))
            stack.extend((child, False) for child in node.children)
            continue
        own = _own_value(node)
        if not node.children:
            values[id(node)] = float(own)
        else:
            values[id(node)] = own + max(values[id(c)] for c in node.children)
    return values[id(root)]


def _solve(names_a, names_b, ratings_a, ratings_b, *, a_first):
    with golden_master_environment(MODEL_ENV), tk_treeview() as treeview:
        generator = TreeGenerator(
            treeview=treeview,
            sort_alpha=False,
            strategic_preferences={},
            rating_system="1-5",
        )
        generator.generate_combinations(
            list(names_a), list(names_b), ratings_a, ratings_b,
            our_team_first=a_first,
        )
        root = generator.model_root
        scorer = DistributionScorer(threshold=CONSERVED // 2, objective="expected")
        return {
            "quantal": scorer.outcome_for(root).expected,
            "optimistic": _propagate_optimistic(root),
        }


@pytest.fixture(scope="module")
def both_seats():
    ours, theirs = _grids()
    return (
        _solve(OUR_PLAYERS, OPP_PLAYERS, ours, theirs, a_first=True),
        _solve(OPP_PLAYERS, OUR_PLAYERS, theirs, ours, a_first=False),
    )


@pytest.mark.requires_tk
def test_mirror_is_a_faithful_reflection(both_seats):
    """Guard the construction itself before drawing conclusions from it.

    Under max-at-every-level both seats solve structurally identical problems,
    so their root values must agree. If this fails the mirror is wrong and the
    conservation numbers below mean nothing.
    """
    us, them = both_seats
    assert us["optimistic"] == pytest.approx(them["optimistic"])


@pytest.mark.requires_tk
def test_optimistic_propagation_violates_conservation(both_seats):
    """The v1 'cumulative' rule lets both sides win the same points.

    max() at opponent levels means we assume they hand us their best branch --
    and they assume the same of us. Both totals inflate, so the sum sits at or
    above the conserved total. It can never sit below it.
    """
    us, them = both_seats
    assert us["optimistic"] + them["optimistic"] >= CONSERVED


@pytest.mark.requires_tk
def test_optimistic_bias_is_strictly_positive_on_an_uneven_grid(both_seats):
    """Non-vacuity: on this grid the violation is real, not merely non-negative."""
    us, them = both_seats
    assert us["optimistic"] + them["optimistic"] > CONSERVED


@pytest.mark.requires_tk
def test_quantal_propagation_is_closer_to_conservation(both_seats):
    """The shipped engine must beat the rule it replaced, on the engine's own terms."""
    us, them = both_seats
    quantal_error = abs(us["quantal"] + them["quantal"] - CONSERVED)
    optimistic_error = abs(us["optimistic"] + them["optimistic"] - CONSERVED)
    assert quantal_error < optimistic_error
