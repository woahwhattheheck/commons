"""Tests for the UIOWA-136 bid-pack assembler.

The tests OPEN THE ARTIFACTS. A page number is only accepted here if it was
re-read out of the rendered PDF; an attachment is only accepted as supplied if
its bytes are on disk in the output folder. The builder's own report of what it
did is never the evidence.

Hostile / missing-data cases live in HostileInputTests.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest

import bid_pack
import docxwrite
import pdfwrite

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")
MANIFEST = os.path.join(FIXTURES, "manifest.json")


def build(tmp, manifest=None, root=None):
    m = manifest if manifest is not None else bid_pack.load_manifest(MANIFEST)
    pack = bid_pack.BidPack(m, root or FIXTURES)
    return pack, pack.assemble(tmp)


def pdf_pages(tmp):
    """Reopen the rendered PDF and return its pages as text."""
    with open(os.path.join(tmp, "proposal.pdf"), "rb") as fh:
        return pdfwrite.read_pdf_pages(fh.read())


def flat(pages):
    """All page text with whitespace collapsed.

    Needed because a rendered document WRAPS: "[UNRESOLVED REFERENCE:
    S-APPENDIX-C]" is one phrase to a reader and two lines to the file. Searching
    the unflattened text for the phrase is a test bug, not a product bug.
    """
    return " ".join(" ".join(pages).split())


def read_text(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as fh:
        return fh.read()


def codes(result, severity=None):
    return [i["code"] for i in result["issues"]
            if severity is None or i["severity"] == severity]


class TempCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bidpack-")
        self.addCleanup(shutil.rmtree, self.tmp, True)


# --------------------------------------------------------------------------

class ManifestValidationTests(TempCase):

    def test_missing_required_top_level_key_is_refused(self):
        m = bid_pack.load_manifest(MANIFEST)
        del m["attachments"]
        with self.assertRaises(bid_pack.ManifestError) as cm:
            bid_pack.validate_manifest(m)
        self.assertIn("attachments", str(cm.exception))

    def test_manifest_with_no_sections_is_refused(self):
        m = bid_pack.load_manifest(MANIFEST)
        m["sections"] = []
        with self.assertRaises(bid_pack.ManifestError):
            bid_pack.validate_manifest(m)

    def test_duplicate_attachment_id_is_refused(self):
        m = bid_pack.load_manifest(MANIFEST)
        m["attachments"].append(dict(m["attachments"][0]))
        with self.assertRaises(bid_pack.ManifestError) as cm:
            bid_pack.validate_manifest(m)
        self.assertIn("duplicate id", str(cm.exception))

    def test_attachment_missing_title_is_refused_not_defaulted(self):
        m = bid_pack.load_manifest(MANIFEST)
        m["attachments"][0].pop("title")
        with self.assertRaises(bid_pack.ManifestError) as cm:
            bid_pack.validate_manifest(m)
        self.assertIn("title", str(cm.exception))

    def test_unknown_schema_is_refused(self):
        m = bid_pack.load_manifest(MANIFEST)
        m["schema"] = "some-other-thing/9"
        with self.assertRaises(bid_pack.ManifestError):
            bid_pack.validate_manifest(m)

    def test_missing_manifest_file_is_a_manifest_error_not_a_traceback(self):
        with self.assertRaises(bid_pack.ManifestError):
            bid_pack.load_manifest(os.path.join(self.tmp, "nope.json"))


# --------------------------------------------------------------------------

class AssemblyTests(TempCase):

    def setUp(self):
        super().setUp()
        self.pack, self.result = build(self.tmp)

    def test_every_declared_document_and_attachment_appears_in_the_index(self):
        m = bid_pack.load_manifest(MANIFEST)
        self.assertEqual(len(self.result["sections"]), len(m["sections"]))
        self.assertEqual(len(self.result["attachments"]), len(m["attachments"]))
        idx = read_text(self.tmp, "00-INDEX.md")
        for a in m["attachments"]:
            self.assertIn(a["id"], idx, "%s vanished from the index" % a["id"])

    def test_filenames_are_stable_across_two_runs(self):
        second = tempfile.mkdtemp(prefix="bidpack2-")
        self.addCleanup(shutil.rmtree, second, True)
        _, again = build(second)
        self.assertEqual([s["filename"] for s in self.result["sections"]],
                         [s["filename"] for s in again["sections"]])
        self.assertEqual([a["filename"] for a in self.result["attachments"]],
                         [a["filename"] for a in again["attachments"]])

    def test_supplied_attachment_bytes_are_actually_on_disk_and_match_the_digest(self):
        import hashlib
        for a in self.result["attachments"]:
            if not a["present"]:
                continue
            path = os.path.join(self.tmp, "attachments", a["filename"])
            self.assertTrue(os.path.isfile(path), "index names a file that is not there")
            with open(path, "rb") as fh:
                blob = fh.read()
            self.assertEqual(len(blob), a["bytes"])
            self.assertEqual(hashlib.sha256(blob).hexdigest(), a["sha256"])

    def test_index_page_numbers_are_confirmed_by_reopening_the_pdf(self):
        pages = pdf_pages(self.tmp)
        for s in self.result["sections"]:
            self.assertIsNotNone(s["page"])
            self.assertIn(s["title"], pages[s["page"] - 1],
                          "index claims %s on page %s but the page does not contain it"
                          % (s["title"], s["page"]))
        for a in self.result["attachments"]:
            self.assertIsNotNone(a["index_page"])
            self.assertIn(a["id"], pages[a["index_page"] - 1])

    def test_pdf_outline_and_links_exist_and_point_somewhere_real(self):
        with open(os.path.join(self.tmp, "proposal.pdf"), "rb") as fh:
            data = fh.read()
        outline = pdfwrite.read_pdf_outline(data)
        titles = [t for t, _ in outline]
        self.assertIn("Document Map", titles)
        self.assertIn("Attachment Index", titles)
        for s in self.result["sections"]:
            self.assertTrue(any(s["title"] in t for t in titles),
                            "%s has no bookmark" % s["title"])
        links = pdfwrite.read_pdf_links(data)
        self.assertTrue(links, "no internal links were written")
        self.assertFalse([l for l in links if l[1] < 0],
                         "a link annotation points outside the document")

    def test_docx_bookmarks_cover_every_internal_link(self):
        path = os.path.join(self.tmp, "proposal.docx")
        marks, links = docxwrite.read_docx_nav(path)
        self.assertTrue(links)
        self.assertFalse([l for l in links if l not in marks],
                         "a .docx hyperlink has no matching bookmark")
        text = "\n".join(docxwrite.read_docx_text(path))
        for a in self.result["attachments"]:
            self.assertIn(a["id"], text)

    def test_monospace_index_columns_survive_into_the_rendered_pdf(self):
        # The regression this guards: the word wrapper used to collapse runs of
        # spaces, so the index columns were aligned in the source string and
        # ragged in the actual document.
        pages = pdf_pages(self.tmp)
        index_page = self.result["attachments"][0]["index_page"] - 1
        rows = [ln for ln in pages[index_page].split("\n")
                if ln.startswith("ATT-") and "   " in ln]
        self.assertEqual(len(rows), len(self.result["attachments"]))
        starts = {r.index("SUPPLIED") if r.lstrip().split()[1] == "SUPPLIED"
                  else r.index("PLACEHOLDER") for r in rows}
        self.assertEqual(len(starts), 1, "status column is not aligned: %r" % rows)

    def test_fiction_notice_reaches_the_rendered_documents(self):
        pages = pdf_pages(self.tmp)
        self.assertIn("FICTION", pages[0])
        self.assertIn("FICTION", read_text(self.tmp, "00-INDEX.md"))

    def test_csv_and_json_agree_with_each_other(self):
        import csv as _csv
        with open(os.path.join(self.tmp, "attachment_index.csv"), encoding="utf-8") as fh:
            rows = {r["attachment_id"]: r for r in _csv.DictReader(fh)}
        data = json.load(open(os.path.join(self.tmp, "bid_pack.json"), encoding="utf-8"))
        self.assertIn("content_digest", data)
        for a in data["attachments"]:
            row = rows[a["id"]]
            self.assertEqual(row["status"], a["status"])
            if a["bytes"] is None:
                self.assertEqual(row["bytes"], "UNKNOWN")
                self.assertEqual(row["sha256"], "UNKNOWN")
            else:
                self.assertEqual(int(row["bytes"]), a["bytes"])

    def test_no_readiness_score_or_percentage_is_emitted_anywhere(self):
        # This order is under the same rule as the rest of the board: absence is
        # never converted into a number. Guard it mechanically.
        blob = json.dumps(self.result).lower()
        for banned in ("maturity", "score", "percent", "readiness_pct", "grade", "rating"):
            self.assertNotIn(banned, blob, "output contains %r" % banned)
        for f in ("00-INDEX.md", "attachment_index.csv"):
            text = read_text(self.tmp, f).lower()
            self.assertNotIn("maturity", text)
            self.assertNotIn("% complete", text)


# --------------------------------------------------------------------------

class GapReportingTests(TempCase):
    """The fixture's deliberate gap must survive all the way to the artifacts."""

    def setUp(self):
        super().setUp()
        self.pack, self.result = build(self.tmp)

    def test_absent_required_attachments_are_rows_not_omissions(self):
        missing = [a for a in self.result["attachments"] if not a["present"]]
        self.assertEqual(sorted(a["id"] for a in missing),
                         ["ATT-FIN-02", "ATT-QUAL-02", "ATT-QUAL-03"])
        for a in missing:
            self.assertIn("NOT SUPPLIED", a["status"])
            self.assertIsNone(a["bytes"])
            self.assertIsNone(a["sha256"])
            self.assertIsNone(a["filename"])

    def test_absent_attachment_never_becomes_a_zero(self):
        import csv as _csv
        with open(os.path.join(self.tmp, "attachment_index.csv"), encoding="utf-8") as fh:
            for row in _csv.DictReader(fh):
                if "NOT SUPPLIED" in row["status"]:
                    self.assertEqual(row["bytes"], "UNKNOWN")
                    self.assertNotEqual(row["bytes"], "0")

    def test_placeholder_file_exists_and_disowns_itself(self):
        names = os.listdir(os.path.join(self.tmp, "attachments"))
        ph = [n for n in names if "PLACEHOLDER" in n]
        self.assertEqual(len(ph), 3)
        body = read_text(self.tmp, "attachments", ph[0])
        self.assertIn("NOT SUPPLIED", body)
        self.assertIn("must not be submitted in its place", body)

    def test_readiness_refuses_to_say_ready_while_required_documents_are_absent(self):
        r = self.result["readiness"]
        self.assertEqual(r["status"], "SUBMISSION_INCOMPLETE")
        self.assertEqual(r["required_declared"], 5)
        self.assertEqual(r["required_present"], 2)
        self.assertEqual(sorted(r["required_not_supplied"]),
                         ["ATT-FIN-02", "ATT-QUAL-02", "ATT-QUAL-03"])
        self.assertIn("UNKNOWN", r["note"])

    def test_dangling_cross_reference_is_reported_and_left_visible(self):
        unresolved = [x for x in self.result["cross_references"] if x["status"] == "UNRESOLVED"]
        self.assertEqual([x["to"] for x in unresolved], ["S-APPENDIX-C"])
        self.assertIn("XREF_UNRESOLVED", codes(self.result))
        whole = flat(pdf_pages(self.tmp))
        self.assertIn("[UNRESOLVED REFERENCE: S-APPENDIX-C]", whole,
                      "the dangling reference was silently deleted from the document")

    def test_reference_to_an_absent_attachment_still_resolves_and_says_not_supplied(self):
        whole = flat(pdf_pages(self.tmp))
        self.assertIn("ATT-FIN-02", whole)
        self.assertIn("PLACEHOLDER, NOT SUPPLIED", whole)

    def test_the_fixture_demonstrates_a_strength_as_well_as_a_gap(self):
        xrefs = self.result["cross_references"]
        resolved = [x for x in xrefs if x["status"] == "RESOLVED"]
        self.assertGreaterEqual(len(resolved), 9)
        self.assertEqual(len(xrefs) - len(resolved), 1)
        self.assertEqual(self.result["render"]["pagination_passes"] <= 4, True)


