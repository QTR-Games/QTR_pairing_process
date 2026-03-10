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

    def generate_combinations(self, fNames, oNames, fRatings, oRatings):
        self.fRatings = fRatings
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
            item_id = self.treeview.tree.insert(parent, 'end', text=f"{first_fName} vs {comb[0]} ({rating_0}/5) OR {comb[1]} ({rating_1}/5)", values=(max(rating_0, rating_1), ""), tags=max(rating_0, rating_1))
            
            if fNames:
                opponent_perms = list(permutations(comb, 2))
                for opponent, next_fName in opponent_perms:                    
                    nested_oNames = [name for name in oNames if name != opponent and name!=next_fName]
                    nested_fNames = [name for name in fNames if name != first_fName]
                    child_id = self.treeview.tree.insert(item_id, 'end', text=f"{opponent} rating {fRatings[first_fName].get(opponent)}", values=(fRatings[first_fName].get(opponent), ""), tags=fRatings[first_fName].get(opponent))                    
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
                    # Store cumulative value in the item's tags for easy access
                    item_data = self.treeview.tree.item(node)
                    current_tags = list(item_data.get('tags', []))
                    # Remove any existing cumulative tag and add new one
                    current_tags = [tag for tag in current_tags if not str(tag).startswith('cumulative_')]
                    current_tags.append(f'cumulative_{leaf_value}')
                    self.treeview.tree.item(node, tags=current_tags)
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
                # Store cumulative value in tags
                item_data = self.treeview.tree.item(node)
                current_tags = list(item_data.get('tags', []))
                current_tags = [tag for tag in current_tags if not str(tag).startswith('cumulative_')]
                current_tags.append(f'cumulative_{max_cumulative}')
                self.treeview.tree.item(node, tags=current_tags)
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
        
        # Sort by cumulative value (highest first - best outcomes at top)
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
        
        # Sort by confidence score (highest first - most reliable outcomes at top)
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
        
        # Sort by resistance score (highest first - most counter-resistant at top)
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
                
                # Detach all children
                for child in current_children:
                    try:
                        self.treeview.tree.detach(child)
                    except tkinter.TclError:
                        pass
                
                # Reattach in original order
                for child in original_children:
                    try:
                        self.treeview.tree.move(child, node, 'end')
                    except tkinter.TclError:
                        pass
                
                # Recursively restore children
                for child in original_children:
                    restore_node(child)
        
        restore_node()
    
    def sort_by_column_recursive(self, column, reverse=False):
        """Sort all tree levels by a specific column"""
        # Save original order if not already saved
        if not self.original_order:
            self.save_original_order_recursive()
        
        # Sort recursively from root
        def sort_node_children(node=""):
            children = list(self.treeview.tree.get_children(node))
            if not children:
                return
            
            # Create list of (child_id, sort_key) tuples
            children_with_keys = []
            for child in children:
                if column == "text":
                    # Sort by the text field (Pairing column)
                    sort_key = self.treeview.tree.item(child, 'text')
                else:
                    # Sort by a value column (Rating or Sort Value)
                    try:
                        values = self.treeview.tree.item(child, 'values')
                        if column == "Rating":
                            sort_key = int(values[0]) if values and values[0] != 'N/A' else 0
                        elif column == "Sort Value":
                            # Use cumulative value from tags if available
                            cumulative = self.get_cumulative_from_tags(child)
                            if cumulative > 0:
                                sort_key = cumulative
                            else:
                                sort_key = int(values[1]) if len(values) > 1 and values[1] != '' else 0
                        else:
                            sort_key = 0
                    except (ValueError, IndexError, TypeError):
                        sort_key = 0
                
                # For text sorting, convert to lowercase for case-insensitive comparison
                if column == "text" and isinstance(sort_key, str):
                    sort_key = sort_key.lower()
                
                children_with_keys.append((child, sort_key))
            
            # Sort the children
            children_with_keys.sort(key=lambda x: x[1], reverse=reverse)
            
            # Reorder in tree
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
            
            # Recursively sort grandchildren
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
        """Get a stable secondary sort key for a node.

        secondary_column: one of {"text", "Rating", "Sort Value"}
        """
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
        """Sort the tree recursively with advanced mode as primary and column sort as secondary.

        Order of precedence (stable): primary_mode -> secondary_column -> original generation order.
        primary_mode: None or one of {"cumulative", "confidence", "resistance"}
        secondary_column: None or one of {"text", "Rating", "Sort Value"}
        secondary_reverse: True for descending secondary sort.
        """
        # Ensure we have an original-order snapshot to use as the final tie-break.
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

            # If the secondary column is Sort Value and primary_mode is active, let the
            # column direction control the primary sort (e.g., ascending cumulative).
            primary_reverse = True
            effective_secondary = secondary_column
            if primary_mode and secondary_column == "Sort Value":
                primary_reverse = secondary_reverse
                effective_secondary = None

            # Secondary sort (column header) first so that primary sort can remain dominant.
            if effective_secondary:
                children.sort(
                    key=lambda cid: self._get_secondary_sort_value(cid, effective_secondary),
                    reverse=secondary_reverse,
                )

            # Primary sort (advanced mode) last, leveraging Python's stable sort.
            if primary_mode:
                children.sort(
                    key=lambda cid: self._get_primary_sort_value(cid, primary_mode),
                    reverse=primary_reverse,
                )

            # Reorder in tree.
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

            # Recurse.
            for child in children:
                sort_node(child)

        sort_node("")