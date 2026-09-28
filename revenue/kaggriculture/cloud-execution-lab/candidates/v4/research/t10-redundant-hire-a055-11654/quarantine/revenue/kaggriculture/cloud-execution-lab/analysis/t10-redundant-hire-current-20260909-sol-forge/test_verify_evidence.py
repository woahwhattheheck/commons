# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import verify_evidence as verify

HERE = Path(__file__).resolve().parent
SUMMARY = "SUMMARY.json"


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
                    encoding="utf-8")


def rebind(root: Path) -> None:
    summary = root / "SUMMARY.json"
    manifest = json.loads((root / "MANIFEST.json").read_text(encoding="utf-8"))
    manifest["evidence"]["summary_bytes"] = summary.stat().st_size
    manifest["evidence"]["summary_sha256"] = hashlib.sha256(summary.read_bytes()).hexdigest()
    (root / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                                        encoding="utf-8")


class VerifyEvidenceTests(unittest.TestCase):
    def clone(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        holder = tempfile.TemporaryDirectory()
        root = Path(holder.name)
        (root / "MANIFEST.json").write_bytes((HERE / "MANIFEST.json").read_bytes())
        (root / "SUMMARY.json").write_bytes((HERE / SUMMARY).read_bytes())
        return holder, root

    def test_exact_packet_passes(self):
        holder, root = self.clone()
        self.addCleanup(holder.cleanup)
        result = verify.verify_packet(root)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["complete_games"], 80)
        self.assertEqual(result["paired_cells"], 40)
        self.assertEqual(result["verdict_flips"], {"W->W": 40})
        self.assertGreaterEqual(result["min_margin_delta"], 5)

    def test_byte_tamper_fails_hash_binding(self):
        holder, root = self.clone()
        self.addCleanup(holder.cleanup)
        with (root / "SUMMARY.json").open("ab") as handle:
            handle.write(b" ")
        with self.assertRaisesRegex(verify.EvidenceError, "byte count|SHA-256"):
            verify.verify_packet(root)

    def test_duplicate_cell_fails_even_when_rebound(self):
        holder, root = self.clone()
        self.addCleanup(holder.cleanup)
        summary = json.loads((root / "SUMMARY.json").read_text(encoding="utf-8"))
        summary["games"][1][:4] = summary["games"][0][:4]
        write_json(root / "SUMMARY.json", summary)
        rebind(root)
        with self.assertRaisesRegex(verify.EvidenceError, "duplicate game cell"):
            verify.verify_packet(root)

    def test_negative_cell_fails_even_when_rebound(self):
        holder, root = self.clone()
        self.addCleanup(holder.cleanup)
        summary = json.loads((root / "SUMMARY.json").read_text(encoding="utf-8"))
        row = next(row for row in summary["games"] if row[:4] == [1, 0, 2609097001, 0])
        row[4] -= 100
        row[6] -= 100
        write_json(root / "SUMMARY.json", summary)
        rebind(root)
        with self.assertRaises(verify.EvidenceError):
            verify.verify_packet(root)

    def test_duplicate_json_key_is_rejected(self):
        holder, root = self.clone()
        self.addCleanup(holder.cleanup)
        path = root / "MANIFEST.json"
        text = path.read_text(encoding="utf-8").replace(
            '"schema_version": 1,', '"schema_version": 1,\n  "schema_version": 1,', 1)
        path.write_text(text, encoding="utf-8")
        with self.assertRaisesRegex(verify.EvidenceError, "duplicate JSON key"):
            verify.verify_packet(root)

    def test_wrong_external_archive_is_rejected(self):
        holder, root = self.clone()
        self.addCleanup(holder.cleanup)
        bad = root / "archive.tar.gz"
        bad.write_bytes(b"not the archive")
        with self.assertRaisesRegex(verify.EvidenceError, "archive byte count"):
            verify.verify_packet(root, archive=bad)


if __name__ == "__main__":
    unittest.main()
