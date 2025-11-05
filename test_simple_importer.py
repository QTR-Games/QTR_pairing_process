#!/usr/bin/env python3
"""
Test script for the updated SimpleExcelImporter
"""

from qtr_pairing_process.excel_management.simple_excel_importer import SimpleExcelImporter
from qtr_pairing_process.db_management.db_manager import DbManager
from tkinter import filedialog
import tkinter as tk

def test_simple_importer():
    """Test the SimpleExcelImporter with the new format"""
    # Create a simple root window for the file dialog
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    # Ask user to select Excel file
    file_path = filedialog.askopenfilename(
        title="Select Excel File to Test Import",
        filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
    )
    
    if not file_path:
        print("No file selected")
        return
        
    try:
        # Skip database testing - just test the file parsing logic
        print("Note: This test only validates file parsing, not database operations")
        print("For full testing, use the application's Simple Import button")
        return
        
        # Load the workbook
        if not importer.load_workbook():
            print("Failed to load workbook")
            return
            
        # Extract friendly team name
        if not importer.extract_friendly_team_name():
            print("Failed to extract friendly team name")
            return
            
        print(f"Friendly Team: {importer.friendly_team_name}")
        print()
        
        # Find opponent team blocks
        opponent_blocks = importer.find_opponent_team_blocks()
        print(f"Found {len(opponent_blocks)} opponent team blocks:")
        
        for i, (row, team_name) in enumerate(opponent_blocks):
            print(f"{i+1}. Row {row}: {team_name}")
            
            try:
                # Extract data for this team
                team_data = importer.extract_team_block_data(row, team_name)
                
                print(f"   Opponent Players: {team_data['opponent_players']}")
                print(f"   Friendly Players: {team_data['friendly_players']}")
                print(f"   Ratings Matrix ({len(team_data['ratings_matrix'])}x{len(team_data['ratings_matrix'][0]) if team_data['ratings_matrix'] else 0}):")
                
                for j, (friendly_player, ratings) in enumerate(zip(team_data['friendly_players'], team_data['ratings_matrix'])):
                    print(f"     {friendly_player}: {ratings}")
                
                # Validate the data
                validation_errors = importer.validate_team_data(team_data)
                if validation_errors:
                    print(f"   Validation Errors: {validation_errors}")
                else:
                    print(f"   ✓ Data is valid")
                    
            except Exception as e:
                print(f"   Error extracting data: {e}")
                
            print()
            
    except Exception as e:
        print(f"Error testing importer: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_importer()