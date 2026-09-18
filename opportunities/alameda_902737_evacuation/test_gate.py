from datetime import datetime, timezone
from hashlib import sha256
import unittest

from opportunities.alameda_902737_evacuation import gate


def h(s):
    return sha256(s.encode()).hexdigest()


G1 = "gen1"
G2 = "gen2"
PG = "primegen1"
PACKET = h("packet")
ADDENDA = h("addenda")
DEADLINE = h("deadline")
TEAMING = h("teaming")
LOCAL_POLICY = h("local-policy")
PLATFORM, REFS, INSURANCE, SECURITY, SUPPORT = map(
    h, ("platform", "refs", "insurance", "security", "support")
)
WORKSHARE = h("workshare")

OFFICIAL = {
    PACKET: ("OFFICIAL_PACKET", "alameda-county", "buyer_packet", "PRESENT", G1),
    ADDENDA: ("OFFICIAL_ADDENDA_INDEX", "alameda-county", "addenda_generation", "CURRENT", G1),
    DEADLINE: ("OFFICIAL_CLAIM", "alameda-county", "deadline", "DUE_2026_10_13_1400_PT", G1),
    TEAMING: ("OFFICIAL_CLAIM", "alameda-county", "teaming", "PERMITTED", G1),
    LOCAL_POLICY: ("OFFICIAL_CLAIM", "alameda-county", "local_participation", "NOT_REQUIRED", G1),
}
PRIME = {
    PLATFORM: ("PRIME_EVIDENCE", "prime", "platform", "VERIFIED", PG),
    REFS: ("PRIME_EVIDENCE", "prime", "three_similar_jurisdictions", "VERIFIED", PG),
    INSURANCE: ("PRIME_EVIDENCE", "prime", "insurance", "VERIFIED", PG),
    SECURITY: ("PRIME_EVIDENCE", "prime", "security_accessibility", "VERIFIED", PG),
    SUPPORT: ("PRIME_EVIDENCE", "prime", "support_24x7", "VERIFIED", PG),
}
WORK = {
    WORKSHARE: (
        "INTERNAL_WORKSHARE_EVIDENCE", "prime", "paid_tjlabs_seam", "DEFINED", "work1"
    )
}


def row(i, digest, kind, subject, gate_name, value, generation):
    return {
        "source_id": i,
        "sha256": digest,
        "kind": kind,
        "subject": subject,
        "gate": gate_name,
        "value": value,
        "generation": generation,
    }


