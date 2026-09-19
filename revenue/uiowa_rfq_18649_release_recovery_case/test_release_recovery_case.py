#!/usr/bin/env python3
"""Regression suite for the UIOWA-109 integrated release-and-recovery case.

Two halves carry equal weight here:

  * every deliberately-broken fixture must be CAUGHT, and
  * the clean fixture must fire NOTHING.

A checker that flags everything catches every defect and is useless. So the
false-positive tests below are not filler -- `test_clean_fixture_fires_nothing`
and `test_independent_recovery_is_not_serialised` are the ones that would fail
first if the engine got greedy.
"""

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import make_fixtures as mf
import release_recovery_case as rrc

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")
ENGINE = os.path.join(HERE, "release_recovery_case.py")

# Every fixture, and the ONE code it must produce. Isolation is the contract:
# a fixture that fires a second code is not proving what it claims to prove.
DEFECT_EXPECTATIONS = {
    "timeline-disagreement": "TIMELINE_DISAGREEMENT",
    "unresolved-source-id": "UNRESOLVED_SOURCE_ID",
    "unsupported-recovery-claim": "UNSUPPORTED_RECOVERY_CLAIM",
    "ordering-inversion": "ORDERING_INVERSION",
    "unknown-timestamp": "UNORDERABLE_EVENT",
    "id-collision": "ID_COLLISION",
    "environment-difference": "ENVIRONMENT_DIFFERENCE",
}

# Field contracts mirrored from the sibling kits on 2026-09-19. The drift test
# below re-reads the real schema when the sibling lane is present.
PROVENANCE_ROOT = ("schema_version", "packet_id", "data_class", "evidence", "sources",
                   "builds", "artifacts", "deployments")
PROVENANCE_DEPLOYMENT = ("id", "artifact_id", "environment", "observed_version",
                         "observed_sha256", "observed_at", "evidence_id")
PROVENANCE_ARTIFACT = ("id", "build_id", "version", "sha256", "local_path", "evidence_id")
PROVENANCE_BUILD = ("id", "source_id", "observed_repository", "observed_revision",
                    "builder_id", "recipe_uri", "recipe_sha256", "started_at",
                    "finished_at", "evidence_id", "input_coverage", "materials")
PROVENANCE_SOURCE = ("id", "repository", "revision", "approved_revision", "approved_at",
                     "approval_evidence_id")
PROVENANCE_EVIDENCE = ("id", "locator", "owner_role", "kind", "captured_at")
RECOVERY_SERVICE = ("service_id", "name", "business_function", "target_rpo_minutes",
                    "target_rto_minutes", "dependencies", "backup", "exercise")
RECOVERY_EXERCISE = ("exercise_id", "disruption_at", "restored_data_as_of",
                     "restore_completed_at", "business_verified_at",
                     "business_verification_evidence_id", "dependency_results")


def load_fixture(name):
    return rrc.load_case(os.path.join(FIXTURES, f"{name}.json"))


def assess_dict(case_dict):
    """Validate + assess an in-memory case, so hostile cases need no temp file."""
    return rrc.assess(rrc.validate_case(copy.deepcopy(case_dict)))


def codes(report):
    return {f["code"] for f in report["findings"]}


def write_temp(payload):
    fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(payload, fh)
    fh.close()
    return fh.name


# ---------------------------------------------------------------------------
# False positives -- the half of this order that is easy to skip
# ---------------------------------------------------------------------------

