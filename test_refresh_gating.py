#!/usr/bin/env python3
"""Regression tests for grouped non-critical refresh gating."""

from typing import Any, cast

from qtr_pairing_process.ui_manager_v2 import UiManager


def test_post_load_refresh_skips_when_signature_unchanged():
    ui = UiManager.__new__(UiManager)
    u = cast(Any, ui)

    calls = {"comment": 0, "calc": 0, "set_dirty": 0, "skip": 0}
    u._grid_dirty = False
    u._last_post_load_refresh_signature = ("sig",)
    u._build_post_load_refresh_signature = lambda: ("sig",)
    u.update_comment_indicators = lambda: calls.__setitem__("comment", calls["comment"] + 1)
    u._schedule_scenario_calculations = lambda immediate=False: calls.__setitem__("calc", calls["calc"] + 1)
    u._set_grid_dirty = lambda is_dirty: calls.__setitem__("set_dirty", calls["set_dirty"] + 1)

    def _skip_noop(*_args, **_kwargs):
        calls["skip"] += 1
        return True

    u._skip_noop = _skip_noop

    ui._post_grid_load_refresh()

    assert calls["skip"] == 1
    assert calls["comment"] == 0
    assert calls["calc"] == 0
    assert calls["set_dirty"] == 0


def test_post_load_refresh_runs_when_signature_changes():
    ui = UiManager.__new__(UiManager)
    u = cast(Any, ui)

    calls = {"comment": 0, "calc": 0, "set_dirty": 0}
    u._grid_dirty = False
    u._last_post_load_refresh_signature = ("old",)
    u._build_post_load_refresh_signature = lambda: ("new",)
    u.update_comment_indicators = lambda: calls.__setitem__("comment", calls["comment"] + 1)
    u._schedule_scenario_calculations = lambda immediate=False: calls.__setitem__("calc", calls["calc"] + 1)
    u._set_grid_dirty = lambda is_dirty: calls.__setitem__("set_dirty", calls["set_dirty"] + 1)
    u._skip_noop = lambda *_args, **_kwargs: True

    ui._post_grid_load_refresh()

    assert calls["comment"] == 1
    assert calls["calc"] == 1
    assert calls["set_dirty"] == 1
    assert u._last_post_load_refresh_signature == ("new",)


def test_update_status_bar_skips_when_signature_unchanged():
    ui = UiManager.__new__(UiManager)
    u = cast(Any, ui)

    calls = {"rebuild": 0, "refresh": 0, "skip": 0}
    u.db_name = "DB"
    u.rating_config = {"name": "1-5"}
    u.rating_range = (1, 5)
    u.color_map = {1: "#111", 2: "#222"}
    u._last_status_bar_signature = (
        "DB",
        "1-5",
        (1, 5),
        tuple(sorted({1: "#111", 2: "#222"}.items())),
    )

    u._rebuild_color_preview = lambda: calls.__setitem__("rebuild", calls["rebuild"] + 1)
    u._refresh_status_messages = lambda: calls.__setitem__("refresh", calls["refresh"] + 1)

    def _skip_noop(*_args, **_kwargs):
        calls["skip"] += 1
        return True

    u._skip_noop = _skip_noop

    ui.update_status_bar()

    assert calls["skip"] == 1
    assert calls["rebuild"] == 0
    assert calls["refresh"] == 0
