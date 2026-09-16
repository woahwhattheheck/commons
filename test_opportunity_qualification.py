from __future__ import annotations

import copy
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent
MODULE_DIR = ROOT / "revenue" / "opportunity_qualification"
sys.path.insert(0, str(MODULE_DIR))

import engine  # noqa: E402
import test_engine as legacy  # noqa: E402
import test_authority_overlay as overlay  # noqa: E402


def completeness_v2_for(packet):
    """Test-only independent commitment constructor for intentionally changed packets."""
    sources = {source["source_id"]: source for source in packet["sources"]}
    gates = []
    for requirement in packet["requirements"]:
        source = sources[requirement["buyer_source_id"]]
        gates.append(
            {
                "gate_id": requirement["gate_id"],
                "category": requirement["category"],
                "mandatory": requirement["mandatory"],
                "route": requirement["route"],
                "cure": requirement["cure"],
                "buyer_source_id": requirement["buyer_source_id"],
                "buyer_source_sha256": source["sha256"],
                "description_sha256": engine.digest(requirement["description"]),
            }
        )
    gates.sort(key=lambda gate: gate["gate_id"])

    opportunity = packet["opportunity"]
    authority_ids = {
        opportunity.get("controlling_source_id"),
        opportunity.get("proposal_deadline_source_id"),
        opportunity.get("question_deadline_source_id"),
        opportunity.get("teaming_source_id"),
    }
    authority_ids.update(
        requirement["buyer_source_id"] for requirement in packet["requirements"]
    )
    authority_sources = []
    for source_id in sorted(source_id for source_id in authority_ids if source_id is not None):
        source = sources[source_id]
        authority_sources.append(
            {
                "source_id": source["source_id"],
                "scope": source["scope"],
                "source_class": source["source_class"],
                "url": source["url"],
                "captured_at": source["captured_at"],
                "sha256": source["sha256"],
            }
        )

    controlling_id = opportunity["controlling_source_id"]
    manifest = {
        "contract": engine.COMPLETENESS_CONTRACT,
        "opportunity_id": opportunity["opportunity_id"],
        "controlling_source_id": controlling_id,
        "controlling_source_sha256": sources[controlling_id]["sha256"],
        "extracted_at": "2026-09-13T09:30:00Z",
        "extraction_evidence_sha256": "e" * 64,
        "complete": True,
        "gate_count": len(gates),
        "gate_set_sha256": engine.digest(gates),
        "gates": gates,
        "authority_source_count": len(authority_sources),
        "authority_source_set_sha256": engine.digest(authority_sources),
        "authority_sources": authority_sources,
    }
    return manifest, engine.digest(manifest)


legacy.completeness_for = completeness_v2_for


def _official_extension_uses_fresh_independent_commitment(self):
    packet = copy.deepcopy(legacy.PACKET)
    packet["sources"].append(
        {
            "source_id": "buyer-addendum",
            "scope": "BUYER",
            "source_class": "OFFICIAL",
            "url": "https://buyer.example.gov/rfp/2026-001/addendum-2",
            "captured_at": "2026-09-13T09:30:00Z",
            "sha256": "8" * 64,
            "label": "Official deadline extension",
        }
    )
    packet["opportunity"]["proposal_deadline"] = "2026-10-15T17:00:00Z"
    packet["opportunity"]["proposal_deadline_source_id"] = "buyer-addendum"
    manifest, root = completeness_v2_for(packet)
    receipt = self.compile(packet, trust=(manifest, root))
    self.assertEqual(receipt["disposition"], engine.PRIME_READY)
    self.assertTrue(receipt["completeness"]["verified"])


legacy.QualificationTests.test_official_extension_can_restore_open_deadline = (
    _official_extension_uses_fresh_independent_commitment
)

QualificationTests = legacy.QualificationTests
AuthorityOverlayTests = overlay.AuthorityOverlayTests


