"""Tests for the OPS-BIDPACK-INTEGRATION adapter.

The adapter reads another lane's landed artifacts. These tests therefore run
twice over: against a self-contained synthetic structure (so the suite passes
anywhere, including a checkout without the sibling lane) and, when the real
sibling lane is present, against the actual delivered files.

The load-bearing guarantee is VERBATIM PRESERVATION: this adapter must not
rewrite another lane's prose. `test_section_bodies_are_byte_identical_to_source`
asserts it on real bytes.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
import unittest

import bid_pack
import from_report_structure as adapter
import packcheck

HERE = os.path.dirname(os.path.abspath(__file__))
REAL_STRUCTURE = os.path.abspath(os.path.join(HERE, "..", "uiowa_rfq_18649_report_structure"))
HAVE_REAL = os.path.isfile(os.path.join(REAL_STRUCTURE, "content_map.json"))

SYNTH_MAP = {
    "map_id": "synthetic-structure/1",
    "status": "SYNTHETIC FIXTURE - FICTION",
    "sections": [
        {"section_id": "SEC-01", "title": "Executive Summary"},
        {"section_id": "SEC-02", "title": "Methodology"},
        {"section_id": "SEC-03", "title": "Appendix A - Supporting Evidence"},
        {"section_id": "SEC-04", "title": "Never Written Section"},
    ],
}

SYNTH_REPORT = """# Synthetic Report (SYNTHETIC SAMPLE)

> **SYNTHETIC EXAMPLE - FICTION.** Nothing here describes any real institution.

Preamble text that belongs to no heading.

## 1. Executive Summary

Body of the summary.   Two spaces preserved.

## 2. Methodology

Method body.

## A. Appendix A - Supporting Evidence

Appendix body.

## Scope boundary