def packet():
    return {
        "opportunity_id": gate.OPPORTUNITY_ID,
        "buyer": {"teaming": "PROHIBITED", "local_participation": "REQUIRED"},
        "prime": {"org_id": "prime"},
        "evidence": [
            row("packet", PACKET, "OFFICIAL_PACKET", "alameda-county", "buyer_packet", "PRESENT", G1),
            row("addenda", ADDENDA, "OFFICIAL_ADDENDA_INDEX", "alameda-county", "addenda_generation", "CURRENT", G1),
            row("deadline", DEADLINE, "OFFICIAL_CLAIM", "alameda-county", "deadline", "DUE_2026_10_13_1400_PT", G1),
            row("teaming", TEAMING, "OFFICIAL_CLAIM", "alameda-county", "teaming", "PERMITTED", G1),
            row("local-policy", LOCAL_POLICY, "OFFICIAL_CLAIM", "alameda-county", "local_participation", "NOT_REQUIRED", G1),
            row("platform", PLATFORM, "PRIME_EVIDENCE", "prime", "platform", "VERIFIED", PG),
            row("refs", REFS, "PRIME_EVIDENCE", "prime", "three_similar_jurisdictions", "VERIFIED", PG),
            row("insurance", INSURANCE, "PRIME_EVIDENCE", "prime", "insurance", "VERIFIED", PG),
            row("security", SECURITY, "PRIME_EVIDENCE", "prime", "security_accessibility", "VERIFIED", PG),
            row("support", SUPPORT, "PRIME_EVIDENCE", "prime", "support_24x7", "VERIFIED", PG),
            row("workshare", WORKSHARE, "INTERNAL_WORKSHARE_EVIDENCE", "prime", "paid_tjlabs_seam", "DEFINED", "work1"),
        ],
    }


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.now = datetime(2026, 9, 17, 20, 0, tzinfo=timezone.utc)
        cls.fn = staticmethod(gate.build_replay_classifier(
            official_roots=OFFICIAL,
            prime_roots=PRIME,
            local_roots={},
            workshare_roots=WORK,
            now=cls.now,
        ))

    def state(self, p):
        return self.fn(p)["semantic"]["state"]

    def test_production_hold(self):
        self.assertEqual(
            gate.production_state()["semantic"]["state"],
            "HOLD_MISSING_OFFICIAL_PACKET",
        )

    def test_production_rejects_caller_clock(self):
        with self.assertRaises(TypeError):
            gate.classify(packet(), now=self.now)

    def test_positive_typed_generation_is_replay_only(self):
        self.assertEqual(self.state(packet()), "QUALIFIED_REPLAY_ONLY")

    def test_caller_buyer_policy_cannot_override_typed_claims(self):
        p = packet()
        p["buyer"] = {"teaming": "PROHIBITED", "local_participation": "REQUIRED"}
        self.assertEqual(self.state(p), "QUALIFIED_REPLAY_ONLY")

    def test_forged_policy_with_real_packet_stays_hold(self):
        p = packet()
        p["evidence"] = [r for r in p["evidence"] if r["gate"] != "teaming"]
        p["evidence"].append(row(
            "fake-teaming", h("fake-teaming"), "OFFICIAL_CLAIM", "alameda-county",
            "teaming", "PERMITTED", G1,
        ))
        self.assertEqual(self.state(p), "HOLD_BUYER_CLAIMS_UNBOUND")

    def test_source_generation_transplant_holds(self):
        roots = dict(OFFICIAL)
        roots[TEAMING] = ("OFFICIAL_CLAIM", "alameda-county", "teaming", "PERMITTED", G2)
        fn = gate.build_replay_classifier(
            official_roots=roots, prime_roots=PRIME, local_roots={},
            workshare_roots=WORK, now=self.now,
        )
        p = packet()
        next(r for r in p["evidence"] if r["gate"] == "teaming")["generation"] = G2
        self.assertEqual(
            fn(p)["semantic"]["state"],
            "HOLD_SOURCE_GENERATION_MISMATCH",
        )

    def test_untrusted_extra_same_gate_cannot_launder(self):
        p = packet()
        p["evidence"].append(row(
            "bad-team", h("bad-team"), "OFFICIAL_CLAIM", "alameda-county",
            "teaming", "PERMITTED", G1,
        ))
        self.assertEqual(self.state(p), "HOLD_BUYER_CLAIMS_UNBOUND")

    def test_prime_generation_transplant_holds(self):
        roots = dict(PRIME)
        roots[SUPPORT] = (
            "PRIME_EVIDENCE", "prime", "support_24x7", "VERIFIED", "primegen2"
        )
        fn = gate.build_replay_classifier(
            official_roots=OFFICIAL, prime_roots=roots, local_roots={},
            workshare_roots=WORK, now=self.now,
        )
        p = packet()
        next(r for r in p["evidence"] if r["gate"] == "support_24x7")["generation"] = "primegen2"
        self.assertEqual(
            fn(p)["semantic"]["state"],
            "HOLD_PRIME_GENERATION_MISMATCH",
        )

    def test_replay_deadline_closes(self):
        late = gate.build_replay_classifier(
            official_roots=OFFICIAL, prime_roots=PRIME, local_roots={},
            workshare_roots=WORK,
            now=datetime(2026, 10, 13, 22, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(
            late(packet())["semantic"]["state"],
            "NO_BID_DEADLINE_CLOSED",
        )

    def test_export_and_helper_rebind_do_not_redirect_saved_production_state(self):
        saved_state = gate.production_state
        original_classify = gate.classify
        original_runtime = gate._RUNTIME
        try:
            gate.classify = lambda *_a, **_k: {"semantic": {"state": "EVIL"}}
            gate._RUNTIME = (lambda: "evil")
            self.assertEqual(
                saved_state()["semantic"]["state"],
                "HOLD_MISSING_OFFICIAL_PACKET",
            )
        finally:
            gate.classify = original_classify
            gate._RUNTIME = original_runtime

    def test_workshare_identity_packet_collocate_stays_rejectable_and_live_is_clean(self):
        from pathlib import Path as _Path
        import open_door_guard as guard

        # Split the historical collocate across source lines so this test file
        # is not itself an admission-phrase hit. The joined string is the
        # exact WORKSHARE line from run 35295683453.
        head = "identity, export and packet-"
        tail = "required interfaces"
        blocked_line = (
            "- Integration contract matrix for GIS, emergency notification, "
            "emergency-management, " + head + tail + "."
        )
        blocked = "\n".join(
            [
                "diff --git a/opportunities/alameda_902737_evacuation/WORKSHARE.md "
                "b/opportunities/alameda_902737_evacuation/WORKSHARE.md",
                "--- a/opportunities/alameda_902737_evacuation/WORKSHARE.md",
                "+++ b/opportunities/alameda_902737_evacuation/WORKSHARE.md",
                "@@ -1,1 +1,1 @@",
                "+" + blocked_line,
            ]
        ) + "\n"
        self.assertEqual(
            {item.rule for item in guard.scan_diff(blocked)},
            {"admission-phrase"},
        )
        path = "opportunities/alameda_902737_evacuation/WORKSHARE.md"
        text = _Path(path).read_text(encoding="utf-8")
        self.assertNotIn(head + tail, text)
        self.assertIn("packet-specified", text)
        lines = [
            guard.AddedLine(path, n, line)
            for n, line in enumerate(text.splitlines(), 1)
        ]
        self.assertEqual(guard.scan_added(lines), [])

    def test_receipt_integrity_and_authority_ceiling(self):
        receipt = self.fn(packet())
        self.assertFalse(receipt["semantic"]["external_authority"])
        self.assertTrue(gate.verify_receipt(receipt))
        receipt["semantic"]["state"] = "TAMPERED"
        self.assertFalse(gate.verify_receipt(receipt))


if __name__ == "__main__":
    unittest.main()
