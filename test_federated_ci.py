#!/usr/bin/env python3
"""Offline contract for the federated CI receipt engine."""
from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path

import host_offload.federated_ci as federated_ci


ROOT = Path(__file__).resolve().parent
PINNED_MAIN = "38dad71081c1dc2e458004324046cebf4008c03c"
GHA_BLOB = "7bfce9a1de21f42068d091968cb4e362c483def8"
GHA_SHA256 = "2f7931ab80cbc676cb0f07b2aa4cd581eb6b25e726bc2b617fa0e2a906eef0af"
GHA_BYTES = 1597


def manifest(source_sha: str = PINNED_MAIN, **overrides):
    data = federated_ci.default_manifest(source_sha)
    data.update(overrides)
    return data


class FederatedCiTests(unittest.TestCase):
    def test_planner_is_deterministic_and_covers_every_test(self):
        tests = ["zeta", "alpha", "mu"]
        first = federated_ci.plan_shards(tests, 2)
        second = federated_ci.plan_shards(list(reversed(tests)), 2)
        self.assertEqual(first, second)
        members = [name for row in first for name in row["tests"]]
        self.assertEqual(sorted(members), ["alpha", "mu", "zeta"])
        self.assertEqual(first[0]["tests"], ["alpha", "zeta"])
        self.assertEqual(first[1]["tests"], ["mu"])

    def test_unknown_provider_is_a_legal_manifest_target(self):
        data = manifest()
        data["providers"] = ["local-fixture", "not-a-real-vendor"]
        federated_ci.validate_manifest(data)

    def test_malformed_manifest_fails_closed(self):
        data = manifest()
        data["schema_version"] = "nope"
        with self.assertRaisesRegex(federated_ci.FederatedError, "schema_version"):
            federated_ci.validate_manifest(data)
        data = manifest()
        data["claim_boundary"]["other_provider_activated"] = True
        with self.assertRaisesRegex(federated_ci.FederatedError, "another provider"):
            federated_ci.validate_manifest(data)

    def test_command_envelope_refuses_shell_and_secret_env(self):
        with self.assertRaisesRegex(federated_ci.FederatedError, "shell"):
            federated_ci.command_envelope(["true"], shell=True)
        with self.assertRaisesRegex(federated_ci.FederatedError, "secret"):
            federated_ci.command_envelope(["true"], env={"GITHUB_TOKEN": "x"})

    def test_local_fixture_runner_is_measured_and_deterministic(self):
        data = manifest()
        a = federated_ci.run_local_fixture(data, 0)
        b = federated_ci.run_local_fixture(data, 0)
        self.assertEqual(a["provider"], "local-fixture")
        self.assertTrue(a["measured"])
        self.assertEqual(a["terminal_state"], "PASSED")
        self.assertEqual(a["exit_code"], 0)
        self.assertEqual(a["receipt_id"], b["receipt_id"])
        self.assertEqual(a["artifacts"][0]["sha256"], b["artifacts"][0]["sha256"])
        self.assertEqual(a["artifacts"][0]["bytes"], b["artifacts"][0]["bytes"])
        self.assertIsNone(a["run_url"])
        self.assertFalse(a["claim_boundary"]["provider_activated_by_this_engine"])
        self.assertFalse(a["claim_boundary"]["other_provider_activated"])
        self.assertEqual(a["artifacts"][0]["sha256"], federated_ci.sha256_text("ok-0"))

    def test_stale_source_is_a_finding(self):
        data = manifest()
        receipt = federated_ci.run_local_fixture(data, 0)
        stale = copy.deepcopy(receipt)
        stale["source_sha"] = "aa" * 20
        stale["receipt_id"] = federated_ci.receipt_id_for(
            stale["job_id"], stale["shard_id"], stale["attempt"], stale["provider"], stale["source_sha"], stale["test_identity"]
        )
        federated_ci.validate_receipt(stale)
        report = federated_ci.reconcile(data, [stale, federated_ci.run_local_fixture(data, 1)])
        codes = [row["code"] for row in report["findings"]]
        self.assertIn("STALE_SOURCE", codes)
        self.assertEqual(report["status"], "DIVERGED")

    def test_partial_shards_are_missing(self):
        data = manifest()
        report = federated_ci.reconcile(data, [federated_ci.run_local_fixture(data, 0)])
        codes = [row["code"] for row in report["findings"]]
        self.assertIn("MISSING_SHARD", codes)
        self.assertEqual(report["status"], "DIVERGED")
        missing = next(row for row in report["findings"] if row["code"] == "MISSING_SHARD")
        self.assertEqual(missing["shard_id"], 1)

    def test_retry_lineage_is_recorded(self):
        data = manifest()
        first = federated_ci.run_local_fixture(data, 0, attempt=1)
        retry = federated_ci.run_local_fixture(data, 0, attempt=2, parent_receipt_id=first["receipt_id"])
        other = federated_ci.run_local_fixture(data, 1)
        report = federated_ci.reconcile(data, [first, retry, other])
        lineage = [row for row in report["findings"] if row["code"] == "RETRY_LINEAGE"]
        self.assertEqual(len(lineage), 1)
        self.assertTrue(lineage[0]["parent_present"])
        self.assertEqual(lineage[0]["attempt"], 2)
        self.assertEqual(report["status"], "RECONCILED")

    def test_duplicate_receipts_are_flagged(self):
        data = manifest()
        a = federated_ci.run_local_fixture(data, 0)
        b = federated_ci.run_local_fixture(data, 1)
        report = federated_ci.reconcile(data, [a, copy.deepcopy(a), b])
        dup = next(row for row in report["findings"] if row["code"] == "DUPLICATE_RECEIPT")
        self.assertEqual(dup["count"], 2)
        self.assertEqual(report["status"], "RECONCILED")

    def test_hash_mismatch_and_artifact_drift(self):
        data = manifest()
        a = federated_ci.run_local_fixture(data, 0)
        b = copy.deepcopy(a)
        b["provider"] = "local-fixture-copy"
        b["receipt_id"] = federated_ci.receipt_id_for(
            b["job_id"], b["shard_id"], b["attempt"], b["provider"], b["source_sha"], b["test_identity"]
        )
        b["artifacts"][0]["sha256"] = "0" * 64
        other = federated_ci.run_local_fixture(data, 1)
        report = federated_ci.reconcile(data, [a, b, other])
        codes = {row["code"] for row in report["findings"]}
        self.assertIn("ARTIFACT_DRIFT", codes)
        self.assertEqual(report["status"], "DIVERGED")

    def test_contradictory_exits(self):
        data = manifest()
        a = federated_ci.run_local_fixture(data, 0)
        b = copy.deepcopy(a)
        b["provider"] = "shadow"
        b["exit_code"] = 1
        b["terminal_state"] = "FAILED"
        b["receipt_id"] = federated_ci.receipt_id_for(
            b["job_id"], b["shard_id"], b["attempt"], b["provider"], b["source_sha"], b["test_identity"]
        )
        other = federated_ci.run_local_fixture(data, 1)
        report = federated_ci.reconcile(data, [a, b, other])
        codes = {row["code"] for row in report["findings"]}
        self.assertIn("CONTRADICTORY_EXIT", codes)
        self.assertEqual(report["status"], "DIVERGED")

    def test_cancellation_is_blocking(self):
        data = manifest()
        a = federated_ci.run_local_fixture(data, 0)
        cancelled = copy.deepcopy(a)
        cancelled["provider"] = "cancelled-lab"
        cancelled["terminal_state"] = "CANCELLED"
        cancelled["exit_code"] = 130
        cancelled["measured"] = False
        cancelled["claim_boundary"]["measured_live_run"] = False
        cancelled["receipt_id"] = federated_ci.receipt_id_for(
            cancelled["job_id"],
            cancelled["shard_id"],
            cancelled["attempt"],
            cancelled["provider"],
            cancelled["source_sha"],
            cancelled["test_identity"],
        )
        other = federated_ci.run_local_fixture(data, 1)
        report = federated_ci.reconcile(data, [a, cancelled, other])
        codes = {row["code"] for row in report["findings"]}
        self.assertIn("CANCELLED", codes)
        self.assertEqual(report["status"], "DIVERGED")

    def test_malformed_receipt_schema(self):
        data = manifest()
        receipt = federated_ci.run_local_fixture(data, 0)
        receipt["terminal_state"] = "WINNING"
        with self.assertRaisesRegex(federated_ci.FederatedError, "terminal_state"):
            federated_ci.validate_receipt(receipt)
        report = federated_ci.reconcile(data, [receipt])
        self.assertEqual(report["findings"][0]["code"], "MALFORMED")

    def test_scanner_hits_fail_closed(self):
        raw = b"email=test@example.com token=ghp_abcdefghijklmnopqrstuvwxyz password=hunter2"
        hits = federated_ci.scan_bytes(raw)
        self.assertEqual(hits["EMAIL"], 1)
        self.assertEqual(hits["GITHUB_TOKEN"], 1)
        self.assertEqual(hits["PASSWORD"], 1)

    def test_reconcile_happy_path_measures_only_local_fixture(self):
        data = manifest()
        receipts = [federated_ci.run_local_fixture(data, 0), federated_ci.run_local_fixture(data, 1)]
        fixture_shape = github_actions_shape_receipt(data, receipts[0])
        report = federated_ci.reconcile(data, receipts + [fixture_shape])
        self.assertEqual(report["status"], "RECONCILED")
        self.assertEqual(report["providers_measured"], ["local-fixture"])
        self.assertIn("github-actions", report["providers_seen"])
        self.assertIn("cirrus", report["providers_supported_by_contract_only"])
        self.assertFalse(report["claim_boundary"]["other_provider_activated"])
        self.assertFalse(report["claim_boundary"]["provider_activated_by_this_engine"])

    def test_checked_in_corpus_and_page(self):
        man = json.loads((ROOT / "ci/federated/manifests/header-echo.v1.json").read_text(encoding="utf-8"))
        federated_ci.validate_manifest(man)
        self.assertEqual(man["source_sha"], PINNED_MAIN)
        r0 = json.loads((ROOT / "ci/federated/receipts/local-fixture-shard-0.json").read_text(encoding="utf-8"))
        r1 = json.loads((ROOT / "ci/federated/receipts/local-fixture-shard-1.json").read_text(encoding="utf-8"))
        federated_ci.validate_receipt(r0)
        federated_ci.validate_receipt(r1)
        self.assertEqual(r0["artifacts"][0]["sha256"], federated_ci.sha256_text("ok-0"))
        self.assertEqual(r1["artifacts"][0]["sha256"], federated_ci.sha256_text("ok-1"))
        readback = json.loads((ROOT / "ci/federated/github_actions_readback.json").read_text(encoding="utf-8"))
        self.assertEqual(readback["provider"], "github-actions")
        self.assertEqual(readback["kind"], "fixture-readback-not-a-live-run")
        self.assertEqual(readback["source"]["commit"], PINNED_MAIN)
        self.assertEqual(readback["source"]["git_blob"], GHA_BLOB)
        self.assertEqual(readback["source"]["sha256"], GHA_SHA256)
        self.assertEqual(readback["source"]["bytes"], GHA_BYTES)
        self.assertFalse(readback["claim_boundary"]["measured_live_run"])
        self.assertFalse(readback["claim_boundary"]["provider_activated_by_this_engine"])
        self.assertFalse(readback["claim_boundary"]["other_provider_activated"])
        self.assertIsNone(readback["run_url"])
        rec = json.loads((ROOT / "ci/federated/reconciliation/example.json").read_text(encoding="utf-8"))
        self.assertEqual(rec["status"], "RECONCILED")
        self.assertEqual(rec["providers_measured"], ["local-fixture"])
        self.assertNotIn("github-actions", rec["providers_measured"])
        page = (ROOT / "federated-ci.html").read_text(encoding="utf-8")
        self.assertIn("local-fixture", page)
        self.assertIn("UNMEASURED", page)
        self.assertIn(PINNED_MAIN, page)
        self.assertNotIn("ghp_", page)
        readme = (ROOT / "ci/federated/README.md").read_text(encoding="utf-8")
        self.assertIn("not a measured run", readme.lower())
        self.assertIn("unknown providers remain usable", readme.lower())

    def test_checked_in_receipts_reconcile(self):
        man = json.loads((ROOT / "ci/federated/manifests/header-echo.v1.json").read_text(encoding="utf-8"))
        receipts = [
            json.loads((ROOT / "ci/federated/receipts/local-fixture-shard-0.json").read_text(encoding="utf-8")),
            json.loads((ROOT / "ci/federated/receipts/local-fixture-shard-1.json").read_text(encoding="utf-8")),
            json.loads((ROOT / "ci/federated/receipts/github-actions-shape-shard-0.json").read_text(encoding="utf-8")),
        ]
        report = federated_ci.reconcile(man, receipts)
        self.assertEqual(report["status"], "RECONCILED")
        self.assertEqual(report["providers_measured"], ["local-fixture"])

    def test_git_object_pin_when_available(self):
        import subprocess

        spec = f"{PINNED_MAIN}:.github/workflows/header-census.yml"
        probe = subprocess.run(["git", "cat-file", "-e", spec], cwd=ROOT, capture_output=True, check=False)
        if probe.returncode != 0:
            self.skipTest("pinned source commit is outside this checkout")
        data = subprocess.check_output(["git", "show", spec], cwd=ROOT)
        blob = subprocess.check_output(["git", "rev-parse", spec], cwd=ROOT, text=True).strip()
        self.assertEqual(len(data), GHA_BYTES)
        self.assertEqual(federated_ci.sha256_bytes(data), GHA_SHA256)
        self.assertEqual(blob, GHA_BLOB)


def github_actions_shape_receipt(data, local_receipt):
    return federated_ci.make_receipt(
        job_id=data["job_id"],
        shard_id=0,
        attempt=1,
        source_sha=data["source_sha"],
        test_identity=local_receipt["test_identity"],
        command=local_receipt["command"],
        exit_code=0,
        duration_ms=0,
        artifacts=local_receipt["artifacts"],
        provider="github-actions",
        run_url="fixture://github-actions/header-census-shape",
        terminal_state="FIXTURE",
        measured=False,
        claim_boundary={
            "measured_live_run": False,
            "provider_activated_by_this_engine": False,
            "other_provider_activated": False,
            "fabricated_url": False,
            "quota_claimed": False,
        },
    )


if __name__ == "__main__":
    unittest.main()
