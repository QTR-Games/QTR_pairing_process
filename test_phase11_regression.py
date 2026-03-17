#!/usr/bin/env python3
"""Phase 11 regression coverage for strategic sorting behavior."""

import tkinter as tk
from tkinter import ttk
from contextlib import nullcontext
from typing import cast

from qtr_pairing_process.tree_generator import TreeGenerator
from qtr_pairing_process.ui_manager_v2 import UiManager


class DummyTreeView:
    """Minimal tree wrapper fixture so TreeGenerator can run without full UI wiring."""

    def __init__(self, tree):
        self.tree = tree


class DummyPerf:
    enabled = False

    def span(self, *_args, **_kwargs):
        return nullcontext()


def _base_prefs():
    return {
        "cumulative2": {"alpha": 0.80},
        "confidence2": {"k": 0.85, "u": 12.0},
        "resistance2": {"beta": 1.0, "gamma": 2.0},
        "strategic3": {
            "weights": [0.40, 0.35, 0.25],
            "rho": 0.20,
            "lam": 0.30,
            "round_win_guardrail_strength": "medium",
        },
        "bus": {
            "threshold_policy": "scenario_dependent",
            "global_threshold": 60,
            "scenario_thresholds": {},
            "depth_thresholds": {"1": 65, "2": 62, "3": 58, "4": 55, "5": 52},
        },
    }


def _build_sample_tree(gen, tree):
    root_node = tree.insert("", "end", text="Pairings", values=(0, 0), tags=("0",))
    a = tree.insert(root_node, "end", text="A vs X", values=(5, 0), tags=("5",))
    b = tree.insert(root_node, "end", text="B vs Y", values=(3, 0), tags=("3",))
    c = tree.insert(root_node, "end", text="C vs Z", values=(2, 0), tags=("2",))

    tree.insert(a, "end", text="X rating 5", values=(5, 0), tags=("5",))
    tree.insert(a, "end", text="X2 rating 4", values=(4, 0), tags=("4",))
    tree.insert(b, "end", text="Y rating 3", values=(3, 0), tags=("3",))
    tree.insert(b, "end", text="Y2 rating 2", values=(2, 0), tags=("2",))
    tree.insert(c, "end", text="Z rating 2", values=(2, 0), tags=("2",))

    gen.calculate_all_path_values_enhanced("")
    gen.calculate_confidence_scores_enhanced("")
    gen.calculate_counter_resistance_scores_enhanced("")
    gen.calculate_strategic3_scores("")
    return root_node


def test_first_pass_strategic_non_zero():
    root = tk.Tk()
    root.withdraw()
    tree = ttk.Treeview(root, columns=("Rating", "Sort Value"))
    gen = TreeGenerator(treeview=DummyTreeView(tree), strategic_preferences=_base_prefs())

    root_node = _build_sample_tree(gen, tree)
    scores = [gen.get_strategic3_from_tags(node) for node in tree.get_children(root_node)]

    root.destroy()
    assert any(score != 0 for score in scores)


def test_deterministic_ordering_across_runs():
    root = tk.Tk()
    root.withdraw()
    tree = ttk.Treeview(root, columns=("Rating", "Sort Value"))
    gen = TreeGenerator(treeview=DummyTreeView(tree), strategic_preferences=_base_prefs())
    root_node = _build_sample_tree(gen, tree)

    ui = UiManager.__new__(UiManager)
    ui.treeview = DummyTreeView(tree)  # type: ignore[assignment]
    ui.tree_generator = gen
    ui.column_sort_states = {"#0": "none", "Rating": "none", "Sort Value": "none"}
    ui.tie_break_order = "confidence_then_cumulative"

    ui._sort_children_combined(root_node, "strategic3", None)
    order_one = [tree.item(child, "text") for child in tree.get_children(root_node)]

    ui._sort_children_combined(root_node, "strategic3", None)
    order_two = [tree.item(child, "text") for child in tree.get_children(root_node)]

    root.destroy()
    assert order_one == order_two


def test_turn_integrity_depth_ownership():
    root = tk.Tk()
    root.withdraw()
    tree = ttk.Treeview(root, columns=("Rating", "Sort Value"))
    gen = TreeGenerator(treeview=DummyTreeView(tree), strategic_preferences=_base_prefs())

    root_node = tree.insert("", "end", text="Pairings", values=(0, 0), tags=("0",))
    d1 = tree.insert(root_node, "end", text="A vs X", values=(4, 0), tags=("4",))
    d2 = tree.insert(d1, "end", text="X rating 4", values=(4, 0), tags=("4",))
    d3 = tree.insert(d2, "end", text="B vs Y", values=(3, 0), tags=("3",))

    gen.our_team_first = True
    assert gen._is_opponent_choice_level(d1) is False  # depth 1
    assert gen._is_opponent_choice_level(d2) is True   # depth 2
    assert gen._is_opponent_choice_level(d3) is False  # depth 3

    root.destroy()


