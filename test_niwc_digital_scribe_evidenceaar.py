from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODULE = ROOT / "competitions" / "niwc-digital-scribe-2026" / "workbench.py"
FIXTURE = ROOT / "competitions" / "niwc-digital-scribe-2026" / "fixtures" / "synthetic_exercise.json"
spec = importlib.util.spec_from_file_location("evidenceaar", MODULE)
assert spec and spec.loader
wb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wb)


def raw(): return FIXTURE.read_bytes()
def obj(): return json.loads(raw())
def enc(v): return json.dumps(v, sort_keys=True, separators=(",", ":")).encode()
def bundle(): return wb.finalize_bundle(raw())

def raises(fn):
    try: fn()
    except wb.ContractError: return
    raise AssertionError("expected ContractError")


def check_determinism(t): t.assertEqual(wb.canonical_bytes(bundle()), wb.canonical_bytes(bundle()))
def check_verify(t): wb.verify_bundle(raw(), bundle())
def check_summary(t):
    s=bundle()["aar"]["summary"]
    t.assertEqual((s["episode_count"],s["claim_count"],s["contradiction_count"],s["coverage_complete_episodes"]),(2,8,1,1))
def check_clock(t):
    e={x["event_id"]:x for x in bundle()["normalized"]["events"]}
    t.assertEqual(e["evt-002"]["corrected_at"],"2026-09-16T13:00:00.500Z"); t.assertEqual(e["evt-003"]["corrected_at"],"2026-09-16T13:00:02.500Z")
def check_episodes(t): t.assertEqual([x["event_ids"] for x in bundle()["aar"]["episodes"]],[["evt-001","evt-002","evt-003","evt-004","evt-005"],["evt-006","evt-007","evt-008"]])
def check_contradiction(t):
    r=bundle()["aar"]["contradictions"][0]; t.assertEqual((r["subject"],r["kind"],r["status"]),("route-alpha","OBSERVATION","UNRESOLVED")); t.assertEqual(sorted(e for a in r["alternatives"] for e in a["event_ids"]),["evt-001","evt-003"])
def check_coverage(t):
    c=bundle()["aar"]["coverage"]; t.assertTrue(c[0]["complete"]); t.assertEqual(c[1]["missing_required_modalities"],["SENSOR","VIDEO"])
def check_lineage(t):
    b=bundle(); sources={x["source_id"]:x for x in b["normalized"]["sources"]}; cl=next(x for x in b["aar"]["claims"] if x["evidence"][0]["event_id"]=="evt-001"); t.assertEqual(cl["evidence"][0]["source_sha256"],sources["text-log"]["sha256"])
def check_render_escape(t):
    b=bundle(); t.assertIn(r"\<safely\>",b["markdown"]); t.assertNotIn("<safely>",b["markdown"]); t.assertIn("&lt;safely&gt; &amp; logged *once*.",b["html"])
def check_authority(t):
    a=bundle()["aar"]["authority"]; t.assertTrue(a["synthetic_offline_only"]); t.assertTrue(all(a[k] is False for k in ("operational_exercise_data_processed","sponsor_submission_authorized","winner_or_award_claimed","payment_or_revenue_claimed")))
def check_receipt(t):
    r=bundle()["receipt"]; t.assertEqual((r["source_count"],r["event_count"],r["exercise_id"]),(4,8,"synthetic-niwc-digital-scribe-demo"))
def check_whitespace(t):
    a=wb.finalize_bundle(enc(obj()))["receipt"]; b=bundle()["receipt"]; t.assertNotEqual(a["input_sha256"],b["input_sha256"]); t.assertEqual((a["normalized_sha256"],a["aar_sha256"]),(b["normalized_sha256"],b["aar_sha256"]))
def check_tamper(t):
    b=bundle(); b["aar"]["summary"]["claim_count"]=999; raises(lambda: wb.verify_bundle(raw(),b))
def check_unknown_bundle(t):
    b=bundle(); b["extra"]=1; raises(lambda: wb.verify_bundle(raw(),b))
def check_mismatch(t):
    b=bundle(); o=obj(); o["exercise_id"]="other"; raises(lambda: wb.verify_bundle(enc(o),b))
def check_duplicate_key(t): raises(lambda: wb.strict_json_loads('{"x":1,"x":2}'))
def check_float(t): raises(lambda: wb.strict_json_loads('{"x":1.25}'))
def check_nan(t): raises(lambda: wb.strict_json_loads('{"x":NaN}'))
def check_huge_int(t): raises(lambda: wb.strict_json_loads('{"x":'+('9'*5000)+'}'))
def check_depth(t):
    v=0
    for _ in range(wb.MAX_NESTING+2): v=[v]
    raises(lambda: wb.canonical_bytes(v))
def mutate(field, value):
    def run(t):
        o=obj(); field(o,value); raises(lambda: wb.finalize_bundle(enc(o)))
    return run

def check_tags(t):
    o=obj(); o["events"][0]["tags"]=["z","a","z"]; e={x["event_id"]:x for x in wb.finalize_bundle(enc(o))["normalized"]["events"]}; t.assertEqual(e["evt-001"]["tags"],["a","z"])
