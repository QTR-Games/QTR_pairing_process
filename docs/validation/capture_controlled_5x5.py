#!/usr/bin/env python3
"""Automate controlled perf capture runs for the Tk UI workflow."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from tkinter import messagebox
from typing import List

from qtr_pairing_process.constants import (
    DEFAULT_COLOR_MAP,
    DIRECTORY,
    SCENARIO_MAP,
    SCENARIO_RANGES,
    SCENARIO_TO_CSV_MAP,
)
from qtr_pairing_process.ui_manager_v2 import UiManager


def _team_choices(ui: UiManager) -> List[str]:
    names = ui.select_team_names()
    return [name for name in names if name and name != "No teams Found"]


def _run_single_capture(run_index: int) -> None:
    ui = UiManager(
        color_map=DEFAULT_COLOR_MAP,
        scenario_map=SCENARIO_MAP,
        directory=DIRECTORY,
        scenario_ranges=SCENARIO_RANGES,
        scenario_to_csv_map=SCENARIO_TO_CSV_MAP,
        print_output=False,
        perf_enabled=True,
    )

    # Avoid welcome modal during automated capture.
    try:
        ui.db_preferences.should_show_welcome_message = lambda: False  # type: ignore[method-assign]
    except Exception:
        pass

    root = ui.root
    original_showwarning = messagebox.showwarning
    messagebox.showwarning = lambda *args, **kwargs: None

    def _select_first_pairing_node() -> bool:
        try:
            tree = ui.treeview.tree
            roots = list(tree.get_children(""))
            if not roots:
                return False

            # Prefer an actual pairing node under root; fallback to root itself.
            children = list(tree.get_children(roots[0]))
            target = children[0] if children else roots[0]
            tree.selection_set(target)
            tree.focus(target)
            tree.see(target)
            return True
        except Exception:
            return False

    def _close_soon(delay_ms: int = 200) -> None:
        try:
            root.after(delay_ms, ui._on_app_close)
        except Exception:
            pass

    def _do_workflow() -> None:
        try:
            ui.on_generate_combinations()
            ui.toggle_cumulative_sort()
            ui.toggle_confidence_sort()
            ui.toggle_counter_sort()
            ui.toggle_strategic_sort()

            if _select_first_pairing_node():
                ui.extract_final_matchups()
            else:
                print(f"[capture run {run_index}] skipped extract: no pairing node available")
            _close_soon(250)
        except Exception as exc:
            print(f"[capture run {run_index}] workflow error: {exc}")
            _close_soon(100)

    def _prime_and_run() -> None:
        try:
            teams = _team_choices(ui)
            if len(teams) < 2:
                print(f"[capture run {run_index}] not enough teams for capture")
                _close_soon(100)
                return

            ui.combobox_1.set(teams[0])
            ui.combobox_2.set(teams[1])

            scenarios = list(ui.scenario_box.cget("values") or [])
            if scenarios:
                ui.scenario_box.set(str(scenarios[0]))

            root.after(700, _do_workflow)
        except Exception as exc:
            print(f"[capture run {run_index}] prime error: {exc}")
            _close_soon(100)

    root.after(700, _prime_and_run)
    try:
        ui.create_ui()
    finally:
        messagebox.showwarning = original_showwarning


def _copy_new_logs(before: set[Path], archive_dir: Path, tag: str, run_index: int) -> int:
    after = set(Path("perf_logs").glob("perf_*.log"))
    new_logs = sorted(after - before, key=lambda p: p.name)
    if not new_logs:
        # Fallback: copy the newest log if no set difference is found.
        candidates = sorted(after, key=lambda p: p.stat().st_mtime)
        if not candidates:
            return 0
        new_logs = [candidates[-1]]

    copied = 0
    archive_dir.mkdir(parents=True, exist_ok=True)
    for src in new_logs:
        dst = archive_dir / f"{tag}_{run_index:02d}_{src.name}"
        shutil.copy2(src, dst)
        copied += 1
    return copied


def main() -> None:
    parser = argparse.ArgumentParser(description="Automate controlled 5x5 perf capture runs")
    parser.add_argument("--tag", required=True, help="Prefix tag for archived logs (e.g. baseline or new)")
    parser.add_argument("--runs", type=int, default=5, help="Number of runs to execute")
    parser.add_argument(
        "--archive-dir",
        default="docs/validation/perf_capture",
        help="Directory where captured logs are archived",
    )
    args = parser.parse_args()

    archive_dir = Path(args.archive_dir)
    total_copied = 0

    for run_index in range(1, max(1, args.runs) + 1):
        before = set(Path("perf_logs").glob("perf_*.log"))
        _run_single_capture(run_index)
        copied = _copy_new_logs(before, archive_dir, args.tag, run_index)
        total_copied += copied
        print(f"[capture run {run_index}] archived {copied} log file(s)")

    print(f"Capture complete. Archived files: {total_copied}")


if __name__ == "__main__":
    main()
