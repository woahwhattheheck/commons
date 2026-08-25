"""Deterministic, synthetic tests for the Subzero Artifact Explorer v2."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import unittest

from host.subzero_explorer import (
    EVIDENCE_CLASSES,
    PACKET,
    RECEIPT_SCHEMA,
    RECEIPT_VERSION,
    SCHEMA_VERSION,
    build_artifact_row,
    build_catalog,
    canonical_json,
    classify_evidence,
    load_catalog,
    parse_excerpt,
    self_test,
)


ROOT = os.path.dirname(os.path.abspath(__file__))
COMMIT = "a" * 40
TREE = "b" * 40


def _packet():
    with open(os.path.join(ROOT, PACKET), encoding="utf-8") as handle:
        return json.load(handle)


def _grbn_expected():
    return next(item for item in _packet()["organs"] if item["name"] == "muhl_grbn")


def _binding(row):
    return {
        "name": row["name"],
        "path": row["path"],
        "sha256": row["sha256"],
    }


def _base_receipt(row):
    return {
        "schema_version": RECEIPT_VERSION,
        "kind": "SUBZERO_VALIDATION_RECEIPT",
        "receipt_id": "synthetic-receipt",
        "catalog": {"source_commit": COMMIT, "source_tree": TREE},
        "artifact": _binding(row),
        "checks": [
            {
                "id": "artifact_sha256",
                "status": "PASS",
                "evidence_path": row["path"],
                "evidence_sha256": row["sha256"],
                "observation": "synthetic hash binding",
            }
        ],
    }


def _valid_runtime(row):
    receipt = _base_receipt(row)
    receipt["runtime_measurement"] = {
        "status": "PASS",
        "run_id": "synthetic-run",
        "process_id": "synthetic-process",
        "observed_at": "2026-08-25T00:00:00Z",
        "runner_path": "synthetic/runner.py",
        "runner_sha256": "c" * 64,
        "test_path": "synthetic/test_runner.py",
        "test_sha256": "d" * 64,
        "input_sha256": "e" * 64,
        "output_sha256": "f" * 64,
    }
    return receipt


def _valid_customer(row):
    receipt = _base_receipt(row)
    receipt["receipt_id"] = "synthetic-customer-pass"
    receipt["buyer_acceptance"] = {
        "status": "PASS",
        "buyer_reference": "synthetic-buyer-reference",
        "accepted_at": "2026-08-25T00:01:00Z",
    }
    receipt["delivered_at"] = "2026-08-25T00:00:30Z"
    receipt["result_address"] = "public://synthetic-delivery"
    return receipt


class SubzeroExplorerV2Tests(unittest.TestCase):
    def test_header_parser_known_present_grbn(self):
        rel = os.path.join("excerpts", "20260823", "muhl_grbn.mno")
        with open(os.path.join(ROOT, rel), "rb") as handle:
            parsed = parse_excerpt(handle.read())
        self.assertTrue(parsed["ok"])
        self.assertEqual(parsed["magic"], "MUHLGRBN")
        self.assertEqual(parsed["n_gate"], 8704)
        self.assertEqual(
            parsed["sha256"],
            "09214540b3f3117ab93a4c509017a5e7b9c5f12d86545069af4ffcdae99c6632",
        )

    def test_generator_is_deterministic_and_uses_exact_enum(self):
        first = build_catalog(ROOT, COMMIT, TREE)
        second = build_catalog(ROOT, COMMIT, TREE)
        self.assertEqual(canonical_json(first), canonical_json(second))
        self.assertEqual(first["schema_version"], SCHEMA_VERSION)
        self.assertEqual(first["source_commit"], COMMIT)
        self.assertEqual(first["source_tree"], TREE)
        self.assertEqual(first["evidence_classes"], list(EVIDENCE_CLASSES))
        self.assertEqual(first["v2"]["spec_id"], "jojo-subzero-explorer-v2-followup-20260825-01")
        self.assertEqual(first["v2"]["source_commit"], COMMIT)
        self.assertTrue(first["v2"]["presence_never_escalates"])
        self.assertFalse(first["v2"]["login_required"])
        self.assertFalse(first["v2"]["privileged_tier"])
        self.assertEqual(len(first["rows"]), 31)
        self.assertEqual(len({row["name"] for row in first["rows"]}), 31)
        self.assertEqual(
            {row["evidence_class"] for row in first["rows"]},
            {"STRUCTURAL_ONLY"},
        )

    def test_every_row_has_hashed_pinned_source_test_card_and_sidecar(self):
        catalog = build_catalog(ROOT, COMMIT, TREE)
        for row in catalog["rows"]:
            self.assertEqual(row["artifact"]["status"], "PRESENT")
            self.assertEqual(len(row["artifact"]["sha256"]), 64)
            self.assertEqual(len(row["artifact"]["git_blob_sha1"]), 40)
            self.assertIn("/blob/%s/" % COMMIT, row["artifact"]["url"])
            for key in ("fabricator", "structural_test", "sidecar", "packet"):
                source = row["sources"][key]
                self.assertEqual(source["status"], "PRESENT", (row["name"], key))
                self.assertEqual(len(source["sha256"]), 64)
                self.assertEqual(len(source["git_blob_sha1"]), 40)
                self.assertIn("/blob/%s/" % COMMIT, source["url"])
            card = row["sources"]["card"]
            self.assertIn(card["status"], ("PRESENT", "FINDER_FAILED"))
            self.assertIn("/blob/%s/" % COMMIT, card["url"])
        grbn = next(row for row in catalog["rows"] if row["name"] == "muhl_grbn")
        self.assertEqual(grbn["header"]["status"], "MATCH")
        self.assertEqual(grbn["acceptance"]["status"], "PASS")

    def test_corruption_fails_closed_to_unknown_with_named_falsifier(self):
        expected = _grbn_expected()
        with tempfile.TemporaryDirectory() as temp:
            stem = "grbn"
            paths = [
                PACKET,
                "excerpts/20260823/muhl_grbn.mno",
                "excerpts/20260823/grbn_circuits.json",
                "muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_%s.py" % stem,
                "muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_%s.py" % stem,
                "ground/SUBZERO_GRBN.md",
            ]
            for rel in paths:
                destination = os.path.join(temp, rel)
                os.makedirs(os.path.dirname(destination), exist_ok=True)
                shutil.copy2(os.path.join(ROOT, rel), destination)
            artifact = os.path.join(temp, "excerpts/20260823/muhl_grbn.mno")
            with open(artifact, "r+b") as handle:
                handle.seek(-1, os.SEEK_END)
                byte = handle.read(1)
                handle.seek(-1, os.SEEK_END)
                handle.write(bytes([byte[0] ^ 1]))
            row = build_artifact_row(temp, expected, COMMIT, TREE, calibrated=True)
        self.assertEqual(row["evidence_class"], "UNKNOWN")
        self.assertIn("artifact_hash", row["acceptance"]["failures"])
        self.assertIn("artifact SHA-256 differs", row["acceptance"]["falsifiers"][0])

    def test_missing_structural_test_fails_closed_not_zero(self):
        expected = _grbn_expected()
        with tempfile.TemporaryDirectory() as temp:
            for rel in (
                PACKET,
                "excerpts/20260823/muhl_grbn.mno",
                "excerpts/20260823/grbn_circuits.json",
                "muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_grbn.py",
                "ground/SUBZERO_GRBN.md",
            ):
                destination = os.path.join(temp, rel)
                os.makedirs(os.path.dirname(destination), exist_ok=True)
                shutil.copy2(os.path.join(ROOT, rel), destination)
            row = build_artifact_row(temp, expected, COMMIT, TREE, calibrated=True)
        self.assertEqual(row["evidence_class"], "UNKNOWN")
        self.assertIn("structural_test", row["acceptance"]["failures"])
        self.assertIsNone(row["sources"]["structural_test"]["bytes"])

    def test_titan_presence_and_payment_alone_never_escalate(self):
        row = build_artifact_row(ROOT, _grbn_expected(), COMMIT, TREE, calibrated=True)
        receipt = _base_receipt(row)
        receipt["titan"] = "PRESENT"
        receipt["path"] = "synthetic/titan.gguf"
        receipt["payment"] = {"status": "PAID", "reference": "synthetic"}
        evidence_class, runtime_ids, customer_ids = classify_evidence(
            True, [receipt], row["artifact"], {"source_commit": COMMIT, "source_tree": TREE}
        )
        self.assertEqual(evidence_class, "STRUCTURAL_ONLY")
        self.assertEqual(runtime_ids, [])
        self.assertEqual(customer_ids, [])

        valid_runtime = _valid_runtime(row)
        valid_runtime["titan"] = "PRESENT"
        self.assertEqual(
            classify_evidence(
                True,
                [valid_runtime],
                row["artifact"],
                {"source_commit": COMMIT, "source_tree": TREE},
            )[0],
            "STRUCTURAL_ONLY",
        )

    def test_valid_bound_runtime_receipt_is_runtime_measured(self):
        row = build_artifact_row(ROOT, _grbn_expected(), COMMIT, TREE, calibrated=True)
        receipt = _valid_runtime(row)
        evidence_class, runtime_ids, _ = classify_evidence(
            True, [receipt], row["artifact"], {"source_commit": COMMIT, "source_tree": TREE}
        )
        self.assertEqual(evidence_class, "RUNTIME_MEASURED")
        self.assertEqual(runtime_ids, ["synthetic-receipt"])
        receipt["runtime_measurement"]["output_sha256"] = "wrong"
        self.assertEqual(
            classify_evidence(
                True,
                [receipt],
                row["artifact"],
                {"source_commit": COMMIT, "source_tree": TREE},
            )[0],
            "STRUCTURAL_ONLY",
        )

    def test_customer_ready_requires_bound_buyer_pass(self):
        row = build_artifact_row(ROOT, _grbn_expected(), COMMIT, TREE, calibrated=True)
        receipt = _valid_customer(row)
        evidence_class, _, customer_ids = classify_evidence(
            True, [receipt], row["artifact"], {"source_commit": COMMIT, "source_tree": TREE}
        )
        self.assertEqual(evidence_class, "CUSTOMER_READY")
        self.assertEqual(customer_ids, ["synthetic-customer-pass"])
        receipt["checks"][0]["evidence_sha256"] = "0" * 64
        self.assertEqual(
            classify_evidence(
                True,
                [receipt],
                row["artifact"],
                {"source_commit": COMMIT, "source_tree": TREE},
            )[0],
            "STRUCTURAL_ONLY",
        )

    def test_receipt_schema_is_strict_and_payment_is_non_classifying(self):
        with open(os.path.join(ROOT, RECEIPT_SCHEMA), encoding="utf-8") as handle:
            schema = json.load(handle)
        self.assertFalse(schema["additionalProperties"])
        self.assertTrue(schema["no_auth"])
        self.assertTrue(schema["no_gate"])
        self.assertFalse(schema["login_required"])
        self.assertFalse(schema["privileged_tier"])
        self.assertTrue(schema["presence_never_escalates"])
        self.assertEqual(schema["evidence_classes"], list(EVIDENCE_CLASSES))
        self.assertIn("runtimeMeasurement", schema["$defs"])
        self.assertIn("buyerAcceptance", schema["$defs"])
        self.assertIn("runtime_receipt", schema["$defs"])
        self.assertIn("buyer_receipt", schema["$defs"])
        self.assertFalse(schema["$defs"]["runtime_receipt"]["additionalProperties"])
        self.assertFalse(schema["$defs"]["buyer_receipt"]["additionalProperties"])
        self.assertIn("never changes an evidence class", schema["$defs"]["payment"]["description"])
        self.assertNotIn("titan", schema["properties"])

    def test_open_ui_has_receipt_download_without_admission_controls(self):
        with open(os.path.join(ROOT, "subzero.html"), encoding="utf-8") as handle:
            html = handle.read().lower()
        self.assertIn("no auth. no gate.", html)
        self.assertIn("validation receipt", html)
        self.assertIn("download", html)
        self.assertNotIn("<form", html)
        self.assertNotIn('type="password"', html)
        self.assertNotIn("login", html)
        self.assertNotIn("signup", html)
        self.assertNotIn("credential", html)
        self.assertNotIn("privileged", html)
        self.assertNotIn("action-tier", html)

    def test_checked_in_catalog_is_exact_generator_output(self):
        with open(os.path.join(ROOT, "ground/SUBZERO_EXPLORER.json"), encoding="utf-8") as handle:
            text = handle.read()
        catalog = load_catalog(text)
        self.assertEqual(catalog.get("error"), "")
        regenerated = build_catalog(ROOT, catalog["source_commit"], catalog["source_tree"])
        catalog.pop("error", None)
        self.assertEqual(text, canonical_json(regenerated))

    def test_self_test(self):
        self.assertTrue(self_test())


if __name__ == "__main__":
    unittest.main()
