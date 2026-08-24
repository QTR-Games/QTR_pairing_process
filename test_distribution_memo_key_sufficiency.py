"""The canonical memo key must be a *sufficient* description of a game state.

Memoization is only sound if two nodes sharing a canonical key genuinely have
the same value. If the key ever drops a component that the value depends on,
the engine will reuse a distribution computed for a different situation and
every score downstream is quietly wrong -- with no crash and no failing
assertion anywhere else in the suite.

These tests assert the invariant directly: same key => same objective value.
They deliberately compare *objective values* rather than whole distributions.
When two children tie on the objective, ``max()`` keeps whichever came first in
list order, so the retained distribution can differ between two presentations
of the same offer (``A OR B`` vs ``B OR A``) while the score is identical by
construction. See ``docs/SCORING_MATHEMATICS.md`` section 4.2.
"""

from __future__ import annotations

from collections import defaultdict

import pytest

from golden_master_harness import tk_treeview
from golden_master_scenarios import FOUR_V_FOUR_COUNTER_FIRST
from qtr_pairing_process.distribution_scoring import DistributionScorer
from qtr_pairing_process.tree_generator import TreeGenerator

OBJECTIVES = ("expected", "floor", "win_probability")
THRESHOLD = 15.0


@pytest.fixture(autouse=True)
def _model_engine(monkeypatch):
    """The model node graph these tests walk only exists in model engine mode."""
    monkeypatch.setenv("QTR_ENGINE", "model")
    monkeypatch.delenv("QTR_RISK", raising=False)
    monkeypatch.delenv("QTR_RENDER", raising=False)


def _build_nodes(treeview):
    scenario = FOUR_V_FOUR_COUNTER_FIRST
    generator = TreeGenerator(
        treeview=treeview,
        sort_alpha=False,
        strategic_preferences={},
        rating_system=scenario.rating_system,
    )
    generator.generate_combinations(
        list(scenario.our_players),
        list(scenario.opponent_players),
        scenario.our_ratings,
        scenario.opponent_ratings,
        our_team_first=scenario.our_team_first,
    )
    return list(generator._walk_model_nodes(None))


def _group_by_canonical_key(nodes, key_func):
    groups = defaultdict(list)
    for node in nodes:
        groups[key_func(node)].append(node)
    return {key: group for key, group in groups.items() if len(group) > 1}


def _objective_value_spread(group, objective):
    ranker = DistributionScorer(threshold=THRESHOLD, objective=objective)
    values = [
        ranker._rank(
            DistributionScorer(
                threshold=THRESHOLD, objective=objective
            ).distribution_for(node),
            ranker.win_need,
        )
        for node in group
    ]
    return max(values) - min(values)


@pytest.mark.requires_tk
@pytest.mark.parametrize("objective", OBJECTIVES)
def test_same_canonical_key_implies_same_objective_value(objective):
    with tk_treeview() as treeview:
        nodes = _build_nodes(treeview)
        key_func = DistributionScorer(
            threshold=THRESHOLD, objective="expected"
        )._canonical_key
        groups = _group_by_canonical_key(nodes, key_func)

        # Non-vacuity: the invariant is only meaningful if the key actually
        # collapses many nodes. On this scenario it collapses ~1,848 of 1,945.
        assert len(groups) >= 100, f"expected many collapsed groups, got {len(groups)}"

        for key, group in groups.items():
            spread = _objective_value_spread(group, objective)
            assert spread == pytest.approx(0.0, abs=1e-12), (
                f"canonical key is not sufficient for {objective}: "
                f"{len(group)} nodes share key {key!r} but their objective "
                f"values span {spread}"
            )


@pytest.mark.requires_tk
def test_dropping_a_key_component_breaks_the_invariant():
    """Proves the test above is not vacuous.

    A key that omits the remaining player pools merges genuinely different
    situations, so the objective values must disagree. If this test ever
    passes, the check above has stopped being able to detect an unsound key.
    """
    with tk_treeview() as treeview:
        nodes = _build_nodes(treeview)
        full_key = DistributionScorer(
            threshold=THRESHOLD, objective="expected"
        )._canonical_key

        def weakened_key(node):
            # Drop the two remaining-pool frozensets (positions 3 and 4).
            key = full_key(node)
            return key[:3] + key[5:]

        groups = _group_by_canonical_key(nodes, weakened_key)
        worst = max(
            _objective_value_spread(group, "expected") for group in groups.values()
        )
        assert worst > 1e-9, (
            "weakening the canonical key did not change any objective value, "
            "so the sufficiency test cannot detect an unsound key"
        )
