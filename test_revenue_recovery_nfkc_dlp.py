import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "revenue_recovery_nfkc", ROOT / "host/revenue_recovery.py"
)
rr = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(rr)


class RevenueRecoveryNFKCDLPTests(unittest.TestCase):
    def test_compatibility_forms_are_scanned_as_sensitive_equivalents(self):
        hostile = (
            "jane＠example．test",
            "ｊａｎｅ＠ｅｘａｍｐｌｅ．ｔｅｓｔ",
            "PASSWORD：hunter2",
            "account number：1234567890",
            "https://example.com/contact?privateEmail＝hidden",
            "https://example.com/contact#accountNumber＝hidden",
        )
        for value in hostile:
            with self.subTest(value=value):
                self.assertTrue(rr.contains_sensitive_value(value))

    def test_percent_decoded_compatibility_forms_are_scanned_after_nfkc(self):
        hostile = (
            "jane%EF%BC%A0example%EF%BC%8Etest",
            "https://example.com/contact?privateEmail%EF%BC%9Dhidden",
            "%EF%BC%B0%EF%BC%A1%EF%BC%B3%EF%BC%B3%EF%BC%B7%EF%BC%AF%EF%BC%B2%EF%BC%A4%EF%BC%9Ahunter2",
        )
        for value in hostile:
            with self.subTest(value=value):
                self.assertTrue(rr.contains_sensitive_value(value))

    def test_nfkc_safe_controls_remain_public(self):
        safe = (
            "status＝ready",
            "topic＝reproducibility",
            "https://example.com/ｐｕｂｌｉｃ?topic＝reproducibility",
            "PUBLIC_OBJECTIVE：reproducibility",
        )
        for value in safe:
            with self.subTest(value=value):
                self.assertFalse(rr.contains_sensitive_value(value))


if __name__ == "__main__":
    unittest.main()
