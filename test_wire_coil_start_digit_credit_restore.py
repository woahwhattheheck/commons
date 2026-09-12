from pathlib import Path

TEXT = (Path(__file__).resolve().parent / "p/wire-coil-start-digit-credit-restore-20260909-01.md").read_text(encoding="utf-8")


def test_restore_receipt_credits_digit_and_coil():
    assert "DIGIT" in TEXT
    assert "COIL" in TEXT
    assert "70267cc7" in TEXT or "#11335" in TEXT
