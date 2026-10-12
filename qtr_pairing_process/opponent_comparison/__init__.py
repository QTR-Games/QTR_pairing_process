"""Comparing opponent models against logged pairing decisions.

This package is kept deliberately, as production code rather than a probe, for
two reasons the owner asked for explicitly: so the comparison is auditable
later, and so adding a new event or team is a matter of dropping a CSV
directory into ``corpora/`` rather than rewriting an analysis.

Start at :func:`qtr_pairing_process.opponent_comparison.corpus.load_corpus` and
:func:`qtr_pairing_process.opponent_comparison.backtest.run_backtest`.

The headline result on the only corpus currently available is a **null**, and it
is reported as one: see ``corpora/wtc2026_usa/README.md``.
"""

from qtr_pairing_process.opponent_comparison.backtest import (
    BacktestReport,
    ModelResult,
    adversarial_line_rate,
    run_backtest,
)
from qtr_pairing_process.opponent_comparison.corpus import (
    Corpus,
    available_corpora,
    load_corpus,
)
from qtr_pairing_process.opponent_comparison.report import (
    DisagreementReport,
    assert_no_confidence_claim,
    compare_models,
    format_backtest,
    format_disagreement,
)
from qtr_pairing_process.opponent_comparison.stats import wilson_interval

__all__ = [
    "BacktestReport",
    "Corpus",
    "DisagreementReport",
    "ModelResult",
    "adversarial_line_rate",
    "assert_no_confidence_claim",
    "available_corpora",
    "compare_models",
    "format_backtest",
    "format_disagreement",
    "load_corpus",
    "run_backtest",
    "wilson_interval",
]
