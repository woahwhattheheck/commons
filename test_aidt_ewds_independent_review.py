"""Independent V2 receipt review by ZZ-KESTREL-47; synthetic/offline only.

Run from repository root with unittest, normally and under python -O. This is
an independent semantic/CLI suite, not live-source or complete-project proof.
"""
from __future__ import annotations

import copy
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from revenue.aidt_ewds_workshare import core

ROOT = Path(__file__).resolve().parent
PYTHON = [sys.executable] + (["-" + "O" * sys.flags.optimize] if sys.flags.optimize else [])


def digest(label):
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def reseal(receipt):
    """Independent implementation, deliberately not the compiler's seal helper."""
    result = copy.deepcopy(receipt)
    result.pop("receipt_sha256", None)
    canonical = json.dumps(result, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True, allow_nan=False).encode("ascii")
    result["receipt_sha256"] = hashlib.sha256(canonical).hexdigest()
    return result


def record(name, version="one"):
    return {"record_id": "SYN-" + name, "record_sha256": digest(name + version)}


def sync(name="event", accepted=True, target_digest=None, target_system="adobe_lms"):
    payload = digest("synthetic payload")
    event = {"source_system": "salesforce", "target_system": target_system,
             "event_id": "SYN-" + name, "entity_ref": "SYN-applicant",
             "operation": "enroll", "payload_sha256": payload}
    observed = {"accepted": accepted, "target_ref": "SYN-enrolment",
                "target_payload_sha256": target_digest or payload}
    return core.compile_sync_receipt(event, observed)


