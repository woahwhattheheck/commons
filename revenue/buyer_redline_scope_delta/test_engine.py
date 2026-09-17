from __future__ import annotations
import copy, hashlib, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
from revenue.buyer_redline_scope_delta.engine import RedlineError, compile_redline, parse_draft, semantic_digest, strict_json_loads, verify_packet

def obj():
    return {"schema":"buyer-redline-draft/v1","document_id":"pilot","generation_id":"g1","observed_at":"2026-09-16T20:00:00Z","clauses":[
        {"id":"accept","category":"acceptance","metric":"criterion","statement":"Acceptance","value":"PASS"},
        {"id":"currency","category":"price_payment","metric":"currency","statement":"Currency","value":"USD"},
        {"id":"net","category":"price_payment","metric":"net_days","statement":"Net","value":15},
        {"id":"price","category":"price_payment","metric":"fixed_price_minor","statement":"Price","value":1250000},
        {"id":"liability","category":"liability_warranty","metric":"unlimited_liability","statement":"Unlimited","value":False},
        {"id":"duration","category":"schedule","metric":"duration_days","statement":"Duration","value":10},
        {"id":"scope","category":"scope","metric":"work","statement":"Core","value":"compiler"}]}

def enc(x): return (json.dumps(x, ensure_ascii=False, separators=(",",":"))+"\n").encode()

def pair(mut=None):
    b=obj(); br=enc(b); c=copy.deepcopy(b)
    c["generation_id"]="g2"; c["observed_at"]="2026-09-16T20:05:00Z"
    c["baseline_semantic_sha256"]=semantic_digest(parse_draft(br, role="baseline"))
    if mut: mut(c)
    return br, enc(c)

