import json, unittest
import contact_cas as c

NOW="2026-09-14T03:50:00Z"; LATER="2026-09-14T03:50:05Z"; AFTER="2026-09-14T04:05:01Z"
A="Z-Vector"; B="Z-Rival"; NA="nonce-a-1234"; NB="nonce-b-1234"
MSG="a"*64; RECEIPT="b"*64; T=c.target_digest_for_email("Lead@Example.com")

class Tests(unittest.TestCase):
    def claimed(self, lease=900):
        return c.claim(c.empty_state(),target_digest=T,owner=A,nonce=NA,now=NOW,lease_seconds=lease)
    def armed(self):
        return c.arm(self.claimed(),target_digest=T,owner=A,nonce=NA,now=LATER,message_sha256=MSG)
    def test_email_digest_normalization(self):
        self.assertEqual(T,c.target_digest_for_email(" lead@example.COM. "))
        self.assertNotEqual(T,c.target_digest_for_email("other@example.com"))
    def test_raw_email_not_persisted(self):
        self.assertNotIn("lead@example.com",c._dump(self.claimed()).lower())
    def test_active_claim_blocks_peer(self):
        with self.assertRaisesRegex(c.ContactCasError,"active claim"):
            c.claim(self.claimed(),target_digest=T,owner=B,nonce=NB,now=LATER)
    def test_expired_claim_replaceable(self):
        s=self.claimed(10)
        s=c.claim(s,target_digest=T,owner=B,nonce=NB,now="2026-09-14T03:50:11Z")
        self.assertEqual(B,s["targets"][T]["owner"])
    def test_arm_nonexpiring(self):
        with self.assertRaisesRegex(c.ContactCasError,"armed"):
            c.claim(self.armed(),target_digest=T,owner=B,nonce=NB,now=AFTER)
    def test_gate_exact_tuple(self):
        s=self.armed()
        self.assertTrue(c.gate(s,target_digest=T,owner=A,nonce=NA,message_sha256=MSG))
        self.assertFalse(c.gate(s,target_digest=T,owner=B,nonce=NA,message_sha256=MSG))
        self.assertFalse(c.gate(s,target_digest=T,owner=A,nonce=NA,message_sha256="c"*64))
    def test_sent_terminal(self):
        s=c.record_sent(self.armed(),target_digest=T,owner=A,nonce=NA,now="2026-09-14T03:50:06Z",
                        message_sha256=MSG,provider_receipt_sha256=RECEIPT)
        self.assertEqual("sent",s["targets"][T]["status"])
        with self.assertRaisesRegex(c.ContactCasError,"sent"):
            c.claim(s,target_digest=T,owner=B,nonce=NB,now=AFTER)
    def test_release_armed_denied(self):
        with self.assertRaisesRegex(c.ContactCasError,"only a claimed"):
            c.release_claimed(self.armed(),target_digest=T,owner=A,nonce=NA)
    def test_reconcile_requires_provider_sent_check(self):
        with self.assertRaisesRegex(c.ContactCasError,"Sent-history"):
            c.reconcile_armed_not_sent(self.armed(),target_digest=T,owner=A,nonce=NA,sent_history_checked=False)
        s=c.reconcile_armed_not_sent(self.armed(),target_digest=T,owner=A,nonce=NA,sent_history_checked=True)
        self.assertNotIn(T,s["targets"])
    def test_bool_not_integer(self):
        with self.assertRaisesRegex(c.ContactCasError,"integer"):
            c.claim(c.empty_state(),target_digest=T,owner=A,nonce=NA,now=NOW,lease_seconds=True)
    def test_duplicate_json_key_rejected(self):
        raw='{"schema":"contact-cas/v1","revision":0,"revision":1,"targets":{}}'
        with self.assertRaisesRegex(c.ContactCasError,"duplicate JSON key"):
            json.loads(raw,object_pairs_hook=c._reject_duplicate_pairs)
    def test_message_digest_newlines(self):
        self.assertEqual(c.message_digest("S","a\r\nb\r"),c.message_digest("S","a\nb\n"))
    def test_revision_monotonic(self):
        s=self.claimed(); self.assertEqual(1,s["revision"])
        s=c.arm(s,target_digest=T,owner=A,nonce=NA,now=LATER,message_sha256=MSG); self.assertEqual(2,s["revision"])
        s=c.record_sent(s,target_digest=T,owner=A,nonce=NA,now="2026-09-14T03:50:06Z",
                        message_sha256=MSG,provider_receipt_sha256=RECEIPT); self.assertEqual(3,s["revision"])
    def test_extra_state_key_rejected(self):
        s=c.empty_state(); s["oops"]=1
        with self.assertRaisesRegex(c.ContactCasError,"state keys"): c.validate_state(s)
    def test_arm_after_expiry_denied(self):
        with self.assertRaisesRegex(c.ContactCasError,"expired"):
            c.arm(self.claimed(2),target_digest=T,owner=A,nonce=NA,now=LATER,message_sha256=MSG)
    def test_public_id_digest_stable(self):
        self.assertEqual(c.target_digest_for_public_id(" ACME / RFP 42 "),
                         c.target_digest_for_public_id("acme   / rfp 42"))
if __name__=="__main__": unittest.main()
