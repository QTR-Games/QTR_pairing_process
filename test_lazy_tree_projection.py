from __future__ import annotations

from types import SimpleNamespace

import pytest

from golden_master_harness import tk_treeview
from golden_master_scenarios import THREE_V_THREE_UNIFORM
from qtr_pairing_process.ui_manager_v2 import UiManager
from qtr_pairing_process.tree_generator import TreeGenerator


pytestmark = pytest.mark.requires_tk


def _tree_row_count(tree, parent=""):
    total = 0
    for child in tree.get_children(parent):
        total += 1 + _tree_row_count(tree, child)
    return total


def _naive_widget_all_strategic_zero(tree, generator, parent=""):
    for child in tree.get_children(parent):
        if generator.get_strategic3_from_tags(child) != 0:
            return False
        if not _naive_widget_all_strategic_zero(tree, generator, child):
            return False
    return True


def test_lazy_projection_materializes_on_open_and_global_zero_check_uses_model(monkeypatch):
    monkeypatch.setenv("QTR_ENGINE", "model")
    monkeypatch.setenv("QTR_RENDER", "lazy")
    scenario = THREE_V_THREE_UNIFORM

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
        generator.calculate_all_path_values_enhanced("")
        generator.calculate_confidence_scores_enhanced("")
        generator.calculate_counter_resistance_scores_enhanced("")
        generator.calculate_strategic3_scores("")

        model_rows = sum(1 for _ in generator._walk_model_nodes(None))
        initial_rows = _tree_row_count(treeview.tree)
        assert initial_rows < model_rows

        root_id = treeview.tree.get_children("")[0]
        first_child = treeview.tree.get_children(root_id)[0]
        placeholder = treeview.tree.get_children(first_child)
        assert len(placeholder) == 1
        assert generator.projector.is_placeholder(treeview.tree, placeholder[0])

        treeview.tree.focus(first_child)
        generator._on_lazy_tree_open(SimpleNamespace(widget=treeview.tree))
        treeview.tree.item(first_child, open=True)

        materialized_children = treeview.tree.get_children(first_child)
        assert len(materialized_children) == len(generator.model_root.children[0].children)
        assert all(
            not generator.projector.is_placeholder(treeview.tree, child)
            for child in materialized_children
        )

        expanded_model_node = generator.projector.node_for(first_child)
        generator.model_root.children.reverse()
        generator._project_model()
        expanded_widget_id = generator.projector.widget_id_for(expanded_model_node)
        assert expanded_widget_id is not None
        assert treeview.tree.item(expanded_widget_id, "open")
        assert len(treeview.tree.get_children(expanded_widget_id)) == len(expanded_model_node.children)

        for model_node in generator.projector.widget_to_node.values():
            model_node.strategic3 = 0
            generator.projector.mark_metric(model_node, "strategic3_")
        hidden_parent = next(
            child
            for child in generator.model_root.children
            if child is not expanded_model_node and child.children
        )
        hidden_node = hidden_parent.children[0]
        assert generator.projector.widget_id_for(hidden_node) is None
        hidden_node.strategic3 = 7
        generator.projector.mark_metric(hidden_node, "strategic3_")

        ui = UiManager.__new__(UiManager)
        ui.treeview = treeview
        ui.tree_generator = generator

        assert _naive_widget_all_strategic_zero(treeview.tree, generator) is True
        assert UiManager._all_strategic_scores_are_zero(ui) is False


def test_lazy_render_flag_falls_back_to_eager_for_widget_engine(monkeypatch):
    monkeypatch.setenv("QTR_ENGINE", "widget")
    monkeypatch.setenv("QTR_RENDER", "lazy")
    scenario = THREE_V_THREE_UNIFORM

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

        assert generator.render_mode == "eager"
        assert _tree_row_count(treeview.tree) == 118