class TestIndependentReceiptSemantics(unittest.TestCase):
    def setUp(self):
        self.good = core.reconcile_migration([record("a")], [record("a")])
        self.bad = core.reconcile_migration([record("b")], [])
        self.evidence = {name: digest("synthetic " + name)
                         for name in core.REQUIRED_WORKSHARE_EVIDENCE}
        self.parent = core.compile_readiness(self.evidence, [self.good], [sync()])

    def test_equal_counts_do_not_hide_three_different_record_errors(self):
        source = [record("shared"), record("missing")]
        target = [record("shared", "changed"), record("extra")]
        receipt = core.reconcile_migration(source, target)
        self.assertEqual((receipt["source_count"], receipt["target_count"]), (2, 2))
        self.assertEqual(receipt["missing_record_ids"], ["SYN-missing"])
        self.assertEqual(receipt["extra_record_ids"], ["SYN-extra"])
        self.assertEqual(receipt["mismatched_record_ids"], ["SYN-shared"])
        self.assertEqual(receipt["decision"], "HOLD_MIGRATION_RECONCILIATION")
        self.assertTrue(core.verify_migration_receipt(receipt))

    def test_resealed_summary_changes_are_rejected_independently(self):
        changes = {
            "source_count": 99,
            "target_count": 99,
            "source_manifest_sha256": digest("wrong source"),
            "target_manifest_sha256": digest("wrong target"),
            "missing_record_ids": [],
            "extra_record_ids": ["SYN-extra"],
            "mismatched_record_ids": ["SYN-changed"],
            "decision": "MIGRATION_RECONCILED",
            "evidence_authority": "AUTHENTICATED_SOURCE",
            "external_submission_authorized": True,
        }
        for field, value in changes.items():
            with self.subTest(field=field):
                changed = copy.deepcopy(self.bad)
                changed[field] = value
                with self.assertRaises(core.WorkshareError):
                    core.verify_migration_receipt(reseal(changed))

    def test_independent_generation_pin_rejects_a_different_valid_generation(self):
        different = core.reconcile_migration([record("different")], [record("different")])
        self.assertTrue(core.verify_migration_receipt(different))
        for side in ("source", "target"):
            with self.subTest(side=side):
                with self.assertRaisesRegex(core.WorkshareError, "independent pin mismatch"):
                    core.verify_migration_receipt(different, **{
                        "expected_" + side + "_manifest_sha256": self.good[side + "_manifest_sha256"]})
        self.assertTrue(core.verify_migration_receipt(self.good,
            expected_source_manifest_sha256=self.good["source_manifest_sha256"],
            expected_target_manifest_sha256=self.good["target_manifest_sha256"]))

    def test_false_is_not_accepted_as_zero_or_zero_as_false(self):
        packets = [(self.good, core.verify_migration_receipt),
                   (sync(), core.verify_sync_receipt), (self.parent, core.verify_readiness)]
        exercised = 0
        for packet, verifier in packets:
            for field, value in packet.items():
                if type(value) is bool or type(value) is int:
                    with self.subTest(schema=packet["schema"], field=field):
                        changed = copy.deepcopy(packet)
                        changed[field] = int(value) if type(value) is bool else bool(value)
                        with self.assertRaises(core.WorkshareError):
                            verifier(reseal(changed))
                        exercised += 1
        self.assertEqual(exercised, 16)

    def test_each_parent_authority_and_blocker_change_is_replayed(self):
        held = core.compile_readiness({}, [self.bad], [sync(accepted=False)])
        changes = {
            "state": "WORKSHARE_READY_FOR_PRIME_REVIEW",
            "hold_reasons": [], "missing_workshare_evidence": [],
            "blocking_migration_receipts": [], "blocking_sync_receipts": [],
            "collection_policy": "AT_LEAST_ONE", "coverage_authority": "COMPLETE_PROJECT",
            "controlling_source_recheck_required": False, "prime_qualified": True,
            "proposal_submission_authorized": True, "revenue_claim_authorized": True,
        }
        for field, value in changes.items():
            with self.subTest(field=field):
                changed = copy.deepcopy(held)
                changed[field] = value
                with self.assertRaises(core.WorkshareError):
                    core.verify_readiness(reseal(changed))

    def test_failed_children_survive_beside_successes_in_both_orders(self):
        rejected = sync("bad-event", accepted=False)
        accepted = sync("good-event")
        expected = None
        for migrations in itertools.permutations([self.good, self.bad]):
            for syncs in itertools.permutations([accepted, rejected]):
                packet = core.compile_readiness(self.evidence, list(migrations), list(syncs))
                self.assertEqual(packet["state"], "HOLD_WORKSHARE_INCOMPLETE")
                self.assertEqual(packet["blocking_migration_receipts"], [self.bad["receipt_sha256"]])
                self.assertEqual(packet["blocking_sync_receipts"], [rejected["receipt_sha256"]])
                self.assertEqual(len(packet["migration_receipts"]), 2)
                self.assertEqual(len(packet["sync_receipts"]), 2)
                self.assertTrue(core.verify_readiness(packet))
                if expected is not None:
                    self.assertEqual(packet, expected)
                expected = packet

    def test_selecting_a_different_collection_does_not_claim_complete_project(self):
        held = core.compile_readiness(self.evidence, [self.good, self.bad], [sync()])
        selected = core.compile_readiness(self.evidence, [self.good], [sync()])
        self.assertNotEqual(held["state"], selected["state"])
        self.assertEqual(selected["state"], "WORKSHARE_READY_FOR_PRIME_REVIEW")
        self.assertEqual(selected["coverage_authority"], "CALLER_SELECTED_COLLECTION_NOT_PROJECT_COMPLETENESS")
        self.assertIs(selected["prime_qualified"], False)
        self.assertIs(selected["proposal_submission_authorized"], False)
        self.assertTrue(core.verify_readiness(selected))

    def test_receipts_detach_nested_manifests_and_evidence(self):
        migration = copy.deepcopy(self.good)
        observation = sync()
        evidence = dict(self.evidence)
        parent = core.compile_readiness(evidence, [migration], [observation])
        before = copy.deepcopy(parent)
        migration["source_records"][0]["record_id"] = "SYN-mutated-after-compile"
        migration["target_records"].clear()
        evidence.clear()
        observation["decision"] = "HOLD_SYNC_ACCEPTANCE"
        self.assertEqual(parent, before)
        self.assertTrue(core.verify_readiness(parent))

    def test_conflicting_event_observations_reject_but_distinct_pairs_are_valid(self):
        accepted = sync()
        rejected = sync(accepted=False)
        with self.assertRaisesRegex(core.WorkshareError, "conflicting current observations"):
            core.compile_readiness(self.evidence, [self.good], [accepted, rejected])
        other_pair = sync(target_system="ewds")
        packet = core.compile_readiness(self.evidence, [self.good], [accepted, other_pair])
        self.assertEqual(len(packet["sync_receipts"]), 2)
        self.assertTrue(core.verify_readiness(packet))

    def test_duplicate_receipts_are_not_treated_as_two_batches(self):
        for migrations, syncs in (([self.good, copy.deepcopy(self.good)], [sync()]),
                                  ([self.good], [sync(), sync()])):
            with self.subTest(kind="migration" if len(migrations) == 2 else "sync"):
                with self.assertRaisesRegex(core.WorkshareError, "duplicate receipt"):
                    core.compile_readiness(self.evidence, migrations, syncs)

    def test_empty_migration_verifies_but_cannot_supply_positive_migration_evidence(self):
        empty = core.reconcile_migration([], [])
        self.assertTrue(core.verify_migration_receipt(empty))
        self.assertEqual(empty["decision"], "NO_RECORDS_TO_RECONCILE")
        parent = core.compile_readiness(self.evidence, [empty], [sync()])
        self.assertIn("MIGRATION_RECEIPTS_NOT_RECONCILED", parent["hold_reasons"])
        self.assertEqual(parent["state"], "HOLD_WORKSHARE_INCOMPLETE")

    def test_plain_data_contract_rejects_extra_fields_and_duplicate_ids(self):
        for rows in ([record("a"), record("a")],
                     [{**record("a"), "raw_payload": "synthetic payload"}],
                     [{"record_id": "SYN-a", "record_sha256": True}]):
            with self.subTest(rows=rows):
                with self.assertRaises(core.WorkshareError):
                    core.reconcile_migration(rows, [])


