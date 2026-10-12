"""Reporting opponent-model comparisons, with n and the gaps attached.

The one rule this module exists to enforce
------------------------------------------
**Disagreement is informative. Agreement is not.**

When two opponent models pick different branches, the prediction for that branch
is fragile, and saying so needs no calibration -- it is a statement about the
models, not about the world. It is useful today.

When two models pick the same branch, it is tempting to read that as "more
likely to be right". That is a probability claim, and it requires knowing
P(correct | models agree), which requires a calibration sample this project does
not have. ``power_analysis.py`` puts the requirement at hundreds of decisions
across many team-events; the corpus has twenty from one team at one event.

So this module renders divergence and refuses to render a confidence number.
``assert_no_confidence_claim`` exists so that the refusal is executable rather
than a comment someone deletes later.
"""

from __future__ import annotations

from dataclasses import dataclass

from qtr_pairing_process.opponent_comparison.backtest import BacktestReport, ModelResult

__all__ = [
    "Divergence",
    "DisagreementReport",
    "assert_no_confidence_claim",
    "format_backtest",
    "format_disagreement",
]


class ConfidenceClaimError(AssertionError):
    """Raised when agreement is about to be presented as likelihood."""


def assert_no_confidence_claim(payload: object) -> None:
    """Guard against agreement being dressed up as a probability.

    Deliberately executable. A comment saying "do not infer confidence from
    agreement" survives exactly as long as the next person who finds it
    inconvenient; this raises.
    """
    banned = (
        "confidence",
        "likelihood",
        "probability",
        "more likely",
        "agreement_score",
        "ensemble_weight",
    )
    text = repr(payload).lower()
    for token in banned:
        if token in text:
            raise ConfidenceClaimError(
                f"{token!r} appears in an opponent-model comparison payload. "
                "Agreement between opponent models is NOT calibrated evidence "
                "of correctness -- that claim needs P(correct | agree), which "
                "this corpus cannot estimate. Report divergence instead."
            )


@dataclass(frozen=True)
class Divergence:
    """One node where two opponent models chose differently."""

    node_id: str
    model_a: str
    model_b: str
    index_a: int
    index_b: int

    def describe(self) -> str:
        return (
            f"{self.node_id}: {self.model_a} -> branch {self.index_a}, "
            f"{self.model_b} -> branch {self.index_b}"
        )


@dataclass
class DisagreementReport:
    """Where two opponent models diverge over a set of decision nodes.

    Carries ``divergences`` and ``nodes_compared`` only. There is intentionally
    no "agreement rate" field: the count of agreements is not a quantity anyone
    should be acting on yet, so it is not offered.
    """

    model_a: str
    model_b: str
    nodes_compared: int = 0
    divergences: tuple[Divergence, ...] = ()

    @property
    def divergent_nodes(self) -> int:
        return len(self.divergences)

    @property
    def divergence_rate(self) -> float | None:
        if self.nodes_compared == 0:
            return None
        return self.divergent_nodes / self.nodes_compared

    def fragile_nodes(self) -> tuple[str, ...]:
        """Nodes whose predicted branch depends on which model you believe."""
        return tuple(d.node_id for d in self.divergences)


def compare_models(model_a, model_b, scored_nodes) -> DisagreementReport:
    """Compare two rating-space models over ``(node_id, child_scores)`` pairs."""
    divergences = []
    compared = 0
    for node_id, child_scores in scored_nodes:
        if len(child_scores) < 2:
            continue
        compared += 1
        index_a = model_a.predict_index(child_scores)
        index_b = model_b.predict_index(child_scores)
        if index_a != index_b:
            divergences.append(
                Divergence(
                    node_id=node_id,
                    model_a=model_a.name,
                    model_b=model_b.name,
                    index_a=index_a,
                    index_b=index_b,
                )
            )
    return DisagreementReport(
        model_a=model_a.name,
        model_b=model_b.name,
        nodes_compared=compared,
        divergences=tuple(divergences),
    )


def _format_model_result(result: ModelResult) -> list[str]:
    lines = [f"  {result.model_name}:"]
    if result.evaluable == 0:
        lines.append("    evaluable n = 0 -- no accuracy can be reported")
    else:
        low, high = result.interval
        lines.append(
            f"    {result.correct}/{result.evaluable} = {result.accuracy:.0%}  "
            f"95% Wilson [{low:.0%}, {high:.0%}]"
        )
        verdict = (
            "separates from chance"
            if result.separates_from_chance
            else "DOES NOT separate from chance (interval contains 50%)"
        )
        lines.append(f"    {verdict}")
    for reason, count in sorted(result.not_evaluable.items()):
        lines.append(f"    not evaluable x{count}: {reason}")
    return lines


def format_backtest(report: BacktestReport) -> str:
    """Render a backtest with n and every not-evaluable reason attached."""
    lines = [
        f"Opponent-model backtest -- corpus {report.corpus_id}",
        "=" * 72,
        f"opponent decisions logged: {report.decisions_total} "
        f"({report.decisions_free} free, {report.decisions_forced} forced)",
        "",
        "Adversarial-line rate -- how often the opponent actually took the",
        "branch worst for us. This is the assumption both mirror models encode.",
    ]
    lines += _format_model_result(report.adversarial_line)
    lines.append("")
    lines.append("Models:")
    for name in sorted(report.models):
        lines += _format_model_result(report.models[name])

    lines.append("")
    if report.any_model_separates:
        lines.append("RESULT: at least one model separates from chance. Read the")
        lines.append("intervals before acting; one event is not a calibration.")
    else:
        lines.append("RESULT: the corpus does not separate the models. No default")
        lines.append("is changed and no winner is declared. A null result reported")
        lines.append("with its n attached is the correct outcome here, not a")
        lines.append("fallback from a failed experiment.")

    if report.caveats:
        lines.append("")
        lines.append("Caveats:")
        lines += [f"  - {c}" for c in report.caveats]
    return "\n".join(lines)


def format_disagreement(report: DisagreementReport) -> str:
    """Render divergence only. Agreement is deliberately absent."""
    lines = [
        f"Opponent-model divergence -- {report.model_a} vs {report.model_b}",
        "=" * 72,
        f"nodes compared: {report.nodes_compared}",
        f"divergent nodes: {report.divergent_nodes}",
    ]
    rate = report.divergence_rate
    if rate is not None:
        lines.append(f"divergence rate: {rate:.0%}")
    lines.append("")
    lines.append("Divergence means the predicted branch depends on which model you")
    lines.append("believe, so treat that branch as fragile.")
    lines.append("")
    lines.append("Agreement is NOT reported. Two models agreeing is not evidence")
    lines.append("they are right: that reading needs P(correct | agree), which")
    lines.append("needs a calibration sample this project does not have.")
    if report.divergences:
        lines.append("")
        for divergence in report.divergences:
            lines.append(f"  {divergence.describe()}")
    return "\n".join(lines)
