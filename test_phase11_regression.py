#!/usr/bin/env python3
"""Phase 11 regression coverage for strategic sorting behavior."""

import tkinter as tk
from tkinter import ttk
from contextlib import nullcontext
from typing import cast, Any

from qtr_pairing_process.perf_timer import PerfTimer
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


class DummyUIPrefs:
    def get_matchup_output_format(self):
        return "standard"


class DummyStrategicPrefsStore:
    def __init__(self):
        self.calls = []

    def set_strategic_preferences(self, prefs):
        self.calls.append(prefs)
        return True


class DummyIntVar:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value


class DummyTokenTreeGenerator:
    def __init__(self):
        self.tokens = []

    def set_memo_state_token(self, token):
        self.tokens.append(token)


class DummyWidget:
    def __init__(self, exists=True):
        self._exists = exists
        self.destroy_called = False

    def winfo_exists(self):
        return self._exists

    def destroy(self):
        self.destroy_called = True
        self._exists = False


class DummyMemoStatsTreeGenerator:
    persistent_memo_enabled = False

    def set_memo_state_token(self, _token):
        return None

    def get_memoization_stats(self):
        return {
            "hits": 7,
            "misses": 3,
            "hit_rate": 0.7,
            "entries": 4,
            "clear_count": 1,
            "last_clear_reason": "memo_state_change",
            "last_clear_bucket": "state_change",
            "last_cleared_entries": 2,
            "memo_context_hash": "abc123def456",
            "memo_key_mode": "structural_path_text_base_rating",
            "memo_clear_reason": "memo_state_change",
            "memo_clear_bucket": "state_change",
            "memo_cleared_entries": 2,
        }


def _persistent_prefs():
    prefs = _base_prefs()
    prefs["strategic3"]["persistent_memo_enabled"] = True
    prefs["strategic3"]["persistent_memo_max_entries"] = 50000
    return prefs


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


def test_memoization_stats_include_diagnostics_fields():
    gen = TreeGenerator(treeview=DummyTreeView(object()), strategic_preferences=_base_prefs())
    stats = gen.get_memoization_stats()

    assert "memo_context_hash" in stats
    assert "memo_key_mode" in stats
    assert "memo_clear_reason" in stats
    assert "memo_clear_bucket" in stats
    assert "memo_cleared_entries" in stats
    assert isinstance(stats["memo_context_hash"], str)
    assert len(stats["memo_context_hash"]) == 12
    assert stats["memo_key_mode"] == "structural_path_text_base_rating"
    assert stats["memo_clear_bucket"] in {
        "",
        "state_change",
        "param_change",
        "tree_cache_reset",
        "manual_clear",
        "context_mismatch",
    }


def test_matchup_output_panel_does_not_render_explainability_summary_label():
    root = tk.Tk()
    root.withdraw()

    ui = UiManager.__new__(UiManager)
    setattr(ui, "db_preferences", cast(Any, DummyUIPrefs()))
    parent = tk.Frame(root)
    parent.pack()

    ui.create_matchup_output_panel(parent=parent)

    all_labels = [
        child
        for child in ui.output_panel_frame.winfo_children()
        if isinstance(child, tk.Label)
    ]
    nested_labels = []
    for child in ui.output_panel_frame.winfo_children():
        nested_labels.extend(
            [grandchild for grandchild in child.winfo_children() if isinstance(grandchild, tk.Label)]
        )
    label_texts = [label.cget("text") for label in all_labels + nested_labels]

    root.destroy()
    assert not any("Explainability:" in text for text in label_texts)


def test_ensure_matchup_output_panel_rebuilds_missing_widgets():
    ui = UiManager.__new__(UiManager)
    setattr(ui, "perf", cast(Any, DummyPerf()))
    ui.matchup_output_panel_created = False

    stale_frame = DummyWidget(exists=True)
    ui.output_panel_frame = stale_frame

    def _create_panel():
        ui.output_panel_frame = DummyWidget(exists=True)
        ui.matchups_text = DummyWidget(exists=True)
        ui.summary_matchups_label = DummyWidget(exists=True)
        ui.summary_spread_label = DummyWidget(exists=True)
        ui.summary_histogram = DummyWidget(exists=True)

    ui.create_matchup_output_panel = _create_panel  # type: ignore[method-assign]

    assert ui._ensure_matchup_output_panel() is True
    assert ui.matchup_output_panel_created is True
    assert stale_frame.destroy_called is True


