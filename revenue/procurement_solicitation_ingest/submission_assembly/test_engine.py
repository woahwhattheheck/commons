from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from revenue.procurement_solicitation_ingest.submission_assembly import engine


def h(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_sha(label: str) -> str:
    return h(label.encode("utf-8"))


class SubmissionAssemblyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "artifacts").mkdir()
        self.artifact_root = self.root / "artifacts"
        self.tech = b"technical response\n"
        self.forms = b"signed certified form\n"
        (self.artifact_root / "Technical.txt").write_bytes(self.tech)
        (self.artifact_root / "Forms.txt").write_bytes(self.forms)
        self.doc = self._base_input()

    def tearDown(self):
        self.tmp.cleanup()

    def _slot(self, slot_id: str, *, required: bool, order: int | None, file_name: str | None,
              formats=None, max_pages=None, max_bytes=None, signature="NONE", certification="NONE",
              attachment_class=None, portal_field=None, section="S1"):
        return {
            "slot_id": slot_id, "required": required, "order": order, "file_name": file_name,
            "formats": formats or [], "max_pages": max_pages, "max_bytes": max_bytes,
            "signature_requirement": signature, "certification_requirement": certification,
            "attachment_class": attachment_class, "portal_field": portal_field, "section_id": section,
        }

    def _attestation(self, kind: str, artifact: bytes, evidence: str):
        return {"type": kind, "artifact_sha256": h(artifact), "evidence_sha256": source_sha(evidence)}

    def _base_input(self):
        v1 = {
            "source_id": "rfp-v1", "source_sha256": source_sha("rfp-v1-bytes"),
            "source_authority": engine.SOURCE_AUTHORITY, "observed_at": "2026-09-01T12:00:00-04:00",
            "sequence": 1, "deadline_at": "2026-10-01T17:00:00-04:00",
            "slots": [
                self._slot("technical", required=True, order=1, file_name="Technical-v1.txt", formats=["txt"], max_pages=5, max_bytes=1024, section="4.1"),
                self._slot("forms", required=False, order=2, file_name="Forms.txt", formats=["txt"], max_pages=2, max_bytes=1024, section="4.2"),
            ],
        }
        v2 = {
            "source_id": "addendum-1", "source_sha256": source_sha("addendum-1-bytes"),
            "source_authority": engine.SOURCE_AUTHORITY, "observed_at": "2026-09-10T09:00:00-04:00",
            "sequence": 2, "deadline_at": "2026-10-02T17:00:00-04:00",
            "slots": [
                self._slot("forms", required=True, order=1, file_name="Forms.txt", formats=["txt"], max_pages=2, max_bytes=1024,
                           signature="SIGNATURE_PRESENT_REQUIRED", certification="CERTIFICATION_PRESENT_REQUIRED",
                           attachment_class="MANDATORY_FORM", portal_field="forms_upload", section="A1.2"),
                self._slot("technical", required=True, order=2, file_name="Technical.txt", formats=["txt"], max_pages=4, max_bytes=1024,
                           attachment_class="TECHNICAL", portal_field="technical_upload", section="A1.1"),
            ],
        }
        return {
            "schema": engine.INPUT_SCHEMA, "truth_boundary": engine.TRUTH_BOUNDARY,
            "evaluated_at": "2026-09-17T03:00:00-04:00", "opportunity_id": "synthetic-rfp-001",
            "source_generations": [v1, v2],
            "artifacts": [
                {"artifact_id": "technical-current", "slot_id": "technical", "path": "Technical.txt", "sha256": h(self.tech), "format": "txt", "pages": 3, "attestations": []},
                {"artifact_id": "forms-current", "slot_id": "forms", "path": "Forms.txt", "sha256": h(self.forms), "format": "txt", "pages": 1,
                 "attestations": [self._attestation("SIGNATURE_PRESENT", self.forms, "signature-evidence"), self._attestation("CERTIFICATION_PRESENT", self.forms, "cert-evidence")]},
            ],
        }

    def _raw(self, doc=None):
        return json.dumps(self.doc if doc is None else doc, sort_keys=True, separators=(",", ":")).encode()

    def _loader(self):
        return engine.artifact_loader_from_root(self.artifact_root)

    def _compile(self, doc=None):
        return engine.compile_manifest(self._raw(doc), self._loader())

    def _manifest(self, doc=None):
        return json.loads(self._compile(doc)[0])

    def test_ready_manifest_binds_latest_generation_and_amendment_delta(self):
        manifest, checklist, receipt = self._compile()
        obj = json.loads(manifest)
        self.assertEqual(engine.READY, obj["status"])
        self.assertEqual("addendum-1", obj["active_source"]["source_id"])
        self.assertEqual([], obj["conflicts"])
        self.assertEqual([], obj["missing_required_slots"])
        self.assertTrue(all(row["candidate_safe_for_owner_review"] for row in obj["slots"]))
        self.assertTrue(all(row["owner_review_still_required"] for row in obj["slots"]))
        changed = {(r["slot_id"], tuple(r["fields"])) for r in obj["instruction_changes_from_prior_generation"]}
        self.assertIn(("__deadline__", ("deadline_at",)), changed)
        self.assertTrue(any(r["slot_id"] == "forms" and "required" in r["fields"] for r in obj["instruction_changes_from_prior_generation"]))
        self.assertTrue(any(r["slot_id"] == "technical" and "file_name" in r["fields"] for r in obj["instruction_changes_from_prior_generation"]))
        self.assertTrue(all(value is False for value in obj["authority"].values()))
        self.assertIn(b"ASSEMBLY_READY_FOR_OWNER_REVIEW", checklist)
        receipt_obj = json.loads(receipt)
        self.assertEqual(h(manifest), receipt_obj["manifest_sha256"])
        self.assertEqual(h(checklist), receipt_obj["checklist_sha256"])
        self.assertTrue(engine.verify(self._raw(), manifest, checklist, receipt, self._loader()))

    def test_missing_required_artifact_holds(self):
        doc = copy.deepcopy(self.doc)
        doc["artifacts"] = [row for row in doc["artifacts"] if row["slot_id"] != "forms"]
        obj = self._manifest(doc)
        self.assertEqual(engine.MISSING, obj["status"])
        self.assertEqual(["forms"], obj["missing_required_slots"])
        self.assertEqual([{"action": "PROVIDE_REQUIRED_ARTIFACT", "slot_id": "forms"}], obj["missing_artifact_worklist"])

    def test_deadline_passed_dominates(self):
        doc = copy.deepcopy(self.doc)
        doc["evaluated_at"] = "2026-10-03T00:00:00-04:00"
        self.assertEqual(engine.DEADLINE, self._manifest(doc)["status"])

    def test_source_conflict_outranks_deadline(self):
        doc = copy.deepcopy(self.doc)
        doc["evaluated_at"] = "2026-10-03T00:00:00-04:00"
        doc["source_generations"][1]["sequence"] = 1
        obj = self._manifest(doc)
        self.assertEqual(engine.CONFLICT, obj["status"])
        self.assertTrue(any("sequence" in reason for reason in obj["conflicts"]))

    def test_duplicate_or_nonmonotone_source_history_holds_conflict(self):
        doc = copy.deepcopy(self.doc)
        doc["source_generations"][1]["sequence"] = 1
        obj = self._manifest(doc)
        self.assertEqual(engine.CONFLICT, obj["status"])
        self.assertTrue(any("sequence" in reason for reason in obj["conflicts"]))

    def test_future_source_holds_conflict(self):
        doc = copy.deepcopy(self.doc)
        doc["source_generations"][1]["observed_at"] = "2026-09-18T09:00:00-04:00"
        obj = self._manifest(doc)
        self.assertEqual(engine.CONFLICT, obj["status"])
        self.assertTrue(any("future source" in reason for reason in obj["conflicts"]))

    def test_stale_artifact_bytes_hold_conflict(self):
        (self.artifact_root / "Technical.txt").write_bytes(b"changed after retained digest\n")
        obj = self._manifest()
        self.assertEqual(engine.CONFLICT, obj["status"])
        self.assertTrue(any("digest does not match bytes" in reason for reason in obj["conflicts"]))

    def test_filename_format_page_byte_and_attestation_fail_closed(self):
        variants = []
        d = copy.deepcopy(self.doc); d["artifacts"][0]["path"] = "wrong.txt"; variants.append((d, "filename"))
        d = copy.deepcopy(self.doc); d["artifacts"][0]["format"] = "pdf"; variants.append((d, "format"))
        d = copy.deepcopy(self.doc); d["artifacts"][0]["pages"] = 5; variants.append((d, "page limit"))
        d = copy.deepcopy(self.doc); d["source_generations"][1]["slots"][1]["max_bytes"] = 4; variants.append((d, "byte limit"))
        d = copy.deepcopy(self.doc); d["artifacts"][1]["attestations"] = [d["artifacts"][1]["attestations"][1]]; variants.append((d, "signature-present"))
        d = copy.deepcopy(self.doc); d["artifacts"][1]["attestations"] = [d["artifacts"][1]["attestations"][0]]; variants.append((d, "certification-present"))
        for doc, needle in variants:
            with self.subTest(needle=needle):
                obj = self._manifest(doc)
                self.assertEqual(engine.CONFLICT, obj["status"])
                self.assertTrue(any(needle in reason for reason in obj["conflicts"]), obj["conflicts"])

    def test_noncurrent_slot_or_duplicate_candidate_holds_conflict(self):
        doc = copy.deepcopy(self.doc)
        extra = copy.deepcopy(doc["artifacts"][0]); extra["artifact_id"] = "technical-copy"; doc["artifacts"].append(extra)
        obj = self._manifest(doc)
        self.assertEqual(engine.CONFLICT, obj["status"])
        self.assertTrue(any("multiple candidate" in reason for reason in obj["conflicts"]))
        doc = copy.deepcopy(self.doc)
        extra = copy.deepcopy(doc["artifacts"][0]); extra["artifact_id"] = "obsolete"; extra["slot_id"] = "removed-v1-slot"; doc["artifacts"].append(extra)
        obj = self._manifest(doc)
        self.assertEqual(engine.CONFLICT, obj["status"])
        self.assertTrue(any("non-current slot" in reason for reason in obj["conflicts"]))

    def test_duplicate_json_float_bool_int_and_naive_time_rejected(self):
        with self.assertRaises(engine.AssemblyError):
            engine.load_strict_json(b'{"schema":"x","schema":"y"}')
        with self.assertRaises(engine.AssemblyError):
            engine.load_strict_json(b'{"x":1.5}')
        doc = copy.deepcopy(self.doc); doc["source_generations"][1]["sequence"] = True
        with self.assertRaises(engine.AssemblyError):
            engine.normalize_input(self._raw(doc))
        doc = copy.deepcopy(self.doc); doc["evaluated_at"] = "2026-09-17T03:00:00"
        with self.assertRaises(engine.AssemblyError):
            engine.normalize_input(self._raw(doc))

    def test_path_traversal_and_symlink_and_fifo_are_fail_closed_without_block(self):
        doc = copy.deepcopy(self.doc); doc["artifacts"][0]["path"] = "../Technical.txt"
        with self.assertRaises(engine.AssemblyError):
            engine.normalize_input(self._raw(doc))
        target = self.artifact_root / "real-tech.txt"; target.write_bytes(self.tech)
        link = self.artifact_root / "Technical.txt"; link.unlink(); link.symlink_to(target.name)
        obj = self._manifest()
        self.assertEqual(engine.CONFLICT, obj["status"])
        self.assertTrue(any("symlink forbidden" in reason for reason in obj["conflicts"]))
        link.unlink(); os.mkfifo(link)
        obj = self._manifest()
        self.assertEqual(engine.CONFLICT, obj["status"])
        self.assertTrue(any("regular file required" in reason for reason in obj["conflicts"]))

    def test_verify_recompiles_semantics_and_rejects_tamper(self):
        manifest, checklist, receipt = self._compile()
        tampered = json.loads(manifest)
        tampered["status"] = engine.READY
        tampered["authority"]["proposal_submission_authorized"] = True
        self.assertFalse(engine.verify(self._raw(), engine.canon(tampered), checklist, receipt, self._loader()))
        self.assertFalse(engine.verify(self._raw(), manifest, checklist + b"tamper", receipt, self._loader()))

    def test_cli_create_exclusive_and_verify(self):
        inp = self.root / "input.json"; inp.write_bytes(self._raw()); out = self.root / "out"
        self.assertEqual(0, engine.main(["compile", "--input", str(inp), "--artifact-root", str(self.artifact_root), "--out-dir", str(out)]))
        self.assertEqual(2, engine.main(["compile", "--input", str(inp), "--artifact-root", str(self.artifact_root), "--out-dir", str(out)]))
        self.assertEqual(0, engine.main(["verify", "--input", str(inp), "--artifact-root", str(self.artifact_root), "--manifest", str(out / "assembly.json"), "--checklist", str(out / "assembly.md"), "--receipt", str(out / "receipt.json")]))

    def test_authority_ceiling_is_hard_false_in_manifest_and_receipt(self):
        manifest, _, receipt = self._compile()
        self.assertTrue(all(v is False for v in json.loads(manifest)["authority"].values()))
        self.assertTrue(all(v is False for v in json.loads(receipt)["authority"].values()))


if __name__ == "__main__":
    unittest.main()
