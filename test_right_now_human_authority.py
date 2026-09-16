from __future__ import annotations

import importlib.util
import inspect
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from host import right_now_human_authority as human
from host import right_now_revenue as revenue


ROOT = Path(__file__).resolve().parent
FRESH_NOW = datetime(2026, 9, 14, 1, 40, 0, tzinfo=timezone.utc)


def funnel(*, positive: int = 0, acceptances: int = 0) -> dict:
    return {
        "schema_version": "commons-reply-to-revenue/v1",
        "kind": "REPLY_TO_REVENUE_FUNNEL",
        "measured_at": "2026-09-13T17:31:00Z",
        "truth": {
            "human_positive": positive,
            "scope_acceptances": acceptances,
        },
    }


def derive(
    catalog_truth: dict,
    *,
    compiled: dict | None = None,
    sources: list[dict[str, str]] | None = None,
) -> dict:
    compiled = funnel() if compiled is None else compiled
    sources = [] if sources is None else sources
    with mock.patch.object(
        human,
        "_compile_current_funnel",
        return_value=(compiled, sources),
    ):
        return human.derive_human_truth(catalog_truth)


def base_control() -> dict:
    return {
        "schema_version": "commons-right-now-control/v3",
        "kind": "RIGHT_NOW_REVENUE_CONTROL",
        "as_of": "2026-09-13T17:30:00Z",
        "truth": {
            "collected_cash_usd": 0,
            "verified_positive_replies": 999,
            "accepted_scopes": 999,
        },
        "blockers": [
            {"id": "BUYER_ACCEPTANCE", "current": 999},
            {"id": "OTHER", "current": 0},
        ],
        "source_receipts": [
            {
                "path": "revenue/right_now/catalog.json",
                "sha256": "0" * 64,
            }
        ],
    }


