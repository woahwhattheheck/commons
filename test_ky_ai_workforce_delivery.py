import copy
import json
import tempfile
import unittest
from pathlib import Path

from revenue.ky_ai_workforce_delivery.delivery import (
    BundleError,
    REQUIRED_PATHWAYS,
    load_json_bytes,
    main,
    validate_bundle,
)


def curriculum(label):
    return {
        "objectives": [f"apply {label} AI workflow", f"evaluate {label} output"],
        "delivery_minutes": 180,
        "accessibility": ["captions", "keyboard-accessible materials"],
        "hands_on_exercises": [f"{label} scenario lab"],
    }


def valid_bundle():
    instructors = []
    for p in REQUIRED_PATHWAYS:
        instructors.append({
            "instructor_id": f"inst-{p}",
            "delivery_modes": ["live_remote", "in_person"],
            "coverage": [p],
            "qualifications": [f"documented {p} adult-learning experience"],
        })
    instructors.append({
        "instructor_id": "inst-career",
        "delivery_modes": ["live_remote", "in_person"],
        "coverage": ["service_b"],
        "qualifications": ["documented career-readiness facilitation experience"],
    })
    cohorts = []
    session_ids = []
    for i, p in enumerate(REQUIRED_PATHWAYS):
        sid = f"s-{p}"
        session_ids.append(sid)
        cohorts.append({
            "cohort_id": f"c-{p}",
            "service": "A",
            "pathway": p,
            "seat_capacity": 180,
            "sessions": [{
                "session_id": sid,
                "instructor_id": f"inst-{p}",
                "delivery_mode": "live_remote" if i % 2 == 0 else "in_person",
                "scheduled_at": f"2026-10-{10+i:02d}T13:00:00-04:00",
                "scheduled_minutes": 180,
            }],
        })
    cohorts.append({
        "cohort_id": "c-career",
        "service": "B",
        "pathway": None,
        "seat_capacity": 180,
        "sessions": [{
            "session_id": "s-career",
            "instructor_id": "inst-career",
            "delivery_mode": "live_remote",
            "scheduled_at": "2026-10-20T13:00:00-04:00",
            "scheduled_minutes": 120,
        }],
    })
    return {
        "schema_version": 1,
        "program_id": "scwdb-ai-readiness-2026-demo",
        "planning_target": 980,
        "curricula": {
            "service_a": {p: curriculum(p) for p in REQUIRED_PATHWAYS},
            "service_b": curriculum("career-readiness"),
        },
        "instructors": instructors,
        "cohorts": cohorts,
        "participants": [
            {"participant_id": "p-001", "cohort_ids": ["c-manufacturing", "c-career"]},
            {"participant_id": "p-002", "cohort_ids": ["c-healthcare"]},
        ],
        "attendance": [
            {"participant_id": "p-001", "session_id": "s-manufacturing", "present_minutes": 170},
            {"participant_id": "p-002", "session_id": "s-healthcare", "present_minutes": 144},
        ],
        "assessments": [
            {"participant_id": "p-001", "scope": "manufacturing", "pre_score": 52, "post_score": 84},
            {"participant_id": "p-002", "scope": "healthcare", "pre_score": 70, "post_score": 65},
        ],
        "reporting": {
            "outcome_fields": ["attendance", "assessment_delta", "pathway"],
            "record_retention_controls": ["retention schedule set by prime and buyer"],
            "accessibility_controls": ["captioning", "accessible digital materials"],
        },
    }


