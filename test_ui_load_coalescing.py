#!/usr/bin/env python3
"""Regression tests for UI grid-load coalescing guards."""

import time
from typing import Any

from qtr_pairing_process.ui_manager_v2 import UiManager


def _build_minimal_ui_manager() -> tuple[UiManager, list[tuple[str, float, dict[str, Any]]]]:
    ui = UiManager.__new__(UiManager)
    ui._last_grid_load_request_key = None
    ui._last_grid_load_request_at = 0.0
    ui._grid_load_duplicate_window_s = 0.2
    ui._grid_load_in_flight = False
    ui._grid_dirty = False
    perf_events = []

    def _log_perf_entry(label, elapsed_ms, **kwargs):
        perf_events.append((label, elapsed_ms, kwargs))

    ui._log_perf_entry = _log_perf_entry  # type: ignore[method-assign]
    return ui, perf_events


def test_grid_load_request_skips_duplicate_when_in_flight():
    ui, perf_events = _build_minimal_ui_manager()
    key = ("Team A", "Team B", 1, True)

    assert ui._should_process_grid_load_request(key) is True
    ui._grid_load_in_flight = True

    assert ui._should_process_grid_load_request(key) is False
    assert any(evt[0] == "grid.load.skipped_duplicate" for evt in perf_events)


def test_grid_load_request_skips_duplicate_in_burst_window():
    ui, perf_events = _build_minimal_ui_manager()
    key = ("Team A", "Team B", 1, True)

    assert ui._should_process_grid_load_request(key) is True
    ui._grid_load_in_flight = False
    ui._last_grid_load_request_at = time.perf_counter()

    assert ui._should_process_grid_load_request(key) is False
    assert any(evt[2].get("reason") == "burst_window" for evt in perf_events)


def test_grid_load_request_force_reload_bypasses_coalescing():
    ui, _perf_events = _build_minimal_ui_manager()
    key = ("Team A", "Team B", 1, True)

    assert ui._should_process_grid_load_request(key) is True
    ui._grid_load_in_flight = True

    assert ui._should_process_grid_load_request(key, force_reload=True) is True
