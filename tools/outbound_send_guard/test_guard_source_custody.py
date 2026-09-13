from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from tools.outbound_send_guard import guard

RECIPIENT = "matt@scientist.com"
OFFER = "scientist-clinical-lab-sow-result-evidence-reconciler-01"


def intent(**overrides):
    value = {
        "schema_version": "outbound-send-intent/v1",
        "intent_id": "intent-scientist-1",
        "recipient": RECIPIENT,
        "offer_id": OFFER,
        "requested_at": "2026-09-13T07:20:00Z",
        "route_kind": "email",
    }
    value.update(overrides)
    return value


def evidence():
    return {
        "schema_version": "outbound-send-evidence/v1",
        "generated_at": "2026-09-13T07:19:30Z",
        "mailbox": {"complete": True, "query_id": "gmail:bidir:scientist", "messages": []},
        "slack": {"complete": True, "query_id": "slack:scientist", "events": []},
        "policy": {
            "cross_offer_cooldown_days": 30,
            "max_evidence_age_seconds": 900,
            "max_future_skew_seconds": 300,
        },
    }


def encoded(value, *, indent=None):
    return json.dumps(value, sort_keys=True, indent=indent).encode("utf-8") + b"\n"


class CoreSourceCustodyTests(unittest.TestCase):
    def test_object_api_has_no_digest_override_and_is_canonical_object_bound(self):
        it, ev = intent(), evidence()
        with self.assertRaises(TypeError):
            guard.evaluate(it, ev, intent_sha256="0" * 64)
        payload = guard.evaluate(it, ev)["payload"]
        self.assertEqual(payload["schema_version"], "outbound-send-guard-receipt/v2")
        self.assertEqual(payload["source"]["custody_mode"], "canonical_objects")
        self.assertIsNone(payload["source"]["byte_custody"])
        self.assertEqual(payload["source"]["intent_object_sha256"], guard.digest_object(it))
        self.assertEqual(payload["source"]["evidence_object_sha256"], guard.digest_object(ev))
        self.assertEqual(payload["evidence"]["intent_sha256"], guard.digest_object(it))
        self.assertEqual(payload["evidence"]["evidence_sha256"], guard.digest_object(ev))

    def test_byte_api_hashes_the_same_bytes_it_strict_parses(self):
        it, ev = intent(), evidence()
        ib, eb = encoded(it, indent=2), encoded(ev, indent=4)
        payload = guard.evaluate_bytes(ib, eb)["payload"]
        self.assertEqual(payload["source"]["custody_mode"], "exact_consumed_bytes")
        self.assertEqual(
            payload["source"]["byte_custody"],
            {
                "mode": "exact_consumed_bytes",
                "intent_sha256": guard.digest_bytes(ib),
                "evidence_sha256": guard.digest_bytes(eb),
            },
        )
        self.assertEqual(payload["source"]["intent_object_sha256"], guard.digest_object(it))
        self.assertEqual(payload["source"]["evidence_object_sha256"], guard.digest_object(ev))

    def test_whitespace_equivalent_sources_keep_object_hash_but_change_byte_hash(self):
        it, ev = intent(), evidence()
        compact = guard.evaluate_bytes(encoded(it), encoded(ev))["payload"]["source"]
        pretty = guard.evaluate_bytes(encoded(it, indent=2), encoded(ev, indent=2))["payload"]["source"]
        self.assertEqual(compact["intent_object_sha256"], pretty["intent_object_sha256"])
        self.assertEqual(compact["evidence_object_sha256"], pretty["evidence_object_sha256"])
        self.assertNotEqual(
            compact["byte_custody"]["intent_sha256"],
            pretty["byte_custody"]["intent_sha256"],
        )

    def test_internal_byte_custody_rejects_mismatch_and_json_scalar_aliases(self):
        it, ev = intent(), evidence()
        with self.assertRaisesRegex(guard.GuardError, "does not match"):
            guard._evaluate(it, ev, raw_bytes=(encoded(intent(offer_id="different")), encoded(ev)))

        false_vs_zero = deepcopy(ev)
        false_vs_zero["mailbox"]["complete"] = 0
        with self.assertRaisesRegex(guard.GuardError, "does not match"):
            guard._evaluate(it, ev, raw_bytes=(encoded(it), encoded(false_vs_zero)))

        int_vs_float = deepcopy(ev)
        int_vs_float["policy"]["cross_offer_cooldown_days"] = 30.0
        with self.assertRaisesRegex(guard.GuardError, "does not match"):
            guard._evaluate(it, ev, raw_bytes=(encoded(it), encoded(int_vs_float)))

    def test_byte_api_rejects_wrong_types_duplicate_keys_and_nonfinite_json(self):
        with self.assertRaisesRegex(guard.GuardError, "intent bytes must be bytes"):
            guard.evaluate_bytes(encoded(intent()).decode(), encoded(evidence()))

        duplicate = b'{"schema_version":"outbound-send-intent/v1","intent_id":"a","intent_id":"b"}'
        with self.assertRaises(guard.DuplicateKeyError):
            guard.evaluate_bytes(duplicate, encoded(evidence()))

        nonfinite = encoded(evidence()).replace(
            b'"cross_offer_cooldown_days": 30',
            b'"cross_offer_cooldown_days": NaN',
        )
        with self.assertRaises(guard.GuardError):
            guard.evaluate_bytes(encoded(intent()), nonfinite)

    def test_cli_receipt_binds_exact_input_file_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            intent_path = root / "intent.json"
            evidence_path = root / "evidence.json"
            receipt_path = root / "receipt.json"
            ib, eb = encoded(intent(), indent=2), encoded(evidence(), indent=3)
            intent_path.write_bytes(ib)
            evidence_path.write_bytes(eb)
            self.assertEqual(
                guard.main(
                    [
                        "--intent",
                        str(intent_path),
                        "--evidence",
                        str(evidence_path),
                        "--out",
                        str(receipt_path),
                    ]
                ),
                0,
            )
            source = json.loads(receipt_path.read_text(encoding="utf-8"))["payload"]["source"]
            self.assertEqual(source["byte_custody"]["intent_sha256"], guard.digest_bytes(ib))
            self.assertEqual(source["byte_custody"]["evidence_sha256"], guard.digest_bytes(eb))


if __name__ == "__main__":
    unittest.main()
