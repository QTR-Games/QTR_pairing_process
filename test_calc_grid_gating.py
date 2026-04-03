#!/usr/bin/env python3
"""Regression tests for calc-grid row apply dedupe gating."""

from typing import Any, cast

from qtr_pairing_process.ui_manager_v2 import UiManager


def _rows_template(floor_prefix: str = "F"):
    return {
        "floor": {row: f"{floor_prefix}{row}" for row in range(1, 6)},
        "pinned": {row: f"P{row}" for row in range(1, 6)},
        "can_pin": {row: f"C{row}" for row in range(1, 6)},
        "protect": {row: f"R{row}" for row in range(1, 6)},
        "bus": {row: f"B{row}" for row in range(1, 6)},
    }


def test_apply_calc_grid_rows_skips_when_rows_unchanged():
    ui = UiManager.__new__(UiManager)
    u = cast(Any, ui)

    calls = {"display": 0, "skip": 0}
    rows = _rows_template("A")

    expected_signature = (
        tuple(rows["floor"].get(row, "---") for row in range(1, 6)),
        tuple(rows["pinned"].get(row, "---") for row in range(1, 6)),
        tuple(rows["can_pin"].get(row, "---") for row in range(1, 6)),
        tuple(rows["protect"].get(row, "---") for row in range(1, 6)),
        tuple(rows["bus"].get(row, "---") for row in range(1, 6)),
    )

    u._last_calc_grid_rows_signature = expected_signature
    u.update_display_fields = lambda *_args, **_kwargs: calls.__setitem__("display", calls["display"] + 1)

    def _skip_noop(*_args, **_kwargs):
        calls["skip"] += 1
        return True

    u._skip_noop = _skip_noop

    ui._apply_calc_grid_rows(rows)

    assert calls["skip"] == 1
    assert calls["display"] == 0


def test_apply_calc_grid_rows_applies_and_updates_signature_when_changed():
    ui = UiManager.__new__(UiManager)
    u = cast(Any, ui)

    calls = {"display": 0}
    rows = _rows_template("Z")

    u._last_calc_grid_rows_signature = None
    u.update_display_fields = lambda *_args, **_kwargs: calls.__setitem__("display", calls["display"] + 1)
    u._skip_noop = lambda *_args, **_kwargs: True

    ui._apply_calc_grid_rows(rows)

    assert calls["display"] == 25
    assert u._last_calc_grid_rows_signature is not None


def test_set_grid_dirty_true_clears_calc_grid_signature():
    ui = UiManager.__new__(UiManager)
    u = cast(Any, ui)

    u._grid_dirty = False
    u._last_post_load_refresh_signature = ("post",)
    u._last_calc_grid_rows_signature = ("calc",)
    u._refresh_status_messages = lambda: None

    ui._set_grid_dirty(True)

    assert u._last_post_load_refresh_signature is None
    assert u._last_calc_grid_rows_signature is None


def test_format_calc_explain_text_bus_contains_key_context():
    ui = UiManager.__new__(UiManager)
    u = cast(Any, ui)

    u._build_bus_analysis_for_display = lambda _row: {
        "bus_score": 72,
        "threshold": 60,
        "degree": "LIGHT",
        "abort": False,
        "spread": 9,
        "downside_risk": 4,
        "outlier_bonus": 8,
        "leverage_bonus": 2,
        "abort_reasons": [],
    }

    text = ui._format_calc_explain_text(2, 4, "YES (72) [LIGHT|GO]")

    assert "BUS RIDE" in text
    assert "Score vs threshold" in text
    assert "Degree:" in text
    assert "Bonuses:" in text


def test_format_calc_explain_text_pinned_is_concise_and_rule_based():
    ui = UiManager.__new__(UiManager)

    text = ui._format_calc_explain_text(3, 1, "PINNED!")

    assert "PINNED?" in text
    assert "Rule:" in text
    assert "bad matchups" in text
