""" © Daniel P Raven 2024 All Rights Reserved """
"""
Matchup Tree Synchronization System

This module provides the core synchronization logic between the Round Tracker
selections and the Matchup Tree navigation. When a user makes selections in
the Round Tracker (Pete vs Opponent 3 in Round 1), the system will automatically
find and highlight the corresponding node in the Matchup Tree.

Key Components:
1. Round Selection Parser - Converts round tracker data to matchup patterns
2. Tree Search Engine - Finds matching nodes in the tree structure  
3. Path Synchronizer - Updates both systems when changes occur
4. Conflict Resolver - Handles cases where selections don't match tree paths
"""

import tkinter as tk
from typing import Dict, List, Optional, Tuple, Any
import re
from dataclasses import dataclass


@dataclass
class MatchupSelection:
    """Represents a single matchup selection from the round tracker."""
    round_num: int
    ante_player: str
    ante_team: str  # 'friendly' or 'enemy'
    response_players: List[str]
    response_team: str  # 'friendly' or 'enemy'
    
    def get_primary_matchup(self) -> Optional[Tuple[str, str]]:
        """Get the primary player vs player matchup for this round."""
        if not self.response_players:
            return None
        
        # For ante/response system, the matchup is ante_player vs first_response_player
        return (self.ante_player, self.response_players[0])
    
    def matches_tree_node_text(self, node_text: str) -> bool:
        """Check if this selection matches a tree node's text representation."""
        matchup = self.get_primary_matchup()
        if not matchup:
            return False
            
        player1, player2 = matchup
        
        # For choice nodes with OR, only match if it contains our players
        if ' OR ' in node_text:
            # Match if either option contains our players
            return (player1 in node_text and player2 in node_text)
        
        # For specific matchup nodes, require exact player match
        vs_pattern = r'^(.+?)\s+vs\s+(.+?)(?:\s*\([^)]+\))?$'
        match = re.search(vs_pattern, node_text.strip(), re.IGNORECASE)
        
        if match:
            node_player1 = match.group(1).strip()
            node_player2 = match.group(2).strip()
            
            # Check both possible orderings
            return ((node_player1 == player1 and node_player2 == player2) or
                   (node_player1 == player2 and node_player2 == player1))
                
        return False


