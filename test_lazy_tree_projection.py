from __future__ import annotations

from types import SimpleNamespace

import pytest

from golden_master_harness import tk_treeview
from golden_master_scenarios import THREE_V_THREE_UNIFORM
from qtr_pairing_process.tree_generator import TreeGenerator
from qtr_pairing_process.ui_manager_v2 import UiManager

pytestmark = pytest.mark.requires_tk


def _tree_row_count(tree, parent=""):
    total = 0
    for child in tree.get_children(parent):
        total += 1 + _tree_row_count(tree, child)
    return total


def _widget_structure(tree, parent=""):
    return [
        (tree.item(child, "text"), _widget_structure(tree, child))
        for child in tree.get_children(parent)
    ]


def _model_structure(node):
    return [
        (child.text, _model_structure(child))
        for child in node.children
    ]


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


def test_eager_projection_preserves_expansion_focus_and_selection(monkeypatch):
    monkeypatch.setenv("QTR_ENGINE", "model")
    monkeypatch.setenv("QTR_RENDER", "eager")
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

        root_id = treeview.tree.get_children("")[0]
        opened_id = treeview.tree.get_children(root_id)[0]
        selected_id = treeview.tree.get_children(root_id)[1]
        opened_node = generator.projector.node_for(opened_id)
        selected_node = generator.projector.node_for(selected_id)

        treeview.tree.item(root_id, open=True)
        treeview.tree.item(opened_id, open=True)
        treeview.tree.selection_set(selected_id)
        treeview.tree.focus(selected_id)

        generator.model_root.children.reverse()
        generator._project_model()

        restored_opened_id = generator.projector.widget_id_for(opened_node)
        restored_selected_id = generator.projector.widget_id_for(selected_node)
        assert restored_opened_id is not None
        assert restored_selected_id is not None
        assert treeview.tree.item(restored_opened_id, "open")
        assert treeview.tree.focus() == restored_selected_id
        assert treeview.tree.selection() == (restored_selected_id,)


def test_lazy_and_eager_combined_strategic_sort_match(monkeypatch):
    scenario = THREE_V_THREE_UNIFORM

    def build_ui(treeview, generator):
        ui = UiManager.__new__(UiManager)
        ui.treeview = treeview
        ui.tree_generator = generator
        ui.column_sort_states = {"#0": "none", "Rating": "none", "Sort Value": "none"}
        ui.tie_break_order = "confidence_then_cumulative"
        return ui

    monkeypatch.setenv("QTR_ENGINE", "model")
    monkeypatch.setenv("QTR_RENDER", "eager")
    with tk_treeview() as eager_treeview:
        eager_generator = TreeGenerator(
            treeview=eager_treeview,
            sort_alpha=False,
            strategic_preferences={},
            rating_system=scenario.rating_system,
        )
        eager_generator.generate_combinations(
            list(scenario.our_players),
            list(scenario.opponent_players),
            scenario.our_ratings,
            scenario.opponent_ratings,
            our_team_first=scenario.our_team_first,
        )
        eager_generator.calculate_all_path_values_enhanced("")
        eager_generator.calculate_confidence_scores_enhanced("")
        eager_generator.calculate_counter_resistance_scores_enhanced("")
        eager_generator.calculate_strategic3_scores("")
        build_ui(eager_treeview, eager_generator)._sort_children_combined("", "strategic3", None)
        eager_structure = _widget_structure(eager_treeview.tree)

    monkeypatch.setenv("QTR_RENDER", "lazy")
    with tk_treeview() as lazy_treeview:
        lazy_generator = TreeGenerator(
            treeview=lazy_treeview,
            sort_alpha=False,
            strategic_preferences={},
            rating_system=scenario.rating_system,
        )
        lazy_generator.generate_combinations(
            list(scenario.our_players),
            list(scenario.opponent_players),
            scenario.our_ratings,
            scenario.opponent_ratings,
            our_team_first=scenario.our_team_first,
        )
        lazy_generator.calculate_all_path_values_enhanced("")
        lazy_generator.calculate_confidence_scores_enhanced("")
        lazy_generator.calculate_counter_resistance_scores_enhanced("")
        lazy_generator.calculate_strategic3_scores("")
        build_ui(lazy_treeview, lazy_generator)._sort_children_combined("", "strategic3", None)
        lazy_structure = [(lazy_generator.model_root.text, _model_structure(lazy_generator.model_root))]

    assert eager_structure == lazy_structure


def test_save_original_order_captures_nested_model_children(monkeypatch):
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

        nested_node = generator.model_root.children[0].children[0]
        generator.save_original_order()

        assert id(generator.model_root) in generator._model_original_order
        assert id(nested_node) in generator._model_original_order


def test_hidden_confidence_aux_metrics_stay_on_model_nodes(monkeypatch):
    monkeypatch.setenv("QTR_ENGINE", "model")
    monkeypatch.setenv("QTR_RENDER", "lazy")
    scenario = THREE_V_THREE_UNIFORM

    with tk_treeview() as treeview:
        reference = TreeGenerator(
            treeview=treeview,
            sort_alpha=False,
            strategic_preferences={},
            rating_system=scenario.rating_system,
        )
        reference.generate_combinations(
            list(scenario.our_players),
            list(scenario.opponent_players),
            scenario.our_ratings,
            scenario.opponent_ratings,
            our_team_first=scenario.our_team_first,
        )
        reference.calculate_confidence_scores_enhanced("")
        expected_floor2 = reference.model_root.children[0].floor2
        expected_ceiling2 = reference.model_root.children[0].ceiling2

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
        generator._confidence_aux_tags_enabled = False
        generator.calculate_confidence_scores_enhanced("")

        node = generator.model_root.children[0]
        assert node.floor2 == expected_floor2
        assert node.ceiling2 == expected_ceiling2
        assert generator.projector.has_metric(node, "floor2_") is False
        assert generator.projector.has_metric(node, "ceiling2_") is False
