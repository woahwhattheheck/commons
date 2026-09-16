from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CORE_PATH = ROOT / "host" / "reply_to_revenue_core.py"
SPEC = importlib.util.spec_from_file_location("_reply_to_revenue_provenance_test_core", CORE_PATH)
assert SPEC is not None and SPEC.loader is not None
core = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(core)


def _event(*, prospect="alpha", receipt="receipt-alpha", provider="GMAIL"):
    return {
        "event_ref": "opaque:gmail:aaaaaaaa11111111",
        "received_at": "2026-08-26T14:08:10Z",
        "prospect_key": prospect,
        "payload_sha256": "a" * 64,
        "markers": ["thank you for reaching out"],
        "provider": provider,
        "matched_receipt_id": receipt,
        "requested_classification": "AUTO_RESPONSE",
    }


def _observations(event):
    return {
        "schema_version": "commons-reply-to-revenue-observations/v1",
        "kind": "REPLY_TO_REVENUE_OBSERVATIONS",
        "measured_at": "2026-08-26T14:10:00Z",
        "monitor": {
            "connector": "GMAIL",
            "status": "AUTHORIZED_BOUNDED_PASS",
            "mailbox_claim": "fixture@example.invalid",
            "sends": 0,
            "queries": 1,
            "attributed_inbound": 1,
        },
        "events": [event],
    }


def _receipt(*, receipt_id="receipt-alpha", prospect="alpha"):
    return {
        "path": f"receipts/{receipt_id}.json",
        "receipt_id": receipt_id,
        "prospect_key": prospect,
        "organization": prospect.title(),
        "recipient_email": None,
        "provider_reference": "fixture:1",
        "provider_state": "COMPLETED",
        "response_state": "UNKNOWN",
        "hard_dnr": True,
        "cash_usd": 0,
        "observed_at": "2026-08-26T14:00:00Z",
    }


class ReplyToRevenueProvenanceTests(unittest.TestCase):
    def _load(self, payload):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "observations.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return core.load_observations(path)

    def test_provider_and_receipt_scalars_fail_closed(self):
        poison = (None, "", "   ", "x" * 201, 7)
        for field in ("provider", "matched_receipt_id"):
            for value in poison:
                with self.subTest(field=field, value=repr(value)):
                    event = _event()
                    event[field] = value
                    with self.assertRaises(core.ReplyRevenueError):
                        self._load(_observations(event))

    def test_unknown_receipt_id_fails_closed_after_real_load(self):
        loaded = self._load(_observations(_event(receipt="receipt-missing")))
        with self.assertRaisesRegex(core.ReplyRevenueError, "not a canonical receipt"):
            core.build_funnel(receipts=[_receipt()], observations=loaded)

    def test_cross_prospect_receipt_transplant_fails_closed(self):
        loaded = self._load(_observations(_event(prospect="beta", receipt="receipt-alpha")))
        with self.assertRaisesRegex(core.ReplyRevenueError, "receipt/prospect mismatch"):
            core.build_funnel(receipts=[_receipt()], observations=loaded)

    def test_duplicate_canonical_receipt_ids_fail_closed(self):
        loaded = self._load(_observations(_event()))
        receipts = [_receipt(), _receipt(prospect="beta")]
        with self.assertRaisesRegex(core.ReplyRevenueError, "duplicate canonical receipt_id"):
            core.build_funnel(receipts=receipts, observations=loaded)

    def test_load_receipts_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            base = {
                "receipt_id": "same-receipt",
                "target_id": "alpha",
                "organization": "Alpha",
                "recipient_email": "alpha@example.invalid",
                "provider_state": "COMPLETED",
                "dedupe": {"do_not_resend": True},
                "facts": {"collected_cash_usd": 0},
            }
            (directory / "a.json").write_text(json.dumps(base), encoding="utf-8")
            other = dict(base)
            other["target_id"] = "beta"
            (directory / "b.json").write_text(json.dumps(other), encoding="utf-8")
            with self.assertRaisesRegex(core.ReplyRevenueError, "duplicate canonical receipt_id"):
                core.load_receipts(directory)

    def test_load_receipts_rejects_explicit_invalid_ids(self):
        for value in (None, "", "   ", "x" * 201, 7):
            with self.subTest(value=repr(value)), tempfile.TemporaryDirectory() as td:
                directory = Path(td)
                payload = {
                    "receipt_id": value,
                    "target_id": "alpha",
                    "organization": "Alpha",
                    "recipient_email": "alpha@example.invalid",
                    "provider_state": "COMPLETED",
                    "dedupe": {"do_not_resend": True},
                    "facts": {"collected_cash_usd": 0},
                }
                (directory / "a.json").write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaises(core.ReplyRevenueError):
                    core.load_receipts(directory)

    def test_provenance_guard_is_captured_not_publicly_rebindable(self):
        original = core._bounded_provenance_scalar
        core._bounded_provenance_scalar = lambda value, where: "forged"
        try:
            bad = _event(provider=None)
            with self.assertRaises(core.ReplyRevenueError):
                self._load(_observations(bad))

            loaded = self._load(_observations(_event(receipt="missing")))
            with self.assertRaises(core.ReplyRevenueError):
                core.build_funnel(receipts=[_receipt()], observations=loaded)
        finally:
            core._bounded_provenance_scalar = original

    def test_valid_receipt_binding_still_builds(self):
        loaded = self._load(_observations(_event()))
        funnel = core.build_funnel(receipts=[_receipt()], observations=loaded)
        self.assertEqual(funnel["truth"]["canonical_receipts"], 1)
        self.assertEqual(funnel["truth"]["inbound_recorded"], 1)
        self.assertEqual(funnel["truth"]["resends"], 0)
        self.assertEqual(funnel["truth"]["transport_actions"], 0)
        self.assertEqual(funnel["truth"]["cash_usd"], 0)
        self.assertIn(
            "bind every inbound observation to one unique canonical receipt for the same prospect",
            funnel["limits"],
        )

    def test_committed_snapshot_matches_repaired_runtime(self):
        funnel = core.validate_funnel()
        self.assertEqual(funnel["truth"]["canonical_receipts"], 19)
        self.assertEqual(funnel["truth"]["inbound_recorded"], 4)
        self.assertEqual(funnel["truth"]["resends"], 0)
        self.assertEqual(funnel["truth"]["transport_actions"], 0)
        self.assertEqual(funnel["truth"]["cash_usd"], 0)


if __name__ == "__main__":
    unittest.main()
