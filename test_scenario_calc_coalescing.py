#!/usr/bin/env python3
"""Regression tests for scenario-calculation scheduling coalescing."""

from typing import Any, cast

from qtr_pairing_process.ui_manager_v2 import UiManager


class _DummyBox:
    def __init__(self, value: str):
        self._value = value

    def get(self) -> str:
        return self._value


class _DummyRoot:
    def __init__(self):
        self.after_calls = []
        self.cancel_calls = []

    def after(self, delay_ms: int, callback):
        self.after_calls.append((delay_ms, callback))
        return len(self.after_calls)

    def after_cancel(self, job_id):
        self.cancel_calls.append(job_id)


def _build_ui_manager_empty_selection() -> tuple[UiManager, _DummyRoot, list[tuple[str, float, dict[str, Any]]], dict[str, int]]:
    ui = UiManager.__new__(UiManager)
    root = _DummyRoot()
    skip_events: list[tuple[str, float, dict[str, Any]]] = []
    counters = {"runs": 0}

    u = cast(Any, ui)
    u.root = root
    u.combobox_1 = _DummyBox("")
    u.combobox_2 = _DummyBox("")
    u._scenario_calc_job = None
    u._scenario_calc_delay_ms = 120
    u._pending_scenario_calc_signature = None
    u._last_scenario_calc_signature = None

    def _log_perf_entry(label, elapsed_ms, **kwargs):
        skip_events.append((label, elapsed_ms, kwargs))

    def _run_scenario_calculations():
        counters["runs"] += 1

    u._log_perf_entry = _log_perf_entry
    u._run_scenario_calculations = _run_scenario_calculations
    return ui, root, skip_events, counters


def test_schedule_immediate_skips_when_signature_unchanged():
    ui, _root, skip_events, counters = _build_ui_manager_empty_selection()
    signature = ui._build_scenario_calc_signature()
    ui._last_scenario_calc_signature = signature

    ui._schedule_scenario_calculations(immediate=True)

    assert counters["runs"] == 0
    assert any(evt[2].get("reason") == "immediate_no_change" for evt in skip_events)


def test_schedule_delayed_skips_when_same_pending_request():
    ui, root, skip_events, _counters = _build_ui_manager_empty_selection()
    signature = ui._build_scenario_calc_signature()
    ui._scenario_calc_job = "42"
    ui._pending_scenario_calc_signature = signature

    ui._schedule_scenario_calculations(immediate=False)

    assert root.cancel_calls == []
    assert root.after_calls == []
    assert any(evt[2].get("reason") == "pending_same_request" for evt in skip_events)


def test_schedule_delayed_replaces_different_pending_request():
    ui, root, _skip_events, _counters = _build_ui_manager_empty_selection()
    ui._scenario_calc_job = "7"
    ui._pending_scenario_calc_signature = ("different",)

    ui._schedule_scenario_calculations(immediate=False)

    assert root.cancel_calls == ["7"]
    assert len(root.after_calls) == 1
