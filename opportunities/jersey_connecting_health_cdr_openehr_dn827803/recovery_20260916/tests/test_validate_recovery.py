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


class JerseyRecoveryPacketTests(unittest.TestCase):
    def test_current_packet_valid(self):
        public = load("public_recovery_20260916.json")
        partners = load("partner_route_ledger_20260916.json")
        self.assertIn("HOLD_TENDER_PACK_REQUIRED", vr.validate_public(public))
        self.assertIn("REPOSITORY_SEND_AUTHORITY_FALSE", vr.validate_partners(partners))

    def test_no_attachments_is_not_pack_acquisition(self):
        public = load("public_recovery_20260916.json")
        public["tender_pack"]["acquired"] = True
        with self.assertRaises(vr.PacketError):
            vr.validate_public(public)

    def test_pack_digest_cannot_be_minted_without_bytes(self):
        public = load("public_recovery_20260916.json")
        public["tender_pack"]["sha256"] = "0" * 64
        with self.assertRaises(vr.PacketError):
            vr.validate_public(public)

    def test_login_boundary_cannot_be_erased(self):
        public = load("public_recovery_20260916.json")
        public["tender_pack"]["boundary"] = "READY"
        with self.assertRaises(vr.PacketError):
            vr.validate_public(public)

    def test_register_interest_cannot_be_authorized_by_packet(self):
        public = load("public_recovery_20260916.json")
        public["authority"]["register_interest_authorized"] = True
        with self.assertRaises(vr.PacketError):
            vr.validate_public(public)

    def test_buyer_contact_cannot_be_authorized_by_packet(self):
        public = load("public_recovery_20260916.json")
        public["authority"]["buyer_contact_authorized"] = True
        with self.assertRaises(vr.PacketError):
            vr.validate_public(public)

    def test_tender_submission_cannot_be_authorized_by_packet(self):
        public = load("public_recovery_20260916.json")
        public["authority"]["tender_submission_authorized"] = True
        with self.assertRaises(vr.PacketError):
            vr.validate_public(public)

    def test_better_dnr_cannot_be_erased(self):
        partners = load("partner_route_ledger_20260916.json")
        better = next(r for r in partners["routes"] if r["partner"] == "Better Ltd")
        better["state"] = "READY"
        with self.assertRaises(vr.PacketError):
            vr.validate_partners(partners)

    def test_vitagroup_route_is_exact(self):
        partners = load("partner_route_ledger_20260916.json")
        vita = next(r for r in partners["routes"] if r["partner"] == "vitagroup HIP")
        vita["route"] = "sales@vitagroup.ag"
        with self.assertRaises(vr.PacketError):
            vr.validate_partners(partners)

    def test_repository_never_authorizes_partner_send(self):
        partners = load("partner_route_ledger_20260916.json")
        vita = next(r for r in partners["routes"] if r["partner"] == "vitagroup HIP")
        vita["send_authorized"] = True
        with self.assertRaises(vr.PacketError):
            vr.validate_partners(partners)

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

    def test_collision_count_bool_rejected(self):
        partners = load("partner_route_ledger_20260916.json")
        vita = next(r for r in partners["routes"] if r["partner"] == "vitagroup HIP")
        vita["collision_census"]["slack_exact_org_domain_before_take"] = False
        with self.assertRaises(vr.PacketError):
            vr.validate_partners(partners)


if __name__ == "__main__":
    unittest.main()