def test_lock_in_bus_threshold_dynamics():
    root = tk.Tk()
    root.withdraw()

    ui = UiManager.__new__(UiManager)
    ui.strategic_preferences = _base_prefs()
    ui.row_checkboxes = [tk.IntVar(value=0) for _ in range(5)]
    ui.column_checkboxes = [tk.IntVar(value=0) for _ in range(5)]
    ui.scenario_var = tk.StringVar(value="1 - Recon")

    threshold_round1 = ui._get_bus_threshold()
    ui.row_checkboxes[0].set(1)
    threshold_round2 = ui._get_bus_threshold()

    # With default prefs and scenario-dependent policy (no scenario override),
    # threshold = average(global_threshold, depth_threshold).
    # round1 depth=1 => (60 + 65) / 2 = 62
    # round2 depth=2 => (60 + 62) / 2 = 61
    assert isinstance(threshold_round1, int)
    assert isinstance(threshold_round2, int)
    assert threshold_round1 == 62
    assert threshold_round2 == 61
    root.destroy()


def test_confidence_mode_penalizes_regret_spread():
    root = tk.Tk()
    root.withdraw()
    tree = ttk.Treeview(root, columns=("Rating", "Sort Value"))
    gen = TreeGenerator(treeview=DummyTreeView(tree), strategic_preferences=_base_prefs())

    root_node = tree.insert("", "end", text="Pairings", values=(0, 0), tags=("0",))
    stable = tree.insert(root_node, "end", text="Stable vs A", values=(3, 0), tags=("3",))
    volatile = tree.insert(root_node, "end", text="Volatile vs B", values=(3, 0), tags=("3",))

    tree.insert(stable, "end", text="A1", values=(3, 0), tags=("3",))
    tree.insert(stable, "end", text="A2", values=(3, 0), tags=("3",))
    tree.insert(volatile, "end", text="B1", values=(5, 0), tags=("5",))
    tree.insert(volatile, "end", text="B2", values=(1, 0), tags=("1",))

    gen.calculate_confidence_scores_enhanced("")
    stable_conf = gen.get_confidence2_from_tags(stable)
    volatile_conf = gen.get_confidence2_from_tags(volatile)
    stable_regret = gen.get_regret2_from_tags(stable)
    volatile_regret = gen.get_regret2_from_tags(volatile)

    root.destroy()
    assert stable_conf >= volatile_conf
    assert volatile_regret >= stable_regret


def test_memoization_hit_rate_increases_on_repeat_sort():
    root = tk.Tk()
    root.withdraw()
    tree = ttk.Treeview(root, columns=("Rating", "Sort Value"))
    gen = TreeGenerator(treeview=DummyTreeView(tree), strategic_preferences=_base_prefs())

    root_node = _build_sample_tree(gen, tree)
    scores_after_first = [gen.get_strategic3_from_tags(node) for node in tree.get_children(root_node)]
    stats_after_first = gen.get_memoization_stats().copy()
    gen.calculate_strategic3_scores("")
    scores_after_second = [gen.get_strategic3_from_tags(node) for node in tree.get_children(root_node)]
    stats_after_second = gen.get_memoization_stats().copy()

    root.destroy()
    assert scores_after_second == scores_after_first
    assert stats_after_second["hits"] > stats_after_first["hits"]


