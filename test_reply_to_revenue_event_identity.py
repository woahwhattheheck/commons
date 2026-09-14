from __future__ import annotations

import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "reply_to_revenue", ROOT / "host" / "reply_to_revenue.py"
)
assert SPEC and SPEC.loader
r2r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r2r)


def event() -> dict[str, object]:
    return {
        "event_ref": "opaque:event-identity-0001",
        "received_at": "2026-09-13T12:00:00Z",
        "prospect_key": "example-buyer",
        "payload_sha256": "a" * 64,
        "markers": ["operator note only"],
        "provider": "gmail",
        "matched_receipt_id": "receipt-example-1",
        "requested_classification": "POSITIVE_SCOPE",
    }


def observations(events: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schema_version": "commons-reply-to-revenue-observations/v1",
        "kind": "REPLY_TO_REVENUE_OBSERVATIONS",
        "measured_at": "2026-09-13T13:00:00Z",
        "monitor": {
            "connector": "fixture",
            "status": "OK",
            "mailbox_claim": "fixture",
            "sends": 0,
            "queries": 1,
            "attributed_inbound": 1,
        },
        "events": events,
    }


class EventEnvelopeIdentityTests(unittest.TestCase):
    def load(self, value: dict[str, object]) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "observations.json"
            path.write_text(r2r.canonical_text(value), encoding="utf-8")
            return r2r.load_observations(path)

    def test_exact_retry_collapses(self) -> None:
        original = event()
        loaded = self.load(observations([original, copy.deepcopy(original)]))
        self.assertEqual(len(loaded["events"]), 1)

    def test_same_ref_and_payload_with_changed_envelope_collides(self) -> None:
        mutations = {
            "received_at": "2026-09-13T12:01:00Z",
            "prospect_key": "different-buyer",
            "markers": ["different operator note"],
            "provider": "different-provider",
            "matched_receipt_id": "different-receipt",
            "requested_classification": "NEGATIVE",
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                original = event()
                duplicate = copy.deepcopy(original)
                duplicate[field] = value
                with self.assertRaisesRegex(
                    r2r.CollisionError, "different observation envelope"
                ):
                    self.load(observations([original, duplicate]))

    def test_same_ref_with_changed_payload_preserves_payload_error(self) -> None:
        original = event()
        duplicate = copy.deepcopy(original)
        duplicate["payload_sha256"] = "b" * 64
        with self.assertRaisesRegex(r2r.CollisionError, "different payload"):
            self.load(observations([original, duplicate]))


if __name__ == "__main__":
    unittest.main()
