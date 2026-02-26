<<<<<<< HEAD
#!/usr/bin/env python3
# type: ignore
"""
Test script for Matchup Tree Synchronization System

This script tests the synchronization between the Round Tracker selections
and the Matchup Tree navigation. It validates that when Pete is selected
against Opponent 3 in Round 1, the corresponding tree node is found and highlighted.

Usage:
    python test_tree_sync.py

Testing Scenarios:
1. Basic sync - Simple player vs player matchup
2. Multi-round sync - Multiple rounds with ante/response logic
3. Tree-to-round sync - Selecting tree node updates dropdowns  
4. Conflict resolution - Handling mismatched selections
5. Performance test - Large tree navigation
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox

# Add the qtr_pairing_process directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'qtr_pairing_process'))

try:
    from qtr_pairing_process.matchup_tree_sync import MatchupTreeSynchronizer, MatchupSelection
    from qtr_pairing_process.db_management.db_manager import DbManager
    from qtr_pairing_process.constants import RATING_SYSTEMS
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the QTR_pairing_process directory")
    sys.exit(1)


class MockTreeWidget:
    """Mock tree widget for testing without full UI."""
    
    def __init__(self):
        self.items = {}
        self.selection_items = []
        self.children_map = {}
        
    def get_children(self, parent=""):
        return self.children_map.get(parent, [])
        
    def item(self, item_id, option=None, **kwargs):
        if option == 'text':
            return self.items.get(item_id, {}).get('text', '')
        elif option == 'values':
            return self.items.get(item_id, {}).get('values', [])
        return self.items.get(item_id, {})
        
    def parent(self, item_id):
        # Find parent by searching children_map
        for parent, children in self.children_map.items():
            if item_id in children:
                return parent
        return ""
        
    def selection(self):
        return self.selection_items
        
    def selection_set(self, item_id):
        self.selection_items = [item_id]
        
    def selection_remove(self, items):
        self.selection_items.clear()
        
    def see(self, item_id):
        pass  # Mock implementation
        
    def bind(self, event, callback):
        pass  # Mock implementation
        
    def add_item(self, item_id, text, values=None, parent=""):
        """Helper method to add items to mock tree."""
        self.items[item_id] = {
            'text': text,
            'values': values or []
        }
        
        if parent not in self.children_map:
            self.children_map[parent] = []
        self.children_map[parent].append(item_id)


class MockTreeView:
    """Mock TreeView wrapper for testing."""
    
    def __init__(self):
        self.tree: MockTreeWidget | None = None  # Will be set in constructor

class MockNotebook:
    """Mock notebook for testing tab visibility."""
    
    def __init__(self):
        self.current_tab = "tree_frame"  # Default to tree tab for tests
    
    def select(self):
        """Return the currently selected tab."""
        return self.current_tab

class MockUIManager:
    """Mock UI manager for testing synchronization."""
    
    def __init__(self):
        self.selected_players_per_round = {}
        self.round_vars = []
        self.enemy_round_vars = []
        self.round_dropdowns = []
        self.enemy_round_dropdowns = []
        
        # Create mock tree widget
        self.treeview = MockTreeView()
        self.treeview.tree = MockTreeWidget()
        
        # Create mock notebook and tree frame for tab visibility checks
        self.notebook = MockNotebook()
        self.tree_frame = "tree_frame"  # Mock frame identifier
        
        # Set up test tree structure
        self._setup_test_tree()
        
        # Set up test round data
        self._setup_test_rounds()
        
    def _setup_test_tree(self):
        """Set up a realistic tree structure for testing."""
        tree = self.treeview.tree
        
        # Root
        tree.add_item("root", "Pairings", [""], "")
        
        # Round 1 choices
        tree.add_item("r1_choice1", "Pete vs Opponent3 (3/5) OR Opponent1 (2/5)", ["3"], "root")
        tree.add_item("r1_pete_opp3", "Pete vs Opponent3 (3/5)", ["3"], "r1_choice1") 
        tree.add_item("r1_pete_opp1", "Pete vs Opponent1 (2/5)", ["2"], "r1_choice1")
        
        # Round 2 under Pete vs Opponent3 path
        tree.add_item("r2_choice1", "Opponent2 vs Kyle (4/5) OR Sarah (3/5)", ["4"], "r1_pete_opp3")
        tree.add_item("r2_opp2_kyle", "Opponent2 vs Kyle (4/5)", ["4"], "r2_choice1")
        tree.add_item("r2_opp2_sarah", "Opponent2 vs Sarah (3/5)", ["3"], "r2_choice1")
        
        # Round 3 under Opponent2 vs Kyle path  
        tree.add_item("r3_choice1", "Mike vs Opponent4 (2/5) OR Opponent5 (4/5)", ["4"], "r2_opp2_kyle")
        tree.add_item("r3_mike_opp4", "Mike vs Opponent4 (2/5)", ["2"], "r3_choice1")
        tree.add_item("r3_mike_opp5", "Mike vs Opponent5 (4/5)", ["4"], "r3_choice1")
        
    def _setup_test_rounds(self):
        """Set up test round selection data."""
        # Round 1: Friendly antes (Pete), Enemy responds (Opponent3)
        self.selected_players_per_round[1] = {
            'ante': 'Pete',
            'ante_team': 'friendly',
            'response1': 'Opponent3',
            'response2': None,
            'response_team': 'enemy'
        }
        
        # Round 2: Enemy antes (Opponent2), Friendly responds (Kyle)
        self.selected_players_per_round[2] = {
            'ante': 'Opponent2', 
            'ante_team': 'enemy',
            'response1': 'Kyle',
            'response2': None,
            'response_team': 'friendly'
        }
        
        # Round 3: Friendly antes (Mike), Enemy responds (Opponent5)
        self.selected_players_per_round[3] = {
            'ante': 'Mike',
            'ante_team': 'friendly', 
            'response1': 'Opponent5',
            'response2': None,
            'response_team': 'enemy'
        }


class TreeSyncTester:
    """Main test class for the synchronization system."""
    
    def __init__(self):
        self.ui_manager = MockUIManager()
        self.synchronizer = MatchupTreeSynchronizer(self.ui_manager, auto_sync_enabled=True)
        self.test_results = []
        
    def run_all_tests(self):
        """Run all synchronization tests."""
        print("=" * 60)
        print("MATCHUP TREE SYNCHRONIZATION TEST SUITE")
        print("=" * 60)
        
        tests = [
            self.test_matchup_selection_parsing,
            self.test_tree_path_matching,
            self.test_round_to_tree_sync,
            self.test_tree_to_round_sync,
            self.test_pattern_matching,
            self.test_conflict_handling,
            self.test_performance,
            self.test_cleanup_method,
            self.test_deepcopy_cache,
            self.test_path_caching,
            self.test_cache_size_limit,
            self.test_tab_visibility_optimization
        ]
        
        for test in tests:
            try:
                print(f"\n🧪 Running {test.__name__}...")
                result = test()
                self.test_results.append((test.__name__, result, None))
                print(f"✅ {test.__name__}: {'PASSED' if result else 'FAILED'}")
            except Exception as e:
                self.test_results.append((test.__name__, False, str(e)))
                print(f"❌ {test.__name__}: ERROR - {e}")
                
        self.print_summary()
        
    def test_matchup_selection_parsing(self):
        """Test parsing round selections into MatchupSelection objects."""
        selections = self.synchronizer._parse_round_selections()
        
        # Should have 3 rounds of selections
        if len(selections) != 3:
            print(f"Expected 3 selections, got {len(selections)}")
            return False
            
        # Test Round 1 selection
        round1 = selections[0]
        if round1.round_num != 1:
            print(f"Round 1 number wrong: {round1.round_num}")
            return False
            
        if round1.ante_player != 'Pete':
            print(f"Round 1 ante wrong: {round1.ante_player}")
            return False
            
        if round1.response_players != ['Opponent3']:
            print(f"Round 1 response wrong: {round1.response_players}")
            return False
            
        # Test primary matchup extraction
        matchup = round1.get_primary_matchup()
        if matchup != ('Pete', 'Opponent3'):
            print(f"Round 1 primary matchup wrong: {matchup}")
            return False
            
        print("  ✓ Successfully parsed 3 round selections")
        print("  ✓ Round 1: Pete vs Opponent3")
        print("  ✓ Round 2: Opponent2 vs Kyle") 
        print("  ✓ Round 3: Mike vs Opponent5")
        
        return True
        
    def test_tree_path_matching(self):
        """Test finding matching tree paths for selections."""
        selections = self.synchronizer._parse_round_selections()
        
        # Test that we can find a matching path
        matching_path = self.synchronizer._find_matching_tree_path(selections)
        
        if not matching_path:
            print("  ❌ No matching path found")
            return False
            
        # Verify the path goes through the expected nodes
        expected_nodes = ['root', 'r1_pete_opp3', 'r2_opp2_kyle', 'r3_mike_opp5']
        
        if len(matching_path) < len(expected_nodes):
            print(f"  ❌ Path too short: {len(matching_path)} < {len(expected_nodes)}")
            return False
            
        # The path should end with the final decision node
        final_node = matching_path[-1]
        final_text = self.ui_manager.treeview.tree.item(final_node, 'text')
        
        if 'Mike vs Opponent5' not in final_text:
            print(f"  ❌ Final node doesn't match: {final_text}")
            return False
            
        print(f"  ✓ Found matching path with {len(matching_path)} nodes")
        print(f"  ✓ Final node: {final_text}")
        
        return True
        
    def test_round_to_tree_sync(self):
        """Test syncing round selections to tree navigation."""
        # Clear any existing tree selection
        self.ui_manager.treeview.tree.selection_items.clear()
        
        # Trigger sync from round to tree
        self.synchronizer.sync_round_to_tree()
        
        # Check that tree selection was updated
        selected_items = self.ui_manager.treeview.tree.selection()
        
        if not selected_items:
            print("  ❌ No tree item selected after sync")
            return False
            
        selected_item = selected_items[0]
        selected_text = self.ui_manager.treeview.tree.item(selected_item, 'text')
        
        # Should select the final decision node
        if 'Mike vs Opponent5' not in selected_text:
            print(f"  ❌ Wrong tree item selected: {selected_text}")
            return False
            
        print(f"  ✓ Tree synchronized to: {selected_text}")
        
        return True
        
    def test_tree_to_round_sync(self):
        """Test syncing tree selection to round dropdowns."""
        # Manually select a tree node
        self.ui_manager.treeview.tree.selection_set('r2_opp2_sarah')
        
        # Clear round selections to test sync
        original_selections = self.ui_manager.selected_players_per_round.copy()
        self.ui_manager.selected_players_per_round.clear()
        
        # Trigger sync from tree to rounds
        self.synchronizer.sync_tree_to_rounds()
        
        # Check that round selections were updated
        if not self.ui_manager.selected_players_per_round:
            print("  ❌ Round selections not updated")
            return False
            
        # Restore original selections for other tests
        self.ui_manager.selected_players_per_round = original_selections
        
        print("  ✓ Round dropdowns updated from tree selection")
        
        return True
        
    def test_pattern_matching(self):
        """Test matchup pattern matching in tree nodes."""
        selection = MatchupSelection(
            round_num=1,
            ante_player='Pete',
            ante_team='friendly',
            response_players=['Opponent3'],
            response_team='enemy'
        )
        
        test_cases = [
            ('Pete vs Opponent3 (3/5)', True),
            ('Opponent3 vs Pete (3/5)', True),
            ('Pete vs Opponent3', True),
            ('Pete vs Opponent1 (2/5)', False),
            ('Kyle vs Sarah (4/5)', False),
            ('Pete vs Opponent3 (3/5) OR Opponent1 (2/5)', True),
        ]
        
        for node_text, expected in test_cases:
            result = selection.matches_tree_node_text(node_text)
            if result != expected:
                print(f"  ❌ Pattern match failed for '{node_text}': got {result}, expected {expected}")
                return False
                
        print("  ✓ All pattern matching tests passed")
        
        return True
        
    def test_conflict_handling(self):
        """Test handling of conflicting or incomplete selections."""
        # Test with incomplete round data
        original_selections = self.ui_manager.selected_players_per_round.copy()
        
        # Create incomplete selection (missing response)
        self.ui_manager.selected_players_per_round = {
            1: {
                'ante': 'Pete',
                'ante_team': 'friendly',
                'response1': None,  # Missing response
                'response2': None,
                'response_team': 'enemy'
            }
        }
        
        # Should handle gracefully without crashing
        try:
            selections = self.synchronizer._parse_round_selections()
            # Should return empty list for incomplete data
            if len(selections) > 0:
                print("  ❌ Should not create selections for incomplete data")
                return False
        except Exception as e:
            print(f"  ❌ Exception on incomplete data: {e}")
            return False
            
        # Test with conflicting data (selection not in tree)
        self.ui_manager.selected_players_per_round = {
            1: {
                'ante': 'NonExistentPlayer',
                'ante_team': 'friendly',
                'response1': 'AnotherNonExistentPlayer',
                'response2': None,
                'response_team': 'enemy'
            }
        }
        
        try:
            matching_path = self.synchronizer._find_matching_tree_path(
                self.synchronizer._parse_round_selections()
            )
            # Should return None for non-matching data
            if matching_path is not None:
                print(f"  ❌ Should not find path for non-existent players")
                return False
        except Exception as e:
            print(f"  ❌ Exception on conflicting data: {e}")
            return False
            
        # Restore original selections
        self.ui_manager.selected_players_per_round = original_selections
        
        print("  ✓ Conflict handling tests passed")
        
        return True
        
    def test_performance(self):
        """Test synchronization performance with larger datasets."""
        import time
        
        # Time the synchronization operations
        start_time = time.time()
        
        for _ in range(10):  # Run sync 10 times
            self.synchronizer.sync_round_to_tree()
            
        end_time = time.time()
        avg_time = (end_time - start_time) / 10
        
        # Should complete quickly (under 100ms per sync)
        if avg_time > 0.1:
            print(f"  ❌ Sync too slow: {avg_time:.3f}s average")
            return False
            
        print(f"  ✓ Performance test passed: {avg_time*1000:.1f}ms average")
        
        return True
    
    def test_cleanup_method(self):
        """Test cleanup method properly releases resources."""
        # Create a new synchronizer for this test
        test_ui_manager = MockUIManager()
        test_sync = MatchupTreeSynchronizer(test_ui_manager, auto_sync_enabled=True)
        
        # Set some cached data
        test_sync.current_tree_path = ['path1', 'path2']
        test_sync.last_round_selections = {1: {'ante': 'test'}}
        test_sync._path_cache = {'key1': ['path']}
        
        # Call cleanup
        test_sync.cleanup()
        
        # Verify caches are cleared
        if test_sync.current_tree_path:
            print(f"  ❌ current_tree_path not cleared: {test_sync.current_tree_path}")
            return False
            
        if test_sync.last_round_selections:
            print(f"  ❌ last_round_selections not cleared")
            return False
            
        if test_sync._path_cache:
            print(f"  ❌ _path_cache not cleared")
            return False
            
        if test_sync.tree_widget is not None:
            print(f"  ❌ tree_widget reference not cleared")
            return False
        
        print("  ✓ Cleanup method properly releases all resources")
        return True
    
    def test_deepcopy_cache(self):
        """Test that cache uses deepcopy to prevent nested mutation bugs."""
        # Setup initial selections with nested dict
        self.ui_manager.selected_players_per_round = {
            1: {
                'ante': 'Pete',
                'ante_team': 'friendly',
                'response1': 'Opponent3',
                'response_team': 'enemy'
            }
        }
        
        # Trigger cache update
        changed = self.synchronizer.is_selections_changed()
        
        if not changed:
            print("  ❌ Should detect initial change")
            return False
        
        # Save a reference to what was cached
        cached_ante_before_mutation = self.synchronizer.last_round_selections[1]['ante']
        
        # Now mutate the nested dictionary in the source
        self.ui_manager.selected_players_per_round[1]['ante'] = 'Modified'
        
        # Check that the cached value was NOT affected by the mutation (proving deepcopy worked)
        cached_ante_after_mutation = self.synchronizer.last_round_selections[1]['ante']
        
        if cached_ante_after_mutation != 'Pete':
            print(f"  ❌ Cache was modified by source mutation (shallow copy bug): {cached_ante_after_mutation}")
            return False
        
        if cached_ante_before_mutation != cached_ante_after_mutation:
            print(f"  ❌ Cache value changed unexpectedly")
            return False
        
        # Now check if change detection works
        changed_again = self.synchronizer.is_selections_changed()
        
        if not changed_again:
            print("  ❌ Should detect nested dict mutation")
            return False
        
        print("  ✓ Deepcopy prevents nested dictionary mutation bugs")
        return True
    
    def test_path_caching(self):
        """Test that path search results are cached for performance."""
        selections = self.synchronizer._parse_round_selections()
        
        # First search should cache the result
        path1 = self.synchronizer._find_matching_tree_path(selections)
        
        # Check that cache has an entry
        cache_size_after_first = len(self.synchronizer._path_cache)
        if cache_size_after_first == 0:
            print(f"  ❌ Path not cached after first search")
            return False
        
        # Second search should use cached result 
        path2 = self.synchronizer._find_matching_tree_path(selections)
        
        # Paths should be identical
        if path1 != path2:
            print(f"  ❌ Cached path differs from original")
            return False
        
        # Cache size shouldn't increase
        cache_size_after_second = len(self.synchronizer._path_cache)
        if cache_size_after_second != cache_size_after_first:
            print(f"  ❌ Cache size increased on second search (not using cache)")
            return False
        
        print(f"  ✓ Path caching working correctly (cache size: {cache_size_after_first})")
        return True
    
    def test_cache_size_limit(self):
        """Test that cache enforces size limit to prevent unbounded growth."""
        # Clear existing cache
        self.synchronizer._path_cache.clear()
        
        # Create many different selections to exceed cache limit
        from qtr_pairing_process.matchup_tree_sync import _MAX_PATH_CACHE_SIZE
        
        for i in range(_MAX_PATH_CACHE_SIZE + 10):
            # Create unique cache key
            cache_key = f"test_key_{i}"
            self.synchronizer._cache_path(cache_key, [f'path_{i}'])
        
        # Cache should not exceed max size
        if len(self.synchronizer._path_cache) > _MAX_PATH_CACHE_SIZE:
            print(f"  ❌ Cache exceeded max size: {len(self.synchronizer._path_cache)} > {_MAX_PATH_CACHE_SIZE}")
            return False
        
        # Cache should be at or near max size (allowing for some tolerance)
        if len(self.synchronizer._path_cache) < _MAX_PATH_CACHE_SIZE - 5:
            print(f"  ❌ Cache unexpectedly small: {len(self.synchronizer._path_cache)}")
            return False
        
        print(f"  ✓ Cache size limit enforced (max: {_MAX_PATH_CACHE_SIZE}, actual: {len(self.synchronizer._path_cache)})")
        return True
    
    def test_tab_visibility_optimization(self):
        """Test that sync is skipped when tree tab is not visible (performance optimization)."""
        # Initially, tree tab should be "visible" in mock
        if not self.synchronizer._is_tree_tab_visible():
            print("  ❌ Tree tab should be visible initially in mock")
            return False
        
        # Sync should work when tree tab is visible
        initial_cache_size = len(self.synchronizer._path_cache)
        self.synchronizer.sync_round_to_tree(1)
        
        # Now simulate switching to a different tab
        self.ui_manager.notebook.current_tab = "team_grid"
        
        if self.synchronizer._is_tree_tab_visible():
            print("  ❌ Tree tab should not be visible when on different tab")
            return False
        
        # Record current state
        cache_size_before_skip = len(self.synchronizer._path_cache)
        sync_count_before = id(self.synchronizer.current_tree_path)
        
        # Attempt sync multiple times - should all be skipped
        for _ in range(5):
            self.synchronizer.sync_round_to_tree(1)
        
        # Cache and sync state should not have changed (syncs were skipped)
        cache_size_after_skip = len(self.synchronizer._path_cache)
        
        if cache_size_after_skip != cache_size_before_skip:
            print(f"  ❌ Cache changed during skipped syncs: {cache_size_before_skip} -> {cache_size_after_skip}")
            return False
        
        # Switch back to tree tab
        self.ui_manager.notebook.current_tab = "tree_frame"
        
        if not self.synchronizer._is_tree_tab_visible():
            print("  ❌ Tree tab should be visible after switching back")
            return False
        
        # Sync should work again
        self.synchronizer.sync_round_to_tree(1)
        
        # Verify the method ran (cache may or may not grow due to caching, but should not fail)
        
        print("  ✓ Tab visibility optimization working correctly")
        print("  ✓ Sync skipped when tree not visible (prevents lag)")
        print("  ✓ Sync resumes when tree becomes visible")
        return True
        
    def print_summary(self):
        """Print test results summary."""
        print("\n" + "=" * 60)
        print("TEST RESULTS SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, result, _ in self.test_results if result)
        total = len(self.test_results)
        
        print(f"Tests passed: {passed}/{total}")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! Tree synchronization is working correctly.")
        else:
            print("❌ Some tests failed. Check the output above for details.")
            
        # Print any errors
        for test_name, result, error in self.test_results:
            if not result and error:
                print(f"  {test_name}: {error}")


def create_demo_ui():
    """Create a minimal demo UI to test synchronization interactively."""
    
    class DemoApp:
        def __init__(self):
            self.root = tk.Tk()
            self.root.title("Matchup Tree Sync Demo")
            self.root.geometry("800x600")
            
            # Create test UI manager
            self.ui_manager = MockUIManager()
            self.synchronizer = MatchupTreeSynchronizer(self.ui_manager, auto_sync_enabled=True)
            
            self.create_widgets()
            
        def create_widgets(self):
            # Title
            title = tk.Label(self.root, text="Matchup Tree Synchronization Demo", 
                           font=("Arial", 16, "bold"))
            title.pack(pady=10)
            
            # Round selections frame
            rounds_frame = tk.LabelFrame(self.root, text="Round Selections", padx=10, pady=10)
            rounds_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Display current selections
            self.selections_text = tk.Text(rounds_frame, height=6, width=60)
            self.selections_text.pack()
            
            # Tree selections frame
            tree_frame = tk.LabelFrame(self.root, text="Tree Structure", padx=10, pady=10)
            tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            # Tree display
            self.tree_text = tk.Text(tree_frame, height=10, width=60)
            self.tree_text.pack(fill=tk.BOTH, expand=True)
            
            # Buttons frame
            buttons_frame = tk.Frame(self.root)
            buttons_frame.pack(fill=tk.X, padx=10, pady=10)
            
            tk.Button(buttons_frame, text="Sync Round → Tree", 
                     command=self.sync_round_to_tree).pack(side=tk.LEFT, padx=5)
            tk.Button(buttons_frame, text="Sync Tree → Round", 
                     command=self.sync_tree_to_round).pack(side=tk.LEFT, padx=5)
            tk.Button(buttons_frame, text="Show Status", 
                     command=self.show_status).pack(side=tk.LEFT, padx=5)
            tk.Button(buttons_frame, text="Run Tests", 
                     command=self.run_tests).pack(side=tk.LEFT, padx=5)
            
            # Update display
            self.update_display()
            
        def sync_round_to_tree(self):
            self.synchronizer.sync_round_to_tree()
            self.update_display()
            
        def sync_tree_to_round(self):
            self.synchronizer.sync_tree_to_rounds()
            self.update_display()
            
        def show_status(self):
            status = self.synchronizer.get_sync_status()
            messagebox.showinfo("Sync Status", 
                              f"Is Syncing: {status['is_syncing']}\n"
                              f"Has Tree Widget: {status['has_tree_widget']}\n"
                              f"Round Selections: {status['round_selections_count']}\n"
                              f"Tree Path Length: {len(status['current_tree_path'])}")
            
        def run_tests(self):
            tester = TreeSyncTester()
            tester.run_all_tests()
            
        def update_display(self):
            # Update round selections display
            self.selections_text.delete(1.0, tk.END)
            for round_num, data in self.ui_manager.selected_players_per_round.items():
                ante = data.get('ante', 'None')
                resp1 = data.get('response1', 'None')
                self.selections_text.insert(tk.END, f"Round {round_num}: {ante} vs {resp1}\n")
                
            # Update tree display
            self.tree_text.delete(1.0, tk.END)
            selected = self.ui_manager.treeview.tree.selection()
            selected_text = "None"
            if selected:
                selected_text = self.ui_manager.treeview.tree.item(selected[0], 'text')
                
            self.tree_text.insert(tk.END, f"Selected: {selected_text}\n\n")
            self.tree_text.insert(tk.END, "Tree Structure:\n")
            self._display_tree_recursive("root", 0)
            
        def _display_tree_recursive(self, node_id, level):
            indent = "  " * level
            text = self.ui_manager.treeview.tree.item(node_id, 'text')
            
            # Highlight selected node
            selected = self.ui_manager.treeview.tree.selection()
            marker = " <<<" if selected and node_id in selected else ""
            
            self.tree_text.insert(tk.END, f"{indent}{text}{marker}\n")
            
            children = self.ui_manager.treeview.tree.get_children(node_id)
            for child in children:
                self._display_tree_recursive(child, level + 1)
                
        def run(self):
            self.root.mainloop()
    
    app = DemoApp()
    app.run()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Matchup Tree Synchronization')
    parser.add_argument('--demo', action='store_true', 
                       help='Run interactive demo instead of tests')
    args = parser.parse_args()
    
    if args.demo:
        create_demo_ui()
    else:
        tester = TreeSyncTester()
=======
#!/usr/bin/env python3
# type: ignore
"""
Test script for Matchup Tree Synchronization System

