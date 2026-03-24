""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """

from itertools import combinations, permutations
import tkinter
import math
import hashlib
import json

import qtr_pairing_process.utility_funcs as uf
from qtr_pairing_process.constants import RATING_SYSTEMS, DEFAULT_RATING_SYSTEM

class TreeGenerator:
    def __init__(
        self,
        treeview,
        sort_alpha=False,
        strategic_preferences=None,
        rating_system=DEFAULT_RATING_SYSTEM,
    ):
        self.treeview = treeview
        self.sort_alpha = bool(sort_alpha)
        self.original_order = {}
        self.fRatings = None
        self.our_team_first = True  # Will be set during generation
        self.rating_system = DEFAULT_RATING_SYSTEM
        self.rating_min = 1
        self.rating_max = 5
        self.rating_display_max = 5
        self.set_rating_system(rating_system)

        # Runtime-tunable strategic/v2 parameters.
        self.strategic_preferences = strategic_preferences or {}
        self.cumulative2_alpha = self._read_numeric_pref(("cumulative2", "alpha"), 0.80, 0.0, 1.0)
        self.confidence2_k = self._read_numeric_pref(("confidence2", "k"), 0.85, 0.0, 5.0)
        self.confidence2_u = self._read_numeric_pref(("confidence2", "u"), 12.0, 0.0, 100.0)
        self.resistance2_beta = self._read_numeric_pref(("resistance2", "beta"), 1.0, 0.0, 10.0)
        self.resistance2_gamma = self._read_numeric_pref(("resistance2", "gamma"), 2.0, 0.0, 10.0)

        raw_weights = self._read_raw_pref(("strategic3", "weights"), [0.40, 0.35, 0.25])
        if not isinstance(raw_weights, list) or len(raw_weights) != 3:
            raw_weights = [0.40, 0.35, 0.25]
        safe_weights = [self._clamp(float(w), 0.0, 1.0) for w in raw_weights]
        weight_sum = sum(safe_weights)
        if weight_sum <= 0:
            self.strategic3_weights = (0.40, 0.35, 0.25)
        else:
            self.strategic3_weights = tuple(w / weight_sum for w in safe_weights)
        self.strategic3_rho = self._read_numeric_pref(("strategic3", "rho"), 0.20, 0.0, 5.0)
        self.strategic3_lam = self._read_numeric_pref(("strategic3", "lam"), 0.30, 0.0, 5.0)
        self._generation_id = 0
        self._memo_state_token = None
        self._strategic_memo_context = None
        self._strategic_memo = {}
        self._strategic_memo_hits = 0
        self._strategic_memo_misses = 0
        self._memo_clear_count = 0
        self._memo_last_clear_reason = ""
        self._memo_last_clear_bucket = ""
        self._memo_last_cleared_entries = 0
        self._memo_key_mode = "structural_path_text_base_rating"
        self._memo_schema_version = 1
        self.persistent_memo_enabled = bool(
            self._read_raw_pref(("strategic3", "persistent_memo_enabled"), True)
        )
        self.persistent_memo_max_entries = int(
            self._read_numeric_pref(("strategic3", "persistent_memo_max_entries"), 50000, 1000, 250000)
        )
        self._suppress_display_updates = False
        self._confidence_aux_tags_enabled = True
        self._materialize_strategic_tags_on_memo_hit = True
        self.reset_strategic_profile_stats()

    def set_rating_system(self, rating_system):
        if rating_system not in RATING_SYSTEMS:
            rating_system = DEFAULT_RATING_SYSTEM
        self.rating_system = rating_system
        self.rating_min, self.rating_max = RATING_SYSTEMS[rating_system]['range']
        self.rating_display_max = int(self.rating_max)

    def _to_reference_rating(self, rating):
        """Normalize active system ratings onto a 1-5 reference scale."""
        try:
            r = int(rating)
        except (TypeError, ValueError):
            return 0

        low = int(self.rating_min)
        high = int(self.rating_max)
        r = max(low, min(high, r))
        if high <= low:
            return 3

        normalized = 1.0 + ((r - low) / float(high - low)) * 4.0
        return int(round(normalized))

    def _read_raw_pref(self, path, fallback):
        current = self.strategic_preferences
        try:
            for key in path:
                current = current.get(key, {})
            value = current
        except AttributeError:
            value = fallback

        if value == {}:
            value = fallback

        return value

    def _read_pref(self, path, fallback, min_value=None, max_value=None):
        """Compatibility wrapper for legacy callers.

        Prefer `_read_raw_pref` for non-numeric values and `_read_numeric_pref`
        for clamped numeric values.
        """
        if min_value is None or max_value is None:
            return self._read_raw_pref(path, fallback)
        return self._read_numeric_pref(path, fallback, min_value, max_value)

    def _read_numeric_pref(self, path, fallback, min_value, max_value):
        value = self._read_raw_pref(path, fallback)

        if not isinstance(value, (int, float, str)):
            return fallback

        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return fallback

        return self._clamp(numeric, min_value, max_value)

    def generate_combinations(self, fNames, oNames, fRatings, oRatings, our_team_first=True):
        self.fRatings = fRatings
        self.our_team_first = our_team_first
        self.treeview.tree.delete(*self.treeview.tree.get_children())
        # Reset sorting state for new generation
        self.original_order_saved = False
        tree_top = self.treeview.tree.insert("", 'end', text="Pairings")
        fNames_sorted = list(fNames)
        oNames_sorted = list(oNames)
        if self.sort_alpha:
            fNames_sorted.sort()
            oNames_sorted.sort()
        
        for name in fNames_sorted:
            fnames_filtered = [x for x in fNames_sorted if x!=name]

            # print(f"Top Level: {name} in {fNames_sorted}")
            self.generate_nested_combinations(name, fnames_filtered, oNames_sorted, fRatings, oRatings, tree_top)
            fNames_sorted[:] = uf.cycle_list(fNames_sorted)
            # oNames_sorted[:] = cycle_list(oNames_sorted)
        
    def generate_nested_combinations(self, first_fName, fNames, oNames, fRatings, oRatings, parent):
        
        combs = list(combinations(oNames, 2))
        if oNames and not combs:
            first_oName = oNames[0]
            combs = list(combinations([first_oName,first_oName], 2))
        combs_sorted = sorted(combs) if self.sort_alpha else combs
        for comb in combs_sorted:
            rating_0 = fRatings[first_fName].get(comb[0], 'N/A')
            rating_1 = fRatings[first_fName].get(comb[1], 'N/A')
            # Calculate all three score types for this pairing
            base_rating = max(rating_0, rating_1)
            cumulative_score = 0  # Will be calculated later during sort operations
            confidence_score = self.calculate_confidence_for_rating(base_rating)
            resistance_score = self.calculate_resistance_for_rating(base_rating, rating_0, rating_1)

            item_id = self.treeview.tree.insert(
                parent,
                'end',
                text=f"{first_fName} vs {comb[0]} ({rating_0}/{self.rating_display_max}) OR {comb[1]} ({rating_1}/{self.rating_display_max})",
                values=(base_rating, cumulative_score, confidence_score, resistance_score),
                tags=base_rating,
            )
            
            if fNames:
                opponent_perms = list(permutations(comb, 2))
                if self.sort_alpha:
                    opponent_perms = sorted(opponent_perms)
                for opponent, next_fName in opponent_perms:                    
                    nested_oNames = [name for name in oNames if name != opponent and name!=next_fName]
                    nested_fNames = [name for name in fNames if name != first_fName]
                    # Calculate scores for child node
                    child_rating = fRatings[first_fName].get(opponent, 0)
                    child_cumulative = 0  # Will be calculated during sort operations
                    child_confidence = self.calculate_confidence_for_rating(child_rating)
                    child_resistance = self.calculate_resistance_for_rating(child_rating, child_rating, child_rating)

                    child_id = self.treeview.tree.insert(
                        item_id,
                        'end',
                        text=f"{opponent} rating {child_rating}",
                        values=(child_rating, child_cumulative, child_confidence, child_resistance),
                        tags=child_rating,
                    )
                    self.generate_nested_combinations(next_fName,nested_oNames, fNames, oRatings, fRatings, child_id)

    def sort_by_cumulative_value(self):
        """Sort all tree branches by their cumulative path values (best to worst)"""
        root_nodes = self.treeview.tree.get_children()
        if root_nodes:
            # Save original order before first sort
            if not hasattr(self, 'original_order_saved') or not self.original_order_saved:
                self.save_original_order()
                self.original_order_saved = True
            
            # First, calculate cumulative values for all complete paths
            self.calculate_all_path_values("")
            # Then sort recursively from root
            for root in root_nodes:
                self.sort_children_by_cumulative(root)

    def calculate_all_path_values(self, node):
        """Calculate and store cumulative values for all paths in the tree"""
        children = self.treeview.tree.get_children(node)
        
        if not children:
            # This is a leaf node, its cumulative value is its own value
            if node:  # Skip empty root
                try:
                    leaf_value = int(self.treeview.tree.item(node, 'values')[0])
                    item_data = self.treeview.tree.item(node)
                    current_tags = list(item_data.get('tags', []))
                    # Remove any existing cumulative tag and add new one
                    current_tags = [tag for tag in current_tags if not str(tag).startswith('cumulative_')]
                    current_tags.append(f'cumulative_{leaf_value}')
                    self.treeview.tree.item(node, tags=current_tags)

                    # Update the cumulative score column (index 1)
                    self.update_node_cumulative_display(node, leaf_value)
                    return leaf_value
                except (ValueError, IndexError):
                    item_data = self.treeview.tree.item(node)
                    current_tags = list(item_data.get('tags', []))
                    current_tags = [tag for tag in current_tags if not str(tag).startswith('cumulative_')]
                    current_tags.append('cumulative_0')
                    self.treeview.tree.item(node, tags=current_tags)
                    return 0
            return 0
        else:
            # This is a branch node, calculate cumulative value from all its complete paths
            max_cumulative = 0
            for child in children:
                child_cumulative = self.calculate_all_path_values(child)
                if node:  # Skip empty root
                    try:
                        node_value = int(self.treeview.tree.item(node, 'values')[0])
                        total_cumulative = node_value + child_cumulative
                        max_cumulative = max(max_cumulative, total_cumulative)
                    except (ValueError, IndexError):
                        max_cumulative = max(max_cumulative, child_cumulative)
                else:
                    max_cumulative = max(max_cumulative, child_cumulative)
            
            if node:  # Skip empty root
                # Store cumulative value in tags and update display
                item_data = self.treeview.tree.item(node)
                current_tags = list(item_data.get('tags', []))
                current_tags = [tag for tag in current_tags if not str(tag).startswith('cumulative_')]
                current_tags.append(f'cumulative_{max_cumulative}')
                self.treeview.tree.item(node, tags=current_tags)

                # Update the cumulative score column (index 1)
                self.update_node_cumulative_display(node, max_cumulative)
            return max_cumulative

    def sort_children_by_cumulative(self, node):
        """Recursively sort children by their cumulative path values"""
        children = self.treeview.tree.get_children(node)
        if not children:
            return
        
        # Get cumulative values for all children
        children_with_scores = []
        for child in children:
            cumulative_value = self.get_cumulative_value_from_tags(child)
            children_with_scores.append((child, cumulative_value))

        # Determine if this is an opponent decision level or our choice level
        # Use the first child to determine the level, since all children are at the same level
        is_opponent_choice_level = self._is_opponent_choice_level(children[0])

        if is_opponent_choice_level:
            # Opponent choice level: Sort by LOWEST cumulative value first (opponent picks what's worst for us)
            children_with_scores.sort(key=lambda x: x[1], reverse=False)
        else:
            # Our choice level: Sort by HIGHEST cumulative value first (we pick what's best for us)
            children_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Reorder children in the tree
        for child, _ in children_with_scores:
            self.treeview.tree.detach(child)
        for child, _ in children_with_scores:
            self.treeview.tree.move(child, node, 'end')
        
        # Recursively sort grandchildren
        for child, _ in children_with_scores:
            self.sort_children_by_cumulative(child)

    def get_cumulative_value_from_tags(self, node):
        """Extract cumulative value from node tags"""
        try:
            item_data = self.treeview.tree.item(node)
            tags = item_data.get('tags', [])
            for tag in tags:
                if str(tag).startswith('cumulative_'):
                    return int(str(tag).replace('cumulative_', ''))
        except (ValueError, TypeError):
            pass
        return 0

    def sort_by_risk_adjusted_confidence(self):
        """Sort tree branches by risk-adjusted confidence scores (reliable outcomes prioritized)"""
        root_nodes = self.treeview.tree.get_children()
        if root_nodes:
            # Save original order before first sort
            if not hasattr(self, 'original_order_saved') or not self.original_order_saved:
                self.save_original_order()
                self.original_order_saved = True
            
            # Calculate confidence scores for all paths
            self.calculate_confidence_scores("")
            # Sort recursively from root
            for root in root_nodes:
                self.sort_children_by_confidence(root)

    def calculate_confidence_scores(self, node):
        """Calculate risk-adjusted confidence scores for all paths"""
        children = self.treeview.tree.get_children(node)
        
        if not children:
            # Leaf node - calculate floor, ceiling, and confidence
            if node:
                try:
                    leaf_value = int(self.treeview.tree.item(node, 'values')[0])
                    # For leaf nodes, confidence is based on rating value
                    # Higher ratings (4-5) = high confidence, middle (3) = medium, low (1-2) = low confidence
                    confidence_score = self.calculate_rating_confidence(leaf_value)
                    self.store_confidence_data(node, leaf_value, leaf_value, confidence_score)
                    return leaf_value, leaf_value, confidence_score
                except (ValueError, IndexError):
                    self.store_confidence_data(node, 0, 0, 0)
                    return 0, 0, 0
            return 0, 0, 0
        else:
            # Branch node - aggregate from children
            path_floors = []
            path_ceilings = []
            path_confidences = []
            
            for child in children:
                child_floor, child_ceiling, child_confidence = self.calculate_confidence_scores(child)
                if node:
                    try:
                        node_value = int(self.treeview.tree.item(node, 'values')[0])
                        node_confidence = self.calculate_rating_confidence(node_value)
                        
                        total_floor = node_value + child_floor
                        total_ceiling = node_value + child_ceiling
                        # Combined confidence considers both current rating and path reliability
                        combined_confidence = (node_confidence + child_confidence) / 2
                        
                        path_floors.append(total_floor)
                        path_ceilings.append(total_ceiling)
                        path_confidences.append(combined_confidence)
                    except (ValueError, IndexError):
                        path_floors.append(child_floor)
                        path_ceilings.append(child_ceiling)
                        path_confidences.append(child_confidence)
                else:
                    path_floors.append(child_floor)
                    path_ceilings.append(child_ceiling)
                    path_confidences.append(child_confidence)
            
            if node and path_floors and path_ceilings and path_confidences:
                # Use the best-case scenario from available paths
                best_floor = max(path_floors)
                best_ceiling = max(path_ceilings)
                # Weight confidence by variance (lower variance = higher confidence)
                avg_confidence = sum(path_confidences) / len(path_confidences)
                variance_penalty = self.calculate_variance_penalty(path_floors + path_ceilings)
                final_confidence = avg_confidence - variance_penalty
                
                self.store_confidence_data(node, best_floor, best_ceiling, final_confidence)
                return best_floor, best_ceiling, final_confidence
            
            return 0, 0, 0

    def calculate_rating_confidence(self, rating):
        """Convert rating value to confidence score (0-100)"""
        ref_rating = self._to_reference_rating(rating)
        confidence_map = {
            5: 95,  # Very high confidence - almost certain win
            4: 80,  # High confidence - strong advantage
            3: 60,  # Medium confidence - even matchup
            2: 35,  # Low confidence - disadvantage
            1: 15   # Very low confidence - likely loss
        }
        return confidence_map.get(ref_rating, 50)

    def calculate_variance_penalty(self, values):
        """Calculate penalty for high variance in path values"""
        if len(values) < 2:
            return 0
        
        mean_val = sum(values) / len(values)
        variance = sum((x - mean_val) ** 2 for x in values) / len(values)
        # Normalize variance to a 0-20 penalty scale
        max_variance = 16  # Theoretical max for ratings 1-5
        penalty = min(20, (variance / max_variance) * 20)
        return penalty

    def store_confidence_data(self, node, floor_val, ceiling_val, confidence):
        """Store confidence analysis data in node tags"""
        try:
            item_data = self.treeview.tree.item(node)
            current_tags = list(item_data.get('tags', []))
            
            # Remove existing confidence tags
            current_tags = [tag for tag in current_tags if not any(
                str(tag).startswith(prefix) for prefix in ['confidence_', 'floor_', 'ceiling_']
            )]
            
            # Add new confidence data
            current_tags.extend([
                f'confidence_{int(confidence)}',
                f'floor_{floor_val}',
                f'ceiling_{ceiling_val}'
            ])
            
            self.treeview.tree.item(node, tags=current_tags)

            # Update the confidence score column (index 2)
            self.update_node_confidence_display(node, confidence)
        except Exception:
            pass

    def sort_children_by_confidence(self, node):
        """Recursively sort children by their confidence scores"""
        children = self.treeview.tree.get_children(node)
        if not children:
            return
        
        # Get confidence scores for all children
        children_with_scores = []
        for child in children:
            confidence_score = self.get_confidence_from_tags(child)
            children_with_scores.append((child, confidence_score))

        # Determine if this is an opponent decision level or our choice level
        # Use the first child to determine the level, since all children are at the same level
        is_opponent_choice_level = self._is_opponent_choice_level(children[0])

        if is_opponent_choice_level:
            # Opponent choice level: Sort by LOWEST confidence first (opponent picks what's least confident for us)
            children_with_scores.sort(key=lambda x: x[1], reverse=False)
        else:
            # Our choice level: Sort by HIGHEST confidence first (we pick what's most confident)
            children_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Reorder children in the tree
        for child, _ in children_with_scores:
            self.treeview.tree.detach(child)
        for child, _ in children_with_scores:
            self.treeview.tree.move(child, node, 'end')
        
        # Recursively sort grandchildren
        for child, _ in children_with_scores:
            self.sort_children_by_confidence(child)

    def get_confidence_from_tags(self, node):
        """Extract confidence score from node tags"""
        try:
            item_data = self.treeview.tree.item(node)
            tags = item_data.get('tags', [])
            for tag in tags:
                if str(tag).startswith('confidence_'):
                    return int(str(tag).replace('confidence_', ''))
        except (ValueError, TypeError):
            pass
        return 0

    def sort_by_opponent_response_simulation(self):
        """Sort tree branches by performance against optimal opponent counter-strategies"""
        root_nodes = self.treeview.tree.get_children()
        if root_nodes:
            # Save original order before first sort
            if not hasattr(self, 'original_order_saved') or not self.original_order_saved:
                self.save_original_order()
                self.original_order_saved = True
            
            # Calculate counter-resistance scores for all paths
            self.calculate_counter_resistance_scores("")
            # Sort recursively from root
            for root in root_nodes:
                self.sort_children_by_counter_resistance(root)

    def calculate_counter_resistance_scores(self, node):
        """Calculate how well each path performs against opponent counter-strategies"""
        children = self.treeview.tree.get_children(node)
        
        if not children:
            # Leaf node - evaluate counter-resistance
            if node:
                try:
                    leaf_value = int(self.treeview.tree.item(node, 'values')[0])
                    # Counter-resistance based on rating stability
                    counter_resistance = self.calculate_counter_resistance(leaf_value)
                    self.store_counter_resistance_data(node, counter_resistance)
                    return counter_resistance
                except (ValueError, IndexError):
                    self.store_counter_resistance_data(node, 0)
                    return 0
            return 0
        else:
            # Branch node - simulate opponent responses
            path_resistances = []
            
            for child in children:
                child_resistance = self.calculate_counter_resistance_scores(child)
                if node:
                    try:
                        node_value = int(self.treeview.tree.item(node, 'values')[0])
                        node_resistance = self.calculate_counter_resistance(node_value)
                        
                        # Simulate opponent counter-strategy
                        # Opponent will try to exploit our weaknesses
                        opponent_counter_effectiveness = self.simulate_opponent_counter(node_value)
                        adjusted_resistance = (node_resistance + child_resistance) / 2
                        adjusted_resistance *= (1 - opponent_counter_effectiveness)
                        
                        path_resistances.append(adjusted_resistance)
                    except (ValueError, IndexError):
                        path_resistances.append(child_resistance)
                else:
                    path_resistances.append(child_resistance)
            
            if node and path_resistances:
                # Use the most counter-resistant path
                best_resistance = max(path_resistances)
                self.store_counter_resistance_data(node, best_resistance)
                return best_resistance
            
            return 0

    def calculate_counter_resistance(self, rating):
        """Calculate how resistant a rating is to opponent counters"""
        ref_rating = self._to_reference_rating(rating)
        # Higher ratings are more vulnerable to counters (opponent focuses best players)
        # Middle ratings (3) are most counter-resistant (opponent wastes effort)
        resistance_map = {
            5: 60,  # High value but vulnerable to focus-fire
            4: 75,  # Good value with moderate vulnerability  
            3: 85,  # Most counter-resistant - opponent indifferent
            2: 70,  # Low value but opponent may ignore
            1: 50   # Very low value, opponent will exploit
        }
        return resistance_map.get(ref_rating, 60)

    def simulate_opponent_counter(self, our_rating):
        """Simulate how effectively opponent can counter our strategy"""
        ref_rating = self._to_reference_rating(our_rating)
        # Opponent counter-effectiveness based on our rating pattern
        if ref_rating >= 4:
            # High ratings draw opponent's best counters
            return 0.3  # 30% effectiveness reduction
        elif ref_rating == 3:
            # Medium ratings are hardest to counter
            return 0.1  # 10% effectiveness reduction
        else:
            # Low ratings - opponent may not need to counter hard
            return 0.2  # 20% effectiveness reduction

    def store_counter_resistance_data(self, node, resistance):
        """Store counter-resistance data in node tags"""
        try:
            self._replace_prefixed_tags(node, {'resistance_': resistance})

            # Update the resistance score column (index 3)
            self.update_node_resistance_display(node, resistance)
        except Exception:
            pass

    def sort_children_by_counter_resistance(self, node):
        """Recursively sort children by their counter-resistance scores"""
        children = self.treeview.tree.get_children(node)
        if not children:
            return
        
        # Get counter-resistance scores for all children
        children_with_scores = []
        for child in children:
            resistance_score = self.get_resistance_from_tags(child)
            children_with_scores.append((child, resistance_score))

        # Determine if this is an opponent decision level or our choice level
        # Use the first child to determine the level, since all children are at the same level
        is_opponent_choice_level = self._is_opponent_choice_level(children[0])

        if is_opponent_choice_level:
            # Opponent choice level: Sort by LOWEST resistance first (opponent picks what's least resistant for us)
            children_with_scores.sort(key=lambda x: x[1], reverse=False)
        else:
            # Our choice level: Sort by HIGHEST resistance first (we pick what's most counter-resistant)
            children_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Reorder children in the tree
        for child, _ in children_with_scores:
            self.treeview.tree.detach(child)
        for child, _ in children_with_scores:
            self.treeview.tree.move(child, node, 'end')
        
        # Recursively sort grandchildren
        for child, _ in children_with_scores:
            self.sort_children_by_counter_resistance(child)

    def get_resistance_from_tags(self, node):
        """Extract counter-resistance score from node tags"""
        try:
            item_data = self.treeview.tree.item(node)
            tags = item_data.get('tags', [])
            for tag in tags:
                if str(tag).startswith('resistance_'):
                    return int(str(tag).replace('resistance_', ''))
        except (ValueError, TypeError):
            pass
        return 0

    def get_cumulative_from_tags(self, node):
        """Extract cumulative value from node tags"""
        try:
            item_data = self.treeview.tree.item(node)
            tags = item_data.get('tags', [])
            for tag in tags:
                if str(tag).startswith('cumulative_'):
                    return int(str(tag).replace('cumulative_', ''))
        except (ValueError, TypeError):
            pass
        return 0

    def _replace_prefixed_tag(self, node, prefix, value):
        """Replace all tags with given prefix and add a new value tag."""
        item_data = self.treeview.tree.item(node)
        current_tags = list(item_data.get('tags', []))
        current_tags = [tag for tag in current_tags if not str(tag).startswith(prefix)]
        current_tags.append(f"{prefix}{int(value)}")
        self.treeview.tree.item(node, tags=current_tags)

    def _replace_prefixed_tags(self, node, prefix_values):
        """Replace multiple prefixed tags with a single tree item write."""
        if not prefix_values:
            return

        item_data = self.treeview.tree.item(node)
        current_tags = list(item_data.get('tags', []))
        prefixes = tuple(prefix_values.keys())
        current_tags = [
            tag for tag in current_tags
            if not any(str(tag).startswith(prefix) for prefix in prefixes)
        ]

        for prefix, value in prefix_values.items():
            current_tags.append(f"{prefix}{int(value)}")

        self.treeview.tree.item(node, tags=current_tags)

    def _extract_prefixed_tag_value(self, node, prefix, default=0):
        """Read an integer tag value by prefix from a tree node."""
        try:
            item_data = self.treeview.tree.item(node)
            tags = item_data.get('tags', [])
            for tag in tags:
                tag_str = str(tag)
                if tag_str.startswith(prefix):
                    suffix = tag_str[len(prefix):]
                    try:
                        return int(suffix)
                    except ValueError:
                        # Ignore non-numeric sibling prefixes, e.g. strategic3_exploit_
                        # when reading strategic3_.
                        continue
        except TypeError:
            pass
        return default

    def _has_prefixed_tag(self, node, prefix):
        """Return True when node has at least one tag with the given prefix."""
        try:
            item_data = self.treeview.tree.item(node)
            tags = item_data.get('tags', [])
            return any(str(tag).startswith(prefix) for tag in tags)
        except TypeError:
            return False

    def reset_strategic_profile_stats(self):
        self._strategic_profile_stats = {
            "nodes_visited": 0,
            "range_nodes": 0,
            "memo_hits": 0,
            "memo_misses": 0,
            "memo_materialized": 0,
            "memo_fastpath_reads": 0,
            "materialize_recursions": 0,
            "tag_writes": 0,
        }

    def get_strategic_profile_stats(self):
        return dict(getattr(self, "_strategic_profile_stats", {}))

    def _materialize_strategic_descendants_from_memo(self, node, weights, rho, lam):
        """Populate missing descendant strategic tags from memo before falling back to recompute."""
        for child in self.treeview.tree.get_children(node):
            if self._has_prefixed_tag(child, 'strategic3_'):
                continue

            self._strategic_profile_stats["nodes_visited"] += 1
            child_key = self._build_structural_memo_key(child)
            memo_value = self._strategic_memo.get(child_key)
            if memo_value is None:
                self._strategic_profile_stats["materialize_recursions"] += 1
                self.calculate_strategic3_scores(child, weights=weights, rho=rho, lam=lam)
                continue

            self._strategic_memo_hits += 1
            self._strategic_profile_stats["memo_hits"] += 1
            self._replace_prefixed_tags(child, {'strategic3_': int(memo_value)})
            self._strategic_profile_stats["tag_writes"] += 1
            self._strategic_profile_stats["memo_materialized"] += 1
            self.update_node_strategic_display(child, int(memo_value))
            self._materialize_strategic_descendants_from_memo(child, weights=weights, rho=rho, lam=lam)

    def _clamp(self, value, min_value, max_value):
        return max(min_value, min(max_value, value))

    def clear_memoization(self, reason=""):
        """Clear strategic memoization cache. Optional reason for diagnostics."""
        cleared_entries = len(self._strategic_memo)
        normalized_reason = str(reason or "unspecified")
        self._memo_clear_count += 1
        self._memo_last_clear_reason = normalized_reason
        self._memo_last_clear_bucket = self._classify_clear_reason(normalized_reason)
        self._memo_last_cleared_entries = cleared_entries
        self._strategic_memo_context = None
        self._strategic_memo = {}

    def _classify_clear_reason(self, reason):
        normalized = str(reason or "").strip().lower()
        if normalized in {"memo_state_change"}:
            return "state_change"
        if normalized in {"memo_context_change"}:
            return "context_mismatch"
        if "param" in normalized:
            return "param_change"
        if "clear_" in normalized and "cache" in normalized:
            return "tree_cache_reset"
        if normalized.startswith("manual"):
            return "manual_clear"
        return "state_change"

    def set_generation_id(self, generation_id):
        """Set tree generation token used for diagnostics and cache bookkeeping."""
        try:
            normalized = int(generation_id)
        except (TypeError, ValueError):
            normalized = 0
        self._generation_id = normalized

    def set_memo_state_token(self, token):
        """Set memo state token and clear memo only when score-relevant state changes."""
        normalized = None if token is None else str(token)
        if normalized != self._memo_state_token:
            self._memo_state_token = normalized
            self.clear_memoization(reason="memo_state_change")

    def get_memoization_stats(self):
        """Return cumulative memoization statistics for strategic scoring."""
        total = self._strategic_memo_hits + self._strategic_memo_misses
        hit_rate = (self._strategic_memo_hits / total) if total else 0.0
        context_repr = repr(self._strategic_memo_context)
        context_hash = hashlib.sha1(context_repr.encode("utf-8")).hexdigest()[:12]
        return {
            "hits": self._strategic_memo_hits,
            "misses": self._strategic_memo_misses,
            "hit_rate": hit_rate,
            "entries": len(self._strategic_memo),
            "clear_count": self._memo_clear_count,
            "last_clear_reason": self._memo_last_clear_reason,
            "last_clear_bucket": self._memo_last_clear_bucket,
            "last_cleared_entries": self._memo_last_cleared_entries,
            "memo_context_hash": context_hash,
            "memo_key_mode": self._memo_key_mode,
            "memo_clear_reason": self._memo_last_clear_reason,
            "memo_clear_bucket": self._memo_last_clear_bucket,
            "memo_cleared_entries": self._memo_last_cleared_entries,
        }

    def _compute_parameter_signature(self):
        guardrail_strength = self._get_guardrail_strength()
        return (
            tuple(round(w, 6) for w in self.strategic3_weights),
            round(float(self.strategic3_rho), 6),
            round(float(self.strategic3_lam), 6),
            guardrail_strength,
        )

    def _get_guardrail_strength(self):
        return str(
            self.strategic_preferences.get('strategic3', {}).get('round_win_guardrail_strength', 'medium')
        ).lower()

    def _get_guardrail_coefficient(self):
        return {
            'low': 0.08,
            'medium': 0.14,
            'high': 0.22,
        }.get(self._get_guardrail_strength(), 0.14)

    def _build_strategic_memo_context(self):
        return ("strategic3", self._compute_parameter_signature(), self._memo_state_token)

    def _build_structural_memo_key(self, node):
        """Build a stable node signature from root-to-node text/value path."""
        lineage = []
        current = node
        while current:
            item = self.treeview.tree.item(current)
            text = str(item.get('text', ''))
            values = item.get('values', ())
            base_rating = values[0] if values else None
            lineage.append((text, base_rating))
            current = self.treeview.tree.parent(current)
        lineage.reverse()
        return tuple(lineage)

    def get_memo_state_token(self):
        return self._memo_state_token

    def get_memo_schema_version(self) -> int:
        return int(self._memo_schema_version)

    def get_persistent_memo_signature(self):
        return {
            "schema_version": self.get_memo_schema_version(),
            "parameter_signature": self._compute_parameter_signature(),
            "memo_state_token": self.get_memo_state_token(),
            "memo_key_mode": self._memo_key_mode,
        }

    def export_memoization_snapshot(self, max_entries=None):
        if not self.persistent_memo_enabled:
            return None
        if self._strategic_memo_context is None or not self._strategic_memo:
            return None

        entry_cap = int(max_entries if max_entries is not None else self.persistent_memo_max_entries)
        entry_cap = max(1, entry_cap)

        entries = []
        for idx, (memo_key, score) in enumerate(self._strategic_memo.items()):
            if idx >= entry_cap:
                break
            entries.append([
                json.loads(json.dumps(memo_key, ensure_ascii=False, default=str)),
                int(score),
            ])

        return {
            "schema_version": self.get_memo_schema_version(),
            "memo_key_mode": self._memo_key_mode,
            "memo_context": json.loads(json.dumps(self._strategic_memo_context, ensure_ascii=False, default=str)),
            "memo_state_token": self.get_memo_state_token(),
            "parameter_signature": json.loads(json.dumps(self._compute_parameter_signature(), ensure_ascii=False, default=str)),
            "entries": entries,
        }

    def _tupleize_nested(self, value):
        if isinstance(value, list):
            return tuple(self._tupleize_nested(item) for item in value)
        return value

    def import_memoization_snapshot(self, payload):
        if not self.persistent_memo_enabled:
            return False
        if not isinstance(payload, dict):
            return False

        schema_version = int(payload.get("schema_version", 0) or 0)
        if schema_version != self.get_memo_schema_version():
            return False
        if payload.get("memo_key_mode") != self._memo_key_mode:
            return False

        state_token = payload.get("memo_state_token")
        if state_token != self.get_memo_state_token():
            return False

        persisted_params = self._tupleize_nested(payload.get("parameter_signature"))
        if persisted_params != self._compute_parameter_signature():
            return False

        persisted_context = self._tupleize_nested(payload.get("memo_context"))
        if persisted_context != self._build_strategic_memo_context():
            return False

        restored = {}
        for item in payload.get("entries", []):
            if not isinstance(item, list) or len(item) != 2:
                continue
            key_raw, score_raw = item
            key_tuple = self._tupleize_nested(key_raw)
            try:
                restored[key_tuple] = int(score_raw)
            except (TypeError, ValueError):
                continue

        if not restored:
            return False

        if all(v == 0 for v in restored.values()):
            return False

        self._strategic_memo_context = persisted_context
        self._strategic_memo = restored
        return True

    def calculate_all_path_values_enhanced(self, node, alpha=None):
        """Enhanced cumulative scoring that is optimistic for us and adversarial for opponent turns."""
        alpha = self.cumulative2_alpha if alpha is None else alpha
        children = self.treeview.tree.get_children(node)

        if not children:
            if node:
                try:
                    leaf_value = int(self.treeview.tree.item(node, 'values')[0])
                    self._replace_prefixed_tag(node, 'cumulative2_', leaf_value)
                    self.update_node_cumulative_display(node, leaf_value)
                    return leaf_value
                except (ValueError, IndexError):
                    self._replace_prefixed_tag(node, 'cumulative2_', 0)
                    self.update_node_cumulative_display(node, 0)
                    return 0
            return 0

        child_scores = [self.calculate_all_path_values_enhanced(child, alpha=alpha) for child in children]

        if node:
            try:
                node_value = int(self.treeview.tree.item(node, 'values')[0])
            except (ValueError, IndexError):
                node_value = 0

            is_opp_level = self._is_opponent_choice_level(children[0]) if children else False
            if is_opp_level:
                min_child = min(child_scores)
                mean_child = sum(child_scores) / max(1, len(child_scores))
                child_component = alpha * min_child + (1.0 - alpha) * mean_child
            else:
                child_component = max(child_scores)

            total_value = int(round(node_value + child_component))
            self._replace_prefixed_tag(node, 'cumulative2_', total_value)
            self.update_node_cumulative_display(node, total_value)
            return total_value

        return max(child_scores) if child_scores else 0

    def get_cumulative2_from_tags(self, node):
        """Extract enhanced cumulative value from node tags."""
        return self._extract_prefixed_tag_value(node, 'cumulative2_', default=0)

    def calculate_confidence_scores_enhanced(self, node, k=None, u=None):
        """Enhanced confidence with volatility and sample-size penalties."""
        k = self.confidence2_k if k is None else k
        u = self.confidence2_u if u is None else u
        write_aux_tags = bool(getattr(self, "_confidence_aux_tags_enabled", True))
        children = self.treeview.tree.get_children(node)

        if not children:
            if node:
                try:
                    rating = int(self.treeview.tree.item(node, 'values')[0])
                except (ValueError, IndexError):
                    rating = 0
                base_conf = self.calculate_rating_confidence(rating)
                score = int(self._clamp(base_conf, 0, 100))
                prefix_values = {'confidence2_': score, 'regret2_': 0}
                if write_aux_tags:
                    prefix_values['floor2_'] = score
                    prefix_values['ceiling2_'] = score
                self._replace_prefixed_tags(node, prefix_values)
                self.update_node_confidence_display(node, score)
                return score, score, score
            return 0, 0, 0

        child_triplets = [self.calculate_confidence_scores_enhanced(child, k=k, u=u) for child in children]
        child_scores = [triplet[2] for triplet in child_triplets]

        mu = sum(child_scores) / max(1, len(child_scores))
        if len(child_scores) > 1:
            variance = sum((s - mu) ** 2 for s in child_scores) / len(child_scores)
            sigma = math.sqrt(variance)
        else:
            sigma = 0.0

        n = max(1, len(child_scores))
        conservative = mu - (k * sigma) - (u / math.sqrt(n))

        if node:
            try:
                node_rating = int(self.treeview.tree.item(node, 'values')[0])
            except (ValueError, IndexError):
                node_rating = 0
            node_conf = self.calculate_rating_confidence(node_rating)
            score = int(round(self._clamp((0.6 * node_conf) + (0.4 * conservative), 0, 100)))

            floor2 = int(round(self._clamp(min(child_scores), 0, 100)))
            ceiling2 = int(round(self._clamp(max(child_scores), 0, 100)))
            regret2 = max(0, ceiling2 - floor2)

            prefix_values = {'confidence2_': score, 'regret2_': regret2}
            if write_aux_tags:
                prefix_values['floor2_'] = floor2
                prefix_values['ceiling2_'] = ceiling2
            self._replace_prefixed_tags(node, prefix_values)
            self.update_node_confidence_display(node, score)
            return floor2, ceiling2, score

        return 0, 0, int(round(self._clamp(conservative, 0, 100)))

    def get_confidence2_from_tags(self, node):
        """Extract enhanced confidence value from node tags."""
        return self._extract_prefixed_tag_value(node, 'confidence2_', default=0)

    def get_regret2_from_tags(self, node):
        """Extract confidence regret spread from node tags (lower is better)."""
        return self._extract_prefixed_tag_value(node, 'regret2_', default=0)

    def calculate_counter_resistance_scores_enhanced(self, node, beta=None, gamma=None, _depth=0):
        """Enhanced resistance with opponent-regret penalty."""
        beta = self.resistance2_beta if beta is None else beta
        gamma = self.resistance2_gamma if gamma is None else gamma
        children = self.treeview.tree.get_children(node)

        if not children:
            if node:
                try:
                    rating = int(self.treeview.tree.item(node, 'values')[0])
                except (ValueError, IndexError):
                    rating = 0
                base = self.calculate_counter_resistance(rating)
                score = int(round(self._clamp(base, 0, 100)))
                self._replace_prefixed_tags(node, {'resistance2_': score})
                self.update_node_resistance_display(node, score)
                return score
            return 0

        child_scores = [
            self.calculate_counter_resistance_scores_enhanced(child, beta=beta, gamma=gamma, _depth=_depth + 1)
            for child in children
        ]

        if node:
            try:
                rating = int(self.treeview.tree.item(node, 'values')[0])
            except (ValueError, IndexError):
                rating = 0

            base_stability = self.calculate_counter_resistance(rating)
            best_our = max(child_scores) if child_scores else 0
            worst_opp = min(child_scores) if child_scores else 0
            regret = max(0.0, best_our - worst_opp)
            # Use recursive depth tracking to avoid repeated parent-chain traversal.
            depth_buffer = max(0.0, 6.0 - float(_depth))

            score = base_stability - (beta * regret) + (gamma * depth_buffer)
            score = int(round(self._clamp(score, 0, 100)))

            self._replace_prefixed_tags(node, {'resistance2_': score})
            self.update_node_resistance_display(node, score)
            return score

        return max(child_scores) if child_scores else 0

    def get_resistance2_from_tags(self, node):
        """Extract enhanced resistance value from node tags."""
        return self._extract_prefixed_tag_value(node, 'resistance2_', default=0)

    def calculate_strategic3_scores(self, node, weights=None, rho=None, lam=None):
        """Strategic fusion score built from enhanced cumulative/confidence/resistance metrics."""
        weights = self.strategic3_weights if weights is None else weights
        rho = self.strategic3_rho if rho is None else rho
        lam = self.strategic3_lam if lam is None else lam
        guardrail_coeff = self._get_guardrail_coefficient()

        if node == "":
            self.reset_strategic_profile_stats()
            memo_context = self._build_strategic_memo_context()
            if memo_context != self._strategic_memo_context:
                self.clear_memoization(reason="memo_context_change")
                self._strategic_memo_context = memo_context

            all_nodes = []

            def collect_nodes(parent):
                for child in self.treeview.tree.get_children(parent):
                    all_nodes.append(child)
                    collect_nodes(child)

            collect_nodes("")
            self._strategic_profile_stats["range_nodes"] = len(all_nodes)

            c_values = [self.get_cumulative2_from_tags(n) for n in all_nodes]
            q_values = [self.get_confidence2_from_tags(n) for n in all_nodes]
            r_values = [self.get_resistance2_from_tags(n) for n in all_nodes]

            if not all_nodes:
                return 0

            has_c = any(v != 0 for v in c_values)
            has_q = any(v != 0 for v in q_values)
            has_r = any(v != 0 for v in r_values)

            if not (has_c and has_q and has_r):
                return 0

            self._strategic3_ranges = {
                'c_min': min(c_values) if c_values else 0,
                'c_max': max(c_values) if c_values else 1,
                'q_min': min(q_values) if q_values else 0,
                'q_max': max(q_values) if q_values else 100,
                'r_min': min(r_values) if r_values else 0,
                'r_max': max(r_values) if r_values else 100,
            }

        if node:
            self._strategic_profile_stats["nodes_visited"] += 1
            memo_key = self._build_structural_memo_key(node)
            if memo_key in self._strategic_memo:
                self._strategic_memo_hits += 1
                self._strategic_profile_stats["memo_hits"] += 1
                strategic_value = int(self._strategic_memo[memo_key])
                materialize_on_hit = bool(getattr(self, "_materialize_strategic_tags_on_memo_hit", True))
                if materialize_on_hit and not self._has_prefixed_tag(node, 'strategic3_'):
                    self._replace_prefixed_tags(node, {'strategic3_': strategic_value})
                    self._strategic_profile_stats["tag_writes"] += 1
                self.update_node_strategic_display(node, strategic_value)

                # Materialize descendant strategic tags/displays as well.
                # Without this, a memo hit on a parent (e.g. synthetic Pairings node)
                # can short-circuit recursion and leave children at stale zeros.
                if materialize_on_hit:
                    self._materialize_strategic_descendants_from_memo(node, weights=weights, rho=rho, lam=lam)

                return strategic_value
            self._strategic_memo_misses += 1
            self._strategic_profile_stats["memo_misses"] += 1

        children = self.treeview.tree.get_children(node)

        def normalize(value, key_min, key_max):
            min_v = self._strategic3_ranges.get(key_min, 0)
            max_v = self._strategic3_ranges.get(key_max, 1)
            denom = max(1e-9, max_v - min_v)
            return self._clamp((value - min_v) / denom, 0.0, 1.0)

        child_scores = [self.calculate_strategic3_scores(child, weights=weights, rho=rho, lam=lam) for child in children]

        if node:
            c_raw = self.get_cumulative2_from_tags(node)
            q_raw = self.get_confidence2_from_tags(node)
            r_raw = self.get_resistance2_from_tags(node)
            memo_key = self._build_structural_memo_key(node)
            floor2 = self._extract_prefixed_tag_value(node, 'floor2_', default=q_raw)
            ceiling2 = self._extract_prefixed_tag_value(node, 'ceiling2_', default=q_raw)

            c_norm = normalize(c_raw, 'c_min', 'c_max')
            q_norm = normalize(q_raw, 'q_min', 'q_max')
            r_norm = normalize(r_raw, 'r_min', 'r_max')

            w_c, w_q, w_r = weights
            # Worst-axis regret proxy: whichever dimension is currently weakest dominates core risk.
            t_core = max(w_c * (1.0 - c_norm), w_q * (1.0 - q_norm), w_r * (1.0 - r_norm))
            smooth = (w_c * c_norm) + (w_q * q_norm) + (w_r * r_norm)
            downside = self._clamp((ceiling2 - floor2) / 100.0, 0.0, 1.0)
            round_win_feasibility = self._clamp((q_norm - 0.5) * 2.0, -1.0, 1.0)
            guardrail_term = guardrail_coeff * round_win_feasibility
            utility = (-t_core) + (rho * smooth) - (lam * downside) + guardrail_term
            node_gain = utility * 100.0

            if children:
                is_opp_level = self._is_opponent_choice_level(children[0])
                child_component = min(child_scores) if is_opp_level else max(child_scores)
                exploitability = max(child_scores) - min(child_scores)
            else:
                child_component = 0.0
                exploitability = 0.0

            strategic_value = int(round(node_gain + child_component))
            self._replace_prefixed_tags(
                node,
                {
                    'strategic3_': strategic_value,
                    'strategic3_exploit_': int(round(exploitability)),
                },
            )
            self._strategic_profile_stats["tag_writes"] += 1
            self.update_node_strategic_display(node, strategic_value)
            self._strategic_memo[memo_key] = strategic_value
            return strategic_value

        return max(child_scores) if child_scores else 0

    def get_strategic3_from_tags(self, node):
        """Extract strategic fusion value from node tags."""
        if self._has_prefixed_tag(node, 'strategic3_'):
            return self._extract_prefixed_tag_value(node, 'strategic3_', default=0)
        try:
            memo_key = self._build_structural_memo_key(node)
            memo_value = self._strategic_memo.get(memo_key)
            if memo_value is not None:
                self._strategic_profile_stats["memo_fastpath_reads"] += 1
                return int(memo_value)
        except Exception:
            pass
        return 0

    def get_strategic3_exploitability_from_tags(self, node):
        """Extract strategic exploitability spread (lower is better)."""
        return self._extract_prefixed_tag_value(node, 'strategic3_exploit_', default=0)

    def unsort_tree(self):
        """Remove sorting and restore original tree order"""
        if hasattr(self, 'original_order') and self.original_order:
            self.unsort_matchup_tree()
        else:
            # If no original order saved, we can't restore, but we can at least 
            # clear the cumulative values to prepare for fresh generation
            self.clear_cumulative_values("")

    def clear_cumulative_values(self, node):
        """Clear cumulative values from all nodes"""
        children = self.treeview.tree.get_children(node)
        for child in children:
            try:
                # Remove cumulative tags
                item_data = self.treeview.tree.item(child)
                current_tags = list(item_data.get('tags', []))
                current_tags = [tag for tag in current_tags if not str(tag).startswith('cumulative_')]
                self.treeview.tree.item(child, tags=current_tags)
            except:
                pass
            self.clear_cumulative_values(child)
    def save_original_order(self):
        # Save the original order of the children for each root node
        root_nodes = self.treeview.tree.get_children()
        for root in root_nodes:
            child_ids = self.treeview.tree.get_children(root)
            self.original_order[root] = list(child_ids)


    def unsort_matchup_tree(self):
        # Restore the original order of the children for each root node
        for root, original_child_ids in self.original_order.items():
            try:
                # Get the current child nodes
                current_child_ids = self.treeview.tree.get_children(root)
            except tkinter.TclError as e:
                print(f"Error getting children of root {root}: {e}")
                continue
            
            # Detach all current children
            for child_id in current_child_ids:
                try:
                    self.treeview.tree.detach(child_id)
                except tkinter.TclError as e:
                    print(f"Error detaching child {child_id}: {e}")
                    continue
            
            # Reinsert the children in their original order
            for child_id in original_child_ids:
                try:
                    self.treeview.tree.move(child_id, root, 'end')
                except tkinter.TclError as e:
                    print(f"Error moving child {child_id} to root {root}: {e}")

    def calculate_confidence_for_rating(self, rating):
        """Calculate confidence score based on rating value"""
        try:
            rating_val = int(rating) if rating != 'N/A' else 0
            return self.calculate_rating_confidence(rating_val)
        except (ValueError, TypeError):
            return 0

    def calculate_resistance_for_rating(self, base_rating, rating_0, rating_1):
        """Calculate resistance score based on rating spread and values"""
        try:
            r0 = int(rating_0) if rating_0 != 'N/A' else 0
            r1 = int(rating_1) if rating_1 != 'N/A' else 0
            base = int(base_rating) if base_rating != 'N/A' else 0
            
            # Resistance is based on:
            # 1. Lower of the two ratings (how bad worst case is)  
            # 2. Spread between ratings (consistency)
            min_rating = min(r0, r1)
            spread = abs(r0 - r1)
            
            # Base resistance from minimum rating (0-50 points)
            base_resistance = min_rating * 10
            
            # Penalty for large spread (inconsistency) (0-25 points penalty)
            spread_penalty = spread * 5
            
            # Final score: base resistance minus spread penalty
            resistance_score = max(0, base_resistance - spread_penalty)
            
            return resistance_score
        except (ValueError, TypeError):
            return 0

    def sort_by_strategic_optimal(self):
        """
        Strategic Optimal Expected Value sorting - combines multi-objective optimization
        with intelligent weighting to maximize 3/5 win probability while preventing 
        catastrophic failures and accounting for opponent counter-strategies.
        """
        root_nodes = self.treeview.tree.get_children()
        if root_nodes:
            # Save original order before first sort
            if not hasattr(self, 'original_order_saved') or not self.original_order_saved:
                self.save_original_order()
                self.original_order_saved = True
            
            # Calculate strategic optimal scores for all paths
            self.calculate_strategic_optimal_scores("")
            # Sort recursively from root
            for root in root_nodes:
                self.sort_children_by_strategic_optimal(root)

    def calculate_strategic_optimal_scores(self, node):
        """
        Calculate strategic optimal expected value scores using multi-objective optimization.
        
        Key factors:
        1. Expected value considering opponent responses
        2. 3/5 win probability optimization  
        3. Catastrophic failure prevention (floor protection)
        4. Counter-pick resistance (front-loaded)
        5. Team strength adaptive weighting
        """
        children = self.treeview.tree.get_children(node)
        
        if not children:
            # Leaf node - calculate base strategic value
            if node:
                try:
                    rating = int(self.treeview.tree.item(node, 'values')[0])
                    
                    # Core Expected Value Calculation
                    base_ev = self.calculate_base_expected_value(rating)
                    
                    # Win Probability for 3/5 context
                    win_probability = self.calculate_win_probability(rating)
                    
                    # Catastrophic Failure Protection 
                    floor_protection = self.calculate_floor_protection(rating)
                    
                    # Counter-pick Resistance (front-loaded weighting)
                    counter_resistance = self.calculate_counter_resistance_value(rating)
                    
                    # Multi-objective score combination
                    strategic_score = self.combine_strategic_factors(
                        base_ev, win_probability, floor_protection, counter_resistance
                    )
                    
                    self.store_strategic_optimal_data(node, strategic_score)
                    return strategic_score
                    
                except (ValueError, IndexError):
                    self.store_strategic_optimal_data(node, 0)
                    return 0
            return 0
        else:
            # Branch node - aggregate strategic values from children
            path_scores = []
            for child in children:
                child_score = self.calculate_strategic_optimal_scores(child)
                if node:
                    try:
                        node_rating = int(self.treeview.tree.item(node, 'values')[0])
                        node_base_ev = self.calculate_base_expected_value(node_rating)
                        node_win_prob = self.calculate_win_probability(node_rating)
                        node_floor = self.calculate_floor_protection(node_rating)
                        node_counter = self.calculate_counter_resistance_value(node_rating)
                        
                        node_strategic = self.combine_strategic_factors(
                            node_base_ev, node_win_prob, node_floor, node_counter
                        )
                        
                        # Combine node score with best child path
                        total_strategic = self.aggregate_path_scores(node_strategic, child_score)
                        path_scores.append(total_strategic)
                        
                    except (ValueError, IndexError):
                        path_scores.append(child_score)
                else:
                    path_scores.append(child_score)
            
            if node:
                # Use best (maximum) strategic score for this branch
                best_strategic = max(path_scores) if path_scores else 0
                self.store_strategic_optimal_data(node, best_strategic)
                return best_strategic
            return max(path_scores) if path_scores else 0

    def calculate_base_expected_value(self, rating):
        """Calculate base expected value from rating with win probability conversion"""
        try:
            r = self._to_reference_rating(rating) if rating != 'N/A' else 0
            # Convert 1-5 rating to win probability and then to expected value
            # Rating 5 = ~90% win = 0.9 EV, Rating 1 = ~10% win = 0.1 EV
            win_prob_map = {5: 0.90, 4: 0.75, 3: 0.50, 2: 0.25, 1: 0.10, 0: 0.05}
            win_probability = win_prob_map.get(r, 0.50)
            # Scale to 0-100 for easier manipulation
            return win_probability * 100
        except (ValueError, TypeError):
            return 50  # Neutral expected value

    def calculate_win_probability(self, rating):
        """Calculate probability of winning this specific matchup for 3/5 optimization"""
        try:
            r = self._to_reference_rating(rating) if rating != 'N/A' else 0
            # Optimized for 3/5 win context - emphasizes ratings 3+ more heavily
            win_weights = {5: 100, 4: 85, 3: 65, 2: 30, 1: 10, 0: 5}
            return win_weights.get(r, 50)
        except (ValueError, TypeError):
            return 50

    def calculate_floor_protection(self, rating):
        """Calculate protection against catastrophic matchup failures"""
        try:
            r = self._to_reference_rating(rating) if rating != 'N/A' else 0
            # Heavily penalize ratings 1-2, neutral on 3+
            # This prevents catastrophic trap scenarios
            floor_scores = {5: 100, 4: 95, 3: 80, 2: 40, 1: 10, 0: 0}
            return floor_scores.get(r, 50)
        except (ValueError, TypeError):
            return 50

    def calculate_counter_resistance_value(self, rating):
        """Calculate resistance to opponent counter-picks (front-loaded weighting)"""
        try:
            r = self._to_reference_rating(rating) if rating != 'N/A' else 0
            # High ratings are harder to counter, but diminishing returns after initial protection
            resistance_scores = {5: 90, 4: 80, 3: 60, 2: 35, 1: 15, 0: 5}
            return resistance_scores.get(r, 50)
        except (ValueError, TypeError):
            return 50

    def combine_strategic_factors(self, base_ev, win_prob, floor_protect, counter_resist):
        """
        Combine strategic factors using multi-objective optimization weights
        
        Priority weighting based on user requirements:
        1. Floor Protection (40%) - Prevent catastrophic failures
        2. Win Probability (30%) - Optimize for 3/5 wins  
        3. Base Expected Value (20%) - General expected value
        4. Counter Resistance (10%) - Front-loaded but diminishing returns
        """
        # Weighted combination with strategic priorities
        strategic_score = (
            floor_protect * 0.40 +      # Highest priority: avoid disasters
            win_prob * 0.30 +           # High priority: win 3/5 matches
            base_ev * 0.20 +            # Medium priority: general EV
            counter_resist * 0.10       # Lower priority: counter resistance
        )
        
        return strategic_score

    def aggregate_path_scores(self, node_score, child_score):
        """Aggregate node and child strategic scores for complete paths"""
        # Use weighted average that emphasizes path consistency
        # 60% current node, 40% best child path
        return (node_score * 0.60) + (child_score * 0.40)

    def store_strategic_optimal_data(self, node, strategic_score):
        """Store strategic optimal data in node tags and update display"""
        try:
            item_data = self.treeview.tree.item(node)
            current_tags = list(item_data.get('tags', []))
            
            # Remove existing strategic tags
            current_tags = [tag for tag in current_tags if not str(tag).startswith('strategic_')]
            
            # Add new strategic data
            current_tags.append(f'strategic_{int(strategic_score)}')
            
            self.treeview.tree.item(node, tags=current_tags)
            
            # Update the sort value column with strategic score  
            self.update_node_strategic_display(node, strategic_score)
        except Exception:
            pass

    def update_node_strategic_display(self, node, strategic_value):
        """Update the sort value column display for strategic optimal scores"""
        if getattr(self, "_suppress_display_updates", False):
            return
        try:
            current_values = list(self.treeview.tree.item(node, 'values'))
            if len(current_values) >= 2:
                # Update the sort value column (index 1) with strategic score
                current_values[1] = int(strategic_value)
                self.treeview.tree.item(node, values=current_values)
        except Exception as e:
            print(f"Error updating strategic display for node {node}: {e}")

    def sort_children_by_strategic_optimal(self, node):
        """Recursively sort children by their strategic optimal scores"""
        children = self.treeview.tree.get_children(node)
        if not children:
            return
        
        # Get strategic scores for all children
        children_with_scores = []
        for child in children:
            strategic_score = self.get_strategic_score_from_tags(child)
            children_with_scores.append((child, strategic_score))
        
        # Determine if this is an opponent decision level or our choice level
        # Use the first child to determine the level, since all children are at the same level
        is_opponent_choice_level = self._is_opponent_choice_level(children[0])
        
        if is_opponent_choice_level:
            # Opponent choice level: Sort by LOWEST strategic score first (opponent picks what's worst for us)
            children_with_scores.sort(key=lambda x: x[1], reverse=False)
        else:
            # Our choice level: Sort by HIGHEST strategic score first (we pick what's best for us)
            children_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Reorder children in the tree
        for child, _ in children_with_scores:
            self.treeview.tree.detach(child)
        for child, _ in children_with_scores:
            self.treeview.tree.move(child, node, 'end')
        
        # Recursively sort grandchildren
        for child, _ in children_with_scores:
            self.sort_children_by_strategic_optimal(child)

    def get_strategic_score_from_tags(self, node):
        """Extract strategic score from node tags"""
        try:
            item_data = self.treeview.tree.item(node)
            tags = item_data.get('tags', [])
            for tag in tags:
                if str(tag).startswith('strategic_'):
                    return int(str(tag).replace('strategic_', ''))
        except (ValueError, TypeError):
            pass
        return 0

    def _is_opponent_choice_level(self, node):
        """
        Determine if this node represents an opponent choice level based on tree depth
        and the "Our Team First" setting.
        
        Rules:
        1. If "Our Team First" is checked: Level 1=Us, 2=Them, 3=Us, 4&5=Them  
        2. If "Our Team First" is unchecked: Level 1=Them, 2=Us, 3=Them, 4&5=Us
        3. The team that doesn't go first controls both decisions 4 & 5
        
        Args:
            node: Node ID to check
            
        Returns:
            True if this is an opponent choice level, False if it's our choice level
        """
        if not node:
            return False
        
        # Calculate the depth of this node (1-based)
        depth = self._calculate_node_depth(node)
        
        if self.our_team_first:
            # Our team goes first
            if depth == 1 or depth == 3:
                return False  # Our choice
            elif depth == 2 or depth == 4 or depth == 5:
                return True   # Opponent choice
        else:
            # Opponent team goes first  
            if depth == 1 or depth == 3:
                return True   # Opponent choice
            elif depth == 2 or depth == 4 or depth == 5:
                return False  # Our choice
        
        # Default for unexpected depths - alternate starting from our_team_first
        return (depth % 2) != (1 if self.our_team_first else 0)
    
    def _calculate_node_depth(self, node):
        """
        Calculate the depth of a node in the tree (1-based, root children are depth 1)
        
        Args:
            node: Node ID
            
        Returns:
            Depth as integer (1-based)
        """
        depth = 0
        current = node
        
        while current:
            parent = self.treeview.tree.parent(current) 
            if not parent:  # Reached root
                break
            depth += 1
            current = parent
        
        return depth

    def update_node_cumulative_display(self, node, cumulative_value):
        """Update the cumulative score column display for a node"""
        if getattr(self, "_suppress_display_updates", False):
            return
        try:
            current_values = list(self.treeview.tree.item(node, 'values'))
            if len(current_values) >= 2:
                # Update the cumulative score column (index 1)
                current_values[1] = cumulative_value
                self.treeview.tree.item(node, values=current_values)
        except Exception as e:
            print(f"Error updating cumulative display for node {node}: {e}")

    def update_node_confidence_display(self, node, confidence_value):
        """Update the confidence score column display for a node"""
        if getattr(self, "_suppress_display_updates", False):
            return
        try:
            current_values = list(self.treeview.tree.item(node, 'values'))
            if len(current_values) >= 3:
                # Update the confidence score column (index 2)
                current_values[2] = int(confidence_value)
                self.treeview.tree.item(node, values=current_values)
        except Exception as e:
            print(f"Error updating confidence display for node {node}: {e}")

    def update_node_resistance_display(self, node, resistance_value):
        """Update the resistance score column display for a node"""
        if getattr(self, "_suppress_display_updates", False):
            return
        try:
            current_values = list(self.treeview.tree.item(node, 'values'))
            if len(current_values) >= 4:
                # Update the resistance score column (index 3)
                current_values[3] = int(resistance_value)
                self.treeview.tree.item(node, values=current_values)
        except Exception as e:
            print(f"Error updating resistance display for node {node}: {e}")