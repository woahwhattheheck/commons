"""Executable contract for UIOWA-033; all records and source bytes are fictional."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import lineage as L


def row(rid="E1", document="DOC1", content="fictional v1", version="v1", **extra):
    result = {"record_id": rid, "document_id": document, "sha256": hashlib.sha256(content.encode()).hexdigest(),
              "version": version, "title": "Fictional release notes", "location": rid + ".txt"}
    result.update(extra)
    return result


def manifest(*rows, name="test"):
    return {"schema": L.SCHEMA, "collection_id": name, "synthetic": True, "records": list(rows)}


def findings(record, fid="F1", **extra):
    return {"findings": [{"finding_id": fid, "citations": [{**L.reference(record), "locator": "section 2", **extra}]}]}


class LineageTests(unittest.TestCase):
    def change(self, before, after):
        return L.compare(manifest(before), manifest(after))["changes"][0]["kind"]

    def impact(self, before, after, citation=None):
        return L.compare(manifest(before), manifest(*after), findings(citation or before))["finding_impacts"][0]

    def test_identical_manifest(self):
        self.assertEqual(self.change(row(), row()), "UNCHANGED")

    def test_rename_retains_hash_and_citation(self):
        before = row()
        after = row(location="renamed.txt")
        self.assertEqual(self.change(before, after), "RENAMED_EXACT_CONTENT")
        self.assertEqual(self.impact(before, [after])["status"], "EXACT_CONTENT_RETAINED")

    def test_metadata_change_not_content_revision(self):
        self.assertEqual(self.change(row(), row(metadata={"owner": "fictional operator"})), "METADATA_CHANGED")

    def test_copy_preserves_original_identity(self):
        self.assertEqual(self.change(row(), row(rid="E2")), "EXACT_CONTENT_COPY")
        report = L.compare(manifest(row()), manifest(row(), row(rid="E2")))
        self.assertEqual(report["duplicates_after"][0]["record_ids"], ["E1", "E2"])

    def test_identical_bytes_different_document_not_same_identity(self):
        self.assertEqual(self.change(row(), row(rid="E2", document="DOC2")), "SAME_BYTES_DIFFERENT_DOCUMENT")
        self.assertEqual(self.impact(row(), [row(rid="E2", document="DOC2")])["status"], "MISSING_FROM_AFTER")

    def test_version_label_conflict(self):
        self.assertEqual(self.change(row(), row(content="different")), "VERSION_LABEL_CONFLICT")
        result = L.compare(manifest(row()), manifest(row(content="different")))
        self.assertEqual(result["anomalies"][0]["kind"], "VERSION_LABEL_CONFLICT")

    def test_different_version_does_not_invent_supersession(self):
        revised = row(content="different", version="v99")
        self.assertEqual(self.change(row(), revised), "CONTENT_CHANGED_REVIEW")
        self.assertEqual(self.impact(row(), [revised])["status"], "CONTENT_CHANGED_REVIEW")

    def test_title_is_not_identity(self):
        other = row(rid="E2", document="DOC2", content="unrelated", title="  FICTIONAL   RELEASE NOTES ")
        self.assertEqual(self.change(row(), other), "TITLE_MATCH_DIFFERENT_CONTENT")

    def test_new_document(self):
        other = row(rid="E2", document="DOC2", content="new", title="Another subject")
        self.assertEqual(self.change(row(), other), "ADDED")

    def test_record_id_reuse(self):
        self.assertEqual(self.change(row(), row(document="DOC2", content="other")), "RECORD_ID_REUSED")

    def test_exact_identity_reuse_across_document_is_invalid(self):
        with self.assertRaisesRegex(L.InvalidInput, "identity reused"):
            self.change(row(), row(document="DOC2"))

    def test_declared_supersession(self):
        before = row()
        after = row(rid="E2", content="fictional revision", version="v2", supersedes=[L.reference(before)])
        impact = self.impact(before, [after])
        self.assertEqual(impact["status"], "DECLARED_SUPERSEDED_REVIEW")
        self.assertEqual(impact["declared_successors"], [L.reference(after)])
        self.assertEqual(impact["locator_validation"], "NOT_PERFORMED")

    def test_superseded_retained_copy_is_not_current_by_hash_alone(self):
        before = row()
        after = row(rid="E2", content="revision", version="v2", supersedes=[L.reference(before)])
        result = self.impact(before, [before, after])
        self.assertEqual(result["status"], "DECLARED_SUPERSEDED_REVIEW")
        self.assertEqual(result["retained_exact_copies"], [L.reference(before)])

    def test_branched_successors_require_review(self):
        before = row()
        children = [row(rid=f"E{i}", content=f"branch {i}", version=f"v{i}", supersedes=[L.reference(before)])
                    for i in (2, 3)]
        result = self.impact(before, children)
        self.assertEqual(result["status"], "BRANCHED_SUCCESSION_REVIEW")
        self.assertEqual(len(result["declared_successors"]), 2)

    def test_transitive_chain_preserves_historical_declarations(self):
        first = row()
        second = row(rid="E2", content="second", version="v2", supersedes=[L.reference(first)])
        third = row(rid="E3", content="third", version="v3", supersedes=[L.reference(second)])
        report = L.compare(manifest(first, second), manifest(third), findings(first))
        self.assertEqual(report["finding_impacts"][0]["declared_successors"], [L.reference(third)])

    def test_dangling_predecessor_does_not_prove_succession(self):
        after = row(rid="E2", content="revision", version="v2", supersedes=[L.reference(row(rid="missing"))])
        report = L.compare(manifest(row()), manifest(after), findings(row()))
        self.assertEqual(report["anomalies"][0]["kind"], "DANGLING_PREDECESSOR")
        self.assertEqual(report["finding_impacts"][0]["status"], "CONTENT_CHANGED_REVIEW")

    def test_cross_document_predecessor_is_diagnostic_not_link(self):
        before = row()
        after = row(rid="E2", document="DOC2", content="other", supersedes=[L.reference(before)])
        report = L.compare(manifest(before), manifest(after), findings(before))
        self.assertEqual(report["anomalies"][0]["kind"], "CROSS_DOCUMENT_PREDECESSOR")
        self.assertEqual(report["finding_impacts"][0]["status"], "MISSING_FROM_AFTER")

    def test_predecessor_cycle_rejected(self):
        first, second = row(), row(rid="E2", version="v2", content="v2")
        first["supersedes"], second["supersedes"] = [L.reference(second)], [L.reference(first)]
        with self.assertRaisesRegex(L.InvalidInput, "cycle"):
            L.compare(manifest(), manifest(first, second))

    def test_missing_citation_record(self):
        report = L.compare(manifest(), manifest(), findings(row()))
        self.assertEqual(report["finding_impacts"][0]["status"], "UNKNOWN_CITATION")

    def test_citation_digest_mismatch(self):
        result = self.impact(row(), [row()], citation=row(content="wrong digest"))
        self.assertEqual(result["status"], "CITATION_DIGEST_MISMATCH")

    def test_absent_records_are_explicit(self):
        report = L.compare(manifest(row()), manifest(), findings(row()))
        self.assertEqual(report["departures"][0]["status"], "RECORD_ABSENT_FROM_AFTER")
        self.assertEqual(report["finding_impacts"][0]["status"], "MISSING_FROM_AFTER")

    def test_no_citations_not_a_pass(self):
        report = L.compare(manifest(), manifest(), {"findings": [{"finding_id": "F1", "citations": []}]})
        self.assertEqual(report["finding_impacts"][0]["status"], "NO_CITATIONS_SUPPLIED")

    def test_input_metadata_and_locators_preserved_without_mutation(self):
        source = row(metadata={"owner": "fictional", "custom": {"tags": ["x", "y"]}})
        before = manifest(source)
        copied = deepcopy(before)
        f = findings(source, locator="page 5; table B")
        report = L.compare(before, before, f)
        self.assertEqual(before, copied)
        self.assertEqual(report["before"], before)
        self.assertEqual(report["input_findings"], f)
        report["before"]["records"][0]["metadata"]["custom"]["tags"].append("z")
        self.assertEqual(before, copied)

    def test_deterministic_report_and_input_binding(self):
        before, after = manifest(row()), manifest(row(rid="E2"))
        a, b = L.compare(before, after), L.compare(before, after)
        self.assertEqual(L.encoded(a), L.encoded(b))
        self.assertEqual(a["input_sha256"]["before"], hashlib.sha256(L.encoded(before).encode()).hexdigest())

    def test_empty_manifest_is_valid(self):
        self.assertEqual(L.compare(manifest(), manifest())["summary"]["before_records"], 0)

    def test_invalid_manifest_fields(self):
        valid = manifest(row())
        invalids = [None, [], {**valid, "schema": "unknown"}, {**valid, "synthetic": 1},
                    {**valid, "records": {}}, {**valid, "records": [None]}, manifest(row(sha256="a" * 63)),
                    manifest(row(sha256="A" * 64)), manifest(row(version="")), manifest(row(), row()),
                    manifest(row(supersedes="E1")), manifest(row(metadata=[]))]
        for candidate in invalids:
            with self.subTest(candidate=candidate), self.assertRaises((L.InvalidInput, ValueError)):
                L.validate_manifest(candidate)

    def test_duplicate_findings_and_predecessors_rejected(self):
        f = findings(row())
        f["findings"] *= 2
        with self.assertRaisesRegex(L.InvalidInput, "duplicate finding"):
            L.compare(manifest(row()), manifest(row()), f)
        with self.assertRaisesRegex(L.InvalidInput, "duplicate predecessor"):
            L.validate_manifest(manifest(row(supersedes=[L.reference(row()), L.reference(row())])))

    def test_strict_json_loader(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "input.json"
            for data in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}'):
                path.write_text(data)
                with self.subTest(data=data), self.assertRaises(L.InvalidInput):
                    L.load(path)

    def test_markdown_escapes_html_pipes_and_linebreaks(self):
        record = row(rid="E|<script>\nnext")
        report = L.compare(manifest(record), manifest(record), findings(record))
        output = L.markdown(report)
        self.assertNotIn("<script>", output)
        self.assertIn("&#124;", output)
        self.assertIn("DRAFT_NON_AUTHORITATIVE", output)
        self.assertIn("NOT", L.encoded(report))

    def test_snapshot_hashes_real_bytes_and_preserves_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = b"Synthetic bytes\x00\xff\n"
            (root / "E1.txt").write_bytes(data)
            record = row()
            del record["sha256"]
            result = L.snapshot(manifest(record), root)
            self.assertEqual(result["records"][0]["sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual((root / "E1.txt").read_bytes(), data)

    def test_snapshot_rejects_wrong_declared_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "E1.txt").write_text("different")
            with self.assertRaisesRegex(L.InvalidInput, "digest differs"):
                L.snapshot(manifest(row()), root)

    def test_snapshot_rejects_escape_and_symlink(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for location in ("../outside", "/etc/passwd"):
                with self.subTest(location=location), self.assertRaises(L.InvalidInput):
                    L.snapshot(manifest(row(location=location)), root)
            (root / "actual.txt").write_text("fictional v1")
            (root / "E1.txt").symlink_to(root / "actual.txt")
            with self.assertRaisesRegex(L.InvalidInput, "symlink"):
                L.snapshot(manifest(row()), root)

    def test_authority_adapter_preserves_scope_and_strips_scores(self):
        source = {"source_id": "ESS-SW-01", "source_ref": "synthetic://ESS-SW-01",
                  "source_content_sha256": row()["sha256"], "authority_generation": "g1",
                  "solicitation_id": "18649", "prime_candidate": "Fictional Prime", "group": "ESS",
                  "dimension": "software", "observed_at": "2026-08-15T12:00:00Z", "evidence_kind": "artifact",
                  "maturity": 3, "confidence_bp": 8900, "claim": "Fictional claim"}
        bundle = {"schema": "uiowa-rfq18649-evidence-authority/v2", "generation": "g1",
                  "solicitation_id": "18649", "prime_candidate": "Fictional Prime", "sources": [source]}
        output = L.from_authority(bundle, synthetic=True)
        self.assertEqual(output["records"][0]["metadata"]["group"], "ESS")
        self.assertNotIn("maturity", L.encoded(output))
        self.assertNotIn("confidence_bp", L.encoded(output))
        self.assertNotIn("claim", output["records"][0])
        bundle["sources"][0]["group"] = "RIS"
        changed = L.from_authority(bundle, synthetic=False)
        self.assertNotEqual(changed["records"][0]["document_id"], output["records"][0]["document_id"])
        self.assertFalse(changed["synthetic"])
        bundle["sources"][0]["authority_generation"] = "g2"
        with self.assertRaisesRegex(L.InvalidInput, "generation mismatch"):
            L.from_authority(bundle, synthetic=True)

    def test_cli_exit_codes_and_read_only_compare(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first, second = root / "before.json", root / "after.json"
            first.write_text(L.encoded(manifest(row())))
            second.write_text(L.encoded(manifest(row(rid="E2"))))
            prior_bytes = first.read_bytes(), second.read_bytes()
            command = [sys.executable, str(Path(L.__file__)), "compare", str(first), str(second)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["changes"][0]["kind"], "EXACT_CONTENT_COPY")
            self.assertEqual((first.read_bytes(), second.read_bytes()), prior_bytes)
            second.write_text('{"schema":1,"schema":2}')
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertIn("duplicate JSON key", result.stderr)



class DemoTests(unittest.TestCase):
    def test_materialized_rehearsal_is_reproducible_and_sources_unchanged(self):
        import demo
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = demo.build(root / "one")
            second = demo.build(root / "two")
            self.assertEqual(first, second)
            expected = {"ADDED": 1, "CONTENT_CHANGED_REVIEW": 2, "EXACT_CONTENT_COPY": 1,
                        "RENAMED_EXACT_CONTENT": 1, "TITLE_MATCH_DIFFERENT_CONTENT": 1,
                        "VERSION_LABEL_CONFLICT": 1}
            self.assertEqual(first["summary"]["change_counts"], expected)
            impacts = {row["finding_id"]: row["status"] for row in first["finding_impacts"]}
            self.assertEqual(impacts["F-ESS-P1"], "DECLARED_SUPERSEDED_REVIEW")
            self.assertEqual(impacts["F-RIS-R1"], "EXACT_CONTENT_RETAINED")
            self.assertEqual(impacts["F-RIS-X1"], "MISSING_FROM_AFTER")
            self.assertEqual(impacts["F-IAM-A1"], "CONTENT_CHANGED_REVIEW")
            for label in ("before", "after"):
                collection = first[label]
                for row in collection["records"]:
                    path = root / "one" / label / row["location"]
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), row["sha256"])
            with self.assertRaises(FileExistsError):
                demo.build(root / "one")
            self.assertEqual((root / "one" / "review.json").read_bytes(),
                             (root / "two" / "review.json").read_bytes())

    def test_demo_and_snapshot_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "rehearsal"
            here = Path(__file__).parent
            process = subprocess.run([sys.executable, str(here / "demo.py"), str(out)],
                                     capture_output=True, text=True, timeout=10)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual(json.loads(process.stdout)["after_records"], 7)
            process = subprocess.run([sys.executable, str(here / "lineage.py"), "snapshot",
                                      str(out / "before-catalog.json"), str(out / "before")],
                                     capture_output=True, text=True, timeout=10)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual(json.loads(process.stdout), L.load(out / "before.json"))


if __name__ == "__main__":
    unittest.main()
