"""Independent UIOWA-071 malformed-input/evidence acceptance.

All inputs are synthetic JSON-shaped records. This suite calls the actual
inventory/schema/guide; it defines no replacement normalization or classifier.
Run by package name from the repository root, normally and with python -O.
Subcase counts are not added to the top-level unittest method count.
"""
from __future__ import annotations

import copy
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

if __package__:
    from . import inventory, interview_guide, schema
else:
    import inventory
    import interview_guide
    import schema

HERE = Path(__file__).resolve().parent
BLANKS = ("", " ", "\t\r\n", "\u2003")
LIST_FIELDS = ("inputs", "outputs", "integrations", "known_limitations", "evidence_refs")
SHAPES = (None, False, True, 0, 1, -1, 1.5, "", " ", "SYNTHETIC-TEXT", [], ["SYNTHETIC"], {}, {"synthetic": True})


def record(**changes):
    row = {
        "entry_id": "SYN-BOUNDARY-01", "group": "ESS", "function": "testing",
        "task": "Fictional test preparation", "declared_status": "ACTIVE",
        "frequency": "MONTHLY", "inputs": [], "outputs": [],
        "integrations": ["fictional workflow"], "observed_benefits": [],
        "known_limitations": [], "evidence_refs": [],
        "users": {"roles": ["fictional reviewer"], "approx_count": None},
    }
    row.update(copy.deepcopy(changes))
    return row


def observed(**changes):
    return record(outputs=["fictional test document"],
                  evidence_refs=["synthetic://boundary/test-document"], **changes)


