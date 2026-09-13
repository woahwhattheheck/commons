from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from revenue.streaming_rendition_qa_pilot import (
    DIAGNOSTIC_PRICE_CENTS, FAULT_CLASSES, INTEGRATION_PRICE_CENTS, PilotError,
    build_report, canonical_json, parse_json_strict, qualify_scope, synthetic_proof,
    verify_report,
)
from revenue.streaming_rendition_qa_pilot.artifacts import read_json_regular, write_artifacts
from streaming_rendition_qa_pilot_package import build

HERE = Path(__file__).resolve().parent
NOW = "2026-09-13T14:30:00Z"

def h(x): return hashlib.sha256(x.encode()).hexdigest()

def scope(**kw):
    x={
        "schema":"streaming-rendition-qa-pilot.scope/v1",
        "pilot_id":"pilot-001","export_ref":"export-001","export_sha256":h("export"),
        "export_descriptor_complete":True,"asset_count":250,"metadata_only":True,
        "requires_media_bytes":False,"requires_drm_secrets":False,"requires_live_provider_access":False,
        "formats":["HLS","DASH"],"fault_classes":list(FAULT_CLASSES),
        "captured_at_utc":"2026-09-13T14:00:00Z","source_ref":"research-001","source_sha256":h("scope-source"),
    }
    x.update(kw); return x

def prospect(i=1, **kw):
    x={
        "schema":"streaming-rendition-qa-pilot.prospect/v1","dedupe_key":f"org-{i}",
        "organization":f"Example Media {i}","public_evidence_tags":["HLS_PUBLIC_EVIDENCE","MULTI_RENDITION_PUBLIC_EVIDENCE"],
        "source_url":f"https://example.org/public-streaming-{i}","source_sha256":h(f"page-{i}"),
        "observed_at_utc":"2026-09-13T13:00:00Z",
    }
    x.update(kw); return x

