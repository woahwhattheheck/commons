"""Tests for the UIOWA-136B structural validator.

A validator that passes a file it should reject is worse than no validator, so
almost every test here BREAKS THE REAL RENDERED DOCUMENT ON PURPOSE and asserts
that the named defect fires. The clean file is the control.

Corruptions are byte-length-preserving wherever possible so the targeted defect
is the one being measured rather than a cascade. Where a corruption does
cascade, the assertion is that the expected defect is among those reported --
never that it is the only one.
"""

from __future__ import annotations

import io
import os
import re
import shutil
import tempfile
import unittest
import zipfile

import bid_pack
import packcheck

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")
MANIFEST = os.path.join(FIXTURES, "manifest.json")


class RenderedCase(unittest.TestCase):
    """Renders the real pack once, then each test corrupts a copy of the bytes."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="packcheck-")
        manifest = bid_pack.load_manifest(MANIFEST)
        bid_pack.BidPack(manifest, FIXTURES).assemble(cls.tmp)
        with open(os.path.join(cls.tmp, "proposal.pdf"), "rb") as fh:
            cls.pdf = fh.read()
        cls.docx = os.path.join(cls.tmp, "proposal.docx")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def assertDefect(self, report, name):
        self.assertIn(name, report.defect_names,
                      "expected defect %r; got %r" % (name, report.defect_names))

    def sub(self, pattern, repl, count=1):
        """Byte-substitute in a copy of the rendered PDF, asserting it applied.

        count=0 means every occurrence (re.subn semantics).
        """
        out, n = re.subn(pattern, repl, self.pdf, count=count)
        if count:
            self.assertEqual(n, count, "corruption pattern %r did not apply" % pattern)
        else:
            self.assertGreater(n, 0, "corruption pattern %r did not apply" % pattern)
        return out


# --------------------------------------------------------------------------

class CleanFileTests(RenderedCase):

    def test_the_real_rendered_pdf_has_no_structural_defect(self):
        r = packcheck.check_pdf(self.pdf, "control")
        self.assertTrue(r.clean, "control file reported defects: %r" % r.defects)
        self.assertGreaterEqual(len(r.checks), 15)
        # the checks that matter most must actually have RUN, not been skipped
        for name in ("xref_offsets_resolve", "stream_lengths", "references_resolve",
                     "page_count", "destinations_in_document", "outline_chain"):
            self.assertIn(name, [n for n, _, _ in r.checks])

    def test_the_real_rendered_docx_has_no_structural_defect(self):
        r = packcheck.check_docx(self.docx)
        self.assertTrue(r.clean, "control file reported defects: %r" % r.defects)

    def test_an_unchecked_file_is_reported_as_not_run_never_as_a_pass(self):
        import contextlib
        path = os.path.join(self.tmp, "00-INDEX.md")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = packcheck.main([path])
        # Nothing was WRONG, so the exit code is 0 -- but nothing was CHECKED
        # either, and the report has to say that out loud rather than let a
        # reader take "0 defects" for "verified".
        self.assertEqual(rc, 0)
        self.assertIn("0 check(s) run", buf.getvalue())
        self.assertIn("NOT RUN: not a .pdf or .docx", buf.getvalue())


# --------------------------------------------------------------------------

class CorruptedPdfTests(RenderedCase):

    def test_truncated_file_is_caught(self):
        r = packcheck.check_pdf(self.pdf[:-60], "truncated")
        self.assertDefect(r, "eof_marker")

    def test_wrong_magic_header_is_caught(self):
        r = packcheck.check_pdf(b"%XDF-1.4" + self.pdf[8:], "bad header")
        self.assertDefect(r, "header")
        self.assertEqual(len(r.checks), 1, "checking stopped at the header, as it should")

    def test_xref_offset_off_by_one_is_caught(self):
        # The defect a same-author reader can never see: pdfwrite's reader scans
        # for 'N 0 obj' and never consults the xref table, so this file would
        # read back perfectly and still break a real viewer.
        m = re.search(rb"xref\s+\d+\s+\d+\s+0000000000 65535 f \n(\d{10}) 00000 n ",
                      self.pdf)
        self.assertIsNotNone(m)
        shifted = b"%010d" % (int(m.group(1)) + 1)
        broken = self.pdf[:m.start(1)] + shifted + self.pdf[m.end(1):]
        self.assertEqual(len(broken), len(self.pdf))
        r = packcheck.check_pdf(broken, "shifted xref")
        self.assertDefect(r, "xref_offsets_resolve")
        # and prove the circularity claim: the same-author reader is unbothered
        import pdfwrite
        self.assertEqual(len(pdfwrite.read_pdf_pages(broken)),
                         len(pdfwrite.read_pdf_pages(self.pdf)))

    def test_falsified_stream_length_is_caught(self):
        m = re.search(rb"/Length (\d+) >>", self.pdf)
        self.assertIsNotNone(m)
        n = int(m.group(1))
        fake = n + 1 if len(str(n + 1)) == len(str(n)) else n - 1
        broken = self.pdf[:m.start(1)] + str(fake).encode() + self.pdf[m.end(1):]
        self.assertEqual(len(broken), len(self.pdf))
        r = packcheck.check_pdf(broken, "bad /Length")
        self.assertDefect(r, "stream_lengths")

    def test_reference_to_a_nonexistent_object_is_caught(self):
        r = packcheck.check_pdf(self.sub(rb"/Contents (\d\d) 0 R", b"/Contents 99 0 R"),
                                "dangling ref")
        self.assertDefect(r, "references_resolve")

    def test_page_count_that_disagrees_with_the_kids_array_is_caught(self):
        m = re.search(rb"/Kids \[ (.*?) \] /Count (\d+)", self.pdf, re.S)
        self.assertIsNotNone(m)
        real = int(m.group(2))
        broken = self.pdf[:m.start(2)] + str(real - 1).encode() + self.pdf[m.end(2):]
        r = packcheck.check_pdf(broken, "bad /Count")
        self.assertDefect(r, "page_count")

    def test_destination_pointing_outside_the_document_is_caught(self):
        r = packcheck.check_pdf(self.sub(rb"/Dest \[ (\d\d) 0 R", b"/Dest [ 97 0 R"),
                                "dest outside doc")
        self.assertDefect(r, "destinations_in_document")

    def test_font_used_but_not_declared_in_resources_is_caught(self):
        # Rename the resource key on EVERY page, leaving the content streams
        # still asking for /FC. Renaming it on one page is not enough: the title
        # page never uses Courier, so a single-page rename is a no-op and the
        # validator is right to report nothing.
        r = packcheck.check_pdf(self.sub(rb"/FC (\d+) 0 R >> >>", rb"/FZ \1 0 R >> >>",
                                         count=0),
                                "undeclared font")
        self.assertDefect(r, "fonts_declared")
        self.assertIn("/FC", dict(r.defects)["fonts_declared"])

    def test_broken_outline_chain_is_caught(self):
        r = packcheck.check_pdf(self.sub(rb"/Next (\d+) 0 R", b"/Next 96 0 R"),
                                "broken outline")
        self.assertDefect(r, "outline_chain")

    def test_outline_chain_that_loops_is_caught_instead_of_hanging(self):
        # point every /Next at the first outline item -> an infinite chain
        m = re.search(rb"/Outlines (\d+) 0 R", self.pdf)
        outlines = int(m.group(1))
        first = int(re.search(rb"%d 0 obj\n<< /Type /Outlines /First (\d+) 0 R"
                              % outlines, self.pdf).group(1))
        pad = b"/Next %s 0 R" % str(first).encode()
        broken = re.sub(rb"/Next (\d+) 0 R",
                        lambda mm: pad + b" " * (len(mm.group(0)) - len(pad)),
                        self.pdf)
        r = packcheck.check_pdf(broken, "looping outline")
        self.assertDefect(r, "outline_chain")
        self.assertIn("loops", dict(r.defects)["outline_chain"])

    def test_missing_startxref_is_caught(self):
        broken = re.sub(rb"startxref\n(\d+)\n%%EOF\n", b"%%EOF\n", self.pdf)
        r = packcheck.check_pdf(broken, "no startxref")
        self.assertDefect(r, "startxref")

    def test_startxref_pointing_at_nothing_is_caught(self):
        m = re.search(rb"startxref\n(\d+)\n%%EOF", self.pdf)
        broken = self.pdf[:m.start(1)] + b"%d" % (len(self.pdf) - 3) + self.pdf[m.end(1):]
        r = packcheck.check_pdf(broken, "bad startxref")
        self.assertDefect(r, "startxref")

    def test_trailer_size_smaller_than_the_real_object_count_is_caught(self):
        m = re.search(rb"/Size (\d+) /Root", self.pdf)
        broken = self.pdf[:m.start(1)] + b"%02d" % 10 + self.pdf[m.end(1):]
        r = packcheck.check_pdf(broken, "bad /Size")
        self.assertDefect(r, "trailer_size")

    def test_a_file_with_no_objects_at_all_does_not_crash_the_validator(self):
        r = packcheck.check_pdf(b"%PDF-1.4\nnothing here\n%%EOF", "empty")
        self.assertDefect(r, "objects_present")

    def test_empty_bytes_do_not_crash_the_validator(self):
        r = packcheck.check_pdf(b"", "empty bytes")
        self.assertDefect(r, "header")


# --------------------------------------------------------------------------

class CorruptedDocxTests(RenderedCase):

    def rebuild(self, drop=(), replace=None):
        """Rewrite the .docx omitting/patching parts, and return the new path."""
        out = os.path.join(self.tmp, "broken.docx")
        replace = replace or {}
        with zipfile.ZipFile(self.docx) as src:
            items = [(i, src.read(i.filename)) for i in src.infolist()]
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
            for info, blob in items:
                if info.filename in drop:
                    continue
                dst.writestr(info.filename, replace.get(info.filename, blob))
        return out

    def test_missing_required_part_is_caught(self):
        r = packcheck.check_docx(self.rebuild(drop=("word/styles.xml",)))
        self.assertDefect(r, "required_parts")

    def test_relationship_pointing_at_a_missing_part_is_caught(self):
        # styles.xml is dropped AND the relationship to it is left behind
        r = packcheck.check_docx(self.rebuild(drop=("word/styles.xml",)))
        self.assertDefect(r, "relationships_resolve")

    def test_malformed_xml_part_is_caught(self):
        r = packcheck.check_docx(self.rebuild(
            replace={"word/document.xml": b"<w:document><w:body></w:document>"}))
        self.assertDefect(r, "xml_well_formed")

    def test_hyperlink_with_no_matching_bookmark_is_caught(self):
        with zipfile.ZipFile(self.docx) as z:
            doc = z.read("word/document.xml").decode("utf-8")
        doc = doc.replace('w:anchor="S_SCOPE"', 'w:anchor="S_NOWHERE"', 1)
        r = packcheck.check_docx(self.rebuild(
            replace={"word/document.xml": doc.encode("utf-8")}))
        self.assertDefect(r, "internal_anchors_resolve")
        self.assertIn("S_NOWHERE", dict(r.defects)["internal_anchors_resolve"])

    def test_unbalanced_bookmarks_are_caught(self):
        with zipfile.ZipFile(self.docx) as z:
            doc = z.read("word/document.xml").decode("utf-8")
        doc = re.sub(r"<w:bookmarkEnd w:id=\"\d+\"/>", "", doc, count=1)
        r = packcheck.check_docx(self.rebuild(
            replace={"word/document.xml": doc.encode("utf-8")}))
        self.assertDefect(r, "bookmarks_balanced")

    def test_a_file_that_is_not_a_zip_at_all_is_caught_not_crashed_on(self):
        path = os.path.join(self.tmp, "notazip.docx")
        with open(path, "wb") as fh:
            fh.write(b"this is plainly not an OOXML package")
        r = packcheck.check_docx(path)
        self.assertDefect(r, "zip_container")

    def test_a_missing_file_is_reported_not_raised(self):
        r = packcheck.check_docx(os.path.join(self.tmp, "absent.docx"))
        self.assertDefect(r, "zip_container")


# --------------------------------------------------------------------------

class CliTests(RenderedCase):

    def test_cli_exits_zero_on_the_clean_pack_and_nonzero_on_a_broken_one(self):
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = packcheck.main([os.path.join(self.tmp, "proposal.pdf"), self.docx])
        self.assertEqual(rc, 0)
        text = buf.getvalue()
        self.assertIn("0 defect(s)", text)
        # the disclaimer is not decoration; a clean run must carry it
        self.assertIn("not a validity, PDF/UA, WCAG or any other conformance claim", text)

        broken = os.path.join(self.tmp, "broken_for_cli.pdf")
        with open(broken, "wb") as fh:
            fh.write(self.pdf[:-60])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = packcheck.main([broken])
        self.assertEqual(rc, 1)
        self.assertIn("eof_marker", buf.getvalue())

    def test_cli_with_no_arguments_is_a_usage_error_not_a_pass(self):
        import contextlib
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(packcheck.main([]), 2)
        self.assertIn("usage:", err.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
