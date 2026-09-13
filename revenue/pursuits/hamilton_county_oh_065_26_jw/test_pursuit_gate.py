import copy
import json
import tempfile
import unittest
from pathlib import Path

from pursuit_gate import BUYER_REQUIREMENTS, PursuitInputError, evaluate, load_json

HERE = Path(__file__).resolve().parent
BASE = json.loads((HERE / "opportunity.json").read_text(encoding="utf-8"))


def controlling_ready():
    v = copy.deepcopy(BASE)
    v["sources"][0].update(status="AVAILABLE", sha256="a" * 64)
    for row in v["requirements"]:
        row["status"] = "SATISFIED"
        row["evidence_source_ids"] = ["county-gob2g-portal"]
        row["note"] = "Bound to recovered controlling official packet for test fixture."
        if row["key"] == "teaming_and_subcontracting_rules":
            row["value"] = True
    v["sources"].append({
        "id":"internal-fit","authority":"INTERNAL_EVIDENCE","url":"https://github.com/woahwhattheheck/commons",
        "status":"AVAILABLE","retrieved_at":"2026-09-13T10:30:00-04:00","sha256":"b"*64
    })
    v["capability_fit"] = {
        "prime":"EVIDENCED","teaming":"EVIDENCED","evidence_source_ids":["internal-fit"],
        "note":"Synthetic test fixture with available internal evidence."
    }
    return v


class PursuitGateTests(unittest.TestCase):
    def test_current_fixture_is_hold(self):
        result = evaluate(BASE)
        self.assertEqual(result["decision"], "HOLD")
        self.assertIn("controlling_solicitation_packet", result["blockers"])
        self.assertFalse(result["authority"]["proposal_submission_authorized"])

    def test_mirror_deadline_does_not_satisfy_requirement(self):
        v = copy.deepcopy(BASE)
        row = next(x for x in v["requirements"] if x["key"] == "response_deadline")
        row["status"] = "SATISFIED"
        result = evaluate(v)
        self.assertEqual(result["decision"], "HOLD")
        self.assertIn("unbound:response_deadline", result["blockers"])

    def test_official_general_does_not_satisfy_solicitation_requirement(self):
        v = copy.deepcopy(BASE)
        v["sources"].append({
            "id":"policy","authority":"OFFICIAL_GENERAL","url":"https://www.hamiltoncountyohio.gov/",
            "status":"AVAILABLE","retrieved_at":"2026-09-13T10:00:00-04:00","sha256":"c"*64
        })
        row = next(x for x in v["requirements"] if x["key"] == "response_deadline")
        row.update(status="SATISFIED", evidence_source_ids=["policy"])
        result = evaluate(v)
        self.assertIn("unbound:response_deadline", result["blockers"])

    def test_available_controlling_source_requires_digest(self):
        v = copy.deepcopy(BASE)
        v["sources"][0]["status"] = "AVAILABLE"
        with self.assertRaises(PursuitInputError):
            evaluate(v)

    def test_all_controlling_requirements_plus_prime_fit_yields_prime(self):
        self.assertEqual(evaluate(controlling_ready())["decision"], "PRIME")

    def test_prime_gap_teaming_fit_and_permission_yields_teaming(self):
        v = controlling_ready()
        v["capability_fit"]["prime"] = "GAP"
        self.assertEqual(evaluate(v)["decision"], "TEAMING")

    def test_teaming_not_true_holds_if_prime_gap(self):
        v = controlling_ready()
        v["capability_fit"]["prime"] = "GAP"
        row = next(x for x in v["requirements"] if x["key"] == "teaming_and_subcontracting_rules")
        row["value"] = False
        self.assertEqual(evaluate(v)["decision"], "HOLD")

    def test_dual_evidenced_fit_gap_is_no_bid(self):
        v = controlling_ready()
        v["capability_fit"]["prime"] = "GAP"
        v["capability_fit"]["teaming"] = "GAP"
        self.assertEqual(evaluate(v)["decision"], "NO_BID")

    def test_controlling_hard_disqualifier_is_no_bid(self):
        v = controlling_ready()
        row = next(x for x in v["requirements"] if x["key"] == "mandatory_qualifications_and_references")
        row["status"] = "DISQUALIFIER"
        result = evaluate(v)
        self.assertEqual(result["decision"], "NO_BID")
        self.assertIn("mandatory_qualifications_and_references", result["hard_disqualifiers"])

    def test_mirror_claimed_disqualifier_cannot_force_no_bid(self):
        v = copy.deepcopy(BASE)
        row = next(x for x in v["requirements"] if x["key"] == "mandatory_qualifications_and_references")
        row.update(status="DISQUALIFIER", evidence_source_ids=["highergov-mirror"])
        result = evaluate(v)
        self.assertEqual(result["decision"], "HOLD")
        self.assertFalse(result["hard_disqualifiers"])

    def test_missing_requirement_row_fails_closed(self):
        v = copy.deepcopy(BASE)
        v["requirements"] = v["requirements"][:-1]
        with self.assertRaises(PursuitInputError):
            evaluate(v)

    def test_duplicate_requirement_row_fails_closed(self):
        v = copy.deepcopy(BASE)
        v["requirements"].append(copy.deepcopy(v["requirements"][0]))
        with self.assertRaises(PursuitInputError):
            evaluate(v)

    def test_unknown_source_reference_fails_closed(self):
        v = copy.deepcopy(BASE)
        v["requirements"][0]["evidence_source_ids"] = ["missing"]
        with self.assertRaises(PursuitInputError):
            evaluate(v)

    def test_capability_fit_may_only_use_internal_evidence(self):
        v = copy.deepcopy(BASE)
        v["capability_fit"].update(prime="EVIDENCED", evidence_source_ids=["highergov-mirror"])
        with self.assertRaises(PursuitInputError):
            evaluate(v)

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.json"
            p.write_text('{"a":1,"a":2}', encoding="utf-8")
            with self.assertRaises(PursuitInputError):
                load_json(p)

    def test_nonfinite_json_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.json"
            p.write_text('{"a":NaN}', encoding="utf-8")
            with self.assertRaises(PursuitInputError):
                load_json(p)

    def test_result_is_deterministic_and_receipted(self):
        a = evaluate(BASE)
        b = evaluate(copy.deepcopy(BASE))
        self.assertEqual(a, b)
        self.assertEqual(len(a["receipt_sha256"]), 64)

    def test_authority_ceiling_is_always_false(self):
        for fixture in (BASE, controlling_ready()):
            auth = evaluate(fixture)["authority"]
            self.assertTrue(all(value is False for value in auth.values()))

    def test_requirement_contract_is_explicit(self):
        self.assertEqual(len(BUYER_REQUIREMENTS), 19)


if __name__ == "__main__":
    unittest.main()
