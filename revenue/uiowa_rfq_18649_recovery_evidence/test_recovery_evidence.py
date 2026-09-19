#!/usr/bin/env python3
"""Tests for the UIOWA-068 recovery evidence analyzer.

These assert behaviour, not shape. The ones that matter most are the ones that
would fail if the tool ever quietly turned an absent record into a pass:

  * a tabletop cannot become restoration evidence
  * "not_attempted" cannot become a passing function check
  * an unmeasured dependency cannot become an optimistic chain time
  * a missing record cannot become a zero

Run:  python3 -m unittest -v test_recovery_evidence
"""

import copy
import csv
import json
import os
import shutil
import tempfile
import unittest

import recovery_evidence as re_mod


HERE = os.path.dirname(os.path.abspath(__file__))
ESTATE = os.path.join(HERE, "fixtures", "synthetic_estate.json")


def load_report(path=ESTATE):
    return re_mod.analyse(re_mod.load_estate(path))


def by_id(report):
    return {r["service_id"]: r for r in report["services"]}


def write_temp_estate(payload):
    handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                         encoding="utf-8")
    json.dump(payload, handle)
    handle.close()
    return handle.name


def raw_estate():
    with open(ESTATE, encoding="utf-8") as handle:
        return json.load(handle)


def minimal_estate(services, backups=None, exercises=None, as_of="2026-09-15"):
    return {
        "fiction_notice": "SYNTHETIC test fixture.",
        "as_of": as_of,
        "services": services,
        "backups": backups or [],
        "exercises": exercises or [],
    }


