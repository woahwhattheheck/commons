import copy, json, os, tempfile, unittest
from datetime import datetime, timedelta, timezone
from coordination.exact_head_evidence_broker import core
from coordination.exact_head_evidence_broker.cli import main as cli_main
N=datetime(2026,9,17,21,25,0,tzinfo=timezone.utc); H='a'*40; B='b'*40; M='c'*40; X='d'*40

def ts(d): return d.strftime('%Y-%m-%dT%H:%M:%SZ')
def packet():
 return {'schema':core.INPUT_SCHEMA,'repo':'woahwhattheheck/commons','pr_number':7,'source_owner_ref':'sol-z','candidate_head_sha':H,'provider_pr_head_sha':H,'base_sha':B,'current_main_sha':M,'observed_at_utc':ts(N-timedelta(minutes=1)),'valid_until_utc':ts(N+timedelta(hours=1)),'mergeability':'true','pr_changed_paths':['coordination/x.py'],'main_changed_paths':['other.py'],'required_workflows':['tests','source-parses'],'workflow_runs':[{'run_id':1,'name':'tests','head_sha':H,'status':'completed','conclusion':'success'},{'run_id':2,'name':'source-parses','head_sha':H,'status':'completed','conclusion':'success'}],'reviews':[{'provider_id':'r1','head_sha':H,'reviewer_ref':'other-seat','verdict':'GREEN'}],'critical_blobs':[{'path':'coordination/x.py','expected_blob_sha':X,'observed_blob_sha':X}]}
