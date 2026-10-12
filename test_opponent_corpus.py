"""Tests for the WTC 2026 USA corpus and its loader.

The fixtures in this corpus were transcribed by eye from five screenshots of a
Pear Master session log. A hand transcription needs an independent check, and
these are it: the arithmetic below is over-determined, so a slip of the eye in
any single cell shows up as a non-zero residual somewhere.
"""

import pytest

from qtr_pairing_process.opponent_comparison import available_corpora, load_corpus
from qtr_pairing_process.opponent_models import (
    EVEN,
    GOOD,
    HARD_DODGE,
    SOFT_DODGE,
    RivalLabelUtility,
    UnidentifiedLabel,
)


@pytest.fixture(scope="module")
def corpus():
    return load_corpus("wtc2026_usa")


class TestCorpusShape:
    def test_the_corpus_is_discoverable_without_naming_it(self):
        assert "wtc2026_usa" in available_corpora()

    def test_provenance(self, corpus):
        assert corpus.event == "WTC 2026"
        assert corpus.team == "USA Death Valley"
        assert corpus.rival_tool == "Pear Master"

    def test_five_rounds_of_five_cells(self, corpus):
        assert len(corpus.cells) == 25
        assert sorted({c.round for c in corpus.cells}) == [1, 2, 3, 4, 5]
        for round_no in range(1, 6):
            assert len([c for c in corpus.cells if c.round == round_no]) == 5

    def test_twenty_free_opponent_decisions_plus_one_forced(self, corpus):
        """The headline count, measured rather than asserted.

        The supplied CSV's 10 'nominated_selected_by_them' cells capture only
        the nomination half of each round. The logs record four opponent
        decision points per round.
        """
        assert len(corpus.opponent_decisions) == 21
        assert len(corpus.free_opponent_decisions) == 20
        forced = [d for d in corpus.opponent_decisions if d.forced]
        assert len(forced) == 1
        assert forced[0].round == 4

    def test_four_free_opponent_decisions_per_round(self, corpus):
        for round_no in range(1, 6):
            free = [d for d in corpus.free_opponent_decisions if d.round == round_no]
            assert len(free) == 4, f"round {round_no}"

    def test_every_free_decision_carries_a_verdict(self, corpus):
        for decision in corpus.free_opponent_decisions:
            assert decision.verdict in {"slipped", "strongest_line"}


class TestRoundValueReconciliation:
    """Each round's printed value must fall out of its label counts.

    This is the check that makes the utility recovery non-circular: the value
    is printed by the rival tool, not derived by us, so matching it is a
    genuine prediction and not a restatement.
    """

    def test_printed_values_match_the_logs(self, corpus):
        printed = {rv.round: rv.printed_value for rv in corpus.round_values}
        assert printed == {1: -8, 2: 1, 3: -10, 4: 2, 5: -18}

    def test_every_round_reconciles_at_zero_residual(self, corpus):
        model = RivalLabelUtility()
        for rv in corpus.round_values:
            computed = (
                model.value_of(GOOD) * rv.good
                + model.value_of(EVEN) * rv.even
                + model.value_of(SOFT_DODGE) * rv.soft_dodge
            )
            assert computed == rv.printed_value, f"round {rv.round}"

    def test_label_counts_sum_to_five_every_round(self, corpus):
        for rv in corpus.round_values:
            assert sum(rv.label_counts.values()) == 5, f"round {rv.round}"

    def test_round_value_counts_match_the_cell_labels(self, corpus):
        """The two fixtures are independent transcriptions; they must agree."""
        for rv in corpus.round_values:
            cells = [c for c in corpus.cells if c.round == rv.round]
            assert sum(1 for c in cells if c.label == GOOD) == rv.good
            assert sum(1 for c in cells if c.label == EVEN) == rv.even
            assert sum(1 for c in cells if c.label == SOFT_DODGE) == rv.soft_dodge

    def test_rounds_two_and_four_alone_identify_good_and_even(self, corpus):
        """G + 4E = 1 and 2G + 3E = 2 give G = 1, E = 0 with no third round."""
        by_round = {rv.round: rv for rv in corpus.round_values}
        r2, r4 = by_round[2], by_round[4]
        assert (r2.good, r2.even, r2.soft_dodge) == (1, 4, 0)
        assert (r4.good, r4.even, r4.soft_dodge) == (2, 3, 0)
        determinant = r2.good * r4.even - r2.even * r4.good
        assert determinant != 0
        good = (r2.printed_value * r4.even - r4.printed_value * r2.even) / determinant
        even = (r2.good * r4.printed_value - r4.good * r2.printed_value) / determinant
        assert (good, even) == (1.0, 0.0)

    def test_rounds_one_and_five_are_out_of_sample_confirmations(self, corpus):
        """Rounds 2 and 4 fix G and E; round 3 fixes S. 1 and 5 are untouched."""
        by_round = {rv.round: rv for rv in corpus.round_values}
        r3 = by_round[3]
        soft = (r3.printed_value - 1.0 * r3.good - 0.0 * r3.even) / r3.soft_dodge
        assert soft == -10.0
        for round_no, expected in ((1, -8), (5, -18)):
            rv = by_round[round_no]
            predicted = 1.0 * rv.good + 0.0 * rv.even + soft * rv.soft_dodge
            assert predicted == expected, f"round {round_no}"


