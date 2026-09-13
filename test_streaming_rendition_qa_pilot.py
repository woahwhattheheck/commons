from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from revenue.streaming_rendition_qa_pilot.build_pilot_packet import (
    CHECKED_REPORT,
    OFFER,
    PROOF,
    PROSPECTS,
    SOURCE_MANIFEST,
    PacketError,
    canonical_json,
    compile_packet,
    load_json,
    render_buyer_report,
    sha256_bytes,
    validate_offer_text,
    validate_proof,
    validate_prospects,
    validate_source_manifest,
    write_packet,
)


class StreamingRenditionQAPilotTests(unittest.TestCase):
    def test_canonical_packet_compiles(self) -> None:
        packet = compile_packet()
        self.assertEqual(packet["schema"], "streaming-rendition-qa-pilot-packet/v1")
        self.assertEqual(len(packet["prospects"]), 10)
        self.assertEqual(
            packet["synthetic_report"]["summary"],
            {"total": 168, "release_ready": 140, "hold": 28},
        )
        self.assertEqual(len(packet["synthetic_report"]["fault_classes"]), 7)
        self.assertTrue(
            all(row["hold_count"] == 4 for row in packet["synthetic_report"]["fault_classes"])
        )
        self.assertEqual(
            CHECKED_REPORT.read_text(encoding="utf-8"),
            render_buyer_report(packet["synthetic_report"]),
        )

    def test_packet_is_byte_deterministic(self) -> None:
        first = canonical_json(compile_packet())
        second = canonical_json(compile_packet())
        self.assertEqual(first, second)
        self.assertEqual(sha256_bytes(first), sha256_bytes(second))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "packet.json"
            digest = write_packet(output, compile_packet())
            self.assertEqual(output.read_bytes(), first)
            self.assertEqual(digest, sha256_bytes(first))

    def test_source_manifest_drift_fails_closed(self) -> None:
        manifest = load_json(SOURCE_MANIFEST)
        changed = copy.deepcopy(manifest)
        changed["fixture"]["hold"] = 27
        with self.assertRaises(PacketError):
            validate_source_manifest(changed)
        changed = copy.deepcopy(manifest)
        changed["projection_sha256"] = "0" * 64
        with self.assertRaises(PacketError):
            validate_source_manifest(changed)

    def test_proof_cannot_claim_payment_acceptance_or_authority(self) -> None:
        proof = load_json(PROOF)
        changed = copy.deepcopy(proof)
        changed["commercial"]["payment_received"] = True
        with self.assertRaises(PacketError):
            validate_proof(changed)
        changed = copy.deepcopy(proof)
        changed["commercial"]["recognized_revenue_usd"] = 2500
        with self.assertRaises(PacketError):
            validate_proof(changed)
        changed = copy.deepcopy(proof)
        changed["authority"]["prospect_contact"] = True
        with self.assertRaises(PacketError):
            validate_proof(changed)

    def test_prospect_queue_rejects_private_or_ambiguous_rows(self) -> None:
        prospects = load_json(PROSPECTS)
        self.assertEqual(len(validate_prospects(prospects)), 10)

        changed = copy.deepcopy(prospects)
        changed[0]["contact_email"] = "buyer@example.com"
        with self.assertRaises(PacketError):
            validate_prospects(changed)

        changed = copy.deepcopy(prospects)
        changed[0]["evidence_summary"] += " buyer@example.com"
        with self.assertRaises(PacketError):
            validate_prospects(changed)

        changed = copy.deepcopy(prospects)
        changed[0]["evidence_url"] = "http://localhost/internal"
        with self.assertRaises(PacketError):
            validate_prospects(changed)

        changed = copy.deepcopy(prospects)
        changed[1]["organization"] = changed[0]["organization"]
        with self.assertRaises(PacketError):
            validate_prospects(changed)

        with self.assertRaises(PacketError):
            validate_prospects(prospects[:-1])

    def test_offer_scope_and_prices_are_bound(self) -> None:
        offer = OFFER.read_text(encoding="utf-8")
        validate_offer_text(offer)
        with self.assertRaises(PacketError):
            validate_offer_text(offer.replace("$2,500 flat", "$1 flat"))
        with self.assertRaises(PacketError):
            validate_offer_text(offer + "\nGuaranteed revenue for every buyer.\n")


if __name__ == "__main__":
    unittest.main()
