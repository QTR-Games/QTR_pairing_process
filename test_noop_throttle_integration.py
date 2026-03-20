#!/usr/bin/env python3
"""Integration-style tests for no-op skip throttling and summary emission."""

from types import SimpleNamespace
from typing import Any, cast

from qtr_pairing_process.ui_manager_v2 import UiManager


def _build_noop_test_ui() -> tuple[UiManager, list[tuple[str, float, dict[str, Any]]]]:
    ui = UiManager.__new__(UiManager)
    u = cast(Any, ui)

    logged_events: list[tuple[str, float, dict[str, Any]]] = []
    u.perf = SimpleNamespace(enabled=True)
    u._noop_skip_counters = {}
    u._noop_skip_last_log_at = {}

    def _log_perf_entry(label: str, elapsed_ms: float, **meta: Any):
        logged_events.append((label, elapsed_ms, meta))

    u._log_perf_entry = _log_perf_entry
    return ui, logged_events


def test_noop_throttle_counts_all_but_logs_once_within_window():
    ui, logged_events = _build_noop_test_ui()

    ui._record_noop_skip("grid.load.skipped_duplicate", "burst_window", throttle_ms=60_000.0)
    ui._record_noop_skip("grid.load.skipped_duplicate", "burst_window", throttle_ms=60_000.0)

    bucket_key = "grid.load.skipped_duplicate|burst_window"
    assert ui._noop_skip_counters[bucket_key] == 2
    assert len(logged_events) == 1
    assert logged_events[0][0] == "grid.load.skipped_duplicate"


def test_noop_without_throttle_logs_every_event():
    ui, logged_events = _build_noop_test_ui()

    ui._record_noop_skip("scenario.calc.skipped", "pending_same_request")
    ui._record_noop_skip("scenario.calc.skipped", "pending_same_request")

    bucket_key = "scenario.calc.skipped|pending_same_request"
    assert ui._noop_skip_counters[bucket_key] == 2
    assert len(logged_events) == 2


def test_noop_summary_emits_total_and_bucket_rows():
    ui, logged_events = _build_noop_test_ui()

    ui._record_noop_skip("comments.indicators.skipped", "no_change")
    ui._record_noop_skip("post.load.refresh.skipped", "no_change")
    ui._record_noop_skip("post.load.refresh.skipped", "no_change")

    logged_events.clear()
    ui._emit_noop_skip_summary()

    summary = [evt for evt in logged_events if evt[0] == "noop.skip.summary"]
    buckets = [evt for evt in logged_events if evt[0] == "noop.skip.bucket"]

    assert len(summary) == 1
    assert summary[0][2]["total_skips"] == 3
    assert summary[0][2]["bucket_count"] == 2
    assert len(buckets) == 2
