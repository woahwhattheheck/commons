from __future__ import annotations

import hashlib
import json
import unittest

from revenue.streaming_rendition_qa_pilot.pilot import (
    DIAGNOSTIC_PRICE_USD,
    EXTERNAL_EFFECTS,
    INTEGRATION_PRICE_USD,
    MAX_ASSETS,
    compile_artifacts,
    compile_pilot,
)
from revenue.streaming_rendition_release_gate.fixture import (
    REQUIRED_FAULT_CLASSES,
    build_fixture,
)


class StreamingRenditionQAPilotTests(unittest.TestCase):
    def test_canonical_sample_reproduces_landed_proof(self) -> None:
        packets, _ = build_fixture()
        report = compile_pilot(packets)
        self.assertEqual(report["input"]["asset_count"], 168)
        self.assertEqual(report["result"]["release_ready"], 140)
        self.assertEqual(report["result"]["hold"], 28)
        self.assertEqual(
            report["result"]["projection_sha256"],
            "e510ed89458a54d32a6cda0da425d92612ed40783fb311c2db86d3ad33f889c2",
        )
        self.assertEqual(
            report["result"]["hold_reason_counts"],
            {reason: 4 for reason in sorted(REQUIRED_FAULT_CLASSES)},
        )

    def test_artifacts_are_deterministic_and_receipt_hashes_reports(self) -> None:
        packets, _ = build_fixture()
        first = compile_artifacts(packets)
        second = compile_artifacts(packets)
        self.assertEqual(first, second)
        receipt = json.loads(first["receipt.json"])
        self.assertEqual(
            receipt["report_json_sha256"],
            hashlib.sha256(first["report.json"]).hexdigest(),
        )
        self.assertEqual(
            receipt["report_markdown_sha256"],
            hashlib.sha256(first["report.md"]).hexdigest(),
        )

    def test_fixed_scope_rejects_empty_nonlist_and_over_cap(self) -> None:
        with self.assertRaises(ValueError):
            compile_pilot([])
        with self.assertRaises(ValueError):
            compile_pilot({})
        packets, _ = build_fixture()
        over = [packets[0] for _ in range(MAX_ASSETS + 1)]
        with self.assertRaises(ValueError):
            compile_pilot(over)

    def test_offer_and_authority_ceiling_are_machine_visible(self) -> None:
        packets, _ = build_fixture()
        report = compile_pilot(packets[:1])
        self.assertEqual(report["offer"]["diagnostic_price_usd"], DIAGNOSTIC_PRICE_USD)
        self.assertEqual(
            report["offer"]["integration_follow_on_price_usd"],
            INTEGRATION_PRICE_USD,
        )
        self.assertTrue(report["offer"]["integration_follow_on_requires_paid_diagnostic"])
        self.assertFalse(report["offer"]["free_custom_adapter"])
        self.assertEqual(report["external_effects"], EXTERNAL_EFFECTS)
        self.assertTrue(all(value is False for value in EXTERNAL_EFFECTS.values()))

    def test_markdown_is_buyer_usable_without_promoting_authority(self) -> None:
        packets, _ = build_fixture()
        artifacts = compile_artifacts(packets)
        text = artifacts["report.md"].decode("utf-8")
        self.assertIn("$2,500", text)
        self.assertIn("$7,500", text)
        self.assertIn("140", text)
        self.assertIn("28", text)
        for reason in REQUIRED_FAULT_CLASSES:
            self.assertIn(reason, text)
        self.assertIn("not media release authority", text.lower())
        self.assertIn("does **not** inspect media bytes", text)

    def test_single_clean_packet_has_no_hold_inventory(self) -> None:
        packets, _ = build_fixture()
        report = compile_pilot([packets[0]])
        self.assertEqual(report["result"]["release_ready"], 1)
        self.assertEqual(report["result"]["hold"], 0)
        self.assertEqual(report["result"]["hold_reason_counts"], {})
        self.assertEqual(report["result"]["affected_assets_by_reason"], {})


if __name__ == "__main__":
    unittest.main()
