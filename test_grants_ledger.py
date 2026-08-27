#!/usr/bin/env python3
"""Fail-closed tests for the public Commons grants ledger."""

from __future__ import annotations

import ast
import copy
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("grants_ledger", ROOT / "host/grants_ledger.py")
grants_ledger = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(grants_ledger)


class GrantsLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger, cls.schema = grants_ledger.load(ROOT)
        cls.by_id = {program["id"]: program for program in cls.ledger["programs"]}

    def assert_invalid(self, broken, pattern):
        with self.assertRaisesRegex(grants_ledger.LedgerError, pattern):
            grants_ledger.validate(ROOT, broken, self.schema)

    def run_cli(self, command):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "host/grants_ledger.py"), command, "--root", str(ROOT)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        rendered = completed.stdout.strip()
        parsed = json.loads(rendered)
        self.assertEqual(rendered, json.dumps(parsed, sort_keys=True, separators=(",", ":")))
        return parsed

    def test_stable_build_invariants_without_head_dependency(self):
        self.assertEqual(grants_ledger.BASE_SHA, "e6ac397aa6f038bf83a89668c9118d63a3770d9f")
        self.assertEqual(self.ledger["generated_from_main"], grants_ledger.BASE_SHA)
        self.assertEqual(
            grants_ledger.BUILD_PATHS,
            (
                "revenue/ip/grants_ledger.schema.json",
                "revenue/ip/grants_ledger.json",
                "host/grants_ledger.py",
                "test_grants_ledger.py",
            ),
        )
        self.assertEqual(self.schema["$id"], "https://woahwhattheheck.github.io/commons/revenue/ip/grants_ledger.schema.json")

    def test_schema_ledger_and_exact_ids_validate(self):
        from test_outcome_commerce import MiniSchemaValidator

        self.assertEqual(self.schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        MiniSchemaValidator(ROOT / "revenue/ip").validate_file(
            self.ledger, "grants_ledger.schema.json"
        )
        result = grants_ledger.validate(ROOT, self.ledger, self.schema)
        self.assertEqual(result["status"], "VALID")
        ids = [program["id"] for program in self.ledger["programs"]]
        self.assertEqual(tuple(ids), grants_ledger.EXPECTED_IDS)
        self.assertEqual(len(ids), len(set(ids)))
        patent_ids = {
            entry["id"]
            for entry in json.loads((ROOT / "revenue/ip/patent_docket.json").read_text(encoding="utf-8"))["entries"]
        }
        self.assertTrue(set(ids).isdisjoint(patent_ids))

    def test_public_schema_matches_runtime_fail_closed_rules(self):
        from test_outcome_commerce import MiniSchemaValidator, SchemaError

        validator = MiniSchemaValidator(ROOT / "revenue/ip")
        broken_values = []

        bad_date = copy.deepcopy(self.ledger)
        bad_date["programs"][0]["deadline"]["date"] = "2026-02-30"
        broken_values.append(bad_date)

        bad_time = copy.deepcopy(self.ledger)
        bad_time["programs"][0]["deadline"]["time"] = "29:59"
        broken_values.append(bad_time)

        credential_url = copy.deepcopy(self.ledger)
        credential_url["programs"][0]["official_urls"][0] = "https://user:secret@example.com/program"
        credential_url["programs"][0]["evidence_urls"][0] = "https://user:secret@example.com/program"
        broken_values.append(credential_url)

        for malformed_url in (
            "https:///program",
            "https://example.com:bad/program",
            "https://./program",
        ):
            malformed = copy.deepcopy(self.ledger)
            malformed["programs"][0]["official_urls"][0] = malformed_url
            malformed["programs"][0]["evidence_urls"][0] = malformed_url
            broken_values.append(malformed)

        exclusive_owner = copy.deepcopy(self.ledger)
        exclusive_owner["programs"][0]["owner"] = "COMMONS_REVIEWER"
        broken_values.append(exclusive_owner)

        blank_analysis = copy.deepcopy(self.ledger)
        blank_analysis["programs"][0]["fit_note"] = "ANALYSIS: "
        broken_values.append(blank_analysis)

        numeric_legal_scope = copy.deepcopy(self.ledger)
        numeric_legal_scope["legal_scope"]["award_claimed"] = 0
        broken_values.append(numeric_legal_scope)

        for index, broken in enumerate(broken_values):
            with self.subTest(case=index):
                with self.assertRaises(SchemaError):
                    validator.validate_file(broken, "grants_ledger.schema.json")

    def test_exact_program_truth(self):
        pesose = self.by_id["nsf-pesose-26-506"]
        self.assertEqual(pesose["application_state"], "OPEN")
        self.assertEqual(
            pesose["deadline"],
            {
                "date": "2026-09-01",
                "time": "17:00",
                "timezone_basis": "submitting organization's local time; not a UTC instant",
            },
        )
        self.assertEqual(
            pesose["funding_text"],
            "Track 1 maximum USD 300,000; Track 2 maximum USD 1,500,000; Track 3 maximum USD 1,500,000; all subject to availability.",
        )
        self.assertEqual(pesose["matching_state"], "NOT_REQUIRED")

        sbir = self.by_id["nsf-sbir-sttr-26-510"]
        self.assertEqual(sbir["application_state"], "OPEN")
        self.assertEqual(
            sbir["deadline"],
            {
                "date": "2026-11-04",
                "time": "17:00",
                "timezone_basis": "submitting organization's local time; not a UTC instant",
            },
        )
        self.assertEqual(sbir["funding_evidence_state"], "CONFLICT")
        self.assertEqual(
            sbir["funding_text"],
            "Phase I maximum USD 305,000; Phase II maximum USD 1,250,000. Fast-Track conflicts internally: the summary says USD 1,555,000, while the detailed award section says USD 1,555,555.",
        )

        restack = self.by_id["nlnet-restack-ois-2026"]
        self.assertEqual(restack["application_state"], "UPCOMING")
        self.assertEqual(restack["opens_date"], "2026-09-03")
        self.assertEqual(
            restack["deadline"],
            {
                "date": "2026-11-03",
                "time": "12:00",
                "timezone_basis": "CEST (noon), as labeled; no conversion performed",
            },
        )
        self.assertEqual(restack["funding_text"], "UNKNOWN: amount lines were not independently verified for this build.")
        self.assertEqual(restack["funding_evidence_state"], "UNKNOWN")
        self.assertEqual(restack["matching_state"], "UNKNOWN")

        self.assertEqual({program["checked_at"] for program in self.ledger["programs"]}, {"2026-08-26T20:50:00Z"})
        self.assertEqual({program["applicant_eligibility_state"] for program in self.ledger["programs"]}, {"UNKNOWN"})
        self.assertEqual({program["submission_status"] for program in self.ledger["programs"]}, {"NOT_SUBMITTED"})
        self.assertEqual({program["award_status"] for program in self.ledger["programs"]}, {"NOT_AWARDED"})
        self.assertEqual({program["cash_received_usd"] for program in self.ledger["programs"]}, {0})

    def test_exact_official_urls(self):
        for program_id, facts in grants_ledger.EXPECTED_FACTS.items():
            self.assertEqual(self.by_id[program_id]["official_urls"], facts["official_urls"])
            self.assertEqual(self.by_id[program_id]["evidence_urls"], facts["official_urls"])

    def test_extra_and_missing_keys_fail_closed(self):
        extra = copy.deepcopy(self.ledger)
        extra["programs"][0]["unexpected"] = "value"
        self.assert_invalid(extra, "extra keys")
        missing = copy.deepcopy(self.ledger)
        del missing["programs"][0]["funder"]
        self.assert_invalid(missing, "missing keys")

    def test_duplicate_id_non_https_and_bad_date_fail_closed(self):
        duplicate = copy.deepcopy(self.ledger)
        duplicate["programs"][2]["id"] = duplicate["programs"][0]["id"]
        self.assert_invalid(duplicate, "duplicate program ids")
        bad_url = copy.deepcopy(self.ledger)
        bad_url["programs"][0]["official_urls"][0] = "http://example.invalid/program"
        bad_url["programs"][0]["evidence_urls"][0] = "http://example.invalid/program"
        self.assert_invalid(bad_url, "must be HTTPS")
        bad_date = copy.deepcopy(self.ledger)
        bad_date["programs"][1]["deadline"]["date"] = "2026-02-30"
        self.assert_invalid(bad_date, "malformed")
        bad_time = copy.deepcopy(self.ledger)
        bad_time["programs"][1]["deadline"]["time"] = "29:59"
        self.assert_invalid(bad_time, "malformed")

    def test_bad_url_authority_hostname_and_port_fail_closed(self):
        cases = (
            ("https:///program", "must be HTTPS"),
            ("https://example.com:bad/program", "invalid port"),
            ("https://example.com:443/program", "may not use a port"),
            ("https://./program", "invalid hostname"),
        )
        for value, pattern in cases:
            with self.subTest(value=value):
                broken = copy.deepcopy(self.ledger)
                broken["programs"][0]["official_urls"][0] = value
                broken["programs"][0]["evidence_urls"][0] = value
                self.assert_invalid(broken, pattern)

    def test_fabricated_outcomes_fail_closed(self):
        cases = (
            ("submission_status", "SUBMITTED", "filing status"),
            ("award_status", "AWARDED", "award status"),
            ("cash_received_usd", 1, "cash"),
        )
        for key, value, pattern in cases:
            with self.subTest(key=key):
                broken = copy.deepcopy(self.ledger)
                broken["programs"][0][key] = value
                self.assert_invalid(broken, pattern)

    def test_legal_scope_requires_exact_false_booleans(self):
        for value in (0, ""):
            with self.subTest(value=value):
                broken = copy.deepcopy(self.ledger)
                broken["legal_scope"]["award_claimed"] = value
                self.assert_invalid(broken, "exact false booleans")

    def test_private_key_at_depth_fails_closed(self):
        broken = copy.deepcopy(self.ledger)
        broken["programs"][2]["deadline"]["bank_details"] = "private-value"
        self.assert_invalid(broken, "publishes private keys")

    def test_evidence_and_analysis_rules_fail_closed(self):
        no_match_basis = copy.deepcopy(self.ledger)
        del no_match_basis["programs"][0]["matching_basis"]
        self.assert_invalid(no_match_basis, "missing keys")
        empty_verified = copy.deepcopy(self.ledger)
        empty_verified["programs"][0]["program_eligibility_text"] = ""
        self.assert_invalid(empty_verified, "must be nonempty text")
        bad_fit = copy.deepcopy(self.ledger)
        bad_fit["programs"][0]["fit_note"] = "Looks suitable"
        self.assert_invalid(bad_fit, "must start ANALYSIS")
        promoted = copy.deepcopy(self.ledger)
        promoted["programs"][0]["applicant_eligibility_state"] = "ELIGIBLE"
        self.assert_invalid(promoted, "may not adjudicate applicant eligibility")

    def test_unreviewed_evidence_and_schema_drift_fail_closed(self):
        invented_funding = copy.deepcopy(self.ledger)
        invented_funding["programs"][0]["funding_text"] = "Track 1 maximum USD 999,999,999."
        self.assert_invalid(invented_funding, "ledger evidence contract drift")

        invented_scope = copy.deepcopy(self.ledger)
        invented_scope["scope"] = "Commons received a grant award and cash."
        self.assert_invalid(invented_scope, "ledger evidence contract drift")

        invented_nonclaims = copy.deepcopy(self.ledger)
        invented_nonclaims["nonclaims"] = ["Commons was awarded funding."]
        self.assert_invalid(invented_nonclaims, "ledger evidence contract drift")

        weakened_schema = copy.deepcopy(self.schema)
        weakened_schema["$defs"]["program"]["properties"]["cash_received_usd"] = {"type": "number"}
        with self.assertRaisesRegex(grants_ledger.LedgerError, "schema contract drift"):
            grants_ledger.validate(ROOT, self.ledger, weakened_schema)

    def test_raw_json_duplicate_keys_and_nonfinite_numbers_fail_closed(self):
        duplicate_outcome = '{"award_status":"AWARDED","award_status":"NOT_AWARDED"}'
        duplicate_private = '{"funder":"private material","funder":"U.S. National Science Foundation"}'
        for raw in (duplicate_outcome, duplicate_private):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(grants_ledger.LedgerError, "duplicate JSON key"):
                    grants_ledger._parse_json(raw, "ledger")

        for raw in ('{"value":NaN}', '{"value":Infinity}', '{"value":-Infinity}'):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(grants_ledger.LedgerError, "non-finite JSON constant"):
                    grants_ledger._parse_json(raw, "ledger")

    def test_list_due_and_next_preserve_unknowns_and_conflict(self):
        listed = self.run_cli("list")
        listed_by_id = {program["id"]: program for program in listed["programs"]}
        self.assertEqual(listed_by_id["nsf-sbir-sttr-26-510"]["funding_evidence_state"], "CONFLICT")
        self.assertEqual(listed_by_id["nlnet-restack-ois-2026"]["funding_evidence_state"], "UNKNOWN")
        due = self.run_cli("due")
        self.assertEqual(len(due["due"]), 3)
        self.assertEqual({item["applicant_eligibility_state"] for item in due["due"]}, {"UNKNOWN"})
        self.assertEqual({item["submission_status"] for item in due["due"]}, {"NOT_SUBMITTED"})
        self.assertIn("CONFLICT", {item["funding_evidence_state"] for item in due["due"]})
        next_result = self.run_cli("next")
        self.assertEqual(next_result["status"], "NONE_READY")
        self.assertEqual(next_result["reason"], "APPLICANT_ELIGIBILITY_UNKNOWN")
        self.assertEqual(tuple(next_result["program_ids"]), grants_ledger.EXPECTED_IDS)

    def test_default_validate_and_summary(self):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "host/grants_ledger.py"), "--root", str(ROOT)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["programs"], 3)
        self.assertEqual(result["application_states"], {"OPEN": 2, "UPCOMING": 1})
        self.assertEqual(result["applicant_eligibility_states"], {"UNKNOWN": 3})
        self.assertEqual(result["submission_statuses"], {"NOT_SUBMITTED": 3})
        self.assertEqual(result["awards"], 0)
        self.assertEqual(result["cash_received_usd"], 0)

    def test_cli_has_only_read_commands_and_no_external_path(self):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "host/grants_ledger.py"), "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        help_text = completed.stdout.lower()
        forbidden_commands = (
            "acc" + "ount",
            "log" + "in",
            "app" + "ly",
            "sub" + "mit",
            "muta" + "tion",
            "creden" + "tial",
        )
        for forbidden in forbidden_commands:
            self.assertIsNone(re.search(r"\b%s\b" % forbidden, help_text), forbidden)
        self.assertIn("{validate,list,due,next}", help_text)
        source = (ROOT / "host/grants_ledger.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertTrue({"socket", "requests", "http", "subprocess", "os"}.isdisjoint(imports))
        for forbidden in forbidden_commands:
            self.assertIsNone(re.search(r"\b%s\b" % forbidden, source.lower()), forbidden)

    def test_four_file_surface_adds_no_open_door_gate(self):
        rendered = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in grants_ledger.BUILD_PATHS).lower()
        for forbidden in (
            r"\b" + "au" + r"th\b",
            r"\b" + "log" + "in" + r"\b",
            r"\b" + "appro" + "val" + r"\b",
            r"\b" + "ro" + "le" + r"\b",
            r"\b" + "ti" + "er" + r"\b",
            "accep" + r"ted[-_ ]action",
            "admis" + r"sion[-_ ]gate",
        ):
            self.assertIsNone(re.search(forbidden, rendered), forbidden)


if __name__ == "__main__":
    unittest.main()
