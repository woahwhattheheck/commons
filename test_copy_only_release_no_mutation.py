#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parent


def _load(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class CopyOnlyReleaseWholeStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.infinitecal = _load(
            "bd07_infinitecal",
            "revenue/production-lims/infinitecal-crossstate-method-parity/infinitecal_parity.py",
        )
        cls.csu = _load(
            "bd07_csu_malt",
            "revenue/production-lims/csu-malt-method-expansion/csu_malt_expansion.py",
        )
        cls.newbloom = _load(
            "bd07_newbloom",
            "revenue/production-lims/newbloom-multistate-beverage-coa/newbloom_beverage_coa.py",
        )

    def test_infinitecal_release_and_denial_leave_entire_ledger_unchanged(self):
        mod = self.infinitecal
        ledger = mod.Ledger()
        ledger.processed_record_ids.add("R1")
        ledger.accepted_by_accession["A1"] = {"record_id": "R1"}
        ledger.holds["H1"] = {"record_id": "H1", "hold_code": "SYNTHETIC_HOLD"}
        ledger.drafts["R1"] = {
            "record_id": "R1",
            "state": "CA",
            "material_id": "M1",
            "status": mod.STAGED,
            "reviewer": None,
            "result_hash": "result",
            "lineage_hash": "lineage",
        }
        ledger.events.append({"record_id": "R1", "event": "STAGE_DRAFT"})

        before = copy.deepcopy(ledger)
        released = mod.release_draft(ledger, "R1", "Aisha Reviewer")
        self.assertEqual(mod.RELEASED, released["status"])
        self.assertEqual("Aisha Reviewer", released["reviewer"])
        self.assertEqual(before, ledger)

        before_denied = copy.deepcopy(ledger)
        with self.assertRaisesRegex(ValueError, "NAMED_HUMAN_REVIEWER_REQUIRED"):
            mod.release_draft(ledger, "R1", "System Reviewer")
        self.assertEqual(before_denied, ledger)

    def test_csu_release_and_denial_leave_entire_ledger_unchanged(self):
        mod = self.csu
        ledger = mod.Ledger()
        ledger.seen.add("SUB-1")
        ledger.seen_payloads["SUB-1"] = "payload"
        ledger.accessions["S1"] = {"sample_id": "S1"}
        ledger.jobs["S1:J1"] = {"job_id": "S1:J1", "sample_id": "S1"}
        ledger.reports["S1"] = {
            "sample_id": "S1",
            "status": mod.STAGED,
            "reviewer": None,
            "expansion_hash": "expansion",
        }
        ledger.holds["SUB-H"] = {"sample_id": "H1", "hold_code": mod.UNSUP}
        ledger.events.append(("SUB-1", "STAGE_REPORT", mod.STAGED))

        before = copy.deepcopy(ledger)
        released = mod.release(ledger, "S1", "Jordan Smith")
        self.assertEqual(mod.RELEASED, released["status"])
        self.assertEqual("Jordan Smith", released["reviewer"])
        self.assertEqual(before, ledger)

        before_denied = copy.deepcopy(ledger)
        with self.assertRaisesRegex(ValueError, "NAMED_HUMAN_REVIEWER_REQUIRED"):
            mod.release(ledger, "S1", "bot123 reviewer")
        self.assertEqual(before_denied, ledger)

    def test_newbloom_release_denials_and_auto_release_leave_whole_shadow_unchanged(self):
        mod = self.newbloom
        shadow = mod.NewBloomBeverageCoAShadow({"mode": "synthetic-read-only", "records": 3})
        shadow.staged_packets["R1"] = {
            "record_id": "R1",
            "batch_id": "B1",
            "state": "STAGED_HUMAN_REVIEW",
            "source_result_sha256": "source",
            "result_schema_sha256": "schema",
            "drafts": [
                {
                    "state_pack": "CA-SYN",
                    "state": "STAGED_HUMAN_REVIEW",
                    "released_by": None,
                    "approval_id": None,
                    "sent": False,
                },
                {
                    "state_pack": "CO-SYN",
                    "state": "STAGED_HUMAN_REVIEW",
                    "released_by": None,
                    "approval_id": None,
                    "sent": False,
                },
            ],
            "released_by": None,
            "approval_id": None,
            "sent": False,
        }
        shadow.holds["H1"] = {"record_id": "H1", "hold_code": "SYNTHETIC_HOLD"}
        shadow.events.append({"record_id": "R1", "status": "STAGED_HUMAN_REVIEW"})
        shadow._seen_records.update({"R1", "H1"})
        shadow._seen_batch_ids.add("B1")

        before = copy.deepcopy(shadow.__dict__)
        released = shadow.release_packet("R1", "Jordan Reviewer", "APR-SYN-0001")
        self.assertEqual("RELEASED_BY_NAMED_HUMAN", released["state"])
        self.assertEqual("Jordan Reviewer", released["released_by"])
        self.assertEqual("APR-SYN-0001", released["approval_id"])
        self.assertTrue(all(draft["state"] == "RELEASED_BY_NAMED_HUMAN" for draft in released["drafts"]))
        self.assertEqual(before, shadow.__dict__)

        for bad_name, approval in (
            ("System Reviewer", "APR-SYN-0001"),
            ("Jordan Reviewer", "not-an-approval"),
        ):
            with self.subTest(bad_name=bad_name, approval=approval):
                before_denied = copy.deepcopy(shadow.__dict__)
                with self.assertRaises(PermissionError):
                    shadow.release_packet("R1", bad_name, approval)
                self.assertEqual(before_denied, shadow.__dict__)

        before_auto = copy.deepcopy(shadow.__dict__)
        with self.assertRaises(PermissionError):
            shadow.automatic_release("R1")
        self.assertEqual(before_auto, shadow.__dict__)


if __name__ == "__main__":
    unittest.main()
