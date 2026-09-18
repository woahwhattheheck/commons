"""Deterministic, synthetic tests for the Subzero Artifact Explorer v2."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
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
    customer_receipt_reasons,
    load_catalog,
    parse_excerpt,
    resolve_source_objects,
    runtime_receipt_reasons,
    self_test,
    source_evidence,
)


ROOT = os.path.dirname(os.path.abspath(__file__))
FAKE_COMMIT = "d" * 40
FAKE_TREE = "e" * 40
GRBN_PATHS = (
    PACKET,
    "excerpts/20260823/muhl_grbn.mno",
    "excerpts/20260823/grbn_circuits.json",
    "muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_grbn.py",
    "muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_grbn.py",
    "ground/SUBZERO_GRBN.md",
)


def _git(cwd, *args):
    return subprocess.check_output(["git", "-C", cwd, *args], stderr=subprocess.DEVNULL).decode().strip()


def _live_objects():
    return _git(ROOT, "rev-parse", "HEAD"), _git(ROOT, "rev-parse", "HEAD^{tree}")


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


def _base_receipt(row, commit, tree):
    return {
        "schema_version": RECEIPT_VERSION,
        "kind": "SUBZERO_VALIDATION_RECEIPT",
        "receipt_id": "synthetic-receipt",
        "catalog": {"source_commit": commit, "source_tree": tree},
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


def _valid_runtime(row, commit, tree):
    receipt = _base_receipt(row, commit, tree)
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


def _valid_customer(row, commit, tree):
    receipt = _base_receipt(row, commit, tree)
    receipt["receipt_id"] = "synthetic-customer-pass"
    receipt["buyer_acceptance"] = {
        "status": "PASS",
        "buyer_reference": "synthetic-buyer-reference",
        "accepted_at": "2026-08-25T00:01:00Z",
    }
    receipt["delivered_at"] = "2026-08-25T00:00:30Z"
    receipt["result_address"] = "public://synthetic-delivery"
    return receipt


def _seed_grbn_repo(paths=GRBN_PATHS):
    temp = tempfile.mkdtemp()
    subprocess.check_call(["git", "init", "-q"], cwd=temp)
    subprocess.check_call(["git", "config", "core.autocrlf", "false"], cwd=temp)
    subprocess.check_call(["git", "config", "user.email", "test@example.com"], cwd=temp)
    subprocess.check_call(["git", "config", "user.name", "fixture"], cwd=temp)
    for rel in paths:
        destination = os.path.join(temp, rel)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.copy2(os.path.join(ROOT, rel), destination)
    subprocess.check_call(["git", "add", "-A"], cwd=temp)
    subprocess.check_call(["git", "commit", "-q", "-m", "fixture"], cwd=temp)
    return temp, _git(temp, "rev-parse", "HEAD"), _git(temp, "rev-parse", "HEAD^{tree}")


def _rmtree(path):
    """Remove temporary Git repositories whose objects are read-only on Windows."""

    def make_writable(function, item, _error):
        os.chmod(item, stat.S_IWRITE)
        function(item)

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=make_writable)
    else:
        shutil.rmtree(path, onerror=make_writable)


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
        commit, tree = _live_objects()
        first = build_catalog(ROOT, commit, tree)
        second = build_catalog(ROOT, commit, tree)
        self.assertEqual(canonical_json(first), canonical_json(second))
        self.assertEqual(first["schema_version"], SCHEMA_VERSION)
        self.assertEqual(first["source_commit"], commit)
        self.assertEqual(first["source_tree"], tree)
        self.assertEqual(first["evidence_classes"], list(EVIDENCE_CLASSES))
        self.assertEqual(first["v2"]["spec_id"], "jojo-subzero-explorer-v2-followup-20260825-01")
        self.assertEqual(first["v2"]["source_commit"], commit)
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
        commit, tree = _live_objects()
        catalog = build_catalog(ROOT, commit, tree)
        for row in catalog["rows"]:
            self.assertEqual(row["artifact"]["status"], "PRESENT")
            self.assertEqual(len(row["artifact"]["sha256"]), 64)
            self.assertEqual(len(row["artifact"]["git_blob_sha1"]), 40)
            self.assertIn("/blob/%s/" % commit, row["artifact"]["url"])
            for key in ("fabricator", "structural_test", "sidecar", "packet", "card"):
                source = row["sources"][key]
                self.assertEqual(source["status"], "PRESENT", (row["name"], key))
                self.assertEqual(len(source["sha256"]), 64)
                self.assertEqual(len(source["git_blob_sha1"]), 40)
                self.assertIn("/blob/%s/" % commit, source["url"])
        grbn = next(row for row in catalog["rows"] if row["name"] == "muhl_grbn")
        self.assertEqual(grbn["header"]["status"], "MATCH")
        self.assertEqual(grbn["acceptance"]["status"], "PASS")
        chpr = next(row for row in catalog["rows"] if row["name"] == "muhl_chimera_pred_rgcg")
        chls = next(row for row in catalog["rows"] if row["name"] == "muhl_chimera_lvin_synd")
        self.assertEqual(chpr["sources"]["card"]["path"], "ground/SUBZERO_CHPR.md")
        self.assertEqual(chls["sources"]["card"]["path"], "ground/SUBZERO_CHLS.md")
        self.assertEqual(chpr["acceptance"]["status"], "PASS")
        self.assertEqual(chls["acceptance"]["status"], "PASS")

    def test_missing_card_fails_closed_not_pass(self):
        paths = [rel for rel in GRBN_PATHS if rel != "ground/SUBZERO_GRBN.md"]
        temp, commit, tree = _seed_grbn_repo(paths)
        try:
            row = build_artifact_row(temp, _grbn_expected(), commit, tree, calibrated=True)
        finally:
            _rmtree(temp)
        self.assertEqual(row["sources"]["card"]["status"], "FINDER_FAILED")
        self.assertEqual(row["evidence_class"], "UNKNOWN")
        self.assertEqual(row["acceptance"]["status"], "FAIL")
        self.assertIn("card", row["acceptance"]["failures"])

    def test_corruption_fails_closed_to_unknown_with_named_falsifier(self):
        temp, commit, tree = _seed_grbn_repo()
        try:
            artifact = os.path.join(temp, "excerpts/20260823/muhl_grbn.mno")
            with open(artifact, "r+b") as handle:
                handle.seek(-1, os.SEEK_END)
                byte = handle.read(1)
                handle.seek(-1, os.SEEK_END)
                handle.write(bytes([byte[0] ^ 1]))
            row = build_artifact_row(temp, _grbn_expected(), commit, tree, calibrated=True)
        finally:
            _rmtree(temp)
        self.assertEqual(row["evidence_class"], "UNKNOWN")
        self.assertIn(row["artifact"]["status"], ("STALE_BINDING", "FINDER_FAILED"))
        self.assertTrue(
            {"artifact_present", "artifact_hash"} & set(row["acceptance"]["failures"])
        )
        self.assertIn("artifact SHA-256 differs", row["acceptance"]["falsifiers"][0])

    def test_stale_fabricator_sidecar_test_and_card_fail_closed(self):
        temp, commit, tree = _seed_grbn_repo()
        try:
            for rel in (
                "muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_grbn.py",
                "muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_grbn.py",
                "excerpts/20260823/grbn_circuits.json",
                "ground/SUBZERO_GRBN.md",
            ):
                path = os.path.join(temp, rel)
                with open(path, "ab") as handle:
                    handle.write(b"\n# stale\n")
            row = build_artifact_row(temp, _grbn_expected(), commit, tree, calibrated=True)
        finally:
            _rmtree(temp)
        self.assertEqual(row["evidence_class"], "UNKNOWN")
        self.assertEqual(row["acceptance"]["status"], "FAIL")
        self.assertEqual(row["sources"]["fabricator"]["status"], "STALE_BINDING")
        self.assertEqual(row["sources"]["structural_test"]["status"], "STALE_BINDING")
        self.assertEqual(row["sources"]["sidecar"]["status"], "STALE_BINDING")
        self.assertEqual(row["sources"]["card"]["status"], "STALE_BINDING")
        for key in ("fabricator", "structural_test", "sidecar", "card"):
            self.assertIn(key, row["acceptance"]["failures"])

    def test_missing_structural_test_fails_closed_not_zero(self):
        paths = [
            rel
            for rel in GRBN_PATHS
            if rel != "muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_grbn.py"
        ]
        temp, commit, tree = _seed_grbn_repo(paths)
        try:
            row = build_artifact_row(temp, _grbn_expected(), commit, tree, calibrated=True)
        finally:
            _rmtree(temp)
        self.assertEqual(row["evidence_class"], "UNKNOWN")
        self.assertIn("structural_test", row["acceptance"]["failures"])
        self.assertIsNone(row["sources"]["structural_test"]["bytes"])

    def test_nonexistent_commit_and_tree_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "present Git commit"):
            build_catalog(ROOT, FAKE_COMMIT, FAKE_TREE)
        commit, tree = _live_objects()
        with self.assertRaisesRegex(ValueError, "present Git tree"):
            resolve_source_objects(ROOT, commit, FAKE_TREE)
        other_tree = _git(ROOT, "rev-parse", "HEAD^^{tree}")
        if other_tree and other_tree != tree:
            with self.assertRaisesRegex(ValueError, "not the tree of the source commit"):
                resolve_source_objects(ROOT, commit, other_tree)
        self.assertEqual(source_evidence(ROOT, "ground/SUBZERO_GRBN.md", FAKE_COMMIT)["status"], "FINDER_FAILED")

    def test_titan_presence_and_payment_alone_never_escalate(self):
        commit, tree = _live_objects()
        row = build_artifact_row(ROOT, _grbn_expected(), commit, tree, calibrated=True)
        receipt = _base_receipt(row, commit, tree)
        receipt["titan"] = "PRESENT"
        receipt["path"] = "synthetic/titan.gguf"
        receipt["payment"] = {"status": "PAID", "reference": "synthetic"}
        evidence_class, runtime_ids, customer_ids = classify_evidence(
            True, [receipt], row["artifact"], {"source_commit": commit, "source_tree": tree}
        )
        self.assertEqual(evidence_class, "STRUCTURAL_ONLY")
        self.assertEqual(runtime_ids, [])
        self.assertEqual(customer_ids, [])

        valid_runtime = _valid_runtime(row, commit, tree)
        valid_runtime["titan"] = "PRESENT"
        self.assertEqual(
            classify_evidence(
                True,
                [valid_runtime],
                row["artifact"],
                {"source_commit": commit, "source_tree": tree},
            )[0],
            "STRUCTURAL_ONLY",
        )

    def test_valid_bound_runtime_receipt_is_runtime_measured(self):
        commit, tree = _live_objects()
        row = build_artifact_row(ROOT, _grbn_expected(), commit, tree, calibrated=True)
        receipt = _valid_runtime(row, commit, tree)
        evidence_class, runtime_ids, _ = classify_evidence(
            True, [receipt], row["artifact"], {"source_commit": commit, "source_tree": tree}
        )
        self.assertEqual(evidence_class, "RUNTIME_MEASURED")
        self.assertEqual(runtime_ids, ["synthetic-receipt"])
        receipt["runtime_measurement"]["output_sha256"] = "wrong"
        self.assertEqual(
            classify_evidence(
                True,
                [receipt],
                row["artifact"],
                {"source_commit": commit, "source_tree": tree},
            )[0],
            "STRUCTURAL_ONLY",
        )

    def test_invalid_runtime_timestamp_and_fail_check_do_not_escalate(self):
        commit, tree = _live_objects()
        row = build_artifact_row(ROOT, _grbn_expected(), commit, tree, calibrated=True)
        receipt = _valid_runtime(row, commit, tree)
        receipt["checks"][0]["status"] = "FAIL"
        receipt["runtime_measurement"]["observed_at"] = "not-a-timestamp"
        self.assertIn("checks.status", runtime_receipt_reasons(receipt, row["artifact"], receipt["catalog"]))
        self.assertIn(
            "runtime_measurement.observed_at",
            runtime_receipt_reasons(receipt, row["artifact"], receipt["catalog"]),
        )
        self.assertEqual(
            classify_evidence(
                True,
                [receipt],
                row["artifact"],
                {"source_commit": commit, "source_tree": tree},
            )[0],
            "STRUCTURAL_ONLY",
        )

    def test_invalid_buyer_and_delivery_timestamps_do_not_escalate(self):
        commit, tree = _live_objects()
        row = build_artifact_row(ROOT, _grbn_expected(), commit, tree, calibrated=True)
        receipt = _valid_customer(row, commit, tree)
        receipt["buyer_acceptance"]["accepted_at"] = "yesterday"
        receipt["delivered_at"] = "also-not-a-timestamp"
        reasons = customer_receipt_reasons(receipt, row["artifact"], receipt["catalog"])
        self.assertIn("buyer_acceptance.accepted_at", reasons)
        self.assertIn("delivered_at", reasons)
        self.assertEqual(
            classify_evidence(
                True,
                [receipt],
                row["artifact"],
                {"source_commit": commit, "source_tree": tree},
            )[0],
            "STRUCTURAL_ONLY",
        )

    def test_nonempty_list_nested_receipt_fields_fail_closed(self):
        commit, tree = _live_objects()
        row = build_artifact_row(ROOT, _grbn_expected(), commit, tree, calibrated=True)
        for field in ("artifact", "catalog", "runtime_measurement", "buyer_acceptance"):
            receipt = _valid_runtime(row, commit, tree)
            receipt[field] = ["not-an-object"]
            reasons = runtime_receipt_reasons(receipt, row["artifact"], {"source_commit": commit, "source_tree": tree})
            self.assertTrue(reasons, field)
            self.assertEqual(
                classify_evidence(
                    True,
                    [receipt],
                    row["artifact"],
                    {"source_commit": commit, "source_tree": tree},
                )[0],
                "STRUCTURAL_ONLY",
                field,
            )

    def test_customer_ready_requires_bound_buyer_pass(self):
        commit, tree = _live_objects()
        row = build_artifact_row(ROOT, _grbn_expected(), commit, tree, calibrated=True)
        receipt = _valid_customer(row, commit, tree)
        evidence_class, _, customer_ids = classify_evidence(
            True, [receipt], row["artifact"], {"source_commit": commit, "source_tree": tree}
        )
        self.assertEqual(evidence_class, "CUSTOMER_READY")
        self.assertEqual(customer_ids, ["synthetic-customer-pass"])
        receipt["checks"][0]["evidence_sha256"] = "0" * 64
        self.assertEqual(
            classify_evidence(
                True,
                [receipt],
                row["artifact"],
                {"source_commit": commit, "source_tree": tree},
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
