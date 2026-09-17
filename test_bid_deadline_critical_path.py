from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from revenue.bid_deadline_critical_path.engine import (
    CriticalPathError,
    INPUT_SCHEMA,
    TRUTH_BOUNDARY,
    _cli,
    authority_flags,
    canonical_json,
    compile_bundle,
    load_json,
    verify_bundle,
)

A="a"*64; B="b"*64; C="c"*64; D="d"*64; E="e"*64; F="f"*64; ONE="1"*64; TWO="2"*64

def ready_value():
    return {
        "schema": INPUT_SCHEMA,
        "truth_boundary": TRUTH_BOUNDARY,
        "case_id": "bid-001",
        "evaluation_time": "2026-09-16T20:00:00Z",
        "max_source_age_seconds": 86400,
        "fixture": False,
        "solicitation": {
            "solicitation_id": "RFP-26-04",
            "submission_deadline_utc": "2026-09-17T20:00:00Z",
            "timezone_label": "America/Indiana/Indianapolis",
            "source_authority": "BUYER_OFFICIAL",
            "source_uri": "buyer://rfp-26-04",
            "source_sha256": A,
            "observed_at": "2026-09-16T19:30:00Z",
        },
        "amendment": {
            "state": "ACKNOWLEDGED_CURRENT",
            "source_authority": "BUYER_OFFICIAL",
            "source_uri": "buyer://rfp-26-04/amendments",
            "source_sha256": B,
            "observed_at": "2026-09-16T19:31:00Z",
        },
        "qualification": {
            "state": "PRIME_SUPPORTED",
            "source_uri": "repo://qualification/26-04",
            "source_sha256": C,
            "observed_at": "2026-09-16T19:32:00Z",
            "gaps": [],
        },
        "final_submission_buffer_seconds": 3600,
        "actions": [
            {
                "action_id": "assemble",
                "label": "Assemble evidence-bound response packet",
                "actor_class": "SWARM",
                "action_class": "PREPARE",
                "state": "PENDING",
                "duration_seconds": 7200,
                "handoff_buffer_seconds": 1800,
                "depends_on": [],
                "evidence_uri": "repo://response/workspace",
                "evidence_sha256": D,
                "evidence_observed_at": "2026-09-16T19:33:00Z",
            },
            {
                "action_id": "review",
                "label": "Owner reviews final packet",
                "actor_class": "OWNER",
                "action_class": "FINAL_REVIEW",
                "state": "PENDING",
                "duration_seconds": 3600,
                "handoff_buffer_seconds": 1800,
                "depends_on": ["assemble"],
                "evidence_uri": "repo://review/checklist",
                "evidence_sha256": E,
                "evidence_observed_at": "2026-09-16T19:34:00Z",
            },
            {
                "action_id": "portal",
                "label": "Owner logs into portal and stages upload",
                "actor_class": "OWNER",
                "action_class": "PORTAL_LOGIN",
                "state": "PENDING",
                "duration_seconds": 1800,
                "handoff_buffer_seconds": 900,
                "depends_on": ["review"],
                "evidence_uri": "buyer://portal/instructions",
                "evidence_sha256": F,
                "evidence_observed_at": "2026-09-16T19:35:00Z",
            },
            {
                "action_id": "submit",
                "label": "Owner makes final submission decision and submits",
                "actor_class": "OWNER",
                "action_class": "SUBMIT",
                "state": "PENDING",
                "duration_seconds": 900,
                "handoff_buffer_seconds": 0,
                "depends_on": ["portal"],
                "evidence_uri": "buyer://portal/submit",
                "evidence_sha256": ONE,
                "evidence_observed_at": "2026-09-16T19:36:00Z",
            },
        ],
    }

def raw(v=None):
    return canonical_json(ready_value() if v is None else v)

def packet_for(v=None):
    p,m,r=compile_bundle(raw(v))
    return load_json(p,"packet"),p,m,r

