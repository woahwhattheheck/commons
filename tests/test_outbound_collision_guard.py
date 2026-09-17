from __future__ import annotations
import copy, hashlib, hmac, json, os, unittest
from revenue.outbound_collision_guard import (
    AUTHORITY, GuardError, MUSE_REGISTRY_SCHEMA, MUSE_TRUST_KEY_ENV,
    acquire, ambiguous_hold, begin_send, intent_fingerprint, observe_send,
    release_unsent, verify,
)

NOW="2026-09-17T03:15:00Z"; LATER="2026-09-17T03:16:00Z"
KEY="outbound-muse-trust-test-key-material-32bytes"
INTENT={"counterparty_key":"example.com","route_key":"email:sales@example.com","thread_key":"gmail:abc123","purpose_key":"paid-workshare:freight-qa"}
A={"claimant_id":"astra-z","session_id":"chat-11"}; B={"claimant_id":"fable-5.1","session_id":"seat-2"}

def canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)

def receipt(*, claimant=A, fp=None, generation=1, decision="SELECTED", rid="muse-r1", request_key="muse-q1", arbitrated="2026-09-17T03:14:59Z", expires="2026-09-17T03:25:00Z", source_ref="slack:dm:muse:1789615000.000001", source_sha="a"*64):
    return {"receipt_id":rid,"request_key":request_key,"intent_fingerprint":fp or intent_fingerprint(INTENT),
            "selected_claimant_id":claimant["claimant_id"],"selected_session_id":claimant["session_id"],
            "lease_generation":generation,"decision":decision,"arbitrated_at":arbitrated,"expires_at":expires,
            "source_ref":source_ref,"source_sha256":source_sha}

def registry(rows=None, *, generated="2026-09-17T03:15:00Z", key=KEY):
    body={"schema":MUSE_REGISTRY_SCHEMA,"generated_at":generated,"receipts":rows or [receipt()]}
    return {**body,"signature_hmac_sha256":hmac.new(key.encode(),canon(body).encode(),hashlib.sha256).hexdigest()}

def legacy_plain_receipt():
    r=receipt(); return {k:r[k] for k in ("receipt_id","intent_fingerprint","selected_claimant_id","selected_session_id","lease_generation","arbitrated_at","expires_at")}

