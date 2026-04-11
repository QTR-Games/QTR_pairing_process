#!/usr/bin/env python3
"""Automate controlled perf capture runs for the Tk UI workflow."""

from __future__ import annotations

import argparse
import shutil
import time
from pathlib import Path
from tkinter import messagebox
from typing import List, Optional, Tuple

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


def _normalize_team_name(name: str) -> str:
    return " ".join(str(name).strip().lower().split())


def _matches_pattern(name: str, pattern: str) -> bool:
    name_norm = _normalize_team_name(name)
    pattern_norm = _normalize_team_name(pattern)

    if not pattern_norm:
        return False

    if "*" not in pattern_norm:
        return name_norm == pattern_norm

    # Minimal wildcard support: prefix* / *suffix / prefix*suffix
    prefix, _, suffix = pattern_norm.partition("*")
    if prefix and not name_norm.startswith(prefix):
        return False
    if suffix and not name_norm.endswith(suffix):
        return False
    return True


def _select_qualified_teams(
    team_names: List[str],
    left_pattern: str,
    right_pattern: str,
) -> Optional[Tuple[str, str]]:
    left_candidates = [name for name in team_names if _matches_pattern(name, left_pattern)]
    right_candidates = [name for name in team_names if _matches_pattern(name, right_pattern)]

    if not left_candidates or not right_candidates:
        return None

    left = sorted(left_candidates)[0]
    # Avoid selecting the same team for both sides if multiple matches exist.
    right_pool = [name for name in right_candidates if name != left] or right_candidates
    right = sorted(right_pool)[0]
    return left, right


def _validate_grid_integrity(ui: UiManager, run_index: int) -> bool:
    """Verify key grid widgets exist before performance workflow executes.

    This protects capture quality when Tk intermittently paints an incomplete
    top panel during automated runs.
    """
    try:
        root = ui.root
        root.update_idletasks()

        grid_frame = getattr(ui, "grid_frame", None)
        if grid_frame is None or not grid_frame.winfo_exists():
            print(f"[capture run {run_index}] grid integrity failed: grid_frame missing")
            return False

        labels = [
            child for child in grid_frame.winfo_children()
            if child.winfo_exists() and child.winfo_class() == "Label"
        ]
        label_texts = {str(label.cget("text")) for label in labels}
        has_rating_header = "Rating Matrix" in label_texts
        has_calc_header = "Calculations" in label_texts

        rating_widget_count = sum(
            1
            for row in getattr(ui, "grid_widgets", [])
            for widget in row
            if widget is not None and widget.winfo_exists()
        )
        display_widget_count = sum(
            1
            for row in getattr(ui, "grid_display_widgets", [])
            for widget in row
            if widget is not None and widget.winfo_exists()
        )

        healthy = (
            has_rating_header
            and has_calc_header
            and rating_widget_count >= 36
            and display_widget_count >= 30
        )

        if not healthy:
            print(
                f"[capture run {run_index}] grid integrity failed: "
                f"rating_header={int(has_rating_header)} "
                f"calc_header={int(has_calc_header)} "
                f"rating_cells={rating_widget_count} "
                f"display_cells={display_widget_count}"
            )
        return healthy
    except Exception as exc:
        print(f"[capture run {run_index}] grid integrity exception: {exc}")
        return False


def _collect_tree_nodes_with_depth(ui: UiManager) -> List[Tuple[str, int]]:
    tree = ui.treeview.tree
    nodes: List[Tuple[str, int]] = []

    def walk(node_id: str, depth: int) -> None:
        nodes.append((node_id, depth))
        for child in tree.get_children(node_id):
            walk(child, depth + 1)

    for root in tree.get_children(""):
        walk(root, 0)
    return nodes


def _try_extract_for_node(ui: UiManager, node_id: str, run_index: int, label: str) -> Tuple[bool, float, int, str]:
    tree = ui.treeview.tree
    tree.selection_set(node_id)
    tree.focus(node_id)
    tree.see(node_id)

    start = time.perf_counter()
    ui.extract_final_matchups()
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    text_content = ""
    if hasattr(ui, "matchups_text") and ui.matchups_text is not None:
        text_content = ui.matchups_text.get("1.0", "end").strip()

    lines = [line for line in text_content.splitlines() if line.strip()]
    line_count = len(lines)
    item_text = tree.item(node_id, "text")
    extracted = bool(text_content)

    print(
        f"[capture run {run_index}] {label}: extracted={int(extracted)} "
        f"elapsed_ms={elapsed_ms:.2f} lines={line_count} node='{item_text}'"
    )
    return extracted, elapsed_ms, line_count, text_content


def _select_deepest_extractable_node(ui: UiManager, run_index: int) -> Optional[Tuple[str, int]]:
    nodes = _collect_tree_nodes_with_depth(ui)
    if not nodes:
        return None

    # Traverse deepest-first to maximize decision-path depth in extraction output.
    for node_id, depth in sorted(nodes, key=lambda item: item[1], reverse=True):
        matchups = ui.parse_matchups_from_tree_item(node_id)
        if matchups:
            print(f"[capture run {run_index}] selected deepest extractable depth={depth}")
            return node_id, depth

    return None