class LadderRules(unittest.TestCase):
    """The rules that stop a well-written record from becoming evidence."""

    @classmethod
    def setUpClass(cls):
        cls.report = load_report()
        cls.rows = by_id(cls.report)

    def test_tabletop_never_lifts_a_service_above_r2(self):
        # SVC-REG has a COMPLETED tabletop exercise and a healthy backup.
        # A discussion of a restore is not a restore.
        reg = self.rows["SVC-REG"]
        self.assertEqual(reg["evidence_rung"], "R2")
        self.assertIsNone(reg["latest_restore_exercise"])
        self.assertTrue(
            any("tabletop" in d and "cannot lift" in d for d in reg["rung_diagnostics"]),
            "the tabletop exclusion must be stated in the diagnostics, not silent")

    def test_restore_without_function_check_stops_at_r3(self):
        # SVC-STORE restored successfully. Nobody checked the restored objects.
        store = self.rows["SVC-STORE"]
        self.assertEqual(store["evidence_rung"], "R3")
        self.assertIsNone(store["verifying_exercise"])

    def test_not_attempted_is_never_a_pass(self):
        store = self.rows["SVC-STORE"]
        codes = [f["code"] for f in self.report["findings"]
                 if f["service_id"] == "SVC-STORE"]
        self.assertIn("RESTORE_DEMONSTRATED_FUNCTION_UNVERIFIED", codes)
        self.assertNotEqual(store["evidence_rung"], "R4")

    def test_failed_function_check_is_distinct_from_not_attempted(self):
        # SVC-BKP-CTL ran the check and it failed. That is a different and more
        # useful state than never having looked, and must surface separately.
        ctl = self.rows["SVC-BKP-CTL"]
        self.assertEqual(ctl["evidence_rung"], "R3")
        ctl_codes = [f["code"] for f in self.report["findings"]
                     if f["service_id"] == "SVC-BKP-CTL"]
        store_codes = [f["code"] for f in self.report["findings"]
                       if f["service_id"] == "SVC-STORE"]
        self.assertIn("FUNCTION_CHECK_FAILED", ctl_codes)
        self.assertNotIn("FUNCTION_CHECK_FAILED", store_codes)

    def test_passing_check_without_evidence_reference_does_not_reach_r4(self):
        # Hostile: a record that claims a pass but points at nothing.
        payload = minimal_estate(
            services=[{"service_id": "S1", "name": "S1", "tier": 1,
                       "business_function": "Do the thing.", "owner_role": "A team",
                       "stated_rto_minutes": 100, "stated_rpo_minutes": 100,
                       "depends_on": []}],
            backups=[{"backup_id": "B1", "service_id": "S1", "scope": "full",
                      "schedule": "daily", "last_job_status": "success",
                      "last_job_at": "2026-09-15"}],
            exercises=[{"exercise_id": "X1", "service_id": "S1", "date": "2026-09-01",
                        "kind": "full_restore", "outcome": "completed",
                        "measured_restore_complete_minutes": 50,
                        "business_function_check": {"performed": True,
                                                    "result": "pass",
                                                    "evidence_ref": None}}])
        path = write_temp_estate(payload)
        try:
            row = by_id(load_report(path))["S1"]
            self.assertEqual(row["evidence_rung"], "R3")
            self.assertTrue(any("no evidence reference" in d
                                for d in row["rung_diagnostics"]))
        finally:
            os.unlink(path)

    def test_failed_restore_attempt_does_not_earn_r3(self):
        grade = self.rows["SVC-GRADE"]
        self.assertEqual(grade["evidence_rung"], "R1")
        self.assertIsNone(grade["latest_restore_exercise"])
        self.assertTrue(any("did not complete" in d for d in grade["rung_diagnostics"]))

    def test_green_but_ancient_backup_is_stale_not_completing(self):
        # BK-GRADE-01 reports success. It last ran 19 days ago on a daily
        # schedule. A dashboard would show it green.
        grade = self.rows["SVC-GRADE"]
        self.assertEqual(grade["backup_health"], "STALE")
        self.assertEqual(grade["last_backup_age_days"], 19)

    def test_stale_backup_caps_a_higher_rung_and_reports_the_cap(self):
        # Hostile: perfect restoration evidence sitting on a dead backup job.
        # A restore in the past does not prove today's data can be restored.
        payload = minimal_estate(
            services=[{"service_id": "S1", "name": "S1", "tier": 1,
                       "business_function": "Do the thing.", "owner_role": "A team",
                       "stated_rto_minutes": 100, "stated_rpo_minutes": 100,
                       "depends_on": []}],
            backups=[{"backup_id": "B1", "service_id": "S1", "scope": "full",
                      "schedule": "daily", "last_job_status": "success",
                      "last_job_at": "2026-01-01"}],
            exercises=[{"exercise_id": "X1", "service_id": "S1", "date": "2026-02-01",
                        "kind": "full_restore", "outcome": "completed",
                        "measured_restore_complete_minutes": 50,
                        "business_function_check": {"performed": True,
                                                    "result": "pass",
                                                    "evidence_ref": "X1/log"}}])
        path = write_temp_estate(payload)
        try:
            row = by_id(load_report(path))["S1"]
            self.assertEqual(row["rung_uncapped"], "R4")
            self.assertEqual(row["evidence_rung"], "R2")
            self.assertEqual(row["rung_capped_from"], "R4")
            self.assertIn("STALE", row["cap_reason"])
        finally:
            os.unlink(path)

    def test_no_records_is_r0_and_never_a_zero(self):
        dirsync = self.rows["SVC-DIRSYNC"]
        self.assertEqual(dirsync["evidence_rung"], "R0")
        self.assertEqual(dirsync["backup_health"], "NO_RECORD")
        # The absent measurement must be None -> "UNKNOWN", never 0.
        self.assertIsNone(dirsync["own_measured_restore_minutes"])
        self.assertIsNone(dirsync["effective_recovery_minutes"])
        self.assertEqual(dirsync["effective_recovery_status"], "UNKNOWN")
        self.assertEqual(dirsync["rto_status"], "UNKNOWN")


