"""Tests for the opponent-model comparison harness.

The headline assertion is ``test_the_gate_does_not_separate_the_models``: the
measured result is a null, and a null that is correctly labelled is the success
condition for this work, not a fallback from a failed experiment.
"""

import pytest

from qtr_pairing_process.opponent_comparison import (
    adversarial_line_rate,
    assert_no_confidence_claim,
    compare_models,
    format_backtest,
    format_disagreement,
    load_corpus,
    run_backtest,
    wilson_interval,
)
from qtr_pairing_process.opponent_comparison.report import ConfidenceClaimError
from qtr_pairing_process.opponent_models import (
    DEFAULT_CUMULATIVE2_MODEL,
    DEFAULT_STRATEGIC3_MODEL,
    HardMirror,
    RivalLabelUtility,
    SoftenedMirror,
)


@pytest.fixture(scope="module")
def corpus():
    return load_corpus("wtc2026_usa")


@pytest.fixture(scope="module")
def report(corpus):
    return run_backtest(
        corpus,
        [DEFAULT_STRATEGIC3_MODEL, RivalLabelUtility(), DEFAULT_CUMULATIVE2_MODEL],
    )


class TestWilsonInterval:
    """Wilson, not the normal approximation, because n is small."""

    def test_known_values(self):
        low, high = wilson_interval(9, 20)
        assert round(low, 4) == 0.2582
        assert round(high, 4) == 0.6579

    def test_against_an_independent_derivation(self):
        """Cross-check by a different algebraic route.

        The implementation uses the centre-and-spread form. Wilson is also the
        solution set of |p_hat - p| <= z*sqrt(p(1-p)/n), which squares to a
        quadratic in p. Solving that directly shares no arithmetic with the
        implementation, so agreement is evidence rather than a tautology.
        """
        from math import sqrt

        z = 1.959963985
        for k, n in ((9, 20), (3, 7), (1, 40), (17, 19)):
            a = n + z * z
            b = -(2 * k + z * z)
            c = k * k / n
            disc = b * b - 4 * a * c
            lo = (-b - sqrt(disc)) / (2 * a)
            hi = (-b + sqrt(disc)) / (2 * a)
            ours = wilson_interval(k, n)
            assert abs(lo - ours[0]) < 1e-9, (k, n)
            assert abs(hi - ours[1]) < 1e-9, (k, n)

    def test_it_differs_from_the_normal_approximation_at_small_n(self):
        """If these matched, the choice of Wilson would be decorative."""
        from math import sqrt

        k, n = 9, 20
        p = k / n
        half = 1.959963985 * sqrt(p * (1 - p) / n)
        normal = (p - half, p + half)
        low, high = wilson_interval(k, n)
        assert abs(low - normal[0]) > 0.005
        assert abs(high - normal[1]) > 0.005

    def test_the_degenerate_cases_normal_approximation_gets_wrong(self):
        """At k=0 and k=n the normal interval collapses to a point. Wilson does not."""
        low, high = wilson_interval(0, 10)
        assert low == 0.0
        assert 0.0 < high < 1.0
        low, high = wilson_interval(10, 10)
        assert high == 1.0
        assert 0.0 < low < 1.0

    def test_no_trials_means_total_ignorance_not_an_error(self):
        assert wilson_interval(0, 0) == (0.0, 1.0)

    def test_the_interval_narrows_as_n_grows(self):
        widths = []
        for n in (10, 20, 100, 1000):
            low, high = wilson_interval(round(0.45 * n), n)
            widths.append(high - low)
        assert widths == sorted(widths, reverse=True)

    def test_more_successes_shifts_the_interval_up(self):
        assert wilson_interval(5, 20)[0] < wilson_interval(15, 20)[0]


class TestTheGate:
    """The measured result, recomputed from the fixture rather than trusted."""

    def test_the_adversarial_line_rate_is_nine_of_twenty(self, corpus):
        result = adversarial_line_rate(corpus)
        assert (result.correct, result.evaluable) == (9, 20)
        assert result.accuracy == 0.45

    def test_the_forced_decision_leaves_the_denominator(self, corpus):
        result = adversarial_line_rate(corpus)
        assert result.not_evaluable == {"forced: not a choice": 1}
        assert result.evaluable == len(corpus.free_opponent_decisions)

    def test_eleven_slips(self, corpus):
        slips = [
            d for d in corpus.free_opponent_decisions if not d.took_adversarial_line
        ]
        assert len(slips) == 11

    def test_the_interval_contains_a_coin_flip(self, corpus):
        """The whole finding, in one assertion."""
        result = adversarial_line_rate(corpus)
        low, high = result.interval
        assert low < 0.5 < high
        assert not result.separates_from_chance

    def test_the_interval_excludes_the_engines_alpha(self, corpus):
        """Suggestive, and deliberately not acted on.

        alpha = 0.80 sits outside [26%, 66%]. One team at one event is not
        grounds to retune a default, so this is reported and nothing else.
        """
        result = adversarial_line_rate(corpus)
        assert result.excludes(0.80)
        assert DEFAULT_CUMULATIVE2_MODEL.alpha == 0.80

    def test_the_gate_does_not_separate_the_models(self, report):
        assert not report.any_model_separates

    def test_neither_model_is_evaluable_and_each_says_why(self, report):
        for name in ("hard_mirror", "softened_mirror", "rival_label_utility"):
            result = report.models[name]
            assert result.evaluable == 0
            assert result.not_evaluable, f"{name} must name its gaps"
            assert sum(result.not_evaluable.values()) == report.decisions_total

    def test_the_mirrors_are_blocked_by_the_missing_rating_matrix(self, report):
        reasons = " ".join(report.models["hard_mirror"].not_evaluable)
        assert "no rating matrix" in reasons

    def test_the_label_model_is_blocked_by_the_unlabelled_counterfactual(self, report):
        reasons = " ".join(report.models["rival_label_utility"].not_evaluable)
        assert "counterfactual unlabelled" in reasons


