from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from host import right_now_human_authority as human
from host import right_now_revenue as revenue


ROOT = revenue.ROOT


def funnel(
    *,
    positive: int = 0,
    acceptances: int = 0,
    measured_at: str = "2026-09-13T17:31:00Z",
) -> dict:
    return {
        "schema_version": "commons-reply-to-revenue/v1",
        "kind": "REPLY_TO_REVENUE_FUNNEL",
        "measured_at": measured_at,
        "truth": {
            "human_positive": positive,
            "scope_acceptances": acceptances,
        },
    }


def base_control() -> dict:
    return {
        "as_of": "2026-09-13T17:00:00Z",
        "truth": {
            "verified_positive_replies": 0,
            "accepted_scopes": 0,
        },
        "blockers": [
            {
                "id": "BUYER_ACCEPTANCE",
                "current": 0,
            }
        ],
        "source_receipts": [
            {"path": "revenue/right_now/catalog.json", "sha256": "c" * 64}
        ],
    }


class RightNowHumanAuthorityTests(unittest.TestCase):
    def test_matching_assertions_are_derived_from_compiled_truth(self):
        actual = human.derive_human_truth(
            {"verified_positive_replies": 2, "accepted_scopes": 1},
            funnel=funnel(positive=2, acceptances=1),
        )
        self.assertEqual(actual["verified_positive_replies"], 2)
        self.assertEqual(actual["accepted_scopes"], 1)
        self.assertEqual(actual["as_of"], "2026-09-13T17:31:00Z")
        self.assertEqual(
            actual["authority"],
            "REPLY_TO_REVENUE_COMPILED_PUBLIC_EVIDENCE",
        )

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
                    human.HumanOutcomeAuthorityError,
                    "non-negative integer",
                ):
                    human.derive_human_truth(truth, funnel=funnel())

    def test_malformed_compiler_truth_fails_closed(self):
        cases = [
            {},
            {
                "kind": "WRONG",
                "measured_at": "2026-09-13T17:31:00Z",
                "truth": {},
            },
            {
                "kind": "REPLY_TO_REVENUE_FUNNEL",
                "measured_at": "",
                "truth": {"human_positive": 0, "scope_acceptances": 0},
            },
            {
                "kind": "REPLY_TO_REVENUE_FUNNEL",
                "measured_at": "2026-09-13T17:31:00Z",
                "truth": {"human_positive": True, "scope_acceptances": 0},
            },
        ]
        for compiled in cases:
            with self.subTest(compiled=compiled):
                with self.assertRaises(human.HumanOutcomeAuthorityError):
                    human.derive_human_truth(
                        {"verified_positive_replies": 0, "accepted_scopes": 0},
                        funnel=compiled,
                    )

    def test_stale_predecessor_as_of_field_cannot_satisfy_current_contract(self):
        predecessor = {
            "kind": "REPLY_TO_REVENUE_FUNNEL",
            "as_of": "2026-09-13T17:31:00Z",
            "truth": {"human_positive": 0, "scope_acceptances": 0},
        }
        with self.assertRaisesRegex(
            human.HumanOutcomeAuthorityError,
            "measured_at must be non-empty",
        ):
            human.derive_human_truth(
                {"verified_positive_replies": 0, "accepted_scopes": 0},
                funnel=predecessor,
            )

    def test_real_canonical_capture_drives_truth_and_exact_source_receipts(self):
        catalog = revenue.read_object(revenue.CATALOG_PATH)
        compiled = human.reply_to_revenue.build_funnel()
        actual = human.capture_human_truth(catalog["truth"])
        self.assertEqual(actual["as_of"], compiled["measured_at"])
        self.assertEqual(
            actual["verified_positive_replies"],
            compiled["truth"]["human_positive"],
        )
        self.assertEqual(
            actual["accepted_scopes"],
            compiled["truth"]["scope_acceptances"],
        )
        expected = {
            path.relative_to(ROOT).as_posix(): revenue.sha256_file(path)
            for path in human.source_paths()
        }
        self.assertEqual(
            {row["path"]: row["sha256"] for row in actual["source_receipts"]},
            expected,
        )

    def test_capture_bytes_and_digest_share_one_read_then_mutation_fails_stability(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            observations = root / "observations.json"
            receipts = root / "receipts"
            receipts.mkdir()
            receipt = receipts / "one.json"
            observations.write_bytes(b'{"generation":"A"}\r\n')
            receipt.write_bytes(b'{"receipt":"A"}\n')
            with (
                patch.object(human.reply_to_revenue, "OBSERVATIONS_PATH", observations),
                patch.object(human.reply_to_revenue, "RECEIPTS_DIR", receipts),
                patch.object(human, "ROOT", root),
            ):
                captured = human._capture_source_generation()
                self.assertEqual(captured[0]["data"], b'{"generation":"A"}\r\n')
                self.assertEqual(
                    captured[0]["sha256"],
                    human._normalized_sha256(captured[0]["data"]),
                )
                observations.write_bytes(b'{"generation":"B"}\n')
                with self.assertRaisesRegex(
                    human.HumanOutcomeAuthorityError,
                    "changed during compile",
                ):
                    human._assert_generation_stable(captured)

    def test_source_paths_cover_observations_and_canonical_receipts(self):
        paths = human.source_paths()
        self.assertTrue(paths)
        self.assertEqual(paths[0], human.reply_to_revenue.OBSERVATIONS_PATH)
        expected_receipts = sorted(human.reply_to_revenue.RECEIPTS_DIR.glob("*.json"))
        self.assertEqual(paths[1:], expected_receipts)


class RightNowHumanAuthorityCompositionTests(unittest.TestCase):
    def _compose(self, *, human_as_of: str = "2026-09-13T18:00:00Z") -> dict:
        compiled_human = {
            "as_of": human_as_of,
            "authority": "REPLY_TO_REVENUE_COMPILED_PUBLIC_EVIDENCE",
            "verified_positive_replies": 2,
            "accepted_scopes": 1,
            "source_receipts": [
                {"path": "revenue/reply_to_revenue/observations.json", "sha256": "a" * 64},
                {"path": "revenue/payment_ready/outreach_receipts/a.json", "sha256": "b" * 64},
            ],
        }
        control = base_control()
        control["truth"]["verified_positive_replies"] = 2
        control["truth"]["accepted_scopes"] = 1
        with (
            patch.object(revenue, "_ORIGINAL_BUILD_CONTROL", return_value=copy.deepcopy(control)),
            patch.object(human, "capture_human_truth", return_value=compiled_human) as capture,
            patch.object(revenue, "read_object", side_effect=AssertionError("catalog must not be re-read")),
        ):
            result = revenue.build_control()
        capture.assert_called_once_with(
            {"verified_positive_replies": 2, "accepted_scopes": 1}
        )
        return result

    def test_newer_human_truth_updates_control_and_captured_source_manifest(self):
        control = self._compose()
        self.assertEqual(control["as_of"], "2026-09-13T18:00:00Z")
        self.assertEqual(control["truth"]["verified_positive_replies"], 2)
        self.assertEqual(control["truth"]["accepted_scopes"], 1)
        self.assertEqual(control["blockers"][0]["current"], 1)
        source_rows = {
            row["path"]: row["sha256"]
            for row in control["source_receipts"]
        }
        self.assertEqual(
            source_rows["revenue/reply_to_revenue/observations.json"],
            "a" * 64,
        )
        self.assertEqual(
            source_rows["revenue/payment_ready/outreach_receipts/a.json"],
            "b" * 64,
        )

    def test_older_human_truth_cannot_move_control_clock_backwards(self):
        control = self._compose(human_as_of="2026-09-13T16:00:00Z")
        self.assertEqual(control["as_of"], "2026-09-13T17:00:00Z")

    def test_malformed_human_as_of_fails_closed(self):
        with self.assertRaisesRegex(revenue.ControlError, "canonical UTC seconds"):
            self._compose(human_as_of="not-a-time")

    def test_human_authority_error_is_translated_to_control_error(self):
        with (
            patch.object(revenue, "_ORIGINAL_BUILD_CONTROL", return_value=copy.deepcopy(base_control())),
            patch.object(
                human,
                "capture_human_truth",
                side_effect=human.HumanOutcomeAuthorityError("counter drift"),
            ),
        ):
            with self.assertRaisesRegex(revenue.ControlError, "counter drift"):
                revenue.build_control()

    def test_conflicting_existing_human_receipt_fails_before_control_mutation(self):
        control = base_control()
        control["source_receipts"].append(
            {"path": "revenue/reply_to_revenue/observations.json", "sha256": "0" * 64}
        )
        snapshot = copy.deepcopy(control)
        captured = {
            "as_of": "2026-09-13T18:00:00Z",
            "authority": "REPLY_TO_REVENUE_COMPILED_PUBLIC_EVIDENCE",
            "verified_positive_replies": 0,
            "accepted_scopes": 0,
            "source_receipts": [
                {"path": "revenue/reply_to_revenue/observations.json", "sha256": "1" * 64}
            ],
        }
        with patch.object(human, "capture_human_truth", return_value=captured):
            with self.assertRaisesRegex(revenue.ControlError, "source digest drift"):
                revenue._compose_human_outcome_authority(control)
        self.assertEqual(control, snapshot)

    def test_importlib_copy_after_canonical_import_keeps_copy_checkout_authority(self):
        spec = importlib.util.spec_from_file_location(
            "right_now_revenue_copy_after_human_canonical",
            Path(__file__).resolve().parent / "host" / "right_now_revenue.py",
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        copy_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(copy_mod)
        readback = json.loads(copy_mod.CHECKOUT_CURRENT_PATH.read_text(encoding="utf-8"))
        now = datetime(2026, 9, 14, 1, 40, 0, tzinfo=timezone.utc)
        with (
            patch.object(copy_mod, "_credential_host_readback", return_value=copy.deepcopy(readback)),
            patch.object(copy_mod, "_current_utc", return_value=now),
            patch.object(copy_mod._core, "build_checkout_authority", copy_mod.build_checkout_authority),
            patch.object(copy_mod._core, "validate_catalog", copy_mod.validate_catalog),
        ):
            compiled = copy_mod.build_control()
        self.assertIs(compiled["truth"]["active_chargeable_checkout"], True)
        self.assertEqual(
            compiled["truth"]["verified_positive_replies"],
            human.reply_to_revenue.build_funnel()["truth"]["human_positive"],
        )


if __name__ == "__main__":
    unittest.main()
