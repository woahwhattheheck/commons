#!/usr/bin/env python3
"""Focused trust-cache regressions the v1 file did not split out.

Unchanged blobs skip, changed bytes invalidate and re-run, malformed
receipts fail honestly, WASTE fires, and the live canary hashes actual
bytes of a named input set. Summaries are not proof.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from host import trust_cache
from host import trust_cache_canary


ROOT = Path(__file__).resolve().parent
CACHE_CLI = ROOT / "host" / "trust_cache.py"
CANARY_CLI = ROOT / "host" / "trust_cache_canary.py"


class TrustCacheHonestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.artifact = self.root / "artifact.bin"
        self.artifact.write_bytes(b"alpha")
        self.ledger = self.root / "receipts.jsonl"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _run_cli(self, *argv: str, tool: Path = CACHE_CLI) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(tool), *argv],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def _pass_once(self, marker: Path) -> None:
        command = [
            sys.executable,
            "-c",
            f"from pathlib import Path; Path({str(marker)!r}).write_text('ran')",
        ]
        snapshot, code = trust_cache.run_check(
            self.artifact, "unit", command, self.ledger
        )
        self.assertEqual(code, 0)
        self.assertEqual(snapshot["event"], "PASS")
        self.assertTrue(marker.exists())

    def test_unchanged_blob_skips_and_waste_fires(self) -> None:
        marker = self.root / "ran.txt"
        self._pass_once(marker)
        marker.unlink()
        snapshot, code = trust_cache.run_check(
            self.artifact,
            "unit",
            [sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).write_text('again')"],
            self.ledger,
        )
        self.assertEqual(code, 0)
        self.assertEqual(snapshot["state"], "TRUSTED")
        self.assertEqual(snapshot["event"], "WASTE")
        self.assertFalse(snapshot["executed"])
        self.assertFalse(marker.exists())
        self.assertEqual(trust_cache.status(self.artifact, "unit", self.ledger)["waste_count"], 1)

    def test_changed_bytes_invalidate_and_rerun_executes(self) -> None:
        marker = self.root / "ran.txt"
        self._pass_once(marker)
        self.artifact.write_bytes(b"beta")
        self.assertEqual(
            trust_cache.status(self.artifact, "unit", self.ledger)["state"],
            "STALE",
        )
        marker.unlink()
        snapshot, code = trust_cache.run_check(
            self.artifact,
            "unit",
            [sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).write_text('stale-rerun')"],
            self.ledger,
        )
        self.assertEqual(code, 0)
        self.assertEqual(snapshot["event"], "PASS")
        self.assertTrue(snapshot["executed"])
        self.assertTrue(marker.exists())
        self.assertEqual(
            trust_cache.status(self.artifact, "unit", self.ledger)["state"],
            "TRUSTED",
        )
        digest = __import__("hashlib").sha256
        self.assertEqual(trust_cache.sha256_file(self.artifact), digest(b"beta").hexdigest())
        self.assertNotEqual(trust_cache.sha256_file(self.artifact), digest(b"alpha").hexdigest())

    def test_hash_is_of_actual_bytes_not_path(self) -> None:
        other = self.root / "other.bin"
        other.write_bytes(b"alpha")
        self.assertEqual(trust_cache.sha256_file(self.artifact), trust_cache.sha256_file(other))
        other.write_bytes(b"gamma")
        self.assertNotEqual(trust_cache.sha256_file(self.artifact), trust_cache.sha256_file(other))

    def test_malformed_json_fails_honestly(self) -> None:
        self.ledger.write_text("{not json\n", encoding="utf-8")
        with self.assertRaises(trust_cache.TrustCacheError) as raised:
            trust_cache.status(self.artifact, "unit", self.ledger)
        self.assertIn("not JSON", str(raised.exception))

    def test_missing_fields_fail_honestly(self) -> None:
        self.ledger.write_text(
            json.dumps({"artifact_sha256": "0" * 64, "check_id": "unit", "result": "PASS"})
            + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(trust_cache.TrustCacheError) as raised:
            trust_cache.read_receipts(self.ledger)
        self.assertIn("wrong fields", str(raised.exception))

    def test_extra_fields_fail_honestly(self) -> None:
        row = {
            "artifact_sha256": "0" * 64,
            "check_id": "unit",
            "result": "PASS",
            "recorded_at": "2026-08-28T00:00:00Z",
            "evidence": {"schema_version": trust_cache.SCHEMA_VERSION},
            "summary": "this is not proof",
        }
        self.ledger.write_text(json.dumps(row) + "\n", encoding="utf-8")
        with self.assertRaises(trust_cache.TrustCacheError) as raised:
            trust_cache.read_receipts(self.ledger)
        self.assertIn("wrong fields", str(raised.exception))

    def test_invalid_sha_fails_honestly(self) -> None:
        row = {
            "artifact_sha256": "not-a-sha",
            "check_id": "unit",
            "result": "PASS",
            "recorded_at": "2026-08-28T00:00:00Z",
            "evidence": {"schema_version": trust_cache.SCHEMA_VERSION},
        }
        self.ledger.write_text(json.dumps(row) + "\n", encoding="utf-8")
        with self.assertRaises(trust_cache.TrustCacheError) as raised:
            trust_cache.read_receipts(self.ledger)
        self.assertIn("invalid artifact_sha256", str(raised.exception))

    def test_summary_line_is_not_proof(self) -> None:
        self.ledger.write_text(
            json.dumps({"summary": "PASS", "trusted": True}) + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(trust_cache.TrustCacheError):
            trust_cache.status(self.artifact, "unit", self.ledger)
        self.assertEqual(
            trust_cache.status(self.artifact, "unit", self.root / "empty.jsonl")["state"],
            "UNVERIFIED",
        )

    def test_fail_result_stays_unverified_and_reruns(self) -> None:
        marker = self.root / "fail.txt"
        command = [sys.executable, "-c", "raise SystemExit(1)"]
        first, code = trust_cache.run_check(self.artifact, "unit", command, self.ledger)
        self.assertEqual(code, 1)
        self.assertEqual(first["event"], "FAIL")
        self.assertEqual(
            trust_cache.status(self.artifact, "unit", self.ledger)["state"],
            "UNVERIFIED",
        )
        command = [
            sys.executable,
            "-c",
            f"from pathlib import Path; Path({str(marker)!r}).write_text('recovered')",
        ]
        second, code = trust_cache.run_check(self.artifact, "unit", command, self.ledger)
        self.assertEqual(code, 0)
        self.assertEqual(second["event"], "PASS")
        self.assertTrue(marker.exists())

    def test_waste_count_cli(self) -> None:
        marker = self.root / "cli.txt"
        first = self._run_cli(
            "--ledger",
            str(self.ledger),
            "run",
            str(self.artifact),
            "unit",
            "--",
            sys.executable,
            "-c",
            f"from pathlib import Path; Path({str(marker)!r}).write_text('cli')",
        )
        self.assertEqual(first.returncode, 0, first.stderr)
        second = self._run_cli(
            "--ledger",
            str(self.ledger),
            "run",
            str(self.artifact),
            "unit",
            "--",
            sys.executable,
            "-c",
            "raise SystemExit('should not run')",
        )
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(json.loads(second.stdout)["event"], "WASTE")
        counted = self._run_cli("--ledger", str(self.ledger), "waste-count")
        self.assertEqual(counted.returncode, 0, counted.stderr)
        self.assertEqual(json.loads(counted.stdout)["waste_count"], 1)

    def test_canary_passes_when_file_exists_and_schema_ok(self) -> None:
        bundle = self.root / "bundle.bin"
        snapshot = trust_cache_canary.inspect(
            [self.artifact], "unit", self.ledger, bundle
        )
        self.assertEqual(snapshot["canary"], "PASS")
        self.assertEqual(snapshot["state"], "UNVERIFIED")
        self.assertEqual(snapshot["rule"], trust_cache_canary.RULE)
        self.assertTrue(bundle.is_file())

    def test_canary_fails_when_artifact_missing(self) -> None:
        with self.assertRaises(trust_cache.TrustCacheError) as raised:
            trust_cache_canary.canary_inputs([self.root / "missing.bin"])
        self.assertIn("artifact missing", str(raised.exception))

    def test_canary_fails_on_schema_drift(self) -> None:
        self.ledger.write_text(
            json.dumps(
                {
                    "artifact_sha256": "0" * 64,
                    "check_id": "unit",
                    "result": "PASS",
                    "recorded_at": "2026-08-28T00:00:00Z",
                    "evidence": {"schema_version": "wrong"},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(trust_cache.TrustCacheError):
            trust_cache_canary.inspect(
                [self.artifact], "unit", self.ledger, self.root / "bundle.bin"
            )

    def test_input_set_bundle_moves_when_any_file_moves(self) -> None:
        second = self.root / "other.bin"
        second.write_bytes(b"other")
        first_digest = trust_cache_canary.write_bundle(
            [self.artifact, second], self.root / "b1.bin"
        )
        second.write_bytes(b"moved")
        moved = trust_cache_canary.write_bundle(
            [self.artifact, second], self.root / "b2.bin"
        )
        self.assertNotEqual(first_digest, moved)

    def test_canary_run_skips_trusted_bundle_and_surfaces_rule(self) -> None:
        marker = self.root / "canary.txt"
        command = [
            sys.executable,
            "-c",
            f"from pathlib import Path; Path({str(marker)!r}).write_text('canary')",
        ]
        first, code = trust_cache_canary.run_named_check(
            [self.artifact], "unit", command, self.ledger
        )
        self.assertEqual(code, 0)
        self.assertEqual(first["event"], "PASS")
        self.assertTrue(marker.exists())
        marker.unlink()
        second, code = trust_cache_canary.run_named_check(
            [self.artifact], "unit", command, self.ledger
        )
        self.assertEqual(code, 0)
        self.assertEqual(second["event"], "WASTE")
        self.assertFalse(second["executed"])
        self.assertFalse(marker.exists())
        self.assertEqual(second["rule"], "Proof is cached. Build unless the bytes moved.")

    def test_canary_cli_status_and_run(self) -> None:
        marker = self.root / "cli-canary.txt"
        status = self._run_cli(
            "--ledger",
            str(self.ledger),
            "canary",
            "--input",
            str(self.artifact),
            "--check-id",
            "unit",
            tool=CANARY_CLI,
        )
        self.assertEqual(status.returncode, 0, status.stderr)
        payload = json.loads(status.stdout)
        self.assertEqual(payload["canary"], "PASS")
        self.assertEqual(payload["rule"], trust_cache_canary.RULE)
        first = self._run_cli(
            "--ledger",
            str(self.ledger),
            "run",
            "--input",
            str(self.artifact),
            "--check-id",
            "unit",
            "--",
            sys.executable,
            "-c",
            f"from pathlib import Path; Path({str(marker)!r}).write_text('ok')",
            tool=CANARY_CLI,
        )
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(json.loads(first.stdout)["event"], "PASS")
        second = self._run_cli(
            "--ledger",
            str(self.ledger),
            "run",
            "--input",
            str(self.artifact),
            "--check-id",
            "unit",
            "--",
            sys.executable,
            "-c",
            "raise SystemExit('waste')",
            tool=CANARY_CLI,
        )
        self.assertEqual(second.returncode, 0, second.stderr)
        wasted = json.loads(second.stdout)
        self.assertEqual(wasted["event"], "WASTE")
        self.assertEqual(wasted["rule"], trust_cache_canary.RULE)


if __name__ == "__main__":
    unittest.main()
