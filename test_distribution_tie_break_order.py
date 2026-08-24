"""The reported distribution must not depend on sibling order.

``DistributionScorer`` picks our move with ``max(child_dists, key=rank)``.
``max`` returns the *first* maximal element, so when two children rank
identically the winner used to be decided by whichever happened to be listed
first -- and sibling order is controlled by the UI's presentation. The same
decision could therefore display a different spread depending only on how the
offer was presented.

These tests build two children that are deliberately equal on rank but
different in shape, then score the same tree with the children in both orders.
The objective value must be equal either way (it always was), and so must the
reported ceiling and floor (it was not).

No Tk, no tree generation -- a hand-built stub keeps this fast and
cross-platform.
"""

from __future__ import annotations

import pytest

from qtr_pairing_process.distribution_scoring import DistributionScorer


class StubNode:
    """Minimal node satisfying the contract DistributionScorer reads.

    Fields mirror the real model node: the ``state_*`` tuple feeds
    ``_canonical_key`` (so distinct nodes must differ or they collide in the
    memo), ``counts_toward_total`` is the documented explicit override, and
    ``is_opponent_choice`` on the *children* decides whether a level is mixed
    (opponent) or maximised (ours).
    """

    def __init__(self, name, base=0, counts=False, opponent=False, children=()):
        self.text = name
        self.base = base
        self.counts_toward_total = counts
        self.is_opponent_choice = opponent
        self.children = list(children)
        self.parent = None
        for child in self.children:
            child.parent = self
        self.state_attacker = name
        self.state_attacker_side = "ours"
        self.state_choosing_side = "ours"
        self.state_our_pool = (name,)
        self.state_opponent_pool = (name,)
        self.state_choice_pool = (name,)


def _branch(name, low, high):
    """An opponent-choice branch that mixes uniformly to {low, high}.

    With ``lam=0`` the softmax over opponent options is uniform, so this
    branch's distribution is exactly 50/50 between the two leaf values and its
    mean is their midpoint.
    """
    return StubNode(
        name,
        counts=False,
        children=[
            StubNode(f"{name} rating {low}", base=low, counts=True, opponent=True),
            StubNode(f"{name} rating {high}", base=high, counts=True, opponent=True),
        ],
    )


def _build(order):
    """Root whose two equally-ranked children are supplied in ``order``.

    ``wide`` spans 0..4 and ``narrow`` spans 1..3. Both have mean 2.0, so they
    tie on the expected-value objective while differing in ceiling and floor --
    exactly the situation where the tie-break becomes observable.
    """
    branches = {"wide": _branch("wide", 0, 4), "narrow": _branch("narrow", 1, 3)}
    return StubNode("root", children=[branches[name] for name in order])


def _score(order):
    scorer = DistributionScorer(threshold=2, lam=0.0, objective="expected")
    return scorer.outcome_for(_build(order))


def test_equal_ranked_children_are_actually_tied():
    """Guard: if these stop tying, the tests below prove nothing."""
    scorer = DistributionScorer(threshold=2, lam=0.0, objective="expected")
    root = _build(("wide", "narrow"))
    wide, narrow = (scorer.outcome_for(child) for child in root.children)

    assert wide.expected == pytest.approx(narrow.expected)
    assert (wide.ceiling, wide.floor) != (narrow.ceiling, narrow.floor)


def test_reported_spread_is_independent_of_sibling_order():
    forward = _score(("wide", "narrow"))
    reverse = _score(("narrow", "wide"))

    assert forward.ceiling == reverse.ceiling
    assert forward.floor == reverse.floor
    assert forward.regret == reverse.regret


def test_objective_value_is_independent_of_sibling_order():
    """The scores themselves were never order-dependent; keep it that way."""
    forward = _score(("wide", "narrow"))
    reverse = _score(("narrow", "wide"))

    assert forward.expected == pytest.approx(reverse.expected)


def test_tie_break_prefers_the_wider_upside():
    """Pins the documented rule rather than just 'some stable choice'.

    Among equally-ranked options the scorer reports the one with more upside,
    which is the behaviour the play-to-your-outs framing depends on.
    """
    assert _score(("narrow", "wide")).ceiling == 4
