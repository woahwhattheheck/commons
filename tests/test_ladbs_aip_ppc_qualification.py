import importlib.util
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PACK = ROOT / "pursuits" / "ladbs_aip_ppc_222114"
SPEC = importlib.util.spec_from_file_location("proposal_gate", ROOT / "tools" / "proposal_gate" / "proposal_gate.py")
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)

class LadbsQualificationPackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.requirements = json.loads((PACK / "requirements.json").read_text())["requirements"]
        cls.evidence = json.loads((PACK / "evidence.json").read_text())["evidence"]
        cls.sources = json.loads((PACK / "sources.json").read_text())
        cls.results = MOD.evaluate(cls.requirements, cls.evidence)
        cls.summary = MOD.summarize(cls.results)

    def test_identity_is_bound(self):
        opp = self.sources["opportunity"]
        self.assertEqual(opp["opportunityId"], "222114")
        self.assertEqual(opp["rfpId"], "2025AIP007")
        self.assertFalse(opp["controllingPackageBytesRecovered"])
        self.assertEqual(opp["currentDisposition"], "HOLD_CONTROLLING_PACKAGE_BYTES")

    def test_gate_is_deliberately_not_submission_ready(self):
        self.assertFalse(self.summary["submission_ready"])
        self.assertIn("GATE-001", self.summary["blocking_requirements"])
        self.assertIn("GATE-003", self.summary["blocking_requirements"])
        self.assertIn("GATE-010", self.summary["owner_gates"])

    def test_conference_is_not_promoted_to_fact_or_attendance(self):
        signal = next(x for x in self.sources["secondaryOnlyRiskSignals"] if "Conference" in x["signal"] or "conference" in x["signal"] )
        self.assertEqual(signal["status"], "UNCONFIRMED_CONTROLLING_BYTES_REQUIRED")
        ev = {x["id"]: x for x in self.evidence}
        self.assertEqual(ev["E-CONFERENCE-ATTENDANCE"]["status"], "missing")

    def test_no_external_authority_evidence_is_faked(self):
        ev = {x["id"]: x for x in self.evidence}
        for key in ["E-RAMP-REGISTRATION","E-REFERENCES","E-INSURANCE","E-BIP","E-CITY-FORMS","E-PRICE-AUTH","E-SIGN-AUTH","E-IMPLEMENTATION-STAFF"]:
            self.assertEqual(ev[key]["status"], "missing")

    def test_generated_readiness_receipt_stays_no_go(self):
        receipt = json.loads((PACK / "CURRENT-READINESS.json").read_text())
        self.assertEqual(receipt["expectedCheckExit"], 2)
        self.assertFalse(receipt["summary"]["submission_ready"])
        self.assertEqual(receipt["summary"], self.summary)

    def test_third_party_budget_is_excluded_as_authority(self):
        self.assertIn("third-party AI budget estimates", self.sources["excludedAsAuthority"])

    def test_full_33_document_inventory_is_bound(self):
        self.assertEqual(self.sources["knownPackageDocumentCount"], 33)
        self.assertEqual(len(self.sources["knownPackageDocuments"]), 33)

    def test_required_document_names_are_present(self):
        docs = set(self.sources["knownPackageDocuments"] )
        self.assertIn("RFP 2025AIP007 AI Powered Pre-Plan Check Assistant Services FINAL 070126.pdf", docs)
        self.assertIn("2025AIP007 RFP Addendum 1 072326.pdf", docs)
        self.assertIn("Appendix 3 - Func Tech Reqs & Use Case Matrix FINAL 070126.pdf", docs)
        self.assertIn("Exhibit 7 - Aritifical Intelligence System Technical Disclosures Form FINAL [fillable] 062426.pdf", docs)

if __name__ == "__main__": unittest.main()
