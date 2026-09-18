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
    def test_duplicate_json_float_nonfinite_unsafe_int_surrogate(self):
            for raw in ('{"a":1,"a":1}','{"a":1.5}','{"a":NaN}','{"a":Infinity}','{"a":9007199254740992}','"\\ud800"'):
                with self.subTest(raw=raw), self.assertRaises(codec.ClaimError): codec.strict_loads(raw)
    def test_bool_int_artifact_alias_fails(self):
            r,m,c=self.current(); mutated=copy.deepcopy(r); mutated["authority"]["send_authorized"]=0; self.assertEqual(mutated,r); self.assertFalse(__import__("revenue.merged_work_payment_claim.verify_v2",fromlist=["verify_artifacts"]).verify_artifacts(ready_doc(),mutated,m,c))
    def test_receipt_markdown_tamper(self):
            r,m,c=self.current(); bad=copy.deepcopy(c); bad["state"]="HOLD_STALE"; self.assertFalse(__import__("revenue.merged_work_payment_claim.verify_v2",fromlist=["verify_artifacts"]).verify_artifacts(ready_doc(),r,m,bad)); self.assertFalse(__import__("revenue.merged_work_payment_claim.verify_v2",fromlist=["verify_artifacts"]).verify_artifacts(ready_doc(),r,m+"x",c))
    def test_library_replay_verify(self):
            from revenue.merged_work_payment_claim.verify_v2 import verify_artifacts
            r,m,c=compiler.compile_replay(ready_doc(),NOW)
            self.assertTrue(verify_artifacts(ready_doc(),r,m,c))