class TestNoFalsePositives(unittest.TestCase):

    def test_clean_fixture_fires_nothing(self):
        """The clean case must be silent. Not 'mostly silent'. Silent."""
        report = rrc.assess(load_fixture("clean"))
        self.assertEqual(report["findings"], [],
                         f"clean fixture produced findings: {codes(report)}")
        self.assertEqual(report["status"], "AGREED")
        self.assertEqual(report["summary"]["contradiction_count"], 0)
        self.assertEqual(report["summary"]["gap_count"], 0)
        self.assertEqual(rrc.exit_code(report), 0)

    def test_clean_fixture_has_no_per_service_gaps_either(self):
        """A gap listed on a service row is still an unexplained complaint."""
        report = rrc.assess(load_fixture("clean"))
        for svc in report["recovery"]["services"]:
            self.assertEqual(svc["gaps"], [],
                             f"{svc['service_id']} reported gaps on the clean case")
            self.assertEqual(svc["restoration_status"], "DEMONSTRATED")

    def test_independent_recovery_is_not_serialised(self):
        """Two services recovering independently must not be read as one sequence.

        Service B's restore legitimately completes BEFORE service A's disruption.
        A global cross-product of disruption x restore_completed calls that an
        inversion. It is not one -- the two services have no dependency between
        them and their recoveries are genuinely parallel.
        """
        case = mf.clean_case()
        # SVC-IAM and SVC-RIS have a dependency; drop it so they are truly parallel.
        for svc in case["recovery"]["services"]:
            if svc["service_id"] == "SVC-RIS":
                svc["dependencies"] = []
                svc["exercise"]["dependency_results"] = []
        # Pull SVC-IAM's whole recovery earlier than SVC-RIS's disruption.
        moved = {"EVT-IAM-DISRUPT": "2026-09-17T18:00:00Z",
                 "EVT-IAM-PIT": "2026-09-17T17:50:00Z",
                 "EVT-IAM-RESTORE": "2026-09-17T18:30:00Z",
                 "EVT-IAM-BIZVERIFY": "2026-09-17T18:40:00Z",
                 "EVT-IAM-BACKUP": "2026-09-17T17:00:00Z"}
        for e in case["events"]:
            if e["event_id"] in moved:
                e["observed_at"] = moved[e["event_id"]]
        for svc in case["recovery"]["services"]:
            if svc["service_id"] == "SVC-IAM":
                ex = svc["exercise"]
                ex["disruption"]["asserted_at"] = moved["EVT-IAM-DISRUPT"]
                ex["restore_completed"]["asserted_at"] = moved["EVT-IAM-RESTORE"]
        report = assess_dict(case)
        self.assertNotIn("ORDERING_INVERSION", codes(report),
                         "independent parallel recovery was flagged as an inversion")
        self.assertEqual(report["status"], "AGREED")

    def test_pre_release_verification_before_deploy_is_not_an_inversion(self):
        """A staging verification legitimately precedes the deployment."""
        report = rrc.assess(rrc.load_case(os.path.join(HERE, "case.json")))
        self.assertNotIn("ORDERING_INVERSION", codes(report))
        stage = [r for r in report["environment"]["verifications"]
                 if r["verification_id"] == "VER-STAGE"]
        self.assertEqual(len(stage), 1)
        self.assertFalse(stage[0]["same_environment_as_deployment"])

    def test_component_without_its_own_clock_is_not_a_disagreement(self):
        """`asserted_at: null` is an honest 'I carry no clock', not a finding."""
        case = mf.clean_case()
        case["release"]["deployment"]["deployed"]["asserted_at"] = None
        report = assess_dict(case)
        self.assertEqual(report["findings"], [])
        rows = [r for r in report["timeline"]["agreement_matrix"]
                if r["event_id"] == "EVT-DEPLOY"]
        self.assertTrue(any(r["agreement"] == "NO_ASSERTION" for r in rows))


# ---------------------------------------------------------------------------
# Each defect class is caught, and caught alone
# ---------------------------------------------------------------------------

class TestDefectsAreCaught(unittest.TestCase):

    def test_each_fixture_fires_its_own_code(self):
        for name, expected in sorted(DEFECT_EXPECTATIONS.items()):
            with self.subTest(fixture=name):
                report = rrc.assess(load_fixture(name))
                self.assertIn(expected, codes(report),
                              f"{name} did not fire {expected}")
                self.assertEqual(rrc.exit_code(report), 1)

    def test_each_fixture_fires_nothing_else(self):
        """Isolation: one mutation, one code. Anything extra is a false positive."""
        for name, expected in sorted(DEFECT_EXPECTATIONS.items()):
            with self.subTest(fixture=name):
                report = rrc.assess(load_fixture(name))
                self.assertEqual(codes(report), {expected},
                                 f"{name} fired extra codes: {codes(report) - {expected}}")

    def test_contradictions_outrank_gaps_in_the_aggregate(self):
        for name in ("timeline-disagreement", "ordering-inversion", "id-collision"):
            with self.subTest(fixture=name):
                self.assertEqual(rrc.assess(load_fixture(name))["status"], "CONTRADICTIONS")
        for name in ("unresolved-source-id", "unsupported-recovery-claim",
                     "unknown-timestamp", "environment-difference"):
            with self.subTest(fixture=name):
                self.assertEqual(rrc.assess(load_fixture(name))["status"], "GAPS")

    def test_timeline_disagreement_names_both_values(self):
        """'A cycle exists' is useless. The finding must carry both claims."""
        report = rrc.assess(load_fixture("timeline-disagreement"))
        finding = next(f for f in report["findings"]
                       if f["code"] == "TIMELINE_DISAGREEMENT")
        self.assertIn("22:05:00", finding["detail"])
        self.assertIn("22:00:00", finding["detail"])
        self.assertIn("EVT-DEPLOY", finding["subject"])
        self.assertEqual(finding["component"], "provenance")

    def test_ordering_inversion_names_both_events_and_the_rule(self):
        report = rrc.assess(load_fixture("ordering-inversion"))
        finding = next(f for f in report["findings"] if f["code"] == "ORDERING_INVERSION")
        self.assertIn("DISRUPTION_BEFORE_RESTORE", finding["detail"])
        self.assertIn("EVT-RIS-DISRUPT", finding["cites"])
        self.assertIn("EVT-RIS-RESTORE", finding["cites"])
        self.assertIn("service:SVC-RIS", finding["detail"])


