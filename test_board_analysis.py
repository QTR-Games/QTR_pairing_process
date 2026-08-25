"""Tests for qtr_pairing_process.board_analysis.

Pure math: no Tk, no database, no GUI. The Hungarian solver is cross-checked
against exhaustive enumeration, which is the only way to be sure an O(n^3)
assignment routine is right.
"""

import itertools
import random

import pytest

from qtr_pairing_process.board_analysis import (
    LIVE,
    SECURED,
    UNWINNABLE,
    assignment_extremes,
    board_outlook,
    cell_outlooks,
    decision_report,
    even_threshold,
)


def brute_force_extremes(matrix):
    """Reference implementation: enumerate every assignment."""
    n = len(matrix)
    totals = [
        sum(matrix[i][perm[i]] for i in range(n))
        for perm in itertools.permutations(range(len(matrix[0])), n)
    ]
    return min(totals), max(totals)


# --- the solver itself -------------------------------------------------------


@pytest.mark.parametrize("size", [1, 2, 3, 4, 5, 6])
def test_assignment_extremes_match_brute_force(size):
    rng = random.Random(1234 + size)
    for _ in range(40):
        matrix = [[rng.randint(1, 5) for _ in range(size)] for _ in range(size)]
        assert assignment_extremes(matrix) == pytest.approx(brute_force_extremes(matrix))


def test_assignment_extremes_handles_floats_and_negatives():
    matrix = [[-1.5, 2.25], [3.75, -0.5]]
    assert assignment_extremes(matrix) == pytest.approx(brute_force_extremes(matrix))


def test_assignment_extremes_on_empty_board():
    assert assignment_extremes([]) == (0.0, 0.0)


def test_assignment_rejects_more_rows_than_columns():
    with pytest.raises(ValueError):
        assignment_extremes([[1, 2], [3, 4], [5, 6]])


# --- the dead-even line ------------------------------------------------------


def test_even_threshold_matches_documented_formula():
    # docs/SCORING_MATHEMATICS.md section 1.4: tau = G * (lo + hi) / 2
    assert even_threshold(5, 1, 5) == 15.0
    assert even_threshold(4, 1, 5) == 12.0
    assert even_threshold(5, 1, 3) == 10.0
    assert even_threshold(5, 1, 10) == 27.5


def test_even_threshold_is_scale_independent():
    """A 1-5 board and a 0-100 board describe the same round differently."""
    assert even_threshold(5, 0, 100) == 250.0
    assert even_threshold(0, 1, 5) == 0.0


def test_even_threshold_rejects_negative_games():
    with pytest.raises(ValueError):
        even_threshold(-1)


# --- outlook semantics -------------------------------------------------------


def test_spread_is_zero_when_every_assignment_scores_the_same():
    flat = [[3, 3], [3, 3]]
    outlook = board_outlook(flat, even_threshold(2))
    assert outlook.spread == 0
    assert outlook.is_decided


def test_verdict_unwinnable_when_ceiling_cannot_clear_tau():
    outlook = board_outlook([[3, 3], [3, 3]], even_threshold(2))
    assert outlook.ceiling == 6.0
    assert outlook.tau == 6.0
    assert outlook.verdict == UNWINNABLE


def test_verdict_secured_when_floor_already_clears_tau():
    outlook = board_outlook([[5, 4], [4, 5]], even_threshold(2))
    assert outlook.floor > outlook.tau
    assert outlook.verdict == SECURED


def test_verdict_live_when_pairing_still_decides_it():
    outlook = board_outlook([[5, 1], [1, 5]], even_threshold(2))
    assert outlook.verdict == LIVE
    assert not outlook.is_decided


def test_committed_points_shift_both_bounds_equally():
    matrix = [[4, 2], [1, 5]]
    base = board_outlook(matrix, even_threshold(2))
    shifted = board_outlook(matrix, even_threshold(2), committed=7.0)
    assert shifted.floor == base.floor + 7.0
    assert shifted.ceiling == base.ceiling + 7.0
    assert shifted.spread == base.spread


# --- per-cell decomposition --------------------------------------------------


def test_cell_outlook_covers_every_pairing():
    matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    cells = cell_outlooks(matrix, even_threshold(3))
    assert set(cells) == {(i, j) for i in range(3) for j in range(3)}


def test_cell_outlook_bounds_are_contained_by_the_board():
    matrix = [[4, 2, 1], [3, 5, 2], [1, 3, 4]]
    tau = even_threshold(3)
    board = board_outlook(matrix, tau)
    for outlook in cell_outlooks(matrix, tau).values():
        assert outlook.floor >= board.floor
        assert outlook.ceiling <= board.ceiling


def test_board_extremes_are_attained_by_some_cell():
    """Every optimal assignment passes through one of its own cells."""
    matrix = [[4, 2, 1], [3, 5, 2], [1, 3, 4]]
    tau = even_threshold(3)
    board = board_outlook(matrix, tau)
    cells = cell_outlooks(matrix, tau).values()
    assert min(c.floor for c in cells) == board.floor
    assert max(c.ceiling for c in cells) == board.ceiling


# --- the decision report -----------------------------------------------------


