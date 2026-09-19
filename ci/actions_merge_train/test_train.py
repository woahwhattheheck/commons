import copy, pathlib, sys, unittest
HERE=pathlib.Path(__file__).resolve().parent; sys.path.insert(0,str(HERE)); import core
SHA="a"*40; BASE="b"*40

def run_capture(run_id=1,*,attempt=1,status="completed",conclusion="success",head=SHA,repo="acme/widgets"):
 return {"schema":"github-actions-workflow-run-capture/v1","run":{"id":run_id,"run_attempt":attempt,"repository":repo,"head_sha":head,"status":status,"conclusion":conclusion}}
def step(number=1,*,status="completed",conclusion="success",name="test"): return {"number":number,"name":name,"status":status,"conclusion":conclusion}
def job(job_id=11,*,status="completed",conclusion="success",runner_id=55,steps=None,name="test"): return {"id":job_id,"name":name,"status":status,"conclusion":conclusion,"runner_id":runner_id,"steps":list(steps or [])}
def jobs_capture(jobs,*,run_id=1,attempt=1,head=SHA,repo="acme/widgets"): return {"schema":"github-actions-jobs-capture/v1","run_id":run_id,"run_attempt":attempt,"repository":repo,"head_sha":head,"jobs":list(jobs)}
def case(run_id=1,*,attempt=1,status="completed",conclusion="success",runner_id=55,steps=None):
 if steps is None: steps=[step()] if conclusion=="success" else [step(conclusion="failure")]
 return {"run":run_capture(run_id,attempt=attempt,status=status,conclusion=conclusion),"jobs":jobs_capture([job(status=status if status!="completed" else "completed",conclusion=conclusion if status=="completed" else None,runner_id=runner_id,steps=steps)],run_id=run_id,attempt=attempt)}
def capture(workflows=None,*,review="GREEN",topology="CURRENT",review_id=7,behind=0):
 workflows=workflows if workflows is not None else [{"name":"source-parses","cases":[case()]}]
 return {"schema":core.CAPTURE_SCHEMA,"repository":"acme/widgets","pr_number":42,"head_sha":SHA,"workflows":workflows,"source_review":{"schema":core.REVIEW_SCHEMA,"repository":"acme/widgets","pr_number":42,"head_sha":SHA,"state":review,"review_id":review_id if review in {"GREEN","RED"} else None},"topology":{"schema":core.TOPOLOGY_SCHEMA,"repository":"acme/widgets","pr_number":42,"head_sha":SHA,"base_sha":BASE if topology!="ABSENT" else None,"behind_by":behind if topology!="ABSENT" else None,"state":topology,"required_workflows":sorted(w["name"] for w in workflows)}}

