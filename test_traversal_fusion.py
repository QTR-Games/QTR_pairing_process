from __future__ import annotations

import pytest

from golden_master_harness import SORT_MODES, tk_treeview
from golden_master_scenarios import SCENARIOS
from qtr_pairing_process.tree_generator import TreeGenerator


# The pre-fusion 5v5 baseline was 243,760 _walk_model_nodes calls and
# 2,303,760 yielded nodes during enhanced_v3 scoring. The optimized pass should
# materialize the model tree once and reuse that list for memo materialization,
# strategic3 ranges, and strategic3 tag materialization.
MAX_5V5_SCORING_WALK_CALLS = 3
MAX_5V5_SCORING_WALK_YIELDS = 60_000


@pytest.mark.requires_tk
def test_enhanced_v3_model_scoring_reuses_single_tree_materialization(monkeypatch):
    monkeypatch.setenv("QTR_ENGINE", "model")
    monkeypatch.setenv("QTR_RENDER", "lazy")

    scenarios = SCENARIOS.values() if isinstance(SCENARIOS, dict) else SCENARIOS
    scenario = next(s for s in scenarios if s.slug.startswith("5v5"))
    original_walk = TreeGenerator._walk_model_nodes
    counters = {"calls": 0, "yielded": 0}

    def counting_walk(self, arg):
        counters["calls"] += 1
        for node in original_walk(self, arg):
            counters["yielded"] += 1
            yield node

    with tk_treeview() as treeview:
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

        monkeypatch.setattr(TreeGenerator, "_walk_model_nodes", counting_walk)
        SORT_MODES["enhanced_v3_scores"](generator)

    assert counters["calls"] <= MAX_5V5_SCORING_WALK_CALLS
    assert counters["yielded"] <= MAX_5V5_SCORING_WALK_YIELDS