class WorkforceDeliveryTests(unittest.TestCase):
    def test_valid_bundle_reports_full_operational_coverage(self):
        report = validate_bundle(valid_bundle())
        self.assertTrue(report["ok"], report["errors"])
        self.assertTrue(report["coverage"]["routine_remote_and_requested_in_person_capability"])
        self.assertEqual(report["stats"]["service_b_session_count"], 1)
        self.assertEqual(report["stats"]["attendance_records_at_least_80_percent"], 2)
        self.assertEqual(report["stats"]["average_assessment_delta"], 13.5)
        self.assertEqual(report["stats"]["planned_seats"], 1080)

    def test_planning_target_is_not_a_guaranteed_minimum(self):
        bundle = valid_bundle()
        for cohort in bundle["cohorts"]:
            cohort["seat_capacity"] = 10
        report = validate_bundle(bundle)
        self.assertTrue(report["ok"], report["errors"])
        self.assertTrue(any("planning target" in w for w in report["warnings"]))

    def test_missing_pathway_is_rejected(self):
        bundle = valid_bundle()
        del bundle["curricula"]["service_a"]["logistics"]
        report = validate_bundle(bundle)
        self.assertFalse(report["ok"])
        self.assertTrue(any("logistics" in e for e in report["errors"]))

    def test_every_pathway_must_have_in_person_capacity(self):
        bundle = valid_bundle()
        bundle["instructors"][3]["delivery_modes"] = ["live_remote"]
        report = validate_bundle(bundle)
        self.assertFalse(report["ok"])
        self.assertTrue(any("healthcare lacks instructor capability" in e for e in report["errors"]))

    def test_service_b_is_required(self):
        bundle = valid_bundle()
        bundle["curricula"]["service_b"] = None
        report = validate_bundle(bundle)
        self.assertFalse(report["ok"])
        self.assertTrue(any("curricula.service_b" in e for e in report["errors"]))

    def test_session_instructor_scope_is_bound(self):
        bundle = valid_bundle()
        bundle["cohorts"][0]["sessions"][0]["instructor_id"] = "inst-healthcare"
        report = validate_bundle(bundle)
        self.assertFalse(report["ok"])
        self.assertTrue(any("not qualified" in e for e in report["errors"]))

    def test_naive_schedule_timestamp_is_rejected(self):
        bundle = valid_bundle()
        bundle["cohorts"][0]["sessions"][0]["scheduled_at"] = "2026-10-10T13:00:00"
        report = validate_bundle(bundle)
        self.assertFalse(report["ok"])
        self.assertTrue(any("timezone-aware" in e for e in report["errors"]))

    def test_attendance_cannot_exceed_scheduled_time(self):
        bundle = valid_bundle()
        bundle["attendance"][0]["present_minutes"] = 181
        report = validate_bundle(bundle)
        self.assertFalse(report["ok"])
        self.assertTrue(any("exceeds scheduled_minutes" in e for e in report["errors"]))

    def test_boolean_numeric_fields_fail_closed(self):
        bundle = valid_bundle()
        bundle["planning_target"] = True
        bundle["cohorts"][0]["seat_capacity"] = True
        report = validate_bundle(bundle)
        self.assertFalse(report["ok"])
        self.assertTrue(any("planning_target" in e for e in report["errors"]))
        self.assertTrue(any("seat_capacity" in e for e in report["errors"]))

    def test_duplicate_json_keys_fail_before_validation(self):
        with self.assertRaises(BundleError):
            load_json_bytes(b'{"schema_version":1,"schema_version":1}')

    def test_participant_identifier_cannot_be_email(self):
        bundle = valid_bundle()
        bundle["participants"][0]["participant_id"] = "person@example.com"
        report = validate_bundle(bundle)
        self.assertFalse(report["ok"])
        self.assertTrue(any("opaque" in e for e in report["errors"]))

    def test_report_is_deterministic(self):
        first = validate_bundle(valid_bundle())
        second = validate_bundle(copy.deepcopy(valid_bundle()))
        self.assertEqual(first, second)
        self.assertEqual(len(first["report_sha256"]), 64)

    def test_negative_assessment_delta_is_reported_not_erased(self):
        report = validate_bundle(valid_bundle())
        self.assertEqual(report["stats"]["average_assessment_delta"], 13.5)

    def test_cli_writes_atomic_report_and_refuses_alias(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            inp = base / "bundle.json"
            out = base / "report.json"
            inp.write_text(json.dumps(valid_bundle()), encoding="utf-8")
            self.assertEqual(main([str(inp), "--output", str(out)]), 0)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(report["ok"])
            before = inp.read_bytes()
            self.assertEqual(main([str(inp), "--output", str(inp)]), 2)
            self.assertEqual(inp.read_bytes(), before)

    def test_attendance_must_match_participant_enrollment(self):
        bundle = valid_bundle()
        bundle["attendance"][0]["session_id"] = "s-logistics"
        report = validate_bundle(bundle)
        self.assertFalse(report["ok"])
        self.assertTrue(any("not enrolled in session cohort" in e for e in report["errors"]))

    def test_assessment_scope_must_match_participant_enrollment(self):
        bundle = valid_bundle()
        bundle["assessments"][0]["scope"] = "construction"
        report = validate_bundle(bundle)
        self.assertFalse(report["ok"])
        self.assertTrue(any("scope is not covered" in e for e in report["errors"]))

    def test_cli_refuses_hardlink_alias_without_mutating_input(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            inp = base / "bundle.json"
            out = base / "alias.json"
            inp.write_text(json.dumps(valid_bundle()), encoding="utf-8")
            out.hardlink_to(inp)
            before = inp.read_bytes()
            self.assertEqual(main([str(inp), "--output", str(out)]), 2)
            self.assertEqual(inp.read_bytes(), before)
            self.assertEqual(out.read_bytes(), before)

    def test_symlink_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            real = base / "bundle.json"
            link = base / "link.json"
            real.write_text(json.dumps(valid_bundle()), encoding="utf-8")
            link.symlink_to(real)
            report_path = base / "report.json"
            self.assertEqual(main([str(link), "--output", str(report_path)]), 2)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertFalse(report["ok"])
            self.assertTrue(any("ordinary regular file" in e for e in report["errors"]))

    def test_authority_flags_never_claim_bid_or_award(self):
        report = validate_bundle(valid_bundle())
        self.assertEqual(report["authority"], {
            "buyer_acceptance": False,
            "partner_commitment": False,
            "proposal_submission": False,
            "award_or_payment": False,
        })


if __name__ == "__main__":
    unittest.main()