# ---------------------------------------------------------------------------
# UNKNOWN discipline -- an absent input never becomes a pass or a zero
# ---------------------------------------------------------------------------

class TestUnknownDiscipline(unittest.TestCase):

    def test_unknown_timestamp_is_unorderable_and_never_defaults(self):
        report = rrc.assess(load_fixture("unknown-timestamp"))
        self.assertIn("EVT-DEPLOY", report["timeline"]["unorderable_events"])
        touching = [r for r in report["timeline"]["ordering_checks"]
                    if "EVT-DEPLOY" in (r["earlier"], r["later"])]
        self.assertTrue(touching, "no ordering rule referenced the unknown event")
        for row in touching:
            self.assertEqual(row["result"], "UNKNOWN",
                             "an unknown endpoint was resolved to a pass or a violation")
        self.assertNotIn("ORDERING_INVERSION", codes(report))

    def test_unknown_timestamp_does_not_become_a_zero_or_a_pass(self):
        report = rrc.assess(load_fixture("unknown-timestamp"))
        self.assertNotEqual(report["status"], "AGREED")
        row = next(r for r in report["timeline"]["agreement_matrix"]
                   if r["event_id"] == "EVT-DEPLOY")
        self.assertIsNone(row["register_observed_at"])

    def test_register_is_not_backfilled_from_a_component_assertion(self):
        """If the register is UNKNOWN but a component asserts a time, say so.

        The wrong behaviour is to quietly adopt the component's value, which
        invents a timeline point nobody recorded.
        """
        case = mf.clean_case()
        for e in case["events"]:
            if e["event_id"] == "EVT-DEPLOY":
                e["observed_at"] = None
        report = assess_dict(case)
        self.assertIn("REGISTER_UNKNOWN_BUT_ASSERTED", codes(report))
        row = next(r for r in report["timeline"]["agreement_matrix"]
                   if r["event_id"] == "EVT-DEPLOY")
        self.assertIsNone(row["register_observed_at"])

    def test_missing_rpo_inputs_stay_unknown_rather_than_zero(self):
        case = mf.clean_case()
        for e in case["events"]:
            if e["event_id"] == "EVT-IAM-PIT":
                e["observed_at"] = None
        report = assess_dict(case)
        svc = next(s for s in report["recovery"]["services"]
                   if s["service_id"] == "SVC-IAM")
        self.assertIsNone(svc["observed_rpo_minutes"])
        self.assertEqual(svc["rpo_result"], "UNKNOWN")

    def test_no_score_or_ranking_is_emitted_anywhere(self):
        report = rrc.assess(rrc.load_case(os.path.join(HERE, "case.json")))
        # `interpretation_boundary` is the block that explicitly DENIES these
        # notions, so scanning it for their names is a false positive on the
        # disclaimer itself. Scan everything else.
        body = {k: v for k, v in report.items() if k != "interpretation_boundary"}
        blob = json.dumps(body).lower()
        for banned in ("maturity", "percentile", "peer_rank", "score_out_of",
                       "grade", "certified", "compliant"):
            self.assertNotIn(banned, blob, f"report leaked a {banned} notion")
        self.assertFalse(report["interpretation_boundary"]["university_finding"])
        self.assertFalse(
            report["interpretation_boundary"]["maturity_or_confidence_score_emitted"])


