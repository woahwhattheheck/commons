"""Benign source-custody regressions for UIOWA-032; all I/O is temporary.

Run beside the component files with python -m unittest -v test_integrity.
The same tests express the desired contract on the original and patched versions.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent


def _load_sibling(stem: str):
    # Keep this suite hermetic when many repository components use generic names.
    path = HERE / f"{stem}.py"
    namespace = "_uiowa032_" + stem + "_" + hashlib.sha256(str(path).encode()).hexdigest()[:12]
    spec = importlib.util.spec_from_file_location(namespace, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load sibling module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[namespace] = module
    spec.loader.exec_module(module)
    return module


extract = _load_sibling("extract")
corpus = _load_sibling("make_synthetic_corpus")
HAS_PYPDF = importlib.util.find_spec("pypdf") is not None


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def text(self, name="evidence.txt", raw=b"# Review\nSynthetic original evidence.\n"):
        p = self.root / name
        p.write_bytes(raw)
        return p

    def docx(self, name="evidence.docx", body=None):
        p = self.root / name
        corpus._write_minimal_docx(p)
        if body is not None:
            with zipfile.ZipFile(p) as zf:
                entries = {item.filename: zf.read(item.filename) for item in zf.infolist()}
            entries["word/document.xml"] = (
                f'<w:document xmlns:w="{extract.W_NS}"><w:body>{body}'
                '<w:sectPr/></w:body></w:document>'
            ).encode()
            with zipfile.ZipFile(p, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for name, data in entries.items():
                    zf.writestr(name, data)
        return p

    def cli(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = extract.main([str(a) for a in args])
        return code, json.loads(output.getvalue()) if output.getvalue() else None

    def binding(self, suffix, parser):
        if suffix == ".docx":
            p = self.docx()
        elif suffix == ".pdf":
            p = self.root / "evidence.pdf"
            corpus._write_minimal_pdf(p, ["Synthetic original PDF evidence."])
        else:
            p = self.text()
        original_bytes = p.read_bytes()
        parse = getattr(extract, parser)

        def replace_after_parse(*args, **kwargs):
            result = parse(*args, **kwargs)
            # Simulates an ordinary source revision arriving after the parser returns.
            p.write_bytes(b"A different source revision, deliberately a different size.\n")
            return result

        with patch.object(extract, parser, side_effect=replace_after_parse):
            result = extract.extract(p)
        self.assertEqual(result["document"]["sha256"], hashlib.sha256(original_bytes).hexdigest())
        self.assertEqual(result["document"]["bytes"], len(original_bytes))
        self.assertNotEqual(p.read_bytes(), original_bytes)

    def test_text_hash_matches_parsed_snapshot_after_source_revision(self):
        self.binding(".txt", "extract_text")

    def test_docx_hash_matches_parsed_snapshot_after_source_revision(self):
        self.binding(".docx", "extract_docx")

    @unittest.skipUnless(HAS_PYPDF, "PDF backend absent; missing-backend contract tested separately")
    def test_pdf_hash_matches_parsed_snapshot_after_source_revision(self):
        self.binding(".pdf", "extract_pdf")

    def test_high_level_extraction_does_not_reopen_source_to_hash(self):
        p = self.text()
        with patch.object(extract, "sha256_file", side_effect=AssertionError("second read")):
            result = extract.extract(p)
        self.assertEqual(result["document"]["sha256"], hashlib.sha256(p.read_bytes()).hexdigest())

    def test_raw_crlf_bom_and_nonascii_bytes_remain_hash_authority(self):
        raw = b"\xef\xbb\xbf# Evidence\r\nCaf\xc3\xa9 example.\r\n"
        result = extract.extract(self.text(raw=raw))
        self.assertEqual(result["document"]["bytes"], len(raw))
        self.assertEqual(result["document"]["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertIn("Caf\u00e9 example.", " ".join(s["text"] for s in result["segments"]))

    def test_invalid_utf8_still_hashes_original_bytes(self):
        raw = b"Synthetic \xff evidence."
        result = extract.extract(self.text(raw=raw))
        self.assertIn("TEXT_DECODE_REPLACEMENTS_USED", result["warnings"])
        self.assertEqual(result["document"]["sha256"], hashlib.sha256(raw).hexdigest())

    def test_empty_file_stays_unreadable(self):
        result = extract.extract(self.text(raw=b""))
        self.assertEqual(result["status"], "unreadable")
        self.assertEqual(result["document"]["sha256"], hashlib.sha256(b"").hexdigest())

    def test_size_limit_checks_actual_read(self):
        p = self.text(raw=b"01234567890")
        with patch.object(extract, "MAX_BYTES", 10):
            with self.assertRaisesRegex(extract.ExtractionError, "INPUT_TOO_LARGE"):
                extract.extract(p)

    def test_exact_size_limit_is_accepted(self):
        p = self.text(raw=b"0123456789")
        with patch.object(extract, "MAX_BYTES", 10):
            self.assertEqual(extract.extract(p)["document"]["bytes"], 10)

    def assert_alias_preserved(self, source, destination):
        before = source.read_bytes()
        code, result = self.cli(source, "-o", destination)
        self.assertEqual(source.read_bytes(), before, "Original evidence was overwritten")
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "error")
        self.assertIn("OUTPUT_ALIASES_INPUT", result["error"])

    def test_cli_rejects_same_input_and_output(self):
        source = self.text()
        self.assert_alias_preserved(source, source)

    def test_cli_rejects_symlink_to_source(self):
        source = self.text()
        target = self.root / "result.json"
        target.symlink_to(source)
        self.assert_alias_preserved(source, target)
        self.assertTrue(target.is_symlink())

    def test_cli_rejects_hardlink_to_source(self):
        source = self.text()
        target = self.root / "result.json"
        os.link(source, target)
        self.assert_alias_preserved(source, target)

    def test_cli_rejects_normalized_relative_alias(self):
        source = self.text()
        (self.root / "subdir").mkdir()
        self.assert_alias_preserved(source, self.root / "subdir" / ".." / source.name)

    def test_cli_distinct_output_preserves_source(self):
        source = self.text()
        before = source.read_bytes()
        target = self.root / "result.json"
        code, stdout = self.cli(source, "-o", target)
        self.assertEqual(code, 0)
        self.assertIsNone(stdout)
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(json.loads(target.read_text())["document"]["sha256"], hashlib.sha256(before).hexdigest())

    def test_cli_replaces_existing_distinct_report(self):
        source = self.text()
        target = self.text("result.json", b"previous report")
        code, stdout = self.cli(source, "-o", target)
        self.assertEqual(code, 0)
        self.assertIsNone(stdout)
        self.assertEqual(json.loads(target.read_text())["schema"], extract.SCHEMA)

    def test_cli_output_directory_error_is_structured(self):
        source = self.text()
        code, result = self.cli(source, "-o", self.root)
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "error")
        self.assertTrue(self.root.is_dir())

    def test_cli_missing_parent_error_is_structured(self):
        source = self.text()
        code, result = self.cli(source, "-o", self.root / "absent" / "result.json")
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "error")
        self.assertFalse((self.root / "absent").exists())

    def test_missing_source_error_is_structured(self):
        code, result = self.cli(self.root / "missing.txt")
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "error")

    def test_input_directory_is_rejected(self):
        with self.assertRaises(extract.ExtractionError):
            extract.extract(self.root)

    def test_docx_content_control_retains_critical_paragraph(self):
        p = self.docx(body='''
<w:p><w:r><w:t>Synthetic introductory note.</w:t></w:r></w:p>
<w:sdt><w:sdtPr><w:tag w:val="approval-evidence"/></w:sdtPr><w:sdtContent>
<w:p><w:r><w:t>Approval remains unverified in this fictional example.</w:t></w:r></w:p>
</w:sdtContent></w:sdt>
<w:p><w:r><w:t>Closing note.</w:t></w:r></w:p>''')
        result = extract.extract(p)
        text = " ".join(s["text"] for s in result["segments"])
        self.assertIn("Approval remains unverified", text)
        segment = next(s for s in result["segments"] if "Approval remains" in s["text"])
        self.assertIn("sdt[1]", segment["locator"])
        self.assertIn("sdtContent[1]", segment["locator"])
        closing = next(s for s in result["segments"] if s["text"] == "Closing note.")
        self.assertEqual(closing["locator"], "paragraph 2")

    def test_docx_nested_controls_retain_heading_context(self):
        p = self.docx(body='''<w:sdt><w:sdtContent><w:customXml>
<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Synthetic Review</w:t></w:r></w:p>
<w:sdt><w:sdtContent><w:p><w:r><w:t>Evidence inside nested controls.</w:t></w:r></w:p></w:sdtContent></w:sdt>
</w:customXml></w:sdtContent></w:sdt>''')
        result = extract.extract(p)
        segment = next(s for s in result["segments"] if s["text"] == "Evidence inside nested controls.")
        self.assertEqual(segment["heading_path"], ["Synthetic Review"])
        self.assertIn("customXml[1]", segment["locator"])

    def test_docx_wrapped_table_is_preserved(self):
        p = self.docx(body='''<w:sdt><w:sdtContent><w:tbl><w:tr>
<w:tc><w:p><w:r><w:t>Synthetic artifact</w:t></w:r></w:p></w:tc>
<w:tc><w:p><w:r><w:t>EV-01</w:t></w:r></w:p></w:tc>
</w:tr></w:tbl></w:sdtContent></w:sdt>''')
        result = extract.extract(p)
        table = next(s for s in result["segments"] if s["kind"] == "table")
        self.assertEqual(table["text"], "Synthetic artifact | EV-01")
        self.assertIn("tbl[1]", table["locator"])

    def test_docx_unsupported_body_content_is_explicit(self):
        p = self.docx(body='<w:p><w:r><w:t>Synthetic note.</w:t></w:r></w:p><w:altChunk/>')
        result = extract.extract(p)
        self.assertTrue(any("UNSUPPORTED_BODY_ELEMENT" in w and "altChunk" in w for w in result["warnings"]))

    def test_docx_empty_content_control_is_explicit(self):
        p = self.docx(body='<w:sdt><w:sdtPr/></w:sdt>')
        result = extract.extract(p)
        self.assertEqual(result["status"], "unreadable")
        self.assertTrue(any("CONTENT_CONTROL_MISSING_CONTENT" in w for w in result["warnings"]))

    def test_docx_tracked_changes_are_disclosed(self):
        p = self.docx(body='<w:p><w:ins><w:r><w:t>Synthetic proposed wording.</w:t></w:r></w:ins></w:p>')
        result = extract.extract(p)
        self.assertTrue(any("TRACKED_CHANGES_PRESENT" in w for w in result["warnings"]))

    def test_standalone_parsers_match_high_level_segments(self):
        for suffix, parser in [(".txt", extract.extract_text), (".docx", extract.extract_docx)]:
            p = self.text() if suffix == ".txt" else self.docx()
            segments, warnings = parser(p)
            result = extract.extract(p)
            self.assertEqual([s.text for s in segments], [s["text"] for s in result["segments"]])
            self.assertEqual(warnings, result["warnings"])

    def test_atomic_replace_failure_keeps_previous_report_and_cleans_temp(self):
        source = self.text()
        target = self.text("result.json", b"previous report")
        before = set(self.root.iterdir())
        with patch("os.replace", side_effect=PermissionError("synthetic write failure")):
            code, result = self.cli(source, "-o", target)
        self.assertEqual(target.read_bytes(), b"previous report")
        self.assertEqual(set(self.root.iterdir()), before)
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "error")

    def test_distinct_report_symlink_does_not_modify_its_target(self):
        source = self.text()
        unrelated = self.text("other-record.txt", b"unrelated synthetic record")
        target = self.root / "result.json"
        target.symlink_to(unrelated)
        code, _ = self.cli(source, "-o", target)
        self.assertEqual(code, 0)
        self.assertEqual(unrelated.read_bytes(), b"unrelated synthetic record")
        self.assertFalse(target.is_symlink())
        self.assertEqual(json.loads(target.read_text())["schema"], extract.SCHEMA)

    def test_distinct_report_hardlink_does_not_modify_its_target(self):
        source = self.text()
        unrelated = self.text("other-record.txt", b"unrelated synthetic record")
        target = self.root / "result.json"
        os.link(unrelated, target)
        code, _ = self.cli(source, "-o", target)
        self.assertEqual(code, 0)
        self.assertEqual(unrelated.read_bytes(), b"unrelated synthetic record")
        self.assertFalse(unrelated.samefile(target))

    def test_parse_failure_does_not_replace_previous_report(self):
        source = self.text("broken.docx", b"Not a Word archive")
        target = self.text("result.json", b"previous report")
        code, result = self.cli(source, "-o", target)
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "error")
        self.assertEqual(target.read_bytes(), b"previous report")

    def test_missing_pdf_backend_has_named_error(self):
        source = self.root / "synthetic.pdf"
        corpus._write_minimal_pdf(source, ["Synthetic dependency contract."])
        with patch.dict(sys.modules, {"pypdf": None}):
            with self.assertRaisesRegex(extract.ExtractionError, "PDF_BACKEND_UNAVAILABLE"):
                extract.extract(source)


if __name__ == "__main__":
    unittest.main()
