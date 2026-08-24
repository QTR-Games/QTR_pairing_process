"""Tests for the opt-in risk columns.

Deliberately Tk-free: the annotation walks the plain PairingNode model and the
projection decision is a pure function of the model, so both can be pinned
without a GUI.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from qtr_pairing_process.distribution_scoring import DistributionScorer, annotate_risk
from qtr_pairing_process.pairing_model import PairingNode, TreeProjector
from qtr_pairing_process.tree_generator import TreeGenerator, risk_columns_requested


@pytest.fixture
def risk_columns_off():
    """Guarantee the class-level flag is restored.

    It is process-global, so a leaked ``True`` would silently change the
    projected values tuple for every later test -- including the golden master.
    """
    previous = TreeProjector.RISK_COLUMNS_ENABLED
    TreeProjector.RISK_COLUMNS_ENABLED = False
    yield
    TreeProjector.RISK_COLUMNS_ENABLED = previous


def _node(
    text,
    base,
    depth,
    is_opponent_choice=False,
    parent=None,
    *,
    counts_toward_total=False,
    base_for_our_team=None,
):
    node = PairingNode(
        text=text, base=base, depth=depth,
        is_opponent_choice=is_opponent_choice, parent=parent,
        counts_toward_total=counts_toward_total,
        base_for_our_team=base if base_for_our_team is None else base_for_our_team,
    )
    if parent is not None:
        parent.children.append(node)
    return node


def _linear_tree(bases):
    """Root -> a single chain of resolution nodes totalling ``sum(bases)``."""
    root = _node("Pairings", 0, 0)
    current = root
    for index, base in enumerate(bases):
        current = _node(
            f"P{index} rating {base}",
            base,
            index + 1,
            parent=current,
            counts_toward_total=True,
        )
    return root


# --------------------------------------------------------------------------
# projection gating
# --------------------------------------------------------------------------

def test_projection_is_unchanged_while_risk_columns_are_disabled(risk_columns_off):
    """The default path must stay byte-identical: golden fixtures hash it."""
    root = _linear_tree([3])
    leaf = root.children[0]

    values = TreeProjector.values_for(leaf)

    assert values == (3, 0, 0, 0)
    assert all(isinstance(value, int) for value in values)


def test_enabling_risk_columns_appends_exactly_four_cells(risk_columns_off):
    root = _linear_tree([3])
    leaf = root.children[0]
    leaf.risk_win_prob = 0.324
    leaf.risk_floor = 10
    leaf.risk_p10 = 13
    leaf.risk_std = 2.16

    TreeProjector.RISK_COLUMNS_ENABLED = True
    values = TreeProjector.values_for(leaf)

    assert len(values) == 8
    assert values[:4] == (3, 0, 0, 0)
    assert values[4:] == ("32.4%", "10", "13", "2.2")


def test_unannotated_nodes_render_blank_not_zero_percent(risk_columns_off):
    """A node that was never scored must not read as a genuine 0% chance."""
    root = _linear_tree([3])
    leaf = root.children[0]

    TreeProjector.RISK_COLUMNS_ENABLED = True
    values = TreeProjector.values_for(leaf)

    assert values[4:] == ("", "", "", "")


def test_risk_columns_require_the_model_engine(monkeypatch):
    """Risk reads the model tree, so it cannot work on the widget engine."""
    monkeypatch.setenv("QTR_RISK", "1")

    monkeypatch.setenv("QTR_ENGINE", "widget")
    assert risk_columns_requested() is False

    monkeypatch.setenv("QTR_ENGINE", "model")
    assert risk_columns_requested() is True

    monkeypatch.delenv("QTR_RISK")
    assert risk_columns_requested() is False


@pytest.mark.parametrize("raw_value", ["oops", "nan", "inf", "-inf"])
def test_invalid_risk_lambda_falls_back_to_default(monkeypatch, raw_value):
    monkeypatch.setenv("QTR_RISK_LAMBDA", raw_value)

    generator = TreeGenerator(treeview=SimpleNamespace(tree=None), strategic_preferences={})

    assert generator.risk_lambda == 1.0


# --------------------------------------------------------------------------
# annotation semantics
# --------------------------------------------------------------------------

def test_annotation_reports_round_totals_not_subtree_totals():
    """The property most likely to regress silently.

    ``distribution_for`` returns the total accumulated from a node *downward*.
    Displayed raw, the last node of a 3+4+5 chain would claim a floor of 5.
    Every node must instead report the finished round total, 12.
    """
    root = _linear_tree([3, 4, 5])
    scorer = DistributionScorer(threshold=15.0, lam=1.0, objective="win_probability")

    annotated = annotate_risk(root, scorer)

    assert annotated == 3
    chain = []
    current = root
    while current.children:
        current = current.children[0]
        chain.append(current)
    assert [node.risk_floor for node in chain] == [12, 12, 12]
    assert [node.risk_p10 for node in chain] == [12, 12, 12]


def test_annotation_banks_points_from_our_perspective_not_the_raw_base():
    """Regression: annotate_risk must bank the same value distribution_for does.

    The generator stores the OPPONENT's rating in ``base`` for opponent-side
    resolutions and our complement in ``base_for_our_team``. Banking raw
    ``base`` diverged on 41.8% of contributing nodes in the real 5v5 tree,
    with a maximum banked-total error of 18 points against a win_need of 28.
    """
    # A 1-10 chain where our perspective (8) is the complement of the stored
    # opponent rating (3): 11 - 3 = 8.
    root = _node("Pairings", 0, 0)
    first = _node("Ours rating 6", 6, 1, parent=root, counts_toward_total=True)
    second = _node(
        "Theirs rating 3", 3, 2, parent=first,
        counts_toward_total=True, base_for_our_team=8,
    )
    third = _node("Ours rating 7", 7, 3, parent=second, counts_toward_total=True)

    scorer = DistributionScorer(threshold=16.5, lam=1.0, objective="win_probability")
    annotate_risk(root, scorer)

    # Round total from OUR perspective is 6 + 8 + 7 = 21, not 6 + 3 + 7 = 16.
    assert [n.risk_floor for n in (first, second, third)] == [21, 21, 21]
    assert [n.risk_p10 for n in (first, second, third)] == [21, 21, 21]
    # 21 clears 16.5, so every node is a certain win. Banking raw base would
    # have produced 16, which does not.
    assert third.risk_win_prob == pytest.approx(1.0)


def test_annotation_skips_the_root_so_it_renders_blank():
    root = _linear_tree([3, 4])
    scorer = DistributionScorer(threshold=15.0, lam=1.0, objective="win_probability")

    annotate_risk(root, scorer)

    assert root.risk_win_prob == -1.0


def test_a_determined_total_scores_zero_or_one_against_the_threshold():
    """With no choices left the round total is fixed, so P(win) is degenerate.

    Each tree gets its own scorer on purpose. These synthetic nodes leave the
    canonical state fields empty, so two different trees would otherwise share
    memo entries and contaminate each other's results.
    """
    losing = _linear_tree([3, 4, 5])   # 12 <= 15
    annotate_risk(losing, DistributionScorer(15.0, 1.0, "win_probability"))
    assert losing.children[0].risk_win_prob == 0.0

    winning = _linear_tree([6, 6, 6])  # 18 > 15
    annotate_risk(winning, DistributionScorer(15.0, 1.0, "win_probability"))
    assert winning.children[0].risk_win_prob == 1.0


def test_annotate_risk_tolerates_a_missing_tree():
    scorer = DistributionScorer(threshold=15.0, lam=1.0, objective="win_probability")
    assert annotate_risk(None, scorer) == 0

def test_risk_sort_fields_cover_every_risk_column_and_name_real_node_fields():
    """A typo here silently makes a column unsortable, so pin the mapping."""
    node = _node("probe", 1, 1)
    assert set(TreeProjector.RISK_SORT_FIELDS) == set(TreeProjector.RISK_COLUMNS)
    for column_id, field in TreeProjector.RISK_SORT_FIELDS.items():
        assert hasattr(node, field), f"{column_id} maps to missing field {field}"


# Sentinel/blank-row sorting used to be pinned here against a *copy* of the
# production logic, which is precisely why the Floor/P10 defect survived: the
# mirror only ever exercised P(win), where the per-field check happens to work.
# Both render paths now share TreeProjector.risk_sort_key, covered for every
# risk column in test_risk_sort_paths.py.
