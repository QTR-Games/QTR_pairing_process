#!/usr/bin/env python3
"""Automation-safe tests for CreateTeamDialog."""

import tkinter as tk

import pytest

from qtr_pairing_process.create_team_dialog import CreateTeamDialog


@pytest.mark.requires_tk
def test_create_team_dialog_cancel_is_non_blocking():
    """Dialog can open and cancel via scheduled callback without manual input."""
    root = tk.Tk()
    root.withdraw()

    try:
        dialog = CreateTeamDialog(root, ["Test Team 1", "Test Team 2", "Sample Team"])
        root.after(120, dialog.cancel)

        result = dialog.show()
        assert result is None
        assert dialog.result is None
    finally:
        if root.winfo_exists():
            root.destroy()


@pytest.mark.requires_tk
def test_create_team_dialog_returns_team_payload():
    """Dialog auto-fills fields and returns normalized payload."""
    root = tk.Tk()
    root.withdraw()

    try:
        dialog = CreateTeamDialog(root, ["Existing Team"]) 

        def _auto_fill_and_submit():
            if dialog.team_name_entry is None or len(dialog.player_entries) != 5:
                return

            dialog.team_name_entry.delete(0, tk.END)
            dialog.team_name_entry.insert(0, "Automation Team")

            for idx, entry in enumerate(dialog.player_entries, start=1):
                entry.delete(0, tk.END)
                entry.insert(0, f"Player {idx}")

            dialog.create_team()

        root.after(160, _auto_fill_and_submit)

        result = dialog.show()
        assert isinstance(result, dict)
        assert result["team_name"] == "Automation Team"
        assert result["player_names"] == [
            "Player 1",
            "Player 2",
            "Player 3",
            "Player 4",
            "Player 5",
        ]
        assert dialog.result == result
    finally:
        if root.winfo_exists():
            root.destroy()