class ChainArithmetic(unittest.TestCase):
    """The dependency closure, and the asymmetry between proving a breach and
    proving compliance."""

    @classmethod
    def setUpClass(cls):
        cls.report = load_report()
        cls.rows = by_id(cls.report)

    def test_unknown_propagates_and_does_not_become_the_best_case(self):
        # SVC-IDP measured its own restore at 95 minutes. It depends on
        # SVC-DIRSYNC, which nobody has ever restored. The chain is UNKNOWN.
        idp = self.rows["SVC-IDP"]
        self.assertEqual(idp["own_measured_restore_minutes"], 95)
        self.assertEqual(idp["effective_recovery_status"], "UNKNOWN")
        self.assertIsNone(idp["effective_recovery_minutes"])
        self.assertIn("SVC-DIRSYNC", idp["unmeasured_links"])
        self.assertEqual(idp["rto_status"], "UNKNOWN")

    def test_fully_measured_chain_yields_a_number(self):
        sis = self.rows["SVC-SIS-DB"]
        self.assertEqual(sis["effective_recovery_status"], "MEASURED")
        self.assertEqual(sis["effective_recovery_minutes"], 320)

    def test_lower_bound_is_reported_even_when_the_chain_is_unknown(self):
        reg = self.rows["SVC-REG"]
        self.assertEqual(reg["effective_recovery_status"], "UNKNOWN")
        self.assertIsNone(reg["effective_recovery_minutes"])
        self.assertEqual(reg["chain_lower_bound_minutes"], 320)

    def test_partial_evidence_can_prove_exceeded(self):
        # 320 measured minutes in the chain against a stated 240. Conclusive
        # even though other links are unmeasured: the truth can only be worse.
        reg = self.rows["SVC-REG"]
        self.assertEqual(reg["rto_status"], "EXCEEDED")

    def test_partial_evidence_can_never_prove_compliance(self):
        # SVC-GRADE's lower bound (320) is comfortably inside its stated 480,
        # but the chain has unmeasured links. That is UNKNOWN, not a pass.
        grade = self.rows["SVC-GRADE"]
        self.assertEqual(grade["chain_lower_bound_minutes"], 320)
        self.assertLess(grade["chain_lower_bound_minutes"], grade["stated_rto_minutes"])
        self.assertEqual(grade["rto_status"], "UNKNOWN")
        self.assertNotEqual(grade["rto_status"], "WITHIN_STATED_RTO")

    def test_compliance_requires_a_complete_measured_chain(self):
        store = self.rows["SVC-STORE"]
        self.assertEqual(store["effective_recovery_status"], "MEASURED")
        self.assertEqual(store["rto_status"], "WITHIN_STATED_RTO")

    def test_circular_recovery_dependency_terminates_and_is_reported(self):
        # The backup control plane needs the catalog; the catalog needs the
        # control plane. Each measured its own restore assuming the other was
        # already up. This must not hang, and must not produce a number.
        ctl = self.rows["SVC-BKP-CTL"]
        self.assertEqual(sorted(ctl["chain_cycle"]), ["SVC-BKP-CTL", "SVC-VAULT"])
        self.assertEqual(ctl["effective_recovery_status"], "UNKNOWN")
        self.assertIsNone(ctl["effective_recovery_minutes"])
        codes = [f["code"] for f in self.report["findings"]
                 if f["service_id"] == "SVC-BKP-CTL"]
        self.assertIn("CIRCULAR_RECOVERY_DEPENDENCY", codes)

    def test_self_referencing_service_does_not_hang(self):
        payload = minimal_estate(
            services=[{"service_id": "S1", "name": "S1", "tier": 1,
                       "business_function": "Do the thing.", "owner_role": "A team",
                       "stated_rto_minutes": 100, "stated_rpo_minutes": 100,
                       "depends_on": ["S1"]}])
        path = write_temp_estate(payload)
        try:
            row = by_id(load_report(path))["S1"]
            self.assertIn("S1", row["chain_cycle"])
            self.assertEqual(row["effective_recovery_status"], "UNKNOWN")
        finally:
            os.unlink(path)

    def test_dangling_dependency_reference_is_surfaced_not_dropped(self):
        lms = self.rows["SVC-LMS-INT"]
        self.assertEqual(lms["chain_missing_records"], ["SVC-GHOST-API"])
        self.assertEqual(lms["effective_recovery_status"], "UNKNOWN")
        codes = [f["code"] for f in self.report["findings"]
                 if f["service_id"] == "SVC-LMS-INT"]
        self.assertIn("MISSING_DEPENDENCY_RECORD", codes)

    def test_blast_radius_counts_transitive_dependents(self):
        # SVC-IDP, SVC-REG and SVC-GRADE all rest on SVC-DIRSYNC.
        self.assertEqual(self.rows["SVC-DIRSYNC"]["blast_radius"], 3)
        self.assertEqual(self.rows["SVC-REG"]["blast_radius"], 0)


