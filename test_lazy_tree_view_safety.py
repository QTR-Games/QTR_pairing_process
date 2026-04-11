#!/usr/bin/env python3
"""Focused safety coverage for lazy tree behavior."""

import tkinter as tk

from qtr_pairing_process.lazy_tree_view import LazyTreeView


def test_on_open_does_not_populate_without_demo_mode():
    root = tk.Tk()
    root.withdraw()

    view = LazyTreeView(print_output=False, master=root, columns=("Rating",))
    node_id = view.tree.insert("", "end", text="Team A", values=(3,))
    view.tree.focus(node_id)

    def _unexpected_populate(_parent=""):
        raise AssertionError("populate_tree should not be called in production mode")

    view.populate_tree = _unexpected_populate  # type: ignore[method-assign]

    view.on_open(None)
    root.destroy()


def test_on_open_demo_population_runs_once_for_leaf_node():
    root = tk.Tk()
    root.withdraw()

    view = LazyTreeView(print_output=False, master=root, columns=("Rating",), enable_demo_population=True)
    node_id = view.tree.insert("", "end", text="Team A", values=(3,))
    view.tree.focus(node_id)

    view.on_open(None)
    first_children = view.tree.get_children(node_id)
    assert len(first_children) == 6

    view.on_open(None)
    second_children = view.tree.get_children(node_id)
    assert len(second_children) == 6

    root.destroy()
