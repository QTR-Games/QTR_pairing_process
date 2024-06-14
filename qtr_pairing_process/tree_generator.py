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
            
        
    def generate_nested_combinations(self, first_fName, fNames, oNames, fRatings, oRatings, parent):
        
        combs = list(combinations(oNames, 2))
        if oNames and not combs:
            first_oName = oNames[0]
            combs = list(combinations([first_oName,first_oName], 2))
        combs_sorted = sorted(combs, key=lambda x: (x[0], x[1])) if self.sort_alpha else combs
        for comb in combs_sorted:
            rating_0 = fRatings[first_fName].get(comb[0], 'N/A')
            rating_1 = fRatings[first_fName].get(comb[1], 'N/A')
            item_id = self.treeview.tree.insert(parent, 'end', text=f"{first_fName} vs {comb[0]} ({rating_0}/5) OR {comb[1]} ({rating_1}/5)", values=fNames, tags=max(rating_0, rating_1))
            
            if fNames:
                opponent_perms = list(permutations(comb, 2))
                for opponent, next_fName in opponent_perms:                    
                    nested_oNames = [name for name in oNames if name != opponent and name!=next_fName]
                    nested_fNames = [name for name in fNames if name != first_fName]
                    child_id = self.treeview.tree.insert(item_id, 'end', text=f"{opponent} rating {fRatings[first_fName].get(opponent)}", values=opponent, tags=fRatings[first_fName].get(opponent))                    
                    self.generate_nested_combinations(next_fName,nested_oNames, fNames, oRatings, fRatings, child_id)
        