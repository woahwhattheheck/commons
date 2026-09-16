import json
from pathlib import Path

from hopf_crossing import (
    crossing_speed,
    exclude_steady_as_prize_object,
    is_simple_imaginary_crossing,
    linearization,
    truncated_channel_is_prize_domain,
)


def test_crossing_is_simple_and_transverse():
    assert is_simple_imaginary_crossing()
    assert crossing_speed() > 0
    lam, conj = linearization(47.0)
    assert abs(lam.real) < 1e-12
    assert abs(lam.imag + conj.imag) < 1e-12


def test_steady_excluded():
    assert exclude_steady_as_prize_object(True) is False
    assert exclude_steady_as_prize_object(False) is True


def test_truncation_not_prize_domain():
    assert truncated_channel_is_prize_domain() is False


def test_truth_ledger_refuses_prize_claim():
    data = json.loads((Path(__file__).parent / "truth.json").read_text())
    assert data["prize_theorem"] is False
    assert data["nonexistence_theorem"] is False
    assert data["award_or_payment"] is False
    assert data["sponsor_contact"] is False