def test_ensure_matchup_output_panel_keeps_valid_widgets():
    ui = UiManager.__new__(UiManager)
    setattr(ui, "perf", cast(Any, DummyPerf()))
    ui.matchup_output_panel_created = False
    ui.output_panel_frame = DummyWidget(exists=True)
    ui.matchups_text = DummyWidget(exists=True)
    ui.summary_matchups_label = DummyWidget(exists=True)
    ui.summary_spread_label = DummyWidget(exists=True)
    ui.summary_histogram = DummyWidget(exists=True)

    def _should_not_recreate():
        raise AssertionError("panel should not be recreated when required widgets are present")

    ui.create_matchup_output_panel = _should_not_recreate  # type: ignore[method-assign]

    assert ui._ensure_matchup_output_panel() is True
    assert ui.matchup_output_panel_created is True


def test_should_invalidate_strategic_memo_reason_policy():
    ui = UiManager.__new__(UiManager)

    assert ui._should_invalidate_strategic_memo("clear_active_generated_tree_cache") is False
    assert ui._should_invalidate_strategic_memo("clear_all_generated_tree_cache") is False
    assert ui._should_invalidate_strategic_memo("generated_tree_snapshot_pruned") is False
    assert ui._should_invalidate_strategic_memo("rating_change") is True
    assert ui._should_invalidate_strategic_memo("scenario_change") is True


def test_set_tree_memo_state_token_tracks_token_churn():
    ui = UiManager.__new__(UiManager)
    setattr(ui, "tree_generator", cast(Any, DummyTokenTreeGenerator()))
    ui._tree_generation_id = 1
    setattr(ui, "perf", cast(Any, DummyPerf()))

    cache_key = ("TeamA", "TeamB", 1, "1-5", True, "sig")
    ui._set_tree_memo_state_token(cache_key)
    ui._set_tree_memo_state_token(cache_key)
    ui._set_tree_memo_state_token(("TeamA", "TeamB", 2, "1-5", True, "sig"))

    token_gen = cast(DummyTokenTreeGenerator, getattr(ui, "tree_generator"))
    assert len(token_gen.tokens) == 3
    assert ui._tree_memo_token_set_count == 3
    assert ui._tree_memo_token_change_count == 2


def test_memoization_reuses_entries_after_tree_rebuild_same_state():
    root = tk.Tk()
    root.withdraw()
    tree = ttk.Treeview(root, columns=("Rating", "Sort Value"))
    gen = TreeGenerator(treeview=DummyTreeView(tree), strategic_preferences=_base_prefs())

    gen.set_memo_state_token("stable-state")
    _build_sample_tree(gen, tree)
    stats_after_first = gen.get_memoization_stats().copy()

    tree.delete(*tree.get_children())
    _build_sample_tree(gen, tree)
    stats_after_rebuild = gen.get_memoization_stats().copy()

    root.destroy()
    assert stats_after_rebuild["hits"] > stats_after_first["hits"]


def test_memo_state_change_clears_with_expected_reason_bucket():
    gen = TreeGenerator(treeview=DummyTreeView(object()), strategic_preferences=_base_prefs())

    # Seed one memo entry so clear telemetry can assert cleared entry count.
    gen._strategic_memo = {"seed": 1}

    gen.set_memo_state_token("state-A")
    stats_after_first_set = gen.get_memoization_stats().copy()

    # Same token should not clear again.
    gen.set_memo_state_token("state-A")
    stats_after_same_token = gen.get_memoization_stats().copy()

    # Different token is score-relevant and must clear with state_change bucket.
    gen._strategic_memo = {"seed": 2}
    gen.set_memo_state_token("state-B")
    stats_after_change = gen.get_memoization_stats().copy()

    assert stats_after_same_token["clear_count"] == stats_after_first_set["clear_count"]
    assert stats_after_change["clear_count"] == stats_after_first_set["clear_count"] + 1
    assert stats_after_change["memo_clear_reason"] == "memo_state_change"
    assert stats_after_change["memo_clear_bucket"] == "state_change"
    assert stats_after_change["memo_cleared_entries"] == 1


def test_sort_by_strategic_emits_new_telemetry_fields(tmp_path):
    ui = UiManager.__new__(UiManager)
    setattr(ui, "tree_generator", cast(Any, DummyMemoStatsTreeGenerator()))
    setattr(ui, "perf", cast(Any, PerfTimer(enabled=True, log_path=tmp_path / "perf_test.log")))
    ui._tree_generation_id = 1
    ui._available_explainability_metrics = {
        "cumulative",
        "confidence",
        "resistance",
        "regret",
        "downside",
        "guardrail",
        "strategic",
        "exploit",
    }

    ui.apply_combined_sort = lambda compute_primary_tags=True: None
    ui.update_sort_value_column = lambda: None
    ui.update_column_headers = lambda: None
    ui.update_sort_button_states = lambda: None
    ui._update_sort_hint = lambda: None

    ui.sort_by_strategic()
    ui.perf.close()

    log_text = (tmp_path / "perf_test.log").read_text(encoding="utf-8")
    assert "strategic.sort.end_to_end" in log_text
    assert "strategic_invocation_id=1" in log_text
    assert "strategic.memo.stats" in log_text
    assert "strategic.explainability.metrics" in log_text
    assert "memo_context_hash=abc123def456" in log_text
    assert "memo_key_mode=structural_path_text_base_rating" in log_text
    assert "memo_clear_reason=memo_state_change" in log_text
    assert "memo_clear_bucket=state_change" in log_text
    assert "memo_cleared_entries=2" in log_text
    assert "has_c2=1" in log_text
    assert "has_q2=1" in log_text
    assert "has_r2=1" in log_text


