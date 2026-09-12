# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("seed_identifiability", HERE / "seed_identifiability.py")
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


class FakeEngine:
    @staticmethod
    def _new_farm(board_size, starting_money):
        half = board_size // 2
        return {"tiles": [[None if x < half and y < half else "LOCKED"
                            for x in range(board_size)] for y in range(board_size)]}


def test_initial_empty_count_and_order():
    pos = MOD.initial_empty_positions(FakeEngine())
    assert len(pos) == 25
    assert pos[0] == (0, 0)
    assert pos[-1] == (4, 4)


def test_default_information_is_small():
    h = 50 * MOD.bernoulli_entropy_bits(0.005)
    assert math.isclose(h, 2.270734616689705, rel_tol=0, abs_tol=1e-12)
    assert math.isclose((1 - 0.005) ** 50, 0.7783125570686419,
                        rel_tol=0, abs_tol=1e-15)


def test_common_zero_pattern_is_highly_ambiguous_in_12bit_domain():
    bits = MOD.weed_bits_for_seed(1, day=0, empty_counts=(25, 25), weed_chance=0.005)
    assert sum(bits) == 0
    matches = MOD.candidate_seeds(bits, seed_start=0, seed_stop=4096, day=0,
                                  empty_counts=(25, 25), weed_chance=0.005)
    assert len(matches) == 3190
    assert 1 in matches
    assert MOD.bounded_verdict(len(matches)) == "AMBIGUOUS_IN_BOUNDED_DOMAIN"


def test_one_weed_pattern_still_collides_in_12bit_domain():
    bits = MOD.weed_bits_for_seed(0, day=0, empty_counts=(25, 25), weed_chance=0.005)
    assert sum(bits) == 1
    matches = MOD.candidate_seeds(bits, seed_start=0, seed_stop=4096, day=0,
                                  empty_counts=(25, 25), weed_chance=0.005)
    assert len(matches) == 21
    assert 0 in matches


def test_two_weed_pattern_can_still_collide():
    bits = MOD.weed_bits_for_seed(13, day=0, empty_counts=(25, 25), weed_chance=0.005)
    assert sum(bits) == 2
    matches = MOD.candidate_seeds(bits, seed_start=0, seed_stop=4096, day=0,
                                  empty_counts=(25, 25), weed_chance=0.005)
    assert len(matches) == 2
    assert 13 in matches


def test_changed_empty_count_changes_observation_contract():
    bits = MOD.weed_bits_for_seed(1, day=0, empty_counts=(24, 25), weed_chance=0.005)
    assert len(bits) == 49
    try:
        MOD.candidate_seeds(bits, seed_start=0, seed_stop=10, day=0,
                            empty_counts=(25, 25), weed_chance=0.005)
    except ValueError as exc:
        assert "expected 50" in str(exc)
    else:
        raise AssertionError("empty-mask drift did not fail closed")


def test_bad_observation_length_refuses():
    try:
        MOD.candidate_seeds((False,), seed_start=0, seed_stop=10, day=0,
                            empty_counts=(25, 25), weed_chance=0.005)
    except ValueError as exc:
        assert "expected 50" in str(exc)
    else:
        raise AssertionError("length mismatch did not fail closed")


def test_bounded_unique_never_claims_global():
    assert MOD.bounded_verdict(1) == "BOUNDED_UNIQUE_NOT_GLOBAL"


def main():
    tests = [value for name, value in sorted(globals().items())
             if name.startswith("test_") and callable(value)]
    for test in tests:
        test()
    print(f"PASS {len(tests)}/{len(tests)} seed-identifiability tests")


if __name__ == "__main__":
    main()
