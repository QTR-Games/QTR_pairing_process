#!/usr/bin/env python3
"""
Test script for the dynamic rating system dialog
"""
import tkinter as tk
import sys
import os

# Add the qtr_pairing_process directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'qtr_pairing_process'))

from qtr_pairing_process.rating_system_dialog import RatingSystemDialog
from qtr_pairing_process.db_management.db_manager import DbManager

def test_rating_dialog():
    """Test the rating system dialog with dynamic sizing"""
    # Create test root window
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    # Create a mock database manager
    db_manager = DbManager()
    
    def show_dialog():
        """Show the rating system dialog"""
        dialog = RatingSystemDialog(root, "1-5", db_manager)
        result = dialog.show()
        
        print(f"Dialog result: {result}")
        if result:
            print(f"Selected system: {result}")
        
        root.quit()
    
    # Schedule dialog to show after root window is ready
    root.after(100, show_dialog)
    
    # Start the event loop
    root.mainloop()

if __name__ == "__main__":
    print("Testing Dynamic Rating System Dialog...")
    test_rating_dialog()
    print("Test completed!")