class GuardTests(unittest.TestCase):
    def setUp(self):
        self.old=os.environ.get(MUSE_TRUST_KEY_ENV); os.environ[MUSE_TRUST_KEY_ENV]=KEY
    def tearDown(self):
        if self.old is None: os.environ.pop(MUSE_TRUST_KEY_ENV,None)
        else: os.environ[MUSE_TRUST_KEY_ENV]=self.old
    def waiting(self): return acquire(intent=INTENT,claimant=A,now=NOW,ttl_s=600)
    def ready(self): return acquire(intent=INTENT,claimant=A,now=NOW,ttl_s=600,muse=registry())

    def test_no_muse_waits_and_authority_false(self):
        out=self.waiting(); self.assertEqual(out["state"],"WAIT_MUSE"); self.assertEqual(out["authority"],AUTHORITY); self.assertTrue(verify(out))
    def test_legacy_plain_muse_injection_fails_closed(self):
        out=acquire(intent=INTENT,claimant=A,now=NOW,ttl_s=600,muse=legacy_plain_receipt()); self.assertEqual(out["state"],"WAIT_MUSE"); self.assertIsNone(out["lease"]["muse_registry_sha256"])
    def test_signed_registry_is_required_for_ready_and_bound_into_lease(self):
        reg=registry(); out=acquire(intent=INTENT,claimant=A,now=NOW,ttl_s=600,muse=reg)
        self.assertEqual(out["state"],"READY_SINGLE_WRITER"); self.assertEqual(out["lease"]["muse_receipt_id"],"muse-r1")
        self.assertEqual(out["lease"]["muse_request_key"],"muse-q1"); self.assertEqual(out["lease"]["muse_source_sha256"],"a"*64)
        self.assertEqual(len(out["lease"]["muse_registry_sha256"]),64); self.assertTrue(verify(out))
    def test_missing_runtime_key_fails_closed(self):
        os.environ.pop(MUSE_TRUST_KEY_ENV,None); self.assertEqual(acquire(intent=INTENT,claimant=A,now=NOW,ttl_s=600,muse=registry())["state"],"WAIT_MUSE")
    def test_wrong_runtime_key_fails_closed(self):
        os.environ[MUSE_TRUST_KEY_ENV]="wrong-runtime-trust-key-xxxxxxxx"; self.assertEqual(acquire(intent=INTENT,claimant=A,now=NOW,ttl_s=600,muse=registry())["state"],"WAIT_MUSE")
    def test_registry_signature_tamper_fails_closed(self):
        reg=registry(); reg["receipts"][0]["source_ref"]="slack:tampered"; self.assertEqual(acquire(intent=INTENT,claimant=A,now=NOW,ttl_s=600,muse=reg)["state"],"WAIT_MUSE")
    def test_source_digest_tamper_fails_closed(self):
        reg=registry(); reg["receipts"][0]["source_sha256"]="b"*64; self.assertEqual(acquire(intent=INTENT,claimant=A,now=NOW,ttl_s=600,muse=reg)["state"],"WAIT_MUSE")
    def test_duplicate_receipt_id_fails_closed(self):
        rows=[receipt(),receipt(source_ref="slack:other",source_sha="b"*64)]; self.assertEqual(acquire(intent=INTENT,claimant=A,now=NOW,ttl_s=600,muse=registry(rows))["state"],"WAIT_MUSE")
    def test_source_remint_fails_closed(self):
        rows=[receipt(),receipt(rid="muse-r2")]; self.assertEqual(acquire(intent=INTENT,claimant=A,now=NOW,ttl_s=600,muse=registry(rows))["state"],"WAIT_MUSE")
    def test_multiple_selected_receipts_for_same_generation_fail_closed(self):
        rows=[receipt(),receipt(rid="muse-r2",source_ref="slack:other",source_sha="b"*64)]; self.assertEqual(acquire(intent=INTENT,claimant=A,now=NOW,ttl_s=600,muse=registry(rows))["state"],"WAIT_MUSE")
    def test_future_registry_fails_closed(self):
        self.assertEqual(acquire(intent=INTENT,claimant=A,now=NOW,ttl_s=600,muse=registry(generated="2026-09-17T03:16:00Z"))["state"],"WAIT_MUSE")
    def test_registry_cannot_predate_receipt(self):
        rows=[receipt(arbitrated="2026-09-17T03:15:01Z",expires="2026-09-17T03:20:00Z")]; self.assertEqual(acquire(intent=INTENT,claimant=A,now="2026-09-17T03:16:00Z",ttl_s=600,muse=registry(rows,generated="2026-09-17T03:15:00Z"))["state"],"WAIT_MUSE")
    def test_future_receipt_fails_closed(self):
        rows=[receipt(arbitrated="2026-09-17T03:15:30Z",expires="2026-09-17T03:25:00Z")]; self.assertEqual(acquire(intent=INTENT,claimant=A,now=NOW,ttl_s=600,muse=registry(rows,generated="2026-09-17T03:15:30Z"))["state"],"WAIT_MUSE")
    def test_expired_receipt_fails_closed(self):
        rows=[receipt(expires="2026-09-17T03:14:59Z",arbitrated="2026-09-17T03:14:00Z")]; self.assertEqual(acquire(intent=INTENT,claimant=A,now=NOW,ttl_s=600,muse=registry(rows))["state"],"WAIT_MUSE")
    def test_wrong_claimant_fails_closed(self):
        self.assertEqual(acquire(intent=INTENT,claimant=A,now=NOW,ttl_s=600,muse=registry([receipt(claimant=B)]))["state"],"WAIT_MUSE")
    def test_wrong_intent_fails_closed(self):
        self.assertEqual(acquire(intent=INTENT,claimant=A,now=NOW,ttl_s=600,muse=registry([receipt(fp="0"*64)]))["state"],"WAIT_MUSE")
    def test_hold_and_yield_decisions_never_ready(self):
        for decision in ("HOLD","YIELD"):
            with self.subTest(decision=decision): self.assertEqual(acquire(intent=INTENT,claimant=A,now=NOW,ttl_s=600,muse=registry([receipt(decision=decision)]))["state"],"WAIT_MUSE")
    def test_lease_capped_by_authenticated_muse_expiry(self):
        out=acquire(intent=INTENT,claimant=A,now=NOW,ttl_s=600,muse=registry([receipt(expires="2026-09-17T03:17:00Z")]))
        self.assertEqual(out["lease"]["expires_at"],"2026-09-17T03:17:00Z")
    def test_live_other_claimant_yields_before_muse_authentication(self):
        old=self.waiting()["lease"]; out=acquire(intent=INTENT,claimant=B,now=LATER,ttl_s=600,existing=old,muse=legacy_plain_receipt()); self.assertEqual(out["state"],"YIELD_EXISTING"); self.assertEqual(out["lease"]["claimant"],A)
    def test_same_claimant_generation_can_become_ready_with_signed_registry(self):
        old=self.waiting()["lease"]; out=acquire(intent=INTENT,claimant=A,now=LATER,ttl_s=600,existing=old,muse=registry()); self.assertEqual(out["lease"]["generation"],1); self.assertEqual(out["state"],"READY_SINGLE_WRITER")
    def test_expired_claim_rotates_generation_and_requires_matching_signed_generation(self):
        old=self.waiting()["lease"]
        rows=[receipt(claimant=B,generation=2,arbitrated="2026-09-17T03:29:59Z",expires="2026-09-17T03:40:00Z")]
        out=acquire(intent=INTENT,claimant=B,now="2026-09-17T03:30:00Z",ttl_s=600,existing=old,muse=registry(rows,generated="2026-09-17T03:30:00Z")); self.assertEqual(out["lease"]["generation"],2); self.assertEqual(out["state"],"READY_SINGLE_WRITER")
    def test_stale_signed_generation_replay_fails_closed(self):
        old=self.waiting()["lease"]; rows=[receipt(generation=1,arbitrated="2026-09-17T03:29:59Z",expires="2026-09-17T03:40:00Z")]
        out=acquire(intent=INTENT,claimant=A,now="2026-09-17T03:30:00Z",ttl_s=600,existing=old,muse=registry(rows,generated="2026-09-17T03:30:00Z")); self.assertEqual(out["lease"]["generation"],2); self.assertEqual(out["state"],"WAIT_MUSE")
    def test_attempt_deterministic_and_changed_body_or_provider_rejected(self):
        ready=self.ready()["lease"]; body=hashlib.sha256(b"hello").hexdigest(); a=begin_send(lease=ready,body_sha256=body,provider="gmail",now=LATER); b=begin_send(lease=a["lease"],body_sha256=body,provider="gmail",now=LATER)
        self.assertEqual(a["lease"]["attempt"],b["lease"]["attempt"]); self.assertTrue(verify(b))
        with self.assertRaises(GuardError): begin_send(lease=a["lease"],body_sha256="2"*64,provider="gmail",now=LATER)
        with self.assertRaises(GuardError): begin_send(lease=a["lease"],body_sha256=body,provider="slack",now=LATER)
    def test_unknown_then_sent_same_attempt_even_after_expiry(self):
        a=begin_send(lease=self.ready()["lease"],body_sha256="1"*64,provider="gmail",now=LATER); rid=a["lease"]["attempt"]["attempt_id"]
        unknown=observe_send(lease=a["lease"],attempt_id=rid,provider_status="UNKNOWN",provider_message_id=None,now="2026-09-17T03:16:10Z"); self.assertEqual(unknown["state"],"READY_SINGLE_WRITER")
        sent=observe_send(lease=unknown["lease"],attempt_id=rid,provider_status="SENT",provider_message_id="gmail:msg",now="2026-09-17T03:26:10Z"); self.assertEqual(sent["state"],"SENT_TERMINAL")
    def test_sent_terminal_blocks_reopen(self):
        a=begin_send(lease=self.ready()["lease"],body_sha256="1"*64,provider="gmail",now=LATER); rid=a["lease"]["attempt"]["attempt_id"]
        sent=observe_send(lease=a["lease"],attempt_id=rid,provider_status="SENT",provider_message_id="gmail:msg-1",now="2026-09-17T03:16:10Z")
        out=acquire(intent=INTENT,claimant=B,now="2026-09-17T03:30:00Z",ttl_s=600,existing=sent["lease"],muse=None); self.assertEqual(out["state"],"SENT_TERMINAL")
    def test_release_and_ambiguous_hold(self):
        out=release_unsent(lease=self.waiting()["lease"],claimant=A,now=LATER); self.assertEqual(out["state"],"RELEASED_UNSENT"); self.assertTrue(verify(out))
        hold=ambiguous_hold(raw_counterparty="Acme / intro",raw_route="unknown alias",purpose_key="paid-workshare:qa"); self.assertEqual(hold["state"],"HOLD_AMBIGUOUS_COUNTERPARTY"); self.assertEqual(hold["authority"],AUTHORITY)
    def test_release_other_claimant_or_attempt_rejected(self):
        with self.assertRaises(GuardError): release_unsent(lease=self.waiting()["lease"],claimant=B,now=LATER)
        a=begin_send(lease=self.ready()["lease"],body_sha256="1"*64,provider="gmail",now=LATER)
        with self.assertRaises(GuardError): release_unsent(lease=a["lease"],claimant=A,now="2026-09-17T03:16:10Z")
    def test_invalid_intent_ttl_timestamp_and_tamper_fail(self):
        bad=dict(INTENT); bad["counterparty_key"]="unknown"
        with self.assertRaises(GuardError): acquire(intent=bad,claimant=A,now=NOW,ttl_s=600)
        with self.assertRaises(GuardError): acquire(intent=INTENT,claimant=A,now=NOW,ttl_s=True)
        with self.assertRaises(GuardError): acquire(intent=INTENT,claimant=A,now="2026-09-17T03:15:00+00:00",ttl_s=600)
        out=self.ready(); forged=copy.deepcopy(out); forged["authority"]["external_send"]=True
        with self.assertRaises(GuardError): verify(forged)
    def test_case_normalization_preserves_old_fingerprint_semantics(self):
        i2=dict(INTENT); i2["counterparty_key"]="EXAMPLE.COM"; self.assertEqual(intent_fingerprint(INTENT),intent_fingerprint(i2))
    def test_legacy_ready_lease_is_rejected_but_legacy_sent_terminal_is_fail_safe(self):
        ready=self.ready()["lease"]
        legacy={k:v for k,v in ready.items() if k not in {"muse_request_key","muse_registry_sha256","muse_registry_generated_at","muse_source_ref","muse_source_sha256"}}
        legacy["schema"]="outbound-collision-replay-guard/v1"
        with self.assertRaises(GuardError): begin_send(lease=legacy,body_sha256="1"*64,provider="gmail",now=LATER)
        legacy_wait=self.waiting()["lease"]; legacy_wait={k:v for k,v in legacy_wait.items() if k not in {"muse_request_key","muse_registry_sha256","muse_registry_generated_at","muse_source_ref","muse_source_sha256"}}; legacy_wait["schema"]="outbound-collision-replay-guard/v1"; legacy_wait["state"]="SENT_TERMINAL"; legacy_wait["terminal_result"]={"attempt_id":"attempt-old","provider_status":"SENT","provider_message_id":"gmail:old","observed_at":NOW}; legacy_wait["attempt"]={"attempt_id":"attempt-old","body_sha256":"1"*64,"provider":"gmail","started_at":NOW}
        out=acquire(intent=INTENT,claimant=B,now=LATER,ttl_s=600,existing=legacy_wait); self.assertEqual(out["state"],"SENT_TERMINAL")

if __name__=="__main__": unittest.main()
