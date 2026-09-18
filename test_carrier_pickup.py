#!/usr/bin/env python3
"""Focused contract tests for formal CARRIER_ONLY→main carrier pickup lane."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from host import carrier_pickup


class CarrierPickupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_verbatim_match_and_readback_emits_valid_receipt(self) -> None:
        content1 = "print('Hello world!')\n"
        content2 = b"\x00\x01\x02\x03\x04\x05"
        sha1 = hashlib.sha256(content1.encode("utf-8")).hexdigest()
        sha2 = hashlib.sha256(content2).hexdigest()

        payload = {
            "schema": carrier_pickup.INPUT_SCHEMA,
            "offered_by": "credless-slug-alpha",
            "carrier_source": "slack-file",
            "source_ref": "F088234",
            "items": [
                {
                    "path": "src/hello.py",
                    "content": content1,
                    "sha256": sha1,
                },
                {
                    "path": "bin/data.bin",
                    "content_base64": base64.b64encode(content2).decode("ascii"),
                    "sha256": sha2,
                },
            ],
        }

        receipt = carrier_pickup.verify_and_land(
            payload,
            root_dir=self.root,
            landing_seat="live-cloud-seat",
            observed_at="2026-09-01T12:00:00Z",
        )

        # Verify receipt structure and attribution
        self.assertEqual(receipt["schema"], carrier_pickup.RECEIPT_SCHEMA)
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["landing_seat"], "live-cloud-seat")
        self.assertEqual(receipt["offered_by"], "credless-slug-alpha")
        self.assertEqual(receipt["carrier_source"], "slack-file")
        self.assertEqual(receipt["source_ref"], "F088234")
        self.assertEqual(receipt["files_count"], 2)
        self.assertIn("Landed verbatim by live-cloud-seat on behalf of credless-slug-alpha", receipt["attribution_line"])

        # Check files on disk
        target_file1 = self.root / "src" / "hello.py"
        target_file2 = self.root / "bin" / "data.bin"
        self.assertTrue(target_file1.exists())
        self.assertTrue(target_file2.exists())
        self.assertEqual(target_file1.read_text(encoding="utf-8"), content1)
        self.assertEqual(target_file2.read_bytes(), content2)

        # Landed blob readback equality
        self.assertEqual(hashlib.sha256(target_file1.read_bytes()).hexdigest(), sha1)
        self.assertEqual(hashlib.sha256(target_file2.read_bytes()).hexdigest(), sha2)

    def test_byte_mismatch_fails_closed_before_any_write(self) -> None:
        good_content = "File 1 contents\n"
        bad_content = "File 2 mismatch contents\n"
        good_sha = hashlib.sha256(good_content.encode("utf-8")).hexdigest()
        bad_sha = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"

        payload = {
            "schema": carrier_pickup.INPUT_SCHEMA,
            "offered_by": "peer-beta",
            "items": [
                {
                    "path": "goods/first.txt",
                    "content": good_content,
                    "sha256": good_sha,
                },
                {
                    "path": "goods/second.txt",
                    "content": bad_content,
                    "sha256": bad_sha,
                },
            ],
        }

        with self.assertRaises(carrier_pickup.VerificationMismatchError):
            carrier_pickup.verify_and_land(payload, root_dir=self.root)

        # Fails closed: Ensure NO files were created
        self.assertFalse((self.root / "goods" / "first.txt").exists())
        self.assertFalse((self.root / "goods" / "second.txt").exists())
        self.assertFalse((self.root / "goods").exists())

    def test_missing_path_or_payload_fails_closed(self) -> None:
        # Missing path
        bad_payload_missing_path = {
            "items": [
                {"content": "something"}
            ]
        }
        with self.assertRaises(carrier_pickup.CarrierPickupError):
            carrier_pickup.verify_and_land(bad_payload_missing_path, root_dir=self.root)

        # Missing payload
        bad_payload_missing_payload = {
            "items": [
                {"path": "empty.txt"}
            ]
        }
        with self.assertRaises(carrier_pickup.CarrierPickupError):
            carrier_pickup.verify_and_land(bad_payload_missing_payload, root_dir=self.root)

        # Empty items list
        bad_empty = {"items": []}
        with self.assertRaises(carrier_pickup.CarrierPickupError):
            carrier_pickup.verify_and_land(bad_empty, root_dir=self.root)

    def test_path_traversal_fails_closed(self) -> None:
        traversal_attempts = [
            "../escape.py",
            "/etc/passwd",
            "foo/../../bar.txt",
            "..",
        ]
        for bad_path in traversal_attempts:
            payload = {
                "items": [
                    {"path": bad_path, "content": "malicious"}
                ]
            }
            with self.assertRaises(carrier_pickup.PathSecurityError):
                carrier_pickup.verify_and_land(payload, root_dir=self.root)

    def test_duplicate_path_fails_closed(self) -> None:
        payload = {
            "items": [
                {"path": "dup.txt", "content": "version 1"},
                {"path": "dup.txt", "content": "version 2"},
            ]
        }
        with self.assertRaises(carrier_pickup.CarrierPickupError):
            carrier_pickup.verify_and_land(payload, root_dir=self.root)
        self.assertFalse((self.root / "dup.txt").exists())

    def test_dry_run_verifies_without_writing(self) -> None:
        content = "Dry run test\n"
        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        payload = {
            "items": [
                {"path": "dry.txt", "content": content, "sha256": sha}
            ]
        }
        receipt = carrier_pickup.verify_and_land(payload, root_dir=self.root, write_files=False)
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["files"][0]["status"], "VERIFIED_DRY")
        self.assertFalse((self.root / "dry.txt").exists())

    def test_verify_landed_tree_checks_matching_and_missing(self) -> None:
        file1 = self.root / "test1.txt"
        file1.write_text("hello 1", encoding="utf-8")
        sha1 = hashlib.sha256(b"hello 1").hexdigest()

        # All match
        check1 = carrier_pickup.verify_landed_tree([
            {"path": "test1.txt", "sha256": sha1}
        ], root_dir=self.root)
        self.assertEqual(check1["status"], "PASS")

        # Missing on disk
        check2 = carrier_pickup.verify_landed_tree([
            {"path": "test1.txt", "sha256": sha1},
            {"path": "missing.txt", "sha256": "abcdef"},
        ], root_dir=self.root)
        self.assertEqual(check2["status"], "FAIL")
        self.assertEqual(check2["results"][1]["status"], "MISSING_ON_DISK")

        # Hash mismatch on disk
        check3 = carrier_pickup.verify_landed_tree([
            {"path": "test1.txt", "sha256": "0000000000000000000000000000000000000000000000000000000000000000"}
        ], root_dir=self.root)
        self.assertEqual(check3["status"], "FAIL")
        self.assertEqual(check3["results"][0]["status"], "HASH_MISMATCH")

    def test_cli_execution_and_self_test(self) -> None:
        # Test CLI --self-test
        res = subprocess.run(
            [sys.executable, str(Path(carrier_pickup.__file__).resolve()), "--self-test"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "PASS")

        # Test CLI stdin landing
        payload = {
            "offered_by": "cli-peer",
            "items": [{"path": "cli_output.txt", "content": "from cli\n"}]
        }
        res_stdin = subprocess.run(
            [sys.executable, str(Path(carrier_pickup.__file__).resolve()), "--root", str(self.root), "--seat", "cli-seat"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_stdin.returncode, 0)
        receipt = json.loads(res_stdin.stdout)
        self.assertEqual(receipt["status"], "PASS")
        self.assertTrue((self.root / "cli_output.txt").exists())
        self.assertEqual((self.root / "cli_output.txt").read_text(encoding="utf-8"), "from cli\n")


if __name__ == "__main__":
    unittest.main()
