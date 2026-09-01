import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest

from charttrace.core.pdf import build_minimal_pdf
from charttrace.storage.ingest import (
    HOLD_ENCRYPTED_INPUT,
    HOLD_SOURCE_HASH_MISMATCH,
    HOLD_SOURCE_TAMPER,
    ImmutableIngestor,
    IngestHold,
)


class ImmutableIngestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "synthetic-record.pdf"
        self.source_bytes = build_minimal_pdf(
            [
                "CT|FACT|FACT-001|2026-01-02|EXACT|chronology|visit|Synthetic event.",
                "Synthetic page two.",
            ]
        )
        self.source.write_bytes(self.source_bytes)
        self.source_mode = stat.S_IMODE(self.source.stat().st_mode)
        self.ingestor = ImmutableIngestor(self.root / "case")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_exact_copy_hash_pages_permissions_and_duplicate(self) -> None:
        expected_hash = hashlib.sha256(self.source_bytes).hexdigest()
        first = self.ingestor.ingest(
            self.source,
            document_id="SYNTH-DOC-001",
            expected_sha256=expected_hash,
        )
        second = self.ingestor.ingest(
            self.source,
            document_id="SYNTH-DOC-002",
        )
        stored = self.ingestor.case_root / first.stored_path

        self.assertEqual(self.source.read_bytes(), self.source_bytes)
        self.assertEqual(stat.S_IMODE(self.source.stat().st_mode), self.source_mode)
        self.assertEqual(stored.read_bytes(), self.source_bytes)
        self.assertEqual(first.source_hash, expected_hash)
        self.assertEqual(first.size_bytes, len(self.source_bytes))
        self.assertEqual(first.mime_type, "application/pdf")
        self.assertEqual(first.page_count, 2)
        self.assertFalse(first.encrypted)
        self.assertIsNone(first.duplicate_of)
        self.assertEqual(second.duplicate_of, "SYNTH-DOC-001")
        self.assertEqual(second.stored_path, first.stored_path)
        stored_mode = stat.S_IMODE(stored.stat().st_mode)
        self.assertNotEqual(stored_mode & stat.S_IRUSR, 0)
        self.assertEqual(
            stored_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH), 0
        )
        self.assertEqual(first.to_dict()["source_sha256"], expected_hash)
        manifest_records = [
            json.loads(line)
            for line in self.ingestor.manifest_path.read_text("ascii").splitlines()
        ]
        self.assertEqual(
            [record["source_sha256"] for record in manifest_records],
            [expected_hash, expected_hash],
        )
        self.assertEqual(self.ingestor.verify_all(), (first, second))

        reopened = ImmutableIngestor(self.ingestor.case_root)
        self.assertEqual(reopened.entries, (first, second))

    def test_hash_mismatch_fails_closed_without_manifest_entry(self) -> None:
        with self.assertRaises(IngestHold) as raised:
            self.ingestor.ingest(
                self.source,
                document_id="SYNTH-DOC-001",
                expected_sha256="0" * 64,
            )
        self.assertIs(raised.exception.code, HOLD_SOURCE_HASH_MISMATCH)
        self.assertEqual(self.ingestor.entries, ())
        self.assertFalse(self.ingestor.manifest_path.exists())

    def test_encrypted_pdf_fails_closed(self) -> None:
        encrypted = self.root / "synthetic-encrypted.pdf"
        encrypted.write_bytes(
            self.source_bytes.replace(
                b"trailer\n<<", b"trailer\n<< /Encrypt 99 0 R "
            )
        )
        with self.assertRaises(IngestHold) as raised:
            self.ingestor.ingest(encrypted, document_id="SYNTH-DOC-ENC")
        self.assertIs(raised.exception.code, HOLD_ENCRYPTED_INPUT)
        self.assertEqual(self.ingestor.entries, ())

    def test_tampered_original_and_derivative_hash_fail_closed(self) -> None:
        entry = self.ingestor.ingest(
            self.source, document_id="SYNTH-DOC-001"
        )
        stored = self.ingestor.case_root / entry.stored_path
        os.chmod(stored, 0o600)
        stored.write_bytes(b"tampered synthetic bytes")
        with self.assertRaises(IngestHold) as raised:
            self.ingestor.verify_original(entry)
        self.assertIs(raised.exception.code, HOLD_SOURCE_TAMPER)

        second_case = ImmutableIngestor(self.root / "second-case")
        clean = second_case.ingest(self.source, document_id="SYNTH-DOC-002")
        with self.assertRaises(IngestHold) as derivative_hold:
            second_case.store_derivative(
                clean.document_id,
                "page.txt",
                b"synthetic derivative",
                source_hash="0" * 64,
            )
        self.assertIs(derivative_hold.exception.code, HOLD_SOURCE_HASH_MISMATCH)
        derivative = second_case.store_derivative(
            clean.document_id,
            "page.txt",
            b"synthetic derivative",
            source_hash=clean.source_hash,
        )
        self.assertTrue(
            derivative.is_relative_to(second_case.derivatives_dir)
        )
        self.assertFalse(
            derivative.is_relative_to(second_case.originals_dir)
        )


if __name__ == "__main__":
    unittest.main()
