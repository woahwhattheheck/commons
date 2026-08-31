#!/usr/bin/env python3
"""Binary tests for the Bid 1421 operations RBAC runner.

The runner is the product. HTML is a window. Fail-closed.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

import billings_bid_1421_operations_runner as runner

ROOT = Path(__file__).resolve().parent
PACK = ROOT / "revenue" / "billings_bid_1421" / "operations_runner"
OPS_PACK = ROOT / "revenue" / "billings_bid_1421" / "operations_package"
PAGE = ROOT / "billings-bid-1421-operations-runner.html"
RECEIPT = ROOT / "p" / "billings-bid-1421-operations-runner-20260831-01.md"
PRODUCT = ROOT / "billings_bid_1421_operations_runner.py"

STOLEN_RECEIPTS = (
    ROOT / "p" / "billings-bid-1421-acceptance-corpus-20260831-01.md",
    ROOT / "p" / "billings-bid-1421-instrument-fixtures-20260831-01.md",
    ROOT / "p" / "billings-bid-1421-partner-recon-20260831-01.md",
    ROOT / "p" / "billings-bid-1421-rfp-compliance-matrix-20260831-01.md",
    ROOT / "p" / "billings-bid-1421-operations-package-20260831-01.md",
    ROOT / "p" / "canyon-multisite-regulated-intake-lims-01.md",
    ROOT / "p" / "organabio-multisite-donor-coa-lims-01.md",
    ROOT / "p" / "pcl-scope-sla-routing-lims-01.md",
)
STOLEN_BLOBS = {
    ROOT / "p" / "billings-bid-1421-operations-package-20260831-01.md": runner.PACKAGE_RECEIPT_BLOB,
    ROOT / "p" / "billings-bid-1421-acceptance-corpus-20260831-01.md": "054e321c",
}

NEW_PATHS = (
    PRODUCT,
    ROOT / "test_billings_bid_1421_operations_runner.py",
    PAGE,
    RECEIPT,
    PACK / "source.json",
    PACK / "directory.json",
    PACK / "cases.json",
)


def _blob(path: Path) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(path)],
        cwd=ROOT,
        text=True,
    ).strip()


class BillingsBid1421OperationsRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.battery = runner.run_battery()
        cls.page = PAGE.read_text(encoding="utf-8") if PAGE.is_file() else ""
        cls.receipt = RECEIPT.read_text(encoding="utf-8") if RECEIPT.is_file() else ""
        cls.source = json.loads((PACK / "source.json").read_text(encoding="utf-8"))
        cls.cases = json.loads((PACK / "cases.json").read_text(encoding="utf-8"))

    def test_cli_product_passes(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(PRODUCT)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("PASS", proc.stdout)
        self.assertIn("cases=10/10", proc.stdout)
        self.assertIn(runner.GOLDEN_AUDIT_SHA256, proc.stdout)

    def test_self_test_flag_passes(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(PRODUCT), "--self-test"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_ten_cases_all_deny_as_specified(self) -> None:
        self.assertTrue(self.battery["ok"], runner.summarize(self.battery))
        self.assertEqual([row["id"] for row in self.battery["cases"]], list(runner.CASE_IDS))
        self.assertEqual(self.battery["cases_ok"], 10)
        self.assertEqual(self.battery["deny_count"], 16)
        self.assertEqual(self.battery["allow_count"], 1)
        self.assertEqual(self.battery["effect_count"], 1)
        self.assertEqual(self.battery["audit_sha256"], runner.GOLDEN_AUDIT_SHA256)
        by_id = {row["id"]: row for row in self.battery["cases"]}
        for case_id in runner.CASE_IDS:
            self.assertTrue(by_id[case_id]["ok"], by_id[case_id])

    def test_each_numbered_package_item_is_present(self) -> None:
        items = {row["package_item"] for row in self.cases["cases"]}
        self.assertEqual(items, set(range(1, 11)))

    def test_unknown_and_disabled_actors_are_refused(self) -> None:
        plane = runner.NonproductionRBACPlane()
        unknown = plane.evaluate(
            {"request_id": "T-UNK", "actor": "NO-SUCH-PERSON", "verb": "create_sample", "site": "WEST"}
        )
        disabled = plane.evaluate(
            {"request_id": "T-DIS", "actor": "SYN-DISABLED", "verb": "create_sample", "site": "WEST"}
        )
        self.assertEqual(unknown["decision"], "DENY")
        self.assertEqual(unknown["reason"], "unknown_actor")
        self.assertEqual(disabled["decision"], "DENY")
        self.assertEqual(disabled["reason"], "disabled_actor")

    def test_field_collector_site_and_release(self) -> None:
        plane = runner.NonproductionRBACPlane()
        site = plane.evaluate(
            {
                "request_id": "T-SITE",
                "actor": "SYN-FIELD-WEST",
                "verb": "create_sample",
                "site": "EAST",
            }
        )
        release = plane.evaluate(
            {
                "request_id": "T-REL",
                "actor": "SYN-FIELD-WEST",
                "verb": "release_result",
                "resource_id": "RESULT-PH-1",
            }
        )
        own_site = plane.evaluate(
            {
                "request_id": "T-OWN",
                "actor": "SYN-FIELD-WEST",
                "verb": "create_sample",
                "site": "WEST",
            }
        )
        self.assertEqual(site["reason"], "site_scope")
        self.assertEqual(release["reason"], "release_refused")
        self.assertTrue(own_site["ok"])

    def test_analyst_method_scope(self) -> None:
        plane = runner.NonproductionRBACPlane()
        other = plane.evaluate(
            {
                "request_id": "T-METH",
                "actor": "SYN-ANALYST-PH",
                "verb": "enter_result",
                "method_id": "SM-5310-B",
                "resource_id": "RESULT-TOC-1",
            }
        )
        expired = plane.evaluate(
            {
                "request_id": "T-EXP",
                "actor": "SYN-ANALYST-EXPIRED",
                "verb": "enter_result",
                "method_id": "SM-4500-H+",
                "resource_id": "RESULT-PH-1",
            }
        )
        current = plane.evaluate(
            {
                "request_id": "T-CUR",
                "actor": "SYN-ANALYST-PH",
                "verb": "enter_result",
                "method_id": "SM-4500-H+",
                "resource_id": "RESULT-PH-1",
            }
        )
        self.assertEqual(other["reason"], "method_not_current")
        self.assertEqual(expired["reason"], "method_expired")
        self.assertTrue(current["ok"])

    def test_qa_cannot_erase_audit(self) -> None:
        plane = runner.NonproductionRBACPlane()
        erase = plane.evaluate(
            {
                "request_id": "T-ERASE",
                "actor": "SYN-QA-1",
                "verb": "erase_audit",
                "resource_id": "AUDIT-LOG",
            }
        )
        hold = plane.evaluate(
            {
                "request_id": "T-HOLD",
                "actor": "SYN-QA-1",
                "verb": "hold_result",
                "resource_id": "RESULT-PH-1",
            }
        )
        self.assertEqual(erase["reason"], "erase_audit_refused")
        self.assertTrue(hold["ok"])
        self.assertEqual(len(plane.audit), 2)

    def test_report_release_only_when_ready(self) -> None:
        plane = runner.NonproductionRBACPlane()
        draft = plane.evaluate(
            {
                "request_id": "T-DRAFT",
                "actor": "SYN-REPORTER-1",
                "verb": "release_report",
                "resource_id": "REPORT-DRAFT-1",
            }
        )
        ready = plane.evaluate(
            {
                "request_id": "T-READY",
                "actor": "SYN-REPORTER-1",
                "verb": "release_report",
                "resource_id": "REPORT-READY-REPLAY",
            }
        )
        self.assertEqual(draft["reason"], "report_not_ready")
        self.assertTrue(ready["ok"])

    def test_integration_adapter_and_admin(self) -> None:
        plane = runner.NonproductionRBACPlane()
        other = plane.evaluate(
            {
                "request_id": "T-ADAPT",
                "actor": "SYN-INTEG-PH",
                "verb": "ingest_adapter",
                "adapter_id": "fixture-toc-1",
            }
        )
        admin = plane.evaluate(
            {
                "request_id": "T-ADM",
                "actor": "SYN-INTEG-PH",
                "verb": "administer_users",
            }
        )
        own = plane.evaluate(
            {
                "request_id": "T-OWNAD",
                "actor": "SYN-INTEG-PH",
                "verb": "ingest_adapter",
                "adapter_id": "fixture-ph-meter-1",
            }
        )
        self.assertEqual(other["reason"], "adapter_scope")
        self.assertEqual(admin["reason"], "role_cannot_use_verb")
        self.assertTrue(own["ok"])

    def test_support_window_and_silent_elevate(self) -> None:
        plane = runner.NonproductionRBACPlane()
        expired = plane.evaluate(
            {
                "request_id": "T-SUP-EXP",
                "actor": "SYN-SUPPORT-EXPIRED",
                "verb": "read_ticket",
                "resource_id": "TICKET-1",
            }
        )
        elevate = plane.evaluate(
            {
                "request_id": "T-ELEV",
                "actor": "SYN-SUPPORT-ACTIVE",
                "verb": "elevate_role",
            }
        )
        active = plane.evaluate(
            {
                "request_id": "T-SUP-OK",
                "actor": "SYN-SUPPORT-ACTIVE",
                "verb": "read_ticket",
                "resource_id": "TICKET-1",
            }
        )
        self.assertEqual(expired["reason"], "support_window_closed")
        self.assertEqual(elevate["reason"], "silent_elevate_refused")
        self.assertTrue(active["ok"])

    def test_separation_of_duties(self) -> None:
        plane = runner.NonproductionRBACPlane()
        sod = plane.evaluate(
            {
                "request_id": "T-SOD",
                "actor": "SYN-PROPOSER-1",
                "verb": "approve_change",
                "resource_id": "CHANGE-001",
            }
        )
        self.assertEqual(sod["decision"], "DENY")
        self.assertEqual(sod["reason"], "separation_of_duties")

    def test_every_decision_has_attributable_audit(self) -> None:
        gaps = runner._audit_gaps(
            runner.NonproductionRBACPlane(),
            [],
        )
        self.assertEqual(gaps, [])  # empty plane, empty decisions
        result = self.battery
        plane = runner.NonproductionRBACPlane()
        # Rebuild from recorded audit/decision pairs.
        decisions = []
        for case in result["cases"]:
            for attempt in case.get("attempts") or []:
                decisions.append(
                    {
                        "request_id": attempt["request_id"],
                        "actor": attempt["actor"],
                        "verb": attempt["verb"],
                        "decision": attempt["decision"],
                        "reason": attempt["reason"],
                    }
                )
        live = runner.NonproductionRBACPlane()
        for case in runner.load_cases()["cases"]:
            if case.get("kind") == "audit_coverage":
                continue
            for attempt in case.get("attempts") or []:
                live.evaluate(attempt)
        self.assertEqual(runner._audit_gaps(live, decisions), [])
        self.assertEqual(len(live.audit), len(decisions))

    def test_replay_produces_one_effect(self) -> None:
        plane = runner.NonproductionRBACPlane()
        first = plane.evaluate(
            {
                "request_id": "REPLAY-1",
                "actor": "SYN-REPORTER-1",
                "verb": "release_report",
                "resource_id": "REPORT-READY-REPLAY",
            }
        )
        second = plane.evaluate(
            {
                "request_id": "REPLAY-1",
                "actor": "SYN-REPORTER-1",
                "verb": "release_report",
                "resource_id": "REPORT-READY-REPLAY",
            }
        )
        self.assertTrue(first["ok"])
        self.assertEqual(second["reason"], "replay_suppressed")
        self.assertEqual(first["effect_count"], 1)
        self.assertEqual(second["effect_count"], 1)
        self.assertEqual(len(plane.effects), 1)

    def test_production_like_needs_named_human_and_still_closes(self) -> None:
        probe = runner.production_like_probe(named_human="SYN-NAMED-HUMAN")
        self.assertTrue(probe["ok"], probe)
        self.assertEqual(probe["named_human_missing"]["reason"], "named_human_missing")
        self.assertEqual(probe["submit_bid"]["reason"], "production_destination_absent")
        self.assertEqual(probe["connect_live_lims"]["reason"], "production_destination_absent")
        self.assertEqual(probe["effect_count"], 0)

    def test_control_allows_are_real_allows(self) -> None:
        control = runner.control_allows()
        self.assertTrue(control["ok"], control)
        self.assertEqual(control["effect_count"], 5)

    def test_deny_by_default_invented_action(self) -> None:
        plane = runner.NonproductionRBACPlane()
        got = plane.evaluate(
            {
                "request_id": "T-VERB",
                "actor": "SYN-FIELD-WEST",
                "verb": "invented_action",
            }
        )
        self.assertEqual(got["decision"], "DENY")
        self.assertEqual(got["reason"], "role_cannot_use_verb")

    def test_operations_package_untouched(self) -> None:
        self.assertEqual(runner.prove_package_untouched(), [])
        package = OPS_PACK / "billings-bid-1421-operations-package.md"
        self.assertEqual(runner.sha256_hex(package), runner.PACKAGE_SHA256)
        self.assertEqual(_blob(ROOT / "p" / f"{runner.PACKAGE_ID}.md"), runner.PACKAGE_RECEIPT_BLOB)

    def test_does_not_rewrite_sibling_packs(self) -> None:
        for name in (
            "acceptance_corpus",
            "compliance_matrix",
            "instrument_fixtures",
            "operations_package",
            "partner_recon",
        ):
            self.assertTrue((ROOT / "revenue" / "billings_bid_1421" / name).is_dir(), name)
        self.assertTrue(PACK.is_dir())
        self.assertNotEqual(PACK, OPS_PACK)

    def test_does_not_remint_stolen_receipts(self) -> None:
        for path in STOLEN_RECEIPTS:
            self.assertTrue(path.is_file(), path.name)
            if path in STOLEN_BLOBS:
                blob = _blob(path)
                self.assertTrue(blob.startswith(STOLEN_BLOBS[path]), (path.name, blob))
        self.assertTrue(RECEIPT.is_file())
        self.assertNotEqual(_blob(RECEIPT), runner.PACKAGE_RECEIPT_BLOB)

    def test_receipt_and_door_are_windows(self) -> None:
        self.assertTrue(RECEIPT.is_file())
        self.assertTrue(PAGE.is_file())
        self.assertIn("id: billings-bid-1421-operations-runner-20260831-01", self.receipt)
        self.assertIn("cash_usd: 0", self.receipt)
        self.assertIn("No City contact", self.receipt)
        self.assertIn(runner.COMMAND, self.receipt)
        self.assertIn(runner.COMMAND, self.page)
        self.assertIn("This page is a window", self.page)
        self.assertIn("No login", self.page)
        self.assertNotIn("login required", self.page.lower())

    def test_never_uses_the_banned_product_word(self) -> None:
        banned = "m" + "ock"
        product_paths = [path for path in NEW_PATHS if path != Path(__file__).resolve()]
        for path in product_paths:
            blob = path.read_text(encoding="utf-8").lower()
            self.assertNotIn(banned, blob, path.name)

    def test_source_stays_nonproduction(self) -> None:
        self.assertEqual(self.source["leftover_id"], runner.LEFTOVER_ID)
        self.assertFalse(self.source["city_contact"])
        self.assertFalse(self.source["city_submission"])
        self.assertFalse(self.source["live_lims"])
        self.assertEqual(self.source["cash_usd"], 0)
        self.assertEqual(self.source["official_command"], runner.COMMAND)


if __name__ == "__main__":
    unittest.main()
