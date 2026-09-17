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
A = "a" * 64
B = "b" * 64
C = "c" * 64
TEST_KEY_HEX = "31" * 32
TEST_KEY = bytes.fromhex(TEST_KEY_HEX)


def ts(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sign(kind, row):
    unsigned = {k: v for k, v in row.items() if k != "auth_tag_hex"}
    payload = {"domain": "commons-payoff-path-evidence/v1", "kind": kind, "row": unsigned}
    row["auth_tag_hex"] = hmac.new(TEST_KEY, canonical(payload), hashlib.sha256).hexdigest()
    return row


def term(*, cls="BUG_BOUNTY", amount=9000, mode="EXACT", observed=None, valid=None, work="work-1", generation=A, eid="e1", source_sha=B, source_id="source-1"):
    if observed is None:
        observed = NOW - timedelta(hours=1)
    if valid is None:
        valid = NOW + timedelta(days=10)
    row = {
        "evidence_id": eid,
        "subject_work_id": work,
        "subject_generation_sha256": generation,
        "evidence_class": cls,
        "source_id": source_id,
        "source_sha256": source_sha,
        "observed_at_utc": ts(observed),
        "valid_until_utc": None if valid is None else ts(valid),
        "amount_mode": mode,
        "amount_minor": amount if mode == "EXACT" else None,
        "currency": "USD" if mode == "EXACT" else None,
        "auth_tag_hex": "0" * 64,
    }
    return sign("TERM", row)


def outcome(kind, *, work="work-1", generation=A, eid="o1", observed=None, source_id="outcome-source"):
    if observed is None:
        observed = NOW - timedelta(minutes=5)
    row = {
        "event_id": eid,
        "subject_work_id": work,
        "subject_generation_sha256": generation,
        "kind": kind,
        "source_id": source_id,
        "source_sha256": C,
        "observed_at_utc": ts(observed),
        "auth_tag_hex": "0" * 64,
    }
    return sign("OUTCOME", row)


def packet(cls="BUG_BOUNTY"):
    return {
        "schema": core.SCHEMA_INPUT,
        "subject_work_id": "work-1",
        "subject_generation_sha256": A,
        "payoff_class": cls,
        "evidence_scope_status": "COMPLETE",
        "term_evidence": [term(cls=cls)] if cls not in {"STRATEGIC_UNPAID", "PRODUCT_CONVERSION"} else [],
        "outcome_evidence": [],
        "conversion_plan": None,
    }


def plan(review=None, effort=8, milestone="Get explicit buyer discovery acceptance"):
    if review is None:
        review = NOW + timedelta(days=7)
    return {"milestone": milestone, "effort_ceiling_hours": effort, "review_by_utc": ts(review)}


class PayoffPathTests(unittest.TestCase):
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

    def compile(self, p):
        return core._compile_at(p, NOW)

    def test_bug_bounty_exact_is_payoff_bound(self):
        r = self.compile(packet())
        self.assertEqual(r["state"], "PAYOFF_BOUND")
        self.assertEqual(r["evidence_authority_key_fingerprint_sha256"], hashlib.sha256(TEST_KEY).hexdigest())

    def test_paid_work_is_separate_positive_state(self):
        self.assertEqual(self.compile(packet("PAID_WORK"))["state"], "PAID_WORK")

    def test_unknown_compensation_is_not_zero(self):
        p = packet()
        p["term_evidence"] = [term(mode="AMOUNT_UNKNOWN")]
        self.assertEqual(self.compile(p)["state"], "HOLD_UNKNOWN_COMPENSATION")

    def test_generic_project_text_cannot_mint_compensation(self):
        p = packet()
        p["term_evidence"] = [term(cls="GENERIC_CONTEXT")]
        self.assertEqual(self.compile(p)["state"], "HOLD_NO_PAYOFF_PATH")

    def test_relabel_without_host_retag_is_rejected(self):
        p = packet()
        p["term_evidence"][0]["evidence_class"] = "PAID_WORK"
        with self.assertRaises(core.GateError):
            self.compile(p)

    def test_source_remint_without_host_retag_is_rejected(self):
        p = packet()
        p["term_evidence"][0]["source_id"] = "forged-source"
        with self.assertRaises(core.GateError):
            self.compile(p)

    def test_outcome_relabel_without_host_retag_is_rejected(self):
        p = packet()
        row = outcome("ACTIVE_DUPLICATE")
        row["kind"] = "SETTLED"
        p["outcome_evidence"] = [row]
        with self.assertRaises(core.GateError):
            self.compile(p)

    def test_unsigned_external_evidence_is_rejected(self):
        p = packet()
        p["term_evidence"][0]["auth_tag_hex"] = "0" * 64
        with self.assertRaises(core.GateError):
            self.compile(p)

    def test_missing_host_authority_rejects_external_evidence(self):
        p = packet()
        old = os.environ.pop(core.EVIDENCE_AUTH_ENV, None)
        try:
            with self.assertRaises(core.GateError):
                self.compile(p)
        finally:
            if old is not None:
                os.environ[core.EVIDENCE_AUTH_ENV] = old

    def test_product_conversion_requires_cash_or_bounded_plan(self):
        p = packet("PRODUCT_CONVERSION")
        self.assertEqual(self.compile(p)["state"], "HOLD_UNBOUNDED_STRATEGIC")
        p["conversion_plan"] = plan()
        self.assertEqual(self.compile(p)["state"], "PAYOFF_BOUND")

    def test_product_conversion_exact_cash_term(self):
        p = packet("PRODUCT_CONVERSION")
        p["term_evidence"] = [term(cls="PRODUCT_CONVERSION")]
        self.assertEqual(self.compile(p)["state"], "PAYOFF_BOUND")

    def test_product_conversion_unknown_cash_does_not_fall_through_plan(self):
        p = packet("PRODUCT_CONVERSION")
        p["term_evidence"] = [term(cls="PRODUCT_CONVERSION", mode="AMOUNT_UNKNOWN")]
        p["conversion_plan"] = plan()
        self.assertEqual(self.compile(p)["state"], "HOLD_UNKNOWN_COMPENSATION")

    def test_strategic_unpaid_requires_bounded_plan_without_host_key(self):
        p = packet("STRATEGIC_UNPAID")
        self.assertEqual(self.compile(p)["state"], "HOLD_UNBOUNDED_STRATEGIC")
        p["conversion_plan"] = plan()
        old = os.environ.pop(core.EVIDENCE_AUTH_ENV, None)
        try:
            r = self.compile(p)
            self.assertEqual(r["state"], "STRATEGIC_UNPAID_BOUNDED")
            self.assertIsNone(r["evidence_authority_key_fingerprint_sha256"])
        finally:
            if old is not None:
                os.environ[core.EVIDENCE_AUTH_ENV] = old

    def test_zero_negative_and_bool_effort_rejected(self):
        for value in (0, -1, True):
            p = packet("STRATEGIC_UNPAID")
            p["conversion_plan"] = plan(effort=value)
            with self.assertRaises(core.GateError):
                self.compile(p)

    def test_expiry_boundary_holds(self):
        p = packet("STRATEGIC_UNPAID")
        p["conversion_plan"] = plan(review=NOW)
        self.assertEqual(self.compile(p)["state"], "HOLD_EXPIRED")

    def test_settled_dominates_attractive_terms(self):
        p = packet()
        p["outcome_evidence"] = [outcome("SETTLED")]
        self.assertEqual(self.compile(p)["state"], "HOLD_ALREADY_SETTLED")

    def test_duplicate_dominates_attractive_terms(self):
        p = packet()
        p["outcome_evidence"] = [outcome("ACTIVE_DUPLICATE")]
        self.assertEqual(self.compile(p)["state"], "HOLD_ACTIVE_DUPLICATE")

    def test_settled_dominates_duplicate(self):
        p = packet()
        p["outcome_evidence"] = [outcome("ACTIVE_DUPLICATE", eid="o1"), outcome("SETTLED", eid="o2")]
        self.assertEqual(self.compile(p)["state"], "HOLD_ALREADY_SETTLED")

    def test_subject_transplant_retagged_is_conflict(self):
        p = packet()
        p["term_evidence"] = [term(work="work-2")]
        self.assertEqual(self.compile(p)["state"], "HOLD_EVIDENCE_CONFLICT")

    def test_generation_transplant_retagged_is_conflict(self):
        p = packet()
        p["term_evidence"] = [term(generation=B)]
        self.assertEqual(self.compile(p)["state"], "HOLD_EVIDENCE_CONFLICT")

    def test_wrong_specific_class_retagged_is_conflict(self):
        p = packet()
        p["term_evidence"] = [term(cls="COMPETITION_PRIZE")]
        self.assertEqual(self.compile(p)["state"], "HOLD_EVIDENCE_CONFLICT")

    def test_future_evidence_is_conflict(self):
        p = packet()
        p["term_evidence"] = [term(observed=NOW + timedelta(seconds=1))]
        self.assertEqual(self.compile(p)["state"], "HOLD_EVIDENCE_CONFLICT")

    def test_stale_evidence_holds(self):
        p = packet()
        p["term_evidence"] = [term(observed=NOW - timedelta(days=91), valid=NOW + timedelta(days=1))]
        self.assertEqual(self.compile(p)["state"], "HOLD_STALE")

    def test_term_expiry_boundary_holds(self):
        p = packet()
        p["term_evidence"] = [term(valid=NOW)]
        self.assertEqual(self.compile(p)["state"], "HOLD_EXPIRED")

    def test_partial_scope_holds(self):
        p = packet()
        p["evidence_scope_status"] = "PARTIAL"
        self.assertEqual(self.compile(p)["state"], "HOLD_INCOMPLETE_EVIDENCE")

    def test_conflicting_exact_terms_hold(self):
        p = packet()
        p["term_evidence"] = [term(eid="e1", amount=9000), term(eid="e2", amount=10000, source_sha=C)]
        self.assertEqual(self.compile(p)["state"], "HOLD_EVIDENCE_CONFLICT")

    def test_unknown_plus_exact_terms_hold_conflict(self):
        p = packet()
        p["term_evidence"] = [term(eid="e1"), term(eid="e2", mode="AMOUNT_UNKNOWN", source_sha=C)]
        self.assertEqual(self.compile(p)["state"], "HOLD_EVIDENCE_CONFLICT")

    def test_authenticated_source_remint_changes_receipt_generation(self):
        p1 = packet()
        p2 = copy.deepcopy(p1)
        p2["term_evidence"] = [term(source_sha=C)]
        r1 = self.compile(p1)
        r2 = self.compile(p2)
        self.assertNotEqual(r1["input_digest_sha256"], r2["input_digest_sha256"])
        self.assertNotEqual(r1["receipt_digest_sha256"], r2["receipt_digest_sha256"])

    def test_receipt_tamper_fails(self):
        p = packet()
        r = self.compile(p)
        r["state"] = "PAID_WORK"
        with self.assertRaises(core.GateError):
            core.verify_integrity(p, r)

    def test_authority_bool_int_alias_rejected_even_if_resealed(self):
        p = packet()
        r = self.compile(p)
        r["authority"]["cash_receipt_proven"] = 0
        unsigned = dict(r)
        unsigned.pop("receipt_digest_sha256")
        r["receipt_digest_sha256"] = hashlib.sha256(canonical(unsigned)).hexdigest()
        with self.assertRaises(core.GateError):
            core.verify_integrity(p, r)

    def test_module_authority_name_cannot_mint(self):
        p = packet()
        core._AUTHORITY = {"cash_receipt_proven": True}
        try:
            r = self.compile(p)
            self.assertFalse(any(r["authority"].values()))
        finally:
            del core._AUTHORITY

    def test_cross_work_receipt_fails(self):
        p = packet()
        r = self.compile(p)
        p2 = copy.deepcopy(p)
        p2["subject_work_id"] = "work-2"
        p2["term_evidence"] = [term(work="work-2")]
        self.assertFalse(core.verify_integrity(p2, r))

    def test_integrity_and_current_verification(self):
        p = packet()
        r = self.compile(p)
        self.assertTrue(core.verify_integrity(p, r))
        self.assertTrue(core._verify_current_at(p, r, NOW + timedelta(hours=1)))
        self.assertFalse(core._verify_current_at(p, r, NOW + timedelta(days=11)))

    def test_compile_trust_chain_ignores_validate_packet_rebind(self):
        p = packet()
        original = core._validate_packet
        core._validate_packet = lambda value: (value, None)
        try:
            self.assertEqual(core.compile_current(p)["state"], "PAYOFF_BOUND")
        finally:
            core._validate_packet = original

    def test_compile_trust_chain_ignores_verify_tag_rebind(self):
        p = packet()
        p["term_evidence"][0]["source_id"] = "forged-source"
        original = core._verify_evidence_tag
        core._verify_evidence_tag = lambda *args, **kwargs: None
        try:
            with self.assertRaises(core.GateError):
                core.compile_current(p)
        finally:
            core._verify_evidence_tag = original

    def test_integrity_trust_chain_ignores_compile_at_rebind(self):
        p = packet()
        r = self.compile(p)
        forged = copy.deepcopy(r)
        forged["state"] = "PAID_WORK"
        unsigned = dict(forged)
        unsigned.pop("receipt_digest_sha256")
        forged["receipt_digest_sha256"] = hashlib.sha256(canonical(unsigned)).hexdigest()
        original = core._compile_at
        core._compile_at = lambda *_args, **_kwargs: forged
        try:
            self.assertFalse(core.verify_integrity(p, forged))
        finally:
            core._compile_at = original

    def test_public_clock_ignores_injected_now_name(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        p = packet("STRATEGIC_UNPAID")
        p["conversion_plan"] = plan(review=now - timedelta(seconds=1))
        core._NOW = lambda: datetime(2000, 1, 1, tzinfo=timezone.utc)
        try:
            self.assertEqual(core.compile_current(p)["state"], "HOLD_EXPIRED")
        finally:
            del core._NOW

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(core.GateError):
            core.loads_strict_json('{"a":1,"a":2}')

    def test_float_and_nonfinite_rejected(self):
        for raw in ('{"a":1.0}', '{"a":NaN}', '{"a":Infinity}'):
            with self.assertRaises(core.GateError):
                core.loads_strict_json(raw)

    def test_giant_int_rejected(self):
        with self.assertRaises(core.GateError):
            core.loads_strict_json('{"a":999999999999999999999999999999999999999}')

    def test_lone_surrogate_rejected(self):
        with self.assertRaises(core.GateError):
            core.loads_strict_json('{"a":"\\ud800"}')

    def test_bool_as_amount_rejected(self):
        p = packet()
        row = term()
        row["amount_minor"] = True
        row = sign("TERM", row)
        p["term_evidence"] = [row]
        with self.assertRaises(core.GateError):
            self.compile(p)

    def test_container_subclass_rejected(self):
        class D(dict):
            pass
        with self.assertRaises(core.GateError):
            core.compile_current(D(packet()))

    def test_authority_ceiling_is_all_false(self):
        r = self.compile(packet())
        self.assertTrue(r["authority"])
        self.assertFalse(any(r["authority"].values()))

    def test_cli_create_exclusive_and_verify(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        p = packet("STRATEGIC_UNPAID")
        p["conversion_plan"] = plan(review=now + timedelta(days=1))
        with tempfile.TemporaryDirectory() as td:
            packet_path = os.path.join(td, "packet.json")
            receipt_path = os.path.join(td, "receipt.json")
            with open(packet_path, "w", encoding="utf-8") as f:
                json.dump(p, f)
            self.assertEqual(cli_main(["compile", packet_path, "--out", receipt_path]), 0)
            self.assertEqual(cli_main(["compile", packet_path, "--out", receipt_path]), 2)
            self.assertEqual(cli_main(["verify-integrity", packet_path, receipt_path]), 0)
            self.assertEqual(cli_main(["verify-current", packet_path, receipt_path]), 0)


if __name__ == "__main__":
    unittest.main()