class PilotTests(unittest.TestCase):
    def report(self, s=None, prospects=None):
        return build_report(s or scope(), [prospect()] if prospects is None else prospects, evaluated_at_utc=NOW)

    def test_exact_250_qualifies_and_prices_exact(self):
        r=self.report()
        self.assertEqual(r["scope_result"]["state"],"QUALIFIED_FOR_OWNER_OFFER_REVIEW")
        self.assertEqual(r["commercial_sheet"]["diagnostic_reference"]["price_cents"],DIAGNOSTIC_PRICE_CENTS)
        self.assertEqual(r["commercial_sheet"]["integration_reference"]["price_cents"],INTEGRATION_PRICE_CENTS)
        self.assertEqual(r["commercial_sheet"]["integration_reference"]["stage"],"OPTIONAL_AFTER_PAID_DIAGNOSTIC")
        self.assertTrue(all(type(x["price_cents"]) is int for x in [r["commercial_sheet"]["diagnostic_reference"],r["commercial_sheet"]["integration_reference"]]))

    def test_251_and_scope_requirements_hold(self):
        cases=[
            (dict(asset_count=251),"ASSET_LIMIT_EXCEEDED"),
            (dict(metadata_only=False),"MEDIA_BYTES_REQUIRED"),
            (dict(requires_media_bytes=True),"MEDIA_BYTES_REQUIRED"),
            (dict(requires_drm_secrets=True),"DRM_SECRET_REQUIRED"),
            (dict(requires_live_provider_access=True),"LIVE_PROVIDER_ACCESS_REQUIRED"),
            (dict(export_descriptor_complete=False),"INCOMPLETE_EXPORT_DESCRIPTOR"),
            (dict(fault_classes=[*FAULT_CLASSES,"NEW_FAULT"]),"UNSUPPORTED_FAULT_CLASS"),
            (dict(formats=["HLS","MAGIC_STREAM"]),"UNSUPPORTED_FORMAT"),
        ]
        for patch,reason in cases:
            with self.subTest(reason=reason):
                q=qualify_scope(scope(**patch)); self.assertEqual(q["state"],"HOLD"); self.assertIn(reason,q["hold_reasons"])

    def test_proof_is_21_assets_and_exact_seven_classes(self):
        a=synthetic_proof(); b=synthetic_proof()
        self.assertEqual(canonical_json(a),canonical_json(b))
        self.assertEqual(len(a["assets"]),21)
        self.assertEqual(tuple(x["fault_class"] for x in a["fault_matrix"]),FAULT_CLASSES)
        self.assertEqual(len([x for x in a["assets"] if x["expected_state"]=="HOLD"]),7)
        self.assertEqual(a["upstream"]["canonical_acceptance"],{"total":168,"release_ready":140,"hold":28,"holds_per_fault_class":4})

    def test_authority_is_always_false(self):
        r=self.report()
        self.assertTrue(all(v is False for v in r["authority_map"].values()))
        self.assertTrue(all(v is False for v in r["commercial_sheet"]["commercial_authority"].values()))
        self.assertTrue(all(x["contact_authority"] is False and x["buyer_intent_inferred"] is False for x in r["prospects"]))

    def test_prospect_cap_dedupe_and_public_url(self):
        self.assertEqual(len(self.report(prospects=[prospect(i) for i in range(1,11)])["prospects"]),10)
        with self.assertRaises(PilotError): self.report(prospects=[prospect(i) for i in range(1,12)])
        with self.assertRaises(PilotError): self.report(prospects=[prospect(1),prospect(2,dedupe_key="org-1")])
        with self.assertRaises(PilotError): self.report(prospects=[prospect(source_url="http://example.org")])
        with self.assertRaises(PilotError): self.report(prospects=[prospect(source_url="https://example.org/token=secret")])

    def test_strict_json_numerics_hashes_time_and_unknown_keys(self):
        for text in ('{"x":1,"x":2}','{"x":NaN}'):
            with self.assertRaises(PilotError): parse_json_strict(text)
        for field,value in [("asset_count",True),("asset_count",1.0),("export_sha256","abc"),("captured_at_utc","2026-09-13T14:00:00.000Z")]:
            bad=scope(); bad[field]=value
            with self.assertRaises(PilotError): qualify_scope(bad)
        bad=scope(); bad["extra"]="x"
        with self.assertRaises(PilotError): qualify_scope(bad)

    def test_scope_opaque_refs_reject_urls_contacts_and_secrets(self):
        for field,value in [("pilot_id","https://x.test"),("export_ref","alice@example.com"),("source_ref","token=abc")]:
            bad=scope(); bad[field]=value
            with self.assertRaises(PilotError): qualify_scope(bad)

    def test_changed_scope_same_pilot_invalidates_old_report(self):
        s1=scope(); r=self.report(s1)
        s2=scope(asset_count=249)
        self.assertFalse(verify_report(r,s2,[prospect()]))
        self.assertNotEqual(r["scope_sha256"],self.report(s2)["scope_sha256"])

    def test_report_and_receipt_tamper_fail(self):
        s=scope(); p=[prospect()]; r=build_report(s,p,evaluated_at_utc=NOW)
        self.assertTrue(verify_report(r,s,p))
        bad=copy.deepcopy(r); bad["commercial_sheet"]["diagnostic_reference"]["price_cents"] += 1
        self.assertFalse(verify_report(bad,s,p))
        reseal=copy.deepcopy(bad); body=dict(reseal); body.pop("receipt_sha256",None); reseal["receipt_sha256"]=hashlib.sha256(canonical_json(body).encode()).hexdigest()
        self.assertFalse(verify_report(reseal,s,p))

    def test_prospect_order_invariance(self):
        ps=[prospect(3),prospect(1),prospect(2)]
        self.assertEqual(canonical_json(self.report(prospects=ps)),canonical_json(self.report(prospects=list(reversed(ps)))))

    def test_artifacts_overwrite_and_symlink_refusal(self):
        r=self.report()
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/"out"; write_artifacts(r,out); self.assertTrue((out/"report.json").is_file())
            with self.assertRaises(PilotError): write_artifacts(r,out)
        if hasattr(os,"symlink"):
            with tempfile.TemporaryDirectory() as td:
                td=Path(td); real=td/"real"; real.write_text("{}")
                link=td/"link"; os.symlink(real,link)
                with self.assertRaises(PilotError): read_json_regular(link)
                target=td/"target"; target.mkdir(); outlink=td/"out"; os.symlink(target,outlink,target_is_directory=True)
                with self.assertRaises(PilotError): write_artifacts(r,outlink)

    def test_input_oversize_and_nonregular_refusal(self):
        from revenue.streaming_rendition_qa_pilot.artifacts import MAX_INPUT_BYTES
        with tempfile.TemporaryDirectory() as td:
            td=Path(td)
            oversized=td/"big.json"
            with oversized.open("wb") as f:
                f.seek(MAX_INPUT_BYTES); f.write(b"x")
            with self.assertRaises(PilotError): read_json_regular(oversized)
            with self.assertRaises(PilotError): read_json_regular(td)

    def test_package_determinism(self):
        with tempfile.TemporaryDirectory() as td:
            a=Path(td)/"a.zip"; b=Path(td)/"b.zip"
            self.assertEqual(build(str(a)),build(str(b))); self.assertEqual(a.read_bytes(),b.read_bytes())

    def test_cli_evaluate_verify_and_no_asof_override(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); bundle=td/"bundle.json"; bundle.write_text(json.dumps({"scope":scope(),"prospects":[prospect()]}))
            out=td/"out"
            run=subprocess.run([sys.executable,str(HERE/"streaming_rendition_qa_pilot_standalone.py"),"evaluate",str(bundle),"--out-dir",str(out)],cwd=HERE,text=True,capture_output=True)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            verify=subprocess.run([sys.executable,str(HERE/"streaming_rendition_qa_pilot_standalone.py"),"verify",str(bundle),str(out/"report.json")],cwd=HERE,text=True,capture_output=True)
            self.assertEqual(verify.returncode,0,verify.stdout+verify.stderr)
            denied=subprocess.run([sys.executable,str(HERE/"streaming_rendition_qa_pilot_standalone.py"),"evaluate",str(bundle),"--out-dir",str(td/"x"),"--as-of",NOW],cwd=HERE,text=True,capture_output=True)
            self.assertNotEqual(denied.returncode,0)

if __name__=="__main__": unittest.main(verbosity=2)
