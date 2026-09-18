from fractions import Fraction

import pytest

from research.sun_a308734_analytic_bridge.bridge_bounds import (
    ETA2,
    PAPER_THETA2,
    cofactor_band_ratio,
    complete_sieve_gap_ratio,
    diagnostic_richert_scale,
    fixed_scale_absorption_counterexample,
    is_sum_of_two_squares_by_criterion,
    pure_three_power_survivor_exponent,
    sieve_threshold_excludes_three,
    smooth_coordinate_pair_count,
    y2_exponent,
    z2_exponent,
)


def test_paper_parameter_exponents_are_exact():
    assert ETA2 == Fraction(1, 34)
    assert z2_exponent() == Fraction(5, 867)
    assert y2_exponent() == Fraction(27, 935)


def test_complete_sifting_exponent_gap_is_factor_seventeen():
    assert complete_sieve_gap_ratio() == 17


def test_actual_y2_scale_still_allows_more_than_seventeen_bands():
    assert cofactor_band_ratio() == Fraction(935, 54)
    assert Fraction(17, 1) < cofactor_band_ratio() < Fraction(18, 1)


def test_simplified_richert_diagnostic_lives_between_18_and_18_point_5():
    scale = diagnostic_richert_scale(PAPER_THETA2)
    assert scale == Fraction(4_455_995, 241_758)
    assert Fraction(18, 1) < scale < Fraction(37, 2)


def test_even_ideal_theta_diagnostic_remains_above_eighteen():
    assert diagnostic_richert_scale(Fraction(1, 1)) == Fraction(989, 54)
    assert diagnostic_richert_scale(Fraction(1, 1)) > 18


def test_three_exclusion_threshold_is_certified_without_floats():
    # With epsilon=0, alpha=5/867.  For m=3^k, m^alpha>3 iff
    # 5*k > 867.  k=173 is below and k=174 is above.
    assert not sieve_threshold_excludes_three(3**173)
    assert sieve_threshold_excludes_three(3**174)
    assert pure_three_power_survivor_exponent(3**173) is None
    assert pure_three_power_survivor_exponent(3**174) == 0


def test_positive_epsilon_shrinks_sieving_exponents():
    eps = Fraction(1, 1000)
    assert 0 < z2_exponent(eps) < z2_exponent()
    assert 0 < y2_exponent(eps) < y2_exponent()


def test_invalid_epsilon_is_rejected():
    with pytest.raises(ValueError):
        z2_exponent(Fraction(-1, 1000))
    with pytest.raises(ValueError):
        z2_exponent(Fraction(1, 34))


def test_fixed_scale_absorption_counterexample_is_exact():
    original, remainder, representable = fixed_scale_absorption_counterexample()
    assert original == 25
    assert remainder == 24
    assert representable is False
    assert not is_sum_of_two_squares_by_criterion(24)
    assert is_sum_of_two_squares_by_criterion(25)


def test_smooth_coordinate_counter_is_lacunary_helper_not_search():
    assert smooth_coordinate_pair_count(1) == 1
    assert smooth_coordinate_pair_count(10) == 7
    assert smooth_coordinate_pair_count(100) > smooth_coordinate_pair_count(10)
