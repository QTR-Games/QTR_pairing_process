"""Tests for the pluggable opponent-model layer.

Each test here guards one specific claim made in the PR. Each was confirmed by
a mutation control -- break the thing, watch this fail, restore -- rather than
by observing that it passes, which proves nothing.
"""

import pytest

from qtr_pairing_process.opponent_models import (
    DEFAULT_CUMULATIVE2_MODEL,
    DEFAULT_STRATEGIC3_MODEL,
    EVEN,
    GOOD,
    HARD_DODGE,
    SOFT_DODGE,
    HardMirror,
    LabelsUnavailable,
    OpponentModel,
    RivalLabelUtility,
    SoftenedMirror,
    UnidentifiedLabel,
    available_models,
    get_model,
)


class TestDefaultsReproducePreviousBehaviour:
    """The defaults must be the old literals, not merely close to them."""

    def test_hard_mirror_is_exactly_min(self):
        for scores in ([1.0], [3.0, 1.0, 2.0], [-5.5, -5.5], [0.0, -0.0]):
            assert HardMirror().combine(scores) == min(scores)

    def test_softened_mirror_matches_the_old_inline_expression(self):
        # The literal that used to appear at three cumulative2 sites.
        alpha = 0.80
        for scores in ([4.0, 1.0, 7.0], [2.5], [-1.0, -3.0], [0.1, 0.2, 0.3, 0.4]):
            expected = alpha * min(scores) + (1.0 - alpha) * (
                sum(scores) / max(1, len(scores))
            )
            assert SoftenedMirror(alpha).combine(scores) == expected

    def test_strategic3_default_is_the_hard_mirror(self):
        assert isinstance(DEFAULT_STRATEGIC3_MODEL, HardMirror)

    def test_cumulative2_default_alpha_is_the_preference_default(self):
        assert isinstance(DEFAULT_CUMULATIVE2_MODEL, SoftenedMirror)
        assert DEFAULT_CUMULATIVE2_MODEL.alpha == 0.80

    def test_the_bare_constructor_also_defaults_to_the_preference_value(self):
        """Guards the default argument itself, not just the module singleton.

        ``DEFAULT_CUMULATIVE2_MODEL`` passes 0.80 explicitly, so it cannot
        catch a change to ``SoftenedMirror.__init__``'s default. A mutation
        control found exactly that hole.
        """
        assert SoftenedMirror().alpha == 0.80
        assert SoftenedMirror().combine([4.0, 1.0, 7.0]) == (
            SoftenedMirror(0.80).combine([4.0, 1.0, 7.0])
        )

    def test_softened_mirror_at_alpha_one_is_the_hard_mirror(self):
        for scores in ([3.0, 1.0, 2.0], [0.0, 5.0]):
            assert SoftenedMirror(1.0).combine(scores) == HardMirror().combine(scores)


class TestModelProtocol:
    def test_models_satisfy_the_protocol(self):
        for model in (HardMirror(), SoftenedMirror(), RivalLabelUtility()):
            assert isinstance(model, OpponentModel)

    def test_registry_round_trips_the_defaults(self):
        assert "hard_mirror" in available_models()
        assert "softened_mirror" in available_models()
        assert "rival_label_utility" in available_models()
        assert get_model("hard_mirror").combine([2.0, 1.0]) == 1.0

    def test_unknown_model_names_the_alternatives(self):
        with pytest.raises(KeyError) as excinfo:
            get_model("no_such_model")
        assert "hard_mirror" in str(excinfo.value)

    def test_alpha_outside_the_unit_interval_is_rejected(self):
        for bad in (-0.1, 1.1):
            with pytest.raises(ValueError):
                SoftenedMirror(bad)


