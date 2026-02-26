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
import logging
from copy import deepcopy
from dataclasses import dataclass

# Configure module logger and precompiled regex patterns
logger = logging.getLogger(__name__)
_VS_PATTERN = re.compile(r'^(.+?)\s+vs\s+(.+?)(?:\s*\([^)]+\))?$', re.IGNORECASE)
_TEAM_PATTERN = re.compile(r'^(.+?)\s+vs\s+(.+?)(?:\s*\([^)]+\))?(?:\s+OR\s+.*)?$', re.IGNORECASE)

# Cache configuration
_MAX_PATH_CACHE_SIZE = 100  # Maximum number of cached tree search paths


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
        match = _VS_PATTERN.search(node_text.strip())
        
        if match:
            node_player1 = match.group(1).strip()
            node_player2 = match.group(2).strip()
            
            # Check both possible orderings
            return ((node_player1 == player1 and node_player2 == player2) or
                   (node_player1 == player2 and node_player2 == player1))
                
        return False


class MatchupTreeSynchronizer:
    """Main synchronization class that coordinates between Round Tracker and Matchup Tree."""
    
    def __init__(self, ui_manager, auto_sync_enabled: bool = False, sync_state_callback=None):
        """
        Initialize the synchronizer with references to the UI components.
        
        Args:
            ui_manager: The main UI manager containing both round tracker and tree components
            auto_sync_enabled: Whether automatic synchronization is enabled (default: False)
            sync_state_callback: Optional callback function(in_sync: bool) to notify sync state changes
        """
        self.ui_manager = ui_manager
        self.tree_widget = ui_manager.treeview.tree if (hasattr(ui_manager, 'treeview') and ui_manager.treeview) else None
        self.is_syncing = False  # Prevent infinite loops during sync operations
        self.sync_direction = None  # Track current sync direction: 'round_to_tree' or 'tree_to_round'
        self.current_tree_path = []  # Cache of current tree selection path
        self.last_round_selections = {}  # Cache of last round selections for change detection
        self.pending_tree_sync_id = None  # Track pending tree-to-round sync callbacks
        self._path_cache: Dict[str, Optional[List[str]]] = {}  # Cache tree search paths for performance
        self._programmatic_tree_change = False  # Flag to ignore tree events during programmatic updates
        self.auto_sync_enabled = auto_sync_enabled  # Whether auto-sync is enabled
        self.sync_state_callback = sync_state_callback  # Callback to notify sync state changes
        
        # Set up event handlers
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Set up event handlers for both round tracker and tree selection changes."""
        if self.tree_widget:
            # Monitor tree selection changes
            self.tree_widget.bind('<<TreeviewSelect>>', self._on_tree_selection_changed)
            
        # The round tracker callbacks will be set up by hooking into existing change handlers
        # We'll enhance the existing on_ante_selection_change_direct and on_response_selection_change_direct

    def _is_tree_tab_visible(self) -> bool:
        """Check if the Matchup Tree tab is currently visible."""
        try:
            if not hasattr(self.ui_manager, 'notebook'):
                return False
            current_tab = self.ui_manager.notebook.select()
            if hasattr(self.ui_manager, 'matchup_tree_frame'):
                tree_tab_id = str(self.ui_manager.matchup_tree_frame)
                return current_tab == tree_tab_id
            return True
        except Exception:
            return True
    
    def set_auto_sync_enabled(self, enabled: bool):
        """Update the auto-sync enabled state at runtime."""
        self.auto_sync_enabled = enabled
        logger.info(f"Auto-sync {'enabled' if enabled else 'disabled'}")
    
    def sync_round_to_tree(self, changed_round: Optional[int] = None, manual_sync: bool = False):
        """
        Synchronize round tracker selections to tree navigation.
        
        Args:
            changed_round: Specific round that changed, or None to sync all rounds
            manual_sync: If True, bypass auto-sync and visibility checks (used for button clicks)
        """
        if self.is_syncing or not self.tree_widget:
            return
        
        if self.sync_state_callback:
            self.sync_state_callback(False)
        
        if not manual_sync and not self.auto_sync_enabled:
            logger.debug("Auto-sync disabled, skipping round-to-tree sync")
            return
        
        if not manual_sync and not self._is_tree_tab_visible():
            return
        
        if self.pending_tree_sync_id is not None:
            try:
                self.ui_manager.root.after_cancel(self.pending_tree_sync_id)
                self.pending_tree_sync_id = None
            except Exception:
                pass
            
        try:
            self.is_syncing = True
            self.sync_direction = 'round_to_tree'
            
            round_selections = self._parse_round_selections()
            if not round_selections:
                return
            
            matching_path = self._find_matching_tree_path(round_selections, changed_round)
            if matching_path:
                self._programmatic_tree_change = True
                self._navigate_to_tree_node(matching_path[-1])
                self.current_tree_path = matching_path
                if self.sync_state_callback:
                    self.sync_state_callback(True)
                if hasattr(self.ui_manager, 'root'):
                    self.ui_manager.root.after(50, lambda: setattr(self, '_programmatic_tree_change', False))
        except Exception as e:
            logger.error(f"Error syncing round to tree: {e}")
        finally:
            self.is_syncing = False
            self.sync_direction = None
    
    def sync_tree_to_rounds(self):
        """
        Synchronize tree selection to round tracker dropdowns.
        This is called when USER manually selects a tree node.
        
        IMPORTANT: This clears and overwrites all dropdown selections.
        Only call this for USER-initiated tree selections, not programmatic changes.
        """
        if self.is_syncing or not self.tree_widget:
            return
            
        try:
            self.is_syncing = True
            self.sync_direction = 'tree_to_round'
            
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
                if self.sync_state_callback:
                    self.sync_state_callback(True)
            
        except Exception as e:
            logger.error(f"Error syncing tree to rounds: {e}")
        finally:
            self.is_syncing = False
            self.sync_direction = None
    
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
        
        # Create cache key from selections
        cache_key = self._create_cache_key(round_selections)
        
        if cache_key in self._path_cache:
            cached_path = self._path_cache[cache_key]
            return cached_path
        
        root_items = self.tree_widget.get_children("")
        if not root_items:
            return None
        
        result_path = None
        for root_item in root_items:
            path = self._recursive_path_search(root_item, round_selections, 0, [root_item])
            if path:
                result_path = path
                break
        
        self._cache_path(cache_key, result_path)
        return result_path
    
    def _create_cache_key(self, selections: List[MatchupSelection]) -> str:
        """Create a hashable cache key from matchup selections."""
        key_parts = []
        for sel in selections:
            matchup = sel.get_primary_matchup()
            if matchup:
                key_parts.append(f"{sel.round_num}:{','.join(sorted(matchup))}")
        return '|'.join(key_parts)
    
    def _cache_path(self, cache_key: str, path: Optional[List[str]]):
        """Cache a tree path with size limit enforcement."""
        if len(self._path_cache) >= _MAX_PATH_CACHE_SIZE:
            try:
                oldest_key = next(iter(self._path_cache))
                del self._path_cache[oldest_key]
            except StopIteration:
                pass
        self._path_cache[cache_key] = path
    
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
            logger.error(f"Error navigating to tree node {node_id}: {e}")
    
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
                try:
                    node_text = self.tree_widget.item(current, 'text')
                    node_values = self.tree_widget.item(current, 'values')
                    
                    if node_text is None:
                        logger.warning(f"Tree node {current} has no text, skipping")
                        parent = self.tree_widget.parent(current)
                        current = parent if parent else None
                        continue
                    
                    path.insert(0, {
                        'node_id': current,
                        'text': node_text,
                        'values': node_values if node_values else []
                    })
                    
                    parent = self.tree_widget.parent(current)
                    current = parent if parent else None
                except tk.TclError as e:
                    logger.warning(f"Error accessing tree node {current}: {e}")
                    break
            
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
            logger.error(f"Error extracting matchups from tree path: {e}")
        
        return matchups
    
    def _parse_matchup_from_text(self, text: str, round_num: int) -> Optional[Dict[str, Any]]:
        """
        Parse matchup information from a tree node's text.
        
        Args:
            text: Tree node text
            round_num: Round number this matchup represents
            
        Returns:
            Dictionary with matchup info (player1, player2, player3 if OR exists) or None if parsing fails
        """
        match = _TEAM_PATTERN.search(text.strip())
        
        if match:
            player1 = match.group(1).strip()
            player2_raw = match.group(2).strip()
            player1 = re.sub(r'\s*\([^)]+\)$', '', player1).strip()
            player2 = None
            player3 = None
            
            if ' OR ' in text:
                or_pattern = re.compile(r'vs\s+(.+?)\s*\([^)]+\)\s+OR\s+(.+?)(?:\s*\([^)]+\))?$', re.IGNORECASE)
                or_match = or_pattern.search(text)
                if or_match:
                    player2 = or_match.group(1).strip()
                    player3 = or_match.group(2).strip()
                    player3 = re.sub(r'\s*\([^)]+\)$', '', player3).strip()
                else:
                    player2 = re.sub(r'\s*\([^)]+\)$', '', player2_raw).strip()
            else:
                player2 = re.sub(r'\s*\([^)]+\)$', '', player2_raw).strip()
            result = {
                'round': round_num,
                'player1': player1,
                'player2': player2,
                'text': text
            }
            if player3:
                result['player3'] = player3
            return result
        else:
            logger.warning(f"Failed to parse matchup from text: {text}")
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
                
                player3 = matchup.get('player3', None)
                
                if round_num <= 5 and player1 and player2:
                    friendly_antes = (round_num % 2 == 1)
                    ante_player = player1
                    response_player1 = player2
                    response_player2 = player3
                    if friendly_antes:
                        ante_team = 'friendly'
                        response_team = 'enemy'
                    else:
                        ante_team = 'enemy'
                        response_team = 'friendly'
                    self.ui_manager.selected_players_per_round[round_num] = {
                        'ante': ante_player,
                        'ante_team': ante_team,
                        'response1': response_player1,
                        'response2': response_player2,
                        'response_team': response_team
                    }
            
            # Update the actual dropdown widgets
            self._update_dropdown_widgets()
            
        except Exception as e:
            logger.error(f"Error updating round dropdowns from tree: {e}")

    def _calculate_dropdown_index(self, round_num: int, position: str, team: str) -> int:
        """Calculate the dropdown index for a given round, position, and team."""
        friendly_antes = (round_num % 2 == 1)
        if team == 'friendly':
            if friendly_antes:
                if position == 'ante':
                    return (round_num - 1) // 2 * 3
                logger.warning(f"Unexpected friendly response in round {round_num}")
                return 0
            response_num = int(position[-1]) if position.startswith('response') else 1
            base_index = ((round_num - 2) // 2 * 3) + 1
            return base_index + (response_num - 1)
        if friendly_antes:
            response_num = int(position[-1]) if position.startswith('response') else 1
            base_index = (round_num - 1) // 2 * 3 + 1
            return base_index + (response_num - 1)
        if position == 'ante':
            return ((round_num - 2) // 2 * 3)
        logger.warning(f"Unexpected enemy response in round {round_num}")
        return 0
    
    def _update_dropdown_widgets(self):
        """Update the actual dropdown widget values to match the tracking data."""
        try:
            if hasattr(self.ui_manager, '_updating_dropdowns'):
                self.ui_manager._updating_dropdowns = True
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
            logger.error(f"Error updating dropdown widgets: {e}")
        finally:
            if hasattr(self.ui_manager, '_updating_dropdowns'):
                self.ui_manager._updating_dropdowns = False
    
    def _on_tree_selection_changed(self, event):
        """Handle tree selection change events."""
        if self._programmatic_tree_change:
            logger.debug("Ignoring programmatic tree selection change")
            return
        if self.sync_state_callback:
            self.sync_state_callback(False)
        if not self.auto_sync_enabled:
            logger.debug("Auto-sync disabled, skipping tree-to-round sync")
            return
        if self.pending_tree_sync_id is not None:
            try:
                self.ui_manager.root.after_cancel(self.pending_tree_sync_id)
            except Exception:
                pass
        if hasattr(self.ui_manager, 'root'):
            def delayed_sync():
                self.pending_tree_sync_id = None
                if not self.is_syncing:
                    self.sync_tree_to_rounds()
            self.pending_tree_sync_id = self.ui_manager.root.after(100, delayed_sync)
    
    def is_selections_changed(self) -> bool:
        """Check if round selections have changed since last sync."""
        current_selections = self.ui_manager.selected_players_per_round
        changed = current_selections != self.last_round_selections
        
        if changed:
            self.last_round_selections = deepcopy(current_selections)
            
        return changed
    
    def force_full_sync(self):
        """Force a complete synchronization between round tracker and tree."""
        logger.info("Forcing full synchronization...")
        self.last_round_selections.clear()
        self.current_tree_path.clear()
        self._path_cache.clear()
        self.sync_round_to_tree(manual_sync=True)

    def cleanup(self):
        """Clean up resources and unbind event handlers."""
        if self.pending_tree_sync_id is not None:
            try:
                self.ui_manager.root.after_cancel(self.pending_tree_sync_id)
                self.pending_tree_sync_id = None
            except Exception as e:
                logger.warning(f"Error canceling pending sync: {e}")
        if self.tree_widget:
            try:
                self.tree_widget.unbind('<<TreeviewSelect>>')
            except Exception as e:
                logger.warning(f"Error unbinding tree event handler: {e}")
        self.last_round_selections.clear()
        self.current_tree_path.clear()
        self._path_cache.clear()
        self._programmatic_tree_change = False
        self.sync_state_callback = None
        self.tree_widget = None
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current synchronization status for debugging."""
        return {
            'is_syncing': self.is_syncing,
            'has_tree_widget': self.tree_widget is not None,
            'current_tree_path': self.current_tree_path,
            'round_selections_count': len(self.ui_manager.selected_players_per_round) if hasattr(self.ui_manager, 'selected_players_per_round') else 0,
            'last_cached_selections': self.last_round_selections
        }