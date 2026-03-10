""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """

from itertools import combinations, permutations
import tkinter

import qtr_pairing_process.utility_funcs as uf

class TreeGenerator:
    def __init__(
        self,
        treeview
    ):
        self.treeview = treeview
        self.original_order = {}
        self.fRatings = None
        self.our_team_first = True  # Will be set during generation

    def generate_combinations(self, fNames, oNames, fRatings, oRatings, our_team_first=True):
        self.fRatings = fRatings
        self.our_team_first = our_team_first
        self.treeview.tree.delete(*self.treeview.tree.get_children())
        # Reset sorting state for new generation
        self.original_order_saved = False
        self.original_order = {}
        tree_top = self.treeview.tree.insert("", 'end', text="Pairings")
        
        # Use original order (no alphabetical sorting)
        for name in fNames:
            fnames_filtered = [x for x in fNames if x!=name]

            # print(f"Top Level: {name} in {fNames}")
            self.generate_nested_combinations(name, fnames_filtered, oNames, fRatings, oRatings, tree_top)
            fNames[:] = uf.cycle_list(fNames)
            # oNames[:] = uf.cycle_list(oNames)
        
        # Save the original order after generation for restore functionality
        self.save_original_order_recursive()
        
    def generate_nested_combinations(self, first_fName, fNames, oNames, fRatings, oRatings, parent):
        
        combs = list(combinations(oNames, 2))
        if oNames and not combs:
            first_oName = oNames[0]
            combs = list(combinations([first_oName,first_oName], 2))
        
        # Use original order (no alphabetical sorting)
        for comb in combs:
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
                text=f"{first_fName} vs {comb[0]} ({rating_0}/5) OR {comb[1]} ({rating_1}/5)",
                values=(base_rating, cumulative_score, confidence_score, resistance_score),
                tags=base_rating,
            )
            
            if fNames:
                opponent_perms = list(permutations(comb, 2))
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
        confidence_map = {
            5: 95,  # Very high confidence - almost certain win
            4: 80,  # High confidence - strong advantage
            3: 60,  # Medium confidence - even matchup
            2: 35,  # Low confidence - disadvantage
            1: 15   # Very low confidence - likely loss
        }
        return confidence_map.get(rating, 50)

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
        # Higher ratings are more vulnerable to counters (opponent focuses best players)
        # Middle ratings (3) are most counter-resistant (opponent wastes effort)
        resistance_map = {
            5: 60,  # High value but vulnerable to focus-fire
            4: 75,  # Good value with moderate vulnerability  
            3: 85,  # Most counter-resistant - opponent indifferent
            2: 70,  # Low value but opponent may ignore
            1: 50   # Very low value, opponent will exploit
        }
        return resistance_map.get(rating, 60)

    def simulate_opponent_counter(self, our_rating):
        """Simulate how effectively opponent can counter our strategy"""
        # Opponent counter-effectiveness based on our rating pattern
        if our_rating >= 4:
            # High ratings draw opponent's best counters
            return 0.3  # 30% effectiveness reduction
        elif our_rating == 3:
            # Medium ratings are hardest to counter
            return 0.1  # 10% effectiveness reduction
        else:
            # Low ratings - opponent may not need to counter hard
            return 0.2  # 20% effectiveness reduction

    def store_counter_resistance_data(self, node, resistance):
        """Store counter-resistance data in node tags"""
        try:
            item_data = self.treeview.tree.item(node)
            current_tags = list(item_data.get('tags', []))
            
            # Remove existing resistance tags
            current_tags = [tag for tag in current_tags if not str(tag).startswith('resistance_')]
            
            # Add new resistance data
            current_tags.append(f'resistance_{int(resistance)}')
            
            self.treeview.tree.item(node, tags=current_tags)

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

    def save_original_order_recursive(self, node=""):
        """Recursively save the original order of all nodes in the tree"""
        children = self.treeview.tree.get_children(node)
        if children:
            self.original_order[node if node else "root"] = list(children)
            for child in children:
                self.save_original_order_recursive(child)

    def restore_original_order(self):
        """Restore the original order of all nodes in the tree"""
        if not self.original_order:
            return

        def restore_node(node=""):
            key = node if node else "root"
            if key in self.original_order:
                original_children = self.original_order[key]
                current_children = list(self.treeview.tree.get_children(node))

                for child in current_children:
                    try:
                        self.treeview.tree.detach(child)
                    except tkinter.TclError:
                        pass

                for child in original_children:
                    try:
                        self.treeview.tree.move(child, node, 'end')
                    except tkinter.TclError:
                        pass

                for child in original_children:
                    restore_node(child)

        restore_node()

    def sort_by_column_recursive(self, column, reverse=False):
        """Sort all tree levels by a specific column"""
        if not self.original_order:
            self.save_original_order_recursive()

        def sort_node_children(node=""):
            children = list(self.treeview.tree.get_children(node))
            if not children:
                return

            children_with_keys = []
            for child in children:
                if column == "text":
                    sort_key = self.treeview.tree.item(child, 'text')
                else:
                    try:
                        values = self.treeview.tree.item(child, 'values')
                        if column == "Rating":
                            sort_key = int(values[0]) if values and values[0] != 'N/A' else 0
                        elif column == "Sort Value":
                            cumulative = self.get_cumulative_from_tags(child)
                            if cumulative > 0:
                                sort_key = cumulative
                            else:
                                sort_key = int(values[1]) if len(values) > 1 and values[1] != '' else 0
                        else:
                            sort_key = 0
                    except (ValueError, IndexError, TypeError):
                        sort_key = 0

                if column == "text" and isinstance(sort_key, str):
                    sort_key = sort_key.lower()

                children_with_keys.append((child, sort_key))

            children_with_keys.sort(key=lambda x: x[1], reverse=reverse)

            for child, _ in children_with_keys:
                try:
                    self.treeview.tree.detach(child)
                except tkinter.TclError:
                    pass

            for child, _ in children_with_keys:
                try:
                    self.treeview.tree.move(child, node, 'end')
                except tkinter.TclError:
                    pass

            for child, _ in children_with_keys:
                sort_node_children(child)

        sort_node_children()

    def ensure_analysis_tags(self, mode):
        """Ensure analysis tags exist for a given advanced sorting mode.

        This computes and stores per-node tags but does not reorder the tree.
        """
        if mode == "cumulative":
            self.calculate_all_path_values("")
        elif mode == "confidence":
            self.calculate_confidence_scores("")
        elif mode == "resistance":
            self.calculate_counter_resistance_scores("")

    def _get_primary_sort_value(self, node, primary_mode):
        if primary_mode == "cumulative":
            return self.get_cumulative_value_from_tags(node)
        if primary_mode == "confidence":
            return self.get_confidence_from_tags(node)
        if primary_mode == "resistance":
            return self.get_resistance_from_tags(node)
        return 0

    def _parse_int(self, value, default=0):
        try:
            if value in (None, "", "N/A"):
                return default
            return int(float(value))
        except (ValueError, TypeError):
            return default

    def _get_secondary_sort_value(self, node, secondary_column):
        """Get a stable secondary sort key for a node."""
        if secondary_column == "text":
            try:
                return str(self.treeview.tree.item(node, 'text')).lower()
            except Exception:
                return ""

        try:
            values = self.treeview.tree.item(node, 'values')
        except Exception:
            values = ()

        if secondary_column == "Rating":
            return self._parse_int(values[0] if len(values) > 0 else None, default=0)

        if secondary_column == "Sort Value":
            return self._parse_int(values[1] if len(values) > 1 else None, default=0)

        return 0

    def sort_combined_recursive(self, primary_mode=None, secondary_column=None, secondary_reverse=False, compute_primary_tags=True):
        """Sort the tree recursively with advanced mode as primary and column sort as secondary."""
        if not self.original_order:
            self.save_original_order_recursive()

        if primary_mode and compute_primary_tags:
            self.ensure_analysis_tags(primary_mode)

        def sort_node(node=""):
            children = list(self.treeview.tree.get_children(node))
            if not children:
                return

            key = node if node else "root"
            original_children = self.original_order.get(key)
            if original_children:
                index_map = {cid: i for i, cid in enumerate(original_children)}
                children.sort(key=lambda cid: index_map.get(cid, 10**9))

            primary_reverse = True
            effective_secondary = secondary_column
            if primary_mode and secondary_column == "Sort Value":
                primary_reverse = secondary_reverse
                effective_secondary = None

            if effective_secondary:
                children.sort(
                    key=lambda cid: self._get_secondary_sort_value(cid, effective_secondary),
                    reverse=secondary_reverse,
                )

            if primary_mode:
                children.sort(
                    key=lambda cid: self._get_primary_sort_value(cid, primary_mode),
                    reverse=primary_reverse,
                )

            for child in children:
                try:
                    self.treeview.tree.detach(child)
                except tkinter.TclError:
                    pass

            for child in children:
                try:
                    self.treeview.tree.move(child, node, 'end')
                except tkinter.TclError:
                    pass

            for child in children:
                sort_node(child)

        sort_node("")

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

            min_rating = min(r0, r1)
            spread = abs(r0 - r1)

            base_resistance = min_rating * 10
            spread_penalty = spread * 5

            resistance_score = max(0, base_resistance - spread_penalty)

            return resistance_score
        except (ValueError, TypeError):
            return 0

    def sort_by_strategic_optimal(self):
        """Strategic optimal sorting with multi-objective weighting."""
        root_nodes = self.treeview.tree.get_children()
        if root_nodes:
            if not hasattr(self, 'original_order_saved') or not self.original_order_saved:
                self.save_original_order()
                self.original_order_saved = True

            self.calculate_strategic_optimal_scores("")
            for root in root_nodes:
                self.sort_children_by_strategic_optimal(root)

    def calculate_strategic_optimal_scores(self, node):
        """Calculate strategic optimal expected value scores using multi-objective optimization."""
        children = self.treeview.tree.get_children(node)

        if not children:
            if node:
                try:
                    rating = int(self.treeview.tree.item(node, 'values')[0])

                    base_ev = self.calculate_base_expected_value(rating)
                    win_probability = self.calculate_win_probability(rating)
                    floor_protection = self.calculate_floor_protection(rating)
                    counter_resistance = self.calculate_counter_resistance_value(rating)

                    strategic_score = self.combine_strategic_factors(
                        base_ev, win_probability, floor_protection, counter_resistance
                    )

                    self.store_strategic_optimal_data(node, strategic_score)
                    return strategic_score

                except (ValueError, IndexError):
                    self.store_strategic_optimal_data(node, 0)
                    return 0
            return 0

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

                    total_strategic = self.aggregate_path_scores(node_strategic, child_score)
                    path_scores.append(total_strategic)

                except (ValueError, IndexError):
                    path_scores.append(child_score)
            else:
                path_scores.append(child_score)

        if node:
            best_strategic = max(path_scores) if path_scores else 0
            self.store_strategic_optimal_data(node, best_strategic)
            return best_strategic

        return max(path_scores) if path_scores else 0

    def calculate_base_expected_value(self, rating):
        """Calculate base expected value from rating with win probability conversion"""
        try:
            r = int(rating) if rating != 'N/A' else 0
            win_prob_map = {5: 0.90, 4: 0.75, 3: 0.50, 2: 0.25, 1: 0.10, 0: 0.05}
            win_probability = win_prob_map.get(r, 0.50)
            return win_probability * 100
        except (ValueError, TypeError):
            return 50

    def calculate_win_probability(self, rating):
        """Calculate probability of winning this matchup for 3/5 optimization"""
        try:
            r = int(rating) if rating != 'N/A' else 0
            win_weights = {5: 100, 4: 85, 3: 65, 2: 30, 1: 10, 0: 5}
            return win_weights.get(r, 50)
        except (ValueError, TypeError):
            return 50

    def calculate_floor_protection(self, rating):
        """Calculate protection against catastrophic matchup failures"""
        try:
            r = int(rating) if rating != 'N/A' else 0
            floor_scores = {5: 100, 4: 95, 3: 80, 2: 40, 1: 10, 0: 0}
            return floor_scores.get(r, 50)
        except (ValueError, TypeError):
            return 50

    def calculate_counter_resistance_value(self, rating):
        """Calculate resistance to opponent counter-picks"""
        try:
            r = int(rating) if rating != 'N/A' else 0
            resistance_scores = {5: 90, 4: 80, 3: 60, 2: 35, 1: 15, 0: 5}
            return resistance_scores.get(r, 50)
        except (ValueError, TypeError):
            return 50

    def combine_strategic_factors(self, base_ev, win_prob, floor_protect, counter_resist):
        """Combine strategic factors using multi-objective optimization weights"""
        return (
            floor_protect * 0.40 +
            win_prob * 0.30 +
            base_ev * 0.20 +
            counter_resist * 0.10
        )

    def aggregate_path_scores(self, node_score, child_score):
        """Aggregate node and child strategic scores for complete paths"""
        return (node_score * 0.60) + (child_score * 0.40)

    def store_strategic_optimal_data(self, node, strategic_score):
        """Store strategic optimal data in node tags and update display"""
        try:
            item_data = self.treeview.tree.item(node)
            current_tags = list(item_data.get('tags', []))

            current_tags = [tag for tag in current_tags if not str(tag).startswith('strategic_')]
            current_tags.append(f'strategic_{int(strategic_score)}')

            self.treeview.tree.item(node, tags=current_tags)

            self.update_node_strategic_display(node, strategic_score)
        except Exception:
            pass

    def update_node_strategic_display(self, node, strategic_value):
        """Update the sort value column display for strategic optimal scores"""
        try:
            current_values = list(self.treeview.tree.item(node, 'values'))
            if len(current_values) >= 2:
                current_values[1] = int(strategic_value)
                self.treeview.tree.item(node, values=current_values)
        except Exception as e:
            print(f"Error updating strategic display for node {node}: {e}")

    def sort_children_by_strategic_optimal(self, node):
        """Recursively sort children by their strategic optimal scores"""
        children = self.treeview.tree.get_children(node)
        if not children:
            return

        children_with_scores = []
        for child in children:
            strategic_score = self.get_strategic_score_from_tags(child)
            children_with_scores.append((child, strategic_score))

        is_opponent_choice_level = self._is_opponent_choice_level(children[0])

        if is_opponent_choice_level:
            children_with_scores.sort(key=lambda x: x[1], reverse=False)
        else:
            children_with_scores.sort(key=lambda x: x[1], reverse=True)

        for child, _ in children_with_scores:
            self.treeview.tree.detach(child)
        for child, _ in children_with_scores:
            self.treeview.tree.move(child, node, 'end')

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
        """Determine if this node represents an opponent choice level."""
        try:
            depth = 0
            current = node
            while current:
                parent = self.treeview.tree.parent(current)
                if not parent:
                    break
                depth += 1
                current = parent

            if self.our_team_first:
                return depth in (2, 4, 5)

            return depth in (1, 3, 4)
        except Exception:
            return False