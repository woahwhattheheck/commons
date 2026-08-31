#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import open_model_release_receipt as receipt


ARTIFACTS = {
    "weights": b"FAKE-WEIGHTS-v1\n",
    "config": b'{"hidden_size":4}\n',
    "tokenizer": b'{"tokens":["open","model"]}\n',
    "loader_ref": b"loader-commit-deadbeef\n",
    "data_provenance": b"synthetic data only\n",
    "license": b"Apache-2.0 synthetic fixture\n",
    "evaluation": b"deterministic fixture; no quality claim\n",
    "sha256sums": b"fixture digest index\n",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_fixture(root: Path) -> Path:
    files = root / "olmo-mini-release"
    files.mkdir()
    rows = []
    for name, data in ARTIFACTS.items():
        filename = f"{name}.bin"
        (files / filename).write_bytes(data)
        rows.append({"name": name, "path": filename, "sha256": digest(data)})
    (files / "loader.py").write_text("print('open model')\n", encoding="utf-8")
    manifest = {
        "release_id": "olmo-mini-release-v1",
        "artifacts": rows,
        "loader": {"command": [sys.executable, "loader.py"], "timeout_seconds": 5},
    }
    path = files / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


class OpenModelReleaseReceiptTests(unittest.TestCase):
    def test_happy_path_is_binary_pass_8_of_8(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = receipt.verify(build_fixture(Path(tmp)))
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["artifact_passes"], 8)
            self.assertTrue(result["loader"]["passed"])

    def test_changed_tokenizer_and_missing_license_are_both_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = build_fixture(Path(tmp))
            base = manifest.parent
            (base / "tokenizer.bin").write_bytes(ARTIFACTS["tokenizer"] + b"X")
            (base / "license.bin").unlink()
            result = receipt.verify(manifest)
            failures = {row["name"]: row for row in result["artifacts"] if not row["passed"]}
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["artifact_passes"], 6)
            self.assertEqual(set(failures), {"tokenizer", "license"})
            self.assertNotEqual(failures["tokenizer"]["actual_sha256"], failures["tokenizer"]["expected_sha256"])
            self.assertIn("FileNotFoundError", failures["license"]["error"])

    def test_loader_failure_prevents_partial_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = build_fixture(Path(tmp))
            data = json.loads(manifest.read_text())
            data["loader"]["command"] = [sys.executable, "-c", "raise SystemExit(7)"]
            manifest.write_text(json.dumps(data))
            result = receipt.verify(manifest)
            self.assertEqual(result["artifact_passes"], 8)
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["loader"]["exit_code"], 7)

    def test_rejects_wrong_artifact_count_and_path_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = build_fixture(Path(tmp))
            data = json.loads(manifest.read_text())
            data["artifacts"].pop()
            manifest.write_text(json.dumps(data))
            with self.assertRaisesRegex(receipt.ManifestError, "exactly eight"):
                receipt.verify(manifest)

        with tempfile.TemporaryDirectory() as tmp:
            manifest = build_fixture(Path(tmp))
            data = json.loads(manifest.read_text())
            data["artifacts"][0]["path"] = "../outside.bin"
            manifest.write_text(json.dumps(data))
            result = receipt.verify(manifest)
            self.assertFalse(result["artifacts"][0]["passed"])
            self.assertIn("escapes manifest directory", result["artifacts"][0]["error"])

    def test_cli_emits_json_and_static_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = build_fixture(root)
            json_out = root / "receipt.json"
            html_out = root / "receipt.html"
            run = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("open_model_release_receipt.py")), "verify", str(manifest), "--json-out", str(json_out), "--html-out", str(html_out)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("PASS 8/8", run.stdout)
            self.assertEqual(json.loads(json_out.read_text())["status"], "PASS")
            page = html_out.read_text()
            self.assertIn('<meta name="viewport"', page)
            self.assertIn("PASS — 8/8 artifacts", page)


if __name__ == "__main__":
    unittest.main()
