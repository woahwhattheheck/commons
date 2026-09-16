from __future__ import annotations
import copy, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from evidence import *
INPUTS=[
 {"source":"district_gage","source_id":"gage-1","observed_at":"2026-09-16T12:00:00Z","fetched_at":"2026-09-16T12:02:00Z","payload_hash":"a"*64},
 {"source":"noaa_rainfall","source_id":"qpf-1","observed_at":"2026-09-16T12:00:00Z","fetched_at":"2026-09-16T12:03:00Z","payload_hash":"b"*64},
 {"source":"usgs_gage","source_id":"usgs-1","observed_at":"2026-09-16T11:55:00Z","fetched_at":"2026-09-16T12:02:00Z","payload_hash":"c"*64},]
SCEN={"scenario_id":"base-001","kind":"baseline","parameters":{},"created_at":"2026-09-16T12:04:00Z"}
LIMITS={"district_gage":60,"noaa_rainfall":60,"usgs_gage":60}
def run(output="d"*64,inputs=INPUTS,scenario=SCEN,**kw):
 args=dict(run_id="r1",model_name="StormWise",model_hash="e"*64,horizon_hours=72,interval_minutes=60,inputs=inputs,scenario=scenario,output_hash=output,started_at="2026-09-16T12:05:00Z",completed_at="2026-09-16T12:25:00Z")
 args.update(kw); return build_run_manifest(**args)
class T(unittest.TestCase):
 def fresh(self): return assess_freshness(INPUTS,as_of="2026-09-16T12:10:00Z",max_age_minutes=LIMITS)
 def test_input_deterministic(self): self.assertEqual(normalize_input(INPUTS[0]),normalize_input(dict(reversed(list(INPUTS[0].items())))))
 def test_bad_hash_rejected(self):
  x=copy.deepcopy(INPUTS[0]); x["payload_hash"]="bad"
  with self.assertRaises(ValueError): normalize_input(x)
 def test_fetch_before_observation_rejected(self):
  x=copy.deepcopy(INPUTS[0]); x["fetched_at"]="2026-09-16T11:00:00Z"
  with self.assertRaises(ValueError): normalize_input(x)
 def test_freshness_pass(self): self.assertEqual(self.fresh()["status"],"pass")
 def test_empty_freshness_is_review(self): self.assertEqual(assess_freshness([],as_of="2026-09-16T12:10:00Z",max_age_minutes={})["status"],"review_required")
 def test_stale_is_review(self): self.assertEqual(assess_freshness(INPUTS,as_of="2026-09-16T14:10:00Z",max_age_minutes=LIMITS)["status"],"review_required")
 def test_bad_limit_type_fails_closed(self):
  with self.assertRaises(ValueError): assess_freshness(INPUTS,as_of="2026-09-16T12:10:00Z",max_age_minutes={**LIMITS,"district_gage":True})
 def test_horizon_minimum(self):
  with self.assertRaises(ValueError): run(horizon_hours=71)
 def test_bool_interval_rejected(self):
  with self.assertRaises(ValueError): run(interval_minutes=True)
 def test_fractional_second_reverse_run_rejected(self):
  with self.assertRaises(ValueError): run(started_at="2026-09-16T12:05:00.500000Z",completed_at="2026-09-16T12:05:00Z")
 def test_duplicate_inputs_rejected(self):
  with self.assertRaises(ValueError): run(inputs=[INPUTS[0],INPUTS[0]])
 def test_scenario_lineage_changes_hash(self):
  alt={**SCEN,"scenario_id":"alt","kind":"rainfall_override","parameters":{"rainfall_multiplier":"1.25"}}
  self.assertNotEqual(run()["scenario_hash"],run(scenario=alt)["scenario_hash"])
 def test_identical_replay_pass(self): self.assertEqual(compare_replay(run(),run())["status"],"pass")
 def test_empty_replay_rejected(self):
  with self.assertRaises(ValueError): compare_replay({}, {})
 def test_tampered_manifest_rejected(self):
  bad=run(); bad["output_hash"]="f"*64
  with self.assertRaises(ValueError): compare_replay(bad,bad)
 def test_output_drift_is_review(self): self.assertEqual(compare_replay(run(),run("f"*64))["status"],"review_required")
 def test_replay_never_claims_accuracy_or_safety(self):
  r=compare_replay(run(),run()); self.assertFalse(r["forecast_accuracy_claim"]); self.assertFalse(r["safety_decision_authority"])
 def test_tampered_freshness_result_rejected_by_gate(self):
  f=assess_freshness([],as_of="2026-09-16T12:10:00Z",max_age_minutes={}); f["status"]="pass"
  with self.assertRaises(ValueError): acceptance_gate(f,compare_replay(run(),run()))
 def test_tampered_replay_result_rejected_by_gate(self):
  r=compare_replay(run(),run("f"*64)); r["status"]="pass"
  with self.assertRaises(ValueError): acceptance_gate(self.fresh(),r)
 def test_gate_never_grants_release_or_emergency_authority(self):
  g=acceptance_gate(self.fresh(),compare_replay(run(),run())); self.assertTrue(g["ready_for_owner_review"]); self.assertFalse(g["forecast_accuracy_authority"]); self.assertFalse(g["emergency_action_authority"]); self.assertFalse(g["production_release_authority"])
if __name__=="__main__": unittest.main()