def test_apply_combined_strategic_reuses_fresh_base_metrics():
    root = tk.Tk()
    root.withdraw()
    tree = ttk.Treeview(root, columns=("Rating", "Sort Value"))
    gen = TreeGenerator(treeview=DummyTreeView(tree), strategic_preferences=_base_prefs())
    _build_sample_tree(gen, tree)

    call_counts = {
        "cumulative": 0,
        "confidence": 0,
        "resistance": 0,
        "strategic": 0,
    }

    orig_cumulative = gen.calculate_all_path_values_enhanced
    orig_confidence = gen.calculate_confidence_scores_enhanced
    orig_resistance = gen.calculate_counter_resistance_scores_enhanced
    orig_strategic = gen.calculate_strategic3_scores

    def wrapped_cumulative(node, *args, **kwargs):
        if node == "":
            call_counts["cumulative"] += 1
        return orig_cumulative(node, *args, **kwargs)

    def wrapped_confidence(node, *args, **kwargs):
        if node == "":
            call_counts["confidence"] += 1
        return orig_confidence(node, *args, **kwargs)

    def wrapped_resistance(node, *args, **kwargs):
        if node == "":
            call_counts["resistance"] += 1
        return orig_resistance(node, *args, **kwargs)

    def wrapped_strategic(node, *args, **kwargs):
        if node == "":
            call_counts["strategic"] += 1
        return orig_strategic(node, *args, **kwargs)

    gen.calculate_all_path_values_enhanced = wrapped_cumulative
    gen.calculate_confidence_scores_enhanced = wrapped_confidence
    gen.calculate_counter_resistance_scores_enhanced = wrapped_resistance
    gen.calculate_strategic3_scores = wrapped_strategic

    ui = UiManager.__new__(UiManager)
    ui.treeview = DummyTreeView(tree)  # type: ignore[assignment]
    ui.tree_generator = gen
    setattr(ui, "perf", DummyPerf())
    ui.column_sort_states = {"#0": "none", "Rating": "none", "Sort Value": "none"}
    ui.active_sort_mode = "strategic3"
    ui.active_column_sort = None
    ui.current_sort_mode = "strategic3"
    ui.tie_break_order = "confidence_then_cumulative"
    ui._primary_metrics_dirty = True
    ui._last_primary_metrics_signature = None
    ui._metric_signatures = {}
    ui._sorted_children_cache = {}
    ui._available_explainability_metrics = set()
    ui._tree_generation_id = 1

    ui.apply_combined_sort(compute_primary_tags=True)
    first_counts = call_counts.copy()

    ui.apply_combined_sort(compute_primary_tags=True)

    root.destroy()
    assert first_counts["cumulative"] == 1
    assert first_counts["confidence"] == 1
    assert first_counts["resistance"] == 1
    assert first_counts["strategic"] == 1
    assert call_counts == first_counts


def test_strategic_preferences_are_loaded_into_generator():
    prefs = _base_prefs()
    prefs["cumulative2"]["alpha"] = 0.67
    prefs["confidence2"]["k"] = 1.25
    prefs["confidence2"]["u"] = 9.0
    prefs["resistance2"]["beta"] = 1.7
    prefs["resistance2"]["gamma"] = 2.8
    prefs["strategic3"]["weights"] = [0.5, 0.3, 0.2]
    prefs["strategic3"]["rho"] = 0.33
    prefs["strategic3"]["lam"] = 0.44

    root = tk.Tk()
    root.withdraw()
    tree = ttk.Treeview(root, columns=("Rating", "Sort Value"))
    gen = TreeGenerator(treeview=DummyTreeView(tree), strategic_preferences=prefs)

    cumulative2_alpha = cast(float, gen.cumulative2_alpha)
    confidence2_k = cast(float, gen.confidence2_k)
    confidence2_u = cast(float, gen.confidence2_u)
    resistance2_beta = cast(float, gen.resistance2_beta)
    resistance2_gamma = cast(float, gen.resistance2_gamma)

    assert abs(cumulative2_alpha - 0.67) < 1e-9
    assert abs(confidence2_k - 1.25) < 1e-9
    assert abs(confidence2_u - 9.0) < 1e-9
    assert abs(resistance2_beta - 1.7) < 1e-9
    assert abs(resistance2_gamma - 2.8) < 1e-9
    expected_weights = (0.5, 0.3, 0.2)
    assert all(abs(actual - expected) < 1e-9 for actual, expected in zip(gen.strategic3_weights, expected_weights))
    strategic3_rho = cast(float, gen.strategic3_rho)
    strategic3_lam = cast(float, gen.strategic3_lam)
    assert abs(strategic3_rho - 0.33) < 1e-9
    assert abs(strategic3_lam - 0.44) < 1e-9

    root.destroy()


def test_guardrail_strength_changes_strategic_score():
    root = tk.Tk()
    root.withdraw()

    low_prefs = _base_prefs()
    low_prefs["strategic3"]["round_win_guardrail_strength"] = "low"
    tree_low = ttk.Treeview(root, columns=("Rating", "Sort Value"))
    gen_low = TreeGenerator(treeview=DummyTreeView(tree_low), strategic_preferences=low_prefs)
    root_low = _build_sample_tree(gen_low, tree_low)
    low_nodes = tree_low.get_children(root_low)
    low_score = gen_low.get_strategic3_from_tags(low_nodes[0])

    high_prefs = _base_prefs()
    high_prefs["strategic3"]["round_win_guardrail_strength"] = "high"
    tree_high = ttk.Treeview(root, columns=("Rating", "Sort Value"))
    gen_high = TreeGenerator(treeview=DummyTreeView(tree_high), strategic_preferences=high_prefs)
    root_high = _build_sample_tree(gen_high, tree_high)
    high_nodes = tree_high.get_children(root_high)
    high_score = gen_high.get_strategic3_from_tags(high_nodes[0])

    root.destroy()
    assert low_score != high_score


