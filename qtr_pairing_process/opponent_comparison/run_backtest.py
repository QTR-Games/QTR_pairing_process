"""Run the opponent-model backtest and print the report.

    python -m qtr_pairing_process.opponent_comparison.run_backtest
"""

from __future__ import annotations

from qtr_pairing_process.opponent_comparison import (
    format_backtest,
    load_corpus,
    run_backtest,
)
from qtr_pairing_process.opponent_models import (
    DEFAULT_CUMULATIVE2_MODEL,
    DEFAULT_STRATEGIC3_MODEL,
    RivalLabelUtility,
)


def main() -> None:
    corpus = load_corpus("wtc2026_usa")
    report = run_backtest(
        corpus,
        [DEFAULT_STRATEGIC3_MODEL, RivalLabelUtility(), DEFAULT_CUMULATIVE2_MODEL],
    )
    print(format_backtest(report))


if __name__ == "__main__":
    main()
