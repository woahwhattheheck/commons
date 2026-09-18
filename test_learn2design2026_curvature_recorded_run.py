#!/usr/bin/env python3
"""Hermetic integrity checks for the retained Learn2Design curvature public matrix."""
from __future__ import annotations
import hashlib, json, statistics, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
RECORD=ROOT/"revenue"/"learn2design2026"/"recorded_runs"/"35183466350"/"curvature_public_matrix_index.json"

def canonical_sha256(value: dict) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",", ":")).encode()).hexdigest()

class Learn2DesignCurvatureRecordedRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads(RECORD.read_text())

    def test_provider_and_authority_pins(self):
        p=self.r["provider"]
        self.assertEqual((p["runId"],p["jobId"],p["artifactId"]),(35183466350,105080417640,10491562843))
        self.assertEqual(p["headSha"],"27cc4947aee1e09a4433691f6a9cdd4a717be3b3")
        self.assertEqual(p["artifactArchiveSha256"],"661cd9533253ed4fbda3c27fef6add6daaffd9b4eb3e9260d0c995f7084bac34")
        self.assertEqual(p["providerConclusion"],"success")
        self.assertTrue(self.r["authority"]["organizerPublicDevelopmentOnly"])
        for key,value in self.r["authority"].items():
            if key != "organizerPublicDevelopmentOnly": self.assertFalse(value,key)
        self.assertFalse(self.r["sourceBoundary"]["rawArtifactBytesCommittedHere"])

    def test_artifact_manifest_is_closed_and_unique(self):
        m=self.r["artifactMembers"]
        self.assertEqual(len(m),21)
        self.assertEqual(len({x["name"] for x in m}),21)
        self.assertEqual(sum(x["bytes"] for x in m),146214)
        for x in m:
            self.assertRegex(x["sha256"],r"^[0-9a-f]{64}$")

    def test_nine_measurement_receipts_and_source_pins(self):
        rows=self.r["measurements"]
        self.assertEqual(len(rows),9)
        self.assertEqual({x["seed"] for x in rows},{7,42,73})
        self.assertEqual({x["arm"] for x in rows},{"curvature_b8","v2_b8","v2_default_b16"})
        member_hash={x["name"]:x["sha256"] for x in self.r["artifactMembers"]}
        for row in rows:
            unsigned=dict(row); receipt=unsigned.pop("receiptSha256")
            self.assertEqual(canonical_sha256(unsigned),receipt)
            self.assertEqual(member_hash[row["artifactFile"]],row["artifactFileSha256"])
            self.assertEqual(row["status"],"COMPLETE_NO_FEASIBLE_POINT")
            self.assertEqual(row["feasibleFiniteEvaluations"],0)
            self.assertFalse(row["hasFeasiblePoint"])
            self.assertIsNone(row["officialScore"])

    def test_terminal_negative_summary_recomputes(self):
        rows=self.r["measurements"]; by=self.r["summary"]["byArm"]
        for arm in ("curvature_b8","v2_b8","v2_default_b16"):
            vals=[x["bestRawObjectiveLoss"] for x in rows if x["arm"]==arm]
            self.assertEqual(statistics.fmean(vals),by[arm]["meanBestRawObjectiveLoss"])
            self.assertEqual(by[arm]["feasibleCells"],0)
        self.assertFalse(self.r["decision"]["promotionAuthorized"])
        self.assertEqual(self.r["decision"]["terminal"],"RETAIN_NEGATIVE_NO_PROMOTION")

if __name__=="__main__": unittest.main()
