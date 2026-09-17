import copy
import pathlib
import subprocess
import sys
import unittest

from revenue.partner_opportunity_qualification_gate.engine import QualificationError, compile_qualification
from revenue.partner_opportunity_qualification_gate.test_gate import packet, ref, src


class PartnerOpportunityQualificationEvidenceKindTests(unittest.TestCase):
    def test_solicitation_requirement_cannot_satisfy_partner_gate(self):
        p = packet()
        p["partners"][0]["gate_dispositions"][0]["evidence_refs"] = [ref("rfp", "a")]
        with self.assertRaises(QualificationError):
            compile_qualification(p)

    def test_owner_workshare_evidence_cannot_satisfy_partner_gate(self):
        p = packet()
        p["sources"].append(
            src(
                "owner-workshare",
                "OWNER_WORKSHARE_EVIDENCE",
                "d",
                "https://owner.example/workshare",
            )
        )
        p["partners"][0]["gate_dispositions"][0]["evidence_refs"] = [
            ref("owner-workshare", "d")
        ]
        with self.assertRaises(QualificationError):
            compile_qualification(p)

    def test_partner_specific_evidence_still_satisfies_partner_gate(self):
        out = compile_qualification(packet())
        self.assertEqual(out["partners"][0]["state"], "READY_FOR_MUSE_ELECTION_ONLY")

    def test_predecessor_replays_under_real_python_optimized(self):
        if sys.flags.optimize:
            return
        root = pathlib.Path(__file__).resolve().parent
        proc = subprocess.run(
            [
                sys.executable,
                "-O",
                "-m",
                "unittest",
                "-v",
                f"{pathlib.Path(__file__).stem}.PartnerOpportunityQualificationEvidenceKindTests.test_solicitation_requirement_cannot_satisfy_partner_gate",
                f"{pathlib.Path(__file__).stem}.PartnerOpportunityQualificationEvidenceKindTests.test_owner_workshare_evidence_cannot_satisfy_partner_gate",
                f"{pathlib.Path(__file__).stem}.PartnerOpportunityQualificationEvidenceKindTests.test_partner_specific_evidence_still_satisfies_partner_gate",
            ],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("Ran 3 tests", proc.stderr)


if __name__ == "__main__":
    unittest.main()