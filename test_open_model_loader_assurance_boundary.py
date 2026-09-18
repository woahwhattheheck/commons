#!/usr/bin/env python3
"""Pin Open Model source-truth: the completeness receipt runs a
manifest-declared loader and does not attest loader side-effect safety.

Regression for tests.yml 34555343381 / PR 12203. Runtime behavior stays
the existing 8/8 + loader-exit contract in test_open_model_release_receipt.py.
"""
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "revenue/open_model_release_receipt/contract.json"
PAGE = ROOT / "open-model-release-receipt.html"
REGISTRY = ROOT / "features/registry/open-model-release-receipt.json"
CATALOG = ROOT / "revenue/outcome_commerce/catalog.json"
REVIEWED_CONTRACT_BLOB = "7be8c00672596c4418a1a9f7a1c597ff2afe11ae"
CHECKOUT = "https://buy.stripe.com/dRmfZgdp34Z322d0Ku43S0o"


def git_hash_object(path: Path) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(path)], cwd=ROOT, text=True
    ).strip()


class OpenModelLoaderAssuranceBoundaryTests(unittest.TestCase):
    def test_reviewed_contract_blob_is_catalog_source_pin(self) -> None:
        self.assertEqual(git_hash_object(CONTRACT), REVIEWED_CONTRACT_BLOB)
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        listing = next(
            row for row in catalog["listings"] if row["id"] == "open-model-release-receipt"
        )
        self.assertEqual(
            listing["source_artifact"],
            {
                "path": "revenue/open_model_release_receipt/contract.json",
                "blob_sha": REVIEWED_CONTRACT_BLOB,
                "terms_authority": "source",
            },
        )

    def test_source_truth_calls_the_loader_manifest_declared(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        page = PAGE.read_text(encoding="utf-8")
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        funnel = catalog["funnels"]["open-model-release-receipt"]

        self.assertIn("run one manifest-declared loader", contract["workflow"])
        self.assertNotIn("deterministic loader", json.dumps(contract))
        self.assertIn(
            "loader exit is the loader-behavior assertion",
            " ".join(contract["acceptance"]).lower(),
        )
        self.assertIn(
            "manifest-declared loader side effects are outside the completeness receipt's assurance",
            contract["data_boundary"],
        )
        self.assertIn(
            "no training-quality or loader-side-effect-safety claim",
            contract["decision_boundary"],
        )
        self.assertTrue(contract["open_door"])
        self.assertFalse(contract["requires_login"])

        self.assertIn("runs one manifest-declared loader", page)
        self.assertNotIn("deterministic loader", page)
        self.assertIn('id="live-cash"', page)
        self.assertIn(CHECKOUT, page)
        self.assertIn("The receipt does not itself deploy or publish the release.", page)

        self.assertIn(
            "manifest-declared loader side effects are outside the completeness receipt's assurance",
            registry["boundaries"],
        )
        self.assertIn(
            "no training-quality or loader-side-effect-safety claim",
            registry["boundaries"],
        )
        self.assertIn(
            "receipt does not itself deploy or publish the release",
            registry["boundaries"],
        )

        self.assertIn("one manifest-declared loader", funnel["acquisition"]["message"])
        self.assertNotIn("deterministic loader", funnel["acquisition"]["message"])
        self.assertIn(
            "Completeness receipt only: no training-quality or loader-side-effect-safety claim, and the receipt does not itself deploy or publish the release",
            funnel["qualification"]["required"],
        )
        self.assertIn(
            "Loader exit is the loader-behavior assertion; filesystem, network, database, training, and publication side effects of the manifest-declared loader are outside this receipt's assurance",
            funnel["fulfillment"]["acceptance"],
        )


if __name__ == "__main__":
    unittest.main()
