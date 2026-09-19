"""Independent synthetic acceptance cases for mortgage snapshot reconciliation.

No lending decision, source authentication, live integration, or browser claim.
"""
import copy
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import mortgage_core as core
import mortgage_case_reconcile as app


ROOT = Path(__file__).resolve().parent
HASH_A = "a" * 64
HASH_B = "b" * 64


def synthetic_case():
    values = {
        "loan_amount": {"currency": "GBP", "minor_units": 12000000},
        "product_code": "FIXED",
        "completion_date": "2026-12-01",
        "income_verified": True,
        "case_note": "Fictional café record",
    }
    kinds = {"loan_amount": "money", "product_code": "code", "completion_date": "date",
             "income_verified": "bool", "case_note": "text"}
    return {
        "schema": "mortgage-case-reconcile/v1", "case_id": "CASE-001",
        "subject_ref": "SUBJECT-001", "as_of": "2026-09-19T12:00:00Z",
        "field_specs": [{"field_id": key, "kind": kinds[key], "required_sources": ["SRC-A", "SRC-B"]}
                        for key in values],
        "sources": [{"source_id": source, "observed_at": "2026-09-19T08:00:00Z",
                     "fields": [{"field_id": key, "value": copy.deepcopy(value)} for key, value in values.items()],
                     "documents": [{"document_id": "DOC-INCOME", "document_type": "INCOME",
                                    "sha256": HASH_A, "status": "validated"}]}
                    for source in ("SRC-A", "SRC-B")],
        "document_requirements": [{"document_type": "INCOME", "min_validated": 1}],
        "milestone_order": ["START", "REVIEW", "COMPLETE"],
        "events": [event("EV-001", "2026-09-19T09:00:00Z", "START"),
                   event("EV-002", "2026-09-19T10:00:00Z", "REVIEW")],
    }


def event(identifier, at, milestone, kind="status"):
    return {"event_id": identifier, "at": at, "event_type": kind,
            "milestone": milestone, "channel": "system", "message_ref": "MSG-" + identifier}


def observation(case, source, field):
    return next(row for row in case["sources"][source]["fields"] if row["field_id"] == field)


def field(receipt, name):
    return next(row for row in receipt["fields"] if row["field_id"] == name)


def document(receipt, name="INCOME"):
    return next(row for row in receipt["documents"] if row["document_type"] == name)


def codes(receipt):
    return {issue["code"] for issue in receipt["issues"]}


