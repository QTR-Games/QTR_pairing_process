Here’s a clean layout plan based on the screenshot and your new requests.

**Layout Plan**

1. **Top Row (Grid + Matchup Extract)**
   - Keep the grid on the left, matchup extract on the right (50/50 split stays).
   - **Move the four buttons** (Generate Combinations, Cumulative, Highest Confidence, Counter) into a **new vertical strip centered between grid and matchup extract**.
   - This strip sits **below the dropdowns** and **above the grid/extract row**.

2. **Controls Bar Above the Tree**
   - Create a **single horizontal bar** just above the tree view.
   - Move the two checkboxes (Sort Pairings Alphabetically, Our team first) into this bar.
   - Place the two checkboxes at the end (right aligned).

3. **Tree View Expansion**
   - Make the tree view **full-width** by removing the left controls column (`tree_controls_frame`) entirely.
   - The tree should stretch from left to right edge of the content area.

**Implementation Notes**
- The sort buttons currently live in `buttons_frame`; they’ll be moved to a new `sort_controls_frame` in the top area.
- The checkbox widgets currently live inside `tree_controls_frame`; they’ll be moved to the new “controls bar” above the tree.
- The tree should be reparented directly into a single tree container with `fill=tk.BOTH, expand=True`.