def check_cli(t,opt):
    with tempfile.TemporaryDirectory() as td:
        out=Path(td)/"b.json"; p=subprocess.run([sys.executable,*opt,str(MODULE),"compile",str(FIXTURE),"-o",str(out)],capture_output=True,text=True); t.assertEqual(p.returncode,0,p.stderr); p=subprocess.run([sys.executable,*opt,str(MODULE),"verify",str(FIXTURE),str(out)],capture_output=True,text=True); t.assertEqual((p.returncode,p.stdout.strip()),(0,"VERIFIED"),p.stderr)
def check_cli_bad(t,opt):
    with tempfile.TemporaryDirectory() as td:
        bad=Path(td)/"bad.json"; bad.write_text('{"x":'+('9'*5000)+'}',encoding="utf-8"); p=subprocess.run([sys.executable,*opt,str(MODULE),"compile",str(bad)],capture_output=True,text=True); t.assertEqual(p.returncode,2); t.assertIn("ERROR:",p.stderr); t.assertNotIn("Traceback",p.stderr)
def check_render_exclusive(t):
    with tempfile.TemporaryDirectory() as td:
        out=Path(td)/"rendered"; p=subprocess.run([sys.executable,str(MODULE),"render",str(FIXTURE),str(out)],capture_output=True,text=True); t.assertEqual(p.returncode,0,p.stderr); t.assertTrue(all((out/x).is_file() for x in ("aar.json","aar.md","aar.html","receipt.json","bundle.json"))); p=subprocess.run([sys.executable,str(MODULE),"render",str(FIXTURE),str(out)],capture_output=True,text=True); t.assertEqual(p.returncode,2); t.assertNotIn("Traceback",p.stderr)

CASES = [
("determinism",check_determinism),("verify",check_verify),("summary",check_summary),("clock",check_clock),("episodes",check_episodes),("contradiction",check_contradiction),("coverage",check_coverage),("lineage",check_lineage),("render_escape",check_render_escape),("authority",check_authority),("receipt",check_receipt),("whitespace",check_whitespace),("tamper",check_tamper),("unknown_bundle",check_unknown_bundle),("mismatch",check_mismatch),("duplicate_key",check_duplicate_key),("float",check_float),("nan",check_nan),("huge_int",check_huge_int),("depth",check_depth),
("synthetic_false",mutate(lambda o,v:o.__setitem__("synthetic",v),False)),("bool_gap",mutate(lambda o,v:o.__setitem__("episode_gap_ms",v),True)),("confidence_bool",mutate(lambda o,v:o["events"][0].__setitem__("confidence_milli",v),True)),("unknown_top",mutate(lambda o,v:o.__setitem__("authority",v),{})),("duplicate_source",mutate(lambda o,v:o["sources"].append(copy.deepcopy(o["sources"][0])),None)),("duplicate_event",mutate(lambda o,v:o["events"].append(copy.deepcopy(o["events"][0])),None)),("unknown_source",mutate(lambda o,v:o["events"][0].__setitem__("source_id",v),"missing")),("unknown_modality",mutate(lambda o,v:o["sources"][0].__setitem__("modality",v),"HOLOGRAM")),("unknown_kind",mutate(lambda o,v:o["events"][0].__setitem__("kind",v),"SPECULATION")),("timezone",mutate(lambda o,v:o["events"][0].__setitem__("observed_at",v),"2026-09-16T13:00:00")),("uppercase_hash",mutate(lambda o,v:o["sources"][0].__setitem__("sha256",v),"A"*64)),("required_empty",mutate(lambda o,v:o.__setitem__("required_modalities",v),[])),("tags",check_tags),("cli_normal",lambda t:check_cli(t,[])),("cli_opt",lambda t:check_cli(t,["-O"])),("cli_bad_normal",lambda t:check_cli_bad(t,[])),("cli_bad_opt",lambda t:check_cli_bad(t,["-O"])),("render_exclusive",check_render_exclusive),("bundle_digest",lambda t:t.assertRegex(bundle()["bundle_sha256"],r"^[0-9a-f]{64}$")),
]
assert len(CASES)==39

class EvidenceAARContractTests(unittest.TestCase):
    def test_engine_module_parses(self):
        import ast
        path = ROOT / "competitions" / "niwc-digital-scribe-2026" / "_engine.py"
        src = path.read_text(encoding="utf-8")
        ast.parse(src)
        self.assertIn('r"[0-9a-f]{64}"', src)
        self.assertNotIn("['ummary']", src)

    def test_summary_publication_keys(self):
        b = bundle()
        self.assertIn("Unresolved contradictions: 1", b["markdown"])
        self.assertIn("Evidence-linked claims: 8", b["html"])
        self.assertIn("UNRESOLVED", b["html"])
        self.assertNotIn("UNRESOLVEE", b["html"])

for i,(name,fn) in enumerate(CASES,1):
    setattr(EvidenceAARContractTests,f"test_{i:02d}_{name}",(lambda f: lambda self: f(self))(fn))

if __name__ == "__main__": unittest.main()
