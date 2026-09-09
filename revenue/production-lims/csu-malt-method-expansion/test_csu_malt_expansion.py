from __future__ import annotations
import copy, importlib.util, json, sys, tempfile, unittest
from pathlib import Path
H=Path(__file__).parent; S=importlib.util.spec_from_file_location("csu",H/"csu_malt_expansion.py"); M=importlib.util.module_from_spec(S); sys.modules[S.name]=M; S.loader.exec_module(M)
class T(unittest.TestCase):
 @classmethod
 def setUpClass(c): c.f=H/"fixtures/csu_80_submissions.json"; c.mf=H/"fixtures/manifest.json"; c.rows,c.m=M.load(c.f,c.mf)
 def first(s):
  L,x,_=M.run(copy.deepcopy(s.rows),s.m); M.verify(s.rows,s.m,L,x); return L,x
 def test_shape(s): s.assertEqual((len(s.rows),sum(not r["seeded_fault"] and r["received_phase"]=="BEFORE_CUTOFF" for r in s.rows),sum(not r["seeded_fault"] and r["received_phase"]=="AFTER_CUTOFF" for r in s.rows)),(80,60,8))
 def test_faults(s):
  d={}
  for r in s.rows:
   if r["seeded_fault"]: d[r["seeded_fault"]]=d.get(r["seeded_fault"],0)+1
  s.assertEqual(d,{M.DUP:4,M.UNSUP:4,M.MISS:4})
 def test_exact(s):
  L,x=s.first(); s.assertEqual(x,{M.CURRENT:60,M.NEXT:8,M.DUP:4,M.UNSUP:4,M.MISS:4}); s.assertEqual(L.counts(),{"processed":80,"accessions":68,"jobs":130,"reports":66,"holds":12,"events":80}); s.assertEqual(set(L.submission_hashes),L.seen)
 def test_routing(s):
  L,_=s.first(); third=[j for j in L.jobs.values() if j["route"]=="THIRD_PARTY"]; s.assertEqual(len(third),6); s.assertTrue(all(j["method_id"]=="ASBC-PROTEIN" for j in third)); s.assertTrue(all(j["route"]=="INTERNAL" for j in L.jobs.values() if j["method_id"]!="ASBC-PROTEIN"))
 def test_qc(s):
  L,_=s.first(); blocked={r["sample_id"] for r in s.rows if r["qc_batch"]=="QC-BREACH-01"}; s.assertEqual(len(blocked),2); s.assertTrue(blocked.isdisjoint(L.reports))
 def test_expansion(s):
  L,_=s.first()
  for a in L.accessions.values(): s.assertEqual(sorted(j["method_id"] for j in L.jobs.values() if j["sample_id"]==a["sample_id"]),sorted(x["method_id"] for x in s.m["package_methods"][a["package"]]))
 def test_unique_jobs(s): L,_=s.first(); s.assertEqual(len(L.jobs),len(set(L.jobs)))
 def test_replay(s):
  L,_=s.first(); before=copy.deepcopy(L); _,x,d=M.run(copy.deepcopy(s.rows),s.m,L); s.assertEqual(d,{k:0 for k in before.counts()}); s.assertEqual(x,{"IDEMPOTENT_REPLAY":80}); s.assertEqual(L,before)
 def test_unknown_phase_fails_before_mutation(s):
  L=M.Ledger(); bad=copy.deepcopy(s.rows[0]); bad["submission_id"]="SUB-BAD-PHASE"; bad["sample_id"]="MALT-BAD-PHASE"; bad["received_phase"]="UNKNOWN_PHASE"; before=copy.deepcopy(L)
  with s.assertRaisesRegex(ValueError,"RECEIVED_PHASE_INVALID"): M.process(bad,L,s.m)
  s.assertEqual(L,before)
 def test_changed_submission_replay_fails_before_mutation(s):
  L=M.Ledger(); original=copy.deepcopy(s.rows[0]); s.assertEqual(M.process(original,L,s.m),M.CURRENT); before=copy.deepcopy(L); changed=copy.deepcopy(original); changed["qc_batch"]="QC-CHANGED"
  with s.assertRaisesRegex(ValueError,"REPLAY_PAYLOAD_MISMATCH"): M.process(changed,L,s.m)
  s.assertEqual(L,before)
 def test_held_submission_replay_identity(s):
  L=M.Ledger(); held=copy.deepcopy(s.rows[72]); s.assertEqual(M.process(held,L,s.m),M.UNSUP); before=copy.deepcopy(L); s.assertEqual(M.process(copy.deepcopy(held),L,s.m),"IDEMPOTENT_REPLAY"); s.assertEqual(L,before); changed=copy.deepcopy(held); changed["grain"]="BARLEY"
  with s.assertRaisesRegex(ValueError,"REPLAY_PAYLOAD_MISMATCH"): M.process(changed,L,s.m)
  s.assertEqual(L,before)
 def test_new_submission_same_sample_is_duplicate_not_replay(s):
  L=M.Ledger(); original=copy.deepcopy(s.rows[0]); s.assertEqual(M.process(original,L,s.m),M.CURRENT); duplicate=copy.deepcopy(original); duplicate["submission_id"]="SUB-NEW-SAME-SAMPLE"; s.assertEqual(M.process(duplicate,L,s.m),M.DUP); s.assertIn("SUB-NEW-SAME-SAMPLE",L.holds); s.assertEqual(L.holds["SUB-NEW-SAME-SAMPLE"]["hold_code"],M.DUP)
 def test_release(s):
  L,_=s.first(); sample=next(iter(L.reports)); old=copy.deepcopy(L.reports[sample]);
  with s.assertRaisesRegex(ValueError,"NAMED_HUMAN"): M.release(L,sample,"")
  out=M.release(L,sample,"QA Reviewer"); s.assertEqual((out["status"],out["reviewer"]),(M.RELEASED,"QA Reviewer")); s.assertEqual(L.reports[sample],old)
 def test_tamper(s):
  p=json.loads(s.f.read_text()); p["schema_version"]+=1
  with tempfile.TemporaryDirectory() as td:
   td=Path(td); f=td/"f.json"; mf=td/"m.json"; f.write_text(json.dumps(p)); mf.write_text(s.mf.read_text())
   with s.assertRaisesRegex(ValueError,"FIXTURE_HASH_MISMATCH"): M.load(f,mf)
if __name__=="__main__": unittest.main()
