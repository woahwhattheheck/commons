import copy
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from acceptance import generate
from rail import RailError, receipt_for, reconcile, verify_receipt


def tiny():
    return {
        "review_owner_role": "Wayne State study provenance reviewer",
        "events": [
            {"event_id":"S1","type":"subject","subject_id":"SUBJ-1","protocol_version":1},
            {"event_id":"B1","type":"batch","batch_id":"B-1","synthesis_id":"SY-1","tracer_code":"F18-X","qc_hash":"a"*64,"release_state":"RELEASED","resynthesis_of":None},
            {"event_id":"D1","type":"dose","dose_id":"D-1","subject_id":"SUBJ-1","batch_id":"B-1","administered_at":"2026-09-01T12:00:00Z","administered_activity_bq":180000000},
            {"event_id":"SC1","type":"scan","accession_id":"SCAN-1","subject_id":"SUBJ-1","dose_id":"D-1","acquired_at":"2026-09-01T13:00:00Z","state":"ACQUIRED","timing_state":"ON_TIME","retry_of":None},
            {"event_id":"SG1","type":"segmentation","segmentation_id":"SEG-1","subject_id":"SUBJ-1","accession_id":"SCAN-1","version":1,"artifact_hash":"b"*64,"parent_segmentation_id":None},
            {"event_id":"M1","type":"map","map_id":"MAP-1","subject_id":"SUBJ-1","accession_id":"SCAN-1","segmentation_id":"SEG-1","version":1,"algorithm_version":"ALG-1","artifact_hash":"c"*64,"parent_map_id":None},
            {"event_id":"H1","type":"handoff","handoff_id":"H-1","subject_id":"SUBJ-1","map_id":"MAP-1","state":"ACKED","destination_role":"study-reviewer","observed_at":"2026-09-01T14:00:00Z"},
        ],
    }


class RailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acceptance = generate(100)
        cls.manifest = reconcile(cls.acceptance)

    def test_100_episode_acceptance(self):
        m = self.manifest
        self.assertEqual(m["subject_count"], 100)
        self.assertEqual(m["complete_episode_count"], 100)
        self.assertEqual(m["cross_subject_association_count"], 0)
        self.assertEqual(m["quarantine_count"], 3)
        self.assertEqual({q["reason"] for q in m["quarantine"]}, {"CROSS_SUBJECT_SCAN_MAP"})
        self.assertEqual(len(m["maps"]), m["accepted_map_count"])
        self.assertTrue(all(x["complete_lineage"] for x in m["episodes"]))

    def test_clean_replay_is_order_invariant(self):
        shuffled = copy.deepcopy(self.acceptance)
        random.Random(913).shuffle(shuffled["events"])
        self.assertEqual(reconcile(shuffled), self.manifest)

    def test_exact_retry_collapses_without_effect(self):
        p = tiny(); p["events"].append(copy.deepcopy(p["events"][-1]))
        m = reconcile(p)
        self.assertEqual(m["retry_event_count"], 1)
        self.assertEqual(m["accepted_handoff_count"], 1)

    def test_conflicting_retry_fails_closed(self):
        p = tiny(); row = copy.deepcopy(p["events"][-1]); row["state"] = "HOLD"; p["events"].append(row)
        with self.assertRaisesRegex(RailError, "conflicting duplicate event_id"):
            reconcile(p)

    def test_phi_field_rejected(self):
        p = tiny(); p["events"][0]["patient_name"] = "Forbidden Person"
        with self.assertRaisesRegex(RailError, "PHI field forbidden"):
            reconcile(p)

    def test_non_integer_activity_rejected_even_optimized(self):
        p = tiny(); p["events"][2]["administered_activity_bq"] = 180.5
        with self.assertRaisesRegex(RailError, "integer"):
            reconcile(p)

    def test_unreleased_batch_dose_is_quarantined(self):
        p = tiny(); p["events"][1]["release_state"] = "HOLD"
        m = reconcile(p)
        self.assertEqual(m["accepted_dose_count"], 0)
        self.assertIn("BATCH_NOT_RELEASED", {q["reason"] for q in m["quarantine"]})
        self.assertEqual(m["complete_episode_count"], 0)

    def test_cross_subject_scan_is_quarantined(self):
        p = tiny()
        p["events"].insert(1, {"event_id":"S2","type":"subject","subject_id":"SUBJ-2","protocol_version":1})
        p["events"][4]["subject_id"] = "SUBJ-2"
        m = reconcile(p)
        self.assertIn("CROSS_SUBJECT_DOSE_SCAN", {q["reason"] for q in m["quarantine"]})
        self.assertEqual(m["cross_subject_association_count"], 0)

    def test_scan_retry_requires_failed_parent(self):
        p = tiny()
        p["events"].append({"event_id":"SC2","type":"scan","accession_id":"SCAN-2","subject_id":"SUBJ-1","dose_id":"D-1","acquired_at":"2026-09-01T13:30:00Z","state":"ACQUIRED","timing_state":"DELAYED","retry_of":"SCAN-1"})
        m = reconcile(p)
        self.assertIn("RETRY_PARENT_NOT_FAILED", {q["reason"] for q in m["quarantine"]})

    def test_resynthesis_unknown_parent_fails(self):
        p = tiny(); p["events"][1]["resynthesis_of"] = "MISSING"
        with self.assertRaisesRegex(RailError, "unknown resynthesis parent"):
            reconcile(p)

    def test_resynthesis_cycle_fails(self):
        p = tiny()
        p["events"].append({"event_id":"B2E","type":"batch","batch_id":"B-2","synthesis_id":"SY-2","tracer_code":"F18-X","qc_hash":"d"*64,"release_state":"RELEASED","resynthesis_of":"B-1"})
        p["events"][1]["resynthesis_of"] = "B-2"
        with self.assertRaisesRegex(RailError, "resynthesis cycle"):
            reconcile(p)

    def test_segmentation_versions_must_be_contiguous(self):
        p = tiny(); p["events"].append({"event_id":"SG3","type":"segmentation","segmentation_id":"SEG-3","subject_id":"SUBJ-1","accession_id":"SCAN-1","version":3,"artifact_hash":"d"*64,"parent_segmentation_id":"SEG-1"})
        with self.assertRaisesRegex(RailError, "segmentation versions must be contiguous"):
            reconcile(p)

    def test_map_parent_must_bind_previous_version(self):
        p = tiny()
        p["events"].append({"event_id":"SG2","type":"segmentation","segmentation_id":"SEG-2","subject_id":"SUBJ-1","accession_id":"SCAN-1","version":2,"artifact_hash":"d"*64,"parent_segmentation_id":"SEG-1"})
        p["events"].append({"event_id":"M2","type":"map","map_id":"MAP-2","subject_id":"SUBJ-1","accession_id":"SCAN-1","segmentation_id":"SEG-2","version":2,"algorithm_version":"ALG-2","artifact_hash":"e"*64,"parent_map_id":None})
        with self.assertRaisesRegex(RailError, "map parent mismatch"):
            reconcile(p)

    def test_old_map_handoff_is_quarantined(self):
        p = tiny()
        p["events"].append({"event_id":"SG2","type":"segmentation","segmentation_id":"SEG-2","subject_id":"SUBJ-1","accession_id":"SCAN-1","version":2,"artifact_hash":"d"*64,"parent_segmentation_id":"SEG-1"})
        p["events"].append({"event_id":"M2","type":"map","map_id":"MAP-2","subject_id":"SUBJ-1","accession_id":"SCAN-1","segmentation_id":"SEG-2","version":2,"algorithm_version":"ALG-2","artifact_hash":"e"*64,"parent_map_id":"MAP-1"})
        m = reconcile(p)
        self.assertIn("HANDOFF_NOT_LATEST_MAP", {q["reason"] for q in m["quarantine"]})
        self.assertEqual(m["accepted_handoff_count"], 0)

    def test_map_manifest_binds_batch_qc_through_scan(self):
        row = reconcile(tiny())["maps"][0]
        self.assertEqual(row["subject_id"], "SUBJ-1")
        self.assertEqual(row["dose_id"], "D-1")
        self.assertEqual(row["batch_id"], "B-1")
        self.assertEqual(row["qc_hash"], "a"*64)
        self.assertEqual(row["segmentation_hash"], "b"*64)

    def test_receipt_detects_tamper(self):
        m = reconcile(tiny()); r = receipt_for(m)
        self.assertTrue(verify_receipt(m, r))
        bad = copy.deepcopy(m); bad["subject_count"] += 1
        with self.assertRaisesRegex(RailError, "manifest hash mismatch"):
            verify_receipt(bad, r)

    def test_all_clinical_authority_is_false(self):
        self.assertEqual(set(self.manifest["authority"].values()), {False})
        self.assertFalse(self.manifest["privacy"]["phi_allowed"])

    def test_cli_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td)/"source.json"; manifest = Path(td)/"manifest.json"; receipt = Path(td)/"receipt.json"
            source.write_text(json.dumps(generate(8)))
            built = subprocess.run([sys.executable, str(HERE/"rail.py"), "build", str(source), "--manifest", str(manifest), "--receipt", str(receipt)], text=True, capture_output=True)
            self.assertEqual(built.returncode, 0, built.stdout+built.stderr)
            checked = subprocess.run([sys.executable, str(HERE/"rail.py"), "verify", str(manifest), str(receipt)], text=True, capture_output=True)
            self.assertEqual(checked.returncode, 0, checked.stdout+checked.stderr)
            self.assertEqual(json.loads(checked.stdout), {"ok": True})

    def test_optimized_mode_keeps_fail_closed_validation(self):
        code = "import sys;sys.path.insert(0,sys.argv[1]);from test_rail import tiny;from rail import reconcile,RailError;p=tiny();p['events'][2]['administered_activity_bq']=1.5;\ntry: reconcile(p)\nexcept RailError: raise SystemExit(0)\nraise SystemExit(9)"
        run = subprocess.run([sys.executable, "-O", "-c", code, str(HERE)])
        self.assertEqual(run.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