def rehash(p):
    q=copy.deepcopy(p); q.pop("receipt_sha256",None)
    raw=json.dumps(q,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()

class Tests(unittest.TestCase):
    def test_baseline_and_core_commercial_rules(self):
        b,c=pair(); p=compile_redline(b,c)
        self.assertEqual(p["status"],"ACCEPTABLE_AS_WRITTEN"); self.assertTrue(verify_packet(p,b,c))
        cases=[
            (lambda x:x["clauses"].append({"id":"extra","category":"scope","metric":"work","statement":"ERP","value":"erp"}),"REQUOTE_REQUIRED"),
            (lambda x:next(z for z in x["clauses"] if z["id"]=="currency").update(value="EUR"),"REQUOTE_REQUIRED"),
            (lambda x:next(z for z in x["clauses"] if z["id"]=="net").update(value=60),"REQUOTE_REQUIRED"),
            (lambda x:next(z for z in x["clauses"] if z["id"]=="duration").update(value=3),"REQUOTE_REQUIRED"),
            (lambda x:next(z for z in x["clauses"] if z["id"]=="liability").update(value=True),"LEGAL_REVIEW_REQUIRED"),
        ]
        for mut,want in cases:
            with self.subTest(want=want):
                b,c=pair(mut); self.assertEqual(compile_redline(b,c)["status"],want)

    def test_clause_id_cannot_remint_semantic_key(self):
        b=obj(); b["clauses"].append({"id":"buyer.access","category":"assumptions","metric":"input","statement":"Buyer access","value":True})
        br=enc(b); c=copy.deepcopy(b); c["generation_id"]="g2"; c["observed_at"]="2026-09-16T20:05:00Z"
        c["baseline_semantic_sha256"]=semantic_digest(parse_draft(br,role="baseline"))
        row=next(z for z in c["clauses"] if z["id"]=="buyer.access")
        row.update(category="scope",metric="work",statement="Supplier ERP",value="erp")
        p=compile_redline(br,enc(c)); self.assertEqual(p["status"],"REQUOTE_REQUIRED")
        rows=[d for d in p["deltas"] if d["clause_id"]=="buyer.access"]
        self.assertEqual([(d["category"],d["change"]) for d in rows],[("assumptions","REMOVED"),("scope","ADDED")])

    def test_self_recomputed_receipt_is_not_verification_authority(self):
        b,c=pair(lambda x:x["clauses"].append({"id":"extra","category":"scope","metric":"work","statement":"ERP","value":"erp"}))
        p=compile_redline(b,c); p["status"]="ACCEPTABLE_AS_WRITTEN"; p["deltas"]=[]; p["summary"]["changed_clause_count"]=0; p["receipt_sha256"]=rehash(p)
        self.assertFalse(verify_packet(p,b,c))

    def test_exact_source_bytes_are_required(self):
        b,c=pair(); p=compile_redline(b,c); b2=json.dumps(json.loads(b),indent=2).encode()
        co=json.loads(c); co["baseline_semantic_sha256"]=semantic_digest(parse_draft(b2,role="baseline")); c2=enc(co)
        self.assertFalse(verify_packet(p,b2,c2)); self.assertTrue(verify_packet(compile_redline(b2,c2),b2,c2))

    def test_real_datetime_chronology(self):
        b,c=pair(); co=json.loads(c); co["observed_at"]="2026-09-16T20:00:00.1Z"
        self.assertEqual(compile_redline(b,enc(co))["status"],"ACCEPTABLE_AS_WRITTEN")
        co["observed_at"]="2026-09-16T19:59:59.999999Z"
        self.assertEqual(compile_redline(b,enc(co))["status"],"HOLD_CONTRADICTION")

    def test_source_binding_and_generation_holds(self):
        b,c=pair(); co=json.loads(c); co["baseline_semantic_sha256"]="0"*64
        self.assertEqual(compile_redline(b,enc(co))["status"],"HOLD_CONTRADICTION")
        co=json.loads(c); co["document_id"]="other"
        self.assertEqual(compile_redline(b,enc(co))["status"],"HOLD_CONTRADICTION")
        co=json.loads(c); co["generation_id"]="g1"; next(z for z in co["clauses"] if z["id"]=="scope")["value"]="changed"
        self.assertEqual(compile_redline(b,enc(co))["status"],"HOLD_CONTRADICTION")

    def test_strict_ingress_and_singletons(self):
        with self.assertRaises(RedlineError): strict_json_loads('{"a":1,"a":2}')
        with self.assertRaises(RedlineError): strict_json_loads('{"a":NaN}')
        for cid,value in (("price",True),("net",False),("duration",False),("liability",1)):
            b=obj(); next(z for z in b["clauses"] if z["id"]==cid)["value"]=value
            with self.subTest(cid=cid), self.assertRaises(RedlineError): parse_draft(enc(b),role="baseline")
        b=obj(); b["clauses"].append(copy.deepcopy(b["clauses"][0]))
        with self.assertRaises(RedlineError): parse_draft(enc(b),role="baseline")

    def test_determinism_authority_and_tamper(self):
        b,c=pair(); p=compile_redline(b,c)
        self.assertEqual(p,compile_redline(b,c)); self.assertTrue(all(v is False for v in p["authority"].values()))
        p["authority"]["accept_terms"]=True; p["receipt_sha256"]=rehash(p); self.assertFalse(verify_packet(p,b,c))

    def test_cli_compile_verify_no_overwrite_and_symlink(self):
        b,c=pair()
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/"b").write_bytes(b); (r/"c").write_bytes(c)
            env=dict(os.environ); env["PYTHONPATH"]=str(Path(__file__).resolve().parents[2])
            cmd=[sys.executable,"-m","revenue.buyer_redline_scope_delta.cli","compile",str(r/"b"),str(r/"c"),str(r/"p"),"--markdown",str(r/"m")]
            first=subprocess.run(cmd,env=env,text=True,capture_output=True); self.assertEqual(first.returncode,0,first.stdout+first.stderr)
            verify=subprocess.run([sys.executable,"-m","revenue.buyer_redline_scope_delta.cli","verify",str(r/"b"),str(r/"c"),str(r/"p")],env=env,text=True,capture_output=True)
            self.assertEqual(verify.returncode,0,verify.stdout+verify.stderr)
            self.assertEqual(subprocess.run(cmd,env=env,text=True,capture_output=True).returncode,2)
            if hasattr(os,"symlink"):
                try: os.symlink(r/"b",r/"link")
                except OSError: pass
                else:
                    bad=subprocess.run([sys.executable,"-m","revenue.buyer_redline_scope_delta.cli","compile",str(r/"link"),str(r/"c"),str(r/"x")],env=env,text=True,capture_output=True)
                    self.assertEqual(bad.returncode,2); self.assertIn("regular file",bad.stdout)

if __name__=="__main__": unittest.main()
