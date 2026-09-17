import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from revenue.real_remax_transaction_cutover import CutoverError, canonical_bytes, compile_cutover, digest, verify_report
from revenue.real_remax_transaction_cutover.cli import load_strict_json, write_exclusive
from revenue.real_remax_transaction_cutover.synthetic_fixture import build_synthetic_bundle


class RealRemaxCutoverTest(unittest.TestCase):
    def setUp(self):
        self.source, self.target, self.mapping, self.policy = build_synthetic_bundle(240)

    def compile(self):
        return compile_cutover(self.source, self.target, self.mapping, self.policy)

    def test_240_transaction_acceptance_and_verify(self):
        report = self.compile()
        self.assertEqual("PARITY", report["decision"])
        self.assertEqual(240, report["summary"]["active_source_transactions"])
        self.assertEqual(240, report["summary"]["parity_transactions"])
        self.assertEqual(0, report["summary"]["finding_count"])
        self.assertTrue(verify_report(self.source, self.target, self.mapping, self.policy, report))
        self.assertFalse(report["authority"]["production_mutation_authorized"])
        self.assertFalse(report["authority"]["buyer_acceptance_proven"])
        self.assertFalse(report["authority"]["payment_proven"])
        self.assertFalse(report["authority"]["revenue_proven"])

    def test_order_invariance(self):
        expected = self.compile()
        self.source["offices"].reverse()
        self.target["offices"].reverse()
        self.mapping["offices"].reverse()
        self.source["transactions"].reverse()
        self.target["transactions"].reverse()
        self.mapping["transactions"].reverse()
        self.source["agents"].reverse()
        self.target["agents"].reverse()
        self.mapping["agents"].reverse()
        self.policy["active_source_stages"].reverse()
        self.policy["required_relationship_roles"].reverse()
        for txn in self.source["transactions"]:
            txn["relationships"].reverse()
        for txn in self.target["transactions"]:
            txn["relationships"].reverse()
        actual = self.compile()
        self.assertEqual(expected, actual)

    def test_stage_and_status_drift_hold(self):
        self.target["transactions"][0]["stage"] = "UNDER_CONTRACT"
        self.target["transactions"][1]["status"] = "HOLD"
        report = self.compile()
        codes = {f["code"] for f in report["findings"]}
        self.assertIn("STAGE_MISMATCH", codes)
        self.assertIn("STATUS_MISMATCH", codes)
        self.assertEqual("HOLD", report["decision"])

    def test_exact_cent_and_relationship_drift_hold(self):
        txn = self.target["transactions"][0]
        txn["gross_commission_cents"] += 1
        txn["relationships"][0]["commission_cents"] += 1
        report = self.compile()
        codes = {f["code"] for f in report["findings"]}
        self.assertIn("GROSS_COMMISSION_MISMATCH", codes)
        self.assertIn("RELATIONSHIP_MISMATCH", codes)

    def test_invalid_internal_split_rejected(self):
        self.target["transactions"][0]["relationships"][0]["split_bps"] = 4999
        with self.assertRaisesRegex(CutoverError, "split_bps do not sum"):
            self.compile()

    def test_missing_transaction_mapping_hold(self):
        self.mapping["transactions"].pop()
        report = self.compile()
        self.assertIn("TRANSACTION_MAP_MISSING", {f["code"] for f in report["findings"]})

    def test_ambiguous_target_mapping_rejected(self):
        self.mapping["transactions"][1]["target_transaction_id"] = self.mapping["transactions"][0]["target_transaction_id"]
        with self.assertRaisesRegex(CutoverError, "multiple sources"):
            self.compile()

    def test_orphan_mapping_rows_rejected(self):
        self.mapping["transactions"].append({"source_transaction_id": "STX99999", "target_transaction_id": "TTX99999"})
        with self.assertRaisesRegex(CutoverError, "transaction source does not exist"):
            self.compile()
        self.source, self.target, self.mapping, self.policy = build_synthetic_bundle(240)
        self.mapping["agents"][0]["target_agent_id"] = "TA999"
        with self.assertRaisesRegex(CutoverError, "agent target does not exist"):
            self.compile()

    def test_duplicate_snapshot_identity_rejected(self):
        self.source["agents"][1]["agent_id"] = self.source["agents"][0]["agent_id"]
        with self.assertRaisesRegex(CutoverError, "duplicate source_snapshot.agent"):
            self.compile()

    def test_mapped_agent_wrong_office_hold(self):
        self.target["agents"][0]["office_id"] = "TO04"
        report = self.compile()
        codes = {f["code"] for f in report["findings"]}
        self.assertIn("AGENT_OFFICE_MISMATCH", codes)
        self.assertIn("RELATIONSHIP_AGENT_OFFICE_MISMATCH", codes)
        self.assertLess(report["summary"]["parity_transactions"], 240)

    def test_findings_ceiling_raises_cutover_error(self):
        self.target["transactions"][0]["stage"] = "UNDER_CONTRACT"
        with mock.patch("revenue.real_remax_transaction_cutover.engine.MAX_FINDINGS", 0):
            with self.assertRaisesRegex(CutoverError, "more than 0 findings"):
                self.compile()

    def test_receipt_tamper_and_reseal_do_not_verify(self):
        report = self.compile()
        forged = copy.deepcopy(report)
        forged["decision"] = "HOLD"
        unsigned = dict(forged)
        unsigned.pop("receipt_sha256")
        forged["receipt_sha256"] = digest(unsigned)
        self.assertFalse(verify_report(self.source, self.target, self.mapping, self.policy, forged))

    def test_source_generation_drift_invalidates_old_report(self):
        report = self.compile()
        self.source["generation"] += 1
        self.assertFalse(verify_report(self.source, self.target, self.mapping, self.policy, report))

    def test_bool_is_not_integer(self):
        self.source["generation"] = True
        with self.assertRaisesRegex(CutoverError, "must be an integer"):
            self.compile()

    def test_strict_json_duplicate_and_nonfinite_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            dup = Path(td) / "dup.json"
            dup.write_bytes(b'{"a":1,"a":2}')
            with self.assertRaisesRegex(CutoverError, "duplicate JSON key"):
                load_strict_json(str(dup))
            nan = Path(td) / "nan.json"
            nan.write_bytes(b'{"a":NaN}')
            with self.assertRaisesRegex(CutoverError, "non-finite"):
                load_strict_json(str(nan))

    def test_strict_json_requires_canonical_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "pretty.json"
            path.write_text('{"b": 2, "a": 1}\n', encoding="utf-8")
            with self.assertRaisesRegex(CutoverError, "not canonical JSON"):
                load_strict_json(str(path))

    def test_exclusive_publication_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "report.json"
            write_exclusive(str(path), {"a": 1})
            with self.assertRaisesRegex(CutoverError, "refusing non-exclusive output"):
                write_exclusive(str(path), {"a": 2})
            self.assertEqual(b'{"a":1}', path.read_bytes())

    def test_foreign_successor_swap_fails_and_preserves_foreign_file(self):
        if os.name == "nt":
            self.skipTest("Windows normally denies renaming an open output; POSIX hostile covers successor swap")
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "report.json"
            displaced = Path(td) / "owned-displaced.json"
            real_fsync = os.fsync
            swapped = False

            def swap_after_durability(fd):
                nonlocal swapped
                real_fsync(fd)
                if not swapped and path.exists():
                    swapped = True
                    os.replace(path, displaced)
                    path.write_bytes(b"FOREIGN")

            with mock.patch("revenue.real_remax_transaction_cutover.cli.os.fsync", side_effect=swap_after_durability):
                with self.assertRaisesRegex(CutoverError, "visible output generation changed"):
                    write_exclusive(str(path), {"a": 1})
            self.assertEqual(b"FOREIGN", path.read_bytes())
            self.assertTrue(displaced.exists())
            self.assertEqual(b"", displaced.read_bytes())

    def test_direct_object_aggregate_bound(self):
        source, target, mapping, policy = build_synthetic_bundle(1)
        with mock.patch("revenue.real_remax_transaction_cutover.schema.MAX_ITEMS", 35):
            with self.assertRaisesRegex(CutoverError, "aggregate 35 row limit"):
                compile_cutover(source, target, mapping, policy)

        source, target, mapping, policy = build_synthetic_bundle(3)
        with mock.patch("revenue.real_remax_transaction_cutover.schema.MAX_ITEMS", 40):
            with self.assertRaisesRegex(CutoverError, "aggregate 40 row limit"):
                compile_cutover(source, target, mapping, policy)

    def test_failed_publication_keeps_owned_zero_byte_tombstone(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "report.json"
            with mock.patch("revenue.real_remax_transaction_cutover.cli.os.write", side_effect=OSError("boom")):
                with self.assertRaisesRegex(OSError, "boom"):
                    write_exclusive(str(path), {"a": 1})
            self.assertTrue(path.exists())
            self.assertEqual(b"", path.read_bytes())

    def test_strict_json_deep_recursion_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "deep.json"
            path.write_bytes(("[" * 4000 + "0" + "]" * 4000).encode("ascii"))
            with self.assertRaisesRegex(CutoverError, "maximum depth"):
                load_strict_json(str(path))

    def test_cli_compile_verify_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name, value in (
                ("source.json", self.source),
                ("target.json", self.target),
                ("map.json", self.mapping),
                ("policy.json", self.policy),
            ):
                (root / name).write_bytes(canonical_bytes(value))
            report_path = root / "report.json"
            env = dict(os.environ)
            env["PYTHONPATH"] = os.getcwd()
            compile_proc = subprocess.run(
                [sys.executable, "-m", "revenue.real_remax_transaction_cutover.cli", "compile", "--source", str(root / "source.json"), "--target", str(root / "target.json"), "--identity-map", str(root / "map.json"), "--policy", str(root / "policy.json"), "--output", str(report_path)],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(0, compile_proc.returncode, compile_proc.stderr + compile_proc.stdout)
            verify_proc = subprocess.run(
                [sys.executable, "-m", "revenue.real_remax_transaction_cutover.cli", "verify", "--source", str(root / "source.json"), "--target", str(root / "target.json"), "--identity-map", str(root / "map.json"), "--policy", str(root / "policy.json"), "--report", str(report_path)],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(0, verify_proc.returncode, verify_proc.stderr + verify_proc.stdout)
            self.assertIn("VERIFIED", verify_proc.stdout)


if __name__ == "__main__":
    unittest.main()