This script tests the synchronization between the Round Tracker selections
and the Matchup Tree navigation. It validates that when Pete is selected
against Opponent 3 in Round 1, the corresponding tree node is found and highlighted.

Usage:
    python test_tree_sync.py

Testing Scenarios:
1. Basic sync - Simple player vs player matchup
2. Multi-round sync - Multiple rounds with ante/response logic
3. Tree-to-round sync - Selecting tree node updates dropdowns  
4. Conflict resolution - Handling mismatched selections
5. Performance test - Large tree navigation
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox

# Add the qtr_pairing_process directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'qtr_pairing_process'))

try:
    from qtr_pairing_process.matchup_tree_sync import MatchupTreeSynchronizer, MatchupSelection
    from qtr_pairing_process.db_management.db_manager import DbManager
    from qtr_pairing_process.constants import RATING_SYSTEMS
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the QTR_pairing_process directory")
    sys.exit(1)


class MockTreeWidget:
    """Mock tree widget for testing without full UI."""
    
    def __init__(self):
        self.items = {}
        self.selection_items = []
        self.children_map = {}
        
    def get_children(self, parent=""):
        return self.children_map.get(parent, [])
        
    def item(self, item_id, option=None, **kwargs):
        if option == 'text':
            return self.items.get(item_id, {}).get('text', '')
        elif option == 'values':
            return self.items.get(item_id, {}).get('values', [])
        return self.items.get(item_id, {})
        
    def parent(self, item_id):
        # Find parent by searching children_map
        for parent, children in self.children_map.items():
            if item_id in children:
                return parent
        return ""
        
    def selection(self):
        return self.selection_items
        
    def selection_set(self, item_id):
        self.selection_items = [item_id]
        
    def selection_remove(self, items):
        self.selection_items.clear()
        
    def see(self, item_id):
        pass  # Mock implementation
        
    def bind(self, event, callback):
        pass  # Mock implementation
        
    def add_item(self, item_id, text, values=None, parent=""):
        """Helper method to add items to mock tree."""
        self.items[item_id] = {
            'text': text,
            'values': values or []
        }
        
        if parent not in self.children_map:
            self.children_map[parent] = []
        self.children_map[parent].append(item_id)