class TestIndependentCLI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.source = self.directory / "source.json"
        self.target = self.directory / "target.json"
        self.source.write_text(json.dumps([record("a")]), encoding="utf-8")
        self.target.write_text("[]", encoding="utf-8")

    def run_cli(self, *args, expected=0):
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        result = subprocess.run(PYTHON + ["-m", "revenue.aidt_ewds_workshare", *map(str, args)],
                                cwd=ROOT, env=env, capture_output=True,
                                text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        return result

    def test_valid_hold_has_successful_cli_exit_without_positive_decision(self):
        result = self.run_cli("migration", self.source, self.target)
        packet = json.loads(result.stdout)
        self.assertEqual(packet["decision"], "HOLD_MIGRATION_RECONCILIATION")
        self.assertEqual(packet["missing_record_ids"], ["SYN-a"])
        self.assertIs(packet["external_submission_authorized"], False)

    @unittest.skipUnless(os.name == "posix", "POSIX alias behavior; Windows not validated")
    def test_exact_path_hardlink_and_symlink_cannot_overwrite_input(self):
        original = self.source.read_bytes()
        hardlink = self.directory / "hardlink.json"
        symlink = self.directory / "symlink.json"
        os.link(self.source, hardlink)
        symlink.symlink_to(self.source)
        for alias in (self.source, hardlink, symlink):
            with self.subTest(alias=alias.name):
                self.run_cli("migration", self.source, self.target, "--out", alias, expected=2)
                self.assertEqual(self.source.read_bytes(), original)
                self.assertEqual(alias.read_bytes(), original)

    def test_existing_report_is_preserved_and_new_report_replays(self):
        output = self.directory / "report.json"
        first = self.run_cli("migration", self.source, self.target, "--out", output)
        self.assertEqual(first.stdout, "")
        before = output.read_bytes()
        self.run_cli("migration", self.source, self.target, "--out", output, expected=2)
        self.assertEqual(output.read_bytes(), before)
        verified = json.loads(self.run_cli("verify", output).stdout)
        self.assertEqual(verified["state"], "VERIFIED_INTERNAL_CONSISTENCY")
        self.assertIs(verified["external_source_authenticity_established"], False)

    @unittest.skipUnless(os.name == "posix", "POSIX symlink behavior; Windows not validated")
    def test_dangling_symlink_is_not_followed_to_create_target(self):
        absent = self.directory / "absent.json"
        link = self.directory / "dangling.json"
        link.symlink_to(absent)
        self.run_cli("migration", self.source, self.target, "--out", link, expected=2)
        self.assertFalse(absent.exists())
        self.assertTrue(link.is_symlink())

    def test_bad_json_never_creates_output_and_does_not_replace_prior_report(self):
        output = self.directory / "report.json"
        for payload in (b'{"a":1,"a":2}', b"[NaN]", b"[1.5]", b"\xff", b"[[[["):
            self.source.write_bytes(payload)
            with self.subTest(payload=payload):
                self.run_cli("migration", self.source, self.target, "--out", output, expected=2)
                self.assertFalse(output.exists())
        output.write_bytes(b"PREVIOUS COMPLETE REPORT")
        self.run_cli("migration", self.source, self.target, "--out", output, expected=2)
        self.assertEqual(output.read_bytes(), b"PREVIOUS COMPLETE REPORT")

    def test_cli_generation_pins_are_reported_and_never_become_authenticity(self):
        packet = core.reconcile_migration([record("a")], [record("a")])
        path = self.directory / "receipt.json"
        path.write_text(json.dumps(packet), encoding="utf-8")
        result = self.run_cli("verify", path, "--expected-source-manifest-sha256",
                              packet["source_manifest_sha256"])
        verification = json.loads(result.stdout)
        self.assertIs(verification["independent_source_pin_checked"], True)
        self.assertIs(verification["independent_target_pin_checked"], False)
        self.assertIs(verification["external_source_authenticity_established"], False)
        self.run_cli("verify", path, "--expected-source-manifest-sha256", digest("other"), expected=2)

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux file-size fault injection")
    def test_real_write_failure_does_not_report_success_or_damage_source(self):
        output = self.directory / "limited.json"
        original = self.source.read_bytes()
        code = """import resource, signal, sys
from revenue.aidt_ewds_workshare.__main__ import main
signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
resource.setrlimit(resource.RLIMIT_FSIZE, (32, 32))
raise SystemExit(main(sys.argv[1:]))
"""
        result = subprocess.run(PYTHON + ["-c", code, "migration", str(self.source),
                                str(self.target), "--out", str(output)], cwd=ROOT,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn("File too large", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(self.source.read_bytes(), original)
        # Create-only is not an atomic-install promise. A partial NEW file may
        # remain, but it must not be a complete successful receipt. A future
        # atomic cleanup improvement can remove it without changing this test.
        if output.exists():
            with self.assertRaises(json.JSONDecodeError):
                json.loads(output.read_text(encoding="utf-8"))

    def test_manifest_pin_options_cannot_be_silently_ignored_for_sync(self):
        path = self.directory / "sync.json"
        path.write_text(json.dumps(sync()), encoding="utf-8")
        self.run_cli("verify", path, "--expected-source-manifest-sha256", digest("pin"), expected=2)


if __name__ == "__main__":
    unittest.main()
