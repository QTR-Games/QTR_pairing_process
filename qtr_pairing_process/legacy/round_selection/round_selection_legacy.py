"""Legacy round-selection UI logic.

Snapshot of the round-selection dropdown feature that was removed from the live UI.
This module is not wired into the application and is kept for reference only.
"""

import tkinter as tk
from tkinter import ttk, messagebox


class RoundSelectionLegacy:
    def __init__(self, ui_manager):
        self.ui = ui_manager

    def create_round_selection_dropdowns(self):
        """Create dropdowns for tracking player selections across tournament rounds."""
        try:
            ui_prefs = self.ui.db_preferences.get_ui_preferences()
            team_size = ui_prefs.get('team_size', 5)
            print(f"Creating dropdowns for {team_size}-player teams")

            for widget in self.ui.round_selection_frame.winfo_children():
                if widget.winfo_class() != 'Frame' or len(widget.winfo_children()) == 0:
                    continue
                widget.destroy()

            self.ui.round_dropdowns.clear()
            self.ui.round_vars.clear()
            self.ui.enemy_round_dropdowns = []
            self.ui.enemy_round_vars = []

            grid_container = tk.Frame(self.ui.round_selection_frame)
            grid_container.pack(fill=tk.X, padx=10, pady=5)

            header_frame = tk.Frame(grid_container)
            header_frame.pack(fill=tk.X, pady=(0, 8))

            header_frame.grid_columnconfigure(0, weight=0, minsize=80)
            header_frame.grid_columnconfigure(1, weight=1, minsize=150)
            header_frame.grid_columnconfigure(2, weight=1, minsize=150)

            tk.Label(header_frame, text="Round", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5, sticky='w')
            tk.Label(header_frame, text="Team B", font=("Arial", 10, "bold")).grid(row=0, column=1, padx=5, sticky='w')
            tk.Label(header_frame, text="Team A", font=("Arial", 10, "bold")).grid(row=0, column=2, padx=5, sticky='w')

            for round_num in range(1, 6):
                round_frame = tk.Frame(grid_container)
                round_frame.pack(fill=tk.X, pady=2)

                round_frame.grid_columnconfigure(0, weight=0, minsize=80)
                round_frame.grid_columnconfigure(1, weight=1, minsize=150)
                round_frame.grid_columnconfigure(2, weight=1, minsize=150)

                tk.Label(round_frame, text=f"Round {round_num}:", font=("Arial", 9), width=8).grid(row=0, column=0, padx=5, sticky='w')

                friendly_antes = (round_num % 2 == 1)

                if friendly_antes:
                    friendly_var = tk.StringVar()
                    friendly_dropdown = ttk.Combobox(round_frame, state='readonly', width=18, textvariable=friendly_var)
                    friendly_dropdown.grid(row=0, column=1, padx=5, pady=2, sticky='ew')

                    enemy_response_frame = tk.Frame(round_frame)
                    enemy_response_frame.grid(row=0, column=2, rowspan=2, padx=5, pady=2, sticky='nsew')

                    enemy_var1 = tk.StringVar()
                    enemy_dropdown1 = ttk.Combobox(enemy_response_frame, state='readonly', width=18, textvariable=enemy_var1)
                    enemy_dropdown1.pack(fill=tk.X, pady=(0, 2))

                    if round_num < team_size:
                        enemy_var2 = tk.StringVar()
                        enemy_dropdown2 = ttk.Combobox(enemy_response_frame, state='readonly', width=18, textvariable=enemy_var2)
                        enemy_dropdown2.pack(fill=tk.X, pady=(0, 0))
                        enemy_var2.trace_add('write', lambda *args, r=round_num, p=2, v=enemy_var2: self.on_response_selection_change_direct(r, p, v))
                        self.ui.enemy_round_vars.extend([enemy_var1, enemy_var2])
                        self.ui.enemy_round_dropdowns.extend([enemy_dropdown1, enemy_dropdown2])
                    else:
                        self.ui.enemy_round_vars.append(enemy_var1)
                        self.ui.enemy_round_dropdowns.append(enemy_dropdown1)

                    friendly_var.trace_add('write', lambda *args, r=round_num, v=friendly_var: self.on_ante_selection_change_direct(r, v))
                    enemy_var1.trace_add('write', lambda *args, r=round_num, p=1, v=enemy_var1: self.on_response_selection_change_direct(r, p, v))

                    self.ui.round_vars.append(friendly_var)
                    self.ui.round_dropdowns.append(friendly_dropdown)
                    self.ui.selected_players_per_round[round_num] = {
                        'ante': None, 'ante_team': 'friendly',
                        'response1': None, 'response2': None, 'response_team': 'enemy'
                    }
                else:
                    enemy_var = tk.StringVar()
                    enemy_dropdown = ttk.Combobox(round_frame, state='readonly', width=18, textvariable=enemy_var)
                    enemy_dropdown.grid(row=0, column=2, padx=5, pady=2, sticky='ew')

                    friendly_response_frame = tk.Frame(round_frame)
                    friendly_response_frame.grid(row=0, column=1, rowspan=2, padx=5, pady=2, sticky='nsew')

                    friendly_var1 = tk.StringVar()
                    friendly_dropdown1 = ttk.Combobox(friendly_response_frame, state='readonly', width=18, textvariable=friendly_var1)
                    friendly_dropdown1.pack(fill=tk.X, pady=(0, 2))

                    if round_num < team_size:
                        friendly_var2 = tk.StringVar()
                        friendly_dropdown2 = ttk.Combobox(friendly_response_frame, state='readonly', width=18, textvariable=friendly_var2)
                        friendly_dropdown2.pack(fill=tk.X, pady=(0, 0))
                        friendly_var2.trace_add('write', lambda *args, r=round_num, p=2, v=friendly_var2: self.on_response_selection_change_direct(r, p, v))
                        self.ui.round_vars.extend([friendly_var1, friendly_var2])
                        self.ui.round_dropdowns.extend([friendly_dropdown1, friendly_dropdown2])
                    else:
                        self.ui.round_vars.append(friendly_var1)
                        self.ui.round_dropdowns.append(friendly_dropdown1)

                    enemy_var.trace_add('write', lambda *args, r=round_num, v=enemy_var: self.on_ante_selection_change_direct(r, v))
                    friendly_var1.trace_add('write', lambda *args, r=round_num, p=1, v=friendly_var1: self.on_response_selection_change_direct(r, p, v))

                    self.ui.enemy_round_vars.append(enemy_var)
                    self.ui.enemy_round_dropdowns.append(enemy_dropdown)
                    self.ui.selected_players_per_round[round_num] = {
                        'ante': None, 'ante_team': 'enemy',
                        'response1': None, 'response2': None, 'response_team': 'friendly'
                    }

            if hasattr(self.ui, 'root'):
                self.ui.root.after_idle(lambda: self.update_round_dropdown_options(force=True))
        except Exception as e:
            print(f"Error creating round selection dropdowns: {e}")
            messagebox.showerror("Error", f"Failed to create round selection dropdowns: {e}")

    def update_round_dropdown_options(self, force: bool = False):
        """Update the options in round dropdowns based on current team selection."""
        try:
            team_1 = self.ui.team1_var.get().strip() if hasattr(self.ui, 'team1_var') else ''
            team_2 = self.ui.team2_var.get().strip() if hasattr(self.ui, 'team2_var') else ''
            if not team_1 or not team_2:
                return

            dropdown_key = (team_1, team_2)
            if not force and dropdown_key == self.ui._round_dropdowns_last_key and not self.ui._round_dropdowns_dirty:
                return

            self.ui._round_dropdowns_last_key = dropdown_key
            self.ui._round_dropdowns_dirty = False

            friendly_players = []
            enemy_players = []

            if self.ui.team1_var.get():
                team1_data = self.ui._get_team_data(self.ui.team1_var.get())
                if team1_data:
                    friendly_players = [row['name'] for row in team1_data['players']]

            if self.ui.team2_var.get():
                team2_data = self.ui._get_team_data(self.ui.team2_var.get())
                if team2_data:
                    enemy_players = [row['name'] for row in team2_data['players']]

            if hasattr(self.ui, 'round_dropdowns') and hasattr(self.ui, 'enemy_round_dropdowns'):
                self._update_ante_response_dropdowns(friendly_players, enemy_players)
        except Exception as e:
            print(f"Error updating round dropdown options: {e}")

    def on_ante_selection_change_direct(self, round_num, var):
        """Handle ante selection changes with direct variable access."""
        try:
            if self.ui._updating_dropdowns:
                return

            selected_player = var.get()
            old_ante = self.ui.selected_players_per_round[round_num].get('ante')
            self.ui.selected_players_per_round[round_num]['ante'] = selected_player if selected_player else None

            if old_ante != (selected_player if selected_player else None):
                self.clear_subsequent_rounds(round_num)

            round_data = self.ui.selected_players_per_round.get(round_num, {})
            ante_team = round_data.get('ante_team', 'unknown')

            if round_num in [2, 3, 4, 5] and selected_player:
                previous_round = round_num - 1
                previous_round_data = self.ui.selected_players_per_round.get(previous_round, {})

                response1 = previous_round_data.get('response1')
                response2 = previous_round_data.get('response2')

                if response1 and response2:
                    if selected_player == response1:
                        previous_round_data['implicit_selection'] = response2
                    elif selected_player == response2:
                        previous_round_data['implicit_selection'] = response1
            else:
                if round_num >= 2:
                    previous_round = round_num - 1
                    previous_round_data = self.ui.selected_players_per_round.get(previous_round, {})
                    if 'implicit_selection' in previous_round_data:
                        previous_round_data['implicit_selection'] = None

            if self.ui.checkbox_sync_enabled:
                self.ui.ui_sync.update_all_checkboxes_from_selections()
                self.ui.ui_sync.update_all_column_checkboxes_from_selections()

            self.update_round_dropdown_options(force=True)

            if round_num == 1 and ante_team == 'friendly':
                self.ui.ui_sync.sync_tree_with_round_1_ante(selected_player)

            print(f"Round {round_num} ante selection ({ante_team}): {selected_player}")
        except Exception as e:
            print(f"Error handling ante selection change: {e}")

    def on_response_selection_change_direct(self, round_num, position, var):
        """Handle response selection changes with direct variable access."""
        try:
            if self.ui._updating_dropdowns:
                return

            selected_player = var.get()
            response_key = f'response{position}'
            old_response = self.ui.selected_players_per_round[round_num].get(response_key)
            self.ui.selected_players_per_round[round_num][response_key] = selected_player if selected_player else None

            if not selected_player and old_response:
                other_position = 2 if position == 1 else 1
                other_key = f'response{other_position}'
                self.ui.selected_players_per_round[round_num][other_key] = None

                if 'implicit_selection' in self.ui.selected_players_per_round[round_num]:
                    self.ui.selected_players_per_round[round_num]['implicit_selection'] = None

            if old_response != (selected_player if selected_player else None):
                self.clear_subsequent_rounds(round_num)
                self.refresh_dropdown_ui_from_tracking()

            self.update_round_dropdown_options(force=True)

            if self.ui.checkbox_sync_enabled:
                self.ui.ui_sync.update_all_checkboxes_from_selections()
                self.ui.ui_sync.update_all_column_checkboxes_from_selections()

            ui_prefs = self.ui.db_preferences.get_ui_preferences()
            team_size = ui_prefs.get('team_size', 5)
            if round_num == team_size and position == 1:
                pass

            round_data = self.ui.selected_players_per_round.get(round_num, {})
            response_team = round_data.get('response_team', 'unknown')
            print(f"Round {round_num} response {position} ({response_team}): {selected_player}")
        except Exception as e:
            print(f"Error handling response selection change: {e}")

    def clear_subsequent_rounds(self, from_round):
        """Clear all dropdown selections in rounds after the specified round."""
        try:
            for round_num in range(from_round + 1, 6):
                if round_num in self.ui.selected_players_per_round:
                    round_data = self.ui.selected_players_per_round[round_num]
                    round_data['ante'] = None
                    round_data['response1'] = None
                    round_data['response2'] = None
                    if 'implicit_selection' in round_data:
                        round_data['implicit_selection'] = None

            self.refresh_dropdown_ui_from_tracking()
            print(f"Cleared all rounds after round {from_round}")
        except Exception as e:
            print(f"Error clearing subsequent rounds: {e}")

    def refresh_dropdown_ui_from_tracking(self):
        """Refresh all dropdown UI elements to match the tracking dictionary."""
        try:
            self.ui._updating_dropdowns = True

            friendly_dropdown_idx = 0
            for round_num in range(1, 6):
                round_data = self.ui.selected_players_per_round.get(round_num, {})
                ante_team = round_data.get('ante_team')
                response_team = round_data.get('response_team')

                if ante_team == 'friendly':
                    if friendly_dropdown_idx < len(self.ui.round_vars):
                        ante_value = round_data.get('ante', '')
                        self.ui.round_vars[friendly_dropdown_idx].set(ante_value if ante_value else "")
                        friendly_dropdown_idx += 1

                if response_team == 'friendly':
                    if friendly_dropdown_idx < len(self.ui.round_vars):
                        response1_value = round_data.get('response1', '')
                        self.ui.round_vars[friendly_dropdown_idx].set(response1_value if response1_value else "")
                        friendly_dropdown_idx += 1

                    if friendly_dropdown_idx < len(self.ui.round_vars):
                        response2_value = round_data.get('response2', '')
                        self.ui.round_vars[friendly_dropdown_idx].set(response2_value if response2_value else "")
                        friendly_dropdown_idx += 1

            enemy_dropdown_idx = 0
            for round_num in range(1, 6):
                round_data = self.ui.selected_players_per_round.get(round_num, {})
                ante_team = round_data.get('ante_team')
                response_team = round_data.get('response_team')

                if ante_team == 'enemy':
                    if enemy_dropdown_idx < len(self.ui.enemy_round_vars):
                        ante_value = round_data.get('ante', '')
                        self.ui.enemy_round_vars[enemy_dropdown_idx].set(ante_value if ante_value else "")
                        enemy_dropdown_idx += 1

                if response_team == 'enemy':
                    if enemy_dropdown_idx < len(self.ui.enemy_round_vars):
                        response1_value = round_data.get('response1', '')
                        self.ui.enemy_round_vars[enemy_dropdown_idx].set(response1_value if response1_value else "")
                        enemy_dropdown_idx += 1

                    ui_prefs = self.ui.db_preferences.get_ui_preferences()
                    team_size = ui_prefs.get('team_size', 5)
                    if round_num < team_size and enemy_dropdown_idx < len(self.ui.enemy_round_vars):
                        response2_value = round_data.get('response2', '')
                        self.ui.enemy_round_vars[enemy_dropdown_idx].set(response2_value if response2_value else "")
                        enemy_dropdown_idx += 1

            self.ui._updating_dropdowns = False
        except Exception as e:
            self.ui._updating_dropdowns = False
            print(f"Error refreshing dropdown UI: {e}")

    def clear_round_dropdowns(self):
        """Clear all values from round selection dropdowns."""
        try:
            self.ui._updating_dropdowns = True

            for var in self.ui.round_vars:
                var.set("")

            for var in self.ui.enemy_round_vars:
                var.set("")

            for round_num in self.ui.selected_players_per_round:
                self.ui.selected_players_per_round[round_num]['ante'] = None
                self.ui.selected_players_per_round[round_num]['response1'] = None
                self.ui.selected_players_per_round[round_num]['response2'] = None
                if 'implicit_selection' in self.ui.selected_players_per_round[round_num]:
                    self.ui.selected_players_per_round[round_num]['implicit_selection'] = None

            for checkbox_var in self.ui.row_checkboxes:
                checkbox_var.set(0)

            for checkbox_var in self.ui.column_checkboxes:
                checkbox_var.set(0)

            self.ui._updating_dropdowns = False
            print("All round dropdowns cleared")
        except Exception as e:
            self.ui._updating_dropdowns = False
            print(f"Error clearing round dropdowns: {e}")

    def fill_round_dropdowns(self):
        """Fill all dropdowns with the first available option (for testing purposes)."""
        try:
            print("Starting to fill all round dropdowns with first available options...")
            self.clear_round_dropdowns()

            friendly_players = self.ui.get_friendly_player_names()
            enemy_players = self.ui.get_enemy_player_names()

            if not friendly_players or not enemy_players:
                print("Cannot fill dropdowns: teams not selected")
                messagebox.showwarning("Teams Required", "Please select both teams before using FILL.")
                return

            for round_num in range(1, 6):
                friendly_antes = (round_num % 2 == 1)
                self.update_round_dropdown_options(force=True)

                if friendly_antes:
                    dropdown_idx = self._get_friendly_ante_dropdown_index(round_num)
                    if dropdown_idx is not None and dropdown_idx < len(self.ui.round_dropdowns):
                        dropdown = self.ui.round_dropdowns[dropdown_idx]
                        values = dropdown['values']
                        if len(values) > 1:
                            first_option = values[1]
                            self.ui.round_vars[dropdown_idx].set(first_option)
                            self.ui.root.update_idletasks()

                    self.update_round_dropdown_options(force=True)

                    enemy_dropdown_indices = self._get_enemy_response_dropdown_indices(round_num)
                    for idx, enemy_idx in enumerate(enemy_dropdown_indices):
                        if enemy_idx < len(self.ui.enemy_round_dropdowns):
                            dropdown = self.ui.enemy_round_dropdowns[enemy_idx]
                            values = dropdown['values']
                            if len(values) > 1:
                                first_option = values[1]
                                self.ui.enemy_round_vars[enemy_idx].set(first_option)
                                self.ui.root.update_idletasks()
                                if idx == 0:
                                    self.update_round_dropdown_options(force=True)
                else:
                    dropdown_idx = self._get_enemy_ante_dropdown_index(round_num)
                    if dropdown_idx is not None and dropdown_idx < len(self.ui.enemy_round_dropdowns):
                        dropdown = self.ui.enemy_round_dropdowns[dropdown_idx]
                        values = dropdown['values']
                        if len(values) > 1:
                            first_option = values[1]
                            self.ui.enemy_round_vars[dropdown_idx].set(first_option)
                            self.ui.root.update_idletasks()

                    self.update_round_dropdown_options(force=True)

                    friendly_dropdown_indices = self._get_friendly_response_dropdown_indices(round_num)
                    for idx, friendly_idx in enumerate(friendly_dropdown_indices):
                        if friendly_idx < len(self.ui.round_dropdowns):
                            dropdown = self.ui.round_dropdowns[friendly_idx]
                            values = dropdown['values']
                            if len(values) > 1:
                                first_option = values[1]
                                self.ui.round_vars[friendly_idx].set(first_option)
                                self.ui.root.update_idletasks()
                                if idx == 0:
                                    self.update_round_dropdown_options(force=True)

            print("Finished filling all round dropdowns")
        except Exception as e:
            print(f"Error filling round dropdowns: {e}")
            messagebox.showerror("Fill Error", f"Failed to fill dropdowns: {e}")

    def _get_friendly_ante_dropdown_index(self, round_num):
        if round_num == 1:
            return 0
        if round_num == 3:
            return 3
        if round_num == 5:
            return 6
        return None

    def _get_enemy_ante_dropdown_index(self, round_num):
        if round_num == 2:
            return 2
        if round_num == 4:
            return 5
        return None

    def _get_enemy_response_dropdown_indices(self, round_num):
        if round_num == 1:
            return [0, 1]
        if round_num == 3:
            return [3, 4]
        if round_num == 5:
            return [6]
        return []

    def _get_friendly_response_dropdown_indices(self, round_num):
        if round_num == 2:
            return [1, 2]
        if round_num == 4:
            return [4, 5]
        return []

    def _update_ante_response_dropdowns(self, friendly_players, enemy_players):
        try:
            for round_num in range(1, 6):
                friendly_antes = (round_num % 2 == 1)

                if friendly_antes:
                    if round_num == 1:
                        available_friendly = self._get_available_friendly_players(round_num, friendly_players)
                    else:
                        available_friendly = self._get_friendly_ante_options(round_num)

                    dropdown_index = self._get_friendly_ante_dropdown_index(round_num)
                    if dropdown_index is not None and dropdown_index < len(self.ui.round_dropdowns):
                        self.ui.round_dropdowns[dropdown_index]['values'] = [""] + available_friendly

                    available_enemy = self._get_available_enemy_players(round_num, enemy_players)
                    enemy_indices = self._get_enemy_response_dropdown_indices(round_num)
                    if enemy_indices:
                        enemy_index = enemy_indices[0]
                        if enemy_index < len(self.ui.enemy_round_dropdowns):
                            self.ui.enemy_round_dropdowns[enemy_index]['values'] = [""] + available_enemy

                    if len(enemy_indices) > 1:
                        available_enemy_2 = self._get_available_enemy_players(round_num, enemy_players, exclude_current_response1=True)
                        enemy_index = enemy_indices[1]
                        if enemy_index < len(self.ui.enemy_round_dropdowns):
                            self.ui.enemy_round_dropdowns[enemy_index]['values'] = [""] + available_enemy_2
                else:
                    ante_options = self._get_enemy_ante_options(round_num)
                    enemy_index = self._get_enemy_ante_dropdown_index(round_num)
                    if enemy_index is not None and enemy_index < len(self.ui.enemy_round_dropdowns):
                        self.ui.enemy_round_dropdowns[enemy_index]['values'] = [""] + ante_options

                    available_friendly = self._get_available_friendly_players(round_num, friendly_players)
                    friendly_indices = self._get_friendly_response_dropdown_indices(round_num)
                    if friendly_indices:
                        friendly_index = friendly_indices[0]
                        if friendly_index < len(self.ui.round_dropdowns):
                            self.ui.round_dropdowns[friendly_index]['values'] = [""] + available_friendly

                    if len(friendly_indices) > 1:
                        available_friendly_2 = self._get_available_friendly_players(round_num, friendly_players, exclude_current_response1=True)
                        friendly_index = friendly_indices[1]
                        if friendly_index < len(self.ui.round_dropdowns):
                            self.ui.round_dropdowns[friendly_index]['values'] = [""] + available_friendly_2
        except Exception as e:
            print(f"Error updating ante/response dropdowns: {e}")

    def _get_enemy_ante_options(self, round_num):
        if round_num <= 1:
            return []

        previous_round = round_num - 1
        previous_round_data = self.ui.selected_players_per_round.get(previous_round, {})

        ante_options = []
        if previous_round_data.get('response_team') == 'enemy':
            if previous_round_data.get('response1'):
                ante_options.append(previous_round_data['response1'])
            if previous_round_data.get('response2'):
                ante_options.append(previous_round_data['response2'])

        return ante_options

    def _get_friendly_ante_options(self, round_num):
        if round_num <= 1:
            return []

        previous_round = round_num - 1
        previous_round_data = self.ui.selected_players_per_round.get(previous_round, {})

        ante_options = []
        if previous_round_data.get('response_team') == 'friendly':
            if previous_round_data.get('response1'):
                ante_options.append(previous_round_data['response1'])
            if previous_round_data.get('response2'):
                ante_options.append(previous_round_data['response2'])

        return ante_options

    def _get_available_friendly_players(self, round_num, all_friendly_players, exclude_current_response1=False):
        used_players = set()

        for r in range(1, round_num):
            round_data = self.ui.selected_players_per_round.get(r, {})
            if round_data.get('ante_team') == 'friendly' and round_data.get('ante'):
                used_players.add(round_data['ante'])
            if round_data.get('response_team') == 'friendly':
                if round_data.get('response1'):
                    used_players.add(round_data['response1'])
                if round_data.get('response2'):
                    used_players.add(round_data['response2'])

        current_round_data = self.ui.selected_players_per_round.get(round_num, {})
        if current_round_data.get('ante_team') == 'friendly' and current_round_data.get('ante'):
            used_players.add(current_round_data['ante'])

        if exclude_current_response1 and current_round_data.get('response_team') == 'friendly':
            if current_round_data.get('response1'):
                used_players.add(current_round_data['response1'])

        return [player for player in all_friendly_players if player not in used_players]

    def _get_available_enemy_players(self, round_num, all_enemy_players, exclude_current_response1=False):
        used_players = set()

        for r in range(1, round_num):
            round_data = self.ui.selected_players_per_round.get(r, {})
            if round_data.get('ante_team') == 'enemy' and round_data.get('ante'):
                used_players.add(round_data['ante'])
            if round_data.get('response_team') == 'enemy':
                if round_data.get('response1'):
                    used_players.add(round_data['response1'])
                if round_data.get('response2'):
                    used_players.add(round_data['response2'])

        current_round_data = self.ui.selected_players_per_round.get(round_num, {})
        if current_round_data.get('ante_team') == 'enemy' and current_round_data.get('ante'):
            used_players.add(current_round_data['ante'])

        if exclude_current_response1 and current_round_data.get('response_team') == 'enemy':
            if current_round_data.get('response1'):
                used_players.add(current_round_data['response1'])

        return [player for player in all_enemy_players if player not in used_players]
