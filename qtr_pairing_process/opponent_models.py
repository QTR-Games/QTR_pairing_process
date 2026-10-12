"""Pluggable opponent models for branch selection at opponent-choice nodes.

Why this module exists
----------------------
At a node where the OPPONENT chooses, the engine has to decide what value the
parent inherits. Historically that decision was spelled inline at five separate
sites in ``tree_generator.py``, in two different shapes:

* ``strategic3`` used ``min(child_scores)`` -- a perfectly adversarial opponent.
* ``cumulative2`` used ``alpha*min + (1-alpha)*mean`` with ``alpha = 0.80`` -- a
  *softened* adversary, already runtime-tunable via the ``cumulative2.alpha``
  preference.

Those are two different opponent models, and nothing named them as such, so
nothing stopped them drifting apart. This module names them, so that selecting
an opponent model is one decision applied consistently rather than five
independent literals.

What the defaults are
---------------------
``HardMirror`` for ``strategic3`` and ``SoftenedMirror(0.80)`` for
``cumulative2`` reproduce the previous behaviour exactly. Swapping the default
is a deliberate act, not a side effect of touching this file.

The posture these encode, and its measured accuracy
---------------------------------------------------
Both mirror models assume the opponent minimises *our* total on *our own*
numbers. ``docs/SCORING_MATHEMATICS.md`` S11.2 is careful that this is a
**bound**, not a claim about what the opponent wants: Finding 12 measured two
teams' views of the same 25 matchups at r = -0.049, so we cannot infer their
preferences from our ratings.

``qtr_pairing_process/opponent_comparison`` backtests the posture against the
only logged opponent decisions we have. Read its report before treating
``alpha`` as calibrated -- on that corpus the adversarial line is taken far less
often than ``alpha = 0.80`` asserts, but the sample is small enough that the
honest response is to report the interval, not to retune.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

__all__ = [
    "GOOD",
    "EVEN",
    "SOFT_DODGE",
    "HARD_DODGE",
    "LABEL_ALPHABET",
    "LabelsUnavailable",
    "UnidentifiedLabel",
    "OpponentModel",
    "HardMirror",
    "SoftenedMirror",
    "RivalLabelUtility",
    "DEFAULT_STRATEGIC3_MODEL",
    "DEFAULT_CUMULATIVE2_MODEL",
    "register",
    "get_model",
    "available_models",
]


# --------------------------------------------------------------- label space

#: The alphabet the rival tool (Pear Master) labels locked pairings with, read
#: from five WTC 2026 navigation logs. Note there are FOUR categories, not the
#: three quoted in ``docs/WHITEPAPER_2026.md`` S5.1 -- see ``HARD_DODGE``.
GOOD = "GOOD"
EVEN = "EVEN"
SOFT_DODGE = "SOFT DODGE"

#: The fourth category. It occurs ZERO times across all five logged rounds, so
#: its weight is not identified by the corpus: any value whatsoever reconciles
#: the observed round totals. Treating it as 0 would be inventing a parameter
#: and calling it a measurement, so ``RivalLabelUtility`` refuses it instead.
HARD_DODGE = "HARD DODGE"

LABEL_ALPHABET = (GOOD, EVEN, SOFT_DODGE, HARD_DODGE)


class LabelsUnavailable(RuntimeError):
    """Raised when a label-space model is asked to score rating-space inputs.

    The engine's tree carries ratings, not ``GOOD``/``EVEN``/``SOFT DODGE``
    labels, and Finding 12 (r = -0.049) says our ratings cannot be converted
    into the opponent's labels. So a label-space model genuinely cannot run
    inside the tree, and saying so loudly beats silently inventing a mapping.
    """


class UnidentifiedLabel(ValueError):
    """Raised when scoring a label whose weight the corpus does not identify."""


# ------------------------------------------------------------------ protocol


@runtime_checkable
class OpponentModel(Protocol):
    """How an opponent-choice node collapses its children into one value."""

    #: Stable identifier used by the registry and by comparison reports.
    name: str

    #: True when the model scores labels rather than ratings, and therefore
    #: cannot be driven by the engine's tree. See :class:`LabelsUnavailable`.
    requires_labels: bool

    def combine(self, child_scores: Sequence[float]) -> float:
        """Value the parent inherits from an opponent-choice node."""

    def predict_index(self, child_scores: Sequence[float]) -> int:
        """Index of the branch this model expects the opponent to take."""


# -------------------------------------------------------------------- models


class HardMirror:
    """A perfectly adversarial opponent: takes whichever branch is worst for us.

    This is the historical ``strategic3`` behaviour, ``min(child_scores)``,
    unchanged.
    """

    name = "hard_mirror"
    requires_labels = False

    def combine(self, child_scores: Sequence[float]) -> float:
        return min(child_scores)

    def predict_index(self, child_scores: Sequence[float]) -> int:
        return min(range(len(child_scores)), key=lambda i: child_scores[i])

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "HardMirror()"


class SoftenedMirror:
    """An opponent who usually takes the adversarial line but not always.

    ``alpha*min + (1-alpha)*mean``. At ``alpha = 1`` this is
    :class:`HardMirror`; at ``alpha = 0`` the opponent is treated as choosing
    uniformly at random.

    This is the historical ``cumulative2`` behaviour, and ``alpha`` defaults to
    the ``cumulative2.alpha`` preference (0.80). That 0.80 is an assumption, not
    a fitted value -- ``docs/WHITEPAPER_2026.md`` S5.3 flags fitting it as a
    standing research gap.
    """

    name = "softened_mirror"
    requires_labels = False

    def __init__(self, alpha: float = 0.80) -> None:
        if not 0.0 <= alpha <= 1.0:
            raise ValueError(f"alpha must be in [0, 1], got {alpha!r}")
        self.alpha = float(alpha)

    def combine(self, child_scores: Sequence[float]) -> float:
        min_child = min(child_scores)
        mean_child = sum(child_scores) / max(1, len(child_scores))
        return self.alpha * min_child + (1.0 - self.alpha) * mean_child

    def predict_index(self, child_scores: Sequence[float]) -> int:
        # The modal prediction is still the adversarial branch; alpha describes
        # how much weight the VALUE carries, not a different argmin.
        return min(range(len(child_scores)), key=lambda i: child_scores[i])

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"SoftenedMirror(alpha={self.alpha})"


class RivalLabelUtility:
    """The rival tool's own objective, recovered from five WTC 2026 logs.

    ``GOOD = +1``, ``EVEN = 0``, ``SOFT DODGE = -10``
    (``docs/WHITEPAPER_2026.md`` S5.1). Reconciles all five logged rounds with
    zero residual against the values those logs print.

    **This is a model of how a rival behaves. It is not our objective, and must
    never be offered as one.** S5.3 shows it inverts against the real win
    condition: a round is won 3-of-5, yet ``4 GOOD, 0 EVEN, 1 SOFT`` scores -6
    and ranks BELOW ``0 GOOD, 5 EVEN, 0 SOFT`` at 0, despite winning four games
    outright. Anything tuned toward this scalar inherits that inversion.

    Two deliberate refusals, both encoding measured gaps rather than taste:

    * :meth:`combine` raises :class:`LabelsUnavailable`, because the engine's
      tree holds ratings and Finding 12 (r = -0.049) refutes converting ours
      into theirs.
    * :meth:`value_of` raises :class:`UnidentifiedLabel` on ``HARD DODGE``,
      which never occurs in the corpus and so has no identified weight.

    Only differences between labels affect a choice, and every round carries
    exactly five cells, so adding a constant ``c`` to all three weights shifts
    every round total by ``5c`` without changing any decision. The decision rule
    therefore depends only on ``GOOD - EVEN = +1`` and ``EVEN - SOFT = +10``.
    """

    name = "rival_label_utility"
    requires_labels = True

    def __init__(self, good: float = 1.0, even: float = 0.0, soft: float = -10.0) -> None:
        self.good = float(good)
        self.even = float(even)
        self.soft = float(soft)

    @property
    def weights(self) -> dict[str, float]:
        return {GOOD: self.good, EVEN: self.even, SOFT_DODGE: self.soft}

    def value_of(self, label: str) -> float:
        """Value one labelled pairing. Raises on the unidentified fourth label."""
        if label == HARD_DODGE:
            raise UnidentifiedLabel(
                "HARD DODGE occurs zero times in the logged corpus, so its weight "
                "is not identified. Scoring it would invent a parameter."
            )
        try:
            return self.weights[label]
        except KeyError:
            raise UnidentifiedLabel(f"unknown label {label!r}") from None

    def score_labels(self, labels: Sequence[str]) -> float:
        """Total value of a set of labelled pairings, e.g. a whole round."""
        return sum(self.value_of(label) for label in labels)

    def combine(self, child_scores: Sequence[float]) -> float:
        raise LabelsUnavailable(
            "RivalLabelUtility scores GOOD/EVEN/SOFT DODGE labels, not ratings. "
            "The engine's tree carries ratings, and Finding 12 (r = -0.049) "
            "refutes deriving the opponent's labels from our ratings, so this "
            "model cannot drive tree search."
        )

    def predict_index(self, child_scores: Sequence[float]) -> int:
        raise LabelsUnavailable(
            "RivalLabelUtility predicts over labelled candidates; use "
            "predict_index_from_labels()."
        )

    def predict_index_from_labels(self, candidate_labels: Sequence[str]) -> int:
        """Which labelled candidate the rival's objective says they take.

        Their objective is *their* gain, which is our loss, so they take the
        candidate we value least.
        """
        values = [self.value_of(label) for label in candidate_labels]
        return min(range(len(values)), key=lambda i: values[i])

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"RivalLabelUtility(good={self.good}, even={self.even}, soft={self.soft})"


# ------------------------------------------------------------------ defaults

#: Reproduces the historical ``strategic3`` opponent handling exactly.
DEFAULT_STRATEGIC3_MODEL = HardMirror()

#: Reproduces the historical ``cumulative2`` opponent handling exactly when
#: constructed with the ``cumulative2.alpha`` preference.
DEFAULT_CUMULATIVE2_MODEL = SoftenedMirror(0.80)


# ------------------------------------------------------------------ registry

_REGISTRY: dict[str, OpponentModel] = {}


def register(model: OpponentModel) -> OpponentModel:
    """Add a model to the by-name registry."""
    _REGISTRY[model.name] = model
    return model


def get_model(name: str) -> OpponentModel:
    """Look a model up by name."""
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(f"unknown opponent model {name!r}; have {sorted(_REGISTRY)}") from None


def available_models() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


register(DEFAULT_STRATEGIC3_MODEL)
register(DEFAULT_CUMULATIVE2_MODEL)
register(RivalLabelUtility())
