from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import inspect
import unittest
from tools.evidence_authority import core
from tools.evidence_authority.codec import AuthorityError, canonical_bytes, loads_strict_json_bytes, sha256_bytes, sha256_value

class KernelTests(unittest.TestCase):
    def material(self, *, record_changes=None, candidate_changes=None, path="provider/receipt.json", max_age=3600):
        now=datetime.now(timezone.utc).replace(microsecond=0)
        record={
            "schema":core.SOURCE_SCHEMA,"record_id":"rec-1","authority_class":"PROVIDER_AUTHENTICATED",
            "issuer":"cognition","subject":"acct-redacted","claim_kind":"MODEL_COST","scope":"MODEL","generation":7,
            "issued_at_utc":core._format_ts(now-timedelta(minutes=2)),"observed_at_utc":core._format_ts(now-timedelta(minutes=1)),
            "valid_until_utc":core._format_ts(now+timedelta(hours=1)),"claim_payload":{"product":"devin","model":"swe-2","amount_minor":0,"currency":"USD"},
        }
        if record_changes: record.update(record_changes)
        raw=canonical_bytes(record)
        manifest={"schema":core.MANIFEST_SCHEMA,"max_age_seconds":max_age,"sources":[{"path":path,"sha256":sha256_bytes(raw)}]}
        manifest_raw=canonical_bytes(manifest);root=sha256_bytes(manifest_raw)
        candidate={
            "schema":core.CANDIDATE_SCHEMA,"record_id":"rec-1","issuer":"cognition","subject":"acct-redacted",
            "claim_kind":"MODEL_COST","scope":"MODEL","generation":7,"claim_payload":{"product":"devin","model":"swe-2","amount_minor":0,"currency":"USD"},
        }
        if candidate_changes: candidate.update(candidate_changes)
        return candidate,manifest_raw,{path:raw},root

    def test_current_positive_is_derived_from_retained_record(self):
        c,m,s,r=self.material();receipt=core.compile_current(c,m,s,r)
        self.assertEqual(receipt["state"],"CURRENT_AUTHORITY")
        self.assertTrue(receipt["current_authority"])
        self.assertEqual(receipt["authority_fact"]["authority_class"],"PROVIDER_AUTHENTICATED")
        self.assertFalse(receipt["external_side_effects_authorized"])
        self.assertEqual(core.verify_receipt(c,m,s,r,receipt),{"integrity_valid":True,"current_authority":False,"external_side_effects_authorized":False})

    def test_candidate_cannot_self_type_authority_or_root(self):
        c,m,s,r=self.material();c["authority_class"]="PROVIDER_AUTHENTICATED"
        with self.assertRaisesRegex(AuthorityError,"keys mismatch"): core.compile_current(c,m,s,r)
        c,m,s,r=self.material();c["authority_root_sha256"]=r
        with self.assertRaisesRegex(AuthorityError,"keys mismatch"): core.compile_current(c,m,s,r)

    def test_source_rewrite_and_self_hash_cannot_keep_pinned_root(self):
        c,m,s,r=self.material();record=loads_strict_json_bytes(next(iter(s.values())))
        record["subject"]="attacker";raw=canonical_bytes(record);path=next(iter(s))
        changed_manifest=canonical_bytes({"schema":core.MANIFEST_SCHEMA,"max_age_seconds":3600,"sources":[{"path":path,"sha256":sha256_bytes(raw)}]})
        with self.assertRaisesRegex(AuthorityError,"pinned root"): core.compile_current(c,changed_manifest,{path:raw},r)

    def test_closed_inventory_rejects_shrink_and_expansion(self):
        c,m,s,r=self.material()
        with self.assertRaisesRegex(AuthorityError,"inventory"): core.compile_current(c,m,{},r)
        extra=dict(s);extra["extra.json"]=b"{}"
        with self.assertRaisesRegex(AuthorityError,"inventory"): core.compile_current(c,m,extra,r)

    def test_path_alias_is_rejected(self):
        c,_,s,_=self.material();raw=next(iter(s.values()))
        m=canonical_bytes({"schema":core.MANIFEST_SCHEMA,"max_age_seconds":3600,"sources":[{"path":"a/../receipt.json","sha256":sha256_bytes(raw)}]})
        with self.assertRaisesRegex(AuthorityError,"aliasing"): core.compile_current(c,m,{"a/../receipt.json":raw},sha256_bytes(m))

    def test_noncanonical_retained_source_is_rejected(self):
        c,_,s,_=self.material();path=next(iter(s));raw=next(iter(s.values()))+b"\n"
        m=canonical_bytes({"schema":core.MANIFEST_SCHEMA,"max_age_seconds":3600,"sources":[{"path":path,"sha256":sha256_bytes(raw)}]})
        with self.assertRaisesRegex(AuthorityError,"not canonical"): core.compile_current(c,m,{path:raw},sha256_bytes(m))

    def test_cross_subject_scope_kind_and_generation_transplant_hold(self):
        for key,value in [("subject","other"),("scope","PRODUCT"),("claim_kind","OTHER"),("generation",8)]:
            c,m,s,r=self.material(candidate_changes={key:value});receipt=core.compile_current(c,m,s,r)
            self.assertEqual(receipt["state"],"HOLD_CLAIM_MISMATCH",key)
            self.assertFalse(receipt["current_authority"])
            self.assertIsNone(receipt["authority_fact"])

    def test_payload_transplant_holds(self):
        c,m,s,r=self.material(candidate_changes={"claim_payload":{"product":"devin","model":"other","amount_minor":0,"currency":"USD"}})
        self.assertEqual(core.compile_current(c,m,s,r)["state"],"HOLD_CLAIM_MISMATCH")

    def test_missing_record_holds(self):
        c,m,s,r=self.material(candidate_changes={"record_id":"missing"})
        self.assertEqual(core.compile_current(c,m,s,r)["state"],"HOLD_RECORD_NOT_FOUND")

    def test_stale_future_expired_never_current(self):
        now=datetime.now(timezone.utc).replace(microsecond=0)
        c,m,s,r=self.material(record_changes={"issued_at_utc":core._format_ts(now-timedelta(hours=3)),"observed_at_utc":core._format_ts(now-timedelta(hours=2)),"valid_until_utc":core._format_ts(now+timedelta(hours=1))},max_age=60)
        self.assertEqual(core.compile_current(c,m,s,r)["state"],"HOLD_STALE")
        c,m,s,r=self.material(record_changes={"issued_at_utc":core._format_ts(now+timedelta(minutes=1)),"observed_at_utc":core._format_ts(now+timedelta(minutes=2)),"valid_until_utc":core._format_ts(now+timedelta(hours=1))})
        self.assertEqual(core.compile_current(c,m,s,r)["state"],"HOLD_FUTURE")
        c,m,s,r=self.material(record_changes={"issued_at_utc":core._format_ts(now-timedelta(hours=2)),"observed_at_utc":core._format_ts(now-timedelta(hours=1)),"valid_until_utc":core._format_ts(now-timedelta(minutes=1))},max_age=7200)
        self.assertEqual(core.compile_current(c,m,s,r)["state"],"HOLD_EXPIRED")

    def test_historical_integrity_never_claims_current(self):
        now=datetime.now(timezone.utc).replace(microsecond=0)
        c,m,s,r=self.material(record_changes={"issued_at_utc":core._format_ts(now-timedelta(days=10)),"observed_at_utc":core._format_ts(now-timedelta(days=10)),"valid_until_utc":core._format_ts(now-timedelta(days=9))},max_age=60)
        hist=core.compile_integrity(c,m,s,r)
        self.assertEqual(hist["state"],"HISTORICAL_AUTHORITY_FACT")
        self.assertFalse(hist["current_authority"])
        self.assertEqual(core.compile_current(c,m,s,r)["state"],"HOLD_EXPIRED")
        self.assertNotIn("now",inspect.signature(core.compile_current).parameters)
        self.assertFalse(hasattr(core,"_compile_at"))

    def test_same_candidate_different_authority_generation_changes_receipt(self):
        c,m,s,r=self.material();old=core.compile_current(c,m,s,r)
        c2,m2,s2,r2=self.material(record_changes={"generation":8})
        new=core.compile_current(c2,m2,s2,r2)
        self.assertNotEqual(old["receipt_sha256"],new["receipt_sha256"])
        self.assertEqual(new["state"],"HOLD_CLAIM_MISMATCH")
        with self.assertRaises(AuthorityError): core.verify_receipt(c,m2,s2,r2,old)

    def test_duplicate_json_huge_int_nonfinite_float_and_surrogate_fail(self):
        for raw in [b'{"a":1,"a":2}', b'{"a":999999999999999999999999999999}', b'{"a":NaN}', b'{"a":1.5}', b'{"a":"\\ud800"}']:
            with self.assertRaises(AuthorityError): loads_strict_json_bytes(raw)

    def test_bool_integer_alias_rejected(self):
        c,m,s,r=self.material(candidate_changes={"generation":True})
        with self.assertRaisesRegex(AuthorityError,"integer"): core.compile_current(c,m,s,r)

    def test_receipt_rehash_cannot_launder_semantic_tamper(self):
        c,m,s,r=self.material();receipt=core.compile_current(c,m,s,r)
        bad=deepcopy(receipt);bad["state"]="HOLD_STALE";bad["current_authority"]=False;bad.pop("receipt_sha256");bad["receipt_sha256"]=sha256_value(bad)
        with self.assertRaisesRegex(AuthorityError,"semantic replay mismatch"): core.verify_receipt(c,m,s,r,bad)

    def test_current_api_captures_source_loader_and_clock_generation(self):
        c,m,s,r=self.material();original_load=core._load_context;original_dt=core._DateTime
        try:
            core._load_context=lambda *a,**k: (_ for _ in ()).throw(RuntimeError("rebound"))
            class FakeClock:
                @classmethod
                def now(cls,tz): return datetime(1970,1,1,tzinfo=timezone.utc)
            core._DateTime=FakeClock
            self.assertEqual(core.compile_current(c,m,s,r)["state"],"CURRENT_AUTHORITY")
        finally:
            core._load_context=original_load;core._DateTime=original_dt

    def test_supported_current_api_captures_policy_helpers_and_hash_generation(self):
        c,m,s,r=self.material();expected=core.compile_current(c,m,s,r)
        names=(
            "_validate_manifest","_validate_source","_validate_candidate","_current_state",
            "_base_receipt","_validate_receipt","_timestamp","_format_ts",
            "sha256_value","canonical_bytes","MAX_TOTAL_SOURCE_BYTES",
            "MANIFEST_SCHEMA","SOURCE_SCHEMA","CANDIDATE_SCHEMA","RECEIPT_SCHEMA",
            "IMPLEMENTATION_CONTRACT","AUTHORITY_CLASSES","SCOPES",
        )
        original={name:getattr(core,name) for name in names}
        def boom(*a,**k): raise RuntimeError("rebound helper")
        try:
            for name in names[:10]: setattr(core,name,boom)
            core.MAX_TOTAL_SOURCE_BYTES=1
            core.MANIFEST_SCHEMA=core.SOURCE_SCHEMA=core.CANDIDATE_SCHEMA=core.RECEIPT_SCHEMA="rebound"
            core.IMPLEMENTATION_CONTRACT="rebound"
            core.AUTHORITY_CLASSES=frozenset()
            core.SCOPES=frozenset()
            actual=core.compile_current(c,m,s,r)
            self.assertEqual(actual,expected)
            self.assertEqual(
                core.verify_receipt(c,m,s,r,actual),
                {"integrity_valid":True,"current_authority":False,"external_side_effects_authorized":False},
            )
        finally:
            for name,value in original.items(): setattr(core,name,value)

    def test_manifest_order_and_duplicate_record_ids_fail(self):
        c,m,s,r=self.material();raw=next(iter(s.values()))
        rows=[{"path":"z.json","sha256":sha256_bytes(raw)},{"path":"a.json","sha256":sha256_bytes(raw)}]
        bad=canonical_bytes({"schema":core.MANIFEST_SCHEMA,"max_age_seconds":3600,"sources":rows})
        with self.assertRaisesRegex(AuthorityError,"sorted"): core.compile_current(c,bad,{"a.json":raw,"z.json":raw},sha256_bytes(bad))
        rows=sorted(rows,key=lambda x:x["path"]);bad=canonical_bytes({"schema":core.MANIFEST_SCHEMA,"max_age_seconds":3600,"sources":rows})
        with self.assertRaisesRegex(AuthorityError,"duplicate authority record_id"): core.compile_current(c,bad,{"a.json":raw,"z.json":raw},sha256_bytes(bad))

    def test_manifest_root_is_not_candidate_controlled(self):
        c,m,s,r=self.material()
        with self.assertRaisesRegex(AuthorityError,"lowercase SHA-256"): core.compile_current(c,m,s,"not-a-root")
        self.assertNotIn("pinned_root_sha256",c)

if __name__=="__main__": unittest.main()
