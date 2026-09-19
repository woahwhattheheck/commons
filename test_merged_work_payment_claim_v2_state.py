from __future__ import annotations
import copy, json, os, tempfile, unittest
from datetime import datetime
from pathlib import Path
from unittest import mock
from revenue.merged_work_payment_claim import compiler_v2 as compiler
from revenue.merged_work_payment_claim import codec_v2 as codec
from revenue.merged_work_payment_claim.output_v2 import publish
from merged_work_payment_claim_v2_test_support import Base, NOW, ready_doc

class Tests(Base):
    def test_ready_current_process_clock(self):
            report,md,receipt=self.current(); self.assertEqual(report["state"],"READY_FOR_MUSE_PAYMENT_REQUEST"); self.assertEqual(report["evaluation_at"],NOW); self.assertEqual(report["mode"],"CURRENT"); self.assertIsNone(report["payment_request"]["recipient"]); self.assertTrue(all(v is False for v in report["authority"].values())); self.assertTrue(__import__("revenue.merged_work_payment_claim.verify_v2",fromlist=["verify_artifacts"]).verify_artifacts(ready_doc(),report,md,receipt))
    def test_replay_never_ready(self):
            report,_,_=compiler.compile_replay(ready_doc(),NOW); self.assertEqual(report["state"],"HOLD_STALE"); self.assertIn("historical_replay_non_authorizing",report["blockers"])
    def test_normalize_precedes_clock(self):
            bad=ready_doc(); bad["work"]["pr_number"]=True
            class Boom(datetime):
                @classmethod
                def now(cls,tz=None): raise AssertionError("clock sampled too early")
            with mock.patch.object(compiler,"datetime",Boom):
                with self.assertRaises(codec.ClaimError): compiler.compile_current(bad)
    def test_no_compensation(self):
            d=ready_doc(); d["compensation"]=[]; self.assertEqual(self.state(d),"HOLD_NO_COMPENSATION_EVIDENCE")
    def test_empty_terms_is_no_compensation(self):
            d=ready_doc(); d["compensation"][0].update(currency=None,amount_minor=None,terms_text=None); self.assertEqual(self.state(d),"HOLD_NO_COMPENSATION_EVIDENCE")
    def test_no_acceptance(self):
            d=ready_doc(); d["acceptance"]=None; self.assertEqual(self.state(d),"HOLD_NO_ACCEPTANCE_EVIDENCE")
    def test_payment_unknown(self):
            d=ready_doc(); d["payment_status"].update(status="UNKNOWN",provenance_class="UNKNOWN"); self.assertEqual(self.state(d),"HOLD_PAYMENT_STATUS_UNKNOWN")
    def test_unpaid_unknown_provenance(self):
            d=ready_doc(); d["payment_status"]["provenance_class"]="UNKNOWN"; self.assertEqual(self.state(d),"HOLD_PAYMENT_STATUS_UNKNOWN")
    def test_paid_dominates_missing_acceptance(self):
            d=ready_doc(); d["acceptance"]=None; d["payment_status"].update(status="PAID",paid_amount_minor=9000,payment_ref="provider:p1"); self.assertEqual(self.state(d),"HOLD_ALREADY_PAID")
    def test_eligibility_missing(self):
            d=ready_doc(); d["eligibility"]=None; self.assertEqual(self.state(d),"HOLD_INCOMPLETE_EVIDENCE")
    def test_ineligible(self):
            d=ready_doc(); d["eligibility"]["status"]="INELIGIBLE"; self.assertEqual(self.state(d),"HOLD_INELIGIBLE")
    def test_compensation_conflict(self):
            d=ready_doc(); x=copy.deepcopy(d["compensation"][0]); x["offer_id"]="offer-43"; x["source_sha256"]="8"*64; d["compensation"].append(x); self.assertEqual(self.state(d),"HOLD_EVIDENCE_CONFLICT")
    def test_supersession_selects_latest(self):
            d=ready_doc(); x=copy.deepcopy(d["compensation"][0]); x.update(offer_id="offer-43",source_sha256="8"*64,advertised_at="2026-09-11T12:00:00Z",supersedes_offer_id="offer-42"); d["compensation"].append(x); r,_,_=self.current(d); self.assertEqual(r["state"],"READY_FOR_MUSE_PAYMENT_REQUEST"); self.assertEqual(r["payment_request"]["offer_id"],"offer-43")
    def test_supersession_cycle_holds(self):
            d=ready_doc(); d["compensation"][0]["supersedes_offer_id"]="offer-43"; x=copy.deepcopy(d["compensation"][0]); x.update(offer_id="offer-43",supersedes_offer_id="offer-42",source_sha256="8"*64); d["compensation"].append(x); self.assertEqual(self.state(d),"HOLD_EVIDENCE_CONFLICT")
    def test_expired(self):
            d=ready_doc(); d["compensation"][0]["expires_at"]="2026-09-18T06:59:59Z"; self.assertEqual(self.state(d),"HOLD_STALE")
    def test_stale_payment(self):
            d=ready_doc(); d["policy"]["max_status_age_hours"]=1; d["payment_status"]["observed_at"]="2026-09-18T05:59:59Z"; self.assertEqual(self.state(d),"HOLD_STALE")
    def test_cooldown(self):
            d=ready_doc(); d["followups"]=[self.followup()]; self.assertEqual(self.state(d),"HOLD_COOLDOWN")
    def test_rejection_conflict(self):
            d=ready_doc(); d["followups"]=[self.followup("PAYMENT_REJECTED")]; self.assertEqual(self.state(d),"HOLD_EVIDENCE_CONFLICT")
