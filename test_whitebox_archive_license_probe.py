#!/usr/bin/env python3
"""Contract tests for the White Box GGUF license metadata probe."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
PROBE_PATH = ROOT / "revenue/ip/whitebox_archive_license_probe.json"
SCHEMA_PATH = ROOT / "revenue/ip/whitebox_archive_license_probe.schema.json"
SPEC = importlib.util.spec_from_file_location(
    "whitebox_archive_license_probe", ROOT / "host/whitebox_archive_license_probe.py"
)
license_probe = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(license_probe)


def _gguf_string(raw: bytes) -> bytes:
    return struct.pack("<Q", len(raw)) + raw


def _metadata_string(key: str, value: str) -> bytes:
    return _gguf_string(key.encode()) + struct.pack("<I", 8) + _gguf_string(value.encode())


def _metadata_u32(key: str, value: int) -> bytes:
    return _gguf_string(key.encode()) + struct.pack("<II", 4, value)


def _synthetic_gguf(name: str, license_id: str) -> bytes:
    metadata = b"".join(
        [
            _metadata_string("general.name", name),
            _metadata_string("general.license", license_id),
            _metadata_u32("general.alignment", 32),
        ]
    )
    raw = b"GGUF" + struct.pack("<IQQ", 3, 0, 3) + metadata
    raw += b"\x00" * ((32 - (len(raw) % 32)) % 32)
    return raw + (b"TENSOR_BYTES_NOT_IN_PREFIX" * 4)


class WhiteBoxArchiveLicenseProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.probe = license_probe.read_json(PROBE_PATH)

    def test_draft_2020_12_schema_and_contract(self):
        from test_outcome_commerce import MiniSchemaValidator

        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertIs(schema["additionalProperties"], False)
        MiniSchemaValidator(SCHEMA_PATH.parent).validate_file(
            self.probe, SCHEMA_PATH.name
        )
        self.assertEqual(license_probe.validate_probe(self.probe)["status"], "VALID")

    def test_exact_eight_model_coverage_and_license_counts(self):
        summary = self.probe["summary"]
        self.assertEqual(summary["expected_models"], 8)
        self.assertEqual(summary["located_models"], 8)
        self.assertEqual(summary["embedded_license_present"], 7)
        self.assertEqual(summary["embedded_license_missing"], 1)
        self.assertEqual(
            summary["embedded_license_counts"],
            [
                {"license_id": "apache-2.0", "models": 2},
                {"license_id": "gemma", "models": 3},
                {"license_id": "llama3.3", "models": 1},
                {"license_id": "mit", "models": 1},
            ],
        )

    def test_exact_embedded_license_map(self):
        observed = {
            row["source_filename"]: row["embedded_license"]["license_id"]
            for row in self.probe["records"]
        }
        self.assertEqual(
            observed,
            {
                "Llama-3.3-70B-Instruct-Q4_K_M.gguf": "llama3.3",
                "SmolLM2-360M-Instruct-Q8_0.gguf": "apache-2.0",
                "gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf": "gemma",
                "gemma-4-31B-it-qat-UD-Q4_K_XL.gguf": "gemma",
                "google_gemma-3-27b-it-Q4_K_M.gguf": "gemma",
                "mistralai_Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M.gguf": "apache-2.0",
                "mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf": None,
                "phi-4-Q4_K_M.gguf": "mit",
            },
        )

    def test_every_local_read_is_bound_to_a_prefix_digest(self):
        self.assertEqual(self.probe["summary"]["metadata_prefix_total_bytes"], 60094112)
        self.assertTrue(
            all(len(row["metadata_prefix_sha256"]) == 64 for row in self.probe["records"])
        )
        self.assertEqual(
            len({row["metadata_prefix_sha256"] for row in self.probe["records"]}), 8
        )

    def test_mixtral_primary_source_is_not_quantized_copy_provenance(self):
        mixtral = next(
            row for row in self.probe["records"] if row["source_filename"].startswith("mixtral-")
        )
        self.assertEqual(mixtral["embedded_license"]["status"], "NOT_EMBEDDED")
        self.assertEqual(
            mixtral["external_base_model_evidence"],
            [license_probe.MIXTRAL_PRIMARY_EVIDENCE],
        )
        self.assertEqual(
            mixtral["external_base_model_evidence"][0]["scope"],
            "BASE_MODEL_PRIMARY_SOURCE_ONLY",
        )
        self.assertIs(mixtral["quantized_copy_source_verified"], False)

    def test_no_absolute_paths_tensor_load_or_transfer_claim(self):
        rendered = json.dumps(self.probe, ensure_ascii=False).lower()
        self.assertNotIn("c:\\llm", rendered)
        self.assertNotIn("c:/llm", rendered)
        scope = self.probe["scope"]
        self.assertIs(scope["source_absolute_paths_published"], False)
        self.assertIs(scope["model_tensor_bytes_loaded"], False)
        self.assertIs(scope["full_model_sha256_computed"], False)
        self.assertIs(self.probe["commercial_readiness"]["transfer_cleared"], False)
        self.assertIs(
            self.probe["commercial_readiness"]["archive_license_offer_ready"], False
        )

    def test_transfer_clearance_injection_fails(self):
        broken = copy.deepcopy(self.probe)
        broken["records"][0]["transfer_cleared"] = True
        with self.assertRaisesRegex(license_probe.ProbeError, "cannot clear"):
            license_probe.validate_probe(broken)

    def test_synthetic_parser_hashes_metadata_prefix_not_tensor_tail(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixture.gguf"
            first = _synthetic_gguf("Fixture", "mit")
            path.write_bytes(first)
            measured = license_probe.read_gguf_prefix(path)
            self.assertEqual(measured["fields"]["general.name"], "Fixture")
            self.assertEqual(measured["fields"]["general.license"], "mit")
            changed = first[: measured["metadata_prefix_bytes"]] + first[
                measured["metadata_prefix_bytes"] :
            ].replace(b"TENSOR", b"MUTATE")
            path.write_bytes(changed)
            replay = license_probe.read_gguf_prefix(path)
            self.assertEqual(
                measured["metadata_prefix_sha256"], replay["metadata_prefix_sha256"]
            )
            self.assertNotEqual(measured["file_size_bytes"], 0)

    def test_inventory_blob_binding_and_cli(self):
        blob = subprocess.check_output(
            ["git", "hash-object", "revenue/ip/whitebox_archive_inventory.json"],
            cwd=ROOT,
            text=True,
        ).strip()
        self.assertEqual(blob, license_probe.INVENTORY_BLOB_SHA)
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host/whitebox_archive_license_probe.py"),
                "validate",
                str(PROBE_PATH),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "VALID")
        self.assertEqual(result["embedded_license_present"], 7)


if __name__ == "__main__":
    unittest.main()
