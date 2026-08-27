"""Sort-on-expand must reorder only the subtree the user opened.

`_on_tree_node_opened` passes the opened widget row and `recurse_mode="expanded"`
into `_sort_children_combined`. The lazy fast path used to drop both arguments
and re-sort the entire model from the root: measured at ~150ms of a ~152ms
expansion on 5v5 (48,751 nodes), versus ~3ms for a single depth-1 subtree.

These tests pin the scoping behavior rather than the timing, so they stay
meaningful on any machine:

* a scoped sort fixes the opened subtree and leaves siblings alone;
* a full sort (node="") still covers the entire tree, so scoping did not
  silently shrink the column-header sort.

The second test is what would catch over-scoping, which is the dangerous
direction: it would leave most of the tree unsorted while looking fast.

A small shim supplies the three attributes `_sort_model_children_combined`
reads. It deliberately duplicates none of the sort logic -- the method under
test is the real one -- which keeps these tests cross-platform instead of
inheriting the Windows-only Tk styling constraint of the full UiManager.
"""
from __future__ import annotations

import pytest

from golden_master_harness import tk_treeview
from golden_master_scenarios import SCENARIOS
from qtr_pairing_process.tree_generator import TreeGenerator
from qtr_pairing_process.ui_manager_v2 import UiManager

# The Tk dependency is in the fixture, not in any test body, so the preflight's
# source scan cannot see it -- same shape as test_lazy_tree_projection.py, which
# already carries this marker. Without it these two error out rather than skip
# wherever there is no display.
pytestmark = pytest.mark.requires_tk

PRIMARY_MODE = "confidence"


def _scenario(slug_prefix: str):
    scenarios = SCENARIOS.values() if isinstance(SCENARIOS, dict) else SCENARIOS
    return next(s for s in scenarios if s.slug.startswith(slug_prefix))


class _SortShim:
    """A partial UiManager: real methods, only the state they read.

    Binding the real `_sort_children_combined` matters -- that is the function
    holding the lazy fast path, and the fix is that the fast path forwards
    `node`. Calling `_sort_model_children_combined` directly instead would skip
    the wiring under test and pass even with the fix reverted.
    """

    _using_lazy_model_render = UiManager._using_lazy_model_render
    _sort_children_combined = UiManager._sort_children_combined
    _sort_model_children_combined = UiManager._sort_model_children_combined

    def __init__(self, generator):
        self.tree_generator = generator
        self.column_sort_states = {}
        self.tie_break_order = "confidence_then_cumulative"


def _flatten(node):
    order = [getattr(node, "text", "") or ""]
    for child in node.children:
        order.extend(_flatten(child))
    return order


@pytest.fixture
def lazy_model_generator(monkeypatch):
    monkeypatch.setenv("QTR_ENGINE", "model")
    monkeypatch.setenv("QTR_RENDER", "lazy")
    scenario = _scenario("3v3")
    with tk_treeview() as treeview:
        generator = TreeGenerator(
            treeview=treeview,
            sort_alpha=False,
            strategic_preferences={},
            rating_system=scenario.rating_system,
        )
        assert generator._use_lazy_rendering(), "fast path under test needs lazy render"
        generator.generate_combinations(
            list(scenario.our_players),
            list(scenario.opponent_players),
            scenario.our_ratings,
            scenario.opponent_ratings,
            our_team_first=scenario.our_team_first,
        )
        yield generator


def _materialized_pair(generator):
    """Return (opened_node, its widget id, a sibling node) for the root's children.

    Must be called *after* any sort: `_project_model` clears and rebuilds the
    widget<->node maps, so a widget id captured earlier no longer resolves and
    would silently fall back to a whole-tree sort. The real UI has the same
    constraint -- the user can only expand a row that exists right now.
    """
    root = generator.model_root
    for child in root.children:
        widget_id = generator.projector.widget_id_for(child)
        if not widget_id:
            continue
        sibling = next((c for c in root.children if c is not child and c.children), None)
        if sibling is not None:
            assert generator._model_node_from_arg(widget_id) is child, "stale widget id"
            return child, widget_id, sibling
    pytest.skip("scenario did not materialize two sibling subtrees")


def test_expansion_sorts_only_the_opened_subtree(lazy_model_generator):
    generator = lazy_model_generator
    shim = _SortShim(generator)

    shim._sort_children_combined("", PRIMARY_MODE, None)
    opened, widget_id, sibling = _materialized_pair(generator)
    sorted_opened = _flatten(opened)
    sorted_sibling = _flatten(sibling)

    # Disturb both subtrees so a sort has real work to do in each.
    opened.children.reverse()
    sibling.children.reverse()
    assert _flatten(opened) != sorted_opened, "reversal did not disturb the opened subtree"
    assert _flatten(sibling) != sorted_sibling, "reversal did not disturb the sibling"

    shim._sort_children_combined(widget_id, PRIMARY_MODE, None, recurse_mode="expanded")

    assert _flatten(opened) == sorted_opened, "opened subtree was not re-sorted"
    # The scoping proof: before the fix `node` was ignored and this sibling
    # would have been re-sorted back to `sorted_sibling` as well.
    assert _flatten(sibling) != sorted_sibling, "sort escaped the opened subtree"


def test_full_sort_still_covers_the_entire_tree(lazy_model_generator):
    generator = lazy_model_generator
    shim = _SortShim(generator)

    shim._sort_children_combined("", PRIMARY_MODE, None)
    opened, _widget_id, sibling = _materialized_pair(generator)
    sorted_opened = _flatten(opened)
    sorted_sibling = _flatten(sibling)

    opened.children.reverse()
    sibling.children.reverse()

    shim._sort_children_combined("", PRIMARY_MODE, None)

    assert _flatten(opened) == sorted_opened
    assert _flatten(sibling) == sorted_sibling

