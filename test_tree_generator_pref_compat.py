#!/usr/bin/env python3
"""Compatibility parity tests for TreeGenerator preference reader helpers."""

from qtr_pairing_process.tree_generator import TreeGenerator


class _DummyTreeView:
    class _Tree:
        def delete(self, *args, **kwargs):
            return None

    def __init__(self):
        self.tree = self._Tree()


def _make_tree_generator(prefs):
    return TreeGenerator(_DummyTreeView(), strategic_preferences=prefs)


def test_read_pref_raw_mode_matches_read_raw_pref():
    prefs = {
        "strategic3": {"round_win_guardrail_strength": "high"},
        "cumulative2": {"alpha": 0.73},
    }
    generator = _make_tree_generator(prefs)

    raw = generator._read_raw_pref(("strategic3", "round_win_guardrail_strength"), "medium")
    compat = generator._read_pref(("strategic3", "round_win_guardrail_strength"), "medium")

    assert compat == raw


def test_read_pref_numeric_mode_matches_read_numeric_pref_for_valid_numeric_string():
    prefs = {"confidence2": {"u": "18.5"}}
    generator = _make_tree_generator(prefs)

    numeric = generator._read_numeric_pref(("confidence2", "u"), 12.0, 0.0, 100.0)
    compat = generator._read_pref(("confidence2", "u"), 12.0, 0.0, 100.0)

    assert compat == numeric


def test_read_pref_numeric_mode_matches_read_numeric_pref_for_invalid_value():
    prefs = {"confidence2": {"u": "not-a-number"}}
    generator = _make_tree_generator(prefs)

    numeric = generator._read_numeric_pref(("confidence2", "u"), 12.0, 0.0, 100.0)
    compat = generator._read_pref(("confidence2", "u"), 12.0, 0.0, 100.0)

    assert compat == numeric == 12.0


def test_read_pref_numeric_mode_matches_read_numeric_pref_for_clamping():
    prefs = {"resistance2": {"gamma": 77}}
    generator = _make_tree_generator(prefs)

    numeric = generator._read_numeric_pref(("resistance2", "gamma"), 2.0, 0.0, 10.0)
    compat = generator._read_pref(("resistance2", "gamma"), 2.0, 0.0, 10.0)

    assert compat == numeric == 10.0


def test_read_pref_raw_mode_matches_read_raw_pref_for_missing_nested_path():
    prefs = {"strategic3": {}}
    generator = _make_tree_generator(prefs)

    raw = generator._read_raw_pref(("strategic3", "tie_break_order"), "confidence_then_cumulative")
    compat = generator._read_pref(("strategic3", "tie_break_order"), "confidence_then_cumulative")

    assert compat == raw == "confidence_then_cumulative"