class TestRivalUtilityArithmetic:
    """GOOD=+1 / EVEN=0 / SOFT=-10, as recovered in WHITEPAPER_2026 S5.1."""

    def test_the_three_identified_weights(self):
        model = RivalLabelUtility()
        assert model.value_of(GOOD) == 1.0
        assert model.value_of(EVEN) == 0.0
        assert model.value_of(SOFT_DODGE) == -10.0

    def test_hard_dodge_is_refused_rather_than_scored_as_zero(self):
        # Zero occurrences in the corpus means zero identification. Returning
        # 0.0 here would be inventing a parameter and calling it a measurement.
        with pytest.raises(UnidentifiedLabel):
            RivalLabelUtility().value_of(HARD_DODGE)

    def test_unknown_labels_are_refused(self):
        with pytest.raises(UnidentifiedLabel):
            RivalLabelUtility().value_of("MARVELLOUS")

    def test_the_whitepaper_inversion_is_real(self):
        """S5.3's claim that this utility inverts against the win condition.

        A round is won 3-of-5. Four outright wins and one dodge must therefore
        beat five draws. Under this utility it does not. That is the reason
        this model must never become our objective, so it is asserted here
        rather than left in prose.
        """
        model = RivalLabelUtility()
        four_wins = model.score_labels([GOOD, GOOD, GOOD, GOOD, SOFT_DODGE])
        five_draws = model.score_labels([EVEN] * 5)
        assert four_wins == -6.0
        assert five_draws == 0.0
        assert four_wins < five_draws

    def test_only_weight_differences_drive_decisions(self):
        """Adding a constant to all weights changes no decision.

        Every round holds exactly five cells, so GOOD+EVEN+SOFT = 5 identically
        and adding c to each weight shifts every round total by 5c. This is why
        the printed round values matter: without them the recovery is pinned
        only up to that constant.
        """
        base = RivalLabelUtility()
        shifted = RivalLabelUtility(good=1.0 + 2, even=0.0 + 2, soft=-10.0 + 2)
        candidates = [GOOD, EVEN, SOFT_DODGE, EVEN]
        assert base.predict_index_from_labels(candidates) == (
            shifted.predict_index_from_labels(candidates)
        )
        for labels in ([GOOD] * 5, [EVEN] * 5, [GOOD, GOOD, EVEN, SOFT_DODGE, EVEN]):
            assert shifted.score_labels(labels) == base.score_labels(labels) + 5 * 2

    def test_the_rival_takes_the_branch_we_value_least(self):
        assert RivalLabelUtility().predict_index_from_labels(
            [GOOD, EVEN, SOFT_DODGE]
        ) == 2


class TestLabelModelCannotDriveTheTree:
    """The refusal is the feature. See Finding 12, r = -0.049."""

    def test_combine_refuses_rating_space_inputs(self):
        with pytest.raises(LabelsUnavailable):
            RivalLabelUtility().combine([1.0, 2.0, 3.0])

    def test_predict_index_refuses_rating_space_inputs(self):
        with pytest.raises(LabelsUnavailable):
            RivalLabelUtility().predict_index([1.0, 2.0, 3.0])

    def test_the_refusal_names_the_reason(self):
        with pytest.raises(LabelsUnavailable) as excinfo:
            RivalLabelUtility().combine([1.0, 2.0])
        message = str(excinfo.value)
        assert "-0.049" in message
        assert "ratings" in message

    def test_requires_labels_flags_which_models_the_engine_can_run(self):
        assert RivalLabelUtility().requires_labels is True
        assert HardMirror().requires_labels is False
        assert SoftenedMirror().requires_labels is False


class TestTreeGeneratorWiring:
    def test_collapse_respects_whose_choice_level_it_is(self):
        from qtr_pairing_process.tree_generator import TreeGenerator

        generator = TreeGenerator.__new__(TreeGenerator)
        scores = [5.0, 1.0, 3.0]
        model = HardMirror()
        assert generator._collapse_children(scores, True, model) == 1.0
        assert generator._collapse_children(scores, False, model) == 5.0

    def test_cumulative2_model_cache_returns_one_object_per_alpha(self):
        from qtr_pairing_process.tree_generator import TreeGenerator

        generator = TreeGenerator.__new__(TreeGenerator)
        generator._cumulative2_model_cache = {}
        first = generator._cumulative2_model_for(0.80)
        second = generator._cumulative2_model_for(0.80)
        other = generator._cumulative2_model_for(0.50)
        assert first is second
        assert other is not first
        assert other.alpha == 0.50