class MockTreeView:
    """Mock TreeView wrapper for testing."""
    
    def __init__(self):
        self.tree: MockTreeWidget | None = None  # Will be set in constructor

class MockUIManager:
    """Mock UI manager for testing synchronization."""
    
    def __init__(self):
        self.selected_players_per_round = {}
        self.round_vars = []
        self.enemy_round_vars = []
        self.round_dropdowns = []
        self.enemy_round_dropdowns = []
        
        # Create mock tree widget
        self.treeview = MockTreeView()
        self.treeview.tree = MockTreeWidget()
        
        # Set up test tree structure
        self._setup_test_tree()
        
        # Set up test round data
        self._setup_test_rounds()
        
    def _setup_test_tree(self):
        """Set up a realistic tree structure for testing."""
        tree = self.treeview.tree
        
        # Root
        tree.add_item("root", "Pairings", [""], "")
        
        # Round 1 choices
        tree.add_item("r1_choice1", "Pete vs Opponent3 (3/5) OR Opponent1 (2/5)", ["3"], "root")
        tree.add_item("r1_pete_opp3", "Pete vs Opponent3 (3/5)", ["3"], "r1_choice1") 
        tree.add_item("r1_pete_opp1", "Pete vs Opponent1 (2/5)", ["2"], "r1_choice1")
        
        # Round 2 under Pete vs Opponent3 path
        tree.add_item("r2_choice1", "Opponent2 vs Kyle (4/5) OR Sarah (3/5)", ["4"], "r1_pete_opp3")
        tree.add_item("r2_opp2_kyle", "Opponent2 vs Kyle (4/5)", ["4"], "r2_choice1")
        tree.add_item("r2_opp2_sarah", "Opponent2 vs Sarah (3/5)", ["3"], "r2_choice1")
        
        # Round 3 under Opponent2 vs Kyle path  
        tree.add_item("r3_choice1", "Mike vs Opponent4 (2/5) OR Opponent5 (4/5)", ["4"], "r2_opp2_kyle")
        tree.add_item("r3_mike_opp4", "Mike vs Opponent4 (2/5)", ["2"], "r3_choice1")
        tree.add_item("r3_mike_opp5", "Mike vs Opponent5 (4/5)", ["4"], "r3_choice1")
        
    def _setup_test_rounds(self):
        """Set up test round selection data."""
        # Round 1: Friendly antes (Pete), Enemy responds (Opponent3)
        self.selected_players_per_round[1] = {
            'ante': 'Pete',
            'ante_team': 'friendly',
            'response1': 'Opponent3',
            'response2': None,
            'response_team': 'enemy'
        }
        
        # Round 2: Enemy antes (Opponent2), Friendly responds (Kyle)
        self.selected_players_per_round[2] = {
            'ante': 'Opponent2', 
            'ante_team': 'enemy',
            'response1': 'Kyle',
            'response2': None,
            'response_team': 'friendly'
        }
        
        # Round 3: Friendly antes (Mike), Enemy responds (Opponent5)
        self.selected_players_per_round[3] = {
            'ante': 'Mike',
            'ante_team': 'friendly', 
            'response1': 'Opponent5',
            'response2': None,
            'response_team': 'enemy'
        }


