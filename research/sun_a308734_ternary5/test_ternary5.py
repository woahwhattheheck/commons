from __future__ import annotations

import json
from pathlib import Path

import pytest

from research.sun_a308734_ternary5.ternary5 import (
    Ternary5Witness,
    bad_prime_obstructions,
    certify_bounded_failure,
    find_witness,
    lift_witness_by_25,
    primitive_25_core,
)


EVIDENCE = Path(__file__).with_name("evidence") / "bounded_shortcut_falsifiers_v1.json"


def test_source_base_case_and_local_congruence() -> None:
    witness = find_witness(5)
    assert witness == Ternary5Witness(0, 1, 1, 0)
    assert witness.value == 5
    assert witness.restricted_square % 12 == 4
    residual = 5 - witness.restricted_square
    assert residual % 12 == 1


def test_25_adic_primitive_descent_and_lift() -> None:
    core, k = primitive_25_core(5 * 25**4)
    assert (core, k) == (5, 4)
    core_witness = Ternary5Witness(0, 1, 1, 0)
    lifted = lift_witness_by_25(core_witness, k)
    lifted.verify(5 * 25**4)
    assert lifted == Ternary5Witness(0, 625, 1, 4)


def test_b_zero_shortcut_is_exactly_falsified() -> None:
    rows = certify_bounded_failure(12233, 0)
    assert {(row["a"], row["b"]) for row in rows} == {
        (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0)
    }
    assert find_witness(12233, max_b=0) is None
    assert find_witness(12233) is not None


def test_b_at_most_one_shortcut_fails_but_conjecture_witness_exists() -> None:
    rows = certify_bounded_failure(1_595_477, 1)
    assert len(rows) == 17
    assert find_witness(1_595_477, max_b=1) is None

    witness = find_witness(1_595_477)
    assert witness == Ternary5Witness(831, 946, 2, 2)
    witness.verify(1_595_477)


def test_evidence_fixture_replays_exactly() -> None:
    fixture = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert fixture["status"] == "FINITE_EXACT_EVIDENCE_NOT_FULL_PROOF"
    for case in fixture["cases"]:
        rows = certify_bounded_failure(case["n"], case["max_b"])
        assert rows
        declared = case.get("unbounded_witness")
        if declared:
            witness = Ternary5Witness(**declared)
            witness.verify(case["n"])


def test_known_obstruction_certificate() -> None:
    # 12233 - 4 = 12229 = 7 * 1747; both bad-prime valuations are odd.
    assert bad_prime_obstructions(12229) == ((7, 1), (1747, 1))


@pytest.mark.parametrize("bad", [0, 1, 2, 6, 17, 25])
def test_non_targets_rejected(bad: int) -> None:
    with pytest.raises(ValueError):
        primitive_25_core(bad)
