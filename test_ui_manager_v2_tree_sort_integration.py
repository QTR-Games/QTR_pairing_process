from __future__ import annotations

import gc
import os
import shutil
import time
from collections import Counter
from pathlib import Path

import pytest

from golden_master_scenarios import THREE_V_THREE_UNIFORM
from qtr_pairing_process.constants import (
    DEFAULT_COLOR_MAP,
    DIRECTORY,
    RATING_SYSTEMS,
    SCENARIO_MAP,
    SCENARIO_RANGES,
    SCENARIO_TO_CSV_MAP,
)
from qtr_pairing_process.db_management.db_manager import DbManager
from qtr_pairing_process.pairing_model import TreeProjector
from qtr_pairing_process.ui_manager_v2 import UiManager


@pytest.fixture
def real_ui_manager(monkeypatch):
    monkeypatch.setenv("QTR_ENGINE", "model")
    monkeypatch.setenv("QTR_RISK", "1")
    monkeypatch.delenv("QTR_RENDER", raising=False)

    previous_risk_columns_enabled = TreeProjector.RISK_COLUMNS_ENABLED
    scenario = THREE_V_THREE_UNIFORM
    db_dir = (
        Path(__file__).resolve().parent
        / ".pytest_cache"
        / f"qtr_ui_sort_db_{os.getpid()}"
    )
    db_dir.mkdir(parents=True, exist_ok=True)
    db_name = "ui_sort_integration.db"

    def select_test_database(self, force_prompt: bool = False) -> bool:
        self.db_path = str(db_dir)
        self.db_name = db_name
        self.db_manager = DbManager(path=self.db_path, name=self.db_name)
        self.db_manager.set_rating_system(scenario.rating_system)
        self.current_rating_system = scenario.rating_system
        self.rating_config = RATING_SYSTEMS[scenario.rating_system]
        self.color_map = self.rating_config["color_map"]
        self.rating_range = self.rating_config["range"]
        self._pending_generated_tree_cache_ensure = False
        return True

    monkeypatch.setattr(UiManager, "select_database", select_test_database)

    ui = None
    try:
        ui = UiManager(
            color_map=DEFAULT_COLOR_MAP,
            scenario_map=SCENARIO_MAP,
            directory=DIRECTORY,
            scenario_ranges=SCENARIO_RANGES,
            scenario_to_csv_map=SCENARIO_TO_CSV_MAP,
            print_output=False,
            perf_enabled=False,
        )
        ui.root.withdraw()
        ui.root.mainloop = lambda *args, **kwargs: None
        ui.create_ui()
        ui.root.withdraw()
        yield ui
    finally:
        if ui is not None and ui._root_is_alive():
            ui.root.destroy()
        if ui is not None and getattr(ui, "db_manager", None) is not None:
            _close_db_manager(ui.db_manager)
            ui.db_manager = None
        TreeProjector.RISK_COLUMNS_ENABLED = previous_risk_columns_enabled
        _remove_db_dir(db_dir)


def _tk_tuple(tree, value) -> tuple[str, ...]:
    if isinstance(value, (tuple, list)):
        return tuple(str(item) for item in value)
    return tuple(tree.tk.splitlist(value))


def _close_db_manager(db_manager) -> None:
    secure_interfaces = getattr(db_manager, "_secure_db_by_thread", {})
    for secure_db in list(secure_interfaces.values()):
        secure_db.close()
    secure_interfaces.clear()


def _remove_db_dir(db_dir: Path) -> None:
    for _ in range(10):
        gc.collect()
        try:
            shutil.rmtree(db_dir)
            return
        except FileNotFoundError:
            return
        except PermissionError:
            time.sleep(0.05)
    shutil.rmtree(db_dir, ignore_errors=True)


def _top_level_rows(tree) -> tuple[str, ...]:
    roots = tree.get_children("")
    assert len(roots) == 1
    rows = tree.get_children(roots[0])
    assert rows
    return rows


def _percent_values(tree, rows: tuple[str, ...], column: str) -> list[float]:
    values = []
    for row in rows:
        raw = tree.set(row, column)
        assert raw.endswith("%"), f"expected percent text in {column}, got {raw!r}"
        values.append(float(raw.removesuffix("%")))
    return values


def _is_monotonic(values: list[float], *, descending: bool) -> bool:
    pairs = zip(values, values[1:], strict=False)
    if descending:
        return all(left >= right for left, right in pairs)
    return all(left <= right for left, right in pairs)


def _invoke_heading(tree, column: str) -> None:
    command = tree.heading(column)["command"]
    assert command, f"{column} heading has no command bound"
    tree.tk.call(command)


@pytest.mark.requires_tk
def test_v2_risk_column_heading_click_sorts_real_tree(real_ui_manager):
    ui = real_ui_manager
    tree = ui.treeview.tree

    expected_columns = (
        "Rating",
        "Sort Value",
        "Confidence",
        "Resistance",
        "P(win)",
        "Floor",
        "P10",
        "Sigma",
    )
    expected_displaycolumns = (
        "Rating",
        "Sort Value",
        "P(win)",
        "Floor",
        "P10",
        "Sigma",
    )
    assert _tk_tuple(tree, tree.cget("columns")) == expected_columns
    assert _tk_tuple(tree, tree.cget("displaycolumns")) == expected_displaycolumns

    scenario = THREE_V_THREE_UNIFORM
    ui.tree_generator.generate_combinations(
        list(scenario.our_players),
        list(scenario.opponent_players),
        scenario.our_ratings,
        scenario.opponent_ratings,
        our_team_first=scenario.our_team_first,
    )

    rows = _top_level_rows(tree)
    raw_values = [tree.set(row, "P(win)") for row in rows]
    distribution = Counter(raw_values)
    pre_sort_values = _percent_values(tree, rows, "P(win)")
    assert len(distribution) >= 3, distribution
    assert not _is_monotonic(pre_sort_values, descending=True), distribution
    assert not _is_monotonic(pre_sort_values, descending=False), distribution

    _invoke_heading(tree, "P(win)")

    assert ui.column_sort_states["P(win)"] == "desc"
    descending_values = _percent_values(tree, _top_level_rows(tree), "P(win)")
    assert _is_monotonic(descending_values, descending=True)

    _invoke_heading(tree, "P(win)")

    assert ui.column_sort_states["P(win)"] == "asc"
    ascending_values = _percent_values(tree, _top_level_rows(tree), "P(win)")
    assert _is_monotonic(ascending_values, descending=False)
    assert ascending_values != descending_values
