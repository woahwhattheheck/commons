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
    def test_cross_subject_compensation(self):
            d=ready_doc(); d["compensation"][0]["subject"]["counterparty_id"]="other"
            with self.assertRaises(codec.ClaimError): self.current(d)
    def test_cross_work_acceptance(self):
            d=ready_doc(); d["acceptance"]["pr_number"]=99
            with self.assertRaises(codec.ClaimError): self.current(d)
    def test_cross_work_followup(self):
            d=ready_doc(); f=self.followup("SPONSOR_REPLIED"); f["repository"]="other/project"; d["followups"]=[f]
            with self.assertRaises(codec.ClaimError): self.current(d)
    def test_cross_work_payment(self):
            d=ready_doc(); d["payment_status"]["repository"]="other/project"
            with self.assertRaises(codec.ClaimError): self.current(d)
    def test_future_evidence(self):
            d=ready_doc(); d["payment_status"]["observed_at"]="2026-09-18T07:00:01Z"
            with self.assertRaises(codec.ClaimError): self.current(d)
    def test_bool_not_int(self):
            d=ready_doc(); d["work"]["pr_number"]=True
            with self.assertRaises(codec.ClaimError): self.current(d)
    def test_semantic_followup_duplicate(self):
            d=ready_doc(); a=self.followup("SPONSOR_REPLIED"); b=copy.deepcopy(a); b["id"]="f2"; d["followups"]=[a,b]
            with self.assertRaises(codec.ClaimError): self.current(d)
