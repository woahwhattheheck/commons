from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "right_now_human_authority", ROOT / "host" / "right_now_human_authority.py"
)
assert SPEC and SPEC.loader
human = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(human)


def funnel(*, positive: int = 0, acceptances: int = 0) -> dict:
    return {
        "schema_version": "commons-reply-to-revenue/v1",
        "kind": "REPLY_TO_REVENUE_FUNNEL",
        "as_of": "2026-09-13T17:31:00Z",
        "truth": {
            "human_positive": positive,
            "scope_acceptances": acceptances,
        },
    }


class RightNowHumanAuthorityTests(unittest.TestCase):
    def test_matching_assertions_are_derived_from_compiled_truth(self):
        actual = human.derive_human_truth(
            {"verified_positive_replies": 2, "accepted_scopes": 1},
            funnel=funnel(positive=2, acceptances=1),
        )
        self.assertEqual(actual["verified_positive_replies"], 2)
        self.assertEqual(actual["accepted_scopes"], 1)
        self.assertEqual(actual["authority"], "REPLY_TO_REVENUE_COMPILED_PUBLIC_EVIDENCE")

    def test_catalog_cannot_self_mint_positive_replies(self):
        with self.assertRaisesRegex(
            human.HumanOutcomeAuthorityError,
            "verified_positive_replies differs",
        ):
            human.derive_human_truth(
                {"verified_positive_replies": 999, "accepted_scopes": 0},
                funnel=funnel(),
            )

    def test_catalog_cannot_self_mint_scope_acceptances(self):
        with self.assertRaisesRegex(
            human.HumanOutcomeAuthorityError,
            "accepted_scopes differs",
        ):
            human.derive_human_truth(
                {"verified_positive_replies": 0, "accepted_scopes": 999},
                funnel=funnel(),
            )

    def test_boolean_and_negative_assertions_fail_closed(self):
        for field, value in (
            ("verified_positive_replies", True),
            ("verified_positive_replies", -1),
            ("accepted_scopes", True),
            ("accepted_scopes", -1),
        ):
            with self.subTest(field=field, value=value):
                truth = {"verified_positive_replies": 0, "accepted_scopes": 0}
                truth[field] = value
                with self.assertRaisesRegex(
                    human.HumanOutcomeAuthorityError, "non-negative integer"
                ):
                    human.derive_human_truth(truth, funnel=funnel())

    def test_malformed_compiler_truth_fails_closed(self):
        cases = [
            None,
            {},
            {"kind": "WRONG", "as_of": "2026-09-13T17:31:00Z", "truth": {}},
            {
                "kind": "REPLY_TO_REVENUE_FUNNEL",
                "as_of": "",
                "truth": {"human_positive": 0, "scope_acceptances": 0},
            },
            {
                "kind": "REPLY_TO_REVENUE_FUNNEL",
                "as_of": "2026-09-13T17:31:00Z",
                "truth": {"human_positive": True, "scope_acceptances": 0},
            },
        ]
        for compiled in cases:
            with self.subTest(compiled=compiled):
                if compiled is None:
                    continue
                with self.assertRaises(human.HumanOutcomeAuthorityError):
                    human.derive_human_truth(
                        {"verified_positive_replies": 0, "accepted_scopes": 0},
                        funnel=compiled,
                    )

    def test_current_public_compiler_confirms_zero_zero(self):
        actual = human.derive_human_truth(
            {"verified_positive_replies": 0, "accepted_scopes": 0}
        )
        self.assertEqual(actual["verified_positive_replies"], 0)
        self.assertEqual(actual["accepted_scopes"], 0)

    def test_source_paths_cover_observations_and_each_outreach_receipt(self):
        paths = human.source_paths()
        self.assertTrue(paths)
        self.assertEqual(paths[0], human.reply_to_revenue.OBSERVATIONS_PATH)
        expected_receipts = sorted(human.reply_to_revenue.RECEIPTS_DIR.glob("*.json"))
        self.assertEqual(paths[1:], expected_receipts)
        self.assertTrue(expected_receipts)


if __name__ == "__main__":
    unittest.main()
