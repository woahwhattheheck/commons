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
def run(output="d"*64,inputs=INPUTS,scenario=SCEN):
 return build_run_manifest(run_id="r1",model_name="StormWise",model_hash="e"*64,horizon_hours=72,interval_minutes=60,inputs=inputs,scenario=scenario,output_hash=output,started_at="2026-09-16T12:05:00Z",completed_at="2026-09-16T12:25:00Z")
class T(unittest.TestCase):
 def test_input_deterministic(self): self.assertEqual(normalize_input(INPUTS[0]),normalize_input(dict(reversed(list(INPUTS[0].items())))))
 def test_bad_hash_rejected(self):
  x=copy.deepcopy(INPUTS[0]); x["payload_hash"]="bad"
  with self.assertRaises(ValueError): normalize_input(x)
 def test_fetch_before_observation_rejected(self):
  x=copy.deepcopy(INPUTS[0]); x["fetched_at"]="2026-09-16T11:00:00Z"
  with self.assertRaises(ValueError): normalize_input(x)
 def test_freshness_pass(self): self.assertEqual(assess_freshness(INPUTS,as_of="2026-09-16T12:10:00Z",max_age_minutes={"district_gage":60,"noaa_rainfall":60,"usgs_gage":60})["status"],"pass")
 def test_stale_is_review(self): self.assertEqual(assess_freshness(INPUTS,as_of="2026-09-16T14:10:00Z",max_age_minutes={"district_gage":60,"noaa_rainfall":60,"usgs_gage":60})["status"],"review_required")
 def test_horizon_minimum(self):
  with self.assertRaises(ValueError): build_run_manifest(run_id="r",model_name="StormWise",model_hash="e"*64,horizon_hours=71,interval_minutes=60,inputs=INPUTS,scenario=SCEN,output_hash="d"*64,started_at="2026-09-16T12:05:00Z",completed_at="2026-09-16T12:25:00Z")
 def test_scenario_lineage_changes_hash(self):
  alt={**SCEN,"scenario_id":"alt","kind":"rainfall_override","parameters":{"rainfall_multiplier":"1.25"}}
  self.assertNotEqual(run()["scenario_hash"],run(scenario=alt)["scenario_hash"])
 def test_identical_replay_pass(self): self.assertEqual(compare_replay(run(),run())["status"],"pass")
 def test_output_drift_is_review(self): self.assertEqual(compare_replay(run(),run("f"*64))["status"],"review_required")
 def test_replay_never_claims_accuracy_or_safety(self):
  r=compare_replay(run(),run()); self.assertFalse(r["forecast_accuracy_claim"]); self.assertFalse(r["safety_decision_authority"])
 def test_gate_never_grants_release_or_emergency_authority(self):
  f=assess_freshness(INPUTS,as_of="2026-09-16T12:10:00Z",max_age_minutes={"district_gage":60,"noaa_rainfall":60,"usgs_gage":60}); g=acceptance_gate(f,compare_replay(run(),run())); self.assertTrue(g["ready_for_owner_review"]); self.assertFalse(g["forecast_accuracy_authority"]); self.assertFalse(g["emergency_action_authority"]); self.assertFalse(g["production_release_authority"])
if __name__=="__main__": unittest.main()
