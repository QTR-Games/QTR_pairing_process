#!/usr/bin/env python3
"""Quick test to verify OR clause parsing in tree nodes."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'qtr_pairing_process'))

from qtr_pairing_process.matchup_tree_sync import MatchupTreeSynchronizer

class MockUIManager:
    """Minimal mock for testing."""
    def __init__(self):
        self.treeview = None
        self.selected_players_per_round = {}

def test_or_parsing():
    """Test that OR clauses are properly extracted."""
    ui_manager = MockUIManager()
    sync = MatchupTreeSynchronizer(ui_manager, auto_sync_enabled=True)

    # We're only testing the parsing method, not the full sync, so tree_widget being None is OK

    # Test case 1: Simple OR clause
    text1 = "Bokur vs FLO (3/5) OR GORKUL (3/5)"
    result1 = sync._parse_matchup_from_text(text1, round_num=1)

    print("Test 1: Simple OR clause")
    print(f"Input: {text1}")
    print(f"Result: {result1}")

    # Verify extraction
    assert result1 is not None, "Failed to parse matchup"
    assert result1['player1'] == 'Bokur', f"Expected player1='Bokur', got '{result1['player1']}'"
    assert result1['player2'] == 'FLO', f"Expected player2='FLO', got '{result1['player2']}'"
    assert result1.get('player3') == 'GORKUL', f"Expected player3='GORKUL', got '{result1.get('player3')}'"
    print("Test 1 PASSED\n")

    # Test case 2: OR with different ratings
    text2 = "FLO vs Dan (4/5) OR Jack (4/5)"
    result2 = sync._parse_matchup_from_text(text2, round_num=2)

    print("Test 2: OR with different ratings")
    print(f"Input: {text2}")
    print(f"Result: {result2}")

    assert result2 is not None, "Failed to parse matchup"
    assert result2['player1'] == 'FLO', f"Expected player1='FLO', got '{result2['player1']}'"
    assert result2['player2'] == 'Dan', f"Expected player2='Dan', got '{result2['player2']}'"
    assert result2.get('player3') == 'Jack', f"Expected player3='Jack', got '{result2.get('player3')}'"
    print("Test 2 PASSED\n")

    # Test case 3: No OR clause (standard matchup)
    text3 = "Pete vs Opponent3 (4/5)"
    result3 = sync._parse_matchup_from_text(text3, round_num=1)

    print("Test 3: Standard matchup (no OR)")
    print(f"Input: {text3}")
    print(f"Result: {result3}")

    assert result3 is not None, "Failed to parse matchup"
    assert result3['player1'] == 'Pete', f"Expected player1='Pete', got '{result3['player1']}'"
    assert result3['player2'] == 'Opponent3', f"Expected player2='Opponent3', got '{result3['player2']}'"
    assert result3.get('player3') is None, f"Expected no player3, got '{result3.get('player3')}'"
    print("Test 3 PASSED\n")

    print("=" * 60)
    print("ALL OR PARSING TESTS PASSED")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_or_parsing()
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
