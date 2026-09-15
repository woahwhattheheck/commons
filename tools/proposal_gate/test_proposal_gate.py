import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
import proposal_gate as pg


class ProposalGateTests(unittest.TestCase):
    def test_missing_mandatory_evidence_blocks(self):
        reqs = [{"id":"FIN-1","section":"Vendor","type":"mandatory","statement":"Provide financial evidence","evidence":["financials"],"response":"Attached."}]
        result = pg.evaluate(reqs, [])
        self.assertEqual(result[0].disposition, "BLOCKED")
        self.assertFalse(pg.summarize(result)["submission_ready"])

    def test_owner_gate_blocks_even_with_evidence(self):
        reqs = [{"id":"SIG-1","section":"Cover","type":"mandatory","statement":"Authorized signature","evidence":["signature"],"response":"Signed.","owner_gate":True}]
        evidence = [{"id":"signature","status":"available"}]
        result = pg.evaluate(reqs, evidence)
        self.assertEqual(result[0].disposition, "BLOCKED")
        self.assertIn("SIG-1", pg.summarize(result)["owner_gates"])

    def test_placeholder_is_not_a_response(self):
        reqs = [{"id":"A-1","section":"A","type":"mandatory","statement":"Describe architecture","evidence":[],"response":"[TBD — insert architecture]"}]
        result = pg.evaluate(reqs, [])
        self.assertEqual(result[0].disposition, "BLOCKED")

    def test_scored_gap_is_at_risk_not_hard_block(self):
        reqs = [{"id":"REF-1","section":"Vendor","type":"scored","statement":"References where available","evidence":["refs"],"response":"See references."}]
        result = pg.evaluate(reqs, [])
        self.assertEqual(result[0].disposition, "AT_RISK")
        self.assertTrue(pg.summarize(result)["submission_ready"])

    def test_ready_payload_and_renderers(self):
        reqs = [{"id":"A-1","section":"Architecture","type":"mandatory","statement":"Describe scalability","evidence":["arch"],"response":"Horizontal workers with bounded queues."}]
        evidence = [{"id":"arch","status":"available"}]
        result = pg.evaluate(reqs, evidence)
        summary = pg.summarize(result)
        self.assertTrue(summary["submission_ready"])
        self.assertEqual(summary["readiness_percent"], 100.0)
        self.assertIn("**READY**", pg.render_markdown(reqs, result))
        self.assertIn("[TBD", pg.render_skeleton(reqs))
        self.assertIn("Horizontal workers", pg.render_draft(reqs))

    def test_duplicate_requirement_rejected(self):
        reqs = [
            {"id":"X","statement":"one","evidence":[]},
            {"id":"X","statement":"two","evidence":[]},
        ]
        with self.assertRaises(ValueError):
            pg.evaluate(reqs, [])


if __name__ == "__main__":
    unittest.main()
