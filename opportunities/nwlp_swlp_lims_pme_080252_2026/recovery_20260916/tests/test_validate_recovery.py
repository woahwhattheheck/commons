import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validate_recovery", ROOT / "validate_recovery.py")
vr = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vr)


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


class RecoveryPacketTests(unittest.TestCase):
    def test_current_packet_valid(self):
        public = load("public_recovery_20260916.json")
        partner = load("partner_route_ledger_20260916.json")
        self.assertIn("HOLD_PORTAL_ATTACHMENT_AUTH_REQUIRED", vr.validate_public(public))
        self.assertIn("REPOSITORY_SEND_AUTHORITY_FALSE", vr.validate_partner(partner))

    def test_public_recovery_cannot_mint_bytes_without_hash(self):
        public = load("public_recovery_20260916.json")
        public["public_recovery"]["questionnaire_bytes_publicly_retrieved"] = True
        with self.assertRaises(vr.PacketError):
            vr.validate_public(public)

    def test_public_recovery_cannot_mint_digest_without_bytes(self):
        public = load("public_recovery_20260916.json")
        public["public_recovery"]["questionnaire_sha256"] = "0" * 64
        with self.assertRaises(vr.PacketError):
            vr.validate_public(public)

    def test_commercial_readiness_cannot_be_escalated(self):
        public = load("public_recovery_20260916.json")
        public["authority"]["commercial_readiness"] = True
        with self.assertRaises(vr.PacketError):
            vr.validate_public(public)

    def test_buyer_contact_authority_cannot_be_escalated(self):
        public = load("public_recovery_20260916.json")
        public["authority"]["buyer_contact_authorized"] = True
        with self.assertRaises(vr.PacketError):
            vr.validate_public(public)

    def test_deadline_cannot_be_silently_extended_to_rendered_2359(self):
        public = load("public_recovery_20260916.json")
        public["response_deadline_authority"]["deadline"] = "2026-10-01T23:59:00+01:00"
        with self.assertRaises(vr.PacketError):
            vr.validate_public(public)

    def test_partner_packet_never_authorizes_send(self):
        partner = load("partner_route_ledger_20260916.json")
        cirdan = next(r for r in partner["routes"] if r["partner"] == "Cirdan")
        cirdan["send_authorized"] = True
        with self.assertRaises(vr.PacketError):
            vr.validate_partner(partner)

    def test_clinisys_provider_dnr_cannot_be_erased(self):
        partner = load("partner_route_ledger_20260916.json")
        clinisys = next(r for r in partner["routes"] if r["partner"] == "Clinisys UK")
        clinisys["state"] = "READY"
        with self.assertRaises(vr.PacketError):
            vr.validate_partner(partner)

    def test_cirdan_route_is_exact(self):
        partner = load("partner_route_ledger_20260916.json")
        cirdan = next(r for r in partner["routes"] if r["partner"] == "Cirdan")
        cirdan["route"] = "sales@cirdan.com"
        with self.assertRaises(vr.PacketError):
            vr.validate_partner(partner)

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "dup.json"
            path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(vr.PacketError):
                vr.load_json(path)

    def test_bool_not_accepted_as_integer(self):
        public = load("public_recovery_20260916.json")
        public["schema_version"] = True
        with self.assertRaises(vr.PacketError):
            vr.validate_public(public)

    def test_partner_collision_count_bool_rejected(self):
        partner = load("partner_route_ledger_20260916.json")
        cirdan = next(r for r in partner["routes"] if r["partner"] == "Cirdan")
        cirdan["collision_census"]["slack_exact_org_domain_route_before_take"] = False
        with self.assertRaises(vr.PacketError):
            vr.validate_partner(partner)


if __name__ == "__main__":
    unittest.main()
