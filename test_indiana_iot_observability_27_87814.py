import copy, unittest
from opportunities.indiana_iot_observability_27_87814.gate import GateError, compile_pursuit, loads_strict
import json
from pathlib import Path

PKG=Path(__file__).resolve().parent/"opportunities"/"indiana_iot_observability_27_87814"
def load(name): return json.loads((PKG/name).read_text())
BASE_LEDGER=load("source_ledger.json")
BASE_REQS=load("requirements.json")
BASE_PARTNERS=load("partner_targets.json")
BASE_SCOPE=load("paid_specialist_scope.json")
NOW="2026-09-17T19:20:00Z"

class ObservabilityPursuitTests(unittest.TestCase):
    def compile(self,l=None,r=None,p=None,s=None):
        return compile_pursuit(l or BASE_LEDGER,r or BASE_REQS,p or BASE_PARTNERS,s or BASE_SCOPE,now=NOW)

    def test_current_carrier_holds(self):
        out=self.compile()
        self.assertEqual(out["decision"],"HOLD")
        self.assertIn("CONTROLLING_PACKAGE_NOT_RETAINED",out["reasons"])
        self.assertFalse(any(out["external_authority"].values()))

    def test_mirror_never_controls_buyer_terms(self):
        bad=copy.deepcopy(BASE_LEDGER)
        mirror=next(x for x in bad["sources"] if x["authority"]=="DISCOVERY_MIRROR")
        mirror["retained"]=True
        mirror["controls"]=["submission_mechanics"]
        with self.assertRaisesRegex(GateError,"cannot control package-only"):
            self.compile(l=bad)

    def test_unretained_source_never_controls_anything(self):
        bad=copy.deepcopy(BASE_LEDGER)
        notice=next(x for x in bad["sources"] if x["authority"]=="OFFICIAL_PUBLIC_NOTICE")
        notice["controls"]=["title"]
        with self.assertRaisesRegex(GateError,"cannot control fields without retained bytes"):
            self.compile(l=bad)

    def test_proven_requirement_requires_evidence(self):
        bad=copy.deepcopy(BASE_REQS)
        row=next(x for x in bad["requirements"] if x["id"]=="security_compliance")
        row["state"]="PROVEN"
        with self.assertRaisesRegex(GateError,"requires retained evidence"):
            self.compile(r=bad)

    def test_nonproven_requirement_cannot_smuggle_positive_evidence(self):
        bad=copy.deepcopy(BASE_REQS)
        row=next(x for x in bad["requirements"] if x["id"]=="security_compliance")
        row["evidence"]=["vendor-marketing"]
        with self.assertRaisesRegex(GateError,"non-PROVEN"):
            self.compile(r=bad)

    def test_partner_target_cannot_claim_contact(self):
        bad=copy.deepcopy(BASE_PARTNERS)
        bad["targets"][0]["contact_authority"]=True
        with self.assertRaisesRegex(GateError,"contact authority"):
            self.compile(p=bad)

    def test_scope_template_cannot_invent_price(self):
        bad=copy.deepcopy(BASE_SCOPE)
        bad["price_usd"]=25000
        with self.assertRaisesRegex(GateError,"price must remain unset"):
            self.compile(s=bad)

    def test_package_alone_does_not_make_prime(self):
        ledger=copy.deepcopy(BASE_LEDGER)
        pkg=next(x for x in ledger["sources"] if x["authority"]=="OFFICIAL_CONTROLLING_PACKAGE")
        pkg["retained"]=True
        out=self.compile(l=ledger)
        self.assertEqual(out["decision"],"HOLD")
        self.assertIn("PRIME_QUALIFICATION_NOT_PROVEN",out["reasons"])

    def test_mirror_intelligence_is_labeled_discovery_only(self):
        out=self.compile()
        self.assertTrue(out["mirror_intelligence"])
        self.assertEqual({x["authority"] for x in out["mirror_intelligence"]},{"DISCOVERY_ONLY"})

    def test_duplicate_keys_and_nonfinite_fail(self):
        with self.assertRaisesRegex(GateError,"duplicate JSON key"):
            loads_strict('{"x":1,"x":2}')
        with self.assertRaisesRegex(GateError,"non-finite"):
            loads_strict('{"x":NaN}')

if __name__=="__main__":
    unittest.main(verbosity=2)
