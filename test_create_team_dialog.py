<<<<<<< HEAD
#!/usr/bin/env python3
"""
Test script for the dynamic Create Team Dialog
"""
import tkinter as tk
import sys
import os

# Add the qtr_pairing_process directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'qtr_pairing_process'))

from qtr_pairing_process.create_team_dialog import CreateTeamDialog

def test_create_team_dialog():
    """Test the Create Team Dialog with dynamic sizing"""
    # Create test root window
    root = tk.Tk()
    root.title("Test Create Team Dialog")
    root.geometry("400x300")
    
    def show_dialog():
        """Show the create team dialog"""
        existing_teams = ["Test Team 1", "Test Team 2", "Sample Team"]
        
        dialog = CreateTeamDialog(root, existing_teams)
        result = dialog.show()
        
        print(f"Dialog result: {result}")
        if result:
            print(f"Team Name: {result['team_name']}")
            print(f"Players: {result['player_names']}")
        
        root.quit()
    
    # Main window content
    title = tk.Label(root, text="Create Team Dialog Test", font=("Arial", 16, "bold"))
    title.pack(pady=20)
    
    desc = tk.Label(root, text="This tests the Create Team Dialog with dynamic sizing.\nClick 'Show Dialog' to test.")
    desc.pack(pady=10)
    
    test_btn = tk.Button(root, text="Show Dialog", command=show_dialog, 
                        bg="lightblue", font=("Arial", 12), padx=20, pady=10)
    test_btn.pack(pady=30)
    
    quit_btn = tk.Button(root, text="Quit Test", command=root.quit, 
                        bg="lightcoral", font=("Arial", 12), padx=20, pady=10)
    quit_btn.pack(pady=10)
    
    print("🧪 Starting Create Team Dialog test...")
    print("📋 Instructions:")
    print("1. Click 'Show Dialog' to open the Create Team Wizard")
    print("2. Check if the dialog sizes properly to show all content")
    print("3. Try entering team and player information")
    print("4. Verify tooltips and validation work correctly")
    
    # Start the event loop
    root.mainloop()

if __name__ == "__main__":
=======
#!/usr/bin/env python3
"""
Test script for the dynamic Create Team Dialog
"""
import tkinter as tk
import sys
import os

# Add the qtr_pairing_process directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'qtr_pairing_process'))

from qtr_pairing_process.create_team_dialog import CreateTeamDialog

def test_create_team_dialog():
    """Test the Create Team Dialog with dynamic sizing"""
    # Create test root window
    root = tk.Tk()
    root.title("Test Create Team Dialog")
    root.geometry("400x300")
    
    def show_dialog():
        """Show the create team dialog"""
        existing_teams = ["Test Team 1", "Test Team 2", "Sample Team"]
        
        dialog = CreateTeamDialog(root, existing_teams)
        result = dialog.show()
        
        print(f"Dialog result: {result}")
        if result:
            print(f"Team Name: {result['team_name']}")
            print(f"Players: {result['player_names']}")
        
        root.quit()
    
    # Main window content
    title = tk.Label(root, text="Create Team Dialog Test", font=("Arial", 16, "bold"))
    title.pack(pady=20)
    
    desc = tk.Label(root, text="This tests the Create Team Dialog with dynamic sizing.\nClick 'Show Dialog' to test.")
    desc.pack(pady=10)
    
    test_btn = tk.Button(root, text="Show Dialog", command=show_dialog, 
                        bg="lightblue", font=("Arial", 12), padx=20, pady=10)
    test_btn.pack(pady=30)
    
    quit_btn = tk.Button(root, text="Quit Test", command=root.quit, 
                        bg="lightcoral", font=("Arial", 12), padx=20, pady=10)
    quit_btn.pack(pady=10)
    
    print("🧪 Starting Create Team Dialog test...")
    print("📋 Instructions:")
    print("1. Click 'Show Dialog' to open the Create Team Wizard")
    print("2. Check if the dialog sizes properly to show all content")
    print("3. Try entering team and player information")
    print("4. Verify tooltips and validation work correctly")
    
    # Start the event loop
    root.mainloop()

if __name__ == "__main__":
>>>>>>> origin/main
    test_create_team_dialog()