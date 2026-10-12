"""The default opponent-model path must be behaviourally identical to pre-change.

``test_golden_master.py`` already compares against committed fixtures, which
were generated before this refactor and so are themselves an identity proof.
This file makes the claim explicit and self-contained: it re-runs each scenario
with ``_collapse_children`` replaced by the **literal expressions that used to
appear inline** in ``tree_generator.py``, and asserts the snapshots match
field for field.

The difference matters. A fixture comparison proves "output equals a recorded
value". This proves "the new indirection computes the same function as the old
code", which survives a fixture regeneration.

The two pre-change literals, quoted verbatim from the replaced sites:

    strategic3 (2 sites):
        min(child_scores) if children[0].is_opponent_choice else max(child_scores)

    cumulative2 (3 sites):
        alpha * min(child_scores) + (1 - alpha) * (sum(child_scores) / len(child_scores))
        ... if opponent level, else max(child_scores)
"""

import pytest

pytest.importorskip("tkinter")

from golden_master_harness import SORT_MODES, generate_model_snapshot  # noqa: E402
from golden_master_scenarios import SCENARIOS  # noqa: E402
from qtr_pairing_process.opponent_models import (  # noqa: E402
    HardMirror,
    SoftenedMirror,
)
from qtr_pairing_process.tree_generator import TreeGenerator  # noqa: E402

pytestmark = pytest.mark.requires_tk

# enhanced_v3_scores is the only mode that drives both the strategic3 and the
# cumulative2 opponent pathways; the other four modes never reach them. Both
# mutation controls for this refactor failed exclusively in this mode, which is
# the evidence for that claim rather than a reading of the call graph.
IDENTITY_MODE = "enhanced_v3_scores"


def _legacy_collapse(self, child_scores, is_opponent_level, model):
    """The pre-change inline arithmetic, reimplemented literally."""
    if not is_opponent_level:
        return max(child_scores)
    if isinstance(model, SoftenedMirror):
        alpha = model.alpha
        return alpha * min(child_scores) + (1 - alpha) * (
            sum(child_scores) / max(1, len(child_scores))
        )
    return min(child_scores)


@pytest.fixture
def legacy_collapse(monkeypatch):
    monkeypatch.setattr(TreeGenerator, "_collapse_children", _legacy_collapse)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.slug)
def test_default_models_match_the_pre_change_literals(scenario, monkeypatch):
    current = generate_model_snapshot(scenario, IDENTITY_MODE)
    monkeypatch.setattr(TreeGenerator, "_collapse_children", _legacy_collapse)
    legacy = generate_model_snapshot(scenario, IDENTITY_MODE)
    assert current == legacy, (
        f"scenario {scenario.slug}: routing opponent collapse through the model "
        "layer changed output. The default must be byte-identical."
    )


def test_the_identity_mode_actually_exercises_the_collapse():
    """Guards against the identity test passing because nothing ran.

    If ``_collapse_children`` were never called, the comparison above would
    compare two identical no-ops and prove nothing.
    """
    calls = []
    original = TreeGenerator._collapse_children

    def counting(self, child_scores, is_opponent_level, model):
        calls.append((tuple(child_scores), is_opponent_level, type(model).__name__))
        return original(self, child_scores, is_opponent_level, model)

    TreeGenerator._collapse_children = counting
    try:
        generate_model_snapshot(SCENARIOS[0], IDENTITY_MODE)
    finally:
        TreeGenerator._collapse_children = original

    assert calls, "_collapse_children was never called"
    assert any(is_opp for _scores, is_opp, _name in calls), "no opponent-choice levels"
    model_names = {name for _scores, _opp, name in calls}
    assert "HardMirror" in model_names, "strategic3 pathway never ran"
    assert "SoftenedMirror" in model_names, "cumulative2 pathway never ran"


def test_identity_mode_is_a_real_sort_mode():
    assert IDENTITY_MODE in SORT_MODES


def test_legacy_reimplementation_matches_the_models_directly():
    """The legacy stand-in must be the old arithmetic, not a copy of the new.

    Without this, ``_legacy_collapse`` could silently drift into calling the
    model layer and the identity test would become circular.
    """
    generator = TreeGenerator.__new__(TreeGenerator)
    cases = [[3.0, 1.0, 2.0], [5.0], [-2.0, -7.5, 0.0, 4.25]]
    for scores in cases:
        hard = HardMirror()
        assert _legacy_collapse(generator, scores, True, hard) == min(scores)
        assert _legacy_collapse(generator, scores, False, hard) == max(scores)

        soft = SoftenedMirror(0.80)
        expected = 0.80 * min(scores) + (1.0 - 0.80) * (
            sum(scores) / max(1, len(scores))
        )
        assert _legacy_collapse(generator, scores, True, soft) == expected
        assert generator._collapse_children(scores, True, soft) == expected


def test_byte_identity_required_preserving_the_operation_order():
    """``1.0 - alpha`` is not ``0.20``, and the difference is observable.

    Writing the complement as a literal 0.20 instead of computing ``1.0 -
    alpha`` changes results in the last bits -- this assertion failed when the
    test was first written with a 0.20 literal, which is how the point was
    found. It is the reason ``SoftenedMirror.combine`` reproduces the original
    expression's operation order rather than tidying it up.
    """
    alpha = 0.80
    assert (1.0 - alpha) != 0.20
    assert (1.0 - alpha) == 0.19999999999999996

    scores = [3.0, 1.0, 2.0]
    mean = sum(scores) / len(scores)
    faithful = alpha * min(scores) + (1.0 - alpha) * mean
    tidied = alpha * min(scores) + 0.20 * mean
    assert faithful != tidied
    assert SoftenedMirror(alpha).combine(scores) == faithful
