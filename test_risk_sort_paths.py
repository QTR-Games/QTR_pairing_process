"""Risk-column sorting across both render paths, and opponent-first perspective.

Two defects motivated this file, both found in review of the risk work:

1. The eager render path -- which is the *default* (``QTR_RENDER`` defaults to
   ``eager``) -- had no risk handling at all, so clicking P(win)/Floor/P10/Sigma
   silently sorted by Sort Value. Only the lazy path was wired up.
2. ``_generate_combinations_model`` hardcoded the opening ``attacker_side`` to
   ``"our"``. Opponent-first scenarios swap the rosters before generation, so
   every rating was then kept raw instead of complemented into our perspective.
"""

from __future__ import annotations

import pytest

from golden_master_harness import tk_treeview
from golden_master_scenarios import THREE_V_THREE_UNIFORM
from qtr_pairing_process.pairing_model import TreeProjector
from qtr_pairing_process.tree_generator import TreeGenerator
from qtr_pairing_process.ui_manager_v2 import UiManager


class FakeTree:
    """Just enough ttk.Treeview surface for ``_sort_children_combined``."""

    def __init__(self, parent, children, meta):
        self._children = {parent: list(children)}
        self._meta = meta
        self._parent = parent

    def get_children(self, node=""):
        return list(self._children.get(node, []))

    def item(self, node, option=None, **kwargs):
        data = self._meta[node]
        if option == "text":
            return data["text"]
        return data

    def move(self, child, parent, _index):
        order = self._children.setdefault(parent, [])
        if child in order:
            order.remove(child)
        order.append(child)


class FakeTreeView:
    def __init__(self, tree):
        self.tree = tree


def _risk_node(win_prob=None, floor=0, p10=0, std=0.0):
    node = type("FakeModelNode", (), {})()
    node.risk_win_prob = -1.0 if win_prob is None else win_prob
    node.risk_floor = floor
    node.risk_p10 = p10
    node.risk_std = std
    node.sort_value = 0
    return node


def _eager_sorted_by(column_id, state, nodes_by_id, texts):
    """Run the eager sorter over a fake tree and return the resulting order."""
    meta = {
        item_id: {"text": texts[item_id], "values": (3, 0), "open": False}
        for item_id in nodes_by_id
    }
    tree = FakeTree("root", list(nodes_by_id), meta)

    projector = type("Projector", (), {"widget_to_node": dict(nodes_by_id)})()

    ui = UiManager.__new__(UiManager)
    ui.treeview = FakeTreeView(tree)
    # No ``_use_lazy_rendering`` attribute -> _using_lazy_model_render() is
    # False, which is exactly the default eager configuration under test.
    ui.tree_generator = type("TreeGen", (), {"projector": projector})()
    ui.column_sort_states = {column_id: state}

    ui._sort_children_combined("root", None, column_id)

    return tree.get_children("root")


def test_eager_path_sorts_by_risk_column_not_sort_value():
    """Regression: the default render path ignored risk columns entirely.

    Every row carries the same Sort Value here, so if the risk branch is
    missing the rows keep their alphabetical order instead of ranking by
    P(win).
    """
    nodes_by_id = {
        "a": _risk_node(0.10),
        "b": _risk_node(0.90),
        "c": _risk_node(0.50),
    }
    texts = {"a": "A", "b": "B", "c": "C"}

    order = _eager_sorted_by("P(win)", "desc", nodes_by_id, texts)

    assert order == ["b", "c", "a"], (
        "eager path did not rank by P(win); it likely fell through to Sort Value"
    )


def test_eager_path_sinks_unannotated_rows_in_both_directions():
    """The blank row is named so that the text fallback would rank it *first*.

    Without the risk branch every secondary key is an identical Sort Value, so
    the alphabetical fallback decides the order and "Aaa" leads. Only real risk
    handling can push it to the bottom in both directions.
    """
    for state, reverse in (("desc", True), ("asc", False)):
        nodes_by_id = {
            "a": _risk_node(0.10),
            "b": _risk_node(0.90),
            "blank": _risk_node(None),
        }
        texts = {"a": "Mid", "b": "Top", "blank": "Aaa"}

        order = _eager_sorted_by("P(win)", state, nodes_by_id, texts)

        assert order[-1] == "blank", (
            f"unannotated row did not sink with reverse={reverse}"
        )


@pytest.mark.parametrize("column_id", sorted(TreeProjector.RISK_SORT_FIELDS))
def test_both_paths_share_one_blank_rule_for_every_risk_column(column_id):
    """Floor and P10 default to 0, which is also a legitimate banked total.

    Gating on each field's own value therefore treated a genuine zero as if it
    were blank (and vice versa). The shared helper keys off the single
    annotation field instead.
    """
    scored_zero = _risk_node(0.0, floor=0, p10=0, std=0.0)
    blank = _risk_node(None)

    for reverse in (True, False):
        rows = [blank, scored_zero]
        rows.sort(
            key=lambda n: TreeProjector.risk_sort_key(n, column_id, reverse),
            reverse=reverse,
        )
        assert rows[-1] is blank, (
            f"{column_id}: blank row did not sink with reverse={reverse}"
        )


def test_risk_sort_key_declines_non_risk_columns():
    node = _risk_node(0.5)
    assert TreeProjector.risk_sort_key(node, "Rating", False) is None
    assert TreeProjector.risk_sort_key(node, "#0", False) is None


@pytest.mark.requires_tk
def test_opponent_first_complements_ratings_into_our_perspective(monkeypatch):
    """Regression: opponent-first kept opponent ratings raw.

    ``on_generate_combinations`` swaps the rosters when the opponent chooses
    first, so the opening side is theirs. Hardcoding ``"our"`` made
    ``_rating_from_our_perspective`` a no-op exactly where it was needed, and
    every risk figure for those scenarios was computed from the wrong side.
    """
    monkeypatch.setenv("QTR_ENGINE", "model")
    scenario = THREE_V_THREE_UNIFORM

    with tk_treeview() as treeview:
        generator = TreeGenerator(
            treeview=treeview,
            sort_alpha=False,
            strategic_preferences={},
            rating_system=scenario.rating_system,
        )
        generator.generate_combinations(
            list(scenario.opponent_players),
            list(scenario.our_players),
            scenario.opponent_ratings,
            scenario.our_ratings,
            our_team_first=False,
        )

        span = generator.rating_min + generator.rating_max
        first_level = generator.model_root.children
        assert first_level, "expected a generated first choice level"

        for node in first_level:
            assert node.base_for_our_team == span - node.base

        # A complement that happens to equal its input (the midpoint) would let
        # the old no-op pass, so require at least one genuinely flipped rating.
        assert any(
            node.base_for_our_team != node.base for node in first_level
        ), "no rating was actually complemented; the fix is not exercised"
