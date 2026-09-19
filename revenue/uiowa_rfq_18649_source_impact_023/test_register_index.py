"""Independent source-bound tests for the 023 dependency adapter, not the comparison engine."""
import copy
import csv
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("uiowa023_dependency_adapter_test", HERE / "register_index.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
DATA = (HERE.parents[1] / module.REGISTER).read_bytes()


def rows():
    return list(csv.DictReader(io.StringIO(DATA.decode(), newline="")))


def encode(records, *, headers=None, ending="\n"):
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=headers or list(records[0]), lineterminator=ending)
    writer.writeheader(); writer.writerows(records)
    return out.getvalue().encode("utf-8")


def synthetic(data):
    return module.build_index(data, revision="synthetic-fixture", expected_blob=None)


class IndexTests(unittest.TestCase):
    def test_actual_source_pin(self):
        self.assertEqual(len(DATA), 3434)
        self.assertEqual(module.git_blob(DATA), module.REGISTER_BLOB)
        result = module.build_index(DATA)
        self.assertEqual(len(result["source_inventory"]), 7)
        self.assertEqual(len(result["artifacts"]), 14)

    def test_contract_and_partial_coverage(self):
        result = module.build_index(DATA)
        self.assertEqual(result["schema"], "uiowa-source-dependencies/v1")
        self.assertEqual(result["namespace"], "uiowa-023-register/v1")
        self.assertEqual(result["coverage"], "partial")
        self.assertNotEqual(result["namespace"], "uiowa-evidence-authority/v2")

    def test_all_original_records_and_extension_fields_preserved(self):
        data = rows(); data[0]["extra"] = "retain é 東京"
        result = synthetic(encode(data, headers=list(data[0])))
        self.assertEqual(result["register_records"][0]["fields"], data[0])
        self.assertEqual(len(result["register_records"]), len(data))
        self.assertEqual({s["source_id"] for s in result["source_inventory"]}, {r["evidence_id"] for r in data})

    def test_iam_conflict_retains_both_observations(self):
        result = module.build_index(DATA)
        finding = next(a for a in result["artifacts"] if a["id"] == "FND-SYN-IAM-DEP-001")
        self.assertEqual(finding["depends_on"], [{"artifact_id": "OBS-SYN-IAM-DEP-001"}, {"artifact_id": "OBS-SYN-IAM-DEP-002"}])

    def test_ess_finding_retains_both_observations(self):
        result = module.build_index(DATA)
        finding = next(a for a in result["artifacts"] if a["id"] == "FND-SYN-ESS-SD-001")
        self.assertEqual(len(finding["depends_on"]), 2)

    def test_shared_observation_retains_both_sources(self):
        data = rows(); data[1]["observation_id"] = data[0]["observation_id"]
        result = synthetic(encode(data))
        observation = next(a for a in result["artifacts"] if a["id"] == data[0]["observation_id"])
        self.assertEqual(len(observation["depends_on"]), 2)

    def test_dependencies_are_typed_and_resolve(self):
        result = module.build_index(DATA)
        sources = {s["source_id"] for s in result["source_inventory"]}
        artifacts = {a["id"] for a in result["artifacts"]}
        for item in result["artifacts"]:
            for dependency in item["depends_on"]:
                self.assertIn(set(dependency), ({"source_id"}, {"artifact_id"}))
                key, value = next(iter(dependency.items()))
                self.assertIn(value, sources if key == "source_id" else artifacts)

    def test_narrative_link_is_declared_not_inferred(self):
        result = module.build_index(DATA)
        case = next(a for a in result["artifacts"] if a["id"] == "UIOWA-023-CASE-D")
        self.assertIn("Analyst-declared", case["dependency_basis"])
        self.assertIn(module.METHOD, case["locator"])
        self.assertEqual(case["depends_on"], [{"artifact_id": "FND-SYN-IAM-DEP-001"}])

    def test_original_source_content_never_claimed_fetched(self):
        result = module.build_index(DATA)
        self.assertTrue(all(s["underlying_content"] == "NOT_FETCHED" for s in result["source_inventory"]))
        self.assertTrue(all(s["representation"] == "register_record" for s in result["source_inventory"]))
        self.assertNotIn("text", result["source_inventory"][0])
        self.assertIn("not original PDF/export", result["provenance"]["notice"])

    def test_multiline_unicode_and_crlf_locators(self):
        data = rows(); data[0]["claim"] = "line one\r\nline two é 東京"
        result = synthetic(encode(data, ending="\r\n"))
        records = result["register_records"]
        self.assertTrue(records[0]["locator"].endswith("#L2-L3"))
        self.assertTrue(records[1]["locator"].endswith("#L4-L4"))
        self.assertEqual(records[0]["fields"]["claim"], data[0]["claim"])

    def test_blank_line_locators_are_exact(self):
        parts = DATA.split(b"\n", 1)
        result = synthetic(parts[0] + b"\n\n" + parts[1])
        self.assertTrue(result["register_records"][0]["locator"].endswith("#L3-L3"))

    def test_duplicate_evidence_id_rejected(self):
        data = rows(); data.append(copy.deepcopy(data[0]))
        with self.assertRaisesRegex(ValueError, "duplicate evidence"):
            synthetic(encode(data))

    def test_header_errors(self):
        for data in (b"", b"evidence_id\nx\n", DATA.replace(b"evidence_id,", b"claim,", 1)):
            with self.subTest(data=data[:20]), self.assertRaises(ValueError):
                synthetic(data)

    def test_duplicate_header_rejected(self):
        header, rest = DATA.split(b"\n", 1)
        with self.assertRaisesRegex(ValueError, "duplicate header"):
            synthetic(header + b",claim\n" + rest)

    def test_wrong_row_width_rejected(self):
        header, rest = DATA.split(b"\n", 1)
        with self.assertRaisesRegex(ValueError, "malformed row width"):
            synthetic(header + b"\nshort,row\n" + rest)

    def test_empty_required_field_rejected(self):
        data = rows(); data[0]["scope_limit"] = " "
        with self.assertRaisesRegex(ValueError, "required value"):
            synthetic(encode(data))

    def test_non_synthetic_ids_rejected(self):
        for key in ("evidence_id", "observation_id", "finding_id"):
            data = rows(); data[0][key] = "REAL-1"
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "synthetic|SYN"):
                synthetic(encode(data))

    def test_malformed_csv_rejected(self):
        header, _ = DATA.split(b"\n", 1)
        with self.assertRaises(csv.Error):
            synthetic(header + b'\n"unterminated')

    def test_changed_pinned_register_refused(self):
        with self.assertRaisesRegex(ValueError, "register drift"):
            module.build_index(DATA + b"\n")

    def test_input_bytes_unchanged_and_repeat_deterministic(self):
        saved = bytes(DATA)
        first = module.canonical(module.build_index(DATA))
        self.assertEqual(DATA, saved)
        self.assertEqual(first, module.canonical(module.build_index(DATA)))

    def test_readable_inventory_keeps_all_destinations(self):
        result = module.build_index(DATA)
        text = module.inventory_markdown(result)
        self.assertIn("PARTIAL DEPENDENCY SURVEY", text)
        for source in result["source_inventory"]:
            self.assertIn(source["locator"], text)
        for artifact in result["artifacts"]:
            self.assertIn(artifact["locator"], text)
            self.assertIn(artifact["id"], text)

    def test_cli_stdout_and_missing_source_error(self):
        command = [sys.executable, str(HERE / "register_index.py")]
        run = subprocess.run(command, capture_output=True, text=True, timeout=15)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout), module.build_index(DATA))
        with tempfile.TemporaryDirectory() as directory:
            bad = subprocess.run(command + ["--repo-root", directory], capture_output=True, text=True, timeout=15)
            self.assertEqual(bad.returncode, 2)
            self.assertNotIn("Traceback", bad.stderr)
            self.assertEqual(bad.stdout, "")


if __name__ == "__main__":
    unittest.main()
