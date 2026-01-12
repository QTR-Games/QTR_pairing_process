"""Automated test for dropdown clearing behavior."""
import time
import tkinter as tk
from qtr_pairing_process.ui_manager import UiManager
from qtr_pairing_process.constants import DEFAULT_COLOR_MAP, SCENARIO_MAP, DIRECTORY, SCENARIO_RANGES, SCENARIO_TO_CSV_MAP

def wait_for_ui():
    """Wait for UI updates to complete."""
    time.sleep(0.5)

def run_test():
    print("=" * 70)
    print("Starting automated dropdown clearing test...")
    print("=" * 70)
    
    # Create UI Manager
    ui = UiManager(
        color_map=DEFAULT_COLOR_MAP,
        scenario_map=SCENARIO_MAP,
        directory=DIRECTORY,
        scenario_ranges=SCENARIO_RANGES,
        scenario_to_csv_map=SCENARIO_TO_CSV_MAP,
        print_output=True
    )
    
    # Schedule the test to run after UI is fully loaded
    def run_test_steps():
        try:
            print("\n" + "=" * 70)
            print("TEST STEP 1: Setting Round 1 ante to 'Justin'")
            print("=" * 70)
    
    # Round 1: Justin (ante)
    if len(ui.round_vars) > 0:
        ui.round_vars[0].set("Justin")
        wait_for_ui()
    
    print("\n" + "=" * 70)
    print("TEST STEP 2: Setting Round 2 responses to 'Mike' and 'Rick'")
    print("=" * 70)
    
    # Round 2: Mike, Rick (responses)
    if len(ui.round_vars) > 1:
        ui.round_vars[1].set("Mike")
        wait_for_ui()
    if len(ui.round_vars) > 2:
        ui.round_vars[2].set("Rick")
        wait_for_ui()
    
    print("\n" + "=" * 70)
    print("TEST STEP 3: Setting Round 3 ante to 'Mike'")
    print("=" * 70)
    
    # Round 3: Mike (ante)
    if len(ui.round_vars) > 3:
        ui.round_vars[3].set("Mike")
        wait_for_ui()
    
    print("\n" + "=" * 70)
    print("Current state BEFORE clearing Mike from Round 2:")
    print("=" * 70)
    print(f"Round 1 ante: {ui.selected_players_per_round.get(1, {}).get('ante')}")
    print(f"Round 2 response1: {ui.selected_players_per_round.get(2, {}).get('response1')}")
    print(f"Round 2 response2: {ui.selected_players_per_round.get(2, {}).get('response2')}")
    print(f"Round 3 ante: {ui.selected_players_per_round.get(3, {}).get('ante')}")
    print(f"Round 3 implicit: {ui.selected_players_per_round.get(3, {}).get('implicit_selection')}")
    
    # Check checkbox states
    friendly_players = ui.get_friendly_player_names()
    print("\nCheckbox states:")
    for idx, player in enumerate(friendly_players):
        if idx < len(ui.row_checkboxes):
            state = ui.row_checkboxes[idx].get()
            print(f"  {player}: {'CHECKED' if state else 'UNCHECKED'}")
    
    print("\n" + "=" * 70)
    print("TEST STEP 4: Clearing Mike from Round 2 response1")
    print("=" * 70)
    
    # Clear Mike from Round 2
    if len(ui.round_vars) > 1:
        ui.round_vars[1].set("")
        wait_for_ui()
    
    print("\n" + "=" * 70)
    print("Current state AFTER clearing Mike from Round 2:")
    print("=" * 70)
    print(f"Round 1 ante: {ui.selected_players_per_round.get(1, {}).get('ante')}")
    print(f"Round 2 response1: {ui.selected_players_per_round.get(2, {}).get('response1')}")
    print(f"Round 2 response2: {ui.selected_players_per_round.get(2, {}).get('response2')}")
    print(f"Round 3 ante: {ui.selected_players_per_round.get(3, {}).get('ante')}")
    print(f"Round 3 implicit: {ui.selected_players_per_round.get(3, {}).get('implicit_selection')}")
    
    # Check checkbox states
    print("\nCheckbox states:")
    for idx, player in enumerate(friendly_players):
        if idx < len(ui.row_checkboxes):
            state = ui.row_checkboxes[idx].get()
            print(f"  {player}: {'CHECKED' if state else 'UNCHECKED'}")
    
    print("\n" + "=" * 70)
    print("TEST VALIDATION:")
    print("=" * 70)
    
    # Validate expected results
    justin_idx = friendly_players.index("Justin") if "Justin" in friendly_players else -1
    mike_idx = friendly_players.index("Mike") if "Mike" in friendly_players else -1
    rick_idx = friendly_players.index("Rick") if "Rick" in friendly_players else -1
    
    test_passed = True
    
    if justin_idx >= 0:
        justin_checked = ui.row_checkboxes[justin_idx].get()
        if justin_checked:
            print("✓ PASS: Justin's checkbox is checked")
        else:
            print("✗ FAIL: Justin's checkbox should be checked but isn't")
            test_passed = False
    
    if mike_idx >= 0:
        mike_checked = ui.row_checkboxes[mike_idx].get()
        if not mike_checked:
            print("✓ PASS: Mike's checkbox is unchecked")
        else:
            print("✗ FAIL: Mike's checkbox should be unchecked but is checked")
            test_passed = False
    
    if rick_idx >= 0:
        rick_checked = ui.row_checkboxes[rick_idx].get()
        if not rick_checked:
            print("✓ PASS: Rick's checkbox is unchecked")
        else:
            print("✗ FAIL: Rick's checkbox should be unchecked but is checked")
            test_passed = False
    
    print("\n" + "=" * 70)
    if test_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 70)
    
    # Keep window open
    print("\nTest complete. Close the window to exit.")
    
    # Schedule test to run after UI loads
    ui.root.after(2000, run_test_steps)
    ui.root.mainloop()

if __name__ == "__main__":
    run_test()
