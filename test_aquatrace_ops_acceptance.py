#!/usr/bin/env python3
"""Binary tests for the AquaTrace ops-acceptance runner.

The runner is the product. HTML is a window. Fail-closed.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

import aquatrace_ops_acceptance as runner

ROOT = Path(__file__).resolve().parent
PACK = ROOT / "revenue" / "aquatrace_ops_acceptance"
PAGE = ROOT / "aquatrace-ops-acceptance.html"
RECEIPT = ROOT / "p" / "AT-GROK-OPS-ACCEPTANCE-01.md"
REGISTRY = ROOT / "features" / "registry" / "AT-GROK-OPS-ACCEPTANCE-01.json"
PRODUCT = ROOT / "aquatrace_ops_acceptance.py"

OFF_LIMIT_PATHS = (
    ROOT / "p" / "AT-GROK-ADAPTER-EVIDENCE-01.md",
    ROOT / "p" / "AT-GROK-CMDP-EVIDENCE-01.md",
    ROOT / "p" / "corrigan-specialty-fuel-blend-dossier-lims-01.md",
    ROOT / "p" / "torrent-workorder-commissioning-lims-01.md",
    ROOT / "p" / "bsk-multilab-accession-parity-lims-01.md",
    ROOT / "p" / "chemtechford-short-hold-intake-lims-01.md",
    ROOT / "p" / "aquatrace-work-order-a-architecture-acceptance-20260831-01.md",
    ROOT / "p" / "aquatrace-work-order-b-production-foundation-20260831-01.md",
    ROOT / "p" / "aquatrace-work-order-c-reporting-offline-20260831-01.md",
    ROOT / "p" / "aquatrace-work-order-d-municipal-ux-package-20260831-01.md",
    ROOT / "p" / "aquatrace-work-order-c-field-mobility-20260831-01.md",
    ROOT / "p" / "aquatrace-work-order-f-release-readiness-20260831-01.md",
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
    ROOT / "test_aquatrace_ops_acceptance.py",
    PAGE,
    RECEIPT,
    REGISTRY,
    PACK / "source.json",
    PACK / "matrix.json",
    PACK / "contract.json",
    PACK / "public_sources.json",
    PACK / "unknown_ledger.json",
    PACK / "README.md",
)


def _blob(path: Path) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(path)],
        cwd=ROOT,
        text=True,
    ).strip()


class AquaTraceOpsAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.battery = runner.run_battery()
        cls.default = runner.run_default()
        cls.page = PAGE.read_text(encoding="utf-8") if PAGE.is_file() else ""
        cls.receipt = RECEIPT.read_text(encoding="utf-8") if RECEIPT.is_file() else ""
        cls.source = json.loads((PACK / "source.json").read_text(encoding="utf-8"))
        cls.matrix = json.loads((PACK / "matrix.json").read_text(encoding="utf-8"))
        cls.unknown = json.loads((PACK / "unknown_ledger.json").read_text(encoding="utf-8"))

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
        self.assertIn("cases=16/16", proc.stdout)
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

    def test_row_command_stays_not_ready(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(PRODUCT), "--row", "identity_mfa_session"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("NOT_READY", proc.stdout)
        self.assertIn("missing_hash", proc.stdout)

    def test_battery_is_deterministic(self) -> None:
        self.assertTrue(self.battery["ok"], runner.summarize(self.battery))
        self.assertEqual(self.battery["case_count"], 16)
        self.assertEqual(self.battery["cases_ok"], 16)
        self.assertEqual(self.battery["product_state"], "NOT_READY")
        self.assertEqual(self.battery["default_ready_count"], 0)
        self.assertEqual(self.battery["default_not_ready_count"], 9)
        self.assertEqual(self.battery["complete_ready_count"], 9)
        self.assertEqual(self.battery["release_count"], 1)
        self.assertEqual(self.battery["deny_count"], 8)
        self.assertEqual(self.battery["audit_sha256"], runner.GOLDEN_AUDIT_SHA256)

    def test_every_named_row_is_present_and_not_ready(self) -> None:
        self.assertEqual(list(self.default["not_ready"]), list(runner.ROW_IDS))
        self.assertEqual([row["id"] for row in self.default["rows"]], list(runner.ROW_IDS))
        self.assertEqual([row["id"] for row in self.matrix["rows"]], list(runner.ROW_IDS))
        required = {
            "id",
            "area",
            "owner",
            "command",
            "procedure",
            "artifact",
            "artifact_hash",
            "freshness",
            "rejection_reason",
            "state",
        }
        for row in self.matrix["rows"]:
            self.assertTrue(required.issubset(row), row["id"])
            self.assertEqual(row["state"], "NOT_READY", row)
            self.assertEqual(row["owner"], "UNKNOWN", row)
            self.assertEqual(row["artifact_hash"], "UNKNOWN", row)
            self.assertEqual(row["freshness"], "UNKNOWN", row)
            self.assertEqual(row["rejection_reason"], "missing_hash_and_freshness", row)

    def test_private_cite_does_not_promote(self) -> None:
        self.assertEqual(self.source["private_cite_sha"], runner.PRIVATE_CITE_SHA)
        self.assertEqual(self.source["later_official_sha"], runner.LATER_OFFICIAL_SHA)
        self.assertFalse(self.source["private_repo_cloned"])
        self.assertFalse(self.source["private_docs_duplicated"])
        self.assertFalse(self.default["invented_certification"])
        self.assertFalse(self.default["production_ready"])
        self.assertFalse(self.default["deployed"])
        self.assertFalse(self.default["submitted"])
        self.assertFalse(self.default["buyer_accepted"])
        self.assertFalse(self.default["promoted"])

    def test_complete_overlay_is_ready_without_inventing_labels(self) -> None:
        complete = self.battery["complete"]
        self.assertEqual(complete["product_state"], "MATRIX_SATISFIED")
        self.assertEqual(complete["ready"], list(runner.ROW_IDS))
        self.assertFalse(complete["production_ready"])
        self.assertFalse(complete["buyer_accepted"])
        self.assertFalse(complete["deployed"])
        self.assertFalse(complete["submitted"])
        self.assertFalse(complete["promoted"])

    def test_system_unnamed_held_denied(self) -> None:
        plane = runner.OpsAcceptancePlane()
        overlay = runner.build_complete_overlay()
        system = plane.evaluate_release(
            {"request_id": "T-SYS", "named_human": "SYSTEM", "overlay": overlay}
        )
        unnamed = plane.evaluate_release(
            {"request_id": "T-NONE", "named_human": "", "overlay": overlay}
        )
        held = plane.evaluate_release(
            {"request_id": "T-HELD", "named_human": "HELD", "overlay": overlay}
        )
        machine = plane.evaluate_release(
            {"request_id": "T-MAC", "named_human": "MACHINE", "overlay": overlay}
        )
        self.assertEqual(system["reason"], "autonomous_release_denied")
        self.assertEqual(unnamed["reason"], "named_human_missing")
        self.assertEqual(held["reason"], "held_release_denied")
        self.assertEqual(machine["reason"], "autonomous_release_denied")
        self.assertEqual(len(plane.records), 0)

    def test_named_human_release_and_replay(self) -> None:
        plane = runner.OpsAcceptancePlane()
        overlay = runner.build_complete_overlay()
        first = plane.evaluate_release(
            {
                "request_id": "T-REL",
                "named_human": runner.HUMAN_APPROVER,
                "overlay": overlay,
            }
        )
        second = plane.evaluate_release(
            {
                "request_id": "T-REL",
                "named_human": runner.HUMAN_APPROVER,
                "overlay": overlay,
            }
        )
        self.assertTrue(first["ok"])
        self.assertEqual(first["effect"]["state"], "RELEASE_RECORDED")
        self.assertFalse(first["effect"]["production_ready"])
        self.assertEqual(second["reason"], "replay_suppressed")
        self.assertEqual(len(plane.records), 1)

    def test_hold_on_default_even_with_named_human(self) -> None:
        plane = runner.OpsAcceptancePlane()
        got = plane.evaluate_release(
            {
                "request_id": "T-EARLY",
                "named_human": runner.HUMAN_APPROVER,
            }
        )
        self.assertEqual(got["decision"], "DENY")
        self.assertEqual(got["reason"], "rows_not_ready")
        self.assertEqual(len(plane.records), 0)

    def test_missing_hash_and_freshness_fail_closed(self) -> None:
        plane = runner.OpsAcceptancePlane()
        row = runner.matrix_rows()[0]
        no_hash = plane.evaluate_row(
            row,
            {
                "owner": runner.HUMAN_APPROVER,
                "artifact": runner.fixture_relpath("identity_mfa_session"),
                "artifact_hash": "UNKNOWN",
                "freshness": runner.CLOCK,
                "freshness_max_age_seconds": runner.FRESHNESS_WINDOW,
            },
        )
        no_fresh = plane.evaluate_row(
            row,
            {
                "owner": runner.HUMAN_APPROVER,
                "artifact": runner.fixture_relpath("identity_mfa_session"),
                "artifact_hash": runner.sha256_hex(
                    ROOT / runner.fixture_relpath("identity_mfa_session")
                ),
                "freshness": "UNKNOWN",
                "freshness_max_age_seconds": runner.FRESHNESS_WINDOW,
            },
        )
        self.assertEqual(no_hash["reason"], "missing_hash")
        self.assertEqual(no_fresh["reason"], "missing_freshness")
        self.assertEqual(no_hash["state"], "NOT_READY")
        self.assertEqual(no_fresh["state"], "NOT_READY")

    def test_never_promotes_declared_ready(self) -> None:
        plane = runner.OpsAcceptancePlane()
        declared = dict(runner.matrix_rows()[3])
        declared["state"] = "READY"
        got = plane.evaluate_row(declared)
        self.assertEqual(got["state"], "NOT_READY")
        self.assertEqual(got["reason"], "missing_hash")
        promote = plane.evaluate_release(
            {
                "request_id": "T-PROMOTE",
                "named_human": runner.HUMAN_APPROVER,
                "verb": "promote",
                "overlay": runner.build_complete_overlay(),
            }
        )
        self.assertEqual(promote["reason"], "promotion_forbidden")

    def test_city_and_bid_stay_closed(self) -> None:
        plane = runner.OpsAcceptancePlane()
        overlay = runner.build_complete_overlay()
        city = plane.evaluate_release(
            {
                "request_id": "T-CITY",
                "named_human": runner.HUMAN_APPROVER,
                "verb": "contact_city",
                "overlay": overlay,
            }
        )
        bid = plane.evaluate_release(
            {
                "request_id": "T-BID",
                "named_human": runner.HUMAN_APPROVER,
                "verb": "submit_bid",
                "overlay": overlay,
            }
        )
        self.assertEqual(city["reason"], "production_destination_absent")
        self.assertEqual(bid["reason"], "production_destination_absent")
        self.assertEqual(len(plane.records), 0)

    def test_unknown_ledger_is_explicit(self) -> None:
        ids = {item["id"] for item in self.unknown["unknowns"]}
        self.assertIn("ALL_ROWS", ids)
        self.assertIn("monitoring", ids)
        self.assertIn("backup_restore_dr", ids)
        self.assertIn("training_uat", ids)
        self.assertIn("buyer_signoff", ids)
        self.assertGreaterEqual(len(self.unknown["unknowns"]), 8)

    def test_does_not_touch_off_limit_paths(self) -> None:
        unique = {
            "aquatrace_ops_acceptance.py",
            "test_aquatrace_ops_acceptance.py",
            "aquatrace-ops-acceptance.html",
            "p/AT-GROK-OPS-ACCEPTANCE-01.md",
            "features/registry/AT-GROK-OPS-ACCEPTANCE-01.json",
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
                path.startswith("revenue/aquatrace_ops_acceptance/")
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
        self.assertIn("id: AT-GROK-OPS-ACCEPTANCE-01", self.receipt)
        self.assertIn("cash_usd: 0", self.receipt)
        self.assertIn("No City contact", self.receipt)
        self.assertIn(runner.COMMAND, self.receipt)
        self.assertIn(runner.PRIVATE_CITE_SHA, self.receipt)
        self.assertIn("UNKNOWN", self.receipt)
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
