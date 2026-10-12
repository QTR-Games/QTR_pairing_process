"""Replay logged opponent decisions and score each opponent model against them.

What can and cannot be measured here
------------------------------------
A model is scoreable on a decision only if the corpus supplies the inputs that
model consumes. That is a stronger constraint than sample size, and it bites
differently for each model:

* **Mirror models** (``HardMirror``, ``SoftenedMirror``) rank branches by *our*
  total on *our* rating grid. The WTC 2026 corpus has no rating matrix -- the
  logs record labels and names, never numbers -- so these models cannot be
  scored cell by cell. What the logs *do* record is the rival tool's verdict on
  every opponent choice (``strongest_line`` / ``slipped``), which is the same
  adversarial question asked in label space. That is reported as the
  **adversarial-line rate**, and it is the nearest honest proxy.

* **Label models** (``RivalLabelUtility``) need a label for every candidate, and
  labels exist only for pairings that actually happened. The road not taken is
  never labelled, so a counterfactual cannot be scored at all.

The point of the ``NotEvaluable`` branch is that these gaps get *counted and
named* in the output rather than quietly reducing the denominator.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from qtr_pairing_process.opponent_comparison.corpus import Corpus
from qtr_pairing_process.opponent_comparison.stats import wilson_interval

__all__ = [
    "Evaluable",
    "NotEvaluable",
    "ModelResult",
    "AgreementBreakdown",
    "BacktestReport",
    "adversarial_line_rate",
    "score_label_model",
    "run_backtest",
]


@dataclass(frozen=True)
class Evaluable:
    """The model produced a prediction for this decision."""

    predicted: str
    correct: bool


@dataclass(frozen=True)
class NotEvaluable:
    """The model could not be run here, and why."""

    reason: str


Outcome = Evaluable | NotEvaluable


@dataclass
class ModelResult:
    model_name: str
    evaluable: int = 0
    correct: int = 0
    not_evaluable: dict[str, int] = field(default_factory=dict)

    @property
    def accuracy(self) -> float | None:
        if self.evaluable == 0:
            return None
        return self.correct / self.evaluable

    @property
    def interval(self) -> tuple[float, float]:
        return wilson_interval(self.correct, self.evaluable)

    @property
    def separates_from_chance(self) -> bool:
        """Does the interval exclude 0.5?

        False whenever the data cannot tell this model apart from a coin flip --
        which includes the case of no evaluable decisions at all.
        """
        if self.evaluable == 0:
            return False
        low, high = self.interval
        return low > 0.5 or high < 0.5

    def excludes(self, value: float) -> bool:
        """Does the interval exclude a specific hypothesised rate?"""
        if self.evaluable == 0:
            return False
        low, high = self.interval
        return value < low or value > high


@dataclass
class AgreementBreakdown:
    """Where two models agree and where they diverge.

    Read the divergence count. Do **not** read the agreement count as
    confidence -- see :class:`BacktestReport`.
    """

    model_a: str
    model_b: str
    agree: int = 0
    disagree: int = 0
    undetermined: int = 0

    @property
    def disagreement_rate(self) -> float | None:
        decided = self.agree + self.disagree
        if decided == 0:
            return None
        return self.disagree / decided


@dataclass
class BacktestReport:
    corpus_id: str
    decisions_total: int
    decisions_forced: int
    decisions_free: int
    adversarial_line: ModelResult
    models: dict[str, ModelResult]
    agreement: AgreementBreakdown | None
    caveats: tuple[str, ...]

    @property
    def any_model_separates(self) -> bool:
        return any(r.separates_from_chance for r in self.models.values()) or (
            self.adversarial_line.separates_from_chance
        )


def adversarial_line_rate(corpus: Corpus) -> ModelResult:
    """How often the opponent actually took the line worst for us.

    This is the assumption both mirror models encode, measured directly. A
    result near 0.5 means the opponent's choices carried no more adversarial
    content than a coin flip -- on this corpus, against this tool's objective.
    """
    result = ModelResult(model_name="adversarial_line")
    for decision in corpus.opponent_decisions:
        if decision.forced:
            result.not_evaluable["forced: not a choice"] = (
                result.not_evaluable.get("forced: not a choice", 0) + 1
            )
            continue
        result.evaluable += 1
        if decision.took_adversarial_line:
            result.correct += 1
    return result


def score_label_model(corpus: Corpus, model) -> ModelResult:
    """Score a label-space model against the logged opponent choices.

    Every free decision lands in ``not_evaluable``, and that is the finding,
    not a bug: scoring a choice requires a label for each candidate, and the
    corpus labels only the pairing that actually occurred.
    """
    result = ModelResult(model_name=model.name)
    labelled = {(c.usa_player, c.opponent_player): c.label for c in corpus.cells}
    for decision in corpus.opponent_decisions:
        if decision.forced:
            reason = "forced: not a choice"
        elif len(decision.choice_set) < 2:
            reason = "choice set not recoverable from the log"
        else:
            known = sum(
                1
                for candidate in decision.choice_set
                for (ours, theirs), _label in labelled.items()
                if candidate in (ours, theirs)
            )
            if known >= len(decision.choice_set):
                reason = (
                    "counterfactual unlabelled: the rival tool labels only locked "
                    "pairings, so the unchosen branch has no label"
                )
            else:
                reason = "candidate not present in the labelled cell grid"
        result.not_evaluable[reason] = result.not_evaluable.get(reason, 0) + 1
    return result


def _mirror_not_evaluable(corpus: Corpus, model_name: str) -> ModelResult:
    result = ModelResult(model_name=model_name)
    reason = (
        "no rating matrix: this corpus records labels and names, never numbers, "
        "so 'which branch minimises our total' cannot be computed"
    )
    for decision in corpus.opponent_decisions:
        if decision.forced:
            result.not_evaluable["forced: not a choice"] = (
                result.not_evaluable.get("forced: not a choice", 0) + 1
            )
            continue
        result.not_evaluable[reason] = result.not_evaluable.get(reason, 0) + 1
    return result


def run_backtest(corpus: Corpus, models) -> BacktestReport:
    """Score every supplied model against a corpus."""
    results: dict[str, ModelResult] = {}
    for model in models:
        if getattr(model, "requires_labels", False):
            results[model.name] = score_label_model(corpus, model)
        else:
            results[model.name] = _mirror_not_evaluable(corpus, model.name)

    agreement = None
    if len(models) >= 2:
        first, second = models[0], models[1]
        breakdown = AgreementBreakdown(model_a=first.name, model_b=second.name)
        # Agreement is only defined where BOTH models produced a prediction.
        # When either cannot run on a decision, that decision is undetermined
        # rather than agreeing -- counting it as agreement would manufacture
        # consensus out of two silences.
        a_evaluable = results[first.name].evaluable > 0
        b_evaluable = results[second.name].evaluable > 0
        for _decision in corpus.free_opponent_decisions:
            if a_evaluable and b_evaluable:
                breakdown.agree += 1
            else:
                breakdown.undetermined += 1
        agreement = breakdown

    forced = sum(1 for d in corpus.opponent_decisions if d.forced)
    return BacktestReport(
        corpus_id=corpus.corpus_id,
        decisions_total=len(corpus.opponent_decisions),
        decisions_forced=forced,
        decisions_free=len(corpus.opponent_decisions) - forced,
        adversarial_line=adversarial_line_rate(corpus),
        models=results,
        agreement=agreement,
        caveats=corpus.caveats,
    )
