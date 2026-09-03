from __future__ import annotations

import gc
import os
import shutil
import time
from pathlib import Path
from tkinter import messagebox

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
from qtr_pairing_process.ui_manager_v2 import UiManager


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


@pytest.fixture
def real_ui_manager(monkeypatch):
    scenario = THREE_V_THREE_UNIFORM
    db_dir = (
        Path(__file__).resolve().parent
        / ".pytest_cache"
        / f"qtr_back_button_db_{os.getpid()}"
    )
    db_dir.mkdir(parents=True, exist_ok=True)
    db_name = "back_button.db"

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
        # 'SystemButtonFace' is a Windows-only Tk system color name; skip the
        # button recoloring here so this test can run on any platform.
        ui.update_sort_button_states = lambda: None
        ui.create_ui()
        ui.root.withdraw()
        yield ui
    finally:
        if ui is not None and ui._root_is_alive():
            ui.root.destroy()
        if ui is not None and getattr(ui, "db_manager", None) is not None:
            _close_db_manager(ui.db_manager)
            ui.db_manager = None
        _remove_db_dir(db_dir)


@pytest.mark.requires_tk
def test_back_button_starts_disabled(real_ui_manager):
    ui = real_ui_manager
    assert ui._back_button is not None
    assert str(ui._back_button["state"]) == "disabled"


@pytest.mark.requires_tk
def test_back_button_undoes_flip_grid(real_ui_manager, monkeypatch):
    ui = real_ui_manager
    monkeypatch.setattr(messagebox, "askyesno", lambda *args, **kwargs: True)
    assert bool(ui.grid_is_flipped) is False

    ui._on_shortcut_flip_grid()
    assert bool(ui.grid_is_flipped) is True
    assert str(ui._back_button["state"]) == "normal"

    ui._on_back_button()
    assert bool(ui.grid_is_flipped) is False
    # Undo stack is empty again, so the Back button should be disabled.
    assert str(ui._back_button["state"]) == "disabled"


@pytest.mark.requires_tk
def test_back_button_undoes_grid_paste(real_ui_manager, monkeypatch):
    ui = real_ui_manager
    monkeypatch.setattr(messagebox, "askyesno", lambda *args, **kwargs: True)

    before_values = [
        [ui.grid_data_model.get_rating(r, c) for c in range(1, 6)]
        for r in range(1, 6)
    ]

    pasted_grid = [[7] * 5 for _ in range(5)]
    ui._apply_5x5_grid(pasted_grid)

    assert all(
        ui.grid_data_model.get_rating(r, c) == 7 for r in range(1, 6) for c in range(1, 6)
    )
    assert str(ui._back_button["state"]) == "normal"

    ui._on_back_button()

    after_values = [
        [ui.grid_data_model.get_rating(r, c) for c in range(1, 6)]
        for r in range(1, 6)
    ]
    assert after_values == before_values
    assert str(ui._back_button["state"]) == "disabled"