class MatchupTreeSynchronizer:
    """Main synchronization class that coordinates between Round Tracker and Matchup Tree."""
    
    def __init__(self, ui_manager):
        """
        Initialize the synchronizer with references to the UI components.
        
        Args:
            ui_manager: The main UI manager containing both round tracker and tree components
        """
        self.ui_manager = ui_manager
        self.tree_widget = ui_manager.treeview.tree if hasattr(ui_manager, 'treeview') else None
        self.is_syncing = False  # Prevent infinite loops during sync operations
        self.current_tree_path = []  # Cache of current tree selection path
        self.last_round_selections = {}  # Cache of last round selections for change detection
        
        # Set up event handlers
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Set up event handlers for both round tracker and tree selection changes."""
        if self.tree_widget:
            # Monitor tree selection changes
            self.tree_widget.bind('<<TreeviewSelect>>', self._on_tree_selection_changed)
            
        # The round tracker callbacks will be set up by hooking into existing change handlers
        # We'll enhance the existing on_ante_selection_change_direct and on_response_selection_change_direct
    
    def sync_round_to_tree(self, changed_round: Optional[int] = None):
        """
        Synchronize round tracker selections to tree navigation.
        
        Args:
            changed_round: Specific round that changed, or None to sync all rounds
        """
        if self.is_syncing or not self.tree_widget:
            return
            
        try:
            self.is_syncing = True
            
            # Get current round selections
            round_selections = self._parse_round_selections()
            
            if not round_selections:
                print("No round selections to sync")
                return
            
            # Find the matching tree path
            matching_path = self._find_matching_tree_path(round_selections, changed_round)
            
            if matching_path:
                # Navigate to the matching node
                self._navigate_to_tree_node(matching_path[-1])
                self.current_tree_path = matching_path
                print(f"Synced to tree node: {matching_path[-1]}")
            else:
                print("No matching tree path found for current round selections")
                
        except Exception as e:
            print(f"Error syncing round to tree: {e}")
        finally:
            self.is_syncing = False
    
    def sync_tree_to_rounds(self):
        """
        Synchronize tree selection to round tracker dropdowns.
        This is called when user manually selects a tree node.
        """
        if self.is_syncing or not self.tree_widget:
            return
            
        try:
            self.is_syncing = True
            
            # Get selected tree item
            selected_items = self.tree_widget.selection()
            if not selected_items:
                return
                
            selected_item = selected_items[0]
            
            # Extract matchup information from tree path
            tree_matchups = self._extract_matchups_from_tree_path(selected_item)
            
            if tree_matchups:
                # Update round tracker dropdowns to match
                self._update_round_dropdowns_from_tree(tree_matchups)
                print(f"Synced round tracker from tree selection")
            
        except Exception as e:
            print(f"Error syncing tree to rounds: {e}")
        finally:
            self.is_syncing = False
    
    def _parse_round_selections(self) -> List[MatchupSelection]:
        """Parse current round tracker selections into MatchupSelection objects."""
        selections = []
        
        if not hasattr(self.ui_manager, 'selected_players_per_round'):
            return selections
            
        for round_num in range(1, 6):  # Rounds 1-5
            round_data = self.ui_manager.selected_players_per_round.get(round_num, {})
            
            ante_player = round_data.get('ante')
            ante_team = round_data.get('ante_team', 'unknown')
            response_team = round_data.get('response_team', 'unknown')
            
            # Collect response players
            response_players = []
            for i in range(1, 3):  # Up to 2 response players
                response_player = round_data.get(f'response{i}')
                if response_player:
                    response_players.append(response_player)
            
            # Only create selection if we have meaningful data
            if ante_player and response_players:
                selection = MatchupSelection(
                    round_num=round_num,
                    ante_player=ante_player,
                    ante_team=ante_team,
                    response_players=response_players,
                    response_team=response_team
                )
                selections.append(selection)
        
        return selections
    
    def _find_matching_tree_path(self, round_selections: List[MatchupSelection], 
                                focus_round: Optional[int] = None) -> Optional[List[str]]:
        """
        Find the tree node path that matches the given round selections.
        
        Args:
            round_selections: List of MatchupSelection objects
            focus_round: Specific round to focus on, or None for full path
            
        Returns:
            List of tree node IDs representing the path, or None if no match found
        """
        if not round_selections or not self.tree_widget:
            return None
        
        # Start from tree root
        root_items = self.tree_widget.get_children("")
        if not root_items:
            return None
        
        # Use recursive search to find matching path
        for root_item in root_items:
            path = self._recursive_path_search(root_item, round_selections, 0, [root_item])
            if path:
                return path
        
        return None
    
    def _recursive_path_search(self, current_node: str, selections: List[MatchupSelection],
                              selection_index: int, current_path: List[str]) -> Optional[List[str]]:
        """
        Recursively search the tree for a path matching the selections.
        
        Args:
            current_node: Current tree node ID
            selections: Remaining selections to match
            selection_index: Index of current selection being matched
            current_path: Path taken so far
            
        Returns:
            Complete path if match found, None otherwise
        """
        if selection_index >= len(selections):
            # We've matched all selections
            return current_path
        
        # Get current node information
        if not self.tree_widget:
            return None
        node_text = self.tree_widget.item(current_node, 'text')
        
        # Check if current node matches current selection
        current_selection = selections[selection_index]
        
        if current_selection.matches_tree_node_text(node_text):
            # This node matches the current selection
            children = self.tree_widget.get_children(current_node)
            
            # If this is a choice node (has children), look for more specific match
            if children and ' OR ' in node_text:
                # Try to find a more specific child match first
                for child in children:
                    child_text = self.tree_widget.item(child, 'text')
                    if current_selection.matches_tree_node_text(child_text):
                        # Found a more specific match, use that path
                        child_path = current_path + [child]
                        if selection_index == len(selections) - 1:
                            return child_path
                        else:
                            # Continue with next selection
                            result = self._recursive_path_search(child, selections, 
                                                               selection_index + 1, child_path)
                            if result:
                                return result
            
            # If no better child match or this is the last selection
            if selection_index == len(selections) - 1:
                return current_path
            else:
                # Look for the next selection in children
                for child in children:
                    child_path = current_path + [child]
                    result = self._recursive_path_search(child, selections, 
                                                       selection_index + 1, child_path)
                    if result:
                        return result
        
        # If this node doesn't match, try children with same selection index
        # (might be a structural node like a choice branch)
        children = self.tree_widget.get_children(current_node)
        for child in children:
            child_path = current_path + [child]
            result = self._recursive_path_search(child, selections, 
                                               selection_index, child_path)
            if result:
                return result
        
        return None
    
    def _navigate_to_tree_node(self, node_id: str):
        """Navigate to and select a specific tree node."""
        if not self.tree_widget:
            return
            
        try:
            # Clear current selection
            self.tree_widget.selection_remove(self.tree_widget.selection())
            
            # Select the target node
            self.tree_widget.selection_set(node_id)
            
            # Ensure the node is visible
            self.tree_widget.see(node_id)
            
            # Expand parent nodes if necessary to show the selected node
            parent = self.tree_widget.parent(node_id)
            while parent:
                self.tree_widget.item(parent, open=True)
                parent = self.tree_widget.parent(parent)
                
        except Exception as e:
            print(f"Error navigating to tree node {node_id}: {e}")
    
    def _extract_matchups_from_tree_path(self, target_node: str) -> List[Dict[str, Any]]:
        """
        Extract matchup information from the path to a target tree node.
        
        Args:
            target_node: Tree node ID to extract path for
            
        Returns:
            List of matchup dictionaries with round, players, etc.
        """
        matchups = []
        
        try:
            if not self.tree_widget:
                return matchups
                
            # Build path from root to target
            path = []
            current = target_node
            
            while current:
                node_text = self.tree_widget.item(current, 'text')
                node_values = self.tree_widget.item(current, 'values')
                
                path.insert(0, {
                    'node_id': current,
                    'text': node_text,
                    'values': node_values
                })
                
                parent = self.tree_widget.parent(current)
                current = parent if parent else None
            
            # Parse path for matchup information
            round_num = 1
            for node_data in path:
                text = node_data['text']
                
                # Look for "vs" patterns that indicate matchups
                if ' vs ' in text and not text.startswith('Pairings'):
                    matchup_info = self._parse_matchup_from_text(text, round_num)
                    if matchup_info:
                        matchups.append(matchup_info)
                        round_num += 1
            
        except Exception as e:
            print(f"Error extracting matchups from tree path: {e}")
        
        return matchups
    
    def _parse_matchup_from_text(self, text: str, round_num: int) -> Optional[Dict[str, Any]]:
        """
        Parse matchup information from a tree node's text.
        
        Args:
            text: Tree node text
            round_num: Round number this matchup represents
            
        Returns:
            Dictionary with matchup info or None if parsing fails
        """
        # Pattern to match "Player1 vs Player2" with optional rating info
        vs_pattern = r'^(.+?)\s+vs\s+(.+?)(?:\s*\([^)]+\))?(?:\s+OR\s+.*)?$'
        match = re.search(vs_pattern, text.strip(), re.IGNORECASE)
        
        if match:
            player1 = match.group(1).strip()
            player2 = match.group(2).strip()
            
            # Remove any rating information from player names
            player1 = re.sub(r'\s*\([^)]+\)$', '', player1).strip()
            player2 = re.sub(r'\s*\([^)]+\)$', '', player2).strip()
            
            return {
                'round': round_num,
                'player1': player1,
                'player2': player2,
                'text': text
            }
        
        return None
    
    def _update_round_dropdowns_from_tree(self, tree_matchups: List[Dict[str, Any]]):
        """
        Update round tracker dropdowns based on tree matchup information.
        
        Args:
            tree_matchups: List of matchup dictionaries from tree
        """
        if not hasattr(self.ui_manager, 'selected_players_per_round'):
            return
        
        try:
            # Clear existing selections
            self.ui_manager.selected_players_per_round.clear()
            
            # Update dropdowns for each matchup
            for matchup in tree_matchups:
                round_num = matchup.get('round', 1)
                player1 = matchup.get('player1', '')
                player2 = matchup.get('player2', '')
                
                if round_num <= 5 and player1 and player2:
                    # Determine ante/response based on round number and team logic
                    friendly_antes = (round_num % 2 == 1)  # Rounds 1,3,5
                    
                    if friendly_antes:
                        ante_player = player1  # Assume player1 is ante
                        response_player = player2
                        ante_team = 'friendly'
                        response_team = 'enemy'
                    else:
                        ante_player = player2  # Assume player2 is ante  
                        response_player = player1
                        ante_team = 'enemy'
                        response_team = 'friendly'
                    
                    # Update the tracking dictionary
                    self.ui_manager.selected_players_per_round[round_num] = {
                        'ante': ante_player,
                        'ante_team': ante_team,
                        'response1': response_player,
                        'response2': None,  # Only one response for now
                        'response_team': response_team
                    }
            
            # Update the actual dropdown widgets
            self._update_dropdown_widgets()
            
        except Exception as e:
            print(f"Error updating round dropdowns from tree: {e}")
    
    def _update_dropdown_widgets(self):
        """Update the actual dropdown widget values to match the tracking data."""
        try:
            # Update round dropdowns
            if hasattr(self.ui_manager, 'round_vars') and hasattr(self.ui_manager, 'enemy_round_vars'):
                round_var_index = 0
                enemy_var_index = 0
                
                for round_num in range(1, 6):
                    round_data = self.ui_manager.selected_players_per_round.get(round_num, {})
                    friendly_antes = (round_num % 2 == 1)
                    
                    if friendly_antes:
                        # Friendly ante
                        if round_var_index < len(self.ui_manager.round_vars):
                            ante_player = round_data.get('ante', '')
                            self.ui_manager.round_vars[round_var_index].set(ante_player)
                            round_var_index += 1
                        
                        # Enemy responses  
                        for i in range(1, 3):
                            if enemy_var_index < len(self.ui_manager.enemy_round_vars):
                                response_player = round_data.get(f'response{i}', '')
                                self.ui_manager.enemy_round_vars[enemy_var_index].set(response_player)
                                enemy_var_index += 1
                    else:
                        # Enemy ante
                        if enemy_var_index < len(self.ui_manager.enemy_round_vars):
                            ante_player = round_data.get('ante', '')
                            self.ui_manager.enemy_round_vars[enemy_var_index].set(ante_player)
                            enemy_var_index += 1
                        
                        # Friendly responses
                        for i in range(1, 3):
                            if round_var_index < len(self.ui_manager.round_vars):
                                response_player = round_data.get(f'response{i}', '')
                                self.ui_manager.round_vars[round_var_index].set(response_player)
                                round_var_index += 1
                                
        except Exception as e:
            print(f"Error updating dropdown widgets: {e}")
    
    def _on_tree_selection_changed(self, event):
        """Handle tree selection change events."""
        # Delay sync to avoid conflicts with tree expansion/collapse
        if hasattr(self.ui_manager, 'root'):
            self.ui_manager.root.after(100, self.sync_tree_to_rounds)
    
    def is_selections_changed(self) -> bool:
        """Check if round selections have changed since last sync."""
        current_selections = self.ui_manager.selected_players_per_round
        changed = current_selections != self.last_round_selections
        
        if changed:
            self.last_round_selections = current_selections.copy()
            
        return changed
    
    def force_full_sync(self):
        """Force a complete synchronization between round tracker and tree."""
        print("Forcing full synchronization...")
        
        # Clear cache
        self.last_round_selections.clear()
        self.current_tree_path.clear()
        
        # Sync round to tree (this is typically the primary direction)
        self.sync_round_to_tree()
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current synchronization status for debugging."""
        return {
            'is_syncing': self.is_syncing,
            'has_tree_widget': self.tree_widget is not None,
            'current_tree_path': self.current_tree_path,
            'round_selections_count': len(self.ui_manager.selected_players_per_round) if hasattr(self.ui_manager, 'selected_players_per_round') else 0,
            'last_cached_selections': self.last_round_selections
        }