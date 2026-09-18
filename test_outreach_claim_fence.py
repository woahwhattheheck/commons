import base64
import datetime as dt
import email.utils
import hashlib
import io
import json
import os
import tempfile
import unittest
import urllib.parse
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

import outreach_claim_fence as ocf
from outreach_claim_fence.core import _NoRedirect


class FakeGitHubTransport:
    def __init__(self):
        self.now = dt.datetime(2026, 9, 14, 12, 0, tzinfo=dt.timezone.utc)
        self.files = {}
        self.commit_counter = 0
        self.requests = []
        self.omit_date = False
        self.malformed_read = False
        self.before_put = None
    def advance(self, seconds): self.now += dt.timedelta(seconds=seconds)
    def _headers(self): return {} if self.omit_date else {"Date": email.utils.format_datetime(self.now, usegmt=True)}
    @staticmethod
    def _path(url):
        parsed = urllib.parse.urlparse(url); return urllib.parse.unquote(parsed.path.split("/contents/",1)[1])
    def request(self, method, url, headers, body=None):
        self.requests.append((method,url,dict(headers),body)); path = self._path(url)
        if method == "GET":
            if self.malformed_read: return ocf.HttpResponse(200,self._headers(),b"not-json")
            item = self.files.get(path)
            if item is None: return ocf.HttpResponse(404,self._headers(),b'{"message":"Not Found"}')
            payload={"type":"file","sha":item["sha"],"encoding":"base64","content":base64.b64encode(item["content"]).decode()}
            return ocf.HttpResponse(200,self._headers(),json.dumps(payload).encode())
        if method != "PUT": raise AssertionError(method)
        if self.before_put is not None:
            cb,self.before_put=self.before_put,None; cb(self,path)
        payload=json.loads(body.decode()); raw=base64.b64decode(payload["content"]); current=self.files.get(path); supplied=payload.get("sha")
        if current is None and supplied is not None: return ocf.HttpResponse(409,self._headers(),b'{}')
        if current is not None and supplied is None: return ocf.HttpResponse(422,self._headers(),b'{}')
        if current is not None and supplied != current["sha"]: return ocf.HttpResponse(409,self._headers(),b'{}')
        blob=hashlib.sha1(b"blob\0"+raw).hexdigest(); self.commit_counter+=1; commit=hashlib.sha1(f"c:{self.commit_counter}:{blob}".encode()).hexdigest()
        self.files[path]={"content":raw,"sha":blob,"commit":commit}
        return ocf.HttpResponse(201 if current is None else 200,self._headers(),json.dumps({"content":{"sha":blob},"commit":{"sha":commit}}).encode())
    def record(self, store, contact="Lead@Example.COM"):
        ident=ocf.normalize_target("email",contact); path=store.path_for(ident.claim_key); return json.loads(self.files[path]["content"]),path
    def inject(self,path,record):
        raw=ocf._canonical_json_bytes(record)+b"\n"; blob=hashlib.sha1(b"blob\0"+raw).hexdigest(); self.files[path]={"content":raw,"sha":blob,"commit":"x"*40}


