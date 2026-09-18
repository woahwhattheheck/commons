#!/usr/bin/env python3
"""Hermetic integrity checks for the rejected Learn2Design V3 public matrix."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import statistics
import unittest

ROOT = Path(__file__).resolve().parent
RECORD = ROOT / "revenue" / "learn2design2026" / "recorded_runs" / "34942764610" / "v3_public_matrix_index.json"
REJECTED_SOURCE = ROOT / "revenue" / "learn2design2026" / "rejected" / "v3_depth_throughput.py"
EXPECTED_V3_BLOB = "78ce195e1779441f2a0c53feef67c8dafd87f240"
EXPECTED_V3_SHA256 = "d0a65c01708941220cd8c16accdfd16136c5294a94e2032b4cd68cdf83a360a9"


def canonical_sha256(value: dict) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()


class Learn2DesignV3RecordedRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.record = json.loads(RECORD.read_text(encoding="utf-8"))
        cls.rows = cls.record["measurements"]

    def test_provider_and_authority_pins(self) -> None:
        provider = self.record["provider"]
        self.assertEqual(provider["runId"], 34942764610)
        self.assertEqual(provider["jobId"], 104295027041)
        self.assertEqual(provider["artifactId"], 10388467797)
        self.assertEqual(
            provider["artifactArchiveSha256"],
            "f41c926d328b290b3f2d76cd0f187c526a542de8b177f4ce469119216323d913",
        )
        self.assertEqual(
            provider["matrixReceiptSha256"],
            "67903abb80f7550f290c7e4a67bb286ad857dc4291bf177d703724f8b18e2e84",
        )
        authority = self.record["authority"]
        self.assertTrue(authority["organizerPublicDevelopmentOnly"])
        for key, value in authority.items():
            if key != "organizerPublicDevelopmentOnly":
                self.assertFalse(value, key)
        self.assertFalse(self.record["sourceBoundary"]["rawArtifactBytesCommittedHere"])

    def test_rejected_v3_source_is_exact_measured_blob(self) -> None:
        raw = REJECTED_SOURCE.read_bytes()
        self.assertEqual(git_blob_sha1(raw), EXPECTED_V3_BLOB)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), EXPECTED_V3_SHA256)
        text = raw.decode("utf-8")
        self.assertIn('algorithm_str = "tjlabs_depth_throughput_portfolio_v3"', text)
        self.assertIn("population_size: int = 8", text)
        self.assertIn("snapback_patience: int = 7", text)
        self.assertIn("recycle_interval: int = 12", text)

    def test_all_nine_provider_row_receipts_recompute(self) -> None:
        self.assertEqual(len(self.rows), 9)
        self.assertEqual({row["seed"] for row in self.rows}, {7, 42, 73})
        self.assertEqual({row["candidate"] for row in self.rows}, {"v1", "v2", "v3"})
        for row in self.rows:
            unsigned = dict(row)
            receipt = unsigned.pop("receiptSha256")
            self.assertEqual(canonical_sha256(unsigned), receipt)
            source = self.record["candidateSources"][row["candidate"]]
            self.assertEqual(row["algorithm"], source["algorithm"])
            self.assertEqual(row["gitBlobSha1"], source["gitBlobSha1"])
            self.assertEqual(row["sourceSha256"], source["sourceSha256"])
            self.assertEqual(row["maxTimeSeconds"], 30)
            self.assertTrue(row["budgetExceeded"])
            self.assertGreater(row["evalCount"], 0)

    def test_summary_recomputes_and_v3_fails_precommitted_gate(self) -> None:
        by = {
            label: sorted(
                (row for row in self.rows if row["candidate"] == label),
                key=lambda row: row["seed"],
            )
            for label in ("v1", "v2", "v3")
        }
        summary = self.record["summary"]
        for label, rows in by.items():
            losses = [row["bestLoss"] for row in rows]
            evals = [row["evalCount"] for row in rows]
            saved = summary["candidates"][label]
            self.assertEqual(losses, saved["losses"])
            self.assertEqual(evals, saved["evalCounts"])
            self.assertEqual(statistics.fmean(losses), saved["meanBestLoss"])
            self.assertEqual(statistics.median(losses), saved["medianBestLoss"])
            self.assertEqual(statistics.fmean(evals), saved["meanEvalCount"])

        pairwise = {}
        for other in ("v1", "v2"):
            wins = losses = ties = 0
            for seed in (7, 42, 73):
                v3 = next(row["bestLoss"] for row in by["v3"] if row["seed"] == seed)
                baseline = next(row["bestLoss"] for row in by[other] if row["seed"] == seed)
                if v3 < baseline:
                    wins += 1
                elif v3 > baseline:
                    losses += 1
                else:
                    ties += 1
            pairwise[f"v3_vs_{other}"] = {"wins": wins, "losses": losses, "ties": ties}
        self.assertEqual(pairwise, summary["pairwise"])

        promote = (
            summary["candidates"]["v3"]["meanBestLoss"] < summary["candidates"]["v1"]["meanBestLoss"]
            and summary["candidates"]["v3"]["meanBestLoss"] < summary["candidates"]["v2"]["meanBestLoss"]
            and pairwise["v3_vs_v1"]["wins"] >= 2
            and pairwise["v3_vs_v2"]["wins"] >= 2
        )
        self.assertFalse(promote)
        self.assertFalse(summary["publicPromotionCriterionMet"])
        self.assertFalse(self.record["decision"]["publicPromotionCriterionMet"])
        self.assertEqual(self.record["decision"]["terminal"], "REJECT_V3")
        self.assertEqual(pairwise["v3_vs_v1"], {"wins": 0, "losses": 3, "ties": 0})
        self.assertEqual(pairwise["v3_vs_v2"], {"wins": 1, "losses": 2, "ties": 0})


if __name__ == "__main__":
    unittest.main()
