#!/usr/bin/env python3
"""Exact-evidence tests for the dated phone-agent capability map."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "phone_agent_capability_map", ROOT / "host/phone_agent_capability_map.py"
)
phone_map = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(phone_map)


class PhoneAgentCapabilityMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.schema = phone_map.load(ROOT)

    def test_schema_and_semantic_contract(self):
        from test_outcome_commerce import MiniSchemaValidator

        self.assertEqual(self.schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertIs(self.schema["additionalProperties"], False)
        MiniSchemaValidator(ROOT / "revenue/ip").validate_file(
            self.data, "phone_agent_capability_map.schema.json"
        )
        result = phone_map.validate(ROOT, self.data, self.schema)
        self.assertEqual(result["status"], "VALID")
        self.assertEqual(result["systems"], 5)
        self.assertEqual(result["dimensions"], 7)
        self.assertEqual(result["claims"], 35)
        self.assertEqual(
            result["status_counts"],
            {"MEASURED": 1, "SOURCE_DOCUMENTED": 28, "UNKNOWN": 6},
        )

    def test_exact_systems_and_boundary_kinds(self):
        self.assertEqual(
            [system["id"] for system in self.data["systems"]],
            ["commons-lda-titan", "openai", "google", "xai", "elevenlabs"],
        )
        self.assertEqual(
            [system["boundary_kind"] for system in self.data["systems"]],
            [
                "DEVICE_CONTROL_AGENT",
                "REALTIME_AUDIO_API",
                "REALTIME_AUDIO_API",
                "REALTIME_AUDIO_API",
                "VOICE_AGENT_PLATFORM",
            ],
        )
        self.assertIn("not a ranking", self.data["comparison_boundary"].lower())

    def test_truth_block_has_no_benchmark_buyer_or_cash_invention(self):
        self.assertEqual(set(self.data["truth"]), phone_map.TRUTH_KEYS)
        self.assertEqual(set(self.data["truth"].values()), {False})

    def test_external_sources_are_provider_primary(self):
        for system in self.data["systems"][1:]:
            allowed = phone_map.PRIMARY_HOSTS[system["id"]]
            for dimension, claim in system["claims"].items():
                source = claim["source"]
                if claim["status"] == "UNKNOWN":
                    self.assertEqual(source["kind"], "NONE", (system["id"], dimension))
                    continue
                self.assertEqual(source["kind"], "PROVIDER_PRIMARY", (system["id"], dimension))
                self.assertIn(urlparse(source["url"]).hostname, allowed)

    def test_unknowns_are_calibrated_not_negative_claims(self):
        unknowns = []
        for system in self.data["systems"]:
            for claim in system["claims"].values():
                if claim["status"] == "UNKNOWN":
                    unknowns.append(claim)
        self.assertEqual(len(unknowns), 6)
        for claim in unknowns:
            self.assertTrue(claim["statement"].startswith("UNKNOWN:"))
            self.assertIn("not assessed as absent", claim["statement"])
            self.assertEqual(claim["source"]["url"], "")

    def test_external_system_cannot_claim_measured(self):
        broken = copy.deepcopy(self.data)
        broken["systems"][1]["claims"]["latency"]["status"] = "MEASURED"
        with self.assertRaisesRegex(phone_map.CapabilityMapError, "external provider may not be marked MEASURED"):
            phone_map.validate(ROOT, broken, self.schema)

    def test_commons_source_blob_drift_fails_closed(self):
        broken = copy.deepcopy(self.data)
        broken["systems"][0]["claims"]["tool_use"]["source"]["blob_sha"] = "0" * 40
        with self.assertRaisesRegex(phone_map.CapabilityMapError, "source blob drift"):
            phone_map.validate(ROOT, broken, self.schema)

    def test_unknown_with_source_fails_closed(self):
        broken = copy.deepcopy(self.data)
        source = broken["systems"][1]["claims"]["recovery"]["source"]
        source["kind"] = "PROVIDER_PRIMARY"
        source["url"] = "https://developers.openai.com/api/docs/guides/realtime-vad"
        with self.assertRaisesRegex(phone_map.CapabilityMapError, "UNKNOWN must use NONE source"):
            phone_map.validate(ROOT, broken, self.schema)

    def test_cli_validate(self):
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host/phone_agent_capability_map.py"),
                "validate",
                "--root",
                str(ROOT),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "VALID")
        self.assertEqual(result["claims"], 35)


if __name__ == "__main__":
    unittest.main()