class T(unittest.TestCase):
 def c(self,p): return core._compile_at(p,N)
 def test_green(self): self.assertEqual(self.c(packet())['state'],'FINALIZATION_EVIDENCE_GREEN')
 def test_head_move(self): p=packet(); p['provider_pr_head_sha']=X; self.assertEqual(self.c(p)['state'],'HOLD_HEAD_MISMATCH')
 def test_overlap(self): p=packet(); p['main_changed_paths']=['coordination/x.py']; self.assertEqual(self.c(p)['state'],'HOLD_MAIN_PATH_OVERLAP')
 def test_queued(self): p=packet(); p['workflow_runs'][0].update(status='queued',conclusion=None); self.assertEqual(self.c(p)['state'],'HOLD_CI_UNKNOWN')
 def test_missing_ci(self): p=packet(); p['workflow_runs'].pop(); self.assertEqual(self.c(p)['state'],'HOLD_CI_UNKNOWN')
 def test_failed_ci(self): p=packet(); p['workflow_runs'][0]['conclusion']='failure'; self.assertEqual(self.c(p)['state'],'HOLD_CI_FAILED')
 def test_ancestor_green_ignored(self): p=packet(); p['reviews'][0]['head_sha']=B; self.assertEqual(self.c(p)['state'],'HOLD_REVIEW_MISSING')
 def test_self_green_ignored(self): p=packet(); p['reviews'][0]['reviewer_ref']='sol-z'; self.assertEqual(self.c(p)['state'],'HOLD_REVIEW_MISSING')
 def test_stop(self): p=packet(); p['reviews'][0]['verdict']='STOP'; self.assertEqual(self.c(p)['state'],'HOLD_REVIEW_STOP')
 def test_conflicting_reviews(self): p=packet(); p['reviews'].append({'provider_id':'r2','head_sha':H,'reviewer_ref':'seat2','verdict':'STOP'}); self.assertEqual(self.c(p)['state'],'HOLD_REVIEW_CONFLICT')
 def test_merge_unknown(self): p=packet(); p['mergeability']='unknown'; self.assertEqual(self.c(p)['state'],'HOLD_MERGEABILITY_UNKNOWN')
 def test_not_mergeable(self): p=packet(); p['mergeability']='false'; self.assertEqual(self.c(p)['state'],'HOLD_NOT_MERGEABLE')
 def test_blob_remint(self): p=packet(); p['critical_blobs'][0]['observed_blob_sha']=B; self.assertEqual(self.c(p)['state'],'HOLD_CRITICAL_BLOB_MISMATCH')
 def test_stale(self): p=packet(); p['valid_until_utc']=ts(N); self.assertEqual(self.c(p)['state'],'HOLD_STALE_SNAPSHOT')
 def test_future(self): p=packet(); p['observed_at_utc']=ts(N+timedelta(seconds=1)); self.assertEqual(self.c(p)['state'],'HOLD_STALE_SNAPSHOT')
 def test_duplicate_path_malformed(self): p=packet(); p['pr_changed_paths']*=2; self.assertEqual(self.c(p)['state'],'HOLD_MALFORMED_EVIDENCE')
 def test_duplicate_run_id_malformed(self): p=packet(); p['workflow_runs'][1]['run_id']=1; self.assertEqual(self.c(p)['state'],'HOLD_MALFORMED_EVIDENCE')
 def test_workflow_collision_malformed(self): p=packet(); p['workflow_runs'].append({'run_id':3,'name':'tests','head_sha':H,'status':'completed','conclusion':'success'}); self.assertEqual(self.c(p)['state'],'HOLD_MALFORMED_EVIDENCE')
 def test_duplicate_review_id_malformed(self): p=packet(); p['reviews'].append(copy.deepcopy(p['reviews'][0])); self.assertEqual(self.c(p)['state'],'HOLD_MALFORMED_EVIDENCE')
 def test_nonterminal_conclusion_rejected(self):
  p=packet(); p['workflow_runs'][0]['status']='queued'
  with self.assertRaises(core.BrokerError): self.c(p)
 def test_duplicate_json_key(self):
  with self.assertRaises(core.BrokerError): core.loads_strict_json('{"a":1,"a":2}')
 def test_float_nonfinite(self):
  for x in ('{"a":1.0}','{"a":NaN}'):
   with self.assertRaises(core.BrokerError): core.loads_strict_json(x)
 def test_giant_int(self):
  with self.assertRaises(core.BrokerError): core.loads_strict_json('{"a":99999999999999999999999999}')
 def test_depth(self):
  x=0
  for _ in range(core.MAX_DEPTH+2): x=[x]
  with self.assertRaises(core.BrokerError): core._freeze(x)
 def test_subclass(self):
  class D(dict): pass
  with self.assertRaises(core.BrokerError): core.compile_current(D(packet()))
 def test_receipt_tamper(self):
  p=packet(); r=self.c(p); r['state']='HOLD_CI_FAILED'
  with self.assertRaises(core.BrokerError): core.verify_integrity(p,r)
 def test_integrity(self):
  p=packet(); r=self.c(p); self.assertTrue(core.verify_integrity(p,r))
 def test_current_expiry(self):
  p=packet(); r=self.c(p); self.assertTrue(core._verify_current_at(p,r,N+timedelta(minutes=1))); self.assertFalse(core._verify_current_at(p,r,N+timedelta(hours=2)))
 def test_authority_false(self): self.assertFalse(any(self.c(packet())['authority'].values()))
 def test_authority_alias_rejected(self):
  p=packet(); r=self.c(p); r['authority']['merge_authorized']=0; u=dict(r); u.pop('receipt_digest_sha256'); r['receipt_digest_sha256']=core._digest(u)
  with self.assertRaises(core.BrokerError): core.verify_integrity(p,r)
 def test_compile_global_rebind_inert(self):
  p=packet(); original=core._validate; core._validate=lambda x: x
  try: self.assertEqual(self.c(p)['state'],'FINALIZATION_EVIDENCE_GREEN')
  finally: core._validate=original
 def test_authority_helper_rebind_inert_expected(self):
  original=core._authority; core._authority=lambda: {'merge_authorized':True}
  try: self.assertFalse(any(core.compile_current(packet())['authority'].values()))
  finally: core._authority=original
 def test_receipt_authority_helper_rebind_inert(self):
  p=packet(); r=self.c(p); original=core._authority; core._authority=lambda: {'merge_authorized':True}
  try: self.assertTrue(core.verify_integrity(p,r))
  finally: core._authority=original
 def test_builtin_shadow_compile_inert(self):
  poison=object(); names=('set','len','sorted','sum','any','bool','int','str','list','dict')
  for n in names: setattr(core,n,poison)
  try: self.assertEqual(self.c(packet())['state'],'FINALIZATION_EVIDENCE_GREEN')
  finally:
   for n in names: delattr(core,n)
 def test_raw_byte_limit(self):
  with self.assertRaises(core.BrokerError): core.loads_strict_json(b' '*(core.MAX_INPUT_BYTES+1))
 def test_multibyte_byte_limit(self):
  with self.assertRaises(core.BrokerError): core.loads_strict_json('é'*(core.MAX_INPUT_BYTES//2+1))
 def test_node_budget(self):
  x=[[0]*100 for _ in range(101)]
  with self.assertRaises(core.BrokerError): core._freeze(x)
 def test_bool_pr_number_rejected(self):
  p=packet(); p['pr_number']=True
  with self.assertRaises(core.BrokerError): self.c(p)
 def test_main_move_invalidates_receipt_replay(self):
  p=packet(); r=self.c(p); p2=copy.deepcopy(p); p2['current_main_sha']=X
  self.assertFalse(core.verify_integrity(p2,r))
 def test_verify_current_helper_rebind_inert(self):
  p=packet(); r=self.c(p); original=core.verify_integrity; core.verify_integrity=lambda *_: True
  try: self.assertTrue(core._verify_current_at(p,r,N+timedelta(minutes=1)))
  finally: core.verify_integrity=original
 def test_schema_global_rebind_inert(self):
  p=packet(); originals=(core.RECEIPT_SCHEMA,core.COMPILER_ID,core.INPUT_SCHEMA)
  core.RECEIPT_SCHEMA='evil'; core.COMPILER_ID='evil'; core.INPUT_SCHEMA='evil'
  try:
   r=self.c(p); self.assertEqual(r['schema'],'commons-exact-head-evidence-receipt/v1'); self.assertEqual(r['compiler_id'],'commons.exact-head-evidence-broker/v1')
  finally: core.RECEIPT_SCHEMA,core.COMPILER_ID,core.INPUT_SCHEMA=originals
 def test_cli(self):
  now=datetime.now(timezone.utc).replace(microsecond=0); p=packet(); p['observed_at_utc']=ts(now-timedelta(seconds=2)); p['valid_until_utc']=ts(now+timedelta(hours=1))
  with tempfile.TemporaryDirectory() as d:
   pp=os.path.join(d,'p.json'); rp=os.path.join(d,'r.json')
   with open(pp,'w',encoding='utf-8') as f: f.write(json.dumps(p))
   self.assertEqual(cli_main(['compile',pp,'--out',rp]),0); self.assertEqual(cli_main(['compile',pp,'--out',rp]),2); self.assertEqual(cli_main(['verify-integrity',pp,rp]),0); self.assertEqual(cli_main(['verify-current',pp,rp]),0)
if __name__=='__main__': unittest.main()