class TrainTests(unittest.TestCase):
 def test_green_is_guarded_review_not_merge_authority(self):
  row=core.compile_capture(capture()); self.assertEqual(row["overall_disposition"],"READY_FOR_GUARDED_REVIEW"); self.assertFalse(row["merge_authorized"]); self.assertEqual(row["workflows"][0]["disposition"],"SOURCE_EXECUTED_GREEN")
 def test_provider_no_run_cancelled_and_queue_are_distinct(self):
  no=case(conclusion="failure",runner_id=0,steps=[]); cancel=case(2,conclusion="cancelled",runner_id=0,steps=[]); queued=case(3,status="queued",conclusion=None,runner_id=0,steps=[])
  rows=core.compile_capture(capture([{"name":"a","cases":[no]},{"name":"b","cases":[cancel]},{"name":"c","cases":[queued]}]))["workflows"]
  self.assertEqual([r["disposition"] for r in rows],["PROVIDER_NO_RUN","PROVIDER_CANCELLED_BEFORE_EXECUTION","PROVIDER_QUEUED"])
 def test_assigned_zero_step_and_partial_matrix_fail_ambiguous(self):
  assigned=case(conclusion="failure",runner_id=9,steps=[])
  partial={"run":run_capture(conclusion="failure"),"jobs":jobs_capture([job(11,conclusion="failure",runner_id=9,steps=[step()]),job(12,status="queued",conclusion=None,runner_id=0,steps=[])])}
  a=core.compile_capture(capture([{"name":"a","cases":[assigned]}])); b=core.compile_capture(capture([{"name":"b","cases":[partial]}]))
  self.assertEqual(a["workflows"][0]["disposition"],"HOLD_AMBIGUOUS"); self.assertEqual(b["workflows"][0]["disposition"],"HOLD_AMBIGUOUS")
 def test_latest_attempt_replaces_older_same_run(self):
  older=case(9,attempt=1,conclusion="failure",runner_id=0,steps=[]); newer=case(9,attempt=2)
  w=core.compile_capture(capture([{"name":"source-parses","cases":[older,newer]}]))["workflows"][0]
  self.assertEqual(w["disposition"],"SOURCE_EXECUTED_GREEN"); self.assertEqual(w["latest_attempts"][0]["run_attempt"],2); self.assertEqual(w["replaced_attempts"][0]["run_attempt"],1)
 def test_conflicting_distinct_executions_hold(self):
  green=case(1); red=case(2,conclusion="failure")
  w=core.compile_capture(capture([{"name":"source-parses","cases":[green,red]}]))["workflows"][0]
  self.assertEqual(w["disposition"],"HOLD_AMBIGUOUS")
 def test_review_and_topology_are_independent_holds(self):
  self.assertEqual(core.compile_capture(capture(review="RED"))["overall_disposition"],"HOLD_SOURCE_REVIEW_RED")
  self.assertEqual(core.compile_capture(capture(topology="STALE",behind=2))["overall_disposition"],"HOLD_TOPOLOGY")
 def test_missing_required_workflow_evidence_holds(self):
  row=core.compile_capture(capture([{"name":"source-parses","cases":[]}]))
  self.assertEqual(row["workflows"][0]["disposition"],"EVIDENCE_ABSENT"); self.assertEqual(row["overall_disposition"],"HOLD_EVIDENCE_ABSENT")
 def test_provider_storm_advice(self):
  one=case(8,attempt=1,conclusion="failure",runner_id=0,steps=[]); two=case(8,attempt=2,conclusion="failure",runner_id=0,steps=[])
  w=core.compile_capture(capture([{"name":"source-parses","cases":[one,two]}]))["workflows"][0]
  self.assertEqual(w["rerun_advice"],"BACKOFF_PROVIDER_STORM")
 def test_wrong_head_duplicate_cross_workflow_bool_and_topology_contract_rejected(self):
  wrong=case(); wrong["run"]["run"]["head_sha"]="c"*40; wrong["jobs"]["head_sha"]="c"*40
  with self.assertRaises(core.EvidenceError): core.compile_capture(capture([{"name":"a","cases":[wrong]}]))
  same=case(5)
  with self.assertRaises(core.EvidenceError): core.compile_capture(capture([{"name":"a","cases":[same]},{"name":"b","cases":[copy.deepcopy(same)]}]))
  bad=capture(); bad["pr_number"]=True
  with self.assertRaises(core.EvidenceError): core.compile_capture(bad)
  bad2=capture(); bad2["topology"]["required_workflows"]=["other"]
  with self.assertRaises(core.EvidenceError): core.compile_capture(bad2)
 def test_train_order_receipt_verify_and_tamper(self):
  a=capture(); b=capture(); b["pr_number"]=41; b["source_review"]["pr_number"]=41; b["topology"]["pr_number"]=41
  first=core.compile_train([a,b]); second=core.compile_train([b,a]); self.assertEqual(first,second); self.assertTrue(core.verify_receipt(first,[a,b])["valid"])
  tampered=copy.deepcopy(first); tampered["prs"][0]["overall_disposition"]="HOLD_AMBIGUOUS"
  self.assertIn("SUPPLIED_RECEIPT_DIGEST_MISMATCH",core.verify_receipt(tampered,[a,b])["reason_codes"])
  projection=dict(tampered); projection.pop("receipt_sha256",None); tampered["receipt_sha256"]=core.digest(projection)
  self.assertIn("RECEIPT_RECOMPUTE_MISMATCH",core.verify_receipt(tampered,[a,b])["reason_codes"])
 def test_markdown_deterministic_and_advisory(self):
  receipt=core.compile_train([capture()]); a=core.render_markdown(receipt); b=core.render_markdown(receipt); self.assertEqual(a,b); self.assertIn("not merge authorization",a); self.assertIn("READY_FOR_GUARDED_REVIEW",a)
 def test_strict_json_rejects_duplicate_keys(self):
  with self.assertRaises(core.EvidenceError): core.loads_strict(b'{"a":1,"a":2}',label="x")
if __name__=="__main__": unittest.main(verbosity=2)
