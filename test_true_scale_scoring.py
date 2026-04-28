from types import SimpleNamespace
from typing import Any, cast

import pytest

from qtr_pairing_process.tree_generator import TreeGenerator


def _make_generator(rating_system: str) -> TreeGenerator:
    return TreeGenerator(treeview=SimpleNamespace(tree=object()), rating_system=rating_system)


def test_confidence_uses_native_continuous_formula_for_1_10():
    gen = _make_generator("1-10")

    assert gen.calculate_rating_confidence(1) == 15
    assert gen.calculate_rating_confidence(5) == 51
    assert gen.calculate_rating_confidence(10) == 95


def test_resistance_peaks_near_midpoint_for_active_scale():
    gen = _make_generator("1-10")

    assert gen.calculate_counter_resistance(1) == 50
    assert gen.calculate_counter_resistance(10) == 50
    assert gen.calculate_counter_resistance(5) == 85
    assert gen.calculate_counter_resistance(6) == 85


def test_opponent_counter_effectiveness_tracks_extremity():
    gen = _make_generator("1-10")

    assert gen.simulate_opponent_counter(1) == pytest.approx(0.3)
    assert gen.simulate_opponent_counter(10) == pytest.approx(0.3)
    assert gen.simulate_opponent_counter(5) == pytest.approx(0.1222222222)


def test_1_10_confidence_has_fewer_ties_than_1_3():
    gen_10 = _make_generator("1-10")
    gen_3 = _make_generator("1-3")

    normalized_samples = [i / 9.0 for i in range(10)]
    ratings_10 = [int(round(1 + (n * 9))) for n in normalized_samples]
    ratings_3 = [int(round(1 + (n * 2))) for n in normalized_samples]

    scores_10 = [gen_10.calculate_rating_confidence(r) for r in ratings_10]
    scores_3 = [gen_3.calculate_rating_confidence(r) for r in ratings_3]

    ties_10 = len(scores_10) - len(set(scores_10))
    ties_3 = len(scores_3) - len(set(scores_3))

    assert ties_10 < ties_3


def test_active_scoring_paths_do_not_require_reference_bucket():
    gen = _make_generator("1-10")

    def _fail_if_called(_rating):
        raise AssertionError("reference conversion should not be used")

    cast(Any, gen)._to_reference_rating = _fail_if_called

    assert gen.calculate_rating_confidence(8) >= 0
    assert gen.calculate_counter_resistance(8) >= 0
    assert gen.simulate_opponent_counter(8) >= 0
    assert gen.calculate_base_expected_value(8) >= 0
    assert gen.calculate_win_probability(8) >= 0
    assert gen.calculate_floor_protection(8) >= 0
    assert gen.calculate_counter_resistance_value(8) >= 0


def test_fast_path_rating_coercion_handles_expected_and_bad_inputs():
    gen = _make_generator("1-10")

    assert gen._to_int_rating(7) == 7
    assert gen._to_int_rating(7.9) == 7
    assert gen._to_int_rating("9") == 9
    assert gen._to_int_rating("N/A") == 0
    assert gen._to_int_rating(None) == 0
    assert gen._to_int_rating("invalid") == 0


def test_confidence_and_resistance_use_fast_path_without_raising():
    gen = _make_generator("1-10")

    assert gen.calculate_confidence_for_rating("8") == gen.calculate_rating_confidence(8)
    assert gen.calculate_confidence_for_rating("invalid") == gen.calculate_rating_confidence(0)
    assert gen.calculate_resistance_for_rating("8", "6", "5") == 45
    assert gen.calculate_resistance_for_rating("bad", "bad", "bad") == 0