class Tests(unittest.TestCase):
    def test_ready(self):
        p,pb,mb,rb=packet_for()
        self.assertEqual(p["decision"],"READY_FOR_OWNER_ACTION")
        self.assertEqual(verify_bundle(raw(),pb,mb,rb),"EXACT_CRITICAL_PATH_MATCH")
        self.assertTrue(all(v is False for v in p["authority"].values()))

    def test_backward_schedule(self):
        p=packet_for()[0]
        by={x["action_id"]:x for x in p["critical_path"]}
        self.assertEqual(by["submit"]["latest_safe_finish_utc"],"2026-09-17T19:00:00Z")
        self.assertEqual(by["submit"]["latest_safe_start_utc"],"2026-09-17T18:45:00Z")
        self.assertEqual(by["portal"]["latest_safe_finish_utc"],"2026-09-17T18:45:00Z")
        self.assertEqual(by["portal"]["latest_safe_start_utc"],"2026-09-17T18:00:00Z")
        self.assertEqual(by["review"]["latest_safe_start_utc"],"2026-09-17T16:30:00Z")
        self.assertEqual(by["assemble"]["latest_safe_start_utc"],"2026-09-17T14:00:00Z")

    def test_source_not_official_holds(self):
        v=ready_value(); v["solicitation"]["source_authority"]="CURATED_EXPORT"
        self.assertEqual(packet_for(v)[0]["decision"],"HOLD_SOURCE")

    def test_stale_source_holds(self):
        v=ready_value(); v["max_source_age_seconds"]=60
        self.assertEqual(packet_for(v)[0]["decision"],"HOLD_SOURCE")

    def test_fixture_holds_source(self):
        v=ready_value(); v["fixture"]=True; v["solicitation"]["source_authority"]="SYNTHETIC_FIXTURE"
        self.assertEqual(packet_for(v)[0]["decision"],"HOLD_SOURCE")

    def test_future_source_rejected(self):
        v=ready_value(); v["solicitation"]["observed_at"]="2026-09-16T20:01:00Z"
        with self.assertRaises(CriticalPathError): compile_bundle(raw(v))

    def test_open_amendment_holds(self):
        v=ready_value(); v["amendment"]["state"]="OPEN_UNACKNOWLEDGED"
        self.assertEqual(packet_for(v)[0]["decision"],"HOLD_AMENDMENT")

    def test_nonofficial_amendment_holds(self):
        v=ready_value(); v["amendment"]["source_authority"]="CURATED_EXPORT"
        self.assertEqual(packet_for(v)[0]["decision"],"HOLD_AMENDMENT")

    def test_unknown_amendment_holds(self):
        v=ready_value(); v["amendment"]["state"]="UNKNOWN"
        self.assertEqual(packet_for(v)[0]["decision"],"HOLD_AMENDMENT")

    def test_stale_amendment_holds(self):
        v=ready_value(); v["amendment"]["observed_at"]="2026-09-15T00:00:00Z"
        self.assertEqual(packet_for(v)[0]["decision"],"HOLD_AMENDMENT")

    def test_qualification_missing_holds(self):
        v=ready_value(); v["qualification"]["state"]="HOLD_MISSING_EVIDENCE"; v["qualification"]["gaps"]=["insurance"]
        self.assertEqual(packet_for(v)[0]["decision"],"HOLD_QUALIFICATION")

    def test_disqualified_holds(self):
        v=ready_value(); v["qualification"]["state"]="DISQUALIFIED"
        self.assertEqual(packet_for(v)[0]["decision"],"HOLD_QUALIFICATION")

    def test_partner_supported_ready(self):
        v=ready_value(); v["qualification"]["state"]="PARTNER_SUPPORTED"
        self.assertEqual(packet_for(v)[0]["decision"],"READY_FOR_OWNER_ACTION")

    def test_dnr_amendment_dominates(self):
        v=ready_value(); v["amendment"]["state"]="DNR"
        self.assertEqual(packet_for(v)[0]["decision"],"DNR")

    def test_dnr_qualification_dominates(self):
        v=ready_value(); v["qualification"]["state"]="DNR"
        self.assertEqual(packet_for(v)[0]["decision"],"DNR")

    def test_blocked_action_holds(self):
        v=ready_value(); v["actions"][1]["state"]="BLOCKED"
        self.assertEqual(packet_for(v)[0]["decision"],"HOLD_DEPENDENCY")

    def test_stale_pending_action_evidence_holds(self):
        v=ready_value(); v["actions"][0]["evidence_observed_at"]="2026-09-15T00:00:00Z"
        self.assertEqual(packet_for(v)[0]["decision"],"HOLD_DEPENDENCY")

    def test_stale_complete_action_does_not_hold(self):
        v=ready_value(); v["actions"][0]["state"]="COMPLETE"; v["actions"][0]["evidence_observed_at"]="2026-09-15T00:00:00Z"
        self.assertEqual(packet_for(v)[0]["decision"],"READY_FOR_OWNER_ACTION")

    def test_deadline_passed(self):
        v=ready_value(); v["solicitation"]["submission_deadline_utc"]="2026-09-16T19:59:59Z"
        self.assertEqual(packet_for(v)[0]["decision"],"MISSED_WINDOW")

    def test_required_work_makes_window_missed(self):
        v=ready_value(); v["solicitation"]["submission_deadline_utc"]="2026-09-16T22:00:00Z"
        self.assertEqual(packet_for(v)[0]["decision"],"MISSED_WINDOW")

    def test_completed_action_duration_zeroed(self):
        v=ready_value(); v["actions"][0]["state"]="COMPLETE"
        p=packet_for(v)[0]; by={x["action_id"]:x for x in p["critical_path"]}
        self.assertEqual(by["assemble"]["latest_safe_start_utc"],by["assemble"]["latest_safe_finish_utc"])

    def test_owner_only_portal(self):
        v=ready_value(); v["actions"][2]["actor_class"]="SWARM"
        with self.assertRaisesRegex(CriticalPathError,"must be OWNER"): compile_bundle(raw(v))

    def test_owner_only_signature(self):
        v=ready_value(); v["actions"][2]["action_class"]="SIGNATURE"; v["actions"][2]["actor_class"]="PARTNER"
        with self.assertRaisesRegex(CriticalPathError,"must be OWNER"): compile_bundle(raw(v))

    def test_owner_only_submit(self):
        v=ready_value(); v["actions"][3]["actor_class"]="SYSTEM"
        with self.assertRaisesRegex(CriticalPathError,"must be OWNER"): compile_bundle(raw(v))

    def test_missing_dependency_rejected(self):
        v=ready_value(); v["actions"][1]["depends_on"]=["missing"]
        with self.assertRaisesRegex(CriticalPathError,"unknown dependency"): compile_bundle(raw(v))

    def test_self_dependency_rejected(self):
        v=ready_value(); v["actions"][1]["depends_on"]=["review"]
        with self.assertRaisesRegex(CriticalPathError,"self dependency"): compile_bundle(raw(v))

    def test_cycle_rejected(self):
        v=ready_value(); v["actions"][0]["depends_on"]=["review"]
        with self.assertRaisesRegex(CriticalPathError,"dependency cycle"): compile_bundle(raw(v))

    def test_duplicate_action_id_rejected(self):
        v=ready_value(); v["actions"][1]["action_id"]="assemble"
        with self.assertRaisesRegex(CriticalPathError,"duplicate action_id"): compile_bundle(raw(v))

    def test_duplicate_dependency_rejected(self):
        v=ready_value(); v["actions"][1]["depends_on"]=["assemble","assemble"]
        with self.assertRaisesRegex(CriticalPathError,"duplicate item"): compile_bundle(raw(v))

    def test_naive_timestamp_rejected(self):
        v=ready_value(); v["solicitation"]["submission_deadline_utc"]="2026-09-17T20:00:00"
        with self.assertRaisesRegex(CriticalPathError,"explicit UTC"): compile_bundle(raw(v))

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(CriticalPathError,"duplicate JSON key"): load_json(b'{"a":1,"a":2}')

    def test_float_nonfinite_rejected(self):
        for bad in [b'{"a":1.2}',b'{"a":NaN}',b'{"a":Infinity}']:
            with self.subTest(bad=bad):
                with self.assertRaises(CriticalPathError): load_json(bad)

    def test_bool_as_duration_rejected(self):
        v=ready_value(); v["actions"][0]["duration_seconds"]=True
        with self.assertRaisesRegex(CriticalPathError,"integer required"): compile_bundle(raw(v))

    def test_unknown_key_rejected(self):
        v=ready_value(); v["credential"]="secret"
        with self.assertRaisesRegex(CriticalPathError,"keys mismatch"): compile_bundle(raw(v))

    def test_action_unknown_key_secret_rejected(self):
        v=ready_value(); v["actions"][2]["password"]="secret"
        with self.assertRaisesRegex(CriticalPathError,"keys mismatch"): compile_bundle(raw(v))

    def test_deterministic(self):
        self.assertEqual(compile_bundle(raw()),compile_bundle(raw()))

    def test_tamper_packet(self):
        pb,mb,rb=compile_bundle(raw()); p=load_json(pb,"packet"); p["decision"]="DNR"
        with self.assertRaisesRegex(CriticalPathError,"bundle mismatch"): verify_bundle(raw(),canonical_json(p),mb,rb)

    def test_tamper_markdown(self):
        pb,mb,rb=compile_bundle(raw())
        with self.assertRaisesRegex(CriticalPathError,"bundle mismatch"): verify_bundle(raw(),pb,mb+b"x",rb)

    def test_tamper_receipt(self):
        pb,mb,rb=compile_bundle(raw()); r=load_json(rb,"receipt"); r["input_sha256"]="0"*64
        with self.assertRaisesRegex(CriticalPathError,"bundle mismatch"): verify_bundle(raw(),pb,mb,canonical_json(r))

    def test_one_byte_input_drift(self):
        pb,mb,rb=compile_bundle(raw()); v=ready_value(); v["actions"][0]["label"]+="!"
        with self.assertRaisesRegex(CriticalPathError,"bundle mismatch"): verify_bundle(raw(v),pb,mb,rb)

    def test_markdown_explicit_no_authority(self):
        _,mb,_=compile_bundle(raw()); text=mb.decode()
        self.assertIn("NOT A SUBMISSION",text)
        self.assertIn("submission: **false**",text)

    def test_receipt_all_authority_false(self):
        _,_,rb=compile_bundle(raw()); r=load_json(rb,"receipt")
        self.assertTrue(all(v is False for v in r["authority"].values()))

    def test_cli_compile_verify_overwrite_fail(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); inp=root/"in.json"; p=root/"p.json"; m=root/"p.md"; r=root/"r.json"
            inp.write_bytes(raw())
            self.assertEqual(_cli(["compile",str(inp),"--packet",str(p),"--markdown",str(m),"--receipt",str(r)]),0)
            self.assertEqual(_cli(["verify",str(inp),str(p),str(m),str(r)]),0)
            self.assertEqual(_cli(["compile",str(inp),"--packet",str(p),"--markdown",str(m),"--receipt",str(r)]),2)

    def test_cli_preflight_no_partial(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); inp=root/"in.json"; p=root/"p.json"; m=root/"p.md"; r=root/"r.json"
            inp.write_bytes(raw()); m.write_text("foreign")
            self.assertEqual(_cli(["compile",str(inp),"--packet",str(p),"--markdown",str(m),"--receipt",str(r)]),2)
            self.assertFalse(p.exists()); self.assertFalse(r.exists()); self.assertEqual(m.read_text(),"foreign")

if __name__=="__main__":
    unittest.main()
