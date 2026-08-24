"""Regression tests for strategic sorting when the strategic memo is warm.

`apply_combined_sort` deliberately sets `_materialize_strategic_tags_on_memo_hit`
to False while it runs the fused calculation, so nodes that hit the memo never
get their `strategic3` / `strategic3_exploit` fields written. That is fine as
long as every reader goes through the memo-aware accessors. The lazy model
sorter used to read the raw fields instead, which ranked every memo-hit row as
zero and silently degraded "smart sort" to insertion order.
"""

from __future__ import annotations

import pytest

from golden_master_harness import tk_treeview
from golden_master_scenarios import THREE_V_THREE_UNIFORM
from qtr_pairing_process.tree_generator import TreeGenerator
from qtr_pairing_process.ui_manager_v2 import UiManager

pytestmark = pytest.mark.requires_tk


def _build_generator(treeview):
    scenario = THREE_V_THREE_UNIFORM
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
    generator.calculate_all_path_values_enhanced("")
    generator.calculate_confidence_scores_enhanced("")
    generator.calculate_counter_resistance_scores_enhanced("")
    return generator


def _ui_for(generator):
    ui = UiManager.__new__(UiManager)
    ui.tree_generator = generator
    ui.column_sort_states = {}
    ui.tie_break_order = "confidence_then_cumulative"
    return ui


def _is_monotonic(values):
    non_increasing = all(a >= b for a, b in zip(values, values[1:], strict=False))
    non_decreasing = all(a <= b for a, b in zip(values, values[1:], strict=False))
    return non_increasing or non_decreasing


def test_lazy_strategic_sort_uses_memo_when_tags_are_suppressed(monkeypatch):
    monkeypatch.setenv("QTR_ENGINE", "model")
    monkeypatch.setenv("QTR_RENDER", "lazy")

    with tk_treeview() as warm_view:
        warm = _build_generator(warm_view)
        warm.calculate_strategic3_scores("")
        memo = dict(warm._strategic_memo)
        memo_context = warm._strategic_memo_context

    assert memo, "warm run should populate the strategic memo"

    with tk_treeview() as cold_view:
        cold = _build_generator(cold_view)
        # Simulate a restored persistent memo on a freshly generated tree.
        cold._strategic_memo = dict(memo)
        cold._strategic_memo_context = memo_context
        # This is what apply_combined_sort does around the fused calculation.
        cold._materialize_strategic_tags_on_memo_hit = False
        cold.calculate_strategic3_scores("")

        top_level = cold.model_root.children
        assert len(top_level) > 2

        # The raw fields are stale by design here; that is the whole point.
        assert all(int(node.strategic3) == 0 for node in top_level)

        scores = [int(cold.get_strategic3_from_tags(n)) for n in top_level]
        assert len(set(scores)) > 1, "scenario must not be degenerate"

        _ui_for(cold)._sort_model_children_combined("strategic3", None)

        sorted_scores = [
            int(cold.get_strategic3_from_tags(n)) for n in cold.model_root.children
        ]
        assert _is_monotonic(sorted_scores), (
            "smart sort must order rows by their real strategic score, "
            f"got {sorted_scores}"
        )


def test_exploitability_accessor_falls_back_to_memo(monkeypatch):
    monkeypatch.setenv("QTR_ENGINE", "model")
    monkeypatch.setenv("QTR_RENDER", "lazy")

    with tk_treeview() as treeview:
        generator = _build_generator(treeview)
        node = generator.model_root.children[0]

        assert not generator.projector.has_metric(node, "strategic3_exploit_")

        memo_key = generator._build_structural_memo_key_model(node)
        generator._strategic_memo[memo_key] = {
            "strategic3": 71,
            "strategic3_exploit": 23,
        }

        assert generator.get_strategic3_from_tags(node) == 71
        assert generator.get_strategic3_exploitability_from_tags(node) == 23
