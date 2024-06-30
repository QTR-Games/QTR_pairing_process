""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """

from itertools import combinations, permutations

import qtr_pairing_process.utility_funcs as uf

class TreeGenerator:
    def __init__(
        self,
        treeview,
        sort_alpha
    ):
        self.treeview = treeview
        self.sort_alpha = sort_alpha

    def generate_combinations(self, fNames, oNames, fRatings, oRatings):
        self.treeview.tree.delete(*self.treeview.tree.get_children())
        tree_top = self.treeview.tree.insert("", 'end', text="Pairings")
        fNames_sorted = sorted(fNames, key=lambda x: x) if self.sort_alpha else fNames
        oNames_sorted = sorted(oNames, key=lambda x: x) if self.sort_alpha else oNames
        
        for name in fNames_sorted:
            fnames_filtered = [x for x in fNames_sorted if x!=name]

            # print(f"Top Level: {name} in {fNames_sorted}")
            self.generate_nested_combinations(name, fnames_filtered, oNames_sorted, fRatings, oRatings, tree_top)
            fNames_sorted[:] = uf.cycle_list(fNames_sorted)
            # oNames_sorted[:] = cycle_list(oNames_sorted)

        self.traverse_and_sum_values()
            
        
    def generate_nested_combinations(self, first_fName, fNames, oNames, fRatings, oRatings, parent):
        
        combs = list(combinations(oNames, 2))
        if oNames and not combs:
            first_oName = oNames[0]
            combs = list(combinations([first_oName,first_oName], 2))
        combs_sorted = sorted(combs, key=lambda x: (x[0], x[1])) if self.sort_alpha else combs
        for comb in combs_sorted:
            rating_0 = fRatings[first_fName].get(comb[0], 'N/A')
            rating_1 = fRatings[first_fName].get(comb[1], 'N/A')
            item_id = self.treeview.tree.insert(parent, 'end', text=f"{first_fName} vs {comb[0]} ({rating_0}/5) OR {comb[1]} ({rating_1}/5)", values=max(rating_0, rating_1), tags=max(rating_0, rating_1))
            
            if fNames:
                opponent_perms = list(permutations(comb, 2))
                for opponent, next_fName in opponent_perms:                    
                    nested_oNames = [name for name in oNames if name != opponent and name!=next_fName]
                    nested_fNames = [name for name in fNames if name != first_fName]
                    child_id = self.treeview.tree.insert(item_id, 'end', text=f"{opponent} rating {fRatings[first_fName].get(opponent)}", values=fRatings[first_fName].get(opponent), tags=fRatings[first_fName].get(opponent))                    
                    self.generate_nested_combinations(next_fName,nested_oNames, fNames, oRatings, fRatings, child_id)

    def set_value(self,value, node):
        try:
            self.treeview.tree.set(node,'Rating',value)
        except (ValueError, IndexError):
            print(f"set_item_details has failed")
            return 0

    def traverse_and_sum_values(self):
        # Get all root nodes
        root_nodes = self.treeview.tree.get_children()
        for root in root_nodes:
            self.sum_leaf_values(root)

    def sum_leaf_values(self, node):
        child_ids = self.treeview.tree.get_children(node)
        if not child_ids:
            # Leaf node, return the integer value from the values column
            try:
                value = int(self.treeview.tree.item(node, 'values')[0])
                # print(f"sum_leaf_values - LEAF NODE HIT.\nreturned value = {value}")
                return value
          
            except (ValueError, IndexError):
                return 0
        else:
            # Sum the values of child nodes
            total_sum = 0
            value = self.treeview.tree.item(node, 'values')
            match_ratings = []
             
            for child_id in child_ids:
                total_sum += int(self.sum_leaf_values(child_id))
                match_ratings.append(int(self.sum_leaf_values(child_id)))

            max_rating = max(match_ratings)
            # print(f"sum_leaf_values - NON LEAF NODE HIT.\nNode: {node}, match_ratings = {match_ratings}, Returned total_sum: {total_sum}")
            # self.set_value(total_sum)
            self.set_value(max_rating, node)
            return total_sum
    
    

    
        