class FenceCase(unittest.TestCase):
    def setUp(self):
        self.t=FakeGitHubTransport(); self.key=b"R"*32
        self.s=ocf.GitHubContentsClaimStore(token="token",transport=self.t,reconciliation_key=self.key)
        self.kw={"target_kind":"email","contact":"Lead@Example.COM","opportunity":"$1500 paid discovery","agent_id":"Z-Tungsten","operation_id":"OP-1","lease_seconds":3600}
    def acquire(self,**u): d=dict(self.kw); d.update(u); return self.s.acquire(**d)
    def arm(self,msg=b"paid proposal",**u):
        d={"target_kind":"email","contact":self.kw["contact"],"agent_id":self.kw["agent_id"],"operation_id":self.kw["operation_id"],"message_digest":ocf.digest_message_bytes(msg),"channel":"email","compensation_path":"$1500 paid discovery"}; d.update(u); return self.s.arm(**d)
    def dispatch(self,token): return self.s.begin_dispatch(target_kind="email",contact=self.kw["contact"],agent_id=self.kw["agent_id"],operation_id=self.kw["operation_id"],dispatch_token=token)
    def contacted(self,msg=b"paid proposal",**u):
        d={"target_kind":"email","contact":self.kw["contact"],"agent_id":self.kw["agent_id"],"operation_id":self.kw["operation_id"],"message_digest":ocf.digest_message_bytes(msg),"channel":"email","compensation_path":"$1500 paid discovery","cooldown_seconds":600}; d.update(u); return self.s.mark_contacted(**d)

    # 1-8 authority / token boundary
    def test_01_schema_is_v2(self): self.assertEqual(ocf.SCHEMA,"outreach-claim-fence/v2")
    def test_02_canonical_defaults_are_v2(self): self.assertTrue(ocf.DEFAULT_BRANCH.endswith("v2")); self.assertTrue(ocf.DEFAULT_ROOT.endswith("v2"))
    def test_03_alt_repository_rejected(self):
        with self.assertRaises(ocf.ValidationError): ocf.GitHubContentsClaimStore(token="x",repository="other/repo")
    def test_04_alt_branch_rejected(self):
        with self.assertRaises(ocf.ValidationError): ocf.GitHubContentsClaimStore(token="x",branch="other")
    def test_05_alt_root_rejected(self):
        with self.assertRaises(ocf.ValidationError): ocf.GitHubContentsClaimStore(token="x",root="other")
    def test_06_alt_api_rejected(self):
        with self.assertRaises(ocf.ValidationError): ocf.GitHubContentsClaimStore(token="x",api_url="https://evil.example")
    def test_07_transport_rejects_http_and_userinfo(self):
        for url in ("http://api.github.com/x","https://u:p@api.github.com/x","https://evil.example/x"):
            with self.subTest(url=url), self.assertRaises(ocf.ValidationError): ocf.UrllibTransport._validate_url(url)
    def test_08_redirect_handler_refuses_follow(self): self.assertIsNone(_NoRedirect().redirect_request(None,None,302,"",{},"https://evil.example"))

    # 9-15 identity / receipt / CAS
    def test_09_email_normalization_collides_case(self): self.assertEqual(ocf.normalize_target("email","Lead@Example.com").claim_key,ocf.normalize_target("email","lead@example.COM").claim_key)
    def test_10_receipt_binds_authority(self):
        r=self.acquire(); self.assertEqual(r.authority_digest,ocf.AUTHORITY_DIGEST); self.assertEqual(r.repository,ocf.CANONICAL_REPOSITORY); self.assertEqual(r.branch,ocf.DEFAULT_BRANCH)
    def test_11_same_owner_acquire_idempotent(self): self.assertEqual(self.acquire().revision,self.acquire().revision)
    def test_12_other_owner_conflicts_live(self):
        self.acquire()
        with self.assertRaises(ocf.ClaimConflict): self.acquire(agent_id="Z-Other",operation_id="OP-2")
    def test_13_expired_active_can_transfer(self): self.acquire(lease_seconds=60); self.t.advance(61); self.assertEqual(self.acquire(agent_id="Z-Other",operation_id="OP-2").agent_id,"Z-Other")
    def test_14_cas_stale_writer_retries(self):
        s2=ocf.GitHubContentsClaimStore(token="token",transport=self.t,reconciliation_key=self.key)
        def race(t,path):
            # Winning concurrent writer claims first using a separate transport call path.
            t.before_put=None; s2.acquire(**{**self.kw,"agent_id":"winner","operation_id":"W"})
        self.t.before_put=race
        with self.assertRaises(ocf.ClaimConflict): self.acquire()
    def test_15_missing_server_time_fails_closed(self): self.t.omit_date=True; self.assertRaises(ocf.ProtocolError,self.acquire)

    # 16-22 arming / dispatch ambiguity
    def test_16_arm_returns_plaintext_one_time_token_not_stored(self):
        self.acquire(); r=self.arm(); self.assertIsNotNone(r.dispatch_token); record,_=self.t.record(self.s); self.assertNotIn(r.dispatch_token,json.dumps(record)); self.assertEqual(record["state"],"ARMED")
    def test_17_arm_requires_paid_path(self):
        self.acquire()
        with self.assertRaises(ocf.ValidationError): self.arm(compensation_path="hope for payoff")
    def test_18_dispatch_requires_current_token(self):
        self.acquire(); token=self.arm().dispatch_token
        with self.assertRaises(ocf.OwnershipError): self.dispatch("wrong-token-which-is-long-enough-000000000")
        self.assertEqual(self.dispatch(token).state,"OUTCOME_UNKNOWN")
    def test_19_dispatch_token_is_one_time_generation(self):
        self.acquire(); old=self.arm().dispatch_token; new=self.arm(msg=b"new message").dispatch_token
        with self.assertRaises(ocf.OwnershipError): self.dispatch(old)
        self.assertEqual(self.dispatch(new).state,"OUTCOME_UNKNOWN")
    def test_20_unknown_blocks_reacquire_forever(self):
        self.acquire(lease_seconds=60); token=self.arm().dispatch_token; self.dispatch(token); self.t.advance(10_000)
        with self.assertRaises(ocf.ClaimConflict): self.acquire(agent_id="other",operation_id="other")
    def test_21_unknown_cannot_release(self):
        self.acquire(); self.dispatch(self.arm().dispatch_token)
        with self.assertRaises(ocf.OwnershipError): self.s.release(target_kind="email",contact=self.kw["contact"],agent_id=self.kw["agent_id"],operation_id=self.kw["operation_id"],reason="no send")
    def test_22_contacted_requires_prior_dispatch(self):
        self.acquire()
        with self.assertRaises(ocf.OwnershipError): self.contacted()

    # 23-30 contact suppression lifecycle
    def test_23_contacted_after_dispatch_records_digest(self):
        self.acquire(); token=self.arm().dispatch_token; self.dispatch(token); r=self.contacted(); self.assertEqual(r.state,"CONTACTED"); record,_=self.t.record(self.s); self.assertEqual(record["contact_count"],1)
    def test_24_contacted_metadata_must_match_arm(self):
        self.acquire(); self.dispatch(self.arm().dispatch_token)
        with self.assertRaises(ocf.ValidationError): self.contacted(channel="slack")
    def test_25_contacted_replay_idempotent_after_expiry(self):
        self.acquire(); self.dispatch(self.arm().dispatch_token); first=self.contacted(); self.t.advance(700); second=self.contacted(); self.assertEqual(first.revision,second.revision)
    def test_26_release_contacted_does_not_shorten_suppression(self):
        self.acquire(); self.dispatch(self.arm().dispatch_token); self.contacted(); self.s.release(target_kind="email",contact=self.kw["contact"],agent_id=self.kw["agent_id"],operation_id=self.kw["operation_id"],reason="handoff")
        with self.assertRaises(ocf.ClaimConflict): self.acquire(agent_id="other",operation_id="other")
        self.t.advance(601); self.assertEqual(self.acquire(agent_id="other",operation_id="other").agent_id,"other")
    def test_27_renew_cannot_shorten_active(self):
        self.acquire(lease_seconds=600); before=self.s.inspect(target_kind="email",contact=self.kw["contact"])["ownership_expires_at"]; self.s.renew(target_kind="email",contact=self.kw["contact"],agent_id=self.kw["agent_id"],operation_id=self.kw["operation_id"],lease_seconds=60); after=self.s.inspect(target_kind="email",contact=self.kw["contact"])["ownership_expires_at"]; self.assertEqual(before,after)
    def test_28_renew_cannot_shorten_contact_suppression(self):
        self.acquire(); self.dispatch(self.arm().dispatch_token); r=self.contacted(cooldown_seconds=600); before=r.contact_not_before; self.s.renew(target_kind="email",contact=self.kw["contact"],agent_id=self.kw["agent_id"],operation_id=self.kw["operation_id"],lease_seconds=60); after=self.s.inspect(target_kind="email",contact=self.kw["contact"]); self.assertEqual(before,after["contact_not_before"])
    def test_29_contact_history_survives_takeover(self):
        self.acquire(); self.dispatch(self.arm().dispatch_token); self.contacted(); self.t.advance(3601); self.acquire(agent_id="other",operation_id="other"); record,_=self.t.record(self.s); self.assertEqual(record["contact_count"],1); self.assertIsNotNone(record["last_message_digest"])
    def test_30_arm_release_before_dispatch_is_safe(self):
        self.acquire(); self.arm(); self.s.release(target_kind="email",contact=self.kw["contact"],agent_id=self.kw["agent_id"],operation_id=self.kw["operation_id"],reason="cancelled pre-send"); self.assertEqual(self.acquire(agent_id="other",operation_id="other").state,"ACTIVE")

    # 31-35 signed reconciliation
    def test_31_unknown_reconcile_requires_key(self):
        s=ocf.GitHubContentsClaimStore(token="token",transport=self.t); self.acquire(); self.dispatch(self.arm().dispatch_token)
        with self.assertRaises(ocf.ValidationError): s.reconcile_unsent(target_kind="email",contact=self.kw["contact"],agent_id=self.kw["agent_id"],operation_id=self.kw["operation_id"],provider_history_digest="a"*64,signature="b"*64)
    def test_32_bad_unsent_signature_rejected(self):
        self.acquire(); self.dispatch(self.arm().dispatch_token)
        with self.assertRaises(ocf.OwnershipError): self.s.reconcile_unsent(target_kind="email",contact=self.kw["contact"],agent_id=self.kw["agent_id"],operation_id=self.kw["operation_id"],provider_history_digest="a"*64,signature="b"*64)
    def test_33_exact_unsent_signature_releases(self):
        self.acquire(); self.dispatch(self.arm().dispatch_token); record,_=self.t.record(self.s); ph="a"*64; sig=ocf.sign_unsent_reconciliation(key=self.key,claim_key=record["claim_key"],record_digest=record["record_digest"],provider_history_digest=ph); r=self.s.reconcile_unsent(target_kind="email",contact=self.kw["contact"],agent_id=self.kw["agent_id"],operation_id=self.kw["operation_id"],provider_history_digest=ph,signature=sig); self.assertEqual(r.state,"RELEASED")
    def test_34_signature_is_generation_bound(self):
        self.acquire(); self.dispatch(self.arm().dispatch_token); record,_=self.t.record(self.s); ph="a"*64; sig=ocf.sign_unsent_reconciliation(key=self.key,claim_key=record["claim_key"],record_digest="0"*64,provider_history_digest=ph)
        with self.assertRaises(ocf.OwnershipError): self.s.reconcile_unsent(target_kind="email",contact=self.kw["contact"],agent_id=self.kw["agent_id"],operation_id=self.kw["operation_id"],provider_history_digest=ph,signature=sig)
    def test_35_reconciled_unsent_can_reassign(self):
        self.acquire(); self.dispatch(self.arm().dispatch_token); record,_=self.t.record(self.s); ph="a"*64; sig=ocf.sign_unsent_reconciliation(key=self.key,claim_key=record["claim_key"],record_digest=record["record_digest"],provider_history_digest=ph); self.s.reconcile_unsent(target_kind="email",contact=self.kw["contact"],agent_id=self.kw["agent_id"],operation_id=self.kw["operation_id"],provider_history_digest=ph,signature=sig); self.assertEqual(self.acquire(agent_id="other",operation_id="other").agent_id,"other")

    # 36-39 record integrity/privacy
    def test_36_record_digest_tamper_fails(self):
        self.acquire(); record,path=self.t.record(self.s); record["agent_id"]="attacker"; self.t.inject(path,record)
        with self.assertRaises(ocf.ProtocolError): self.s.inspect(target_kind="email",contact=self.kw["contact"])
    def test_37_record_authority_tamper_fails_even_resealed(self):
        self.acquire(); record,path=self.t.record(self.s); record["branch"]="evil"; record=ocf._seal_record(record); self.t.inject(path,record)
        with self.assertRaises(ocf.ProtocolError): self.s.inspect(target_kind="email",contact=self.kw["contact"])
    def test_38_unknown_fields_fail_closed(self):
        self.acquire(); record,path=self.t.record(self.s); record["raw_contact"]="lead@example.com"; record=ocf._seal_record(record); self.t.inject(path,record)
        with self.assertRaises(ocf.ProtocolError): self.s.inspect(target_kind="email",contact=self.kw["contact"])
    def test_39_inspect_never_returns_raw_contact(self): self.acquire(); self.assertNotIn("lead@example.com",json.dumps(self.s.inspect(target_kind="email",contact=self.kw["contact"])).lower())

    # 40-42 filesystem / CLI
    def test_40_bounded_regular_file_digest(self):
        with tempfile.NamedTemporaryFile("wb",delete=False) as f: f.write(b"abc"); name=f.name
        try: self.assertEqual(ocf.digest_message_file(name),hashlib.sha256(b"abc").hexdigest())
        finally: os.unlink(name)
    def test_41_symlink_message_file_rejected(self):
        if not hasattr(os,"O_NOFOLLOW"): self.skipTest("platform has no O_NOFOLLOW")
        with tempfile.TemporaryDirectory() as d:
            target=os.path.join(d,"target"); link=os.path.join(d,"link")
            with open(target,"wb") as f: f.write(b"abc")
            os.symlink(target,link)
            with self.assertRaises(ocf.ValidationError): ocf.digest_message_file(link)
    def test_42_cli_has_no_namespace_override_and_json_errors(self):
        stderr=io.StringIO()
        with redirect_stderr(stderr): code=ocf.main(["--api-url","https://evil.example","acquire"])
        self.assertEqual(code,2); self.assertEqual(json.loads(stderr.getvalue())["error"],"ValidationError")


if __name__ == "__main__": unittest.main(verbosity=2)