# ---------------------------------------------------------------------------
# Recovery claims must follow actual verification records
# ---------------------------------------------------------------------------

class TestRecoveryClaimSupport(unittest.TestCase):

    def test_unsupported_business_claim_cannot_reach_demonstrated(self):
        report = rrc.assess(load_fixture("unsupported-recovery-claim"))
        svc = next(s for s in report["recovery"]["services"]
                   if s["service_id"] == "SVC-RIS")
        self.assertEqual(svc["business_verification"], "NOT_EVIDENCED")
        self.assertNotEqual(svc["restoration_status"], "DEMONSTRATED")
        self.assertEqual(svc["restoration_status"], "PARTIAL")

    def test_dangling_source_id_downgrades_rather_than_passes(self):
        report = rrc.assess(load_fixture("unresolved-source-id"))
        svc = next(s for s in report["recovery"]["services"]
                   if s["service_id"] == "SVC-IAM")
        self.assertEqual(svc["backup_status"], "UNKNOWN")
        self.assertNotEqual(svc["restoration_status"], "DEMONSTRATED")

    def test_interview_only_evidence_stays_unknown(self):
        """UIOWA-057's rule, consumed rather than re-litigated."""
        case = mf.clean_case()
        for row in case["evidence"]:
            if row["evidence_id"] == "EV-SYN-IAM-BACKUP":
                row["kind"] = "interview"
        report = assess_dict(case)
        svc = next(s for s in report["recovery"]["services"]
                   if s["service_id"] == "SVC-IAM")
        self.assertEqual(svc["backup_status"], "UNKNOWN")
        self.assertTrue(any("interview" in g for g in svc["gaps"]))

    def test_restoration_status_cannot_be_asserted_by_the_input(self):
        """There must be no input field that sets the verdict directly."""
        case = mf.clean_case()
        case["recovery"]["services"][0]["restoration_status"] = "DEMONSTRATED"
        with self.assertRaises(rrc.CaseError):
            rrc.validate_case(case)

    def test_service_never_exercised_is_not_demonstrated_and_not_a_failure(self):
        report = rrc.assess(rrc.load_case(os.path.join(HERE, "case.json")))
        svc = next(s for s in report["recovery"]["services"]
                   if s["service_id"] == "SVC-IAM")
        self.assertEqual(svc["restoration_status"], "NOT_DEMONSTRATED")
        self.assertTrue(any("not a failed exercise" in g for g in svc["gaps"]))
        self.assertFalse(report["interpretation_boundary"]["missing_evidence_is_failure"])
        self.assertFalse(report["interpretation_boundary"]["missing_evidence_is_a_pass"])

    def test_dependency_result_for_an_undeclared_dependency_is_reported(self):
        case = mf.clean_case()
        ex = next(s for s in case["recovery"]["services"]
                  if s["service_id"] == "SVC-RIS")["exercise"]
        ex["dependency_results"].append(
            {"dependency_id": "SVC-GHOST",
             "verified": mf.ref("EVT-RIS-DEPVERIFY", "2026-09-17T23:05:00Z"),
             "evidence_id": "EV-SYN-RIS-DEPVERIFY"})
        report = assess_dict(case)
        self.assertIn("UNDECLARED_DEPENDENCY_RESULT", codes(report))

    def test_dependency_outside_the_case_is_unresolved_not_assumed_recovered(self):
        case = mf.clean_case()
        next(s for s in case["recovery"]["services"]
             if s["service_id"] == "SVC-RIS")["dependencies"] = ["SVC-IAM", "SVC-OFFSITE"]
        report = assess_dict(case)
        self.assertIn("UNRESOLVED_DEPENDENCY", codes(report))
        svc = next(s for s in report["recovery"]["services"]
                   if s["service_id"] == "SVC-RIS")
        self.assertNotEqual(svc["restoration_status"], "DEMONSTRATED")


# ---------------------------------------------------------------------------
# The narrative case carries a strength AND a real gap
# ---------------------------------------------------------------------------