class TestMalformedEvidenceBoundary(unittest.TestCase):
    def build_one(self, raw):
        before = copy.deepcopy(raw)
        result = inventory.build([raw], source_label="SYNTHETIC-BASALT-ACCEPTANCE")
        self.assertEqual(raw, before, "the actual build must not rewrite the caller's record")
        self.assertEqual(len(result.entries), 1)
        self.assertEqual(result.meta["record_count"], 1)
        self.assertEqual(sum(result.counts().values()), 1)
        return result, result.entries[0]

    def test_blank_outputs_cannot_establish_active_use(self):
        for blank in BLANKS:
            with self.subTest(blank=repr(blank)):
                result, row = self.build_one(record(outputs=[blank]))
                self.assertEqual(row["classification"], "UNSUPPORTED_CLAIM")
                self.assertEqual(row["outputs"], [])
                self.assertTrue(result.issues, "blank supplied members need a diagnostic")

    def test_blank_locators_cannot_remove_the_missing_locator_question(self):
        for blank in BLANKS:
            with self.subTest(blank=repr(blank)):
                result, row = self.build_one(record(evidence_refs=[blank]))
                self.assertEqual(row["classification"], "UNSUPPORTED_CLAIM")
                self.assertEqual(row["evidence_refs"], [])
                self.assertIn("NO_EVIDENCE_LOCATOR", [g["gap"] for g in row["gaps"]])
                self.assertTrue(result.issues)

    def test_all_blank_lists_are_unknown_not_confident_empty_answers(self):
        for field in LIST_FIELDS:
            for blank in BLANKS:
                with self.subTest(field=field, blank=repr(blank)):
                    result, row = self.build_one(record(**{field: [blank]}))
                    self.assertEqual(row[field], [])
                    self.assertEqual(row[field + "_state"], "UNKNOWN")
                    self.assertTrue(result.issues)

    def test_explicit_empty_lists_retain_none_reported(self):
        for field in LIST_FIELDS:
            with self.subTest(field=field):
                _, row = self.build_one(record(**{field: []}))
                self.assertEqual(row[field], [])
                self.assertEqual(row[field + "_state"], "NONE_REPORTED")

    def test_nonblank_members_survive_adjacent_blank_members_verbatim(self):
        for field in LIST_FIELDS:
            for blank in BLANKS:
                with self.subTest(field=field, blank=repr(blank)):
                    valid = "  synthetic://boundary/retained-value  "
                    result, row = self.build_one(record(**{field: [blank, valid, blank]}))
                    self.assertEqual(row[field], [valid], "nonblank content must not be trimmed or discarded")
                    self.assertEqual(row[field + "_state"], "REPORTED")
                    self.assertTrue(result.issues)

    def test_blank_integration_and_limitations_keep_actual_followups(self):
        for field, gap, probe in (("integrations", "UNKNOWN_INTEGRATION", "P-INT-01"),
                                  ("known_limitations", "NO_LIMITATIONS_CAPTURED", "P-LIM-01")):
            with self.subTest(field=field):
                raw = observed(); raw[field] = ["\t"]
                _, row = self.build_one(raw)
                self.assertIn(gap, [g["gap"] for g in row["gaps"]])
                self.assertIn(probe, [q["id"] for q in interview_guide.probes_for(row)])

    def test_missing_or_malformed_benefit_claim_cannot_count_as_example(self):
        for claim in (*BLANKS, None, False, 0, [], ["claim"], {}):
            with self.subTest(claim=claim):
                result, row = self.build_one(record(observed_benefits=[{
                    "claim": claim, "example_ref": "synthetic://boundary/example"}]))
                self.assertEqual(row["benefits_with_example"], 0)
                self.assertEqual(row["classification"], "UNSUPPORTED_CLAIM")
                self.assertTrue(any(i["code"] == "MALFORMED_BENEFIT" for i in result.issues))

    def test_supported_and_unsupported_valid_benefit_claims_survive(self):
        for bad_claim in (None, " "):
            with self.subTest(bad_claim=bad_claim):
                benefits = [
                    {"claim": "Fictional supported description", "example_ref": "synthetic://boundary/example"},
                    {"claim": bad_claim, "example_ref": "synthetic://boundary/not-a-claim"},
                    {"claim": "Fictional unsupported description", "example_ref": None},
                ]
                _, row = self.build_one(record(observed_benefits=benefits))
                self.assertEqual(row["benefits_with_example"], 1)
                self.assertEqual(row["benefits_unsupported"], 1)
                self.assertEqual([b["claim"] for b in row["observed_benefits"]],
                                 [benefits[0]["claim"], benefits[2]["claim"]])
                self.assertIn("UNSUPPORTED_BENEFIT", [g["gap"] for g in row["gaps"]])

    def test_invalid_status_does_not_fall_through_to_active(self):
        for status in ("ACTVE", True, False, 1, ["ACTIVE"], {"value": "ACTIVE"}, " "):
            with self.subTest(status=status):
                result, row = self.build_one(observed(declared_status=status))
                self.assertEqual(row["classification"], "UNKNOWN")
                self.assertEqual(row["declared_status"], "UNKNOWN")
                self.assertTrue(result.issues)

    def test_invalid_ids_preserve_each_record_and_valid_neighbors(self):
        for bad_id in (["SYN"], {"id": "SYN"}, [], {}, True, 1, " "):
            with self.subTest(bad_id=bad_id):
                rows = [observed(entry_id="SYN-FIRST"), observed(entry_id=bad_id),
                        observed(entry_id="SYN-LAST")]
                before = copy.deepcopy(rows)
                result = inventory.build(rows, source_label="SYNTHETIC-MIXED")
                self.assertEqual(rows, before)
                self.assertEqual(len(result.entries), 3)
                self.assertEqual(sum(result.counts().values()), 3)
                self.assertEqual(result.entries[0]["entry_id"], "SYN-FIRST")
                self.assertEqual(result.entries[-1]["entry_id"], "SYN-LAST")
                self.assertTrue(result.entries[1]["validation_codes"])
                json.dumps(result.as_dict(), allow_nan=False)
                inventory.render_markdown(result)

    def test_boolean_counts_are_not_people_and_integer_zero_stays_zero(self):
        for value in (False, True, 0.0, -1, "0", [], {}):
            with self.subTest(value=value):
                result, row = self.build_one(observed(users={"roles": [], "approx_count": value}))
                self.assertEqual(row["user_count"], "UNKNOWN")
                self.assertTrue(result.issues)
        for value in (0, 1, 50):
            with self.subTest(valid_count=value):
                _, row = self.build_one(observed(users={"roles": [], "approx_count": value}))
                self.assertEqual(type(row["user_count"]), int)
                self.assertEqual(row["user_count"], value)

    def test_json_shape_matrix_never_loses_a_record_or_mutates_input(self):
        fields = ("entry_id", "group", "function", "task", "declared_status", "frequency",
                  "users", "inputs", "outputs", "integrations", "observed_benefits",
                  "known_limitations", "evidence_refs", "captured_at", "respondent_role", "notes")
        for field in fields:
            for value in SHAPES:
                with self.subTest(field=field, value=value):
                    raw = observed(); raw[field] = copy.deepcopy(value)
                    result, row = self.build_one(raw)
                    self.assertEqual(sum(c["entries"] for c in result.coverage()) + len(result.unmapped()), 1)
                    self.assertIn(row["classification"], schema.CLASSIFICATIONS)
                    json.dumps(result.as_dict(), allow_nan=False)
                    inventory.render_markdown(result)
                    interview_guide.probes_for(row)

    def test_original_fixture_and_sample_semantics_are_preserved(self):
        records, label = inventory.load(HERE / "fixtures/synthetic_ai_use.json")
        result = inventory.build(records, source_label=label)
        self.assertEqual(json.loads(json.dumps(result.as_dict())),
                         json.loads((HERE / "sample_output/ai_use_inventory.json").read_text(encoding="utf-8")))
        self.assertEqual(inventory.render_markdown(result),
                         (HERE / "sample_output/ai_use_inventory.md").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temp:
            for name, writer in (("ai_use_inventory.csv", inventory.write_csv),
                                 ("ai_use_gaps.csv", inventory.write_gaps_csv)):
                path = Path(temp) / name; writer(result, path)
                self.assertEqual(path.read_bytes(), (HERE / "sample_output" / name).read_bytes())

    def test_mixed_collection_cli_keeps_all_rows_and_input_bytes(self):
        rows = [observed(entry_id="SYN-FIRST"),
                observed(entry_id=["malformed"]),
                record(entry_id="SYN-BLANK", outputs=[" "], evidence_refs=["\t"]),
                observed(entry_id="SYN-STATUS", declared_status="ACTVE"),
                observed(entry_id="SYN-LAST")]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); input_path = root / "synthetic.json"; out = root / "out"
            payload = json.dumps(rows, ensure_ascii=True).encode("utf-8")
            input_path.write_bytes(payload)
            run = subprocess.run([sys.executable, *(["-O"] * sys.flags.optimize), "-S",
                                  str(HERE / "inventory.py"), "--input", str(input_path), "--outdir", str(out)],
                                 cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertEqual(input_path.read_bytes(), payload)
            result = json.loads((out / "ai_use_inventory.json").read_text(encoding="utf-8"))
            self.assertEqual(len(result["entries"]), 5)
            self.assertEqual(sum(result["counts"].values()), 5)
            self.assertEqual(result["entries"][2]["classification"], "UNSUPPORTED_CLAIM")
            self.assertEqual(result["entries"][3]["classification"], "UNKNOWN")
            with (out / "ai_use_inventory.csv").open(encoding="utf-8", newline="") as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 5)
            self.assertNotIn("Traceback", run.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
