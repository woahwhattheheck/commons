#!/usr/bin/env python3
"""Binary tests for the AquaTrace Lane F release-readiness runner.

The runner is the product. HTML is a window. Fail-closed.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

import aquatrace_work_order_f_release_readiness as runner

ROOT = Path(__file__).resolve().parent
PACK = ROOT / "revenue" / "aquatrace_work_order_f_release_readiness"
PAGE = ROOT / "aquatrace-work-order-f-release-readiness.html"
RECEIPT = ROOT / "p" / "aquatrace-work-order-f-release-readiness-20260831-01.md"
REGISTRY = ROOT / "features" / "registry" / "aquatrace-work-order-f-release-readiness-20260831-01.json"
PRODUCT = ROOT / "aquatrace_work_order_f_release_readiness.py"

OFF_LIMIT_PATHS = (
    ROOT / "p" / "aquatrace-work-order-a-architecture-acceptance-20260831-01.md",
    ROOT / "p" / "aquatrace-work-order-b-production-foundation-20260831-01.md",
    ROOT / "p" / "aquatrace-work-order-c-reporting-offline-20260831-01.md",
    ROOT / "p" / "aquatrace-work-order-d-municipal-ux-package-20260831-01.md",
    ROOT / "p" / "aquatrace-work-order-c-field-mobility-20260831-01.md",
    ROOT / "p" / "sanair-asbestos-coc-router-lims-01.md",
    ROOT / "p" / "westpak-scope-capacity-routing-lims-01.md",
    ROOT / "p" / "ddl-crosssite-method-proficiency-lims-01.md",
    ROOT / "p" / "wadsworth-five-site-consolidation-lims-01.md",
    ROOT / "p" / "highpower-ssf-receiving-gate-lims-01.md",
    ROOT / "p" / "sharp-rtu-vial-isolator-lineage-lims-01.md",
    ROOT / "p" / "pcl-scope-sla-routing-lims-01.md",
    ROOT / "p" / "canyon-multisite-regulated-intake-lims-01.md",
    ROOT / "p" / "billings-bid-1421-acceptance-runner-20260831-01.md",
    ROOT / "humans.html",
)

NEW_PATHS = (
    PRODUCT,
    ROOT / "test_aquatrace_work_order_f_release_readiness.py",
    PAGE,
    RECEIPT,
    REGISTRY,
    PACK / "source.json",
    PACK / "gates.json",
    PACK / "default_pointers.json",
    PACK / "contract.json",
    PACK / "README.md",
)


def _blob(path: Path) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(path)],
        cwd=ROOT,
        text=True,
    ).strip()


class AquaTraceWorkOrderFReleaseReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.battery = runner.run_battery()
        cls.default = runner.run_default()
        cls.page = PAGE.read_text(encoding="utf-8") if PAGE.is_file() else ""
        cls.receipt = RECEIPT.read_text(encoding="utf-8") if RECEIPT.is_file() else ""
        cls.source = json.loads((PACK / "source.json").read_text(encoding="utf-8"))

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
        self.assertIn("cases=11/11", proc.stdout)
        self.assertIn("NOT_READY", proc.stdout)
        self.assertIn(runner.GOLDEN_AUDIT_SHA256, proc.stdout)
        self.assertIn(runner.PRIVATE_CITE_SHA, proc.stdout)

    def test_self_test_flag_passes(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(PRODUCT), "--self-test"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_battery_is_deterministic(self) -> None:
        self.assertTrue(self.battery["ok"], runner.summarize(self.battery))
        self.assertEqual(self.battery["case_count"], 11)
        self.assertEqual(self.battery["cases_ok"], 11)
        self.assertEqual(self.battery["product_state"], "NOT_READY")
        self.assertEqual(self.battery["default_ready_count"], 0)
        self.assertEqual(self.battery["default_not_ready_count"], 8)
        self.assertEqual(self.battery["complete_ready_count"], 8)
        self.assertEqual(self.battery["release_count"], 1)
        self.assertEqual(self.battery["audit_sha256"], runner.GOLDEN_AUDIT_SHA256)

    def test_every_named_gate_is_present(self) -> None:
        self.assertEqual(list(self.default["not_ready"]), list(runner.GATE_IDS))
        self.assertEqual(
            [row["gate"] for row in self.default["gates"]],
            list(runner.GATE_IDS),
        )
        for row in self.default["gates"]:
            self.assertEqual(row["state"], "NOT_READY", row)
            self.assertEqual(row["reason"], "cite_only_not_local_bytes", row)

    def test_private_cite_does_not_promote(self) -> None:
        self.assertEqual(self.source["private_cite_sha"], runner.PRIVATE_CITE_SHA)
        self.assertEqual(self.source["private_cite_path"], runner.PRIVATE_CITE_PATH)
        self.assertFalse(self.source["private_repo_cloned"])
        self.assertFalse(self.default["invented_certification"])
        self.assertFalse(self.default["production_ready"])
        self.assertFalse(self.default["deployed"])
        self.assertFalse(self.default["submitted"])
        self.assertFalse(self.default["buyer_accepted"])

    def test_complete_synthetic_is_ready_without_inventing_labels(self) -> None:
        complete = self.battery["complete"]
        self.assertEqual(complete["product_state"], "GATES_SATISFIED")
        self.assertEqual(complete["ready"], list(runner.GATE_IDS))
        self.assertFalse(complete["production_ready"])
        self.assertFalse(complete["buyer_accepted"])
        self.assertFalse(complete["deployed"])
        self.assertFalse(complete["submitted"])

    def test_system_unnamed_held_denied(self) -> None:
        plane = runner.ReleaseReadinessPlane()
        pointers = runner.build_complete_pointers()
        system = plane.evaluate_release(
            {"request_id": "T-SYS", "named_human": "SYSTEM", "pointers": pointers}
        )
        unnamed = plane.evaluate_release(
            {"request_id": "T-NONE", "named_human": "", "pointers": pointers}
        )
        held = plane.evaluate_release(
            {"request_id": "T-HELD", "named_human": "HELD", "pointers": pointers}
        )
        machine = plane.evaluate_release(
            {"request_id": "T-MAC", "named_human": "MACHINE", "pointers": pointers}
        )
        self.assertEqual(system["reason"], "autonomous_release_denied")
        self.assertEqual(unnamed["reason"], "named_human_missing")
        self.assertEqual(held["reason"], "held_release_denied")
        self.assertEqual(machine["reason"], "autonomous_release_denied")
        self.assertEqual(len(plane.records), 0)

    def test_named_human_release_and_replay(self) -> None:
        plane = runner.ReleaseReadinessPlane()
        pointers = runner.build_complete_pointers()
        first = plane.evaluate_release(
            {
                "request_id": "T-REL",
                "named_human": runner.HUMAN_APPROVER,
                "pointers": pointers,
            }
        )
        second = plane.evaluate_release(
            {
                "request_id": "T-REL",
                "named_human": runner.HUMAN_APPROVER,
                "pointers": pointers,
            }
        )
        self.assertTrue(first["ok"])
        self.assertEqual(first["effect"]["state"], "RELEASE_RECORDED")
        self.assertFalse(first["effect"]["production_ready"])
        self.assertEqual(second["reason"], "replay_suppressed")
        self.assertEqual(len(plane.records), 1)

    def test_hold_on_default_even_with_named_human(self) -> None:
        plane = runner.ReleaseReadinessPlane()
        got = plane.evaluate_release(
            {
                "request_id": "T-EARLY",
                "named_human": runner.HUMAN_APPROVER,
                "pointers": runner.load_default_pointers(),
            }
        )
        self.assertEqual(got["decision"], "DENY")
        self.assertEqual(got["reason"], "gates_not_ready")
        self.assertEqual(len(plane.records), 0)

    def test_forbidden_labels_fail_closed(self) -> None:
        plane = runner.ReleaseReadinessPlane()
        digest = runner.sha256_hex(ROOT / runner.evidence_relpath("security"))
        for label in (
            "CERTIFIED",
            "PRODUCTION_READY",
            "DEPLOYED",
            "SUBMITTED",
            "BUYER_ACCEPTED",
        ):
            got = plane.evaluate_pointer(
                {
                    "gate": "security",
                    "kind": "LOCAL_SHA256",
                    "label": label,
                    "path": runner.evidence_relpath("security"),
                    "recorded_by": runner.HUMAN_APPROVER,
                    "sha": digest,
                    "source": "commons-synthetic",
                }
            )
            self.assertEqual(got["state"], "NOT_READY", label)
            self.assertEqual(got["reason"], "forbidden_label", label)

    def test_hash_mismatch_and_missing_file_fail_closed(self) -> None:
        plane = runner.ReleaseReadinessPlane()
        mismatch = plane.evaluate_pointer(
            {
                "gate": "demo",
                "kind": "LOCAL_SHA256",
                "label": "MEASURED",
                "path": runner.evidence_relpath("demo"),
                "recorded_by": runner.HUMAN_APPROVER,
                "sha": "0" * 64,
                "source": "commons-synthetic",
            }
        )
        missing = plane.evaluate_pointer(
            {
                "gate": "demo",
                "kind": "LOCAL_SHA256",
                "label": "MEASURED",
                "path": "revenue/aquatrace_work_order_f_release_readiness/evidence/nope.json",
                "recorded_by": runner.HUMAN_APPROVER,
                "sha": "a" * 64,
                "source": "commons-synthetic",
            }
        )
        self.assertEqual(mismatch["reason"], "local_hash_mismatch")
        self.assertEqual(missing["reason"], "local_evidence_missing")

    def test_city_and_bid_stay_closed(self) -> None:
        plane = runner.ReleaseReadinessPlane()
        pointers = runner.build_complete_pointers()
        city = plane.evaluate_release(
            {
                "request_id": "T-CITY",
                "named_human": runner.HUMAN_APPROVER,
                "verb": "contact_city",
                "pointers": pointers,
            }
        )
        bid = plane.evaluate_release(
            {
                "request_id": "T-BID",
                "named_human": runner.HUMAN_APPROVER,
                "verb": "submit_bid",
                "pointers": pointers,
            }
        )
        self.assertEqual(city["reason"], "production_destination_absent")
        self.assertEqual(bid["reason"], "production_destination_absent")
        self.assertEqual(len(plane.records), 0)

    def test_does_not_touch_off_limit_paths(self) -> None:
        unique = {
            "aquatrace_work_order_f_release_readiness.py",
            "test_aquatrace_work_order_f_release_readiness.py",
            "aquatrace-work-order-f-release-readiness.html",
            "p/aquatrace-work-order-f-release-readiness-20260831-01.md",
            "features/registry/aquatrace-work-order-f-release-readiness-20260831-01.json",
        }
        changed = subprocess.check_output(
            ["git", "diff", "--name-only", "origin/main"],
            cwd=ROOT,
            text=True,
        ).splitlines()
        untracked = subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=ROOT,
            text=True,
        ).splitlines()
        touched = [path for path in changed + untracked if path]
        for path in touched:
            self.assertTrue(
                path.startswith("revenue/aquatrace_work_order_f_release_readiness/")
                or path in unique,
                path,
            )
        for path in OFF_LIMIT_PATHS:
            if path.is_file():
                before = subprocess.check_output(
                    ["git", "hash-object", str(path)],
                    cwd=ROOT,
                    text=True,
                ).strip()
                self.assertEqual(before, _blob(path), path.name)

    def test_receipt_and_door_are_windows(self) -> None:
        self.assertTrue(RECEIPT.is_file())
        self.assertTrue(PAGE.is_file())
        self.assertIn("id: aquatrace-work-order-f-release-readiness-20260831-01", self.receipt)
        self.assertIn("cash_usd: 0", self.receipt)
        self.assertIn("No City contact", self.receipt)
        self.assertIn(runner.COMMAND, self.receipt)
        self.assertIn(runner.PRIVATE_CITE_SHA, self.receipt)
        self.assertIn(runner.COMMAND, self.page)
        self.assertIn("This page is a window", self.page)
        self.assertIn("No login", self.page)
        self.assertNotIn("login required", self.page.lower())
        self.assertIn("NOT_READY", self.page)

    def test_registry_row_matches_leftover(self) -> None:
        rec = json.loads(REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(rec["id"], runner.LEFTOVER_ID)
        self.assertEqual(rec["schema"], "commons-feature-v1")
        self.assertIn(str(PRODUCT.relative_to(ROOT)), rec["claimed_paths"])
        self.assertIn(str(RECEIPT.relative_to(ROOT)), rec["claimed_paths"])

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
        self.assertEqual(self.source["pre_sale_transport"], "NONE")


if __name__ == "__main__":
    unittest.main()
