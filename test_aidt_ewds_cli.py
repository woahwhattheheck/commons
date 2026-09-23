"""Real subprocess execution of the offline AIDT operator commands."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from revenue.aidt_ewds_workshare import core as c
from test_aidt_ewds_manifest_replay import digest, evidence, migration, record, sync

ROOT = Path(__file__).resolve().parent


class AIDTCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aidt-cli-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def fixture(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def run_cli(self, *arguments, expected=0):
        command = [sys.executable]
        if sys.flags.optimize:
            command.append("-O")
        command += ["-m", "revenue.aidt_ewds_workshare", *map(str, arguments)]
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                env=env, timeout=15, check=False)
        self.assertEqual(result.returncode, expected, result.stderr)
        if expected:
            self.assertNotIn("Traceback", result.stderr)
        return result

    def test_migration_and_verify_roundtrip_with_independent_pins(self):
        source = self.fixture("source.json", [record("synthetic-row")])
        target = self.fixture("target.json", [record("synthetic-row")])
        output = self.root / "migration.json"
        self.run_cli("migration", source, target, "--out", output)
        receipt = json.loads(output.read_text())
        result = self.run_cli("verify", output,
            "--expected-source-manifest-sha256", receipt["source_manifest_sha256"],
            "--expected-target-manifest-sha256", receipt["target_manifest_sha256"])
        verified = json.loads(result.stdout)
        self.assertEqual(verified["state"], "VERIFIED_INTERNAL_CONSISTENCY")
        self.assertIs(verified["independent_source_pin_checked"], True)
        self.assertIs(verified["external_source_authenticity_established"], False)

    def test_readiness_roundtrip_uses_real_compiler(self):
        e = self.fixture("evidence.json", evidence())
        ms = self.fixture("migrations.json", [migration()])
        ss = self.fixture("syncs.json", [sync()])
        result = self.run_cli("readiness", e, ms, ss)
        receipt = json.loads(result.stdout)
        self.assertTrue(c.verify_readiness(receipt))
        output = self.fixture("readiness.json", receipt)
        verified = json.loads(self.run_cli("verify", output).stdout)
        self.assertEqual(verified["schema"], "aidt-ewds-readiness/v2")

    def test_failed_batch_is_diagnostic_output_not_process_failure(self):
        source = self.fixture("source.json", [record("missing")])
        target = self.fixture("target.json", [])
        result = json.loads(self.run_cli("migration", source, target).stdout)
        self.assertEqual(result["decision"], "HOLD_MIGRATION_RECONCILIATION")
        self.assertEqual(result["missing_record_ids"], ["missing"])

    def test_sync_compile_and_verify(self):
        event = {"source_system": "salesforce", "target_system": "adobe_lms",
                 "event_id": "synthetic", "entity_ref": "synthetic-row", "operation": "enroll",
                 "payload_sha256": digest("payload")}
        observed = {"accepted": True, "target_ref": "synthetic-target",
                    "target_payload_sha256": digest("payload")}
        result = self.run_cli("sync", self.fixture("event.json", event),
                              self.fixture("observed.json", observed))
        receipt = json.loads(result.stdout)
        self.assertTrue(c.verify_sync_receipt(receipt))
        output = self.fixture("sync.json", receipt)
        self.run_cli("verify", output)

    def test_duplicate_keys_rejected_before_output(self):
        source = self.root / "duplicate.json"
        source.write_text('[{"record_id":"a","record_id":"b","record_sha256":"' + digest("x") + '"}]')
        output = self.root / "must-not-exist.json"
        self.run_cli("migration", source, self.fixture("target.json", []), "--out", output, expected=2)
        self.assertFalse(output.exists())

    def test_malformed_values_are_errors_without_tracebacks(self):
        for text in ('NaN', '1.5', '9' * 5000, '[' * 2000, '\ud800'):
            with self.subTest(value=text[:20]):
                source = self.root / "bad.json"
                source.write_bytes(text.encode("utf-8", errors="surrogatepass"))
                self.run_cli("verify", source, expected=2)

    def test_existing_output_preserved(self):
        source = self.fixture("source.json", [record("row")])
        output = self.root / "preserved.json"
        output.write_text("existing bytes")
        self.run_cli("migration", source, source, "--out", output, expected=2)
        self.assertEqual(output.read_text(), "existing bytes")

    def test_wrong_independent_pin_rejected(self):
        receipt = self.fixture("migration.json", migration())
        self.run_cli("verify", receipt, "--expected-source-manifest-sha256", digest("wrong"), expected=2)

    def test_pins_cannot_be_ignored_on_other_receipt_kinds(self):
        receipt = self.fixture("sync.json", sync())
        self.run_cli("verify", receipt, "--expected-target-manifest-sha256", digest("ignored"), expected=2)

    def test_legacy_input_and_missing_file_report_errors(self):
        legacy = self.fixture("legacy.json", {"schema": "aidt-ewds-migration/v1"})
        self.run_cli("verify", legacy, expected=2)
        self.run_cli("verify", self.root / "does-not-exist.json", expected=2)

    def test_demo_is_reproducible_and_semantically_verifiable(self):
        command = [sys.executable] + (["-O"] if sys.flags.optimize else [])
        command += ["-m", "revenue.aidt_ewds_workshare.demo"]
        results = [subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                  timeout=15, check=True).stdout for _ in range(2)]
        self.assertEqual(results[0], results[1])
        self.assertTrue(c.verify_readiness(json.loads(results[0])))


if __name__ == "__main__":
    unittest.main()