def test_sort_by_strategic_recovers_from_all_zero_tags():
    root = tk.Tk()
    root.withdraw()
    tree = ttk.Treeview(root, columns=("Rating", "Sort Value"))

    root_node = tree.insert("", "end", text="Pairings", values=(0, 0), tags=("0",))
    child = tree.insert(root_node, "end", text="A vs X", values=(4, 0), tags=("4", "strategic3_0"))

    gen = TreeGenerator(treeview=DummyTreeView(tree), strategic_preferences=_base_prefs())

    def recalc_override(node, *args, **kwargs):
        if node == "":
            gen._replace_prefixed_tag(child, "strategic3_", 7)
            return 7
        return 0

    gen.calculate_strategic3_scores = recalc_override

    ui = UiManager.__new__(UiManager)
    ui.treeview = DummyTreeView(tree)  # type: ignore[assignment]
    ui.tree_generator = gen
    ui.perf = DummyPerf()
    ui._metric_signatures = {}
    ui._primary_metrics_dirty = True
    ui._last_primary_metrics_signature = None
    ui._available_explainability_metrics = set()
    ui._strategic_sort_invocation_id = 0
    ui.column_sort_states = {"#0": "none", "Rating": "none", "Sort Value": "none"}
    ui.active_column_sort = None
    ui.active_sort_mode = None
    ui.current_sort_mode = "none"
    ui.apply_combined_sort = lambda compute_primary_tags=True: None
    ui.update_column_headers = lambda: None
    ui.update_sort_button_states = lambda: None
    ui._update_sort_hint = lambda: None
    ui._build_tree_cache_key = lambda: None
    ui._set_tree_memo_state_token = lambda *_args, **_kwargs: None
    ui._is_persistent_strategic_memo_enabled = lambda: False

    ui.sort_by_strategic()

    displayed = tree.item(child, "values")[1]
    assert gen.get_strategic3_from_tags(child) == 7
    assert str(displayed) == "7"
    root.destroy()


def test_persistent_memo_snapshot_roundtrip_with_strict_signature():
    gen = TreeGenerator(treeview=DummyTreeView(object()), strategic_preferences=_persistent_prefs())
    gen.set_memo_state_token("stable-token")
    gen._strategic_memo_context = gen._build_strategic_memo_context()
    gen._strategic_memo = {
        (("Pairings", 0), ("A vs X", 5)): 17,
        (("Pairings", 0), ("B vs Y", 3)): 11,
    }

    payload = gen.export_memoization_snapshot()
    assert payload is not None
    assert payload.get("entries")

    gen2 = TreeGenerator(treeview=DummyTreeView(object()), strategic_preferences=_persistent_prefs())
    gen2.set_memo_state_token("stable-token")

    imported = gen2.import_memoization_snapshot(payload)
    assert imported is True
    assert len(gen2._strategic_memo) > 0


def test_persistent_memo_snapshot_rejects_state_or_param_mismatch():
    gen = TreeGenerator(treeview=DummyTreeView(object()), strategic_preferences=_persistent_prefs())
    gen.set_memo_state_token("state-A")
    gen._strategic_memo_context = gen._build_strategic_memo_context()
    gen._strategic_memo = {(("Pairings", 0), ("A vs X", 5)): 9}
    payload = gen.export_memoization_snapshot()
    assert payload is not None

    # State mismatch should reject import.
    gen_state_mismatch = TreeGenerator(
        treeview=DummyTreeView(object()),
        strategic_preferences=_persistent_prefs(),
    )
    gen_state_mismatch.set_memo_state_token("state-B")
    assert gen_state_mismatch.import_memoization_snapshot(payload) is False

    # Parameter mismatch should reject import.
    param_mismatch_prefs = _persistent_prefs()
    param_mismatch_prefs["strategic3"]["lam"] = 0.99
    gen_param_mismatch = TreeGenerator(
        treeview=DummyTreeView(object()),
        strategic_preferences=param_mismatch_prefs,
    )
    gen_param_mismatch.set_memo_state_token("state-A")
    assert gen_param_mismatch.import_memoization_snapshot(payload) is False