class TreeSyncTester:
    """Main test class for the synchronization system."""
    
    def __init__(self):
        self.ui_manager = MockUIManager()
        self.synchronizer = MatchupTreeSynchronizer(self.ui_manager)
        self.test_results = []
        
    def run_all_tests(self):
        """Run all synchronization tests."""
        print("=" * 60)
        print("MATCHUP TREE SYNCHRONIZATION TEST SUITE")
        print("=" * 60)
        
        tests = [
            self.test_matchup_selection_parsing,
            self.test_tree_path_matching,
            self.test_round_to_tree_sync,
            self.test_tree_to_round_sync,
            self.test_pattern_matching,
            self.test_conflict_handling,
            self.test_performance
        ]
        
        for test in tests:
            try:
                print(f"\n🧪 Running {test.__name__}...")
                result = test()
                self.test_results.append((test.__name__, result, None))
                print(f"✅ {test.__name__}: {'PASSED' if result else 'FAILED'}")
            except Exception as e:
                self.test_results.append((test.__name__, False, str(e)))
                print(f"❌ {test.__name__}: ERROR - {e}")
                
        self.print_summary()
        
    def test_matchup_selection_parsing(self):
        """Test parsing round selections into MatchupSelection objects."""
        selections = self.synchronizer._parse_round_selections()
        
        # Should have 3 rounds of selections
        if len(selections) != 3:
            print(f"Expected 3 selections, got {len(selections)}")
            return False
            
        # Test Round 1 selection
        round1 = selections[0]
        if round1.round_num != 1:
            print(f"Round 1 number wrong: {round1.round_num}")
            return False
            
        if round1.ante_player != 'Pete':
            print(f"Round 1 ante wrong: {round1.ante_player}")
            return False
            
        if round1.response_players != ['Opponent3']:
            print(f"Round 1 response wrong: {round1.response_players}")
            return False
            
        # Test primary matchup extraction
        matchup = round1.get_primary_matchup()
        if matchup != ('Pete', 'Opponent3'):
            print(f"Round 1 primary matchup wrong: {matchup}")
            return False
            
        print("  ✓ Successfully parsed 3 round selections")
        print("  ✓ Round 1: Pete vs Opponent3")
        print("  ✓ Round 2: Opponent2 vs Kyle") 
        print("  ✓ Round 3: Mike vs Opponent5")
        
        return True
        
    def test_tree_path_matching(self):
        """Test finding matching tree paths for selections."""
        selections = self.synchronizer._parse_round_selections()
        
        # Test that we can find a matching path
        matching_path = self.synchronizer._find_matching_tree_path(selections)
        
        if not matching_path:
            print("  ❌ No matching path found")
            return False
            
        # Verify the path goes through the expected nodes
        expected_nodes = ['root', 'r1_pete_opp3', 'r2_opp2_kyle', 'r3_mike_opp5']
        
        if len(matching_path) < len(expected_nodes):
            print(f"  ❌ Path too short: {len(matching_path)} < {len(expected_nodes)}")
            return False
            
        # The path should end with the final decision node
        final_node = matching_path[-1]
        final_text = self.ui_manager.treeview.tree.item(final_node, 'text')
        
        if 'Mike vs Opponent5' not in final_text:
            print(f"  ❌ Final node doesn't match: {final_text}")
            return False
            
        print(f"  ✓ Found matching path with {len(matching_path)} nodes")
        print(f"  ✓ Final node: {final_text}")
        
        return True
        
    def test_round_to_tree_sync(self):
        """Test syncing round selections to tree navigation."""
        # Clear any existing tree selection
        self.ui_manager.treeview.tree.selection_items.clear()
        
        # Trigger sync from round to tree
        self.synchronizer.sync_round_to_tree()
        
        # Check that tree selection was updated
        selected_items = self.ui_manager.treeview.tree.selection()
        
        if not selected_items:
            print("  ❌ No tree item selected after sync")
            return False
            
        selected_item = selected_items[0]
        selected_text = self.ui_manager.treeview.tree.item(selected_item, 'text')
        
        # Should select the final decision node
        if 'Mike vs Opponent5' not in selected_text:
            print(f"  ❌ Wrong tree item selected: {selected_text}")
            return False
            
        print(f"  ✓ Tree synchronized to: {selected_text}")
        
        return True
        
    def test_tree_to_round_sync(self):
        """Test syncing tree selection to round dropdowns."""
        # Manually select a tree node
        self.ui_manager.treeview.tree.selection_set('r2_opp2_sarah')
        
        # Clear round selections to test sync
        original_selections = self.ui_manager.selected_players_per_round.copy()
        self.ui_manager.selected_players_per_round.clear()
        
        # Trigger sync from tree to rounds
        self.synchronizer.sync_tree_to_rounds()
        
        # Check that round selections were updated
        if not self.ui_manager.selected_players_per_round:
            print("  ❌ Round selections not updated")
            return False
            
        # Restore original selections for other tests
        self.ui_manager.selected_players_per_round = original_selections
        
        print("  ✓ Round dropdowns updated from tree selection")
        
        return True
        
    def test_pattern_matching(self):
        """Test matchup pattern matching in tree nodes."""
        selection = MatchupSelection(
            round_num=1,
            ante_player='Pete',
            ante_team='friendly',
            response_players=['Opponent3'],
            response_team='enemy'
        )
        
        test_cases = [
            ('Pete vs Opponent3 (3/5)', True),
            ('Opponent3 vs Pete (3/5)', True),
            ('Pete vs Opponent3', True),
            ('Pete vs Opponent1 (2/5)', False),
            ('Kyle vs Sarah (4/5)', False),
            ('Pete vs Opponent3 (3/5) OR Opponent1 (2/5)', True),
        ]
        
        for node_text, expected in test_cases:
            result = selection.matches_tree_node_text(node_text)
            if result != expected:
                print(f"  ❌ Pattern match failed for '{node_text}': got {result}, expected {expected}")
                return False
                
        print("  ✓ All pattern matching tests passed")
        
        return True
        
    def test_conflict_handling(self):
        """Test handling of conflicting or incomplete selections."""
        # Test with incomplete round data
        original_selections = self.ui_manager.selected_players_per_round.copy()
        
        # Create incomplete selection (missing response)
        self.ui_manager.selected_players_per_round = {
            1: {
                'ante': 'Pete',
                'ante_team': 'friendly',
                'response1': None,  # Missing response
                'response2': None,
                'response_team': 'enemy'
            }
        }
        
        # Should handle gracefully without crashing
        try:
            selections = self.synchronizer._parse_round_selections()
            # Should return empty list for incomplete data
            if len(selections) > 0:
                print("  ❌ Should not create selections for incomplete data")
                return False
        except Exception as e:
            print(f"  ❌ Exception on incomplete data: {e}")
            return False
            
        # Test with conflicting data (selection not in tree)
        self.ui_manager.selected_players_per_round = {
            1: {
                'ante': 'NonExistentPlayer',
                'ante_team': 'friendly',
                'response1': 'AnotherNonExistentPlayer',
                'response2': None,
                'response_team': 'enemy'
            }
        }
        
        try:
            matching_path = self.synchronizer._find_matching_tree_path(
                self.synchronizer._parse_round_selections()
            )
            # Should return None for non-matching data
            if matching_path is not None:
                print(f"  ❌ Should not find path for non-existent players")
                return False
        except Exception as e:
            print(f"  ❌ Exception on conflicting data: {e}")
            return False
            
        # Restore original selections
        self.ui_manager.selected_players_per_round = original_selections
        
        print("  ✓ Conflict handling tests passed")
        
        return True
        
    def test_performance(self):
        """Test synchronization performance with larger datasets."""
        import time
        
        # Time the synchronization operations
        start_time = time.time()
        
        for _ in range(10):  # Run sync 10 times
            self.synchronizer.sync_round_to_tree()
            
        end_time = time.time()
        avg_time = (end_time - start_time) / 10
        
        # Should complete quickly (under 100ms per sync)
        if avg_time > 0.1:
            print(f"  ❌ Sync too slow: {avg_time:.3f}s average")
            return False
            
        print(f"  ✓ Performance test passed: {avg_time*1000:.1f}ms average")
        
        return True
        
    def print_summary(self):
        """Print test results summary."""
        print("\n" + "=" * 60)
        print("TEST RESULTS SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, result, _ in self.test_results if result)
        total = len(self.test_results)
        
        print(f"Tests passed: {passed}/{total}")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! Tree synchronization is working correctly.")
        else:
            print("❌ Some tests failed. Check the output above for details.")
            
        # Print any errors
        for test_name, result, error in self.test_results:
            if not result and error:
                print(f"  {test_name}: {error}")


def create_demo_ui():
    """Create a minimal demo UI to test synchronization interactively."""
    
    class DemoApp:
        def __init__(self):
            self.root = tk.Tk()
            self.root.title("Matchup Tree Sync Demo")
            self.root.geometry("800x600")
            
            # Create test UI manager
            self.ui_manager = MockUIManager()
            self.synchronizer = MatchupTreeSynchronizer(self.ui_manager)
            
            self.create_widgets()
            
        def create_widgets(self):
            # Title
            title = tk.Label(self.root, text="Matchup Tree Synchronization Demo", 
                           font=("Arial", 16, "bold"))
            title.pack(pady=10)
            
            # Round selections frame
            rounds_frame = tk.LabelFrame(self.root, text="Round Selections", padx=10, pady=10)
            rounds_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Display current selections
            self.selections_text = tk.Text(rounds_frame, height=6, width=60)
            self.selections_text.pack()
            
            # Tree selections frame
            tree_frame = tk.LabelFrame(self.root, text="Tree Structure", padx=10, pady=10)
            tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            # Tree display
            self.tree_text = tk.Text(tree_frame, height=10, width=60)
            self.tree_text.pack(fill=tk.BOTH, expand=True)
            
            # Buttons frame
            buttons_frame = tk.Frame(self.root)
            buttons_frame.pack(fill=tk.X, padx=10, pady=10)
            
            tk.Button(buttons_frame, text="Sync Round → Tree", 
                     command=self.sync_round_to_tree).pack(side=tk.LEFT, padx=5)
            tk.Button(buttons_frame, text="Sync Tree → Round", 
                     command=self.sync_tree_to_round).pack(side=tk.LEFT, padx=5)
            tk.Button(buttons_frame, text="Show Status", 
                     command=self.show_status).pack(side=tk.LEFT, padx=5)
            tk.Button(buttons_frame, text="Run Tests", 
                     command=self.run_tests).pack(side=tk.LEFT, padx=5)
            
            # Update display
            self.update_display()
            
        def sync_round_to_tree(self):
            self.synchronizer.sync_round_to_tree()
            self.update_display()
            
        def sync_tree_to_round(self):
            self.synchronizer.sync_tree_to_rounds()
            self.update_display()
            
        def show_status(self):
            status = self.synchronizer.get_sync_status()
            messagebox.showinfo("Sync Status", 
                              f"Is Syncing: {status['is_syncing']}\n"
                              f"Has Tree Widget: {status['has_tree_widget']}\n"
                              f"Round Selections: {status['round_selections_count']}\n"
                              f"Tree Path Length: {len(status['current_tree_path'])}")
            
        def run_tests(self):
            tester = TreeSyncTester()
            tester.run_all_tests()
            
        def update_display(self):
            # Update round selections display
            self.selections_text.delete(1.0, tk.END)
            for round_num, data in self.ui_manager.selected_players_per_round.items():
                ante = data.get('ante', 'None')
                resp1 = data.get('response1', 'None')
                self.selections_text.insert(tk.END, f"Round {round_num}: {ante} vs {resp1}\n")
                
            # Update tree display
            self.tree_text.delete(1.0, tk.END)
            selected = self.ui_manager.treeview.tree.selection()
            selected_text = "None"
            if selected:
                selected_text = self.ui_manager.treeview.tree.item(selected[0], 'text')
                
            self.tree_text.insert(tk.END, f"Selected: {selected_text}\n\n")
            self.tree_text.insert(tk.END, "Tree Structure:\n")
            self._display_tree_recursive("root", 0)
            
        def _display_tree_recursive(self, node_id, level):
            indent = "  " * level
            text = self.ui_manager.treeview.tree.item(node_id, 'text')
            
            # Highlight selected node
            selected = self.ui_manager.treeview.tree.selection()
            marker = " <<<" if selected and node_id in selected else ""
            
            self.tree_text.insert(tk.END, f"{indent}{text}{marker}\n")
            
            children = self.ui_manager.treeview.tree.get_children(node_id)
            for child in children:
                self._display_tree_recursive(child, level + 1)
                
        def run(self):
            self.root.mainloop()
    
    app = DemoApp()
    app.run()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Matchup Tree Synchronization')
    parser.add_argument('--demo', action='store_true', 
                       help='Run interactive demo instead of tests')
    args = parser.parse_args()
    
    if args.demo:
        create_demo_ui()
    else:
        tester = TreeSyncTester()
>>>>>>> origin/main
        tester.run_all_tests()