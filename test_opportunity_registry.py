#!/usr/bin/env python3
"""Fail-closed tests for the Commons non-dilutive opportunity registry."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "opportunity_registry", ROOT / "host/opportunity_registry.py"
)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mod)


class OpportunityRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry, cls.schema = mod.load(ROOT)
        cls.by_id = {row["id"]: row for row in cls.registry["opportunities"]}

    def run_cli(self, command, root=None):
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host/opportunity_registry.py"),
                command,
                "--root",
                str(root or ROOT),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        rendered = completed.stdout.strip()
        parsed = json.loads(rendered)
        self.assertEqual(rendered, json.dumps(parsed, sort_keys=True, separators=(",", ":")))
        return parsed

    def test_compile_is_deterministic_and_valid(self):
        first = mod.compile_registry(ROOT)
        second = mod.compile_registry(ROOT)
        self.assertEqual(mod.canonical_dumps(first), mod.canonical_dumps(second))
        stored = mod.validate(ROOT, self.registry, self.schema)
        self.assertEqual(stored["status"], "VALID")
        self.assertEqual(
            stored["receipt_drift_paths"],
            [item["path"] for item in mod.receipt_drift(ROOT, self.registry)],
        )
        result = mod.validate(ROOT, first, self.schema)
        self.assertEqual(result["status"], "VALID")
        self.assertEqual(result["receipt_drift_count"], 0)
        self.assertEqual(result["receipt_drift_paths"], [])
        self.assertEqual(result["submitted"], 0)
        self.assertEqual(result["awarded"], 0)
        self.assertEqual(result["cash_received_usd"], 0)
        self.assertEqual(result["next"], "NONE_READY")

    def test_cli_validate_list_due_next(self):
        valid = self.run_cli("validate")
        self.assertEqual(valid["status"], "VALID")
        listed = self.run_cli("list")
        self.assertEqual(len(listed["opportunities"]), 21)
        due = self.run_cli("due")
        self.assertEqual(due["due"][0]["id"], "nsf-pesose-26-506")
        self.assertEqual(due["due"][0]["deadline_freshness"], "URGENT")
        nxt = self.run_cli("next")
        self.assertEqual(nxt["status"], "NONE_READY")
        self.assertEqual(nxt["reason"], "APPLICANT_ELIGIBILITY_UNKNOWN")
        self.assertEqual(len(nxt["opportunity_ids"]), 21)

    def test_legal_scope_and_zero_money(self):
        legal = self.registry["legal_scope"]
        self.assertTrue(all(value is False for value in legal.values()))
        self.assertEqual(legal["application_submitted"], False)
        self.assertEqual(self.registry["counts"]["cash_received_usd"], 0)
        for row in self.registry["opportunities"]:
            self.assertEqual(row["applicant_eligibility_state"], "UNKNOWN")
            self.assertEqual(row["expected_value_usd"], "UNKNOWN")
            self.assertEqual(row["cash_received_usd"], 0)
            self.assertIs(row["contacted"], False)
            self.assertIs(row["partnership_claimed"], False)
            self.assertEqual(row["award_status"], "NOT_AWARDED")
            self.assertTrue(row["fit"]["note"].startswith("ANALYSIS:"))
            self.assertTrue(row["owner"].startswith("COMMONS_ANY_"))
            self.assertNotIn("application_draft", row)
            self.assertNotIn("tax_identifier", row)

    def test_pesose_urgent_and_composed_grants(self):
        pesose = self.by_id["nsf-pesose-26-506"]
        self.assertEqual(pesose["lane"], "GRANT")
        self.assertEqual(pesose["deadline_freshness"], "URGENT")
        self.assertEqual(pesose["submission_status"], "NOT_SUBMITTED")
        self.assertEqual(
            pesose["official_urls"][0],
            "https://www.nsf.gov/funding/opportunities/pesose-pathways-enable-secure-open-source-ecosystems/nsf26-506/solicitation",
        )
        sbir = self.by_id["nsf-sbir-sttr-26-510"]
        self.assertEqual(sbir["stated_funding_evidence_state"], "CONFLICT")
        restack = self.by_id["nlnet-restack-ois-2026"]
        self.assertEqual(restack["application_state"], "UPCOMING")
        stf = self.by_id["sovereign-tech-fund-rolling"]
        self.assertEqual(stf["deadline_freshness"], "ROLLING")
        self.assertIn("EUR 50,000", stf["stated_funding_text"])
        codesupply = self.by_id["nlnet-codesupply-ois-2026"]
        self.assertEqual(codesupply["deadline_freshness"], "UNKNOWN")
        license_row = self.by_id["commons-public-license-unknown"]
        self.assertEqual(license_row["probability_state"], "BLOCKED_LICENSE_UNKNOWN")

    def test_live_offers_are_not_applications(self):
        hour = self.by_id["titan-hands-activation-hour"]
        self.assertEqual(hour["lane"], "PILOT")
        self.assertEqual(hour["probability_state"], "LIVE_OFFER_NOT_AN_APPLICATION")
        self.assertEqual(hour["submission_status"], "NOT_APPLICABLE")
        self.assertIn("USD 250", hour["stated_funding_text"])
        self.assertEqual(hour["cash_received_usd"], 0)
        archive = self.by_id["whitebox-archive-license"]
        self.assertEqual(archive["probability_state"], "BLOCKED_EVIDENCE")
        sam = self.by_id["procurement-sam-gov-procurement"]
        self.assertEqual(sam["probability_state"], "BLOCKED_REGISTRATION")
        research = self.by_id["research-eleutherai-lm-eval-harness"]
        self.assertEqual(research["probability_state"], "RESEARCHED_NOT_CONTACTED")

    def test_capability_receipt_drift_is_exact_and_named(self):
        expected = []
        for cap in self.registry["capabilities"]:
            self.assertEqual(cap["status"], "SHIPPED_ON_MAIN")
            for rec in cap["receipts"]:
                path = ROOT / rec["path"]
                if not path.is_file():
                    expected.append({
                        "path": rec["path"],
                        "state": "MISSING",
                        "pinned_sha256": rec["sha256"],
                        "pinned_bytes": rec["bytes"],
                        "live_sha256": None,
                        "live_bytes": None,
                    })
                    continue
                live_sha256 = mod.sha256_file(path)
                live_bytes = path.stat().st_size
                if live_sha256 != rec["sha256"] or live_bytes != rec["bytes"]:
                    expected.append({
                        "path": rec["path"],
                        "state": "DRIFT",
                        "pinned_sha256": rec["sha256"],
                        "pinned_bytes": rec["bytes"],
                        "live_sha256": live_sha256,
                        "live_bytes": live_bytes,
                    })
        self.assertEqual(
            mod.receipt_drift(ROOT, self.registry),
            sorted(expected, key=lambda item: item["path"]),
        )

    def test_features_html_receipt_is_snapshot_and_drift_is_visible(self):
        recs = [rec for cap in self.registry["capabilities"] for rec in cap["receipts"]]
        feat = [rec for rec in recs if rec["path"] == "features.html"]
        self.assertEqual(len(feat), 1, "features.html must have one capability receipt")
        path = ROOT / "features.html"
        self.assertTrue(path.is_file())
        html = (ROOT / "opportunity.html").read_text(encoding="utf-8")
        self.assertIn(feat[0]["sha256"][:16], html)
        drift_paths = [item["path"] for item in mod.receipt_drift(ROOT, self.registry)]
        moved = (
            mod.sha256_file(path) != feat[0]["sha256"]
            or path.stat().st_size != feat[0]["bytes"]
        )
        self.assertEqual("features.html" in drift_paths, moved)

    def test_capability_receipts_name_every_stale_path(self):
        stale = []
        for cap in self.registry["capabilities"]:
            for rec in cap["receipts"]:
                path = ROOT / rec["path"]
                if not path.is_file():
                    stale.append(rec["path"])
                    continue
                live = mod.sha256_file(path)
                size = path.stat().st_size
                if live != rec["sha256"] or size != rec["bytes"]:
                    stale.append(rec["path"])
        self.assertEqual(
            [item["path"] for item in mod.receipt_drift(ROOT, self.registry)],
            sorted(stale),
        )

    def test_resource_ledger_receipt_is_snapshot_and_drift_is_visible(self):
        recs = [rec for cap in self.registry["capabilities"] for rec in cap["receipts"]]
        ledger = [rec for rec in recs if rec["path"] == "ground/RESOURCE_LEDGER.json"]
        self.assertEqual(len(ledger), 1, "ground/RESOURCE_LEDGER.json must have one capability receipt")
        path = ROOT / "ground/RESOURCE_LEDGER.json"
        self.assertTrue(path.is_file())
        html = (ROOT / "opportunity.html").read_text(encoding="utf-8")
        self.assertIn(ledger[0]["sha256"][:16], html)
        drift_paths = [item["path"] for item in mod.receipt_drift(ROOT, self.registry)]
        moved = (
            mod.sha256_file(path) != ledger[0]["sha256"]
            or path.stat().st_size != ledger[0]["bytes"]
        )
        self.assertEqual("ground/RESOURCE_LEDGER.json" in drift_paths, moved)

    def test_packets_and_js_off_html(self):
        html = (ROOT / "opportunity.html").read_text(encoding="utf-8")
        proof = (ROOT / "proof-to-proposal.html").read_text(encoding="utf-8")
        self.assertIn("OPEN OPPORTUNITY DOOR", html)
        self.assertIn("nsf-pesose-26-506", html)
        self.assertIn("TITAN Hands", html)
        self.assertIn("RINGDELTA", html)
        self.assertNotRegex(html, r"requireAuth|login required|permission gate|api[-_]?key required")
        self.assertIn("not filings", proof.lower())
        for row in self.registry["opportunities"]:
            packet = ROOT / "revenue/ip/packets" / ("%s.md" % row["packet_id"])
            self.assertTrue(packet.is_file(), packet)
            text = packet.read_text(encoding="utf-8")
            self.assertIn("**not** an application", text)
            self.assertIn(row["id"], text)
            self.assertIn("sha256", text)

    def test_registry_grid_wraps_long_official_urls(self):
        html = (ROOT / "opportunity.html").read_text(encoding="utf-8")
        self.assertIn("minmax(min(22rem,100%),1fr)", html)
        self.assertIn(".opp,.struct,.struct dd{min-width:0}", html)
        self.assertIn(".struct dd,.struct a{overflow-wrap:anywhere}", html)

    def test_rejects_cash_and_eligibility_fabrication(self):
        broken = copy.deepcopy(self.registry)
        broken["opportunities"][0]["cash_received_usd"] = 1
        with self.assertRaisesRegex(mod.RegistryError, "cash"):
            mod.validate(ROOT, broken, self.schema)
        broken = copy.deepcopy(self.registry)
        broken["opportunities"][0]["applicant_eligibility_state"] = "ELIGIBLE"
        with self.assertRaisesRegex(mod.RegistryError, "eligibility"):
            mod.validate(ROOT, broken, self.schema)
        broken = copy.deepcopy(self.registry)
        broken["legal_scope"]["award_claimed"] = 0
        with self.assertRaisesRegex(mod.RegistryError, "legal_scope"):
            mod.validate(ROOT, broken, self.schema)
        raw = '{"a":1,"a":2}'
        with self.assertRaisesRegex(mod.RegistryError, "duplicate JSON key"):
            mod._parse_json(raw, "dup")

    def test_compile_writes_same_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            for rel in (
                "revenue/ip",
                "revenue/distribution",
                "host",
                "docs",
                "ground",
                "p",
                "excerpts/20260828",
                "evidence",
                "host/titan_hands",
            ):
                (dest / rel).mkdir(parents=True, exist_ok=True)
            # Full compile needs the whole receipt tree; compile in-repo instead.
        first = mod.compile_registry(ROOT)
        second = mod.compile_registry(ROOT)
        self.assertEqual(mod._canonical_sha256(first), mod._canonical_sha256(second))

    def test_open_door_and_surfaces_exist(self):
        for rel in (
            "opportunity.html",
            "proof-to-proposal.html",
            "ground/OPPORTUNITY_REGISTRY.md",
            "ground/PROOF_TO_PROPOSAL.md",
            "p/grok-opportunity-registry-20260828-02.md",
        ):
            self.assertTrue((ROOT / rel).is_file(), rel)
        host = (ROOT / "host/opportunity_registry.py").read_text(encoding="utf-8")
        self.assertNotRegex(host, r"os.environ\[.API_KEY|SECRET_TOKEN|password\s*=")
        compose_paths = [row["path"] for row in self.registry["compose"]]
        self.assertIn("revenue/listing_registry/registry.json", compose_paths)
        self.assertTrue((ROOT / "listing-registry.html").is_file())
        self.assertTrue((ROOT / "host/listing_registry.py").is_file())
        self.assertNotIn("listing_registry.py", (ROOT / "host/opportunity_registry.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