# --------------------------------------------------------------------------

class HostileInputTests(TempCase):
    """Missing, contradictory and malicious inputs."""

    def test_manifest_claiming_a_file_that_is_not_there_loses_to_the_filesystem(self):
        m = bid_pack.load_manifest(MANIFEST)
        for a in m["attachments"]:
            if a["id"] == "ATT-QUAL-02":
                a["provided"] = True          # the manifest asserts it is supplied
        _, result = build(self.tmp, manifest=m)
        att = [a for a in result["attachments"] if a["id"] == "ATT-QUAL-02"][0]
        self.assertFalse(att["present"])
        self.assertIn("NOT SUPPLIED", att["status"])
        self.assertIn("ATTACHMENT_DECLARED_PROVIDED_BUT_ABSENT", codes(result, bid_pack.ERROR))

    def test_strict_mode_exits_nonzero_on_that_contradiction(self):
        m = bid_pack.load_manifest(MANIFEST)
        for a in m["attachments"]:
            if a["id"] == "ATT-QUAL-02":
                a["provided"] = True
        mpath = os.path.join(FIXTURES, "_tmp_contradiction.json")
        with open(mpath, "w", encoding="utf-8") as fh:
            json.dump(m, fh)
        self.addCleanup(os.remove, mpath)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = bid_pack.main(["--manifest", mpath, "--out", self.tmp, "--strict"])
        self.assertEqual(rc, 1)
        # the CLI must have said WHY it refused, not just returned 1
        self.assertIn("ATTACHMENT_DECLARED_PROVIDED_BUT_ABSENT", buf.getvalue())
        self.assertIn("SUBMISSION_INCOMPLETE", buf.getvalue())

    def test_zero_byte_attachment_is_not_counted_as_evidence(self):
        empty = os.path.join(FIXTURES, "attachments", "_tmp_empty.txt")
        open(empty, "w").close()
        self.addCleanup(os.remove, empty)
        m = bid_pack.load_manifest(MANIFEST)
        for a in m["attachments"]:
            if a["id"] == "ATT-QUAL-02":
                a["source"] = "attachments/_tmp_empty.txt"
        _, result = build(self.tmp, manifest=m)
        att = [a for a in result["attachments"] if a["id"] == "ATT-QUAL-02"][0]
        self.assertEqual(att["bytes"], 0)
        self.assertIn("EMPTY FILE", att["status"])
        self.assertIn("ATTACHMENT_EMPTY_FILE", codes(result))
        # an empty file does not close the gap
        self.assertIn("ATT-QUAL-02", result["readiness"]["required_not_supplied"])

    def test_case_insensitive_filename_collision_is_disambiguated_not_overwritten(self):
        m = bid_pack.load_manifest(MANIFEST)
        m["attachments"][0]["filename"] = "Shared.TXT"
        m["attachments"][2]["filename"] = "shared.txt"
        with self.assertRaises(bid_pack.ManifestError) as cm:
            bid_pack.BidPack(m, FIXTURES).assemble(self.tmp)
        self.assertIn("overwrite", str(cm.exception))

    def test_auto_generated_collision_is_disambiguated_and_disclosed(self):
        m = bid_pack.load_manifest(MANIFEST)
        m["attachments"][0]["filename"] = "A03-vendor-registration-and-taxpayer-identification.txt"
        _, result = build(self.tmp, manifest=m)
        names = [a["filename"] for a in result["attachments"] if a["filename"]]
        self.assertEqual(len(names), len(set(n.lower() for n in names)))
        self.assertIn("FILENAME_COLLISION_RESOLVED", codes(result))

    def test_path_escaping_the_pack_root_is_refused(self):
        m = bid_pack.load_manifest(MANIFEST)
        m["attachments"][0]["source"] = "../../../etc/passwd"
        with self.assertRaises(bid_pack.ManifestError) as cm:
            bid_pack.BidPack(m, FIXTURES).assemble(self.tmp)
        self.assertIn("escapes the pack root", str(cm.exception))

    def test_absolute_source_path_is_refused(self):
        m = bid_pack.load_manifest(MANIFEST)
        m["attachments"][0]["source"] = "/etc/hosts"
        with self.assertRaises(bid_pack.ManifestError):
            bid_pack.BidPack(m, FIXTURES).assemble(self.tmp)

    def test_missing_section_body_produces_a_visible_placeholder_page(self):
        m = bid_pack.load_manifest(MANIFEST)
        m["sections"][2]["source"] = "sections/does_not_exist.md"
        _, result = build(self.tmp, manifest=m)
        sec = [s for s in result["sections"] if s["id"] == "S-QUAL"][0]
        self.assertEqual(sec["content_status"], "NOT_SUPPLIED")
        self.assertIn("SECTION_CONTENT_NOT_SUPPLIED", codes(result))
        pages = pdf_pages(self.tmp)
        self.assertIn("SECTION CONTENT NOT SUPPLIED", flat(pages))
        # ...and the section keeps its slot rather than silently vanishing
        self.assertEqual(len(result["sections"]), len(m["sections"]))

    def test_character_outside_winansi_is_reported_not_silently_mangled(self):
        src = os.path.join(FIXTURES, "sections", "_tmp_unicode.md")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write("Fee basis uses an en dash – which WinAnsi has, and a CJK "
                     "character 中 which it does not.\n")
        self.addCleanup(os.remove, src)
        m = bid_pack.load_manifest(MANIFEST)
        m["sections"][0]["source"] = "sections/_tmp_unicode.md"
        _, result = build(self.tmp, manifest=m)
        self.assertIn("UNICODE_NOT_REPRESENTABLE_IN_PDF", codes(result))
        detail = [i["detail"] for i in result["issues"]
                  if i["code"] == "UNICODE_NOT_REPRESENTABLE_IN_PDF"][0]
        self.assertIn("中", detail)
        self.assertNotIn("–", detail)       # the en dash DID survive
        # the markdown output keeps the original character even though the PDF cannot
        doc = read_text(self.tmp, "documents", "01-cover-letter.md")
        self.assertIn("中", doc)
        self.assertIn("中", "".join(docxwrite.read_docx_text(
            os.path.join(self.tmp, "proposal.docx"))))

    def test_attachment_with_no_source_at_all_is_a_placeholder_not_a_crash(self):
        m = bid_pack.load_manifest(MANIFEST)
        m["attachments"][1].pop("source")
        _, result = build(self.tmp, manifest=m)
        att = result["attachments"][1]
        self.assertFalse(att["present"])
        self.assertIn("NOT SUPPLIED", att["status"])

    def test_pack_with_no_attachments_at_all_still_renders_and_says_so(self):
        m = bid_pack.load_manifest(MANIFEST)
        m["attachments"] = []
        _, result = build(self.tmp, manifest=m)
        self.assertEqual(result["readiness"]["required_declared"], 0)
        # zero DECLARED is an observed fact; it is not a pass, and the note says
        # the University's actual required list is UNKNOWN
        self.assertIn("UNKNOWN", result["readiness"]["note"])
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "proposal.pdf")))

    def test_pagination_that_will_not_settle_is_refused_rather_than_guessed(self):
        real = bid_pack.pdfwrite.anchor_pages
        state = {"n": 0}

        def unstable(pages):
            state["n"] += 1
            out = real(pages)
            # move one anchor every pass so the map never converges
            return {k: (v[0] + state["n"], v[1]) for k, v in out.items()}

        bid_pack.pdfwrite.anchor_pages = unstable
        self.addCleanup(setattr, bid_pack.pdfwrite, "anchor_pages", real)
        with self.assertRaises(bid_pack.PaginationError):
            build(self.tmp)


if __name__ == "__main__":
    unittest.main(verbosity=2)
