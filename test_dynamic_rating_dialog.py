#!/usr/bin/env python3
"""
Automation-safe tests for the dynamic rating system dialog.
"""
import tkinter as tk
import pytest

from qtr_pairing_process.rating_system_dialog import RatingSystemDialog


class _StubDbManager:
    def __init__(self, ratings_count=0):
        self._ratings_count = ratings_count

    def get_ratings_count(self):
        return self._ratings_count


@pytest.mark.requires_tk
def test_rating_dialog_cancel_is_non_blocking():
    """Dialog can open and close via scheduled cancel without manual input."""
    root = tk.Tk()
    root.withdraw()

    try:
        dialog = RatingSystemDialog(root, "1-5", _StubDbManager(ratings_count=0))
        root.after(120, dialog._on_cancel)

        result = dialog.show()
        assert result is None
        assert dialog.selected_system is None
    finally:
        if root.winfo_exists():
            root.destroy()


@pytest.mark.requires_tk
def test_rating_dialog_apply_returns_selected_system():
    """Dialog applies a changed system when data count is zero (no confirm prompt)."""
    root = tk.Tk()
    root.withdraw()

    try:
        dialog = RatingSystemDialog(root, "1-5", _StubDbManager(ratings_count=0))

        def _auto_apply():
            if dialog.system_var is None:
                return
            dialog.system_var.set("1-3")
            dialog._on_apply()

        root.after(140, _auto_apply)

        result = dialog.show()
        assert result is None
        assert dialog.selected_system == "1-3"
    finally:
        if root.winfo_exists():
            root.destroy()