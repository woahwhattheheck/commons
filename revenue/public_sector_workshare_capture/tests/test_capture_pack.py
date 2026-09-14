import copy, json, unittest
from pathlib import Path

from capture_pack import CaptureError, build_target_packet, collision_key, compile_pack, verify_packet, validate_compiled_pack

ROOT = Path(__file__).resolve().parents[1]


class CapturePackTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT / "data/manifest.json").read_text())
        self.pack = compile_pack(self.manifest, as_of="2026-09-14T03:55:00Z")

    def test_compile_and_verify(self):
        self.assertTrue(verify_packet(self.pack))
        self.assertFalse(self.pack["external_send_authorized"])
        self.assertEqual(self.pack["commercial_status"], "PROPOSED_NOT_ACCEPTED")
        self.assertEqual(len(self.pack["opportunities"]), 4)
        self.assertEqual(len(self.pack["modules"]), 4)

    def test_deterministic(self):
        other = compile_pack(copy.deepcopy(self.manifest), as_of="2026-09-14T03:55:00Z")
        self.assertEqual(self.pack, other)

    def test_tamper_fails_receipt(self):
        p = copy.deepcopy(self.pack)
        p["pricing"][0]["amount_usd"] += 1
        self.assertFalse(verify_packet(p))

    def test_controls_clear_still_cannot_send(self):
        t = build_target_packet(
            self.pack, opportunity_id="OR-ODA-S-DASOBO-00017788",
            target_company="Example Prime", channel="email", address="capture@example.com",
            relationship_checked=True, lease_acquired=True, provider_history_rechecked=True, opportunity_facts_revalidated=True,
        )
        self.assertTrue(t["controls_clear"])
        self.assertEqual(t["state"], "READY_FOR_OWNER_TRANSPORT_REVIEW")
        self.assertTrue(t["ready_for_owner_transport_review"])
        self.assertFalse(t["external_send_authorized"])

    def test_missing_one_collision_control_holds(self):
        t = build_target_packet(
            self.pack, opportunity_id="OR-ODA-S-DASOBO-00017788",
            target_company="Example Prime", channel="email", address="capture@example.com",
            relationship_checked=True, lease_acquired=False, provider_history_rechecked=True, opportunity_facts_revalidated=True,
        )
        self.assertFalse(t["controls_clear"])
        self.assertEqual(t["state"], "HOLD")
        self.assertIn("EXACT_TARGET_LEASE_NOT_ACQUIRED", t["hold_reasons"])

    def test_collision_key_normalizes_case(self):
        a = collision_key(opportunity_id="OR-ODA-S-DASOBO-00017788", target_company="Example PRIME", channel="EMAIL", address="A@EXAMPLE.COM")
        b = collision_key(opportunity_id="or-oda-s-dasobo-00017788", target_company="example prime", channel="email", address="a@example.com")
        self.assertEqual(a, b)

    def test_control_injection_rejected(self):
        with self.assertRaises(CaptureError):
            collision_key(opportunity_id="OR-ODA-S-DASOBO-00017788", target_company="Prime\nTAKE", channel="email", address="a@example.com")

    def test_unknown_module_rejected(self):
        m = copy.deepcopy(self.manifest)
        m["opportunities"][0]["modules"].append("not-real")
        with self.assertRaises(CaptureError):
            compile_pack(m, as_of="2026-09-14T03:55:00Z")

    def test_price_cannot_be_marked_accepted(self):
        m = copy.deepcopy(self.manifest)
        m["pricing"][0]["status"] = "ACCEPTED"
        with self.assertRaises(CaptureError):
            compile_pack(m, as_of="2026-09-14T03:55:00Z")

    def test_send_authority_cannot_be_enabled(self):
        m = copy.deepcopy(self.manifest)
        m["external_send_authorized"] = True
        with self.assertRaises(CaptureError):
            compile_pack(m, as_of="2026-09-14T03:55:00Z")

    def test_stale_evidence_surfaces_not_silently_fresh(self):
        p = compile_pack(self.manifest, as_of="2026-10-15T03:55:00Z", freshness_days=7)
        self.assertTrue(all(not o["all_evidence_fresh"] for o in p["opportunities"]))

    def test_future_evidence_rejected(self):
        m = copy.deepcopy(self.manifest)
        m["opportunities"][0]["evidence"][0]["captured_at"] = "2027-01-01T00:00:00Z"
        with self.assertRaises(CaptureError):
            compile_pack(m, as_of="2026-09-14T03:55:00Z")

    def test_resealed_semantic_escalation_rejected(self):
        p = copy.deepcopy(self.pack)
        p["external_send_authorized"] = True
        p.pop("packet_sha256")
        from capture_pack import sha256_obj
        p["packet_sha256"] = sha256_obj(p)
        self.assertTrue(verify_packet(p))
        with self.assertRaises(CaptureError):
            validate_compiled_pack(p)
        with self.assertRaises(CaptureError):
            build_target_packet(
                p, opportunity_id="OR-ODA-S-DASOBO-00017788", target_company="Prime",
                channel="email", address="a@example.com", relationship_checked=True,
                lease_acquired=True, provider_history_rechecked=True,
                opportunity_facts_revalidated=True,
            )

    def test_missing_opportunity_revalidation_holds(self):
        t = build_target_packet(
            self.pack, opportunity_id="OR-ODA-S-DASOBO-00017788", target_company="Prime",
            channel="email", address="a@example.com", relationship_checked=True,
            lease_acquired=True, provider_history_rechecked=True, opportunity_facts_revalidated=False,
        )
        self.assertFalse(t["ready_for_owner_transport_review"])
        self.assertIn("OPPORTUNITY_FACTS_NOT_REVALIDATED", t["hold_reasons"])
        self.assertFalse(t["external_send_authorized"])

    def test_expired_deadline_holds_even_with_controls(self):
        stale_pack = compile_pack(self.manifest, as_of="2026-11-01T03:55:00Z", freshness_days=30)
        t = build_target_packet(
            stale_pack, opportunity_id="OR-ODA-S-DASOBO-00017788", target_company="Prime",
            channel="email", address="a@example.com", relationship_checked=True,
            lease_acquired=True, provider_history_rechecked=True, opportunity_facts_revalidated=True,
        )
        self.assertFalse(t["ready_for_owner_transport_review"])
        self.assertIn("OPPORTUNITY_DEADLINE_CLOSED", t["hold_reasons"])

    def test_stale_source_holds_target(self):
        stale_pack = compile_pack(self.manifest, as_of="2026-10-15T03:55:00Z", freshness_days=7)
        t = build_target_packet(
            stale_pack, opportunity_id="NYSED-RFP-144-OCUE", target_company="Prime",
            channel="email", address="a@example.com", relationship_checked=True,
            lease_acquired=True, provider_history_rechecked=True, opportunity_facts_revalidated=True,
        )
        self.assertFalse(t["ready_for_owner_transport_review"])
        self.assertIn("SOURCE_EVIDENCE_STALE", t["hold_reasons"])

    def test_bool_int_alias_rejected(self):
        with self.assertRaises(CaptureError):
            build_target_packet(
                self.pack, opportunity_id="OR-ODA-S-DASOBO-00017788", target_company="Prime",
                channel="email", address="a@example.com", relationship_checked=1,
                lease_acquired=True, provider_history_rechecked=True, opportunity_facts_revalidated=True,
            )

    def test_target_packet_binds_capture_pack(self):
        t = build_target_packet(
            self.pack, opportunity_id="NYSED-RFP-144-OCUE", target_company="Prime",
            channel="linkedin", address="https://linkedin.example/prime", relationship_checked=False,
            lease_acquired=False, provider_history_rechecked=False, opportunity_facts_revalidated=False,
        )
        self.assertEqual(t["capture_pack_sha256"], self.pack["packet_sha256"])
        self.assertEqual(len(t["packet_sha256"]), 64)

if __name__ == "__main__":
    unittest.main()