def _select_alternate_extractable_node(
    ui: UiManager,
    exclude_node: str,
    prefer_different_depth: int,
    run_index: int,
) -> Optional[Tuple[str, int]]:
    nodes = _collect_tree_nodes_with_depth(ui)
    candidates_diff_depth: List[Tuple[int, str, int]] = []
    candidates_same_depth: List[Tuple[int, str, int]] = []

    for node_id, depth in nodes:
        if node_id == exclude_node:
            continue
        matchups = ui.parse_matchups_from_tree_item(node_id)
        if not matchups:
            continue
        depth_delta = abs(depth - prefer_different_depth)
        if depth != prefer_different_depth:
            candidates_diff_depth.append((depth_delta, node_id, depth))
        else:
            candidates_same_depth.append((depth_delta, node_id, depth))

    if candidates_diff_depth:
        # Prefer the furthest different depth to maximize level separation.
        candidates_diff_depth.sort(key=lambda item: item[0], reverse=True)
        _score, node_id, depth = candidates_diff_depth[0]
        print(f"[capture run {run_index}] selected alternate extractable depth={depth}")
        return node_id, depth

    if not candidates_same_depth:
        return None

    # Fallback only when no extractable node exists at a different depth.
    candidates_same_depth.sort(key=lambda item: item[0], reverse=True)
    _score, node_id, depth = candidates_same_depth[0]
    print(f"[capture run {run_index}] selected alternate extractable depth={depth}")
    return node_id, depth


def _run_single_capture(
    run_index: int,
    workflow: str,
    left_team_pattern: str,
    right_team_pattern: str,
) -> None:
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

    def _select_first_pairing_node() -> Optional[Tuple[str, int]]:
        tree = ui.treeview.tree
        roots = list(tree.get_children(""))
        if not roots:
            return None

        # Prefer an actual pairing node under root; fallback to root itself.
        children = list(tree.get_children(roots[0]))
        target = children[0] if children else roots[0]
        depth = 1 if children else 0
        return target, depth

    def _close_soon(delay_ms: int = 200) -> None:
        try:
            root.after(delay_ms, ui._on_app_close)
        except Exception:
            pass

    def _do_workflow() -> None:
        try:
            if not _validate_grid_integrity(ui, run_index):
                print(f"[capture run {run_index}] skipped workflow: incomplete UI grid state")
                _close_soon(100)
                return

            ui.on_generate_combinations()
            ui.toggle_cumulative_sort()
            ui.toggle_confidence_sort()
            ui.toggle_counter_sort()
            ui.toggle_strategic_sort()

            if workflow == "simple":
                selected = _select_first_pairing_node()
                if not selected:
                    print(f"[capture run {run_index}] skipped extract: no pairing node available")
                else:
                    node_id, depth = selected
                    print(f"[capture run {run_index}] simple selection depth={depth}")
                    _try_extract_for_node(ui, node_id, run_index, "extract.simple")

            elif workflow == "deep-single":
                selected = _select_deepest_extractable_node(ui, run_index)
                if not selected:
                    print(f"[capture run {run_index}] skipped extract: no deep extractable node found")
                else:
                    node_id, _depth = selected
                    _try_extract_for_node(ui, node_id, run_index, "extract.deep_single")

            elif workflow == "deep-double":
                first = _select_deepest_extractable_node(ui, run_index)
                if not first:
                    print(f"[capture run {run_index}] skipped deep-double: no extractable first node")
                else:
                    first_node, first_depth = first
                    first_ok, first_ms, _first_lines, first_text = _try_extract_for_node(
                        ui,
                        first_node,
                        run_index,
                        "extract.deep_double.first",
                    )

                    second = _select_alternate_extractable_node(
                        ui,
                        exclude_node=first_node,
                        prefer_different_depth=first_depth,
                        run_index=run_index,
                    )

                    if not second:
                        print(f"[capture run {run_index}] skipped second extract: no alternate node found")
                    else:
                        second_node, second_depth = second
                        second_ok, second_ms, _second_lines, second_text = _try_extract_for_node(
                            ui,
                            second_node,
                            run_index,
                            "extract.deep_double.second",
                        )
                        overridden = bool(first_ok and second_ok and first_text != second_text)
                        print(
                            f"[capture run {run_index}] deep-double summary: "
                            f"depth1={first_depth} depth2={second_depth} "
                            f"override={int(overridden)} "
                            f"extract1_ms={first_ms:.2f} extract2_ms={second_ms:.2f}"
                        )

            else:
                print(f"[capture run {run_index}] unknown workflow '{workflow}'")
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

            qualified = _select_qualified_teams(teams, left_team_pattern, right_team_pattern)
            if not qualified:
                print(
                    f"[capture run {run_index}] team qualification failed: "
                    f"left='{left_team_pattern}' right='{right_team_pattern}'"
                )
                _close_soon(100)
                return

            left_team, right_team = qualified
            print(
                f"[capture run {run_index}] qualified teams: "
                f"left='{left_team}' right='{right_team}'"
            )

            ui.combobox_1.set(left_team)
            ui.combobox_2.set(right_team)

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
        "--workflow",
        default="simple",
        choices=["simple", "deep-single", "deep-double"],
        help="Capture workflow mode: simple, deepest single extract, or dual-depth extraction override test",
    )
    parser.add_argument(
        "--archive-dir",
        default="docs/validation/perf_capture",
        help="Directory where captured logs are archived",
    )
    parser.add_argument(
        "--left-team-pattern",
        default="dapper badgers",
        help="Required left-team wildcard pattern (default: dapper badgers)",
    )
    parser.add_argument(
        "--right-team-pattern",
        default="germany rackelhahn",
        help="Required right-team pattern (default: germany rackelhahn)",
    )
    args = parser.parse_args()

    archive_dir = Path(args.archive_dir)
    total_copied = 0

    for run_index in range(1, max(1, args.runs) + 1):
        before = set(Path("perf_logs").glob("perf_*.log"))
        _run_single_capture(
            run_index,
            args.workflow,
            args.left_team_pattern,
            args.right_team_pattern,
        )
        copied = _copy_new_logs(before, archive_dir, args.tag, run_index)
        total_copied += copied
        print(f"[capture run {run_index}] archived {copied} log file(s)")

    print(f"Capture complete. Archived files: {total_copied}")


if __name__ == "__main__":
    main()
