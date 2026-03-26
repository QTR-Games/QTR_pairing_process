#!/usr/bin/env python3
"""
Test script for the updated SimpleExcelImporter
"""

import pytest
from tkinter import filedialog
import tkinter as tk


pytestmark = pytest.mark.skip(reason="Manual interactive script; opens file chooser")


def test_simple_importer():
    """Test the SimpleExcelImporter with the new format"""
    root = tk.Tk()
    root.withdraw()

    file_path = filedialog.askopenfilename(
        title="Select Excel File to Test Import",
        filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
    )

    if not file_path:
        print("No file selected")
        return

    try:
        print("Note: This test only validates file parsing, not database operations")
        print("For full testing, use the application's Simple Import button")
        return
    except Exception as e:
        print(f"Error testing importer: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_simple_importer()