def test_chooser_direction_unchecked_friendly_depth2_descending_strategic():
    root = tk.Tk()
    root.withdraw()
    tree = ttk.Treeview(root, columns=("Rating", "Sort Value"))
    gen = TreeGenerator(treeview=DummyTreeView(tree), strategic_preferences=_base_prefs())
    gen.our_team_first = True

    root_node = tree.insert("", "end", text="Pairings", values=(0, 0), tags=("0",))
    depth1 = tree.insert(root_node, "end", text="Friendly choice", values=(0, 0), tags=("0",))
    better = tree.insert(depth1, "end", text="Friendly A", values=(0, 0), tags=("strategic3_-108",))
    worse = tree.insert(depth1, "end", text="Friendly B", values=(0, 0), tags=("strategic3_-200",))

    ui = UiManager.__new__(UiManager)
    ui.treeview = DummyTreeView(tree)  # type: ignore[assignment]
    ui.tree_generator = gen
    ui.column_sort_states = {"#0": "none", "Rating": "none", "Sort Value": "none"}
    ui.tie_break_order = "confidence_then_cumulative"

    ui._sort_children_combined(depth1, "strategic3", None)
    ordered = list(tree.get_children(depth1))

    root.destroy()
    assert ordered[0] == better
    assert ordered[1] == worse


def test_chooser_direction_depth_owner_flip_between_team_first_states():
    root = tk.Tk()
    root.withdraw()
    tree = ttk.Treeview(root, columns=("Rating", "Sort Value"))
    gen = TreeGenerator(treeview=DummyTreeView(tree), strategic_preferences=_base_prefs())

    root_node = tree.insert("", "end", text="Pairings", values=(0, 0), tags=("0",))
    high = tree.insert(root_node, "end", text="High", values=(0, 0), tags=("strategic3_-108",))
    low = tree.insert(root_node, "end", text="Low", values=(0, 0), tags=("strategic3_-200",))

    ui = UiManager.__new__(UiManager)
    ui.treeview = DummyTreeView(tree)  # type: ignore[assignment]
    ui.tree_generator = gen
    ui.column_sort_states = {"#0": "none", "Rating": "none", "Sort Value": "none"}
    ui.tie_break_order = "confidence_then_cumulative"

    # Team-first checked: root children (depth 1) are our choice, so higher strategic first.
    gen.our_team_first = True
    ui._sort_children_combined("", "strategic3", None)
    order_checked = list(tree.get_children(root_node))

    # Team-first unchecked: root children (depth 1) are opponent choice, so lower strategic first.
    gen.our_team_first = False
    ui._sort_children_combined("", "strategic3", None)
    order_unchecked = list(tree.get_children(root_node))

    root.destroy()
    assert order_checked[0] == high
    assert order_checked[1] == low
    assert order_unchecked[0] == low
    assert order_unchecked[1] == high


def test_enemy_choice_node_orders_worst_for_us_first():
    root = tk.Tk()
    root.withdraw()
    tree = ttk.Treeview(root, columns=("Rating", "Sort Value"))
    gen = TreeGenerator(treeview=DummyTreeView(tree), strategic_preferences=_base_prefs())
    gen.our_team_first = False

    # Depth-1 node is enemy-owned when My Team First is unchecked.
    root_node = tree.insert("", "end", text="Pairings", values=(0, 0), tags=("0",))
    enemy_node = tree.insert(root_node, "end", text="FLO vs Dan OR Pete", values=(4, 0), tags=("strategic3_-139",))
    better_for_us = tree.insert(enemy_node, "end", text="Dan rating 4", values=(4, 0), tags=("strategic3_-141",))
    worse_for_us = tree.insert(enemy_node, "end", text="Pete rating 2", values=(2, 0), tags=("strategic3_-146",))

    ui = UiManager.__new__(UiManager)
    ui.treeview = DummyTreeView(tree)  # type: ignore[assignment]
    ui.tree_generator = gen
    ui.column_sort_states = {"#0": "none", "Rating": "none", "Sort Value": "none"}
    ui.tie_break_order = "confidence_then_cumulative"

    ui._sort_children_combined(enemy_node, "strategic3", None)
    ordered = list(tree.get_children(enemy_node))

    root.destroy()
    assert ordered[0] == worse_for_us
    assert ordered[1] == better_for_us


def test_strategic_tag_reader_ignores_exploit_prefix_collision():
    root = tk.Tk()
    root.withdraw()
    tree = ttk.Treeview(root, columns=("Rating", "Sort Value"))
    gen = TreeGenerator(treeview=DummyTreeView(tree), strategic_preferences=_base_prefs())

    root_node = tree.insert("", "end", text="Pairings", values=(0, 0), tags=("0",))
    node = tree.insert(
        root_node,
        "end",
        text="Sample",
        values=(0, 0),
        tags=("strategic3_exploit_12", "strategic3_-108"),
    )

    strategic_value = gen.get_strategic3_from_tags(node)

    root.destroy()
    assert strategic_value == -108