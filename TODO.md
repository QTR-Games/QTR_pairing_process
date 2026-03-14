# Project To Do

Finish the following tasks:
- Parameterization via config in KLIK_KLAK_KONFIG.json is not wired yet.
- Automated regression tests for v2 and strategic3 are not added yet.
- No performance memoization yet for strategic3 recursion.

finish the implementation of v2 calc:
- Wire all tuning parameters to config with safe defaults and runtime loading.
- Add targeted tests for deterministic ordering, first-click non-zero values, and legacy-vs-v2 behavior.
- Add a small strategic breakdown view (C2, Q2, R2, downside, final strategic score) for explainability.

find a way to sort the best possible tree nodes to the top of the list...
- at first pass...
- after clicking a button...
- do this by learning from how the enhanced math works.
- Ensure that the 'best' possible sorted options rise to the top of the choices you can make AT EACH LEVEL OF THE TREE.

Find a way to learn from the enhanced math and...
- optimize the right grid numbers and calc.
figure out how to do bussing (aka throwing someone under the bus)
- Bussing definition:
- Bussing is done when you have the choice to throw one of your own players into a extremely poor matchup, usually a 1. The trade off is that this decision NOW will result in much better choices for the rest of the players in later rounds. This is an expected value calculation. But it has to be worth the risk. How do you determine which bad decisions in the present will pinch the opponent into making certain moves later which will give you and advantage. Can we leverage the math we've just implemented in the v2 calculations and the strategic calculations to figure out how to measure bussing?

Enhance the calc grid.
- Originally, I had the FLOOR column because I wanted to know at a glance, which of the players you can choose to play first would have the least worst matchups. The floor is a sum of all the ratings left to right for each person's row. The player with the highest floor has the best games into the widest field.
- work toward this goal for the other columns in the calc grid as well.

Find a way to incorporate basic strategies that even a human can see and make sure the ratings and sorting calculations are taking this into account.
- You never want to drop a player that has two red matchups (1's) while both of those matchups are still 'on the table'. It's too easy for the enemy team to lock that person into having to pick between the two opponents they have a 1 against.

Remove alphabetic sorting. With advanced math we don't need it.

Remove the default setting for "my team first".

Add a quick integration test module for generated_tree_cache persistence and generation-id propagation.

Add a Data Management action to clear only generated_tree_cache entries for the active matchup or all matchups.

Add a targeted regression test for chooser-direction behavior:
- My Team First unchecked: friendly-choice sibling sort is descending by strategic value.
- My Team First checked: chooser-direction flips correctly by depth owner.