class RightNowHumanAuthorityTests(unittest.TestCase):
    def test_public_authority_has_no_caller_funnel_or_clock_surface(self):
        self.assertEqual(
            list(inspect.signature(human.derive_human_truth).parameters),
            ["catalog_truth"],
        )

    def test_matching_assertions_are_derived_from_compiled_truth(self):
        actual = derive(
            {"verified_positive_replies": 2, "accepted_scopes": 1},
            compiled=funnel(positive=2, acceptances=1),
        )
        self.assertEqual(actual["verified_positive_replies"], 2)
        self.assertEqual(actual["accepted_scopes"], 1)
        self.assertEqual(actual["measured_at"], "2026-09-13T17:31:00Z")
        self.assertEqual(actual["sources"], [])

    def test_catalog_cannot_self_mint_positive_replies(self):
        with self.assertRaisesRegex(
            human.HumanOutcomeAuthorityError,
            "verified_positive_replies differs",
        ):
            derive({"verified_positive_replies": 999, "accepted_scopes": 0})

    def test_catalog_cannot_self_mint_scope_acceptances(self):
        with self.assertRaisesRegex(
            human.HumanOutcomeAuthorityError,
            "accepted_scopes differs",
        ):
            derive({"verified_positive_replies": 0, "accepted_scopes": 999})

    def test_boolean_negative_and_mapping_subclass_assertions_fail_closed(self):
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
                    derive(truth)

        class MutableTruth(dict):
            pass

        with self.assertRaisesRegex(
            human.HumanOutcomeAuthorityError, "exact object"
        ):
            human.derive_human_truth(
                MutableTruth(
                    verified_positive_replies=0,
                    accepted_scopes=0,
                )
            )

    def test_compiler_contract_requires_measured_at_not_stale_as_of(self):
        stale = funnel()
        stale["as_of"] = stale.pop("measured_at")
        with self.assertRaisesRegex(
            human.HumanOutcomeAuthorityError,
            "measured_at must be canonical UTC seconds",
        ):
            derive(
                {"verified_positive_replies": 0, "accepted_scopes": 0},
                compiled=stale,
            )

    def test_malformed_compiler_truth_fails_closed(self):
        cases = [
            {},
            {
                "schema_version": "wrong",
                "kind": "REPLY_TO_REVENUE_FUNNEL",
                "measured_at": "2026-09-13T17:31:00Z",
                "truth": {"human_positive": 0, "scope_acceptances": 0},
            },
            {
                "schema_version": "commons-reply-to-revenue/v1",
                "kind": "WRONG",
                "measured_at": "2026-09-13T17:31:00Z",
                "truth": {},
            },
            {
                "schema_version": "commons-reply-to-revenue/v1",
                "kind": "REPLY_TO_REVENUE_FUNNEL",
                "measured_at": "",
                "truth": {"human_positive": 0, "scope_acceptances": 0},
            },
            {
                "schema_version": "commons-reply-to-revenue/v1",
                "kind": "REPLY_TO_REVENUE_FUNNEL",
                "measured_at": "2026-09-13T17:31:00Z",
                "truth": {"human_positive": True, "scope_acceptances": 0},
            },
        ]
        for compiled in cases:
            with self.subTest(compiled=compiled):
                with self.assertRaises(human.HumanOutcomeAuthorityError):
                    derive(
                        {"verified_positive_replies": 0, "accepted_scopes": 0},
                        compiled=compiled,
                    )

    def test_source_generation_change_while_loading_fails_closed(self):
        before = [{"path": "a.json", "sha256": "1" * 64}]
        after = [{"path": "a.json", "sha256": "2" * 64}]
        with mock.patch.object(
            human, "_source_snapshot", side_effect=[before, after]
        ), mock.patch.object(
            human.reply_to_revenue, "load_receipts", return_value=[]
        ), mock.patch.object(
            human.reply_to_revenue,
            "load_observations",
            return_value={"events": []},
        ), self.assertRaisesRegex(
            human.HumanOutcomeAuthorityError, "changed while loading"
        ):
            human._compile_current_funnel()

    def test_current_public_compiler_and_real_sources_match_catalog(self):
        catalog = revenue.read_object(revenue.CATALOG_PATH)
        actual = human.derive_human_truth(catalog["truth"])
        self.assertEqual(
            actual["verified_positive_replies"],
            catalog["truth"]["verified_positive_replies"],
        )
        self.assertEqual(
            actual["accepted_scopes"],
            catalog["truth"]["accepted_scopes"],
        )
        expected_paths = [
            path.relative_to(human.ROOT).as_posix()
            for path in human.source_paths()
        ]
        self.assertEqual(
            [entry["path"] for entry in actual["sources"]],
            expected_paths,
        )
        self.assertTrue(actual["sources"])
        for entry in actual["sources"]:
            self.assertRegex(entry["sha256"], r"^[0-9a-f]{64}$")

    def test_wrapper_binds_truth_chronology_blocker_and_source_receipts(self):
        derived = {
            "measured_at": "2026-09-13T17:31:00Z",
            "authority": "REPLY_TO_REVENUE_COMPILED_PUBLIC_EVIDENCE",
            "verified_positive_replies": 2,
            "accepted_scopes": 1,
            "sources": [
                {
                    "path": "revenue/reply_to_revenue/observations.json",
                    "sha256": "1" * 64,
                },
                {
                    "path": "revenue/payment_ready/outreach_receipts/a.json",
                    "sha256": "2" * 64,
                },
            ],
        }
        with mock.patch.object(
            revenue, "_ORIGINAL_BUILD_CONTROL", return_value=base_control()
        ), mock.patch.object(
            revenue.right_now_human_authority,
            "derive_human_truth",
            return_value=derived,
        ):
            actual = revenue.build_control()
        self.assertEqual(actual["as_of"], derived["measured_at"])
        self.assertEqual(actual["truth"]["verified_positive_replies"], 2)
        self.assertEqual(actual["truth"]["accepted_scopes"], 1)
        buyer = next(
            row for row in actual["blockers"] if row["id"] == "BUYER_ACCEPTANCE"
        )
        self.assertEqual(buyer["current"], 1)
        self.assertNotIn("sources", actual)
        self.assertEqual(actual["source_receipts"][-2:], derived["sources"])

    def test_wrapper_rejects_conflicting_source_identity(self):
        control = base_control()
        control["source_receipts"] = [
            {
                "path": "revenue/reply_to_revenue/observations.json",
                "sha256": "a" * 64,
            }
        ]
        derived = {
            "measured_at": "2026-09-13T17:31:00Z",
            "authority": "REPLY_TO_REVENUE_COMPILED_PUBLIC_EVIDENCE",
            "verified_positive_replies": 0,
            "accepted_scopes": 0,
            "sources": [
                {
                    "path": "revenue/reply_to_revenue/observations.json",
                    "sha256": "b" * 64,
                }
            ],
        }
        with mock.patch.object(
            revenue, "_ORIGINAL_BUILD_CONTROL", return_value=control
        ), mock.patch.object(
            revenue.right_now_human_authority,
            "derive_human_truth",
            return_value=derived,
        ):
            with self.assertRaisesRegex(revenue.ControlError, "source digest conflict"):
                revenue.build_control()

    def test_real_control_uses_own_hooks_after_sibling_wrapper_load(self):
        previous = (
            revenue._core.build_checkout_authority,
            revenue._core.validate_catalog,
            revenue._core.build_control,
        )
        spec = importlib.util.spec_from_file_location(
            "right_now_revenue_human_authority_sibling",
            ROOT / "host" / "right_now_revenue.py",
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        sibling = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(sibling)
            readback = json.loads(
                revenue.CHECKOUT_CURRENT_PATH.read_text(encoding="utf-8")
            )
            with mock.patch.object(
                revenue, "_credential_host_readback", return_value=readback
            ), mock.patch.object(
                revenue, "_current_utc", return_value=FRESH_NOW
            ):
                actual = revenue.build_control()
        finally:
            (
                revenue._core.build_checkout_authority,
                revenue._core.validate_catalog,
                revenue._core.build_control,
            ) = previous

        self.assertIs(actual["truth"]["active_chargeable_checkout"], True)
        self.assertNotIn("sources", actual)
        bound = {row["path"]: row["sha256"] for row in actual["source_receipts"]}
        expected_paths = {
            path.relative_to(human.ROOT).as_posix()
            for path in human.source_paths()
        }
        self.assertTrue(expected_paths.issubset(bound))
        self.assertGreaterEqual(
            actual["as_of"],
            human.derive_human_truth(
                revenue.read_object(revenue.CATALOG_PATH)["truth"]
            )["measured_at"],
        )


if __name__ == "__main__":
    unittest.main()
