#!/usr/bin/env python3
"""Automation-safe tests for modal grab conflict handling."""

import tkinter as tk
import time

import pytest


def _safe_grab_set(dialog: tk.Toplevel, owner: tk.Toplevel) -> None:
    """Replicate safe-grab fallback used by production dialog flows."""
    try:
        dialog.grab_set()
    except tk.TclError as err:
        if "grab failed" in str(err).lower():
            try:
                owner.grab_release()
            except tk.TclError:
                pass
            dialog.after(10, lambda: dialog.grab_set())
        else:
            raise


@pytest.mark.requires_tk
def test_second_modal_can_acquire_grab_after_release_fallback():
    """Second dialog can become modal when first dialog already holds a grab."""
    root = tk.Tk()
    root.withdraw()

    first_dialog = None
    second_dialog = None
    try:
        first_dialog = tk.Toplevel(root)
        first_dialog.transient(root)
        first_dialog.grab_set()

        second_dialog = tk.Toplevel(first_dialog)
        second_dialog.transient(first_dialog)

        _safe_grab_set(second_dialog, first_dialog)

        root.update_idletasks()
        deadline = time.perf_counter() + 0.25
        while time.perf_counter() < deadline:
            root.update()

        current = root.grab_current()
        assert current == second_dialog
    finally:
        for widget in (second_dialog, first_dialog, root):
            if widget is not None and widget.winfo_exists():
                widget.destroy()


@pytest.mark.requires_tk
def test_second_modal_close_releases_grab_cleanly():
    """Closing the second modal should leave no stuck grab state."""
    root = tk.Tk()
    root.withdraw()

    first_dialog = None
    second_dialog = None
    try:
        first_dialog = tk.Toplevel(root)
        first_dialog.transient(root)
        first_dialog.grab_set()

        second_dialog = tk.Toplevel(first_dialog)
        second_dialog.transient(first_dialog)
        _safe_grab_set(second_dialog, first_dialog)

        root.update_idletasks()
        second_dialog.destroy()
        root.update_idletasks()

        current = root.grab_current()
        assert current in (None, first_dialog)
    finally:
        for widget in (second_dialog, first_dialog, root):
            if widget is not None and widget.winfo_exists():
                widget.destroy()