A heading the structure map does not declare.
"""


def write_synth(root, report=SYNTH_REPORT, content_map=None):
    os.makedirs(os.path.join(root, "examples"), exist_ok=True)
    with open(os.path.join(root, "content_map.json"), "w", encoding="utf-8") as fh:
        json.dump(content_map if content_map is not None else SYNTH_MAP, fh)
    with open(os.path.join(root, "examples", "report_sample.md"), "w",
              encoding="utf-8") as fh:
        fh.write(report)
    return root


class TempCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="adapter-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.src = write_synth(os.path.join(self.tmp, "structure"))
        self.out = os.path.join(self.tmp, "out")


# --------------------------------------------------------------------------

class NormalizationTests(unittest.TestCase):

    def test_numeric_and_letter_ordinals_are_stripped_for_matching(self):
        self.assertEqual(adapter.normalize_title("1. Executive Summary"),
                         adapter.normalize_title("Executive Summary"))
        self.assertEqual(adapter.normalize_title("7.1. Group Findings - ESS"),
                         adapter.normalize_title("Group Findings - ESS"))
        # the appendices are the case that actually broke: the sample writes
        # "A. Appendix A - ..." and the map writes "Appendix A - ..."
        self.assertEqual(adapter.normalize_title("A. Appendix A - Supporting Evidence"),
                         adapter.normalize_title("Appendix A - Supporting Evidence"))

    def test_en_dash_and_hyphen_titles_match(self):
        self.assertEqual(adapter.normalize_title("Appendix A – Evidence"),
                         adapter.normalize_title("Appendix A - Evidence"))

    def test_normalization_does_not_collapse_genuinely_different_titles(self):
        self.assertNotEqual(adapter.normalize_title("Methodology"),
                            adapter.normalize_title("Method"))

    def test_split_report_returns_verbatim_substrings(self):
        preamble, secs = adapter.split_report(SYNTH_REPORT)
        self.assertIn("Preamble text", preamble)
        for heading, body in secs:
            self.assertIn(body, SYNTH_REPORT, "body for %r was not verbatim" % heading)

    def test_report_with_no_headings_is_all_preamble_not_an_error(self):
        preamble, secs = adapter.split_report("just some text\n")
        self.assertEqual(secs, [])
        self.assertEqual(preamble, "just some text\n")


# --------------------------------------------------------------------------

class SyntheticSourceTests(TempCase):

    def test_mapped_placeholder_and_source_only_are_all_accounted_for(self):
        report, manifest = adapter.build(self.src, self.out)
        c = report["counts"]
        self.assertEqual(c["map_sections"], 4)
        self.assertEqual(c["mapped"], 3)
        self.assertEqual(c["map_only_placeholder"], 1)      # "Never Written Section"
        self.assertEqual(c["source_only_carried"], 2)       # preamble + Scope boundary
        self.assertEqual(len(manifest["sections"]), 6)

    def test_declared_section_with_no_body_is_a_placeholder_not_invented_text(self):
        report, manifest = adapter.build(self.src, self.out)
        ghost = [s for s in report["sections"] if s["title"] == "Never Written Section"][0]
        self.assertEqual(ghost["content_status"], "NOT_SUPPLIED")
        self.assertEqual(ghost["origin"], "MAP_ONLY")
        entry = [s for s in manifest["sections"] if s["id"] == ghost["id"]][0]
        self.assertNotIn("source", entry)
        codes = [i["code"] for i in report["issues"]]
        self.assertIn("MAP_SECTION_WITHOUT_BODY", codes)

    def test_source_heading_absent_from_the_map_is_carried_not_dropped(self):
        report, manifest = adapter.build(self.src, self.out)
        titles = [s["title"] for s in report["sections"]]
        self.assertIn("Scope boundary", titles)
        self.assertIn("Front matter", titles)
        carried = [s for s in report["sections"] if s["title"] == "Scope boundary"][0]
        self.assertEqual(carried["origin"], "SOURCE_ONLY")
        self.assertEqual(carried["content_status"], "SUPPLIED")

    def test_attachment_list_is_unknown_not_an_empty_pass(self):
        report, manifest = adapter.build(self.src, self.out)
        self.assertEqual(manifest["attachments"], [])
        self.assertEqual(report["attachment_policy"]["status"], "UNKNOWN")
        self.assertIn("UNKNOWN", report["attachment_policy"]["note"])

    def test_assembled_pack_does_not_claim_readiness_with_nothing_declared(self):
        _report, manifest = adapter.build(self.src, self.out)
        result = bid_pack.BidPack(manifest, self.out).assemble(
            os.path.join(self.out, "submission"))
        self.assertEqual(result["readiness"]["status"], "NO_REQUIRED_ATTACHMENTS_DECLARED")
        self.assertNotIn("PRESENT", result["readiness"]["status"])

    def test_placeholder_section_renders_a_visible_page_in_the_pdf(self):
        _report, manifest = adapter.build(self.src, self.out)
        sub = os.path.join(self.out, "submission")
        bid_pack.BidPack(manifest, self.out).assemble(sub)
        import pdfwrite
        with open(os.path.join(sub, "proposal.pdf"), "rb") as fh:
            pages = pdfwrite.read_pdf_pages(fh.read())
        flat = " ".join(" ".join(pages).split())
        self.assertIn("SECTION CONTENT NOT SUPPLIED", flat)
        self.assertIn("Never Written Section", flat)

    def test_ambiguous_duplicate_headings_are_reported_not_silently_resolved(self):
        dupe = SYNTH_REPORT + "\n## 1. Executive Summary\n\nA second one.\n"
        src = write_synth(os.path.join(self.tmp, "dupe"), report=dupe)
        report, _m = adapter.build(src, os.path.join(self.tmp, "dupeout"))
        self.assertIn("AMBIGUOUS_SOURCE_HEADING", [i["code"] for i in report["issues"]])

    def test_manifest_produced_is_accepted_by_the_assembler_validator(self):
        _report, manifest = adapter.build(self.src, self.out)
        bid_pack.validate_manifest(manifest)       # raises on anything malformed

    def test_adapter_output_is_deterministic_across_two_runs(self):
        r1, m1 = adapter.build(self.src, os.path.join(self.tmp, "a"))
        r2, m2 = adapter.build(self.src, os.path.join(self.tmp, "b"))
        self.assertEqual(json.dumps(m1, sort_keys=True), json.dumps(m2, sort_keys=True))
        self.assertEqual(json.dumps(r1["counts"], sort_keys=True),
                         json.dumps(r2["counts"], sort_keys=True))


# --------------------------------------------------------------------------

class HostileSourceTests(TempCase):

    def test_missing_content_map_is_refused_with_a_useful_message(self):
        empty = os.path.join(self.tmp, "empty")
        os.makedirs(empty, exist_ok=True)
        with self.assertRaises(adapter.AdapterError) as cm:
            adapter.build(empty, self.out)
        self.assertIn("content map not found", str(cm.exception))

    def test_missing_report_sample_is_refused_rather_than_half_built(self):
        src = os.path.join(self.tmp, "nosample")
        os.makedirs(src, exist_ok=True)
        with open(os.path.join(src, "content_map.json"), "w", encoding="utf-8") as fh:
            json.dump(SYNTH_MAP, fh)
        with self.assertRaises(adapter.AdapterError) as cm:
            adapter.build(src, self.out)
        self.assertIn("report sample not found", str(cm.exception))
        self.assertFalse(os.path.exists(os.path.join(self.out, "manifest.json")))

    def test_malformed_content_map_json_is_refused(self):
        src = os.path.join(self.tmp, "badjson")
        os.makedirs(os.path.join(src, "examples"), exist_ok=True)
        with open(os.path.join(src, "content_map.json"), "w", encoding="utf-8") as fh:
            fh.write("{not json")
        with open(os.path.join(src, "examples", "report_sample.md"), "w",
                  encoding="utf-8") as fh:
            fh.write(SYNTH_REPORT)
        with self.assertRaises(adapter.AdapterError) as cm:
            adapter.build(src, self.out)
        self.assertIn("not valid JSON", str(cm.exception))

    def test_content_map_with_no_sections_is_refused(self):
        src = write_synth(os.path.join(self.tmp, "nosec"),
                          content_map={"map_id": "x", "sections": []})
        with self.assertRaises(adapter.AdapterError) as cm:
            adapter.build(src, self.out)
        self.assertIn("no sections", str(cm.exception))

    def test_map_section_with_a_blank_title_is_flagged_not_silently_matched(self):
        cmap = {"map_id": "x", "sections": [{"section_id": "SEC-01", "title": ""},
                                            {"section_id": "SEC-02", "title": "Methodology"}]}
        src = write_synth(os.path.join(self.tmp, "blank"), content_map=cmap)
        report, _m = adapter.build(src, self.out)
        self.assertIn("MAP_SECTION_WITHOUT_TITLE", [i["code"] for i in report["issues"]])

    def test_report_that_is_entirely_preamble_yields_all_placeholders(self):
        src = write_synth(os.path.join(self.tmp, "noheads"),
                          report="# Title\n\nNothing but prose.\n")
        report, manifest = adapter.build(src, self.out)
        self.assertEqual(report["counts"]["mapped"], 0)
        self.assertEqual(report["counts"]["map_only_placeholder"], 4)
        # it still assembles, and every declared section is visibly missing
        result = bid_pack.BidPack(manifest, self.out).assemble(
            os.path.join(self.out, "submission"))
        self.assertTrue(all(s["content_status"] == "NOT_SUPPLIED"
                            for s in result["sections"]
                            if s["id"].startswith("SEC-")))

    def test_cli_refuses_a_missing_source_with_exit_code_two(self):
        import contextlib
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = adapter.main(["--structure", os.path.join(self.tmp, "nope"),
                               "--out", self.out])
        self.assertEqual(rc, 2)
        self.assertIn("REFUSED", err.getvalue())


# --------------------------------------------------------------------------

@unittest.skipUnless(HAVE_REAL, "sibling lane uiowa_rfq_18649_report_structure not present")
class RealDeliveredArtifactTests(TempCase):
    """Runs against the actual landed files when they are on disk."""

    def test_every_structure_map_section_is_accounted_for(self):
        report, _m = adapter.build(REAL_STRUCTURE, self.out)
        c = report["counts"]
        self.assertEqual(c["mapped"] + c["map_only_placeholder"], c["map_sections"])
        self.assertGreaterEqual(c["map_sections"], 10)

    def test_section_bodies_are_byte_identical_to_source(self):
        # The load-bearing guarantee: this adapter does not rewrite another
        # lane's prose.
        report, _m = adapter.build(REAL_STRUCTURE, self.out)
        with open(os.path.join(REAL_STRUCTURE, "examples", "report_sample.md"),
                  encoding="utf-8") as fh:
            source = fh.read()
        checked = 0
        for s in report["sections"]:
            if s["content_status"] != "SUPPLIED":
                continue
            path = os.path.join(self.out, "sections",
                                "%s.md" % bid_pack.slugify(s["id"]))
            with open(path, encoding="utf-8") as fh:
                body = fh.read()
            self.assertIn(body, source,
                          "body for %r is not a verbatim slice of the source" % s["id"])
            checked += 1
        self.assertGreater(checked, 5)

    def test_source_sections_outside_the_map_are_carried_and_reported(self):
        report, _m = adapter.build(REAL_STRUCTURE, self.out)
        carried = [s for s in report["sections"] if s["origin"] == "SOURCE_ONLY"]
        self.assertTrue(carried, "no source-only section was detected or carried")
        self.assertIn("SOURCE_SECTION_NOT_IN_MAP", [i["code"] for i in report["issues"]])

    def test_assembled_documents_pass_the_structural_validator(self):
        _r, manifest = adapter.build(REAL_STRUCTURE, self.out)
        sub = os.path.join(self.out, "submission")
        bid_pack.BidPack(manifest, self.out).assemble(sub)
        with open(os.path.join(sub, "proposal.pdf"), "rb") as fh:
            pdf = packcheck.check_pdf(fh.read(), "integrated pdf")
        docx = packcheck.check_docx(os.path.join(sub, "proposal.docx"))
        self.assertTrue(pdf.clean, "integrated PDF has defects: %r" % pdf.defects)
        self.assertTrue(docx.clean, "integrated DOCX has defects: %r" % docx.defects)
        self.assertGreaterEqual(len(pdf.checks), 15)

    def test_the_source_fiction_label_survives_into_the_rendered_pack(self):
        _r, manifest = adapter.build(REAL_STRUCTURE, self.out)
        sub = os.path.join(self.out, "submission")
        bid_pack.BidPack(manifest, self.out).assemble(sub)
        with open(os.path.join(sub, "00-INDEX.md"), encoding="utf-8") as fh:
            index = fh.read()
        self.assertIn("SYNTHETIC", index.upper())
        self.assertIn("NOT SUBMITTED", index.upper())


if __name__ == "__main__":
    unittest.main(verbosity=2)
