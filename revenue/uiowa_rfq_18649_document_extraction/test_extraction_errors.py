"""Offline source-snapshot and error-contract checks; all artifacts are fictional."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

import extract
import make_synthetic_corpus


class ErrorContractTests(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.root = Path(work.name)

    def cli(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = extract.main([str(arg) for arg in args])
        return code, json.loads(output.getvalue())

    def assert_snapshot_survives_replacement(self, suffix, backend_name, make):
        source = self.root / ('synthetic' + suffix)
        make(source)
        original = source.read_bytes()
        backend = getattr(extract, backend_name)

        def change_source_after_snapshot(raw):
            source.write_bytes(b'New source bytes after the captured snapshot.')
            return backend(raw)

        with patch.object(extract, backend_name, side_effect=change_source_after_snapshot):
            result = extract.extract(source)
        self.assertEqual(result['document']['bytes'], len(original))
        self.assertEqual(result['document']['sha256'], hashlib.sha256(original).hexdigest())
        self.assertNotEqual(result['document']['sha256'], hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertTrue(any(segment['text'] for segment in result['segments']))
        self.assertNotIn('New source bytes', json.dumps(result['segments']))

    def test_text_parser_and_digest_share_prechange_snapshot(self):
        self.assert_snapshot_survives_replacement('.md', '_extract_text_bytes',
            lambda p: p.write_text('# Synthetic\nOriginal text.\n', encoding='utf-8'))

    def test_docx_parser_and_digest_share_prechange_snapshot(self):
        self.assert_snapshot_survives_replacement('.docx', '_extract_docx_bytes',
            make_synthetic_corpus._write_minimal_docx)

    def test_pdf_parser_and_digest_share_prechange_snapshot(self):
        self.assert_snapshot_survives_replacement('.pdf', '_extract_pdf_bytes',
            lambda p: make_synthetic_corpus._write_minimal_pdf(p, ['Original synthetic PDF.']))

    def test_missing_backend_has_named_cli_error(self):
        source = self.root / 'synthetic.pdf'
        make_synthetic_corpus._write_minimal_pdf(source, ['Synthetic PDF.'])
        with patch.dict(sys.modules, {'pypdf': None}):
            code, payload = self.cli(source)
        self.assertEqual(code, 2)
        self.assertEqual(payload['status'], 'error')
        self.assertIn('PDF_BACKEND_UNAVAILABLE', payload['error'])
        self.assertEqual(payload['segments'], [])

    def test_missing_source_has_structured_error(self):
        code, payload = self.cli(self.root / 'missing.txt')
        self.assertEqual(code, 2)
        self.assertEqual(payload['status'], 'error')
        self.assertEqual(payload['error'], 'INPUT_NOT_A_REGULAR_FILE')

    def test_read_failure_does_not_emit_extracted_evidence(self):
        source = self.root / 'synthetic.txt'
        source.write_text('Synthetic.', encoding='utf-8')
        with patch.object(Path, 'open', side_effect=PermissionError('synthetic failure')):
            code, payload = self.cli(source)
        self.assertEqual(code, 2)
        self.assertEqual(payload['error'], 'INPUT_READ_FAILED:PermissionError')
        self.assertEqual(payload['segments'], [])

    def test_observed_metadata_change_is_not_a_success(self):
        source = self.root / 'synthetic.txt'
        source.write_text('Synthetic.', encoding='utf-8')
        before = source.stat()
        after = SimpleNamespace(**{name: getattr(before, name) for name in
            ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_mode')})
        after.st_mtime_ns += 1
        with patch.object(os, 'fstat', side_effect=[before, after]):
            code, payload = self.cli(source)
        self.assertEqual(code, 2)
        self.assertEqual(payload['error'], 'INPUT_CHANGED_DURING_READ')
        self.assertEqual(payload['segments'], [])

    def test_corrupt_docx_has_named_error(self):
        source = self.root / 'synthetic.docx'
        source.write_bytes(b'Not a ZIP file. Synthetic malformed input.')
        code, payload = self.cli(source)
        self.assertEqual(code, 2)
        self.assertEqual(payload['error'], 'DOCX_INVALID_ZIP_CONTAINER')

    def test_missing_main_document_has_named_error(self):
        source = self.root / 'synthetic.docx'
        with zipfile.ZipFile(source, 'w') as archive:
            archive.writestr('unrelated.txt', 'Synthetic.')
        code, payload = self.cli(source)
        self.assertEqual(code, 2)
        self.assertEqual(payload['error'], 'DOCX_MISSING_word/document.xml')

    def test_malformed_style_part_does_not_silently_invent_context(self):
        source = self.root / 'synthetic.docx'
        make_synthetic_corpus._write_minimal_docx(source)
        with zipfile.ZipFile(source, 'a') as archive:
            archive.writestr('word/styles.xml', '<not-closed')
        result = extract.extract(source)
        self.assertEqual(result['status'], 'partial')
        self.assertTrue(any('STYLES_XML_PARSE_ERROR' in warning for warning in result['warnings']))
        self.assertTrue(any(segment['text'] for segment in result['segments']))

    def test_docx_expanded_part_limit_is_checked(self):
        source = self.root / 'synthetic.docx'
        make_synthetic_corpus._write_minimal_docx(source)
        original = extract.MAX_BYTES
        try:
            # Call the bytes backend to distinguish package bytes from expanded XML.
            extract.MAX_BYTES = 8
            with self.assertRaisesRegex(extract.ExtractionError, 'DOCX_PART_TOO_LARGE'):
                extract._extract_docx_bytes(source.read_bytes())
        finally:
            extract.MAX_BYTES = original

    def test_invalid_pdf_has_named_open_error(self):
        source = self.root / 'synthetic.pdf'
        source.write_bytes(b'%PDF-1.4\nSynthetic incomplete PDF.\n')
        code, payload = self.cli(source)
        self.assertEqual(code, 2)
        self.assertTrue(payload['error'].startswith('PDF_OPEN_FAILED:'))
        self.assertEqual(payload['segments'], [])


if __name__ == '__main__':
    unittest.main()
