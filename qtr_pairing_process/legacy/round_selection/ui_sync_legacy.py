"""Legacy UI synchronization helpers.

Snapshot of the round-selection sync controller removed from the live UI.
This module is not wired into the application.
"""

from typing import Optional


class UiSyncControllerLegacy:
    def __init__(self, ui_manager):
        self.ui = ui_manager

    def sync_checkbox_with_player_selection(self, player_name):
        if not self.ui.checkbox_sync_enabled:
            return
        try:
            if not player_name:
                self.update_all_checkboxes_from_selections()
                return

            friendly_players = self.ui.get_friendly_player_names()
            for row_idx, friendly_player in enumerate(friendly_players):
                if friendly_player == player_name:
                    if row_idx < len(self.ui.row_checkboxes):
                        self.ui.row_checkboxes[row_idx].set(1)
                    break
        except Exception as exc:
            print(f"Error syncing checkbox with player selection: {exc}")

    def sync_column_checkbox_with_player_selection(self, player_name):
        if not self.ui.checkbox_sync_enabled:
            return
        try:
            if not player_name:
                self.update_all_column_checkboxes_from_selections()
                return

            enemy_players = self.ui.get_opponent_player_names()
            for col_idx, enemy_player in enumerate(enemy_players):
                if enemy_player == player_name:
                    if col_idx < len(self.ui.column_checkboxes):
                        self.ui.column_checkboxes[col_idx].set(1)
                    break
        except Exception as exc:
            print(f"Error syncing column checkbox with player selection: {exc}")

    def update_all_column_checkboxes_from_selections(self):
        if not self.ui.checkbox_sync_enabled:
            return
        try:
            self.ui._updating_dropdowns = True
            ui_prefs = self.ui.db_preferences.get_ui_preferences()
            team_size = ui_prefs.get('team_size', 5)

            selected_players = set()
            for round_num in range(1, 6):
                round_data = self.ui.selected_players_per_round.get(round_num, {})
                ante_team = round_data.get('ante_team')

                if ante_team == 'enemy' and round_data.get('ante'):
                    selected_players.add(round_data['ante'])

                if round_data.get('implicit_selection'):
                    enemy_players = self.ui.get_opponent_player_names()
                    if round_data['implicit_selection'] in enemy_players:
                        selected_players.add(round_data['implicit_selection'])

                if round_num == team_size:
                    response_team = round_data.get('response_team')
                    if response_team == 'enemy' and round_data.get('response1'):
                        selected_players.add(round_data['response1'])

            enemy_players = self.ui.get_opponent_player_names()
            for col_idx, enemy_player in enumerate(enemy_players):
                if col_idx < len(self.ui.column_checkboxes):
                    new_state = 1 if enemy_player in selected_players else 0
                    if self.ui.column_checkboxes[col_idx].get() != new_state:
                        self.ui.column_checkboxes[col_idx].set(new_state)
        except Exception as exc:
            print(f"Error updating all column checkboxes from selections: {exc}")
        finally:
            self.ui._updating_dropdowns = False

    def update_all_checkboxes_from_selections(self):
        if not self.ui.checkbox_sync_enabled:
            return
        try:
            self.ui._updating_dropdowns = True
            ui_prefs = self.ui.db_preferences.get_ui_preferences()
            team_size = ui_prefs.get('team_size', 5)

            selected_players = set()
            for round_num in range(1, 6):
                round_data = self.ui.selected_players_per_round.get(round_num, {})
                ante_team = round_data.get('ante_team')

                if ante_team == 'friendly' and round_data.get('ante'):
                    selected_players.add(round_data['ante'])

                if round_data.get('implicit_selection'):
                    friendly_players = self.ui.get_friendly_player_names()
                    if round_data['implicit_selection'] in friendly_players:
                        selected_players.add(round_data['implicit_selection'])

                if round_num == team_size:
                    response_team = round_data.get('response_team')
                    if response_team == 'friendly' and round_data.get('response1'):
                        selected_players.add(round_data['response1'])

            friendly_players = self.ui.get_friendly_player_names()
            for row_idx, friendly_player in enumerate(friendly_players):
                if row_idx < len(self.ui.row_checkboxes):
                    new_state = 1 if friendly_player in selected_players else 0
                    if self.ui.row_checkboxes[row_idx].get() != new_state:
                        self.ui.row_checkboxes[row_idx].set(new_state)
        except Exception as exc:
            print(f"Error updating all checkboxes from selections: {exc}")
        finally:
            self.ui._updating_dropdowns = False

    def sync_tree_with_round_1_ante(self, selected_player: Optional[str]):
        if not self.ui.sync_enabled:
            return
        try:
            if self.ui._tree_sync_in_progress:
                return

            if not selected_player:
                self.collapse_entire_tree()
                self.ui._current_tree_top_player = None
                return

            if self.ui._current_tree_top_player == selected_player:
                return

            root_nodes = self.ui.treeview.tree.get_children()
            if not root_nodes:
                self.ui._log_perf_entry("tree.sync.skip", 0.0, reason="no_tree")
                return

            self.sort_tree_worst_first()
            self.collapse_entire_tree()
            self.expand_and_select_round1_nodes(selected_player)
            self.ui._current_tree_top_player = selected_player
        except Exception as exc:
            print(f"Error synchronizing tree with Round 1 ante: {exc}")

    def collapse_entire_tree(self):
        try:
            def collapse_recursive(node_id):
                self.ui.treeview.tree.item(node_id, open=False)
                for child in self.ui.treeview.tree.get_children(node_id):
                    collapse_recursive(child)

            for root in self.ui.treeview.tree.get_children():
                collapse_recursive(root)
        except Exception as exc:
            print(f"Error collapsing tree: {exc}")

    def expand_and_select_round1_nodes(self, player_name: str):
        try:
            root_nodes = self.ui.treeview.tree.get_children()
            if not root_nodes:
                return

            pairings_root = root_nodes[0]
            self.ui.treeview.tree.item(pairings_root, open=True)
            round1_nodes = self.ui.treeview.tree.get_children(pairings_root)

            player_nodes = []
            other_nodes = []
            for node_id in round1_nodes:
                node_text = self.ui.treeview.tree.item(node_id, 'text')
                if player_name in node_text:
                    player_nodes.append((node_id, node_text))
                else:
                    other_nodes.append((node_id, node_text))

            other_nodes.sort(key=lambda x: x[1])

            for node_id in round1_nodes:
                self.ui.treeview.tree.detach(node_id)

            for node_id, _ in player_nodes:
                self.ui.treeview.tree.move(node_id, pairings_root, 'end')
                self.ui.treeview.tree.item(node_id, open=False)

            for node_id, _ in other_nodes:
                self.ui.treeview.tree.move(node_id, pairings_root, 'end')
                self.ui.treeview.tree.item(node_id, open=False)

            if player_nodes:
                first_matching_node = player_nodes[0][0]
                self.ui.treeview.tree.selection_remove(self.ui.treeview.tree.selection())
                self.ui.treeview.tree.selection_set(first_matching_node)
                self.ui.treeview.tree.see(first_matching_node)
        except Exception as exc:
            print(f"Error expanding Round 1 nodes: {exc}")

    def sort_tree_worst_first(self):
        try:
            if not hasattr(self.ui.tree_generator, 'original_order_saved') or not self.ui.tree_generator.original_order_saved:
                self.ui.tree_generator.save_original_order()
                self.ui.tree_generator.original_order_saved = True

            self.ui.tree_generator.calculate_all_path_values("")
            for root in self.ui.treeview.tree.get_children():
                self.sort_children_by_cumulative_reverse(root)

            self.ui.current_sort_mode = "worst_first"
            self.ui.active_sort_mode = "worst_first"
            self.ui.treeview.tree.heading("Sort Value", text="Worst First")
            self.ui.update_sort_value_column()
            self.ui.is_sorted = True
        except Exception as exc:
            print(f"Error sorting tree worst first: {exc}")

    def sort_children_by_cumulative_reverse(self, node):
        try:
            children = self.ui.treeview.tree.get_children(node)
            if not children:
                return

            children_with_scores = []
            for child in children:
                cumulative_value = self.ui.tree_generator.get_cumulative_value_from_tags(child)
                children_with_scores.append((child, cumulative_value))

            children_with_scores.sort(key=lambda x: x[1], reverse=False)

            for child, _ in children_with_scores:
                self.ui.treeview.tree.detach(child)
            for child, _ in children_with_scores:
                self.ui.treeview.tree.move(child, node, 'end')

            for child, _ in children_with_scores:
                self.sort_children_by_cumulative_reverse(child)
        except Exception as exc:
            print(f"Error sorting children reverse: {exc}")