class TestReportOutput:
    def test_the_backtest_report_attaches_n(self, report):
        text = format_backtest(report)
        assert "9/20" in text
        assert "n = 0" in text

    def test_the_backtest_report_states_the_null(self, report):
        text = format_backtest(report)
        assert "does not separate" in text
        assert "No default" in text

    def test_the_backtest_report_carries_the_caveats(self, report):
        text = format_backtest(report)
        assert "HARD DODGE" in text
        assert "One team, one event" in text

    def test_not_evaluable_reasons_reach_the_output(self, report):
        text = format_backtest(report)
        assert "not evaluable" in text
        assert "no rating matrix" in text

    def test_the_report_separates_sample_size_from_corpus_design(self, report):
        """The gate's reason must travel with its number.

        Without this, a reader records '45%, inconclusive, collect more data'
        and plans the wrong collection. The posture is sample-size limited;
        the models are not limited by sample size at all.
        """
        text = format_backtest(report)
        assert "would and would not fix" in text
        assert "NOT limited by sample size" in text
        assert "leave them at zero forever" in text


class TestDisagreementNotConfidence:
    """Section 3 of the brief, made executable."""

    def test_divergence_is_detected(self):
        a, b = HardMirror(), SoftenedMirror(0.80)
        nodes = [("n1", [3.0, 1.0, 2.0]), ("n2", [5.0, 9.0])]
        result = compare_models(a, b, nodes)
        # Both mirrors argmin, so these must agree; divergence needs models
        # that genuinely rank differently.
        assert result.nodes_compared == 2
        assert result.divergent_nodes == 0

    def test_models_that_rank_differently_are_reported_as_divergent(self):
        class Contrarian:
            name = "contrarian"
            requires_labels = False

            def combine(self, scores):
                return max(scores)

            def predict_index(self, scores):
                return max(range(len(scores)), key=lambda i: scores[i])

        result = compare_models(HardMirror(), Contrarian(), [("n1", [3.0, 1.0, 2.0])])
        assert result.divergent_nodes == 1
        assert result.fragile_nodes() == ("n1",)
        assert result.divergence_rate == 1.0

    def test_single_child_nodes_are_not_decisions(self):
        result = compare_models(HardMirror(), SoftenedMirror(), [("n1", [4.0])])
        assert result.nodes_compared == 0
        assert result.divergence_rate is None

    def test_the_disagreement_report_has_no_agreement_rate(self):
        result = compare_models(HardMirror(), SoftenedMirror(), [("n1", [2.0, 1.0])])
        assert not hasattr(result, "agreement_rate")
        assert not hasattr(result, "confidence")

    def test_the_rendered_report_refuses_the_confidence_reading(self):
        result = compare_models(HardMirror(), SoftenedMirror(), [("n1", [2.0, 1.0])])
        text = format_disagreement(result)
        assert "Agreement is NOT reported" in text
        assert "fragile" in text

    def test_the_guard_rejects_a_confidence_claim(self):
        with pytest.raises(ConfidenceClaimError):
            assert_no_confidence_claim({"agreement_score": 0.9})
        with pytest.raises(ConfidenceClaimError):
            assert_no_confidence_claim("models agree so this is more likely")

    def test_the_guard_passes_a_divergence_claim(self):
        assert_no_confidence_claim({"divergent_nodes": 3, "nodes_compared": 10})

    def test_the_guard_names_the_missing_quantity(self):
        with pytest.raises(ConfidenceClaimError) as excinfo:
            assert_no_confidence_claim({"confidence": 0.9})
        assert "P(correct | agree)" in str(excinfo.value)


class TestPowerAnalysisStaysReproducible:
    def test_the_observed_count_is_the_corrected_twenty(self, corpus):
        from qtr_pairing_process.opponent_comparison import power_analysis

        assert power_analysis.OPP_DECISIONS_NOW == 20
        assert power_analysis.OPP_DECISIONS_PER_ROUND == 4
        assert power_analysis.OPP_DECISIONS_NOW == len(corpus.free_opponent_decisions)

    def test_its_wilson_matches_the_harness_wilson(self):
        from qtr_pairing_process.opponent_comparison import power_analysis

        for k, n in ((9, 20), (0, 10), (10, 10), (3, 7)):
            theirs = power_analysis.wilson(k, n)
            ours = wilson_interval(k, n)
            assert round(theirs[0], 9) == round(ours[0], 9)
            assert round(theirs[1], 9) == round(ours[1], 9)

    def test_importing_it_prints_nothing(self, capsys):
        import importlib

        from qtr_pairing_process.opponent_comparison import power_analysis

        importlib.reload(power_analysis)
        assert capsys.readouterr().out == ""

    def test_the_ensemble_claim_needs_far_more_than_we_have(self):
        """Q3 is the expensive question, and this pins how expensive."""
        from qtr_pairing_process.opponent_comparison import power_analysis

        per_group = power_analysis.n_two_proportion(0.80, 0.60)
        assert per_group > 20 * 4
