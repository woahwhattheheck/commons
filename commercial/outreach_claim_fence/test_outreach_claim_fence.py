import datetime as dt
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import outreach_claim_fence as f

T0 = "2026-09-14T03:45:00Z"
T1 = "2026-09-14T03:45:30Z"
T2 = "2026-09-14T03:46:00Z"
T3 = "2026-09-14T03:48:00Z"
SRC = "slack:C0C2BE7K0KA/1789317107.693609"
DRAFT = hashlib.sha256(b"hello buyer").hexdigest()


class ClaimFenceTests(unittest.TestCase):
    def held(self, actor="Z-Sol-41", hold=120):
        return f.new_claim(source_ref=SRC, actor=actor, now=T0, hold_seconds=hold)

    def test_claim_id_is_deterministic(self):
        self.assertEqual(f.claim_id(SRC), f.claim_id("  " + SRC + "  "))
        self.assertEqual(len(f.claim_id(SRC)), 32)

    def test_scope_changes_collision_but_intent_does_not(self):
        self.assertNotEqual(f.claim_id(SRC, "initial", "email"), f.claim_id(SRC, "followup-1", "email"))
        self.assertEqual(f.claim_id(SRC, "initial", "email"), f.claim_id(SRC, "initial", "dm"))
        self.assertNotEqual(f.identity_sha256(SRC, "initial", "email"), f.identity_sha256(SRC, "initial", "dm"))

    def test_two_peers_different_channels_rendezvous_same_path(self):
        a = f.new_claim(source_ref=SRC, actor="peer-a", intent="email", now=T0)
        b = f.new_claim(source_ref=SRC, actor="peer-b", intent="dm", now=T0)
        self.assertEqual(f.claim_path(a["claim_id"]), f.claim_path(b["claim_id"]))
        self.assertNotEqual(a["identity_sha256"], b["identity_sha256"])

    def test_claim_path_is_sharded(self):
        cid = f.claim_id(SRC)
        self.assertEqual(f.claim_path(cid), f"ground/outreach-claims/v1/{cid[:2]}/{cid}.json")

    def test_rejects_raw_email_as_source(self):
        with self.assertRaises(f.ClaimError):
            f.new_claim(source_ref="person@example.com", actor="a", now=T0)

    def test_rejects_mailto_as_source(self):
        with self.assertRaises(f.ClaimError):
            f.new_claim(source_ref="mailto:person.example.com", actor="a", now=T0)

    def test_rejects_bad_actor(self):
        with self.assertRaises(f.ClaimError):
            self.held("two words")

    def test_hold_bounds(self):
        for bad in (True, 0, 14, 3601):
            with self.assertRaises(f.ClaimError):
                self.held(hold=bad)

    def test_new_record_validates(self):
        rec = self.held()
        self.assertEqual(f.validate_record(rec), rec)
        self.assertEqual(rec["state"], "HELD")
        self.assertEqual(rec["generation"], 1)

    def test_canonical_json_stable(self):
        rec = self.held()
        a = f.canonical_json(rec)
        b = f.canonical_json(dict(reversed(list(rec.items()))))
        self.assertEqual(a, b)
        self.assertTrue(a.endswith("\n"))

    def test_owner_may_commit_but_not_send_while_held(self):
        d = f.decision(self.held(), actor="Z-Sol-41", now=T1)
        self.assertEqual(d["code"], "OWNER_MAY_COMMIT")
        self.assertFalse(d["may_send"])

    def test_other_is_blocked_while_held(self):
        d = f.decision(self.held(), actor="peer", now=T1)
        self.assertEqual(d["code"], "BLOCKED_HELD_BY_OTHER")

    def test_expired_hold_available_but_not_sendable(self):
        d = f.decision(self.held(hold=15), actor="peer", now=T2)
        self.assertEqual(d["code"], "AVAILABLE_EXPIRED_HOLD")
        self.assertFalse(d["may_send"])

    def test_owner_commit(self):
        rec = f.commit_claim(self.held(), actor="Z-Sol-41", draft_sha256=DRAFT, now=T1)
        self.assertEqual(rec["state"], "COMMITTED")
        self.assertIsNone(rec["hold_until"])
        self.assertEqual(rec["draft_sha256"], DRAFT)

    def test_commit_is_send_gate(self):
        rec = f.commit_claim(self.held(), actor="Z-Sol-41", draft_sha256=DRAFT, now=T1)
        self.assertTrue(f.decision(rec, actor="Z-Sol-41", now=T2)["may_send"])
        self.assertEqual(f.decision(rec, actor="peer", now=T2)["code"], "BLOCKED_COMMITTED_BY_OTHER")

    def test_wrong_actor_cannot_commit(self):
        with self.assertRaises(f.ClaimError):
            f.commit_claim(self.held(), actor="peer", draft_sha256=DRAFT, now=T1)

    def test_cannot_commit_expired_hold(self):
        with self.assertRaises(f.ClaimError):
            f.commit_claim(self.held(hold=15), actor="Z-Sol-41", draft_sha256=DRAFT, now=T2)

    def test_bad_draft_digest_rejected(self):
        with self.assertRaises(f.ClaimError):
            f.commit_claim(self.held(), actor="Z-Sol-41", draft_sha256="123", now=T1)

    def test_mark_sent(self):
        rec = f.commit_claim(self.held(), actor="Z-Sol-41", draft_sha256=DRAFT, now=T1)
        sent = f.mark_sent(rec, actor="Z-Sol-41", evidence="gmail:18f0abc123", now=T2)
        self.assertEqual(sent["state"], "SENT")
        self.assertEqual(f.decision(sent, actor="Z-Sol-41", now=T3)["code"], "BLOCKED_ALREADY_SENT")
        self.assertFalse(f.decision(sent, actor="Z-Sol-41", now=T3)["may_send"])

    def test_sent_requires_commit(self):
        with self.assertRaises(f.ClaimError):
            f.mark_sent(self.held(), actor="Z-Sol-41", evidence="gmail:x", now=T1)

    def test_send_evidence_is_opaque_token(self):
        rec = f.commit_claim(self.held(), actor="Z-Sol-41", draft_sha256=DRAFT, now=T1)
        with self.assertRaises(f.ClaimError):
            f.mark_sent(rec, actor="Z-Sol-41", evidence="person@example.com", now=T2)
        with self.assertRaises(f.ClaimError):
            f.mark_sent(rec, actor="Z-Sol-41", evidence="contains spaces", now=T2)

    def test_release_held(self):
        rec = f.release_claim(self.held(), actor="Z-Sol-41", reason="bad-fit", now=T1)
        self.assertEqual(rec["state"], "RELEASED")
        self.assertEqual(f.decision(rec, actor="peer", now=T2)["code"], "AVAILABLE_RELEASED")

    def test_commit_cannot_be_released(self):
        rec = f.commit_claim(self.held(), actor="Z-Sol-41", draft_sha256=DRAFT, now=T1)
        with self.assertRaises(f.ClaimError):
            f.release_claim(rec, actor="Z-Sol-41", reason="changed-mind", now=T2)

    def test_takeover_expired_hold(self):
        old = self.held(hold=15)
        rec = f.takeover_claim(old, new_actor="peer", now=T2)
        self.assertEqual(rec["generation"], 2)
        self.assertEqual(rec["actor"], "peer")
        self.assertEqual(rec["claim_id"], old["claim_id"])
        self.assertEqual(rec["source_fingerprint"], old["source_fingerprint"])
        self.assertEqual(rec["collision_sha256"], old["collision_sha256"])
        self.assertEqual(rec["identity_sha256"], old["identity_sha256"])

    def test_takeover_released(self):
        released = f.release_claim(self.held(), actor="Z-Sol-41", reason="handoff", now=T1)
        rec = f.takeover_claim(released, new_actor="peer", now=T2)
        self.assertEqual(rec["generation"], 2)
        self.assertEqual(rec["state"], "HELD")

    def test_takeover_live_hold_rejected(self):
        with self.assertRaises(f.ClaimError):
            f.takeover_claim(self.held(), new_actor="peer", now=T1)

    def test_takeover_committed_rejected_forever(self):
        rec = f.commit_claim(self.held(), actor="Z-Sol-41", draft_sha256=DRAFT, now=T1)
        with self.assertRaises(f.ClaimError):
            f.takeover_claim(rec, new_actor="peer", now="2030-01-01T00:00:00Z")

    def test_tampered_state_rejected(self):
        rec = self.held()
        rec["state"] = "MAGIC"
        with self.assertRaises(f.ClaimError):
            f.validate_record(rec)

    def test_unknown_key_rejected(self):
        rec = self.held()
        rec["surprise"] = True
        with self.assertRaises(f.ClaimError):
            f.validate_record(rec)

    def test_missing_key_rejected(self):
        rec = self.held()
        del rec["actor"]
        with self.assertRaises(f.ClaimError):
            f.validate_record(rec)

    def test_held_cannot_carry_committed_fields(self):
        rec = self.held()
        rec["draft_sha256"] = DRAFT
        with self.assertRaises(f.ClaimError):
            f.validate_record(rec)

    def test_chronology_enforced_for_sent(self):
        rec = f.commit_claim(self.held(), actor="Z-Sol-41", draft_sha256=DRAFT, now=T1)
        with self.assertRaises(f.ClaimError):
            f.mark_sent(rec, actor="Z-Sol-41", evidence="gmail:x", now=T0)

    def test_naive_time_rejected(self):
        with self.assertRaises(f.ClaimError):
            f.parse_time("2026-09-14T03:45:00")

    def test_load_record_round_trip(self):
        rec = self.held()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "claim.json"
            p.write_text(f.canonical_json(rec), encoding="utf-8")
            self.assertEqual(f.load_record(p), rec)

    def test_json_encoding_is_ascii(self):
        rec = self.held(actor="ascii")
        self.assertEqual(f.canonical_json(rec).encode("ascii").decode("ascii"), f.canonical_json(rec))

    def test_bool_generation_rejected(self):
        rec = self.held()
        rec["generation"] = True
        with self.assertRaises(f.ClaimError):
            f.validate_record(rec)

    def test_bad_scope_rejected(self):
        with self.assertRaises(f.ClaimError):
            f.new_claim(source_ref=SRC, actor="a", scope="Not Allowed!", now=T0)

    def test_claim_id_bound_to_stored_collision_identity(self):
        rec = self.held()
        self.assertEqual(rec["claim_id"], rec["collision_sha256"][:32])
        self.assertEqual(
            rec["collision_sha256"],
            f.collision_sha256_from_fingerprint(rec["source_fingerprint"], rec["scope"]),
        )
        self.assertEqual(
            rec["identity_sha256"],
            f.identity_sha256_from_fingerprint(rec["source_fingerprint"], rec["scope"], rec["intent"]),
        )

    def test_tampered_claim_id_rejected(self):
        rec = self.held()
        rec["claim_id"] = "0" * 32 if rec["claim_id"] != "0" * 32 else "1" * 32
        with self.assertRaises(f.ClaimError):
            f.validate_record(rec)

    def test_tampered_collision_digest_rejected(self):
        rec = self.held()
        rec["collision_sha256"] = "0" * 64 if rec["collision_sha256"] != "0" * 64 else "1" * 64
        with self.assertRaises(f.ClaimError):
            f.validate_record(rec)

    def test_tampered_identity_digest_rejected(self):
        rec = self.held()
        rec["identity_sha256"] = "0" * 64 if rec["identity_sha256"] != "0" * 64 else "1" * 64
        with self.assertRaises(f.ClaimError):
            f.validate_record(rec)

    def test_tampered_scope_rejected_by_identity_binding(self):
        rec = self.held()
        rec["scope"] = "followup-1"
        with self.assertRaises(f.ClaimError):
            f.validate_record(rec)

    def test_tampered_intent_rejected_by_identity_binding(self):
        rec = self.held()
        rec["intent"] = "dm"
        with self.assertRaises(f.ClaimError):
            f.validate_record(rec)

    def test_source_fingerprint_does_not_embed_source(self):
        fp = f.source_fingerprint(SRC)
        self.assertNotIn("C0C2", fp)
        self.assertEqual(len(fp), 64)


if __name__ == "__main__":
    unittest.main()