class TestHardDodgeIsUnidentified:
    def test_hard_dodge_never_occurs(self, corpus):
        """Zero occurrences is why its weight has no identified value."""
        assert all(rv.hard_dodge == 0 for rv in corpus.round_values)
        assert not any(c.label == HARD_DODGE for c in corpus.cells)

    def test_any_hard_dodge_weight_reconciles_the_corpus(self, corpus):
        """The formal statement of 'unidentified': the data cannot tell.

        If the corpus contained even one HARD DODGE this loop would fail for
        every weight but the true one -- which is precisely the point.
        """
        for candidate_weight in (-1000.0, -10.0, 0.0, 7.5):
            for rv in corpus.round_values:
                total = (
                    1.0 * rv.good
                    + 0.0 * rv.even
                    + -10.0 * rv.soft_dodge
                    + candidate_weight * rv.hard_dodge
                )
                assert total == rv.printed_value

    def test_scoring_a_hard_dodge_raises(self):
        with pytest.raises(UnidentifiedLabel):
            RivalLabelUtility().score_labels([GOOD, HARD_DODGE])


class TestGuaranteeConsistency:
    def test_each_round_ends_at_its_final_outcome(self, corpus):
        """The last guarantee vector must equal the round's label counts.

        An independent path to the same numbers: guarantees accumulate step by
        step through the protocol, while round_values records only the end
        state. They were transcribed separately.
        """
        by_round = {rv.round: rv for rv in corpus.round_values}
        for round_no in range(1, 6):
            steps = sorted(
                (g for g in corpus.guarantees if g.round == round_no),
                key=lambda g: g.step,
            )
            assert steps, f"round {round_no} has no guarantee steps"
            rv = by_round[round_no]
            assert steps[-1].after == (
                rv.good,
                rv.even,
                rv.soft_dodge,
                rv.hard_dodge,
            ), f"round {round_no}"

    def test_guarantees_never_decrease_in_total(self, corpus):
        """Locked cells stay locked, so the vector total is non-decreasing."""
        for round_no in range(1, 6):
            steps = sorted(
                (g for g in corpus.guarantees if g.round == round_no),
                key=lambda g: g.step,
            )
            for step in steps:
                assert sum(step.after) >= sum(step.before), f"r{round_no} s{step.step}"

    def test_each_step_chains_to_the_next(self, corpus):
        for round_no in range(1, 6):
            steps = sorted(
                (g for g in corpus.guarantees if g.round == round_no),
                key=lambda g: g.step,
            )
            for previous, following in zip(steps, steps[1:], strict=False):
                assert previous.after == following.before, (
                    f"round {round_no} breaks between steps "
                    f"{previous.step} and {following.step}"
                )


class TestOurOwnDecisions:
    def test_nineteen_of_twenty_usa_decisions_were_engine_optimal(self, corpus):
        optimal = sum(rv.our_decisions_optimal for rv in corpus.round_values)
        total = sum(rv.our_decisions_total for rv in corpus.round_values)
        assert (optimal, total) == (19, 20)

    def test_the_single_suboptimal_decision_is_in_round_five(self, corpus):
        off = [
            rv.round
            for rv in corpus.round_values
            if rv.our_decisions_optimal != rv.our_decisions_total
        ]
        assert off == [5]
