#!/usr/bin/env python3
"""Exact-source tests for the public patent docket."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("patent_docket", ROOT / "host/patent_docket.py")
patent_docket = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(patent_docket)


class PatentDocketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docket, cls.schema = patent_docket.load(ROOT)

    def test_contract_and_exact_three_entries(self):
        from test_outcome_commerce import MiniSchemaValidator

        self.assertEqual(self.schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertIs(self.schema["additionalProperties"], False)
        MiniSchemaValidator(ROOT / "revenue/ip").validate_file(
            self.docket, "patent_docket.schema.json"
        )
        self.assertEqual(self.docket["schema_version"], "commons-patent-docket/v1")
        self.assertEqual(
            [entry["id"] for entry in self.docket["entries"]],
            [
                "stored-digital-computer",
                "white-box-parameter-inspection",
                "agentic-handset-operator",
            ],
        )

    def test_exact_sources_history_and_status_validate(self):
        result = patent_docket.validate(ROOT, self.docket, self.schema)
        self.assertEqual(result["status"], "VALID")
        self.assertEqual(result["entries"], 3)
        self.assertEqual(result["filing_statuses"], {"OWNER_REPORTED_FILED": 3})
        self.assertEqual(result["jurisdictions"], ["US"])

    def test_no_legal_conclusion_or_private_filing_identifier(self):
        self.assertEqual(set(self.docket["legal_scope"].values()), {False})
        rendered = json.dumps(self.docket, sort_keys=True).lower()
        for key in patent_docket.PRIVATE_KEYS:
            self.assertIn(key, self.docket["omitted_private_fields"])
            self.assertEqual(rendered.count('"%s"' % key), 1, key)
        self.assertNotIn("filed_receipt_verified", rendered)
        self.assertNotIn("patentability_confirmed", rendered)

    def test_source_blob_drift_fails_closed(self):
        broken = copy.deepcopy(self.docket)
        broken["entries"][0]["source"]["blob_sha"] = "0" * 40
        with self.assertRaisesRegex(patent_docket.DocketError, "source blob drift"):
            patent_docket.validate(ROOT, broken, self.schema)

    def test_earliest_public_receipt_drift_fails_closed(self):
        broken = copy.deepcopy(self.docket)
        broken["entries"][1]["earliest_public_receipt"]["commit_sha"] = "0" * 40
        with self.assertRaisesRegex(patent_docket.DocketError, "earliest commit drift"):
            patent_docket.validate(ROOT, broken, self.schema)

    def test_private_key_injection_fails_closed(self):
        broken = copy.deepcopy(self.docket)
        broken["entries"][0]["application_number"] = "private-value"
        with self.assertRaisesRegex(patent_docket.DocketError, "publishes private keys"):
            patent_docket.validate(ROOT, broken, self.schema)

    def test_status_cannot_regress_to_ready_to_file(self):
        broken = copy.deepcopy(self.docket)
        broken["entries"][2]["filing_status"] = "DRAFT_READY_TO_FILE"
        with self.assertRaisesRegex(patent_docket.DocketError, "contradicts current owner-reported"):
            patent_docket.validate(ROOT, broken, self.schema)

    def test_cli_validate(self):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "host/patent_docket.py"), "validate", "--root", str(ROOT)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "VALID")
        self.assertEqual(result["entries"], 3)


if __name__ == "__main__":
    unittest.main()