def test_safe_and_bold_diverge_when_the_safe_choice_forecloses_winning():
    """A real board where playing safe guarantees a draw and gives up the win.

    Opponent 23, the home team's own scenario-0 ratings. Pairing
    Echo into their first list pins the round at exactly tau: floor 15.0, ceiling
    15.0. It cannot be lost and it cannot be won. Pairing Bravo into the same
    opponent is floor 14.0, ceiling 16.0 -- it risks the round to keep the win
    reachable at all.

    This is the trade-off the single-number sort collapses, and the reason
    "play to your outs" is a real strategy rather than a slogan.
    """
    report = decision_report(WTC_TRADEOFF_BOARD, even_threshold(5))
    assert report.choice_matters
    assert report.safest.outlook.floor > report.boldest.outlook.floor
    assert report.boldest.outlook.ceiling > report.safest.outlook.ceiling
    assert report.floor_at_stake == pytest.approx(1.0)
    assert report.ceiling_at_stake == pytest.approx(1.0)
    # The safe cell is pinned to tau exactly: safe from defeat, incapable of victory.
    assert report.safest.outlook.floor == report.safest.outlook.ceiling == 15.0
    assert report.boldest.outlook.ceiling > 15.0


def test_a_dominating_choice_is_not_reported_as_a_trade_off():
    """When one pairing is best on both bounds, there is nothing to trade."""
    matrix = [[5, 1, 1], [1, 5, 1], [1, 1, 5]]
    report = decision_report(matrix, even_threshold(3))
    assert not report.choice_matters
    assert len({(c.outlook.floor, c.outlook.ceiling) for c in report.frontier}) == 1
    assert report.floor_at_stake == 0.0
    assert report.ceiling_at_stake == 0.0


def test_dominated_cells_are_excluded_from_the_frontier():
    report = decision_report(WTC_TRADEOFF_BOARD, even_threshold(5))
    assert len(report.frontier) < 25
    for cell in report.frontier:
        assert not any(other.dominates(cell) for other in report.frontier)


def test_hidden_floor_cost_is_the_spread_among_ceiling_tied_cells():
    """The number a ceiling-only metric cannot see."""
    tau = even_threshold(5)
    report = decision_report(WTC_FLAT_BOARD, tau)
    cells = cell_outlooks(WTC_FLAT_BOARD, tau).values()
    best_ceiling = max(c.ceiling for c in cells)
    tied = [c.floor for c in cells if c.ceiling == best_ceiling]
    assert report.hidden_floor_cost == pytest.approx(max(tied) - min(tied))
    assert report.hidden_floor_cost > 0


def test_report_is_independent_of_row_and_column_order():
    """Presentation order must not change what is recommended."""
    matrix = [[4, 2, 1], [3, 5, 2], [1, 3, 4]]
    tau = even_threshold(3)
    first = decision_report(matrix, tau)
    order = [2, 0, 1]
    shuffled = [[matrix[i][j] for j in order] for i in order]
    second = decision_report(shuffled, tau)
    assert first.board.floor == second.board.floor
    assert first.board.ceiling == second.board.ceiling
    assert first.safest.outlook.floor == second.safest.outlook.floor
    assert first.boldest.outlook.ceiling == second.boldest.outlook.ceiling


def test_report_rejects_an_empty_board():
    with pytest.raises(ValueError):
        decision_report([], 0.0)


# --- regression: the real WTC 2024 board -------------------------------------

# the home team's own pre-event ratings against Opponent 02, scenario
# 0, taken from teamthe home team2024_FinalDB.db. Rows are Bravo, Charlie, Delta, Echo,
# Alpha; columns are Nads, Robin, Pottsie, Aleks, James.
# See docs/WTC2024_GROUND_TRUTH.md, Findings 12 and 13.
WTC_FLAT_BOARD = [
    [3, 3, 3, 2, 3],
    [3, 3, 2, 2, 3],
    [3, 3, 3, 3, 3],
    [3, 3, 2, 3, 1],
    [3, 3, 3, 1, 3],
]

# the home team vs Opponent 23, same database and scenario. Rows are
# Bravo, Charlie, Delta, Echo, Alpha; columns are their first list, their third list,
# their fourth list, their fifth list, their fifth list. This is the one board of 31 that
# carries a genuine floor-versus-ceiling trade-off rather than a dominant cell.
WTC_TRADEOFF_BOARD = [
    [4, 3, 3, 3, 3],
    [2, 3, 3, 3, 3],
    [3, 3, 3, 3, 3],
    [3, 2, 3, 3, 1],
    [3, 3, 3, 3, 3],
]


def test_australia_board_was_unwinnable_on_our_own_ratings():
    """The round that ended the home team's 2024 run could not be won.

    The best assignment available scored exactly tau, and a round is won
    strictly above tau. No pairing decision could have changed that, which is
    information the app has never surfaced.
    """
    outlook = board_outlook(WTC_FLAT_BOARD, even_threshold(5))
    assert outlook.ceiling == 15.0
    assert outlook.tau == 15.0
    assert outlook.verdict == UNWINNABLE
    assert outlook.ceiling_margin == 0.0


def test_australia_board_floor_and_ceiling_match_exhaustive_enumeration():
    assert assignment_extremes(WTC_FLAT_BOARD) == pytest.approx(brute_force_extremes(WTC_FLAT_BOARD))
    assert assignment_extremes(WTC_FLAT_BOARD) == (10.0, 15.0)


def test_australia_board_hides_four_points_of_floor_behind_a_tied_ceiling():
    """One cell dominates -- and the current metric cannot tell.

    Nineteen of the twenty-five pairings reach the same ceiling of 15.0, so a
    ceiling-only score rates them equally. Their guaranteed floors range from
    10.0 to 14.0. Four points of downside are invisible, and there is a pairing
    that protects all four of them at zero cost to the upside.
    """
    report = decision_report(WTC_FLAT_BOARD, even_threshold(5))
    assert not report.choice_matters
    assert report.hidden_floor_cost == pytest.approx(4.0)
    assert report.safest.outlook.floor == pytest.approx(14.0)
    assert report.safest.outlook.ceiling == pytest.approx(15.0)
    assert report.floor_at_stake == 0.0
    assert report.ceiling_at_stake == 0.0