class TestNarrativeCase(unittest.TestCase):

    def setUp(self):
        self.report = rrc.assess(rrc.load_case(os.path.join(HERE, "case.json")))

    def test_contains_every_element_the_order_asks_for(self):
        env = self.report["environment"]
        self.assertEqual(env["deployed_version"], "fictional-2.3.0")   # known version
        self.assertTrue(env["environment_difference"])                  # env difference
        outcomes = {v["outcome"] for v in env["verifications"]}
        self.assertIn("FAILED", outcomes)                               # failed verification
        self.assertTrue(self.report["recovery"]["services"])            # recovery records

    def test_shows_a_real_strength(self):
        svc = next(s for s in self.report["recovery"]["services"]
                   if s["service_id"] == "SVC-ESS")
        self.assertEqual(svc["restoration_status"], "DEMONSTRATED")
        self.assertEqual(svc["backup_status"], "EVIDENCED")
        self.assertEqual(svc["dependency_verification"], "EVIDENCED")
        self.assertEqual(svc["business_verification"], "EVIDENCED")
        self.assertEqual(svc["gaps"], [])

    def test_shows_a_real_gap(self):
        svc = next(s for s in self.report["recovery"]["services"]
                   if s["service_id"] == "SVC-RIS")
        self.assertEqual(svc["restoration_status"], "PARTIAL")
        self.assertEqual(svc["dependency_verification"], "UNKNOWN")
        self.assertTrue(svc["gaps"])
        self.assertIn("UNSUPPORTED_RECOVERY_CLAIM", codes(self.report))

    def test_provenance_chain_still_links_despite_the_gaps(self):
        """A release can be fully traceable and still not be demonstrably recovered."""
        self.assertTrue(self.report["provenance"]["linked"])
        self.assertEqual(len(self.report["provenance"]["trace"]), 3)

    def test_is_labelled_fiction(self):
        self.assertIn("SYNTHETIC", self.report["fiction_notice"])
        self.assertEqual(self.report["data_class"], "synthetic")
        blob = json.dumps(self.report)
        self.assertNotIn("University of Iowa", blob.replace(
            self.report["fiction_notice"], ""))


# ---------------------------------------------------------------------------
# Hostile and missing-data input
# ---------------------------------------------------------------------------

class TestHostileInput(unittest.TestCase):

    def test_malformed_json_is_rejected_with_no_report(self):
        path = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False).name
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('{"schema_version": 1, "case_id": ')
        with self.assertRaises(rrc.CaseError):
            rrc.load_case(path)

    def test_empty_object_is_rejected(self):
        with self.assertRaises(rrc.CaseError):
            rrc.validate_case({})

    def test_json_array_root_is_rejected(self):
        with self.assertRaises(rrc.CaseError):
            rrc.validate_case([])

    def test_unknown_field_is_an_error_not_silently_dropped(self):
        case = mf.clean_case()
        case["extra_field"] = "an adapter mistake"
        with self.assertRaises(rrc.CaseError):
            rrc.validate_case(case)

    def test_duplicate_event_ids_are_rejected(self):
        case = mf.clean_case()
        case["events"].append(dict(case["events"][0]))
        with self.assertRaises(rrc.CaseError):
            rrc.validate_case(case)

    def test_duplicate_json_keys_are_rejected(self):
        path = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False).name
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('{"case_id": "a", "case_id": "b"}')
        with self.assertRaises(rrc.CaseError):
            rrc.load_case(path)

    def test_non_finite_constants_are_rejected(self):
        path = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False).name
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('{"case_id": NaN}')
        with self.assertRaises(rrc.CaseError):
            rrc.load_case(path)

    def test_empty_service_list_is_never_a_pass(self):
        case = mf.clean_case()
        case["recovery"]["services"] = []
        with self.assertRaises(rrc.CaseError) as ctx:
            rrc.validate_case(case)
        self.assertIn("never a pass", str(ctx.exception))

    def test_timestamp_without_offset_is_rejected(self):
        case = mf.clean_case()
        case["events"][0]["observed_at"] = "2026-09-17T14:00:00"
        with self.assertRaises(rrc.CaseError):
            rrc.validate_case(case)

    def test_timestamp_without_seconds_is_rejected(self):
        case = mf.clean_case()
        case["events"][0]["observed_at"] = "2026-09-17T14:00Z"
        with self.assertRaises(rrc.CaseError):
            rrc.validate_case(case)

    def test_missing_file_is_a_clean_error(self):
        with self.assertRaises(rrc.CaseError):
            rrc.load_case(os.path.join(HERE, "definitely-not-here.json"))

    def test_wrong_schema_version_is_rejected(self):
        case = mf.clean_case()
        case["schema_version"] = 99
        with self.assertRaises(rrc.CaseError):
            rrc.validate_case(case)

    def test_unreferenced_but_unresolvable_event_reference_is_reported(self):
        case = mf.clean_case()
        case["release"]["deployment"]["deployed"]["event_id"] = "EVT-DOES-NOT-EXIST"
        report = assess_dict(case)
        self.assertIn("UNRESOLVED_EVENT_ID", codes(report))
        self.assertNotEqual(report["status"], "AGREED")

    def test_negative_rpo_target_is_rejected(self):
        case = mf.clean_case()
        case["recovery"]["services"][0]["target_rpo_minutes"] = -5
        with self.assertRaises(rrc.CaseError):
            rrc.validate_case(case)