class AuthoritySourceTrustTests(unittest.TestCase):
    def compile_with(self, packet, manifest, root):
        return engine.compile_qualification(
            copy.deepcopy(packet),
            trusted_as_of=legacy.AS_OF,
            trusted_completeness=copy.deepcopy(manifest),
            trusted_completeness_sha256=root,
        )

    def test_retained_fixture_binds_full_buyer_authority_descriptor(self):
        manifest = copy.deepcopy(legacy.TRUSTED_COMPLETENESS)
        self.assertEqual(manifest["contract"], engine.COMPLETENESS_CONTRACT)
        self.assertEqual(manifest["authority_source_count"], 1)
        source = manifest["authority_sources"][0]
        self.assertEqual(
            set(source),
            {"source_id", "scope", "source_class", "url", "captured_at", "sha256"},
        )
        self.assertEqual(source["source_id"], "buyer-rfp")
        self.assertEqual(source["scope"], "BUYER")
        self.assertEqual(source["source_class"], "OFFICIAL")
        self.assertEqual(
            engine.digest(manifest["authority_sources"]),
            manifest["authority_source_set_sha256"],
        )
        self.assertEqual(
            engine.digest(manifest), legacy.TRUSTED_COMPLETENESS_SHA256
        )

    def test_frozen_root_rejects_official_to_secondary_flip(self):
        packet = copy.deepcopy(legacy.PACKET)
        packet["sources"][0]["source_class"] = "SECONDARY"
        receipt = self.compile_with(
            packet,
            legacy.TRUSTED_COMPLETENESS,
            legacy.TRUSTED_COMPLETENESS_SHA256,
        )
        self.assertEqual(receipt["disposition"], engine.HOLD)
        self.assertFalse(receipt["completeness"]["verified"])
        self.assertIn(
            "PACKAGE_AUTHORITY_SOURCE_SET_MISMATCH",
            receipt["completeness"]["reasons"],
        )

    def test_secondary_retained_root_cannot_be_upgraded_to_official(self):
        packet = copy.deepcopy(legacy.PACKET)
        packet["sources"][0]["source_class"] = "SECONDARY"
        manifest, root = completeness_v2_for(packet)
        baseline = self.compile_with(packet, manifest, root)
        self.assertEqual(baseline["disposition"], engine.HOLD)
        self.assertTrue(baseline["completeness"]["verified"])

        promoted = copy.deepcopy(packet)
        promoted["sources"][0]["source_class"] = "OFFICIAL"
        receipt = self.compile_with(promoted, manifest, root)
        self.assertEqual(receipt["disposition"], engine.HOLD)
        self.assertFalse(receipt["completeness"]["verified"])
        self.assertIn(
            "PACKAGE_AUTHORITY_SOURCE_SET_MISMATCH",
            receipt["completeness"]["reasons"],
        )

    def test_frozen_root_rejects_authority_url_provenance_drift(self):
        packet = copy.deepcopy(legacy.PACKET)
        packet["sources"][0]["url"] = "https://mirror.example.com/rfp/2026-001"
        receipt = self.compile_with(
            packet,
            legacy.TRUSTED_COMPLETENESS,
            legacy.TRUSTED_COMPLETENESS_SHA256,
        )
        self.assertEqual(receipt["disposition"], engine.HOLD)
        self.assertFalse(receipt["completeness"]["verified"])
        self.assertIn(
            "PACKAGE_AUTHORITY_SOURCE_SET_MISMATCH",
            receipt["completeness"]["reasons"],
        )

    def test_frozen_root_rejects_authority_scope_drift(self):
        packet = copy.deepcopy(legacy.PACKET)
        packet["sources"][0]["scope"] = "CAPABILITY"
        receipt = self.compile_with(
            packet,
            legacy.TRUSTED_COMPLETENESS,
            legacy.TRUSTED_COMPLETENESS_SHA256,
        )
        self.assertEqual(receipt["disposition"], engine.HOLD)
        self.assertFalse(receipt["completeness"]["verified"])
        self.assertIn(
            "PACKAGE_AUTHORITY_SOURCE_SET_MISMATCH",
            receipt["completeness"]["reasons"],
        )
        self.assertTrue(
            engine.verify_receipt_against_inputs(
                receipt,
                packet,
                trusted_as_of=legacy.AS_OF,
                trusted_completeness=copy.deepcopy(legacy.TRUSTED_COMPLETENESS),
                trusted_completeness_sha256=legacy.TRUSTED_COMPLETENESS_SHA256,
            )
        )

    def test_requirement_bound_to_capability_source_without_root_still_rejects(self):
        packet = copy.deepcopy(legacy.PACKET)
        packet["requirements"][0]["buyer_source_id"] = "prime-cap"
        with self.assertRaises(engine.QualificationError) as caught:
            engine.compile_qualification(
                packet,
                trusted_as_of=legacy.AS_OF,
                trusted_completeness=None,
                trusted_completeness_sha256=None,
            )
        self.assertIn(
            "requirement must bind a BUYER source",
            str(caught.exception),
        )

    def test_separate_deadline_source_class_is_bound(self):
        packet = copy.deepcopy(legacy.PACKET)
        packet["sources"].append(
            {
                "source_id": "buyer-addendum",
                "scope": "BUYER",
                "source_class": "OFFICIAL",
                "url": "https://buyer.example.gov/rfp/2026-001/addendum-2",
                "captured_at": "2026-09-13T09:30:00Z",
                "sha256": "8" * 64,
                "label": "Official deadline extension",
            }
        )
        packet["opportunity"]["proposal_deadline"] = "2026-10-15T17:00:00Z"
        packet["opportunity"]["proposal_deadline_source_id"] = "buyer-addendum"
        manifest, root = completeness_v2_for(packet)
        baseline = self.compile_with(packet, manifest, root)
        self.assertEqual(baseline["disposition"], engine.PRIME_READY)
        self.assertTrue(baseline["completeness"]["verified"])

        packet["sources"][-1]["source_class"] = "SECONDARY"
        receipt = self.compile_with(packet, manifest, root)
        self.assertEqual(receipt["disposition"], engine.HOLD)
        self.assertFalse(receipt["completeness"]["verified"])
        self.assertIn(
            "PACKAGE_AUTHORITY_SOURCE_SET_MISMATCH",
            receipt["completeness"]["reasons"],
        )

    def test_separate_teaming_source_class_is_bound(self):
        packet = copy.deepcopy(legacy.PACKET)
        packet["sources"].append(
            {
                "source_id": "buyer-teaming",
                "scope": "BUYER",
                "source_class": "OFFICIAL",
                "url": "https://buyer.example.gov/rfp/2026-001/teaming",
                "captured_at": "2026-09-13T09:20:00Z",
                "sha256": "9" * 64,
                "label": "Official teaming instruction",
            }
        )
        packet["opportunity"]["teaming_source_id"] = "buyer-teaming"
        gate = packet["requirements"][1]
        gate["cure"] = "PARTNER"
        gate["prime_state"] = "MISSING"
        gate["prime_evidence_ids"] = []
        gate["team_state"] = "PASS"
        gate["team_evidence_ids"] = ["team-reference"]
        gate["category"] = "REFERENCE"
        packet["evidence"][3]["category"] = "REFERENCE"

        manifest, root = completeness_v2_for(packet)
        baseline = self.compile_with(packet, manifest, root)
        self.assertEqual(baseline["disposition"], engine.TEAMING_READY)
        self.assertTrue(baseline["completeness"]["verified"])

        packet["sources"][-1]["source_class"] = "SECONDARY"
        receipt = self.compile_with(packet, manifest, root)
        self.assertEqual(receipt["disposition"], engine.HOLD)
        self.assertFalse(receipt["team"]["ready"])
        self.assertFalse(receipt["completeness"]["verified"])
        self.assertIn(
            "PACKAGE_AUTHORITY_SOURCE_SET_MISMATCH",
            receipt["completeness"]["reasons"],
        )

    def test_verifier_rejects_source_authority_relabel_under_frozen_root(self):
        packet = copy.deepcopy(legacy.PACKET)
        receipt = self.compile_with(
            packet,
            legacy.TRUSTED_COMPLETENESS,
            legacy.TRUSTED_COMPLETENESS_SHA256,
        )
        self.assertTrue(
            engine.verify_receipt_against_inputs(
                receipt,
                copy.deepcopy(packet),
                trusted_as_of=legacy.AS_OF,
                trusted_completeness=copy.deepcopy(legacy.TRUSTED_COMPLETENESS),
                trusted_completeness_sha256=legacy.TRUSTED_COMPLETENESS_SHA256,
            )
        )
        packet["sources"][0]["source_class"] = "SECONDARY"
        self.assertFalse(
            engine.verify_receipt_against_inputs(
                receipt,
                packet,
                trusted_as_of=legacy.AS_OF,
                trusted_completeness=copy.deepcopy(legacy.TRUSTED_COMPLETENESS),
                trusted_completeness_sha256=legacy.TRUSTED_COMPLETENESS_SHA256,
            )
        )

    def test_manifest_authority_set_digest_is_internally_checked(self):
        manifest = copy.deepcopy(legacy.TRUSTED_COMPLETENESS)
        manifest["authority_sources"][0]["url"] = "https://mirror.example.com/rfp"
        with self.assertRaises(engine.QualificationError):
            self.compile_with(
                legacy.PACKET, manifest, legacy.TRUSTED_COMPLETENESS_SHA256
            )

    def test_bool_authority_source_count_is_rejected(self):
        manifest = copy.deepcopy(legacy.TRUSTED_COMPLETENESS)
        manifest["authority_source_count"] = True
        with self.assertRaises(engine.QualificationError):
            self.compile_with(
                legacy.PACKET, manifest, legacy.TRUSTED_COMPLETENESS_SHA256
            )

    @unittest.skipIf(
        os.environ.get("OPPQ_OPT_CHILD") == "1",
        "optimized child does not recursively spawn itself",
    )
    def test_same_root_suite_passes_under_python_optimized(self):
        env = os.environ.copy()
        env["OPPQ_OPT_CHILD"] = "1"
        proc = subprocess.run(
            [sys.executable, "-O", str(Path(__file__).resolve())],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=180,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
