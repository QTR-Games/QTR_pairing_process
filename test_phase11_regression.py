#!/usr/bin/env python3
"""Phase 11 regression coverage for strategic sorting behavior."""

import tkinter as tk
from tkinter import ttk

from qtr_pairing_process.tree_generator import TreeGenerator
from qtr_pairing_process.ui_manager_v2 import UiManager


class DummyTreeView:
    def __init__(self, tree):
        self.tree = tree


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
    ui.treeview = DummyTreeView(tree)
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

    assert isinstance(threshold_round1, int)
    assert isinstance(threshold_round2, int)
    assert threshold_round1 != threshold_round2
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

    _build_sample_tree(gen, tree)
    stats_after_first = gen.get_memoization_stats().copy()
    gen.calculate_strategic3_scores("")
    stats_after_second = gen.get_memoization_stats().copy()

    root.destroy()
    assert stats_after_second["hits"] > stats_after_first["hits"]