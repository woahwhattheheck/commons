from __future__ import annotations

import unittest

from revenue.tate_lyle_cp_kelco_solution_proof_gate.codec import digest
from revenue.tate_lyle_cp_kelco_solution_proof_gate.fixture import make_acceptance_batch
from revenue.tate_lyle_cp_kelco_solution_proof_gate.gate import evaluate, verify
from revenue.tate_lyle_cp_kelco_solution_proof_gate.rules import (
    HOLD_LEGACY,
    HOLD_OWNER,
    HOLD_REGION,
    HOLD_SPEC,
    HOLD_STABILITY,
)


class AcceptanceTests(unittest.TestCase):
    def test_acceptance_counts(self) -> None:
        batch = make_acceptance_batch()
        result = evaluate(batch)
        receipt = result["receipt"]
        self.assertEqual(receipt["record_count"], 120)
        self.assertEqual(receipt["pass_count"], 90)
        self.assertEqual(receipt["hold_count"], 30)
        self.assertEqual(receipt["seeded_defect_count"], 75)
        self.assertEqual(receipt["source_writes"], 0)
        self.assertEqual(receipt["network_writes"], 0)
        self.assertIs(receipt["external_authority"], False)
        self.assertTrue(verify(result, batch=batch))
        again = evaluate(batch)
        self.assertEqual(digest(result), digest(again))

    def test_defect_mix(self) -> None:
        batch = make_acceptance_batch()
        rows = evaluate(batch)["manifest"]["rows"]
        holds = [row for row in rows if row["status"] == "HOLD"]
        self.assertEqual(len(holds), 30)
        counts = {
            HOLD_SPEC: 0,
            HOLD_REGION: 0,
            HOLD_LEGACY: 0,
            HOLD_STABILITY: 0,
            HOLD_OWNER: 0,
        }
        for row in holds:
            for code in row["holds"]:
                counts[code] += 1
        self.assertEqual(counts[HOLD_SPEC], 20)
        self.assertEqual(counts[HOLD_REGION], 15)
        self.assertEqual(counts[HOLD_LEGACY], 15)
        self.assertEqual(counts[HOLD_STABILITY], 15)
        self.assertEqual(counts[HOLD_OWNER], 10)

    def test_code_record_pairs_stable(self) -> None:
        rows = evaluate(make_acceptance_batch())["manifest"]["rows"]
        pairs = [(row["record_id"], row["code"]) for row in rows]
        self.assertEqual(len(pairs), 120)
        self.assertEqual(pairs[0], ("REC-001", "TLCK-001"))
        self.assertEqual(pairs[-1], ("REC-120", "TLCK-120"))

    def test_duplicate_identical_collapses(self) -> None:
        batch = make_acceptance_batch()
        batch["records"] = batch["records"] + [dict(batch["records"][0])]
        result = evaluate(batch)
        self.assertEqual(result["receipt"]["record_count"], 120)

    def test_same_id_changed_payload_refuses(self) -> None:
        batch = make_acceptance_batch()
        changed = dict(batch["records"][0])
        changed["region"] = "APAC"
        batch["records"] = batch["records"] + [changed]
        with self.assertRaises(Exception):
            evaluate(batch)

    def test_verify_rejects_tamper(self) -> None:
        batch = make_acceptance_batch()
        result = evaluate(batch)
        result["receipt"]["pass_count"] = 91
        self.assertFalse(verify(result, batch=batch))


if __name__ == "__main__":
    unittest.main()
