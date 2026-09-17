import copy
import hashlib
import hmac
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from revenue.payoff_path_ledger import core
from revenue.payoff_path_ledger.cli import main as cli_main

NOW = datetime(2026, 9, 17, 20, 30, 0, tzinfo=timezone.utc)
A, B, C = "a" * 64, "b" * 64, "c" * 64
TEST_KEY_HEX = "31" * 32
TEST_KEY = bytes.fromhex(TEST_KEY_HEX)


def ts(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sign(kind, row):
    unsigned = {k: v for k, v in row.items() if k != "auth_tag_hex"}
    payload = {"domain": "commons-payoff-path-evidence/v2", "kind": kind, "row": unsigned}
    row["auth_tag_hex"] = hmac.new(TEST_KEY, canonical(payload), hashlib.sha256).hexdigest()
    return row


def term(*, cls="BUG_BOUNTY", amount=9000, mode="EXACT", observed=None, valid=None, work="work-1", generation=A, eid="e1", source_sha=B, source_id="terms-source"):
    observed = NOW - timedelta(hours=1) if observed is None else observed
    valid = NOW + timedelta(days=10) if valid is None else valid
    return sign("TERM", {
        "evidence_id": eid,
        "subject_work_id": work,
        "subject_generation_sha256": generation,
        "evidence_class": cls,
        "source_id": source_id,
        "source_sha256": source_sha,
        "observed_at_utc": ts(observed),
        "valid_until_utc": None if valid is False else ts(valid),
        "amount_mode": mode,
        "amount_minor": amount if mode == "EXACT" else None,
        "currency": "USD" if mode == "EXACT" else None,
        "auth_tag_hex": "0" * 64,
    })


def outcome(kind, *, work="work-1", generation=A, eid="o1", observed=None, source_id="outcome-source"):
    observed = NOW - timedelta(minutes=5) if observed is None else observed
    return sign("OUTCOME", {
        "event_id": eid,
        "subject_work_id": work,
        "subject_generation_sha256": generation,
        "kind": kind,
        "source_id": source_id,
        "source_sha256": C,
        "observed_at_utc": ts(observed),
        "auth_tag_hex": "0" * 64,
    })


def plan(review=None, effort=8, milestone="Get explicit buyer discovery acceptance"):
    review = NOW + timedelta(days=7) if review is None else review
    return {"milestone": milestone, "effort_ceiling_hours": effort, "review_by_utc": ts(review)}


def packet(cls="BUG_BOUNTY", *, complete=True):
    p = {
        "schema": core.SCHEMA_INPUT,
        "subject_work_id": "work-1",
        "subject_generation_sha256": A,
        "payoff_class": cls,
        "evidence_scope_status": "COMPLETE" if complete else "PARTIAL",
        "scope_attestation": None,
        "term_evidence": [term(cls=cls)] if cls not in {"STRATEGIC_UNPAID", "PRODUCT_CONVERSION"} else [],
        "outcome_evidence": [],
        "conversion_plan": None,
    }
    if complete:
        refresh_scope(p)
    return p


def refresh_scope(p, *, observed=None, valid=None, source_id="census-source", source_sha=C):
    observed = NOW - timedelta(minutes=2) if observed is None else observed
    valid = NOW + timedelta(hours=6) if valid is None else valid
    census = hashlib.sha256(canonical({"term_evidence": p["term_evidence"], "outcome_evidence": p["outcome_evidence"]})).hexdigest()
    p["evidence_scope_status"] = "COMPLETE"
    p["scope_attestation"] = sign("SCOPE", {
        "attestation_id": "scope-1",
        "subject_work_id": p["subject_work_id"],
        "subject_generation_sha256": p["subject_generation_sha256"],
        "census_source_id": source_id,
        "census_source_sha256": source_sha,
        "evidence_census_sha256": census,
        "observed_at_utc": ts(observed),
        "valid_until_utc": ts(valid),
        "auth_tag_hex": "0" * 64,
    })
    return p


class PayoffPathV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_key = os.environ.get(core.EVIDENCE_AUTH_ENV)
        os.environ[core.EVIDENCE_AUTH_ENV] = TEST_KEY_HEX

    @classmethod
    def tearDownClass(cls):
        if cls.old_key is None:
            os.environ.pop(core.EVIDENCE_AUTH_ENV, None)
        else:
            os.environ[core.EVIDENCE_AUTH_ENV] = cls.old_key

    def compile(self, p, now=NOW):
        return core._compile_at(p, now)

    def test_01_bounty_positive_requires_authenticated_scope(self):
        r = self.compile(packet())
        self.assertEqual(r["state"], "PAYOFF_BOUND")
        self.assertIsNotNone(r["scope_attestation_fingerprint_sha256"])

    def test_02_paid_work_positive(self):
        self.assertEqual(self.compile(packet("PAID_WORK"))["state"], "PAID_WORK")

    def test_03_unknown_compensation_not_zero(self):
        p = packet(); p["term_evidence"] = [term(mode="AMOUNT_UNKNOWN")]; refresh_scope(p)
        self.assertEqual(self.compile(p)["state"], "HOLD_UNKNOWN_COMPENSATION")

    def test_04_generic_context_cannot_mint_compensation(self):
        p = packet(); p["term_evidence"] = [term(cls="GENERIC_CONTEXT")]; refresh_scope(p)
        self.assertEqual(self.compile(p)["state"], "HOLD_NO_PAYOFF_PATH")

    def test_05_partial_scope_holds(self):
        p = packet(complete=False); p["term_evidence"] = [term()]
        self.assertEqual(self.compile(p)["state"], "HOLD_INCOMPLETE_EVIDENCE")

    def test_06_complete_missing_scope_attestation_holds(self):
        p = packet(); p["scope_attestation"] = None
        self.assertEqual(self.compile(p)["state"], "HOLD_INCOMPLETE_EVIDENCE")

    def test_07_scope_tag_forgery_holds(self):
        p = packet(); p["scope_attestation"]["auth_tag_hex"] = "0" * 64
        self.assertEqual(self.compile(p)["state"], "HOLD_INCOMPLETE_EVIDENCE")

    def test_08_settled_omission_invalidates_scope(self):
        p = packet(); p["outcome_evidence"] = [outcome("SETTLED")]; refresh_scope(p)
        self.assertEqual(self.compile(p)["state"], "HOLD_ALREADY_SETTLED")
        p["outcome_evidence"] = []
        self.assertEqual(self.compile(p)["state"], "HOLD_INCOMPLETE_EVIDENCE")

    def test_09_duplicate_omission_invalidates_scope(self):
        p = packet(); p["outcome_evidence"] = [outcome("ACTIVE_DUPLICATE")]; refresh_scope(p)
        self.assertEqual(self.compile(p)["state"], "HOLD_ACTIVE_DUPLICATE")
        p["outcome_evidence"] = []
        self.assertEqual(self.compile(p)["state"], "HOLD_INCOMPLETE_EVIDENCE")

    def test_10_conflicting_term_omission_invalidates_scope(self):
        p = packet(); p["term_evidence"] = [term(eid="e1", amount=9000), term(eid="e2", amount=10000, source_sha=C)]; refresh_scope(p)
        self.assertEqual(self.compile(p)["state"], "HOLD_EVIDENCE_CONFLICT")
        p["term_evidence"] = [p["term_evidence"][0]]
        self.assertEqual(self.compile(p)["state"], "HOLD_INCOMPLETE_EVIDENCE")

    def test_11_scope_subject_transplant_holds(self):
        p = packet(); p["scope_attestation"]["subject_work_id"] = "work-2"; p["scope_attestation"] = sign("SCOPE", p["scope_attestation"])
        self.assertEqual(self.compile(p)["state"], "HOLD_INCOMPLETE_EVIDENCE")

    def test_12_scope_expiry_holds_incomplete(self):
        p = packet(); refresh_scope(p, valid=NOW)
        self.assertEqual(self.compile(p)["state"], "HOLD_INCOMPLETE_EVIDENCE")

    def test_13_scope_future_holds_incomplete(self):
        p = packet(); refresh_scope(p, observed=NOW + timedelta(seconds=1), valid=NOW + timedelta(hours=1))
        self.assertEqual(self.compile(p)["state"], "HOLD_INCOMPLETE_EVIDENCE")

    def test_14_missing_host_key_rejects_external_rows(self):
        p = packet(); old = os.environ.pop(core.EVIDENCE_AUTH_ENV, None)
        try:
            with self.assertRaises(core.GateError): self.compile(p)
        finally:
            if old is not None: os.environ[core.EVIDENCE_AUTH_ENV] = old

    def test_15_missing_host_key_plan_only_complete_holds(self):
        p = packet("STRATEGIC_UNPAID"); p["conversion_plan"] = plan(); refresh_scope(p)
        old = os.environ.pop(core.EVIDENCE_AUTH_ENV, None)
        try:
            self.assertEqual(self.compile(p)["state"], "HOLD_INCOMPLETE_EVIDENCE")
        finally:
            if old is not None: os.environ[core.EVIDENCE_AUTH_ENV] = old

    def test_16_term_relabel_without_retag_rejected(self):
        p = packet(); p["term_evidence"][0]["evidence_class"] = "PAID_WORK"
        with self.assertRaises(core.GateError): self.compile(p)

    def test_17_source_remint_without_retag_rejected(self):
        p = packet(); p["term_evidence"][0]["source_id"] = "forged"
        with self.assertRaises(core.GateError): self.compile(p)

    def test_18_settled_dominates_with_valid_scope(self):
        p = packet(); p["outcome_evidence"] = [outcome("SETTLED")]; refresh_scope(p)
        self.assertEqual(self.compile(p)["state"], "HOLD_ALREADY_SETTLED")

    def test_19_duplicate_dominates_with_valid_scope(self):
        p = packet(); p["outcome_evidence"] = [outcome("ACTIVE_DUPLICATE")]; refresh_scope(p)
        self.assertEqual(self.compile(p)["state"], "HOLD_ACTIVE_DUPLICATE")

    def test_20_strategic_bounded_requires_scope(self):
        p = packet("STRATEGIC_UNPAID"); p["conversion_plan"] = plan(); refresh_scope(p)
        self.assertEqual(self.compile(p)["state"], "STRATEGIC_UNPAID_BOUNDED")

    def test_21_product_conversion_plan_requires_scope(self):
        p = packet("PRODUCT_CONVERSION"); p["conversion_plan"] = plan(); refresh_scope(p)
        self.assertEqual(self.compile(p)["state"], "PAYOFF_BOUND")

    def test_22_plan_expiry(self):
        p = packet("STRATEGIC_UNPAID"); p["conversion_plan"] = plan(review=NOW); refresh_scope(p)
        self.assertEqual(self.compile(p)["state"], "HOLD_EXPIRED")

    def test_23_unbounded_strategic_with_valid_scope(self):
        p = packet("STRATEGIC_UNPAID"); refresh_scope(p)
        self.assertEqual(self.compile(p)["state"], "HOLD_UNBOUNDED_STRATEGIC")

    def test_24_direct_object_depth_bound(self):
        value = 0
        for _ in range(core.MAX_JSON_DEPTH + 2): value = [value]
        with self.assertRaises(core.GateError): core._freeze_json(value)

    def test_25_raw_json_depth_bound(self):
        raw = "[" * (core.MAX_JSON_DEPTH + 2) + "0" + "]" * (core.MAX_JSON_DEPTH + 2)
        with self.assertRaises(core.GateError): core.loads_strict_json(raw)

    def test_26_node_budget(self):
        value = [[0] * 220 for _ in range(20)]
        with self.assertRaises(core.GateError): core._freeze_json(value)

    def test_27_duplicate_json_key(self):
        with self.assertRaises(core.GateError): core.loads_strict_json('{"a":1,"a":2}')

    def test_28_float_nonfinite(self):
        for raw in ('{"a":1.0}', '{"a":NaN}', '{"a":Infinity}'):
            with self.assertRaises(core.GateError): core.loads_strict_json(raw)

    def test_29_giant_int(self):
        with self.assertRaises(core.GateError): core.loads_strict_json('{"a":999999999999999999999999999999999}')

    def test_30_lone_surrogate(self):
        with self.assertRaises(core.GateError): core.loads_strict_json('{"a":"\\ud800"}')

    def test_31_container_subclass(self):
        class D(dict): pass
        with self.assertRaises(core.GateError): core.compile_current(D(packet()))

    def test_32_bool_amount_rejected_even_retagged(self):
        p = packet(); row = term(); row["amount_minor"] = True; row = sign("TERM", row); p["term_evidence"] = [row]; refresh_scope(p)
        with self.assertRaises(core.GateError): self.compile(p)

    def test_33_authority_all_exact_false(self):
        r = self.compile(packet())
        self.assertTrue(r["authority"])
        self.assertTrue(all(type(v) is bool and v is False for v in r["authority"].values()))

    def test_34_receipt_tamper_fails(self):
        p = packet(); r = self.compile(p); r["state"] = "PAID_WORK"
        with self.assertRaises(core.GateError): core.verify_integrity(p, r)

    def test_35_authority_int_alias_rejected_resealed(self):
        p = packet(); r = self.compile(p); r["authority"]["cash_receipt_proven"] = 0
        unsigned = dict(r); unsigned.pop("receipt_digest_sha256")
        r["receipt_digest_sha256"] = hashlib.sha256(canonical(unsigned)).hexdigest()
        with self.assertRaises(core.GateError): core.verify_integrity(p, r)

    def test_36_now_name_injection_inert(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        p = packet("STRATEGIC_UNPAID"); p["conversion_plan"] = {"milestone":"m", "effort_ceiling_hours":1, "review_by_utc":ts(now - timedelta(seconds=1))}
        p["term_evidence"] = []; p["outcome_evidence"] = []
        obs = now - timedelta(seconds=5); valid = now + timedelta(hours=1)
        census = hashlib.sha256(canonical({"term_evidence":[],"outcome_evidence":[]})).hexdigest()
        p["scope_attestation"] = sign("SCOPE", {"attestation_id":"scope-now","subject_work_id":"work-1","subject_generation_sha256":A,"census_source_id":"census","census_source_sha256":C,"evidence_census_sha256":census,"observed_at_utc":ts(obs),"valid_until_utc":ts(valid),"auth_tag_hex":"0"*64})
        core._NOW = lambda: datetime(2000,1,1,tzinfo=timezone.utc)
        try: self.assertEqual(core.compile_current(p)["state"], "HOLD_EXPIRED")
        finally: del core._NOW

    def test_37_authority_name_injection_inert(self):
        core._AUTHORITY = {"cash_receipt_proven": True}
        try: self.assertFalse(any(self.compile(packet())["authority"].values()))
        finally: del core._AUTHORITY

    def test_38_validate_packet_rebind_inert_public_compile(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        p = packet("STRATEGIC_UNPAID"); p["conversion_plan"] = {"milestone":"m","effort_ceiling_hours":1,"review_by_utc":ts(now+timedelta(hours=1))}
        p["term_evidence"]=[]; p["outcome_evidence"]=[]
        census=hashlib.sha256(canonical({"term_evidence":[],"outcome_evidence":[]})).hexdigest()
        p["scope_attestation"]=sign("SCOPE",{"attestation_id":"scope-x","subject_work_id":"work-1","subject_generation_sha256":A,"census_source_id":"census","census_source_sha256":C,"evidence_census_sha256":census,"observed_at_utc":ts(now-timedelta(seconds=5)),"valid_until_utc":ts(now+timedelta(hours=1)),"auth_tag_hex":"0"*64})
        original = core._validate_packet; core._validate_packet = lambda *a, **k: (p,None,True,[])
        try: self.assertEqual(core.compile_current(p)["state"], "STRATEGIC_UNPAID_BOUNDED")
        finally: core._validate_packet = original

    def test_39_verify_tag_rebind_inert(self):
        p = packet(); p["term_evidence"][0]["source_id"] = "forged"
        original = core._verify_evidence_tag; core._verify_evidence_tag = lambda *a, **k: None
        try:
            with self.assertRaises(core.GateError): core.compile_current(p)
        finally: core._verify_evidence_tag = original

    def test_40_compile_at_rebind_inert_integrity(self):
        p = packet(); r = self.compile(p); forged = copy.deepcopy(r); forged["state"] = "PAID_WORK"
        unsigned = dict(forged); unsigned.pop("receipt_digest_sha256"); forged["receipt_digest_sha256"] = hashlib.sha256(canonical(unsigned)).hexdigest()
        original = core._compile_at; core._compile_at = lambda *a, **k: forged
        try: self.assertFalse(core.verify_integrity(p, forged))
        finally: core._compile_at = original

    def test_41_current_verification_scope_expiry(self):
        p = packet(); refresh_scope(p, valid=NOW + timedelta(hours=1)); r = self.compile(p)
        self.assertTrue(core._verify_current_at(p, r, NOW + timedelta(minutes=30)))
        self.assertFalse(core._verify_current_at(p, r, NOW + timedelta(hours=2)))

    def test_42_subject_transplant_retagged_conflicts(self):
        p = packet(); p["term_evidence"] = [term(work="work-2")]; refresh_scope(p)
        self.assertEqual(self.compile(p)["state"], "HOLD_EVIDENCE_CONFLICT")

    def test_43_generation_transplant_retagged_conflicts(self):
        p = packet(); p["term_evidence"] = [term(generation=B)]; refresh_scope(p)
        self.assertEqual(self.compile(p)["state"], "HOLD_EVIDENCE_CONFLICT")

    def test_44_conflicting_economics(self):
        p = packet(); p["term_evidence"]=[term(eid="e1",amount=9000),term(eid="e2",amount=10000,source_sha=C)]; refresh_scope(p)
        self.assertEqual(self.compile(p)["state"], "HOLD_EVIDENCE_CONFLICT")

    def test_45_unknown_plus_exact_conflict(self):
        p = packet(); p["term_evidence"]=[term(eid="e1"),term(eid="e2",mode="AMOUNT_UNKNOWN",source_sha=C)]; refresh_scope(p)
        self.assertEqual(self.compile(p)["state"], "HOLD_EVIDENCE_CONFLICT")

    def test_46_scope_source_change_without_retag_holds(self):
        p = packet(); p["scope_attestation"]["census_source_id"] = "other-census"
        self.assertEqual(self.compile(p)["state"], "HOLD_INCOMPLETE_EVIDENCE")

    def test_47_partial_scope_attestation_structural_conflict_rejected(self):
        p = packet(); p["evidence_scope_status"] = "PARTIAL"
        with self.assertRaises(core.GateError): self.compile(p)

    def test_48_invalid_host_key_rejected(self):
        p = packet(); old=os.environ.get(core.EVIDENCE_AUTH_ENV); os.environ[core.EVIDENCE_AUTH_ENV]="BAD"
        try:
            with self.assertRaises(core.GateError): self.compile(p)
        finally: os.environ[core.EVIDENCE_AUTH_ENV]=old

    def test_49_order_change_invalidates_scope_generation(self):
        p=packet(); p["term_evidence"]=[term(eid="e1"),term(eid="e2",source_sha=C)]; refresh_scope(p); p["term_evidence"].reverse()
        self.assertEqual(self.compile(p)["state"], "HOLD_INCOMPLETE_EVIDENCE")

    def test_50_cli_create_verify_plan_only(self):
        now=datetime.now(timezone.utc).replace(microsecond=0)
        p=packet("STRATEGIC_UNPAID"); p["term_evidence"]=[]; p["outcome_evidence"]=[]; p["conversion_plan"]={"milestone":"m","effort_ceiling_hours":1,"review_by_utc":ts(now+timedelta(hours=1))}
        census=hashlib.sha256(canonical({"term_evidence":[],"outcome_evidence":[]})).hexdigest()
        p["scope_attestation"]=sign("SCOPE",{"attestation_id":"scope-cli","subject_work_id":"work-1","subject_generation_sha256":A,"census_source_id":"census","census_source_sha256":C,"evidence_census_sha256":census,"observed_at_utc":ts(now-timedelta(seconds=5)),"valid_until_utc":ts(now+timedelta(hours=1)),"auth_tag_hex":"0"*64})
        with tempfile.TemporaryDirectory() as td:
            pp=os.path.join(td,"p.json"); rp=os.path.join(td,"r.json")
            with open(pp,"w",encoding="utf-8") as f: json.dump(p,f)
            self.assertEqual(cli_main(["compile",pp,"--out",rp]),0)
            self.assertEqual(cli_main(["compile",pp,"--out",rp]),2)
            self.assertEqual(cli_main(["verify-integrity",pp,rp]),0)
            self.assertEqual(cli_main(["verify-current",pp,rp]),0)


if __name__ == "__main__":
    unittest.main()