class Findings(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.report = load_report()
        cls.rows = by_id(cls.report)

    def test_verified_service_on_unverified_dependency_is_flagged(self):
        # The finding a green dashboard hides: SVC-IDP is fully verified and
        # rests on a service with no recovery evidence at all.
        matches = [f for f in self.report["findings"]
                   if f["code"] == "VERIFIED_SERVICE_ON_UNVERIFIED_DEPENDENCY"]
        self.assertTrue(matches)
        self.assertEqual(matches[0]["service_id"], "SVC-IDP")
        self.assertIn("SVC-DIRSYNC=R0", matches[0]["evidence"])

    def test_stale_backup_is_a_high_severity_finding(self):
        matches = [f for f in self.report["findings"]
                   if f["code"] == "BACKUP_REPORTS_SUCCESS_BUT_IS_STALE"]
        self.assertEqual([f["service_id"] for f in matches], ["SVC-GRADE"])
        self.assertEqual(matches[0]["severity"], "high")

    def test_config_only_backup_yields_unknown_rpo_not_a_failure(self):
        # SVC-REG's only backup is config-only. The records cannot speak to
        # data loss, so the answer is UNKNOWN -- not a pass and not a fail.
        reg = self.rows["SVC-REG"]
        self.assertEqual(reg["rpo_status"], "UNKNOWN")
        self.assertIn("No data-scope backup record", reg["rpo_detail"])

    def test_rpo_shortfall_names_the_unrecorded_mechanism_possibility(self):
        sis = self.rows["SVC-SIS-DB"]
        self.assertEqual(sis["rpo_status"], "SCHEDULE_DOES_NOT_MEET_RPO")
        self.assertIn("not in these records", sis["rpo_detail"])

    def test_unknown_offsite_stays_unknown_rather_than_false(self):
        store = self.rows["SVC-STORE"]
        self.assertEqual(store["offsite_copy"], "UNKNOWN")
        codes = [f["code"] for f in self.report["findings"]
                 if f["service_id"] == "SVC-STORE"]
        self.assertIn("OFFSITE_COPY_UNKNOWN", codes)

    def test_every_finding_carries_a_service_and_a_statement(self):
        for finding in self.report["findings"]:
            self.assertTrue(finding["service_id"])
            self.assertTrue(finding["statement"])
            self.assertIn(finding["severity"], ("high", "medium", "low"))

    def test_no_maturity_or_compliance_language_in_output(self):
        # The rungs are evidence statements. They must not be dressed up as a
        # maturity score, a certification, or a peer comparison.
        text = re_mod.render_report(self.report, "SVC-REG").lower()
        for banned in ("maturity level", "compliant", "certified", "percentile",
                       "peer average", "grade of"):
            self.assertNotIn(banned, text, "banned framing %r appeared" % banned)

    def test_owners_are_roles_not_individuals(self):
        for row in self.report["services"]:
            self.assertTrue(
                row["owner_role"].endswith("team") or row["owner_role"] == "UNKNOWN",
                "owner_role %r should name a role, never a person" % row["owner_role"])


class Ranking(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.report = load_report()

    def test_highest_ranked_is_the_unevidenced_service_many_things_rest_on(self):
        top = self.report["next_exercises"][0]
        self.assertEqual(top["service_id"], "SVC-DIRSYNC")
        self.assertEqual(top["priority_score"], 32)

    def test_fully_verified_services_are_not_ranked(self):
        ranked = {e["service_id"] for e in self.report["next_exercises"]}
        self.assertNotIn("SVC-IDP", ranked)
        self.assertNotIn("SVC-SIS-DB", ranked)

    def test_every_ranked_item_shows_its_arithmetic(self):
        for item in self.report["next_exercises"]:
            self.assertIn("tier_weight", item["formula"])
            self.assertIn("= %d" % item["priority_score"], item["formula"])
            self.assertTrue(item["recommended_exercise"])

    def test_ranking_order_is_deterministic_under_tie(self):
        # SVC-STORE and SVC-VAULT both score 12; blast radius breaks the tie.
        order = [e["service_id"] for e in self.report["next_exercises"]]
        self.assertLess(order.index("SVC-STORE"), order.index("SVC-VAULT"))


class HostileInput(unittest.TestCase):
    """Missing, malformed and adversarial records."""

    def test_missing_as_of_is_refused_rather_than_defaulted_to_today(self):
        payload = minimal_estate(services=[])
        del payload["as_of"]
        path = write_temp_estate(payload)
        try:
            with self.assertRaises(re_mod.EstateError) as ctx:
                re_mod.load_estate(path)
            self.assertIn("as_of", str(ctx.exception))
        finally:
            os.unlink(path)

    def test_malformed_json_is_refused_with_a_useful_message(self):
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                             encoding="utf-8")
        handle.write("{ this is not json ")
        handle.close()
        try:
            with self.assertRaises(re_mod.EstateError) as ctx:
                re_mod.load_estate(handle.name)
            self.assertIn("not valid JSON", str(ctx.exception))
        finally:
            os.unlink(handle.name)

    def test_missing_file_is_refused(self):
        with self.assertRaises(re_mod.EstateError):
            re_mod.load_estate(os.path.join(HERE, "does-not-exist.json"))

    def test_unparseable_date_becomes_unknown_and_is_reported(self):
        payload = minimal_estate(
            services=[{"service_id": "S1", "name": "S1", "tier": 1,
                       "business_function": "Do the thing.", "owner_role": "A team",
                       "stated_rto_minutes": 100, "stated_rpo_minutes": 100,
                       "depends_on": []}],
            backups=[{"backup_id": "B1", "service_id": "S1", "scope": "full",
                      "schedule": "daily", "last_job_status": "success",
                      "last_job_at": "last Tuesday"}])
        path = write_temp_estate(payload)
        try:
            estate = re_mod.load_estate(path)
            report = re_mod.analyse(estate)
            row = by_id(report)["S1"]
            # A success with no usable timestamp cannot be called current.
            self.assertEqual(row["backup_health"], "UNKNOWN")
            self.assertIsNone(row["last_backup_age_days"])
            self.assertTrue(any("unparseable date" in i for i in report["load_issues"]))
        finally:
            os.unlink(path)

    def test_records_pointing_at_unknown_services_are_reported_not_dropped(self):
        payload = minimal_estate(
            services=[],
            backups=[{"backup_id": "B9", "service_id": "GHOST", "scope": "full",
                      "schedule": "daily", "last_job_status": "success",
                      "last_job_at": "2026-09-15"}],
            exercises=[{"exercise_id": "X9", "service_id": "GHOST",
                        "date": "2026-09-01", "kind": "full_restore",
                        "outcome": "completed"}])
        path = write_temp_estate(payload)
        try:
            estate = re_mod.load_estate(path)
            self.assertTrue(any("B9" in i for i in estate["load_issues"]))
            self.assertTrue(any("X9" in i for i in estate["load_issues"]))
        finally:
            os.unlink(path)

    def test_missing_business_function_check_is_not_a_pass(self):
        payload = minimal_estate(
            services=[{"service_id": "S1", "name": "S1", "tier": 1,
                       "business_function": "Do the thing.", "owner_role": "A team",
                       "stated_rto_minutes": 100, "stated_rpo_minutes": 100,
                       "depends_on": []}],
            backups=[{"backup_id": "B1", "service_id": "S1", "scope": "full",
                      "schedule": "daily", "last_job_status": "success",
                      "last_job_at": "2026-09-15"}],
            exercises=[{"exercise_id": "X1", "service_id": "S1", "date": "2026-09-01",
                        "kind": "full_restore", "outcome": "completed",
                        "measured_restore_complete_minutes": 50}])
        path = write_temp_estate(payload)
        try:
            estate = re_mod.load_estate(path)
            row = by_id(re_mod.analyse(estate))["S1"]
            self.assertEqual(row["evidence_rung"], "R3")
            self.assertTrue(any("no business_function_check" in i
                                for i in estate["load_issues"]))
        finally:
            os.unlink(path)

    def test_zero_is_preserved_and_distinct_from_missing(self):
        # A genuine measurement of 0 must survive; the tool must not treat it
        # as absent just because it is falsey.
        payload = minimal_estate(
            services=[{"service_id": "S1", "name": "S1", "tier": 1,
                       "business_function": "Do the thing.", "owner_role": "A team",
                       "stated_rto_minutes": 0, "stated_rpo_minutes": 100,
                       "depends_on": []}],
            backups=[{"backup_id": "B1", "service_id": "S1", "scope": "full",
                      "schedule": "daily", "last_job_status": "success",
                      "last_job_at": "2026-09-15"}],
            exercises=[{"exercise_id": "X1", "service_id": "S1", "date": "2026-09-01",
                        "kind": "failover", "outcome": "completed",
                        "measured_restore_complete_minutes": 0,
                        "business_function_check": {"performed": True,
                                                    "result": "pass",
                                                    "evidence_ref": "X1/log"}}])
        path = write_temp_estate(payload)
        try:
            row = by_id(load_report(path))["S1"]
            self.assertEqual(row["own_measured_restore_minutes"], 0)
            self.assertEqual(row["effective_recovery_minutes"], 0)
            self.assertEqual(row["rto_status"], "WITHIN_STATED_RTO")
        finally:
            os.unlink(path)

    def test_empty_estate_produces_an_empty_report_not_a_crash(self):
        path = write_temp_estate(minimal_estate(services=[]))
        try:
            report = load_report(path)
            self.assertEqual(report["counts"]["services"], 0)
            self.assertEqual(report["findings"], [])
            self.assertEqual(report["next_exercises"], [])
            text = re_mod.render_report(report, "SVC-NOT-THERE")
            self.assertIn("not in the estate", text)
        finally:
            os.unlink(path)

    def test_unrecognised_schedule_yields_unknown_not_a_default_cadence(self):
        payload = minimal_estate(
            services=[{"service_id": "S1", "name": "S1", "tier": 1,
                       "business_function": "Do the thing.", "owner_role": "A team",
                       "stated_rto_minutes": 100, "stated_rpo_minutes": 100,
                       "depends_on": []}],
            backups=[{"backup_id": "B1", "service_id": "S1", "scope": "full",
                      "schedule": "when we remember", "last_job_status": "success",
                      "last_job_at": "2020-01-01"}])
        path = write_temp_estate(payload)
        try:
            row = by_id(load_report(path))["S1"]
            self.assertEqual(row["backup_health"], "UNKNOWN")
            self.assertEqual(row["rpo_status"], "UNKNOWN")
        finally:
            os.unlink(path)

    def test_duplicate_service_id_is_reported(self):
        svc = {"service_id": "S1", "name": "S1", "tier": 1,
               "business_function": "Do the thing.", "owner_role": "A team",
               "stated_rto_minutes": 100, "stated_rpo_minutes": 100,
               "depends_on": []}
        path = write_temp_estate(minimal_estate(services=[svc, copy.deepcopy(svc)]))
        try:
            estate = re_mod.load_estate(path)
            self.assertTrue(any("duplicate service_id" in i
                                for i in estate["load_issues"]))
        finally:
            os.unlink(path)


class Outputs(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_cli_writes_all_three_artifacts(self):
        code = re_mod.main(["--estate", ESTATE, "--outdir", self.tmp, "--quiet"])
        self.assertEqual(code, 0)
        for name in ("recovery_evidence.json", "recovery_evidence_matrix.csv",
                     "recovery_evidence_report.md"):
            self.assertTrue(os.path.exists(os.path.join(self.tmp, name)), name)

    def test_cli_returns_nonzero_on_unusable_input(self):
        code = re_mod.main(["--estate", os.path.join(HERE, "nope.json"),
                            "--outdir", self.tmp, "--quiet"])
        self.assertEqual(code, 2)

    def test_csv_never_leaves_a_cell_blank(self):
        # A blank cell in a spreadsheet reads as zero. Absent values must say
        # UNKNOWN out loud.
        re_mod.main(["--estate", ESTATE, "--outdir", self.tmp, "--quiet"])
        path = os.path.join(self.tmp, "recovery_evidence_matrix.csv")
        with open(path, encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 9)
        for row in rows:
            for column, value in row.items():
                self.assertNotEqual(value.strip(), "",
                                    "blank cell in %s for %s" % (column,
                                                                 row["service_id"]))
        dirsync = [r for r in rows if r["service_id"] == "SVC-DIRSYNC"][0]
        self.assertEqual(dirsync["own_measured_restore_minutes"], "UNKNOWN")
        self.assertEqual(dirsync["effective_recovery_minutes"], "UNKNOWN")

    def test_csv_neutralises_formula_injection_without_losing_the_value(self):
        payload = minimal_estate(
            services=[{"service_id": "S1", "name": "=HYPERLINK(\"http://x\",\"go\")",
                       "tier": 1, "business_function": "Do the thing.",
                       "owner_role": "A team", "stated_rto_minutes": 100,
                       "stated_rpo_minutes": 100, "depends_on": []}])
        path = write_temp_estate(payload)
        try:
            re_mod.main(["--estate", path, "--outdir", self.tmp, "--quiet"])
            with open(os.path.join(self.tmp, "recovery_evidence_matrix.csv"),
                      encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertTrue(rows[0]["name"].startswith("'="))
            self.assertIn("HYPERLINK", rows[0]["name"])
        finally:
            os.unlink(path)

    def test_negative_numbers_are_not_mangled_by_the_csv_guard(self):
        self.assertEqual(re_mod._cell(-5), "-5")
        self.assertEqual(re_mod._cell("-5"), "-5")
        self.assertEqual(re_mod._cell("-SUM(A1)"), "'-SUM(A1)")

    def test_report_states_the_lower_bound_is_not_an_estimate(self):
        report = load_report()
        text = re_mod.render_report(report, "SVC-REG")
        self.assertIn("lower bound", text)
        self.assertIn("not an estimate", text)

    def test_report_is_labelled_fiction(self):
        report = load_report()
        text = re_mod.render_report(report, "SVC-REG")
        self.assertIn("SYNTHETIC", text.upper())

    def test_two_runs_produce_identical_output(self):
        # No clock, no randomness, no set iteration leaking into order.
        first = json.dumps(load_report(), indent=2, default=str)
        second = json.dumps(load_report(), indent=2, default=str)
        self.assertEqual(first, second)

    def test_report_does_not_depend_on_the_wall_clock(self):
        # The as_of date is the only time source; nothing reads datetime.now.
        with open(os.path.join(HERE, "recovery_evidence.py"), encoding="utf-8") as fh:
            source = fh.read()
        for banned in ("datetime.now", "date.today", "time.time"):
            self.assertNotIn(banned, source,
                             "%s would make the output irreproducible" % banned)


if __name__ == "__main__":
    unittest.main(verbosity=2)