class MortgageCaseTests(unittest.TestCase):
    def setUp(self):
        self.case = synthetic_case()
        self.temp = tempfile.TemporaryDirectory(prefix="mortgage-independent-")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.input = self.folder / "case-input.json"
        self.input_bytes = (json.dumps(self.case, ensure_ascii=False, indent=3) + "\n\n").encode()
        self.input.write_bytes(self.input_bytes)

    def cli(self, *args, cwd=ROOT):
        env = dict(os.environ); env.pop("PYTHONPATH", None)
        optimization = ["-" + "O" * sys.flags.optimize] if sys.flags.optimize else []
        return subprocess.run([sys.executable, "-B", *optimization, "mortgage_case_reconcile.py", *map(str, args)],
                              cwd=cwd, env=env, capture_output=True, text=True, timeout=30)

    def exported_bundle(self):
        output = self.folder / "bundle"
        app.export_bundle(self.input, output)
        return output

    def assert_rejected(self, case):
        with self.assertRaises(core.ContractError):
            core.normalize_case(case)

    def test_normalization_is_idempotent_permutation_stable_and_does_not_mutate(self):
        observation(self.case, 0, "case_note")["value"] = " Fictional\t cafe\u0301   record "
        before = copy.deepcopy(self.case)
        normalized = core.normalize_case(self.case)
        self.assertEqual(self.case, before)
        self.assertEqual(normalized, core.normalize_case(normalized))
        changed = copy.deepcopy(self.case)
        changed["field_specs"].reverse(); changed["sources"].reverse(); changed["events"].reverse()
        for spec in changed["field_specs"]: spec["required_sources"].reverse()
        for source in changed["sources"]: source["fields"].reverse(); source["documents"].reverse()
        self.assertEqual(core.compile_case(changed), core.compile_case(self.case))
        self.assertEqual(normalized["milestone_order"], ["START", "REVIEW", "COMPLETE"])
        self.assertEqual(observation(normalized, 0, "case_note")["value"], "Fictional café record")

    def test_root_schema_missing_unknown_and_pii_shaped_keys_rejected(self):
        for change in (lambda c: c.update(schema="other/v1"), lambda c: c.pop("as_of"),
                       lambda c: c.update(unrecognized=True), lambda c: c.update(email="not-real")):
            with self.subTest(change=change):
                case = copy.deepcopy(self.case); change(case); self.assert_rejected(case)

    def test_typed_containers_and_nested_unknown_keys_rejected(self):
        for key in ("field_specs", "sources", "document_requirements", "milestone_order", "events"):
            with self.subTest(key=key):
                case = copy.deepcopy(self.case); case[key] = {}; self.assert_rejected(case)
        for location in ("source", "field", "document", "event", "requirement"):
            case = copy.deepcopy(self.case)
            target = {"source": case["sources"][0], "field": case["sources"][0]["fields"][0],
                      "document": case["sources"][0]["documents"][0], "event": case["events"][0],
                      "requirement": case["document_requirements"][0]}[location]
            target["unexpected"] = 1
            with self.subTest(location=location): self.assert_rejected(case)

    def test_identifier_scopes_duplicates_and_unresolved_references_rejected(self):
        changes = [lambda c: c.update(case_id=True), lambda c: c.update(subject_ref="lowercase"),
                   lambda c: c["sources"].append(copy.deepcopy(c["sources"][0])),
                   lambda c: c["events"].append(copy.deepcopy(c["events"][0])),
                   lambda c: c["sources"][0]["fields"].append(copy.deepcopy(c["sources"][0]["fields"][0])),
                   lambda c: c["sources"][0]["documents"].append(copy.deepcopy(c["sources"][0]["documents"][0])),
                   lambda c: c["events"][0].update(milestone="UNDECLARED"),
                   lambda c: c["sources"][0]["fields"][0].update(field_id="undeclared")]
        for number, change in enumerate(changes):
            case = copy.deepcopy(self.case); change(case)
            with self.subTest(number=number): self.assert_rejected(case)

    def test_money_requires_exact_nonboolean_integer_units_and_currency_shape(self):
        for units in (True, False, -1, 10**15 + 1, 1.0, "1", None):
            case = copy.deepcopy(self.case); observation(case, 0, "loan_amount")["value"]["minor_units"] = units
            with self.subTest(units=units): self.assert_rejected(case)
        for currency in ("gbp", "GB", 123):
            case = copy.deepcopy(self.case); observation(case, 0, "loan_amount")["value"]["currency"] = currency
            with self.subTest(currency=currency): self.assert_rejected(case)
        for units in (0, 10**15):
            case = copy.deepcopy(self.case); observation(case, 0, "loan_amount")["value"]["minor_units"] = units
            self.assertEqual(observation(core.normalize_case(case), 0, "loan_amount")["value"]["minor_units"], units)

    def test_bool_code_date_and_text_values_are_typed_and_calendar_valid(self):
        for name, value in (("income_verified", 1), ("income_verified", "true"), ("product_code", "fixed"),
                            ("completion_date", "2026-02-29"), ("completion_date", "2026-2-01"),
                            ("case_note", ""), ("case_note", "x" * 161), ("case_note", 17)):
            case = copy.deepcopy(self.case); observation(case, 0, name)["value"] = value
            with self.subTest(field=name, value=value): self.assert_rejected(case)
        observation(self.case, 0, "completion_date")["value"] = "2028-02-29"
        core.normalize_case(self.case)

    def test_timestamps_are_canonical_valid_and_not_after_assessment(self):
        for bad in ("2026-09-19T09:00:00+00:00", "2026-09-19T09:00:00.000Z", "2026-02-30T09:00:00Z",
                    "2026-09-19T12:00:01Z", True):
            for target in ("source", "event"):
                case = copy.deepcopy(self.case)
                if target == "source": case["sources"][0]["observed_at"] = bad
                else: case["events"][0]["at"] = bad
                with self.subTest(target=target, bad=bad): self.assert_rejected(case)

    def test_strict_json_rejects_duplicate_keys_and_nonfinite_numbers(self):
        for raw in ('{"schema":1,"schema":2}', '{"nested":{"x":1,"x":2}}', '{"n":NaN}',
                    '{"n":Infinity}', '{"n":-Infinity}', '{"n":1e999}', '{'):
            with self.subTest(raw=raw), self.assertRaises(core.ContractError): core.strict_json_loads(raw)

    def test_aligned_baseline_is_reconciliation_only_with_false_authority(self):
        receipt = core.compile_case(self.case)
        self.assertEqual(receipt["schema"], "mortgage-case-receipt/v1")
        self.assertEqual({row["status"] for row in receipt["fields"]}, {"ALIGNED"})
        self.assertEqual(document(receipt)["validated_unique_hashes"], [HASH_A])
        self.assertEqual(document(receipt)["status"], "SATISFIED")
        self.assertEqual(receipt["current_milestone"], "REVIEW")
        self.assertEqual(receipt["current_milestone_status"], "KNOWN")
        self.assertEqual(receipt["reconciliation_status"], "NO_DECLARED_BLOCKERS")
        self.assertEqual(receipt["issues"], [])
        self.assertTrue(receipt["authority"])
        self.assertTrue(all(value is False for value in receipt["authority"].values()))

    def test_missing_required_observation_preserves_available_evidence(self):
        self.case["sources"][1]["fields"] = [row for row in self.case["sources"][1]["fields"] if row["field_id"] != "loan_amount"]
        receipt = core.compile_case(self.case); row = field(receipt, "loan_amount")
        self.assertEqual(row["status"], "MISSING")
        self.assertEqual(row["missing_sources"], ["SRC-B"])
        self.assertEqual([obs["source_id"] for obs in row["observations"]], ["SRC-A"])
        self.assertIn("SOURCE_FIELD_MISSING", codes(receipt))

    def test_conflict_and_missing_are_both_retained(self):
        self.case["sources"].append({"source_id": "SRC-C", "observed_at": "2026-09-19T08:00:00Z", "fields": [], "documents": []})
        next(s for s in self.case["field_specs"] if s["field_id"] == "product_code")["required_sources"].append("SRC-C")
        observation(self.case, 1, "product_code")["value"] = "VARIABLE"
        receipt = core.compile_case(self.case); row = field(receipt, "product_code")
        self.assertEqual(row["status"], "CONFLICT")
        self.assertEqual(set(row["distinct_values"]), {"FIXED", "VARIABLE"})
        self.assertEqual(row["missing_sources"], ["SRC-C"])
        self.assertTrue({"FIELD_CONFLICT", "SOURCE_FIELD_MISSING"} <= codes(receipt))

    def test_revised_snapshot_resolves_only_after_supplied_values_agree(self):
        changed = copy.deepcopy(self.case); observation(changed, 1, "product_code")["value"] = "VARIABLE"
        blocked = core.compile_case(changed)
        self.assertEqual(blocked["reconciliation_status"], "REVIEW_REQUIRED")
        revised = copy.deepcopy(changed); observation(revised, 0, "product_code")["value"] = "VARIABLE"
        resolved = core.compile_case(revised)
        self.assertEqual(resolved["reconciliation_status"], "NO_DECLARED_BLOCKERS")
        self.assertNotEqual(blocked["source_digest"], resolved["source_digest"])
        self.assertEqual(field(blocked, "product_code")["status"], "CONFLICT")
        with self.assertRaises(core.ContractError): app.verify_receipt(revised, blocked)

    def test_required_source_and_document_threshold_references_are_validated(self):
        for required in ([], ["SRC-Z"], ["SRC-A", "SRC-A"]):
            case = copy.deepcopy(self.case); case["field_specs"][0]["required_sources"] = required
            with self.subTest(required=required): self.assert_rejected(case)
        for minimum in (True, 0, 21, 1.0):
            case = copy.deepcopy(self.case); case["document_requirements"][0]["min_validated"] = minimum
            with self.subTest(minimum=minimum): self.assert_rejected(case)

    def test_repeated_document_hash_is_one_validated_document(self):
        self.case["document_requirements"][0]["min_validated"] = 2
        receipt = core.compile_case(self.case)
        self.assertEqual(document(receipt)["validated_unique_hashes"], [HASH_A])
        self.assertEqual(len(document(receipt)["observations"]), 2)
        self.assertEqual(document(receipt)["status"], "UNMET")
        self.assertIn("DOCUMENT_REQUIREMENT_UNMET", codes(receipt))

    def test_two_distinct_uncontested_validated_documents_satisfy_two(self):
        self.case["document_requirements"][0]["min_validated"] = 2
        self.case["sources"][1]["documents"] = [{"document_id": "DOC-SECOND", "document_type": "INCOME", "sha256": HASH_B, "status": "validated"}]
        row = document(core.compile_case(self.case))
        self.assertEqual(row["validated_unique_hashes"], [HASH_A, HASH_B])
        self.assertEqual(row["status"], "SATISFIED")

    def test_same_hash_conflicting_status_is_not_counted_as_validated(self):
        for status in ("received", "rejected"):
            case = copy.deepcopy(self.case); case["sources"][1]["documents"][0]["status"] = status
            receipt = core.compile_case(case); row = document(receipt)
            with self.subTest(status=status):
                self.assertEqual(row["validated_unique_hashes"], [])
                self.assertIn(HASH_A, row["contested_hashes"])
                self.assertEqual({o["status"] for o in row["observations"]}, {"validated", status})
                self.assertTrue({"DOCUMENT_STATUS_CONFLICT", "DOCUMENT_REQUIREMENT_UNMET"} <= codes(receipt))

    def test_same_document_id_changed_hash_or_type_preserves_contested_records(self):
        for change in ({"sha256": HASH_B}, {"document_type": "IDENTITY"}):
            case = copy.deepcopy(self.case); case["sources"][1]["documents"][0].update(change)
            receipt = core.compile_case(case)
            with self.subTest(change=change):
                self.assertIn("DOCUMENT_ID_CONFLICT", codes(receipt))
                self.assertEqual(document(receipt)["validated_unique_hashes"], [])
                observations = [o for row in receipt["documents"] for o in row["observations"]]
                self.assertEqual(len(observations), 2)
                self.assertEqual({o["source_id"] for o in observations}, {"SRC-A", "SRC-B"})

    def test_rejected_documents_do_not_satisfy_requirement(self):
        for source in self.case["sources"]: source["documents"][0]["status"] = "rejected"
        receipt = core.compile_case(self.case)
        self.assertEqual(document(receipt)["validated_unique_hashes"], [])
        self.assertIn("DOCUMENT_REQUIREMENT_UNMET", codes(receipt))
        self.assertNotIn("DOCUMENT_STATUS_CONFLICT", codes(receipt))

    def test_informational_events_are_retained_without_false_state_regression(self):
        for n, kind in enumerate(("request", "response", "document"), 3):
            self.case["events"].append(event(f"EV-00{n}", f"2026-09-19T11:0{n}:00Z", "START", kind))
        receipt = core.compile_case(self.case)
        self.assertEqual(receipt["current_milestone"], "REVIEW")
        self.assertEqual(len(receipt["timeline"]), 5)
        self.assertNotIn("MILESTONE_REGRESSION", codes(receipt))

    def test_actual_status_regression_is_blocking_and_retains_current_status(self):
        self.case["events"].append(event("EV-003", "2026-09-19T11:00:00Z", "START"))
        receipt = core.compile_case(self.case)
        self.assertIn("MILESTONE_REGRESSION", codes(receipt))
        self.assertEqual(receipt["current_milestone"], "START")
        self.assertEqual(receipt["reconciliation_status"], "REVIEW_REQUIRED")

    def test_simultaneous_status_disagreement_remains_ambiguous(self):
        self.case["events"].append(event("EV-003", "2026-09-19T10:00:00Z", "COMPLETE"))
        receipt = core.compile_case(self.case)
        self.assertIsNone(receipt["current_milestone"])
        self.assertEqual(receipt["current_milestone_status"], "AMBIGUOUS")
        self.assertIn("MILESTONE_AMBIGUOUS", codes(receipt))
        self.assertNotIn("MILESTONE_REGRESSION", codes(receipt))
        self.assertEqual(receipt, core.compile_case({**self.case, "events": list(reversed(self.case["events"]))}))

    def test_no_status_event_leaves_current_state_unknown(self):
        for row in self.case["events"]: row["event_type"] = "request"
        receipt = core.compile_case(self.case)
        self.assertIsNone(receipt["current_milestone"])
        self.assertEqual(receipt["current_milestone_status"], "UNKNOWN")
        self.assertIn("MILESTONE_STATUS_MISSING", codes(receipt))
        self.assertEqual(len(receipt["timeline"]), 2)

    def test_actions_link_exact_issue_ids_for_suffix_related_subjects(self):
        self.case["field_specs"] = [{"field_id": name, "kind": "code", "required_sources": ["SRC-A", "SRC-B"]}
                                    for name in ("amount", "loan_amount")]
        self.case["sources"][0]["fields"] = [{"field_id": name, "value": "A"} for name in ("amount", "loan_amount")]
        self.case["sources"][1]["fields"] = [{"field_id": name, "value": "B"} for name in ("amount", "loan_amount")]
        receipt = core.compile_case(self.case)
        issues = {i["issue_id"]: i for i in receipt["issues"]}
        self.assertEqual(len(issues), 2)
        self.assertEqual({a["issue_id"] for a in receipt["next_actions"]}, set(issues))
        for action in receipt["next_actions"]:
            issue = issues[action["issue_id"]]
            self.assertEqual(action["subject"], issue["subject"])
            self.assertEqual(action["source_ids"], issue["source_ids"])

    def test_receipt_verification_recompiles_instead_of_trusting_resealed_digest(self):
        receipt = core.compile_case(self.case)
        self.assertTrue(app.verify_receipt(self.case, receipt)["ok"])
        receipt["current_milestone"] = "COMPLETE"
        receipt.pop("semantic_digest")
        receipt["semantic_digest"] = hashlib.sha256(core.canonical_bytes(receipt)).hexdigest()
        with self.assertRaises(core.ContractError): app.verify_receipt(self.case, receipt)

    def test_different_input_cannot_reuse_old_receipt(self):
        receipt = core.compile_case(self.case)
        self.case["sources"][0]["observed_at"] = "2026-09-19T08:01:00Z"
        with self.assertRaises(core.ContractError): app.verify_receipt(self.case, receipt)

    def test_html_escapes_supported_text_and_csv_protects_formula_looking_cells(self):
        observation(self.case, 0, "case_note")["value"] = "Fictional <em>café</em> & record"
        receipt = core.compile_case(self.case)
        rendered = app.html_summary(receipt)
        self.assertIsInstance(rendered, str)
        self.assertIn("&lt;em&gt;café&lt;/em&gt;", rendered)
        self.assertNotIn("<em>café</em>", rendered)
        # Renderer API accepts a receipt mapping; exercise its escaping directly.
        receipt["case_id"] = "=1+1"
        for issue in receipt["issues"]: issue["subject"] = "+SUM(1,2)"
        for action in receipt["next_actions"]: action["subject"] = "+SUM(1,2)"
        output = app.exception_csv(receipt)
        self.assertIsInstance(output, str)
        rows = list(csv.reader(io.StringIO(output)))
        self.assertGreater(len(rows), 1)
        protected = [cell for row in rows[1:] for cell in row if "=1+1" in cell or "+SUM(1,2)" in cell]
        self.assertTrue(protected)
        self.assertTrue(all(cell.startswith("'") for cell in protected))

    def test_bundle_keeps_exact_input_and_all_payloads_and_runs_copied_verifier(self):
        folder = self.exported_bundle()
        expected = {"case.json", "normalized-case.json", "receipt.json", "exceptions.csv", "summary.html",
                    "README.md", "mortgage_core.py", "mortgage_case_reconcile.py", "bundle-manifest.json"}
        self.assertEqual({p.name for p in folder.iterdir()}, expected)
        self.assertEqual((folder / "case.json").read_bytes(), self.input_bytes)
        self.assertEqual(json.loads((folder / "normalized-case.json").read_bytes()), core.normalize_case(self.case))
        self.assertTrue(app.verify_bundle(folder)["ok"])
        result = self.cli("verify-bundle", ".", cwd=folder)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual({p.name for p in folder.iterdir()}, expected)

    def test_bundle_rejects_derived_tamper_even_if_inventory_hash_is_resealed(self):
        folder = self.exported_bundle()
        target = folder / "summary.html"; target.write_bytes(target.read_bytes() + b"\n<p>altered</p>")
        path = folder / "bundle-manifest.json"; manifest = json.loads(path.read_bytes())
        manifest["files"]["summary.html"] = hashlib.sha256(target.read_bytes()).hexdigest()
        path.write_text(json.dumps(manifest))
        with self.assertRaises(core.ContractError): app.verify_bundle(folder)

    def test_bundle_existing_directory_symlinks_and_extra_file_do_not_pass(self):
        output = self.folder / "existing"; output.mkdir(); marker = output / "keep"; marker.write_bytes(b"preserve")
        with self.assertRaises(core.ContractError): app.export_bundle(self.input, output)
        self.assertEqual(list(output.iterdir()), [marker])
        alias = self.folder / "alias"; alias.symlink_to(output, target_is_directory=True)
        with self.assertRaises(core.ContractError): app.export_bundle(self.input, alias)
        self.assertEqual(marker.read_bytes(), b"preserve")
        folder = self.exported_bundle(); (folder / "unlisted.txt").write_text("extra")
        with self.assertRaises(core.ContractError): app.verify_bundle(folder)

    def test_actual_legacy_cli_compile_verify_and_revised_input(self):
        paths = [self.folder / name for name in ("receipt.json", "exceptions.csv", "summary.html")]
        args = ["compile", self.input, "--json-out", paths[0], "--csv-out", paths[1], "--html-out", paths[2]]
        result = self.cli(*args); self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = self.cli("verify", self.input, paths[0]); self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        observation(self.case, 1, "product_code")["value"] = "VARIABLE"
        self.input.write_text(json.dumps(self.case))
        result = self.cli("verify", self.input, paths[0]); self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_preflights_existing_destinations_and_input_or_output_aliases(self):
        retained = self.folder / "retained.csv"; retained.write_bytes(b"old output")
        receipt = self.folder / "new-receipt.json"; html = self.folder / "new-summary.html"
        result = self.cli("compile", self.input, "--json-out", receipt, "--csv-out", retained, "--html-out", html)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(receipt.exists()); self.assertFalse(html.exists()); self.assertEqual(retained.read_bytes(), b"old output")
        for first, second in ((self.input, self.folder / "new.csv"), (receipt, receipt)):
            result = self.cli("compile", self.input, "--json-out", first, "--csv-out", second, "--html-out", html)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(self.input.read_bytes(), self.input_bytes)
            self.assertFalse(html.exists()); self.assertFalse(receipt.exists())

    def test_cli_malformed_input_is_contained_and_creates_no_outputs(self):
        for n, raw in enumerate((b"\xff", b'{"schema":1,"schema":2}', b'{"x":NaN}', b'[]')):
            invalid = self.folder / f"invalid-{n}.json"; invalid.write_bytes(raw)
            output = self.folder / f"invalid-output-{n}"
            result = self.cli("bundle", invalid, "--output-dir", output)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("Traceback", result.stderr)
            self.assertFalse(output.exists())
            self.assertEqual(invalid.read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
