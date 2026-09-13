from __future__ import annotations
import copy,json,os,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from evaluator import ContractError,canonical_bytes,evaluate,load_json_file,loads_strict,publish_json_exclusive,verify_report
NOW=datetime(2026,9,13,15,0,0,tzinfo=timezone.utc); D="1"*64; E="2"*64

def row(sid,family,condition,expected,observed,completed=True,latency=20,explained=True):
    return {"scenario_id":sid,"family_id":family,"condition":condition,"expected_label":expected,"observed_label":observed,"completed":completed,"latency_ms":latency,"explanation_factors":["signal.primary"] if explained else [],"explanation_sha256":D if explained else "0"*64}
def suite():
    return {"schema":"daf-ai-eval-scenario-set/v1","suite_id":"synthetic.sensor.v1","captured_at":"2026-09-13T14:00:00Z","source_sha256":E,"scenarios":[row("base.a","a","BASELINE","track","track",latency=10),row("pert.a","a","PERTURBATION","track","track",latency=25),row("drift.a","a","DRIFT","track","track",latency=30),row("base.b","b","BASELINE","clear","clear",latency=15),row("pert.b","b","PERTURBATION","clear","clear",latency=40),row("drift.b","b","DRIFT","clear","track",latency=50)]}
def policy(): return {"schema":"daf-ai-eval-policy/v1","policy_id":"phase1.synthetic.thresholds","min_accuracy_bp":8000,"min_reliability_bp":10000,"min_robustness_bp":10000,"max_drift_drop_bp":5000,"min_explainability_bp":10000,"max_p95_latency_ms":100}
def adapter(): return {"schema":"daf-ai-eval-adapter-record/v1","adapter_id":"research.sim.adapter","provider_class":"SYNTHETIC","source_ref":"fixture.synthetic","source_sha256":D,"synthetic_or_research_owned":True,"claims_government_simulator_access":False}
class EvalTests(unittest.TestCase):
    def test_happy_metrics_and_receipt(self):
        r=evaluate(suite(),policy(),adapter(),trusted_now=NOW); self.assertEqual(r["state"],"PROOF_PASS"); self.assertEqual(r["metrics"]["accuracy_bp"],8333); self.assertEqual(r["metrics"]["reliability_bp"],10000); self.assertEqual(r["metrics"]["robustness_bp"],10000); self.assertEqual(r["metrics"]["baseline_accuracy_bp"],10000); self.assertEqual(r["metrics"]["drift_accuracy_bp"],5000); self.assertEqual(r["metrics"]["drift_drop_bp"],5000); self.assertEqual(r["metrics"]["p95_latency_ms"],50); self.assertTrue(verify_report(suite(),policy(),adapter(),r,trusted_now=NOW))
    def test_threshold_reasons_are_stable(self):
        p=policy(); p["min_accuracy_bp"]=9000; p["max_drift_drop_bp"]=4000; p["max_p95_latency_ms"]=49; r=evaluate(suite(),p,adapter(),trusted_now=NOW); self.assertEqual(r["reason_codes"],["ACCURACY_BELOW_MINIMUM","DRIFT_DROP_EXCEEDS_MAXIMUM","P95_LATENCY_EXCEEDS_MAXIMUM"])
    def test_incomplete_is_reliability_failure(self):
        s=suite(); s["scenarios"][1]["completed"]=False; self.assertIn("RELIABILITY_BELOW_MINIMUM",evaluate(s,policy(),adapter(),trusted_now=NOW)["reason_codes"])
    def test_perturbation_mismatch_is_robustness_failure(self):
        s=suite(); s["scenarios"][1]["observed_label"]="clear"; self.assertIn("ROBUSTNESS_BELOW_MINIMUM",evaluate(s,policy(),adapter(),trusted_now=NOW)["reason_codes"])
    def test_missing_explanation_is_explicit(self):
        s=suite(); s["scenarios"][0]["explanation_factors"]=[]; s["scenarios"][0]["explanation_sha256"]="0"*64; self.assertIn("EXPLAINABILITY_BELOW_MINIMUM",evaluate(s,policy(),adapter(),trusted_now=NOW)["reason_codes"])
    def test_no_perturbations_defaults_robustness_to_full(self):
        s=suite(); s["scenarios"]=[r for r in s["scenarios"] if r["condition"]!="PERTURBATION"]; r=evaluate(s,policy(),adapter(),trusted_now=NOW); self.assertEqual(r["metrics"]["robustness_bp"],10000); self.assertEqual(r["metrics"]["robustness_pair_count"],0)
    def test_derived_family_requires_baseline(self):
        s=suite(); s["scenarios"]=s["scenarios"][1:]
        with self.assertRaisesRegex(ContractError,"lacks baseline"): evaluate(s,policy(),adapter(),trusted_now=NOW)
    def test_multiple_baselines_rejected(self):
        s=suite(); s["scenarios"].append(row("base.a2","a","BASELINE","track","track"))
        with self.assertRaisesRegex(ContractError,"multiple baselines"): evaluate(s,policy(),adapter(),trusted_now=NOW)
    def test_duplicate_scenario_rejected(self):
        s=suite(); s["scenarios"].append(copy.deepcopy(s["scenarios"][0]))
        with self.assertRaisesRegex(ContractError,"duplicate scenario_id"): evaluate(s,policy(),adapter(),trusted_now=NOW)
    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(ContractError,"duplicate JSON key"): loads_strict('{"schema":"x","schema":"y"}')
    def test_nan_rejected(self):
        with self.assertRaisesRegex(ContractError,"non-finite"): loads_strict('{"x":NaN}')
    def test_bool_does_not_alias_int(self):
        p=policy(); p["min_accuracy_bp"]=True
        with self.assertRaisesRegex(ContractError,"must be an integer"): evaluate(suite(),p,adapter(),trusted_now=NOW)
    def test_unknown_field_rejected(self):
        s=suite(); s["extra"]="no"
        with self.assertRaisesRegex(ContractError,"keys mismatch"): evaluate(s,policy(),adapter(),trusted_now=NOW)
    def test_future_capture_rejected(self):
        s=suite(); s["captured_at"]="2026-09-14T00:00:00Z"
        with self.assertRaisesRegex(ContractError,"future"): evaluate(s,policy(),adapter(),trusted_now=NOW)
    def test_noncanonical_timestamp_rejected(self):
        s=suite(); s["captured_at"]="2026-09-13T14:00:00+00:00"
        with self.assertRaisesRegex(ContractError,"canonical"): evaluate(s,policy(),adapter(),trusted_now=NOW)
    def test_uppercase_digest_rejected(self):
        s=suite(); s["source_sha256"]="A"*64
        with self.assertRaisesRegex(ContractError,"lowercase sha256"): evaluate(s,policy(),adapter(),trusted_now=NOW)
    def test_government_simulator_claim_rejected(self):
        a=adapter(); a["claims_government_simulator_access"]=True
        with self.assertRaisesRegex(ContractError,"may not claim"): evaluate(suite(),policy(),a,trusted_now=NOW)
    def test_non_owned_adapter_rejected(self):
        a=adapter(); a["synthetic_or_research_owned"]=False
        with self.assertRaisesRegex(ContractError,"requires synthetic"): evaluate(suite(),policy(),a,trusted_now=NOW)
    def test_report_tamper_rejected(self):
        r=evaluate(suite(),policy(),adapter(),trusted_now=NOW); r["metrics"]["accuracy_bp"]+=1
        with self.assertRaisesRegex(ContractError,"does not exactly match"): verify_report(suite(),policy(),adapter(),r,trusted_now=NOW)
    def test_policy_tamper_changes_receipt(self):
        r1=evaluate(suite(),policy(),adapter(),trusted_now=NOW); p=policy(); p["max_p95_latency_ms"]=99; r2=evaluate(suite(),p,adapter(),trusted_now=NOW); self.assertNotEqual(r1["policy_sha256"],r2["policy_sha256"]); self.assertNotEqual(r1["report_sha256"],r2["report_sha256"])
    def test_order_changes_digest_not_metrics(self):
        s1=suite(); s2=suite(); s2["scenarios"]=list(reversed(s2["scenarios"])); r1=evaluate(s1,policy(),adapter(),trusted_now=NOW); r2=evaluate(s2,policy(),adapter(),trusted_now=NOW); self.assertEqual(r1["metrics"],r2["metrics"]); self.assertNotEqual(r1["scenario_set_sha256"],r2["scenario_set_sha256"])
    def test_file_ingress_and_exclusive_publish(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"input.json"; p.write_bytes(canonical_bytes(suite())); loaded=load_json_file(p); out=Path(td)/"report.json"; r=evaluate(loaded,policy(),adapter(),trusted_now=NOW); publish_json_exclusive(out,r); self.assertEqual(json.loads(out.read_text())["report_sha256"],r["report_sha256"])
            with self.assertRaises(FileExistsError): publish_json_exclusive(out,r)
    @unittest.skipUnless(hasattr(os,"symlink"),"symlink not supported")
    def test_symlink_input_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            real=Path(td)/"real.json"; real.write_bytes(canonical_bytes(suite())); link=Path(td)/"link.json"; os.symlink(real,link)
            with self.assertRaisesRegex(ContractError,"regular file"): load_json_file(link)
if __name__=="__main__": unittest.main()