def test_strategic_memo_hit_materializes_strategic_tags():
    root = tk.Tk()
    root.withdraw()

    tree = ttk.Treeview(root, columns=("Rating", "Sort Value"))
    gen = TreeGenerator(treeview=DummyTreeView(tree), strategic_preferences=_persistent_prefs())

    root_node = tree.insert("", "end", text="Pairings", values=(0, 0), tags=("0",))
    child = tree.insert(root_node, "end", text="A vs X", values=(5, 0), tags=("5",))

    memo_key = gen._build_structural_memo_key(child)
    gen._strategic_memo[memo_key] = 42

    assert gen.get_strategic3_from_tags(child) == 0
    stats_before = gen.get_memoization_stats().copy()

    score = gen.calculate_strategic3_scores(child)

    stats_after = gen.get_memoization_stats().copy()
    assert score == 42
    assert stats_after["hits"] > stats_before["hits"]
    assert gen.get_strategic3_from_tags(child) == 42
    assert any(str(tag).startswith("strategic3_") for tag in tree.item(child, "tags"))
    root.destroy()


def test_parent_memo_hit_materializes_descendant_strategic_tags():
    root = tk.Tk()
    root.withdraw()

    tree = ttk.Treeview(root, columns=("Rating", "Sort Value"))
    gen = TreeGenerator(treeview=DummyTreeView(tree), strategic_preferences=_persistent_prefs())

    root_node = tree.insert("", "end", text="Pairings", values=(0, 0), tags=("0",))
    parent = tree.insert(root_node, "end", text="A vs X", values=(4, 0), tags=("4",))
    child = tree.insert(parent, "end", text="X rating 4", values=(4, 0), tags=("4",))

    parent_key = gen._build_structural_memo_key(parent)
    child_key = gen._build_structural_memo_key(child)
    gen._strategic_memo[parent_key] = 55
    gen._strategic_memo[child_key] = 31

    assert gen.get_strategic3_from_tags(parent) == 0
    assert gen.get_strategic3_from_tags(child) == 0

    gen.calculate_strategic3_scores(parent)

    assert gen.get_strategic3_from_tags(parent) == 55
    assert gen.get_strategic3_from_tags(child) == 31
    root.destroy()


def test_strategic_score_distribution_counts_nodes():
    root = tk.Tk()
    root.withdraw()

    tree = ttk.Treeview(root, columns=("Rating", "Sort Value"))
    gen = TreeGenerator(treeview=DummyTreeView(tree), strategic_preferences=_base_prefs())

    pairings = tree.insert("", "end", text="Pairings", values=(0, 0), tags=("0", "strategic3_0"))
    a = tree.insert(pairings, "end", text="A vs X", values=(4, 0), tags=("4", "strategic3_7"))
    tree.insert(a, "end", text="X rating 4", values=(4, 0), tags=("4", "strategic3_0"))

    ui = UiManager.__new__(UiManager)
    ui.treeview = DummyTreeView(tree)  # type: ignore[assignment]
    ui.tree_generator = gen

    dist = ui._get_strategic_score_distribution()

    assert dist == {"total": 3, "non_zero": 1, "zero": 2}
    root.destroy()


def test_persistent_memo_toggle_updates_runtime_and_prefs():
    ui = UiManager.__new__(UiManager)
    prefs_store = DummyStrategicPrefsStore()
    setattr(ui, "db_preferences", cast(Any, prefs_store))
    setattr(ui, "persistent_memo_var", cast(Any, DummyIntVar(0)))
    setattr(ui, "tree_generator", cast(Any, DummyMemoStatsTreeGenerator()))
    setattr(ui, "strategic_preferences", _persistent_prefs())

    ui._on_persistent_memo_toggle()

    assert ui.tree_generator.persistent_memo_enabled is False
    assert ui.strategic_preferences["strategic3"]["persistent_memo_enabled"] is False
    assert prefs_store.calls[-1] == {
        "strategic3": {
            "persistent_memo_enabled": False,
        }
    }


def test_strategic_mode_exposes_component_explainability_metrics():
    ui = UiManager.__new__(UiManager)
    ui._available_explainability_metrics = set()

    ui._mark_explainability_metrics_available("strategic3")

    assert "cumulative" in ui._available_explainability_metrics
    assert "confidence" in ui._available_explainability_metrics
    assert "resistance" in ui._available_explainability_metrics
    assert "regret" in ui._available_explainability_metrics
    assert "downside" in ui._available_explainability_metrics
    assert "guardrail" in ui._available_explainability_metrics
    assert "strategic" in ui._available_explainability_metrics
    assert "exploit" in ui._available_explainability_metrics


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