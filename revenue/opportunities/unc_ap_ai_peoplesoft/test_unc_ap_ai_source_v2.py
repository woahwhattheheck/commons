from datetime import datetime, timezone
import hashlib
import unittest

import unc_ap_ai as m

DOC = b"synthetic retained buyer packet generation"
DOC_SHA = hashlib.sha256(DOC).hexdigest()


def at(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


def bound_ledger():
    docs = [{"name": "buyer-packet.pdf", "sha256": DOC_SHA}]
    generation = m.receipt({"schema": m.SOURCE_MANIFEST_SCHEMA, "documents": docs})
    return {
        "schema": m.SOURCE_SCHEMA,
        "buyer": m.BUYER,
        "solicitation_id": m.SOLICITATION_ID,
        "first_party_url": m.FIRST_PARTY_URL,
        "status": "OPEN",
        "observed_at": "2026-09-17T21:15:00-04:00",
        "offer_due_at": "2026-09-25T12:00:00-04:00",
        "source_generation": generation,
        "required_documents": docs,
    }


class SourceTrustRootTests(unittest.TestCase):
    def test_checked_in_legacy_ledger_stays_unbound(self):
        loaded = m.load_source_ledger()
        self.assertIsNone(loaded["source_generation"])
        self.assertIsNone(loaded["required_documents"])
        out = m._compile_source_at(loaded, {}, as_of=at("2026-09-18T03:00:00Z"))
        self.assertEqual(out["state"], "HOLD_SOURCE_BYTES")

    def test_actual_bytes_are_hashed(self):
        ledger = bound_ledger()
        good = m._compile_source_at(
            ledger, {"buyer-packet.pdf": DOC}, as_of=at("2026-09-18T03:00:00Z")
        )
        self.assertEqual(good["state"], "SOURCE_BOUND")
        wrong = m._compile_source_at(
            ledger, {"buyer-packet.pdf": b"different"}, as_of=at("2026-09-18T03:00:00Z")
        )
        self.assertEqual(wrong["state"], "HOLD_SOURCE_BYTES")

    def test_manifest_generation_must_bind_document_list(self):
        ledger = bound_ledger()
        ledger["source_generation"] = "a" * 64
        with self.assertRaises(m.ContractError):
            m._compile_source_at(
                ledger, {"buyer-packet.pdf": DOC}, as_of=at("2026-09-18T03:00:00Z")
            )

    def test_deadline_uses_evaluation_time(self):
        ledger = bound_ledger()
        before = m._compile_source_at(
            ledger, {"buyer-packet.pdf": DOC}, as_of=at("2026-09-25T15:59:59Z")
        )
        closed = m._compile_source_at(
            ledger, {"buyer-packet.pdf": DOC}, as_of=at("2026-09-25T16:00:00Z")
        )
        self.assertEqual(before["state"], "SOURCE_BOUND")
        self.assertEqual(closed["state"], "HOLD_DEADLINE")

    def test_strict_json_rejects_ambiguous_forms(self):
        for raw in ('{"a":1,"a":2}', '{"x":NaN}', '{"x":1.5}'):
            with self.subTest(raw=raw), self.assertRaises(m.ContractError):
                m.load_strict_json(raw)


if __name__ == "__main__":
    unittest.main()
