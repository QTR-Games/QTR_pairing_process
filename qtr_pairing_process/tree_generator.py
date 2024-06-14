from itertools import combinations, permutations

import utility_funcs as uf

class TreeGenerator:
    def __init__(
        self,
        treeview
    ):
        self.treeview = treeview

    def generate_combinations(self, fNames, oNames, fRatings, oRatings, treeview, sort_alpha):
        self.treeview.tree.delete(*treeview.tree.get_children())
        tree_top = treeview.tree.insert("", 'end', text="Pairings")
        fNames_sorted = sorted(fNames, key=lambda x: x) if sort_alpha else fNames
        oNames_sorted = sorted(oNames, key=lambda x: x) if sort_alpha else oNames
        
        for name in fNames_sorted:
            # print(f"Top Level: {name} in {fNames_sorted}")
            self.generate_nested_combinations(fNames_sorted, oNames_sorted, fRatings, oRatings, treeview.tree, tree_top, sort_alpha)
            fNames_sorted[:] = uf.cycle_list(fNames_sorted)
            # oNames_sorted[:] = cycle_list(oNames_sorted)
            
        
    def generate_nested_combinations(self, fNames, oNames, fRatings, oRatings, treeview, parent, sort_alpha):
        if not fNames:
            # print("NOT FNAMES")
            return
        
        first_fName = fNames[0]
        remaining_fNames = fNames[1:]
        first_oName = oNames[0]
        remaining_oNames = oNames[1:]
        combs = list(combinations(oNames, 2))
        combs_sorted = sorted(combs, key=lambda x: (x[0], x[1])) if sort_alpha else combs
        for comb in combs_sorted:
            rating_0 = fRatings[first_fName].get(comb[0], 'N/A')
            rating_1 = fRatings[first_fName].get(comb[1], 'N/A')
            item_id = treeview.insert(parent, 'end', text=f"{first_fName} vs {comb[0]} ({rating_0}/5) OR {comb[1]} ({rating_1}/5)", values=remaining_fNames, tags=maximum(rating_0, rating_1))
            
            if remaining_fNames:
                for opponent in comb:
                    nested_oNames = [name for name in oNames if name != opponent]
                    nested_fNames = [name for name in fNames if name != first_fName]
                    child_id = self.treeview.insert(item_id, 'end', text=f"{opponent} rating {fRatings[first_fName].get(opponent)}", values=opponent, tags=fRatings[first_fName].get(opponent))                    
                    self.generate_nested_combinations(nested_oNames, remaining_fNames, oRatings, fRatings, treeview, child_id, sort_alpha)
        