#!/usr/bin/env python3
"""Tests for the UIOWA-123 print renderer and page inspector.

The central assertions are the NEGATIVE CONTROL ones: the naive renderer must
actually produce each defect and the fixed renderer must produce none. An
inspector that has never gone red proves nothing, so "the checker finds the
planted defect" is tested before "the checker finds nothing in good output".
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import printreport as pr  # noqa: E402

FIXTURES = os.path.join(HERE, "fixtures")
MAIN_DOC = os.path.join(FIXTURES, "report_document.json")
ORPHAN_DOC = os.path.join(FIXTURES, "boundary_orphan_heading.json")
CITATION_DOC = os.path.join(FIXTURES, "boundary_citation_split.json")
ALL_DOCS = (MAIN_DOC, ORPHAN_DOC, CITATION_DOC)


def defect_names(defects):
    return sorted({d["defect"] for d in defects})


def run_doc(path, mode):
    doc = pr.load_document(path)
    return pr.render(doc, mode)


class TestMetrics(unittest.TestCase):
    def test_courier_advance_is_exact(self):
        """Courier advances 600/1000 em. The whole renderer rests on this."""
        self.assertAlmostEqual(pr.char_width(10.0), 6.0)
        self.assertAlmostEqual(pr.text_width("abcde", 10.0), 30.0)

    def test_max_chars_is_a_floor_not_a_guess(self):
        self.assertEqual(pr.max_chars(60.0, 10.0), 10)
        self.assertEqual(pr.max_chars(59.0, 10.0), 9)
        self.assertEqual(pr.max_chars(0.0, 10.0), 0)

    def test_wrapped_lines_fit_the_column(self):
        text = " ".join("word%d" % i for i in range(60))
        width = 200.0
        for line in pr.wrap(text, width, 9.0):
            self.assertLessEqual(pr.text_width(line, 9.0), width + 0.01)

    def test_wrap_never_drops_characters(self):
        for text in ("short",
                     " ".join("w%d" % i for i in range(200)),
                     "a" * 500,
                     "supercalifragilistic" * 12 + " tail",
                     "   leading and trailing   "):
            out = "".join(pr.wrap(text, 120.0, 9.0))
            self.assertEqual("".join(out.split()), "".join(text.split()),
                             "wrap lost or invented characters")

    def test_unbreakable_token_is_split_not_overflowed(self):
        """A token wider than the column must be hard-split. Letting it run
        past the margin is a clipped-text defect; dropping it is worse."""
        token = "X" * 400
        lines = pr.wrap(token, 100.0, 9.0)
        self.assertGreater(len(lines), 1)
        for line in lines:
            self.assertLessEqual(pr.text_width(line, 9.0), 100.01)
        self.assertEqual("".join(lines), token)

    def test_empty_text_yields_one_empty_line(self):
        self.assertEqual(pr.wrap("", 100.0, 9.0), [""])
        self.assertEqual(pr.wrap("   ", 100.0, 9.0), [""])


class TestNegativeControl(unittest.TestCase):
    """The naive renderer must really produce the defects it claims to."""

    def test_naive_main_report_clips_text(self):
        _, defects, _ = run_doc(MAIN_DOC, "naive")
        self.assertIn("CLIPPED_TEXT", defect_names(defects))
        clipped = [d for d in defects if d["defect"] == "CLIPPED_TEXT"]
        self.assertGreater(len(clipped), 10)

    def test_naive_main_report_separates_a_table_header(self):
        _, defects, _ = run_doc(MAIN_DOC, "naive")
        self.assertIn("TABLE_HEADER_SEPARATED", defect_names(defects))

    def test_naive_orphans_a_heading(self):
        _, defects, _ = run_doc(ORPHAN_DOC, "naive")
        self.assertEqual(defect_names(defects), ["ORPHANED_HEADING"])

    def test_naive_splits_a_citation(self):
        _, defects, _ = run_doc(CITATION_DOC, "naive")
        self.assertEqual(defect_names(defects), ["CITATION_SPLIT"])

    def test_all_four_defect_classes_are_demonstrated(self):
        seen = set()
        for path in ALL_DOCS:
            _, defects, _ = run_doc(path, "naive")
            seen.update(d["defect"] for d in defects)
        self.assertEqual(seen, set(pr.DEFECT_MEANINGS),
                         "a defect class the inspector defines is never "
                         "demonstrated by any fixture")

    def test_fixed_renderer_is_clean_on_every_document(self):
        for path in ALL_DOCS:
            _, defects, _ = run_doc(path, "fixed")
            self.assertEqual(defects, [],
                             "fixed renderer produced defects on %s: %s"
                             % (os.path.basename(path), defect_names(defects)))

    def test_inspector_catches_a_planted_defect_in_synthetic_pages(self):
        """Independent of the renderers: hand-place a run below the page floor."""
        run = pr.Run("off the bottom", pr.CONTENT_L,
                     pr.CONTENT_BOTTOM - 30.0, 9.0, False, "b1",
                     "paragraph", "body")
        defects = pr.inspect_pages([[run]])
        self.assertEqual(defect_names(defects), ["CLIPPED_TEXT"])

    def test_inspector_catches_a_run_past_the_right_margin(self):
        run = pr.Run("X" * 400, pr.CONTENT_L, 400.0, 9.0, False, "b1",
                     "paragraph", "body")
        defects = pr.inspect_pages([[run]])
        self.assertEqual(defect_names(defects), ["CLIPPED_TEXT"])

    def test_inspector_is_silent_on_a_clean_page(self):
        run = pr.Run("inside the box", pr.CONTENT_L, 400.0, 9.0, False, "b1",
                     "paragraph", "body")
        self.assertEqual(pr.inspect_pages([[run]]), [])


class TestTextConservation(unittest.TestCase):
    def test_no_text_is_lost_by_either_renderer(self):
        for path in ALL_DOCS:
            for mode in ("naive", "fixed"):
                _, _, audit = run_doc(path, mode)
                self.assertTrue(audit["no_text_lost"],
                                "%s/%s lost characters: %s"
                                % (os.path.basename(path), mode,
                                   audit["missing_char_counts"]))
                self.assertEqual(audit["missing_char_counts"], {})

    def test_fixed_repeats_table_headers_and_naive_does_not(self):
        """The +chars in the fixed render are the repeated header rows. That
        difference IS the table-header fix, so it is asserted directly."""
        _, _, fixed = run_doc(MAIN_DOC, "fixed")
        _, _, naive = run_doc(MAIN_DOC, "naive")
        self.assertGreater(fixed["added_chars"], 0)
        self.assertEqual(naive["added_chars"], 0)

    def test_conservation_detects_a_real_loss(self):
        """The audit must be capable of failing, or it guarantees nothing."""
        doc = pr.load_document(MAIN_DOC)
        pages = pr.render_blocks(doc, "fixed")
        pages[0] = pages[0][:-5]  # drop five placed runs
        audit = pr.audit_text_conservation(doc, pages)
        self.assertFalse(audit["no_text_lost"])
        self.assertNotEqual(audit["missing_char_counts"], {})


class TestEncoding(unittest.TestCase):
    def test_transliterations_are_recorded_not_silent(self):
        doc = pr.load_document(MAIN_DOC)
        tr = doc["_transliterations"]
        self.assertIn("—", tr)
        self.assertGreater(tr["—"], 0)

    def test_no_unencodable_characters_survive_in_the_fixtures(self):
        for path in ALL_DOCS:
            doc = pr.load_document(path)
            pages = pr.render_blocks(doc, "fixed")
            self.assertEqual(pr.unencodable_characters(pages), {},
                             "%s would render '?' in the PDF"
                             % os.path.basename(path))

    def test_unknown_unicode_is_reported_not_invented(self):
        """No ASCII stand-in is guessed for a character we do not understand."""
        doc = pr.normalize_document(
            {"title": "T", "blocks": [{"id": "x", "kind": "paragraph",
                                       "text": "你好 α"}]})
        pages = pr.render_blocks(doc, "fixed")
        bad = pr.unencodable_characters(pages)
        self.assertIn("你", bad)
        self.assertIn("α", bad)

    def test_transliteration_is_applied_before_measurement(self):
        """An em dash becomes two characters. If layout saw the original and
        the audit saw the replacement they would disagree forever."""
        doc = pr.normalize_document(
            {"title": "T", "blocks": [{"id": "x", "kind": "paragraph",
                                       "text": "a — b"}]})
        self.assertEqual(doc["blocks"][0]["text"], "a -- b")
        pages = pr.render_blocks(doc, "fixed")
        self.assertTrue(pr.audit_text_conservation(doc, pages)["no_text_lost"])


class TestPdfOutput(unittest.TestCase):
    def test_pdf_is_structurally_valid_and_has_the_right_page_count(self):
        out = tempfile.mkdtemp(prefix="uiowa123-")
        try:
            doc = pr.load_document(MAIN_DOC)
            pages = pr.render_blocks(doc, "fixed")
            path = os.path.join(out, "r.pdf")
            n = pr.write_pdf(pages, path, "t")
            self.assertEqual(n, len(pages))
            info = pr.verify_pdf(path, n, pages)
            self.assertTrue(info["structurally_valid"], info["problems"])
            self.assertEqual(info["pages"], len(pages))
            self.assertGreater(info["bytes"], 1000)
        finally:
            shutil.rmtree(out, ignore_errors=True)

    def test_verify_pdf_rejects_a_truncated_file(self):
        out = tempfile.mkdtemp(prefix="uiowa123-")
        try:
            doc = pr.load_document(CITATION_DOC)
            pages = pr.render_blocks(doc, "fixed")
            path = os.path.join(out, "r.pdf")
            n = pr.write_pdf(pages, path, "t")
            with open(path, "rb") as fh:
                blob = fh.read()
            with open(path, "wb") as fh:
                fh.write(blob[:len(blob) // 2])
            info = pr.verify_pdf(path, n, pages)
            self.assertFalse(info["structurally_valid"])
        finally:
            shutil.rmtree(out, ignore_errors=True)

    def test_pdf_bytes_are_deterministic(self):
        out = tempfile.mkdtemp(prefix="uiowa123-")
        try:
            blobs = []
            for i in range(2):
                doc = pr.load_document(MAIN_DOC)
                pages = pr.render_blocks(doc, "fixed")
                path = os.path.join(out, "r%d.pdf" % i)
                pr.write_pdf(pages, path, "t")
                with open(path, "rb") as fh:
                    blobs.append(fh.read())
            self.assertEqual(blobs[0], blobs[1])
        finally:
            shutil.rmtree(out, ignore_errors=True)

    def test_parentheses_and_backslashes_are_escaped(self):
        """Unescaped '(' ends a PDF string early and corrupts the page."""
        doc = pr.normalize_document(
            {"title": "T", "blocks": [{"id": "x", "kind": "paragraph",
                                       "text": "a (b) c \\ d"}]})
        out = tempfile.mkdtemp(prefix="uiowa123-")
        try:
            pages = pr.render_blocks(doc, "fixed")
            path = os.path.join(out, "r.pdf")
            n = pr.write_pdf(pages, path, "t")
            self.assertTrue(pr.verify_pdf(path, n, pages)["structurally_valid"])
        finally:
            shutil.rmtree(out, ignore_errors=True)


class TestHostileAndMissingInput(unittest.TestCase):
    def _doc(self, blob):
        path = tempfile.mktemp(suffix=".json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(blob, fh)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        return path

    def test_missing_file_names_the_file(self):
        with self.assertRaises(pr.DocumentError) as ctx:
            pr.load_document("/nonexistent/nope.json")
        self.assertIn("nope.json", str(ctx.exception))

    def test_malformed_json_names_the_file(self):
        path = tempfile.mktemp(suffix=".json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("{ not json ,,,")
        self.addCleanup(lambda: os.remove(path))
        with self.assertRaises(pr.DocumentError) as ctx:
            pr.load_document(path)
        self.assertIn(os.path.basename(path), str(ctx.exception))

    def test_unknown_block_kind_is_rejected(self):
        path = self._doc({"title": "T", "blocks": [
            {"id": "a", "kind": "sidebar", "text": "x"}]})
        with self.assertRaises(pr.DocumentError) as ctx:
            pr.load_document(path)
        self.assertIn("sidebar", str(ctx.exception))

    def test_duplicate_block_ids_are_rejected(self):
        """Duplicate ids would silently merge two blocks in the inspector's
        page map, hiding a real defect."""
        path = self._doc({"title": "T", "blocks": [
            {"id": "a", "kind": "paragraph", "text": "x"},
            {"id": "a", "kind": "paragraph", "text": "y"}]})
        with self.assertRaises(pr.DocumentError) as ctx:
            pr.load_document(path)
        self.assertIn("duplicate", str(ctx.exception).lower())

    def test_table_row_width_mismatch_is_rejected(self):
        path = self._doc({"title": "T", "blocks": [
            {"id": "t", "kind": "table", "headers": ["a", "b", "c"],
             "rows": [["1", "2"]]}]})
        with self.assertRaises(pr.DocumentError) as ctx:
            pr.load_document(path)
        self.assertIn("2 cells", str(ctx.exception))

    def test_empty_table_is_rejected(self):
        path = self._doc({"title": "T", "blocks": [
            {"id": "t", "kind": "table", "headers": ["a"], "rows": []}]})
        with self.assertRaises(pr.DocumentError):
            pr.load_document(path)

    def test_every_problem_is_reported_at_once(self):
        path = self._doc({"title": "T", "blocks": [
            {"id": "a", "kind": "wishful", "text": "x"},
            {"id": "b", "kind": "heading", "level": 9, "text": "h"},
            {"id": "c", "kind": "paragraph"}]})
        with self.assertRaises(pr.DocumentError) as ctx:
            pr.load_document(path)
        msg = str(ctx.exception)
        self.assertIn("wishful", msg)
        self.assertIn("level", msg)
        self.assertIn("no text", msg)

    def test_document_with_no_blocks_renders_without_crashing(self):
        doc = pr.normalize_document({"title": "Empty (FICTIONAL)", "blocks": []})
        pages, defects, audit = pr.render(doc, "fixed")
        self.assertEqual(len(pages), 1)
        self.assertEqual(defects, [])
        self.assertTrue(audit["no_text_lost"])

    def test_row_taller_than_a_page_splits_instead_of_overflowing(self):
        """Hostile content: a single table row with more text than a page holds.

        This test found a real bug. A row that does not fit on ANY page has
        nowhere to be moved to, and the renderer used to emit it in full and
        let it run off the bottom. It must split across pages, keep every line
        inside the content box, and re-emit the header on each continuation so
        the columns stay labelled.
        """
        doc = pr.normalize_document({"title": "T", "blocks": [
            {"id": "t", "kind": "table", "headers": ["h1", "h2"],
             "rows": [["ok", "Z" * 12000]]}]})
        pages, defects, audit = pr.render(doc, "fixed")
        self.assertGreater(len(pages), 1)
        self.assertEqual(defects, [], defect_names(defects))
        self.assertTrue(audit["no_text_lost"])

    def test_the_same_over_tall_row_still_breaks_the_naive_renderer(self):
        """Negative control for the fix above."""
        doc = pr.normalize_document({"title": "T", "blocks": [
            {"id": "t", "kind": "table", "headers": ["h1", "h2"],
             "rows": [["ok", "Z" * 12000]]}]})
        _, defects, audit = pr.render(doc, "naive")
        self.assertIn("CLIPPED_TEXT", defect_names(defects))
        self.assertTrue(audit["no_text_lost"])


class TestCli(unittest.TestCase):
    def test_cli_runs_all_fixtures_and_exits_zero(self):
        out = tempfile.mkdtemp(prefix="uiowa123-cli-")
        try:
            self.assertEqual(pr.main(["--out", out]), 0)
            for name in ("report_document_fixed.pdf",
                         "report_document_naive.pdf",
                         "inspection_report_document_fixed.md",
                         "inspection_report_document_fixed.json"):
                path = os.path.join(out, name)
                self.assertTrue(os.path.exists(path), "%s missing" % name)
                self.assertGreater(os.path.getsize(path), 0)
        finally:
            shutil.rmtree(out, ignore_errors=True)

    def test_cli_exits_two_on_a_bad_document(self):
        path = tempfile.mktemp(suffix=".json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("nope")
        self.addCleanup(lambda: os.remove(path))
        out = tempfile.mkdtemp(prefix="uiowa123-cli-")
        try:
            self.assertEqual(pr.main(["--document", path, "--out", out]), 2)
        finally:
            shutil.rmtree(out, ignore_errors=True)

    def test_reports_state_the_visual_check_is_outstanding(self):
        """The one claim this lane must never make is that a human looked."""
        out = tempfile.mkdtemp(prefix="uiowa123-cli-")
        try:
            pr.main(["--out", out])
            with open(os.path.join(out, "inspection_report_document_fixed.md"),
                      encoding="utf-8") as fh:
                md = fh.read()
            self.assertIn("No human has visually inspected", md)
            with open(os.path.join(out, "inspection_report_document_fixed.json"),
                      encoding="utf-8") as fh:
                blob = json.load(fh)
            self.assertEqual(blob["visual_check_by_human"],
                             "OUTSTANDING - not performed")
            self.assertIn("FICTIONAL", blob["fiction_notice"])
        finally:
            shutil.rmtree(out, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