# ---------------------------------------------------------------------------
# Projections stay inside the sibling kits' contracts
# ---------------------------------------------------------------------------

class TestProjections(unittest.TestCase):

    def setUp(self):
        self.case = rrc.load_case(os.path.join(HERE, "case.json"))

    def test_provenance_projection_matches_the_057_packet_contract(self):
        packet = rrc.project_provenance(self.case)
        self.assertEqual(set(packet), set(PROVENANCE_ROOT))
        self.assertEqual(packet["schema_version"], 1)
        self.assertEqual(set(packet["deployments"][0]), set(PROVENANCE_DEPLOYMENT))
        self.assertEqual(set(packet["artifacts"][0]), set(PROVENANCE_ARTIFACT))
        self.assertEqual(set(packet["builds"][0]), set(PROVENANCE_BUILD))
        self.assertEqual(set(packet["sources"][0]), set(PROVENANCE_SOURCE))
        self.assertEqual(set(packet["evidence"][0]), set(PROVENANCE_EVIDENCE))

    def test_recovery_projection_matches_the_068_record_contract(self):
        records = rrc.project_recovery(self.case)
        self.assertEqual(set(records), {"assessment_id", "synthetic", "services"})
        self.assertTrue(records["synthetic"])
        for svc in records["services"]:
            self.assertEqual(set(svc), set(RECOVERY_SERVICE))
            self.assertEqual(set(svc["backup"]), {"last_successful_at", "evidence_id"})
            if svc["exercise"] is not None:
                self.assertEqual(set(svc["exercise"]), set(RECOVERY_EXERCISE))

    def test_projections_agree_on_the_shared_timeline(self):
        """The whole point: both exports must show the same instant for one event."""
        packet = rrc.project_provenance(self.case)
        records = rrc.project_recovery(self.case)
        ess = next(s for s in records["services"] if s["service_id"] == "SVC-ESS")
        ris = next(s for s in records["services"] if s["service_id"] == "SVC-RIS")
        # Both services observed the SAME disruption event; both exports must agree.
        self.assertEqual(ess["exercise"]["disruption_at"],
                         ris["exercise"]["disruption_at"])
        deploy = packet["deployments"][0]["observed_at"]
        self.assertEqual(deploy, "2026-09-17T22:00:00+00:00")
        self.assertLess(deploy, ess["exercise"]["disruption_at"])

    def test_projections_preserve_unknown_as_null(self):
        records = rrc.project_recovery(self.case)
        ris = next(s for s in records["services"] if s["service_id"] == "SVC-RIS")
        dep = ris["exercise"]["dependency_results"][0]
        self.assertIsNone(dep["verified_at"],
                          "an UNKNOWN time was materialised in the projection")
        self.assertIsNone(ris["exercise"]["business_verified_at"])

    def test_environment_projection_marks_coverage(self):
        view = rrc.project_environment(self.case)
        by_id = {v["verification_id"]: v for v in view["verifications"]}
        self.assertFalse(by_id["VER-STAGE"]["covers_deployment_environment"])
        self.assertTrue(by_id["VER-PROD"]["covers_deployment_environment"])

    def test_provenance_contract_has_not_drifted_from_the_sibling_lane(self):
        """Live drift guard: re-read 057's real schema when the lane is present.

        Skips cleanly in a staging checkout where the sibling is absent -- a skip
        is honest; a silent pass would not be.
        """
        sibling = os.path.join(HERE, os.pardir, "uiowa_rfq_18649_release_provenance",
                               "packet.schema.json")
        if not os.path.exists(sibling):
            self.skipTest("sibling lane uiowa_rfq_18649_release_provenance not present; "
                          "contract drift cannot be checked from here")
        with open(sibling, encoding="utf-8") as fh:
            schema = json.load(fh)
        self.assertEqual(set(schema["required"]), set(PROVENANCE_ROOT))
        props = schema["properties"]
        pairs = (("deployments", PROVENANCE_DEPLOYMENT), ("artifacts", PROVENANCE_ARTIFACT),
                 ("builds", PROVENANCE_BUILD), ("sources", PROVENANCE_SOURCE),
                 ("evidence", PROVENANCE_EVIDENCE))
        for name, expected in pairs:
            with self.subTest(array=name):
                self.assertEqual(set(props[name]["items"]["required"]), set(expected),
                                 f"057's {name} contract changed; update the projection")


# ---------------------------------------------------------------------------
# Determinism and CLI
# ---------------------------------------------------------------------------

class TestDeterminismAndCli(unittest.TestCase):

    def test_two_runs_are_byte_identical(self):
        """No wall clock anywhere -- two operators on different days get one answer."""
        a = rrc.assess(rrc.load_case(os.path.join(HERE, "case.json")))
        b = rrc.assess(rrc.load_case(os.path.join(HERE, "case.json")))
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))

    def test_fixtures_on_disk_match_the_generator(self):
        """A hand-edited fixture would break the one-mutation property."""
        with open(os.path.join(HERE, "case.json"), encoding="utf-8") as fh:
            on_disk = fh.read().rstrip("\n")
        self.assertEqual(json.dumps(mf.narrative_case(), sort_keys=True, indent=2),
                         on_disk)
        for name, (mutate, _why) in sorted(mf.MUTATIONS.items()):
            with self.subTest(fixture=name):
                expected = mutate(copy.deepcopy(mf.clean_case()))
                with open(os.path.join(FIXTURES, f"{name}.json"), encoding="utf-8") as fh:
                    actual = json.load(fh)
                self.assertEqual(expected, actual,
                                 f"fixtures/{name}.json differs from make_fixtures.py")

    def test_cli_exit_codes(self):
        clean = subprocess.run([sys.executable, ENGINE,
                                os.path.join(FIXTURES, "clean.json"), "--format", "json"],
                               capture_output=True, text=True)
        self.assertEqual(clean.returncode, 0, clean.stderr)
        broken = subprocess.run([sys.executable, ENGINE,
                                 os.path.join(FIXTURES, "ordering-inversion.json"),
                                 "--format", "json"], capture_output=True, text=True)
        self.assertEqual(broken.returncode, 1)

    def test_cli_malformed_input_exits_two_and_emits_no_report(self):
        path = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False).name
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("not json at all")
        proc = subprocess.run([sys.executable, ENGINE, path], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout.strip(), "",
                         "a malformed input produced report output")
        self.assertIn("error:", proc.stderr)

    def test_cli_schema_runs_without_a_case(self):
        proc = subprocess.run([sys.executable, ENGINE, "--schema"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        schema = json.loads(proc.stdout)
        self.assertEqual(schema["schema_version"], 1)
        self.assertIn("release_scope", schema["ordering_rules"])

    def test_renderers_produce_usable_output(self):
        report = rrc.assess(rrc.load_case(os.path.join(HERE, "case.json")))
        md = rrc.render_markdown(report)
        self.assertIn("Cross-component status", md)
        self.assertIn("SVC-ESS", md)
        self.assertIn("SYNTHETIC", md)
        csv_text = rrc.render_csv(report)
        header = csv_text.splitlines()[0]
        self.assertEqual(header,
                         "event_id,event_kind,register_observed_at,asserting_component,"
                         "asserting_path,asserted_at,agreement")
        self.assertGreater(len(csv_text.splitlines()), 5)

    def test_markdown_escapes_pipes_so_the_table_survives(self):
        """A pipe in an identifier must not shift every later table column."""
        case = mf.clean_case()
        case["release"]["deployment"]["environment"] = "ess|prod"
        case["environments"][0]["environment_id"] = "ess|prod"
        case["verifications"][0]["environment"] = "ess|prod"
        report = assess_dict(case)
        self.assertEqual(report["findings"], [],
                         "renaming an environment should not create findings")
        md = rrc.render_markdown(report)
        rows = [l for l in md.splitlines()
                if l.startswith("| `VER-") or l.startswith("| `SVC-")]
        self.assertTrue(rows, "no table rows rendered")
        for line in rows:
            # A correctly escaped row has only its own structural pipes.
            unescaped = line.replace("\\|", "")
            self.assertIn(unescaped.count("|"), (6, 8),
                          f"unescaped pipe shifted a row: {line}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
